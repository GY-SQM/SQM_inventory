# -*- coding: utf-8 -*-
"""B12 회귀 테스트 — Allocation AI 컬럼매핑 실패/키 미설정을 명시한다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOC_API = os.path.join(ROOT, "backend", "api", "allocation_api.py")


def _read_alloc_api() -> str:
    with open(ALLOC_API, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\).*?:", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\ndef\s+|\n@router", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_ai_mapping_records_explicit_unavailable_status_when_gemini_key_missing():
    code = _read_alloc_api()
    fn = _function_block(code, "_ai_match_columns")

    assert "AI_MAPPING_STATUS" in code, "AI 매핑 실패 원인을 보존하는 상태 객체가 필요함"
    assert "GEMINI_KEY_MISSING" in fn, "Gemini 키 미설정 전용 code가 필요함"
    assert "Gemini 키 미설정" in fn, "사용자에게 Gemini 키 미설정을 명시해야 함"
    assert "_set_ai_mapping_status" in fn, "AI 매핑 실패 원인을 상태로 기록해야 함"


def test_bulk_import_header_failure_message_includes_ai_mapping_status():
    code = _read_alloc_api()
    fn = _function_block(code, "bulk_import_allocation")

    assert "ai_mapping_status" in fn, "헤더 인식 실패 응답에 AI 매핑 상태를 포함해야 함"
    assert "_format_ai_mapping_failure_hint" in fn, "최종 오류 메시지에 AI 실패 사유 helper를 사용해야 함"
    assert "Gemini 키 미설정" in fn, "bulk import 오류 메시지에도 키 미설정 문구가 포함되어야 함"
    assert "AI_MAPPING_FAILED" in fn, "detail code로 AI 매핑 실패를 구분해야 함"


def test_ai_mapping_import_failure_also_has_user_visible_reason():
    code = _read_alloc_api()
    fn = _function_block(code, "_ai_match_columns")

    assert "GEMINI_UTILS_IMPORT_FAILED" in fn, "gemini_utils import 실패도 명시 code가 필요함"
    assert "Gemini 유틸 import 실패" in fn, "import 실패도 사용자/로그에 명확해야 함"
