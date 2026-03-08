from engine_modules.inventory_validator import check_rack_capacity, check_warehouse_capacity, check_system_capacity, validate_location_code
from engine_modules.lot_balance_checker import check_lot_weight_balance


def test_rack_capacity_ok():
    assert check_rack_capacity(19, 1).ok is True


def test_rack_capacity_exceeded():
    assert check_rack_capacity(20, 1).ok is False


def test_location_code():
    assert validate_location_code('A-03-05-02').ok is True


def test_lot_balance():
    assert check_lot_weight_balance('LOT1', 5001.0, 5001.0).ok is True
