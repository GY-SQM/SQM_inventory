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
