# -*- coding: utf-8 -*-
"""
SQM v6.2.7 — PICKED → SOLD 2단계 워크플로 테스트
====================================================
S4-1 엔진 수정 이후 stop_at_picked=True의 정상 동작을 검증.

실행: python -m pytest tests/test_picked_to_sold_flow.py -v
"""

import os
import sys
import pytest
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.conftest import inbound_lot, outbound_lot, get_lot, get_tonbags

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 1. stop_at_picked=True 기본 동작
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestStopAtPickedBasic:
    """stop_at_picked=True: 톤백 PICKED + inventory 무게 갱신."""

    def test_picked_updates_weights(self, engine, lot_500kg):
        """PICKED 후 current_weight↓, picked_weight↑ 확인."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # stop_at_picked=True → 1000kg (2톤백)
        r = outbound_lot(engine, lot_no, 'CATL', 1000.0, stop_at_picked=True)
        assert r['success'], f"실패: {r.get('errors')}"

        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 4001.0  # 5001 - 1000
        assert lot_row['picked_weight'] == 1000.0

        # 톤백 상태 확인
        picked = get_tonbags(engine, lot_no, 'PICKED')
        available = get_tonbags(engine, lot_no, 'AVAILABLE')
        assert len(picked) == 2
        assert len(available) == 8

    def test_picked_integrity(self, engine, lot_500kg):
        """PICKED 후 정합성 유지 확인."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        outbound_lot(engine, lot_no, 'BYD', 500.0, stop_at_picked=True)

        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity['valid'], f"정합성 실패: {integrity.get('errors')}"

    def test_picked_then_more_picked(self, engine, lot_500kg):
        """연속 PICKED (서로 다른 고객)."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 1차: CATL 1500kg
        r1 = outbound_lot(engine, lot_no, 'CATL', 1500.0, stop_at_picked=True)
        assert r1['success']

        # 2차: BYD 2000kg
        r2 = outbound_lot(engine, lot_no, 'BYD', 2000.0, stop_at_picked=True)
        assert r2['success']

        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 1501.0  # 5001 - 1500 - 2000
        assert lot_row['picked_weight'] == 3500.0

        picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(picked) == 7  # 3 + 4 = 7톤백


# ═══════════════════════════════════════════
# 2. PICKED → cancel (역전이)
# ═══════════════════════════════════════════

@pytest.mark.outbound
@pytest.mark.rollback
class TestPickedThenCancel:
    """stop_at_picked 후 취소 → AVAILABLE 복귀."""

    def test_cancel_after_picked(self, engine, lot_500kg):
        """PICKED 1건 취소 → 무게 복구."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        outbound_lot(engine, lot_no, 'CATL', 500.0, stop_at_picked=True)
        
        picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(picked) == 1

        # 취소
        cr = engine.cancel_outbound_tonbag(lot_no, picked[0]['sub_lt'])
        assert cr['success'], f"취소 실패: {cr.get('errors')}"

        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 5001.0  # 원상 복구
        assert lot_row['picked_weight'] == 0.0

        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity['valid']

    def test_cancel_partial_picked(self, engine, lot_500kg):
        """3톤백 PICKED 중 1건 취소 → 2건만 PICKED."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        outbound_lot(engine, lot_no, 'CATL', 1500.0, stop_at_picked=True)
        
        picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(picked) == 3

        # 1건만 취소
        engine.cancel_outbound_tonbag(lot_no, picked[0]['sub_lt'])

        remaining_picked = get_tonbags(engine, lot_no, 'PICKED')
        assert len(remaining_picked) == 2

        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 4001.0  # 5001 - 1000
        assert lot_row['picked_weight'] == 1000.0


# ═══════════════════════════════════════════
# 3. 혼합 플로우 (일반 출고 + PICKED)
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestMixedOutboundFlow:
    """일반 출고와 stop_at_picked 혼합."""

    def test_normal_then_picked(self, engine, lot_500kg):
        """일반 출고 2000kg → PICKED 1500kg → 나머지 확인."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 일반 출고 2000kg
        r1 = outbound_lot(engine, lot_no, 'CATL', 2000.0)
        assert r1['success']

        # stop_at_picked 1500kg
        r2 = outbound_lot(engine, lot_no, 'BYD', 1500.0, stop_at_picked=True)
        assert r2['success']

        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 1501.0  # 5001 - 2000 - 1500
        # picked_weight: 일반 2000 + PICKED 1500 = 3500
        assert lot_row['picked_weight'] == 3500.0

    def test_picked_overflow_rejected(self, engine, lot_500kg):
        """PICKED 시 가용 재고 초과 → 실패."""
        inbound_lot(engine, lot_500kg)
        lot_no = lot_500kg['lot_no']

        # 일반 출고 4500kg (9톤백)
        outbound_lot(engine, lot_no, 'CATL', 4500.0)

        # 잔여 501kg (1톤백 + 샘플) → 1000kg PICKED 불가
        r = outbound_lot(engine, lot_no, 'BYD', 1000.0, stop_at_picked=True)
        assert not r['success'], "가용 초과 PICKED가 성공하면 안 됨"


# ═══════════════════════════════════════════
# 4. 1000kg 톤백에서 stop_at_picked
# ═══════════════════════════════════════════

@pytest.mark.outbound
class TestStopAtPicked1000kg:
    """1000kg 톤백 LOT에서 stop_at_picked."""

    def test_1000kg_picked(self, engine, lot_1000kg):
        """1000kg x 5 LOT → 2000kg PICKED."""
        inbound_lot(engine, lot_1000kg)
        lot_no = lot_1000kg['lot_no']

        r = outbound_lot(engine, lot_no, 'Tesla', 2000.0, stop_at_picked=True)
        assert r['success']

        lot_row = get_lot(engine, lot_no)
        assert lot_row['current_weight'] == 3001.0  # 5001 - 2000
        assert lot_row['picked_weight'] == 2000.0

        integrity = engine.verify_lot_integrity(lot_no)
        assert integrity['valid']
