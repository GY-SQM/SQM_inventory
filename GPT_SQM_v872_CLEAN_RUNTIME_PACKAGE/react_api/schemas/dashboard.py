# -*- coding: utf-8 -*-
"""
dashboard schemas — con_return_critical 필드 추가
배치: react_api/schemas/dashboard.py (기존 덮어쓰기)
"""
from typing import List, Optional
from pydantic import BaseModel


class DashboardSummaryItem(BaseModel):
    status: str
    bag_count: int
    weight_kg: float
    weight_mt: float
    sample_bag_count: int = 0


class DashboardSummaryTotals(BaseModel):
    bag_count: int
    weight_kg: float
    weight_mt: float
    sample_bag_count: int = 0


# ★ Q3 신규: Con Return 임박 항목
class ConReturnAlert(BaseModel):
    lot_no:       str
    con_return:   str
    days_left:    int
    container_no: str = ""
    warehouse:    str = ""
    is_critical:  bool = False   # True = 3일 이내


# ★ Q3 신규: DashboardSummaryResponse에 con_return 필드 추가
class DashboardSummaryResponse(BaseModel):
    items:      List[DashboardSummaryItem]
    totals:     DashboardSummaryTotals
    generated_at: str
    # ★ 추가 필드
    con_return_critical_count: int = 0    # 3일 이내
    con_return_warning_count:  int = 0    # 7일 이내
    con_return_alerts:         List[ConReturnAlert] = []


class ProductSummaryRow(BaseModel):
    product_name: str
    lot_count:    int
    tonbag_count: int
    available_kg: float
    reserved_kg:  float
    picked_kg:    float
    outbound_kg:  float
    available_mt: float
    reserved_mt:  float
    picked_mt:    float
    outbound_mt:  float
    total_mt:     float


class ProductSummaryResponse(BaseModel):
    rows:         List[ProductSummaryRow]
    generated_at: str


class LocationSummaryRow(BaseModel):
    location:   str
    bag_count:  int
    weight_kg:  float
    weight_mt:  float


class LocationSummaryResponse(BaseModel):
    rows:         List[LocationSummaryRow]
    generated_at: str
