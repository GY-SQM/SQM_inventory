# -*- coding: utf-8 -*-
"""[감사 M3 확장] db_session 컨텍스트 매니저 단위 테스트.

보장: 정상 종료 → commit+close / 예외 → rollback+close(+재전파). 어느 경우든 연결이
닫혀 DB 락을 남기지 않는다.
"""
import os
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.api.db_session import db_session


@pytest.fixture()
def dbpath():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    con.commit()
    con.close()
    yield path
    for p in (path, path + "-wal", path + "-shm"):
        try:
            os.remove(p)
        except OSError:
            pass


def _factory(path):
    def _f():
        c = sqlite3.connect(path, timeout=5, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c
    return _f


def _count(path):
    c = sqlite3.connect(path)
    try:
        return c.execute("SELECT COUNT(*) FROM t").fetchone()[0]
    finally:
        c.close()


def _is_closed(con):
    try:
        con.execute("SELECT 1")
        return False
    except sqlite3.ProgrammingError:
        return True


def test_normal_commits_and_closes(dbpath):
    with db_session(_factory(dbpath)) as con:
        con.execute("INSERT INTO t (v) VALUES ('a')")
    assert _count(dbpath) == 1, "정상 종료 시 자동 commit"
    assert _is_closed(con), "연결이 닫혀야 함"


def test_exception_rolls_back_and_closes(dbpath):
    with pytest.raises(ValueError):
        with db_session(_factory(dbpath)) as con:
            con.execute("INSERT INTO t (v) VALUES ('b')")
            raise ValueError("boom")
    assert _count(dbpath) == 0, "예외 시 rollback — 데이터 미반영"
    assert _is_closed(con), "예외에도 연결이 닫혀야 함(락 방지)"


def test_readonly_does_not_commit(dbpath):
    with db_session(_factory(dbpath), readonly=True) as con:
        con.execute("INSERT INTO t (v) VALUES ('c')")
    assert _count(dbpath) == 0, "readonly 는 commit 안 함"
    assert _is_closed(con)


def test_path_source_works(dbpath):
    with db_session(dbpath) as con:
        con.execute("INSERT INTO t (v) VALUES ('d')")
    assert _count(dbpath) == 1
    assert _is_closed(con)


def test_no_lock_after_error(dbpath):
    """핵심: 예외로 끝난 직후에도 다음 쓰기가 잠기지 않는다."""
    with pytest.raises(RuntimeError):
        with db_session(_factory(dbpath)) as con:
            con.execute("INSERT INTO t (v) VALUES ('x')")   # 미커밋 쓰기 도중 예외
            raise RuntimeError("mid-write error")
    # 곧바로 다른 연결로 쓰기 — database is locked 없이 성공해야 함
    with db_session(_factory(dbpath)) as con2:
        con2.execute("INSERT INTO t (v) VALUES ('y')")
    assert _count(dbpath) == 1
