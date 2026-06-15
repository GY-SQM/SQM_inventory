# -*- coding: utf-8 -*-
"""B1 회귀 테스트 — apply_approved SQL 상수명을 식별자로 쓰지 않는다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTBOUND_MIXIN = os.path.join(ROOT, "engine_modules", "inventory_modular", "outbound_mixin.py")


def _read_outbound_mixin() -> str:
    with open(OUTBOUND_MIXIN, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\)\s*->\s*Dict\s*:", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\n    def\s+", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_apply_approved_update_uses_sql_parameters_for_status_constants():
    code = _read_outbound_mixin()
    fn = _function_block(code, "apply_approved_allocation_reservations")

    update_match = re.search(
        r"UPDATE\s+allocation_plan[\s\S]*?WHERE\s+id=\?\s+AND\s+status=\?\s+AND\s+workflow_status=\?",
        fn,
        re.I,
    )
    assert update_match, (
        "승인 반영 UPDATE는 status/workflow_status 상수를 SQL 문자열 식별자로 쓰지 말고 ? 파라미터로 비교해야 함"
    )
    update_sql = update_match.group(0)
    assert "workflow_status=?" in update_sql.replace(" ", ""), "workflow_status SET도 ? 파라미터여야 함"

    forbidden_patterns = [
        "workflow_status=ALLOC_WF_APPLIED",
        "status=ALLOC_STAGED",
        "workflow_status=ALLOC_WF_APPROVED",
    ]
    compact = re.sub(r"\s+", "", fn)
    for pat in forbidden_patterns:
        assert pat not in compact, f"SQL 안에 파이썬 상수명 {pat}를 식별자로 쓰면 sqlite 구문/컬럼 오류가 발생함"


def test_apply_approved_update_passes_constants_in_execute_params():
    code = _read_outbound_mixin()
    fn = _function_block(code, "apply_approved_allocation_reservations")

    assert "ALLOC_WF_APPLIED" in fn, "APPLIED workflow 상수는 파라미터 값으로 사용되어야 함"
    assert "ALLOC_STAGED" in fn, "STAGED status 상수는 파라미터 값으로 사용되어야 함"
    assert "ALLOC_WF_APPROVED" in fn, "APPROVED workflow 상수는 파라미터 값으로 사용되어야 함"

    params_match = re.search(
        r"self\.db\.execute\([\s\S]*?UPDATE\s+allocation_plan[\s\S]*?\(([\s\S]*?ALLOC_WF_APPLIED[\s\S]*?ALLOC_STAGED[\s\S]*?ALLOC_WF_APPROVED[\s\S]*?)\)\s*,?\s*\)",
        fn,
        re.I,
    )
    assert params_match, (
        "allocation_plan UPDATE execute 파라미터에 plan_id와 함께 ALLOC_WF_APPLIED, ALLOC_STAGED, ALLOC_WF_APPROVED를 전달해야 함"
    )
