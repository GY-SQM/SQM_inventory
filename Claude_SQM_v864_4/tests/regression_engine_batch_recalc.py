"""
Regression: Phase 3-B fix — batch path _recalc_current_weight missing
Fix: features/parsers/sales_order_engine.py — _recalc_current_weight added to batch path
"""
import sys
import pathlib
import inspect

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def test_batch_path_calls_recalc():
    """sales_order_engine batch path must call _recalc_current_weight."""
    import features.parsers.sales_order_engine as soe
    src = inspect.getsource(soe)
    # Phase 3-B added _recalc_current_weight call on batch path (executemany path)
    assert "_recalc_current_weight" in src, (
        "sales_order_engine must call _recalc_current_weight (Phase 3-B fix missing)"
    )


def test_recalc_called_on_multiple_paths():
    """_recalc_current_weight must appear at least twice (batch + non-batch)."""
    import features.parsers.sales_order_engine as soe
    src = inspect.getsource(soe)
    count = src.count("_recalc_current_weight")
    assert count >= 2, (
        f"Expected _recalc_current_weight on batch+non-batch paths (≥2 calls), found {count}"
    )


if __name__ == "__main__":
    test_batch_path_calls_recalc()
    test_recalc_called_on_multiple_paths()
    print("OK — Phase 3-B batch recalc regression guards pass")
