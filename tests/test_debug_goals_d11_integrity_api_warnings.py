# -*- coding: utf-8 -*-
"""D11 회귀 테스트 — /check API가 정합성 warnings를 반환한다."""
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.api.integrity_api import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_engine(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_sqm_d11.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE inventory (lot_no TEXT PRIMARY KEY, initial_weight REAL, current_weight REAL, picked_weight REAL, status TEXT, mxbg_pallet INTEGER)")
    conn.execute("CREATE TABLE inventory_tonbag (id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER, status TEXT, weight REAL, is_sample INTEGER, tonbag_uid TEXT)")
    conn.execute("CREATE TABLE audit_log (id INTEGER PRIMARY KEY, event_type TEXT, event_data TEXT, created_at TEXT, lot_no TEXT)")
    conn.commit()

    import config
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setenv("SQM_TEST_DB_PATH", db_path)

    import backend.api
    from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
    backend.api.engine = SQMInventoryEngineV3(db_path)
    backend.api.ENGINE_AVAILABLE = True

    yield conn
    conn.close()

def test_integrity_check_includes_warnings(setup_engine):
    mock_db = setup_engine
    
    # 1. Setup a lot with a warning (e.g. mxbg_pallet mismatch)
    # Header: mxbg=10
    mock_db.execute("INSERT INTO inventory (lot_no, initial_weight, current_weight, picked_weight, status, mxbg_pallet) VALUES ('LOT-D11', 5001.0, 5001.0, 0.0, 'AVAILABLE', 10)")
    # Tonbags: only 2 bags (mismatch 10 != 2 -> warning)
    mock_db.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, status, weight, is_sample, tonbag_uid) VALUES ('LOT-D11', 1, 'AVAILABLE', 500.0, 0, 'U1')")
    mock_db.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, status, weight, is_sample, tonbag_uid) VALUES ('LOT-D11', 99, 'AVAILABLE', 1.0, 1, 'LOT-D11-S00')")
    mock_db.commit()
    
    response = client.get("/api/integrity/check")
    assert response.status_code == 200
    data = response.json()
    
    # [BUG] Currently warning_lots is missing
    assert "warnings" in data["data"], "API 응답에 warnings 필드가 있어야 함"
    assert len(data["data"]["warnings"]) > 0, "톤백 수 불일치 경고가 포함되어야 함"
    assert data["data"]["warnings"][0]["lot_no"] == "LOT-D11"
    assert any("톤백 수 불일치" in w for w in data["data"]["warnings"][0]["warnings"])
