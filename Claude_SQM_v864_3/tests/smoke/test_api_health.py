# -*- coding: utf-8 -*-
"""
tests/smoke/test_api_health.py
==============================
Phase 0 Safety Net: smoke tests against the FastAPI app via TestClient.

These tests do NOT require main_webview.py to be running. TestClient
drives the ASGI app in-process. The goal is to verify that basic
endpoints respond with 200 — not to validate payload correctness. The
backend currently serves sample data when ENGINE_AVAILABLE is False,
which is acceptable for Phase 0.
"""
from __future__ import annotations

import json

import pytest


pytestmark = pytest.mark.smoke


def _dump(resp):
    """Best-effort pretty-print of a response body for debugging."""
    try:
        return json.dumps(resp.json(), ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        return resp.text


def test_health_endpoint_responds(api_client):
    """GET /api/health returns 200 and includes a status field."""
    resp = api_client.get("/api/health")
    if resp.status_code != 200:
        print(f"[health] status={resp.status_code} body={_dump(resp)}")
    assert resp.status_code == 200, (
        f"/api/health expected 200, got {resp.status_code}: {_dump(resp)}"
    )
    body = resp.json()
    assert "status" in body, f"health response missing 'status': {body}"


def test_dashboard_stats_responds(api_client):
    """
    GET /api/dashboard/stats returns 200.

    If ENGINE_AVAILABLE is False the backend returns sample data — that
    is fine for Phase 0. We only verify the endpoint does not crash.
    """
    resp = api_client.get("/api/dashboard/stats")
    if resp.status_code != 200:
        print(f"[dashboard] status={resp.status_code} body={_dump(resp)}")
    assert resp.status_code == 200, (
        f"/api/dashboard/stats expected 200, got {resp.status_code}: {_dump(resp)}"
    )


def test_inventory_endpoint_responds(api_client):
    """GET /api/inventory returns 200 with a data envelope."""
    resp = api_client.get("/api/inventory")
    if resp.status_code != 200:
        print(f"[inventory] status={resp.status_code} body={_dump(resp)}")
    assert resp.status_code == 200, (
        f"/api/inventory expected 200, got {resp.status_code}: {_dump(resp)}"
    )
    body = resp.json()
    # Either sample or real data — both envelopes have a 'data' key.
    assert "data" in body, f"inventory response missing 'data' key: {body}"
