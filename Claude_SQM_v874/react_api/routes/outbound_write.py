# -*- coding: utf-8 -*-
"""출고 처리 + 출고 취소 + 출고 확정 엔드포인트.
★ P2-D: /confirm 엔드포인트 추가 (MobileDashboard 연결)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

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
        raise HTTPException(500, f"처리 실패: {exc}")


@router.put("/cancel", response_model=WriteResponse)
def outbound_cancel(req: OutboundCancelRequest) -> WriteResponse:
    try:
        with get_engine() as engine:
            result = cancel_outbound(engine, req)
        return WriteResponse(**result)
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).error("오류: %s", exc, exc_info=True)
        raise HTTPException(500, f"처리 실패: {exc}")


# ── ★ 신규: 출고 확정 (PICKED → OUTBOUND) ────────────────────
class OutboundConfirmRequest(BaseModel):
    lot_no: str
    force_all: bool = False


@router.post("/confirm", response_model=WriteResponse)
def outbound_confirm(req: OutboundConfirmRequest) -> WriteResponse:
    """
    POST /api/outbound/confirm
    PICKED → OUTBOUND 확정
    MobileDashboard.jsx 의 "확정" 버튼과 연결
    """
    try:
        with get_engine() as engine:
            from features.services.outbound_service import OutboundService
            svc    = OutboundService(engine.db)
            result = svc.confirm_outbound(
                lot_no=req.lot_no,
                force_all=req.force_all
            )
        return WriteResponse(
            success=result["success"],
            message=(
                f"출고 확정 완료: {result['confirmed']}톤백"
                if result["success"]
                else "; ".join(result["errors"][:2])
            ),
            data={
                "confirmed": result["confirmed"],
                "errors":    result.get("errors", []),
                "warnings":  result.get("warnings", []),
            }
        )
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).error("출고확정 오류: %s", exc, exc_info=True)
        raise HTTPException(500, f"출고 확정 실패: {exc}")
