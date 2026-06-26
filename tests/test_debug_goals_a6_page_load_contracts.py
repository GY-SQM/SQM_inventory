# -*- coding: utf-8 -*-
"""A6 회귀 테스트 — dashboard/allocation/picked 페이지가 실패 응답을 빈 테이블로 숨기지 않는다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_JS = os.path.join(ROOT, "frontend", "js", "pages", "dashboard.js")
ALLOCATION_JS = os.path.join(ROOT, "frontend", "js", "_archive", "pages", "allocation.js")
PICKED_JS = os.path.join(ROOT, "frontend", "js", "_archive", "pages", "picked.js")


def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _compact(code: str) -> str:
    return re.sub(r"\s+", "", code)


def _function_block(code: str, name: str) -> str:
    match = re.search(r"(?:async\s+)?function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", code)
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


def _assert_failure_contract(code: str, load_block: str, page_label: str) -> None:
    compact = _compact(load_block)
    assert "ok===false" in compact or "ok === false" in load_block, (
        f"{page_label}가 HTTP 2xx + ok:false 업무 실패를 성공/빈 데이터로 처리할 수 있음"
    )
    assert "success===false" in compact or "success === false" in load_block, (
        f"{page_label}가 HTTP 2xx + success:false 업무 실패를 성공/빈 데이터로 처리할 수 있음"
    )
    assert "console.error" in code, f"{page_label} 로드 실패를 console.error로 남겨야 함"
    assert "showToast" in code, f"{page_label} 로드 실패를 showToast로 사용자에게 알려야 함"
    assert "로드 실패" in code or "불러오기 실패" in code, f"{page_label} 화면에 실패 문구가 필요함"


def test_dashboard_loadAll_validates_response_shape_and_reports_failure():
    code = _read(DASHBOARD_JS)
    load_all = _function_block(code, "loadAll")

    assert "normalizeDashboardStats" in code, "dashboard 응답을 products/lots 구조로 정규화해야 함"
    assert re.search(r"Array\.isArray\([^)]*products[^)]*\)", load_all), "products 배열 보장이 필요함"
    assert re.search(r"Array\.isArray\([^)]*lots[^)]*\)", load_all), "lots 배열 보장이 필요함"
    assert "data.products || SAMPLE.products" not in load_all, "products를 배열 검증 없이 fallback하면 안 됨"
    assert "data.lots || SAMPLE.lots" not in load_all, "lots를 배열 검증 없이 fallback하면 안 됨"
    _assert_failure_contract(code, load_all, "dashboard")


def test_allocation_load_extracts_rows_and_reports_failure():
    code = _read(ALLOCATION_JS)
    load = _function_block(code, "load")
    compact = _compact(load)

    assert "fetchJsonChecked" in code, "allocation 직접 fetch는 응답 본문/업무 실패 검증 helper가 필요함"
    assert "extractRows" in code and "extractRows" in load, "allocation 응답 rows를 extractRows로 정규화해야 함"
    assert "Array.isArray" in load, "allocation data 배열 보장이 필요함"
    assert re.search(r"data=Array\.isArray\([^)]*\)\?[^:]+:\[\]", compact), (
        "allocation data는 Array.isArray(rows) ? rows : [] 형태로 보장되어야 함"
    )
    assert not re.search(r"data\s*=\s*j\.data\s*\|\|\s*\[\]", load), "j.data 직접 대입 금지"
    _assert_failure_contract(code, load, "allocation")


def test_picked_load_extracts_rows_and_reports_failure():
    code = _read(PICKED_JS)
    load = _function_block(code, "load")
    compact = _compact(load)

    assert "extractRows" in code and "extractRows" in load, "picked 응답 rows를 extractRows로 정규화해야 함"
    assert "Array.isArray" in load, "picked rows 배열 보장이 필요함"
    assert re.search(r"rows=Array\.isArray\([^)]*\)\?[^:]+:\[\]", compact), (
        "picked rows는 Array.isArray(rows) ? rows : [] 형태로 보장되어야 함"
    )
    assert "(res?.data??res?.rows??[])||[]" not in compact, "res.data/res.rows 직접 fallback 금지"
    _assert_failure_contract(code, load, "picked")
    assert "picked-empty" in code and "empty.textContent" in load, "picked 실패는 empty 영역에 표시되어야 함"
