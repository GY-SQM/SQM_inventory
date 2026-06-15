# -*- coding: utf-8 -*-
"""D10 회귀 테스트 — 입고 후 정합성 검증 실패 시 입고를 차단(Hard-stop)한다."""
import sqlite3
import pytest
from engine_modules.inventory_modular.engine import SQMInventoryEngineV3

@pytest.fixture
def engine(tmp_path):
    db_path = str(tmp_path / "test_sqm_d10.db")
    engine = SQMInventoryEngineV3(db_path)
    return engine

def test_process_inbound_fails_if_integrity_check_fails(engine):
    # Mock verify_lot_integrity to always return False
    # Actually, we can trigger a real integrity failure.
    # E.g. make mxbg_pallet mismatch tonbag count (if we can skip tonbag creation but keep mxbg_pallet)
    # But easier to just monkeypatch verify_lot_integrity for this specific test.
    
    original_verify = engine.verify_lot_integrity
    def mock_verify(lot_no):
        return {'valid': False, 'errors': ['[TEST] 정합성 강제 실패'], 'warnings': [], 'details': {}}
    
    engine.verify_lot_integrity = mock_verify
    
    packing = {
        'lot_no': 'LOT-D10',
        'net_weight': 1001.0,
        'mxbg_pallet': 2,
        'bl_no': 'BL-D10',
        'product': 'TEST'
    }
    
    result = engine.process_inbound(packing)
    
    # [BUG] Currently it returns success=True with warnings
    assert result['success'] is False, "정합성 검증 실패 시 입고가 실패해야 함 (D10)"
    assert any('[TEST] 정합성 강제 실패' in e for e in result['errors'])
    
    # DB 확인: 롤백되어야 함
    row = engine.db.fetchone("SELECT COUNT(*) as cnt FROM inventory WHERE lot_no='LOT-D10'")
    assert row['cnt'] == 0, "정합성 실패 시 데이터가 롤백되어야 함"
