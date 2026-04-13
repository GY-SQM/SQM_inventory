# -*- coding: utf-8 -*-
from typing import List, Optional
from pydantic import BaseModel, Field


class InventoryRow(BaseModel):
    tonbag_id: int
    lot_no: str
    tonbag_uid: str = ""
    tonbag_no: str = ""
    product_name: str = ""
    sap_no: str = ""
    bl_no: str = ""
    status: str = ""
    location: str = ""
    weight_kg: float = 0.0
    weight_mt: float = 0.0
    is_sample: int = 0
    inbound_date: Optional[str] = None
    picked_date: Optional[str] = None
    outbound_date: Optional[str] = None
    # tkinter 동일 필드 추가
    container_no: str = ""
    net_weight: float = 0.0
    current_weight: float = 0.0
    initial_weight: float = 0.0
    mxbg_pallet: int = 0
    salar_invoice_no: str = ""
    ship_date: Optional[str] = None
    arrival_date: Optional[str] = None
    con_return: Optional[str] = None
    free_time: int = 0
    warehouse: str = ""
    customs: str = ""
    picked_weight: float = 0.0


class InventorySearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    rows: List[InventoryRow]
    generated_at: str


class InventoryFilterOptionsResponse(BaseModel):
    statuses: List[str]
    products: List[str]
    locations: List[str]
    generated_at: str


class LotStatusItem(BaseModel):
    status: str
    bag_count: int
    weight_kg: float
    weight_mt: float


class LotTonbagRow(BaseModel):
    tonbag_id: int
    tonbag_uid: str = ""
    tonbag_no: str = ""
    sub_lt: Optional[int] = None
    status: str = ""
    location: str = ""
    weight_kg: float = 0.0
    weight_mt: float = 0.0
    is_sample: int = 0
    picked_date: Optional[str] = None
    outbound_date: Optional[str] = None


class LotDetailResponse(BaseModel):
    lot_no: str
    product_name: str = ""
    sap_no: str = ""
    bl_no: str = ""
    inventory_status: str = ""
    tonbag_count: int = 0
    container_no: str = ""
    ship_date: Optional[str] = None
    arrival_date: Optional[str] = None
    con_return: Optional[str] = None
    free_time: int = 0
    warehouse: str = ""
    net_weight: float = 0.0
    current_weight: float = 0.0
    initial_weight: float = 0.0
    status_summary: List[LotStatusItem] = Field(default_factory=list)
    tonbags: List[LotTonbagRow] = Field(default_factory=list)
    generated_at: str
