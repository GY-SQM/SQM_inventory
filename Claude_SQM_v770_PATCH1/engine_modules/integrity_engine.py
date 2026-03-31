# -*- coding: utf-8 -*-
"""Stage 4 Integrity Engine.

이 모듈은 기존 mixin을 대체하지 않고 보조 검증 엔진으로 추가된다.
호출처에서 필요 시 import 하여 사용한다.
"""
from __future__ import annotations
from typing import Any, Dict
from engine_modules.inventory_validator import (
    check_rack_capacity,
    check_system_capacity,
    check_warehouse_capacity,
    validate_location_code,
)
from engine_modules.lot_balance_checker import check_lot_weight_balance


def validate_integrity_snapshot(
    *,
    lot_no: str,
    expected_lot_weight: float,
    available_tonbag_weight: float,
    rack_count: int,
    rack_incoming: int,
    warehouse_code: str,
    warehouse_count: int,
    system_count: int,
    location_code: str,
) -> Dict[str, Any]:
    lot = check_lot_weight_balance(lot_no, expected_lot_weight, available_tonbag_weight)
    rack = check_rack_capacity(rack_count, rack_incoming)
    wh = check_warehouse_capacity(warehouse_code, warehouse_count)
    sysv = check_system_capacity(system_count)
    loc = validate_location_code(location_code)
    checks = [lot.ok, rack.ok, wh.ok, sysv.ok, loc.ok]
    return {
        'ok': all(checks),
        'lot': lot,
        'rack': rack,
        'warehouse': wh,
        'system': sysv,
        'location': loc,
    }
