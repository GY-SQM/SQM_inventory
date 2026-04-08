# -*- coding: utf-8 -*-
"""Return 조회 서비스 — return_history 테이블 조회 + 통계."""
import logging
from typing import Any, Dict, List, Optional

from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)


def get_return_history(
    lot_no: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict[str, Any]:
    """return_history 테이블 페이지 조회."""
    with get_db() as db:
        conditions: List[str] = ["1=1"]
        params: List[Any] = []

        if lot_no:
            conditions.append("r.lot_no LIKE ?")
            params.append(f"%{lot_no}%")
        if start_date:
            conditions.append("r.return_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("r.return_date <= ?")
            params.append(end_date)

        where_sql = " AND ".join(conditions)
        offset = (page - 1) * page_size

        total_row = db.fetchone(
            f"SELECT COUNT(*) AS total FROM return_history r WHERE {where_sql}",
            tuple(params),
        )
        total = int((total_row or {}).get("total") or 0)

        rows = db.fetchall(
            f"SELECT r.id, r.lot_no, r.sub_lt, "
            f"r.return_date, "
            f"COALESCE(r.original_customer, '') AS original_customer, "
            f"COALESCE(r.original_sale_ref, '') AS original_sale_ref, "
            f"COALESCE(r.reason, '') AS reason, "
            f"COALESCE(r.remark, '') AS remark, "
            f"COALESCE(r.weight_kg, 0) AS weight_kg, "
            f"r.created_at, "
            f"COALESCE(i.product, '') AS product, "
            f"COALESCE(i.sap_no, '') AS sap_no "
            f"FROM return_history r "
            f"LEFT JOIN inventory i ON i.lot_no = r.lot_no "
            f"WHERE {where_sql} "
            f"ORDER BY r.id DESC LIMIT ? OFFSET ?",
            tuple(params + [page_size, offset]),
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "rows": rows or [],
            "generated_at": now_str(),
        }


def get_return_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """반품 통계 — 사유별/월별 집계."""
    with get_db() as db:
        conditions: List[str] = ["1=1"]
        params: List[Any] = []

        if start_date:
            conditions.append("return_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("return_date <= ?")
            params.append(end_date)

        where_sql = " AND ".join(conditions)

        # 전체 요약
        summary_row = db.fetchone(
            f"SELECT COUNT(*) AS total_count, "
            f"COALESCE(SUM(COALESCE(weight_kg, 0)), 0) AS total_weight_kg "
            f"FROM return_history WHERE {where_sql}",
            tuple(params),
        )

        # 사유별 집계
        by_reason = db.fetchall(
            f"SELECT COALESCE(reason, '기타') AS reason, "
            f"COUNT(*) AS count, "
            f"COALESCE(SUM(COALESCE(weight_kg, 0)), 0) AS weight_kg "
            f"FROM return_history WHERE {where_sql} "
            f"GROUP BY COALESCE(reason, '기타') ORDER BY count DESC",
            tuple(params),
        )

        # 월별 집계
        by_month = db.fetchall(
            f"SELECT strftime('%Y-%m', return_date) AS month, "
            f"COUNT(*) AS count, "
            f"COALESCE(SUM(COALESCE(weight_kg, 0)), 0) AS weight_kg "
            f"FROM return_history WHERE {where_sql} "
            f"GROUP BY strftime('%Y-%m', return_date) "
            f"ORDER BY month DESC LIMIT 12",
            tuple(params),
        )

        return {
            "total_count": int((summary_row or {}).get("total_count") or 0),
            "total_weight_kg": round(float((summary_row or {}).get("total_weight_kg") or 0), 3),
            "by_reason": by_reason or [],
            "by_month": by_month or [],
            "generated_at": now_str(),
        }
