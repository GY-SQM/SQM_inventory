# -*- coding: utf-8 -*-
"""D1 회귀 테스트 — 반품 RETURN 대기 후 자동 AVAILABLE 복귀 옵션."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RETURN_MIXIN = os.path.join(ROOT, "engine_modules", "inventory_modular", "return_mixin.py")


def _read_return_mixin() -> str:
    with open(RETURN_MIXIN, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\).*?:", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\n    def\s+", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_process_return_exposes_auto_finalize_queue_after_transaction():
    code = _read_return_mixin()
    fn = _function_block(code, "process_return")

    assert "auto_finalize_to_available" in fn, "반품 후 AVAILABLE 자동복귀 옵션이 필요함"
    assert "_auto_finalize_returns" in fn, "트랜잭션 이후 finalize 대상을 수집해야 함"
    assert "finalize_return_to_available" in fn, "RETURN→AVAILABLE 공개 메서드를 호출해야 함"
    assert "finalized" in fn, "응답에 자동복귀 결과를 포함해야 함"


def test_process_return_does_not_call_finalize_inside_return_transaction():
    code = _read_return_mixin()
    fn = _function_block(code, "process_return")
    tx_pos = fn.index('with self.db.transaction("IMMEDIATE")')
    finalize_pos = fn.rindex("self.finalize_return_to_available")

    assert finalize_pos > tx_pos
    after_tx_marker = "# D1_AUTO_FINALIZE_RETURN_TO_AVAILABLE"
    assert after_tx_marker in fn
    assert fn.index(after_tx_marker) < finalize_pos, "중첩 트랜잭션 방지를 위해 transaction 밖에서 finalize 해야 함"
