# -*- coding: utf-8 -*-
"""PUT /api/location/update — 톤백 위치 변경 엔드포인트."""
from fastapi import APIRouter

from react_api.schemas.write_models import LocationUpdateRequest, WriteResponse
from react_api.services.outbound_write_service import update_location
from react_api.utils.db import get_db

router = APIRouter(prefix="/api/location", tags=["location"])


@router.put("/update", response_model=WriteResponse)
def location_update(req: LocationUpdateRequest) -> WriteResponse:
    with get_db() as db:
        result = update_location(db, req)
    return WriteResponse(**result)
