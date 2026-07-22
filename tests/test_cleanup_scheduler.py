# -*- coding: utf-8 -*-
"""
tests/test_cleanup_scheduler.py
===============================
SQM v9.0.6 — audit_log 자동 정리 스케줄러 등록 회귀 테스트

검증:
    - tools/cleanup_audit_job.py: 실행 가능, JSON 출력, days 인자 처리
    - tools/install_cleanup_scheduler.ps1: schtasks /Create 라인 포함
    - tools/uninstall_cleanup_scheduler.ps1: schtasks /Delete 라인 포함
    - tools/cleanup_audit_job.py가 core.db_allowed의 cleanup_audit를 호출
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


# ── job 스크립트 실행 가능 ────────────────────────────────

def test_cs01_job_script_exists():
    """cleanup_audit_job.py 존재."""
    p = TOOLS / "cleanup_audit_job.py"
    assert p.exists(), f"job 스크립트 누락: {p}"
    assert p.stat().st_size > 100, "job 스크립트가 너무 짧음"


def test_cs02_job_script_runs_no_arg():
    """days 인자 없이 실행 → JSON 한 줄, exit 0."""
    result = subprocess.run(
        [sys.executable, str(TOOLS / "cleanup_audit_job.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, f"exit {result.returncode}\nstderr: {result.stderr}"
    out = result.stdout.strip()
    assert out, "stdout 비어있음"
    parsed = json.loads(out)
    assert "ok" in parsed
    assert "data" in parsed
    assert "deleted" in parsed["data"]
    # days 인자 없이 실행 → 기본 30일
    assert parsed["data"]["days"] == 30


def test_cs03_job_script_days_arg():
    """days=7 인자 전달 → data.days=7."""
    result = subprocess.run(
        [sys.executable, str(TOOLS / "cleanup_audit_job.py"), "7"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=str(ROOT),
    )
    assert result.returncode == 0
    parsed = json.loads(result.stdout.strip())
    assert parsed["data"]["days"] == 7


def test_cs04_job_script_days_zero_noop():
    """days=0 → no-op (cleanup_audit 자체가 silent return)."""
    result = subprocess.run(
        [sys.executable, str(TOOLS / "cleanup_audit_job.py"), "0"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=str(ROOT),
    )
    assert result.returncode == 0
    # days=0이면 cleanup_audit는 0 반환, ok=True
    parsed = json.loads(result.stdout.strip())
    assert parsed["data"]["days"] == 0
    assert parsed["data"]["deleted"] == 0


def test_cs05_job_script_invalid_days():
    """잘못된 days 인자 → exit 0 (silent), error 또는 기본값."""
    result = subprocess.run(
        [sys.executable, str(TOOLS / "cleanup_audit_job.py"), "notanumber"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=str(ROOT),
    )
    # parse 실패 시 error JSON 출력 + exit 0
    assert result.returncode == 0
    parsed = json.loads(result.stdout.strip())
    assert parsed["ok"] is False


def test_cs06_job_calls_cleanup_audit():
    """cleanup_audit_job.py가 core.db_allowed.cleanup_audit를 호출."""
    src = (TOOLS / "cleanup_audit_job.py").read_text(encoding="utf-8")
    assert "from core.db_allowed import cleanup_audit" in src
    assert "cleanup_audit(days=days)" in src


# ── install / uninstall PowerShell ───────────────────────

def test_cs10_install_ps1_exists():
    """install_cleanup_scheduler.ps1 존재."""
    p = TOOLS / "install_cleanup_scheduler.ps1"
    assert p.exists()
    assert p.stat().st_size > 200


def test_cs11_install_ps1_has_schtasks_create():
    """install ps1이 schtasks /Create 명령을 포함."""
    src = (TOOLS / "install_cleanup_scheduler.ps1").read_text(encoding="utf-8")
    assert "schtasks" in src
    assert "/Create" in src
    assert "cleanup_audit_job.py" in src


def test_cs12_install_ps1_uses_weekly_schedule():
    """install ps1이 주간 스케줄 (/SC WEEKLY) 사용."""
    src = (TOOLS / "install_cleanup_scheduler.ps1").read_text(encoding="utf-8")
    assert "/SC" in src
    assert "WEEKLY" in src


def test_cs13_install_ps1_idempotent():
    """install ps1이 기존 작업 제거 후 재등록 (idempotent)."""
    src = (TOOLS / "install_cleanup_scheduler.ps1").read_text(encoding="utf-8")
    # /Query → /Delete → /Create 순서
    assert "/Query" in src
    assert "/Delete" in src
    assert "/Create" in src


def test_cs14_install_ps1_env_overrides():
    """SCHEDULE_DAY, SCHEDULE_TIME, DAYS 환경변수 override 지원."""
    src = (TOOLS / "install_cleanup_scheduler.ps1").read_text(encoding="utf-8")
    for var in ("SCHEDULE_DAY", "SCHEDULE_TIME", "DAYS", "PYTHON_EXE"):
        assert f"env:{var}" in src or f"$env:{var}" in src, f"env var {var} 미지원"


def test_cs20_uninstall_ps1_exists():
    """uninstall_cleanup_scheduler.ps1 존재."""
    p = TOOLS / "uninstall_cleanup_scheduler.ps1"
    assert p.exists()


def test_cs21_uninstall_ps1_has_schtasks_delete():
    """uninstall ps1이 schtasks /Delete 명령 포함."""
    src = (TOOLS / "uninstall_cleanup_scheduler.ps1").read_text(encoding="utf-8")
    assert "schtasks" in src
    assert "/Delete" in src


def test_cs22_uninstall_ps1_skip_if_missing():
    """uninstall ps1은 미등록 시 no-op (skip 메시지)."""
    src = (TOOLS / "uninstall_cleanup_scheduler.ps1").read_text(encoding="utf-8")
    # 미등록 케이스 메시지
    assert "skip" in src.lower() or "Skip" in src


# ── 태스크명 일관성 ─────────────────────────────────────

def test_cs30_task_name_consistent():
    """install과 uninstall이 같은 태스크명 사용."""
    a = (TOOLS / "install_cleanup_scheduler.ps1").read_text(encoding="utf-8")
    b = (TOOLS / "uninstall_cleanup_scheduler.ps1").read_text(encoding="utf-8")
    assert "SQM Audit Cleanup" in a
    assert "SQM Audit Cleanup" in b
