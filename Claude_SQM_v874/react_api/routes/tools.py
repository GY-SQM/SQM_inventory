# -*- coding: utf-8 -*-
"""도구 API — Excel 내보내기, 정합성 체크."""
import io
import csv
import os
import glob as _glob
import logging
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Query, Header, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


def _csv_streaming_response(headers: list, rows: list, filename: str) -> StreamingResponse:
    """UTF-8 BOM CSV StreamingResponse 생성 헬퍼."""
    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM — Excel 한글 호환
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row.get(h.lower(), '') if isinstance(row, dict) else '' for h in headers])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.get("/export-lot-list")
def export_lot_list(
    status: Optional[str] = Query(None),
    product_name: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
):
    """LOT 리스트 CSV 내보내기 (v864 LOT 리스트 전용 export)."""
    with get_db() as db:
        conditions = ["1=1"]
        params: list = []
        if status:
            conditions.append("i.status = ?")
            params.append(status.upper())
        if product_name:
            conditions.append("i.product_name = ?")
            params.append(product_name)
        if keyword:
            conditions.append("(i.lot_no LIKE ? OR i.bl_no LIKE ? OR i.sap_no LIKE ?)")
            params.extend([f"%{keyword}%"] * 3)

        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT i.lot_no, i.bl_no, i.sap_no, i.product_name, i.status,
                   i.current_weight, i.net_weight,
                   COUNT(t.id) AS bag_count,
                   SUM(CASE WHEN COALESCE(t.is_sample,0)=1 THEN 1 ELSE 0 END) AS sample_flag,
                   i.inbound_date
            FROM inventory i
            LEFT JOIN inventory_tonbag t ON i.lot_no = t.lot_no
            {where}
            GROUP BY i.lot_no
            ORDER BY i.inbound_date DESC, i.lot_no
        """
        rows = db.fetchall(sql, tuple(params))

    headers = ['LOT_NO', 'BL_NO', 'SAP_NO', 'PRODUCT_NAME', 'STATUS',
               'CURRENT_WEIGHT', 'NET_WEIGHT', 'BAG_COUNT', 'SAMPLE_FLAG', 'INBOUND_DATE']
    dt = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"SQM_LOT_list_{dt}.csv"
    return _csv_streaming_response(headers, rows, filename)


@router.get("/export-tonbag-list")
def export_tonbag_list(
    status: Optional[str] = Query(None),
    lot_no: Optional[str] = Query(None),
):
    """톤백리스트 CSV 내보내기 (v864 톤백리스트 전용 export)."""
    with get_db() as db:
        conditions = ["1=1"]
        params: list = []
        if status:
            conditions.append("t.status = ?")
            params.append(status.upper())
        if lot_no:
            conditions.append("t.lot_no LIKE ?")
            params.append(f"%{lot_no}%")

        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT t.tonbag_no, t.lot_no, i.bl_no, t.location, t.status,
                   t.weight, COALESCE(t.is_sample, 0) AS sample_flag,
                   i.inbound_date, t.outbound_date
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON t.lot_no = i.lot_no
            {where}
            ORDER BY t.lot_no, t.sub_lt
        """
        rows = db.fetchall(sql, tuple(params))

    headers = ['TONBAG_NO', 'LOT_NO', 'BL_NO', 'LOCATION', 'STATUS',
               'WEIGHT', 'SAMPLE_FLAG', 'INBOUND_DATE', 'OUTBOUND_DATE']
    dt = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"SQM_tonbag_list_{dt}.csv"
    return _csv_streaming_response(headers, rows, filename)


@router.get("/export-logs")
def export_logs(
    log_type: Optional[str] = Query(None, description="audit/inventory/operation"),
    format: Optional[str] = Query("csv", description="csv/json"),
):
    """로그 CSV/JSON 내보내기."""
    with get_db() as db:
        # operation_log 테이블 시도, 없으면 빈 데이터
        try:
            sql = "SELECT * FROM operation_log ORDER BY created_at DESC LIMIT 5000"
            rows = db.fetchall(sql)
        except Exception:
            rows = []

    if not rows:
        # fallback: inventory 변경 로그
        try:
            with get_db() as db:
                rows = db.fetchall("SELECT lot_no, status, inbound_date as created_at FROM inventory ORDER BY inbound_date DESC LIMIT 5000")
        except Exception:
            rows = []

    dt = datetime.now().strftime('%Y%m%d_%H%M')

    if format == "json":
        import json
        content = json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)
        filename = f"SQM_logs_{dt}.json"
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # CSV
    headers = list(rows[0].keys()) if rows else ['no_data']
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row.get(h, '') for h in headers])
    output.seek(0)
    filename = f"SQM_logs_{dt}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/integrity-repair")
def integrity_repair():
    """DB 정합성 복구: inventory.status를 tonbag 다수결로 동기화."""
    with get_db() as db:
        repaired = []

        # inventory.status와 tonbag 상태 불일치 LOT 조회
        mismatch = db.fetchall("""
            SELECT i.lot_no, i.status as inv_status,
                   COUNT(CASE WHEN t.status='AVAILABLE' THEN 1 END) as avail_cnt,
                   COUNT(CASE WHEN t.status='RESERVED' THEN 1 END) as rsv_cnt,
                   COUNT(CASE WHEN t.status='PICKED' THEN 1 END) as picked_cnt,
                   COUNT(CASE WHEN t.status='OUTBOUND' THEN 1 END) as outbound_cnt,
                   COUNT(t.id) as total_cnt
            FROM inventory i
            JOIN inventory_tonbag t ON i.lot_no = t.lot_no
            GROUP BY i.lot_no
        """)

        for row in mismatch:
            lot = row['lot_no']
            total = row['total_cnt'] or 1
            # 다수결: 가장 많은 상태로 inventory.status 동기화
            counts = {
                'AVAILABLE': row['avail_cnt'],
                'RESERVED': row['rsv_cnt'],
                'PICKED': row['picked_cnt'],
                'OUTBOUND': row['outbound_cnt'],
            }
            dominant = max(counts, key=lambda k: counts[k])
            if counts[dominant] > total * 0.5 and dominant != row['inv_status']:
                db.execute(
                    "UPDATE inventory SET status=? WHERE lot_no=?",
                    (dominant, lot)
                )
                repaired.append({'lot_no': lot, 'old': row['inv_status'], 'new': dominant})

        db.commit()

    return {
        'success': True,
        'repaired_count': len(repaired),
        'details': repaired[:50],
        'generated_at': now_str(),
    }


@router.post("/reset-test-db")
def reset_test_db(
    x_confirm_reset: Optional[str] = Header(None, alias="X-Confirm-Reset"),
):
    """테스트 DB 초기화 (개발 전용 — production 차단)."""
    if x_confirm_reset != "CONFIRM_RESET":
        raise HTTPException(status_code=400, detail="X-Confirm-Reset 헤더가 필요합니다.")

    # production 환경 차단
    env = os.environ.get("SQM_ENV", "development").lower()
    if env in ("production", "prod"):
        raise HTTPException(status_code=403, detail="Production 환경에서는 실행할 수 없습니다.")

    tables_cleared = []
    _ALLOWED_RESET_TABLES = frozenset({"operation_log", "outbound_log", "return_log", "move_log"})
    with get_db() as db:
        for tbl in _ALLOWED_RESET_TABLES:
            try:
                if tbl not in _ALLOWED_RESET_TABLES:
                    continue  # 화이트리스트 외 테이블 차단
                db.execute(f"DELETE FROM {tbl}")  # noqa: S608 — tbl은 화이트리스트 검증 완료
                tables_cleared.append(tbl)
            except Exception:
                pass
        db.commit()

    return {
        'success': True,
        'message': f'{len(tables_cleared)}개 테이블 초기화 완료',
        'tables_cleared': tables_cleared,
        'generated_at': now_str(),
    }


@router.post("/backup/create")
def backup_create():
    """DB 백업 생성."""
    import shutil
    from pathlib import Path
    db_candidates = [
        Path("data/sqm.db"),
        Path("../data/sqm.db"),
    ]
    db_path = next((p for p in db_candidates if p.exists()), None)
    if not db_path:
        return {"success": False, "message": "DB 파일을 찾을 수 없습니다."}

    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    dt = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = backup_dir / f"sqm_backup_{dt}.db"
    shutil.copy2(db_path, dest)
    return {"success": True, "message": f"백업 생성: {dest.name}"}


@router.post("/db-optimize")
def db_optimize():
    """SQLite VACUUM + ANALYZE."""
    with get_db() as db:
        db.execute("VACUUM")
        db.execute("ANALYZE")
    return {"success": True, "message": "DB 최적화 완료"}


@router.get("/export/csv")
def export_csv(
    type: Optional[str] = Query(None, description="customs|rubyli|tonbag|integrated"),
    status: Optional[str] = Query(None),
    product_name: Optional[str] = Query(None),
):
    """재고 데이터를 type별 양식으로 CSV 내보내기."""
    dt = datetime.now().strftime('%Y%m%d_%H%M')

    with get_db() as db:
        # ── type별 분기 ────────────────────────────────────
        if type == 'customs':
            # 통관요청 양식: LOT + BL + 제품 + 중량 + 컨테이너
            sql = """
                SELECT i.lot_no, i.bl_no, i.sap_no, i.product_name,
                       i.net_weight, i.current_weight, i.container_no,
                       i.inbound_date, i.ship_date, i.arrival_date
                FROM inventory i ORDER BY i.inbound_date DESC
            """
            rows = db.fetchall(sql)
            headers = ['LOT_NO', 'BL_NO', 'SAP_NO', 'PRODUCT_NAME',
                       'NET_WEIGHT', 'CURRENT_WEIGHT', 'CONTAINER_NO',
                       'INBOUND_DATE', 'SHIP_DATE', 'ARRIVAL_DATE']
            filename = f"SQM_customs_{dt}.csv"

        elif type == 'rubyli':
            # 루비리 양식: 톤백 단위 상세
            sql = """
                SELECT t.tonbag_no, t.lot_no, i.bl_no, i.sap_no,
                       i.product_name, t.weight, t.location, t.status,
                       i.inbound_date
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON t.lot_no = i.lot_no
                WHERE t.status IN ('AVAILABLE','RESERVED')
                ORDER BY t.lot_no, t.sub_lt
            """
            rows = db.fetchall(sql)
            headers = ['TONBAG_NO', 'LOT_NO', 'BL_NO', 'SAP_NO',
                       'PRODUCT_NAME', 'WEIGHT', 'LOCATION', 'STATUS',
                       'INBOUND_DATE']
            filename = f"SQM_rubyli_{dt}.csv"

        elif type == 'tonbag':
            # 톤백 현황: 전체 톤백 목록
            sql = """
                SELECT t.tonbag_no, t.lot_no, t.sub_lt, i.bl_no,
                       i.product_name, t.weight, t.location, t.status,
                       COALESCE(t.is_sample, 0) AS is_sample,
                       i.inbound_date, t.outbound_date
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON t.lot_no = i.lot_no
                ORDER BY t.lot_no, t.sub_lt
            """
            rows = db.fetchall(sql)
            headers = ['TONBAG_NO', 'LOT_NO', 'SUB_LT', 'BL_NO',
                       'PRODUCT_NAME', 'WEIGHT', 'LOCATION', 'STATUS',
                       'IS_SAMPLE', 'INBOUND_DATE', 'OUTBOUND_DATE']
            filename = f"SQM_tonbag_report_{dt}.csv"

        elif type == 'integrated':
            # 통합 현황: LOT별 요약 + 톤백 수
            sql = """
                SELECT i.lot_no, i.bl_no, i.sap_no, i.product_name,
                       i.status, i.net_weight, i.current_weight,
                       COUNT(t.id) AS bag_count,
                       SUM(CASE WHEN t.status='AVAILABLE' THEN 1 ELSE 0 END) AS avail_bags,
                       SUM(CASE WHEN t.status='OUTBOUND' THEN 1 ELSE 0 END) AS out_bags,
                       i.inbound_date, i.container_no
                FROM inventory i
                LEFT JOIN inventory_tonbag t ON i.lot_no = t.lot_no
                GROUP BY i.lot_no
                ORDER BY i.inbound_date DESC
            """
            rows = db.fetchall(sql)
            headers = ['LOT_NO', 'BL_NO', 'SAP_NO', 'PRODUCT_NAME',
                       'STATUS', 'NET_WEIGHT', 'CURRENT_WEIGHT',
                       'BAG_COUNT', 'AVAIL_BAGS', 'OUT_BAGS',
                       'INBOUND_DATE', 'CONTAINER_NO']
            filename = f"SQM_integrated_{dt}.csv"

        else:
            # 기본: 전체 톤백 데이터
            conditions = []
            params = []
            if status:
                conditions.append("t.status = ?")
                params.append(status.upper())
            if product_name:
                conditions.append("i.product_name = ?")
                params.append(product_name)

            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            sql = f"""
                SELECT t.lot_no, t.tonbag_uid, t.tonbag_no, t.sub_lt,
                       i.product_name, i.sap_no, i.bl_no,
                       t.status, t.location, t.weight,
                       i.inbound_date, i.container_no
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON t.lot_no = i.lot_no
                {where}
                ORDER BY t.lot_no, t.sub_lt
            """
            rows = db.fetchall(sql, tuple(params))
            headers = ['LOT_NO', 'TONBAG_UID', 'TONBAG_NO', 'SUB_LT',
                       'PRODUCT', 'SAP_NO', 'BL_NO',
                       'STATUS', 'LOCATION', 'WEIGHT_KG',
                       'INBOUND_DATE', 'CONTAINER_NO']
            filename = f"sqm_export_{dt}.csv"

    return _csv_streaming_response(headers, rows, filename)


@router.get("/integrity-check")
def integrity_check():
    """DB 정합성 체크: 재고 무결성 확인."""
    with get_db() as db:
        issues = []

        # 1. inventory_tonbag에는 있지만 inventory에 없는 LOT
        orphan_tonbags = db.fetchall("""
            SELECT DISTINCT t.lot_no
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON t.lot_no = i.lot_no
            WHERE i.lot_no IS NULL
        """)
        if orphan_tonbags:
            lots = [r['lot_no'] for r in orphan_tonbags]
            issues.append({
                'type': 'ORPHAN_TONBAG',
                'severity': 'ERROR',
                'message': f'inventory에 없는 LOT의 톤백 {len(lots)}건',
                'details': lots[:20],
            })

        # 2. 상태 불일치: inventory.status vs 톤백 다수 상태
        status_mismatch = db.fetchall("""
            SELECT i.lot_no, i.status as inv_status,
                   GROUP_CONCAT(DISTINCT t.status) as tonbag_statuses,
                   COUNT(t.id) as bag_count
            FROM inventory i
            JOIN inventory_tonbag t ON i.lot_no = t.lot_no
            GROUP BY i.lot_no
            HAVING COUNT(DISTINCT t.status) > 2
        """)
        if status_mismatch:
            for row in status_mismatch:
                issues.append({
                        'type': 'STATUS_MISMATCH',
                        'severity': 'WARNING',
                        'message': f"LOT {row['lot_no']}: inventory={row['inv_status']}, tonbags={row['tonbag_statuses']}",
                    })

        # 3. 중량 합계 불일치
        weight_mismatch = db.fetchall("""
            SELECT i.lot_no, i.current_weight,
                   SUM(CASE WHEN t.status IN ('AVAILABLE','RESERVED') AND COALESCE(t.is_sample,0)=0 THEN t.weight ELSE 0 END) as calc_weight
            FROM inventory i
            JOIN inventory_tonbag t ON i.lot_no = t.lot_no
            GROUP BY i.lot_no
            HAVING ABS(COALESCE(i.current_weight,0) - calc_weight) > 1.0
        """)
        if weight_mismatch:
            for row in weight_mismatch[:10]:
                issues.append({
                        'type': 'WEIGHT_MISMATCH',
                        'severity': 'WARNING',
                        'message': f"LOT {row['lot_no']}: recorded={row['current_weight']}, calculated={row['calc_weight']}",
                    })

        return {
            'success': True,
            'total_issues': len(issues),
            'issues': issues,
            'generated_at': now_str(),
        }


@router.get("/schema-check")
def schema_check():
    """운영 DB 스키마 점검 — 주요 테이블 존재 여부 확인."""
    _REQUIRED_TABLES = [
        "inventory",
        "inventory_tonbag",
        "allocation_plan",
        "sold_table",
        "picking_table",
        "stock_movement",
    ]
    results = []
    with get_db() as db:
        for tbl in _REQUIRED_TABLES:
            try:
                info = db.fetchall(f"PRAGMA table_info({tbl})")  # noqa: S608
                ok = len(info) > 0
            except Exception:
                ok = False
            results.append({"name": tbl, "ok": ok})

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    all_ok = passed == total
    message = "모든 테이블 정상" if all_ok else f"{total - passed}개 테이블 누락"

    return {
        "all_ok": all_ok,
        "passed": passed,
        "total": total,
        "message": message,
        "results": results,
    }


@router.post("/checksum-update")
def checksum_update():
    """inventory 테이블 체크섬 갱신"""
    import hashlib
    with get_db() as db:
        rows = db.fetchall("SELECT lot_no, status, current_weight FROM inventory ORDER BY lot_no")
        data = str([(r['lot_no'], r['status'], r['current_weight']) for r in rows])
        checksum = hashlib.sha256(data.encode()).hexdigest()[:16]
    return {"success": True, "checksum": checksum, "row_count": len(rows), "generated_at": now_str()}


@router.get("/self-test")
def self_test():
    """전체 시스템 진단"""
    results = []
    with get_db() as db:
        try:
            db.fetchall("SELECT 1")
            results.append({"name": "DB 연결", "ok": True})
        except Exception:
            results.append({"name": "DB 연결", "ok": False})
        for tbl in ["inventory", "inventory_tonbag", "allocation_plan", "sold_table", "picking_table"]:
            try:
                cnt = db.fetchone(f"SELECT COUNT(*) as c FROM {tbl}")
                results.append({"name": f"테이블 {tbl}", "ok": True, "count": cnt['c'] if cnt else 0})
            except Exception:
                results.append({"name": f"테이블 {tbl}", "ok": False})
    passed = sum(1 for r in results if r["ok"])
    return {"success": True, "passed": passed, "total": len(results), "results": results, "generated_at": now_str()}


@router.post("/clean-logs")
def clean_logs():
    """7일 이상 된 .log 파일 삭제."""
    log_dirs = [
        Path("logs"),
        Path("../logs"),
        Path("data/logs"),
    ]
    cutoff = datetime.now() - timedelta(days=7)
    deleted = 0

    for log_dir in log_dirs:
        if not log_dir.is_dir():
            continue
        for log_file in log_dir.glob("*.log"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    log_file.unlink()
                    deleted += 1
            except Exception:
                logger.warning("로그 파일 삭제 실패: %s", log_file)

    return {
        "success": True,
        "message": f"{deleted}개 파일 정리",
        "deleted": deleted,
    }
