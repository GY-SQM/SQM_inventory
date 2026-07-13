# -*- coding: utf-8 -*-
"""[감사 M3] 배정 엔드포인트가 '오류가 나도 연결을 닫아' DB 락을 남기지 않는지 검증.

수정 전: raw 연결을 오류 경로에서 close 못 해 커밋 안 된 쓰기 연결이 남음 →
  SQLite(WAL)에서 다음 쓰기가 'database is locked' 로 잠김.
수정 후: with db_session(...) 로 예외 시에도 rollback+close 보장 → 다음 쓰기 정상.
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
    """N번째 execute 에서 예외를 던지는 연결 프록시(그 외는 실제 연결로 위임).
    쓰기가 한 번 성공한 뒤(=쓰기 트랜잭션 오픈) 예외를 내 '누수 시 락' 상황을 재현."""
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
        return getattr(self._real, name)   # commit/rollback/close/row_factory 등 위임


def _make_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    eng = SQMInventoryEngineV3(db_path=path)   # 스키마 생성
    db = eng.db
    db.execute("INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
               "picked_weight, mxbg_pallet, status) VALUES ('LOTX','P',1000,0,1000,1,'RESERVED')")
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, is_sample, status) "
               "SELECT id,'LOTX',1,1000,0,'RESERVED' FROM inventory WHERE lot_no='LOTX'")
    db.execute("INSERT INTO allocation_plan (lot_no, status) VALUES ('LOTX','RESERVED')")
    eng.close()   # 엔진 연결 해제 — 이후 락은 오직 엔드포인트 연결 때문
    return path


def _cleanup(path):
    for p in (path, path + "-wal", path + "-shm"):
        try:
            os.remove(p)
        except OSError:
            pass


def _can_write_now(path):
    """새 연결로 즉시 쓰기가 되는지(=락 없음). 짧은 timeout 으로 잠기면 빠르게 실패."""
    c = sqlite3.connect(path, timeout=1.0)
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("BEGIN IMMEDIATE")
        c.execute("UPDATE inventory SET updated_at=datetime('now') WHERE lot_no='LOTX'")
        c.commit()
        return True
    except sqlite3.OperationalError as e:
        return False if "locked" in str(e).lower() else True
    finally:
        c.close()


def test_reset_all_error_does_not_lock_db(monkeypatch):
    path = _make_db()
    try:
        import backend.api.allocation_api as aa

        real_holder = {}

        def _boom_factory():
            real = sqlite3.connect(path, timeout=5, check_same_thread=False)
            real.row_factory = sqlite3.Row
            real.execute("PRAGMA journal_mode=WAL")
            real.execute("PRAGMA busy_timeout=3000")
            # SELECT(1) → UPDATE allocation_plan(2, 쓰기 성공=락 오픈) → UPDATE inventory(3) BOOM
            bc = _BoomConn(real, boom_at=3)
            real_holder["real"] = real
            return bc

        monkeypatch.setattr(aa, "_alloc_db", _boom_factory)

        # 엔드포인트 실행 → 주입 오류로 실패(HTTPException 500)
        with pytest.raises(HTTPException):
            aa.reset_all_allocations()

        # 핵심: 오류가 났어도 연결이 닫혀 다음 쓰기가 잠기지 않아야 함
        assert _can_write_now(path) is True, "오류 후 DB가 잠김 — 연결이 안 닫혔다"
    finally:
        _cleanup(path)
