# -*- coding: utf-8 -*-
"""보안 미들웨어: 입력값 검증, 에러 핸들링, 로깅."""
import logging
import time
import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sqm.security")

# Admin 토큰 (쓰기 API 보호)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


class SecurityMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 + 쓰기 API 토큰 검증."""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        path = request.url.path
        method = request.method

        # 쓰기 API는 ADMIN_TOKEN 검증 (설정된 경우만)
        if ADMIN_TOKEN and method in ('POST', 'PUT', 'DELETE') and path.startswith('/api/'):
            token = request.headers.get('X-Admin-Token', '')
            if token != ADMIN_TOKEN:
                logger.warning(f"Unauthorized write attempt: {method} {path}")
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "message": "관리자 인증 필요", "data": {}},
                )

        try:
            response = await call_next(request)
            elapsed = time.time() - start
            logger.info(f"{method} {path} → {response.status_code} ({elapsed:.2f}s)")
            return response
        except Exception as e:
            elapsed = time.time() - start
            logger.exception(f"{method} {path} → ERROR ({elapsed:.2f}s)")
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "내부 서버 오류", "data": {}},
            )


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """요청 크기 제한 (100MB)."""

    MAX_SIZE = 100 * 1024 * 1024

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.MAX_SIZE:
            return JSONResponse(
                status_code=413,
                content={"success": False, "message": f"요청 크기 초과 (최대 {self.MAX_SIZE // (1024*1024)}MB)", "data": {}},
            )
        return await call_next(request)
