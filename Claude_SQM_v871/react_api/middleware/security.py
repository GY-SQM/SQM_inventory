# -*- coding: utf-8 -*-
"""보안 미들웨어 v2 — 입력 검증, 인증, 로깅, Rate Limit."""
import logging
import time
import os
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sqm.security")

# 쓰기 API 보호 토큰 (.env에서 로드)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Rate Limit 설정 — IP당 분당 최대 요청 수
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))

# IP별 요청 카운터 {ip: [timestamp, ...]}
_rate_store: dict = defaultdict(list)


def _check_rate_limit(ip: str) -> bool:
    """True = 허용, False = 차단."""
    now    = time.time()
    window = 60.0
    hits   = _rate_store[ip]
    # 1분 이전 기록 제거
    _rate_store[ip] = [t for t in hits if now - t < window]
    if len(_rate_store[ip]) >= RATE_LIMIT_PER_MINUTE:
        return False
    _rate_store[ip].append(now)
    return True


# 토큰 검증이 필요한 쓰기 경로
WRITE_METHODS = {'POST', 'PUT', 'DELETE', 'PATCH'}

# 토큰 없이 허용하는 안전한 경로 (GET 전용)
PUBLIC_PATHS = {
    '/api/health',
    '/api/dashboard/summary',
    '/docs',
    '/openapi.json',
    '/',
}


class SecurityMiddleware(BaseHTTPMiddleware):
    """요청 로깅 + 쓰기 API 토큰 검증 + Rate Limit."""

    async def dispatch(self, request: Request, call_next):
        start  = time.time()
        path   = request.url.path
        method = request.method
        ip     = request.client.host if request.client else "unknown"

        # ── Rate Limit ───────────────────────────────────────
        if not _check_rate_limit(ip):
            logger.warning("Rate limit 초과: %s %s (IP: %s)", method, path, ip)
            return JSONResponse(
                status_code=429,
                content={"success": False, "message": "요청이 너무 많습니다. 잠시 후 재시도하세요."},
            )

        # ── 쓰기 API 토큰 검증 ────────────────────────────────
        if (ADMIN_TOKEN
                and method in WRITE_METHODS
                and path.startswith('/api/')
                and path not in PUBLIC_PATHS):
            token = request.headers.get('X-Admin-Token', '')
            if token != ADMIN_TOKEN:
                logger.warning("인증 실패: %s %s (IP: %s)", method, path, ip)
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "message": "관리자 인증 필요 (X-Admin-Token 헤더)"},
                )

        # ── 요청 처리 ─────────────────────────────────────────
        try:
            response = await call_next(request)
            elapsed  = time.time() - start
            # 느린 요청 경고 (2초 이상)
            if elapsed > 2.0:
                logger.warning("느린 요청: %s %s → %d (%.2fs)", method, path, response.status_code, elapsed)
            else:
                logger.info("%s %s → %d (%.3fs)", method, path, response.status_code, elapsed)
            return response
        except Exception:
            elapsed = time.time() - start
            logger.exception("요청 처리 오류: %s %s (%.2fs)", method, path, elapsed)
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "내부 서버 오류"},
            )


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """요청 크기 제한 (기본 100MB, .env로 조정 가능)."""

    MAX_SIZE = int(os.getenv("MAX_REQUEST_MB", "100")) * 1024 * 1024

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.MAX_SIZE:
            mb = self.MAX_SIZE // (1024 * 1024)
            logger.warning("요청 크기 초과: %d bytes (최대 %dMB)", int(content_length), mb)
            return JSONResponse(
                status_code=413,
                content={"success": False, "message": f"파일 크기 초과 (최대 {mb}MB)"},
            )
        return await call_next(request)
