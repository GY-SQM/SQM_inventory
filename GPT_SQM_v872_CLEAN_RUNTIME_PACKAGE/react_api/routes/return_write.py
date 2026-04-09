# -*- coding: utf-8 -*-
"""Return 쓰기 라우트 — 소량반품 + Excel 다량반품."""
import logging
import os
import tempfile
from typing import Optional, Literal, List

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from react_api.schemas.write_models import WriteResponse
from react_api.services.return_write_service import execute_single_return
from react_api.utils.db import get_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/return", tags=["return"])


# ─── 소량반품 ───
class ReturnSingleRequest(BaseModel):
    lot_no: str = Field(..., min_length=1)
    sub_lt: int
    reason_code: Literal["품질불량", "수량오류", "고객요청", "파손", "기타"]
    note: Optional[str] = ""


@router.post("/single", response_model=WriteResponse)
def return_single(req: ReturnSingleRequest) -> WriteResponse:
    """소량반품 단건 처리."""
    with get_engine() as engine:
        result = execute_single_return(
            engine=engine,
            lot_no=req.lot_no,
            sub_lt=req.sub_lt,
            reason_code=req.reason_code,
            note=req.note or "",
        )
    return WriteResponse(**result)


# ─── Excel 다량반품 preview ───
@router.post("/bulk-excel")
def return_bulk_excel_preview(file: UploadFile = File(...)):
    """Excel 업로드 → 파싱 결과만 반환 (DB 저장 없음)."""
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename or "upload.xlsx")[1] or ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name

        from features.parsers.return_inbound_parser import parse_return_inbound_excel
        result = parse_return_inbound_excel(tmp_path)

        return {
            "parse_ok": result.get("parse_ok", False),
            "rows": result.get("items", []),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "total": len(result.get("items", [])),
        }
    except Exception as exc:
        logger.error("bulk-excel preview 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"Excel 파싱 실패: {str(exc)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ─── Excel 다량반품 confirm ───
class BulkReturnItem(BaseModel):
    lot_no: str
    sub_lt: Optional[int] = None
    reason: str = "기타"
    remark: str = ""


class BulkReturnConfirmRequest(BaseModel):
    items: List[BulkReturnItem] = Field(..., min_length=1)


@router.post("/bulk-confirm", response_model=WriteResponse)
def return_bulk_confirm(req: BulkReturnConfirmRequest) -> WriteResponse:
    """preview 결과를 받아 실제 DB 반품 처리. 전체 성공 or 전체 rollback."""
    with get_engine() as engine:
        success_count = 0
        fail_count = 0
        errors = []

        return_data = []
        for item in req.items:
            return_data.append({
                "lot_no": item.lot_no,
                "sub_lt": item.sub_lt,
                "reason": item.reason,
                "remark": item.remark,
            })

        try:
            result = engine.process_return(return_data)
            success = result.get("success", False)
            success_count = result.get("processed", 0)
            fail_count = len(req.items) - success_count
            errors = result.get("errors", [])

            return WriteResponse(
                success=success,
                message=f"다량반품 처리: 성공 {success_count}건, 실패 {fail_count}건",
                data={
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "errors": errors,
                    "warnings": result.get("warnings", []),
                },
            )
        except Exception as e:
            logger.exception("다량반품 처리 실패")
            return WriteResponse(
                success=False,
                message=f"다량반품 처리 실패: {str(e)}",
                data={"success_count": 0, "fail_count": len(req.items), "errors": [str(e)]},
            )
