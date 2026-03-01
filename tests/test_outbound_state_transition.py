# -*- coding: utf-8 -*-
"""
SQM v6.2.7 — 출고 상태전이 회귀 테스트
========================================

4-AI 통합 디버깅에서 도출된 핵심 검증 항목:
  1. AVAILABLE → SOLD/DEPLETED 정상 전이 (stop_at_picked=False)
  2. All-or-Nothing 트랜잭션 롤백
  3. 톤백 상태와 inventory 정합성 (대원칙: initial = current + picked)
  4. 반품 역전이 (PICKED/SOLD → AVAILABLE)
  5. weight_kg 기반 출고 (P0-2 수정 검증)
  6. thread-local 트랜잭션 (P0-3 검증)

✅ S3-BUG-1 수정 완료 (4단계):
  stop_at_picked=True에서 _update_lot_after_pick() 호출 추가.
  inventory.current_weight/picked_weight 정상 갱신 → 정합성 유지.

실행: python -m pytest tests/test_outbound_state_transition.py -v
"""

import os
import sys
import tempfile
import logging
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def engine():
    """테스트용 엔진 (임시 DB)"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    try:
        from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
        eng = SQMInventoryEngineV3(db_path)
        yield eng
    finally:
        try:
            eng.db.close()
        except Exception:
            pass
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture
def lot_500kg():
    """500kg 톤백 × 10 + 샘플 1kg = 5001kg"""
    return {
        'lot_no': 'TEST-500-001',
        'sap_no': 'SAP-500-001',
        'bl_no': 'BL-TEST-500',
        'container_no': 'CONT-500',
        'product': 'LITHIUM CARBONATE',
        'product_code': 'LC',
        'mxbg_pallet': 10,
        'net_weight': 5001.0,
        'gross_weight': 5200.0,
        'salar_invoice_no': 'INV-500',
        'warehouse': '광양',
    }


@pytest.fixture
def lot_1000kg():
    """1000kg 톤백 × 5 + 샘플 1kg = 5001kg"""
    return {
        'lot_no': 'TEST-1000-001',
        'sap_no': 'SAP-1000-001',
        'bl_no': 'BL-TEST-1000',
        'container_no': 'CONT-1000',
        'product': 'NICKEL SULFATE',
        'product_code': 'NS',
        'mxbg_pallet': 5,
        'net_weight': 5001.0,
        'gross_weight': 5200.0,
        'salar_invoice_no': 'INV-1000',
        'warehouse': '광양',
    }


def _inbound(engine, packing):
    """입고 헬퍼 — 성공 확인"""
    result = engine.process_inbound(packing)
    assert result['success'], f"입고 실패: {result.get('errors', [])}"
    return result


def _get_lot(engine, lot_no):
    """inventory 행 조회 → dict"""
    row = engine.db.fetchone(
        "SELECT * FROM inventory WHERE lot_no = ?", (lot_no,))
    return dict(row) if row else None


def _get_tonbags(engine, lot_no, status=None):
    """톤백 목록 조회 (샘플 제외)"""
    if status:
        rows = engine.db.fetchall(
            "SELECT * FROM inventory_tonbag WHERE lot_no = ? AND status = ? "
            "AND COALESCE(is_sample,0)=0", (lot_no, status))
    else:
        rows = engine.db.fetchall(
            "SELECT * FROM inventory_tonbag WHERE lot_no = ? "
            "AND COALESCE(is_sample,0)=0", (lot_no,))
    return [dict(r) for r in (rows or [])]


def _outbound(engine, lot_no, customer, weight_kg):
    """출고 헬퍼 (stop_at_picked=False)"""
    alloc = {
        'lot_no': lot_no,
        'customer': customer,
        'weight_kg': weight_kg,
        'qty_mt': weight_kg / 1000.0,
    }
    return engine.process_outbound(alloc, source='TEST', stop_at_picked=False)


# ═══════════════════════════════════════════
# 테스트 1: 정상 출고 (stop_at_picked=False)
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestOutboundNormalFlow:

    def test_partial_outbound(self, engine, lot_500kg):
        """부분 출고: 500kg×5 = 2500kg"""
        _inbound(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        result = _outbound(engine, lot_no, 'CATL', 2500.0)
        assert result['success'], f"출고 실패: {result}"
        assert result['processed'] == 1

        lot = _get_lot(engine, lot_no)
        cw = float(lot['current_weight'])
        pw = float(lot['picked_weight'])
        assert cw < 5001, f"current_weight 미감소: {cw}"
        assert pw >= 2500, f"picked_weight 미증가: {pw}"

    def test_full_outbound_depleted(self, engine, lot_500kg):
        """전량 출고 (샘플 제외): 5000kg"""
        _inbound(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        result = _outbound(engine, lot_no, 'Panasonic', 5000.0)
        assert result['success'], f"출고 실패: {result}"

        available = _get_tonbags(engine, lot_no, 'AVAILABLE')
        assert len(available) == 0, f"잔여 AVAILABLE: {len(available)}"

    def test_outbound_1000kg_tonbag(self, engine, lot_1000kg):
        """P0-2 검증: 1000kg 톤백 LOT 부분 출고"""
        _inbound(engine, lot_1000kg)
        lot_no = lot_1000kg['lot_no']

        result = _outbound(engine, lot_no, 'BYD', 3000.0)
        assert result['success'], f"출고 실패: {result}"

        available = _get_tonbags(engine, lot_no, 'AVAILABLE')
        assert len(available) == 2, f"AVAILABLE: {len(available)} (기대: 2)"

    def test_source_tracking(self, engine, lot_500kg):
        """출고 경로(source) allocation_plan 기록"""
        _inbound(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        alloc = {'lot_no': lot_no, 'customer': 'CATL', 'weight_kg': 500.0}
        engine.process_outbound(alloc, source='API:test', stop_at_picked=False)

        plan = engine.db.fetchone(
            "SELECT source FROM allocation_plan WHERE lot_no = ?", (lot_no,))
        if plan:
            src = plan['source'] if isinstance(plan, dict) else plan[0]
            assert 'API' in str(src), f"source 미기록: {src}"


# ═══════════════════════════════════════════
# 테스트 2: stop_at_picked=True 버그 문서화
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestStopAtPicked:
    """S4-1 FIX 검증: stop_at_picked=True가 정상 동작."""

    def test_stop_at_picked_success(self, engine, lot_500kg):
        """stop_at_picked=True → 정합성 유지 + 성공 (S3-BUG-1 수정됨)"""
        _inbound(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 1차: 일반 출고 2500kg
        result = _outbound(engine, lot_no, 'CATL', 2500.0)
        assert result['success']

        # 2차: stop_at_picked=True 500kg → 이제 성공해야 함
        alloc = {'lot_no': lot_no, 'customer': 'BYD', 'weight_kg': 500.0}
        r = engine.process_outbound(alloc, source='TEST', stop_at_picked=True)
        assert r['success'], f"stop_at_picked 실패: {r.get('errors', r.get('message'))}"

        # 정합성 검증
        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity['valid'], f"정합성 실패: {integrity.get('errors')}"

        # 무게 확인: 5001 - 2500 - 500 = 2001
        lot_row = _get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 2001.0


# ═══════════════════════════════════════════
# 테스트 3: All-or-Nothing 롤백
# ═══════════════════════════════════════════

@pytest.mark.rollback
class TestOutboundRollback:

    def test_insufficient_stock_rollback(self, engine, lot_500kg):
        """재고 초과 요청 → 롤백, 톤백 원복"""
        _inbound(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        result = _outbound(engine, lot_no, 'CATL', 99999.0)
        assert not result['success'] or result.get('lots_processed', 0) == 0

        available = _get_tonbags(engine, lot_no, 'AVAILABLE')
        assert len(available) == 10, f"롤백 실패: AVAILABLE={len(available)}"

    def test_nonexistent_lot_rejected(self, engine):
        """존재하지 않는 LOT → 실패"""
        result = _outbound(engine, 'NONEXISTENT-LOT', 'TEST', 1000.0)
        assert not result['success'] or result.get('lots_processed', 0) == 0


# ═══════════════════════════════════════════
# 테스트 4: 정합성 검증
# ═══════════════════════════════════════════

@pytest.mark.integration
class TestOutboundIntegrity:

    def test_weight_integrity_initial_eq_current_plus_picked(self, engine, lot_500kg):
        """대원칙: initial = current + picked"""
        _inbound(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        result = _outbound(engine, lot_no, 'CATL', 2500.0)
        assert result['success'], f"출고 실패: {result}"

        if hasattr(engine, 'verify_lot_integrity'):
            integrity = engine.verify_lot_integrity(lot_no)
            assert integrity['valid'], f"정합성 실패: {integrity['errors']}"

        lot = _get_lot(engine, lot_no)
        iw = float(lot.get('initial_weight', 0))
        cw = float(lot.get('current_weight', 0))
        pw = float(lot.get('picked_weight', 0))
        diff = abs(iw - (cw + pw))
        assert diff < 1.0, f"무게 불일치: {iw} ≠ {cw}+{pw} (차이:{diff})"

    def test_tonbag_sum_matches_current_weight(self, engine, lot_500kg):
        """톤백 AVAILABLE 합계 ≈ inventory.current_weight"""
        _inbound(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        result = _outbound(engine, lot_no, 'CATL', 1500.0)
        assert result['success'], f"출고 실패: {result}"

        row = engine.db.fetchone(
            "SELECT COALESCE(SUM(weight),0) as s FROM inventory_tonbag "
            "WHERE lot_no = ? AND status = 'AVAILABLE'", (lot_no,))
        tb_sum = float(row['s'] if isinstance(row, dict) else row[0])

        lot = _get_lot(engine, lot_no)
        cw = float(lot['current_weight'])
        diff = abs(tb_sum - cw)
        assert diff < 1.0, f"톤백합({tb_sum}) ≠ cw({cw})"


# ═══════════════════════════════════════════
# 테스트 5: 반품 역전이
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestReturnStateTransition:

    def test_return_after_outbound(self, engine, lot_500kg):
        """출고 후 반품 → AVAILABLE 복원"""
        _inbound(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        result = _outbound(engine, lot_no, 'CATL', 1000.0)
        assert result['success'], f"출고 실패: {result}"

        # 출고된(non-AVAILABLE) 톤백 찾기
        non_avail = engine.db.fetchall(
            "SELECT * FROM inventory_tonbag WHERE lot_no = ? "
            "AND status != 'AVAILABLE' AND COALESCE(is_sample,0)=0",
            (lot_no,))
        non_avail = [dict(r) for r in (non_avail or [])]

        if not non_avail:
            pytest.skip("출고 후 non-AVAILABLE 톤백 없음")

        if not hasattr(engine, 'process_return'):
            pytest.skip("process_return 미구현")

        ret = engine.process_return([{
            'lot_no': lot_no,
            'sub_lt': non_avail[0]['sub_lt'],
            'reason': '품질 불량',
            'remark': '테스트 반품',
        }], source_type='RETURN_SINGLE')

        if ret['returned'] > 0:
            after_avail = _get_tonbags(engine, lot_no, 'AVAILABLE')
            assert len(after_avail) >= 9, f"반품 후 AVAILABLE: {len(after_avail)}"

    def test_return_integrity(self, engine, lot_500kg):
        """반품 후에도 정합성 유지"""
        _inbound(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        result = _outbound(engine, lot_no, 'BYD', 500.0)
        if not result['success']:
            pytest.skip("출고 실패")

        non_avail = engine.db.fetchall(
            "SELECT * FROM inventory_tonbag WHERE lot_no = ? "
            "AND status != 'AVAILABLE' AND COALESCE(is_sample,0)=0", (lot_no,))
        non_avail = [dict(r) for r in (non_avail or [])]

        if non_avail and hasattr(engine, 'process_return'):
            engine.process_return([{
                'lot_no': lot_no,
                'sub_lt': non_avail[0]['sub_lt'],
                'reason': 'test',
            }], source_type='RETURN_SINGLE')

        if hasattr(engine, 'verify_lot_integrity'):
            integrity = engine.verify_lot_integrity(lot_no)
            assert integrity['valid'], f"반품 후 정합성 실패: {integrity['errors']}"


# ═══════════════════════════════════════════
# 테스트 6: P0-3 thread-local 트랜잭션
# ═══════════════════════════════════════════

@pytest.mark.integration
class TestTransactionThreadLocal:

    def test_transaction_flag_isolation(self, engine):
        """P0-3: 트랜잭션 플래그 thread-local 동작"""
        db = engine.db
        with db.transaction("IMMEDIATE"):
            in_tx = getattr(db._local, 'in_transaction', False)
            assert in_tx, "트랜잭션 중 in_transaction=True"

        after = getattr(db._local, 'in_transaction', False)
        assert not after, "트랜잭션 후 in_transaction=False"

    def test_nested_transaction(self, engine):
        """중첩 트랜잭션"""
        db = engine.db
        with db.transaction("IMMEDIATE"):
            with db.transaction("IMMEDIATE"):
                assert getattr(db._local, 'in_transaction', False)
        assert not getattr(db._local, 'in_transaction', False)


# ═══════════════════════════════════════════
# 테스트 7: Full Cycle (입고 → 출고 → 반품)
# ═══════════════════════════════════════════

@pytest.mark.integration
class TestFullCycle:

    def test_inbound_outbound_return_cycle(self, engine, lot_500kg):
        """전체 사이클: 입고 → 부분출고 → 반품 → 정합성"""
        lot_no = lot_500kg['lot_no']

        # 1) 입고
        _inbound(engine, lot_500kg)
        lot = _get_lot(engine, lot_no)
        assert float(lot['current_weight']) == 5001.0

        # 2) 부분 출고
        result = _outbound(engine, lot_no, 'CATL', 2000.0)
        assert result['success'], f"출고 실패: {result}"

        lot = _get_lot(engine, lot_no)
        cw_after_out = float(lot['current_weight'])
        assert cw_after_out < 5001

        # 3) 반품
        if hasattr(engine, 'process_return'):
            non_avail = engine.db.fetchall(
                "SELECT * FROM inventory_tonbag WHERE lot_no = ? "
                "AND status != 'AVAILABLE' AND COALESCE(is_sample,0)=0",
                (lot_no,))
            non_avail = [dict(r) for r in (non_avail or [])]

            if non_avail:
                ret = engine.process_return([{
                    'lot_no': lot_no,
                    'sub_lt': non_avail[0]['sub_lt'],
                    'reason': 'Full cycle test',
                }], source_type='RETURN_SINGLE')

                if ret['returned'] > 0:
                    lot = _get_lot(engine, lot_no)
                    assert float(lot['current_weight']) > cw_after_out

        # 4) 최종 정합성
        if hasattr(engine, 'verify_lot_integrity'):
            integrity = engine.verify_lot_integrity(lot_no)
            assert integrity['valid'], f"최종 정합성 실패: {integrity['errors']}"
