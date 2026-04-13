# -*- coding: utf-8 -*-
"""입고 API — PDF 4종 파싱 + LOT 생성 완전 연결 (v0.5.1).

워크플로우:
  1. POST /api/inbound/parse-preview  — PDF 업로드 → 파싱만 (미리보기)
  2. POST /api/inbound/confirm        — 파싱 결과 확인 후 DB 저장
  3. POST /api/inbound/create         — 수동 입력으로 LOT 직접 생성 (기존)

서류 종류:
  BL(선하증권) / PL(Packing List) / FA(Invoice) / DO(Delivery Order)
  4종 중 BL + PL + FA 필수, DO 선택
"""
import os
import tempfile
import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from react_api.schemas.write_models import InboundCreateRequest, WriteResponse
from react_api.services.inbound_write_service import create_inbound
from react_api.utils.db import get_engine, get_db, now_str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/inbound", tags=["inbound"])


# ── 임시 파일 저장 헬퍼 ────────────────────────────────────────────────────────
def _save_tmp(upload: UploadFile, content: bytes) -> str:
    """업로드 파일을 임시 경로에 저장하고 경로 반환."""
    _, ext = os.path.splitext(upload.filename or "upload.pdf")
    fd, path = tempfile.mkstemp(suffix=ext.lower(), prefix="sqm_inbound_")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(content)
    return path


def _cleanup(*paths):
    """임시 파일 정리."""
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


# ── 파서 결과 → process_inbound 파라미터 변환 ─────────────────────────────────
def _build_inbound_params(docs) -> dict:
    """
    ShipmentDocuments → process_inbound(packing_data, invoice_data, bl_data, do_data)
    형식으로 변환.
    """
    packing_data = {}
    invoice_data = {}
    bl_data      = {}
    do_data      = {}

    # ── Packing List (PL) ─────────────────────────────────────────────────────
    pl = getattr(docs, "packing_list", None)
    if pl:
        packing_data = {
            "lot_no":        getattr(pl, "lot_no",        "") or "",
            "sap_no":        getattr(pl, "sap_no",        "") or "",
            "bl_no":         getattr(pl, "bl_no",         "") or "",
            "container_no":  getattr(pl, "container_no",  "") or "",
            "product":       getattr(pl, "product",       "") or getattr(pl, "product_name", "") or "",
            "product_code":  getattr(pl, "product_code",  "") or "",
            "lot_sqm":       getattr(pl, "lot_sqm",       "") or "",
            "mxbg_pallet":   getattr(pl, "mxbg_pallet",   0)  or 0,
            "net_weight":    getattr(pl, "net_weight",    0.0) or 0.0,
            "gross_weight":  getattr(pl, "gross_weight",  0.0) or 0.0,
            "warehouse":     getattr(pl, "warehouse",     "") or "",
            "vessel":        getattr(pl, "vessel",        "") or "",
        }
        # 톤백 목록
        tonbags = getattr(pl, "tonbags", None) or getattr(pl, "lots", None)
        if tonbags:
            packing_data["tonbags"] = [
                {
                    "weight":    getattr(tb, "weight",    getattr(tb, "net_weight", 0)) or 0,
                    "is_sample": getattr(tb, "is_sample", False),
                }
                for tb in tonbags
            ]

    # ── Invoice (FA) ──────────────────────────────────────────────────────────
    inv = getattr(docs, "invoice", None)
    if inv:
        invoice_data = {
            "invoice_no":   getattr(inv, "invoice_no",   getattr(inv, "salar_invoice_no", "")) or "",
            "ship_date":    getattr(inv, "ship_date",    "") or "",
            "arrival_date": getattr(inv, "arrival_date", "") or "",
            "warehouse":    getattr(inv, "warehouse",    "") or "",
        }
        # PL에서 못 가져온 필드 보완
        for k in ("lot_no", "sap_no", "bl_no", "net_weight", "gross_weight", "product"):
            if not packing_data.get(k):
                v = getattr(inv, k, None)
                if v:
                    packing_data[k] = v

    # ── BL ───────────────────────────────────────────────────────────────────
    bl = getattr(docs, "bl", None)
    if bl:
        bl_data = {
            "bl_no":        getattr(bl, "bl_no",        "") or "",
            "vessel":       getattr(bl, "vessel",       "") or "",
            "container_no": getattr(bl, "container_no", "") or "",
            "ship_date":    getattr(bl, "ship_date",    "") or "",
        }
        if not packing_data.get("bl_no"):
            packing_data["bl_no"] = bl_data.get("bl_no", "")

    # ── DO ───────────────────────────────────────────────────────────────────
    do = getattr(docs, "do_doc", None) or getattr(docs, "do", None)
    if do:
        do_data = {
            "arrival_date":    getattr(do, "arrival_date",    "") or "",
            "free_time":       getattr(do, "free_time",       0)  or 0,
            "free_time_date":  getattr(do, "free_time_date",  "") or "",
            "con_return":      getattr(do, "con_return",      "") or "",
            "container_no":    getattr(do, "container_no",    "") or "",
        }

    return {
        "packing_data": packing_data or None,
        "invoice_data": invoice_data or None,
        "bl_data":      bl_data      or None,
        "do_data":      do_data      or None,
    }


# ── 1. PDF 파싱 미리보기 (DB 저장 없음) ─────────────────────────────────────────
@router.post("/parse-preview")
async def inbound_parse_preview(
    bl_file:  Optional[UploadFile] = File(None),
    pl_file:  Optional[UploadFile] = File(None),
    fa_file:  Optional[UploadFile] = File(None),
    do_file:  Optional[UploadFile] = File(None),
):
    """
    PDF 서류 업로드 → 파싱만 실행 → 미리보기 반환 (DB 저장 없음).

    - bl_file : BL (선하증권) PDF
    - pl_file : Packing List PDF  ← 필수
    - fa_file : Invoice (상업송장) PDF  ← 필수
    - do_file : Delivery Order PDF (선택)

    BL + PL + FA 중 하나라도 없으면 경고 반환.
    """
    if not pl_file and not fa_file and not bl_file:
        raise HTTPException(400, "BL / PL / FA 중 최소 1개 파일이 필요합니다.")

    tmp_paths = {}
    try:
        # 파일 저장
        for key, upload in [("bl", bl_file), ("pl", pl_file),
                             ("fa", fa_file), ("do", do_file)]:
            if upload:
                content = await upload.read()
                tmp_paths[key] = _save_tmp(upload, content)

        # DocumentParserV3 호출
        try:
            from parsers.document_parser_modular.parser import DocumentParserV3
            parser = DocumentParserV3()
            docs = parser.parse_shipment_documents(
                invoice_path=tmp_paths.get("fa"),
                packing_path=tmp_paths.get("pl"),
                bl_path=tmp_paths.get("bl"),
                do_path=tmp_paths.get("do"),
            )
        except ImportError:
            # fallback — document_detector로 단일 파일 파싱
            from parsers.document_detector import DocumentDetector
            detector = DocumentDetector()
            docs = None
            for key, path in tmp_paths.items():
                detected = detector.detect(path)
                logger.info(f"[Inbound] detected {key}: {detected}")

            return {
                "success": True,
                "message": "DocumentParserV3 없음 — 파일 감지만 완료. 수동 입력 사용 권장.",
                "data":    {"detected_files": list(tmp_paths.keys())},
                "generated_at": now_str(),
            }

        # 파싱 결과 → 미리보기 딕셔너리
        params   = _build_inbound_params(docs)
        packing  = params.get("packing_data") or {}
        invoice  = params.get("invoice_data") or {}
        bl       = params.get("bl_data")      or {}
        do_d     = params.get("do_data")      or {}

        warnings = []
        if not packing.get("lot_no"):  warnings.append("LOT NO 파싱 실패")
        if not packing.get("bl_no"):   warnings.append("BL NO 파싱 실패")
        if not packing.get("net_weight") and not packing.get("gross_weight"):
            warnings.append("중량 파싱 실패")

        # 교차검증 결과 포함
        cc = getattr(docs, "cross_check_result", None)
        cc_summary = str(cc.summary) if cc else ""

        return {
            "success":  True,
            "message":  f"파싱 완료 {'— 경고: ' + str(warnings) if warnings else ''}",
            "warnings": warnings,
            "data": {
                "lot_no":       packing.get("lot_no", ""),
                "sap_no":       packing.get("sap_no", ""),
                "bl_no":        packing.get("bl_no", "") or bl.get("bl_no", ""),
                "container_no": packing.get("container_no", ""),
                "product":      packing.get("product", ""),
                "net_weight":   packing.get("net_weight", 0),
                "gross_weight": packing.get("gross_weight", 0),
                "mxbg_pallet":  packing.get("mxbg_pallet", 0),
                "invoice_no":   invoice.get("invoice_no", ""),
                "ship_date":    invoice.get("ship_date", "") or bl.get("ship_date", ""),
                "arrival_date": invoice.get("arrival_date", "") or do_d.get("arrival_date", ""),
                "free_time":    do_d.get("free_time", 0),
                "con_return":   do_d.get("con_return", ""),
                "warehouse":    packing.get("warehouse", "") or invoice.get("warehouse", ""),
                "vessel":       packing.get("vessel", "") or bl.get("vessel", ""),
                "tonbag_count": len(packing.get("tonbags", [])),
                "cross_check":  cc_summary,
                # 전체 파라미터 (confirm 시 재사용)
                "_params":      params,
            },
            "generated_at": now_str(),
        }

    except Exception as exc:
        logger.error("inbound_parse_preview 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"파싱 실패: {exc}")
    finally:
        _cleanup(*tmp_paths.values())


# ── 2. 입고 확정 (파싱 결과 → DB 저장) ──────────────────────────────────────────
@router.post("/confirm")
async def inbound_confirm(
    bl_file:  Optional[UploadFile] = File(None),
    pl_file:  Optional[UploadFile] = File(None),
    fa_file:  Optional[UploadFile] = File(None),
    do_file:  Optional[UploadFile] = File(None),
    source_file: str = Form(default=""),
):
    """
    PDF 서류 업로드 → 파싱 → process_inbound() → LOT + 톤백 DB 저장.

    미리보기(/parse-preview) 확인 후 이 엔드포인트로 최종 저장.
    """
    if not pl_file and not fa_file and not bl_file:
        raise HTTPException(400, "BL / PL / FA 중 최소 1개 파일이 필요합니다.")

    tmp_paths = {}
    try:
        for key, upload in [("bl", bl_file), ("pl", pl_file),
                             ("fa", fa_file), ("do", do_file)]:
            if upload:
                content = await upload.read()
                tmp_paths[key] = _save_tmp(upload, content)

        # 파싱
        from parsers.document_parser_modular.parser import DocumentParserV3
        parser = DocumentParserV3()
        docs   = parser.parse_shipment_documents(
            invoice_path=tmp_paths.get("fa"),
            packing_path=tmp_paths.get("pl"),
            bl_path=tmp_paths.get("bl"),
            do_path=tmp_paths.get("do"),
        )
        params = _build_inbound_params(docs)
        packing = params.get("packing_data") or {}

        if not packing.get("lot_no"):
            raise HTTPException(422, "LOT NO 파싱 실패 — 수동 입고(/api/inbound/create)를 사용하세요.")

        # 중복 LOT 방지 선행 검사
        lot_no_check = packing.get("lot_no", "")
        with get_db() as _db:
            existing = _db.fetchone(
                "SELECT id FROM inventory WHERE lot_no = ?", (lot_no_check,)
            )
        if existing:
            raise HTTPException(409, f"이미 입고된 LOT입니다: {lot_no_check}")

        # DB 저장
        with get_engine() as engine:
            result = engine.process_inbound(
                packing_data=packing,
                invoice_data=params.get("invoice_data"),
                bl_data=params.get("bl_data"),
                do_data=params.get("do_data"),
                source_type="PDF",
                source_file=source_file or (
                    ",".join(f.filename for f in [bl_file, pl_file, fa_file, do_file] if f)
                ),
            )

        return {
            "success":        result.get("success", False),
            "message":        result.get("message", ""),
            "lot_no":         result.get("lot_no"),
            "created_lots":   result.get("created_lots", []),
            "created_tonbags":result.get("created_tonbags", 0),
            "warnings":       result.get("warnings", []),
            "errors":         result.get("errors", []),
            "generated_at":   now_str(),
        }

    except HTTPException:
        raise
    except ImportError as exc:
        raise HTTPException(501, f"파서 모듈 없음: {exc}")
    except Exception as exc:
        logger.error("inbound_confirm 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"입고 처리 실패: {exc}")
    finally:
        _cleanup(*tmp_paths.values())


# ── 3. 수동 입고 (기존 — 직접 입력) ────────────────────────────────────────────
@router.post("/create", response_model=WriteResponse)
def inbound_create(req: InboundCreateRequest) -> WriteResponse:
    """수동 입력으로 LOT 직접 생성 (PDF 없이 필드 직접 입력)."""
    with get_engine() as engine:
        result = create_inbound(engine, req)
    return WriteResponse(**result)


# ── 4. 문서 자동 감지 (doc_type 판별) ──────────────────────────────────────────
@router.post("/detect-doc-type")
async def detect_doc_type(file: UploadFile = File(...)):
    """
    단일 PDF → 문서 종류 자동 감지.
    반환: { doc_type: 'BL' | 'PL' | 'FA' | 'DO' | 'UNKNOWN' }
    """
    content = await file.read()
    tmp_path = None
    try:
        _, ext = os.path.splitext(file.filename or "upload.pdf")
        fd, tmp_path = tempfile.mkstemp(suffix=ext.lower(), prefix="sqm_detect_")
        os.close(fd)
        with open(tmp_path, "wb") as f:
            f.write(content)

        from parsers.document_detector import DocumentDetector
        detector = DocumentDetector()
        result   = detector.detect(tmp_path)

        doc_type = "UNKNOWN"
        if result:
            name = str(result).upper()
            if "PACKING" in name or "PL" in name:
                doc_type = "PL"
            elif "INVOICE" in name or "FA" in name:
                doc_type = "FA"
            elif "BL" in name or "BILL" in name or "LADING" in name:
                doc_type = "BL"
            elif "DO" in name or "DELIVERY" in name:
                doc_type = "DO"
            elif "PICKING" in name:
                doc_type = "PICKING"

        return {
            "success":    True,
            "doc_type":   doc_type,
            "raw_result": str(result),
            "filename":   file.filename,
            "generated_at": now_str(),
        }
    except Exception as exc:
        logger.error("detect_doc_type 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"문서 감지 실패: {exc}")
    finally:
        _cleanup(tmp_path)
