# -*- coding: utf-8 -*-
"""SQM React API v0.6.0 — v869 릴리즈

실행:
    uvicorn react_api.main:app --reload --host 127.0.0.1 --port 8000
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from react_api.schemas.common import HealthResponse
from react_api.utils.db import now_str
from react_api.middleware.security import SecurityMiddleware, RequestSizeLimitMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

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
from react_api.routes.templates      import (
    inbound_tpl_router, picking_tpl_router,
    move_appr_router,   swap_router,
)


# ── P1: 서버 시작 시 엔진 1회 초기화 → app.state.engine 공유 ─────────────
# get_engine() 매 요청마다 생성하는 오버헤드 제거
# 라우터에서는 기존 get_engine() context manager 그대로 사용 가능
# (이미 충분히 안전한 with 패턴을 유지하면서 startup 로그만 추가)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 서버 시작 — 엔진 1회 생성 → app.state.engine 공유 ─────────
    # 매 요청마다 get_engine() 신규 생성 오버헤드 제거 (P1 개선)
    logger.info("🚀 SQM API 시작 중...")
    from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
    try:
        engine = SQMInventoryEngineV3()
        app.state.engine       = engine
        app.state.engine_ready = True
        db_path = getattr(engine, 'db_path', 'unknown')
        logger.info(f"✅ 엔진 초기화 완료 (공유 인스턴스): {db_path}")
    except Exception as e:
        app.state.engine       = None
        app.state.engine_ready = False
        logger.error(f"❌ 엔진 초기화 실패: {e}")
    yield
    # ── 서버 종료 ──────────────────────────────────────────────────
    engine = getattr(app.state, 'engine', None)
    if engine:
        try:
            engine.close()
        except Exception:
            pass
    logger.info("🔴 SQM API 종료")


app = FastAPI(
    title="SQM API",
    version="0.6.0",
    description="SQM v869 — React 전환 완성 + 감사 기반 안정화",
    lifespan=lifespan,
)

app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SecurityMiddleware)
# CORS 허용 도메인 — .env의 ALLOWED_ORIGINS에서 로드
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
    allow_methods=["*"],
    allow_headers=["*", "X-Admin-Token"],
)

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
app.include_router(inbound_tpl_router)
app.include_router(picking_tpl_router)
app.include_router(move_appr_router)
app.include_router(swap_router)


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(ok=True, service="sqm-api", generated_at=now_str())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "react_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
