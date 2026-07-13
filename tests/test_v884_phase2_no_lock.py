# -*- coding: utf-8 -*-
"""[감사 M3 Phase 2] 출고/입고/스캔/재고 쓰기 엔드포인트가 오류 시 DB 락을 안 남기는지.

Phase 1(배정)과 동일 검증을 _db() 기반 파일(actions3 등)에 대해 확인 —
with db_session(...) 채택이 파일 전반에서 동작함을 보장.
"""
import os
import sqlite3
import sys
import tempfile

import pytest

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
               "picked_weight, mxbg_pallet, status) VALUES ('LOTZ','P',1000,1000,0,1,'AVAILABLE')")
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, is_sample, status) "
               "SELECT id,'LOTZ',1,1000,0,'AVAILABLE' FROM inventory WHERE lot_no='LOTZ'")
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
        c.execute("UPDATE inventory SET updated_at=datetime('now') WHERE lot_no='LOTZ'")
        c.commit()
        return True
    except sqlite3.OperationalError as e:
        return False if "locked" in str(e).lower() else True
    finally:
        c.close()


def _boom_factory(path, boom_at):
    def _f():
        real = sqlite3.connect(path, timeout=5, check_same_thread=False)
        real.row_factory = sqlite3.Row
        real.execute("PRAGMA journal_mode=WAL")
        real.execute("PRAGMA busy_timeout=3000")
        return _BoomConn(real, boom_at)
    return _f


def test_return_create_error_does_not_lock_db(monkeypatch):
    """actions3.return_create 쓰기 도중 오류 주입 → 이후 쓰기 미잠금."""
    path = _make_db()
    holder = []
    try:
        import backend.api.actions3 as a3

        def _factory():
            f = _boom_factory(path, boom_at=3)()   # SELECT(1) → UPDATE inv(2) → UPDATE tonbag(3) BOOM
            holder.append(f)   # GC 로 락이 가려지지 않도록 참조 유지
            return f
        monkeypatch.setattr(a3, "_db", _factory)

        r = a3.return_create({"lot_no": "LOTZ", "reason": "테스트"})
        # 오류를 err_response 로 반환(ok=False) — 그래도 연결은 닫혀야 함
        assert r.get("ok") is False, r

        assert _can_write_now(path) is True, "오류 후 DB가 잠김 — 연결이 안 닫혔다"
    finally:
        _cleanup(path)
