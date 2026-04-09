# -*- coding: utf-8 -*-
"""Advanced API — 출고 이력, LOT 상태 흐름, 톤백 이력."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/advanced", tags=["advanced"])


@router.get("/outbound-history")
def outbound_history(
    lot_no: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """출고 이력 조회."""
    try:
        with get_db() as db:
            conditions = []
            params = []
            if lot_no:
                conditions.append("s.lot_no = ?")
                params.append(lot_no)
            if customer:
                conditions.append("s.customer LIKE ?")
                params.append(f"%{customer}%")
            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            rows = db.fetchall(f"""
                SELECT s.lot_no, COALESCE(s.tonbag_uid,'') AS tonbag_uid,
                       COALESCE(s.picking_no,'') AS picking_no,
                       COALESCE(s.customer,'') AS customer,
                       COALESCE(s.sold_qty_kg,0) AS sold_qty_kg,
                       COALESCE(s.sold_qty_mt,0) AS sold_qty_mt,
                       COALESCE(s.status,'') AS status, s.delivery_date,
                       COALESCE(i.product,'') AS product,
                       COALESCE(i.sap_no,'') AS sap_no
                FROM sold_table s
                LEFT JOIN inventory i ON s.lot_no = i.lot_no
                {where}
                ORDER BY s.delivery_date DESC
                LIMIT ?
            """, tuple(params) + (limit,))
            return {'rows': rows or [], 'total': len(rows or []), 'generated_at': now_str()}
    except Exception as exc:
        logger.error("outbound_history 실패: %s", exc, exc_info=True)
        raise HTTPException(500, "출고 이력 조회 실패")


@router.get("/lot-status-flow/{lot_no}")
def lot_status_flow(lot_no: str):
    """LOT의 톤백 상태 분포 + 시간별 흐름."""
    try:
        with get_db() as db:
            dist = db.fetchall("""
                SELECT COALESCE(status,'') AS status, COUNT(*) AS cnt,
                       COALESCE(SUM(COALESCE(weight,0)),0) AS total_kg
                FROM inventory_tonbag
                WHERE lot_no = ?
                GROUP BY status
            """, (lot_no,))

            audit = db.fetchall("""
                SELECT COALESCE(event_type,'') AS event_type,
                       COALESCE(event_data,'') AS event_data, created_at
                FROM audit_log
                WHERE event_data LIKE ?
                ORDER BY created_at DESC
                LIMIT 20
            """, (f"%{lot_no}%",))

            return {
                'lot_no': lot_no,
                'status_distribution': dist or [],
                'audit_trail': audit or [],
                'generated_at': now_str(),
            }
    except Exception as exc:
        logger.error("lot_status_flow 실패: %s", exc, exc_info=True)
        raise HTTPException(500, "LOT 상태 흐름 조회 실패")


@router.get("/allocation-summary")
def allocation_summary():
    """배정 요약: 상태별 통계."""
    try:
        with get_db() as db:
            rows = db.fetchall("""
                SELECT COALESCE(status,'') AS status, COUNT(*) AS cnt,
                       COALESCE(SUM(COALESCE(qty_mt, 0)),0) AS total_mt
                FROM allocation_plan
                GROUP BY status
                ORDER BY cnt DESC
            """)
            return {'rows': rows or [], 'generated_at': now_str()}
    except Exception as exc:
        logger.error("allocation_summary 실패: %s", exc, exc_info=True)
        raise HTTPException(500, "배정 요약 조회 실패")


@router.get("/weight-summary")
def weight_summary():
    """중량 요약: 제품별 상태별 중량."""
    try:
        with get_db() as db:
            rows = db.fetchall("""
                SELECT COALESCE(i.product,'') AS product,
                       COALESCE(t.status,'') AS status,
                       COUNT(t.id) AS bag_count,
                       COALESCE(SUM(COALESCE(t.weight,0)),0) AS total_kg
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON t.lot_no = i.lot_no
                WHERE COALESCE(t.is_sample, 0) = 0
                GROUP BY i.product, t.status
                ORDER BY i.product, t.status
            """)
            return {'rows': rows or [], 'generated_at': now_str()}
    except Exception as exc:
        logger.error("weight_summary 실패: %s", exc, exc_info=True)
        raise HTTPException(500, "중량 요약 조회 실패")
