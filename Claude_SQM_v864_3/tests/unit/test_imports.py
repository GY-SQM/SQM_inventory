# -*- coding: utf-8 -*-
"""
tests/unit/test_imports.py
==========================
Phase 0 Safety Net: verify core Python modules can be imported.

These tests deliberately do NOT instantiate the engine — the engine
currently fails silently and leaves ENGINE_AVAILABLE=False. We only
check that the *modules* and class symbols exist. Instantiation is
covered in Phase 2 once the engine load issue is fixed.
"""
from __future__ import annotations

import importlib

import pytest


pytestmark = pytest.mark.unit


def test_can_import_backend_api():
    """backend.api defines the FastAPI `app` object."""
    try:
        mod = importlib.import_module("backend.api")
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"Cannot import backend.api: {type(e).__name__}: {e}")
    assert hasattr(mod, "app"), "backend.api must expose `app` (FastAPI instance)"


def test_can_import_backend_common_errors():
    """backend.common.errors defines NotReadyError for HTTP 501 stubs."""
    try:
        mod = importlib.import_module("backend.common.errors")
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            f"Cannot import backend.common.errors: {type(e).__name__}: {e}"
        )
    assert hasattr(mod, "NotReadyError"), (
        "backend.common.errors must expose NotReadyError"
    )


def test_can_import_backend_api_menubar():
    """backend.api.menubar defines the F001-F062 router."""
    try:
        mod = importlib.import_module("backend.api.menubar")
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            f"Cannot import backend.api.menubar: {type(e).__name__}: {e}"
        )
    assert hasattr(mod, "router"), (
        "backend.api.menubar must expose `router` (APIRouter instance)"
    )


def test_engine_class_exists():
    """
    SQMInventoryEngineV3 class must be importable even if instantiation
    would fail. We import the class symbol only — NOT constructing an
    instance — so this passes regardless of ENGINE_AVAILABLE state.
    """
    try:
        mod = importlib.import_module("engine_modules.inventory_modular.engine")
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            "Cannot import engine_modules.inventory_modular.engine: "
            f"{type(e).__name__}: {e}"
        )
    assert hasattr(mod, "SQMInventoryEngineV3"), (
        "engine module must expose SQMInventoryEngineV3 class"
    )
