# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool
    service: str
    generated_at: str


class StandardResponse(BaseModel):
    """범용 API 응답 스키마 — 조회/쓰기 공통."""
    success: bool = True
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    generated_at: Optional[str] = None


class PaginatedResponse(BaseModel):
    """페이지 조회 응답 스키마."""
    total: int = 0
    page: int = 1
    page_size: int = 50
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: str = ""
