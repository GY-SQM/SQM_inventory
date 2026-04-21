"""
SQM v864.3 — Dashboard KPI 실데이터 엔드포인트
Phase 3 Q1: GET /api/dashboard/kpi

SQL 집계 — DB 직접 접근 (engine 없이도 동작)
컬럼 확인: stock_movement.qty_kg / movement_date(nullable) / created_at
           inventory.status / inventory_tonbag.location+status
"""
import sqlite3
import os
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

router = APIRouter(prefix="/api/dashboard", tags=["dashboard-kpi"])

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def _get_db_path() -> str:
    """config.py 의존 없이 프로젝트 루트 기준 DB 경로 반환."""
    here = os.path.dirname(os.path.abspath(__file__))          # backend/api/
    project_root = os.path.dirname(os.path.dirname(here))      # Claude_SQM_v864_3/
    return os.path.join(project_root, "data", "db", "sqm_inventory.db")


def _run_kpi_queries(db_path: str) -> dict:
    """
    KPI 집계 SQL 4종 실행.
    movement_date 가 NULL 인 레코드는 created_at 으로 대체 (COALESCE).
    """
    con = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=3000")
    try:
        cur = con.cursor()

        # ① 오늘 입고량 (MT)
        cur.execute("""
            SELECT COALESCE(SUM(qty_kg), 0) / 1000.0
            FROM stock_movement
            WHERE movement_type = 'INBOUND'
              AND DATE(COALESCE(movement_date, created_at), 'localtime')
                  = DATE('now', 'localtime')
        """)
        today_inbound_mt = round(float(cur.fetchone()[0] or 0.0), 3)

        # ② 오늘 출고량 (MT)
        cur.execute("""
            SELECT COALESCE(SUM(qty_kg), 0) / 1000.0
            FROM stock_movement
            WHERE movement_type = 'OUTBOUND'
              AND DATE(COALESCE(movement_date, created_at), 'localtime')
                  = DATE('now', 'localtime')
        """)
        today_outbound_mt = round(float(cur.fetchone()[0] or 0.0), 3)

        # ③ 현재 재고 LOT 수 (출고/반품/판매 완료 제외)
        cur.execute("""
            SELECT COUNT(DISTINCT lot_no)
            FROM inventory
            WHERE status NOT IN ('SOLD', 'RETURNED', 'OUTBOUND')
        """)
        current_stock_lots = int(cur.fetchone()[0] or 0)

        # ④ 위치 미배정 톤백 수 (출고/판매 제외, location 없음)
        cur.execute("""
            SELECT COUNT(*)
            FROM inventory_tonbag
            WHERE (location IS NULL OR TRIM(location) = '')
              AND status NOT IN ('SOLD', 'RETURNED', 'OUTBOUND')
        """)
        unassigned_locations = int(cur.fetchone()[0] or 0)

        return {
            "today_inbound_mt":     today_inbound_mt,
            "today_outbound_mt":    today_outbound_mt,
            "current_stock_lots":   current_stock_lots,
            "unassigned_locations": unassigned_locations,
        }
    finally:
        con.close()


@router.get("/kpi")
def get_dashboard_kpi():
    """
    Phase 3 Q1 — Dashboard KPI 실데이터 (5초 폴링용)

    Response:
        ok: bool
        data:
            today_inbound_mt:    float  (MT, 오늘 입고)
            today_outbound_mt:   float  (MT, 오늘 출고)
            current_stock_lots:  int    (현재 재고 LOT 수)
            unassigned_locations: int   (위치 미배정 톤백 수)
            updated_at:          str    (KST ISO 8601)
    """
    now_str = datetime.now(KST).isoformat(timespec="seconds")

    try:
        db_path = _get_db_path()
        kpi = _run_kpi_queries(db_path)
        return {
            "ok": True,
            "data": {**kpi, "updated_at": now_str},
        }
    except Exception as exc:
        logger.error("[dashboard/kpi] 집계 실패: %s", exc, exc_info=True)
        return {
            "ok": False,
            "data": {
                "today_inbound_mt":     0.0,
                "today_outbound_mt":    0.0,
                "current_stock_lots":   0,
                "unassigned_locations": 0,
                "updated_at":           now_str,
            },
            "error": str(exc),
        }
