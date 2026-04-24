# -*- coding: utf-8 -*-
"""
SQM v864.3 — Outbound API (Phase 4-B)
POST /api/outbound/quick : 즉시 출고 (원스톱) — F015
engine.quick_outbound(lot_no, count, customer, reason, operator) 직접 호출
"""
import logging
import os
import tempfile
import csv as _csv
import shutil
import uuid
from datetime import datetime, timedelta
from io import StringIO, BytesIO
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Body, Form
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/outbound", tags=["outbound"])


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


# ────────────────────────────────────────────────────────────
# [Sprint 1-3-E] Proof Documents 저장소 + 90일 자동 정리
#
# v864-2: data/proof_docs/YYYY-MM-DD/ 에 근거문서 저장 + 90일 보존
# 프론트는 출고 확정(ooConfirmOutbound) 직후 이 endpoint 호출
# ────────────────────────────────────────────────────────────
PROOF_DOCS_ROOT = Path("data") / "proof_docs"
PROOF_DOCS_RETENTION_DAYS = 90


def _cleanup_old_proof_docs() -> Dict[str, Any]:
    """90일 이상된 proof_docs/{YYYY-MM-DD}/ 폴더 자동 정리. 시작 시 1회 호출."""
    if not PROOF_DOCS_ROOT.exists():
        return {"removed": 0, "skipped": 0}
    cutoff = datetime.now() - timedelta(days=PROOF_DOCS_RETENTION_DAYS)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    removed, skipped = 0, 0
    for date_dir in PROOF_DOCS_ROOT.iterdir():
        if not date_dir.is_dir():
            continue
        # 폴더명이 YYYY-MM-DD 형식인지 검증
        try:
            datetime.strptime(date_dir.name, "%Y-%m-%d")
        except ValueError:
            skipped += 1
            continue
        if date_dir.name < cutoff_str:
            try:
                shutil.rmtree(date_dir)
                removed += 1
                logger.info(f"[proof-docs] cleanup: removed {date_dir}")
            except Exception as e:
                logger.warning(f"[proof-docs] cleanup failed for {date_dir}: {e}")
    return {"removed": removed, "skipped": skipped, "cutoff_date": cutoff_str}


# 모듈 import 시 1회 cleanup (앱 시작 시점)
try:
    _cleanup_result = _cleanup_old_proof_docs()
    logger.info(f"[proof-docs] startup cleanup: {_cleanup_result}")
except Exception as _e:
    logger.warning(f"[proof-docs] startup cleanup error: {_e}")


@router.post(
    "/proof-upload",
    summary="📎 OneStop Outbound 근거문서 multi-file 업로드 [Sprint 1-3-E]",
)
async def proof_upload(
    files: List[UploadFile] = File(...),
    batch_id: Optional[str] = Form(None),
):
    """
    근거문서 multi-file 업로드.

    저장 경로: `data/proof_docs/YYYY-MM-DD/{batch_id}/`
    파일명 sanitize (알파벳/숫자/`. _ -` 만 유지) + 중복 시 _N 접미사
    90일 이상된 폴더는 앱 시작 시 자동 삭제됨.
    """
    if not files:
        raise HTTPException(400, "파일 없음")

    today = datetime.now().strftime("%Y-%m-%d")
    if not batch_id:
        batch_id = str(uuid.uuid4())[:8]

    target_dir = PROOF_DOCS_ROOT / today / batch_id
    target_dir.mkdir(parents=True, exist_ok=True)

    saved: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    for f in files:
        original = f.filename or "unknown"
        # 안전한 파일명 (한글 보존, 기호만 제거)
        safe_chars = []
        for c in original:
            if c.isalnum() or c in "._- ()[]가-힣":
                safe_chars.append(c)
            elif '\uac00' <= c <= '\ud7af' or '\u3131' <= c <= '\u3163':  # 한글
                safe_chars.append(c)
            else:
                safe_chars.append("_")
        safe_name = "".join(safe_chars).strip() or f"file_{len(saved)+1}"
        target = target_dir / safe_name
        # 중복 회피
        if target.exists():
            stem = target.stem
            ext = target.suffix
            counter = 1
            while target.exists():
                target = target_dir / f"{stem}_{counter}{ext}"
                counter += 1
        try:
            content = await f.read()
            target.write_bytes(content)
            saved.append({
                "original":  original,
                "saved_as":  str(target.relative_to(PROOF_DOCS_ROOT)).replace("\\", "/"),
                "size":      len(content),
            })
        except Exception as e:
            logger.error(f"[proof-upload] {original} 저장 실패: {e}")
            failed.append({"original": original, "reason": str(e)})

    return {
        "ok": True,
        "data": {
            "batch_id":     batch_id,
            "date":         today,
            "saved_count":  len(saved),
            "failed_count": len(failed),
            "files":        saved,
            "errors":       failed,
            "directory":    str(target_dir).replace("\\", "/"),
            "retention_days": PROOF_DOCS_RETENTION_DAYS,
        },
        "message": f"{len(saved)}개 근거문서 저장됨 (batch={batch_id}, dir={today})",
    }


@router.get(
    "/proof-cleanup-status",
    summary="📎 Proof docs 보존 정책 상태 조회 [Sprint 1-3-E]",
)
def proof_cleanup_status():
    """현재 proof_docs 디렉터리 상태 + 보존 정책 정보."""
    if not PROOF_DOCS_ROOT.exists():
        return {
            "ok": True,
            "data": {
                "exists": False,
                "retention_days": PROOF_DOCS_RETENTION_DAYS,
                "directory": str(PROOF_DOCS_ROOT),
            },
        }
    date_dirs = []
    total_files, total_size = 0, 0
    for date_dir in sorted(PROOF_DOCS_ROOT.iterdir()):
        if not date_dir.is_dir():
            continue
        sub_count = sum(1 for _ in date_dir.rglob("*") if _.is_file())
        sub_size = sum(p.stat().st_size for p in date_dir.rglob("*") if p.is_file())
        date_dirs.append({
            "date": date_dir.name,
            "file_count": sub_count,
            "size_bytes": sub_size,
        })
        total_files += sub_count
        total_size += sub_size
    return {
        "ok": True,
        "data": {
            "exists":         True,
            "retention_days": PROOF_DOCS_RETENTION_DAYS,
            "directory":      str(PROOF_DOCS_ROOT).replace("\\", "/"),
            "date_count":     len(date_dirs),
            "total_files":    total_files,
            "total_size_bytes": total_size,
            "dates":          date_dirs[-30:],  # 최근 30일만
        },
    }
