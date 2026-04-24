# -*- coding: utf-8 -*-
"""
SQM v864.3 — Inbound API
POST /api/inbound/pdf  : base64 PDF decode -> pdf_parser -> DB save
Phase 4-D
"""
import base64
import logging
import tempfile
import os
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/inbound", tags=["inbound"])


# ────────────────────────────────────────────────────────────
# v864.3 Phase 4-B: 수동 입고 (Excel 업로드) — PyWebView 네이티브
# F002: 엑셀 파일 수동 입고
# tkinter filedialog → HTML <input type="file"> + multipart/form-data
# ────────────────────────────────────────────────────────────
_INBOUND_COLUMN_MAP = {
    # 표준 키 → 허용 Excel 컬럼명 (소문자 비교)
    "lot_no":         ["lot_no", "lot", "lot no", "lot번호", "로트", "로트번호"],
    "sap_no":         ["sap_no", "sap", "sap no", "sap번호"],
    "bl_no":          ["bl_no", "bl", "bl no", "b/l", "선하증권"],
    "container_no":   ["container_no", "container", "컨테이너", "컨테이너번호"],
    "product":        ["product", "product_name", "품목", "제품", "상품"],
    "product_code":   ["product_code", "제품코드", "품목코드"],
    "mxbg_pallet":    ["mxbg_pallet", "pallet", "팔레트", "mx_bag_pallet"],
    "net_weight":     ["net_weight", "net", "net(mt)", "net_kg", "순중량", "중량"],
    "gross_weight":   ["gross_weight", "gross", "gross(mt)", "gross_kg", "총중량"],
    "warehouse":      ["warehouse", "창고", "warehouse_name"],
    "arrival_date":   ["arrival_date", "arrival", "도착일"],
    "stock_date":     ["stock_date", "inbound_date", "입고일", "재고일"],
    "lot_sqm":        ["lot_sqm"],
    "salar_invoice_no": ["salar_invoice_no", "invoice", "인보이스"],
    "ship_date":      ["ship_date", "출항일", "선적일"],
    "con_return":     ["con_return", "반납일"],
    "free_time":      ["free_time", "프리타임"],
}


def _match_columns(df_columns) -> dict:
    """Excel 컬럼명을 표준 키로 매핑. {표준키: 원본컬럼} 반환."""
    result = {}
    lowered = {str(c).strip().lower(): c for c in df_columns}
    for std_key, aliases in _INBOUND_COLUMN_MAP.items():
        for alias in aliases:
            a = alias.strip().lower()
            if a in lowered:
                result[std_key] = lowered[a]
                break
    return result


def _clean_value(v: Any) -> Any:
    """pandas NaN / 빈 문자열 정리."""
    try:
        import math
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
    except Exception:
        pass
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    return v


@router.post("/bulk-import-excel", summary="📊 수동 입고 — Excel 업로드 (F002)")
async def bulk_import_excel(file: UploadFile = File(...)):
    """
    PyWebView 네이티브 수동 입고.
    - multipart/form-data 로 Excel 파일 업로드
    - pandas 로 header=1 (수동 입고 템플릿) 우선, 실패 시 header=0 fallback
    - 각 행을 engine.add_inventory_from_dict(row_dict) 호출
    - 결과: {success_count, fail_count, total, errors: [...]}
    """
    # 1. 입력 검증
    if not file.filename:
        raise HTTPException(400, "파일명이 없습니다.")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(400, f"Excel 파일만 지원 (.xlsx/.xls). 받은 파일: {file.filename}")

    # 2. pandas 확인
    try:
        import pandas as pd
    except ImportError:
        raise HTTPException(500, "pandas 미설치 — pip install pandas openpyxl")

    # 3. 엔진 확인
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진이 사용 불가 상태입니다.")

    # 4. 파일을 임시 저장
    tmp_path = None
    try:
        content = await file.read()
        if not content:
            raise HTTPException(400, "빈 파일")

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        logger.info(f"[bulk-import] 수신: {file.filename} ({len(content)} bytes) -> {tmp_path}")

        # 5. Excel 읽기 — 수동 입고 템플릿(header=1) 우선, 실패 시 header=0
        df = None
        header_used = None
        for header_row in (1, 0, 2):
            try:
                candidate = pd.read_excel(tmp_path, header=header_row)
                if candidate.empty:
                    continue
                # 컬럼 매핑이 최소 2개 이상 되면 성공으로 간주
                matched = _match_columns(candidate.columns)
                if len(matched) >= 2:
                    df = candidate
                    header_used = header_row
                    break
            except Exception as e:
                logger.debug(f"[bulk-import] header={header_row} 실패: {e}")
                continue
        if df is None or df.empty:
            raise HTTPException(400, "Excel 헤더를 인식할 수 없습니다. (header=0/1/2 시도 실패) 템플릿을 확인해주세요.")

        col_map = _match_columns(df.columns)
        logger.info(f"[bulk-import] header={header_used}, {len(df)}행, 매핑: {list(col_map.keys())}")
        if "lot_no" not in col_map:
            raise HTTPException(400, f"필수 컬럼 'lot_no' 없음. 감지된 컬럼: {list(df.columns)}")

        # 6. 행별 엔진 호출
        success_count = 0
        fail_count = 0
        errors = []
        for idx, row in df.iterrows():
            data = {}
            for std_key, orig_col in col_map.items():
                data[std_key] = _clean_value(row[orig_col])
            # lot_no 필수
            if not data.get("lot_no"):
                fail_count += 1
                errors.append({"row": int(idx) + 2, "reason": "lot_no 빈 값"})
                continue
            try:
                result = engine.add_inventory_from_dict(data)
                if result.get("success"):
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append({
                        "row": int(idx) + 2,
                        "lot_no": str(data.get("lot_no", "")),
                        "reason": result.get("message") or result.get("error") or "unknown",
                    })
            except Exception as e:
                fail_count += 1
                errors.append({
                    "row": int(idx) + 2,
                    "lot_no": str(data.get("lot_no", "")),
                    "reason": f"exception: {e}",
                })
                logger.warning(f"[bulk-import] row {idx} 실패: {e}")

        logger.info(f"[bulk-import] 완료: 성공 {success_count} / 실패 {fail_count} / 총 {len(df)}")

        return {
            "ok": True,
            "data": {
                "filename": file.filename,
                "total": int(len(df)),
                "success_count": success_count,
                "fail_count": fail_count,
                "header_row": header_used,
                "matched_columns": list(col_map.keys()),
                "errors": errors[:50],  # 최대 50건만
            },
            "message": f"{success_count}건 입고 완료 / {fail_count}건 실패",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[bulk-import] 예기치 않은 에러: {e}")
        raise HTTPException(500, f"Internal error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ────────────────────────────────────────────────────────────
# v864.3 Phase 4-B: 반품 입고 (Excel 업로드) — F007
# 기존 features.parsers.return_inbound_parser + return_inbound_engine 재사용
# ────────────────────────────────────────────────────────────
@router.post("/return-excel", summary="🔄 반품 입고 — Excel 업로드 (F007)")
async def return_inbound_excel(file: UploadFile = File(...)):
    """
    반품 Excel → picking_table 매칭 → inventory 복구 (트랜잭션).
    - parse_return_inbound_excel 로 파싱
    - process_return_inbound(engine, parsed) 로 DB 반영 (전체 or 롤백)
    """
    if not file.filename:
        raise HTTPException(400, "파일명이 없습니다.")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(400, f"Excel 파일만 지원 (.xlsx/.xls). 받은 파일: {file.filename}")

    # 엔진 확인
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진이 사용 불가 상태입니다.")

    # 파서/엔진 함수 import
    try:
        from features.parsers.return_inbound_parser import parse_return_inbound_excel
        from features.parsers.return_inbound_engine import process_return_inbound
    except ImportError as e:
        raise HTTPException(500, f"반품 엔진 import 실패: {e}")

    tmp_path = None
    try:
        content = await file.read()
        if not content:
            raise HTTPException(400, "빈 파일")

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        logger.info(f"[return-excel] 수신: {file.filename} ({len(content)} bytes)")

        # 1. 파싱
        parsed = parse_return_inbound_excel(tmp_path)
        if not parsed.get("parse_ok"):
            return {
                "ok": False,
                "data": {
                    "filename": file.filename,
                    "parse_ok": False,
                    "errors": parsed.get("errors", []),
                    "items": parsed.get("items", []),
                },
                "error": "파싱 실패",
                "detail": {"code": "PARSE_FAILED", "errors": parsed.get("errors", [])},
                "message": "Excel 파싱 실패",
            }

        # 2. DB 반영 (트랜잭션)
        result = process_return_inbound(engine, parsed, source_file=file.filename)

        if not result.get("success"):
            return {
                "ok": False,
                "data": {
                    "filename": file.filename,
                    "returned": result.get("returned", 0),
                    "errors": result.get("errors", []),
                    "details": result.get("details", []),
                },
                "error": "반품 처리 실패",
                "detail": {"code": "RETURN_FAILED", "errors": result.get("errors", [])},
                "message": "반품 처리 중 실패 — 전체 롤백",
            }

        logger.info(
            f"[return-excel] 완료: {result.get('returned', 0)}건 반품 복구 ({file.filename})"
        )
        return {
            "ok": True,
            "data": {
                "filename": file.filename,
                "returned": result.get("returned", 0),
                "details": result.get("details", [])[:50],
            },
            "message": f"{result.get('returned', 0)}건 반품 입고 완료",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[return-excel] 예기치 않은 에러: {e}")
        raise HTTPException(500, f"Internal error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass



class PdfInboundRequest(BaseModel):
    pdf_base64: str
    filename: str = "upload.pdf"


# ────────────────────────────────────────────────────────────
# F001 PDF 스캔 입고 — multipart 업로드 (base64 대안)
# 프론트에서 FormData 로 바로 PDF 전송 가능 (base64 인코딩 불필요)
# 내부적으로 /pdf base64 엔드포인트와 동일 로직 재사용
# ────────────────────────────────────────────────────────────
@router.post("/pdf-upload", summary="📄 PDF 스캔 입고 — multipart 업로드 (F001)")
async def pdf_inbound_upload(file: UploadFile = File(...)):
    """
    multipart/form-data 로 PDF 업로드 후 /api/inbound/pdf 와 동일하게 처리.
    """
    if not file.filename:
        raise HTTPException(400, "파일명 없음")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, f"PDF 파일만 지원. 받은 파일: {file.filename}")

    content = await file.read()
    if not content:
        raise HTTPException(400, "빈 파일")
    if content[:4] != b"%PDF":
        raise HTTPException(400, "유효한 PDF 파일이 아닙니다")

    # base64 인코딩 후 내부 함수 호출 — 로직 재사용
    import base64 as _b64
    req = PdfInboundRequest(
        pdf_base64=_b64.b64encode(content).decode("ascii"),
        filename=file.filename,
    )
    return pdf_inbound(req)


# ────────────────────────────────────────────────────────────
# [Sprint 1-2-B] OneStop 입고 — 4종 multipart + 크로스체크
#
# v864-2 source: gui_app_modular/dialogs/onestop_inbound.py
# Input: 4 multipart PDFs (BL, PL required; Invoice, DO optional)
# Flow:
#   1. 각 PDF 임시 저장
#   2. parsers.document_parser_modular.DocumentParserV3 로 4종 파싱
#   3. parsers.cross_check_engine.cross_check_documents 로 교차 검증
#   4. PL 결과만 기존 pdf_inbound 로직으로 DB 저장 (Sprint 1-2-C에서 4종 병합 저장)
#   5. 응답: cross_check 요약 + 18열 preview_rows + 저장 결과
# ────────────────────────────────────────────────────────────
def _safe_attr(obj, *names, default=""):
    """객체에서 첫 번째로 존재하고 truthy 한 속성값 반환."""
    if not obj:
        return default
    for n in names:
        v = getattr(obj, n, None)
        if v:
            return v
    return default


def _parse_one(parser, path, doc_type_method: str):
    """파싱 함수 호출. 실패 시 None 반환 (4종 중 하나 실패해도 나머지 진행)."""
    if not path:
        return None
    try:
        fn = getattr(parser, doc_type_method)
        return fn(path)
    except Exception as e:
        logger.warning(f"{doc_type_method} 파싱 실패: {e}", exc_info=True)
        return None


@router.post(
    "/onestop-upload",
    summary="📥 OneStop 입고 — 4종 PDF multipart + 크로스체크 (v864-2 OneStopInboundDialog)",
)
async def onestop_inbound_upload(
    bl: "UploadFile | None" = File(None),
    pl: UploadFile = File(...),
    invoice: "UploadFile | None" = File(None),
    do_file: "UploadFile | None" = File(None),
    dry_run: bool = Query(True, description="True면 파싱만 실행, DB 저장은 하지 않음 (Sprint 1-2-C 기본값)"),
):
    """
    4종 PDF 를 업로드하면 파싱 + 크로스체크 (+ 선택적 PL DB 저장) 수행.

    - `pl`: Packing List (필수)
    - `bl`: Bill of Lading (선택 — 크로스체크 용도)
    - `invoice`: Invoice / FA (선택 — 크로스체크 용도)
    - `do_file`: Delivery Order (선택 — 크로스체크 + 나중에 등록 가능)
    - `dry_run`: True(기본) = 파싱만, False = 기존처럼 PL 자동 저장 (레거시 호환)

    v864-2 워크플로우를 따르려면 `dry_run=True` 로 파싱 → 프론트에서 편집 →
    `/api/inbound/onestop-save` 호출로 최종 저장.
    """
    # 1. 각 파일 임시 저장
    inputs = [
        ("pl", pl, True),
        ("bl", bl, False),
        ("invoice", invoice, False),
        ("do", do_file, False),
    ]
    tmp_paths: "dict[str, str | None]" = {}
    for key, uf, required in inputs:
        if uf is None:
            if required:
                raise HTTPException(400, f"{key}: 파일이 없습니다 (필수)")
            tmp_paths[key] = None
            continue
        if not uf.filename or not uf.filename.lower().endswith(".pdf"):
            raise HTTPException(400, f"{key}: PDF 파일만 지원 (받음: {uf.filename})")
        content = await uf.read()
        if not content:
            raise HTTPException(400, f"{key}: 빈 파일")
        if content[:4] != b"%PDF":
            raise HTTPException(400, f"{key}: 유효한 PDF 파일이 아닙니다")
        tf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tf.write(content)
        tf.close()
        tmp_paths[key] = tf.name

    try:
        # 2. 파서 로드 + 4종 파싱
        try:
            from parsers.document_parser_modular.parser import DocumentParserV3
            parser = DocumentParserV3()
        except Exception as e:
            logger.error(f"DocumentParserV3 로드 실패: {e}", exc_info=True)
            raise HTTPException(500, f"파서 로드 실패: {e}")

        parsed = {
            "packing_list": _parse_one(parser, tmp_paths["pl"], "parse_packing_list"),
            "bl":           _parse_one(parser, tmp_paths["bl"], "parse_bl"),
            "invoice":      _parse_one(parser, tmp_paths["invoice"], "parse_invoice"),
            "do":           _parse_one(parser, tmp_paths["do"], "parse_do"),
        }

        if parsed["packing_list"] is None:
            raise HTTPException(422, "Packing List 파싱 실패 (최소 1종은 파싱되어야 합니다)")

        # 3. 크로스체크
        xc_items, xc_summary, xc_counts = [], "", {}
        try:
            from parsers.cross_check_engine import cross_check_documents
            xc = cross_check_documents(
                invoice=parsed["invoice"],
                packing_list=parsed["packing_list"],
                bl=parsed["bl"],
                do=parsed["do"],
            )
            xc_summary = xc.summary
            xc_counts = {
                "critical": xc.critical_count,
                "warning":  xc.warning_count,
                "info":     xc.info_count,
                "has_critical": xc.has_critical,
            }
            xc_items = [
                {
                    "field": it.field_name,
                    "level": int(it.level),
                    "icon": it.level_icon,
                    "message": it.message,
                    "sources": it.sources,
                }
                for it in xc.items
            ]
        except Exception as e:
            logger.warning(f"cross_check_documents 실패 — 건너뜀: {e}", exc_info=True)
            xc = None
            xc_summary = "크로스체크 엔진 미실행"
            xc_counts = {"critical": 0, "warning": 0, "info": 0, "has_critical": False}

        # 4. 18열 preview_rows 조립 (v864-2 PREVIEW_COLUMNS 매칭)
        preview_rows = []
        pl_obj = parsed["packing_list"]
        pl_rows = getattr(pl_obj, "rows", None) or getattr(pl_obj, "lots", None) or []
        bl_no = _safe_attr(parsed["bl"], "bl_no", "bl_number")
        inv_no = _safe_attr(parsed["invoice"], "invoice_no", "invoice_number")
        ship_date = _safe_attr(parsed["bl"], "ship_date", "shipped_on_board")
        arrival = _safe_attr(parsed["do"], "arrival_date", "eta")
        con_return = _safe_attr(parsed["do"], "con_return", "container_return")
        free_time = _safe_attr(parsed["do"], "free_time")
        wh = _safe_attr(parsed["do"], "warehouse", "warehouse_name")

        for idx, row in enumerate(pl_rows, start=1):
            lot = str(_safe_attr(row, "lot_no", "lot")).strip()
            xc_tag = xc.get_row_tag(lot) if xc and lot else None
            preview_rows.append({
                "no": idx,
                "lot_no":      lot,
                "sap_no":      str(_safe_attr(row, "sap_no")),
                "bl_no":       str(bl_no),
                "product":     str(_safe_attr(row, "product", "product_name")),
                "status":      "NEW",
                "container":   str(_safe_attr(row, "container_no", "container")),
                "code":        str(_safe_attr(row, "product_code", "code")),
                "lot_sqm":     str(_safe_attr(row, "lot_sqm")),
                "mxbg":        str(_safe_attr(row, "mxbg_pallet", "maxibag")),
                "net_kg":      str(_safe_attr(row, "net_weight", "net_kg")),
                "gross_kg":    str(_safe_attr(row, "gross_weight", "gross_kg")),
                "invoice_no":  str(inv_no),
                "ship_date":   str(ship_date),
                "arrival":     str(arrival),
                "con_return":  str(con_return),
                "free_time":   str(free_time),
                "wh":          str(wh),
                "xc_tag":      xc_tag,
            })

        # 5. PL 데이터 DB 저장 — dry_run=True 면 스킵 (Sprint 1-2-C 기본값)
        saved_result = None
        if not dry_run:
            try:
                with open(tmp_paths["pl"], "rb") as f:
                    pl_bytes = f.read()
                import base64 as _b64
                save_req = PdfInboundRequest(
                    pdf_base64=_b64.b64encode(pl_bytes).decode("ascii"),
                    filename=pl.filename,
                )
                saved_result = pdf_inbound(save_req)
            except Exception as e:
                logger.warning(f"PL DB 저장 실패 (파싱은 성공): {e}", exc_info=True)
                saved_result = {"ok": False, "message": f"DB 저장 실패: {e}"}

        # 6. 응답 조립
        return {
            "ok": True,
            "message": (
                f"4종 파싱 완료 — PL LOT {len(preview_rows)}개"
                + (f" | {xc_summary}" if xc_summary else "")
            ),
            "data": {
                "preview_rows": preview_rows,
                "preview_count": len(preview_rows),
                "cross_check": {
                    "summary": xc_summary,
                    **xc_counts,
                    "items": xc_items,
                },
                "parsed_docs": {
                    "bl_loaded":      parsed["bl"] is not None,
                    "pl_loaded":      parsed["packing_list"] is not None,
                    "invoice_loaded": parsed["invoice"] is not None,
                    "do_loaded":      parsed["do"] is not None,
                },
                "saved_result": (saved_result.get("data") if isinstance(saved_result, dict) else None),
                "bl_no":      str(bl_no),
                "invoice_no": str(inv_no),
            },
        }
    finally:
        for p in tmp_paths.values():
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass


# ────────────────────────────────────────────────────────────
# [Sprint 1-2-C] OneStop 입고 — 편집된 미리보기 → DB 저장
#
# v864-2 workflow: 파싱 → 미리보기에서 편집 → 확인 → DB 저장
# Frontend 는 /onestop-upload?dry_run=true 로 파싱만 받은 뒤,
# 18열 테이블에서 더블클릭으로 셀 편집하고, "DB 업로드" 버튼 클릭시
# 편집된 preview_rows JSON 을 이 엔드포인트로 POST.
# ────────────────────────────────────────────────────────────
class OneStopSaveRequest(BaseModel):
    rows: "list[dict]"


# 프론트 preview_rows (18열) → engine.add_inventory_from_dict 표준 키 매핑
_ONESTOP_ROW_KEY_MAP = {
    "lot_no":           "lot_no",
    "sap_no":           "sap_no",
    "bl_no":            "bl_no",
    "product":          "product",
    "container":        "container_no",
    "code":             "product_code",
    "lot_sqm":          "lot_sqm",
    "mxbg":             "mxbg_pallet",
    "net_kg":           "net_weight",
    "gross_kg":         "gross_weight",
    "invoice_no":       "salar_invoice_no",
    "ship_date":        "ship_date",
    "arrival":          "arrival_date",
    "con_return":       "con_return",
    "free_time":        "free_time",
    "wh":               "warehouse",
}


def _onestop_row_to_engine_dict(row: dict) -> dict:
    """프론트 18열 row → engine.add_inventory_from_dict 입력 dict 변환."""
    out = {}
    for fe_key, eng_key in _ONESTOP_ROW_KEY_MAP.items():
        v = row.get(fe_key)
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
            if not v:
                continue
        out[eng_key] = v
    return out


@router.post(
    "/onestop-save",
    summary="📤 OneStop 입고 — 편집된 18열 미리보기 → DB 저장 (Sprint 1-2-C)",
)
def onestop_inbound_save(req: OneStopSaveRequest):
    """
    /onestop-upload?dry_run=true 로 파싱 후 프론트에서 편집된 preview_rows 를
    받아 실제 DB에 저장.

    각 row 는 18개 필드를 가진 dict (lot_no/sap_no/bl_no/... /wh) 이며,
    engine.add_inventory_from_dict 로 저장된다.
    """
    rows = req.rows or []
    if not rows:
        raise HTTPException(400, "rows 가 비어있습니다")

    # 엔진 확인
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진이 사용 불가 상태입니다.")

    success_count, fail_count = 0, 0
    errors: "list[dict]" = []

    for idx, row in enumerate(rows, start=1):
        data = _onestop_row_to_engine_dict(row)
        if not data.get("lot_no"):
            fail_count += 1
            errors.append({"row": idx, "reason": "lot_no 빈 값"})
            continue
        try:
            result = engine.add_inventory_from_dict(data)
            if result.get("success"):
                success_count += 1
            else:
                fail_count += 1
                errors.append({
                    "row":    idx,
                    "lot_no": str(data.get("lot_no", "")),
                    "reason": result.get("message") or result.get("error") or "unknown",
                })
        except Exception as e:
            fail_count += 1
            errors.append({
                "row":    idx,
                "lot_no": str(data.get("lot_no", "")),
                "reason": f"exception: {e}",
            })
            logger.warning(f"[onestop-save] row {idx} 실패: {e}")

    logger.info(f"[onestop-save] 완료: 성공 {success_count} / 실패 {fail_count} / 총 {len(rows)}")

    return {
        "ok": True,
        "data": {
            "total":         len(rows),
            "success_count": success_count,
            "fail_count":    fail_count,
            "errors":        errors[:50],  # 최대 50건
        },
        "message": f"{success_count}건 입고 완료 / {fail_count}건 실패",
    }


# ────────────────────────────────────────────────────────────
# [Sprint 2-A] Inbound Template CRUD
# v864-2 source: dialogs/inbound_template_dialog.py (461 lines)
# Table: inbound_template (existing schema)
# ────────────────────────────────────────────────────────────
def _it_db():
    """SQLite connection."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    db_path = os.path.join(root, "data", "db", "sqm_inventory.db")
    import sqlite3
    con = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


@router.get("/templates", summary="📋 Inbound 템플릿 목록 [Sprint 2-A]")
def list_inbound_templates(active_only: bool = False):
    try:
        con = _it_db()
        sql = "SELECT * FROM inbound_template"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY template_name"
        rows = con.execute(sql).fetchall()
        con.close()
        return {"ok": True, "data": {"items": [dict(r) for r in rows], "total": len(rows)}}
    except Exception as e:
        logger.error(f"list_inbound_templates error: {e}")
        raise HTTPException(500, str(e))


@router.get("/templates/{template_id}", summary="📋 Inbound 템플릿 단일 조회 [Sprint 2-A]")
def get_inbound_template(template_id: str):
    try:
        con = _it_db()
        row = con.execute(
            "SELECT * FROM inbound_template WHERE template_id = ?",
            (template_id,),
        ).fetchone()
        con.close()
        if not row:
            raise HTTPException(404, f"템플릿 없음: {template_id}")
        return {"ok": True, "data": dict(row)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/templates", summary="📋 Inbound 템플릿 생성 [Sprint 2-A]")
def create_inbound_template(payload: "Dict[str, Any]" = Body(...)):
    """
    Body 필수: template_id, template_name
    선택: carrier_id, bag_weight_kg, product_hint, weight_format,
          gemini_hint_packing/invoice/bl, note, is_active, bl_format
    """
    tid = (payload or {}).get("template_id", "").strip()
    name = (payload or {}).get("template_name", "").strip()
    if not tid or not name:
        raise HTTPException(400, "template_id 와 template_name 필수")
    fields = {
        "template_id":         tid,
        "template_name":       name,
        "carrier_id":          payload.get("carrier_id", "UNKNOWN"),
        "bag_weight_kg":       int(payload.get("bag_weight_kg", 500)),
        "product_hint":        payload.get("product_hint", ""),
        "weight_format":       payload.get("weight_format", "EURO"),
        "gemini_hint_packing": payload.get("gemini_hint_packing", ""),
        "gemini_hint_invoice": payload.get("gemini_hint_invoice", ""),
        "gemini_hint_bl":      payload.get("gemini_hint_bl", ""),
        "note":                payload.get("note", ""),
        "is_active":           1 if payload.get("is_active", True) else 0,
        "bl_format":           payload.get("bl_format", ""),
    }
    cols = ", ".join(fields.keys())
    placeholders = ", ".join(["?"] * len(fields))
    try:
        con = _it_db()
        con.execute(f"INSERT INTO inbound_template ({cols}) VALUES ({placeholders})", list(fields.values()))
        con.commit(); con.close()
        return {"ok": True, "data": fields, "message": f"템플릿 생성됨: {name}"}
    except Exception as e:
        if "UNIQUE" in str(e) or "PRIMARY" in str(e):
            raise HTTPException(409, f"template_id 중복: {tid}")
        logger.error(f"create_inbound_template error: {e}")
        raise HTTPException(500, str(e))


@router.patch("/templates/{template_id}", summary="📋 Inbound 템플릿 수정 [Sprint 2-A]")
def update_inbound_template(template_id: str, updates: "Dict[str, Any]" = Body(...)):
    allowed = {"template_name", "carrier_id", "bag_weight_kg", "product_hint", "weight_format",
               "gemini_hint_packing", "gemini_hint_invoice", "gemini_hint_bl",
               "note", "is_active", "bl_format"}
    fields = {k: v for k, v in (updates or {}).items() if k in allowed}
    if not fields:
        raise HTTPException(400, f"수정 가능 필드 없음. 허용: {sorted(allowed)}")
    if "is_active" in fields:
        fields["is_active"] = 1 if fields["is_active"] else 0
    if "bag_weight_kg" in fields:
        try: fields["bag_weight_kg"] = int(fields["bag_weight_kg"])
        except (ValueError, TypeError):
            raise HTTPException(400, "bag_weight_kg 는 정수")
    sets = ", ".join(f"{k}=?" for k in fields.keys())
    values = list(fields.values()) + [template_id]
    try:
        con = _it_db()
        cur = con.execute(f"UPDATE inbound_template SET {sets} WHERE template_id=?", values)
        if cur.rowcount == 0:
            con.close()
            raise HTTPException(404, f"템플릿 없음: {template_id}")
        con.commit(); con.close()
        return {"ok": True, "data": {"template_id": template_id, "updated": list(fields.keys())}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/templates/{template_id}", summary="📋 Inbound 템플릿 삭제 [Sprint 2-A]")
def delete_inbound_template(template_id: str):
    try:
        con = _it_db()
        cur = con.execute("DELETE FROM inbound_template WHERE template_id=?", (template_id,))
        if cur.rowcount == 0:
            con.close()
            raise HTTPException(404, f"템플릿 없음: {template_id}")
        con.commit(); con.close()
        return {"ok": True, "message": f"삭제됨: {template_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/pdf")
def pdf_inbound(req: PdfInboundRequest):
    """
    PDF 스캔 입고 처리.
    1. base64 디코드 -> 임시 파일
    2. parsers.pdf_parser 로 문서 파싱
    3. 파싱 결과 DB 저장 (engine_modules 재활용)
    4. 결과 반환
    """
    # 1. base64 decode
    try:
        pdf_bytes = base64.b64decode(req.pdf_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}")

    if len(pdf_bytes) < 4 or pdf_bytes[:4] != b"%PDF":
        raise HTTPException(status_code=400, detail="Not a valid PDF file")

    # 2. 임시 파일로 저장
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        # 3. pdf_parser 시도
        parsed = None
        parse_error = None
        try:
            from parsers.pdf_parser import SQMPdfParser
            parser = SQMPdfParser()
            parsed = parser.parse(tmp_path)
            logger.info(f"PDF parsed OK: {req.filename}, result type: {type(parsed).__name__}")
        except ImportError:
            logger.warning("pdf_parser not available (PyMuPDF missing?)")
            parse_error = "pdf_parser unavailable"
        except Exception as e:
            logger.warning(f"pdf_parser error: {e}")
            parse_error = str(e)

        # 4. DB 저장 — v864.3: PackingListData.lots 순회하여 engine.add_inventory_from_dict()
        saved_count = 0
        save_errors = []
        saved_lots = []
        parse_type = type(parsed).__name__ if parsed is not None else None
        if parsed is not None and parse_type == "PackingListData":
            try:
                from backend.api import engine, ENGINE_AVAILABLE
                if ENGINE_AVAILABLE and engine is not None and hasattr(engine, "add_inventory_from_dict"):
                    # 공통 필드 (product, vessel 등) 전파
                    common = {
                        "product":      getattr(parsed, "product", "") or "",
                        "product_code": getattr(parsed, "product_code", "") or "",
                    }
                    for idx, lot in enumerate(getattr(parsed, "lots", []) or []):
                        lot_data = dict(common)
                        lot_data.update(lot or {})
                        if not lot_data.get("lot_no"):
                            save_errors.append({"index": idx, "reason": "lot_no 없음"})
                            continue
                        try:
                            result = engine.add_inventory_from_dict(lot_data)
                            if result.get("success"):
                                saved_count += 1
                                saved_lots.append(str(lot_data.get("lot_no")))
                            else:
                                save_errors.append({
                                    "index": idx,
                                    "lot_no": str(lot_data.get("lot_no", "")),
                                    "reason": result.get("message") or result.get("error") or "unknown",
                                })
                        except Exception as e:
                            save_errors.append({
                                "index": idx,
                                "lot_no": str(lot_data.get("lot_no", "")),
                                "reason": f"exception: {e}",
                            })
                else:
                    save_errors.append({"reason": "엔진 사용 불가"})
            except Exception as e:
                logger.warning(f"[pdf-inbound] DB save error: {e}")
                save_errors.append({"reason": f"exception: {e}"})

        # 5. 응답
        if parsed is not None:
            return {
                "ok": True,
                "success": True,  # backward-compat
                "message": f"PDF 파싱 완료 ({req.filename}) · 저장 {saved_count}건 · 실패 {len(save_errors)}건",
                "data": {
                    "filename": req.filename,
                    "size_bytes": len(pdf_bytes),
                    "parse_type": parse_type,
                    "saved_count": saved_count,
                    "saved_lots": saved_lots[:50],
                    "errors": save_errors[:50],
                    "folio": getattr(parsed, "folio", "") if parse_type == "PackingListData" else None,
                    "product": getattr(parsed, "product", "") if parse_type == "PackingListData" else None,
                    "lots_total": len(getattr(parsed, "lots", []) or []) if parse_type == "PackingListData" else None,
                },
            }
        else:
            return {
                "ok": False,
                "success": False,
                "message": f"PDF 파싱 실패: {parse_error or '알 수 없는 에러'}",
                "error": parse_error or "parse failed",
                "detail": {"code": "PDF_PARSE_FAILED", "parse_error": parse_error},
                "data": {
                    "filename": req.filename,
                    "size_bytes": len(pdf_bytes),
                    "parse_error": parse_error,
                },
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"pdf_inbound unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
