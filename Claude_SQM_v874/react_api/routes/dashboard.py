# -*- coding: utf-8 -*-
"""Dashboard 조회 라우트 — QueryCache v2 적용
배치: react_api/routes/dashboard.py (기존 덮어쓰기)
생성일: 2026-04-08
"""
import logging
from fastapi import APIRouter, HTTPException
from react_api.schemas.dashboard import (
    DashboardSummaryResponse,
    ProductSummaryResponse,
    LocationSummaryResponse,
)
from react_api.dashboard_read_service import DashboardReadService
from react_api.utils.db import get_db

# ★ QueryCache 연결 (없으면 비활성화)
try:
    from engine_modules.query_cache import cache as _cache
    _CACHE_OK = True
except ImportError:
    _cache   = None
    _CACHE_OK = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary():
    """★ 10초 캐시 적용 — 매 요청마다 DB 조회 제거"""
    if _CACHE_OK:
        cached = _cache.get("dash:summary")
        if cached is not None:
            return DashboardSummaryResponse(**cached)
    try:
        with get_db() as db:
            data = DashboardReadService(db).get_summary()
        if _CACHE_OK:
            _cache.set_realtime("dash:summary", data,
                                tables=["inventory_tonbag"])
        return DashboardSummaryResponse(**data)
    except Exception as exc:
        logger.error("dashboard_summary 실패: %s", exc, exc_info=True)
        raise HTTPException(500, "대시보드 요약 조회 실패")


@router.get("/by-product", response_model=ProductSummaryResponse)
def dashboard_by_product():
    """★ 10초 캐시 적용"""
    if _CACHE_OK:
        cached = _cache.get("dash:by_product")
        if cached is not None:
            return ProductSummaryResponse(**cached)
    try:
        with get_db() as db:
            data = DashboardReadService(db).get_by_product()
        if _CACHE_OK:
            _cache.set_realtime("dash:by_product", data,
                                tables=["inventory"])
        return ProductSummaryResponse(**data)
    except Exception as exc:
        logger.error("dashboard_by_product 실패: %s", exc, exc_info=True)
        raise HTTPException(500, "제품별 요약 조회 실패")


@router.get("/location-summary", response_model=LocationSummaryResponse)
def dashboard_location_summary():
    """★ 10초 캐시 적용"""
    if _CACHE_OK:
        cached = _cache.get("dash:location")
        if cached is not None:
            return LocationSummaryResponse(**cached)
    try:
        with get_db() as db:
            data = DashboardReadService(db).get_location_summary()
        if _CACHE_OK:
            _cache.set_realtime("dash:location", data,
                                tables=["inventory_tonbag"])
        return LocationSummaryResponse(**data)
    except Exception as exc:
        logger.error("dashboard_location_summary 실패: %s", exc, exc_info=True)
        raise HTTPException(500, "위치별 요약 조회 실패")


@router.get("/alerts")
def get_dashboard_alerts():
    """대시보드 알림 수집 — v864 동일 6가지 알림"""
    from react_api.utils.db import get_db, now_str
    alerts = []
    kpi = {"unassigned_location_count": 0, "scan_failure_rate": None, "avg_lot_age_days": 0.0}

    with get_db() as db:
        # 1. 톤백 무결성 이슈
        try:
            row = db.fetchone("""
                SELECT COUNT(DISTINCT t.lot_no) as cnt
                FROM inventory_tonbag t LEFT JOIN inventory i ON t.lot_no = i.lot_no
                WHERE i.lot_no IS NULL
            """)
            if row and row['cnt'] > 0:
                alerts.append({"icon": "🔧", "message": f"톤백 무결성 이슈 {row['cnt']}건", "severity": "warning"})
        except: pass

        # 2. 컨테이너 반납 D-3
        try:
            rows = db.fetchall("""
                SELECT lot_no, con_return FROM inventory
                WHERE con_return IS NOT NULL AND con_return != ''
                AND date(con_return) <= date('now', '+3 days')
                AND status NOT IN ('OUTBOUND', 'SOLD', 'DEPLETED')
                ORDER BY con_return ASC LIMIT 5
            """)
            for r in rows:
                alerts.append({"icon": "⏰", "message": f"{r['lot_no']}: 컨테이너 반납 D-3 이내 ({r['con_return']})", "severity": "error"})
        except: pass

        # 3. Allocation 초과
        try:
            rows = db.fetchall("""
                SELECT a.lot_no FROM allocation_plan a
                JOIN inventory i ON a.lot_no = i.lot_no
                WHERE a.status = 'RESERVED' AND a.allocated_qty > i.current_weight
                LIMIT 5
            """)
            for r in rows:
                alerts.append({"icon": "🔴", "message": f"{r['lot_no']}: Allocation 초과", "severity": "error"})
        except: pass

        # 4. 위치 미배정
        try:
            row = db.fetchone("""
                SELECT COUNT(*) as cnt FROM inventory_tonbag
                WHERE (location IS NULL OR location = '') AND status IN ('AVAILABLE', 'RESERVED')
            """)
            if row and row['cnt'] > 0:
                alerts.append({"icon": "📍", "message": f"위치 미배정 톤백 {row['cnt']}개", "severity": "warning"})
                kpi["unassigned_location_count"] = row['cnt']
        except: pass

        # 5. 부분 출고 잔류
        try:
            rows = db.fetchall("""
                SELECT DISTINCT t1.lot_no FROM inventory_tonbag t1
                WHERE t1.status = 'OUTBOUND' AND EXISTS (
                    SELECT 1 FROM inventory_tonbag t2 WHERE t2.lot_no = t1.lot_no AND t2.status = 'AVAILABLE'
                ) LIMIT 5
            """)
            for r in rows:
                alerts.append({"icon": "⚠️", "message": f"{r['lot_no']}: 부분 출고 잔류", "severity": "warning"})
        except: pass

        # 6. 예약 만료 임박
        try:
            rows = db.fetchall("""
                SELECT lot_no, created_at FROM allocation_plan
                WHERE status = 'RESERVED' AND date(created_at) < date('now', '-4 days')
                LIMIT 5
            """)
            for r in rows:
                alerts.append({"icon": "⏰", "message": f"{r['lot_no']}: 예약 만료 임박", "severity": "warning"})
        except: pass

        # KPI: 평균 재고 기간
        try:
            row = db.fetchone("""
                SELECT AVG(julianday('now') - julianday(inbound_date)) as avg_days
                FROM inventory WHERE status IN ('AVAILABLE','RESERVED') AND inbound_date IS NOT NULL
            """)
            if row and row['avg_days']:
                kpi["avg_lot_age_days"] = round(row['avg_days'], 1)
        except: pass

    return {
        "alerts": alerts,
        "total_count": len(alerts),
        "kpi_footer": kpi,
        "generated_at": now_str(),
    }
