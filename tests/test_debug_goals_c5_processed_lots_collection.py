# -*- coding: utf-8 -*-
"""C5 회귀 테스트 — 대량 LOT 스캔 재계산 대상 LOT을 루프 내에서 직접 수집한다."""
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


def test_lot_mode_scan_collects_processed_lots_inside_success_loop():
    code = _read_barcode()
    fn = _function_block(code, "process_barcode_scan_for_lot_mode")
    step2_pos = fn.index("# ── STEP 2: PICKED → SOLD")
    batch_recalc_pos = fn.index("P2_SCAN_BATCH")
    success_block = fn[step2_pos:batch_recalc_pos]

    assert "processed_lots.add(lot_no)" in success_block, (
        "성공 처리된 LOT만 루프 안에서 직접 processed_lots에 수집해야 함"
    )


def test_batch_recalc_filters_none_and_does_not_refetch_lots_from_scanned_codes():
    code = _read_barcode()
    fn = _function_block(code, "process_barcode_scan_for_lot_mode")
    recalc_start = fn.index("P2_SCAN_BATCH") - 500
    recalc_block = fn[recalc_start:recalc_start + 1100]

    assert "if _lot" in recalc_block or "if not _lot" in recalc_block, "None/빈 LOT 필터가 필요함"
    assert "for _lot in sorted(processed_lots)" in recalc_block or "for _lot in processed_lots" in recalc_block
    assert "self.db.fetchone(\n                    \"SELECT lot_no FROM inventory_tonbag" not in recalc_block, (
        "스캔 코드로 사후 재조회하면 not_found/None이 섞여 일부 LOT 재계산이 누락될 수 있음"
    )
