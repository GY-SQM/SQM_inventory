"""
SQM v6.2.7 — 출고 상태전이 엣지케이스 테스트
================================================
기존 test_outbound_state_transition.py (13개)를 보완하는 엣지케이스.

신규 테스트:
  1. 동일 LOT 연속 출고 (부분 + 부분 + 잔여)
  2. 전량 출고 후 재출고 시도 → 거부
  3. 0kg / 음수 / 미존재 LOT 출고 시도 → 거부
  4. 다중 고객 동시 출고
  5. 출고 후 cancel_outbound_tonbag (역전이)
  6. 소량 LOT (2톤백) 전량 출고
  7. 1000kg 톤백 출고

실행: python -m pytest tests/test_outbound_edge_cases.py -v
"""

import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# conftest.py에서 engine, lot_500kg, lot_1000kg, lot_small 자동 로드
from tests.conftest import get_lot, get_tonbags, inbound_lot, outbound_lot

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Edge Case 1: 연속 부분 출고
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestSequentialPartialOutbound:
    """동일 LOT에서 여러 번 부분 출고."""

    def test_three_sequential_outbound(self, engine, lot_500kg):
        """500kg x 10 LOT → 1500kg + 1000kg + 2500kg = 5000kg 전량."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 1차: 1500kg (3톤백)
        r1 = outbound_lot(engine, lot_no, 'CATL', 1500.0)
        assert r1['success'], f"1차 실패: {r1.get('message')}"
        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 3501.0  # 5001 - 1500

        # 2차: 1000kg (2톤백)
        r2 = outbound_lot(engine, lot_no, 'BYD', 1000.0)
        assert r2['success'], f"2차 실패: {r2.get('message')}"
        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 2501.0  # 3501 - 1000

        # 3차: 나머지 전량 2500kg (5톤백)
        r3 = outbound_lot(engine, lot_no, 'Panasonic', 2500.0)
        assert r3['success'], f"3차 실패: {r3.get('message')}"
        lot_row = get_lot(engine, lot_no)
        # 샘플 1kg만 남음
        assert lot_row['current_weight'] == 1.0

        # 모든 톤백 PICKED (샘플 제외)
        avail_tonbags = get_tonbags(engine, lot_no, 'AVAILABLE')
        assert len(avail_tonbags) == 0

    def test_progressive_integrity(self, engine, lot_500kg):
        """부분 출고마다 정합성 유지 확인."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        for i, (customer, weight) in enumerate([
            ('CATL', 500.0), ('BYD', 500.0), ('Tesla', 500.0)
        ], 1):
            result = outbound_lot(engine, lot_no, customer, weight)
            assert result['success'], f"{i}차 출고 실패"

            # 정합성: verify_lot_integrity
            integrity = engine.verify_lot_integrity(lot_no)
            assert integrity.get('valid', False), (
                f"{i}차 후 정합성 실패: {integrity.get('issues')}"
            )


# ═══════════════════════════════════════════
# Edge Case 2: 전량 출고 후 재출고 시도
# ═══════════════════════════════════════════

@pytest.mark.outbound
@pytest.mark.rollback
class TestOverOutbound:
    """재고 초과 출고 시도 → 거부 확인."""

    def test_outbound_after_depleted(self, engine, lot_500kg):
        """전량 출고 후 추가 출고 → 실패."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 전량 출고 (5000kg = 10 x 500)
        r1 = outbound_lot(engine, lot_no, 'CATL', 5000.0)
        assert r1['success']

        # 추가 출고 시도 → 반드시 실패
        r2 = outbound_lot(engine, lot_no, 'BYD', 500.0)
        assert not r2['success'], "전량 출고 후 추가 출고가 성공하면 안 됨"

    def test_outbound_exceeding_available(self, engine, lot_500kg):
        """가용 재고 초과 출고 → 실패."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 가용 재고 5001kg보다 많이 출고 시도
        r = outbound_lot(engine, lot_no, 'CATL', 9999.0)
        assert not r['success'], "재고 초과 출고가 성공하면 안 됨"


# ═══════════════════════════════════════════
# Edge Case 3: 잘못된 입력값
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestInvalidOutboundInput:
    """비정상 입력값 방어."""

    def test_zero_weight_outbound(self, engine, lot_500kg):
        """0kg 출고 시도."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']
        r = outbound_lot(engine, lot_no, 'CATL', 0.0)
        assert not r['success'], "0kg 출고가 성공하면 안 됨"

    def test_negative_weight_outbound(self, engine, lot_500kg):
        """음수 출고 시도."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']
        r = outbound_lot(engine, lot_no, 'CATL', -500.0)
        assert not r['success'], "음수 출고가 성공하면 안 됨"

    def test_nonexistent_lot(self, engine):
        """존재하지 않는 LOT 출고 시도."""
        r = outbound_lot(engine, 'LOT-GHOST-999', 'CATL', 500.0)
        assert not r['success']


# ═══════════════════════════════════════════
# Edge Case 4: 다중 고객 동시 배분
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestMultiCustomerOutbound:
    """동일 LOT를 여러 고객에게 분배."""

    def test_three_customers_same_lot(self, engine, lot_500kg):
        """3개 고객에게 분배 → 총 출고 수량 정합성."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        customers = [('CATL', 1500.0), ('BYD', 2000.0), ('Tesla', 1500.0)]
        total_out = 0
        for customer, weight in customers:
            r = outbound_lot(engine, lot_no, customer, weight)
            assert r['success'], f"{customer} 출고 실패: {r.get('message')}"
            total_out += weight

        # 전량 5000kg 출고 확인
        assert total_out == 5000.0
        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 1.0  # 샘플만

        # PICKED 톤백 = 10개
        picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(picked) == 10


# ═══════════════════════════════════════════
# Edge Case 5: 출고 취소 (cancel_outbound_tonbag)
# ═══════════════════════════════════════════

@pytest.mark.outbound
@pytest.mark.rollback
class TestOutboundCancel:
    """출고 후 톤백 단건 취소."""

    def test_cancel_single_tonbag(self, engine, lot_500kg):
        """출고 후 1건 취소 → AVAILABLE 복귀."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 1000kg 출고 (2톤백)
        r = outbound_lot(engine, lot_no, 'CATL', 1000.0)
        assert r['success']

        picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(picked) >= 2

        # 첫 번째 PICKED 톤백 취소 (sub_lt = int)
        first_sub_lt = picked[0]['sub_lt']
        cr = engine.cancel_outbound_tonbag(lot_no, first_sub_lt)
        assert cr.get('success', False), f"취소 실패: {cr.get('message', cr.get('errors'))}"

        # 취소 후 current_weight 증가 확인
        lot_row = get_lot(engine, lot_no)
        # 원래 5001 - 1000 = 4001, 취소 후 +500 = 4501
        assert lot_row['current_weight'] == 4501.0

    def test_cancel_restores_integrity(self, engine, lot_500kg):
        """취소 후 정합성 유지."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        outbound_lot(engine, lot_no, 'CATL', 500.0)

        picked = get_tonbags(engine, lot_no, 'PICKED')
        if picked:
            engine.cancel_outbound_tonbag(lot_no, picked[0]['sub_lt'])

        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity.get('valid', False), f"취소 후 정합성 실패: {integrity.get('issues')}"


# ═══════════════════════════════════════════
# Edge Case 6: 소량 LOT (2톤백) 전량 출고
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestSmallLotFullOutbound:
    """톤백 2개뿐인 소량 LOT."""

    def test_small_lot_full_depletion(self, engine, lot_small):
        """1001kg LOT (500x2 + 1) → 전량 출고."""
        inbound_lot(engine, lot_small)
        lot_no = lot_small['lot_no']

        r = outbound_lot(engine, lot_no, 'CATL', 1000.0)
        assert r['success']

        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 1.0  # 샘플만 남음

        avail = get_tonbags(engine, lot_no, 'AVAILABLE')
        assert len(avail) == 0


# ═══════════════════════════════════════════
# Edge Case 7: 1000kg 톤백 출고
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestLargeTonbagOutbound:
    """1000kg 톤백 LOT 출고."""

    def test_1000kg_partial_outbound(self, engine, lot_1000kg):
        """1000kg x 5 LOT → 2000kg 출고."""
        inbound_lot(engine, lot_1000kg)
        lot_no = lot_1000kg['lot_no']

        r = outbound_lot(engine, lot_no, 'BYD', 2000.0)
        assert r['success']

        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 3001.0  # 5001 - 2000

        # 정합성 확인
        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity.get('valid', False)
