# -*- coding: utf-8 -*-
"""C3 회귀 테스트 — stop_at_picked=True 경로도 allocation_plan 기록을 보장한다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTBOUND = os.path.join(ROOT, "engine_modules", "inventory_modular", "outbound_mixin.py")


def _read_outbound() -> str:
    with open(OUTBOUND, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\).*?:", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\n    def\s+", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_stop_at_picked_returns_only_after_allocation_plan_insert_attempt():
    code = _read_outbound()
    fn = _function_block(code, "_process_single_outbound")

    alloc_insert_pos = fn.index("INSERT INTO allocation_plan")
    stop_pos = fn.index("if stop_at_picked:")
    return_pos = fn.index("return {'lot_no': lot_no", stop_pos)

    assert alloc_insert_pos < stop_pos < return_pos, (
        "stop_at_picked=True 경로는 반환 전에 allocation_plan을 기록해야 함"
    )


def test_allocation_plan_insert_has_legacy_schema_fallback_without_source_column():
    code = _read_outbound()
    fn = _function_block(code, "_process_single_outbound")

    assert "C3_ALLOC_PLAN_LEGACY_NO_SOURCE" in fn, "source 컬럼 없는 레거시 스키마 폴백 로그/사유가 필요함"
    assert "INSERT INTO allocation_plan" in fn and "executed_at)" in fn, "현행 스키마 insert는 유지해야 함"
    assert "outbound_date, status, executed_at)" in fn, (
        "source 컬럼이 없어도 allocation_plan을 기록하는 fallback INSERT가 필요함"
    )
    fallback_block = fn[fn.index("C3_ALLOC_PLAN_LEGACY_NO_SOURCE"):fn.index("else:", fn.index("C3_ALLOC_PLAN_LEGACY_NO_SOURCE"))]
    assert "raise" not in fallback_block, (
        "source 컬럼 누락은 stop_at_picked allocation_plan 기록 누락으로 이어지면 안 됨"
    )
