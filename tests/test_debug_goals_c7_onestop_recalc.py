# -*- coding: utf-8 -*-
"""C7 회귀 테스트 — OneStop SOLD 전환은 current_weight=0 하드코딩 대신 재계산한다."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTBOUND_API = os.path.join(ROOT, "backend", "api", "outbound_api.py")


def _read_outbound_api() -> str:
    with open(OUTBOUND_API, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\).*?:", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\n\s*@router|\nclass\s+", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_onestop_complete_does_not_zero_inventory_current_weight():
    code = _read_outbound_api()
    fn = _function_block(code, "onestop_complete")

    assert "current_weight=0" not in fn, "부분 출고/잔량 LOT에서 current_weight=0 하드코딩 금지"
    assert "current_weight = 0" not in fn, "부분 출고/잔량 LOT에서 current_weight=0 하드코딩 금지"


def test_onestop_complete_recalculates_lot_after_sold_transition():
    code = _read_outbound_api()
    fn = _function_block(code, "onestop_complete")

    assert "_recalc_current_weight" in fn, "SOLD 전환 후 LOT 무게 재계산 호출 필요"
    assert "_recalc_lot_status" in fn or "recalc_lot_status" in fn, "SOLD 전환 후 LOT 상태 재계산 호출 필요"
    assert "C7_ONESTOP_COMPLETE" in fn, "재계산 reason으로 C7 추적 가능해야 함"
