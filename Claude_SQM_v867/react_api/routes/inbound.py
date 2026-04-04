# -*- coding: utf-8 -*-
"""POST /api/inbound/create — 입고 처리 엔드포인트."""
from fastapi import APIRouter

from react_api.schemas.write_models import InboundCreateRequest, WriteResponse
from react_api.services.inbound_write_service import create_inbound
from react_api.utils.db import get_db

router = APIRouter(prefix="/api/inbound", tags=["inbound"])


@router.post("/create", response_model=WriteResponse)
def inbound_create(req: InboundCreateRequest) -> WriteResponse:
    with get_db() as db:
        result = create_inbound(db, req)
    return WriteResponse(**result)
