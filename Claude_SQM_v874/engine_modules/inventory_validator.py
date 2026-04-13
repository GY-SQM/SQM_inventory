# -*- coding: utf-8 -*-
"""Stage 4 inventory integrity helpers for SQM.

핵심 역할
- LOT / LOCATION 기본 무결성 검증

v8.7.1 P1-7: 미사용 capacity 함수 3건 제거
  (check_rack_capacity, check_warehouse_capacity, check_system_capacity)
  — codebase 전체 검색 결과 호출처 0건 확인 후 제거
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ValidationResult:
    ok: bool
    code: str
    message: str


def validate_location_code(location_code: str) -> ValidationResult:
    code = str(location_code or '').strip().upper()
    # A-03-05-02 형식
    import re
    if re.fullmatch(r'[A-Z]-\d{2}-\d{2}-\d{2}', code):
        return ValidationResult(True, 'LOCATION_CODE_OK', f'Location 형식 정상: {code}')
    return ValidationResult(False, 'ERROR_INVALID_LOCATION', f'Location 형식 오류: {code}')
