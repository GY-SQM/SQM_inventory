# -*- coding: utf-8 -*-
"""회귀 테스트 — audit-report 🟡 #3 STRIDE I (정보노출) + D (서비스거부).

v8.8.5(2026-07-21):
  - core/error_helpers.py: safe_internal_error() — 5xx str(e) 노출 방지
  - core/upload_limits.py: check_upload_size() + UploadSizeLimitMiddleware
  - backend/api/__init__.py: UploadSizeLimitMiddleware 등록 (50MB)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERROR_HELPERS = os.path.join(ROOT, "core", "error_helpers.py")
UPLOAD_LIMITS = os.path.join(ROOT, "core", "upload_limits.py")
API_INIT = os.path.join(ROOT, "backend", "api", "__init__.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# STRIDE I — error_helpers.py 존재 + 동작
# ---------------------------------------------------------------------------

def test_stride_i_error_helpers_module_exists():
    """STRIDE I: core/error_helpers.py 모듈이 존재해야 함."""
    assert os.path.exists(ERROR_HELPERS), "core/error_helpers.py 누락"


def test_stride_i_safe_internal_error_function_exists():
    """STRIDE I: safe_internal_error() 함수 시그니처 확인."""
    code = _read(ERROR_HELPERS)
    m = re.search(
        r"def\s+safe_internal_error\s*\(\s*e[^)]*\)\s*->\s*HTTPException",
        code,
        re.DOTALL,
    )
    assert m, "safe_internal_error(e, ...) -> HTTPException 시그니처 누락"


def test_stride_i_safe_internal_error_hides_str_e():
    """STRIDE I: helper가 str(e)를 클라이언트에 노출하면 안 됨 (request_id만 노출)."""
    code = _read(ERROR_HELPERS)
    # detail에 str(e) 직접 노출 없음 (request_id만)
    m = re.search(r'detail=safe_msg', code)
    assert m, "detail=safe_msg 패턴 누락 — str(e) 노출 위험"
    # safe_msg 정의에 str(e) 없어야 함
    m2 = re.search(r'safe_msg\s*=\s*f["\'].*?\{e\}', code)
    assert not m2, "safe_msg에 {e} 직접 노출 — STRIDE I 위반"


def test_stride_i_safe_internal_error_logs_full_traceback():
    """STRIDE I: helper는 서버 로그에 전체 traceback 기록해야 함."""
    code = _read(ERROR_HELPERS)
    assert "logger.exception" in code, "logger.exception 호출 누락 (서버 로그 traceback)"


# ---------------------------------------------------------------------------
# STRIDE D — upload_limits.py + 미들웨어 등록
# ---------------------------------------------------------------------------

def test_stride_d_upload_limits_module_exists():
    """STRIDE D: core/upload_limits.py 모듈이 존재해야 함."""
    assert os.path.exists(UPLOAD_LIMITS), "core/upload_limits.py 누락"


def test_stride_d_max_upload_bytes_constant():
    """STRIDE D: MAX_UPLOAD_BYTES 상수 (50MB) 가 정의되어 있어야 함."""
    code = _read(UPLOAD_LIMITS)
    m = re.search(
        r"MAX_UPLOAD_BYTES\s*:\s*int\s*=\s*(\d+)\s*\*\s*1024\s*\*\s*1024",
        code,
    )
    assert m, "MAX_UPLOAD_BYTES = N * 1024 * 1024 형태 누락"
    mb = int(m.group(1))
    assert 1 <= mb <= 100, f"MAX_UPLOAD_BYTES={mb}MB — 비합리적 (1~100MB 범위)"


def test_stride_d_check_upload_size_function():
    """STRIDE D: check_upload_size() 함수가 정의되어 있어야 함."""
    code = _read(UPLOAD_LIMITS)
    m = re.search(
        r"def\s+check_upload_size\s*\([^)]*data\s*:\s*bytes[^)]*\)",
        code,
        re.DOTALL,
    )
    assert m, "check_upload_size(data: bytes, ...) 시그니처 누락"


def test_stride_d_middleware_class_defined():
    """STRIDE D: UploadSizeLimitMiddleware 클래스가 정의되어 있어야 함."""
    code = _read(UPLOAD_LIMITS)
    assert "class UploadSizeLimitMiddleware" in code, "UploadSizeLimitMiddleware 클래스 누락"
    # BaseHTTPMiddleware 상속
    assert "BaseHTTPMiddleware" in code, "BaseHTTPMiddleware 상속 누락"
    # dispatch 메서드
    assert "async def dispatch" in code, "dispatch 메서드 누락"
    # 413 status_code 반환
    assert "413" in code, "413 status code 누락"


def test_stride_d_middleware_registered_in_api_init():
    """STRIDE D: backend/api/__init__.py 에 미들웨어가 등록되어 있어야 함."""
    code = _read(API_INIT)
    # UploadSizeLimitMiddleware 임포트 + add_middleware 호출
    assert "UploadSizeLimitMiddleware" in code, (
        "backend/api/__init__.py에 UploadSizeLimitMiddleware 미들웨어 등록 누락"
    )
    assert re.search(
        r"app\.add_middleware\(\s*UploadSizeLimitMiddleware",
        code,
    ), "app.add_middleware(UploadSizeLimitMiddleware, ...) 호출 누락"


# ---------------------------------------------------------------------------
# in-process 동작 검증
# ---------------------------------------------------------------------------

def test_stride_i_safe_internal_error_returns_safe_message():
    """STRIDE I: safe_internal_error(RuntimeError("내부 쿼리: SELECT * FROM secrets")) 호출 시
    클라이언트 응답 detail에 str(e) 본문이 노출되지 않고 request_id만 있어야 함."""
    sys.path.insert(0, ROOT)
    from core.error_helpers import safe_internal_error

    e = RuntimeError("SECRET_DB_PATH=D:/sqm/secrets.db password=hunter2")
    http_exc = safe_internal_error(e, op="테스트")
    assert http_exc.status_code == 500
    # detail에 str(e)의 비밀 문자열이 없어야 함
    assert "hunter2" not in str(http_exc.detail), (
        f"클라이언트 응답에 비밀번호 노출: {http_exc.detail!r}"
    )
    assert "D:/sqm/secrets.db" not in str(http_exc.detail), (
        f"클라이언트 응답에 경로 노출: {http_exc.detail!r}"
    )
    # request_id (12자 hex) 만 노출
    assert "ref:" in str(http_exc.detail), "request_id 마커 누락"


def test_stride_d_check_upload_size_rejects_oversize():
    """STRIDE D: 50MB 초과 데이터는 413 HTTPException."""
    sys.path.insert(0, ROOT)
    from fastapi import HTTPException
    from core.upload_limits import check_upload_size, MAX_UPLOAD_BYTES

    # 정확히 한도 + 1 바이트
    over = b"x" * (MAX_UPLOAD_BYTES + 1)
    try:
        check_upload_size(over)
    except HTTPException as he:
        assert he.status_code == 413, f"413이 아닌 {he.status_code} 반환"
        assert "초과" in str(he.detail), "초과 메시지 누락"
    else:
        raise AssertionError("한도 초과인데 예외 안 남")


def test_stride_d_check_upload_size_allows_undersize():
    """STRIDE D: 한도 미만 데이터는 정상 통과."""
    sys.path.insert(0, ROOT)
    from core.upload_limits import check_upload_size, MAX_UPLOAD_BYTES

    # 한도 미만
    ok = b"x" * (1024 * 1024)  # 1 MB
    check_upload_size(ok)  # 예외 없이 통과해야 함
