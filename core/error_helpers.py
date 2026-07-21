# -*- coding: utf-8 -*-
"""
core.error_helpers — STRIDE I (Information Disclosure) 대응.

v8.8.5(2026-07-21) — audit-report.md 🟡 #3 STRIDE I:
  기존 `HTTPException(500, str(e))` 패턴은 예외 객체의 전체 문자열을 클라이언트에 노출.
  이는 SQL 쿼리·파일 경로·DB 비밀번호 등 내부 정보가 새는 보안 이슈.

해결:
  `safe_internal_error(e, op, *, status_code=500)` — 클라이언트에는 일반화된 메시지
  + 서버 로그(`logger.exception`)에는 전체 traceback 기록.
  향후 모든 5xx HTTPException은 이 helper를 통해 처리 권장.

사용 예:
    from core.error_helpers import safe_internal_error

    try:
        ...
    except Exception as e:
        raise safe_internal_error(e, op="PL 파싱")
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)


# 클라이언트에 노출되는 일반화된 500 메시지
_GENERIC_500_MSG = "내부 오류가 발생했습니다. 잠시 후 다시 시도하거나 관리자에게 문의하세요."


def safe_internal_error(
    e: BaseException,
    op: str = "요청 처리",
    *,
    status_code: int = 500,
    log_full_traceback: bool = True,
) -> HTTPException:
    """STRIDE I: 5xx HTTPException을 클라이언트에 안전한 메시지로 변환.

    클라이언트 응답:
      - 일반화된 한국어 메시지 ("내부 오류가 발생했습니다...")
      - 추적용 짧은 request_id (서버 로그와 매칭 가능)

    서버 로그:
      - `logger.exception()` — 전체 traceback + str(e) 기록
      - request_id 포함하여 클라이언트 응답의 ID와 매칭

    Args:
        e: 발생한 예외 객체 (str(e)에 내부 정보 포함 가능)
        op: 작업명 (예: "PL 파싱", "DB 업데이트") — 로그용 컨텍스트
        status_code: HTTP 상태 코드 (기본 500)
        log_full_traceback: True면 logger.exception, False면 logger.error(str)

    Returns:
        HTTPException — FastAPI가 자동으로 raise. 호출처에서 `raise safe_internal_error(...)`.
    """
    request_id = uuid.uuid4().hex[:12]
    if log_full_traceback:
        logger.exception(
            "[STRIDE-I/%s] %s 실패 (request_id=%s): %s",
            op, op, request_id, type(e).__name__,
        )
    else:
        logger.error(
            "[STRIDE-I/%s] %s 실패 (request_id=%s): %s",
            op, op, request_id, e,
        )
    # 클라이언트에 노출되는 메시지는 request_id만 포함 (traceback X)
    safe_msg = f"{_GENERIC_500_MSG} (ref: {request_id})"
    return HTTPException(status_code=status_code, detail=safe_msg)
