# -*- coding: utf-8 -*-
"""Dashboard 조회 라우트."""
import logging

from fastapi import APIRouter, HTTPException
from react_api.schemas.dashboard import (
    DashboardSummaryResponse, ProductSummaryResponse, LocationSummaryResponse,
)
from react_api.dashboard_read_service import DashboardReadService
from react_api.utils.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary():
    try:
        with get_db() as db:
            service = DashboardReadService(db)
            return DashboardSummaryResponse(**service.get_summary())
    except Exception as exc:
        logger.error("dashboard_summary 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="대시보드 요약 조회 실패")


@router.get("/by-product", response_model=ProductSummaryResponse)
def dashboard_by_product():
    try:
        with get_db() as db:
            service = DashboardReadService(db)
            return ProductSummaryResponse(**service.get_by_product())
    except Exception as exc:
        logger.error("dashboard_by_product 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="제품별 요약 조회 실패")


@router.get("/location-summary", response_model=LocationSummaryResponse)
def dashboard_location_summary():
    try:
        with get_db() as db:
            service = DashboardReadService(db)
            return LocationSummaryResponse(**service.get_location_summary())
    except Exception as exc:
        logger.error("dashboard_location_summary 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="위치별 요약 조회 실패")
