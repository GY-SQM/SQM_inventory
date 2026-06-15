# -*- coding: utf-8 -*-
"""B8 회귀 테스트 — 반품입고 Excel LOT/PICKING 매칭 실패를 행별 사유로 반환한다."""
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARSER = os.path.join(ROOT, "features", "parsers", "return_inbound_parser.py")
ENGINE = os.path.join(ROOT, "features", "parsers", "return_inbound_engine.py")
INBOUND_API = os.path.join(ROOT, "backend", "api", "inbound.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\).*?:", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\ndef\s+|\nasync\s+def\s+|\nclass\s+", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_return_parser_preserves_excel_line_number_per_item():
    parser = _read(PARSER)
    assert '"line_no": int(idx) + 1' in parser, "파서 item에 Excel 행 번호 line_no를 포함해야 함"


def test_return_engine_adds_row_detail_when_lot_or_picking_not_matched():
    engine = _read(ENGINE)
    fn = _function_block(engine, "process_return_inbound")

    assert 'line_no = row.get("line_no")' in fn, "엔진이 parser의 line_no를 읽어야 함"
    assert "RETURN_MATCH_NOT_FOUND" in fn, "LOT/PICKING 미매칭 전용 fail_code가 필요함"
    assert 'result["details"].append' in fn, "실패 시에도 details에 행별 사유를 남겨야 함"
    assert '"line_no": line_no' in fn, "실패 detail에 line_no를 포함해야 함"
    assert '"lot_no": lot_no' in fn and '"picking_no": picking_no' in fn, "실패 detail에 LOT/PICKING 정보를 포함해야 함"
    assert '"matched": got' in fn and '"required": need' in fn, "필요/매칭 수량을 detail에 포함해야 함"


def test_return_excel_api_returns_failure_details_to_frontend():
    api = _read(INBOUND_API)
    fn = _function_block(api, "return_inbound_excel")

    assert '"details": result.get("details", [])' in fn, "실패 응답에 행별 details를 그대로 반환해야 함"
    assert "RETURN_FAILED" in fn, "반품 실패 코드는 유지되어야 함"
