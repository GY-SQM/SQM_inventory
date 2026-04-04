# -*- coding: utf-8 -*-
"""Inventory 조회 라우트."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from react_api.schemas.inventory import (
    InventoryFilterOptionsResponse, InventorySearchResponse, LotDetailResponse,
)
from react_api.services.inventory_read_service import (
    get_inventory_filters, search_inventory, get_lot_detail,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/filters", response_model=InventoryFilterOptionsResponse)
def inventory_filters():
    try:
        return get_inventory_filters()
    except Exception as exc:
        logger.error("inventory_filters 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="필터 옵션 조회 실패")


@router.get("/search", response_model=InventorySearchResponse)
def inventory_search(
    product_name: Optional[str] = Query(None),
    lot_no: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        return search_inventory(
            product_name=product_name, lot_no=lot_no, status=status,
            location=location, keyword=keyword, page=page, page_size=page_size,
        )
    except Exception as exc:
        logger.error("inventory_search 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="재고 검색 실패")


@router.get("/lot/{lot_no}", response_model=LotDetailResponse)
def inventory_lot_detail(lot_no: str):
    try:
        result = get_lot_detail(lot_no)
        if result is None:
            raise HTTPException(status_code=404, detail=f"LOT not found: {lot_no}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("inventory_lot_detail 실패 (lot=%s): %s", lot_no, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="LOT 상세 조회 실패")
