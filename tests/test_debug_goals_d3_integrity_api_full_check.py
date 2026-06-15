# -*- coding: utf-8 -*-
"""D3 회귀 테스트 — /check API가 verify_lot_integrity의 모든 검증 항목을 반영한다."""
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
    db_path = str(tmp_path / "test_sqm_d3.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE inventory (lot_no TEXT PRIMARY KEY, initial_weight REAL, current_weight REAL, picked_weight REAL, status TEXT, mxbg_pallet INTEGER)")
    conn.execute("CREATE TABLE inventory_tonbag (id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER, status TEXT, weight REAL, is_sample INTEGER)")
    conn.execute("CREATE TABLE allocation_plan (id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER, status TEXT, qty_mt REAL)")
    # D2/D12 need audit_log
    conn.execute("CREATE TABLE audit_log (id INTEGER PRIMARY KEY, event_type TEXT, event_data TEXT, created_at TEXT, lot_no TEXT)")
    conn.commit()

    # Monkeypatch config.DB_PATH and re-init engine
    import config
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setenv("SQM_TEST_DB_PATH", db_path)

    import backend.api
    from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
    backend.api.engine = SQMInventoryEngineV3(db_path)
    backend.api.ENGINE_AVAILABLE = True

    yield conn
    conn.close()

def test_integrity_check_captures_picked_greater_than_initial(setup_engine):
    mock_db = setup_engine
    # initial = current + picked (1000 = -100 + 1100) -> 식은 맞지만 비정상
    # 또는 1000 = 0 + 1100 -> 식 틀림
    # D3 목표는 picked > initial 같은 edge case를 잡는 것.
    
    # Case 1: Equation holds but picked > initial (e.g. current is negative or something)
    # Actually if pw > iw + 1.0, verify_lot_integrity sets valid=False.
    
    mock_db.execute("INSERT INTO inventory (lot_no, initial_weight, current_weight, picked_weight, status, mxbg_pallet) VALUES ('LOT-D3-1', 1001.0, -100.0, 1101.0, 'AVAILABLE', 2)")
    mock_db.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, status, weight, is_sample) VALUES ('LOT-D3-1', 99, 'AVAILABLE', 1.0, 1)")
    mock_db.commit()
    
    response = client.get("/api/integrity/check")
    assert response.status_code == 200
    data = response.json()
    
    # 기존 코드는 ABS(1000 - (-100 + 1100)) = 0 이므로 통과시켜버림.
    # 하지만 current_weight < 0 이므로 에러여야 함.
    assert any(d['lot_no'] == 'LOT-D3-1' for d in data['data']['details']), "current_weight 음수는 에러로 검출되어야 함"

def test_integrity_check_captures_tonbag_mismatch_even_if_inventory_header_is_consistent(setup_engine):
    mock_db = setup_engine
    # Header: 1000 = 1000 + 0 (OK)
    # Tonbags: 500 (AVAILABLE) -> Sum = 500 != Header 1000 (ERROR)
    
    mock_db.execute("INSERT INTO inventory (lot_no, initial_weight, current_weight, picked_weight, status, mxbg_pallet) VALUES ('LOT-D3-2', 1001.0, 1001.0, 0.0, 'AVAILABLE', 2)")
    mock_db.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, status, weight, is_sample) VALUES ('LOT-D3-2', 1, 'AVAILABLE', 500.0, 0)")
    mock_db.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, status, weight, is_sample) VALUES ('LOT-D3-2', 99, 'AVAILABLE', 1.0, 1)")
    mock_db.commit()
    
    response = client.get("/api/integrity/check")
    assert response.status_code == 200
    data = response.json()
    
    # 기존 코드는 inventory 테이블만 보므로 이 불일치를 못 잡음.
    assert any(d['lot_no'] == 'LOT-D3-2' for d in data['data']['details']), "Header-Tonbag 불일치는 에러로 검출되어야 함"
