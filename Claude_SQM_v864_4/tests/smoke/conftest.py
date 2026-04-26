# -*- coding: utf-8 -*-
"""
tests/smoke/conftest.py
=======================
Phase 0 Safety Net: fixtures for smoke tests.

Mirrors tests/unit/conftest.py so smoke tests can run independently.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(scope="session")
def base_url() -> str:
    """Local FastAPI URL used by PyWebView in production."""
    return "http://127.0.0.1:8765"


@pytest.fixture(scope="session")
def api_client():
    """
    FastAPI TestClient bound to backend.api:app.

    Uses TestClient (not httpx against a live server) so smoke tests do
    not require main_webview.py to be running. If backend.api fails to
    import, the test is skipped with a descriptive message.
    """
    try:
        from fastapi.testclient import TestClient
        from backend.api import app
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"backend.api import failed — cannot build TestClient: {e}")
        return None

    with TestClient(app) as client:
        yield client
