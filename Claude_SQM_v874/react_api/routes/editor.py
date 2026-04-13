# -*- coding: utf-8 -*-
"""P3: DB 컨트롤 센터 — 검색/편집/이력/되돌리기 API"""
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/editor", tags=["editor"])

# ── 편집 금지 필드 ──
BLOCKED_FIELDS = frozenset({
    'id', 'inventory_id', 'lot_no', 'sub_lt', 'tonbag_uid', 'tonbag_no',
    'status', 'weight', 'is_sample', 'product', 'product_code', 'product_name',
    'initial_weight', 'current_weight', 'picked_weight',
    'net_weight', 'gross_weight', 'tonbag_count', 'mxbg_pallet',
    'created_at', 'updated_at',
})

ALLOWED_TABLES = frozenset({'inventory', 'inventory_tonbag'})


class CellUpdate(BaseModel):
    table: str
    id: int
    field: str
    old_value: str = ''
    new_value: str


class BulkUpdate(BaseModel):
    table: str
    ids: List[int]
    field: str
    new_value: str


class RevertRequest(BaseModel):
    audit_id: int


# ── P3-2: 검색 API ──
@router.get("/search")
def editor_search(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    lot_no: Optional[str] = Query(None),
    container_no: Optional[str] = Query(None),
    tonbag_uid: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
):
    """LOT + 톤백 검색"""
    with get_db() as db:
        conditions = ["1=1"]
        params = []

        if date_from:
            conditions.append("i.inbound_date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("i.inbound_date <= ?")
            params.append(date_to)
        if lot_no:
            conditions.append("i.lot_no LIKE ?")
            params.append(f"%{lot_no}%")
        if container_no:
            conditions.append("i.container_no LIKE ?")
            params.append(f"%{container_no}%")

        where = " AND ".join(conditions)
        offset = (page - 1) * page_size

        # 총 건수
        count_row = db.fetchone(f"SELECT COUNT(*) as cnt FROM inventory i WHERE {where}", tuple(params))
        total = count_row['cnt'] if count_row else 0

        # LOT 목록
        lots = db.fetchall(f"""
            SELECT i.id, i.lot_no, i.bl_no, i.sap_no, i.product_name, i.status,
                   i.net_weight, i.current_weight, i.container_no,
                   i.ship_date, i.arrival_date, i.con_return, i.free_time,
                   i.vessel, i.warehouse, i.remarks, i.inbound_date
            FROM inventory i WHERE {where}
            ORDER BY i.inbound_date DESC
            LIMIT ? OFFSET ?
        """, tuple(params) + (page_size, offset))

        # 각 LOT의 톤백
        for lot in lots:
            if tonbag_uid:
                tonbags = db.fetchall(
                    "SELECT id, lot_no, sub_lt, tonbag_uid, tonbag_no, weight, location, status FROM inventory_tonbag WHERE lot_no=? AND tonbag_uid LIKE ?",
                    (lot['lot_no'], f"%{tonbag_uid}%")
                )
            else:
                tonbags = db.fetchall(
                    "SELECT id, lot_no, sub_lt, tonbag_uid, tonbag_no, weight, location, status FROM inventory_tonbag WHERE lot_no=?",
                    (lot['lot_no'],)
                )
            lot['tonbags'] = tonbags

    return {"success": True, "lots": lots, "total": total, "page": page, "page_size": page_size}


# ── P3-3: 단건 편집 API ──
@router.post("/update-cell")
def update_cell(req: CellUpdate):
    """단일 셀 편집 + audit_log"""
    if req.table not in ALLOWED_TABLES:
        raise HTTPException(400, f"테이블 '{req.table}'은 편집 불가")
    if req.field in BLOCKED_FIELDS:
        raise HTTPException(400, f"필드 '{req.field}'는 편집 금지 (BLOCKED_FIELDS)")

    with get_db() as db:
        # 현재 값 확인 (동시 수정 방지)
        row = db.fetchone(f"SELECT {req.field} FROM {req.table} WHERE id=?", (req.id,))
        if not row:
            raise HTTPException(404, "레코드를 찾을 수 없습니다.")

        current = str(row[req.field] or '')
        if current != req.old_value:
            raise HTTPException(409, f"동시 수정 감지: 현재값 '{current}' ≠ 기존값 '{req.old_value}'")

        # 업데이트
        db.execute(f"UPDATE {req.table} SET {req.field}=? WHERE id=?", (req.new_value, req.id))

        # audit_log 기록
        lot_no = ''
        if req.table == 'inventory':
            r = db.fetchone("SELECT lot_no FROM inventory WHERE id=?", (req.id,))
            lot_no = r['lot_no'] if r else ''
        elif req.table == 'inventory_tonbag':
            r = db.fetchone("SELECT lot_no FROM inventory_tonbag WHERE id=?", (req.id,))
            lot_no = r['lot_no'] if r else ''

        db.execute("""
            INSERT INTO audit_log (event_type, lot_no, field_name, old_value, new_value, table_name, record_id, created_at)
            VALUES ('DB_EDIT', ?, ?, ?, ?, ?, ?, ?)
        """, (lot_no, req.field, req.old_value, req.new_value, req.table, req.id, now_str()))

        db.commit()

    return {"success": True, "message": f"{req.field} 수정 완료"}


# ── P3-4: 일괄 편집 API ──
@router.post("/update-bulk")
def update_bulk(req: BulkUpdate):
    """일괄 편집 + audit_log"""
    if req.table not in ALLOWED_TABLES:
        raise HTTPException(400, f"테이블 '{req.table}'은 편집 불가")
    if req.field in BLOCKED_FIELDS:
        raise HTTPException(400, f"필드 '{req.field}'는 편집 금지")
    if len(req.ids) > 500:
        raise HTTPException(400, "최대 500건까지 일괄 편집 가능")

    updated = 0
    with get_db() as db:
        for rid in req.ids:
            row = db.fetchone(f"SELECT {req.field}, lot_no FROM {req.table} WHERE id=?", (rid,))
            if not row:
                continue
            old_val = str(row[req.field] or '')
            lot_no = row.get('lot_no', '')

            db.execute(f"UPDATE {req.table} SET {req.field}=? WHERE id=?", (req.new_value, rid))
            db.execute("""
                INSERT INTO audit_log (event_type, lot_no, field_name, old_value, new_value, table_name, record_id, created_at)
                VALUES ('DB_BULK_EDIT', ?, ?, ?, ?, ?, ?, ?)
            """, (lot_no, req.field, old_val, req.new_value, req.table, rid, now_str()))
            updated += 1

        db.commit()

    return {"success": True, "updated_count": updated, "message": f"{updated}건 일괄 수정 완료"}


# ── P3-5: 감사 이력 + 되돌리기 ──
@router.get("/audit-log")
def get_audit_log(
    lot_no: Optional[str] = Query(None),
    field_name: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """감사 이력 조회"""
    with get_db() as db:
        conditions = ["event_type IN ('DB_EDIT','DB_BULK_EDIT','DB_REVERT')"]
        params = []
        if lot_no:
            conditions.append("lot_no LIKE ?")
            params.append(f"%{lot_no}%")
        if field_name:
            conditions.append("field_name = ?")
            params.append(field_name)
        if date_from:
            conditions.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("created_at <= ?")
            params.append(date_to)

        where = " AND ".join(conditions)
        offset = (page - 1) * page_size

        total_row = db.fetchone(f"SELECT COUNT(*) as cnt FROM audit_log WHERE {where}", tuple(params))
        total = total_row['cnt'] if total_row else 0

        rows = db.fetchall(f"""
            SELECT id, event_type, lot_no, field_name, old_value, new_value, table_name, record_id, created_at
            FROM audit_log WHERE {where}
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, tuple(params) + (page_size, offset))

    return {"success": True, "logs": rows, "total": total, "page": page}


@router.post("/revert")
def revert_edit(req: RevertRequest):
    """감사 로그 기반 되돌리기"""
    with get_db() as db:
        log = db.fetchone("SELECT * FROM audit_log WHERE id=?", (req.audit_id,))
        if not log:
            raise HTTPException(404, "감사 로그를 찾을 수 없습니다.")

        table = log['table_name']
        record_id = log['record_id']
        field = log['field_name']
        old_value = log['old_value']

        if table not in ALLOWED_TABLES:
            raise HTTPException(400, "되돌리기 불가 테이블")
        if field in BLOCKED_FIELDS:
            raise HTTPException(400, "되돌리기 불가 필드")

        # 되돌리기 실행
        current = db.fetchone(f"SELECT {field} FROM {table} WHERE id=?", (record_id,))
        if not current:
            raise HTTPException(404, "원본 레코드 없음")

        db.execute(f"UPDATE {table} SET {field}=? WHERE id=?", (old_value, record_id))

        # 되돌리기 로그
        db.execute("""
            INSERT INTO audit_log (event_type, lot_no, field_name, old_value, new_value, table_name, record_id, created_at)
            VALUES ('DB_REVERT', ?, ?, ?, ?, ?, ?, ?)
        """, (log['lot_no'], field, str(current[field] or ''), old_value, table, record_id, now_str()))

        db.commit()

    return {"success": True, "message": f"되돌리기 완료: {field} → {old_value}"}


@router.get("/audit-export")
def export_audit(format: str = Query("csv")):
    """감사 로그 CSV 내보내기"""
    import io, csv
    from fastapi.responses import StreamingResponse

    with get_db() as db:
        rows = db.fetchall("""
            SELECT id, event_type, lot_no, field_name, old_value, new_value, table_name, record_id, created_at
            FROM audit_log WHERE event_type IN ('DB_EDIT','DB_BULK_EDIT','DB_REVERT')
            ORDER BY created_at DESC LIMIT 5000
        """)

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    headers = ['ID', 'EVENT', 'LOT_NO', 'FIELD', 'OLD_VALUE', 'NEW_VALUE', 'TABLE', 'RECORD_ID', 'CREATED_AT']
    writer.writerow(headers)
    for r in rows:
        writer.writerow([r.get(h.lower(), '') for h in headers])
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename=audit_log_{datetime.now().strftime('%Y%m%d')}.csv"},
    )


# ── P3-8: 테이블 탐색기 + DB 건강 ──
@router.get("/tables")
def list_tables():
    """DB 테이블 목록 + 행수"""
    with get_db() as db:
        tables_raw = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        result = []
        for t in tables_raw:
            name = t['name']
            try:
                cnt = db.fetchone(f"SELECT COUNT(*) as c FROM [{name}]")
                result.append({"name": name, "row_count": cnt['c'] if cnt else 0})
            except Exception:
                result.append({"name": name, "row_count": -1})
    return {"success": True, "tables": result, "total": len(result)}


@router.get("/table/{name}")
def read_table(name: str, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    """테이블 데이터 읽기 (화이트리스트 검증, 읽기 전용)"""
    # 안전: 테이블명 화이트리스트
    with get_db() as db:
        tables = [t['name'] for t in db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")]
        if name not in tables:
            raise HTTPException(404, f"테이블 '{name}' 없음")

        total_row = db.fetchone(f"SELECT COUNT(*) as c FROM [{name}]")
        total = total_row['c'] if total_row else 0
        offset = (page - 1) * page_size

        rows = db.fetchall(f"SELECT * FROM [{name}] LIMIT ? OFFSET ?", (page_size, offset))

        # 컬럼 정보
        cols = db.fetchall(f"PRAGMA table_info([{name}])")
        columns = [{"name": c['name'], "type": c['type']} for c in cols]

    return {"success": True, "table": name, "columns": columns, "rows": rows, "total": total, "page": page}


@router.get("/db-health")
def db_health():
    """DB 건강 지표"""
    import os
    from pathlib import Path

    db_candidates = [Path("data/db/sqm_inventory.db"), Path("../data/db/sqm_inventory.db")]
    db_path = next((p for p in db_candidates if p.exists()), None)

    info = {"db_size_mb": 0, "wal_size_mb": 0, "index_count": 0, "edit_count_24h": 0}

    if db_path:
        info["db_size_mb"] = round(db_path.stat().st_size / 1024 / 1024, 2)
        wal = db_path.with_suffix('.db-wal')
        if wal.exists():
            info["wal_size_mb"] = round(wal.stat().st_size / 1024 / 1024, 2)

    with get_db() as db:
        idx = db.fetchone("SELECT COUNT(*) as c FROM sqlite_master WHERE type='index'")
        info["index_count"] = idx['c'] if idx else 0

        try:
            edits = db.fetchone("""
                SELECT COUNT(*) as c FROM audit_log
                WHERE event_type IN ('DB_EDIT','DB_BULK_EDIT')
                AND created_at >= datetime('now', '-1 day')
            """)
            info["edit_count_24h"] = edits['c'] if edits else 0
        except Exception:
            pass

    return {"success": True, **info, "generated_at": now_str()}
