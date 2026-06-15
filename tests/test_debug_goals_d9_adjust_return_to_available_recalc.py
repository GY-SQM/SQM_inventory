# -*- coding: utf-8 -*-
"""D9 회귀 테스트 — return_to_available 액션 시 LOT 무게를 재계산한다."""
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.api.inventory_adjust_api import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.fixture
def mock_db_and_engine(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_sqm_d9.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE inventory (lot_no TEXT PRIMARY KEY, status TEXT, initial_weight REAL, current_weight REAL, picked_weight REAL, updated_at TEXT)")
    conn.execute("CREATE TABLE inventory_tonbag (lot_no TEXT, sub_lt INTEGER, status TEXT, weight REAL, updated_at TEXT)")
    # D9: recalc needs tonbag_move_log or at least existing tonbags
    conn.commit()
    
    monkeypatch.setenv("SQM_TEST_DB_PATH", db_path)
    
    import backend.api
    from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
    backend.api.engine = SQMInventoryEngineV3(db_path)
    backend.api.ENGINE_AVAILABLE = True
    
    yield conn, backend.api.engine
    conn.close()

def test_return_to_available_action_recalculates_weight(mock_db_and_engine, monkeypatch):
    conn, engine = mock_db_and_engine
    
    # 1. Setup LOT in RETURN status with WRONG weight (0)
    # Header
    conn.execute("INSERT INTO inventory (lot_no, status, initial_weight, current_weight, picked_weight) VALUES ('LOT-D9', 'RETURN', 1000, 0, 0)")
    # Tonbags
    conn.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, status, weight) VALUES ('LOT-D9', 1, 'RETURN', 500)")
    conn.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, status, weight) VALUES ('LOT-D9', 2, 'RETURN', 500)")
    conn.commit()
    
    # 2. Call API
    response = client.post("/api/inventory/adjust", json={
        "lot_no": "LOT-D9",
        "action": "return_to_available"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    
    # 3. Verify DB
    row = conn.execute("SELECT status, current_weight FROM inventory WHERE lot_no='LOT-D9'").fetchone()
    assert row["status"] == "AVAILABLE"
    
    # [BUG] Currently it stays 0 because no recalc is called in inventory_adjust_api.py
    assert row["current_weight"] == 1000, "return_to_available 후에는 current_weight가 1000으로 재계산되어야 함"
