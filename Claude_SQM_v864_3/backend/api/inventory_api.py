"""
SQM v864.3 - Inventory / Allocation / Tonbag / Scan endpoints
GET  /api/inventory          사이드바 Inventory 탭 데이터
GET  /api/allocation         사이드바 Allocation 탭 데이터
GET  /api/tonbags            톤백 리스트
POST /api/scan/process       바코드 스캔 처리
GET  /api/health             시스템 헬스체크
"""
import sqlite3, os, sys, logging
from typing import Optional
from fastapi import APIRouter, Query as QP, HTTPException
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

# ─── 헬퍼 ────────────────────────────────────────────────────────────
def _db_path() -> str:
    # 테스트 모드: 환경변수 SQM_TEST_DB_PATH 우선 사용
    env_path = os.environ.get("SQM_TEST_DB_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main_path = os.path.join(root, "data", "db", "sqm_inventory.db")
    # 메인 DB가 없거나 백업 fallback 사용 (테스트 환경 보호)
    if not os.path.exists(main_path):
        backup = os.path.join(root, "backup", "sqm_backup_20260421_232322.db")
        if os.path.exists(backup):
            return backup
    return main_path

def _db() -> sqlite3.Connection:
    db = sqlite3.connect(_db_path(), timeout=10)
    db.row_factory = sqlite3.Row
    return db

def _rows(cur) -> list:
    return [dict(r) for r in cur.fetchall()]

# ─── 라우터 ──────────────────────────────────────────────────────────
inv_router  = APIRouter(prefix="/api/inventory",  tags=["inventory"])
alloc_router = APIRouter(prefix="/api/allocation", tags=["allocation"])
tb_router   = APIRouter(prefix="/api/tonbags",    tags=["tonbags"])
scan_router = APIRouter(prefix="/api/scan",       tags=["scan"])
health_router = APIRouter(prefix="/api",           tags=["health"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET /api/inventory   — Inventory 탭 메인 데이터
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@inv_router.get("")
def get_inventory(
    status: Optional[str] = QP(None),
    product: Optional[str] = QP(None),
    lot_no:  Optional[str] = QP(None),
    limit:   int = QP(200),
):
    try:
        db = _db()
        c  = db.cursor()
        sql = """
            SELECT
                i.lot_no        AS lot,
                i.sap_no        AS sap,
                i.bl_no         AS bl,
                i.product,
                i.status,
                ROUND(i.current_weight / 1000.0, 3) AS balance,
                ROUND(i.net_weight / 1000.0, 3)     AS net,
                i.container_no  AS container,
                i.mxbg_pallet,
                (SELECT COUNT(*) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.status = 'AVAILABLE' AND t.is_sample = 0
                ) AS avail_bags,
                i.salar_invoice_no AS invoice_no,
                i.ship_date,
                i.arrival_date,
                i.con_return,
                i.free_time,
                i.warehouse     AS wh,
                i.customs,
                ROUND(i.initial_weight / 1000.0, 3) AS initial_weight,
                ROUND((i.initial_weight - i.current_weight) / 1000.0, 3) AS outbound_weight,
                i.inbound_date  AS date,
                i.location,
                i.sale_ref,
                i.sold_to       AS customer,
                i.remarks
            FROM inventory i
            WHERE 1=1
        """
        params = []
        if status:
            sql += " AND i.status = ?"
            params.append(status)
        if product:
            sql += " AND i.product LIKE ?"
            params.append(f"%{product}%")
        if lot_no:
            sql += " AND i.lot_no LIKE ?"
            params.append(f"%{lot_no}%")
        sql += " ORDER BY i.inbound_date DESC LIMIT ?"
        params.append(limit)
        rows = _rows(c.execute(sql, params))
        db.close()
        return rows
    except Exception as e:
        log.error(f"GET /api/inventory error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POST /api/inventory/{lot}/cancel  — 배정 취소
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@inv_router.post("/{lot_no}/cancel")
def cancel_inventory(lot_no: str):
    try:
        db = _db()
        db.execute(
            "UPDATE inventory SET status='STOCK', sale_ref=NULL, sold_to=NULL WHERE lot_no=?",
            (lot_no,)
        )
        db.commit(); db.close()
        return {"success": True, "message": f"{lot_no} 배정 취소 완료"}
    except Exception as e:
        log.error(f"cancel error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET /api/allocation  — Allocation 탭 메인 데이터
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@alloc_router.get("")
def get_allocation(
    status:  Optional[str] = QP(None),
    customer: Optional[str] = QP(None),
    limit:   int = QP(200),
):
    try:
        db = _db()
        c  = db.cursor()
        # allocation_plan 테이블 우선, 없으면 inventory SOLD 기준
        plan_count = c.execute("SELECT COUNT(*) FROM allocation_plan").fetchone()[0]
        if plan_count > 0:
            sql = """
                SELECT
                    ap.lot_no           AS lot,
                    i.product,
                    ap.customer,
                    ap.sale_ref,
                    ROUND(ap.qty_mt, 3) AS balance,
                    ap.outbound_date    AS ship_date,
                    ap.status,
                    ap.picking_no,
                    ap.workflow_status
                FROM allocation_plan ap
                LEFT JOIN inventory i ON i.lot_no = ap.lot_no
                WHERE 1=1
            """
            params = []
            if status:
                sql += " AND ap.status = ?"
                params.append(status)
            if customer:
                sql += " AND ap.customer LIKE ?"
                params.append(f"%{customer}%")
            sql += " ORDER BY ap.created_at DESC LIMIT ?"
            params.append(limit)
        else:
            # allocation_plan 비어있으면 inventory의 SOLD/RESERVED 기준
            sql = """
                SELECT
                    i.lot_no        AS lot,
                    i.product,
                    i.sold_to       AS customer,
                    i.sale_ref,
                    ROUND(i.current_weight/1000.0, 3) AS balance,
                    NULL            AS ship_date,
                    i.status,
                    NULL            AS picking_no,
                    NULL            AS workflow_status
                FROM inventory i
                WHERE i.status IN ('SOLD','RESERVED','PICKING','PICKED')
            """
            params = []
            if customer:
                sql += " AND i.sold_to LIKE ?"
                params.append(f"%{customer}%")
            sql += " ORDER BY i.inbound_date DESC LIMIT ?"
            params.append(limit)

        rows = _rows(c.execute(sql, params))
        db.close()
        return rows
    except Exception as e:
        log.error(f"GET /api/allocation error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POST /api/allocation/{lot}/cancel  — 배정 취소
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@alloc_router.post("/{lot_no}/cancel")
def cancel_allocation(lot_no: str):
    try:
        db = _db()
        db.execute(
            "UPDATE allocation_plan SET status='CANCELLED', cancelled_at=datetime('now') WHERE lot_no=?",
            (lot_no,)
        )
        db.commit(); db.close()
        return {"success": True, "message": f"{lot_no} 배정 취소"}
    except Exception as e:
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET /api/tonbags     — 톤백 리스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@tb_router.get("")
def get_tonbags(
    lot_no:  Optional[str] = QP(None),
    status:  Optional[str] = QP(None),
    limit:   int = QP(300),
):
    try:
        db = _db()
        c  = db.cursor()
        sql = """
            SELECT
                t.sub_lt,
                t.lot_no,
                t.sap_no,
                t.bl_no,
                t.inbound_date,
                ROUND(t.weight / 1000.0, 3) AS weight,
                t.status,
                t.location,
                t.picked_to     AS container,
                i.product,
                t.tonbag_uid,
                t.tonbag_no
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON i.lot_no = t.lot_no
            WHERE 1=1
        """
        params = []
        if lot_no:
            sql += " AND t.lot_no LIKE ?"
            params.append(f"%{lot_no}%")
        if status:
            sql += " AND t.status = ?"
            params.append(status)
        sql += " ORDER BY t.inbound_date DESC, t.sub_lt LIMIT ?"
        params.append(limit)
        rows = _rows(c.execute(sql, params))
        db.close()
        return rows
    except Exception as e:
        log.error(f"GET /api/tonbags error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POST /api/scan/process  — 바코드 스캔 처리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@scan_router.post("/process")
def scan_process(payload: dict):
    barcode = (payload.get("barcode") or "").strip()
    action  = (payload.get("action") or "lookup").strip()
    if not barcode:
        raise HTTPException(400, "barcode is required")
    try:
        db = _db()
        c  = db.cursor()
        # sub_lt 또는 tonbag_uid로 조회
        row = c.execute("""
            SELECT t.*, i.product, i.status AS lot_status
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON i.lot_no = t.lot_no
            WHERE t.sub_lt = ? OR t.tonbag_uid = ?
        """, (barcode, barcode)).fetchone()

        if not row:
            db.close()
            return {"success": False, "message": f"바코드를 찾을 수 없음: {barcode}"}

        r = dict(row)
        if action == "lookup":
            db.close()
            return {
                "success": True,
                "message": f"LOT {r.get('lot_no')} / {r.get('sub_lt')} — 위치: {r.get('location','-')}",
                "data": r
            }
        elif action == "outbound":
            db.execute(
                "UPDATE inventory_tonbag SET status='PICKED', picked_date=date('now') WHERE sub_lt=?",
                (barcode,)
            )
            db.commit()
            db.close()
            return {"success": True, "message": f"{barcode} 출고 처리 완료", "data": r}
        else:
            db.close()
            return {"success": True, "message": f"{barcode} 조회 완료", "data": r}
    except Exception as e:
        log.error(f"scan process error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET /api/health       — 헬스체크
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@health_router.get("/health")
def health_check():
    try:
        db = _db()
        c  = db.cursor()
        lots  = c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        tbags = c.execute("SELECT COUNT(*) FROM inventory_tonbag").fetchone()[0]
        db.close()
        return {
            "status": "ok",
            "lots": lots,
            "tonbags": tbags,
            "engine_count": lots
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "engine_count": 0}
