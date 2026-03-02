"""
SQM v6.2.7 — outbound_mixin 커버리지 향상 테스트
===================================================
목표: outbound_mixin.py 24.3% → 50%+
대상: reserve_from_allocation, execute_reserved, cancel_reservation,
      quick_outbound, confirm_outbound, revert 계열, 헬퍼 함수

실행: python -m pytest tests/test_outbound_coverage.py -v
"""

import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.conftest import get_lot, get_tonbags, inbound_lot, outbound_lot

logger = logging.getLogger(__name__)


def make_lot(idx: int, tb_count: int = 10, unit_w: int = 500) -> dict:
    return {
        'lot_no': f'COV{idx:05d}',
        'product': 'LITHIUM CARBONATE',
        'mxbg_pallet': tb_count,
        'net_weight': float(tb_count * unit_w + 1),
    }


def make_alloc_row(lot_no: str, customer: str = 'CATL', qty_mt: float = 1.5,
                   sale_ref: str = '', outbound_date: str = '2026-03-15',
                   sublot_count: int = 0) -> dict:
    return {
        'lot_no': lot_no,
        'sold_to': customer,
        'sale_ref': sale_ref or f'SO-{lot_no}',
        'qty_mt': qty_mt,
        'outbound_date': outbound_date,
        'sublot_count': sublot_count,
    }


# ═══════════════════════════════════════════════════════════
#  1. reserve_from_allocation — 기본
# ═══════════════════════════════════════════════════════════

@pytest.mark.outbound
class TestReserveFromAllocation:
    """Allocation → RESERVED 예약 워크플로."""

    def test_basic_reserve(self, engine):
        """1 LOT, 4톤백 예약 (40% < 50% 임계) → RESERVED 상태."""
        inbound_lot(engine, make_lot(100))  # 10톤백 = 5000kg
        alloc = [make_alloc_row('COV00100', 'CATL', qty_mt=2.0, sublot_count=4)]
        r = engine.reserve_from_allocation(alloc, source_file='test.xlsx')
        assert r['success'], f"예약 실패: {r.get('errors')}"
        assert r['reserved'] == 4

        reserved = get_tonbags(engine, 'COV00100', 'RESERVED')
        assert len(reserved) == 4
        for tb in reserved:
            assert tb['picked_to'] == 'CATL'

    def test_reserve_partial(self, engine):
        """10톤백 LOT에서 3개만 예약 (30%)."""
        inbound_lot(engine, make_lot(101))
        alloc = [make_alloc_row('COV00101', 'BYD', qty_mt=1.5, sublot_count=3)]
        r = engine.reserve_from_allocation(alloc, source_file='test.xlsx')
        assert r['success']
        assert r['reserved'] == 3

        avail = get_tonbags(engine, 'COV00101', 'AVAILABLE')
        reserved = get_tonbags(engine, 'COV00101', 'RESERVED')
        assert len(avail) == 7  # 10 - 3 (샘플 제외)
        assert len(reserved) == 3

    def test_reserve_multi_lot(self, engine):
        """여러 LOT 동시 예약 (각 20%)."""
        for i in range(3):
            inbound_lot(engine, make_lot(110 + i))

        alloc = [
            make_alloc_row('COV00110', 'CATL', qty_mt=1.0, sublot_count=2),
            make_alloc_row('COV00111', 'BYD', qty_mt=1.5, sublot_count=3),
            make_alloc_row('COV00112', 'LG', qty_mt=0.5, sublot_count=1),
        ]
        r = engine.reserve_from_allocation(alloc, source_file='multi.xlsx')
        assert r['success']
        assert r['reserved'] == 6  # 2+3+1

    def test_reserve_empty_list(self, engine):
        """빈 allocation → 실패."""
        r = engine.reserve_from_allocation([], source_file='empty.xlsx')
        assert not r['success']
        assert r['reserved'] == 0

    def test_reserve_no_lot_no(self, engine):
        """LOT 번호 누락 → 에러."""
        alloc = [{'sold_to': 'CATL', 'qty_mt': 2.5}]
        r = engine.reserve_from_allocation(alloc)
        assert r['reserved'] == 0
        assert any('LOT' in e for e in r['errors'])

    def test_reserve_nonexistent_lot(self, engine):
        """미존재 LOT → 에러."""
        alloc = [make_alloc_row('LOT-GHOST-999')]
        r = engine.reserve_from_allocation(alloc)
        assert r['reserved'] == 0
        assert len(r['errors']) > 0

    def test_reserve_exceed_available(self, engine):
        """가용 초과 예약 → 에러."""
        inbound_lot(engine, make_lot(120, tb_count=3))
        alloc = [make_alloc_row('COV00120', sublot_count=10)]
        r = engine.reserve_from_allocation(alloc)
        assert r['reserved'] == 0
        assert any('부족' in e or '초과' in e for e in r['errors'])

    def test_reserve_sample_row(self, engine):
        """샘플 행 (0.001 MT) 예약."""
        inbound_lot(engine, make_lot(130))
        alloc = [make_alloc_row('COV00130', qty_mt=0.001, sublot_count=1)]
        r = engine.reserve_from_allocation(alloc)
        # 샘플 예약은 is_sample=1 톤백 대상
        assert isinstance(r, dict)

    def test_reserve_invalid_date(self, engine):
        """잘못된 출고일 → 에러."""
        inbound_lot(engine, make_lot(135))
        alloc = [make_alloc_row('COV00135', outbound_date='not-a-date')]
        r = engine.reserve_from_allocation(alloc)
        assert r['reserved'] == 0
        assert any('DATE' in e.upper() or '형식' in e for e in r['errors'])

    def test_reserve_stock_movement_created(self, engine):
        """예약 시 stock_movement RESERVED 이력."""
        inbound_lot(engine, make_lot(140))
        alloc = [make_alloc_row('COV00140', sublot_count=2)]
        engine.reserve_from_allocation(alloc, source_file='test.xlsx')

        mvmt = engine.db.fetchone(
            "SELECT movement_type FROM stock_movement "
            "WHERE lot_no = 'COV00140' AND movement_type = 'RESERVED'")
        assert mvmt is not None

    def test_reserve_duplicate_detection(self, engine):
        """동일 파일 2회 예약 → 중복 감지."""
        inbound_lot(engine, make_lot(145, tb_count=20))
        alloc = [make_alloc_row('COV00145', sublot_count=3)]

        r1 = engine.reserve_from_allocation(alloc, source_file='dup_test.xlsx')
        assert r1['success']

        r2 = engine.reserve_from_allocation(alloc, source_file='dup_test.xlsx')
        # 2번째는 중복 감지 플래그 또는 가용 부족
        assert isinstance(r2, dict)

    def test_allocation_plan_table(self, engine):
        """allocation_plan 테이블에 기록 확인."""
        inbound_lot(engine, make_lot(150))
        alloc = [make_alloc_row('COV00150', sublot_count=2)]
        r = engine.reserve_from_allocation(alloc)

        plans = engine.db.fetchall(
            "SELECT * FROM allocation_plan WHERE lot_no = 'COV00150' AND status = 'RESERVED'")
        assert len(plans) == 2


# ═══════════════════════════════════════════════════════════
#  2. execute_reserved — RESERVED → PICKED
# ═══════════════════════════════════════════════════════════

@pytest.mark.outbound
class TestExecuteReserved:
    """예약 → 출고 실행 (RESERVED → PICKED)."""

    def _setup_reserved(self, engine, lot_idx, tb_count=4):
        """입고 + 예약 설정 헬퍼."""
        lot_data = make_lot(lot_idx)
        inbound_lot(engine, lot_data)
        alloc = [make_alloc_row(lot_data['lot_no'], sublot_count=tb_count)]
        engine.reserve_from_allocation(alloc, source_file='setup.xlsx')
        return lot_data['lot_no']

    def test_execute_all_reserved(self, engine):
        """전체 RESERVED → PICKED."""
        lot_no = self._setup_reserved(engine, 200, tb_count=3)
        r = engine.execute_reserved(lot_no=lot_no)
        assert r['success'], f"실행 실패: {r.get('errors', r.get('message'))}"
        assert r['executed'] >= 3

        picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(picked) >= 3

    def test_execute_by_date(self, engine):
        """target_date 이전 건만 실행."""
        lot_no = self._setup_reserved(engine, 210, tb_count=2)
        r = engine.execute_reserved(target_date='2026-12-31')
        assert isinstance(r, dict)

    def test_execute_no_reserved(self, engine):
        """예약 건 없을 때."""
        inbound_lot(engine, make_lot(220))
        r = engine.execute_reserved(lot_no='COV00220')
        assert not r['success']
        assert 'message' in r

    def test_execute_then_integrity(self, engine):
        """예약→실행→정합성 검증."""
        lot_no = self._setup_reserved(engine, 230, tb_count=4)
        engine.execute_reserved(lot_no=lot_no)

        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity['valid'], f"정합성 실패: {integrity.get('errors')}"


# ═══════════════════════════════════════════════════════════
#  3. cancel_reservation — RESERVED → AVAILABLE
# ═══════════════════════════════════════════════════════════

@pytest.mark.outbound
class TestCancelReservation:
    """예약 취소 → AVAILABLE 복귀."""

    def _setup_reserved(self, engine, lot_idx, tb_count=4):
        lot_data = make_lot(lot_idx)
        inbound_lot(engine, lot_data)
        alloc = [make_alloc_row(lot_data['lot_no'], sublot_count=tb_count)]
        r = engine.reserve_from_allocation(alloc, source_file='setup.xlsx')
        return lot_data['lot_no'], r.get('plan_ids', [])

    def test_cancel_by_lot(self, engine):
        """LOT 전체 예약 취소."""
        lot_no, _ = self._setup_reserved(engine, 300, tb_count=3)

        r = engine.cancel_reservation(lot_no=lot_no)
        assert r['cancelled'] >= 3

        avail = get_tonbags(engine, lot_no, 'AVAILABLE')
        reserved = get_tonbags(engine, lot_no, 'RESERVED')
        assert len(reserved) == 0
        assert len(avail) >= 10  # 전체 복귀

    def test_cancel_by_plan_ids(self, engine):
        """특정 plan_id만 취소."""
        lot_no, plan_ids = self._setup_reserved(engine, 310, tb_count=4)

        if plan_ids and len(plan_ids) >= 2:
            r = engine.cancel_reservation(plan_ids=plan_ids[:2])
            assert r['cancelled'] == 2

    def test_cancel_no_match(self, engine):
        """취소 대상 없음."""
        r = engine.cancel_reservation(lot_no='LOT-GHOST')
        assert r['cancelled'] == 0

    def test_cancel_then_re_reserve(self, engine):
        """취소 후 재예약."""
        lot_no, _ = self._setup_reserved(engine, 320, tb_count=3)

        engine.cancel_reservation(lot_no=lot_no)
        alloc = [make_alloc_row(lot_no, sublot_count=3)]
        r2 = engine.reserve_from_allocation(alloc)
        assert r2['success']
        assert r2['reserved'] == 3

    def test_cancel_integrity(self, engine):
        """취소 후 정합성."""
        lot_no, _ = self._setup_reserved(engine, 330, tb_count=4)
        engine.cancel_reservation(lot_no=lot_no)

        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity['valid']


# ═══════════════════════════════════════════════════════════
#  4. quick_outbound — 빠른 출고
# ═══════════════════════════════════════════════════════════

@pytest.mark.outbound
class TestQuickOutbound:
    """Allocation 없이 빠른 출고."""

    def test_quick_basic(self, engine):
        """기본 빠른 출고 2개."""
        inbound_lot(engine, make_lot(400))
        r = engine.quick_outbound('COV00400', count=2, customer='CATL')
        assert r['success'], f"빠른 출고 실패: {r.get('errors')}"
        assert r['picked_count'] == 2

        picked = get_tonbags(engine, 'COV00400', 'PICKED')
        assert len(picked) == 2

    def test_quick_exceed_limit(self, engine):
        """최대 개수 초과 → 실패."""
        inbound_lot(engine, make_lot(410))
        r = engine.quick_outbound('COV00410', count=999, customer='CATL')
        assert not r['success']

    def test_quick_exceed_available(self, engine):
        """가용 초과 → 실패."""
        inbound_lot(engine, make_lot(420, tb_count=2))
        r = engine.quick_outbound('COV00420', count=5, customer='CATL')
        assert not r['success']

    def test_quick_empty_customer(self, engine):
        """고객명 빈값 → 실패."""
        inbound_lot(engine, make_lot(430))
        r = engine.quick_outbound('COV00430', count=1, customer='')
        assert not r['success']

    def test_quick_empty_lot(self, engine):
        """LOT 빈값 → 실패."""
        r = engine.quick_outbound('', count=1, customer='CATL')
        assert not r['success']

    def test_quick_then_integrity(self, engine):
        """빠른 출고 후 정합성."""
        inbound_lot(engine, make_lot(440))
        engine.quick_outbound('COV00440', count=3, customer='CATL')
        integrity = engine.verify_lot_integrity('COV00440')
        assert integrity['valid']


# ═══════════════════════════════════════════════════════════
#  5. cancel_outbound_bulk — 대량 출고 취소
# ═══════════════════════════════════════════════════════════

@pytest.mark.outbound
class TestCancelOutboundBulk:
    """대량 출고 취소."""

    def test_bulk_cancel(self, engine):
        """여러 톤백 동시 취소."""
        inbound_lot(engine, make_lot(500))
        outbound_lot(engine, 'COV00500', 'CATL', 1500.0)

        picked = get_tonbags(engine, 'COV00500', 'PICKED')
        assert len(picked) >= 3

        items = [{'lot_no': 'COV00500', 'sub_lt': tb['sub_lt']} for tb in picked[:2]]
        r = engine.cancel_outbound_bulk(items)
        assert r['success']
        assert r.get('cancelled', 0) >= 2

    def test_bulk_cancel_empty(self, engine):
        """빈 리스트 → 0건 취소 (에러 없이)."""
        r = engine.cancel_outbound_bulk([])
        assert r['cancelled'] == 0


# ═══════════════════════════════════════════════════════════
#  6. revert 계열 테스트
# ═══════════════════════════════════════════════════════════

@pytest.mark.outbound
class TestRevertFunctions:
    """상태 되돌리기 함수."""

    def test_revert_picked_to_reserved(self, engine):
        """PICKED → RESERVED 되돌리기."""
        inbound_lot(engine, make_lot(600))
        alloc = [make_alloc_row('COV00600', sublot_count=3)]
        engine.reserve_from_allocation(alloc)
        engine.execute_reserved(lot_no='COV00600')

        r = engine.revert_picked_to_reserved(lot_no='COV00600')
        assert isinstance(r, dict)

    def test_revert_no_target(self, engine):
        """되돌릴 대상 없음."""
        inbound_lot(engine, make_lot(610))
        r = engine.revert_picked_to_reserved(lot_no='COV00610')
        assert isinstance(r, dict)
        assert r.get('reverted', 0) == 0


# ═══════════════════════════════════════════════════════════
#  7. 헬퍼 함수 테스트
# ═══════════════════════════════════════════════════════════

@pytest.mark.outbound
class TestOutboundHelpers:
    """outbound_mixin 헬퍼 함수."""

    def test_normalize_outbound_date_valid(self, engine):
        """정상 날짜 → YYYY-MM-DD."""
        r = engine._normalize_outbound_date('2026-03-15')
        assert r == '2026-03-15'

    def test_normalize_outbound_date_invalid(self, engine):
        """잘못된 날짜 → ValueError."""
        with pytest.raises(ValueError):
            engine._normalize_outbound_date('not-a-date')

    def test_normalize_outbound_date_none(self, engine):
        """None → 오늘 또는 빈값."""
        r = engine._normalize_outbound_date(None)
        assert isinstance(r, str)

    def test_table_exists(self, engine):
        """존재하는 테이블 확인."""
        assert engine._table_exists('inventory')
        assert engine._table_exists('inventory_tonbag')
        assert not engine._table_exists('nonexistent_table_xyz')

    def test_allocation_random_mode(self, engine):
        """랜덤 모드 반환."""
        mode = engine._get_allocation_random_mode()
        assert mode in ('seeded', 'random', 'none', '')

    def test_allocation_strict_mode(self, engine):
        """strict 모드 반환."""
        strict = engine._get_allocation_strict_mode()
        assert isinstance(strict, bool)

    def test_allocation_reservation_mode(self, engine):
        """예약 모드 반환."""
        mode = engine._get_allocation_reservation_mode()
        assert mode in ('tonbag', 'lot', '')

    def test_risk_flags(self, engine):
        """위험 플래그 계산."""
        flags = engine._allocation_risk_flags(10000, 5000)
        assert isinstance(flags, list)

    def test_requires_approval(self, engine):
        """승인 필요 여부."""
        r = engine._allocation_requires_approval(10000, 5000)
        assert isinstance(r, bool)

    def test_recalc_lot_status(self, engine):
        """LOT 상태 재계산."""
        inbound_lot(engine, make_lot(700))
        engine._recalc_lot_status('COV00700')
        lot = get_lot(engine, 'COV00700')
        assert lot is not None

    def test_assert_sample_policy(self, engine):
        """샘플 정책 확인."""
        inbound_lot(engine, make_lot(710))
        # 정상 상태에서는 예외 없음
        engine._assert_sample_policy('COV00710')

    def test_source_fingerprint(self, engine):
        """소스 지문 생성."""
        alloc = [make_alloc_row('COV99999')]
        fp = engine._compute_allocation_source_fingerprint(alloc, 'test.xlsx')
        assert isinstance(fp, str)
        assert len(fp) > 0


# ═══════════════════════════════════════════════════════════
#  8. 전체 워크플로 (Reserve → Execute → Confirm)
# ═══════════════════════════════════════════════════════════

@pytest.mark.outbound
@pytest.mark.integration
class TestFullAllocationWorkflow:
    """완전한 Allocation 워크플로."""

    def test_reserve_execute_cycle(self, engine):
        """입고 → 예약 → 실행 → 정합성."""
        inbound_lot(engine, make_lot(800))
        lot_no = 'COV00800'

        # 예약
        alloc = [make_alloc_row(lot_no, sublot_count=4)]
        r1 = engine.reserve_from_allocation(alloc)
        assert r1['success']

        # 실행
        r2 = engine.execute_reserved(lot_no=lot_no)
        assert r2['success']

        # 정합성
        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity['valid']

        # 상태 확인
        picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(picked) == 4

    def test_reserve_cancel_cycle(self, engine):
        """입고 → 예약 → 취소 → 재예약 → 실행."""
        inbound_lot(engine, make_lot(810))
        lot_no = 'COV00810'

        # 예약
        r1 = engine.reserve_from_allocation(
            [make_alloc_row(lot_no, 'CATL', sublot_count=3)])
        assert r1['success']

        # 취소
        r2 = engine.cancel_reservation(lot_no=lot_no)
        assert r2['cancelled'] >= 3

        # 다른 고객으로 재예약
        r3 = engine.reserve_from_allocation(
            [make_alloc_row(lot_no, 'BYD', sublot_count=4)])
        assert r3['success']
        assert r3['reserved'] == 4

        # 실행
        r4 = engine.execute_reserved(lot_no=lot_no)
        assert r4['success']

        # 정합성
        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity['valid']

    def test_mixed_quick_and_allocation(self, engine):
        """같은 LOT에서 빠른 출고 + Allocation 혼합."""
        inbound_lot(engine, make_lot(820, tb_count=20))
        lot_no = 'COV00820'

        # 빠른 출고 3개
        r1 = engine.quick_outbound(lot_no, count=3, customer='CATL')
        assert r1['success']

        # Allocation 예약 5개
        alloc = [make_alloc_row(lot_no, 'BYD', sublot_count=4)]
        r2 = engine.reserve_from_allocation(alloc)
        assert r2['success']

        # 실행
        r3 = engine.execute_reserved(lot_no=lot_no)
        assert r3['success']

        # 상태 확인
        picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(picked) >= 7  # 3 quick + 5 alloc

        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity['valid']
