# -*- coding: utf-8 -*-
"""B4 회귀 테스트 — Allocation 일부 처리와 전체 실패를 구분한다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOC_API = os.path.join(ROOT, "backend", "api", "allocation_api.py")


def _read_alloc_api() -> str:
    with open(ALLOC_API, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _import_function_block(code: str) -> str:
    marker = "result = engine.reserve_from_allocation"
    pos = code.index(marker)
    start = code.rfind("@router", 0, pos)
    end = code.index("# ────────────────────────────────────────────────────────────", pos)
    return code[start:end]


def test_allocation_import_uses_processed_count_for_partial_success():
    code = _read_alloc_api()
    fn = _import_function_block(code)

    assert 'processed = int(result.get("processed", reserved)' in fn, (
        "engine 결과의 processed 수를 읽어 reserved=0이어도 처리된 행과 전체 실패를 구분해야 함"
    )
    assert "partial_success" in fn, "부분 성공/부분 처리 상태 플래그가 필요함"
    assert "PARTIAL_SUCCESS" in fn, "부분 성공/부분 처리 전용 코드가 필요함"
    assert "processed > 0" in fn, "processed>0이면 전체 실패와 다른 분기로 처리해야 함"


def test_allocation_import_partial_success_returns_ok_true_with_reasons():
    code = _read_alloc_api()
    fn = _import_function_block(code)

    partial_match = re.search(r"if\s+partial_success\s*:[\s\S]*?return\s+\{(?P<body>[\s\S]*?)\n\s*\}\s*\n\s*if\s+not\s+partial_success", fn)
    assert partial_match, "partial_success 반환 분기를 찾지 못함"
    body = partial_match.group("body")

    assert '"ok": True' in body, "processed>0 부분 처리 케이스는 전체 실패가 아니라 ok:true로 반환해야 함"
    assert '"reserved": reserved' in body, "예약 수를 응답에 포함해야 함"
    assert '"processed": processed' in body, "처리 수를 응답에 포함해야 함"
    assert '"errors": errors[:20]' in body, "실패 사유를 함께 반환해야 함"
    assert '"error_details": error_details[:20]' in body, "행별 실패 상세를 함께 반환해야 함"
    assert '"partial_success": True' in body, "부분 처리 플래그를 응답 data에 포함해야 함"


def test_allocation_import_full_failure_remains_ok_false_only_when_processed_zero():
    code = _read_alloc_api()
    fn = _import_function_block(code)

    assert "processed <= 0" in fn or "not partial_success" in fn, (
        "전체 실패 ok:false는 processed=0인 경우로 제한되어야 함"
    )
    assert '"code": "ALLOCATION_FAILED"' in fn, "전체 실패 코드는 유지해야 함"
