# -*- coding: utf-8 -*-
"""
P2-C-02 — BaseRepository: 프로젝트 공통 DB 접근 기반 클래스.
모든 repository는 이 클래스를 상속하여 일관된 DB 접근 및 트랜잭션 관리를 보장한다.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)


class BaseRepository:
    """프로젝트 공통 DB 접근 기반 클래스.

    사용법:
        class MyRepo(BaseRepository):
            def get_items(self):
                return self.fetchall("SELECT * FROM items")

            def save_item(self, name):
                with self.transaction():
                    self.execute("INSERT INTO items (name) VALUES (?)", (name,))
    """

    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None):
        """SQL 실행 후 cursor 반환."""
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params or ()))
        return cur

    def fetchone(self, sql: str, params: Optional[Iterable[Any]] = None):
        """단일 행 조회."""
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: Optional[Iterable[Any]] = None):
        """전체 행 조회."""
        return self.execute(sql, params).fetchall()

    @contextmanager
    def transaction(self):
        """트랜잭션 컨텍스트 매니저. 성공 시 commit, 실패 시 rollback."""
        try:
            yield self
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
