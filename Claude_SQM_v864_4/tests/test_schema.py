# -*- coding: utf-8 -*-
"""
tests/test_schema.py
====================
Schema invariant tests for SQM Phase 4.

Verifies that:
  - Core tables exist after SQMDatabase initialisation
  - Required triggers exist (weight floor, insert weight floor)
  - Required indexes exist (sold_table dedup)
  - Sample-exclusion invariant is conceptually correct

All tests use the session-scoped empty_db fixture from conftest.py.
"""

import sqlite3
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_conn(empty_db) -> sqlite3.Connection:
    """Return a read-only sqlite3 connection to the test DB."""
    conn = sqlite3.connect(str(empty_db))
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row is not None


def _trigger_exists(conn: sqlite3.Connection, trigger_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?",
        (trigger_name,)
    ).fetchone()
    return row is not None


def _index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSchemaTables:
    """Core table existence checks."""

    def test_schema_tables_exist_inventory(self, empty_db):
        """inventory table must exist after DB initialisation."""
        conn = _get_conn(empty_db)
        try:
            assert _table_exists(conn, "inventory"), \
                "Table 'inventory' is missing from schema"
        finally:
            conn.close()

    def test_schema_tables_exist_inventory_tonbag(self, empty_db):
        """inventory_tonbag table must exist."""
        conn = _get_conn(empty_db)
        try:
            assert _table_exists(conn, "inventory_tonbag"), \
                "Table 'inventory_tonbag' is missing from schema"
        finally:
            conn.close()

    def test_schema_tables_exist_audit_log(self, empty_db):
        """audit_log table must exist."""
        conn = _get_conn(empty_db)
        try:
            assert _table_exists(conn, "audit_log"), \
                "Table 'audit_log' is missing from schema"
        finally:
            conn.close()


class TestSchemaTriggers:
    """Trigger existence checks (Phase 4-A regression guards)."""

    def test_schema_weight_floor_trigger(self, empty_db):
        """trg_inventory_weight_floor (BEFORE UPDATE) must exist — v8.7.1 P0-5."""
        conn = _get_conn(empty_db)
        try:
            assert _trigger_exists(conn, "trg_inventory_weight_floor"), (
                "Trigger 'trg_inventory_weight_floor' is missing. "
                "_migrate_v871_inventory_weight_floor() may not have run."
            )
        finally:
            conn.close()

    def test_schema_weight_floor_insert_trigger(self, empty_db):
        """trg_inventory_weight_floor_insert (BEFORE INSERT) must exist — v8.6.4.2 P1."""
        conn = _get_conn(empty_db)
        try:
            assert _trigger_exists(conn, "trg_inventory_weight_floor_insert"), (
                "Trigger 'trg_inventory_weight_floor_insert' is missing. "
                "_migrate_v872_inventory_weight_floor_insert() may not have run."
            )
        finally:
            conn.close()


class TestSchemaIndexes:
    """Index existence checks."""

    def test_schema_sold_dedup_index(self, empty_db):
        """idx_sold_dedup UNIQUE index on sold_table must exist — v8.6.4.2 P4."""
        conn = _get_conn(empty_db)
        try:
            assert _index_exists(conn, "idx_sold_dedup"), (
                "Index 'idx_sold_dedup' is missing. "
                "_migrate_v872_sold_table_dedup_index() may not have run."
            )
        finally:
            conn.close()


class TestSchemaSampleExclusion:
    """Verify the sample-exclusion invariant is represented in the schema."""

    def test_schema_sample_excluded_view_or_logic(self, empty_db):
        """
        inventory_tonbag must have an is_sample column so the engine can
        exclude sample tonbags from current_weight calculations.

        The key invariant:
            current_weight = SUM(weight) WHERE status IN ('AVAILABLE','RESERVED')
                             AND (is_sample IS NULL OR is_sample = 0)
        """
        conn = _get_conn(empty_db)
        try:
            # Check column presence via PRAGMA
            cols = conn.execute(
                "PRAGMA table_info(inventory_tonbag)"
            ).fetchall()
            col_names = [row["name"] for row in cols]
            assert "is_sample" in col_names, (
                "Column 'is_sample' missing from inventory_tonbag — "
                "sample-exclusion invariant cannot be enforced."
            )
        finally:
            conn.close()
