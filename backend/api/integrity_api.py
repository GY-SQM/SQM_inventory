import sqlite3, os, logging
from fastapi import APIRouter

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/integrity", tags=["integrity"])


def _db_path():
    env = os.environ.get("SQM_TEST_DB_PATH")
    if env and os.path.exists(env): return env
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p = os.path.join(root, "data", "db", "sqm_inventory.db")
    if not os.path.exists(p):
        b = os.path.join(root, "backup", "sqm_backup_20260421_232322.db")
        if os.path.exists(b): return b
    return p


def _db():
    conn = sqlite3.connect(_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/check")
async def integrity_check():
    try:
        conn = _db()
        total = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        rows = conn.execute(
            "SELECT lot_no, initial_weight, current_weight, picked_weight, "
            "ABS(initial_weight - (current_weight + picked_weight)) AS diff "
            "FROM inventory "
            "WHERE ABS(initial_weight - (current_weight + picked_weight)) > 1.0"
        ).fetchall()
        conn.close()
        error_list = [dict(r) for r in rows]
        return dict(
            success=True,
            message="정합성 검사 완료",
            data=dict(
                total=total,
                ok=total - len(error_list),
                error=len(error_list),
                details=error_list,
            )
        )
    except Exception as e:
        log.error("integrity_check error: %s", e)
        return dict(success=False, message=str(e), data=None)


@router.get("/diagnostic")
async def integrity_diagnostic():
    """
    정합성 진단: initial_weight(inventory) vs SUM(tonbag.weight) 불일치 LOT 조회.
    상태별 톤백 분포 포함 → 어디서 무게가 누락됐는지 파악 가능.
    """
    try:
        conn = _db()
        summary_rows = conn.execute("""
            SELECT
                i.status AS inv_status,
                COUNT(DISTINCT i.lot_no)              AS lot_cnt,
                ROUND(COALESCE(SUM(i.initial_weight),0)/1000.0,3) AS initial_mt,
                ROUND(COALESCE(SUM(tb_all.total_w),0)/1000.0,3)  AS tonbag_mt,
                ROUND((COALESCE(SUM(i.initial_weight),0) - COALESCE(SUM(tb_all.total_w),0))/1000.0,3) AS diff_mt
            FROM inventory i
            LEFT JOIN (
                SELECT lot_no, SUM(weight) AS total_w FROM inventory_tonbag GROUP BY lot_no
            ) tb_all ON tb_all.lot_no = i.lot_no
            GROUP BY i.status
            ORDER BY ABS(COALESCE(SUM(i.initial_weight),0) - COALESCE(SUM(tb_all.total_w),0)) DESC
        """).fetchall()

        orphan_rows = conn.execute("""
            SELECT
                i.lot_no,
                i.status                        AS inv_status,
                i.product,
                ROUND(i.initial_weight/1000.0,3) AS initial_mt,
                ROUND(COALESCE(tb_all.total_w,0)/1000.0,3) AS tonbag_total_mt,
                ROUND((i.initial_weight - COALESCE(tb_all.total_w,0))/1000.0,3) AS diff_mt,
                COALESCE(tb_cnt.pending_cnt,0)   AS pending_bags,
                COALESCE(tb_cnt.avail_cnt,0)     AS avail_bags,
                COALESCE(tb_cnt.sold_cnt,0)      AS sold_bags,
                COALESCE(tb_cnt.total_cnt,0)     AS total_bags
            FROM inventory i
            LEFT JOIN (
                SELECT lot_no, SUM(weight) AS total_w FROM inventory_tonbag GROUP BY lot_no
            ) tb_all ON tb_all.lot_no = i.lot_no
            LEFT JOIN (
                SELECT lot_no,
                    SUM(CASE WHEN status='PENDING'   THEN 1 ELSE 0 END) AS pending_cnt,
                    SUM(CASE WHEN status='AVAILABLE' THEN 1 ELSE 0 END) AS avail_cnt,
                    SUM(CASE WHEN status='SOLD'      THEN 1 ELSE 0 END) AS sold_cnt,
                    COUNT(*) AS total_cnt
                FROM inventory_tonbag GROUP BY lot_no
            ) tb_cnt ON tb_cnt.lot_no = i.lot_no
            WHERE ABS(i.initial_weight - COALESCE(tb_all.total_w,0)) > 1.0
            ORDER BY ABS(i.initial_weight - COALESCE(tb_all.total_w,0)) DESC
            LIMIT 100
        """).fetchall()

        balance = conn.execute("""
            SELECT
                ROUND(COALESCE(SUM(i.initial_weight),0)/1000.0,3) AS total_initial_mt,
                ROUND(COALESCE(SUM(CASE WHEN t.status='PENDING'   THEN t.weight ELSE 0 END),0)/1000.0,3) AS pending_mt,
                ROUND(COALESCE(SUM(CASE WHEN t.status IN ('AVAILABLE','RESERVED','PICKED','RETURN') THEN t.weight ELSE 0 END),0)/1000.0,3) AS stock_mt,
                ROUND(COALESCE(SUM(CASE WHEN t.status IN ('SOLD','SHIPPED','CONFIRMED') THEN t.weight ELSE 0 END),0)/1000.0,3) AS sold_mt
            FROM inventory i
            LEFT JOIN inventory_tonbag t ON t.lot_no = i.lot_no
        """).fetchone()

        conn.close()
        return dict(
            success=True,
            data=dict(
                balance=dict(balance),
                by_status=[dict(r) for r in summary_rows],
                orphan_lots=[dict(r) for r in orphan_rows],
                orphan_count=len(orphan_rows),
            )
        )
    except Exception as e:
        log.error("integrity_diagnostic error: %s", e)
        return dict(success=False, message=str(e), data=None)
