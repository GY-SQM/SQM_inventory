# -*- coding: utf-8 -*-
"""A1 회귀 테스트 — 스플래시 API 응답 실패를 0 재고로 조용히 통과시키지 않는다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_WEBVIEW = os.path.join(ROOT, "main_webview.py")


def _read_main_webview() -> str:
    with open(MAIN_WEBVIEW, encoding="utf-8", errors="ignore") as f:
        return f.read()


def test_splash_health_fetch_checks_res_ok_before_json():
    code = _read_main_webview()

    match = re.search(
        r"var\s+res\s*=\s*await\s+fetch\(\s*base\s*\+\s*['\"]\/api\/health['\"]"
        r"[\s\S]*?"
        r"var\s+d\s*=\s*await\s+res\.json\s*\(\s*\)",
        code,
    )

    assert match, "스플래시 /api/health fetch 후 res.json() 구간을 찾지 못함"

    snippet = match.group(0)
    assert "res.ok" in snippet, (
        "스플래시 /api/health 응답에서 res.ok 확인 없이 res.json()을 호출하고 있음"
    )
    assert snippet.index("res.ok") < snippet.index("res.json"), (
        "스플래시 /api/health res.ok 검증은 res.json() 호출 전에 있어야 함"
    )


def test_splash_kpi_fetch_rejects_http_or_business_failure_before_using_zero_data():
    code = _read_main_webview()

    match = re.search(
        r"var\s+r2\s*=\s*await\s+fetch\(\s*base\s*\+\s*['\"]\/api\/dashboard\/kpi['\"]"
        r"[\s\S]*?"
        r"invalid\s+current_stock_mt",
        code,
    )

    assert match, "스플래시 /api/dashboard/kpi fetch 후 mt 반영 구간을 찾지 못함"

    snippet = match.group(0)
    assert "r2.ok" in snippet, (
        "스플래시 /api/dashboard/kpi HTTP 응답에서 r2.ok 확인이 없음"
    )
    assert "d2.ok === false" in snippet or "d2.ok===false" in snippet, (
        "스플래시 /api/dashboard/kpi 업무 실패(ok:false)를 0 재고로 조용히 통과시킬 수 있음"
    )
    assert "Number.isFinite" in snippet, (
        "스플래시 /api/dashboard/kpi current_stock_mt 숫자 검증이 없음"
    )


def test_splash_api_failure_is_reported_not_silently_swallowed():
    code = _read_main_webview()

    assert "reportSplashError" in code, "스플래시 API 실패 보고 함수가 없음"
    assert "console.error('[splash]'" in code, "스플래시 API 실패를 console.error로 남기지 않음"
    assert "재고 요약 로드 실패" in code, "스플래시 화면에 재고 요약 로드 실패 상태를 표시하지 않음"
    assert "catch(e){reportSplashError" in code.replace("\n", "").replace(" ", ""), (
        "스플래시 API 실패 catch가 비어 있거나 실패 보고를 호출하지 않음"
    )
