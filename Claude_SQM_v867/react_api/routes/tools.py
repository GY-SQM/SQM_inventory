# -*- coding: utf-8 -*-
"""도구 API — Excel 내보내기, 정합성 체크."""
import io
import csv
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("/export/csv")
def export_csv(
    status: Optional[str] = Query(None),
    product_name: Optional[str] = Query(None),
):
    """재고 데이터를 CSV로 내보내기."""
    with get_db() as db:
        conditions = []
        params = []
        if status:
            conditions.append("t.status = ?")
            params.append(status.upper())
        if product_name:
            conditions.append("i.product_name = ?")
            params.append(product_name)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT t.lot_no, t.tonbag_uid, t.tonbag_no, t.sub_lt,
                   i.product_name, i.sap_no, i.bl_no,
                   t.status, t.location, t.weight,
                   i.inbound_date, i.container_no
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON t.lot_no = i.lot_no
            {where}
            ORDER BY t.lot_no, t.sub_lt
        """
        rows = db.fetchall(sql, tuple(params))

    headers = [
        'LOT_NO', 'TONBAG_UID', 'TONBAG_NO', 'SUB_LT',
        'PRODUCT', 'SAP_NO', 'BL_NO',
        'STATUS', 'LOCATION', 'WEIGHT_KG',
        'INBOUND_DATE', 'CONTAINER_NO',
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        if isinstance(row, dict):
            writer.writerow([row.get(h.lower(), '') for h in headers])
        else:
            writer.writerow(row)

    output.seek(0)
    filename = f"sqm_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/integrity-check")
def integrity_check():
    """DB 정합성 체크: 재고 무결성 확인."""
    with get_db() as db:
        issues = []

        # 1. inventory_tonbag에는 있지만 inventory에 없는 LOT
        orphan_tonbags = db.fetchall("""
            SELECT DISTINCT t.lot_no
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON t.lot_no = i.lot_no
            WHERE i.lot_no IS NULL
        """)
        if orphan_tonbags:
            lots = [r['lot_no'] if isinstance(r, dict) else r[0] for r in orphan_tonbags]
            issues.append({
                'type': 'ORPHAN_TONBAG',
                'severity': 'ERROR',
                'message': f'inventory에 없는 LOT의 톤백 {len(lots)}건',
                'details': lots[:20],
            })

        # 2. 상태 불일치: inventory.status vs 톤백 다수 상태
        status_mismatch = db.fetchall("""
            SELECT i.lot_no, i.status as inv_status,
                   GROUP_CONCAT(DISTINCT t.status) as tonbag_statuses,
                   COUNT(t.id) as bag_count
            FROM inventory i
            JOIN inventory_tonbag t ON i.lot_no = t.lot_no
            GROUP BY i.lot_no
            HAVING COUNT(DISTINCT t.status) > 2
        """)
        if status_mismatch:
            for row in status_mismatch:
                if isinstance(row, dict):
                    issues.append({
                        'type': 'STATUS_MISMATCH',
                        'severity': 'WARNING',
                        'message': f"LOT {row['lot_no']}: inventory={row['inv_status']}, tonbags={row['tonbag_statuses']}",
                    })

        # 3. 중량 합계 불일치
        weight_mismatch = db.fetchall("""
            SELECT i.lot_no, i.current_weight,
                   SUM(CASE WHEN t.status IN ('AVAILABLE','RESERVED') AND COALESCE(t.is_sample,0)=0 THEN t.weight ELSE 0 END) as calc_weight
            FROM inventory i
            JOIN inventory_tonbag t ON i.lot_no = t.lot_no
            GROUP BY i.lot_no
            HAVING ABS(COALESCE(i.current_weight,0) - calc_weight) > 1.0
        """)
        if weight_mismatch:
            for row in weight_mismatch[:10]:
                if isinstance(row, dict):
                    issues.append({
                        'type': 'WEIGHT_MISMATCH',
                        'severity': 'WARNING',
                        'message': f"LOT {row['lot_no']}: recorded={row['current_weight']}, calculated={row['calc_weight']}",
                    })

        return {
            'success': True,
            'total_issues': len(issues),
            'issues': issues,
            'generated_at': now_str(),
        }
