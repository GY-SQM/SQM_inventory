# -*- coding: utf-8 -*-
"""A7 회귀 테스트 — main.js router init 실패를 콘솔에만 숨기지 않는다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_JS = os.path.join(ROOT, "frontend", "js", "main.js")
ROUTER_JS = os.path.join(ROOT, "frontend", "js", "router.js")


def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


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


def test_main_has_router_failure_report_helper_with_visible_feedback():
    code = _read(MAIN_JS)

    assert "function reportRouterProblem" in code, "router 실패를 사용자에게 알리는 전용 helper가 필요함"
    helper = _function_block(code, "reportRouterProblem")

    assert "console.error" in helper, "router 실패 traceback/원인은 console.error로 남겨야 함"
    assert "showToast" in helper, "router 실패를 toast로 사용자에게 알려야 함"
    assert "page-container" in helper, "router 실패 시 화면 영역에 에러 배너를 표시해야 함"
    assert "routerInitFailed" in helper, "window.SQM.routerInitFailed 상태를 남겨야 함"
    assert "routerInitError" in helper, "window.SQM.routerInitError 상태를 남겨야 함"


def test_main_router_init_catch_calls_failure_reporter_not_console_only():
    code = _read(MAIN_JS)
    boot = _function_block(code, "boot")

    assert "initRouterSafely" in code and "initRouterSafely()" in boot, (
        "boot()는 router init을 직접 try/catch 한 줄로 삼키지 말고 initRouterSafely()를 호출해야 함"
    )
    assert "console.error('router', e)" not in boot, (
        "router init 실패를 console.error만 하고 끝내면 사이드바 장애가 사용자에게 보이지 않음"
    )

    safe = _function_block(code, "initRouterSafely")
    assert "mods.router?.initRouter?.()" not in safe, "optional chaining으로 router 누락을 조용히 무시하면 안 됨"
    assert "reportRouterProblem" in safe, "router 모듈 누락/initRouter 누락/throw를 reportRouterProblem으로 알려야 함"
    assert "typeof mods.router.initRouter !== 'function'" in safe, "initRouter 함수 누락을 명시적으로 검사해야 함"


def test_main_loadModules_records_failed_router_module():
    code = _read(MAIN_JS)
    load_modules = _function_block(code, "loadModules")

    assert "mods[name] = null" in load_modules, "모듈 import 실패도 mods에 null로 기록해야 실패 모듈 로그가 정확함"
    assert "name === 'router'" in load_modules, "router 모듈 로드 실패는 별도로 사용자에게 알려야 함"
    assert "reportRouterProblem" in load_modules, "router 모듈 import 실패도 reportRouterProblem으로 보여야 함"


def test_main_failsafe_respects_sqm_inline_binding_marker():
    code = _read(MAIN_JS)
    fail_safe = _function_block(code, "installFailSafe")

    assert "_sqmBound" in fail_safe, (
        "sqm-inline.js는 data-route에 _sqmBound를 쓰므로 fail-safe가 정상 바인딩을 미바인딩으로 오판하면 안 됨"
    )
    assert "renderPage" in fail_safe, "window.renderPage 또는 window.SQM.renderPage가 있으면 실제 라우터가 있다고 보아야 함"


def test_router_initRouter_stays_noop_without_click_binding():
    code = _read(ROUTER_JS)
    init_router = _function_block(code, "initRouter")
    executable = "\n".join(line for line in init_router.splitlines() if not line.strip().startswith("//"))

    assert "addEventListener" not in executable, "A7 수정이 router.js 클릭 바인딩을 부활시키면 안 됨"
    assert "navigateTo(" not in executable, "A7 수정이 router.js initRouter에서 navigateTo를 호출하면 안 됨"
