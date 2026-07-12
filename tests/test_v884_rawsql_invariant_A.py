# -*- coding: utf-8 -*-
"""[감사 raw-SQL / 방침 (A)] raw-SQL 우회 엔드포인트 무게 불변식 복구 회귀 테스트.

방침 (A): 화면 동작(상태 전이)은 그대로 두고, 커밋 직후 엔진 재계산으로
`initial_weight = current_weight + picked_weight` 불변식만 복구한다.

대상(단일 LOT 4개):
  - actions2.outbound_confirm  : current_weight=0 만 하고 picked 로 안 옮겨 무게 증발
  - actions3.return_create     : RETURN 전환 후 무게 재계산 누락
  - scan_api.scan_confirm_outbound : (a)바인딩 개수 버그로 항상 실패 (b)무게 재계산 누락
  - allocation_api.revert_allocation_step : SOLD→PICKED 시 sold_table 잔존 + 무게 미정합
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
    eng = SQMInventoryEngineV3(db_path=path)
    return eng, path


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


def _seed_available(eng, lot, normals=2, kg=1000):
    db = eng.db
    init = normals * kg + 1
    db.execute(
        "INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
        "picked_weight, mxbg_pallet, status) VALUES (?,?,?,?,0,?,'AVAILABLE')",
        (lot, "P1", init, init, normals))
    iid = eng.db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot,))
    iid = iid["id"] if isinstance(iid, dict) else iid[0]
    for s in range(1, normals + 1):
        db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
                   "is_sample, status) VALUES (?,?,?,?,0,'AVAILABLE')", (iid, lot, s, kg))
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
               "is_sample, status) VALUES (?,?,0,1,1,'AVAILABLE')", (iid, lot))


def _bind_engine(monkeypatch, eng):
    import backend.api as bapi
    monkeypatch.setattr(bapi, "engine", eng, raising=False)
    monkeypatch.setattr(bapi, "ENGINE_AVAILABLE", True, raising=False)


def test_action2_outbound_confirm_restores_weight(monkeypatch):
    eng, path = _mk_engine()
    try:
        _bind_engine(monkeypatch, eng)
        import backend.api.actions2 as a2
        monkeypatch.setattr(a2, "_db_path", lambda: path)
        _seed_available(eng, "LOTA2", normals=2)

        r = a2.outbound_confirm({"lot_no": "LOTA2", "customer": "ACME"})
        assert r.get("ok") is True, r
        # (A) 핵심: 무게가 사라지지 않고 picked 로 이동 → 불변식 유지
        assert eng.verify_lot_integrity("LOTA2")["valid"], eng.verify_lot_integrity("LOTA2")
    finally:
        _cleanup(eng, path)


def test_action3_return_create_restores_weight(monkeypatch):
    eng, path = _mk_engine()
    try:
        _bind_engine(monkeypatch, eng)
        import backend.api.actions3 as a3
        monkeypatch.setattr(a3, "_db_path", lambda: path)
        _seed_available(eng, "LOTR3", normals=2)
        eng.quick_outbound("LOTR3", 2, "ACME")   # PICKED 상태에서 반품 → picked→current 이동 필요

        r = a3.return_create({"lot_no": "LOTR3", "reason": "고객요청"})
        assert r.get("ok") is True, r
        assert eng.verify_lot_integrity("LOTR3")["valid"], eng.verify_lot_integrity("LOTR3")
    finally:
        _cleanup(eng, path)


def test_scan_confirm_outbound_works_and_keeps_integrity(monkeypatch):
    eng, path = _mk_engine()
    try:
        _bind_engine(monkeypatch, eng)
        import backend.api.scan_api as sa
        monkeypatch.setattr(sa, "_db_path", lambda: path)
        _seed_available(eng, "LOTS5", normals=2)
        eng.quick_outbound("LOTS5", 2, "ACME")   # 톤백 PICKED
        row = eng.db.fetchone(
            "SELECT tonbag_uid FROM inventory_tonbag WHERE lot_no='LOTS5' AND status='PICKED' LIMIT 1")
        uid = row["tonbag_uid"] if isinstance(row, dict) else row[0]

        r = sa.scan_confirm_outbound({"uid": uid})
        # 바인딩 버그 수정 → 이제 성공(기존엔 항상 실패)
        assert r.get("success") is True, r
        assert eng.verify_lot_integrity("LOTS5")["valid"], eng.verify_lot_integrity("LOTS5")
    finally:
        _cleanup(eng, path)


def test_revert_step_sold_to_picked_clears_soldtable(monkeypatch):
    eng, path = _mk_engine()
    try:
        _bind_engine(monkeypatch, eng)
        import backend.api.allocation_api as aa
        import sqlite3

        def _tmp_alloc_db():
            con = sqlite3.connect(path, timeout=5, check_same_thread=False)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA journal_mode=WAL")
            return con
        monkeypatch.setattr(aa, "_alloc_db", _tmp_alloc_db)

        # SOLD 상태 재현: 톤백 SOLD, inventory SOLD, allocation_plan SOLD, sold_table 1행
        _seed_available(eng, "LOTV7", normals=2)
        db = eng.db
        db.execute("UPDATE inventory_tonbag SET status='SOLD' WHERE lot_no='LOTV7' AND is_sample=0")
        db.execute("UPDATE inventory SET status='SOLD', current_weight=0, picked_weight=2000 WHERE lot_no='LOTV7'")
        iid = eng.db.fetchone("SELECT id FROM inventory WHERE lot_no='LOTV7'")
        iid = iid["id"] if isinstance(iid, dict) else iid[0]
        tbs = eng.db.fetchall("SELECT id FROM inventory_tonbag WHERE lot_no='LOTV7' AND is_sample=0")
        for tb in tbs:
            tbid = tb["id"] if isinstance(tb, dict) else tb[0]
            db.execute("INSERT INTO allocation_plan (lot_no, tonbag_id, status) VALUES ('LOTV7',?,'SOLD')", (tbid,))
            db.execute("INSERT INTO sold_table (lot_no, tonbag_id, sold_qty_kg, status, created_by) "
                       "VALUES ('LOTV7',?,1000,'SOLD','test')", (tbid,))

        assert _cnt(eng, "SELECT COUNT(*) c FROM sold_table WHERE lot_no='LOTV7'") == 2

        r = aa.revert_allocation_step({"from_status": "SOLD", "lot_nos": ["LOTV7"]})
        assert r.get("ok") is True, r
        # 화면 동작 그대로: SOLD→PICKED
        assert _cnt(eng, "SELECT COUNT(*) c FROM inventory_tonbag WHERE lot_no='LOTV7' AND status='PICKED'") == 2
        # (A) 데이터 정합: 판매기록 정리됨
        assert _cnt(eng, "SELECT COUNT(*) c FROM sold_table WHERE lot_no='LOTV7'") == 0, "sold_table wedge 제거"
        assert eng.verify_lot_integrity("LOTV7")["valid"], eng.verify_lot_integrity("LOTV7")
    finally:
        _cleanup(eng, path)


def _cnt(eng, sql, params=()):
    r = eng.db.fetchone(sql, params)
    return (r["c"] if isinstance(r, dict) else r[0]) if r else 0
