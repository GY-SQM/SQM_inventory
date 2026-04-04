# -*- coding: utf-8 -*-
"""Dashboard 조회 라우트."""
from fastapi import APIRouter
from react_api.schemas.dashboard import (
    DashboardSummaryResponse, ProductSummaryResponse, LocationSummaryResponse,
)
from react_api.dashboard_read_service import DashboardReadService
from react_api.utils.db import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary():
    service = DashboardReadService(get_db())
    return DashboardSummaryResponse(**service.get_summary())


@router.get("/by-product", response_model=ProductSummaryResponse)
def dashboard_by_product():
    service = DashboardReadService(get_db())
    return ProductSummaryResponse(**service.get_by_product())


@router.get("/location-summary", response_model=LocationSummaryResponse)
def dashboard_location_summary():
    service = DashboardReadService(get_db())
    return LocationSummaryResponse(**service.get_location_summary())
