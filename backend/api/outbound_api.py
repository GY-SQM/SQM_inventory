# -*- coding: utf-8 -*-
"""
SQM v8.6.6 — Outbound API (Phase 4-B)
POST /api/outbound/quick : 즉시 출고 (원스톱) — F015
engine.quick_outbound(lot_no, count, customer, reason, operator) 직접 호출
"""
import logging
import os
import tempfile
import json
import csv as _csv
import hashlib
import shutil
from datetime import date, datetime
from pathlib import Path
from io import StringIO, BytesIO
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/outbound", tags=["outbound"])

BASE_DIR = Path(__file__).resolve().parents[2]
PROOF_DOCS_DIR = BASE_DIR / "data" / "proof_docs"


def _ensure_audit_log_table(db) -> None:
    """Ensure v864-2 S1 audit_log shape exists before one-stop writes."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,
            event_data  TEXT,
            batch_id    TEXT,
            tonbag_id   TEXT,
            user_note   TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            created_by  TEXT DEFAULT 'WEBVIEW_ONESTOP'
        )
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_event
        ON audit_log(event_type, created_at)
        """
    )


def _write_audit_log(
    db,
    event_type: str,
    event_data: Optional[Dict[str, Any]] = None,
    batch_id: str = "",
    tonbag_id: str = "",
    user_note: str = "",
) -> None:
    _ensure_audit_log_table(db)
    data_str = json.dumps(event_data or {}, ensure_ascii=False)
    db.execute(
        """
        INSERT INTO audit_log
            (event_type, event_data, batch_id, tonbag_id, user_note, created_at, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_type,
            data_str,
            batch_id or "",
            tonbag_id or "",
            user_note or "",
            datetime.now().isoformat(),
            "WEBVIEW_ONESTOP",
        ),
    )


def _db_row_to_dict(row) -> Dict[str, Any]:
    if row is None:
        return {}
    try:
        return {k: row[k] for k in row.keys()}
    except Exception:
        return dict(row)


def _cleanup_old_proof_docs(db, retention_days: int = 90) -> int:
    """Delete proof_docs date folders older than retention_days, preserving audit rows."""
    base = PROOF_DOCS_DIR
    if not base.exists():
        return 0
    cutoff = date.today().toordinal() - retention_days
    removed = 0
    for entry in base.iterdir():
        if not entry.is_dir():
            continue
        try:
            folder_date = date.fromisoformat(entry.name)
        except (ValueError, TypeError):
            continue
        if folder_date.toordinal() >= cutoff:
            continue
        try:
            file_count = len([p for p in entry.iterdir() if p.is_file()])
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
            _write_audit_log(
                db,
                event_type="PROOF_CLEANUP",
                event_data={
                    "folder": entry.name,
                    "file_count": file_count,
                    "retention_days": retention_days,
                },
                user_note=f"자동 정리: {entry.name} ({file_count}개 파일)",
            )
        except Exception as e:
            logger.warning(f"[proof-cleanup] {entry} 삭제 실패: {e}")
    return removed


class QuickOutboundRequest(BaseModel):
    lot_no: str = Field(..., min_length=1, description="LOT 번호")
    count: int = Field(..., gt=0, description="출고 톤백 개수")
    customer: str = Field(..., min_length=1, description="고객명")
    reason: str = Field("", description="사유 (선택)")
    operator: str = Field("", description="작업자 (선택)")


@router.post("/quick", summary="🚀 즉시 출고 — 원스톱 (F015)")
def quick_outbound(req: QuickOutboundRequest):
    """
    Allocation 없이 소량 즉시 출고 (AVAILABLE → PICKED 직접 전환).
    engine.quick_outbound() 트랜잭션 호출.
    """
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")
    if not hasattr(engine, "quick_outbound"):
        raise HTTPException(500, "엔진에 quick_outbound 메서드 없음")

    try:
        result = engine.quick_outbound(
            lot_no=req.lot_no.strip(),
            count=req.count,
            customer=req.customer.strip(),
            reason=req.reason or "",
            operator=req.operator or "",
        )
    except Exception as e:
        logger.exception(f"[quick-outbound] engine 에러: {e}")
        raise HTTPException(500, f"Engine error: {e}")

    if result.get("success"):
        picked = int(result.get("picked_count", 0))
        total_weight_kg = float(result.get("total_weight_kg", 0))
        logger.info(
            f"[quick-outbound] OK: LOT={req.lot_no}, picked={picked}, "
            f"total_weight={total_weight_kg}kg, customer={req.customer}"
        )
        return {
            "ok": True,
            "data": {
                "lot_no": req.lot_no,
                "picked_count": picked,
                "total_weight_kg": total_weight_kg,
                "total_weight_mt": round(total_weight_kg / 1000.0, 3),
                "customer": req.customer,
            },
            "message": f"{picked}개 톤백 출고 완료 ({round(total_weight_kg/1000.0, 2)} MT)",
        }
    else:
        # 실패: 엔진 errors 배열 그대로 사용자에게 반환
        errors = result.get("errors", [])
        return {
            "ok": False,
            "data": {
                "lot_no": req.lot_no,
                "picked_count": int(result.get("picked_count", 0)),
                "errors": errors,
            },
            "error": "즉시 출고 실패",
            "detail": {"code": "QUICK_OUTBOUND_FAILED", "errors": errors},
            "message": "; ".join(errors) if errors else "즉시 출고 실패",
        }


@router.get("/quick/info", summary="즉시 출고 — LOT 가용 정보 (F015 보조)")
def quick_outbound_info(lot_no: str):
    """
    특정 LOT 의 가용 톤백 개수와 총 중량 반환.
    프론트 폼에서 '최대 가능 개수' 표시용.
    """
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    lot_no = (lot_no or "").strip()
    if not lot_no:
        raise HTTPException(400, "lot_no required")

    try:
        rows = engine.db.fetchall(
            """SELECT COUNT(*) AS cnt, COALESCE(SUM(weight), 0) AS total_kg
               FROM inventory_tonbag
               WHERE lot_no = ? AND status = 'AVAILABLE' AND COALESCE(is_sample,0) = 0""",
            (lot_no,),
        )
        if rows:
            r = rows[0]
            cnt = int(r["cnt"] if hasattr(r, "__getitem__") else r[0])
            total_kg = float(r["total_kg"] if hasattr(r, "__getitem__") else r[1])
        else:
            cnt, total_kg = 0, 0.0
    except Exception as e:
        logger.warning(f"[quick-info] 조회 실패: {e}")
        raise HTTPException(500, f"조회 실패: {e}")

    try:
        from engine_modules.constants import QUICK_OUTBOUND_MAX_TONBAGS
        max_count = int(QUICK_OUTBOUND_MAX_TONBAGS)
    except Exception:
        max_count = 50  # fallback

    return {
        "ok": True,
        "data": {
            "lot_no": lot_no,
            "available_count": cnt,
            "total_weight_kg": total_kg,
            "total_weight_mt": round(total_kg / 1000.0, 3),
            "max_count": max_count,
        },
    }


# ────────────────────────────────────────────────────────────
# F017 Picking List PDF 업로드 — 출고 예정 항목 DB 반영
# features.parsers.picking_list_parser + picking_engine 재사용
# ────────────────────────────────────────────────────────────
@router.post("/picking-list-pdf", summary="📋 Picking List PDF 업로드 (F017)")
async def picking_list_pdf(file: UploadFile = File(...)):
    """
    Picking List PDF 파싱 → picking_engine.apply_picking_list_to_db() 호출.
    """
    if not file.filename:
        raise HTTPException(400, "파일명 없음")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, f"PDF 파일만 지원. 받은 파일: {file.filename}")

    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    try:
        from features.parsers.picking_list_parser import parse_picking_list_pdf
        from features.parsers.picking_engine import apply_picking_list_to_db
    except ImportError as e:
        raise HTTPException(500, f"Picking 엔진 import 실패: {e}")

    tmp_path = None
    try:
        content = await file.read()
        if not content:
            raise HTTPException(400, "빈 파일")
        if content[:4] != b"%PDF":
            raise HTTPException(400, "유효한 PDF 파일이 아닙니다")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        logger.info(f"[picking-list-pdf] 수신: {file.filename} ({len(content)} bytes)")

        # 1. 파싱
        doc = parse_picking_list_pdf(tmp_path)
        if not doc.get("parse_ok"):
            return {
                "ok": False,
                "data": {
                    "filename": file.filename,
                    "parse_ok": False,
                    "warnings": doc.get("warnings", []),
                    "total_lots": doc.get("total_lots", 0),
                    "items": doc.get("items", [])[:10],
                },
                "error": "Picking List 파싱 실패",
                "detail": {"code": "PARSE_FAILED", "warnings": doc.get("warnings", [])},
                "message": "Picking List 파싱 실패 — PDF 내용을 확인해주세요",
            }

        # 2. DB 반영
        result = apply_picking_list_to_db(engine, doc, tmp_path)
        try:
            from backend.api.sales_order_validation import validate_picking_doc
            allocation_validation = validate_picking_doc(doc)
        except Exception as ve:
            logger.warning("[picking-list-pdf] allocation validation failed: %s", ve)
            allocation_validation = {
                "level": "warning",
                "issues": [{"severity": "warning", "message": f"Allocation 검증 실패: {ve}"}],
                "context": {},
            }

        if result.get("success"):
            applied = int(result.get("applied", 0) or result.get("picked", 0) or 0)
            logger.info(f"[picking-list-pdf] 반영 완료: {applied}건 ({file.filename})")
            return {
                "ok": True,
                "data": {
                    "filename": file.filename,
                    "parse_method": doc.get("parse_method"),
                    "total_lots": doc.get("total_lots", 0),
                    "total_normal_mt": doc.get("total_normal_mt", 0),
                    "total_sample_kg": doc.get("total_sample_kg", 0),
                    "applied": applied,
                    "warnings": doc.get("warnings", []),
                    "details": result.get("details", [])[:30],
                    "allocation_validation": allocation_validation,
                },
                "message": f"Picking List 반영 완료 ({applied}건)",
            }
        else:
            return {
                "ok": False,
                "data": {
                    "filename": file.filename,
                    "total_lots": doc.get("total_lots", 0),
                    "errors": result.get("errors", []),
                    "warnings": doc.get("warnings", []),
                },
                "error": "Picking List 반영 실패",
                "detail": {"code": "APPLY_FAILED", "errors": result.get("errors", [])},
                "message": "DB 반영 실패 — 상세 errors 확인",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[picking-list-pdf] 에러: {e}")
        raise HTTPException(500, f"Internal error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ────────────────────────────────────────────────────────────
@router.post("/picking-import-excel", summary="📋 Picking List Excel 업로드 (피킹 이력 반영)")
async def picking_import_excel(file: UploadFile = File(...)):
    """
    Picking List Excel(.xlsx/.xls) 파싱 → apply_picking_list_to_db() 호출.
    PDF(picking-list-pdf)와 동일한 picking_engine 을 공유한다.
    """
    if not file.filename:
        raise HTTPException(400, "파일명 없음")
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, f"Excel 파일만 지원. 받은 파일: {file.filename}")

    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    try:
        from features.parsers.picking_excel_parser import parse_picking_list_excel
        from features.parsers.picking_engine import apply_picking_list_to_db
    except ImportError as e:
        raise HTTPException(500, f"Picking 엔진 import 실패: {e}")

    tmp_path = None
    try:
        content = await file.read()
        if not content:
            raise HTTPException(400, "빈 파일")
        ext = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        logger.info(f"[picking-import-excel] 수신: {file.filename} ({len(content)} bytes)")

        doc = parse_picking_list_excel(tmp_path)
        if not doc.get("parse_ok"):
            return {
                "ok": False,
                "data": {
                    "filename": file.filename,
                    "parse_ok": False,
                    "warnings": doc.get("warnings", []),
                    "total_lots": doc.get("total_lots", 0),
                    "items": doc.get("items", [])[:10],
                },
                "error": "Picking List Excel 파싱 실패",
                "detail": {"code": "PARSE_FAILED", "warnings": doc.get("warnings", [])},
                "message": "Picking List Excel 파싱 실패 — 파일 내용을 확인해주세요",
            }

        result = apply_picking_list_to_db(engine, doc, tmp_path)
        try:
            from backend.api.sales_order_validation import validate_picking_doc
            allocation_validation = validate_picking_doc(doc)
        except Exception as ve:
            logger.warning("[picking-import-excel] allocation validation failed: %s", ve)
            allocation_validation = {
                "level": "warning",
                "issues": [{"severity": "warning", "message": f"Allocation 검증 실패: {ve}"}],
                "context": {},
            }

        if result.get("success"):
            applied = int(result.get("applied", 0) or result.get("picked", 0) or 0)
            logger.info(f"[picking-import-excel] 반영 완료: {applied}건 ({file.filename})")
            return {
                "ok": True,
                "data": {
                    "filename": file.filename,
                    "parse_method": doc.get("parse_method"),
                    "total_lots": doc.get("total_lots", 0),
                    "total_normal_mt": doc.get("total_normal_mt", 0),
                    "total_sample_kg": doc.get("total_sample_kg", 0),
                    "applied": applied,
                    "warnings": doc.get("warnings", []),
                    "details": result.get("details", [])[:30],
                    "allocation_validation": allocation_validation,
                },
                "message": f"Picking List 반영 완료 ({applied}건)",
            }
        return {
            "ok": False,
            "data": {
                "filename": file.filename,
                "total_lots": doc.get("total_lots", 0),
                "errors": result.get("errors", []),
                "warnings": doc.get("warnings", []),
            },
            "error": "Picking List 반영 실패",
            "detail": {"code": "APPLY_FAILED", "errors": result.get("errors", [])},
            "message": "DB 반영 실패 — 상세 errors 확인",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[picking-import-excel] 에러: {e}")
        raise HTTPException(500, f"Internal error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────
# F016 빠른 출고 (붙여넣기) — 여러 LOT 텍스트 → 일괄 즉시 출고
# 각 행: "LOT_NO TAB COUNT" 또는 "LOT_NO,COUNT"
# 고객명 공통 1개 (모든 LOT 동일)
# engine.quick_outbound() 반복 호출
# ────────────────────────────────────────────────────────────
class QuickOutboundPasteRequest(BaseModel):
    rows: list = Field(..., min_length=1, description="[{lot_no, count}, ...] 리스트")
    customer: str = Field(..., min_length=1, description="공통 고객명")
    reason: str = Field("", description="사유")
    operator: str = Field("", description="작업자")


@router.post("/quick-paste", summary="📤 빠른 출고 (붙여넣기) — 여러 LOT 일괄 (F016)")
def quick_outbound_paste(req: QuickOutboundPasteRequest):
    """
    rows: [{lot_no, count}, ...] 를 순회하며 engine.quick_outbound() 반복.
    행별 독립 (한 행 실패가 다른 행 롤백 안 됨).
    """
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None or not hasattr(engine, "quick_outbound"):
        raise HTTPException(500, "엔진 quick_outbound 없음")

    success_count = 0
    fail_count = 0
    total_weight_kg = 0.0
    results = []

    for idx, row in enumerate(req.rows):
        try:
            lot_no = str((row or {}).get("lot_no", "")).strip()
            count = int((row or {}).get("count", 0))
        except Exception as e:
            fail_count += 1
            results.append({"row": idx + 1, "lot_no": "?", "ok": False, "reason": f"파싱 실패: {e}"})
            continue

        if not lot_no or count <= 0:
            fail_count += 1
            results.append({"row": idx + 1, "lot_no": lot_no or "?", "ok": False, "reason": "lot_no 또는 count 유효하지 않음"})
            continue

        try:
            r = engine.quick_outbound(
                lot_no=lot_no, count=count, customer=req.customer.strip(),
                reason=req.reason or "", operator=req.operator or "",
            )
            if r.get("success"):
                success_count += 1
                picked = int(r.get("picked_count", 0))
                tw = float(r.get("total_weight_kg", 0))
                total_weight_kg += tw
                results.append({
                    "row": idx + 1, "lot_no": lot_no, "ok": True,
                    "picked_count": picked, "total_weight_kg": tw,
                })
            else:
                fail_count += 1
                errs = r.get("errors", [])
                results.append({
                    "row": idx + 1, "lot_no": lot_no, "ok": False,
                    "reason": "; ".join(errs) if errs else "unknown",
                })
        except Exception as e:
            fail_count += 1
            results.append({"row": idx + 1, "lot_no": lot_no, "ok": False, "reason": f"exception: {e}"})
            logger.warning(f"[quick-paste] row {idx+1} 실패: {e}")

    logger.info(
        f"[quick-paste] 완료: 성공 {success_count} / 실패 {fail_count} / 총 {len(req.rows)} "
        f"· 총중량 {total_weight_kg:.1f} kg · 고객 {req.customer}"
    )
    return {
        "ok": True if fail_count == 0 else False,
        "data": {
            "total": len(req.rows),
            "success_count": success_count,
            "fail_count": fail_count,
            "total_weight_kg": total_weight_kg,
            "total_weight_mt": round(total_weight_kg / 1000.0, 3),
            "customer": req.customer,
            "results": results,
        },
        "message": f"{success_count}건 출고 / {fail_count}건 실패 (총 {round(total_weight_kg/1000.0, 2)} MT)",
    }


# ────────────────────────────────────────────────────────────
# F028 출고 확정 — PICKED → OUTBOUND (SOLD)
# engine.confirm_outbound(lot_no, force_all) 호출
# ────────────────────────────────────────────────────────────
class ConfirmOutboundRequest(BaseModel):
    lot_no: str = Field("", description="LOT 번호 (빈 값이면 전체 확정 — force_all 필수)")
    force_all: bool = Field(False, description="lot_no 빈 값일 때 전체 확정 명시")


class OneStopTonbagRef(BaseModel):
    lot_no: str = Field(..., min_length=1)
    sub_lt: str = Field(..., min_length=1)


class OneStopPickRequest(BaseModel):
    tonbags: List[OneStopTonbagRef] = Field(..., min_length=1)
    customer: str = Field("", description="picked_to/customer")
    sale_ref: str = Field("", description="sale_ref")


class OneStopCompleteRequest(BaseModel):
    tonbags: List[OneStopTonbagRef] = Field(..., min_length=1)
    customer: str = Field("", description="customer")
    sale_ref: str = Field("", description="sale_ref")
    validation_results: List[Dict[str, Any]] = Field(default_factory=list)
    proof_docs: List[Dict[str, Any]] = Field(default_factory=list)


@router.get("/picked-summary", summary="출고 확정 전 PICKED 톤백 요약 (F028 보조)")
def picked_summary(lot_no: str = ""):
    """
    PICKED 상태 톤백의 요약 반환 — 확정 전 미리보기용.
    lot_no 빈 값이면 전체 LOT 그룹.
    """
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    lot_no = (lot_no or "").strip()
    try:
        if lot_no:
            rows = engine.db.fetchall(
                """SELECT lot_no, COUNT(*) AS cnt, COALESCE(SUM(weight), 0) AS total_kg,
                          picked_to, sale_ref
                   FROM inventory_tonbag
                   WHERE status = 'PICKED' AND lot_no = ?
                   GROUP BY lot_no, picked_to, sale_ref""",
                (lot_no,),
            )
        else:
            rows = engine.db.fetchall(
                """SELECT lot_no, COUNT(*) AS cnt, COALESCE(SUM(weight), 0) AS total_kg,
                          picked_to, sale_ref
                   FROM inventory_tonbag
                   WHERE status = 'PICKED'
                   GROUP BY lot_no, picked_to, sale_ref
                   ORDER BY lot_no"""
            )
    except Exception as e:
        logger.warning(f"[picked-summary] 조회 실패: {e}")
        raise HTTPException(500, f"조회 실패: {e}")

    items = []
    total_count = 0
    total_kg = 0.0
    for r in rows or []:
        c = int(r["cnt"] if hasattr(r, "__getitem__") else r[0])
        kg = float(r["total_kg"] if hasattr(r, "__getitem__") else r[1])
        items.append({
            "lot_no": r["lot_no"],
            "count": c,
            "total_weight_kg": kg,
            "total_weight_mt": round(kg / 1000.0, 3),
            "picked_to": r["picked_to"] or "",
            "sale_ref": r["sale_ref"] or "",
        })
        total_count += c
        total_kg += kg

    return {
        "ok": True,
        "data": {
            "items": items,
            "total_lots": len(items),
            "total_count": total_count,
            "total_weight_kg": total_kg,
            "total_weight_mt": round(total_kg / 1000.0, 3),
        },
    }


@router.post("/confirm", summary="✅ 출고 확정 — PICKED → OUTBOUND (F028)")
def confirm_outbound_endpoint(req: ConfirmOutboundRequest):
    """
    engine.confirm_outbound(lot_no, force_all) 호출.
    - lot_no 지정: 해당 LOT의 PICKED 톤백 OUTBOUND 확정
    - lot_no 없고 force_all=True: 전체 PICKED 일괄 확정 (위험)
    """
    # Phase 2-1: 출고 확정 전 자동 백업
    try:
        from backend.api.actions import auto_backup
        auto_backup("outbound_confirm")
    except Exception as _bk_e:
        import logging as _log
        _log.getLogger(__name__).warning(f"[confirm_outbound] 자동 백업 실패 (계속): {_bk_e}")

    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None or not hasattr(engine, "confirm_outbound"):
        raise HTTPException(500, "엔진 confirm_outbound 없음")

    lot_no = (req.lot_no or "").strip() or None
    force_all = bool(req.force_all)

    if not lot_no and not force_all:
        return {
            "ok": False,
            "data": {"confirmed": 0, "errors": ["lot_no 미지정 + force_all=False → 차단"]},
            "error": "전체 확정은 force_all=True 명시 필수",
            "detail": {"code": "CONFIRM_ALL_BLOCKED"},
            "message": "lot_no 지정 또는 force_all=true 필요",
        }

    try:
        result = engine.confirm_outbound(lot_no=lot_no, force_all=force_all)
    except Exception as e:
        logger.exception(f"[confirm-outbound] 에러: {e}")
        raise HTTPException(500, f"Engine error: {e}")

    if result.get("success"):
        confirmed = int(result.get("confirmed", 0))
        logger.info(
            f"[confirm-outbound] OK: lot_no={lot_no or '(ALL)'}, confirmed={confirmed}"
        )
        # Phase 2-2: 출고 확정 감사 로그
        try:
            from backend.api.audit_helper import write_audit
            import os as _os
            _here = _os.path.dirname(_os.path.abspath(__file__))
            _db = _os.path.normpath(_os.path.join(_here, "..", "..", "data", "db", "sqm_inventory.db"))
            write_audit(
                _db, "OUTBOUND_CONFIRM",
                table_name="inventory",
                record_id=lot_no or "(ALL)",
                extra={"confirmed": confirmed, "force_all": force_all},
                user_note=f"출고 확정 {confirmed}건",
                created_by="WEBVIEW_OUTBOUND",
            )
        except Exception as _ae:
            logger.warning(f"[confirm-outbound] 감사 로그 실패 (무시): {_ae}")

        return {
            "ok": True,
            "data": {
                "lot_no": lot_no or "(ALL)",
                "confirmed": confirmed,
                "warnings": result.get("warnings", []),
            },
            "message": f"{confirmed}개 톤백 출고 확정 완료",
        }
    else:
        errors = result.get("errors", [])
        return {
            "ok": False,
            "data": {
                "lot_no": lot_no or "(ALL)",
                "confirmed": int(result.get("confirmed", 0)),
                "errors": errors,
            },
            "error": "출고 확정 실패",
            "detail": {"code": "CONFIRM_FAILED", "errors": errors},
            "message": result.get("message") or ("; ".join(errors) if errors else "확정 실패"),
        }


@router.post("/onestop-pick", summary="🚀 OneStop 출고 — DRAFT → WAIT_SCAN, 선택 톤백 PICKED")
def onestop_pick(req: OneStopPickRequest):
    """
    v864-2 S1OneStopOutboundDialog._confirm_draft 대응.
    선택된 AVAILABLE 톤백을 PICKED로 전환하고 WAIT_SCAN 단계로 넘긴다.
    """
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    picked = 0
    skipped: List[Dict[str, Any]] = []
    now = datetime.now().isoformat()
    picked_date = date.today().isoformat()
    customer = (req.customer or "").strip()
    sale_ref = (req.sale_ref or "").strip()

    try:
        db = engine.db
        _ensure_audit_log_table(db)
        for ref in req.tonbags:
            lot_no = ref.lot_no.strip()
            sub_lt = str(ref.sub_lt).strip()
            cur = db.execute(
                """
                UPDATE inventory_tonbag
                   SET status='PICKED', picked_to=?, picked_date=?, sale_ref=?, updated_at=?
                 WHERE lot_no=? AND CAST(sub_lt AS TEXT)=? AND status='AVAILABLE'
                """,
                (customer, picked_date, sale_ref, now, lot_no, sub_lt),
            )
            count = int(getattr(cur, "rowcount", 0) or 0)
            if count:
                picked += count
            else:
                skipped.append({"lot_no": lot_no, "sub_lt": sub_lt, "reason": "AVAILABLE 아님 또는 없음"})
        db.conn.commit()
    except Exception as e:
        try:
            engine.db.conn.rollback()
        except Exception:
            pass
        logger.exception(f"[onestop-pick] 실패: {e}")
        raise HTTPException(500, f"PICKED 전환 실패: {e}")

    return {
        "ok": picked > 0,
        "data": {"picked": picked, "requested": len(req.tonbags), "skipped": skipped[:100]},
        "message": f"{picked}개 톤백 PICKED 전환 완료",
    }


@router.post("/onestop-complete", summary="🚀 OneStop 출고 — FINALIZED → OUTBOUND 완료")
def onestop_complete(req: OneStopCompleteRequest):
    """
    v864-2 S1OneStopOutboundDialog._move_to_completed 대응.
    FINALIZED 건의 PICKED 톤백을 OUTBOUND로 확정하고 audit_log에 OUTBOUND_SOLD를 남긴다.
    """
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    completed = 0
    skipped: List[Dict[str, Any]] = []
    by_lot: Dict[str, Dict[str, Any]] = {}
    now = datetime.now().isoformat()
    outbound_date = date.today().isoformat()
    customer = (req.customer or "").strip()
    sale_ref = (req.sale_ref or "").strip()

    try:
        db = engine.db
        _ensure_audit_log_table(db)
        for ref in req.tonbags:
            lot_no = ref.lot_no.strip()
            sub_lt = str(ref.sub_lt).strip()
            row = db.fetchone(
                """
                SELECT lot_no, sub_lt, weight, status
                  FROM inventory_tonbag
                 WHERE lot_no=? AND CAST(sub_lt AS TEXT)=?
                """,
                (lot_no, sub_lt),
            )
            row_dict = _db_row_to_dict(row)
            cur = db.execute(
                """
                UPDATE inventory_tonbag
                   SET status='SOLD', outbound_date=?, updated_at=?
                 WHERE lot_no=? AND CAST(sub_lt AS TEXT)=? AND status='PICKED'
                """,
                (outbound_date, now, lot_no, sub_lt),
            )
            count = int(getattr(cur, "rowcount", 0) or 0)
            if not count:
                skipped.append({
                    "lot_no": lot_no,
                    "sub_lt": sub_lt,
                    "status": row_dict.get("status", ""),
                    "reason": "PICKED 아님 또는 없음",
                })
                continue
            completed += count
            entry = by_lot.setdefault(lot_no, {"lot_no": lot_no, "tonbag_count": 0, "weight_kg": 0.0})
            entry["tonbag_count"] += 1
            entry["weight_kg"] += float(row_dict.get("weight") or 0)

        for lot_no, entry in by_lot.items():
            # [fix B-4] inventory 상위 테이블 status 도 SOLD 갱신 (tonbag만 갱신하던 버그 수정)
            db.execute(
                "UPDATE inventory SET status='SOLD', sold_to=?, current_weight=0, updated_at=? WHERE lot_no=? AND status != 'SOLD'",
                (customer or None, now, lot_no)
            )
            _write_audit_log(
                db,
                event_type="SOLD",
                event_data={
                    "lot_no": lot_no,
                    "customer": customer,
                    "sale_ref": sale_ref,
                    "tonbag_count": entry["tonbag_count"],
                    "actual_qty_kg": entry["weight_kg"],
                    "validation_results": req.validation_results,
                    "proof_docs": req.proof_docs,
                },
                batch_id=sale_ref or f"WEBVIEW-{now[:10]}",
                user_note=f"S1 원스톱 출고 완료: {lot_no} → {customer or '-'}",
            )
        db.conn.commit()
    except Exception as e:
        try:
            engine.db.conn.rollback()
        except Exception:
            pass
        logger.exception(f"[onestop-complete] 실패: {e}")
        raise HTTPException(500, f"출고 완료 실패: {e}")

    return {
        "ok": completed > 0,
        "data": {
            "completed": completed,
            "requested": len(req.tonbags),
            "skipped": skipped[:100],
            "lots": list(by_lot.values()),
            "proof_docs": req.proof_docs,
        },
        "message": f"{completed}개 톤백 OUTBOUND 확정 완료",
    }


@router.post("/proof-upload", summary="📎 OneStop 출고 — 근거문서 저장소 업로드")
async def proof_upload(files: List[UploadFile] = File(...)):
    """
    v864-2 S1OneStopOutboundDialog._attach_proof_doc 대응.
    파일을 data/proof_docs/YYYY-MM-DD/ 에 저장하고 SHA-256 기반 중복명을 방지한다.
    """
    if not files:
        raise HTTPException(400, "업로드 파일 없음")
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    db = engine.db
    today_dir = PROOF_DOCS_DIR / date.today().isoformat()
    today_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Dict[str, Any]] = []
    duplicates: List[Dict[str, Any]] = []
    cleanup_removed = 0

    try:
        _ensure_audit_log_table(db)
        cleanup_removed = _cleanup_old_proof_docs(db, retention_days=90)
        seen_hashes = set()
        for existing in today_dir.iterdir():
            if existing.is_file() and "_" in existing.name:
                seen_hashes.add(existing.name.split("_", 1)[0])

        for upload in files:
            if not upload.filename:
                continue
            content = await upload.read()
            if not content:
                continue
            file_hash = hashlib.sha256(content).hexdigest()
            hash_prefix = file_hash[:8]
            safe_name = os.path.basename(upload.filename).replace("\\", "_").replace("/", "_")
            if hash_prefix in seen_hashes:
                duplicates.append({"filename": safe_name, "hash": file_hash})
                continue
            dest_name = f"{hash_prefix}_{safe_name}"
            dest_path = today_dir / dest_name
            suffix = 1
            while dest_path.exists():
                dest_path = today_dir / f"{hash_prefix}_{suffix}_{safe_name}"
                suffix += 1
            dest_path.write_bytes(content)
            seen_hashes.add(hash_prefix)
            doc = {
                "id": file_hash[:16],
                "name": safe_name,
                "stored_path": str(dest_path),
                "relative_path": str(dest_path.relative_to(BASE_DIR)),
                "size": len(content),
                "hash": file_hash,
                "added_at": datetime.now().isoformat(),
            }
            saved.append(doc)
            _write_audit_log(
                db,
                event_type="PROOF_ATTACH",
                event_data={
                    "file_name": safe_name,
                    "file_hash": file_hash,
                    "file_size": len(content),
                    "stored_path": str(dest_path),
                },
                user_note=f"근거문서 첨부: {safe_name}",
            )
        db.conn.commit()
    except Exception as e:
        try:
            db.conn.rollback()
        except Exception:
            pass
        logger.exception(f"[proof-upload] 실패: {e}")
        raise HTTPException(500, f"근거문서 저장 실패: {e}")

    return {
        "ok": True,
        "data": {
            "saved": saved,
            "duplicates": duplicates,
            "saved_count": len(saved),
            "duplicate_count": len(duplicates),
            "cleanup_removed": cleanup_removed,
            "base_dir": str(today_dir),
        },
        "message": f"근거문서 {len(saved)}건 저장"
        + (f" / 중복 {len(duplicates)}건" if duplicates else ""),
    }


@router.get("/audit-log", summary="📋 OneStop 출고 감사 로그")
def outbound_audit_log(
    date_from: str = "",
    date_to: str = "",
    type: str = "",
    limit: int = 500,
):
    """audit_log 조회. v864-2 감사 로그 팝업의 WebView 대응."""
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    limit = max(1, min(int(limit or 500), 1000))
    params: List[Any] = []
    sql = """
        SELECT id, event_type, event_data, batch_id, tonbag_id, user_note, created_at, created_by
          FROM audit_log
         WHERE 1=1
    """
    if type and type != "전체":
        sql += " AND event_type=?"
        params.append(type)
    if date_from:
        sql += " AND created_at >= ?"
        params.append(date_from + "T00:00:00")
    if date_to:
        sql += " AND created_at <= ?"
        params.append(date_to + "T23:59:59")
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    try:
        db = engine.db
        _ensure_audit_log_table(db)
        rows = db.fetchall(sql, tuple(params))
    except Exception as e:
        logger.exception(f"[audit-log] 조회 실패: {e}")
        raise HTTPException(500, f"감사 로그 조회 실패: {e}")

    data = [_db_row_to_dict(r) for r in rows or []]
    return {"ok": True, "data": {"rows": data, "count": len(data)}, "message": f"{len(data)}건 조회"}


# ────────────────────────────────────────────────────────────
# [Sprint 1-3-C] OneStop Outbound — OUT 스캔 파일 파싱
#
# v864-2: onestop_outbound.py Tab 3 OUT 스캔 검증
# Frontend uploads csv/xlsx → backend extracts {tonbag_uid, actual_kg}
# 검증 자체는 frontend에서 (선택된 톤백 expected vs actual 비교)
# ────────────────────────────────────────────────────────────
def _parse_scan_csv_text(text: str) -> List[Dict[str, Any]]:
    """CSV/TSV 텍스트 → [{tonbag_uid, actual_kg, raw}] 추출."""
    rows = []
    # 자동 구분자 감지 (탭 우선)
    delim = '\t' if text.count('\t') > text.count(',') else ','
    reader = _csv.reader(StringIO(text), delimiter=delim)
    headers = None
    for raw_row in reader:
        if not raw_row or all(not str(c).strip() for c in raw_row):
            continue
        if headers is None:
            # 첫 비어있지 않은 행 = 헤더
            headers = [str(c).strip().lower() for c in raw_row]
            continue
        if len(raw_row) < 2:
            continue
        d = {h: (raw_row[i] if i < len(raw_row) else '') for i, h in enumerate(headers)}
        # 컬럼 키 자동 매핑
        uid = ''
        for k in ('tonbag_uid', 'tonbag_id', 'sub_lt', 'tonbag', 'uid', 'id'):
            if d.get(k):
                uid = str(d[k]).strip()
                break
        if not uid and raw_row:
            uid = str(raw_row[0]).strip()
        actual = None
        for k in ('actual_kg', 'actual', 'weight_kg', 'weight', 'kg', 'net_kg'):
            v = d.get(k)
            if v:
                try:
                    actual = float(str(v).replace(',', '').strip())
                    break
                except (ValueError, TypeError):
                    continue
        if uid:
            rows.append({"tonbag_uid": uid, "actual_kg": actual, "raw": d})
    return rows


@router.post(
    "/onestop-scan-parse",
    summary="📊 OneStop 출고 — OUT 스캔 파일 파싱 (csv/xlsx) [Sprint 1-3-C]",
)
async def onestop_scan_parse(file: UploadFile = File(...)):
    """
    OUT 스캔 파일(csv/xlsx)을 파싱해 {tonbag_uid, actual_kg} 행 리스트 반환.
    Frontend는 이 결과를 selected_tonbags 와 매칭해 검증 수행.
    """
    if not file.filename:
        raise HTTPException(400, "파일명 없음")
    fname_lower = file.filename.lower()
    content = await file.read()
    if not content:
        raise HTTPException(400, "빈 파일")

    rows: List[Dict[str, Any]] = []
    if fname_lower.endswith(".csv"):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = content.decode("cp949")
            except Exception as e:
                raise HTTPException(400, f"CSV 인코딩 인식 실패 (utf-8/cp949 시도): {e}")
        rows = _parse_scan_csv_text(text)
    elif fname_lower.endswith((".xlsx", ".xls")):
        try:
            import pandas as pd
        except ImportError:
            raise HTTPException(500, "pandas 미설치 — pip install pandas openpyxl")
        try:
            df = pd.read_excel(BytesIO(content), header=0)
        except Exception as e:
            raise HTTPException(400, f"Excel 읽기 실패: {e}")
        # DataFrame → CSV 텍스트 → 파싱 (단일 경로 재사용)
        text = df.to_csv(index=False)
        rows = _parse_scan_csv_text(text)
    else:
        raise HTTPException(400, f"지원하지 않는 형식: {file.filename} (csv/xlsx 만)")

    if not rows:
        raise HTTPException(422, "파싱 결과 0행 (헤더에 tonbag_uid/sub_lt 와 actual_kg/weight 컬럼 필요)")

    return {
        "ok": True,
        "data": {
            "filename":     file.filename,
            "rows":         rows,
            "row_count":    len(rows),
            "uid_count":    sum(1 for r in rows if r.get("tonbag_uid")),
            "actual_count": sum(1 for r in rows if r.get("actual_kg") is not None),
        },
        "message": f"파싱 완료 — {len(rows)}행 추출",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET /api/outbound/proof-docs-list  — 증빙 서류 목록 (Stage 3)
# GET /api/outbound/proof-docs-download — 증빙 서류 다운로드 (Stage 3)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.get("/proof-docs-list", summary="📎 Proof docs 파일 목록 (Stage 3)")
def proof_docs_list(date: str = "", lot_no: str = ""):
    if not PROOF_DOCS_DIR.exists():
        return {"ok": True, "data": {"files": [], "total": 0}}
    files = []
    try:
        if date:
            search_dirs = [PROOF_DOCS_DIR / date] if (PROOF_DOCS_DIR / date).exists() else []
        else:
            search_dirs = sorted([d for d in PROOF_DOCS_DIR.iterdir() if d.is_dir()])[-30:]
        for date_dir in search_dirs:
            for batch_dir in (sorted(date_dir.iterdir()) if date_dir.is_dir() else []):
                if batch_dir.is_file():
                    fname = batch_dir.name
                    if lot_no and lot_no not in fname:
                        continue
                    files.append({"date": date_dir.name, "batch": "", "filename": fname,
                                  "path": str(batch_dir).replace("\\", "/"),
                                  "size_bytes": batch_dir.stat().st_size, "ext": batch_dir.suffix.lower()})
                elif batch_dir.is_dir():
                    for f in sorted(batch_dir.iterdir()):
                        if not f.is_file():
                            continue
                        if lot_no and lot_no not in f.name and lot_no not in batch_dir.name:
                            continue
                        files.append({"date": date_dir.name, "batch": batch_dir.name, "filename": f.name,
                                      "path": str(f).replace("\\", "/"),
                                      "size_bytes": f.stat().st_size, "ext": f.suffix.lower()})
        files.sort(key=lambda x: (x["date"], x["batch"], x["filename"]), reverse=True)
        files = files[:200]
        return {"ok": True, "data": {"files": files, "total": len(files)}}
    except Exception as e:
        logger.exception("proof-docs-list error: %s", e)
        return {"ok": False, "message": str(e)}


@router.get("/proof-docs-download", summary="📎 Proof docs 파일 다운로드 (Stage 3)")
def proof_docs_download(path: str = ""):
    from fastapi.responses import FileResponse
    if not path:
        raise HTTPException(400, "path 파라미터 필요")
    abs_path = Path(path).resolve()
    abs_root = PROOF_DOCS_DIR.resolve()
    try:
        abs_path.relative_to(abs_root)
    except ValueError:
        raise HTTPException(403, "허용되지 않는 경로")
    if not abs_path.exists() or not abs_path.is_file():
        raise HTTPException(404, "파일 없음")
    return FileResponse(path=str(abs_path), filename=abs_path.name, media_type="application/octet-stream")


# ════════════════════════════════════════════════════════════════════
# v8.7.0 (2026-05-24): 출고 바코드 스캔 → SOLD 확정
# 현장 직원이 출고 시점에 톤백 바코드를 스캔한 결과 Excel 업로드 →
# 매칭된 톤백을 PICKED → SOLD 전환 + 실제 위치 반영.
# 사용자 정책: "이 파일이 업로드되면 비로소 SOLD 확정"
# ════════════════════════════════════════════════════════════════════
@router.post(
    "/barcode-confirm-sold",
    summary="📦 바코드 스캔 → SOLD 확정 (출고 최종 단계)",
)
async def barcode_confirm_sold(file: UploadFile = File(...), dry_run: bool = True):
    """현장 바코드 스캔 Excel → PICKED 톤백을 SOLD 로 확정.

    Args:
        file: bar_code.xlsx (11컬럼: SAP/BL/Container/품목/UID/SubLT/번호/중량/상태/실제위치/셀위치)
        dry_run: True(기본)=미리보기만, False=실제 DB 반영

    Returns:
        {
            ok: bool,
            dry_run: bool,
            summary: {total, match, mismatch_status, not_found, sample_count, applied},
            preview: {matched: [], mismatch_status: [], not_found: []},  # 각 최대 50건
            warnings: []
        }
    """
    import sqlite3
    from time import perf_counter

    if not file.filename:
        raise HTTPException(400, "파일명 없음")
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, f"Excel 파일만 지원. 받은 파일: {file.filename}")

    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    try:
        from features.parsers.barcode_sold_parser import parse_barcode_sold_excel
    except ImportError as e:
        raise HTTPException(500, f"barcode_sold_parser import 실패: {e}")

    tmp_path = None
    try:
        content = await file.read()
        if not content:
            raise HTTPException(400, "빈 파일")
        ext = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        logger.info(f"[barcode-confirm-sold] 수신: {file.filename} ({len(content)} bytes, dry_run={dry_run})")

        t_parse_start = perf_counter()
        doc = parse_barcode_sold_excel(tmp_path)
        parse_sec = perf_counter() - t_parse_start
        if not doc.get("parse_ok"):
            return {
                "ok": False,
                "dry_run": dry_run,
                "summary": {"total": 0, "match": 0, "mismatch_status": 0, "not_found": 0, "sample_count": 0, "applied": 0},
                "preview": {"matched": [], "mismatch_status": [], "not_found": []},
                "warnings": doc.get("warnings", []),
                "error": "파싱 실패",
            }

        items = doc.get("items", [])
        matched: List[Dict[str, Any]] = []
        mismatch_status: List[Dict[str, Any]] = []
        not_found: List[Dict[str, Any]] = []

        # DB 직접 조회/업데이트 (engine 의존성 최소화)
        db_path = getattr(engine, "db_path", None) or os.path.join(BASE_DIR, "data", "db", "sqm_inventory.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            t_match_start = perf_counter()
            def _chunks(seq, size=900):
                for i in range(0, len(seq), size):
                    yield seq[i:i + size]

            uids = sorted({str(it.get("tonbag_uid") or "").strip() for it in items if it.get("tonbag_uid")})
            rows_by_uid: Dict[str, sqlite3.Row] = {}
            for chunk in _chunks(uids):
                placeholders = ",".join("?" * len(chunk))
                for row in conn.execute(
                    f"SELECT id, tonbag_uid, status, location, lot_no, sub_lt, sale_ref, picked_to, pick_ref, picking_id, weight, is_sample, bl_no, sap_no, inbound_date FROM inventory_tonbag WHERE tonbag_uid IN ({placeholders})",
                    chunk,
                ).fetchall():
                    rows_by_uid[str(row["tonbag_uid"] or "").strip()] = row

            fallback_items = [
                it for it in items
                if str(it.get("tonbag_uid") or "").strip() not in rows_by_uid
                and it.get("lot_no")
                and it.get("sub_lt") is not None
            ]
            lot_sub_keys = {
                (str(it.get("lot_no") or "").strip(), int(it.get("sub_lt")))
                for it in fallback_items
                if str(it.get("lot_no") or "").strip()
            }
            rows_by_lot_sub: Dict[tuple[str, int], sqlite3.Row] = {}
            for lot_chunk in _chunks(sorted({k[0] for k in lot_sub_keys})):
                placeholders = ",".join("?" * len(lot_chunk))
                for row in conn.execute(
                    f"SELECT id, tonbag_uid, status, location, lot_no, sub_lt, sale_ref, picked_to, pick_ref, picking_id, weight, is_sample, bl_no, sap_no, inbound_date FROM inventory_tonbag WHERE lot_no IN ({placeholders})",
                    lot_chunk,
                ).fetchall():
                    try:
                        key = (str(row["lot_no"] or "").strip(), int(row["sub_lt"]))
                    except Exception:
                        continue
                    if key in lot_sub_keys:
                        rows_by_lot_sub[key] = row

            # v8.7.0 추가: sold_table에 이미 등록된 tonbag_id 미리 조회 (진짜 중복 판정용)
            all_candidate_ids = []
            for it in items:
                uid = str(it.get("tonbag_uid") or "").strip()
                _row = rows_by_uid.get(uid)
                if _row is None and it.get("lot_no") and it.get("sub_lt") is not None:
                    try:
                        _row = rows_by_lot_sub.get((str(it["lot_no"]).strip(), int(it["sub_lt"])))
                    except Exception:
                        _row = None
                if _row is not None:
                    all_candidate_ids.append(_row["id"])
            already_in_sold_table: set = set()
            for chunk in _chunks(all_candidate_ids):
                placeholders = ",".join("?" * len(chunk))
                for row in conn.execute(
                    f"SELECT DISTINCT tonbag_id FROM sold_table WHERE tonbag_id IN ({placeholders})",
                    chunk,
                ).fetchall():
                    already_in_sold_table.add(row[0])

            for it in items:
                uid = str(it.get("tonbag_uid") or "").strip()
                row = rows_by_uid.get(uid)
                if row is None and it.get("lot_no") and it.get("sub_lt") is not None:
                    try:
                        row = rows_by_lot_sub.get((str(it["lot_no"]).strip(), int(it["sub_lt"])))
                    except Exception:
                        row = None

                if row is None:
                    not_found.append({
                        "tonbag_uid": uid, "lot_no": it.get("lot_no"),
                        "sub_lt": it.get("sub_lt"), "actual_location": it.get("actual_location"),
                    })
                    continue

                cur_status = (row["status"] or "").upper()
                in_sold_table = row["id"] in already_in_sold_table

                # v8.7.0 fix: 현장 바코드 스캔 = 위치 확정 + 출고 동시 이행 워크플로우
                # 진짜 중복 = inventory_tonbag.status='SOLD' AND sold_table 에도 행 존재
                # (둘 다 SOLD 인 경우만 스킵, 한쪽만 SOLD면 sold_table에 INSERT 보충)
                if cur_status == "SOLD" and in_sold_table:
                    mismatch_status.append({
                        "tonbag_uid": uid, "tonbag_id": row["id"],
                        "current_status": cur_status, "expected": "≠SOLD",
                        "actual_location": it.get("actual_location"),
                        "note": "이미 SOLD + sold_table 등록됨 — 중복 스킵",
                    })
                    continue

                matched.append({
                    "tonbag_uid": uid,
                    "tonbag_id": row["id"],
                    "previous_status": cur_status,
                    "current_location": row["location"],
                    "new_location": it.get("actual_location"),
                    "location_changed": (row["location"] or "") != (it.get("actual_location") or ""),
                    # sold_table INSERT 용 데이터 (inventory_tonbag + bar_code.xlsx item 병합)
                    "_db_lot_no":    row["lot_no"],
                    "_db_sub_lt":    row["sub_lt"],
                    "_db_sale_ref":  row["sale_ref"] if "sale_ref" in row.keys() else None,
                    "_db_picked_to": row["picked_to"] if "picked_to" in row.keys() else None,
                    "_db_pick_ref":  row["pick_ref"] if "pick_ref" in row.keys() else None,
                    "_db_picking_id":row["picking_id"] if "picking_id" in row.keys() else None,
                    "_db_weight":    row["weight"] if "weight" in row.keys() else None,
                    "_db_is_sample": row["is_sample"] if "is_sample" in row.keys() else 0,
                    "_db_bl_no":     row["bl_no"] if "bl_no" in row.keys() else None,
                    "_db_sap_no":    row["sap_no"] if "sap_no" in row.keys() else None,
                    "_needs_inventory_update": cur_status != "SOLD",
                    "_needs_sold_insert":      not in_sold_table,
                })
            match_sec = perf_counter() - t_match_start

            # 실제 적용
            applied = 0
            sold_inserted = 0
            apply_sec = 0.0
            if not dry_run and matched:
                t_apply_start = perf_counter()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                today = datetime.now().strftime("%Y-%m-%d")
                for m in matched:
                    # (a) inventory_tonbag UPDATE (이미 SOLD면 0 rows affected)
                    if m.get("_needs_inventory_update"):
                        conn.execute(
                            """
                            UPDATE inventory_tonbag
                            SET status = 'SOLD',
                                location = COALESCE(?, location),
                                location_updated_at = ?,
                                outbound_date = COALESCE(outbound_date, ?),
                                updated_at = ?
                            WHERE id = ? AND status != 'SOLD'
                            """,
                            (m["new_location"] or None, now, today, now, m["tonbag_id"]),
                        )
                    # (b) sold_table INSERT (v8.7.0 fix: SOLD 페이지 표시 위해 필수)
                    if m.get("_needs_sold_insert"):
                        weight_kg = float(m.get("_db_weight") or 0)
                        weight_mt = round(weight_kg / 1000.0, 4) if weight_kg else 0.0
                        conn.execute(
                            """
                            INSERT INTO sold_table (
                                lot_no, tonbag_id, sub_lt, tonbag_uid,
                                picking_id, sales_order_no, picking_no,
                                sap_no, bl_no, customer,
                                sold_qty_mt, sold_qty_kg,
                                status, sold_date, created_at, created_by,
                                is_sample
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SOLD', ?, ?, 'BARCODE_SCAN', ?)
                            """,
                            (
                                m.get("_db_lot_no"), m["tonbag_id"], m.get("_db_sub_lt"), m["tonbag_uid"],
                                m.get("_db_picking_id"), m.get("_db_sale_ref"), m.get("_db_pick_ref"),
                                m.get("_db_sap_no"), m.get("_db_bl_no"), m.get("_db_picked_to"),
                                weight_mt, weight_kg,
                                today, now,
                                int(m.get("_db_is_sample") or 0),
                            ),
                        )
                        sold_inserted += 1
                # 실제 적용 건수 재계산 (inventory_tonbag 기준)
                applied = conn.execute(
                    "SELECT COUNT(*) FROM inventory_tonbag WHERE id IN ({}) AND status = 'SOLD'".format(
                        ",".join("?" * len(matched))
                    ),
                    [m["tonbag_id"] for m in matched],
                ).fetchone()[0]

                # ════════════════════════════════════════════════════════════
                # v8.7.0 정책 (사용자 최종 확정 2026-05-25 - 절대 변경 금지):
                #   ┌─ 바코드 스캔 SOLD 확정 = 업로드 파일에 명시된 톤백만 1:1 처리.
                #   ├─ 자동 추론은 어떤 형태든 금지 (LOT 기반, picking_no 기반 모두 금지).
                #   ├─ 샘플 SOLD는 별도 워크플로우 (피킹리스트 기반)로 처리해야 함.
                #   └─ 이 함수에서 본품 외 톤백을 자동으로 SOLD 전환하지 않음.
                # ════════════════════════════════════════════════════════════
                conn.commit()
                apply_sec = perf_counter() - t_apply_start
                logger.info(
                    f"[barcode-confirm-sold] inventory_tonbag SOLD={applied}, sold_table INSERT={sold_inserted}"
                )
                logger.info(f"[barcode-confirm-sold] 반영 완료: {applied}건 ({file.filename})")

            sample_count = sum(1 for it in items if (it.get("weight_kg") or 0) < 10)

            return {
                "ok": True,
                "dry_run": dry_run,
                "summary": {
                    "total": len(items),
                    "match": len(matched),
                    "mismatch_status": len(mismatch_status),
                    "not_found": len(not_found),
                    "sample_count": sample_count,
                    "applied": applied if not dry_run else 0,
                    "sold_inserted": sold_inserted if not dry_run else 0,
                    "parse_sec": round(parse_sec, 3),
                    "match_sec": round(match_sec, 3),
                    "apply_sec": round(apply_sec, 3),
                },
                "preview": {
                    "matched": matched[:50],
                    "mismatch_status": mismatch_status[:50],
                    "not_found": not_found[:50],
                },
                "warnings": doc.get("warnings", []),
                "filename": file.filename,
            }
        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[barcode-confirm-sold] 처리 실패")
        raise HTTPException(500, f"처리 실패: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ════════════════════════════════════════════════════════════════════
# v8.7.0 (2026-05-25): 피킹리스트 기반 샘플 SOLD 확정
#
# 정책 (사용자 최종 확정 — 절대 변경 금지):
#   - 자동 추론 절대 금지. 피킹리스트 파일에 명시된 샘플 행만 1:1 처리.
#   - 본품은 별도 메뉴(barcode-confirm-sold)에서 바코드 검증으로 SOLD.
#   - 샘플은 바코드 안 찍히므로 피킹리스트 데이터로만 SOLD 가정 → 이 메뉴 사용.
#   - 매칭: 피킹리스트의 KG 행(is_sample=True) → inventory_tonbag.lot_no AND is_sample=1
# ════════════════════════════════════════════════════════════════════
@router.post(
    "/picking-sample-sold",
    summary="🧪 피킹리스트 기반 샘플 SOLD 확정 (PDF/Excel)",
)
async def picking_sample_sold(file: UploadFile = File(...), dry_run: bool = True):
    """피킹리스트 PDF/Excel → 샘플 행만 추출 → SOLD 확정.

    Args:
        file: Picking List PDF (.pdf) 또는 Excel (.xlsx/.xls)
        dry_run: True(기본)=미리보기만, False=실제 DB 반영

    Returns:
        {
            ok: bool,
            dry_run: bool,
            summary: {total_sample_rows, match, mismatch_status, not_found, applied, sold_inserted},
            preview: {matched: [], mismatch_status: [], not_found: []},
            warnings: []
        }
    """
    import sqlite3

    if not file.filename:
        raise HTTPException(400, "파일명 없음")
    fname_lower = file.filename.lower()
    if not fname_lower.endswith((".pdf", ".xlsx", ".xls")):
        raise HTTPException(400, f"PDF/Excel 파일만 지원. 받은 파일: {file.filename}")

    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")

    tmp_path = None
    try:
        content = await file.read()
        if not content:
            raise HTTPException(400, "빈 파일")
        ext = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        logger.info(f"[picking-sample-sold] 수신: {file.filename} ({len(content)} bytes, dry_run={dry_run})")

        # 파일 타입에 따라 파서 선택
        if ext == ".pdf":
            from features.parsers.picking_list_parser import parse_picking_list_pdf
            doc = parse_picking_list_pdf(tmp_path)
        else:
            from features.parsers.picking_excel_parser import parse_picking_list_excel
            doc = parse_picking_list_excel(tmp_path)

        if not doc.get("parse_ok"):
            return {
                "ok": False,
                "dry_run": dry_run,
                "summary": {"total_sample_rows": 0, "match": 0, "mismatch_status": 0, "not_found": 0, "applied": 0, "sold_inserted": 0},
                "preview": {"matched": [], "mismatch_status": [], "not_found": []},
                "warnings": doc.get("warnings", []),
                "error": "파싱 실패",
            }

        # 샘플 행만 필터링 (is_sample=True)
        sample_items = [it for it in doc.get("items", []) if it.get("is_sample")]
        if not sample_items:
            return {
                "ok": True,
                "dry_run": dry_run,
                "summary": {"total_sample_rows": 0, "match": 0, "mismatch_status": 0, "not_found": 0, "applied": 0, "sold_inserted": 0},
                "preview": {"matched": [], "mismatch_status": [], "not_found": []},
                "warnings": doc.get("warnings", []) + ["피킹리스트에 샘플(KG) 행 없음 — 처리할 항목 없음"],
                "message": "이 피킹리스트에는 샘플 행이 없습니다",
            }

        matched: List[Dict[str, Any]] = []
        mismatch_status: List[Dict[str, Any]] = []
        not_found: List[Dict[str, Any]] = []

        db_path = getattr(engine, "db_path", None) or os.path.join(BASE_DIR, "data", "db", "sqm_inventory.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            # 각 샘플 행에 대해 inventory_tonbag에서 매칭
            for it in sample_items:
                lot_no = str(it.get("lot_no") or "").strip()
                if not lot_no:
                    not_found.append({"lot_no": "(empty)", "qty_kg": it.get("qty_kg")})
                    continue

                # 매칭: lot_no + is_sample=1
                row = conn.execute(
                    """
                    SELECT id, tonbag_uid, status, sub_lt, weight,
                           sale_ref, picked_to, pick_ref, picking_id, bl_no, sap_no
                    FROM inventory_tonbag
                    WHERE lot_no = ? AND COALESCE(is_sample, 0) = 1
                    LIMIT 1
                    """,
                    (lot_no,),
                ).fetchone()

                if row is None:
                    not_found.append({
                        "lot_no": lot_no,
                        "qty_kg": it.get("qty_kg"),
                        "note": "inventory_tonbag에 샘플 톤백 없음",
                    })
                    continue

                # 중복 체크: 이미 SOLD + sold_table 등록됨
                in_sold_table = conn.execute(
                    "SELECT 1 FROM sold_table WHERE tonbag_id = ? LIMIT 1",
                    (row["id"],),
                ).fetchone() is not None
                cur_status = (row["status"] or "").upper()

                if cur_status == "SOLD" and in_sold_table:
                    mismatch_status.append({
                        "lot_no": lot_no,
                        "tonbag_id": row["id"],
                        "tonbag_uid": row["tonbag_uid"],
                        "current_status": cur_status,
                        "note": "이미 SOLD + sold_table 등록됨 — 중복 스킵",
                    })
                    continue

                matched.append({
                    "lot_no": lot_no,
                    "tonbag_id": row["id"],
                    "tonbag_uid": row["tonbag_uid"],
                    "sub_lt": row["sub_lt"],
                    "previous_status": cur_status,
                    "weight_kg": float(row["weight"] or 1.0),
                    "_db_sale_ref": row["sale_ref"],
                    "_db_picked_to": row["picked_to"],
                    "_db_pick_ref": row["pick_ref"],
                    "_db_picking_id": row["picking_id"],
                    "_db_bl_no": row["bl_no"],
                    "_db_sap_no": row["sap_no"],
                    "_needs_inventory_update": cur_status != "SOLD",
                    "_needs_sold_insert": not in_sold_table,
                })

            # 실제 적용
            applied = 0
            sold_inserted = 0
            if not dry_run and matched:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                today = datetime.now().strftime("%Y-%m-%d")
                for m in matched:
                    if m.get("_needs_inventory_update"):
                        conn.execute(
                            """
                            UPDATE inventory_tonbag
                            SET status = 'SOLD',
                                outbound_date = COALESCE(outbound_date, ?),
                                updated_at = ?
                            WHERE id = ? AND status != 'SOLD'
                            """,
                            (today, now, m["tonbag_id"]),
                        )
                    if m.get("_needs_sold_insert"):
                        weight_kg = float(m.get("weight_kg") or 1.0)
                        weight_mt = round(weight_kg / 1000.0, 4)
                        conn.execute(
                            """
                            INSERT INTO sold_table (
                                lot_no, tonbag_id, sub_lt, tonbag_uid,
                                picking_id, sales_order_no, picking_no,
                                sap_no, bl_no, customer,
                                sold_qty_mt, sold_qty_kg,
                                status, sold_date, created_at, created_by,
                                is_sample
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SOLD', ?, ?, 'PICKING_SAMPLE', 1)
                            """,
                            (
                                m["lot_no"], m["tonbag_id"], m.get("sub_lt"), m.get("tonbag_uid"),
                                m.get("_db_picking_id"),
                                doc.get("sales_order_no") or m.get("_db_sale_ref"),
                                doc.get("picking_no") or m.get("_db_pick_ref"),
                                m.get("_db_sap_no"), m.get("_db_bl_no"),
                                doc.get("customer") or m.get("_db_picked_to"),
                                weight_mt, weight_kg, today, now,
                            ),
                        )
                        sold_inserted += 1
                applied = conn.execute(
                    "SELECT COUNT(*) FROM inventory_tonbag WHERE id IN ({}) AND status = 'SOLD'".format(
                        ",".join("?" * len(matched))
                    ),
                    [m["tonbag_id"] for m in matched],
                ).fetchone()[0]
                conn.commit()
                logger.info(f"[picking-sample-sold] 반영 완료: inventory={applied}, sold_table INSERT={sold_inserted}")

            return {
                "ok": True,
                "dry_run": dry_run,
                "summary": {
                    "total_sample_rows": len(sample_items),
                    "match": len(matched),
                    "mismatch_status": len(mismatch_status),
                    "not_found": len(not_found),
                    "applied": applied if not dry_run else 0,
                    "sold_inserted": sold_inserted if not dry_run else 0,
                },
                "preview": {
                    "matched": matched[:50],
                    "mismatch_status": mismatch_status[:50],
                    "not_found": not_found[:50],
                },
                "warnings": doc.get("warnings", []),
                "filename": file.filename,
                "picking_no": doc.get("picking_no"),
                "customer": doc.get("customer"),
            }
        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[picking-sample-sold] 처리 실패")
        raise HTTPException(500, f"처리 실패: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
