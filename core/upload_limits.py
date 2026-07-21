# -*- coding: utf-8 -*-
"""
core.upload_limits — STRIDE D (Denial of Service) 대응.

v8.8.5(2026-07-21) — audit-report.md 🟡 #3 STRIDE D:
  기존 UploadFile 엔드포인트들은 크기 제한이 없어서 수 GB 업로드 가능.
  메모리 고갈 → DoS 취약점.

해결 (2단 방어):
  1. `UploadSizeLimitMiddleware` (전역): Content-Length 헤더로 사전 차단.
     — 미들웨어가 너무 큰 요청은 413 Payload Too Large로 즉시 거부.
  2. `check_upload_size(pdf_bytes)` (개별 호출처): 실제 read 후에도 한 번 더 검증.
     — Content-Length 위장 가능성 + multipart streaming 대응.

사용 예:
    # main_webview.py에 미들웨어 등록
    from core.upload_limits import UploadSizeLimitMiddleware
    app.add_middleware(UploadSizeLimitMiddleware, max_bytes=50 * 1024 * 1024)

    # 각 UploadFile 엔드포인트
    from core.upload_limits import check_upload_size, MAX_UPLOAD_BYTES
    pdf_bytes = await file.read()
    check_upload_size(pdf_bytes)  # 초과 시 413 raise
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


# 기본 업로드 한도: 50 MB
MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024


def check_upload_size(
    data: bytes,
    max_bytes: int = MAX_UPLOAD_BYTES,
    *,
    label: str = "upload",
) -> None:
    """STRIDE D: 업로드 데이터 크기 검증 (개별 호출처용 가드).

    Args:
        data: 업로드된 bytes
        max_bytes: 최대 허용 크기 (기본 50 MB)
        label: 로그/메시지용 라벨 (예: "PDF", "Excel")

    Raises:
        HTTPException 413 — 크기 초과 시
    """
    if len(data) > max_bytes:
        logger.warning(
            f"[STRIDE-D] {label} 업로드 크기 초과: {len(data):,} > {max_bytes:,} bytes"
        )
        raise HTTPException(
            status_code=413,
            detail=(
                f"파일 크기 초과: {len(data):,} bytes (최대 {max_bytes:,} bytes)"
            ),
        )


class UploadSizeLimitMiddleware(BaseHTTPMiddleware):
    """STRIDE D: 전역 업로드 크기 미들웨어 (Content-Length 헤더 사전 검사).

    Note: Content-Length는 클라이언트가 보낸 헤더라 위장 가능.
          하지만 빠른 사전 차단 + 정상 클라이언트 DoS 방어에 효과적.
          실제 read 후 `check_upload_size()` 로 한 번 더 검증 권장.
    """

    def __init__(self, app, max_bytes: int = MAX_UPLOAD_BYTES):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        # POST + multipart/form-data 또는 octet-stream 만 검사
        if request.method in ("POST", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            if cl:
                try:
                    cl_int = int(cl)
                except ValueError:
                    cl_int = 0
                if cl_int > self.max_bytes:
                    logger.warning(
                        f"[STRIDE-D/MW] {request.url.path} 업로드 크기 초과: "
                        f"{cl_int:,} > {self.max_bytes:,} bytes"
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                f"파일 크기 초과: {cl_int:,} bytes "
                                f"(최대 {self.max_bytes:,} bytes)"
                            )
                        },
                    )
        return await call_next(request)
