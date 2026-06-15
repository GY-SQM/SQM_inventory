# -*- coding: utf-8 -*-
"""B9 회귀 테스트 — Allocation export 후 수정본 재업로드 충돌을 편집 플래그로 구분한다."""
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
    next_def = re.search(r"\n(?:@router|def\s+)", code[match.end():])
    end = match.end() + next_def.start() if next_def else len(code)
    return code[match.start():end]


def test_export_marks_allocation_rows_as_exported_for_edit_when_supported():
    code = _read_alloc_api()
    export_fn = _function_block(code, "export_allocation_excel")

    assert "def _mark_allocation_exported_for_edit" in code, "export 편집 플래그 helper가 필요함"
    assert "EXPORTED_FOR_EDIT" in code, "편집용 export workflow_status 값이 필요함"
    assert "export_edit_flag" in export_fn, "export 응답 data에 편집 플래그 적용 결과가 필요함"
    assert "_mark_allocation_exported_for_edit" in export_fn, "export 후 원본 행에 편집 플래그를 기록해야 함"


def test_export_excel_contains_reupload_guidance_columns():
    code = _read_alloc_api()
    export_fn = _function_block(code, "export_allocation_excel")

    assert "편집상태" in export_fn, "Excel에 편집상태 컬럼이 필요함"
    assert "재업로드 안내" in export_fn, "Excel에 재업로드 안내 컬럼이 필요함"
    assert "수정본 재업로드 전" in export_fn, "사용자에게 reset/초기화 필요성을 명시해야 함"


def test_duplicate_error_distinguishes_exported_edit_reupload():
    code = _read_alloc_api()
    import_fn = _function_block(code, "bulk_import_allocation")

    assert "_detect_export_edit_duplicate" in code, "export 편집본 중복 감지 helper가 필요함"
    assert "EDIT_EXPORT_DUPLICATE" in import_fn, "export 편집본 재업로드 전용 error_code가 필요함"
    assert "reset-all" in import_fn or "전체 초기화" in import_fn, "재업로드 충돌 시 초기화/편집 절차 안내가 필요함"
