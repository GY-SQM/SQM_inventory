# -*- coding: utf-8 -*-
"""
features.parsers.review_models — 사전검수 데이터 모델 (P2 탈결합)
================================================================
사전검수 브리지(preview_review_bridge)와 GUI 다이얼로그(PreParseReviewDialog)가
공유하는 순수 dataclass. Tk/GUI 비의존이라 중립 위치에 둔다.
(이전엔 GUI 다이얼로그 파일 안에 정의돼 있어 브리지가 GUI에 결합됐다.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DOC_TYPES = ("BL", "PL", "FA", "DO", "OTHER", "EXCLUDE")
FIELD_TYPES = ("string", "int", "float", "date", "enum", "unknown")


@dataclass
class PreviewField:
    key: str
    label: str
    value: Any = ""
    field_type: str = "string"
    required: bool = False
    allowed_values: list[str] = field(default_factory=list)
    status: str = "대기"
    message: str = ""


@dataclass
class ReviewItem:
    file_path: str
    file_name: str
    auto_doc_type: str = "OTHER"
    user_doc_type: str = "OTHER"
    detect_reason: str = ""
    preview_fields: list[PreviewField] = field(default_factory=list)
    preview_status: str = "대기"
    excluded: bool = False
    ai_instruction: str = ""
    ai_last_suggestion: dict[str, Any] | None = None
