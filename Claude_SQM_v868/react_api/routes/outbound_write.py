# -*- coding: utf-8 -*-
"""출고 처리 + 출고 취소 엔드포인트."""
from fastapi import APIRouter

from react_api.schemas.write_models import (
    OutboundExecuteRequest,
    OutboundCancelRequest,
    WriteResponse,
)
from react_api.services.outbound_write_service import execute_outbound, cancel_outbound
from react_api.utils.db import get_db

router = APIRouter(prefix="/api/outbound", tags=["outbound"])


@router.post("/execute", response_model=WriteResponse)
def outbound_execute(req: OutboundExecuteRequest) -> WriteResponse:
    with get_db() as db:
        result = execute_outbound(db, req)
    return WriteResponse(**result)


@router.put("/cancel", response_model=WriteResponse)
def outbound_cancel(req: OutboundCancelRequest) -> WriteResponse:
    with get_db() as db:
        result = cancel_outbound(db, req)
    return WriteResponse(**result)
