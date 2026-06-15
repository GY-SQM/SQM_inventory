# -*- coding: utf-8 -*-
"""A4 회귀 테스트 — api-client가 빈/204 응답을 {} 정상 데이터로 오인하지 않는다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_CLIENT = os.path.join(ROOT, "frontend", "js", "api-client.js")


def _read_api_client() -> str:
    with open(API_CLIENT, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _compact(code: str) -> str:
    return re.sub(r"\s+", "", code)


def test_api_client_does_not_convert_json_parse_failure_to_empty_success_object():
    code = _read_api_client()

    assert not re.search(r"catch\s*\{\s*return\s*\{\s*\}\s*;?\s*\}", code), (
        "api-client.js가 res.json() 실패/빈 응답을 catch { return {}; } 로 "
        "정상 데이터처럼 반환하고 있음"
    )
    assert "return await res.json()" not in code or "return {}" not in code, (
        "res.json() 실패 시 {}로 대체하는 패턴은 상위 로직이 성공으로 오인할 수 있음"
    )


def test_api_client_has_explicit_204_no_content_handling_before_json_parse():
    code = _read_api_client()

    parse_pos = code.find("JSON.parse")
    status_204_matches = list(
        re.finditer(r"(res\.status\s*={2,3}\s*204|204\s*={2,3}\s*res\.status)", code)
    )

    assert status_204_matches, "HTTP 204 No Content 응답을 명시적으로 처리하는 분기가 없음"
    assert parse_pos == -1 or status_204_matches[0].start() < parse_pos, (
        "204 응답 처리는 JSON.parse 호출 전에 이루어져야 함"
    )


def test_api_client_empty_body_is_detected_from_text_not_silently_swallowed():
    code = _read_api_client()
    compact = _compact(code)

    assert "res.text(" in code, "빈 body를 구분하려면 성공 응답 body를 res.text()로 먼저 읽어야 함"
    assert "JSON.parse" in code, "빈 body 검사 후 JSON.parse로 JSON 파싱 실패를 명시 처리해야 함"
    assert ".trim()" in compact and "emptyresponse" in compact.lower(), (
        "빈 응답 body를 명시적으로 검사하고 empty response 오류로 처리해야 함"
    )


def test_api_client_business_failure_body_is_promoted_to_api_error_before_success_sound():
    code = _read_api_client()
    compact = _compact(code)

    assert "data.ok===false" in compact or "data.success===false" in compact, (
        "HTTP 2xx라도 ok:false/success:false 업무 실패 응답은 성공으로 반환하면 안 됨"
    )
    assert "thrownewApiError" in compact, "업무 실패/빈 응답은 ApiError로 승격해야 함"

    play_pos = compact.find("playSuccess()")
    failure_pos_candidates = [
        pos for pos in [compact.find("data.ok===false"), compact.find("data.success===false")]
        if pos != -1
    ]
    assert failure_pos_candidates and min(failure_pos_candidates) < play_pos, (
        "playSuccess()는 업무 실패 응답 검증 후에만 실행되어야 함"
    )


def test_api_client_no_content_result_has_explicit_success_and_status():
    code = _read_api_client()
    compact = _compact(code)

    assert "status:res.status" in compact, "204 명시 응답 객체에 HTTP status를 포함해야 함"
    assert "success:true" in compact and "ok:true" in compact, (
        "204 명시 응답 객체에는 ok:true/success:true가 있어야 상위가 상태를 오인하지 않음"
    )
    assert "noContent:true" in compact or "empty:true" in compact, (
        "204 명시 응답 객체에는 noContent:true 또는 empty:true가 있어야 함"
    )
