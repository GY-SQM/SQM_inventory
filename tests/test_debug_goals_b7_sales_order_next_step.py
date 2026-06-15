# -*- coding: utf-8 -*-
"""B7 회귀 테스트 — Sales/Picking 검증 PASS 후 다음 전환 단계를 명시한다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATION = os.path.join(ROOT, "backend", "api", "sales_order_validation.py")


def _read_validation() -> str:
    with open(VALIDATION, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\)\s*->\s*dict\s*:", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\ndef\s+", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_finalize_adds_transition_guidance_for_ok_validation():
    code = _read_validation()
    fn = _function_block(code, "_finalize")

    assert "next_step" in fn, "검증 결과에 다음 단계 안내 next_step이 필요함"
    assert "transition_required" in fn, "검증 PASS가 상태전환 완료가 아님을 표시해야 함"
    assert "confirm_endpoint" in fn, "SOLD 확정 엔드포인트 안내가 필요함"
    assert "pick_endpoint" in fn, "PICKED 전환 엔드포인트 안내가 필요함"


def test_matched_messages_explain_validation_does_not_change_status():
    code = _read_validation()

    assert "검증 PASS" in code, "MATCHED 메시지에 검증 PASS 문구가 필요함"
    assert "상태 전환은 별도" in code, "검증 함수가 상태 전환을 하지 않는다는 안내가 필요함"
    assert "/api/outbound/confirm" in code, "출고확정 API 경로 안내가 필요함"


def test_validation_callers_return_allocation_validation_with_next_step():
    outbound_path = os.path.join(ROOT, "backend", "api", "outbound_api.py")
    queries_path = os.path.join(ROOT, "backend", "api", "queries3.py")
    with open(outbound_path, encoding="utf-8", errors="ignore") as f:
        outbound = f.read()
    with open(queries_path, encoding="utf-8", errors="ignore") as f:
        queries = f.read()

    assert "allocation_validation" in outbound and "validate_picking_doc" in outbound
    assert "allocation_validation" in queries and "validate_sales_order_no" in queries
    assert "next_step" in _function_block(_read_validation(), "_finalize"), (
        "호출자는 allocation_validation 전체를 반환하므로 helper가 next_step을 포함해야 함"
    )
