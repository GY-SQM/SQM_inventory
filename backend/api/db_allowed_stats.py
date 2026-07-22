# -*- coding: utf-8 -*-
"""
backend/api/db_allowed_stats.py
================================
SQM v9.0.2~0.4 — central allowlist 모니터링 endpoint

GET /api/admin/db-allowed/stats
    → validate() 호출 통계 (in-memory)
    → { total_calls, allowed, blocked, by_kind }

GET /api/admin/db-allowed/audit?since=YYYY-MM-DD&kind=table&limit=100
    → db_allowed_audit 테이블 조회 (DB 영속 로그, v9.0.3~)
    → { rows: [{ts, area, kind, result, value}, ...] }
"""
import sqlite3
from typing import Optional

from fastapi import APIRouter, Query
import core.db_allowed as _db_allowed_mod
from core.db_allowed import stats_detailed, _VALIDATE_COUNTS, cleanup_audit

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


@router.get("/audit", summary="db_allowed_audit 로그 조회 (DB 영속, v9.0.3+)")
def get_db_allowed_audit(
    since: Optional[str] = Query(None, description="YYYY-MM-DD 형식. 예: 2026-07-22"),
    kind: Optional[str] = Query(None, description="kind 필터 (table/status/area/scope_type/lot_field/file_ext)"),
    blocked_only: bool = Query(False, description="True면 차단 시도만 (result=0)"),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    db_allowed_audit 테이블 조회 (DB 영속 로그).

    운영자가 시간대별/유형별 분석 가능.
    """
    db_path = _db_allowed_mod._get_default_db_path()
    if not db_path:
        return {"ok": False, "error": "DB 경로 없음 (테스트 환경?)", "data": {"rows": []}}

    sql = "SELECT ts, area, kind, result, value FROM db_allowed_audit WHERE 1=1"
    params: list = []

    if since:
        sql += " AND ts >= ?"
        params.append(f"{since} 00:00:00")
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    if blocked_only:
        sql += " AND result = 0"

    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    try:
        con = sqlite3.connect(db_path, timeout=5)
        try:
            rows = con.execute(sql, params).fetchall()
            return {
                "ok": True,
                "data": {
                    "rows": [
                        {"ts": ts, "area": area, "kind": kind, "result": bool(result), "value": value}
                        for ts, area, kind, result, value in rows
                    ],
                    "count": len(rows),
                    "limit": limit,
                },
            }
        finally:
            con.close()
    except sqlite3.Error as e:
        return {"ok": False, "error": str(e), "data": {"rows": []}}


@router.post("/audit/cleanup", summary="오래된 audit_log 정리 (v9.0.5+)")
def post_audit_cleanup(
    days: int = Query(30, ge=1, le=365, description="보관 기간 (일). 기본 30일."),
):
    """
    N일 이전 audit_log row 삭제.

    운영 부담 ↓ — DB 크기 자동 관리.
    기본 30일 (월 단위), 1~365일 설정 가능.
    """
    deleted = cleanup_audit(days)
    return {"ok": True, "data": {"deleted": deleted, "days": days}}
