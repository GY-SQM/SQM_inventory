# -*- coding: utf-8 -*-
"""
SQM React Phase 1 - FastAPI Main (Draft)
----------------------------------------
1단계 목표:
- 조회 전용 API만 제공
- 기존 tkinter 운영본 유지
- SQLite schema / business policy 변경 없음
- 상태 표시는 OUTBOUND 기준

실행 예시:
    uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Generator, List, Optional

from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine_modules.database import SQMDatabase
from api.dashboard_read_service import DashboardReadService

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SQM Read API",
    version="0.1.0",
    description="SQM React 1단계용 조회 전용 API 초안",
)

# 개발 단계에서 React(Vite)와 연결하기 위한 기본 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def get_db() -> Generator[SQMDatabase, None, None]:
    """DB 연결을 열고, 사용 후 안전하게 닫는다."""
    db = SQMDatabase()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            logger.debug("DB close 중 무시 가능한 예외", exc_info=True)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =========================
# Pydantic Schemas
# =========================
class HealthResponse(BaseModel):
    ok: bool
    service: str
    generated_at: str


class DashboardSummaryItem(BaseModel):
    status: str
    bag_count: int
    weight_kg: float
    weight_mt: float
    sample_bag_count: int = 0


class DashboardSummaryTotals(BaseModel):
    bag_count: int
    weight_kg: float
    weight_mt: float
    sample_bag_count: int = 0


class DashboardSummaryResponse(BaseModel):
    items: List[DashboardSummaryItem]
    totals: DashboardSummaryTotals
    generated_at: str


class ProductSummaryRow(BaseModel):
    product_name: str
    lot_count: int
    tonbag_count: int
    available_kg: float
    reserved_kg: float
    picked_kg: float
    outbound_kg: float
    available_mt: float
    reserved_mt: float
    picked_mt: float
    outbound_mt: float
    total_mt: float


class ProductSummaryResponse(BaseModel):
    rows: List[ProductSummaryRow]
    generated_at: str


class LocationSummaryRow(BaseModel):
    location: str
    bag_count: int
    weight_kg: float
    weight_mt: float


class LocationSummaryResponse(BaseModel):
    rows: List[LocationSummaryRow]
    generated_at: str


class InventoryRow(BaseModel):
    tonbag_id: int
    lot_no: str
    tonbag_uid: str = ""
    tonbag_no: str = ""
    product_name: str = ""
    sap_no: str = ""
    bl_no: str = ""
    status: str = ""
    location: str = ""
    weight_kg: float = 0.0
    weight_mt: float = 0.0
    is_sample: int = 0
    inbound_date: Optional[str] = None
    picked_date: Optional[str] = None
    outbound_date: Optional[str] = None


class InventorySearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    rows: List[InventoryRow]
    generated_at: str


class InventoryFilterOptionsResponse(BaseModel):
    statuses: List[str]
    products: List[str]
    locations: List[str]
    generated_at: str


class LotStatusItem(BaseModel):
    status: str
    bag_count: int
    weight_kg: float
    weight_mt: float


class LotTonbagRow(BaseModel):
    tonbag_id: int
    tonbag_uid: str = ""
    tonbag_no: str = ""
    sub_lt: Optional[int] = None
    status: str = ""
    location: str = ""
    weight_kg: float = 0.0
    weight_mt: float = 0.0
    is_sample: int = 0
    picked_date: Optional[str] = None
    outbound_date: Optional[str] = None


class LotDetailResponse(BaseModel):
    lot_no: str
    product_name: str = ""
    sap_no: str = ""
    bl_no: str = ""
    inventory_status: str = ""
    tonbag_count: int = 0
    status_summary: List[LotStatusItem] = Field(default_factory=list)
    tonbags: List[LotTonbagRow] = Field(default_factory=list)
    generated_at: str


# =========================
# Helpers
# =========================
def _normalize_display_status(raw_status: Optional[str]) -> str:
    status = (raw_status or "").strip().upper()
    if status == "SOLD":
        return "OUTBOUND"
    return status or "UNKNOWN"


def _build_search_conditions(
    *, product_name: Optional[str], lot_no: Optional[str],
    status: Optional[str], location: Optional[str], keyword: Optional[str],
) -> tuple:
    """검색 조건 SQL 조각 + 파라미터 리스트를 반환한다."""
    conditions: List[str] = ["1=1"]
    params: List[Any] = []

    if product_name:
        conditions.append("i.product LIKE ?")
        params.append(f"%{product_name}%")
    if lot_no:
        conditions.append("t.lot_no LIKE ?")
        params.append(f"%{lot_no}%")
    if location:
        conditions.append("COALESCE(t.location, '') LIKE ?")
        params.append(f"%{location}%")
    if status:
        normalized = _normalize_display_status(status)
        if normalized == "OUTBOUND":
            conditions.append("t.status IN ('OUTBOUND', 'SOLD')")
        else:
            conditions.append("t.status = ?")
            params.append(normalized)
    if keyword:
        conditions.append(
            "("
            "t.lot_no LIKE ? OR "
            "COALESCE(t.tonbag_uid, '') LIKE ? OR "
            "COALESCE(t.tonbag_no, '') LIKE ? OR "
            "COALESCE(i.product, '') LIKE ? OR "
            "COALESCE(i.bl_no, '') LIKE ? OR "
            "COALESCE(i.sap_no, '') LIKE ?"
            ")"
        )
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw, kw, kw])

    return conditions, params


def _row_to_inventory(row: dict) -> InventoryRow:
    """DB 행 dict → InventoryRow 변환."""
    weight_kg = round(float(row.get("weight_kg") or 0), 3)
    return InventoryRow(
        tonbag_id=int(row.get("tonbag_id") or 0),
        lot_no=row.get("lot_no") or "",
        tonbag_uid=row.get("tonbag_uid") or "",
        tonbag_no=row.get("tonbag_no") or "",
        product_name=row.get("product_name") or "",
        sap_no=row.get("sap_no") or "",
        bl_no=row.get("bl_no") or "",
        status=_normalize_display_status(row.get("raw_status")),
        location=row.get("location") or "",
        weight_kg=weight_kg,
        weight_mt=round(weight_kg / 1000.0, 3),
        is_sample=int(row.get("is_sample") or 0),
        inbound_date=row.get("inbound_date"),
        picked_date=row.get("picked_date"),
        outbound_date=row.get("outbound_date"),
    )


# =========================
# Routes
# =========================
@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(ok=True, service="sqm-read-api", generated_at=now_str())


@app.get("/api/dashboard/summary", response_model=DashboardSummaryResponse, tags=["dashboard"])
def dashboard_summary() -> DashboardSummaryResponse:
    try:
        with get_db() as db:
            service = DashboardReadService(db)
            return DashboardSummaryResponse(**service.get_summary())
    except Exception as exc:
        logger.error("dashboard_summary 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="대시보드 요약 조회 실패")


@app.get("/api/dashboard/by-product", response_model=ProductSummaryResponse, tags=["dashboard"])
def dashboard_by_product() -> ProductSummaryResponse:
    try:
        with get_db() as db:
            service = DashboardReadService(db)
            return ProductSummaryResponse(**service.get_by_product())
    except Exception as exc:
        logger.error("dashboard_by_product 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="제품별 요약 조회 실패")


@app.get("/api/dashboard/location-summary", response_model=LocationSummaryResponse, tags=["dashboard"])
def dashboard_location_summary() -> LocationSummaryResponse:
    try:
        with get_db() as db:
            service = DashboardReadService(db)
            return LocationSummaryResponse(**service.get_location_summary())
    except Exception as exc:
        logger.error("dashboard_location_summary 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="위치별 요약 조회 실패")


@app.get("/api/inventory/filters", response_model=InventoryFilterOptionsResponse, tags=["inventory"])
def inventory_filters() -> InventoryFilterOptionsResponse:
    try:
        with get_db() as db:
            statuses = db.fetchall(
                "SELECT DISTINCT status FROM inventory_tonbag WHERE COALESCE(status, '') <> '' ORDER BY status"
            )
            products = db.fetchall(
                "SELECT DISTINCT product FROM inventory WHERE COALESCE(product, '') <> '' ORDER BY product"
            )
            locations = db.fetchall(
                "SELECT DISTINCT location FROM inventory_tonbag WHERE COALESCE(TRIM(location), '') <> '' ORDER BY location"
            )

            normalized_statuses = sorted({_normalize_display_status(row.get("status")) for row in statuses})

            return InventoryFilterOptionsResponse(
                statuses=normalized_statuses,
                products=[row.get("product") for row in products if row.get("product")],
                locations=[row.get("location") for row in locations if row.get("location")],
                generated_at=now_str(),
            )
    except Exception as exc:
        logger.error("inventory_filters 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="필터 옵션 조회 실패")


@app.get("/api/inventory/search", response_model=InventorySearchResponse, tags=["inventory"])
def inventory_search(
    product_name: Optional[str] = Query(None),
    lot_no: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> InventorySearchResponse:
    try:
        with get_db() as db:
            conditions, params = _build_search_conditions(
                product_name=product_name, lot_no=lot_no,
                status=status, location=location, keyword=keyword,
            )
            where_sql = " AND ".join(conditions)
            offset = (page - 1) * page_size

            total_row = db.fetchone(
                f"SELECT COUNT(*) AS total FROM inventory_tonbag t "
                f"LEFT JOIN inventory i ON i.lot_no = t.lot_no WHERE {where_sql}",
                tuple(params),
            )
            total = int((total_row or {}).get("total") or 0)

            rows = db.fetchall(
                f"""
                SELECT
                    t.id AS tonbag_id, t.lot_no,
                    COALESCE(t.tonbag_uid, '') AS tonbag_uid,
                    COALESCE(t.tonbag_no, '') AS tonbag_no,
                    COALESCE(i.product, '') AS product_name,
                    COALESCE(i.sap_no, '') AS sap_no,
                    COALESCE(i.bl_no, '') AS bl_no,
                    COALESCE(t.status, '') AS raw_status,
                    COALESCE(t.location, '') AS location,
                    COALESCE(t.weight, 0) AS weight_kg,
                    COALESCE(t.is_sample, 0) AS is_sample,
                    t.inbound_date, t.picked_date, t.outbound_date
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON i.lot_no = t.lot_no
                WHERE {where_sql}
                ORDER BY t.lot_no, t.sub_lt, t.id
                LIMIT ? OFFSET ?
                """,
                tuple(params + [page_size, offset]),
            )

            normalized_rows = [_row_to_inventory(row) for row in rows]

            return InventorySearchResponse(
                total=total, page=page, page_size=page_size,
                rows=normalized_rows, generated_at=now_str(),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("inventory_search 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="재고 검색 실패")


@app.get("/api/inventory/lot/{lot_no}", response_model=LotDetailResponse, tags=["inventory"])
def inventory_lot_detail(lot_no: str) -> LotDetailResponse:
    try:
        with get_db() as db:
            inventory_row = db.fetchone(
                "SELECT lot_no, product, sap_no, bl_no, status, tonbag_count "
                "FROM inventory WHERE lot_no = ? LIMIT 1",
                (lot_no,),
            )
            if not inventory_row:
                raise HTTPException(status_code=404, detail=f"LOT not found: {lot_no}")

            status_rows = db.fetchall(
                """
                SELECT
                    CASE WHEN status IN ('OUTBOUND', 'SOLD') THEN 'OUTBOUND' ELSE status END AS display_status,
                    COUNT(*) AS bag_count,
                    COALESCE(SUM(COALESCE(weight, 0)), 0) AS weight_kg
                FROM inventory_tonbag
                WHERE lot_no = ?
                GROUP BY CASE WHEN status IN ('OUTBOUND', 'SOLD') THEN 'OUTBOUND' ELSE status END
                ORDER BY display_status
                """,
                (lot_no,),
            )

            tonbag_rows = db.fetchall(
                """
                SELECT
                    id AS tonbag_id,
                    COALESCE(tonbag_uid, '') AS tonbag_uid,
                    COALESCE(tonbag_no, '') AS tonbag_no,
                    sub_lt,
                    COALESCE(status, '') AS raw_status,
                    COALESCE(location, '') AS location,
                    COALESCE(weight, 0) AS weight_kg,
                    COALESCE(is_sample, 0) AS is_sample,
                    picked_date, outbound_date
                FROM inventory_tonbag
                WHERE lot_no = ?
                ORDER BY sub_lt, id
                """,
                (lot_no,),
            )

            return LotDetailResponse(
                lot_no=inventory_row.get("lot_no") or lot_no,
                product_name=inventory_row.get("product") or "",
                sap_no=inventory_row.get("sap_no") or "",
                bl_no=inventory_row.get("bl_no") or "",
                inventory_status=_normalize_display_status(inventory_row.get("status")),
                tonbag_count=int(inventory_row.get("tonbag_count") or 0),
                status_summary=[
                    LotStatusItem(
                        status=_normalize_display_status(row.get("display_status")),
                        bag_count=int(row.get("bag_count") or 0),
                        weight_kg=round(float(row.get("weight_kg") or 0), 3),
                        weight_mt=round(float(row.get("weight_kg") or 0) / 1000.0, 3),
                    )
                    for row in status_rows
                ],
                tonbags=[
                    LotTonbagRow(
                        tonbag_id=int(row.get("tonbag_id") or 0),
                        tonbag_uid=row.get("tonbag_uid") or "",
                        tonbag_no=row.get("tonbag_no") or "",
                        sub_lt=row.get("sub_lt"),
                        status=_normalize_display_status(row.get("raw_status")),
                        location=row.get("location") or "",
                        weight_kg=round(float(row.get("weight_kg") or 0), 3),
                        weight_mt=round(float(row.get("weight_kg") or 0) / 1000.0, 3),
                        is_sample=int(row.get("is_sample") or 0),
                        picked_date=row.get("picked_date"),
                        outbound_date=row.get("outbound_date"),
                    )
                    for row in tonbag_rows
                ],
                generated_at=now_str(),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("inventory_lot_detail 실패 (lot=%s): %s", lot_no, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="LOT 상세 조회 실패")
