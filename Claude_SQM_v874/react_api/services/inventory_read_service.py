# -*- coding: utf-8 -*-
"""
inventory_read_service.py v2
 개선 #5: COUNT(*) OVER() 윈도우 함수 → 쿼리 2번→1번
 개선 #6: ADMIN_TOKEN 강도 검사
생성일: 2026-04-08 | SQM v8.7.1
배치: react_api/services/inventory_read_service.py (덮어쓰기)
"""
import logging
import os
from typing import Any, List, Optional

from react_api.utils.status_normalizer import normalize_display_status
from react_api.utils.db import get_db, now_str
from react_api.schemas.inventory import (
    InventoryRow, InventorySearchResponse,
    InventoryFilterOptionsResponse,
    LotDetailResponse, LotStatusItem, LotTonbagRow,
)

logger = logging.getLogger(__name__)


# ================================================================
#  개선 #6: ADMIN_TOKEN 강도 검사 (서버 시작 시 1회)
# ================================================================
def _check_admin_token_strength():
    """ADMIN_TOKEN이 취약하면 로그 경고"""
    token = os.getenv("ADMIN_TOKEN", "")
    weak_tokens = {
        "", "admin", "password", "sqm", "sqm_admin",
        "sqm_admin_2026", "1234", "test", "secret"
    }
    if not token:
        logger.critical(
            " ADMIN_TOKEN 미설정! .env에 강력한 토큰을 설정하세요.\n"
            "  예: ADMIN_TOKEN=SQM@Gwangyang#2026!Secure"
        )
    elif token.lower() in weak_tokens or len(token) < 12:
        logger.warning(
            f"️ ADMIN_TOKEN이 너무 약합니다 (현재: '{token[:4]}...')\n"
            "  영문+숫자+특수문자 16자 이상 권장\n"
            "  예: ADMIN_TOKEN=SQM@Gwangyang#2026!Secure"
        )
    else:
        logger.info(" ADMIN_TOKEN 강도 OK")

# 모듈 로드 시 1회 실행
_check_admin_token_strength()


# ================================================================
# 재고 필터 옵션
# ================================================================

def get_inventory_filters() -> InventoryFilterOptionsResponse:
    with get_db() as db:
        statuses  = db.fetchall(
            "SELECT DISTINCT status FROM inventory_tonbag "
            "WHERE COALESCE(status,'') <> '' ORDER BY status"
        )
        products  = db.fetchall(
            "SELECT DISTINCT product FROM inventory "
            "WHERE COALESCE(product,'') <> '' ORDER BY product"
        )
        locations = db.fetchall(
            "SELECT DISTINCT location FROM inventory_tonbag "
            "WHERE COALESCE(TRIM(location),'') <> '' ORDER BY location"
        )
        normalized_statuses = sorted({
            normalize_display_status(row.get("status")) for row in statuses
        })
        return InventoryFilterOptionsResponse(
            statuses=normalized_statuses,
            products=[row.get("product") for row in products if row.get("product")],
            locations=[row.get("location") for row in locations if row.get("location")],
            generated_at=now_str(),
        )


# ================================================================
#  개선 #5: search_inventory() — 윈도우 함수로 COUNT 쿼리 제거
# ================================================================

def search_inventory(
    product_name: Optional[str] = None,
    lot_no:       Optional[str] = None,
    status:       Optional[str] = None,
    location:     Optional[str] = None,
    keyword:      Optional[str] = None,
    page:         int = 1,
    page_size:    int = 50,
) -> InventorySearchResponse:
    """
     윈도우 함수 COUNT(*) OVER() 적용
    기존: COUNT 쿼리 + SELECT 쿼리 = DB 2번 hit
    개선: SELECT COUNT(*) OVER() AS total ... = DB 1번 hit
    """
    with get_db() as db:
        conditions: List[str] = ["1=1"]
        params:     List[Any] = []

        if product_name:
            conditions.append("i.product LIKE ?")
            params.append(f"%{product_name}%")
        if lot_no:
            conditions.append("t.lot_no LIKE ?")
            params.append(f"%{lot_no}%")
        if location:
            conditions.append("COALESCE(t.location,'') LIKE ?")
            params.append(f"%{location}%")
        if status:
            normalized = normalize_display_status(status)
            if normalized == "OUTBOUND":
                conditions.append("t.status IN ('OUTBOUND','SOLD')")
            else:
                conditions.append("t.status = ?")
                params.append(normalized)
        if keyword:
            conditions.append(
                "(t.lot_no LIKE ? OR COALESCE(t.tonbag_uid,'') LIKE ? OR "
                "COALESCE(t.tonbag_no,'') LIKE ? OR COALESCE(i.product,'') LIKE ? OR "
                "COALESCE(i.bl_no,'') LIKE ? OR COALESCE(i.sap_no,'') LIKE ?)"
            )
            kw = f"%{keyword}%"
            params.extend([kw]*6)

        where_sql = " AND ".join(conditions)
        offset    = (page - 1) * page_size

        #  윈도우 함수: COUNT(*) OVER() — 1번 쿼리로 total 포함
        rows = db.fetchall(
            f"""SELECT
                COUNT(*) OVER() AS total_count,
                t.id AS tonbag_id, t.lot_no,
                COALESCE(t.tonbag_uid,'')  AS tonbag_uid,
                COALESCE(t.tonbag_no,'')   AS tonbag_no,
                COALESCE(i.product,'')     AS product_name,
                COALESCE(i.sap_no,'')      AS sap_no,
                COALESCE(i.bl_no,'')       AS bl_no,
                COALESCE(t.status,'')      AS raw_status,
                COALESCE(t.location,'')    AS location,
                COALESCE(t.weight,0)       AS weight_kg,
                COALESCE(t.is_sample,0)    AS is_sample,
                t.inbound_date, t.picked_date, t.outbound_date,
                COALESCE(i.container_no,'')    AS container_no,
                COALESCE(i.net_weight,0)       AS net_weight,
                COALESCE(i.current_weight,0)   AS current_weight,
                COALESCE(i.initial_weight,0)   AS initial_weight,
                COALESCE(i.mxbg_pallet,0)      AS mxbg_pallet,
                COALESCE(i.salar_invoice_no,'') AS salar_invoice_no,
                i.ship_date, i.arrival_date, i.con_return,
                COALESCE(i.free_time,0)        AS free_time,
                COALESCE(i.warehouse,'')       AS warehouse,
                COALESCE(i.customs,'')         AS customs,
                COALESCE(i.picked_weight,0)    AS picked_weight
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON i.lot_no = t.lot_no
            WHERE {where_sql}
            ORDER BY t.lot_no, t.sub_lt, t.id
            LIMIT ? OFFSET ?""",
            tuple(params + [page_size, offset]),
        )

        # total은 첫 행에서 추출 (윈도우 함수 결과)
        total = int(rows[0].get("total_count") if rows and hasattr(rows[0],'keys')
                    else (rows[0][0] if rows else 0)) if rows else 0

        def _sf(v):
            try: return round(float(v or 0), 3)
            except (ValueError, TypeError): return 0.0
        def _si(v):
            try: return int(v or 0)
            except (ValueError, TypeError): return 0

        normalized_rows = [
            InventoryRow(
                tonbag_id=_si(row.get("tonbag_id") if hasattr(row,'keys') else row[1]),
                lot_no=str(row.get("lot_no") if hasattr(row,'keys') else row[2] or ""),
                tonbag_uid=str(row.get("tonbag_uid") if hasattr(row,'keys') else row[3] or ""),
                tonbag_no=str(row.get("tonbag_no") if hasattr(row,'keys') else row[4] or ""),
                product_name=str(row.get("product_name") if hasattr(row,'keys') else row[5] or ""),
                sap_no=str(row.get("sap_no") if hasattr(row,'keys') else row[6] or ""),
                bl_no=str(row.get("bl_no") if hasattr(row,'keys') else row[7] or ""),
                status=normalize_display_status(
                    row.get("raw_status") if hasattr(row,'keys') else row[8]
                ),
                location=str(row.get("location") if hasattr(row,'keys') else row[9] or ""),
                weight_kg=_sf(row.get("weight_kg") if hasattr(row,'keys') else row[10]),
                weight_mt=round(_sf(row.get("weight_kg") if hasattr(row,'keys') else row[10])/1000,3),
                is_sample=_si(row.get("is_sample") if hasattr(row,'keys') else row[11]),
                inbound_date=row.get("inbound_date") if hasattr(row,'keys') else row[12],
                picked_date=row.get("picked_date") if hasattr(row,'keys') else row[13],
                outbound_date=row.get("outbound_date") if hasattr(row,'keys') else row[14],
                container_no=str(row.get("container_no") if hasattr(row,'keys') else row[15] or ""),
                net_weight=_sf(row.get("net_weight") if hasattr(row,'keys') else row[16]),
                current_weight=_sf(row.get("current_weight") if hasattr(row,'keys') else row[17]),
                initial_weight=_sf(row.get("initial_weight") if hasattr(row,'keys') else row[18]),
                mxbg_pallet=_si(row.get("mxbg_pallet") if hasattr(row,'keys') else row[19]),
                salar_invoice_no=str(row.get("salar_invoice_no") if hasattr(row,'keys') else row[20] or ""),
                ship_date=row.get("ship_date") if hasattr(row,'keys') else row[21],
                arrival_date=row.get("arrival_date") if hasattr(row,'keys') else row[22],
                con_return=row.get("con_return") if hasattr(row,'keys') else row[23],
                free_time=_si(row.get("free_time") if hasattr(row,'keys') else row[24]),
                warehouse=str(row.get("warehouse") if hasattr(row,'keys') else row[25] or ""),
                customs=str(row.get("customs") if hasattr(row,'keys') else row[26] or ""),
                picked_weight=_sf(row.get("picked_weight") if hasattr(row,'keys') else row[27]),
            )
            for row in rows
        ]

        return InventorySearchResponse(
            total=total, page=page, page_size=page_size,
            rows=normalized_rows, generated_at=now_str(),
        )


# ================================================================
# LOT 상세 조회
# ================================================================

def get_lot_detail(lot_no: str) -> Optional[LotDetailResponse]:
    """LOT 상세 조회 — 톤백 목록 + 상태 요약 포함."""
    with get_db() as db:
        inv = db.fetchone(
            "SELECT * FROM inventory WHERE lot_no = ?", (lot_no,)
        )
        if not inv:
            return None
        inv = dict(inv) if hasattr(inv, 'keys') else inv

        def _g(key, default=""):
            return inv.get(key, default) if isinstance(inv, dict) else default

        def _gf(key):
            try: return round(float(_g(key, 0) or 0), 3)
            except (ValueError, TypeError): return 0.0

        def _gi(key):
            try: return int(_g(key, 0) or 0)
            except (ValueError, TypeError): return 0

        # 톤백 목록
        tonbags_raw = db.fetchall(
            "SELECT id, lot_no, sub_lt, tonbag_uid, tonbag_no, status, "
            "location, weight, is_sample, picked_date, outbound_date "
            "FROM inventory_tonbag WHERE lot_no = ? ORDER BY sub_lt",
            (lot_no,)
        ) or []

        tonbags = []
        for t in tonbags_raw:
            td = dict(t) if hasattr(t, 'keys') else t
            w = float(td.get('weight', 0) or 0) if isinstance(td, dict) else 0
            tonbags.append(LotTonbagRow(
                tonbag_id=int(td.get('id', 0) if isinstance(td, dict) else td[0]),
                tonbag_uid=str(td.get('tonbag_uid', '') if isinstance(td, dict) else (td[3] or '')),
                tonbag_no=str(td.get('tonbag_no', '') if isinstance(td, dict) else (td[4] or '')),
                sub_lt=int(td.get('sub_lt', 0) if isinstance(td, dict) else (td[2] or 0)),
                status=normalize_display_status(
                    td.get('status', '') if isinstance(td, dict) else (td[5] or '')
                ),
                location=str(td.get('location', '') if isinstance(td, dict) else (td[6] or '')),
                weight_kg=round(w, 3),
                weight_mt=round(w / 1000, 3),
                is_sample=int(td.get('is_sample', 0) if isinstance(td, dict) else (td[8] or 0)),
                picked_date=td.get('picked_date') if isinstance(td, dict) else td[9],
                outbound_date=td.get('outbound_date') if isinstance(td, dict) else td[10],
            ))

        # 상태 요약
        status_rows = db.fetchall(
            "SELECT status, COUNT(*) AS cnt, COALESCE(SUM(weight),0) AS wt "
            "FROM inventory_tonbag WHERE lot_no = ? GROUP BY status",
            (lot_no,)
        ) or []
        status_summary = []
        for sr in status_rows:
            sd = dict(sr) if hasattr(sr, 'keys') else sr
            wt = float(sd.get('wt', 0) if isinstance(sd, dict) else sd[2])
            status_summary.append(LotStatusItem(
                status=normalize_display_status(
                    sd.get('status', '') if isinstance(sd, dict) else sd[0]
                ),
                bag_count=int(sd.get('cnt', 0) if isinstance(sd, dict) else sd[1]),
                weight_kg=round(wt, 3),
                weight_mt=round(wt / 1000, 3),
            ))

        return LotDetailResponse(
            lot_no=lot_no,
            product_name=str(_g('product', '')),
            sap_no=str(_g('sap_no', '')),
            bl_no=str(_g('bl_no', '')),
            inventory_status=normalize_display_status(str(_g('status', ''))),
            tonbag_count=len(tonbags),
            container_no=str(_g('container_no', '')),
            ship_date=_g('ship_date', None),
            arrival_date=_g('arrival_date', None),
            con_return=_g('con_return', None),
            free_time=_gi('free_time'),
            warehouse=str(_g('warehouse', '')),
            net_weight=_gf('net_weight'),
            current_weight=_gf('current_weight'),
            initial_weight=_gf('initial_weight'),
            status_summary=status_summary,
            tonbags=tonbags,
            generated_at=now_str(),
        )
