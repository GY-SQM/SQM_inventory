# -*- coding: utf-8 -*-
from typing import List
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


class DashboardSummaryResponse(BaseModel):
    items: List[DashboardSummaryItem]
    totals: DashboardSummaryTotals
    generated_at: str


class ProductSummaryRow(BaseModel):
    product_name: str
    lot_count: int
    tonbag_count: int
    available_kg: float
    reserved_kg: float
    picked_kg: float
    outbound_kg: float
    available_mt: float
    reserved_mt: float
    picked_mt: float
    outbound_mt: float
    total_mt: float


class ProductSummaryResponse(BaseModel):
    rows: List[ProductSummaryRow]
    generated_at: str


class LocationSummaryRow(BaseModel):
    location: str
    bag_count: int
    weight_kg: float
    weight_mt: float


class LocationSummaryResponse(BaseModel):
    rows: List[LocationSummaryRow]
    generated_at: str
