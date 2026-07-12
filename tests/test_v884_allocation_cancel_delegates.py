# -*- coding: utf-8 -*-
"""[감사 #3-M4] allocation cancel 이 엔진 정식 경로로 위임하는지 회귀 테스트.

수정 전: cancel_allocation_by_lot 이 raw-SQL 로 allocation_plan.status='CANCELLED'
  만 하고 톤백 RESERVED→AVAILABLE 복원·무게 재계산을 누락 → 활성 plan 없는
  '고아 RESERVED 톤백'이 남아 재예약 불가.
수정 후: engine.cancel_reservation(lot_no) 위임 → 톤백 AVAILABLE 복원 + plan CANCELLED
  + 무게 재계산 정합.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


def _seed_reserved(e, lot, normals=2, kg=1000):
    """AVAILABLE lot 을 만든 뒤 톤백을 RESERVED + allocation_plan(RESERVED) 로 세팅."""
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
                   "is_sample, status) VALUES (?,?,?,?,0,'RESERVED')", (iid, lot, s, kg))
    # 예약된 톤백마다 allocation_plan(RESERVED) 기록
    tbs = db.fetchall("SELECT id FROM inventory_tonbag WHERE lot_no=? AND COALESCE(is_sample,0)=0", (lot,))
    for tb in tbs:
        tb_id = tb["id"] if isinstance(tb, dict) else tb[0]
        db.execute("INSERT INTO allocation_plan (lot_no, tonbag_id, status) VALUES (?,?,'RESERVED')",
                   (lot, tb_id))


def _cnt(e, sql, params=()):
    r = e.db.fetchone(sql, params)
    return (r["c"] if isinstance(r, dict) else r[0]) if r else 0


def test_cancel_allocation_delegates_to_engine(monkeypatch):
    import backend.api as backend_api

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    eng = SQMInventoryEngineV3(db_path=path)
    monkeypatch.setattr(backend_api, "engine", eng, raising=False)
    monkeypatch.setattr(backend_api, "ENGINE_AVAILABLE", True, raising=False)
    try:
        _seed_reserved(eng, "LOTM", normals=2)
        assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag WHERE lot_no='LOTM' AND status='RESERVED'") == 2

        from backend.api.allocation_api import cancel_allocation_by_lot
        r = cancel_allocation_by_lot("LOTM")

        assert r["ok"] is True
        assert r.get("cancelled") == 2
        # 엔진 위임 증거 — 구 raw-SQL 은 하지 않던 톤백 복원:
        assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                    "WHERE lot_no='LOTM' AND status='RESERVED'") == 0, "고아 RESERVED 톤백 없음"
        assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                    "WHERE lot_no='LOTM' AND status='AVAILABLE'") == 2, "톤백 AVAILABLE 복원"
        # allocation_plan 은 CANCELLED
        assert _cnt(eng, "SELECT COUNT(*) c FROM allocation_plan "
                    "WHERE lot_no='LOTM' AND status='CANCELLED'") == 2
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
