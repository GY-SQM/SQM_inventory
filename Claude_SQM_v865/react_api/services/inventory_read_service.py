# -*- coding: utf-8 -*-
"""Inventory 조회 전용 서비스."""
from typing import Any, Dict, List, Optional

from react_api.utils.status_normalizer import normalize_display_status
from react_api.utils.db import get_db, now_str
from react_api.schemas.inventory import (
    InventoryRow, InventorySearchResponse,
    InventoryFilterOptionsResponse,
    LotDetailResponse, LotStatusItem, LotTonbagRow,
)


def get_inventory_filters() -> InventoryFilterOptionsResponse:
    db = get_db()
    statuses = db.fetchall(
        "SELECT DISTINCT status FROM inventory_tonbag WHERE COALESCE(status, '') <> '' ORDER BY status"
    )
    products = db.fetchall(
        "SELECT DISTINCT product FROM inventory WHERE COALESCE(product, '') <> '' ORDER BY product"
    )
    locations = db.fetchall(
        "SELECT DISTINCT location FROM inventory_tonbag WHERE COALESCE(TRIM(location), '') <> '' ORDER BY location"
    )
    normalized_statuses = sorted({normalize_display_status(row.get("status")) for row in statuses})
    return InventoryFilterOptionsResponse(
        statuses=normalized_statuses,
        products=[row.get("product") for row in products if row.get("product")],
        locations=[row.get("location") for row in locations if row.get("location")],
        generated_at=now_str(),
    )


def search_inventory(
    product_name: Optional[str] = None,
    lot_no: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> InventorySearchResponse:
    db = get_db()
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
        normalized = normalize_display_status(status)
        if normalized == "OUTBOUND":
            conditions.append("t.status IN ('OUTBOUND', 'SOLD')")
        else:
            conditions.append("t.status = ?")
            params.append(normalized)
    if keyword:
        conditions.append(
            "(t.lot_no LIKE ? OR "
            "COALESCE(t.tonbag_uid, '') LIKE ? OR "
            "COALESCE(t.tonbag_no, '') LIKE ? OR "
            "COALESCE(i.product, '') LIKE ? OR "
            "COALESCE(i.bl_no, '') LIKE ? OR "
            "COALESCE(i.sap_no, '') LIKE ?)"
        )
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw, kw, kw])

    where_sql = " AND ".join(conditions)
    offset = (page - 1) * page_size

    total_row = db.fetchone(
        f"SELECT COUNT(*) AS total FROM inventory_tonbag t "
        f"LEFT JOIN inventory i ON i.lot_no = t.lot_no WHERE {where_sql}",
        tuple(params),
    )
    total = int((total_row or {}).get("total") or 0)

    rows = db.fetchall(
        f"SELECT t.id AS tonbag_id, t.lot_no, "
        f"COALESCE(t.tonbag_uid, '') AS tonbag_uid, "
        f"COALESCE(t.tonbag_no, '') AS tonbag_no, "
        f"COALESCE(i.product, '') AS product_name, "
        f"COALESCE(i.sap_no, '') AS sap_no, "
        f"COALESCE(i.bl_no, '') AS bl_no, "
        f"COALESCE(t.status, '') AS raw_status, "
        f"COALESCE(t.location, '') AS location, "
        f"COALESCE(t.weight, 0) AS weight_kg, "
        f"COALESCE(t.is_sample, 0) AS is_sample, "
        f"t.inbound_date, t.picked_date, t.outbound_date "
        f"FROM inventory_tonbag t LEFT JOIN inventory i ON i.lot_no = t.lot_no "
        f"WHERE {where_sql} ORDER BY t.lot_no, t.sub_lt, t.id "
        f"LIMIT ? OFFSET ?",
        tuple(params + [page_size, offset]),
    )

    normalized_rows = [
        InventoryRow(
            tonbag_id=int(row.get("tonbag_id") or 0),
            lot_no=row.get("lot_no") or "",
            tonbag_uid=row.get("tonbag_uid") or "",
            tonbag_no=row.get("tonbag_no") or "",
            product_name=row.get("product_name") or "",
            sap_no=row.get("sap_no") or "",
            bl_no=row.get("bl_no") or "",
            status=normalize_display_status(row.get("raw_status")),
            location=row.get("location") or "",
            weight_kg=round(float(row.get("weight_kg") or 0), 3),
            weight_mt=round(float(row.get("weight_kg") or 0) / 1000.0, 3),
            is_sample=int(row.get("is_sample") or 0),
            inbound_date=row.get("inbound_date"),
            picked_date=row.get("picked_date"),
            outbound_date=row.get("outbound_date"),
        )
        for row in rows
    ]

    return InventorySearchResponse(
        total=total, page=page, page_size=page_size,
        rows=normalized_rows, generated_at=now_str(),
    )


def get_lot_detail(lot_no: str) -> LotDetailResponse:
    db = get_db()
    inventory_row = db.fetchone(
        "SELECT lot_no, product, sap_no, bl_no, status, tonbag_count "
        "FROM inventory WHERE lot_no = ? LIMIT 1",
        (lot_no,),
    )
    if not inventory_row:
        return None

    status_rows = db.fetchall(
        "SELECT CASE WHEN status IN ('OUTBOUND','SOLD') THEN 'OUTBOUND' ELSE status END AS display_status, "
        "COUNT(*) AS bag_count, COALESCE(SUM(COALESCE(weight,0)),0) AS weight_kg "
        "FROM inventory_tonbag WHERE lot_no = ? "
        "GROUP BY CASE WHEN status IN ('OUTBOUND','SOLD') THEN 'OUTBOUND' ELSE status END "
        "ORDER BY display_status",
        (lot_no,),
    )

    tonbag_rows = db.fetchall(
        "SELECT id AS tonbag_id, COALESCE(tonbag_uid,'') AS tonbag_uid, "
        "COALESCE(tonbag_no,'') AS tonbag_no, sub_lt, "
        "COALESCE(status,'') AS raw_status, COALESCE(location,'') AS location, "
        "COALESCE(weight,0) AS weight_kg, COALESCE(is_sample,0) AS is_sample, "
        "picked_date, outbound_date "
        "FROM inventory_tonbag WHERE lot_no = ? ORDER BY sub_lt, id",
        (lot_no,),
    )

    return LotDetailResponse(
        lot_no=inventory_row.get("lot_no") or lot_no,
        product_name=inventory_row.get("product") or "",
        sap_no=inventory_row.get("sap_no") or "",
        bl_no=inventory_row.get("bl_no") or "",
        inventory_status=normalize_display_status(inventory_row.get("status")),
        tonbag_count=int(inventory_row.get("tonbag_count") or 0),
        status_summary=[
            LotStatusItem(
                status=normalize_display_status(row.get("display_status")),
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
                status=normalize_display_status(row.get("raw_status")),
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
