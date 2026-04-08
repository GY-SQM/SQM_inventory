# -*- coding: utf-8 -*-
"""Audit log 유틸리티 — react_api 전용."""
import json
import logging
from typing import Any, Dict, Optional

from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)


def write_audit_log(
    event_type: str,
    event_data: Optional[Dict[str, Any]] = None,
    created_by: str = "system",
) -> bool:
    """audit_log 테이블에 이벤트 기록."""
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO audit_log (event_type, event_data, created_by, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    event_type,
                    json.dumps(event_data or {}, ensure_ascii=False),
                    created_by,
                    now_str(),
                ),
            )
            db.conn.commit()
        return True
    except Exception as e:
        logger.error("audit_log 기록 실패: %s", e, exc_info=True)
        return False
