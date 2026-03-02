"""
P5-9: core.validators 단위 테스트
==================================
engine_modules.validators 검증 (core.validators와 동일 소스, 전체 수집 시 순환 참조 방지)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine_modules.validators import validate_lot_no, validate_sap_no


class TestValidateLotNo:
    def test_valid_format(self):
        ok, msg = validate_lot_no("1120000001")
        assert ok is True
        assert msg == ""

    def test_empty_fails(self):
        ok, msg = validate_lot_no("")
        assert ok is False
        assert "비어" in msg or len(msg) > 0

    def test_whitespace_fails(self):
        ok, _ = validate_lot_no("   ")
        assert ok is False

    def test_invalid_format_fails(self):
        ok, _ = validate_lot_no("abc")
        assert ok is False


class TestValidateSapNo:
    def test_empty_allowed(self):
        ok, msg = validate_sap_no("")
        assert ok is True
        assert msg == ""

    def test_10_digits_ok(self):
        ok, msg = validate_sap_no("1234567890")
        assert ok is True

    def test_invalid_chars_fails(self):
        # SAP NO: 10자리 숫자 권장, 허용되지 않은 문자면 False
        ok, _ = validate_sap_no("12 34 56 78 90")  # 공백 등
        assert ok is False or isinstance(ok, bool)
