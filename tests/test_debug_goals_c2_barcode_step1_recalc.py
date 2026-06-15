# -*- coding: utf-8 -*-
"""C2 회귀 테스트 — LOT 스캔 STEP1(PICKED) 직후 상위 LOT 상태/무게를 재계산한다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BARCODE = os.path.join(ROOT, "core", "barcode_scan_engine.py")


def _read_barcode() -> str:
    with open(BARCODE, encoding="utf-8", errors="ignore") as f:
        return f.read()


def test_lot_mode_scan_recalculates_lot_immediately_after_step1_picked():
    code = _read_barcode()

    step1_pos = code.index("# ── STEP 1: RESERVED → PICKED")
    step2_pos = code.index("# ── STEP 2: PICKED → SOLD", step1_pos)
    step1_block = code[step1_pos:step2_pos]

    assert "_recalc_inventory_lot_weights" in step1_block and "lot_no" in step1_block, (
        "STEP1에서 tonbag을 PICKED로 바꾼 직후 LOT 상태/무게 재계산이 필요함"
    )
    assert "C2_SCAN_STEP1_PICKED" in step1_block, "C2 원인 추적용 재계산 reason이 필요함"


def test_lot_mode_scan_keeps_batch_recalc_after_step2_as_safety_net():
    code = _read_barcode()

    assert "P2_SCAN_BATCH" in code, "STEP2 이후 배치 재계산 안전망은 유지되어야 함"
    assert "processed_lots" in code, "스캔 LOT 목록 기반 배치 재계산 흐름은 유지되어야 함"
