# -*- coding: utf-8 -*-
"""
tests/test_lint_db_hardcoding.py
==================================
SQM v9.0.0 — Phase 2 Step 3: lint_db_hardcoding 도구 자체 검증

테스트:
    - 도구 모듈 import 가능
    - find_hardcoding() 기본 동작
    - should_exclude() 정상
    - main() 실행 가능 (CI 통합 검증)
"""
import subprocess
import sys
from pathlib import Path

import pytest

# 도구 import (경로 추가 필요)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from lint_db_hardcoding import (
    find_hardcoding,
    should_exclude,
    TARGETS,
    MIN_ID_LEN,
)


# ── 기본 동작 ─────────────────────────────────────────────

def test_l01_module_imports():
    """도구 모듈이 import 가능."""
    assert len(TARGETS) > 0
    assert MIN_ID_LEN >= 3


def test_l02_targets_not_empty():
    """대상 식별자가 충분히 있음 (10개 이상)."""
    assert len(TARGETS) >= 10


def test_l03_should_exclude_db_allowed():
    """core/db_allowed.py는 exclude."""
    db_allowed = ROOT / "core" / "db_allowed.py"
    assert should_exclude(db_allowed) is True


def test_l04_should_exclude_tests_dir():
    """tests/ 는 exclude."""
    test_file = ROOT / "tests" / "test_foo.py"
    assert should_exclude(test_file) is True


def test_l05_should_exclude_pycache():
    """__pycache__ 는 exclude."""
    pycache = ROOT / "__pycache__" / "foo.pyc"
    assert should_exclude(pycache) is True


def test_l06_should_not_exclude_backend():
    """backend/ 파일은 exclude 안 됨."""
    backend_file = ROOT / "backend" / "api" / "inbound.py"
    assert should_exclude(backend_file) is False


# ── find_hardcoding ─────────────────────────────────────

def test_l07_find_hardcoding_real_backend(tmp_path):
    """실제 backend/ 검사 — 1개 이상의 hit 발견 (방대한 SQL 사용)."""
    hits = find_hardcoding(ROOT / "backend")
    assert len(hits) > 0


def test_l08_find_hardcoding_empty_dir(tmp_path):
    """빈 디렉토리 → hits 0건."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    hits = find_hardcoding(empty_dir)
    assert hits == []


def test_l09_find_hardcoding_synthetic_file(tmp_path):
    """합성 파일에 식별자 → 1개 이상 hit."""
    test_file = tmp_path / "test_sample.py"
    test_file.write_text('TABLE_NAME = "inventory"\n', encoding="utf-8")
    hits = find_hardcoding(tmp_path)
    assert len(hits) >= 1


# ── main() 실행 가능 ─────────────────────────────────────

def test_l10_main_runs_on_backend():
    """도구가 backend/ 에서 실행 가능 (CI 통합 검증)."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "lint_db_hardcoding.py"), "backend"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    # exit 0 (이상적) 또는 exit 1 (hits 발견) 둘 다 정상
    assert result.returncode in (0, 1), f"예상치 못한 exit code: {result.returncode}\nstderr: {result.stderr}"
    # stdout에 [INFO] 또는 [WARN] 헤더 있어야 함
    assert "[INFO]" in result.stdout or "[OK]" in result.stdout or "[WARN]" in result.stdout
