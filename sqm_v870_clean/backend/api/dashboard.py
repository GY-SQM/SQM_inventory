"""
SQM v8.6.6 — Dashboard KPI 실데이터 엔드포인트
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
    project_root = os.path.dirname(os.path.dirname(here))      # Claude_SQM_v864_4/
    return os.path.join(project_root, "data", "db", "sqm_inventory.db")


def _run_kpi_queries(db_path: str) -> dict:
    """
    KPI 집계 — inventory_tonbag 기반, is_sample 컬럼으로 톤백/샘플 분리.

    5개 카드 × (톤백 / 샘플) = 10개 무게 필드 + 미배정 개수 2개.

      카드 1: 전일 재고  = 현재 재고 - 오늘 입고 + 오늘 출고 (출고로 어제 마감 복원)
      카드 2: 오늘 입고  = inbound_date = 오늘
      카드 3: 오늘 출고  = outbound_date = 오늘
      카드 4: 현재 재고  = status NOT IN (SOLD, RETURNED, PENDING)
      카드 5: 미배정 톤백 = 현재 재고 중 location 비어있음 (개수 단위)
    """
    con = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=3000")
    try:
        cur = con.cursor()

        # ─── 오늘 입고 (톤백/샘플) — inventory_tonbag.inbound_date 기준 ───
        cur.execute("""
            SELECT
                ROUND(COALESCE(SUM(CASE WHEN COALESCE(is_sample,0)=0 THEN weight ELSE 0 END),0)/1000.0, 3),
                ROUND(COALESCE(SUM(CASE WHEN COALESCE(is_sample,0)=1 THEN weight ELSE 0 END),0)/1000.0, 3)
            FROM inventory_tonbag
            WHERE DATE(COALESCE(inbound_date, created_at), 'localtime') = DATE('now', 'localtime')
        """)
        r = cur.fetchone()
        today_inbound_tonbag_mt = float(r[0] or 0.0)
        today_inbound_sample_mt = float(r[1] or 0.0)

        # ─── 오늘 출고 (톤백/샘플) — outbound_date 기준 ───
        cur.execute("""
            SELECT
                ROUND(COALESCE(SUM(CASE WHEN COALESCE(is_sample,0)=0 THEN weight ELSE 0 END),0)/1000.0, 3),
                ROUND(COALESCE(SUM(CASE WHEN COALESCE(is_sample,0)=1 THEN weight ELSE 0 END),0)/1000.0, 3)
            FROM inventory_tonbag
            WHERE outbound_date IS NOT NULL
              AND DATE(outbound_date, 'localtime') = DATE('now', 'localtime')
        """)
        r = cur.fetchone()
        today_outbound_tonbag_mt = float(r[0] or 0.0)
        today_outbound_sample_mt = float(r[1] or 0.0)

        # ─── 현재 재고 (톤백/샘플) — alive status ───
        cur.execute("""
            SELECT
                ROUND(COALESCE(SUM(CASE WHEN COALESCE(is_sample,0)=0 THEN weight ELSE 0 END),0)/1000.0, 3),
                ROUND(COALESCE(SUM(CASE WHEN COALESCE(is_sample,0)=1 THEN weight ELSE 0 END),0)/1000.0, 3)
            FROM inventory_tonbag
            WHERE status NOT IN ('SOLD','RETURNED','PENDING')
        """)
        r = cur.fetchone()
        current_stock_tonbag_mt = float(r[0] or 0.0)
        current_stock_sample_mt = float(r[1] or 0.0)

        # ─── 전일 재고 = 현재 재고 - 오늘 입고 + 오늘 출고 ───
        prev_stock_tonbag_mt = round(current_stock_tonbag_mt - today_inbound_tonbag_mt + today_outbound_tonbag_mt, 3)
        prev_stock_sample_mt = round(current_stock_sample_mt - today_inbound_sample_mt + today_outbound_sample_mt, 3)

        # ─── 미배정 톤백 (개수, 톤백/샘플 분리) ───
        cur.execute("""
            SELECT
                SUM(CASE WHEN COALESCE(is_sample,0)=0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN COALESCE(is_sample,0)=1 THEN 1 ELSE 0 END)
            FROM inventory_tonbag
            WHERE (location IS NULL OR TRIM(location)='')
              AND status NOT IN ('SOLD','RETURNED','PENDING')
        """)
        r = cur.fetchone()
        unassigned_tonbag_bags = int(r[0] or 0)
        unassigned_sample_bags = int(r[1] or 0)

        # ─── 호환용 (구 키, 합산값) ───
        today_inbound_mt     = round(today_inbound_tonbag_mt + today_inbound_sample_mt, 3)
        today_outbound_mt    = round(today_outbound_tonbag_mt + today_outbound_sample_mt, 3)
        current_stock_mt     = round(current_stock_tonbag_mt + current_stock_sample_mt, 3)
        prev_stock_mt        = round(prev_stock_tonbag_mt + prev_stock_sample_mt, 3)
        unassigned_total     = unassigned_tonbag_bags + unassigned_sample_bags

        # ─── 현재 재고 LOT 수 (기존 호환 키, 일부 화면이 참조) ───
        cur.execute("""
            SELECT COUNT(DISTINCT lot_no)
            FROM inventory
            WHERE status NOT IN ('SOLD','RETURNED','PENDING')
        """)
        current_stock_lots = int(cur.fetchone()[0] or 0)

        return {
            # 카드 1: 전일 재고
            "prev_stock_tonbag_mt":     prev_stock_tonbag_mt,
            "prev_stock_sample_mt":     prev_stock_sample_mt,
            "prev_stock_mt":            prev_stock_mt,
            # 카드 2: 오늘 입고
            "today_inbound_tonbag_mt":  today_inbound_tonbag_mt,
            "today_inbound_sample_mt":  today_inbound_sample_mt,
            "today_inbound_mt":         today_inbound_mt,
            # 카드 3: 오늘 출고
            "today_outbound_tonbag_mt": today_outbound_tonbag_mt,
            "today_outbound_sample_mt": today_outbound_sample_mt,
            "today_outbound_mt":        today_outbound_mt,
            # 카드 4: 현재 재고
            "current_stock_tonbag_mt":  current_stock_tonbag_mt,
            "current_stock_sample_mt":  current_stock_sample_mt,
            "current_stock_mt":         current_stock_mt,
            # 카드 5: 미배정 톤백 (개)
            "unassigned_tonbag_bags":   unassigned_tonbag_bags,
            "unassigned_sample_bags":   unassigned_sample_bags,
            "unassigned_total":         unassigned_total,
            # 호환 (구 키)
            "current_stock_lots":       current_stock_lots,
            "unassigned_locations":     unassigned_total,
            "unassigned_main_bags":     unassigned_tonbag_bags,
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
            # 카드 1: 전일 재고 (어제 마감)
            prev_stock_tonbag_mt:     float (MT, 톤백)
            prev_stock_sample_mt:     float (MT, 샘플)
            prev_stock_mt:            float (MT, 합산)
            # 카드 2: 오늘 입고
            today_inbound_tonbag_mt:  float
            today_inbound_sample_mt:  float
            today_inbound_mt:         float
            # 카드 3: 오늘 출고
            today_outbound_tonbag_mt: float
            today_outbound_sample_mt: float
            today_outbound_mt:        float
            # 카드 4: 현재 재고
            current_stock_tonbag_mt:  float
            current_stock_sample_mt:  float
            current_stock_mt:         float
            # 카드 5: 미배정 톤백 (개수)
            unassigned_tonbag_bags:   int
            unassigned_sample_bags:   int
            unassigned_total:         int
            # 호환 (구 키)
            current_stock_lots:       int
            unassigned_locations:     int
            unassigned_main_bags:     int
            updated_at:               str (KST ISO 8601)
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
                "prev_stock_tonbag_mt":     0.0,
                "prev_stock_sample_mt":     0.0,
                "prev_stock_mt":            0.0,
                "today_inbound_tonbag_mt":  0.0,
                "today_inbound_sample_mt":  0.0,
                "today_inbound_mt":         0.0,
                "today_outbound_tonbag_mt": 0.0,
                "today_outbound_sample_mt": 0.0,
                "today_outbound_mt":        0.0,
                "current_stock_tonbag_mt":  0.0,
                "current_stock_sample_mt":  0.0,
                "current_stock_mt":         0.0,
                "unassigned_tonbag_bags":   0,
                "unassigned_sample_bags":   0,
                "unassigned_total":         0,
                "current_stock_lots":       0,
                "unassigned_locations":     0,
                "unassigned_main_bags":     0,
                "updated_at":               now_str,
            },
            "error": str(exc),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET /api/dashboard/stats  — 대시보드 통계 패널
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.get("/stats")
def get_dashboard_stats():
    """
    Dashboard 통계 — 5단계 상태 요약 + 제품x상태 매트릭스 + 정합성 검증.

    v864.2 대응: dashboard_data_mixin._get_status_four_phase_stats()
                + dashboard_data_mixin._get_integrity_summary()
    """
    try:
        db_path = _get_db_path()
        db = sqlite3.connect(db_path, timeout=10)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=3000")
        c = db.cursor()

        # ── 기본 통계 (기존 호환) ──
        total_lots  = c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        total_tbags = c.execute("SELECT COUNT(*) FROM inventory_tonbag").fetchone()[0]
        stock_lots  = c.execute("SELECT COUNT(*) FROM inventory WHERE status='AVAILABLE'").fetchone()[0]
        sold_lots   = c.execute("SELECT COUNT(*) FROM inventory WHERE status IN ('SOLD','RESERVED','PICKED')").fetchone()[0]
        total_wt    = c.execute("SELECT COALESCE(SUM(current_weight),0) FROM inventory WHERE status != 'PENDING'").fetchone()[0]
        # v9.4 [AVAIL-FIX]: 톤백 레벨 status 기준 무게 집계 (LOT 레벨 오버카운트 수정)
        avail_wt    = c.execute("SELECT COALESCE(SUM(weight),0) FROM inventory_tonbag WHERE status='AVAILABLE'").fetchone()[0]
        reserved_wt = c.execute("SELECT COALESCE(SUM(weight),0) FROM inventory_tonbag WHERE status='RESERVED'").fetchone()[0]
        picked_wt   = c.execute("SELECT COALESCE(SUM(weight),0) FROM inventory_tonbag WHERE status='PICKED'").fetchone()[0]

        # ── 상태 요약 (inventory_tonbag 기준) — 일반 + 샘플 분리 ──
        status_rows = c.execute("""
            SELECT
                CASE
                    WHEN status IN ('SOLD', 'SHIPPED', 'CONFIRMED') THEN 'outbound'
                    WHEN status = 'AVAILABLE' THEN 'available'
                    WHEN status = 'RESERVED'  THEN 'reserved'
                    WHEN status = 'PICKED'    THEN 'picked'
                    WHEN status = 'RETURN'    THEN 'return'
                    ELSE 'other'
                END AS grp,
                COALESCE(is_sample, 0)       AS is_sample,
                COUNT(DISTINCT lot_no)        AS lots,
                COUNT(*)                      AS tonbags,
                COALESCE(SUM(weight), 0)      AS weight_kg
            FROM inventory_tonbag
            GROUP BY grp, is_sample
        """).fetchall()

        status_summary = {}
        for grp_name in ('available', 'reserved', 'picked', 'outbound', 'return'):
            status_summary[grp_name] = {
                "lots": 0, "tonbags": 0, "weight_kg": 0.0,
                "normal_bags": 0, "normal_kg": 0.0,
                "sample_bags": 0, "sample_kg": 0.0,
            }
        for row in status_rows:
            grp, is_sample, lots, tonbags, weight_kg = row
            if grp not in status_summary:
                continue
            s = status_summary[grp]
            s["lots"]     += lots
            s["tonbags"]  += tonbags
            s["weight_kg"] = round(s["weight_kg"] + float(weight_kg), 1)
            if is_sample:
                s["sample_bags"] += tonbags
                s["sample_kg"]    = round(s["sample_kg"] + float(weight_kg), 1)
            else:
                s["normal_bags"] += tonbags
                s["normal_kg"]    = round(s["normal_kg"] + float(weight_kg), 1)
        for grp_name in status_summary:
            s = status_summary[grp_name]
            s["weight_kg"] = round(s["weight_kg"], 1)

        # ── 제품x상태 매트릭스 (제품별 톤백 수량, 정상/샘플 분리) ──
        matrix_rows = c.execute("""
            SELECT
                COALESCE(i.product, '(미지정)')  AS product,
                COALESCE(tb.is_sample, 0)        AS is_sample,
                SUM(CASE WHEN tb.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available,
                SUM(CASE WHEN tb.status = 'RESERVED'  THEN 1 ELSE 0 END) AS reserved,
                SUM(CASE WHEN tb.status = 'PICKED'    THEN 1 ELSE 0 END) AS picked,
                SUM(CASE WHEN tb.status IN ('SOLD','SHIPPED','CONFIRMED') THEN 1 ELSE 0 END) AS outbound,
                SUM(CASE WHEN tb.status = 'RETURN'    THEN 1 ELSE 0 END) AS return_cnt,
                COUNT(*)                         AS total,
                COUNT(DISTINCT CASE WHEN tb.status IN ('AVAILABLE','RESERVED','PICKED','RETURN')
                    THEN tb.lot_no END)           AS lot_count,
                COALESCE(SUM(tb.weight), 0)      AS weight_kg
            FROM inventory_tonbag tb
            LEFT JOIN inventory i ON tb.lot_no = i.lot_no
            GROUP BY COALESCE(i.product, '(미지정)'), COALESCE(tb.is_sample, 0)
            ORDER BY COALESCE(i.product, '(미지정)'), COALESCE(tb.is_sample, 0)
        """).fetchall()

        product_matrix = []
        for row in matrix_rows:
            product_matrix.append({
                "product":    row[0],
                "is_sample":  bool(row[1]),
                "available":  row[2],
                "reserved":   row[3],
                "picked":     row[4],
                "outbound":   row[5],
                "return":     row[6],
                "total":      row[7],
                "lot_count":  row[8],
                "weight_mt":  round(float(row[9]) / 1000.0, 2),
            })

        # ── 정합성 요약 (총입고 = PENDING대기 + 현재재고 + 출고누계) ──
        # BUG FIX (v8.7.0): total_inbound_kg → 전체 initial_weight 기준, pending_kg 분리 표시
        # PENDING 톤백은 창고 미반입 → current_stock_kg 제외, pending_kg로 별도 집계
        total_inbound_kg = c.execute("""
            SELECT COALESCE(SUM(initial_weight), 0) FROM inventory
        """).fetchone()[0]

        # PENDING 대기 중량 — 창고 미반입 (정합성 계산에서 별도 분리)
        pending_kg = c.execute("""
            SELECT COALESCE(SUM(weight), 0) FROM inventory_tonbag
            WHERE status = 'PENDING'
        """).fetchone()[0]

        # 현재 재고 중량 — AVAILABLE + RESERVED + RETURN, 샘플 포함
        current_stock_kg = c.execute("""
            SELECT COALESCE(SUM(weight), 0) FROM inventory_tonbag
            WHERE status IN ('AVAILABLE', 'RESERVED', 'RETURN')
        """).fetchone()[0]

        # 출고 작업 중 (PICKED: 차량 미출발, 취소 가능) — 별도 집계
        picked_kg = c.execute("""
            SELECT COALESCE(SUM(weight), 0) FROM inventory_tonbag
            WHERE status = 'PICKED'
        """).fetchone()[0]

        # 출고 누계 (SOLD 전용 — OUTBOUND/SHIPPED/CONFIRMED는 SOLD로 통합됨, b2d136e)
        outbound_total_kg = c.execute("""
            SELECT COALESCE(SUM(weight), 0) FROM inventory_tonbag
            WHERE status = 'SOLD'
        """).fetchone()[0]

        # diff = 총입고 - PENDING대기 - 현재재고 - PICKED - 출고누계 → 이상적으로 0
        diff_kg = round(
            float(total_inbound_kg)
            - float(pending_kg)
            - float(current_stock_kg)
            - float(picked_kg)
            - float(outbound_total_kg),
            1,
        )
        integrity = {
            "total_inbound_kg":  round(float(total_inbound_kg), 1),
            "pending_kg":        round(float(pending_kg), 1),
            "current_stock_kg":  round(float(current_stock_kg), 1),
            "picked_kg":         round(float(picked_kg), 1),
            "outbound_total_kg": round(float(outbound_total_kg), 1),
            "diff_kg":           diff_kg,
            "ok":                abs(diff_kg) <= 1.0,
        }

        # LOT 행 기준 합계 (엑셀 «LOT 재고현황» 순중량/현재중량 합과 동일 — 샘플은 보통 순중량−현재중량 차이로 반영)
        _nw_sum, _cw_sum = c.execute(
            """
            SELECT COALESCE(SUM(net_weight), 0), COALESCE(SUM(current_weight), 0)
            FROM inventory
            WHERE status != 'PENDING'
            """
        ).fetchone()
        _nw_sum = float(_nw_sum or 0)
        _cw_sum = float(_cw_sum or 0)
        _sample_tb = c.execute(
            """
            SELECT COALESCE(SUM(weight), 0) FROM inventory_tonbag
            WHERE COALESCE(is_sample, 0) = 1
              AND status IN ('AVAILABLE', 'RESERVED', 'RETURN')
            """
        ).fetchone()[0]
        lot_weight_summary = {
            "sum_net_weight_kg": round(_nw_sum, 1),
            "sum_current_weight_kg": round(_cw_sum, 1),
            "gap_net_minus_current_kg": round(_nw_sum - _cw_sum, 1),
            "sum_net_mt": round(_nw_sum / 1000.0, 3),
            "sum_current_mt": round(_cw_sum / 1000.0, 3),
            "sample_tonbags_in_stock_kg": round(float(_sample_tb or 0), 1),
        }

        db.close()

        return {
            # 기존 호환 필드
            "total_lots":      total_lots,
            "total_tbags":     total_tbags,
            "stock_lots":      stock_lots,
            "sold_lots":       sold_lots,
            "total_weight_mt": round(total_wt / 1000.0, 2),
            # v9.4: 톤백 레벨 정확한 상태별 무게
            "available_mt":    round(avail_wt  / 1000.0, 3),
            "reserved_mt":     round(reserved_wt / 1000.0, 3),
            "picked_mt":       round(picked_wt  / 1000.0, 3),
            # 신규: 5단계 상태 요약
            "status_summary":  status_summary,
            # 신규: 제품x상태 매트릭스
            "product_matrix":  product_matrix,
            # 신규: 정합성 검증
            "integrity":       integrity,
            # LOT 목록/엑셀과 동일한 중량 합계 (순중량 vs 현재중량·샘플 톤백)
            "lot_weight_summary": lot_weight_summary,
        }
    except Exception as e:
        logger.error("[dashboard/stats] 집계 실패: %s", e, exc_info=True)
        return {"error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET /api/dashboard/alerts — ALERTS 패널 (v8.6.7 추가)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.get("/alerts")
def get_alerts():
    """
    재고 알림 패널 (v8.6.7 신규).

    조건:
      - 무중량(weight=0) 톤백 → CRITICAL
      - 위치(location) 미배정 톤백 → WARNING
      - 7일 이상 미동작 LOT → INFO

    Response: {"alerts": [{level, message, count}, ...], "total": N}
    """
    try:
        db_path = _get_db_path()
        con = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=3000")
        c = con.cursor()

        alerts = []

        # ① 무중량 톤백 (CRITICAL)
        zero_wt = c.execute(
            "SELECT COUNT(*) FROM inventory_tonbag "
            "WHERE COALESCE(weight, 0) <= 0 AND status = 'AVAILABLE'"
        ).fetchone()[0]
        if zero_wt > 0:
            alerts.append({
                "level": "critical",
                "message": f"무중량 톤백 {zero_wt}개 발견",
                "count": zero_wt,
            })

        # ② 위치 미배정 톤백 (WARNING)
        no_loc = c.execute(
            "SELECT COUNT(*) FROM inventory_tonbag "
            "WHERE (location IS NULL OR location = '') "
            "AND status = 'AVAILABLE'"
        ).fetchone()[0]
        if no_loc > 0:
            alerts.append({
                "level": "warning",
                "message": f"위치 미배정 톤백 {no_loc}개",
                "count": no_loc,
            })

        # ③ 7일 미동작 LOT (INFO)
        stale = c.execute("""
            SELECT COUNT(DISTINCT inventory_id) FROM inventory_tonbag
            WHERE status = 'AVAILABLE'
              AND COALESCE(updated_at, created_at, '1970-01-01')
                  < DATE('now', '-7 days', 'localtime')
        """).fetchone()[0]
        if stale > 0:
            alerts.append({
                "level": "info",
                "message": f"7일 이상 미동작 LOT {stale}개",
                "count": stale,
            })

        con.close()

        return {
            "alerts": alerts,
            "total": len(alerts),
            "generated_at": datetime.now(KST).isoformat(),
        }
    except Exception as e:
        logger.error("[dashboard/alerts] 집계 실패: %s", e, exc_info=True)
        return {"alerts": [], "total": 0, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET /api/dashboard/sidebar-counts  — 사이드바 배지용 경량 집계
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.get("/sidebar-counts")
def get_sidebar_counts():
    """
    사이드바 배지용 경량 API (v8.7.0 확장).
    inventory_tonbag.status 기준 — PENDING/SOLD 포함, 샘플 분리.

    Response:
        pending / available / reserved / picked / sold / return / total
        각각: { bags: int, mt: float, sample_bags: int }
    """
    try:
        db_path = _get_db_path()
        con = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=3000")
        c = con.cursor()

        rows = c.execute("""
            SELECT
                status,
                COUNT(*)                                                      AS bags,
                COALESCE(SUM(weight), 0) / 1000.0                            AS mt,
                SUM(CASE WHEN COALESCE(is_sample, 0) = 1 THEN 1 ELSE 0 END) AS sample_bags
            FROM inventory_tonbag
            WHERE status IN ('PENDING', 'AVAILABLE', 'RESERVED', 'PICKED', 'SOLD', 'RETURN')
            GROUP BY status
        """).fetchall()
        con.close()

        result = {
            "pending":   {"bags": 0, "mt": 0.0, "sample_bags": 0},
            "available": {"bags": 0, "mt": 0.0, "sample_bags": 0},
            "reserved":  {"bags": 0, "mt": 0.0, "sample_bags": 0},
            "picked":    {"bags": 0, "mt": 0.0, "sample_bags": 0},
            "sold":      {"bags": 0, "mt": 0.0, "sample_bags": 0},
            "return":    {"bags": 0, "mt": 0.0, "sample_bags": 0},
        }
        for status, bags, mt, sample_bags in rows:
            key = status.lower()
            if key in result:
                result[key] = {
                    "bags":        int(bags),
                    "mt":          round(float(mt), 2),
                    "sample_bags": int(sample_bags),
                }

        # total = PENDING 제외 재고 합계 (Available + Reserved + Picked + Return)
        inv_keys = ["available", "reserved", "picked", "return"]
        total_bags = sum(result[k]["bags"] for k in inv_keys)
        total_mt   = round(sum(result[k]["mt"]  for k in inv_keys), 2)
        result["total"] = {"bags": total_bags, "mt": total_mt, "sample_bags": 0}
        return {"ok": True, "data": result}
    except Exception as exc:
        logger.error("[dashboard/sidebar-counts] 집계 실패: %s", exc, exc_info=True)
        return {"ok": False, "error": str(exc)}
