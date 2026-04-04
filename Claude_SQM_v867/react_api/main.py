# -*- coding: utf-8 -*-
"""
SQM React Phase 1 - FastAPI Main (Refactored)
----------------------------------------------
Thin entry point. Routes/schemas/services are separated.

실행:
    uvicorn react_api.main:app --reload --host 127.0.0.1 --port 8000
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from react_api.schemas.common import HealthResponse
from react_api.utils.db import now_str
from react_api.middleware.security import SecurityMiddleware, RequestSizeLimitMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
from react_api.routes.dashboard import router as dashboard_router
from react_api.routes.inventory import router as inventory_router
from react_api.routes.tabs import router as tabs_router
from react_api.routes.inbound import router as inbound_router
from react_api.routes.outbound_write import router as outbound_write_router
from react_api.routes.location import router as location_router
from react_api.routes.files import router as files_router
from react_api.routes.search import router as search_router
from react_api.routes.tools import router as tools_router
from react_api.routes.advanced import router as advanced_router
from react_api.routes.ai_dashboard import router as ai_router

app = FastAPI(
    title="SQM API",
    version="0.3.0",
    description="SQM v867 - Read + Write API",
)

app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(ok=True, service="sqm-read-api", generated_at=now_str())
