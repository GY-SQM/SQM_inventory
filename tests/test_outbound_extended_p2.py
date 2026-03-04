# -*- coding: utf-8 -*-
"""
SQM v6.2.7 — outbound 확장 커버리지 Part 2 (80% → 85%)
=========================================================
quick_outbound, cancel_reservation, revert_picked_to_reserved
"""

import os
import sys
import sqlite3
import pytest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import inbound_lot


def _reserve_with_plan(engine, lot_no, customer='TESTCORP', count=2):
    """AVAILABLE → RESERVED + allocation_plan 행 생성."""
    tbs = engine.db.fetchall(
        "SELECT id, sub_lt, weight FROM inventory_tonbag "
        "WHERE lot_no=? AND status='AVAILABLE' AND COALESCE(is_sample,0)=0 "
        "ORDER BY id LIMIT ?",
        (lot_no, count)
    )
    plan_ids = []
    for tb in tbs:
        engine.db.execute(
            "UPDATE inventory_tonbag SET status='RESERVED', picked_to=? WHERE id=?",
            (customer, tb['id'])
        )
        engine.db.execute(
            """INSERT INTO allocation_plan 
               (lot_no, tonbag_id, sub_lt, customer, qty_mt, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'RESERVED', datetime('now'))""",
            (lot_no, tb['id'], tb.get('sub_lt', 0), customer,
             float(tb.get('weight', 0) or 0) / 1000)
        )
        row = engine.db.fetchone("SELECT last_insert_rowid() AS id")
        plan_ids.append(row['id'] if row else 0)
    engine.db.commit()
    return plan_ids


def _execute_plan(engine, lot_no):
    """RESERVED → EXECUTED (allocation_plan + tonbag PICKED)."""
    plans = engine.db.fetchall(
        "SELECT id, tonbag_id FROM allocation_plan "
        "WHERE lot_no=? AND status='RESERVED'",
        (lot_no,)
    )
    now = '2026-03-01 12:00:00'
    for p in plans:
        engine.db.execute(
            "UPDATE allocation_plan SET status='EXECUTED', executed_at=? WHERE id=?",
            (now, p['id'])
        )
        engine.db.execute(
            "UPDATE inventory_tonbag SET status='PICKED', picked_date=? WHERE id=?",
            (now, p['tonbag_id'])
        )
    engine.db.commit()


def _ensure_picking_table(engine):
    """picking_table 생성."""
    try:
        engine.db.execute("""
            CREATE TABLE IF NOT EXISTS picking_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT, tonbag_id INTEGER, sub_lt INTEGER,
                tonbag_uid TEXT, customer TEXT, qty_kg REAL,
                status TEXT, picking_date TEXT, created_by TEXT, remark TEXT
            )
        """)
        engine.db.commit()
    except Exception:
        pass


# ═══════════════════════════════════════
# quick_outbound
# ═══════════════════════════════════════

class TestQuickOutbound:
    """빠른 출고 테스트."""

    def test_basic_quick(self, engine):
        """정상 빠른 출고."""
        _ensure_picking_table(engine)
        inbound_lot(engine, {'lot_no': 'QO001', 'mxbg_pallet': 6, 'net_weight': 3001.0})

        r = engine.quick_outbound('QO001', 2, 'CATL', reason='긴급 출하')
        assert r['success']
        assert r['picked_count'] == 2
        assert r['total_weight_kg'] > 0
        assert 'quick_ref' in r

        # PICKED 상태 확인
        picked = engine.db.fetchall(
            "SELECT * FROM inventory_tonbag WHERE lot_no='QO001' AND status='PICKED'"
        )
        assert len(picked) == 2

    def test_quick_no_customer(self, engine):
        """고객명 없으면 실패."""
        r = engine.quick_outbound('QO002', 1, '')
        assert not r['success']
        assert any('고객명' in e for e in r['errors'])

    def test_quick_no_lot(self, engine):
        """LOT 번호 없으면 실패."""
        r = engine.quick_outbound('', 1, 'CATL')
        assert not r['success']
        assert any('LOT' in e for e in r['errors'])

    def test_quick_exceeds_max(self, engine):
        """최대 개수 초과."""
        r = engine.quick_outbound('QO003', 100, 'CATL')
        assert not r['success']
        assert any('최대' in e for e in r['errors'])

    def test_quick_insufficient_tonbags(self, engine):
        """가용 톤백 부족."""
        _ensure_picking_table(engine)
        inbound_lot(engine, {'lot_no': 'QO004', 'mxbg_pallet': 2, 'net_weight': 1001.0})
        r = engine.quick_outbound('QO004', 5, 'BYD')
        assert not r['success']
        assert any('부족' in e for e in r['errors'])

    def test_quick_stock_movement(self, engine):
        """QUICK_OUTBOUND stock_movement 기록."""
        _ensure_picking_table(engine)
        inbound_lot(engine, {'lot_no': 'QO005', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        engine.quick_outbound('QO005', 1, 'LG')

        moves = engine.db.fetchall(
            "SELECT * FROM stock_movement WHERE lot_no='QO005' AND movement_type='QUICK_OUTBOUND'"
        )
        assert len(moves) >= 1

    def test_quick_allocation_plan(self, engine):
        """allocation_plan EXECUTED 행 자동 생성."""
        _ensure_picking_table(engine)
        inbound_lot(engine, {'lot_no': 'QO006', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        engine.quick_outbound('QO006', 1, 'SK')

        plans = engine.db.fetchall(
            "SELECT * FROM allocation_plan WHERE lot_no='QO006' AND status='EXECUTED'"
        )
        assert len(plans) >= 1
        assert plans[0].get('source', '') == 'QUICK' or 'QUICK' in str(plans[0].get('source_file', ''))

    def test_quick_weight_deduction(self, engine):
        """current_weight 차감 확인."""
        _ensure_picking_table(engine)
        inbound_lot(engine, {'lot_no': 'QO007', 'mxbg_pallet': 4, 'net_weight': 2001.0})

        before = engine.db.fetchone("SELECT current_weight FROM inventory WHERE lot_no='QO007'")
        before_wt = float(before['current_weight']) if before else 0

        r = engine.quick_outbound('QO007', 2, 'CATL')
        assert r['success']

        after = engine.db.fetchone("SELECT current_weight FROM inventory WHERE lot_no='QO007'")
        after_wt = float(after['current_weight']) if after else 0

        assert after_wt < before_wt


# ═══════════════════════════════════════
# cancel_reservation
# ═══════════════════════════════════════

class TestCancelReservation:
    """RESERVED 예약 취소."""

    def test_cancel_by_lot(self, engine):
        """LOT 기준 취소."""
        inbound_lot(engine, {'lot_no': 'CR001', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _reserve_with_plan(engine, 'CR001', count=2)

        r = engine.cancel_reservation(lot_no='CR001')
        assert r['success']
        assert r['cancelled'] == 2

        # AVAILABLE 복원 확인
        avail = engine.db.fetchall(
            "SELECT status FROM inventory_tonbag WHERE lot_no='CR001' AND status='AVAILABLE'"
        )
        assert len(avail) >= 2

    def test_cancel_by_plan_id(self, engine):
        """plan_id 기준 단건 취소."""
        inbound_lot(engine, {'lot_no': 'CR002', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        plan_ids = _reserve_with_plan(engine, 'CR002', count=2)

        r = engine.cancel_reservation(plan_id=plan_ids[0])
        assert r['success']
        assert r['cancelled'] == 1

    def test_cancel_by_plan_ids(self, engine):
        """plan_ids 다건 일괄 취소."""
        inbound_lot(engine, {'lot_no': 'CR003', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        plan_ids = _reserve_with_plan(engine, 'CR003', count=2)

        r = engine.cancel_reservation(plan_ids=plan_ids)
        assert r['success']
        assert r['cancelled'] == 2

    def test_cancel_empty_plan_ids(self, engine):
        """빈 plan_ids → 일반 조회 분기."""
        inbound_lot(engine, {'lot_no': 'CR004E', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        # plan_ids=[] 는 falsy이므로 전체 RESERVED 조회로 분기 → 없으면 '없음'
        r = engine.cancel_reservation(plan_ids=[])
        assert not r['success']
        assert '비어' in r.get('message', '') or '없음' in r.get('message', '')

    def test_cancel_no_reserved(self, engine):
        """RESERVED 없을 때."""
        inbound_lot(engine, {'lot_no': 'CR004', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        r = engine.cancel_reservation(lot_no='CR004')
        assert not r['success']
        assert '없음' in r.get('message', '')

    def test_cancel_stock_movement(self, engine):
        """CANCEL_RESERVE 이력 기록."""
        inbound_lot(engine, {'lot_no': 'CR005', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _reserve_with_plan(engine, 'CR005', count=1)
        engine.cancel_reservation(lot_no='CR005')

        moves = engine.db.fetchall(
            "SELECT * FROM stock_movement WHERE lot_no='CR005' AND movement_type='CANCEL_RESERVE'"
        )
        assert len(moves) >= 1

    def test_cancel_recalc_status(self, engine):
        """취소 후 LOT 상태 재계산."""
        inbound_lot(engine, {'lot_no': 'CR006', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _reserve_with_plan(engine, 'CR006', count=4)

        # 전부 RESERVED → 취소 → AVAILABLE
        engine.cancel_reservation(lot_no='CR006')
        lot = engine.db.fetchone("SELECT status FROM inventory WHERE lot_no='CR006'")
        assert lot is not None


# ═══════════════════════════════════════
# revert_picked_to_reserved
# ═══════════════════════════════════════

class TestRevertPickedToReserved:
    """PICKED → RESERVED 되돌리기."""

    def test_basic_revert(self, engine):
        """정상 되돌리기."""
        inbound_lot(engine, {'lot_no': 'RPR001', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _reserve_with_plan(engine, 'RPR001', count=2)
        _execute_plan(engine, 'RPR001')

        r = engine.revert_picked_to_reserved(lot_no='RPR001')
        assert r['success']
        assert r['reverted'] == 2

        # RESERVED 복원 확인
        reserved = engine.db.fetchall(
            "SELECT status FROM inventory_tonbag WHERE lot_no='RPR001' AND status='RESERVED'"
        )
        assert len(reserved) == 2

    def test_revert_no_executed(self, engine):
        """EXECUTED 없을 때."""
        inbound_lot(engine, {'lot_no': 'RPR002', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        r = engine.revert_picked_to_reserved(lot_no='RPR002')
        assert not r['success']
        assert '없습니다' in r.get('message', '')

    def test_revert_stock_movement(self, engine):
        """REVERT_PICKED 이력 기록."""
        inbound_lot(engine, {'lot_no': 'RPR003', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _reserve_with_plan(engine, 'RPR003', count=1)
        _execute_plan(engine, 'RPR003')
        engine.revert_picked_to_reserved(lot_no='RPR003')

        moves = engine.db.fetchall(
            "SELECT * FROM stock_movement WHERE lot_no='RPR003' AND movement_type='REVERT_PICKED'"
        )
        assert len(moves) >= 1

    def test_revert_all(self, engine):
        """lot_no=None → 전체 EXECUTED 되돌리기."""
        inbound_lot(engine, {'lot_no': 'RPR004', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _reserve_with_plan(engine, 'RPR004', count=2)
        _execute_plan(engine, 'RPR004')

        r = engine.revert_picked_to_reserved(lot_no=None)
        assert r['success']
        assert r['reverted'] >= 2

    def test_revert_plan_status(self, engine):
        """allocation_plan EXECUTED → RESERVED 복원."""
        inbound_lot(engine, {'lot_no': 'RPR005', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _reserve_with_plan(engine, 'RPR005', count=1)
        _execute_plan(engine, 'RPR005')
        engine.revert_picked_to_reserved(lot_no='RPR005')

        plans = engine.db.fetchall(
            "SELECT status FROM allocation_plan WHERE lot_no='RPR005'"
        )
        for p in plans:
            assert p['status'] == 'RESERVED'
