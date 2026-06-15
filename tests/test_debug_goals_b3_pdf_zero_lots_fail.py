# -*- coding: utf-8 -*-
"""B3 회귀 테스트 — PDF 파싱 0건을 성공으로 반환하지 않는다."""
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


def test_pdf_inbound_rejects_zero_lot_parse_before_success_response():
    code = _read_inbound()
    fn = _function_block(code, "pdf_inbound")

    assert "PDF_PARSE_ZERO_LOTS" in fn, "파싱 0건 전용 오류 코드가 필요함"
    assert "lots_total == 0" in fn or "lots_total <= 0" in fn, "성공 응답 전에 lots_total 0건을 검사해야 함"
    assert "파싱된 LOT이 없습니다" in fn or "0 lots" in fn, "0건 사유를 사용자에게 명확히 알려야 함"

    zero_pos = fn.index("PDF_PARSE_ZERO_LOTS")
    success_pos = fn.index('"ok": True')
    assert zero_pos < success_pos, "0건 차단 로직은 ok:true 성공 응답보다 먼저 실행되어야 함"


def test_pdf_inbound_zero_lot_response_is_not_ok_true_saved_zero():
    code = _read_inbound()
    fn = _function_block(code, "pdf_inbound")

    zero_block_match = re.search(r'"ok": False,[\s\S]{0,1200}?PDF_PARSE_ZERO_LOTS[\s\S]{0,700}?"saved_count": 0', fn)
    assert zero_block_match, "PDF_PARSE_ZERO_LOTS 응답 블록을 찾지 못함"
    zero_block = zero_block_match.group(0)

    assert '"ok": False' in zero_block, "파싱 0건은 ok:false여야 함"
    assert '"success": False' in zero_block, "파싱 0건은 success:false여야 함"
    assert '"saved_count": 0' in zero_block, "0건 응답에는 saved_count=0을 명시해야 함"
