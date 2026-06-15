# -*- coding: utf-8 -*-
"""D2 회귀 테스트 — 상태복원 후 LOT 무게를 톤백 상태 기준으로 재계산한다."""
import sqlite3

from backend.api.status_revert_api import execute_status_revert


def _make_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE inventory (lot_no TEXT PRIMARY KEY, status TEXT, initial_weight REAL, current_weight REAL, picked_weight REAL, sold_to TEXT, sale_ref TEXT, updated_at TEXT)")
    con.execute("CREATE TABLE inventory_tonbag (lot_no TEXT, sub_lt INTEGER, status TEXT, weight REAL, sale_ref TEXT, picked_to TEXT, pick_ref TEXT, updated_at TEXT)")
    con.execute("CREATE TABLE audit_log (event_type TEXT, event_data TEXT, user_note TEXT, created_by TEXT, created_at TEXT)")
    return con


def test_execute_status_revert_recalculates_weights_after_sold_to_picked():
    con = _make_db()
    con.execute("INSERT INTO inventory VALUES ('LOT-D2', 'SOLD', 1000, 0, 0, NULL, NULL, NULL)")
    con.execute("INSERT INTO inventory_tonbag VALUES ('LOT-D2', 1, 'SOLD', 500, NULL, NULL, NULL, NULL)")
    con.execute("INSERT INTO inventory_tonbag VALUES ('LOT-D2', 2, 'SOLD', 500, NULL, NULL, NULL, NULL)")

    result = execute_status_revert(con, {
        "from_status": "SOLD",
        "to_status": "PICKED",
        "scope_type": "lot_no",
        "scope_value": "LOT-D2",
        "actor": "test",
    })

    assert result["ok"] is True
    row = con.execute("SELECT status, current_weight, picked_weight FROM inventory WHERE lot_no='LOT-D2'").fetchone()
    assert row["status"] == "PICKED"
    assert row["current_weight"] == 0
    assert row["picked_weight"] == 1000
    assert result["data"]["counts"]["recalculated_lots"] == 1


def test_execute_status_revert_recalculates_available_weight_after_reserved_to_available():
    con = _make_db()
    con.execute("INSERT INTO inventory VALUES ('LOT-D2B', 'RESERVED', 1000, 0, 1000, NULL, NULL, NULL)")
    con.execute("INSERT INTO inventory_tonbag VALUES ('LOT-D2B', 1, 'RESERVED', 500, NULL, NULL, NULL, NULL)")
    con.execute("INSERT INTO inventory_tonbag VALUES ('LOT-D2B', 2, 'RESERVED', 500, NULL, NULL, NULL, NULL)")

    result = execute_status_revert(con, {
        "from_status": "RESERVED",
        "to_status": "AVAILABLE",
        "scope_type": "lot_no",
        "scope_value": "LOT-D2B",
        "actor": "test",
    })

    assert result["ok"] is True
    row = con.execute("SELECT status, current_weight, picked_weight FROM inventory WHERE lot_no='LOT-D2B'").fetchone()
    assert row["status"] == "AVAILABLE"
    assert row["current_weight"] == 1000
    assert row["picked_weight"] == 0
