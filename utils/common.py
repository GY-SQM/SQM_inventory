# -*- coding: utf-8 -*-
"""
SQM v5.5.5 — 공용 유틸리티 (Single Source of Truth)
=====================================================
safe_float, safe_str, normalize_column_name 등
모든 모듈에서 공통으로 사용하는 함수를 한 곳에 모음.

사용법:
    from utils.common import safe_float, safe_str, normalize_column_name
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


def safe_float(value: Any, default: float = 0.0) -> float:
    """안전한 실수 변환 (쉼표, 공백, 하이픈 처리)"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace(',', '').replace(' ', '').strip()
        if not cleaned or cleaned == '-':
            return default
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = '') -> str:
    """안전한 문자열 변환"""
    if value is None:
        return default
    try:
        result = str(value).strip()
        return result if result else default
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """안전한 정수 변환"""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        if isinstance(value, float):
            return int(value)
        cleaned = str(value).replace(',', '').replace(' ', '').strip()
        if not cleaned or cleaned == '-':
            return default
        if '.' in cleaned:
            return int(float(cleaned))
        return int(cleaned)
    except (ValueError, TypeError):
        return default


def normalize_column_name(name: str) -> str:
    """컬럼명 정규화: 소문자, 공백→언더스코어, 특수문자 제거"""
    if not name:
        return ''
    result = str(name).strip().lower()
    result = result.replace(' ', '_').replace('-', '_')
    result = re.sub(r'[^a-z0-9_]', '', result)
    result = re.sub(r'_+', '_', result).strip('_')
    return result
