"""
SQM v6.2.7 — 잘못된 데이터 방어 테스트 (Bad Data Test)
========================================================
비정상/악의적/엣지케이스 데이터 입력 시 엔진 방어력 검증.

영역:
  1. 입고 (Inbound)  — 빈값, 음수, 초대형, 특수문자, SQL 인젝션, 중복
  2. 출고 (Outbound)  — 0kg, 음수, 미존재 LOT, 소수점, 초과, 문자열 무게
  3. 반품 (Return)    — 빈 데이터, AVAILABLE 상태 반품, 미존재 톤백
  4. 정합성 (Integrity) — 수동 DB 조작 후 검증, 톤백/inventory 불일치

실행: python -m pytest tests/test_bad_data_defense.py -v
"""

import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.conftest import get_lot, get_tonbags, inbound_lot, outbound_lot

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  1. 입고 (Inbound) — 잘못된 데이터 방어
# ═══════════════════════════════════════════════════════════

@pytest.mark.inbound
class TestBadInboundData:
    """비정상 입고 데이터 → 모두 실패해야 함."""

    # --- 빈값/누락 ---

    def test_empty_dict(self, engine):
        """빈 dict 입고 → 실패."""
        r = engine.process_inbound({})
        assert not r['success']
        assert len(r['errors']) > 0

    def test_none_input(self, engine):
        """None 입고 → 실패 (크래시 없이)."""
        try:
            r = engine.process_inbound(None)
            assert not r['success']
        except (TypeError, AttributeError):
            pass  # None 처리 불가도 방어 OK

    def test_no_lot_no(self, engine):
        """lot_no 없이 입고 → 실패."""
        r = engine.process_inbound({
            'product': 'LITHIUM CARBONATE',
            'mxbg_pallet': 10,
            'net_weight': 5001.0,
        })
        assert not r['success']
        assert any('LOT' in e or 'lot' in e for e in r['errors'])

    def test_empty_lot_no(self, engine):
        """lot_no 빈 문자열 → 실패."""
        r = engine.process_inbound({
            'lot_no': '',
            'product': 'TEST',
            'mxbg_pallet': 5,
            'net_weight': 2501.0,
        })
        assert not r['success']

    def test_whitespace_lot_no(self, engine):
        """lot_no 공백만 → 실패."""
        r = engine.process_inbound({
            'lot_no': '   ',
            'product': 'TEST',
            'mxbg_pallet': 5,
            'net_weight': 2501.0,
        })
        assert not r['success']

    # --- 잘못된 숫자 ---

    def test_zero_weight(self, engine):
        """net_weight 0 → 실패."""
        r = engine.process_inbound({
            'lot_no': 'BAD-ZERO-WT',
            'product': 'TEST',
            'mxbg_pallet': 5,
            'net_weight': 0,
        })
        assert not r['success']

    def test_negative_weight(self, engine):
        """net_weight 음수 → 실패."""
        r = engine.process_inbound({
            'lot_no': 'BAD-NEG-WT',
            'product': 'TEST',
            'mxbg_pallet': 5,
            'net_weight': -5000.0,
        })
        assert not r['success']

    def test_string_weight(self, engine):
        """net_weight 문자열 → 실패 또는 0 처리."""
        r = engine.process_inbound({
            'lot_no': 'BAD-STR-WT',
            'product': 'TEST',
            'mxbg_pallet': 5,
            'net_weight': 'abc',
        })
        assert not r['success']

    def test_extremely_large_weight(self, engine):
        """비현실적 무게 (100만 톤) → 성공은 하되 경고 또는 거부."""
        r = engine.process_inbound({
            'lot_no': 'BAD-HUGE-WT',
            'product': 'TEST',
            'mxbg_pallet': 1,
            'net_weight': 1_000_000_000.0,  # 100만톤
        })
        # 시스템이 받아들이든 거부하든 크래시는 없어야 함
        assert isinstance(r, dict)

    # --- 중복 입고 ---

    def test_duplicate_lot(self, engine, lot_500kg):
        """동일 LOT 2번 입고 → 2번째 실패."""
        r1 = engine.process_inbound(lot_500kg)
        assert r1['success']

        r2 = engine.process_inbound(lot_500kg)
        assert not r2['success']
        assert any('존재' in e or 'exist' in e.lower() or '중복' in e
                   for e in r2['errors'])

    # --- 특수문자 / SQL 인젝션 ---

    def test_special_chars_lot_no(self, engine):
        """LOT 번호에 특수문자 → 크래시 없이 처리."""
        for bad_lot in ["LOT'DROP", 'LOT"TABLE', 'LOT;DELETE', 'LOT<script>']:
            r = engine.process_inbound({
                'lot_no': bad_lot,
                'product': 'TEST',
                'mxbg_pallet': 2,
                'net_weight': 1001.0,
            })
            # 성공/실패 무관, 크래시 없어야 함
            assert isinstance(r, dict), f"특수문자 LOT 크래시: {bad_lot}"

    def test_sql_injection_lot_no(self, engine):
        """SQL 인젝션 시도 → 방어."""
        r = engine.process_inbound({
            'lot_no': "'; DROP TABLE inventory; --",
            'product': 'TEST',
            'mxbg_pallet': 2,
            'net_weight': 1001.0,
        })
        assert isinstance(r, dict)
        # inventory 테이블이 살아있어야 함
        row = engine.db.fetchone("SELECT COUNT(*) as cnt FROM inventory")
        assert row is not None, "SQL 인젝션으로 테이블 파괴됨!"

    def test_unicode_lot_no(self, engine):
        """한글/이모지 LOT 번호 → 크래시 없이."""
        r = engine.process_inbound({
            'lot_no': '한글LOT-테스트-🎉',
            'product': '리튬카보네이트',
            'mxbg_pallet': 3,
            'net_weight': 1501.0,
        })
        assert isinstance(r, dict)

    # --- 극단적 LOT 번호 ---

    def test_very_long_lot_no(self, engine):
        """100자 LOT 번호 → 거부 (30자 제한)."""
        r = engine.process_inbound({
            'lot_no': 'X' * 100,
            'product': 'TEST',
            'mxbg_pallet': 2,
            'net_weight': 1001.0,
        })
        assert not r['success']


# ═══════════════════════════════════════════════════════════
#  2. 출고 (Outbound) — 잘못된 데이터 방어
# ═══════════════════════════════════════════════════════════

@pytest.mark.outbound
class TestBadOutboundData:
    """비정상 출고 데이터 → 모두 실패해야 함."""

    def test_empty_allocation(self, engine):
        """빈 allocation → 실패."""
        r = engine.process_outbound({})
        assert not r['success']

    def test_none_allocation(self, engine):
        """None allocation → 실패."""
        try:
            r = engine.process_outbound(None)
            assert not r['success']
        except (TypeError, AttributeError):
            pass  # 방어 OK

    def test_empty_list(self, engine):
        """빈 리스트 → 실패."""
        r = engine.process_outbound([])
        assert not r['success']

    def test_zero_weight(self, engine, lot_500kg):
        """0kg 출고 → 실패."""
        inbound_lot(engine, lot_500kg)
        r = outbound_lot(engine, lot_500kg['lot_no'], 'CATL', 0.0)
        assert not r['success']

    def test_negative_weight(self, engine, lot_500kg):
        """음수 출고 → 실패."""
        inbound_lot(engine, lot_500kg)
        r = outbound_lot(engine, lot_500kg['lot_no'], 'CATL', -500.0)
        assert not r['success']

    def test_string_weight(self, engine, lot_500kg):
        """문자열 무게 → 실패."""
        inbound_lot(engine, lot_500kg)
        alloc = {
            'lot_no': lot_500kg['lot_no'],
            'customer': 'CATL',
            'weight_kg': 'abc',
        }
        r = engine.process_outbound(alloc, source='TEST')
        assert not r['success']

    def test_nonexistent_lot(self, engine):
        """미존재 LOT → 실패."""
        r = outbound_lot(engine, 'LOT-GHOST-999', 'CATL', 500.0)
        assert not r['success']

    def test_exceed_available(self, engine, lot_500kg):
        """가용 초과 (5001kg LOT에서 99999kg) → 실패."""
        inbound_lot(engine, lot_500kg)
        r = outbound_lot(engine, lot_500kg['lot_no'], 'CATL', 99999.0)
        assert not r['success']

    def test_fractional_weight(self, engine, lot_500kg):
        """소수점 무게 (123.456kg) → 크래시 없이."""
        inbound_lot(engine, lot_500kg)
        r = outbound_lot(engine, lot_500kg['lot_no'], 'CATL', 123.456)
        # 톤백 단위에 안 맞으면 실패 가능, 크래시만 없으면 OK
        assert isinstance(r, dict)

    def test_empty_customer(self, engine, lot_500kg):
        """고객명 빈 문자열 → 크래시 없이."""
        inbound_lot(engine, lot_500kg)
        r = outbound_lot(engine, lot_500kg['lot_no'], '', 500.0)
        assert isinstance(r, dict)

    def test_sql_injection_customer(self, engine, lot_500kg):
        """고객명 SQL 인젝션 → 방어."""
        inbound_lot(engine, lot_500kg)
        r = outbound_lot(engine, lot_500kg['lot_no'],
                        "'; DROP TABLE outbound; --", 500.0)
        assert isinstance(r, dict)
        # outbound 테이블 생존 확인
        row = engine.db.fetchone("SELECT COUNT(*) as cnt FROM outbound")
        assert row is not None


# ═══════════════════════════════════════════════════════════
#  3. 반품 (Return) — 잘못된 데이터 방어
# ═══════════════════════════════════════════════════════════

@pytest.mark.rollback
class TestBadReturnData:
    """비정상 반품 데이터 → 실패 또는 skip."""

    def test_empty_return(self, engine):
        """빈 리스트 반품 → 실패."""
        r = engine.process_return([])
        assert not r['success']

    def test_none_return(self, engine):
        """None 반품 → 실패."""
        try:
            r = engine.process_return(None)
            assert not r['success']
        except (TypeError, AttributeError):
            pass

    def test_missing_lot_no(self, engine):
        """lot_no 없는 반품 → skip + 에러."""
        r = engine.process_return([{'sub_lt': 1, 'reason': 'test'}])
        assert r['skipped'] >= 1

    def test_missing_sub_lt(self, engine):
        """sub_lt 없는 반품 → skip."""
        r = engine.process_return([{'lot_no': 'LOT-X', 'reason': 'test'}])
        assert r['skipped'] >= 1

    def test_nonexistent_tonbag(self, engine):
        """미존재 톤백 반품 → skip."""
        r = engine.process_return([{
            'lot_no': 'LOT-GHOST-999',
            'sub_lt': 1,
            'reason': 'test'
        }])
        assert r['skipped'] >= 1

    def test_return_available_tonbag(self, engine, lot_500kg):
        """AVAILABLE 상태 톤백 반품 시도 → 거부."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 출고 안 한 상태 → 톤백은 AVAILABLE
        r = engine.process_return([{
            'lot_no': lot_no,
            'sub_lt': 1,
            'reason': '잘못된 반품'
        }])
        # AVAILABLE 상태는 반품 대상 아님 → skip
        assert r['skipped'] >= 1 or not r['success']

    def test_return_same_tonbag_twice(self, engine, lot_500kg):
        """동일 톤백 2회 반품 시도 → 2번째 거부."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 출고
        outbound_lot(engine, lot_no, 'CATL', 500.0)
        picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(picked) >= 1
        sub_lt = picked[0]['sub_lt']

        # 1차 반품 → 성공
        r1 = engine.process_return([{
            'lot_no': lot_no, 'sub_lt': sub_lt, 'reason': '1차 반품'
        }])
        assert r1['returned'] >= 1

        # 2차 반품 (이미 AVAILABLE) → 거부
        r2 = engine.process_return([{
            'lot_no': lot_no, 'sub_lt': sub_lt, 'reason': '2차 반품'
        }])
        assert r2['skipped'] >= 1 or r2['returned'] == 0


# ═══════════════════════════════════════════════════════════
#  4. 출고 취소 (Cancel) — 잘못된 데이터
# ═══════════════════════════════════════════════════════════

@pytest.mark.rollback
class TestBadCancelData:
    """비정상 출고 취소 데이터."""

    def test_cancel_nonexistent(self, engine):
        """미존재 톤백 취소 → 실패."""
        r = engine.cancel_outbound_tonbag('LOT-GHOST', 999)
        assert not r['success']

    def test_cancel_available_tonbag(self, engine, lot_500kg):
        """AVAILABLE 톤백 취소 (PICKED 아님) → 거부."""
        inbound_lot(engine, lot_500kg)
        r = engine.cancel_outbound_tonbag(lot_500kg['lot_no'], 1)
        assert not r['success']

    def test_cancel_negative_sub_lt(self, engine, lot_500kg):
        """음수 sub_lt → 실패."""
        inbound_lot(engine, lot_500kg)
        r = engine.cancel_outbound_tonbag(lot_500kg['lot_no'], -1)
        assert not r['success']


# ═══════════════════════════════════════════════════════════
#  5. 정합성 (Integrity) — DB 조작 후 감지
# ═══════════════════════════════════════════════════════════

@pytest.mark.integration
class TestIntegrityAfterCorruption:
    """DB를 직접 조작 → verify_lot_integrity가 감지하는지 확인."""

    def test_detect_weight_mismatch(self, engine, lot_500kg):
        """inventory.current_weight를 수동 변경 → 정합성 실패 감지."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 정상 상태 확인
        i1 = engine.verify_lot_integrity(lot_no)
        assert i1['valid']

        # DB 직접 조작: current_weight를 비정상 값으로
        engine.db.execute(
            "UPDATE inventory SET current_weight = 9999 WHERE lot_no = ?",
            (lot_no,))

        # 정합성 검증 → 실패 감지
        i2 = engine.verify_lot_integrity(lot_no)
        assert not i2['valid'], "무게 조작을 감지하지 못함!"
        assert len(i2['errors']) > 0

    def test_detect_picked_weight_mismatch(self, engine, lot_500kg):
        """inventory.picked_weight 조작 → 감지."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        outbound_lot(engine, lot_no, 'CATL', 1000.0)

        # picked_weight를 0으로 조작
        engine.db.execute(
            "UPDATE inventory SET picked_weight = 0 WHERE lot_no = ?",
            (lot_no,))

        i = engine.verify_lot_integrity(lot_no)
        assert not i['valid'], "picked_weight 조작을 감지하지 못함!"

    def test_detect_tonbag_status_mismatch(self, engine, lot_500kg):
        """톤백 status를 수동 변경 → 불일치 감지."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 톤백 하나를 임의로 PICKED 변경 (inventory는 그대로)
        engine.db.execute(
            "UPDATE inventory_tonbag SET status = 'PICKED' "
            "WHERE lot_no = ? AND sub_lt = 1 AND COALESCE(is_sample,0) = 0",
            (lot_no,))

        i = engine.verify_lot_integrity(lot_no)
        assert not i['valid'], "톤백 status 조작을 감지하지 못함!"

    def test_detect_missing_sample(self, engine, lot_500kg):
        """샘플 톤백 삭제 → 정합성 실패."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 샘플 톤백 삭제
        engine.db.execute(
            "DELETE FROM inventory_tonbag WHERE lot_no = ? AND is_sample = 1",
            (lot_no,))

        i = engine.verify_lot_integrity(lot_no)
        assert not i['valid'], "샘플 삭제를 감지하지 못함!"

    def test_integrity_nonexistent_lot(self, engine):
        """미존재 LOT 정합성 → 실패."""
        i = engine.verify_lot_integrity('LOT-NOT-HERE')
        assert not i['valid']


# ═══════════════════════════════════════════════════════════
#  6. 경계값 (Boundary) — 극단적 정상 데이터
# ═══════════════════════════════════════════════════════════

@pytest.mark.integration
class TestBoundaryValues:
    """정상이지만 극단적인 경계값."""

    def test_single_tonbag_lot(self, engine):
        """톤백 1개 LOT (최소 단위) → 성공."""
        r = engine.process_inbound({
            'lot_no': 'BOUND-1TB',
            'product': 'TEST',
            'mxbg_pallet': 1,
            'net_weight': 501.0,  # 500kg + 1kg 샘플
        })
        assert r['success'], f"1톤백 입고 실패: {r.get('errors')}"

    def test_many_tonbag_lot(self, engine):
        """톤백 50개 LOT (대용량) → 성공."""
        r = engine.process_inbound({
            'lot_no': 'BOUND-50TB',
            'product': 'TEST',
            'mxbg_pallet': 50,
            'net_weight': 25001.0,  # 500 x 50 + 1
        })
        assert r['success'], f"50톤백 입고 실패: {r.get('errors')}"

        tonbags = get_tonbags(engine, 'BOUND-50TB')
        assert len(tonbags) == 50

    def test_outbound_exact_one_tonbag(self, engine, lot_500kg):
        """정확히 1톤백(500kg) 출고."""
        inbound_lot(engine, lot_500kg)
        r = outbound_lot(engine, lot_500kg['lot_no'], 'CATL', 500.0)
        assert r['success']

        lot_row = get_lot(engine, lot_500kg['lot_no'])
        assert lot_row['current_weight'] == 4501.0

    def test_outbound_all_then_verify(self, engine, lot_500kg):
        """전량 출고 → 잔여 = 샘플 1kg만."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        r = outbound_lot(engine, lot_no, 'CATL', 5000.0)
        assert r['success']

        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 1.0  # 샘플만

        avail = get_tonbags(engine, lot_no, 'AVAILABLE')
        assert len(avail) == 0

        i = engine.verify_lot_integrity(lot_no)
        assert i['valid']


# ═══════════════════════════════════════════════════════════
#  7. 동시성/순서 (Sequence) — 비정상 순서 호출
# ═══════════════════════════════════════════════════════════

@pytest.mark.integration
class TestBadSequence:
    """비정상 호출 순서."""

    def test_outbound_before_inbound(self, engine):
        """입고 전에 출고 시도 → 실패."""
        r = outbound_lot(engine, 'LOT-NO-INBOUND', 'CATL', 500.0)
        assert not r['success']

    def test_return_before_outbound(self, engine, lot_500kg):
        """출고 전에 반품 시도 → 거부."""
        inbound_lot(engine, lot_500kg)
        r = engine.process_return([{
            'lot_no': lot_500kg['lot_no'],
            'sub_lt': 1,
            'reason': 'test'
        }])
        assert r['returned'] == 0

    def test_cancel_before_outbound(self, engine, lot_500kg):
        """출고 전에 취소 시도 → 실패."""
        inbound_lot(engine, lot_500kg)
        r = engine.cancel_outbound_tonbag(lot_500kg['lot_no'], 1)
        assert not r['success']

    def test_double_inbound_outbound_return_cycle(self, engine, lot_500kg):
        """입고→출고→반품→재출고 전체 사이클."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 출고 500kg
        r1 = outbound_lot(engine, lot_no, 'CATL', 500.0)
        assert r1['success']

        # 반품
        picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(picked) >= 1
        r2 = engine.process_return([{
            'lot_no': lot_no,
            'sub_lt': picked[0]['sub_lt'],
            'reason': '품질 불량'
        }])
        assert r2['returned'] >= 1

        # 재출고 (반품된 톤백 포함)
        r3 = outbound_lot(engine, lot_no, 'BYD', 500.0)
        assert r3['success']

        # 최종 정합성
        i = engine.verify_lot_integrity(lot_no)
        assert i['valid'], f"사이클 후 정합성 실패: {i.get('errors')}"
