# -*- coding: utf-8 -*-
"""AI Dashboard API — 분석/차트 데이터/인사이트."""
from fastapi import APIRouter

from react_api.utils.db import get_db, now_str

router = APIRouter(prefix="/api/ai", tags=["ai-dashboard"])


@router.get("/insights")
def get_insights():
    """재고 인사이트 자동 생성."""
    with get_db() as db:
        insights = []

        # 1. 장기 체류 재고
        long_stay = db.fetchall("""
            SELECT lot_no, product_name, inbound_date,
                   julianday('now') - julianday(inbound_date) as days_stayed
            FROM inventory
            WHERE status = 'AVAILABLE' AND inbound_date IS NOT NULL
            AND julianday('now') - julianday(inbound_date) > 90
            ORDER BY days_stayed DESC
            LIMIT 5
        """)
        if long_stay:
            for row in long_stay:
                if isinstance(row, dict):
                    insights.append({
                        'type': 'LONG_STAY',
                        'severity': 'warning',
                        'message': f"LOT {row['lot_no']} ({row['product_name']}): {int(row.get('days_stayed', 0))}일 체류",
                    })

        # 2. 제품별 재고 편중
        product_skew = db.fetchall("""
            SELECT i.product_name,
                   SUM(CASE WHEN t.status = 'AVAILABLE' THEN t.weight ELSE 0 END) as avail_kg,
                   SUM(t.weight) as total_kg
            FROM inventory_tonbag t
            JOIN inventory i ON t.lot_no = i.lot_no
            WHERE COALESCE(t.is_sample, 0) = 0
            GROUP BY i.product_name
            HAVING total_kg > 0
            ORDER BY avail_kg DESC
        """)
        if product_skew:
            total_all = sum(
                (r.get('avail_kg', 0) if isinstance(r, dict) else r[1]) or 0
                for r in product_skew
            )
            if total_all > 0:
                for row in product_skew:
                    avail = (row.get('avail_kg', 0) if isinstance(row, dict) else row[1]) or 0
                    pct = (avail / total_all) * 100
                    if pct > 40:
                        pname = row.get('product_name', '') if isinstance(row, dict) else row[0]
                        insights.append({
                            'type': 'PRODUCT_SKEW',
                            'severity': 'info',
                            'message': f"{pname}: 가용 재고의 {pct:.1f}% 차지 ({avail/1000:.1f} MT)",
                        })

        # 3. 출고 대기 과다
        pending = db.fetchall("""
            SELECT COUNT(*) as cnt FROM inventory_tonbag WHERE status = 'PICKED'
        """)
        if pending:
            cnt = pending[0].get('cnt', 0) if isinstance(pending[0], dict) else pending[0][0]
            if cnt > 50:
                insights.append({
                    'type': 'PICKED_BACKLOG',
                    'severity': 'warning',
                    'message': f"PICKED 상태 톤백 {cnt}개 — 출고 완료 필요",
                })

        return {
            'insights': insights,
            'total': len(insights),
            'generated_at': now_str(),
        }


@router.get("/chart/status-pie")
def chart_status_pie():
    """상태별 원형 차트 데이터."""
    with get_db() as db:
        rows = db.fetchall("""
            SELECT status, COUNT(*) as cnt, SUM(weight) as total_kg
            FROM inventory_tonbag
            WHERE COALESCE(is_sample, 0) = 0
            GROUP BY status
            ORDER BY cnt DESC
        """)
        data = []
        for row in rows:
            if isinstance(row, dict):
                data.append({'label': row['status'], 'count': row['cnt'], 'weight_kg': row['total_kg']})
            else:
                data.append({'label': row[0], 'count': row[1], 'weight_kg': row[2]})
        return {'data': data, 'generated_at': now_str()}


@router.get("/chart/inbound-trend")
def chart_inbound_trend():
    """월별 입고 추이 데이터."""
    with get_db() as db:
        rows = db.fetchall("""
            SELECT strftime('%Y-%m', inbound_date) as month,
                   COUNT(*) as lot_count,
                   SUM(current_weight) as total_kg
            FROM inventory
            WHERE inbound_date IS NOT NULL
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """)
        data = []
        for row in rows:
            if isinstance(row, dict):
                data.append({'month': row['month'], 'lots': row['lot_count'], 'weight_kg': row['total_kg']})
            else:
                data.append({'month': row[0], 'lots': row[1], 'weight_kg': row[2]})
        data.reverse()
        return {'data': data, 'generated_at': now_str()}
