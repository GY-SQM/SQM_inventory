# -*- coding: utf-8 -*-
"""[감사 #3-C] allocation/confirm 이 엔진 정식 경로로 위임하는지 회귀 테스트.

수정 전: POST /api/allocation/{lot}/confirm 이 raw-SQL 2개 UPDATE
  (allocation_plan.status='SOLD', inventory.status='SOLD')만 하고 톤백 전환·
  sold_table·stock_movement·무게 재계산을 누락 → LOT wedge.
수정 후: engine.confirm_outbound(lot) 로 위임 → 톤백 SOLD 전환 + sold_table 기록 +
  stock_movement + 무게 재계산이 한 트랜잭션으로 정합.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


def _seed(e, lot, normals=2, kg=1000):
    db = e.db
    init = normals * kg + 1
    db.execute(
        "INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
        "picked_weight, mxbg_pallet, status) VALUES (?,?,?,?,0,?,'AVAILABLE')",
        (lot, "P1", init, init, normals))
    iid_row = db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot,))
    iid = iid_row["id"] if isinstance(iid_row, dict) else iid_row[0]
    for s in range(1, normals + 1):
        db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
                   "is_sample, status) VALUES (?,?,?,?,0,'AVAILABLE')", (iid, lot, s, kg))
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
               "is_sample, status) VALUES (?,?,0,1,1,'AVAILABLE')", (iid, lot))


def _cnt(e, sql, params):
    r = e.db.fetchone(sql, params)
    return (r["c"] if isinstance(r, dict) else r[0]) if r else 0


def test_confirm_allocation_delegates_to_engine(monkeypatch):
    import backend.api as backend_api

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    eng = SQMInventoryEngineV3(db_path=path)
    monkeypatch.setattr(backend_api, "engine", eng, raising=False)
    monkeypatch.setattr(backend_api, "ENGINE_AVAILABLE", True, raising=False)
    try:
        _seed(eng, "LOTC", normals=2)
        eng.quick_outbound("LOTC", 2, "ACME")   # 톤백 2개 PICKED

        from backend.api.allocation_api import confirm_allocation_by_lot
        r = confirm_allocation_by_lot("LOTC")

        assert r["ok"] is True
        assert r.get("confirmed") == 2
        # 엔진 위임 증거 — 구 raw-2UPDATE 는 하지 않던 것:
        assert _cnt(eng, "SELECT COUNT(*) c FROM sold_table WHERE lot_no='LOTC'", ()) == 2, \
            "sold_table 기록됨(엔진 정식 경로)"
        assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                    "WHERE lot_no='LOTC' AND status='PICKED'", ()) == 0, \
            "톤백 PICKED 잔여 0 (SOLD 전환)"
        assert _cnt(eng, "SELECT COUNT(*) c FROM stock_movement "
                    "WHERE lot_no='LOTC' AND movement_type='OUTBOUND'", ()) >= 1, \
            "stock_movement OUTBOUND 기록됨"
        # LOT 무결성 유지 (wedge 없음)
        assert eng.verify_lot_integrity("LOTC")["valid"]
    finally:
        try:
            eng.close()
        except Exception:
            pass
        for p in (path, path + "-wal", path + "-shm"):
            try:
                os.remove(p)
            except OSError:
                pass
