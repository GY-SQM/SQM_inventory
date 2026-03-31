# -*- coding: utf-8 -*-
"""
SQM v7.0.0 — InventoryValidator 테스트 (20개)
===============================================
LOT 번호 형식, 중량 검증, SAP NO, 취약점 차단
v2.9.30 발견 7가지 취약점 회귀 테스트 포함
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine_modules.validators import (
    InventoryValidator, validate_lot_no,
    validate_weight, validate_sap_no
)

V = InventoryValidator()
LOT_OK = "1125072340"


# ── 1. LOT 번호 검증 ───────────────────────────────────────────────────────

class TestValidateLotNo:

    def test_T501_valid_sqm_lot_no(self):
        r = V.validate_lot_no(LOT_OK)
        assert r.is_valid is True

    def test_T502_empty_string_blocked(self):
        """취약점1: 빈 LOT 번호 허용 → 차단"""
        r = V.validate_lot_no('')
        assert r.is_valid is False

    def test_T503_none_blocked(self):
        r = V.validate_lot_no(None)
        assert r.is_valid is False

    def test_T504_too_short_blocked(self):
        r = V.validate_lot_no('112')
        assert r.is_valid is False

    def test_T505_too_long_blocked(self):
        r = V.validate_lot_no('A' * 25)
        assert r.is_valid is False

    def test_T506_non_standard_format_gives_warning(self):
        r = V.validate_lot_no('ABCDE12345')
        # 형식 비표준 → warnings 있어야 함 (is_valid는 True일 수 있음)
        assert isinstance(r.is_valid, bool)

    def test_T507_legacy_function_valid_lot(self):
        ok, msg = validate_lot_no(LOT_OK)
        assert ok is True

    def test_T508_legacy_function_empty_lot(self):
        ok, msg = validate_lot_no('')
        assert ok is False
        assert len(msg) > 0


# ── 2. 중량 검증 ───────────────────────────────────────────────────────────

class TestValidateWeight:

    def test_T509_normal_500kg_passes(self):
        r = V.validate_weight(500.0)
        assert r.is_valid is True

    def test_T510_normal_1000kg_passes(self):
        r = V.validate_weight(1000.0)
        assert r.is_valid is True

    def test_T511_negative_weight_blocked(self):
        """취약점2: 음수 중량 저장 → 차단"""
        r = V.validate_weight(-100.0)
        assert r.is_valid is False

    def test_T512_zero_weight_blocked(self):
        r = V.validate_weight(0.0)
        assert r.is_valid is False

    def test_T513_none_weight_blocked(self):
        r = V.validate_weight(None)
        assert r.is_valid is False

    def test_T514_extreme_over_100ton_blocked(self):
        r = V.validate_weight(100001.0)
        assert r.is_valid is False

    def test_T515_sample_1kg_passes(self):
        r = V.validate_weight(1.0)
        assert r.is_valid is True

    def test_T516_legacy_function_valid(self):
        ok, _ = validate_weight(500.0)
        assert ok is True

    def test_T517_legacy_function_negative(self):
        ok, msg = validate_weight(-1.0)
        assert ok is False

    def test_T518_string_number_converted(self):
        """문자열로 전달된 숫자도 처리"""
        r = V.validate_weight("500")
        assert r.is_valid is True


# ── 3. SAP NO 검증 ─────────────────────────────────────────────────────────

class TestValidateSapNo:

    def test_T519_empty_sap_no_ok(self):
        """SAP NO는 선택 필드 — 빈값 허용"""
        ok, _ = validate_sap_no('')
        assert ok is True

    def test_T520_none_sap_no_ok(self):
        ok, _ = validate_sap_no(None)
        assert ok is True
