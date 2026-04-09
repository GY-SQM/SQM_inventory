# -*- coding: utf-8 -*-
"""위치 매핑 라우트 — 단건 + Excel 일괄."""
import logging
import os
import tempfile
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from react_api.schemas.write_models import WriteResponse
from react_api.services.location_bulk_service import (
    update_single_location, bulk_update_locations, parse_location_excel,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/location", tags=["location-bulk"])


class SingleLocationRequest(BaseModel):
    lot_no: str = Field(..., min_length=1)
    sub_lt: int
    location: str = Field(..., min_length=1)
    operator: Optional[str] = "web_user"


class BulkLocationItem(BaseModel):
    lot_no: str
    sub_lt: int
    location: str


class BulkLocationRequest(BaseModel):
    items: List[BulkLocationItem] = Field(..., min_length=1)
    operator: Optional[str] = "web_user"


@router.post("/single-update", response_model=WriteResponse)
def location_single_update(req: SingleLocationRequest) -> WriteResponse:
    """단건 위치 변경."""
    try:
        result = update_single_location(
            lot_no=req.lot_no, sub_lt=req.sub_lt,
            location=req.location, operator=req.operator or "web_user",
        )
        return WriteResponse(**result)
    except Exception as exc:
        logger.error("단건 위치 변경 실패: %s", exc, exc_info=True)
        raise HTTPException(500, "위치 변경 실패")


@router.post("/bulk-upload")
def location_bulk_upload(file: UploadFile = File(...)):
    """위치 매핑 Excel 업로드 → preview."""
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename or "upload.xlsx")[1] or ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        result = parse_location_excel(tmp_path)
        return result
    except Exception as exc:
        logger.error("위치 Excel 파싱 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"Excel 파싱 실패: {str(exc)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@router.post("/bulk-update", response_model=WriteResponse)
def location_bulk_update(req: BulkLocationRequest) -> WriteResponse:
    """일괄 위치 변경."""
    try:
        items = [{"lot_no": i.lot_no, "sub_lt": i.sub_lt, "location": i.location} for i in req.items]
        result = bulk_update_locations(items, operator=req.operator or "web_user")
        return WriteResponse(**result)
    except Exception as exc:
        logger.error("일괄 위치 변경 실패: %s", exc, exc_info=True)
        raise HTTPException(500, "일괄 위치 변경 실패")
