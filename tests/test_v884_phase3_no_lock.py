# -*- coding: utf-8 -*-
"""[감사 M3 Phase 3] product_master/settings/inbound 쓰기 엔드포인트 오류 시 미잠금.

Phase 1·2 와 동일 검증을 _open_db() 기반 inbound 엔드포인트에 대해 확인.
"""
import os
import sqlite3
import sys
import tempfile

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


class _BoomConn:
    def __init__(self, real, boom_at):
        self._real = real
        self._n = 0
        self._boom = boom_at

    def execute(self, *a, **k):
        self._n += 1
        if self._n >= self._boom:
            raise sqlite3.OperationalError("injected failure (test)")
        return self._real.execute(*a, **k)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _make_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    eng = SQMInventoryEngineV3(db_path=path)
    db = eng.db
    db.execute("INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
               "picked_weight, mxbg_pallet, status) VALUES ('LOTP','P',1000,1000,0,1,'PENDING')")
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, is_sample, status) "
               "SELECT id,'LOTP',1,1000,0,'PENDING' FROM inventory WHERE lot_no='LOTP'")
    eng.close()
    return path


def _cleanup(path):
    for p in (path, path + "-wal", path + "-shm"):
        try:
            os.remove(p)
        except OSError:
            pass


def _can_write_now(path):
    c = sqlite3.connect(path, timeout=1.0)
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("BEGIN IMMEDIATE")
        c.execute("UPDATE inventory SET updated_at=datetime('now') WHERE lot_no='LOTP'")
        c.commit()
        return True
    except sqlite3.OperationalError as e:
        return False if "locked" in str(e).lower() else True
    finally:
        c.close()


def test_confirm_inbound_error_does_not_lock_db(monkeypatch):
    path = _make_db()
    holder = []
    try:
        import backend.api.inbound as inb

        def _factory():
            real = sqlite3.connect(path, timeout=5, check_same_thread=False)
            real.row_factory = sqlite3.Row
            real.execute("PRAGMA journal_mode=WAL")
            real.execute("PRAGMA busy_timeout=3000")
            # SELECT(1) → PRAGMA table_info(2) → UPDATE inventory(3, 쓰기=락) → UPDATE tonbag(4) BOOM
            bc = _BoomConn(real, boom_at=4)
            holder.append(real)   # GC 로 락 가려지지 않게 참조 유지
            return bc
        monkeypatch.setattr(inb, "_open_db", _factory)

        with pytest.raises(HTTPException):
            inb.confirm_inbound("LOTP", {"inbound_date": "2026-07-13"})

        assert _can_write_now(path) is True, "오류 후 DB가 잠김 — 연결이 안 닫혔다"
    finally:
        _cleanup(path)
