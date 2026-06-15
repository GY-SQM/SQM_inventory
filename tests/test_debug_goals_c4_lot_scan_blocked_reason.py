# -*- coding: utf-8 -*-
"""C4 회귀 테스트 — allocation 미등록 LOT 스캔 차단 사유를 사용자에게 명시한다."""
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


def test_lot_scan_blocked_includes_errors_message_and_next_step():
    code = _read_barcode()
    fn = _function_block(code, "_confirm_one_uid_random")
    blocked_pos = fn.index("LOT_SCAN_BLOCKED")
    block = fn[blocked_pos - 220:blocked_pos + 900]

    assert "errors" in block, "LOT_SCAN_BLOCKED 응답에 errors 배열이 필요함"
    assert "message" in block, "LOT_SCAN_BLOCKED 응답에 사용자 표시 message가 필요함"
    assert "next_step" in block, "선행 조치 안내 next_step이 필요함"
    assert "Allocation" in block or "배분" in block, "Allocation/배분 선행조건을 명시해야 함"
    assert "예약" in block or "allocation_plan" in block, "예약 계획 부재를 명시해야 함"


def test_lot_scan_blocked_is_not_silent_empty_failure():
    code = _read_barcode()
    fn = _function_block(code, "_confirm_one_uid_random")
    blocked_pos = fn.index("LOT_SCAN_BLOCKED")
    block = fn[blocked_pos - 120:blocked_pos + 420]

    assert "return {\"ok\": False, \"uid\": uid, \"reason\": \"LOT_SCAN_BLOCKED\", \"lot_no\": lot_no}" not in block, (
        "단순 reason만 반환하면 사용자가 왜 막혔는지 알 수 없음"
    )
