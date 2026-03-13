# -*- coding: utf-8 -*-
"""
SQM v7.3.2 — DB Helper
========================
스캔/출고 Mixin용 공통 DB 접근 헬퍼.
기존 engine과 독립적으로 sqlite3 직접 접근 가능.
"""
import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_DEFAULT_DB = 'data/db/sqm_inventory.db'

# 필요한 테이블 자동 생성
_ENSURE_TABLES_SQL = [
    """CREATE TABLE IF NOT EXISTS audit_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT,
        event_type  TEXT,
        lot_no      TEXT,
        detail      TEXT,
        event_data  TEXT,
        batch_id    TEXT,
        tonbag_id   TEXT,
        user_note   TEXT,
        created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        created_by  TEXT DEFAULT 'SQM'
    )""",
    """CREATE INDEX IF NOT EXISTS idx_audit_action
       ON audit_log(action_type, created_at)""",
    """CREATE TABLE IF NOT EXISTS outbound_scan_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        lot_no      TEXT,
        tonbag_uid  TEXT,
        scan_time   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        status      TEXT,
        weight_kg   REAL DEFAULT 0,
        is_undone   INTEGER DEFAULT 0
    )""",
    """CREATE INDEX IF NOT EXISTS idx_scan_lot
       ON outbound_scan_log(lot_no, scan_time)""",
]


def get_db_path(app) -> str:
    """앱 객체에서 DB 경로 추출."""
    path = getattr(app, 'db_path', None)
    return path if path else _DEFAULT_DB


@contextmanager
def get_conn(app):
    """sqlite3 연결을 context manager로 제공. Row factory 자동 설정."""
    db_path = get_db_path(app)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def ensure_tables(app):
    """필요한 테이블이 없으면 자동 생성."""
    try:
        with get_conn(app) as conn:
            for sql in _ENSURE_TABLES_SQL:
                conn.execute(sql)
            conn.commit()
            logger.debug("[db_helper] audit_log, outbound_scan_log 테이블 확인 완료")
    except Exception as e:
        logger.warning(f"[db_helper] 테이블 생성 실패: {e}")


def fetchone(app, sql, params=()):
    """단일 행 조회. dict 반환."""
    try:
        with get_conn(app) as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"[db_helper] fetchone 오류: {e}")
        return None


def fetchall(app, sql, params=()):
    """다수 행 조회. list[dict] 반환."""
    try:
        with get_conn(app) as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"[db_helper] fetchall 오류: {e}")
        return []


def execute(app, sql, params=()):
    """단일 실행 + commit."""
    try:
        with get_conn(app) as conn:
            conn.execute(sql, params)
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"[db_helper] execute 오류: {e}")
        return False
