# -*- coding: utf-8 -*-
"""A2 회귀 테스트 — API 실패 오류 화면도 숨김 런처에서 반드시 화면에 보인다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_WEBVIEW = os.path.join(ROOT, "main_webview.py")


def _read_main_webview() -> str:
    with open(MAIN_WEBVIEW, encoding="utf-8", errors="ignore") as f:
        return f.read()


def test_error_loaded_branch_forces_window_visible_before_return():
    code = _read_main_webview()

    match = re.search(
        r"if\s+_phase\[0\]\s*==\s*['\"]error['\"]\s*:"
        r"(?P<body>[\s\S]*?)"
        r"\n\s*#\s*_phase\[0\]\s*==\s*['\"]main['\"]",
        code,
    )

    assert match, "on_loaded()의 _phase == 'error' 분기를 찾지 못함"

    body = match.group("body")
    assert "_force_show_main_window()" in body, (
        "API 실패 오류 화면 로드 후에도 숨김 런처 대응을 위해 "
        "_phase == 'error' 분기에서 _force_show_main_window()를 호출해야 함"
    )
    assert body.index("_force_show_main_window()") < body.rindex("return"), (
        "오류 화면 표시 강제는 error 분기 return 전에 실행되어야 함"
    )
    assert "evaluate_js" not in body, (
        "오류 화면에서는 죽은 백엔드 fetch 루프 방지를 위해 JS 브릿지를 설치하면 안 됨"
    )


def test_api_wait_failure_loads_error_html_with_forced_visibility():
    code = _read_main_webview()

    match = re.search(
        r"else:\s*"
        r"[\s\S]*?API 시작 실패 -> 오류 화면 표시"
        r"[\s\S]*?window\.load_html\(error_html\)"
        r"[\s\S]*?오류 HTML 로드 완료",
        code,
    )

    assert match, "wait_for_api(timeout=10) 실패 시 오류 화면 로드/완료 로그 경로를 찾지 못함"

    snippet = match.group(0)
    assert '_phase[0] = "error"' in snippet or "_phase[0] = 'error'" in snippet, (
        "API 실패 시 window.load_html(error_html) 전에 _phase를 error로 전환해야 함"
    )
    assert "window.html = error_html" in snippet, (
        "PyWebView 초기화 race 방지를 위해 load_html 전에 window.html도 error_html로 동기화해야 함"
    )
    assert snippet.count("_force_show_main_window()") >= 2, (
        "오류 화면 로드 전후로 창 표시를 강제해야 숨김 런처/흰 화면 고착을 막을 수 있음"
    )
    assert "API 서버 시작 실패" in snippet, "오류 HTML에 사용자에게 보일 실패 제목이 있어야 함"
    assert "sqm_debug.log" in snippet, "오류 HTML에 로그 파일 안내가 있어야 함"

    phase_pos = min(
        pos for pos in [
            snippet.find('_phase[0] = "error"'),
            snippet.find("_phase[0] = 'error'"),
        ]
        if pos != -1
    )
    html_sync_pos = snippet.index("window.html = error_html")
    load_pos = snippet.index("window.load_html(error_html)")

    assert phase_pos < html_sync_pos < load_pos, (
        "error phase 전환 → window.html 동기화 → window.load_html(error_html) 순서여야 함"
    )


def test_wait_for_api_rebuilds_probe_urls_with_latest_api_port_each_loop():
    code = _read_main_webview()

    match = re.search(
        r"def\s+wait_for_api\(timeout=10\):(?P<body>[\s\S]*?)\n#\s*=+",
        code,
    )

    assert match, "wait_for_api 함수를 찾지 못함"

    body = match.group("body")
    while_pos = body.index("while time.time() < deadline")
    probes_pos = body.index("probes = [")
    assert while_pos < probes_pos, (
        "API_PORT 재시도 변경을 반영하려면 probes 목록을 while 루프 안에서 매번 생성해야 함"
    )
    assert "last_error" in body and "last_url" in body, (
        "API 타임아웃 로그에 마지막 probe URL/예외를 남겨야 원인 추적이 가능함"
    )
