# -*- coding: utf-8 -*-
"""출고 처리 + 출고 취소 엔드포인트."""
from fastapi import APIRouter

from react_api.schemas.write_models import (
    OutboundExecuteRequest,
    OutboundCancelRequest,
    WriteResponse,
)
from react_api.services.outbound_write_service import execute_outbound, cancel_outbound
from react_api.utils.db import get_engine

router = APIRouter(prefix="/api/outbound", tags=["outbound"])


@router.post("/execute", response_model=WriteResponse)
def outbound_execute(req: OutboundExecuteRequest) -> WriteResponse:
    try:
        with get_engine() as engine:
            result = execute_outbound(engine, req)
        return WriteResponse(**result)


    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).error("오류: %s", exc, exc_info=True)
        from fastapi import HTTPException as _HTTPEx
        raise _HTTPEx(500, f"처리 실패: {exc}")

@router.put("/cancel", response_model=WriteResponse)
def outbound_cancel(req: OutboundCancelRequest) -> WriteResponse:
    try:
        with get_engine() as engine:
            result = cancel_outbound(engine, req)
        return WriteResponse(**result)

    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).error("오류: %s", exc, exc_info=True)
        from fastapi import HTTPException as _HTTPEx
        raise _HTTPEx(500, f"처리 실패: {exc}")
