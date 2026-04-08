# -*- coding: utf-8 -*-
"""Return 조회 라우트 — 반품 이력 + 통계."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from react_api.services.return_read_service import (
    get_return_history,
    get_return_statistics,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/return", tags=["return"])


@router.get("/list")
def return_list(
    lot_no: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        return get_return_history(
            lot_no=lot_no, start_date=start_date, end_date=end_date,
            page=page, page_size=page_size,
        )
    except Exception as exc:
        logger.error("return_list: %s", exc, exc_info=True)
        raise HTTPException(500, "반품 이력 조회 실패")


@router.get("/statistics")
def return_statistics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    try:
        return get_return_statistics(start_date=start_date, end_date=end_date)
    except Exception as exc:
        logger.error("return_statistics: %s", exc, exc_info=True)
        raise HTTPException(500, "반품 통계 조회 실패")
