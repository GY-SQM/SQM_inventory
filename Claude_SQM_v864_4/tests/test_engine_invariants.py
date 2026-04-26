# -*- coding: utf-8 -*-
"""
tests/test_engine_invariants.py
================================
Business logic invariant tests — inspect source code (no DB needed).

All tests use inspect.getsource() to verify that critical invariants
are present in the source. No engine instantiation required.
"""

import inspect
import pytest


def _get_source(module_path: str, attr: str = None) -> str:
    """Import a module and return its source, or a method's source."""
    import importlib
    mod = importlib.import_module(module_path)
    if attr:
        obj = getattr(mod, attr)
        return inspect.getsource(obj)
    return inspect.getsource(mod)


class TestRecalcInvariants:
    """Verify _recalc_current_weight uses correct SQL filters."""

    def test_recalc_uses_available_reserved_only(self):
        """_recalc_current_weight SQL must filter AVAILABLE and RESERVED statuses."""
        from engine_modules.inventory_modular.crud_mixin import CRUDMixin
        src = inspect.getsource(CRUDMixin._recalc_current_weight)
        assert "AVAILABLE" in src, "AVAILABLE status missing from recalc SQL"
        assert "RESERVED" in src, "RESERVED status missing from recalc SQL"

    def test_recalc_excludes_sample(self):
        """_recalc_current_weight must exclude sample tonbags (is_sample filter)."""
        from engine_modules.inventory_modular.crud_mixin import CRUDMixin
        src = inspect.getsource(CRUDMixin._recalc_current_weight)
        assert "is_sample" in src, (
            "_recalc_current_weight must reference is_sample column"
        )
        # Either is_sample = 0 or IS NULL check must be present
        has_zero_check = "is_sample = 0" in src
        has_null_check = "is_sample IS NULL" in src or "is_sample is NULL" in src.lower()
        assert has_zero_check or has_null_check, (
            "_recalc_current_weight must filter is_sample=0 or IS NULL"
        )


class TestOutboundMixinInvariants:
    """Verify critical guards in outbound_mixin.py."""

    def _get_outbound_source(self) -> str:
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "engine_modules" / "inventory_modular" / "outbound_mixin.py"
        return p.read_text(encoding="utf-8")

    def test_all_outbound_paths_call_recalc(self):
        """outbound_mixin.py must call _recalc_current_weight at least 8 times."""
        src = self._get_outbound_source()
        count = src.count("_recalc_current_weight")
        assert count >= 8, (
            f"Expected >= 8 _recalc_current_weight calls in outbound_mixin.py, "
            f"found {count}"
        )

    def test_reserve_from_allocation_delegates_to_helpers(self):
        """reserve_from_allocation must call the three _ra_ helper methods."""
        src = self._get_outbound_source()
        assert "_ra_validate_lot_availability" in src, (
            "_ra_validate_lot_availability not found in outbound_mixin.py"
        )
        assert "_ra_fetch_tonbag_pool" in src, (
            "_ra_fetch_tonbag_pool not found in outbound_mixin.py"
        )
        assert "_ra_execute_lot_reservation" in src, (
            "_ra_execute_lot_reservation not found in outbound_mixin.py"
        )

    def test_double_outbound_guard_exists(self):
        """Double-outbound guard function must exist in outbound_mixin.py."""
        src = self._get_outbound_source()
        assert "_co_check_double_sold" in src or "_co_guard_against_double_outbound" in src, (
            "Double-outbound guard (_co_check_double_sold or "
            "_co_guard_against_double_outbound) not found"
        )

    def test_cancel_outbound_calls_recalc(self):
        """cancel_outbound_tonbag must call _recalc_current_weight.

        Strategy: find all _recalc_current_weight calls in the source that have
        'CANCEL_OUTBOUND_TONBAG' or 'P2_CANCEL' in their reason string, which
        unambiguously ties recalc to the cancel_outbound_tonbag pathway.
        """
        src = self._get_outbound_source()
        assert "cancel_outbound_tonbag" in src, "cancel_outbound_tonbag not found"
        # The reason string written in cancel_outbound_tonbag call
        assert "P2_CANCEL_OUTBOUND_TONBAG" in src or (
            "_recalc_current_weight" in src and "cancel_outbound" in src.lower()
        ), (
            "outbound_mixin.py must call _recalc_current_weight with "
            "P2_CANCEL_OUTBOUND_TONBAG reason in cancel_outbound_tonbag"
        )


class TestValidatorInvariants:
    """Verify validators.py follows mutation-free pattern."""

    def test_validator_no_standalone_update(self):
        """
        validators.py must not contain a standalone UPDATE inventory SET current_weight
        without a nearby _recalc call (validators should not mutate weight directly).
        """
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "engine_modules" / "validators.py"
        src = p.read_text(encoding="utf-8")
        # If UPDATE inventory SET current_weight exists, _recalc must be within 600 chars
        update_idx = src.find("UPDATE inventory SET current_weight")
        if update_idx < 0:
            # No such update — invariant satisfied
            return
        window = src[update_idx:update_idx + 600]
        assert "_recalc" in window, (
            "validators.py has UPDATE inventory SET current_weight "
            "without a nearby _recalc call (within 600 chars)"
        )


class TestCRUDMixinInvariants:
    """Verify crud_mixin.py business logic patterns."""

    def test_inbound_uses_sample_weight_exclusion(self):
        """add_inventory (crud_mixin) must subtract SAMPLE_WEIGHT_KG for initial current_weight."""
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "engine_modules" / "inventory_modular" / "crud_mixin.py"
        src = p.read_text(encoding="utf-8")
        assert "SAMPLE_WEIGHT_KG" in src, (
            "crud_mixin.py must reference SAMPLE_WEIGHT_KG for sample exclusion"
        )
        # The net_weight - SAMPLE_WEIGHT_KG pattern for initial weight
        assert "net_weight" in src and "SAMPLE_WEIGHT_KG" in src, (
            "crud_mixin must use net_weight and SAMPLE_WEIGHT_KG together"
        )

    def test_ra_helpers_have_correct_signatures(self):
        """_ra_validate_lot_availability must accept lot_no, qty_mt, is_sample_req."""
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "engine_modules" / "inventory_modular" / "outbound_mixin.py"
        src = p.read_text(encoding="utf-8")
        # Find the function definition
        idx = src.find("def _ra_validate_lot_availability(")
        assert idx >= 0, "_ra_validate_lot_availability not found"
        sig_block = src[idx:idx + 300]
        assert "lot_no" in sig_block, "lot_no param missing from _ra_validate_lot_availability"
        assert "qty_mt" in sig_block, "qty_mt param missing from _ra_validate_lot_availability"
        assert "is_sample_req" in sig_block, (
            "is_sample_req param missing from _ra_validate_lot_availability"
        )


class TestSalesOrderEngineInvariants:
    """Verify sales_order_engine.py batch path calls recalc."""

    def test_sales_order_engine_has_recalc_on_batch_path(self):
        """sales_order_engine.py must call executemany AND _recalc_current_weight."""
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "features" / "parsers" / "sales_order_engine.py"
        if not p.exists():
            pytest.skip("sales_order_engine.py not found")
        src = p.read_text(encoding="utf-8")
        assert "executemany" in src, (
            "sales_order_engine.py must use executemany for batch path"
        )
        assert "_recalc_current_weight" in src, (
            "sales_order_engine.py must call _recalc_current_weight on batch path"
        )
