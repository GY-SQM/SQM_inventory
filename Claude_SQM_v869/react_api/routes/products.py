# -*- coding: utf-8 -*-
"""제품 마스터 CRUD API."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/products", tags=["products"])


def _ensure_table(db):
    """product_master 테이블 없으면 생성."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS product_master (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            code            TEXT    NOT NULL UNIQUE,
            full_name       TEXT    NOT NULL,
            korean_name     TEXT    NOT NULL DEFAULT '',
            tonbag_support  INTEGER NOT NULL DEFAULT 0,
            is_default      INTEGER NOT NULL DEFAULT 0,
            is_active       INTEGER NOT NULL DEFAULT 1,
            sort_order      INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT,
            updated_at      TEXT
        )
    """)


# ── 1. 전체 목록 조회 ─────────────────────────────────────────────────────────
@router.get("/list")
def product_list(active_only: bool = Query(True)):
    """제품 마스터 목록 조회."""
    try:
        with get_db() as db:
            _ensure_table(db)
            sql = "SELECT * FROM product_master"
            if active_only:
                sql += " WHERE is_active = 1"
            sql += " ORDER BY sort_order, code"
            rows = db.fetchall(sql)
            return {
                'success': True,
                'total':   len(rows or []),
                'rows':    [dict(r) for r in (rows or [])],
                'generated_at': now_str(),
            }
    except Exception as exc:
        logger.error("product_list 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"제품 목록 조회 실패: {exc}")


# ── 2. 단일 조회 ──────────────────────────────────────────────────────────────
@router.get("/{product_id}")
def product_get(product_id: int):
    """제품 단일 조회."""
    try:
        with get_db() as db:
            _ensure_table(db)
            row = db.fetchone("SELECT * FROM product_master WHERE id = ?", (product_id,))
            if not row:
                raise HTTPException(404, f"제품 ID {product_id} 없음")
            return {'success': True, 'row': dict(row)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("product_get 실패: %s", exc, exc_info=True)
        raise HTTPException(500, str(exc))


# ── 3. 제품 추가 ──────────────────────────────────────────────────────────────
@router.post("/create")
def product_create(payload: dict):
    """제품 추가.
    payload: { code, full_name, korean_name?, tonbag_support? }
    """
    code      = str(payload.get('code', '')).upper().strip()
    full_name = str(payload.get('full_name', '')).strip()
    if not code:
        raise HTTPException(400, "code 필수")
    if not full_name:
        raise HTTPException(400, "full_name 필수")
    if len(code) > 10:
        raise HTTPException(400, "code 최대 10자")

    try:
        with get_db() as db:
            _ensure_table(db)
            existing = db.fetchone("SELECT id FROM product_master WHERE code = ?", (code,))
            if existing:
                raise HTTPException(409, f"이미 존재하는 코드: {code}")

            max_row   = db.fetchone("SELECT MAX(sort_order) AS mx FROM product_master")
            max_order = int(max_row.get('mx', 0) or 0) if max_row else 0
            now       = now_str()
            db.execute("""
                INSERT INTO product_master
                    (code, full_name, korean_name, tonbag_support, is_default, sort_order, created_at)
                VALUES (?, ?, ?, ?, 0, ?, ?)
            """, (
                code, full_name,
                str(payload.get('korean_name', '')).strip(),
                1 if payload.get('tonbag_support') else 0,
                max_order + 10,
                now,
            ))
            new_row = db.fetchone("SELECT * FROM product_master WHERE code = ?", (code,))
            return {
                'success': True,
                'message': f"제품 '{code}' 추가 완료",
                'row':     dict(new_row) if new_row else {},
            }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("product_create 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"제품 추가 실패: {exc}")


# ── 4. 제품 수정 ──────────────────────────────────────────────────────────────
@router.put("/{product_id}")
def product_update(product_id: int, payload: dict):
    """제품 수정.
    payload: { code?, full_name?, korean_name?, tonbag_support? }
    """
    try:
        with get_db() as db:
            _ensure_table(db)
            existing = db.fetchone("SELECT * FROM product_master WHERE id = ?", (product_id,))
            if not existing:
                raise HTTPException(404, f"제품 ID {product_id} 없음")
            if existing:
                cur = existing
            else:
                cols = ['id','code','full_name','korean_name','tonbag_support',
                        'is_default','is_active','sort_order','created_at','updated_at']
                cur  = dict(zip(cols, existing))

            code      = str(payload.get('code', cur.get('code', ''))).upper().strip()
            full_name = str(payload.get('full_name', cur.get('full_name', ''))).strip()
            if not code or not full_name:
                raise HTTPException(400, "code, full_name 필수")

            db.execute("""
                UPDATE product_master
                SET code = ?, full_name = ?, korean_name = ?,
                    tonbag_support = ?, updated_at = ?
                WHERE id = ?
            """, (
                code, full_name,
                str(payload.get('korean_name', cur.get('korean_name', ''))).strip(),
                1 if payload.get('tonbag_support', cur.get('tonbag_support', 0)) else 0,
                now_str(),
                product_id,
            ))
            return {'success': True, 'message': f"제품 '{code}' 수정 완료"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("product_update 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"제품 수정 실패: {exc}")


# ── 5. 제품 비활성화 (소프트 삭제) ───────────────────────────────────────────
@router.delete("/{product_id}")
def product_delete(product_id: int):
    """제품 비활성화 (is_default=1 이면 삭제 불가)."""
    try:
        with get_db() as db:
            _ensure_table(db)
            row = db.fetchone("SELECT code, is_default FROM product_master WHERE id = ?", (product_id,))
            if not row:
                raise HTTPException(404, f"제품 ID {product_id} 없음")
            is_def = row.get('is_default', 0)
            code   = row.get('code', 0)
            if is_def:
                raise HTTPException(400, f"기본 제품 '{code}'은 삭제할 수 없습니다.")
            db.execute(
                "UPDATE product_master SET is_active = 0, updated_at = ? WHERE id = ?",
                (now_str(), product_id),
            )
            return {'success': True, 'message': f"제품 '{code}' 비활성화 완료"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("product_delete 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"제품 삭제 실패: {exc}")
