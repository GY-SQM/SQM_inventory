# -*- coding: utf-8 -*-
"""회귀 테스트 — audit-report 🟡 #1 PG_PASSWORD 기본값 정리.

config.py: PG_PASSWORD 기본값 'postgres' → '' 로 변경.
- SQM 기본 운영은 SQLite → PG_PASSWORD가 실제로 사용되지 않음
- PostgreSQL 전환 시 SQM_PG_PASSWORD 환경변수 **명시적** 설정이 강제됨
- 빈 비번으로 psycopg2 시도 → 연결 실패 → 명확한 에러
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PY = os.path.join(ROOT, "config.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 정적 분석 (코드 패턴)
# ---------------------------------------------------------------------------

def test_audit_y1_config_no_default_postgres_password():
    """audit 🟡 #1: config.py의 PG_PASSWORD 기본값이 'postgres'면 안 됨."""
    code = _read(CONFIG_PY)
    m = re.search(
        r"PG_PASSWORD\s*=\s*os\.environ\.get\(\s*['\"]SQM_PG_PASSWORD['\"]\s*,\s*['\"]([^'\"]*)['\"]\s*\)",
        code,
    )
    assert m, "PG_PASSWORD = os.environ.get('SQM_PG_PASSWORD', ...) 패턴 못 찾음"
    default = m.group(1)
    assert default != "postgres", (
        f"PG_PASSWORD 기본값이 여전히 'postgres' — audit 🟡 #1 미해결"
    )
    assert default == "", (
        f"PG_PASSWORD 기본값이 '{default}' (기대값: '' 빈 문자열) — audit 정책과 다름"
    )


def test_audit_y1_config_has_audit_comment():
    """audit 🟡 #1: config.py에 audit 식별 주석이 있어야 함 (왜 빈 문자열인지 명시)."""
    code = _read(CONFIG_PY)
    assert "audit-report.md" in code, (
        "config.py에 audit-report.md 참조 주석 누락"
    )
    assert "🟡" in code, "config.py에 audit 🟡 #1 식별자 누락"


# ---------------------------------------------------------------------------
# in-process 검증 (실제 환경변수 동작)
# ---------------------------------------------------------------------------

def _import_config_with_env(env_overrides: dict = None):
    """config 모듈을 fresh state로 import (캐시 우회)."""
    saved_env = {}
    if env_overrides:
        for k, v in env_overrides.items():
            saved_env[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    # 캐시 제거
    for mod_name in list(sys.modules):
        if mod_name == "config" or mod_name.startswith("config."):
            del sys.modules[mod_name]
    if "core.config" in sys.modules or "core" in sys.modules:
        for mod_name in list(sys.modules):
            if mod_name == "core.config" or mod_name == "core":
                del sys.modules[mod_name]
    sys.path.insert(0, ROOT)
    import config
    # 환경 복원
    for k, v in saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return config


def test_audit_y1_default_empty_when_no_env():
    """audit 🟡 #1: SQM_PG_PASSWORD 미설정 시 PG_PASSWORD = ''."""
    cfg = _import_config_with_env({"SQM_PG_PASSWORD": None})
    assert cfg.PG_PASSWORD == "", (
        f"환경변수 미설정 시 PG_PASSWORD={cfg.PG_PASSWORD!r}, 기대값 ''"
    )


def test_audit_y1_explicit_env_value_used():
    """audit 🟡 #1: SQM_PG_PASSWORD 명시 설정 시 그 값 사용."""
    cfg = _import_config_with_env({"SQM_PG_PASSWORD": "my_secret_123"})
    assert cfg.PG_PASSWORD == "my_secret_123", (
        f"환경변수 설정값 무시됨: PG_PASSWORD={cfg.PG_PASSWORD!r}"
    )


def test_audit_y1_pg_connection_string_handles_empty_password():
    """audit 🟡 #1: get_pg_connection_string()이 빈 비번에서도 호출 가능해야 함 (에러 안 남)."""
    cfg = _import_config_with_env({"SQM_PG_PASSWORD": None})
    try:
        url = cfg.get_pg_connection_string()
    except Exception as e:
        raise AssertionError(f"get_pg_connection_string() 예외: {e}")
    # URL은 host/user/db 정보를 포함해야 함 (비번 없어도)
    assert "postgresql://" in url, f"PG 연결 문자열 형식 이상: {url}"
    assert cfg.PG_HOST in url, f"PG_HOST가 URL에 없음: {url}"
