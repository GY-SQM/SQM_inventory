# -*- coding: utf-8 -*-
"""P2-C-02 — BaseRepository 테스트."""
import sqlite3
import pytest
from features.repositories.base_repository import BaseRepository


def test_import():
    assert BaseRepository is not None


def test_execute_and_fetch():
    conn = sqlite3.connect(":memory:")
    repo = BaseRepository(conn)
    repo.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    repo.execute("INSERT INTO t (id, name) VALUES (?, ?)", (1, "Alice"))
    row = repo.fetchone("SELECT name FROM t WHERE id = ?", (1,))
    assert row[0] == "Alice"


def test_fetchall():
    conn = sqlite3.connect(":memory:")
    repo = BaseRepository(conn)
    repo.execute("CREATE TABLE t (id INTEGER)")
    repo.execute("INSERT INTO t VALUES (1)")
    repo.execute("INSERT INTO t VALUES (2)")
    rows = repo.fetchall("SELECT * FROM t ORDER BY id")
    assert len(rows) == 2


def test_transaction_commit():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    repo = BaseRepository(conn)

    with repo.transaction():
        repo.execute("INSERT INTO t (name) VALUES (?)", ("A",))

    row = conn.execute("SELECT COUNT(*) FROM t").fetchone()
    assert row[0] == 1


def test_transaction_rollback():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    repo = BaseRepository(conn)

    with pytest.raises(ValueError):
        with repo.transaction():
            repo.execute("INSERT INTO t (name) VALUES (?)", ("A",))
            raise ValueError("test rollback")

    row = conn.execute("SELECT COUNT(*) FROM t").fetchone()
    assert row[0] == 0
