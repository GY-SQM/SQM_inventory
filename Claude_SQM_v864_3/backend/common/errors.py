"""
SQM v864.3 - FastAPI common error module
=========================================
- ApiError: 프로젝트 표준 예외
- wrap_engine_call: 엔진 호출 래퍼 (HTTP 로 예외 승격)
- install_exception_handlers: 앱 레벨 핸들러 등록

Phase 2 Step 3 (2026-04-21):
  NotReadyError: HTTP 501 -> HTTP 200 + body.ok=false
  이유: DevTools Console 은 4xx/5xx 를 빨간색으로 칠해서
        의도된 "준비 중" 안내도 실제 에러처럼 보임.
"""
from __future__ import annotations

import logging
import traceback
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("sqm.api")


# ========== Response Formatters ==========
def ok_response(data: Any = None, message: str | None = None) -> dict:
    """표준 성공 응답 포맷"""
    return {"ok": True, "data": data, "error": None, "message": message}


def err_response(error: str, detail: Any = None) -> dict:
    """표준 에러 응답 포맷 (JSON body 용)"""
    return {"ok": False, "data": None, "error": error, "detail": detail}


# ========== Exception Classes ==========
class ApiError(Exception):
    """프로젝트 표준 예외 (HTTP status + 메시지)"""

    def __init__(self, code: int, message: str, detail: Any = None):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotReadyError(ApiError):
    """
    아직 구현되지 않은 기능.
    Phase 2 Step 3: HTTP 200 + body.ok=false + detail.code=NOT_READY.
    프론트: body.ok===false && detail?.code==='NOT_READY' -> info toast.
    """

    def __init__(self, feature: str = ""):
        super().__init__(
            200,
            f"NotReady{' - ' + feature if feature else ''}",
            detail={"code": "NOT_READY", "feature": feature},
        )


# ========== Engine Call Wrapper ==========
def wrap_engine_call(fn: Callable, *args, **kwargs) -> dict:
    """
    Tkinter 핸들러를 HTTP 응답으로 승격하는 표준 래퍼.
    - NotImplementedError -> HTTP 200 + body.ok=false (soft-fail)
    - FileNotFoundError -> HTTP 404
    - PermissionError -> HTTP 403
    - ValueError/KeyError -> HTTP 400
    - ApiError code==200 -> soft-fail body
    - 그 외 -> HTTP 500
    """
    try:
        result = fn(*args, **kwargs)
        return ok_response(data=result)
    except NotImplementedError as e:
        return err_response(
            f"NotReady: {e}",
            detail={"code": "NOT_READY", "reason": str(e)},
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"FileNotFound: {e}") from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"PermissionDenied: {e}") from e
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"BadRequest: {e}") from e
    except ApiError as e:
        if e.code == 200:
            return err_response(e.message, detail=e.detail)
        raise HTTPException(status_code=e.code, detail=e.message) from e
    except Exception as e:
        log.exception("engine call failed")
        raise HTTPException(
            status_code=500,
            detail=f"EngineError: {type(e).__name__}: {e}",
        ) from e


async def wrap_engine_call_async(fn: Callable, *args, **kwargs) -> dict:
    """비동기 버전 - async def 함수용"""
    try:
        result = await fn(*args, **kwargs)
        return ok_response(data=result)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=f"NotReady: {e}") from e
    except Exception as e:
        log.exception("async engine call failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ========== App-level Handler Install ==========
def install_exception_handlers(app: FastAPI) -> None:
    """FastAPI 앱에 전역 예외 핸들러 설치"""

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.code,
            content=err_response(exc.message, detail=exc.detail),
        )

    @app.exception_handler(Exception)
    async def handle_generic(request: Request, exc: Exception):
        log.error("unhandled exception at %s", request.url)
        log.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content=err_response(
                "ServerError",
                detail={"type": type(exc).__name__, "message": str(exc)},
            ),
        )


__all__ = [
    "ApiError",
    "NotReadyError",
    "wrap_engine_call",
    "wrap_engine_call_async",
    "install_exception_handlers",
    "ok_response",
    "err_response",
]
