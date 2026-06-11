"""
SQM v8.6.6 - Inventory / Allocation / Tonbag / Scan endpoints
GET  /api/inventory          사이드바 Inventory 탭 데이터
GET  /api/allocation         사이드바 Allocation 탭 데이터
GET  /api/tonbags            톤백 리스트
POST /api/scan/process       바코드 스캔 처리
GET  /api/health             시스템 헬스체크
"""
import sqlite3, os, sys, logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query as QP, HTTPException, Body
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
    db.execute("PRAGMA journal_mode=WAL")    # [fix B-5] 동시 read/write 허용
    db.execute("PRAGMA busy_timeout=3000")   # [fix B-5] 잠금 충돌 3초 대기
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
                -- v9.4: 톤백 레벨 상태별 무게 (MT)
                ROUND((SELECT COALESCE(SUM(t.weight),0) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.status = 'AVAILABLE' AND t.is_sample = 0
                ) / 1000.0, 3) AS avail_mt,
                ROUND((SELECT COALESCE(SUM(t.weight),0) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.status = 'RESERVED' AND t.is_sample = 0
                ) / 1000.0, 3) AS reserved_mt,
                ROUND((SELECT COALESCE(SUM(t.weight),0) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.status = 'PICKED' AND t.is_sample = 0
                ) / 1000.0, 3) AS picked_mt,
                (SELECT COUNT(*) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.status = 'AVAILABLE' AND t.is_sample = 0
                ) AS tb_avail,
                (SELECT COUNT(*) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.status = 'RESERVED' AND t.is_sample = 0
                ) AS tb_reserved,
                (SELECT COUNT(*) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.status = 'PICKED' AND t.is_sample = 0
                ) AS tb_picked,
                (SELECT COUNT(*) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.is_sample = 0
                ) AS total_bags,
                (SELECT COUNT(*) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.status IN ('SOLD','CONFIRMED','SHIPPED') AND t.is_sample = 0
                ) AS tb_sold,
                (SELECT COUNT(*) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.is_sample = 1
                   AND t.status IN ('AVAILABLE','RESERVED','PICKED','RETURN')
                ) AS sample_bags,
                ROUND((SELECT COALESCE(SUM(t.weight),0) FROM inventory_tonbag t
                 WHERE t.lot_no = i.lot_no AND t.is_sample = 1
                   AND t.status IN ('AVAILABLE','RESERVED','PICKED','RETURN')
                ) / 1000.0, 3) AS sample_weight_mt,
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
                i.remarks,
                i.lot_sqm,
                i.product_code,
                i.vessel,
                i.voyage
            FROM inventory i
            WHERE 1=1
        """
        params = []
        if status:
            status_norm = str(status).strip().upper()
            if status_norm == "AVAILABLE":
                sql += """
                    AND COALESCE(i.status, '') = ?
                    AND NOT EXISTS (
                        SELECT 1
                          FROM inventory_tonbag t
                         WHERE t.lot_no = i.lot_no
                           AND t.status IN ('RESERVED','PICKED','SOLD','SHIPPED','CONFIRMED','DEPLETED')
                    )
                    AND NOT EXISTS (
                        SELECT 1
                          FROM allocation_plan ap
                         WHERE ap.lot_no = i.lot_no
                           AND (
                               ap.status IN ('RESERVED','PICKED','SOLD','STAGED','PENDING_APPROVAL')
                               OR COALESCE(ap.workflow_status, '') IN ('PENDING_APPROVAL','APPROVED')
                           )
                    )
                """
                params.append("AVAILABLE")
            elif status_norm == "RESERVED":
                sql += """
                    AND (
                        COALESCE(i.status, '') = ?
                        OR EXISTS (
                            SELECT 1
                              FROM inventory_tonbag t
                             WHERE t.lot_no = i.lot_no
                               AND t.status = 'RESERVED'
                        )
                        OR EXISTS (
                            SELECT 1
                              FROM allocation_plan ap
                             WHERE ap.lot_no = i.lot_no
                               AND ap.status = 'RESERVED'
                        )
                    )
                """
                params.append("RESERVED")
            else:
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
# GET /api/inventory/unallocated-tonbags  (v8.7.0 위치 매핑 워크플로우)
#   location 미배정 톤백 + LOT 단위 진행률 통계
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@inv_router.get("/unallocated-tonbags",
                summary="📍 위치 미배정 톤백 + LOT 진행률")
def unallocated_tonbags(lot_no: Optional[str] = QP(None),
                        limit:  int = QP(2000)):
    """
    위치(location)가 비어 있는 활성 톤백 목록 + LOT별 진행률.

    Args:
      lot_no: 특정 LOT 만 조회 (선택)
      limit:  반환 행 수 제한 (기본 2000)

    Returns:
      {
        ok: true,
        data: {
          tonbags: [
            { id, tonbag_uid, lot_no, sub_lt, tonbag_no, weight_kg,
              status, product, packing_type }, ...
          ],
          lot_progress: [
            { lot_no, product, packing_type, total_tonbags,
              allocated, unallocated, progress_pct }, ...
          ],
          summary: { total, allocated, unallocated, progress_pct,
                     lot_count, lot_done, lot_partial, lot_pending }
        }
      }
    """
    try:
        db = _db()
        try:
            where = ["COALESCE(t.is_sample, 0) = 0",
                     "t.status IN ('AVAILABLE','PICKED','RESERVED','PENDING')"]
            params: list = []
            if lot_no:
                where.append("t.lot_no = ?")
                params.append(lot_no)
            where_sql = " AND ".join(where)

            # 미배정 톤백 리스트 (location IS NULL OR '')
            sql_un = (
                "SELECT t.id, t.tonbag_uid, t.lot_no, t.sub_lt, "
                "       t.tonbag_no, COALESCE(t.weight_kg,0) AS weight_kg, "
                "       t.status, i.product, COALESCE(i.packing_type,'') AS packing_type "
                "  FROM inventory_tonbag t "
                "  LEFT JOIN inventory i ON i.lot_no = t.lot_no "
                f" WHERE {where_sql} "
                "   AND (t.location IS NULL OR TRIM(t.location) = '') "
                " ORDER BY t.lot_no, t.sub_lt "
                f" LIMIT {int(limit)} "
            )
            tonbags = _rows(db.execute(sql_un, params))

            # LOT 별 진행률 (총/배정/미배정)
            sql_pg = (
                "SELECT t.lot_no, "
                "       COALESCE(i.product,'') AS product, "
                "       COALESCE(i.packing_type,'') AS packing_type, "
                "       COUNT(*) AS total_tonbags, "
                "       SUM(CASE WHEN t.location IS NOT NULL "
                "                  AND TRIM(t.location) != '' "
                "                THEN 1 ELSE 0 END) AS allocated "
                "  FROM inventory_tonbag t "
                "  LEFT JOIN inventory i ON i.lot_no = t.lot_no "
                f" WHERE {where_sql} "
                " GROUP BY t.lot_no "
                " ORDER BY t.lot_no "
            )
            pg_rows = _rows(db.execute(sql_pg, params))
            lot_progress = []
            lot_done = lot_partial = lot_pending = 0
            for r in pg_rows:
                total = int(r['total_tonbags'] or 0)
                alloc = int(r['allocated'] or 0)
                un    = total - alloc
                pct   = round((alloc / total * 100), 1) if total else 0.0
                if alloc == total and total > 0:
                    lot_done += 1
                elif alloc == 0:
                    lot_pending += 1
                else:
                    lot_partial += 1
                lot_progress.append({
                    'lot_no':        r['lot_no'],
                    'product':       r['product'],
                    'packing_type':  r['packing_type'],
                    'total_tonbags': total,
                    'allocated':     alloc,
                    'unallocated':   un,
                    'progress_pct':  pct,
                })

            # 전체 요약
            total_all = sum(p['total_tonbags'] for p in lot_progress)
            alloc_all = sum(p['allocated']     for p in lot_progress)
            unall_all = total_all - alloc_all
            sum_pct   = round((alloc_all / total_all * 100), 1) if total_all else 0.0

            return {"ok": True, "data": {
                "tonbags": tonbags,
                "lot_progress": lot_progress,
                "summary": {
                    "total":          total_all,
                    "allocated":      alloc_all,
                    "unallocated":    unall_all,
                    "progress_pct":   sum_pct,
                    "lot_count":      len(lot_progress),
                    "lot_done":       lot_done,
                    "lot_partial":    lot_partial,
                    "lot_pending":    lot_pending,
                },
                "lot_no_filter": lot_no,
                "limit_applied": limit,
            }}
        finally:
            db.close()
    except Exception as e:
        log.error(f"unallocated-tonbags error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POST /api/inventory/assign-location  (v8.7.0 단건 위치 배정)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@inv_router.post("/assign-location",
                 summary="📍 단건 위치 배정 (실시간 검증)")
def assign_location(payload: dict = Body(...)):
    """
    Payload:
      { tonbag_id: int, location: str, operator?: str, note?: str }

    동작:
      1) location 형식 검증 (G5-04-01-07)
      2) 셀 capacity 사전 점검 (capacity 초과면 차단)
      3) inventory_tonbag.location UPDATE
      4) stock_movement (ALLOCATE) + audit_log (LOCATION_ASSIGN)
      5) 사후 무결성 검증 (HALF/OVER/MIXED 감지)
    """
    try:
        from datetime import datetime
        from engine_modules.warehouse_cell_logic import (
            validate_cell_location, get_cell_state, check_cell_invariants,
        )

        tonbag_id = payload.get('tonbag_id')
        location  = (payload.get('location') or '').strip().upper()
        operator  = (payload.get('operator') or 'user').strip()
        note      = (payload.get('note') or '').strip()

        if not tonbag_id:
            raise HTTPException(400, 'tonbag_id 필수')
        if not location:
            raise HTTPException(400, 'location 필수')

        v = validate_cell_location(location)
        if not v.get('ok'):
            return {"ok": False, "error": f"위치 형식 오류: {v.get('reason')}", "data": None}

        db = _db()
        try:
            row = db.execute(
                "SELECT id, lot_no, sub_lt, COALESCE(weight_kg,0) AS w, "
                "       COALESCE(location,'') AS loc, status "
                "  FROM inventory_tonbag WHERE id=?",
                (tonbag_id,)
            ).fetchone()
            if not row:
                return {"ok": False, "error": f"톤백 id={tonbag_id} 없음", "data": None}
            tb = dict(row)
            from_loc = tb['loc']
            if from_loc and from_loc == location:
                return {"ok": False, "error": "현재 위치와 동일", "data": {"tonbag_id": tonbag_id}}

            # 사전 capacity 점검 — 신규 location에 들어갈 자리 있는지
            pre_state = get_cell_state(db, location)
            if pre_state['state'] == 'OCCUPIED' and pre_state['active_count'] >= pre_state['capacity']:
                return {"ok": False,
                        "error": f"셀 가득 참 ({pre_state['active_count']}/{pre_state['capacity']})",
                        "data": {"cell_state": pre_state}}

            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            db.execute(
                "UPDATE inventory_tonbag SET location=?, location_updated_at=?, updated_at=? "
                "WHERE id=?",
                (location, ts, ts, tonbag_id)
            )
            # stock_movement (ALLOCATE = 첫 배정, RELOCATE = 재이동)
            move_type = 'ALLOCATE' if not from_loc else 'RELOCATE'
            db.execute(
                "INSERT INTO stock_movement "
                "    (lot_no, sub_lt, movement_type, qty_kg, "
                "     from_location, to_location, reason_code, operator, remarks, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'LOC_ASSIGN', ?, ?, ?)",
                (tb['lot_no'], tb['sub_lt'], move_type, tb['w'],
                 from_loc or '', location, operator,
                 note or 'v8.7.0 위치 매핑', ts)
            )
            db.execute(
                "INSERT INTO audit_log "
                "    (event_type, event_data, user_note, created_by, created_at) "
                "VALUES ('LOCATION_ASSIGN', ?, ?, ?, ?)",
                (f'{{"tonbag_id":{tonbag_id},"lot_no":"{tb["lot_no"]}",'
                 f'"sub_lt":{tb["sub_lt"]},"from":"{from_loc}","to":"{location}"}}',
                 note or f'위치 배정 {from_loc or "(미배정)"} → {location}',
                 operator, ts)
            )
            db.commit()

            # 사후 무결성 검증
            warns = []
            for chk in {from_loc, location}:
                if not chk:
                    continue
                rep = check_cell_invariants(db, chk)
                if not rep['ok']:
                    warns.extend(rep['warnings'])

            return {"ok": True, "data": {
                "tonbag_id":      tonbag_id,
                "lot_no":         tb['lot_no'],
                "sub_lt":         tb['sub_lt'],
                "from_location":  from_loc,
                "to_location":    location,
                "movement_type":  move_type,
                "cell_warnings":  warns,
                "message":        f"{tb['lot_no']}-{tb['sub_lt']} → {location} 배정 완료",
            }}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"assign-location error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POST /api/inventory/assign-locations-bulk  (v8.7.0 일괄 위치 배정)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@inv_router.post("/assign-locations-bulk",
                 summary="📍 일괄 위치 배정")
def assign_locations_bulk(payload: dict = Body(...)):
    """
    Payload:
      { assignments: [{tonbag_id, location}, ...], operator?: str, note?: str }

    각 항목을 순차 처리 — 실패한 건은 errors 배열에 누적, 성공한 건은 계속.
    트랜잭션 단위는 항목별 — 일부 실패해도 나머지 진행.
    """
    try:
        items = payload.get('assignments') or []
        operator = (payload.get('operator') or 'user').strip()
        note     = (payload.get('note') or '').strip()
        if not isinstance(items, list) or not items:
            raise HTTPException(400, 'assignments 필수 (list)')

        success_list = []
        error_list   = []
        for idx, it in enumerate(items):
            sub_payload = {
                'tonbag_id': it.get('tonbag_id'),
                'location':  it.get('location'),
                'operator':  operator,
                'note':      note or f'bulk #{idx + 1}',
            }
            try:
                res = assign_location(sub_payload)
                if res.get('ok'):
                    success_list.append({
                        'index':     idx,
                        'tonbag_id': it.get('tonbag_id'),
                        'data':      res.get('data'),
                    })
                else:
                    error_list.append({
                        'index':     idx,
                        'tonbag_id': it.get('tonbag_id'),
                        'reason':    res.get('error') or 'unknown',
                    })
            except HTTPException as he:
                error_list.append({
                    'index':     idx,
                    'tonbag_id': it.get('tonbag_id'),
                    'reason':    he.detail,
                })
            except Exception as e:
                error_list.append({
                    'index':     idx,
                    'tonbag_id': it.get('tonbag_id'),
                    'reason':    str(e),
                })

        return {"ok": True, "data": {
            "total":         len(items),
            "success_count": len(success_list),
            "fail_count":    len(error_list),
            "success":       success_list,
            "errors":        error_list,
            "message":       f"성공 {len(success_list)}건 / 실패 {len(error_list)}건",
        }}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"assign-locations-bulk error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POST /api/inventory/clear-lot-locations   (v8.7.0)
# 잘못 배정된 톤백 위치 일괄 초기화 (location → NULL)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@inv_router.post("/clear-lot-locations", summary="🧹 LOT 톤백 위치 초기화")
def clear_lot_locations(payload: dict = Body(...)):
    """
    지정 LOT 들의 inventory_tonbag.location 을 NULL 로 초기화.
    payload: { lot_nos: ["LOT-001", "LOT-002", ...] }
    잘못 임포트된 위치재고 엑셀을 batch 삭제 후 위치도 되돌릴 때 사용.
    """
    lot_nos = payload.get("lot_nos") or []
    if not lot_nos:
        raise HTTPException(400, "lot_nos 가 비어 있습니다")
    if not isinstance(lot_nos, list):
        raise HTTPException(400, "lot_nos 는 배열이어야 합니다")

    try:
        con = _db()
        try:
            ts = datetime.now().isoformat(timespec="seconds")
            cleared_total = 0
            results = []
            for lot_no in lot_nos:
                lot_no = str(lot_no).strip()
                if not lot_no:
                    continue
                cur = con.execute(
                    "UPDATE inventory_tonbag SET location=NULL, updated_at=? WHERE lot_no=? AND location IS NOT NULL",
                    (ts, lot_no),
                )
                cleared_total += cur.rowcount
                results.append({"lot_no": lot_no, "cleared": cur.rowcount})
            con.commit()
        finally:
            con.close()
        log.info(f"[clear-lot-locations] lots={len(lot_nos)} tonbags_cleared={cleared_total}")
        return {
            "ok": True,
            "lot_count": len(lot_nos),
            "tonbag_cleared": cleared_total,
            "results": results,
            "message": f"{len(lot_nos)}개 LOT, 톤백 {cleared_total}개 위치 초기화 완료",
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"clear-lot-locations error: {e}")
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
# [Sprint 1-1-D] PATCH /api/allocation/{lot_no} — 행 필드 업데이트
# v864-2 AllocationDialog 인라인 편집 워크플로우 포팅
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_ALLOC_EDITABLE_FIELDS = {
    "customer", "sale_ref", "qty_mt", "outbound_date", "status",
}


@alloc_router.patch("/{lot_no}")
def update_allocation(lot_no: str, updates: Dict[str, Any] = Body(...)):
    """
    allocation_plan 행의 허용된 필드를 업데이트.
    Body: {field_name: value, ...}

    허용 필드: customer, sale_ref, qty_mt, outbound_date, status
    (lot_no/sap_no/product 는 외래키·조인 영향으로 편집 불허)
    """
    fields = {k: v for k, v in (updates or {}).items() if k in _ALLOC_EDITABLE_FIELDS}
    if not fields:
        raise HTTPException(
            400,
            f"허용된 필드 없음. 편집 가능: {sorted(_ALLOC_EDITABLE_FIELDS)}"
        )
    # qty_mt 는 numeric 강제
    if "qty_mt" in fields:
        try:
            fields["qty_mt"] = float(fields["qty_mt"])
        except (TypeError, ValueError):
            raise HTTPException(400, "qty_mt 는 숫자여야 합니다")
    sets = ", ".join(f"{k}=?" for k in fields.keys())
    values = list(fields.values()) + [lot_no]
    try:
        db = _db()
        cursor = db.execute(
            f"UPDATE allocation_plan SET {sets}, created_at=datetime('now') WHERE lot_no=?",
            values
        )
        if cursor.rowcount == 0:
            db.close()
            raise HTTPException(404, f"allocation_plan 에서 {lot_no} 찾지 못함")
        db.commit(); db.close()
        return {"success": True, "lot_no": lot_no, "updated_fields": list(fields.keys())}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"PATCH /api/allocation/{lot_no} error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [Sprint 1-1-E] POST /api/allocation/{lot_no}/pick — RESERVED → PICKED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@alloc_router.post("/{lot_no}/pick")
def pick_allocation(lot_no: str):
    """배정 → 출고 실행 (RESERVED → PICKED)."""
    try:
        db = _db()
        cursor = db.execute(
            """UPDATE allocation_plan
               SET status='PICKED', executed_at=datetime('now')
               WHERE lot_no=? AND status='RESERVED'""",
            (lot_no,)
        )
        changes = cursor.rowcount
        db.commit(); db.close()
        if changes == 0:
            raise HTTPException(404, f"{lot_no}: RESERVED 상태가 아니거나 존재하지 않음")
        return {"success": True, "lot_no": lot_no, "message": f"{lot_no} → PICKED"}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"POST /api/allocation/{lot_no}/pick error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [Sprint 1-1-E] POST /api/allocation/{lot_no}/confirm — PICKED → SOLD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@alloc_router.post("/{lot_no}/confirm")
def confirm_allocation(lot_no: str):
    """출고 확정 (PICKED → SOLD)."""
    try:
        db = _db()
        cursor = db.execute(
            """UPDATE allocation_plan
               SET status='SOLD', executed_at=datetime('now')
               WHERE lot_no=? AND status='PICKED'""",
            (lot_no,)
        )
        changes = cursor.rowcount
        # inventory 테이블 상태도 SOLD 로
        db.execute(
            "UPDATE inventory SET status='SOLD' WHERE lot_no=?",
            (lot_no,)
        )
        db.commit(); db.close()
        if changes == 0:
            raise HTTPException(404, f"{lot_no}: PICKED 상태가 아니거나 존재하지 않음")
        return {"success": True, "lot_no": lot_no, "message": f"{lot_no} → SOLD"}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"POST /api/allocation/{lot_no}/confirm error: {e}")
        raise HTTPException(500, str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [Sprint 1-1-E] POST /api/allocation/{lot_no}/reset — LOT 배정 초기화
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@alloc_router.post("/{lot_no}/reset")
def reset_allocation(lot_no: str):
    """
    LOT 배정 완전 초기화.
    - allocation_plan 에서 해당 lot_no 행 DELETE
    - inventory 테이블 status 를 AVAILABLE 로 원복 (SOLD 가 아닌 경우만)
    """
    try:
        db = _db()
        # inventory status 가 이미 SOLD 면 보호 (출고 완료된 건 reset 불가)
        row = db.execute("SELECT status FROM inventory WHERE lot_no=?", (lot_no,)).fetchone()
        if row and row[0] == "SOLD":
            raise HTTPException(409, f"{lot_no}: SOLD 상태는 reset 불가 (반품으로 처리하세요)")
        del_cur = db.execute("DELETE FROM allocation_plan WHERE lot_no=?", (lot_no,))
        deleted = del_cur.rowcount
        db.execute(
            "UPDATE inventory SET status='AVAILABLE', sold_to=NULL, sale_ref=NULL WHERE lot_no=? AND status!='SOLD'",
            (lot_no,)
        )
        db.commit(); db.close()
        if deleted == 0:
            return {"success": True, "lot_no": lot_no, "message": f"{lot_no}: 배정 기록 없음 (inventory만 초기화)"}
        return {"success": True, "lot_no": lot_no, "message": f"{lot_no} 배정 완전 초기화 ({deleted}건 삭제)"}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"POST /api/allocation/{lot_no}/reset error: {e}")
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
        # 위치재고 Import 테이블(lot_location_map)이 없는 DB에서도 아래 JOIN 이
        # 깨지지 않도록 보장 — location_map_api 의 스키마 생성 로직 재사용
        try:
            from backend.api.location_map_api import _ensure_tables as _ensure_locmap
            _ensure_locmap(db)
        except Exception:
            pass
        c  = db.cursor()
        # location: 톤백별 위치(t.location)가 있으면 우선, 없으면 위치재고 Import
        #           최신 batch 의 LOT 단위 셀 매핑(map_location)으로 대체.
        sql = """
            SELECT
                t.sub_lt,
                t.lot_no,
                t.sap_no,
                t.bl_no,
                t.inbound_date,
                ROUND(t.weight / 1000.0, 3) AS weight,
                t.status,
                COALESCE(NULLIF(TRIM(t.location), ''), lm.map_location) AS location,
                lm.map_location,
                t.picked_to     AS container,
                i.product,
                t.tonbag_uid,
                t.tonbag_no,
                COALESCE(t.is_sample, 0) AS is_sample
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON i.lot_no = t.lot_no
            LEFT JOIN (
                SELECT lot_no, GROUP_CONCAT(location, ', ') AS map_location
                FROM (
                    SELECT lot_no, location
                    FROM lot_location_map
                    WHERE batch_id = (SELECT MAX(id) FROM lot_location_import_batch)
                    ORDER BY lot_no, location
                )
                GROUP BY lot_no
            ) lm ON lm.lot_no = t.lot_no
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
# POST /api/scan/bulk-upload  — 바코드 스캔 결과 CSV/Excel 업로드 (Stage 3)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from fastapi import UploadFile, File as FileField
import io, pathlib as _pathlib

@scan_router.post("/bulk-upload")
async def scan_bulk_upload(file: UploadFile = FileField(...), action: str = "lookup"):
    """
    CSV/Excel 파일 업로드 → tonbag_uid / sub_lt 일괄 조회.
    action=lookup: 조회만 / action=outbound|return|pick|available: 상태 전환
    """
    try:
        content = await file.read()
        ext = _pathlib.Path(file.filename or "upload.csv").suffix.lower()
        try:
            import pandas as pd
        except ImportError:
            return {"ok": False, "message": "pandas not installed"}
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(io.BytesIO(content), header=0, dtype=str)
        else:
            try:
                df = pd.read_csv(io.StringIO(content.decode("utf-8")), header=0, dtype=str)
            except Exception:
                df = pd.read_csv(io.StringIO(content.decode("cp949", errors="replace")), header=0, dtype=str)
        df.columns = [str(c).strip().lower() for c in df.columns]
        uid_col = None
        for cand in ["tonbag_uid", "uid", "sub_lt", "barcode", "scan_id", df.columns[0]]:
            if cand in df.columns:
                uid_col = cand
                break
        if uid_col is None:
            return {"ok": False, "message": "인식 가능한 UID 컬럼 없음 (tonbag_uid / sub_lt / barcode)"}
        uids = df[uid_col].dropna().str.strip().unique().tolist()
        if not uids:
            return {"ok": False, "message": "유효한 UID 없음"}
        db = _db()
        results = []
        for uid in uids:
            row = db.execute("""
                SELECT t.id, t.sub_lt, t.lot_no, t.tonbag_uid, t.status,
                       t.weight, t.location, i.product, i.warehouse
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON i.lot_no = t.lot_no
                WHERE t.tonbag_uid = ? OR t.sub_lt = ?
                LIMIT 1
            """, (uid, uid)).fetchone()
            if row:
                r = dict(row)
                r["input_uid"] = uid
                r["matched"] = True
                if action != "lookup":
                    STATUS_TRANS = {
                        "outbound": ("PICKED", "SOLD"),
                        "return": ("RETURN"),
                        "pick": ("AVAILABLE", "PICKED"),
                        "available": (None, "AVAILABLE"),
                    }
                    trans = STATUS_TRANS.get(action.lower())
                    if trans:
                        src, dst = trans
                        if src is None or r.get("status") == src:
                            db.execute("UPDATE inventory_tonbag SET status=? WHERE id=?", (dst, r["id"]))
                            r["status_changed"] = f"{src or '*'} -> {dst}"
                r["weight"] = float(r.get("weight") or 0)
            else:
                r = {"input_uid": uid, "matched": False, "lot_no": None, "status": None, "weight": 0}
            results.append(r)
        db.commit()
        db.close()
        matched = sum(1 for r in results if r.get("matched"))
        not_matched = len(results) - matched
        return {"ok": True, "message": f"처리 완료: {matched} 매칭 / {not_matched} 미매칭",
                "results": results, "matched_count": matched, "not_matched_count": not_matched, "action": action}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("scan bulk-upload error: %s", e)
        return {"ok": False, "message": str(e)}


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
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "engine_count": 0}
