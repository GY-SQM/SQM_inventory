# -*- coding: utf-8 -*-
"""allocation_lot_overview_mixin 헬퍼 단위 테스트 (v8.1.8)."""

from gui_app_modular.tabs.allocation_lot_overview_mixin import (
    _abbr_status,
    _alloc_ratio_pct,
    _compute_lot_state,
    _fmt_ns,
    _sample_cell,
)


def test_abbr_status_known():
    assert _abbr_status("AVAILABLE") == "AVAIL"
    assert _abbr_status("RESERVED") == "RSV"
    assert _abbr_status("PICKED") == "PICK"


def test_sample_cell_zero_one_many():
    assert _sample_cell(0, []) == "없음"
    assert _sample_cell(0, ["AVAILABLE"]) == "⚠ 불일치"
    assert _sample_cell(1, ["AVAILABLE"]) == "1·AVAIL"
    assert _sample_cell(2, ["AVAILABLE", "RESERVED"]) == "⚠ 2개?"


def test_fmt_ns():
    assert _fmt_ns(0, 0) == "—"
    assert _fmt_ns(3, 1500) == "3 (1.5MT)"


def test_compute_lot_state_full_rsv_plan_only():
    assert _compute_lot_state(0, 0, 0, 0, 0, 1.2) == "FULL RSV"


def test_compute_lot_state_available():
    assert _compute_lot_state(10, 10, 0, 0, 0, 0) == "AVAILABLE"


def test_compute_lot_state_partial_reserved():
    assert _compute_lot_state(10, 7, 3, 0, 0, 0) == "PARTIAL"


def test_alloc_ratio_pct_general_only():
    assert _alloc_ratio_pct(10000, 5000, 0, 0, 0) == 50
    assert _alloc_ratio_pct(10000, 0, 0, 0, 2.5) == 25
    assert _alloc_ratio_pct(0, 100, 0, 0, 0) == 0
    assert _alloc_ratio_pct(1000, 500, 500, 0, 0) == 100
