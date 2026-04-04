# -*- coding: utf-8 -*-
"""
SQM React Phase 1 - FastAPI Main (Refactored)
----------------------------------------------
Thin entry point. Routes/schemas/services are separated.

실행:
    uvicorn react_api.main:app --reload --host 127.0.0.1 --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from react_api.schemas.common import HealthResponse
from react_api.utils.db import now_str
from react_api.routes.dashboard import router as dashboard_router
from react_api.routes.inventory import router as inventory_router

app = FastAPI(
    title="SQM Read API",
    version="0.2.0",
    description="SQM React Phase 1 - Read-Only API",
)

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


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(ok=True, service="sqm-read-api", generated_at=now_str())
