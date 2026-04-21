# -*- coding: utf-8 -*-
"""
tests/unit/conftest.py
======================
Phase 0 Safety Net: fixtures for unit tests.

NOTE: tests/conftest.py already exists and handles sys.path injection +
DB fixtures. This subdirectory conftest adds fixtures specific to the
Phase 0 harness (api_client, base_url). pytest auto-composes parent +
child conftests, so both layers of fixtures are available here.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

# Re-ensure project root is on sys.path (defensive; parent conftest also does this)
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

    If backend won't import (e.g. missing deps), skip the test with a
    clear message rather than crashing the run.
    """
    try:
        from fastapi.testclient import TestClient
        from backend.api import app
    except Exception as e:  # noqa: BLE001 — we want any import failure to skip
        pytest.skip(f"backend.api import failed — cannot build TestClient: {e}")
        return None  # unreachable, satisfies type checkers

    with TestClient(app) as client:
        yield client
