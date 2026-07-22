# -*- coding: utf-8 -*-
"""
backend/api/db_allowed_stats.py
================================
SQM v9.0.2 — GET endpoint for central allowlist 모니터링 조회

GET /api/admin/db-allowed/stats
    → validate() 호출 통계 (in-memory)
    → { total_calls, allowed, blocked, by_kind }

frontend dashboard 또는 운영 모니터링에서 호출.
v9.0.2 Step 1.
"""
from fastapi import APIRouter
from core.db_allowed import stats_detailed, _VALIDATE_COUNTS

router = APIRouter(prefix="/api/admin/db-allowed", tags=["admin"])


@router.get("/stats", summary="central allowlist validate() 호출 통계 (in-memory)")
def get_db_allowed_stats():
    """
    validate() 호출 통계 조회.

    Returns:
        {
            "total_calls": int,
            "allowed": int,
            "blocked": int,
            "by_kind": {kind: {"allowed": int, "blocked": int}, ...}
        }
    """
    s = stats_detailed()
    # 내부 카운트 dict도 함께 노출 (frontend에서 디버깅용)
    s["raw_counts"] = {
        f"{area}|{kind}|{result}": count
        for (area, kind, result), count in _VALIDATE_COUNTS.items()
    }
    return {"ok": True, "data": s}
