# -*- coding: utf-8 -*-
"""추가 탭용 조회 라우트 — 톤백, 배정, 출고예정, 피킹, 출고완료."""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from react_api.utils.db import get_db, now_str
from react_api.utils.status_normalizer import normalize_display_status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tabs", tags=["tabs"])


@router.get("/tonbag")
def tonbag_list(
    lot_no: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        with get_db() as db:
            conditions = ["1=1"]
            params = []
            if lot_no:
                conditions.append("t.lot_no LIKE ?")
                params.append(f"%{lot_no}%")
            if status:
                ns = normalize_display_status(status)
                if ns == "OUTBOUND":
                    conditions.append("t.status IN ('OUTBOUND','SOLD')")
                else:
                    conditions.append("t.status = ?")
                    params.append(ns)
            if keyword:
                conditions.append(
                    "(t.lot_no LIKE ? OR COALESCE(t.tonbag_uid,'') LIKE ? OR "
                    "COALESCE(i.product,'') LIKE ? OR COALESCE(i.sap_no,'') LIKE ? OR "
                    "COALESCE(i.bl_no,'') LIKE ?)"
                )
                kw = f"%{keyword}%"
                params.extend([kw, kw, kw, kw, kw])

            where = " AND ".join(conditions)
            offset = (page - 1) * page_size

            total = int((db.fetchone(
                f"SELECT COUNT(*) AS c FROM inventory_tonbag t "
                f"LEFT JOIN inventory i ON i.lot_no=t.lot_no WHERE {where}",
                tuple(params),
            ) or {}).get("c") or 0)

            rows = db.fetchall(
                f"SELECT t.id, t.lot_no, COALESCE(t.tonbag_no,'') AS tonbag_no, "
                f"COALESCE(t.tonbag_uid,'') AS tonbag_uid, "
                f"COALESCE(i.sap_no,'') AS sap_no, COALESCE(i.bl_no,'') AS bl_no, "
                f"COALESCE(i.product,'') AS product, "
                f"COALESCE(t.status,'') AS status, COALESCE(t.weight,0) AS weight, "
                f"COALESCE(t.location,'') AS location, COALESCE(t.is_sample,0) AS is_sample, "
                f"COALESCE(i.container_no,'') AS container_no, "
                f"COALESCE(i.net_weight,0) AS net_weight, "
                f"COALESCE(i.salar_invoice_no,'') AS salar_invoice_no, "
                f"i.ship_date, i.arrival_date, i.con_return, "
                f"COALESCE(i.free_time,0) AS free_time, "
                f"COALESCE(i.warehouse,'') AS warehouse, "
                f"COALESCE(i.current_weight,0) AS current_weight, "
                f"t.picked_date, t.outbound_date "
                f"FROM inventory_tonbag t LEFT JOIN inventory i ON i.lot_no=t.lot_no "
                f"WHERE {where} ORDER BY t.lot_no, t.sub_lt, t.id LIMIT ? OFFSET ?",
                tuple(params + [page_size, offset]),
            )

            return {
                "total": total, "page": page, "page_size": page_size,
                "rows": [{
                    **r,
                    "status": normalize_display_status(r.get("status")),
                    "weight_mt": round(float(r.get("weight") or 0) / 1000, 3),
                } for r in (rows or [])],
                "generated_at": now_str(),
            }
    except Exception as exc:
        logger.error("tonbag_list: %s", exc, exc_info=True)
        raise HTTPException(500, "톤백 조회 실패")


@router.get("/allocation")
def allocation_list(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        with get_db() as db:
            conditions = ["1=1"]
            params = []
            if status:
                conditions.append("a.status = ?")
                params.append(status)
            if keyword:
                conditions.append(
                    "(a.lot_no LIKE ? OR COALESCE(a.customer,'') LIKE ? OR "
                    "COALESCE(a.sale_ref,'') LIKE ?)"
                )
                kw = f"%{keyword}%"
                params.extend([kw, kw, kw])

            where = " AND ".join(conditions)
            offset = (page - 1) * page_size

            total = int((db.fetchone(
                f"SELECT COUNT(*) AS c FROM allocation_plan a WHERE {where}",
                tuple(params),
            ) or {}).get("c") or 0)

            rows = db.fetchall(
                f"SELECT a.id, a.lot_no, a.tonbag_id, a.sub_lt, "
                f"COALESCE(a.customer,'') AS customer, COALESCE(a.sale_ref,'') AS sale_ref, "
                f"COALESCE(a.qty_mt,0) AS qty_mt, a.outbound_date, a.status, "
                f"COALESCE(a.source_file,'') AS source_file, a.created_at, "
                f"a.executed_at, a.cancelled_at, "
                f"COALESCE(i.product,'') AS product, COALESCE(i.sap_no,'') AS sap_no "
                f"FROM allocation_plan a "
                f"LEFT JOIN inventory i ON i.lot_no=a.lot_no "
                f"WHERE {where} ORDER BY a.id DESC LIMIT ? OFFSET ?",
                tuple(params + [page_size, offset]),
            )

            return {
                "total": total, "page": page, "page_size": page_size,
                "rows": rows or [],
                "generated_at": now_str(),
            }
    except Exception as exc:
        logger.error("allocation_list: %s", exc, exc_info=True)
        raise HTTPException(500, "배정 조회 실패")


@router.get("/picked")
def picked_list(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    try:
        with get_db() as db:
            offset = (page - 1) * page_size
            total = int((db.fetchone("SELECT COUNT(*) AS c FROM picking_table") or {}).get("c") or 0)
            rows = db.fetchall(
                "SELECT p.id, p.lot_no, p.sub_lt, COALESCE(p.tonbag_uid,'') AS tonbag_uid, "
                "COALESCE(p.picking_no,'') AS picking_no, COALESCE(p.customer,'') AS customer, "
                "COALESCE(p.qty_kg,0) AS qty_kg, COALESCE(p.qty_mt,0) AS qty_mt, "
                "p.status, p.creation_date, COALESCE(i.product,'') AS product "
                "FROM picking_table p LEFT JOIN inventory i ON i.lot_no=p.lot_no "
                "ORDER BY p.id DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            )
            return {"total": total, "page": page, "rows": rows or [], "generated_at": now_str()}
    except Exception as exc:
        logger.error("picked_list: %s", exc, exc_info=True)
        raise HTTPException(500, "피킹 조회 실패")


@router.get("/sold")
def sold_list(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    try:
        with get_db() as db:
            offset = (page - 1) * page_size
            total = int((db.fetchone("SELECT COUNT(*) AS c FROM sold_table") or {}).get("c") or 0)
            rows = db.fetchall(
                "SELECT s.id, s.lot_no, s.sub_lt, COALESCE(s.tonbag_uid,'') AS tonbag_uid, "
                "COALESCE(s.picking_no,'') AS picking_no, COALESCE(s.customer,'') AS customer, "
                "COALESCE(s.sold_qty_kg,0) AS sold_qty_kg, COALESCE(s.sold_qty_mt,0) AS sold_qty_mt, "
                "s.status, s.delivery_date, COALESCE(i.product,'') AS product "
                "FROM sold_table s LEFT JOIN inventory i ON i.lot_no=s.lot_no "
                "ORDER BY s.id DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            )
            return {"total": total, "page": page, "rows": rows or [], "generated_at": now_str()}
    except Exception as exc:
        logger.error("sold_list: %s", exc, exc_info=True)
        raise HTTPException(500, "출고완료 조회 실패")


@router.get("/outbound")
def outbound_list(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    try:
        with get_db() as db:
            offset = (page - 1) * page_size
            total = int((db.fetchone("SELECT COUNT(*) AS c FROM outbound") or {}).get("c") or 0)
            rows = db.fetchall(
                "SELECT id, COALESCE(outbound_no,'') AS outbound_no, "
                "COALESCE(sale_ref,'') AS sale_ref, COALESCE(customer,'') AS customer, "
                "COALESCE(total_qty_mt,0) AS total_qty_mt, outbound_date, "
                "COALESCE(destination,'') AS destination, status, "
                "COALESCE(remarks,'') AS remarks, created_at "
                "FROM outbound ORDER BY id DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            )
            return {"total": total, "page": page, "rows": rows or [], "generated_at": now_str()}
    except Exception as exc:
        logger.error("outbound_list: %s", exc, exc_info=True)
        raise HTTPException(500, "출고예정 조회 실패")


@router.get("/move-log")
def move_log_list(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """톤백 이동 이력 조회."""
    try:
        with get_db() as db:
            conditions = ["1=1"]
            params = []
            if keyword:
                conditions.append(
                    "(m.lot_no LIKE ? OR COALESCE(m.from_location,'') LIKE ? OR "
                    "COALESCE(m.to_location,'') LIKE ?)"
                )
                kw = f"%{keyword}%"
                params.extend([kw, kw, kw])

            where = " AND ".join(conditions)
            offset = (page - 1) * page_size

            total = int((db.fetchone(
                f"SELECT COUNT(*) AS c FROM tonbag_move_log m WHERE {where}",
                tuple(params),
            ) or {}).get("c") or 0)

            rows = db.fetchall(
                f"SELECT m.id, m.lot_no, m.sub_lt, "
                f"COALESCE(m.from_location,'') AS from_location, "
                f"COALESCE(m.to_location,'') AS to_location, "
                f"COALESCE(m.source,'') AS source, "
                f"COALESCE(m.reason_code,'') AS reason_code, "
                f"COALESCE(m.operator,'') AS operator, "
                f"COALESCE(m.note,'') AS note, "
                f"m.created_at "
                f"FROM tonbag_move_log m WHERE {where} "
                f"ORDER BY m.id DESC LIMIT ? OFFSET ?",
                tuple(params + [page_size, offset]),
            )
            return {"total": total, "page": page, "page_size": page_size, "rows": rows or [], "generated_at": now_str()}
    except Exception as exc:
        logger.error("move_log_list: %s", exc, exc_info=True)
        raise HTTPException(500, "이동 이력 조회 실패")


@router.get("/audit-log")
def audit_log_list(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """감사 로그 조회."""
    try:
        with get_db() as db:
            conditions = ["1=1"]
            params = []
            if keyword:
                conditions.append(
                    "(COALESCE(a.event_type,'') LIKE ? OR COALESCE(a.event_data,'') LIKE ?)"
                )
                kw = f"%{keyword}%"
                params.extend([kw, kw])

            where = " AND ".join(conditions)
            offset = (page - 1) * page_size

            total = int((db.fetchone(
                f"SELECT COUNT(*) AS c FROM audit_log a WHERE {where}",
                tuple(params),
            ) or {}).get("c") or 0)

            rows = db.fetchall(
                f"SELECT a.id, COALESCE(a.event_type,'') AS event_type, "
                f"COALESCE(a.event_data,'') AS event_data, a.created_at "
                f"FROM audit_log a WHERE {where} "
                f"ORDER BY a.id DESC LIMIT ? OFFSET ?",
                tuple(params + [page_size, offset]),
            )
            return {"total": total, "page": page, "page_size": page_size, "rows": rows or [], "generated_at": now_str()}
    except Exception as exc:
        logger.error("audit_log_list: %s", exc, exc_info=True)
        raise HTTPException(500, "감사 로그 조회 실패")


@router.get("/stock-movement")
def stock_movement_list(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """재고 이동 이력 조회 (입고/출고/반품 등)."""
    try:
        with get_db() as db:
            conditions = ["1=1"]
            params = []
            if keyword:
                conditions.append(
                    "(COALESCE(sm.lot_no,'') LIKE ? OR COALESCE(sm.movement_type,'') LIKE ? OR "
                    "COALESCE(sm.description,'') LIKE ?)"
                )
                kw = f"%{keyword}%"
                params.extend([kw, kw, kw])

            where = " AND ".join(conditions)
            offset = (page - 1) * page_size

            total = int((db.fetchone(
                f"SELECT COUNT(*) AS c FROM stock_movement sm WHERE {where}",
                tuple(params),
            ) or {}).get("c") or 0)

            rows = db.fetchall(
                f"SELECT sm.id, COALESCE(sm.lot_no,'') AS lot_no, sm.sub_lt, "
                f"COALESCE(sm.movement_type,'') AS movement_type, "
                f"COALESCE(sm.description,'') AS description, "
                f"COALESCE(sm.qty_kg,0) AS qty_kg, "
                f"COALESCE(sm.source,'') AS source, "
                f"sm.created_at "
                f"FROM stock_movement sm WHERE {where} "
                f"ORDER BY sm.id DESC LIMIT ? OFFSET ?",
                tuple(params + [page_size, offset]),
            )
            return {"total": total, "page": page, "page_size": page_size, "rows": rows or [], "generated_at": now_str()}
    except Exception as exc:
        logger.error("stock_movement_list: %s", exc, exc_info=True)
        raise HTTPException(500, "재고 이동 이력 조회 실패")
