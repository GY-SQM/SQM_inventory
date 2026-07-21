# -*- coding: utf-8 -*-
"""회귀 테스트 — audit-report 🟡 #4 로그 회전 정책.

config_logging.py: 이미 RotatingFileHandler(LOG_MAX_SIZE_MB=10, LOG_BACKUP_COUNT=5) 적용됨.
main_webview.py:   2026-07-21 회전 정책 추가 (이전 FileHandler → RotatingFileHandler).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_LOGGING = os.path.join(ROOT, "config_logging.py")
MAIN_WEBVIEW = os.path.join(ROOT, "main_webview.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# config_logging.py — 회전 정책 상수/설정
# ---------------------------------------------------------------------------

def test_audit_y4_config_logging_has_backup_count():
    """audit 🟡 #4: config_logging.py에 LOG_BACKUP_COUNT >= 5 있어야 함."""
    code = _read(CONFIG_LOGGING)
    m = re.search(r"LOG_BACKUP_COUNT\s*=\s*(\d+)", code)
    assert m, "LOG_BACKUP_COUNT 상수 누락"
    n = int(m.group(1))
    assert n >= 5, f"LOG_BACKUP_COUNT={n} (<5) — audit 권고 미충족"


def test_audit_y4_config_logging_has_max_size():
    """audit 🟡 #4: LOG_MAX_SIZE_MB 합리적 크기 (10~50MB)."""
    code = _read(CONFIG_LOGGING)
    m = re.search(r"LOG_MAX_SIZE_MB\s*=\s*(\d+)", code)
    assert m, "LOG_MAX_SIZE_MB 상수 누락"
    n = int(m.group(1))
    assert 1 <= n <= 50, f"LOG_MAX_SIZE_MB={n} — 비합리적 크기"


def test_audit_y4_setup_logging_uses_rotating_handler():
    """audit 🟡 #4: setup_logging()이 RotatingFileHandler 사용해야 함."""
    code = _read(CONFIG_LOGGING)
    # setup_logging 함수 본문 안에 RotatingFileHandler 호출
    m = re.search(
        r"def\s+setup_logging\s*\([^)]*\):(.*?)(?=\ndef\s+|\Z)",
        code,
        re.DOTALL,
    )
    assert m, "setup_logging 함수 본문 못 찾음"
    body = m.group(1)
    assert "RotatingFileHandler" in body, (
        "setup_logging() 본문에 RotatingFileHandler 미사용 — 회전 없음"
    )
    assert "maxBytes" in body, "RotatingFileHandler에 maxBytes 미지정"
    assert "backupCount" in body, "RotatingFileHandler에 backupCount 미지정"


# ---------------------------------------------------------------------------
# main_webview.py — debug 로그 회전
# ---------------------------------------------------------------------------

def test_audit_y4_main_webview_uses_rotating_file_handler():
    """audit 🟡 #4: main_webview.py의 sqm_debug.log 핸들러가 RotatingFileHandler 여야 함."""
    code = _read(MAIN_WEBVIEW)
    # RotatingFileHandler 임포트 확인
    assert "from logging.handlers import RotatingFileHandler" in code, (
        "main_webview.py에 RotatingFileHandler 임포트 누락"
    )
    # LOG_PATH 정의 이후 영역 (충분히 큰 슬라이스) 에 RotatingFileHandler 호출
    file_h_section = code[code.find("LOG_PATH ="):][:3000]
    assert "RotatingFileHandler(" in file_h_section, (
        "main_webview.py LOG_PATH 영역에 RotatingFileHandler 호출 누락"
    )
    assert "maxBytes" in file_h_section, "maxBytes 미지정"
    assert "backupCount" in file_h_section, "backupCount 미지정"


def test_audit_y4_main_webview_max_size_reasonable():
    """audit 🟡 #4: main_webview.py의 회전 크기 1~50MB 범위 (10 * 1024 * 1024 형태)."""
    code = _read(MAIN_WEBVIEW)
    # maxBytes=10 * 1024 * 1024 형태 (곱셈 표현)
    m = re.search(
        r"maxBytes\s*=\s*(\d+)\s*\*\s*1024\s*\*\s*1024",
        code,
    )
    assert m, "main_webview.py의 maxBytes=N * 1024 * 1024 패턴 못 찾음"
    mb = int(m.group(1))
    assert 1 <= mb <= 50, f"maxBytes={mb}MB — 비합리적 크기 (1~50MB 범위 벗어남)"


def test_audit_y4_main_webview_backup_count_5():
    """audit 🟡 #4: main_webview.py의 backupCount=5 여야 함."""
    code = _read(MAIN_WEBVIEW)
    m = re.search(
        r"backupCount\s*=\s*(\d+)",
        code,
    )
    assert m, "main_webview.py의 backupCount 인자 못 찾음"
    n = int(m.group(1))
    assert n >= 5, f"main_webview.py backupCount={n} (<5) — audit 권고 미충족"


# ---------------------------------------------------------------------------
# in-process 검증 — config_logging 모듈 임포트 + 정책 점검
# ---------------------------------------------------------------------------

def test_audit_y4_config_logging_module_loads():
    """audit 🟡 #4: config_logging 모듈 정상 임포트 + 정책 상수 노출."""
    sys.path.insert(0, ROOT)
    import config_logging
    assert hasattr(config_logging, "LOG_MAX_SIZE_MB")
    assert hasattr(config_logging, "LOG_BACKUP_COUNT")
    assert hasattr(config_logging, "LOG_FILE")
    assert config_logging.LOG_BACKUP_COUNT >= 5
    assert config_logging.LOG_MAX_SIZE_MB <= 50
