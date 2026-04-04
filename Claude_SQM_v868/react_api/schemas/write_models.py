# -*- coding: utf-8 -*-
"""쓰기 API 요청/응답 모델."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─── 공통 응답 ───
class WriteResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)


# ─── POST /api/inbound/create ───
class TonbagInput(BaseModel):
    weight: float = Field(..., gt=0, description="톤백 중량(kg)")
    is_sample: bool = False


class InboundCreateRequest(BaseModel):
    lot_no: str = Field(..., min_length=1, max_length=30)
    product_name: str = Field(..., min_length=1)
    sap_no: Optional[str] = ""
    bl_no: str = Field(..., min_length=1)
    total_weight_kg: float = Field(..., gt=0)
    bag_count: int = Field(..., gt=0)
    location: Optional[str] = ""
    container_no: Optional[str] = ""
    invoice_no: Optional[str] = ""
    ship_date: Optional[str] = ""
    arrival_date: Optional[str] = ""
    warehouse: Optional[str] = ""
    source_type: str = "WEB"
    source_file: Optional[str] = ""
    tonbags: Optional[List[TonbagInput]] = None


# ─── POST /api/outbound/execute ───
class OutboundItem(BaseModel):
    lot_no: str
    sub_lt: int
    customer: Optional[str] = ""
    qty_kg: Optional[float] = None


class OutboundExecuteRequest(BaseModel):
    items: List[OutboundItem] = Field(..., min_length=1)
    customer: str = Field(..., min_length=1)
    sale_ref: Optional[str] = ""
    destination: Optional[str] = ""
    source: str = "WEB"
    stop_at_picked: bool = False


# ─── PUT /api/outbound/cancel ───
class OutboundCancelRequest(BaseModel):
    lot_no: str
    sub_lt: int


# ─── PUT /api/location/update ───
class LocationUpdateRequest(BaseModel):
    lot_no: str
    sub_lt: int
    new_location: str = Field(..., min_length=1)


# ─── POST /api/files/upload ───
# 파일 업로드는 multipart/form-data로 처리 (UploadFile 사용)
