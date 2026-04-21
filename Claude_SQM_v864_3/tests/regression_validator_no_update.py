"""
Regression: Phase 3 fix — validators.py UPDATE removal
Fix: validators.py must NOT directly UPDATE inventory.current_weight
     except for DEPLETED auto-fix which is immediately followed by _recalc_current_weight.
"""
import sys
import pathlib
import inspect
import re

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def test_validator_update_is_depleted_only():
    """
    Any UPDATE inventory SET current_weight in validators.py must be
    paired with a subsequent _recalc_current_weight call (not standalone).
    """
    import engine_modules.validators as v
    src = inspect.getsource(v)

    # Find all UPDATE inventory SET current_weight patterns
    update_matches = list(re.finditer(
        r"UPDATE\s+inventory\s+SET\s+current_weight", src, re.IGNORECASE
    ))

    for m in update_matches:
        # Check nearby context (300 chars) for _recalc_current_weight
        context = src[m.start(): m.start() + 600]
        assert "_recalc_current_weight" in context, (
            f"validators.py UPDATE inventory SET current_weight at offset {m.start()} "
            f"is not followed by _recalc_current_weight (Phase 3 guard violated)"
        )


def test_validator_no_silent_update():
    """Validators must not silently update current_weight without audit trail."""
    import engine_modules.validators as v
    src = inspect.getsource(v)
    # Ensure any update has a logger call nearby
    update_matches = list(re.finditer(
        r"UPDATE\s+inventory\s+SET\s+current_weight", src, re.IGNORECASE
    ))
    for m in update_matches:
        context = src[max(0, m.start() - 200): m.start() + 200]
        assert "logger" in context, (
            f"validators.py UPDATE at offset {m.start()} has no logger call nearby"
        )


if __name__ == "__main__":
    test_validator_update_is_depleted_only()
    test_validator_no_silent_update()
    print("OK — Phase 3 validator no-update regression guards pass")
