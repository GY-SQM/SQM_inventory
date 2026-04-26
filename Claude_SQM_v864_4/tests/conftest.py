# -*- coding: utf-8 -*-
"""
tests/conftest.py
=================
Shared pytest fixtures for the SQM Phase 4 test suite.
"""

import pathlib
import sys

# Ensure project root is on sys.path so engine_modules can be imported
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from tests.fixtures import get_fixtures_dir, create_empty_db


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory):
    """Session-scoped temp directory for all test DBs."""
    return tmp_path_factory.mktemp("sqm_fixtures")


@pytest.fixture(scope="session")
def empty_db(fixtures_dir):
    """Session-scoped empty (schema-only) SQLite DB."""
    p = fixtures_dir / "inventory_empty.db"
    create_empty_db(str(p))
    return p


@pytest.fixture(scope="session")
def ten_lots_db(fixtures_dir):
    """Session-scoped DB pre-populated with 10 LOT rows."""
    from tests.fixtures import create_ten_lots_db
    p = fixtures_dir / "inventory_ten_lots.db"
    create_ten_lots_db(str(p))
    return p
