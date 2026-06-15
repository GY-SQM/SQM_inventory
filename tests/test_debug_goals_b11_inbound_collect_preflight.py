# -*- coding: utf-8 -*-
"""B11 회귀 테스트 — 입고 필수 검증을 early return 하나로 숨기지 않는다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOUND_MIXIN = os.path.join(ROOT, "engine_modules", "inventory_modular", "inbound_mixin.py")


def _read_inbound_mixin() -> str:
    with open(INBOUND_MIXIN, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\).*?:", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\n    def\s+", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_process_inbound_collects_required_errors_before_returning():
    code = _read_inbound_mixin()
    fn = _function_block(code, "process_inbound")

    assert "preflight_errors" in fn, "필수 검증 오류를 preflight_errors에 모아야 함"
    assert "IB-01" in fn and "IB-02" in fn and "IB-08" in fn, "LOT/중량/B/L 필수 검증 코드가 함께 필요함"
    assert "result['errors'].extend(preflight_errors)" in fn, "모은 오류를 한번에 errors에 반영해야 함"
    assert "INBOUND_PREFLIGHT_FAILED" in fn, "필수 검증 실패 메시지 코드가 필요함"


def test_missing_lot_does_not_return_before_weight_and_bl_validation():
    code = _read_inbound_mixin()
    fn = _function_block(code, "process_inbound")

    missing_lot_pos = fn.index("IB-01")
    weight_pos = fn.index("IB-02")
    bl_pos = fn.index("IB-08")
    preflight_return_pos = fn.index("INBOUND_PREFLIGHT_FAILED")

    assert missing_lot_pos < weight_pos < preflight_return_pos, "LOT 누락 후에도 중량 검증까지 수행해야 함"
    assert missing_lot_pos < bl_pos < preflight_return_pos, "LOT 누락 후에도 B/L 검증까지 수행해야 함"
    assert "return result" not in fn[missing_lot_pos:weight_pos], "LOT 누락 직후 early return 하면 안 됨"


def test_legacy_single_field_early_return_messages_are_not_used_for_required_preflight():
    code = _read_inbound_mixin()
    fn = _function_block(code, "process_inbound")

    assert "LOT 번호가 없습니다" not in fn, "LOT 누락은 IB-01 preflight 오류로 통일해야 함"
    assert "유효하지 않은 중량" not in fn, "중량 오류는 IB-02 preflight 오류로 통일해야 함"
