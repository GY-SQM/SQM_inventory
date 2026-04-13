# -*- coding: utf-8 -*-
"""
SQM React API — main.py 패치 (P2 개선 #3)
 추가된 것:
  1. 서버 시작/종료 Telegram 알림
  2. 전역 500 에러 핸들러 → Telegram 실시간 알림
  3. DB 연결 실패 → CRITICAL 알림
  4. /api/health 응답에 engine_ready 상태 포함

배치: react_api/main.py 덮어쓰기
"""
import logging
import os
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from react_api.schemas.common import HealthResponse
from react_api.utils.db import now_str
from react_api.middleware.security import SecurityMiddleware, RequestSizeLimitMiddleware

# ── 추가: Telegram 알림 모듈 ──────────────────────────────────
from react_api.utils.telegram_alert import alert_info, alert_critical, alert_error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
for _uv_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    logging.getLogger(_uv_name).propagate = False

logger = logging.getLogger(__name__)

from react_api.routes.dashboard      import router as dashboard_router
from react_api.routes.inventory      import router as inventory_router
from react_api.routes.tabs           import router as tabs_router
from react_api.routes.inbound        import router as inbound_router
from react_api.routes.outbound_write import router as outbound_write_router
from react_api.routes.location       import router as location_router
from react_api.routes.files          import router as files_router
from react_api.routes.search         import router as search_router
from react_api.routes.advanced       import router as advanced_router
from react_api.routes.ai_dashboard   import router as ai_router
from react_api.routes.return_tab     import router as return_router
from react_api.routes.return_write   import router as return_write_router
from react_api.routes.do_update      import router as do_update_router
from react_api.routes.location_bulk  import router as location_bulk_router
from react_api.routes.tools          import router as tools_router
from react_api.routes.reports        import router as reports_router
from react_api.routes.products       import router as products_router
from react_api.routes.approval       import router as approval_router
from react_api.routes.ai_chat        import router as ai_chat_router
from react_api.routes.smart_inbound  import router as smart_inbound_router
from react_api.routes.editor         import router as editor_router
from react_api.routes.backup         import router as backup_router
from react_api.routes.templates      import (
    inbound_tpl_router, picking_tpl_router,
    move_appr_router,   swap_router,
)


# ================================================================
# Lifespan — 시작/종료 + Telegram 알림 추가
# ================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 서버 시작 ──────────────────────────────────────────────
    logger.info(" SQM API 시작 중...")
    from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
    try:
        engine = SQMInventoryEngineV3()
        app.state.engine       = engine
        app.state.engine_ready = True
        db_path = getattr(engine, 'db_path', 'unknown')
        logger.info(f" 엔진 초기화 완료: {db_path}")

        #  추가: 서버 시작 Telegram 알림
        await alert_info(
            f" SQM API 서버 시작\n"
            f"DB: {db_path}\n"
            f"시각: {now_str()}"
        )

    except Exception as e:
        app.state.engine       = None
        app.state.engine_ready = False
        logger.critical(f" 엔진 초기화 실패 (서버 시작 불가): {e}", exc_info=True)

        #  추가: 엔진 초기화 실패 CRITICAL 알림
        await alert_critical(
            "엔진 초기화 실패",
            f"SQM API가 시작됐지만 DB 엔진 로드에 실패했습니다.\n"
            f"오류: {str(e)}"
        )
        # P0-4: 엔진 없이 서버 작동 불가 — 에러를 재발생시켜 원인 명확화
        raise

    yield

    # ── 서버 종료 ──────────────────────────────────────────────
    engine = getattr(app.state, 'engine', None)
    if engine:
        try:
            engine.close()
        except Exception:
            pass

    #  추가: 서버 종료 Telegram 알림
    await alert_info(f" SQM API 서버 종료\n시각: {now_str()}")
    logger.info(" SQM API 종료")


# ================================================================
# FastAPI 앱 생성
# ================================================================
app = FastAPI(
    title="SQM API",
    version="0.6.1",                          #  버전 업 (0.6.0 → 0.6.1)
    description="SQM v871 — P2 개선 #3 에러 알림 적용",
    lifespan=lifespan,
)


# ================================================================
#  추가: 전역 500 에러 핸들러 → Telegram 알림
# ================================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    모든 처리되지 않은 500 에러를 잡아서:
    1. 로그 기록
    2. Telegram 즉시 알림
    3. 표준 500 응답 반환
    """
    path = request.url.path
    method = request.method

    logger.error(
        f"[500] {method} {path} → {type(exc).__name__}: {exc}",
        exc_info=True
    )

    #  Telegram 에러 알림
    await alert_error(
        context=f"{method} {path}",
        error=exc
    )

    return JSONResponse(
        status_code=500,
        content={
            "ok":    False,
            "error": "내부 서버 오류가 발생했습니다.",
            "path":  path,
        }
    )


# ================================================================
# Middleware
# ================================================================
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SecurityMiddleware)


@app.middleware("http")
async def check_engine_ready(request: Request, call_next):
    """엔진 미초기화 상태에서 API 호출 시 503 반환 (헬스체크/docs/테스트 제외)"""
    skip_prefixes = ("/health", "/docs", "/openapi.json", "/redoc")
    path = request.url.path
    if path == "/" or path.startswith(skip_prefixes):
        return await call_next(request)
    # 테스트 환경에서는 engine_ready가 설정 안 되어 있을 수 있으므로,
    # state에 engine_ready 속성 자체가 없으면 통과 (테스트 호환)
    if hasattr(request.app.state, "engine_ready") and not request.app.state.engine_ready:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "DB 엔진 초기화 중입니다. 잠시 후 재시도하세요."},
        )
    return await call_next(request)

import socket as _sock
try:
    _local_ip = _sock.gethostbyname(_sock.gethostname())
except Exception:
    _local_ip = "127.0.0.1"

_default_origins = [
    "http://localhost:5173",     "http://127.0.0.1:5173",
    "http://localhost:8000",     "http://127.0.0.1:8000",
    f"http://{_local_ip}:8000",  f"http://{_local_ip}:5173",
]
_env_origins = os.environ.get("ALLOWED_ORIGINS", "")
_extra = [o.strip() for o in _env_origins.split(",") if o.strip()]
_allow_origins = list(set(_default_origins + _extra))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Token", "Accept"],
)


# ================================================================
# 라우터 등록 (기존과 동일)
# ================================================================
app.include_router(dashboard_router)
app.include_router(inventory_router)
app.include_router(tabs_router)
app.include_router(inbound_router)
app.include_router(outbound_write_router)
app.include_router(location_router)
app.include_router(files_router)
app.include_router(search_router)
app.include_router(tools_router)
app.include_router(advanced_router)
app.include_router(ai_router)
app.include_router(return_router)
app.include_router(return_write_router)
app.include_router(do_update_router)
app.include_router(location_bulk_router)
app.include_router(reports_router)
app.include_router(products_router)
app.include_router(approval_router)
app.include_router(ai_chat_router)
app.include_router(smart_inbound_router)
app.include_router(inbound_tpl_router)
app.include_router(picking_tpl_router)
app.include_router(move_appr_router)
app.include_router(swap_router)
app.include_router(editor_router)
app.include_router(backup_router)


# ================================================================
# Health 엔드포인트 — engine_ready 상태 포함
# ================================================================
@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health(request: Request) -> HealthResponse:
    """
     개선: engine_ready 상태 포함
    engine_ready=False 이면 DB 연결 실패 상태
    """
    engine_ready = getattr(request.app.state, 'engine_ready', True)
    return HealthResponse(
        ok=engine_ready,
        service="sqm-api",
        generated_at=now_str()
    )


# ================================================================
# React 정적 파일 서빙
# ================================================================
_dist_dir = Path(__file__).resolve().parent.parent / "web" / "dist"
if _dist_dir.exists():
    # /assets 등 정적 리소스
    app.mount("/assets", StaticFiles(directory=_dist_dir / "assets"), name="static-assets")

    # favicon, icons 등 루트 정적 파일
    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(_dist_dir / "favicon.svg")

    @app.get("/icons.svg")
    async def icons():
        return FileResponse(_dist_dir / "icons.svg")

    # SPA fallback — 모든 비-API 경로를 index.html로
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API 경로는 이미 위 라우터에서 처리됨
        file_path = _dist_dir / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_dist_dir / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "react_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
