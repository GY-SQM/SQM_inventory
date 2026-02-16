# -*- coding: utf-8 -*-
"""
P5-10: core.formatters 단위 테스트
===================================
gui_app_modular.utils.formatters 검증 (core.formatters와 동일 소스, 전체 수집 시 순환 참조 방지)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from gui_app_modular.utils.formatters import (
    format_number,
    format_weight,
    format_weight_kg,
    format_weight_mt,
    find_column,
)


class TestFormatNumber:
    def test_basic(self):
        assert "1" in format_number(1.0)
        assert "2" in format_number(2.5, decimals=1)

    def test_comma(self):
        out = format_number(1234.5, use_comma=True)
        assert "1" in out and "234" in out or "1,234" in out

    def test_invalid_returns_str(self):
        assert isinstance(format_number("x"), str)


class TestFormatWeight:
    def test_kg(self):
        out = format_weight(500, unit="kg")
        assert "500" in out and "kg" in out

    def test_mt(self):
        out = format_weight(1000, unit="MT")
        assert "1" in out and "MT" in out

    def test_auto_large(self):
        out = format_weight(2000, unit="auto")
        assert "MT" in out or "2" in out


class TestFormatWeightKg:
    def test_integer_kg(self):
        assert "500" in format_weight_kg(500)
        assert "kg" in format_weight_kg(500)


class TestFormatWeightMt:
    def test_conversion(self):
        out = format_weight_mt(1000)
        assert "1" in out and "MT" in out


class TestFindColumn:
    def test_found(self):
        cols = ["Lot No", "Weight", "Status"]
        assert find_column(cols, ["weight", "Weight"], None) in ("Weight", "weight")

    def test_not_found_returns_default(self):
        cols = ["A", "B"]
        assert find_column(cols, ["C"], "X") == "X"

    def test_case_insensitive(self):
        cols = ["LOT_NO"]
        assert find_column(cols, ["lot_no"], None) == "LOT_NO"
