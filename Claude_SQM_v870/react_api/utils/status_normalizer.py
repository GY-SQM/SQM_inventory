# -*- coding: utf-8 -*-
"""SOLD -> OUTBOUND 표시 정규화 단일 유틸리티."""
from typing import Optional


def normalize_display_status(raw_status: Optional[str]) -> str:
    """DB raw status를 UI 표시용으로 정규화. SOLD → OUTBOUND."""
    status = (raw_status or "").strip().upper()
    if status == "SOLD":
        return "OUTBOUND"
    return status or "UNKNOWN"
