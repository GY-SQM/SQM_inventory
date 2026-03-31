# -*- coding: utf-8 -*-
"""
P4 테스트: _require_lot_no() — None/빈값 거부, 유효값 반환
"""
import pytest
from engine_modules.inventory_modular.base import InventoryBaseMixin


class TestRequireLotNo:
    """_require_lot_no 메서드 검증"""

    def setup_method(self):
        self.mixin = InventoryBaseMixin()

    # --- 정상 케이스 ---
    def test_valid_lot_no(self):
        """정상 LOT 번호는 strip된 문자열을 반환"""
        result = self.mixin._require_lot_no("1120000001", "test")
        assert result == "1120000001"

    def test_valid_lot_no_with_spaces(self):
        """앞뒤 공백이 있으면 strip 후 반환"""
        result = self.mixin._require_lot_no("  1120000001  ", "test")
        assert result == "1120000001"

    def test_numeric_lot_no_cast(self):
        """숫자(int)도 문자열로 변환하여 반환"""
        result = self.mixin._require_lot_no(1120000001, "test")
        assert result == "1120000001"

    # --- 실패 케이스 ---
    @pytest.mark.edge
    def test_none_raises(self):
        """None → ValueError"""
        with pytest.raises(ValueError, match="None"):
            self.mixin._require_lot_no(None, "test_caller")

    @pytest.mark.edge
    def test_empty_string_raises(self):
        """빈 문자열 → ValueError"""
        with pytest.raises(ValueError, match="빈 문자열"):
            self.mixin._require_lot_no("", "test_caller")

    @pytest.mark.edge
    def test_whitespace_only_raises(self):
        """공백만 있는 문자열 → strip 후 빈 문자열이므로 ValueError"""
        with pytest.raises(ValueError, match="빈 문자열"):
            self.mixin._require_lot_no("   ", "test_caller")

    # --- caller 포함 ---
    def test_error_message_includes_caller(self):
        """에러 메시지에 caller 이름이 포함되는지 확인"""
        with pytest.raises(ValueError, match="my_function"):
            self.mixin._require_lot_no(None, "my_function")
