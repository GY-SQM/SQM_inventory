# -*- coding: utf-8 -*-
"""
tests/test_lint_sql_context.py
==============================
SQM v9.0.6 — narrow SQL context lint 회귀 테스트

검증:
    - 도구 모듈 import 가능
    - find_narrow_sql_exec()가 cur.execute/conn.execute의 f-string만 잡음
    - _is_dangerous_sql_arg() 정확
    - _is_exec_call() 정확
    - _fstring_only_safe_placeholders() 정확
    - partition_by_baseline() 분류 정확
    - main() 실행 가능 (CI 통합)
    - baseline 적용 시 exit 0
    - baseline에 없는 새 패턴 추가 시 exit 1
"""
import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from lint_sql_context import (
    find_narrow_sql_exec,
    load_baseline,
    partition_by_baseline,
    should_exclude,
    _is_dangerous_sql_arg,
    _is_exec_call,
    _fstring_only_safe_placeholders,
    BASELINE_PATH,
)


# ── 기본 동작 ──────────────────────────────────────────

def test_lsc01_module_imports():
    """도구 모듈 import 가능 + baseline 파일 존재."""
    assert BASELINE_PATH.exists(), f"baseline 누락: {BASELINE_PATH}"


def test_lsc02_baseline_is_valid_json():
    """baseline 파일이 유효한 JSON."""
    baseline = load_baseline()
    assert isinstance(baseline, dict)
    # v9.0.6 첫 등록 시 11건 이상이어야 함
    assert len(baseline) >= 10, f"baseline에 등록된 항목이 너무 적음: {len(baseline)}건"


def test_lsc03_baseline_keys_format():
    """baseline 키가 'file.py:line' 형식 (메타 키 _* 제외)."""
    baseline = load_baseline()
    for k in baseline:
        if k.startswith("_"):
            continue  # 메타 키 (_comment 등)
        assert ":" in k, f"잘못된 키 형식: {k}"
        file_part, line_part = k.rsplit(":", 1)
        assert file_part.endswith(".py"), f"파일명이 .py가 아님: {file_part}"
        assert line_part.isdigit(), f"라인 번호가 숫자가 아님: {line_part}"


# ── _is_exec_call 정확성 ───────────────────────────────

def test_lsc10_is_exec_call_cur_execute():
    """cur.execute(...) → True."""
    code = "cur.execute(sql)"
    tree = ast.parse(code)
    call = tree.body[0].value
    assert _is_exec_call(call) is True


def test_lsc11_is_exec_call_con_executescript():
    """con.executescript(sql) → True."""
    code = "con.executescript(sql)"
    tree = ast.parse(code)
    call = tree.body[0].value
    assert _is_exec_call(call) is True


def test_lsc12_is_exec_call_not_execute_method():
    """cur.fetchone() → False (execute가 아님)."""
    code = "cur.fetchone()"
    tree = ast.parse(code)
    call = tree.body[0].value
    assert _is_exec_call(call) is False


def test_lsc13_is_exec_call_other_receiver():
    """foo.execute(sql) → False (cur/conn/cursor/db/con이 아님)."""
    code = "foo.execute(sql)"
    tree = ast.parse(code)
    call = tree.body[0].value
    assert _is_exec_call(call) is False


# ── _is_dangerous_sql_arg 정확성 ───────────────────────

def test_lsc20_is_dangerous_fstring():
    """f-string → True."""
    code = 'cur.execute(f"SELECT * FROM {t}")'
    tree = ast.parse(code)
    arg = tree.body[0].value.args[0]
    assert _is_dangerous_sql_arg(arg) is True


def test_lsc21_is_dangerous_string_concat():
    """string concat → True."""
    code = 'cur.execute("SELECT " + x + " FROM t")'
    tree = ast.parse(code)
    arg = tree.body[0].value.args[0]
    assert _is_dangerous_sql_arg(arg) is True


def test_lsc22_is_dangerous_constant_string():
    """상수 문자열 → False."""
    code = 'cur.execute("SELECT * FROM t")'
    tree = ast.parse(code)
    arg = tree.body[0].value.args[0]
    assert _is_dangerous_sql_arg(arg) is False


def test_lsc23_is_dangerous_fstring_safe_ph():
    """f-string with safe placeholder (ph) → False."""
    code = 'cur.execute(f"SELECT * FROM t WHERE x IN ({ph})", lots)'
    tree = ast.parse(code)
    arg = tree.body[0].value.args[0]
    assert _is_dangerous_sql_arg(arg) is False


# ── _fstring_only_safe_placeholders 정확성 ─────────────

def test_lsc30_safe_only_ph():
    """f-string with {ph} only → True (safe)."""
    code = 'f"SELECT * FROM t WHERE id IN ({ph})"'
    tree = ast.parse(code)
    node = tree.body[0].value
    assert _fstring_only_safe_placeholders(node) is True


def test_lsc31_safe_with_set_clause():
    """f-string with {sets} → True (safe)."""
    code = 'f"UPDATE t SET {sets} WHERE id=?"'
    tree = ast.parse(code)
    node = tree.body[0].value
    assert _fstring_only_safe_placeholders(node) is True


def test_lsc32_unsafe_with_unknown_var():
    """f-string with {user_input} → False (unsafe)."""
    code = 'f"SELECT * FROM t WHERE name=\'{user_input}\'"'
    tree = ast.parse(code)
    node = tree.body[0].value
    assert _fstring_only_safe_placeholders(node) is False


def test_lsc33_safe_with_join_call():
    """f-string with {','.join('?'*N)} → True (.join builder)."""
    code = "f'SELECT * FROM t WHERE id IN ({\",\".join(\"?\"*N)})'"
    tree = ast.parse(code)
    node = tree.body[0].value
    assert _fstring_only_safe_placeholders(node) is True


def test_lsc34_unsafe_with_unknown_call():
    """f-string with {str(x).format(...)} → False."""
    code = 'f"SELECT {build_clause(x)}"'
    tree = ast.parse(code)
    node = tree.body[0].value
    # build_clause is Call with attr 'build_clause' (not 'join')
    assert _fstring_only_safe_placeholders(node) is False


# ── find_narrow_sql_exec 정확성 ────────────────────────

def test_lsc40_find_in_synthetic_dir(tmp_path):
    """합성 디렉토리에서 f-string execute를 정확히 잡음."""
    src1 = tmp_path / "a.py"
    src1.write_text(
        'cur.execute("SELECT * FROM t")\n'  # not dangerous
        'cur.execute(f"SELECT * FROM {x}")\n'  # dangerous
        'cur.fetchone()\n'  # not execute
        'con.execute("INSERT INTO t VALUES (" + str(x) + ")")\n',  # dangerous concat
        encoding="utf-8",
    )
    findings = find_narrow_sql_exec(tmp_path)
    # 2건 dangerous (f-string + concat)
    assert len(findings) == 2


def test_lsc41_find_excludes_tools_tests(tmp_path):
    """tools/, tests/ 디렉토리는 자동 exclude (rglob이 target_dir 한정이지만
    실제 디렉토리 구조에서 exclude)."""
    # tmp_path는 별도 디렉토리라서 core/tools/tests는 rglob에 안 잡힘
    # 단, should_exclude 검증으로 충분
    from pathlib import Path
    test_file = tmp_path / "_db_allowed.py"  # excluded by name
    test_file.write_text('cur.execute(f"SELECT * FROM {t}")', encoding="utf-8")
    # tmp_path는 tools/ 가 아니라서 exclude 안 됨 → 1건 발견
    findings = find_narrow_sql_exec(tmp_path)
    assert len(findings) == 1

    # 별도로 should_exclude 검증
    fake_tools = Path("/tools/something.py")
    assert should_exclude(fake_tools) is True


# ── partition_by_baseline 정확성 ──────────────────────

def test_lsc50_partition_baseline_matching(tmp_path):
    """baseline 매칭 / 미매칭 정확히 분류."""
    findings = [
        {"file": ROOT / "backend" / "api" / "inbound.py", "line": 100, "arg": "x"},
        {"file": ROOT / "backend" / "api" / "inbound.py", "line": 200, "arg": "y"},
        {"file": ROOT / "backend" / "api" / "queries.py", "line": 300, "arg": "z"},
    ]
    baseline = {
        "backend/api/inbound.py:100": "REVERT_MAP safe",
        # 200은 미등록
    }
    new, reviewed = partition_by_baseline(findings, baseline)
    assert len(new) == 2
    assert len(reviewed) == 1
    assert reviewed[0]["line"] == 100


# ── main() 실행 가능 (CI 통합) ────────────────────────

def test_lsc60_main_runs_on_backend_exit_0():
    """baseline 적용 시 main() exit 0."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "lint_sql_context.py"), "backend"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, f"예상 exit 0, 실제 {result.returncode}\nstderr: {result.stderr}\nstdout:\n{result.stdout[:500]}"
    assert "[REVIEWED]" in result.stdout


def test_lsc61_main_detects_new_finding(tmp_path):
    """baseline에 없는 새 패턴 추가 시 exit 1."""
    # ROOT 내부에 fake 디렉토리 만들어서 (relative_to 통과)
    import shutil
    fake_dir = ROOT / "_tmp_test_lint" / "fake_backend"
    if fake_dir.exists():
        shutil.rmtree(fake_dir.parent)
    fake_dir.mkdir(parents=True)
    try:
        src = fake_dir / "danger.py"
        src.write_text(
            'cur.execute(f"SELECT * FROM t WHERE name=\'{user_input}\'")\n',
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "lint_sql_context.py"), str(fake_dir)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        assert result.returncode == 1, f"예상 exit 1, 실제 {result.returncode}\nstdout: {result.stdout}"
        assert "[WARN]" in result.stdout
        assert "user_input" in result.stdout
    finally:
        shutil.rmtree(fake_dir.parent, ignore_errors=True)
