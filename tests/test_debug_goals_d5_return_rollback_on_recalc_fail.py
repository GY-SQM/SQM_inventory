# -*- coding: utf-8 -*-
"""D5 회귀 테스트 — 재계산 실패 시 반품 처리를 롤백한다."""
import sqlite3
import pytest
from engine_modules.return_reinbound_engine import ReturnReinboundEngine, ReturnResult

class MockEngine:
    def _recalc_current_weight(self, lot_no, reason=None):
        raise ValueError("재계산 엔진 고장")

def _setup_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE inventory (
            lot_no TEXT PRIMARY KEY, status TEXT, 
            initial_weight REAL, current_weight REAL, picked_weight REAL
        )
    """)
    conn.execute("""
        CREATE TABLE inventory_tonbag (
            id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER, 
            status TEXT, weight REAL, weight_kg REAL, 
            is_sample INTEGER, tonbag_uid TEXT, location TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE outbound_log (
            outbound_id TEXT PRIMARY KEY, lot_no TEXT, customer TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE return_log (
            return_id TEXT PRIMARY KEY, outbound_id TEXT, lot_no TEXT, 
            customer TEXT, weight_kg REAL, processed_as TEXT, 
            new_location TEXT, operator_id TEXT, return_date TEXT, reason TEXT
        )
    """)
    conn.execute("CREATE TABLE sold_table (lot_no TEXT, status TEXT, remark TEXT)")
    
    conn.execute("INSERT INTO inventory VALUES ('LOT-D5', 'SOLD', 501, 0, 0)")
    conn.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, status, weight, weight_kg, is_sample, tonbag_uid) VALUES ('LOT-D5', 1, 'SOLD', 500, 500, 0, 'U1')")
    conn.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, status, weight, weight_kg, is_sample, tonbag_uid) VALUES ('LOT-D5', 99, 'AVAILABLE', 1, 1, 1, 'LOT-D5-S00')")
    conn.execute("INSERT INTO outbound_log VALUES ('OUT-D5', 'LOT-D5', 'CUST-A')")
    conn.commit()
    return conn


def test_process_rollbacks_on_recalc_failure():
    conn = _setup_db()
    engine = ReturnReinboundEngine(conn)
    engine._engine = MockEngine()
    
    result = engine.process(
        outbound_id='OUT-D5',
        lot_no='LOT-D5',
        new_location='RACK-1',
        reason='Test'
    )
    
    assert result.ok is False
    assert "재계산 엔진 고장" in result.error
    
    # Check rollback: return_log should be empty
    row = conn.execute("SELECT COUNT(*) FROM return_log").fetchone()
    assert row[0] == 0
    
    # tonbag should still be SOLD
    tb = conn.execute("SELECT status FROM inventory_tonbag WHERE lot_no='LOT-D5' AND sub_lt=1").fetchone()
    assert tb['status'] == 'SOLD'
