# -*- coding: utf-8 -*-
"""B6 회귀 테스트 — apply_approved 일부 미반영을 성공으로만 숨기지 않는다."""
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


def test_apply_approved_tracks_attempted_and_failed_lots():
    code = _read_outbound_mixin()
    fn = _function_block(code, "apply_approved_allocation_reservations")

    assert '"attempted": 0' in fn, "승인 반영 대상 건수 attempted를 결과에 포함해야 함"
    assert '"failed": 0' in fn, "미반영 건수 failed를 결과에 포함해야 함"
    assert 'result["attempted"] = len(staged_rows)' in fn, "조회된 승인 완료 건수를 attempted에 기록해야 함"
    assert 'result["failed"] += 1' in fn, "continue 스킵되는 미반영 LOT은 failed 카운트에 반영해야 함"


def test_apply_approved_partial_success_has_explicit_flag_and_warning():
    code = _read_outbound_mixin()
    fn = _function_block(code, "apply_approved_allocation_reservations")

    assert '"partial_success"' in fn, "일부만 반영된 경우 partial_success 플래그가 필요함"
    assert "result[\"partial_success\"] = result[\"applied\"] > 0 and result[\"failed\"] > 0" in fn, (
        "applied>0 이면서 failed>0이면 부분성공으로 표시해야 함"
    )
    assert "APPLY_APPROVED_PARTIAL" in fn, "부분 반영 전용 warning/error code가 필요함"


def test_apply_approved_api_returns_attempted_failed_partial_fields():
    api_path = os.path.join(ROOT, "backend", "api", "allocation_api.py")
    with open(api_path, encoding="utf-8", errors="ignore") as f:
        api = f.read()

    assert '"attempted": int(result.get("attempted", 0))' in api, "apply-approved API data에 attempted 포함 필요"
    assert '"failed": int(result.get("failed", 0))' in api, "apply-approved API data에 failed 포함 필요"
    assert '"partial_success": bool(result.get("partial_success"))' in api, "apply-approved API data에 partial_success 포함 필요"
