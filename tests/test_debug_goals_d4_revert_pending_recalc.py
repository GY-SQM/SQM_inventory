# -*- coding: utf-8 -*-
"""D4 회귀 테스트 — AVAILABLE→PENDING 상태복원 후 LOT 무게를 재계산한다."""
import sqlite3
from backend.api.status_revert_api import execute_status_revert

def _make_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE inventory (lot_no TEXT PRIMARY KEY, status TEXT, initial_weight REAL, current_weight REAL, picked_weight REAL, inbound_date TEXT, updated_at TEXT)")
    con.execute("CREATE TABLE inventory_tonbag (lot_no TEXT, sub_lt INTEGER, status TEXT, weight REAL, updated_at TEXT)")
    con.execute("CREATE TABLE audit_log (event_type TEXT, event_data TEXT, user_note TEXT, created_by TEXT, created_at TEXT)")
    return con

def test_execute_status_revert_recalculates_weights_after_available_to_pending():
    con = _make_db()
    # Initial state: AVAILABLE with 1000kg
    con.execute("INSERT INTO inventory (lot_no, status, initial_weight, current_weight, picked_weight, inbound_date, updated_at) VALUES ('LOT-D4', 'AVAILABLE', 1000, 1000, 0, '2026-06-01', NULL)")
    con.execute("INSERT INTO inventory_tonbag VALUES ('LOT-D4', 1, 'AVAILABLE', 500, NULL)")
    con.execute("INSERT INTO inventory_tonbag VALUES ('LOT-D4', 2, 'AVAILABLE', 500, NULL)")

    result = execute_status_revert(con, {
        "from_status": "AVAILABLE",
        "to_status": "PENDING",
        "scope_type": "lot_no",
        "scope_value": "LOT-D4",
        "actor": "test",
    })

    assert result["ok"] is True
    row = con.execute("SELECT status, current_weight, picked_weight FROM inventory WHERE lot_no='LOT-D4'").fetchone()
    assert row["status"] == "PENDING"
    # PENDING은 재고로 잡히지 않아야 하므로 current_weight=0 이어야 함
    assert row["current_weight"] == 0, "AVAILABLE->PENDING 후에는 current_weight가 0으로 재계산되어야 함"
    assert row["picked_weight"] == 0
