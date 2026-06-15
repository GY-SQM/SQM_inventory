# -*- coding: utf-8 -*-
"""D7 회귀 테스트 — 재고조정 시 UPDATE rowcount가 0이면 실패로 처리한다."""
import sqlite3
import pytest
from engine_modules.inventory_modular.adjust_executor import execute_adjustment

class MockDB:
    def __init__(self):
        self.lastrowid = 100
    
    def fetchone(self, query, params=()):
        if "FROM inventory" in query:
            return {"mxbg_pallet": 10, "net_weight": 5000, "gross_weight": 5131, "current_weight": 5000, "status": "AVAILABLE"}
        if "FROM allocation_plan" in query:
            return {"reserved_count": 0}
        return None
        
    def execute(self, query, params=()):
        class Cursor:
            def __init__(self, rowcount, lastrowid):
                self.rowcount = rowcount
                self.lastrowid = lastrowid
        
        # Simulate UPDATE affecting 0 rows (e.g. concurrent delete or logic error)
        rowcount = 0 if "UPDATE inventory" in query else 1
        return Cursor(rowcount, self.lastrowid)

    def transaction(self, mode="DEFERRED"):
        class Tx:
            def __enter__(self): pass
            def __exit__(self, *args): pass
        return Tx()

def test_execute_adjustment_fails_if_update_rowcount_is_zero():
    db = MockDB()
    items = [{"lot_no": "LOT-D7", "new_count": 5}]
    
    result = execute_adjustment(items, db, excel_path=None)
    
    # rowcount=0이면 failed에 있어야 함
    assert "LOT-D7" not in result.success, "UPDATE 0행이면 성공 목록에 있으면 안 됨"
    assert any("LOT-D7" in f and "0행" in f for f in result.failed), f"실패 사유에 0행 업데이트임이 명시되어야 함. Actual: {result.failed}"
