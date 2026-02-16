# -*- coding: utf-8 -*-
"""
P5-11: core.constants 단위 테스트
=================================
engine_modules.constants 값 검증 (core.constants와 동일 소스, 전체 수집 시 순환 참조 방지)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from engine_modules.constants import (
    STATUS_AVAILABLE,
    STATUS_PICKED,
    STATUS_SOLD,
    STATUS_DEPLETED,
    DEFAULT_WAREHOUSE,
    SAMPLE_WEIGHT_KG,
    BL_PREFIXES,
    DATE_FORMAT,
)


class TestCoreConstants:
    def test_status_values(self):
        assert STATUS_AVAILABLE == "AVAILABLE"
        assert STATUS_PICKED == "PICKED"
        assert STATUS_SOLD == "SOLD"
        assert STATUS_DEPLETED == "DEPLETED"

    def test_warehouse(self):
        assert DEFAULT_WAREHOUSE == "광양"

    def test_sample_weight(self):
        assert SAMPLE_WEIGHT_KG == 1.0

    def test_bl_prefixes(self):
        assert "MAEU" in BL_PREFIXES
        assert isinstance(BL_PREFIXES, (tuple, list))

    def test_date_format(self):
        assert "%Y" in DATE_FORMAT
        assert "%m" in DATE_FORMAT
