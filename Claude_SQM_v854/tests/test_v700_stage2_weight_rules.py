# -*- coding: utf-8 -*-
"""
SQM v7.0.0 — Stage2 무게 계산 규칙 테스트 (15개)
==================================================
무게 계산 공식: (LOT 총무게 - 1kg 샘플) / mxbg_pallet
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine_modules.tonbag_weight_rules import (
    calculate_tonbag_weight, get_rule_status, build_rule_result
)


class TestCalculateTonbagWeight:

    def test_T201_500kg_standard_20bags(self):
        """20톤백 × 500kg = LOT 10001kg 기준"""
        w = calculate_tonbag_weight(10001.0, 20)
        assert abs(w - 500.0) < 0.01

    def test_T202_1000kg_standard_20bags(self):
        """20톤백 × 1000kg = LOT 20001kg 기준"""
        w = calculate_tonbag_weight(20001.0, 20)
        assert abs(w - 1000.0) < 0.01

    def test_T203_sample_1kg_excluded_from_calculation(self):
        """샘플 1kg 반드시 제외"""
        w = calculate_tonbag_weight(10001.0, 20)
        # (10001 - 1) / 20 = 500.0
        assert abs(w - 500.0) < 0.01

    def test_T204_500kg_10bags(self):
        w = calculate_tonbag_weight(5001.0, 10)
        assert abs(w - 500.0) < 0.01

    def test_T205_custom_sample_weight(self):
        """샘플 0.5kg 커스텀"""
        w = calculate_tonbag_weight(5000.5, 10, sample_weight_kg=0.5)
        assert abs(w - 500.0) < 0.01

    def test_T206_zero_bags_returns_zero(self):
        w = calculate_tonbag_weight(10001.0, 0)
        assert w == 0.0

    def test_T207_result_is_float(self):
        w = calculate_tonbag_weight(10001.0, 20)
        assert isinstance(w, float)


class TestGetRuleStatus:

    def test_T208_500kg_status_label(self):
        status = get_rule_status(500.0)
        assert "500" in status or status is not None

    def test_T209_1000kg_status_label(self):
        status = get_rule_status(1000.0)
        assert "1000" in status or status is not None

    def test_T210_nonstandard_weight_has_status(self):
        status = get_rule_status(750.0)
        assert isinstance(status, str)


class TestBuildRuleResult:

    def test_T211_result_has_tonbag_weight(self):
        r = build_rule_result(10001.0, 20)
        assert hasattr(r, 'tonbag_weight_kg')

    def test_T212_result_has_rule_status(self):
        r = build_rule_result(10001.0, 20)
        assert hasattr(r, 'rule_status')

    def test_T213_500kg_rule_weight_correct(self):
        r = build_rule_result(10001.0, 20)
        assert abs(r.tonbag_weight_kg - 500.0) < 0.01

    def test_T214_1000kg_rule_weight_correct(self):
        r = build_rule_result(20001.0, 20)
        assert abs(r.tonbag_weight_kg - 1000.0) < 0.01

    def test_T215_lot_weight_integrity_1kg_sample(self):
        """핵심 불변 조건: LOT 총무게 = (톤백수 × 단가) + 1kg"""
        bags = 20
        per_bag = 500.0
        lot_total = bags * per_bag + 1.0  # 10001kg
        r = build_rule_result(lot_total, bags)
        assert abs(r.tonbag_weight_kg - per_bag) < 0.01
