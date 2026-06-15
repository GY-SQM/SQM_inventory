# -*- coding: utf-8 -*-
"""B5 회귀 테스트 — Allocation 예약 후 실제 RESERVED 톤백 상태를 재조회한다."""
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


def test_allocation_import_rechecks_actual_reserved_tonbags_after_engine_result():
    code = _read_alloc_api()
    fn = _import_function_block(code)

    assert "def _verify_reserved_tonbags" in code, "실제 RESERVED 톤백 재조회 helper가 필요함"
    assert "reserved_recheck = _verify_reserved_tonbags(engine, rows, reserved)" in fn, (
        "reserve_from_allocation 결과 직후 실제 inventory_tonbag RESERVED 상태를 재조회해야 함"
    )
    assert '"reserved_recheck"' in fn, "응답 data에 reserved_recheck 진단 결과를 포함해야 함"


def test_reserved_recheck_queries_inventory_tonbag_reserved_state():
    code = _read_alloc_api()
    helper_match = re.search(r"def\s+_verify_reserved_tonbags\([\s\S]*?\n\ndef\s+", code)
    assert helper_match, "_verify_reserved_tonbags helper 블록을 찾지 못함"
    helper = helper_match.group(0)

    assert "inventory_tonbag" in helper, "재검증은 inventory_tonbag 실제 상태를 조회해야 함"
    assert "status='RESERVED'" in helper or 'status = \'RESERVED\'' in helper or 'status = "RESERVED"' in helper, (
        "실제 RESERVED 상태를 조건으로 조회해야 함"
    )
    assert "sale_ref" in helper and "lot_no" in helper, "LOT/sale_ref 기준으로 방금 예약된 톤백을 조회해야 함"
    assert "expected_reserved" in helper and "actual_reserved" in helper, "예상/실제 예약 수를 모두 반환해야 함"
    assert "ok" in helper, "재검증 결과 ok 플래그가 필요함"


def test_allocation_import_reserved_mismatch_is_not_silent_success():
    code = _read_alloc_api()
    fn = _import_function_block(code)

    assert "RESERVED_RECHECK_MISMATCH" in fn, "예약 수 불일치 전용 경고/오류 코드가 필요함"
    assert "reserved_recheck.get(\"ok\") is False" in fn or "not reserved_recheck.get(\"ok\")" in fn, (
        "reserved_recheck 실패를 감지해야 함"
    )
    assert "errors.append" in fn and "error_details.append" in fn, (
        "불일치 시 errors와 error_details에 원인을 남겨야 함"
    )
