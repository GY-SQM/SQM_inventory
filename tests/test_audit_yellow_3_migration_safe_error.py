# -*- coding: utf-8 -*-
"""회귀 테스트 — audit 🟡 #3 STRIDE I 마이그레이션 (#1, 2026-07-21).

backend/ 8개 파일에서 `raise HTTPException(500, str(e))` 65건을
`raise safe_internal_error(e, op="API 요청")` 로 일괄 변환.

이 테스트는:
  - 0건 검증: `HTTPException(500, str(e))` 패턴이 코드에 0건
  - import 검증: 모든 변환된 파일에 `safe_internal_error` import 존재
  - 호출 검증: `safe_internal_error(e, op=...)` 호출 패턴 확인
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = [
    "backend/api/actions2.py",
    "backend/api/actions3.py",
    "backend/api/allocation_api.py",
    "backend/api/carriers.py",
    "backend/api/inbound.py",
    "backend/api/inventory_api.py",
    "backend/api/settings.py",
    "backend/api/__init__.py",
]


def _read(rel_path: str) -> str:
    with open(os.path.join(ROOT, rel_path), encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 0건 검증
# ---------------------------------------------------------------------------

def test_audit_y3_migration_zero_old_pattern():
    """STRIDE I: `raise HTTPException(500, str(e))` 패턴이 0건이어야 함."""
    total = 0
    for rel in TARGETS:
        code = _read(rel)
        n = len(re.findall(
            r"raise\s+HTTPException\(500,\s*str\(e\)\)",
            code,
        ))
        if n > 0:
            total += n
            raise AssertionError(f"{rel}: {n}건의 구 패턴 잔존")
    assert total == 0, f"구 패턴 잔존: {total}건"


# ---------------------------------------------------------------------------
# import 검증
# ---------------------------------------------------------------------------

def test_audit_y3_migration_safe_error_imported_in_all_files():
    """STRIDE I: 8개 변환 파일 모두 `from core.error_helpers import safe_internal_error`."""
    for rel in TARGETS:
        code = _read(rel)
        assert "from core.error_helpers import safe_internal_error" in code, (
            f"{rel}: safe_internal_error import 누락"
        )


# ---------------------------------------------------------------------------
# 호출 패턴 검증
# ---------------------------------------------------------------------------

def test_audit_y3_migration_safe_error_used_in_all_files():
    """STRIDE I: 8개 파일 모두 safe_internal_error(e, op=...) 호출 존재."""
    for rel in TARGETS:
        code = _read(rel)
        # safe_internal_error(e, op=...) 패턴 (op="..." 또는 op='...')
        n = len(re.findall(
            r"safe_internal_error\s*\(\s*e\s*,\s*op\s*=",
            code,
        ))
        assert n > 0, f"{rel}: safe_internal_error(e, op=...) 호출 누락"


# ---------------------------------------------------------------------------
# 총 마이그레이션 건수 검증 (65건)
# ---------------------------------------------------------------------------

def test_audit_y3_migration_total_count_65():
    """STRIDE I: 총 65건의 safe_internal_error 호출이 있어야 함."""
    total = 0
    for rel in TARGETS:
        code = _read(rel)
        n = len(re.findall(
            r"safe_internal_error\s*\(\s*e\s*,\s*op\s*=",
            code,
        ))
        total += n
    assert total == 65, (
        f"총 변환 건수 {total} (기대값 65) — 일부 누락 또는 중복 변환"
    )


# ---------------------------------------------------------------------------
# 동작 검증 (in-process)
# ---------------------------------------------------------------------------

def test_audit_y3_migration_safe_error_still_works():
    """STRIDE I: 변환된 코드도 safe_internal_error가 정상 동작 (회귀 없음)."""
    import sys
    sys.path.insert(0, ROOT)
    from fastapi import HTTPException
    from core.error_helpers import safe_internal_error

    e = RuntimeError("SECRET_TEST")
    http_exc = safe_internal_error(e, op="API 요청")
    assert isinstance(http_exc, HTTPException)
    assert http_exc.status_code == 500
    assert "SECRET_TEST" not in str(http_exc.detail), (
        "변환 후에도 str(e) 노출 — STRIDE I 위반"
    )
    assert "ref:" in str(http_exc.detail)
