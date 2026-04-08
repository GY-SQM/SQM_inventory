# -*- coding: utf-8 -*-
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Optional

class BaseRepository:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None):
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params or ()))
        return cur

    def fetchone(self, sql: str, params: Optional[Iterable[Any]] = None):
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: Optional[Iterable[Any]] = None):
        return self.execute(sql, params).fetchall()

    @contextmanager
    def transaction(self):
        try:
            yield self
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
