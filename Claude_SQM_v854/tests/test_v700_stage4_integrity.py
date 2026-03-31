# -*- coding: utf-8 -*-
"""
SQM v7.0.0 — Stage4 무결성 엔진 테스트 (20개)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine_modules.inventory_validator import (
    check_rack_capacity, check_warehouse_capacity,
    check_system_capacity, validate_location_code,
    RACK_CAPACITY, WAREHOUSE_CAPACITY, SYSTEM_CAPACITY
)
from engine_modules.lot_balance_checker import check_lot_weight_balance


class TestStage4Constants:

    def test_T401_rack_capacity_is_20(self):
        assert RACK_CAPACITY == 20

    def test_T402_warehouse_A_capacity_is_3500(self):
        assert WAREHOUSE_CAPACITY.get('A') == 3500

    def test_T403_system_capacity_is_7000(self):
        assert SYSTEM_CAPACITY == 7000

    def test_T403b_warehouse_B_capacity_is_3500(self):
        assert WAREHOUSE_CAPACITY.get('B') == 3500


class TestRackCapacity:

    def test_T404_zero_count_ok(self):
        assert check_rack_capacity(0).ok is True

    def test_T405_half_full_ok(self):
        assert check_rack_capacity(10).ok is True

    def test_T406_exactly_20_ok(self):
        assert check_rack_capacity(20).ok is True

    def test_T407_21_exceeds_capacity(self):
        assert check_rack_capacity(21).ok is False

    def test_T408_incoming_pushes_over_limit(self):
        assert check_rack_capacity(18, incoming_count=5).ok is False

    def test_T409_incoming_stays_within_limit(self):
        assert check_rack_capacity(15, incoming_count=5).ok is True

    def test_T410_result_has_message(self):
        r = check_rack_capacity(25)
        assert r.message and len(r.message) > 0


class TestWarehouseCapacity:

    def test_T411_warehouse_A_within_limit(self):
        assert check_warehouse_capacity('A', 3000).ok is True

    def test_T412_warehouse_A_exactly_3500_ok(self):
        assert check_warehouse_capacity('A', 3500).ok is True

    def test_T413_warehouse_A_over_3500_fails(self):
        assert check_warehouse_capacity('A', 3501).ok is False

    def test_T414_warehouse_B_within_limit(self):
        assert check_warehouse_capacity('B', 3500).ok is True

    def test_T415_warehouse_B_over_limit(self):
        assert check_warehouse_capacity('B', 3501).ok is False

    def test_T416_system_total_within_7000(self):
        assert check_system_capacity(7000).ok is True

    def test_T417_system_total_over_7000_fails(self):
        assert check_system_capacity(7001).ok is False


class TestLocationCode:

    def test_T418_valid_format_A_03_05_02(self):
        assert validate_location_code('A-03-05-02').ok is True

    def test_T419_valid_format_B_01_01_01(self):
        assert validate_location_code('B-01-01-01').ok is True

    def test_T420_invalid_no_hyphens(self):
        assert validate_location_code('A030502').ok is False

    def test_T421_result_has_code_field(self):
        r = validate_location_code('A-03-05-02')
        assert hasattr(r, 'code')

    def test_T422_empty_location_invalid(self):
        assert validate_location_code('').ok is False


class TestLotBalanceChecker:

    def test_T423_balanced_within_tolerance(self):
        # tolerance=0.5kg: diff=0.5 → ok
        r = check_lot_weight_balance('LOT001', 10001.0, 10000.5)
        assert r.ok is True

    def test_T424_over_tolerance_fails(self):
        # diff=1.0 > tolerance=0.5
        r = check_lot_weight_balance('LOT001', 10001.0, 10000.0)
        assert r.ok is False
