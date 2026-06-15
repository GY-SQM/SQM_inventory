# -*- coding: utf-8 -*-
"""C9 회귀 테스트 — transaction 컨텍스트 내부 명시 commit 중복을 제거한다."""
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


def test_lot_mode_scan_transaction_has_no_manual_commit_inside_context():
    code = _read_barcode()
    fn = _function_block(code, "process_barcode_scan_for_lot_mode")
    tx_pos = fn.index('with self.db.transaction("IMMEDIATE")')
    return_pos = fn.index("'success': sold_count > 0", tx_pos)
    tx_block = fn[tx_pos:return_pos]

    assert "db.conn.commit" not in tx_block, "transaction 컨텍스트 내부 명시 commit은 중복/위험함"
    assert "C9_TRANSACTION_CONTEXT_OWNS_COMMIT" in fn, "C9 의도를 주석/로그로 남겨야 함"
