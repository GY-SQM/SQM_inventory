# -*- coding: utf-8 -*-
"""
SQM v864.3 — Allocation API (Phase 4-B)
POST /api/allocation/bulk-import-excel : Excel 업로드 → reserve_from_allocation
F014 위치 배정 (Allocation 출고 예약) 네이티브 구현
"""
import logging
import os
import tempfile
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/allocation", tags=["allocation"])


# Allocation 행 컬럼 별칭 매핑
_ALLOC_COLUMN_MAP = {
    "lot_no":        ["lot_no", "lot", "lot no", "lot번호", "로트"],
    "sold_to":       ["sold_to", "sold to", "customer", "고객", "고객사"],
    "sale_ref":      ["sale_ref", "sale ref", "sales_ref", "sales ref", "sc_rcvd", "sc rcvd", "판매참조"],
    "qty_mt":        ["qty_mt", "qty", "quantity", "qty mt", "qty(mt)", "kg", "weight", "수량"],
    "outbound_date": ["outbound_date", "outbound date", "ship_date", "ship date", "출고일", "선적일"],
    "sublot_count":  ["sublot_count", "sublot count", "tonbag_count", "tonbag count", "톤백수"],
    "is_sample":     ["is_sample", "sample", "샘플"],
    "export_type":   ["export_type", "export type", "수출종류"],
    "unit":          ["unit", "단위"],
}


def _match_alloc_columns(df_columns) -> dict:
    """Excel 컬럼 → 표준 키 매핑"""
    result = {}
    lowered = {str(c).strip().lower(): c for c in df_columns}
    for std_key, aliases in _ALLOC_COLUMN_MAP.items():
        for alias in aliases:
            a = alias.strip().lower()
            if a in lowered:
                result[std_key] = lowered[a]
                break
    return result


def _clean_value(v: Any) -> Any:
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


@router.post("/bulk-import-excel", summary="📍 Allocation 입력 — Excel 업로드 (F014)")
async def bulk_import_allocation(file: UploadFile = File(...)):
    """
    Allocation Excel → 톤백 예약 (AVAILABLE → RESERVED).
    - engine.reserve_from_allocation(rows, source_file) 호출
    - All-or-Nothing 트랜잭션
    """
    if not file.filename:
        raise HTTPException(400, "파일명이 없습니다.")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(400, f"Excel 파일만 지원 (.xlsx/.xls). 받은 파일: {file.filename}")

    try:
        import pandas as pd
    except ImportError:
        raise HTTPException(500, "pandas 미설치")

    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:
        raise HTTPException(500, f"엔진 로드 실패: {e}")
    if not ENGINE_AVAILABLE or engine is None:
        raise HTTPException(500, "엔진 사용 불가")
    if not hasattr(engine, "reserve_from_allocation"):
        raise HTTPException(500, "엔진에 reserve_from_allocation 메서드 없음")

    tmp_path = None
    try:
        content = await file.read()
        if not content:
            raise HTTPException(400, "빈 파일")

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        logger.info(f"[allocation-import] 수신: {file.filename} ({len(content)} bytes)")

        # header=0/1/2 자동 감지
        df = None
        header_used = None
        for header_row in (0, 1, 2):
            try:
                candidate = pd.read_excel(tmp_path, header=header_row)
                if candidate.empty:
                    continue
                matched = _match_alloc_columns(candidate.columns)
                if "lot_no" in matched and ("sold_to" in matched or "qty_mt" in matched):
                    df = candidate
                    header_used = header_row
                    break
            except Exception as e:
                logger.debug(f"[allocation-import] header={header_row} 실패: {e}")
                continue
        if df is None or df.empty:
            raise HTTPException(400, "Excel 헤더 인식 실패 — lot_no + sold_to/qty_mt 컬럼 필요")

        col_map = _match_alloc_columns(df.columns)
        logger.info(f"[allocation-import] header={header_used}, {len(df)}행, 매핑: {list(col_map.keys())}")

        # row dict 리스트 생성
        rows = []
        for idx, row in df.iterrows():
            r = {}
            for std_key, orig_col in col_map.items():
                r[std_key] = _clean_value(row[orig_col])
            if not r.get("lot_no"):
                continue  # 빈 lot_no 행은 skip
            # customer 별명: sold_to ↔ customer
            if r.get("sold_to") and not r.get("customer"):
                r["customer"] = r["sold_to"]
            rows.append(r)

        if not rows:
            raise HTTPException(400, "유효한 데이터 행이 없습니다 (lot_no 전부 비어있음)")

        # 엔진 호출 — 트랜잭션 내부 처리
        result = engine.reserve_from_allocation(rows, source_file=file.filename)

        success = bool(result.get("success"))
        reserved = int(result.get("reserved", 0))
        errors = result.get("errors", [])
        error_details = result.get("error_details", [])
        plan_ids = result.get("plan_ids", [])

        if success:
            logger.info(
                f"[allocation-import] 완료: {reserved}건 예약 / 에러 {len(errors)}건 ({file.filename})"
            )
            return {
                "ok": True,
                "data": {
                    "filename": file.filename,
                    "total_rows": len(rows),
                    "reserved": reserved,
                    "plan_ids": plan_ids[:50],
                    "header_row": header_used,
                    "matched_columns": list(col_map.keys()),
                    "errors": errors[:20],
                    "error_details": error_details[:20],
                    "warnings": result.get("warnings", [])[:20],
                },
                "message": f"{reserved}건 Allocation 예약 완료 / 경고 {len(errors)}건",
            }
        else:
            return {
                "ok": False,
                "data": {
                    "filename": file.filename,
                    "total_rows": len(rows),
                    "reserved": reserved,
                    "errors": errors[:20],
                    "error_details": error_details[:20],
                },
                "error": "Allocation 예약 실패",
                "detail": {"code": "ALLOCATION_FAILED", "errors": errors[:10]},
                "message": "Allocation 실패 — 전체 롤백",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[allocation-import] 예기치 않은 에러: {e}")
        raise HTTPException(500, f"Internal error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
