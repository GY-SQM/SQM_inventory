# -*- coding: utf-8 -*-
"""[감사 raw-SQL / 방침 (A)] MED 엔드포인트 무게 불변식·정합 복구 회귀 테스트.

대상(발췌 — 대표 위험군):
  - inventory_api.scan_process(outbound): 재스캔 시 무게 이중차감(음수/붕괴) + WHERE sub_lt
    로 타 LOT 오염 → id+AVAILABLE 가드 + 엔진 재계산으로 idempotent.
  - inventory_api.cancel_inventory: allocation_plan 미취소(재예약 막힘) + 무게 미정합 복구.
  - allocation_api.reset_allocation_by_lot: 톤백 미복원 wedge + 무게 미정합 복구.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


def _mk_engine():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return SQMInventoryEngineV3(db_path=path), path


def _cleanup(eng, path):
    try:
        eng.close()
    except Exception:
        pass
    for p in (path, path + "-wal", path + "-shm"):
        try:
            os.remove(p)
        except OSError:
            pass


def _seed(eng, lot, status="AVAILABLE", normals=2, kg=1000):
    """inventory + 톤백을 지정 상태로 시딩. 무게는 상태에 맞게(초기엔 current=full)."""
    db = eng.db
    init = normals * kg + 1
    # PICKED 이면 current=0/picked=full 로(엔진 정합 상태 재현), 그 외 current=full
    cur_w = 0 if status == "PICKED" else init
    pk_w = normals * kg if status == "PICKED" else 0
    db.execute(
        "INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
        "picked_weight, mxbg_pallet, status) VALUES (?,?,?,?,?,?,?)",
        (lot, "P1", init, cur_w, pk_w, normals, status))
    iid = eng.db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot,))
    iid = iid["id"] if isinstance(iid, dict) else iid[0]
    for s in range(1, normals + 1):
        db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
                   "is_sample, status) VALUES (?,?,?,?,0,?)", (iid, lot, s, kg, status))
    # 샘플은 항상 AVAILABLE(창고 내)
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
               "is_sample, status) VALUES (?,?,0,1,1,'AVAILABLE')", (iid, lot))


def _weights(eng, lot):
    r = eng.db.fetchone("SELECT current_weight, picked_weight FROM inventory WHERE lot_no=?", (lot,))
    if isinstance(r, dict):
        return float(r["current_weight"]), float(r["picked_weight"])
    return float(r[0]), float(r[1])


def _cnt(eng, sql, params=()):
    r = eng.db.fetchone(sql, params)
    return (r["c"] if isinstance(r, dict) else r[0]) if r else 0


def _bind(monkeypatch, eng):
    import backend.api as bapi
    monkeypatch.setattr(bapi, "engine", eng, raising=False)
    monkeypatch.setattr(bapi, "ENGINE_AVAILABLE", True, raising=False)


def test_scan_process_rescan_idempotent(monkeypatch):
    eng, path = _mk_engine()
    try:
        _bind(monkeypatch, eng)
        monkeypatch.setenv("SQM_TEST_DB_PATH", path)
        import backend.api.inventory_api as iv
        _seed(eng, "LOTSP", status="AVAILABLE", normals=2)
        row = eng.db.fetchone(
            "SELECT tonbag_uid FROM inventory_tonbag WHERE lot_no='LOTSP' AND is_sample=0 LIMIT 1")
        uid = row["tonbag_uid"] if isinstance(row, dict) else row[0]

        r1 = iv.scan_process({"barcode": uid, "action": "outbound"})
        assert r1["success"] is True, r1
        c1, p1 = _weights(eng, "LOTSP")
        assert abs(c1 - 1001) < 0.01 and abs(p1 - 1000) < 0.01, (c1, p1)
        # 재스캔 — 이중 차감 없이 동일해야(멱등)
        iv.scan_process({"barcode": uid, "action": "outbound"})
        c2, p2 = _weights(eng, "LOTSP")
        assert abs(c2 - 1001) < 0.01 and abs(p2 - 1000) < 0.01, f"재스캔 이중차감! {(c2, p2)}"
        assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                    "WHERE lot_no='LOTSP' AND status='PICKED'") == 1
    finally:
        _cleanup(eng, path)


def test_cancel_inventory_cancels_plan_and_recalcs(monkeypatch):
    eng, path = _mk_engine()
    try:
        _bind(monkeypatch, eng)
        monkeypatch.setenv("SQM_TEST_DB_PATH", path)
        import backend.api.inventory_api as iv
        _seed(eng, "LOTCI", status="PICKED", normals=2)
        # allocation_plan RESERVED 남겨둠
        tbs = eng.db.fetchall("SELECT id FROM inventory_tonbag WHERE lot_no='LOTCI' AND is_sample=0")
        for tb in tbs:
            tbid = tb["id"] if isinstance(tb, dict) else tb[0]
            eng.db.execute("INSERT INTO allocation_plan (lot_no, tonbag_id, status) VALUES ('LOTCI',?,'RESERVED')", (tbid,))

        r = iv.cancel_inventory("LOTCI")
        assert r["success"] is True, r
        # allocation_plan 취소됨(재예약 가능)
        assert _cnt(eng, "SELECT COUNT(*) c FROM allocation_plan WHERE lot_no='LOTCI' AND status='RESERVED'") == 0
        assert _cnt(eng, "SELECT COUNT(*) c FROM allocation_plan WHERE lot_no='LOTCI' AND status='CANCELLED'") == 2
        # 톤백 AVAILABLE 복원 + 무게 재계산(picked→current)
        assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag WHERE lot_no='LOTCI' AND status='AVAILABLE'") == 3
        cur, pk = _weights(eng, "LOTCI")
        assert abs(cur - 2001) < 0.01 and abs(pk - 0) < 0.01, (cur, pk)
    finally:
        _cleanup(eng, path)


def test_reset_by_lot_restores_tonbags(monkeypatch):
    eng, path = _mk_engine()
    try:
        _bind(monkeypatch, eng)
        import backend.api.allocation_api as aa
        import sqlite3

        def _tmp_alloc_db():
            con = sqlite3.connect(path, timeout=5, check_same_thread=False)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA journal_mode=WAL")
            return con
        monkeypatch.setattr(aa, "_alloc_db", _tmp_alloc_db)

        _seed(eng, "LOTRL", status="PICKED", normals=2)
        tbs = eng.db.fetchall("SELECT id FROM inventory_tonbag WHERE lot_no='LOTRL' AND is_sample=0")
        for tb in tbs:
            tbid = tb["id"] if isinstance(tb, dict) else tb[0]
            eng.db.execute("INSERT INTO allocation_plan (lot_no, tonbag_id, status) VALUES ('LOTRL',?,'PICKED')", (tbid,))

        r = aa.reset_allocation_by_lot("LOTRL")
        assert r["ok"] is True, r
        # 완전 초기화: 톤백도 AVAILABLE 로 복원(wedge 제거)
        assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                    "WHERE lot_no='LOTRL' AND status IN ('PICKED','RESERVED')") == 0, "톤백 wedge 제거"
        assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag "
                    "WHERE lot_no='LOTRL' AND status='AVAILABLE'") == 3
        cur, pk = _weights(eng, "LOTRL")
        assert abs(cur - 2001) < 0.01 and abs(pk - 0) < 0.01, (cur, pk)
    finally:
        _cleanup(eng, path)
