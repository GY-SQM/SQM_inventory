# -*- coding: utf-8 -*-
"""D8 회귀 테스트 — 반품 재입고 시 샘플 존재 여부를 트랜잭션 시작 전(Preflight)에 검증한다."""
import sqlite3
import pytest
from engine_modules.return_reinbound_engine import ReturnReinboundEngine

def _setup_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE inventory (lot_no TEXT PRIMARY KEY, status TEXT, initial_weight REAL, current_weight REAL, picked_weight REAL)")
    conn.execute("CREATE TABLE inventory_tonbag (id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER, status TEXT, weight REAL, weight_kg REAL, is_sample INTEGER, tonbag_uid TEXT, location TEXT)")
    conn.execute("CREATE TABLE outbound_log (outbound_id TEXT PRIMARY KEY, lot_no TEXT, customer TEXT)")
    conn.execute("CREATE TABLE return_log (return_id TEXT PRIMARY KEY, outbound_id TEXT, lot_no TEXT, customer TEXT, weight_kg REAL, processed_as TEXT, new_location TEXT, operator_id TEXT, return_date TEXT, reason TEXT)")
    conn.execute("CREATE TABLE sold_table (lot_no TEXT, status TEXT, remark TEXT)")
    
    # LOT with NO sample
    conn.execute("INSERT INTO inventory VALUES ('LOT-D8', 'SOLD', 500, 0, 0)")
    conn.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, status, weight, weight_kg, is_sample, tonbag_uid) VALUES ('LOT-D8', 1, 'SOLD', 500, 500, 0, 'U1')")
    # NO SAMPLE INSERTED HERE
    
    conn.execute("INSERT INTO outbound_log VALUES ('OUT-D8', 'LOT-D8', 'CUST-A')")
    conn.commit()
    return conn

def test_process_returns_fail_during_preflight_if_no_sample():
    conn = _setup_db()
    engine = ReturnReinboundEngine(conn)
    
    # We want to check if BEGIN was called.
    # In a real sqlite3 connection, we can't easily check transaction status without overhead.
    # But we can verify if return_id generation was skipped if we put validation in _preflight.
    
    result = engine.process(
        outbound_id='OUT-D8',
        lot_no='LOT-D8',
        new_location='RACK-1',
        reason='Test'
    )
    
    assert result.ok is False
    assert "샘플" in result.error
    
    # If it failed in _preflight, error message should NOT contain "DB 오류 (롤백)"
    assert "DB 오류 (롤백)" not in result.error, "Preflight에서 걸러져야 하므로 DB 롤백 오류가 나오면 안 됨"
    
    # If it failed in _preflight, ReturnResult.return_id should be None
    assert result.return_id is None, "Preflight 실패 시 return_id가 생성되지 않아야 함"
