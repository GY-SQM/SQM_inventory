"""
Phase 1-3 & 1-4 스모크 테스트
- 전역 JS 에러 핸들러 파일 존재 및 핵심 로직 포함 여부
- API 타임아웃 + 재시도 로직이 sqm-core.js / api-client.js에 있는지 확인
"""
import os

BASE = os.path.join(os.path.dirname(__file__), "..", "frontend")


def _read(rel_path: str) -> str:
    path = os.path.join(BASE, rel_path)
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


# ── Phase 1-3: 전역 JS 에러 핸들러 ──────────────────────────

def test_error_handler_file_exists():
    """sqm-error-handler.js 파일이 존재해야 한다."""
    path = os.path.join(BASE, "js", "sqm-error-handler.js")
    assert os.path.exists(path), "sqm-error-handler.js 파일 없음"


def test_error_handler_has_window_error_listener():
    """window error 이벤트 리스너가 있어야 한다."""
    code = _read("js/sqm-error-handler.js")
    assert "addEventListener('error'" in code or 'addEventListener("error"' in code, \
        "window error 이벤트 리스너 없음"


def test_error_handler_has_unhandledrejection_listener():
    """unhandledrejection 리스너가 있어야 한다."""
    code = _read("js/sqm-error-handler.js")
    assert "unhandledrejection" in code, "unhandledrejection 리스너 없음"


def test_error_handler_shows_toast():
    """에러 발생 시 showToast를 호출해야 한다."""
    code = _read("js/sqm-error-handler.js")
    assert "showToast" in code, "에러 핸들러가 showToast를 호출하지 않음"


def test_error_handler_logs_to_console():
    """에러를 console.error로도 기록해야 한다."""
    code = _read("js/sqm-error-handler.js")
    assert "console.error" in code, "console.error 로그 없음"


def test_error_handler_registered_in_index_html():
    """index.html이 sqm-error-handler.js를 로드해야 한다."""
    html = _read("index.html")
    assert "sqm-error-handler.js" in html, \
        "index.html에 sqm-error-handler.js 스크립트 태그 없음"


def test_error_handler_has_guard_flag():
    """중복 로드 방지 가드가 있어야 한다."""
    code = _read("js/sqm-error-handler.js")
    assert "__SQM_ERROR_HANDLER__" in code, "중복 로드 방지 가드 없음"


# ── Phase 1-4: API 타임아웃 + 재시도 ─────────────────────────

def test_sqm_core_has_timeout_logic():
    """sqm-core.js에 타임아웃 로직이 있어야 한다."""
    code = _read("js/sqm-core.js")
    assert "timeout" in code.lower(), "sqm-core.js에 타임아웃 없음"
    assert "Promise.race" in code, "Promise.race 타임아웃 패턴 없음"


def test_sqm_core_has_retry_logic():
    """sqm-core.js에 재시도 로직이 있어야 한다."""
    code = _read("js/sqm-core.js")
    assert "retries" in code or "retry" in code.lower(), \
        "sqm-core.js에 재시도 로직 없음"


def test_api_client_has_timeout():
    """api-client.js에 타임아웃이 있어야 한다."""
    code = _read("js/api-client.js")
    assert "timeout" in code.lower(), "api-client.js에 타임아웃 없음"


def test_api_client_has_retry():
    """api-client.js에 재시도가 있어야 한다."""
    code = _read("js/api-client.js")
    assert "retries" in code, "api-client.js에 재시도 없음"


def test_api_client_has_exponential_backoff():
    """api-client.js에 지수 백오프가 있어야 한다."""
    code = _read("js/api-client.js")
    # 지수 백오프 패턴: 2 ** i 또는 Math.pow 또는 500/1000/2000 패턴
    has_backoff = ("2 **" in code or "Math.pow" in code or
                   "500 *" in code or "backoff" in code.lower())
    assert has_backoff, "지수 백오프 없음"
