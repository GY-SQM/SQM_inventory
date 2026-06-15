# -*- coding: utf-8 -*-
"""B2 회귀 테스트 — PDF 입고가 PENDING 저장 후 다음 단계를 명시한다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOUND_PY = os.path.join(ROOT, "backend", "api", "inbound.py")


def _read_inbound() -> str:
    with open(INBOUND_PY, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\):", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\n(?:async\s+)?def\s+|\n@router\.", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_pdf_inbound_response_declares_pending_status_and_confirm_next_step():
    code = _read_inbound()
    fn = _function_block(code, "pdf_inbound")

    assert 'lot_data["status"] = "PENDING"' in fn, "PDF 입고는 PENDING으로 저장되는 정책을 유지해야 함"
    assert "requires_inbound_confirm" in fn, "응답 data에 입고확정 필요 여부를 명시해야 함"
    assert "saved_status" in fn and "PENDING" in fn, "응답 data에 저장 상태 PENDING을 명시해야 함"
    assert "next_step" in fn, "응답 data에 다음 단계 안내가 필요함"
    assert "Pending" in fn or "PENDING" in fn, "다음 단계 안내에 Pending 탭/상태가 보여야 함"
    assert "/api/inbound/confirm/{lot_no}" in fn, "응답 data에 LOT별 입고확정 API 템플릿을 제공해야 함"


def test_pdf_inbound_success_message_mentions_manual_confirm_when_saved_pending():
    code = _read_inbound()
    fn = _function_block(code, "pdf_inbound")

    message_match = re.search(r'"message"\s*:\s*\([\s\S]*?\),', fn)
    assert message_match, "pdf_inbound 성공 응답 message 블록을 찾지 못함"
    message_block = message_match.group(0)
    assert "입고확정" in message_block or "Pending" in message_block or "PENDING" in message_block, (
        "PDF 저장 성공 message가 PENDING 저장 후 입고확정 필요성을 안내해야 함"
    )
