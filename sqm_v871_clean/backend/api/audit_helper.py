"""
SQM 공통 감사 로그 헬퍼 (Phase 2-2)
모든 CRUD 작업에서 audit_log 테이블에 일관된 방식으로 기록.
"""
import json
import logging
import sqlite3
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

_ENSURE_SQL = """
    CREATE TABLE IF NOT EXISTS audit_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type  TEXT NOT NULL,
        event_data  TEXT,
        batch_id    TEXT,
        tonbag_id   TEXT,
        user_note   TEXT,
        created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        created_by  TEXT DEFAULT 'WEBVIEW'
    )
"""

_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS idx_audit_event
    ON audit_log(event_type, created_at)
"""


def write_audit(
    db_path: str,
    event_type: str,
    *,
    table_name: str = "",
    record_id: Any = None,
    old_value: Any = None,
    new_value: Any = None,
    extra: Optional[dict] = None,
    user_note: str = "",
    created_by: str = "WEBVIEW",
) -> None:
    """
    audit_log 테이블에 이벤트 기록.
    실패해도 예외를 상위로 전파하지 않음 — 감사 로그 오류가 업무 흐름을 막지 않음.

    event_data JSON 구조:
        {
          "table_name": "inventory",
          "record_id":  "LOT-001",
          "old_value":  {...} 또는 단순 값,
          "new_value":  {...} 또는 단순 값,
          "extra":      {...}  기타 컨텍스트
        }
    """
    try:
        payload: dict = {}
        if table_name:
            payload["table_name"] = table_name
        if record_id is not None:
            payload["record_id"] = record_id
        if old_value is not None:
            payload["old_value"] = old_value
        if new_value is not None:
            payload["new_value"] = new_value
        if extra:
            payload.update(extra)

        data_str = json.dumps(payload, ensure_ascii=False, default=str)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        from backend.api.db_helper import get_db_connection
        con = get_db_connection(db_path, timeout=5, retries=3)
        con.execute(_ENSURE_SQL)
        con.execute(_INDEX_SQL)
        con.execute(
            """
            INSERT INTO audit_log
                (event_type, event_data, user_note, created_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_type, data_str, user_note or "", created_by, now),
        )
        con.commit()
        con.close()
    except Exception as e:
        logger.warning(f"[audit_helper] 감사 로그 기록 실패 (무시): {e}")
