# -*- coding: utf-8 -*-
"""A5 회귀 테스트 — inventory.js가 API 응답 객체를 배열 rows로 정규화한다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVENTORY_JS = os.path.join(ROOT, "frontend", "js", "pages", "inventory.js")


def _read_inventory_js() -> str:
    with open(INVENTORY_JS, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _compact(code: str) -> str:
    return re.sub(r"\s+", "", code)


def _function_block(code: str, name: str) -> str:
    match = re.search(
        r"(?:async\s+)?function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{",
        code,
    )
    assert match, f"{name}() 함수를 찾지 못함"

    start = match.end() - 1
    depth = 0
    for i in range(start, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return code[match.start(): i + 1]

    raise AssertionError(f"{name}() 함수 블록 종료를 찾지 못함")


def test_inventory_load_does_not_assign_raw_json_response_directly_to_allData():
    code = _read_inventory_js()
    load = _function_block(code, "load")

    assert not re.search(
        r"allData\s*=\s*res\.ok\s*\?\s*await\s+res\.json\s*\(\s*\)",
        load,
    ), (
        "inventory.js가 res.json() 결과를 allData에 직접 대입하고 있음. "
        "{total,data:[...]} 응답 객체가 들어가면 allData.filter에서 TypeError 발생"
    )
    assert not re.search(r"allData\s*=\s*await\s+res\.json\s*\(\s*\)", load), (
        "inventory.js가 await res.json() 결과를 검증 없이 allData에 직접 대입하고 있음"
    )


def test_inventory_load_extracts_rows_and_guards_allData_array():
    code = _read_inventory_js()
    load = _function_block(code, "load")
    compact = _compact(load)

    assert "extractRows" in load, (
        "InventoryPage.load()는 API payload를 extractRows(...)로 정규화해야 함"
    )
    assert "Array.isArray" in load, (
        "InventoryPage.load() success path에 Array.isArray 배열 보장 가드가 없음"
    )
    assert re.search(r"allData=Array\.isArray\([^)]*\)\?[^:]+:\[\]", compact), (
        "allData는 최종적으로 Array.isArray(rows) ? rows : [] 형태로 설정되어야 함"
    )


def test_inventory_has_local_extractRows_fallback_for_common_response_shapes():
    code = _read_inventory_js()

    assert "function extractRows" in code, "window.extractRows가 없어도 동작하는 로컬 extractRows fallback이 필요함"
    assert "Array.isArray(res)" in code, "배열 직접 응답을 지원해야 함"
    assert "Array.isArray(res.data)" in code, "{data:[...]} 응답을 지원해야 함"
    assert "Array.isArray(res.data.rows)" in code, "{data:{rows:[...]}} 응답을 지원해야 함"
    assert "Array.isArray(res.data.items)" in code, "{data:{items:[...]}} 응답을 지원해야 함"


def test_inventory_rows_are_normalized_before_filter_and_render():
    code = _read_inventory_js()
    load = _function_block(code, "load")

    assert "function normalizeInventoryRow" in code, "lot_no/sap_no 등 backend 필드명을 UI 필드로 정규화해야 함"
    assert ".map(normalizeInventoryRow)" in load, "rows를 allData에 넣기 전에 normalizeInventoryRow를 적용해야 함"
    for token in ["lot_no", "sap_no", "bl_no", "container_no", "current_weight", "net_weight"]:
        assert token in code, f"normalizeInventoryRow가 {token} 대체 필드를 처리해야 함"


def test_inventory_applyFilters_does_not_call_filter_on_unvalidated_allData():
    code = _read_inventory_js()
    apply_filters = _function_block(code, "applyFilters")
    compact = _compact(apply_filters)

    assert "Array.isArray" in apply_filters, "applyFilters()가 allData 배열 여부를 방어하지 않음"
    assert not re.search(r"filtered\s*=\s*allData\.filter\s*\(", apply_filters), (
        "applyFilters()가 allData.filter(...)를 직접 호출하고 있음"
    )
    assert re.search(r"Array\.isArray\(allData\).*?\.filter\(", compact), (
        "filter 입력은 Array.isArray(allData)로 보장된 배열이어야 함"
    )


def test_inventory_load_reports_failures_before_sample_fallback():
    code = _read_inventory_js()
    load = _function_block(code, "load")

    assert "console.error('[inventory]" in load, "재고 API 로드 실패를 console.error로 남겨야 함"
    assert "showToast" in load, "재고 API 로드 실패를 사용자에게 toast로 알려야 함"
    assert "window.SAMPLE_INVENTORY" in load, "fallback은 명시적으로 window.SAMPLE_INVENTORY를 사용해야 함"
