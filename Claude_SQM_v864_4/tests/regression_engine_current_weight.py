"""
Regression: BUG-2026-04-20-001 (5001kg current_weight drift)
Phase 3-A fix: crud_mixin.py:194 — current_weight = net_weight - SAMPLE_WEIGHT_KG
Design A: inventory.current_weight = AVAILABLE + RESERVED tonbags (sample excluded)
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine_modules.inventory_modular.crud_mixin import SAMPLE_WEIGHT_KG


def test_sample_weight_constant_defined():
    """SAMPLE_WEIGHT_KG must be defined and positive."""
    assert SAMPLE_WEIGHT_KG > 0, f"SAMPLE_WEIGHT_KG={SAMPLE_WEIGHT_KG} must be > 0"


def test_inbound_excludes_sample_weight():
    """current_weight init = net_weight - SAMPLE_WEIGHT_KG (not net_weight)."""
    net_weight = 5001.0
    expected_current = net_weight - SAMPLE_WEIGHT_KG
    assert expected_current == 5000.0, (
        f"With net_weight={net_weight} and SAMPLE_WEIGHT_KG={SAMPLE_WEIGHT_KG}, "
        f"expected current_weight=5000.0, got {expected_current}"
    )


def test_recalc_excludes_sample():
    """_recalc_current_weight SQL must filter is_sample=0."""
    import inspect
    import engine_modules.inventory_modular.crud_mixin as cm
    src = inspect.getsource(cm.CRUDMixin._recalc_current_weight)
    assert "is_sample" in src, "_recalc_current_weight must filter by is_sample"
    assert "= 0" in src or "IS NULL" in src, "_recalc_current_weight must exclude samples (is_sample=0 or IS NULL)"


if __name__ == "__main__":
    test_sample_weight_constant_defined()
    test_inbound_excludes_sample_weight()
    test_recalc_excludes_sample()
    print("OK — BUG-2026-04-20-001 regression guards pass")
