# -*- coding: utf-8 -*-
import sqlite3

from repositories.base_repository import BaseRepository

def test_transaction_commit():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    repo = BaseRepository(conn)

    with repo.transaction():
        repo.execute("INSERT INTO t (name) VALUES (?)", ("A",))

    row = conn.execute("SELECT COUNT(*) FROM t").fetchone()
    assert row[0] == 1
