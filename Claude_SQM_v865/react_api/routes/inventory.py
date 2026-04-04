# -*- coding: utf-8 -*-
"""Inventory 조회 라우트."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from react_api.schemas.inventory import (
    InventoryFilterOptionsResponse, InventorySearchResponse, LotDetailResponse,
)
from react_api.services.inventory_read_service import (
    get_inventory_filters, search_inventory, get_lot_detail,
)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/filters", response_model=InventoryFilterOptionsResponse)
def inventory_filters():
    return get_inventory_filters()


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
    return search_inventory(
        product_name=product_name, lot_no=lot_no, status=status,
        location=location, keyword=keyword, page=page, page_size=page_size,
    )


@router.get("/lot/{lot_no}", response_model=LotDetailResponse)
def inventory_lot_detail(lot_no: str):
    result = get_lot_detail(lot_no)
    if result is None:
        raise HTTPException(status_code=404, detail=f"LOT not found: {lot_no}")
    return result
