# -*- coding: utf-8 -*-
"""A9 회귀 테스트 — outbound.js 출고확정 실패 시 재시도 수단을 남긴다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTBOUND_JS = os.path.join(ROOT, "frontend", "js", "pages", "outbound.js")


def _read_outbound_js() -> str:
    with open(OUTBOUND_JS, encoding="utf-8", errors="ignore") as f:
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


def test_confirm_outbound_failure_keeps_retry_action_not_toast_only():
    code = _read_outbound_js()
    confirm_fn = _function_block(code, "confirmOutbound")

    assert "showOutboundRetry" in code, "출고확정 실패 시 재시도 UI helper가 필요함"
    assert "showOutboundRetry" in confirm_fn, "confirmOutbound 실패 분기에서 재시도 UI를 표시해야 함"
    assert "outbound-retry" in code, "재시도 버튼/배너 식별자가 필요함"
    assert "다시 시도" in code or "재시도" in code, "사용자가 누를 수 있는 재시도 문구가 필요함"
    assert "confirmOutbound(lotNo)" in code, "재시도 버튼은 동일 LOT의 confirmOutbound를 다시 호출해야 함"

    catch_match = re.search(r"catch\s*\([^)]*\)?\s*\{(?P<body>[\s\S]*?)\}\s*\n\s*\}", confirm_fn)
    assert catch_match, "confirmOutbound catch 블록을 찾지 못함"
    catch_body = catch_match.group("body")
    assert "window.showToast" in catch_body, "실패 toast는 유지해야 함"
    assert "showOutboundRetry" in catch_body, "catch가 toast만 하고 끝나면 안 됨"


def test_confirm_outbound_validates_http_and_business_failure():
    code = _read_outbound_js()
    confirm_fn = _function_block(code, "confirmOutbound")

    assert "fetchJsonChecked" in code, "출고확정 응답은 HTTP/JSON/업무 실패 검증 helper로 처리해야 함"
    assert "fetchJsonChecked" in confirm_fn, "confirmOutbound는 fetch 후 res.json 직접 호출 대신 fetchJsonChecked를 사용해야 함"
    assert "!res.ok" in code or "res.ok === false" in code, "HTTP 실패를 명시적으로 에러 처리해야 함"
    assert "success === false" in code or "data.success" in confirm_fn, "업무 실패 응답도 성공으로 처리하면 안 됨"


def test_cancel_outbound_uses_same_retry_pattern_for_sibling_failure():
    code = _read_outbound_js()
    cancel_fn = _function_block(code, "cancelOutbound")

    assert "fetchJsonChecked" in cancel_fn, "취소도 동일한 응답 검증 helper를 사용해야 함"
    assert "showOutboundRetry" in cancel_fn, "취소 실패도 재시도 UI를 표시해야 함"
    assert "cancelOutbound(lotNo)" in code, "취소 재시도 버튼은 동일 LOT의 cancelOutbound를 다시 호출해야 함"
