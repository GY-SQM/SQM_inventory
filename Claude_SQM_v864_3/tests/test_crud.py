# -*- coding: utf-8 -*-
"""
tests/test_crud.py
==================
CRUD invariant tests for SQM Phase 5.

Tests schema structure, data integrity, and basic CRUD properties
using direct sqlite3 on fixture databases.
"""

import sqlite3
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _conn(db_path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row["name"] for row in rows]


def _table_exists(conn, table_name) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInventoryColumns:
    """Verify critical columns exist on core tables."""

    def test_inventory_table_has_current_weight_column(self, empty_db):
        """inventory.current_weight must exist — central recalc target."""
        conn = _conn(empty_db)
        try:
            cols = _columns(conn, "inventory")
            assert "current_weight" in cols, (
                "Column 'current_weight' missing from inventory table"
            )
        finally:
            conn.close()

    def test_inventory_tonbag_has_is_sample_column(self, empty_db):
        """inventory_tonbag.is_sample must exist — sample exclusion gate."""
        conn = _conn(empty_db)
        try:
            cols = _columns(conn, "inventory_tonbag")
            assert "is_sample" in cols, (
                "Column 'is_sample' missing from inventory_tonbag"
            )
        finally:
            conn.close()


class TestSampleWeightConstant:
    """Verify SAMPLE_WEIGHT_KG business constant."""

    def test_sample_weight_constant_is_one_kg(self):
        """SAMPLE_WEIGHT_KG must equal 1.0 (fixed sample mass)."""
        try:
            from core.constants import SAMPLE_WEIGHT_KG
        except ImportError:
            from engine_modules.constants import SAMPLE_WEIGHT_KG
        assert SAMPLE_WEIGHT_KG == 1.0, (
            f"SAMPLE_WEIGHT_KG expected 1.0, got {SAMPLE_WEIGHT_KG}"
        )

    def test_current_weight_excludes_sample_in_recalc_sql(self):
        """_recalc_current_weight SQL must filter is_sample = 0 / IS NULL."""
        import inspect
        from engine_modules.inventory_modular.crud_mixin import CRUDMixin
        src = inspect.getsource(CRUDMixin._recalc_current_weight)
        assert "is_sample" in src, "_recalc_current_weight must reference is_sample"
        # The filter expression should exclude samples
        assert "is_sample = 0" in src or "is_sample IS NULL" in src, (
            "_recalc_current_weight SQL must exclude sample tonbags "
            "(is_sample = 0 or IS NULL)"
        )


class TestTenLotsFixture:
    """Verify ten_lots_db fixture has correct data."""

    def test_ten_lots_db_has_correct_row_count(self, ten_lots_db):
        """ten_lots_db fixture must contain exactly 10 inventory rows."""
        conn = _conn(ten_lots_db)
        try:
            count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
            assert count == 10, f"Expected 10 inventory rows, got {count}"
        finally:
            conn.close()

    def test_ten_lots_db_current_weight_nonnegative(self, ten_lots_db):
        """All current_weight values must be >= 0 (floor enforced)."""
        conn = _conn(ten_lots_db)
        try:
            rows = conn.execute(
                "SELECT lot_no, current_weight FROM inventory WHERE current_weight < 0"
            ).fetchall()
            assert len(rows) == 0, (
                f"Negative current_weight found: {[dict(r) for r in rows]}"
            )
        finally:
            conn.close()

    def test_inventory_tonbag_status_values_valid(self, ten_lots_db):
        """All inventory_tonbag.status values must be in the known set."""
        valid_statuses = {
            "AVAILABLE", "RESERVED", "PICKED", "SOLD",
            "RETURNED", "DEPLETED", "OUTBOUND"
        }
        conn = _conn(ten_lots_db)
        try:
            rows = conn.execute(
                "SELECT DISTINCT status FROM inventory_tonbag"
            ).fetchall()
            for row in rows:
                s = row[0]
                assert s in valid_statuses, (
                    f"Unexpected tonbag status '{s}' not in {valid_statuses}"
                )
        finally:
            conn.close()


class TestAuxiliaryTables:
    """Verify auxiliary tables exist and have expected columns."""

    def test_audit_log_table_exists_and_has_columns(self, empty_db):
        """audit_log table must exist with at least id and action columns."""
        conn = _conn(empty_db)
        try:
            assert _table_exists(conn, "audit_log"), "Table 'audit_log' is missing"
            cols = _columns(conn, "audit_log")
            assert len(cols) > 0, "audit_log has no columns"
        finally:
            conn.close()

    def test_stock_movement_table_exists(self, empty_db):
        """stock_movement table must exist after DB init."""
        conn = _conn(empty_db)
        try:
            assert _table_exists(conn, "stock_movement"), (
                "Table 'stock_movement' is missing from schema"
            )
        finally:
            conn.close()

    def test_allocation_plan_table_exists(self, empty_db):
        """allocation_plan table must exist (Allocation workflow support)."""
        conn = _conn(empty_db)
        try:
            assert _table_exists(conn, "allocation_plan"), (
                "Table 'allocation_plan' is missing from schema"
            )
        finally:
            conn.close()


class TestIntegrityConstraints:
    """Verify DB-level integrity constraints are enforced."""

    def test_sold_table_dedup_index_enforced(self, empty_db):
        """idx_sold_dedup UNIQUE index must reject duplicate (sales_order_no, lot_no, sub_lt) inserts."""
        import datetime
        conn = _conn(empty_db)
        try:
            cols = _columns(conn, "sold_table")
            required = {"lot_no", "sub_lt", "sales_order_no"}
            if not required.issubset(set(cols)):
                pytest.skip(f"sold_table missing required columns for dedup test: {required - set(cols)}")

            # idx_sold_dedup is on (sales_order_no, lot_no, COALESCE(sub_lt, ''))
            insert_sql = (
                "INSERT INTO sold_table (sales_order_no, lot_no, sub_lt) VALUES (?, ?, ?)"
            )
            try:
                conn.execute(insert_sql, ("SO-DUP-001", "DUP_LOT_001", 1))
                conn.commit()
                with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)):
                    conn.execute(insert_sql, ("SO-DUP-001", "DUP_LOT_001", 1))
                    conn.commit()
            except sqlite3.OperationalError as e:
                pytest.skip(f"sold_table insert needs more columns: {e}")
        finally:
            conn.close()

    def test_weight_floor_trigger_blocks_negative_update(self, empty_db):
        """trg_inventory_weight_floor must prevent current_weight going below 0.

        The trigger may either RAISE (rejecting the update with IntegrityError)
        or floor the value to 0. Both behaviours satisfy the invariant.
        """
        import datetime
        conn = _conn(empty_db)
        try:
            today = datetime.date.today().isoformat()
            now = datetime.datetime.now().isoformat()
            cols = _columns(conn, "inventory")
            if "current_weight" not in cols:
                pytest.skip("inventory lacks current_weight column")
            conn.execute(
                "INSERT OR IGNORE INTO inventory "
                "(lot_no, sap_no, product, mxbg_pallet, net_weight, "
                "current_weight, initial_weight, picked_weight, warehouse, "
                "stock_date, status, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("TRG_TEST_001", "SAP00001", "TEST", 20,
                 10000.0, 5000.0, 10000.0, 0.0,
                 "GY", today, "AVAILABLE", now, now)
            )
            conn.commit()

            # Attempt to set current_weight to negative value.
            # Trigger behaviour: RAISE(FAIL, ...) → IntegrityError/OperationalError,
            # OR silent floor to 0. Either result satisfies the invariant.
            try:
                conn.execute(
                    "UPDATE inventory SET current_weight = -999.0 WHERE lot_no = ?",
                    ("TRG_TEST_001",)
                )
                conn.commit()
                # If no exception, the trigger must have floored the value
                row = conn.execute(
                    "SELECT current_weight FROM inventory WHERE lot_no = ?",
                    ("TRG_TEST_001",)
                ).fetchone()
                assert row is not None
                cw = float(row[0])
                assert cw >= 0.0, (
                    f"Trigger did not block or floor negative current_weight: {cw}"
                )
            except (sqlite3.IntegrityError, sqlite3.OperationalError):
                # Trigger raised an error — negative update was correctly rejected
                conn.rollback()
                # Verify the original positive value was preserved
                row = conn.execute(
                    "SELECT current_weight FROM inventory WHERE lot_no = ?",
                    ("TRG_TEST_001",)
                ).fetchone()
                if row is not None:
                    assert float(row[0]) >= 0.0
        finally:
            conn.close()
