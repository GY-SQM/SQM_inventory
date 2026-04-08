# -*- coding: utf-8 -*-
"""PUT /api/location/update — 톤백 위치 변경 엔드포인트."""
from fastapi import APIRouter

from react_api.schemas.write_models import LocationUpdateRequest, WriteResponse
from react_api.services.outbound_write_service import update_location
from react_api.utils.db import get_engine

router = APIRouter(prefix="/api/location", tags=["location"])


@router.put("/update", response_model=WriteResponse)
def location_update(req: LocationUpdateRequest) -> WriteResponse:
    try:
        with get_engine() as engine:
            result = update_location(engine, req)
        return WriteResponse(**result)

    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).error("오류: %s", exc, exc_info=True)
        from fastapi import HTTPException as _HTTPEx
        raise _HTTPEx(500, f"처리 실패: {exc}")
