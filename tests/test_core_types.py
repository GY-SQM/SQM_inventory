"""
P5-8: core.types 단위 테스트
============================
safe_int, safe_float, safe_str, normalize_column_name
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.types import normalize_column_name, safe_float, safe_int, safe_str


class TestSafeInt:
    def test_valid_int(self):
        assert safe_int(42) == 42
        assert safe_int("42") == 42
        assert safe_int(42.9) == 42

    def test_none_default(self):
        assert safe_int(None) == 0
        assert safe_int(None, default=99) == 99

    def test_invalid_returns_default(self):
        assert safe_int("") == 0
        assert safe_int("abc") == 0
        assert safe_int("-", default=-1) == -1

    def test_comma_stripped(self):
        assert safe_int("1,234") == 1234


class TestSafeFloat:
    def test_valid_float(self):
        assert safe_float(1.5) == 1.5
        assert safe_float("1.5") == 1.5
        assert safe_float("1,234.5") == 1234.5

    def test_none_default(self):
        assert safe_float(None) == 0.0
        assert safe_float(None, default=1.0) == 1.0

    def test_invalid_returns_default(self):
        assert safe_float("") == 0.0
        assert safe_float("x") == 0.0


class TestSafeStr:
    def test_valid_str(self):
        assert safe_str("hello") == "hello"
        assert safe_str(42) == "42"
        assert safe_str("  a  ") == "a"

    def test_none_default(self):
        assert safe_str(None) == ""
        assert safe_str(None, default="x") == "x"


class TestNormalizeColumnName:
    def test_lowercase(self):
        assert normalize_column_name("Weight") == "weight"

    def test_spaces_to_underscore(self):
        assert normalize_column_name("net weight") == "net_weight"

    def test_special_stripped(self):
        assert "lot" in normalize_column_name("LOT_NO")
        # hyphen → underscore, then non-alnum 제거
        assert normalize_column_name("a-b") == "a_b"
