# -*- coding: utf-8 -*-
"""Allocation 승인 워크플로우 API."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from react_api.utils.db import get_db, get_engine, now_str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/approval", tags=["approval"])

ACTOR = "react_ui"


# ── 1. 승인 대기 목록 ─────────────────────────────────────────────────────────
@router.get("/queue")
def approval_queue(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """workflow_status = PENDING_APPROVAL 인 allocation_plan 목록."""
    try:
        with get_db() as db:
            conditions = ["a.workflow_status = 'PENDING_APPROVAL'"]
            params = []
            if keyword:
                conditions.append(
                    "(a.lot_no LIKE ? OR COALESCE(a.customer,'') LIKE ? "
                    "OR COALESCE(a.sale_ref,'') LIKE ?)"
                )
                kw = f"%{keyword}%"
                params.extend([kw, kw, kw])

            where  = " AND ".join(conditions)
            offset = (page - 1) * page_size

            total = int((db.fetchone(
                f"SELECT COUNT(*) AS c FROM allocation_plan a WHERE {where}",
                tuple(params),
            ) or {}).get("c") or 0)

            rows = db.fetchall(
                f"""SELECT a.id, a.lot_no, a.customer, a.sale_ref,
                           COALESCE(a.qty_mt, 0) AS qty_mt,
                           a.outbound_date, a.status,
                           a.workflow_status, a.created_at,
                           COALESCE(i.product,'') AS product
                    FROM allocation_plan a
                    LEFT JOIN inventory i ON i.lot_no = a.lot_no
                    WHERE {where}
                    ORDER BY a.created_at DESC
                    LIMIT ? OFFSET ?""",
                tuple(params + [page_size, offset]),
            )

            return {
                "total":    total,
                "page":     page,
                "rows":     [dict(r) for r in (rows or [])],
                "generated_at": now_str(),
            }
    except Exception as exc:
        logger.error("approval_queue 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"승인 대기 조회 실패: {exc}")


# ── 2. 일괄 승인 ──────────────────────────────────────────────────────────────
@router.post("/approve")
def approve(payload: dict):
    """
    선택된 allocation_plan ID 목록을 APPROVED 처리.
    payload: { ids: [int, ...], reason: str }
    """
    ids    = [int(i) for i in (payload.get("ids") or []) if str(i).isdigit()]
    reason = payload.get("reason") or "approved via React UI"
    if not ids:
        raise HTTPException(400, "승인할 ID 목록이 없습니다.")
    try:
        ts = now_str()
        placeholders = ",".join(["?"] * len(ids))
        with get_db() as db:
            # 배치 UPDATE — N+1 제거
            cur = db.execute(
                f"""UPDATE allocation_plan
                    SET workflow_status = 'APPROVED',
                        approved_by = ?, approved_at = ?
                    WHERE id IN ({placeholders})
                      AND workflow_status = 'PENDING_APPROVAL'""",
                (ACTOR, ts, *ids),
            )
            approved = getattr(cur, "rowcount", 0) or 0
            # 이력 배치 INSERT
            if approved > 0:
                try:
                    updated_ids = [
                        r["id"]
                        for r in (db.fetchall(
                            f"SELECT id FROM allocation_plan WHERE id IN ({placeholders}) AND workflow_status='APPROVED'",
                            tuple(ids)
                        ) or [])
                    ]
                    for pid in updated_ids:
                        db.execute(
                            """INSERT OR IGNORE INTO allocation_approval
                               (allocation_plan_id, status, actor, reason, created_at)
                               VALUES (?, 'APPROVED', ?, ?, ?)""",
                            (pid, ACTOR, reason, ts),
                        )
                except Exception:
                    pass  # allocation_approval 테이블 없으면 스킵

        return {
            "success":   approved > 0,
            "approved":  approved,
            "message":   f"{approved}건 승인 완료",
            "generated_at": now_str(),
        }
    except Exception as exc:
        logger.error("approve 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"승인 처리 실패: {exc}")


# ── 3. 일괄 반려 ──────────────────────────────────────────────────────────────
@router.post("/reject")
def reject(payload: dict):
    """
    선택된 allocation_plan ID 목록을 REJECTED 처리.
    payload: { ids: [int, ...], reason: str }
    """
    ids    = [int(i) for i in (payload.get("ids") or []) if str(i).isdigit()]
    reason = payload.get("reason") or "rejected via React UI"
    if not ids:
        raise HTTPException(400, "반려할 ID 목록이 없습니다.")
    try:
        ts = now_str()
        placeholders = ",".join(["?"] * len(ids))
        with get_db() as db:
            # 배치 UPDATE — N+1 제거
            cur = db.execute(
                f"""UPDATE allocation_plan
                    SET workflow_status = 'REJECTED',
                        rejected_reason = ?
                    WHERE id IN ({placeholders})
                      AND workflow_status = 'PENDING_APPROVAL'""",
                (reason, *ids),
            )
            rejected = getattr(cur, "rowcount", 0) or 0
            # 이력 배치 INSERT
            if rejected > 0:
                try:
                    rejected_ids = [
                        r["id"]
                        for r in (db.fetchall(
                            f"SELECT id FROM allocation_plan WHERE id IN ({placeholders}) AND workflow_status='REJECTED'",
                            tuple(ids)
                        ) or [])
                    ]
                    for pid in rejected_ids:
                        db.execute(
                            """INSERT OR IGNORE INTO allocation_approval
                               (allocation_plan_id, status, actor, reason, created_at)
                               VALUES (?, 'REJECTED', ?, ?, ?)""",
                            (pid, ACTOR, reason, ts),
                        )
                except Exception:
                    pass  # allocation_approval 테이블 없으면 스킵

        return {
            "success":  rejected > 0,
            "rejected": rejected,
            "message":  f"{rejected}건 반려 완료",
            "generated_at": now_str(),
        }
    except Exception as exc:
        logger.error("reject 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"반려 처리 실패: {exc}")


# ── 4. 승인 이력 조회 ─────────────────────────────────────────────────────────
@router.get("/history")
def approval_history(
    lot_no:    Optional[str] = Query(None),
    page:      int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Allocation 승인/반려 이력 조회."""
    try:
        with get_db() as db:
            # allocation_approval 테이블 존재 여부 확인
            tbl = db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='allocation_approval'"
            )
            if not tbl:
                # 테이블 없으면 allocation_plan workflow 이력으로 대체
                conditions = ["a.workflow_status IN ('APPROVED','REJECTED')"]
                params = []
                if lot_no:
                    conditions.append("a.lot_no LIKE ?")
                    params.append(f"%{lot_no}%")
                where  = " AND ".join(conditions)
                offset = (page - 1) * page_size
                total  = int((db.fetchone(
                    f"SELECT COUNT(*) AS c FROM allocation_plan a WHERE {where}",
                    tuple(params),
                ) or {}).get("c") or 0)
                rows = db.fetchall(
                    f"""SELECT a.id, a.lot_no, a.customer, a.sale_ref,
                               a.workflow_status AS status,
                               a.approved_by AS actor,
                               COALESCE(a.approved_at, a.created_at) AS created_at,
                               '' AS reason
                        FROM allocation_plan a
                        WHERE {where}
                        ORDER BY a.approved_at DESC
                        LIMIT ? OFFSET ?""",
                    tuple(params + [page_size, offset]),
                )
            else:
                conditions = ["1=1"]
                params = []
                if lot_no:
                    conditions.append("p.lot_no LIKE ?")
                    params.append(f"%{lot_no}%")
                where  = " AND ".join(conditions)
                offset = (page - 1) * page_size
                total  = int((db.fetchone(
                    f"""SELECT COUNT(*) AS c
                        FROM allocation_approval h
                        LEFT JOIN allocation_plan p ON p.id = h.allocation_plan_id
                        WHERE {where}""",
                    tuple(params),
                ) or {}).get("c") or 0)
                rows = db.fetchall(
                    f"""SELECT h.id, p.lot_no, p.customer, p.sale_ref,
                               h.status, h.actor, h.created_at, h.reason
                        FROM allocation_approval h
                        LEFT JOIN allocation_plan p ON p.id = h.allocation_plan_id
                        WHERE {where}
                        ORDER BY h.created_at DESC
                        LIMIT ? OFFSET ?""",
                    tuple(params + [page_size, offset]),
                )

            return {
                "total":    total,
                "page":     page,
                "rows":     [dict(r) for r in (rows or [])],
                "generated_at": now_str(),
            }
    except Exception as exc:
        logger.error("approval_history 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"이력 조회 실패: {exc}")


# ── 5. 승인 후 예약 반영 ──────────────────────────────────────────────────────
@router.post("/apply-approved")
def apply_approved():
    """APPROVED 상태 allocation_plan → 실제 톤백 RESERVED 처리."""
    try:
        with get_db() as db:
            approved_rows = db.fetchall(
                """SELECT id, lot_no, tonbag_id, sub_lt, qty_mt, sale_ref, customer
                   FROM allocation_plan
                   WHERE workflow_status = 'APPROVED'
                     AND status = 'STAGED'"""
            )
            if not approved_rows:
                return {
                    "success": True, "applied": 0,
                    "message": "반영할 승인 건이 없습니다.",
                    "generated_at": now_str(),
                }

            applied = 0
            ts = now_str()
            with db.transaction():
                for r in approved_rows:
                    pid     = r.get("id", 0)
                    t_id    = r.get("tonbag_id", 0)

                    if t_id:
                        db.execute(
                            "UPDATE inventory_tonbag SET status='RESERVED' WHERE id=? AND status='AVAILABLE'",
                            (t_id,),
                        )
                    db.execute(
                        "UPDATE allocation_plan SET status='RESERVED', executed_at=? WHERE id=?",
                        (ts, pid),
                    )
                    applied += 1

        return {
            "success":  applied > 0,
            "applied":  applied,
            "message":  f"{applied}건 예약 반영 완료",
            "generated_at": now_str(),
        }
    except Exception as exc:
        logger.error("apply_approved 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"예약 반영 실패: {exc}")
