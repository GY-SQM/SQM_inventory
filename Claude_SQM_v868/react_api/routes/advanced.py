# -*- coding: utf-8 -*-
"""Advanced API — 출고 ���력, LOT 상태 흐름, 톤백 이력."""
from typing import Optional
from fastapi import APIRouter, Query

from react_api.utils.db import get_db, now_str

router = APIRouter(prefix="/api/advanced", tags=["advanced"])


@router.get("/outbound-history")
def outbound_history(
    lot_no: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """출고 이력 조회."""
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
            SELECT s.lot_no, s.tonbag_uid, s.picking_no, s.customer,
                   s.sold_qty_kg, s.sold_qty_mt, s.status, s.delivery_date,
                   i.product_name, i.sap_no
            FROM sold_table s
            LEFT JOIN inventory i ON s.lot_no = i.lot_no
            {where}
            ORDER BY s.delivery_date DESC
            LIMIT ?
        """, tuple(params) + (limit,))

        result = []
        for row in rows:
            if isinstance(row, dict):
                result.append(row)
            else:
                result.append({
                    'lot_no': row[0], 'tonbag_uid': row[1], 'picking_no': row[2],
                    'customer': row[3], 'sold_qty_kg': row[4], 'sold_qty_mt': row[5],
                    'status': row[6], 'delivery_date': row[7],
                    'product_name': row[8], 'sap_no': row[9],
                })
        return {'rows': result, 'total': len(result), 'generated_at': now_str()}


@router.get("/lot-status-flow/{lot_no}")
def lot_status_flow(lot_no: str):
    """LOT의 톤백 상태 분포 + 시간별 흐���."""
    with get_db() as db:
        # 상태별 분포
        dist = db.fetchall("""
            SELECT status, COUNT(*) as cnt, SUM(weight) as total_kg
            FROM inventory_tonbag
            WHERE lot_no = ?
            GROUP BY status
        """, (lot_no,))

        status_dist = []
        for row in dist:
            if isinstance(row, dict):
                status_dist.append(row)
            else:
                status_dist.append({'status': row[0], 'count': row[1], 'total_kg': row[2]})

        # audit 이력
        audit = db.fetchall("""
            SELECT event_type, event_data, created_at
            FROM audit_log
            WHERE event_data LIKE ?
            ORDER BY created_at DESC
            LIMIT 20
        """, (f"%{lot_no}%",))

        audit_rows = []
        for row in audit:
            if isinstance(row, dict):
                audit_rows.append(row)
            else:
                audit_rows.append({'event_type': row[0], 'event_data': row[1], 'created_at': row[2]})

        return {
            'lot_no': lot_no,
            'status_distribution': status_dist,
            'audit_trail': audit_rows,
            'generated_at': now_str(),
        }


@router.get("/allocation-summary")
def allocation_summary():
    """배정 요약: 상태별 통계."""
    with get_db() as db:
        rows = db.fetchall("""
            SELECT status, COUNT(*) as cnt,
                   SUM(COALESCE(qty_mt, 0)) as total_mt
            FROM allocation_plan
            GROUP BY status
            ORDER BY cnt DESC
        """)
        result = []
        for row in rows:
            if isinstance(row, dict):
                result.append(row)
            else:
                result.append({'status': row[0], 'count': row[1], 'total_mt': row[2]})
        return {'rows': result, 'generated_at': now_str()}


@router.get("/weight-summary")
def weight_summary():
    """중량 요약: 제품별 상태별 중량."""
    with get_db() as db:
        rows = db.fetchall("""
            SELECT i.product_name, t.status,
                   COUNT(t.id) as bag_count,
                   SUM(t.weight) as total_kg
            FROM inventory_tonbag t
            JOIN inventory i ON t.lot_no = i.lot_no
            WHERE COALESCE(t.is_sample, 0) = 0
            GROUP BY i.product_name, t.status
            ORDER BY i.product_name, t.status
        """)
        result = []
        for row in rows:
            if isinstance(row, dict):
                result.append(row)
            else:
                result.append({
                    'product_name': row[0], 'status': row[1],
                    'bag_count': row[2], 'total_kg': row[3],
                })
        return {'rows': result, 'generated_at': now_str()}
