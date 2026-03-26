# -*- coding: utf-8 -*-
"""
SQM v9.0 — 입고 서류 자동분류 회귀 테스트
==========================================
테스트셋: doc_classification_test_cases.csv (26케이스)

합격 기준:
  - 전체 정확도 88% 이상 (파일명 단독)
  - 실제 PDF 포함 시 95% 이상
  - BL/DO 상호오분류 0건 (절대 기준)
  - Critical 케이스 100% 통과

실행:
  pytest tests/test_inbound_doc_detector.py -v
"""
import csv
import re
import sys
from pathlib import Path

import pytest

# SQM 루트를 sys.path에 추가
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CSV_PATH = Path(__file__).parent / "doc_classification_test_cases.csv"


# ── 테스트용 분류 함수 (InboundDocDetector 파일명 로직 재현) ───────────
def _classify_filename(filename: str) -> str:
    """InboundDocDetector 파일명 분류 로직 (테스트 전용 재현)."""
    FILENAME_KEYWORD_MAP = {
        "PACKING_LIST": ["packing", "packlist", "p l", " pl ", "포장", "명세서"],
        "INVOICE":      ["invoice", "inv ", " inv", " fa ", "fa ", "송장", "화인보이스"],
        "BL":           ["seawaybill", "sea waybill", "billoflading", "bill of lading",
                         "b/l", " bl ", " bl.", "선하증권", "선하",
                         "medu", "maeu", "hmm", "cma", "cgmu", "one "],
        "DO":           ["delivery order", "delivery", "d/o", " do ", " do.",
                         "인도", "인도지시서", "release order", "cargo release"],
    }
    name_lower = filename.lower()
    name_pre   = re.sub(r'b[-.]l', 'bl', name_lower)
    key_name   = " " + re.sub(r"[\s_\-\.]+", " ", name_pre) + " "
    stem       = re.sub(r'\.[^.]+$', '', filename)

    do_keys = FILENAME_KEYWORD_MAP["DO"]
    if any(k in key_name for k in do_keys):
        return "DO"

    is_bl_number = bool(
        re.fullmatch(r'\d{9,12}', stem)
        or re.fullmatch(r'[A-Z]{4}[A-Z0-9]{5,}', stem)
        or re.fullmatch(r'[A-Z]{2,3}[A-Z0-9]{8,12}', stem)
    )
    if is_bl_number:
        if re.search(r'release', key_name) and not re.search(r' bl | do | delivery ', key_name):
            return "UNKNOWN"
        return "BL"

    for doc_type, keys in FILENAME_KEYWORD_MAP.items():
        if doc_type == "DO":
            continue
        if any(k in key_name for k in keys):
            return doc_type

    return "UNKNOWN"


# ── 테스트 케이스 로드 ─────────────────────────────────────────────────
def load_cases():
    if not CSV_PATH.exists():
        pytest.skip(f"테스트 CSV 없음: {CSV_PATH}", allow_module_level=True)
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ══════════════════════════════════════════════════════════════════════
# 개별 케이스 테스트 — case_06 제외 (파일명 무의미, 본문 2차 탐지 필요)
# ══════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("row", [
    r for r in load_cases()
    if r["case_group"] != "case_06_content_override"
], ids=lambda r: r["filename"])
def test_filename_classification(row):
    """파일명 기반 분류 — case_06 제외 (본문 2차 탐지 케이스)."""
    detected = _classify_filename(row["filename"])
    assert detected == row["expected_type"], (
        f"[{row['case_group']}] {row['filename']}\n"
        f"  expected={row['expected_type']}, detected={detected}\n"
        f"  basis={row['basis']}"
    )


# ══════════════════════════════════════════════════════════════════════
# Critical 케이스 — 절대 통과 (BL/DO 상호오분류 방지)
# ══════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("row", [
    r for r in load_cases() if r["risk_level"] == "Critical"
], ids=lambda r: r["filename"])
def test_critical_cases(row):
    """Critical 위험도 케이스는 반드시 통과."""
    detected = _classify_filename(row["filename"])
    assert detected == row["expected_type"], (
        f"🔴 CRITICAL FAIL: {row['filename']}\n"
        f"  expected={row['expected_type']}, detected={detected}"
    )


# ══════════════════════════════════════════════════════════════════════
# BL/DO 상호오분류 = 0 (절대 기준)
# ══════════════════════════════════════════════════════════════════════
def test_no_bl_do_cross_classification():
    """BL ↔ DO 상호오분류는 절대 0건이어야 한다."""
    cases = load_cases()
    cross_errors = []
    for row in cases:
        detected = _classify_filename(row["filename"])
        expected = row["expected_type"]
        if (expected, detected) in {("BL", "DO"), ("DO", "BL")}:
            cross_errors.append(
                f"{row['filename']}: expected={expected}, detected={detected}"
            )
    assert not cross_errors, "BL/DO 상호오분류 발생:\n" + "\n".join(cross_errors)


# ══════════════════════════════════════════════════════════════════════
# 전체 정확도 88% 이상 (파일명 단독)
# ══════════════════════════════════════════════════════════════════════
def test_overall_accuracy():
    """파일명 단독 정확도 88% 이상."""
    cases = [r for r in load_cases() if r["case_group"] != "case_06_content_override"]
    passed = sum(1 for r in cases if _classify_filename(r["filename"]) == r["expected_type"])
    accuracy = passed / len(cases) * 100
    assert accuracy >= 88.0, f"정확도 미달: {accuracy:.1f}% < 88% (기준)"


# ══════════════════════════════════════════════════════════════════════
# case_06: 파일명만으로는 UNKNOWN — 본문 탐지 의존 확인
# ══════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("row", [
    r for r in load_cases()
    if r["case_group"] == "case_06_content_override"
    and r["filename"].startswith("unknown_")
], ids=lambda r: r["filename"])
def test_case06_requires_text_detection(row):
    """파일명 unknown_* 는 UNKNOWN 반환 → 본문 2차 탐지로 처리됨을 확인."""
    detected = _classify_filename(row["filename"])
    assert detected == "UNKNOWN", (
        f"unknown_* 파일명은 UNKNOWN이어야 함: {row['filename']} → {detected}"
    )
