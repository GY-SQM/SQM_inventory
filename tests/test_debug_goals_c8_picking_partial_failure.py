# -*- coding: utf-8 -*-
"""C8 회귀 테스트 — 피킹리스트 반영 실패 시 부분결과/경고/아이템을 반환한다."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTBOUND_API = os.path.join(ROOT, "backend", "api", "outbound_api.py")


def _read_outbound_api() -> str:
    with open(OUTBOUND_API, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _function_block(code: str, name: str) -> str:
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\([^)]*\).*?:", code)
    assert match, f"{name} 함수를 찾지 못함"
    next_def = re.search(r"\n\s*@router|\nclass\s+", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_picking_list_pdf_failure_returns_partial_items_and_details():
    code = _read_outbound_api()
    fn = _function_block(code, "picking_list_pdf")
    failure_pos = fn.index('"Picking List 반영 실패"')
    data_pos = fn.rfind('"data"', 0, failure_pos)
    failure_block = fn[data_pos:failure_pos + 900]

    assert '"items"' in failure_block, "반영 실패 시 파싱된 items 일부를 반환해야 함"
    assert '"details"' in failure_block, "반영 실패 시 행별/LOT별 details를 반환해야 함"
    assert '"allocation_validation"' in failure_block, "검증 결과도 실패 응답에 포함해야 함"
    assert '"partial_result"' in failure_block, "부분 결과 플래그/객체가 필요함"


def test_picking_list_excel_failure_returns_partial_items_and_details():
    code = _read_outbound_api()
    fn = _function_block(code, "picking_import_excel")
    failure_pos = fn.index('"Picking List 반영 실패"')
    data_pos = fn.rfind('"data"', 0, failure_pos)
    failure_block = fn[data_pos:failure_pos + 900]

    assert '"items"' in failure_block, "Excel 반영 실패 시 파싱된 items 일부를 반환해야 함"
    assert '"details"' in failure_block, "Excel 반영 실패 시 details를 반환해야 함"
    assert '"partial_result"' in failure_block, "Excel 실패 응답도 부분 결과를 명시해야 함"
