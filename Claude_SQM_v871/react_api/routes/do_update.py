# -*- coding: utf-8 -*-
"""D/O 후속 연결 라우트."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from react_api.schemas.write_models import WriteResponse
from react_api.services.do_update_service import apply_do_update

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/do-update", tags=["do-update"])


class DoUpdateRequest(BaseModel):
    lot_no: str = Field(..., min_length=1)
    do_no: Optional[str] = None
    ship_date: Optional[str] = None
    arrival_date: Optional[str] = None
    con_return: Optional[str] = None
    free_time: Optional[int] = None


@router.post("/apply", response_model=WriteResponse)
def do_update_apply(req: DoUpdateRequest) -> WriteResponse:
    """D/O 후속 연결 — inventory 테이블 업데이트."""
    try:
        result = apply_do_update(
            lot_no=req.lot_no,
            do_no=req.do_no,
            ship_date=req.ship_date,
            arrival_date=req.arrival_date,
            con_return=req.con_return,
            free_time=req.free_time,
        )
        return WriteResponse(**result)
    except Exception as exc:
        logger.error("D/O 업데이트 실패: %s", exc, exc_info=True)
        raise HTTPException(500, "D/O 업데이트 실패")
