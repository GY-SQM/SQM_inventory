# -*- coding: utf-8 -*-
"""C6 회귀 테스트 — 소량 LOT 스캔 오차허용을 과대 적용하지 않는다."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BARCODE = os.path.join(ROOT, "core", "barcode_scan_engine.py")


def _read_barcode() -> str:
    with open(BARCODE, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\).*?:", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\n    def\s+", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_scan_tolerance_has_ratio_with_upper_and_lower_bounds():
    code = _read_barcode()
    assert "def _scan_target_tolerance_kg" in code, "오차허용 계산 helper가 필요함"
    helper = _function_block(code, "_scan_target_tolerance_kg")

    assert "min(" in helper and "max(" in helper, "비율 허용값에 상/하한이 모두 필요함"
    assert "0.001" in helper, "기존 0.1% 비율 기준은 유지해야 함"
    assert "0.05" in helper or "50g" in helper, "소량 LOT용 최소 허용값은 1kg보다 작아야 함"
    assert "0.5" in helper or "500g" in helper, "대량 LOT용 최대 허용값은 제한해야 함"


def test_random_uid_confirm_uses_tolerance_helper_not_max_one_kg():
    code = _read_barcode()
    fn = _function_block(code, "_confirm_one_uid_random")

    assert "_scan_target_tolerance_kg(target_kg)" in fn, "TARGET_EXCEEDED 검증은 helper 기반이어야 함"
    assert "max(1.0, target_kg * 0.001)" not in fn, "최소 1kg 허용은 소량 LOT에서 과대함"
