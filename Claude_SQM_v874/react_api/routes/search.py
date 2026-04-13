# -*- coding: utf-8 -*-
"""통합 검색 API — 키워드/기간/상태 통합 검색."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from react_api.utils.db import get_db, now_str

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/unified")
def unified_search(
    keyword: Optional[str] = Query(None, description="키워드 (LOT, SAP, BL, 제품명 등)"),
    status: Optional[str] = Query(None, description="상태 필터"),
    date_from: Optional[str] = Query(None, description="시작일 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="종료일 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """통합 검색: inventory + inventory_tonbag + allocation_plan 교차 검색."""
    try:
        with get_db() as db:
            conditions = []
            params = []

            if keyword:
                kw = f"%{keyword}%"
                conditions.append("""(
                    t.lot_no LIKE ? OR t.tonbag_uid LIKE ? OR t.tonbag_no LIKE ?
                    OR i.product_name LIKE ? OR i.sap_no LIKE ? OR i.bl_no LIKE ?
                    OR t.location LIKE ?
                )""")
                params.extend([kw, kw, kw, kw, kw, kw, kw])

            if status:
                conditions.append("t.status = ?")
                params.append(status.upper())

            if date_from:
                conditions.append("i.inbound_date >= ?")
                params.append(date_from)

            if date_to:
                conditions.append("i.inbound_date <= ?")
                params.append(date_to)

            where = "WHERE " + " AND ".join(conditions) if conditions else ""

            count_sql = f"""
                SELECT COUNT(*) AS total FROM inventory_tonbag t
                LEFT JOIN inventory i ON t.lot_no = i.lot_no
                {where}
            """
            total_row = db.fetchone(count_sql, tuple(params))
            total = (
                total_row.get('total', 0) if total_row else 0
            )

            offset = (page - 1) * page_size
            data_sql = f"""
                SELECT t.lot_no, t.tonbag_uid, t.tonbag_no, t.sub_lt,
                       i.product_name, i.sap_no, i.bl_no,
                       t.status, t.location, t.weight,
                       i.inbound_date, i.container_no
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON t.lot_no = i.lot_no
                {where}
                ORDER BY t.lot_no, t.sub_lt
                LIMIT ? OFFSET ?
            """
            rows = db.fetchall(data_sql, tuple(params) + (page_size, offset))

            result_rows = []
            for row in rows:
                result_rows.append(row)

            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'rows': result_rows,
                'generated_at': now_str(),
            }
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("unified_search 오류: %s", exc, exc_info=True)
        raise HTTPException(500, f"검색 실패: {exc}")
