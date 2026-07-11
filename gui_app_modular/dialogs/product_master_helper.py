# -*- coding: utf-8 -*-
"""
SQM — 제품 마스터 헬퍼 (P1 탈결합: core.product_master 로 이전됨)
================================================================
구현은 core.product_master 로 이전됐다. 이 모듈은 레거시 GUI 호환을 위해
core.product_master 를 역-re-export 한다. (신규 코드는 core.product_master 직접 사용)
"""

from core.product_master import (  # noqa: F401
    auto_detect_product_code,
    get_product_choices,
    get_product_code_map,
    get_product_inventory_report,
    parse_product_choice,
)

__all__ = [
    'get_product_choices',
    'parse_product_choice',
    'get_product_code_map',
    'auto_detect_product_code',
    'get_product_inventory_report',
]
