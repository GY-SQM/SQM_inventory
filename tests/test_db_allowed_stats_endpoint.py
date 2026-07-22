# -*- coding: utf-8 -*-
"""
tests/test_db_allowed_stats_endpoint.py
=======================================
SQM v9.0.2 — GET endpoint /api/admin/db-allowed/stats 테스트

FastAPI TestClient로 직접 호출 검증.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.db_allowed import reset_counts
from backend.api.db_allowed_stats import router


@pytest.fixture
def client():
    """TestClient with only db_allowed_stats router."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_setup_method():
    """각 테스트 전 카운터 초기화."""
    reset_counts()


def test_e01_endpoint_basic(client):
    """빈 카운터 → total_calls 0."""
    reset_counts()
    response = client.get("/api/admin/db-allowed/stats")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_calls"] == 0
    assert data["allowed"] == 0
    assert data["blocked"] == 0
    assert data["by_kind"] == {}


def test_e02_endpoint_after_validate(client):
    """validate() 호출 후 통계 반영."""
    from core.db_allowed import validate
    reset_counts()
    validate("inventory", "table", "inventory")  # allowed
    validate("inventory", "table", "bad")  # blocked
    response = client.get("/api/admin/db-allowed/stats")
    data = response.json()["data"]
    assert data["total_calls"] == 2
    assert data["allowed"] == 1
    assert data["blocked"] == 1
    assert data["by_kind"]["table"]["allowed"] == 1
    assert data["by_kind"]["table"]["blocked"] == 1


def test_e03_endpoint_raw_counts(client):
    """raw_counts 노출 (디버깅용)."""
    from core.db_allowed import validate
    reset_counts()
    validate("inventory", "status", "AVAILABLE")  # allowed
    response = client.get("/api/admin/db-allowed/stats")
    data = response.json()["data"]
    # raw_counts는 (area, kind, result) 형식의 key
    # 예: "inventory|status|True" (area="inventory", kind="status", result=True)
    assert any("status" in k and "True" in k for k in data["raw_counts"].keys())
    assert all(v >= 1 for v in data["raw_counts"].values())
