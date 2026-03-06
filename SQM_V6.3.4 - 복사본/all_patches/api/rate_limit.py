"""
SQM v7.0.0-alpha — Rate Limiting 미들웨어
==========================================
slowapi 기반 IP/사용자별 요청 속도 제한.

설정:
    - 인증 없는 요청: 분당 30회
    - 인증된 요청: 분당 120회
    - POST (입출고/반품): 분당 30회
    - WebSocket: 제한 없음
"""

import logging
import os

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# Rate Limit 설정
# ═══════════════════════════════════════════

DEFAULT_RATE = os.environ.get('SQM_RATE_LIMIT', '120/minute')
ANON_RATE = os.environ.get('SQM_ANON_RATE', '30/minute')
WRITE_RATE = os.environ.get('SQM_WRITE_RATE', '30/minute')


def _get_rate_key(request: Request) -> str:
    auth = request.headers.get('authorization', '')
    if auth.startswith('Bearer '):
        try:
            from api.auth import verify_token
            token = auth[7:]
            payload = verify_token(token)
            if payload and payload.get('sub'):
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_get_rate_key, default_limits=[DEFAULT_RATE])


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    logger.warning(f"[RateLimit] 초과: {_get_rate_key(request)} — {exc.detail}")
    return JSONResponse(
        status_code=429,
        content={
            "detail": "요청 한도 초과 — 잠시 후 다시 시도하세요",
            "limit": str(exc.detail),
        },
    )
