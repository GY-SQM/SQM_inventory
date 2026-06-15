# -*- coding: utf-8 -*-
"""A8 회귀 테스트 — wait_for_api 타임아웃 시 사용자 피드백과 재시도 수단을 표시한다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_WEBVIEW = os.path.join(ROOT, "main_webview.py")


def _read_main_webview() -> str:
    with open(MAIN_WEBVIEW, encoding="utf-8", errors="ignore") as f:
        return f.read()


def test_wait_for_api_timeout_log_keeps_probe_context():
    code = _read_main_webview()
    match = re.search(r"def\s+wait_for_api\(timeout=10\):(?P<body>[\s\S]*?)\n#\s*=+", code)
    assert match, "wait_for_api 함수를 찾지 못함"
    body = match.group("body")

    assert "last_url" in body and "last_error" in body, "타임아웃 로그에 마지막 probe URL/예외가 필요함"
    assert "API 서버 연결 타임아웃" in body, "타임아웃 원인을 로그에 명시해야 함"


def test_api_timeout_error_screen_has_visible_banner_and_retry_button():
    code = _read_main_webview()
    match = re.search(r"error_html\s*=\s*\((?P<body>[\s\S]*?)\n\s*\)", code)
    assert match, "API 시작 실패 error_html 블록을 찾지 못함"
    body = match.group("body")

    assert "API 연결 타임아웃" in body, "오류 화면에 타임아웃 배너/문구가 보여야 함"
    assert "id=\"api-timeout-banner\"" in body or "api-timeout-banner" in body, (
        "오류 화면에는 API 타임아웃 배너 식별자가 있어야 함"
    )
    assert "id=\"retry-api" in body or "retry-api" in body, "오류 화면에 재시도 버튼이 있어야 함"
    assert "다시 시도" in body or "재시도" in body, "재시도 버튼 문구가 필요함"
    assert "window.location.href" in body and "API_HOST" in body and "API_PORT" in body, (
        "재시도 버튼은 현재 API_HOST/API_PORT의 메인 URL로 다시 이동해야 함"
    )


def test_api_timeout_error_screen_is_loaded_after_phase_error_and_force_show():
    code = _read_main_webview()
    match = re.search(
        r"API 시작 실패 -> 오류 화면 표시[\s\S]*?window\.load_html\(error_html\)[\s\S]*?_force_show_main_window\(\)",
        code,
    )
    assert match, "API 타임아웃 오류 화면 load_html 후 창 강제 표시 경로가 필요함"
    snippet = match.group(0)

    assert '_phase[0] = "error"' in snippet, "오류 화면 로드 전 phase를 error로 전환해야 함"
    assert "window.html = error_html" in snippet, "PyWebView race 방지를 위해 window.html도 동기화해야 함"
