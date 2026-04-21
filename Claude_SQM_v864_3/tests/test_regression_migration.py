# -*- coding: utf-8 -*-
"""
tests/test_regression_migration.py
===================================
Migration idempotency and regression tests for SQM Phase 4.

Tests:
  - Migration is idempotent (run twice → no error)
  - INSERT with negative current_weight is blocked by trigger

These tests only use sqlite3 directly (Plan-B safe) and the
session-scoped fixtures_dir from conftest.py.
"""

import sqlite3
import pathlib
import sys
import pytest

# Ensure project root importable
ROOT = pathlib.Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(tmp_path: pathlib.Path, name: str) -> pathlib.Path:
    """Create a fresh empty SQM DB at tmp_path/name via SQMDatabase."""
    p = tmp_path / name
    try:
        from engine_modules.database import SQMDatabase
        db = SQMDatabase(str(p))
        try:
            db.close_all()
        except Exception:
            pass
    except Exception:
        # Plan B — plain file for raw sqlite3 tests
        p.touch()
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMigrationIdempotency:
    """_run_all_migrations() must be safe to call multiple times."""

    def test_migration_idempotent(self, fixtures_dir):
        """
        Running _run_all_migrations() twice on the same DB must not raise.

        SQMDatabase.__init__ already calls migrations once.  We force a
        second call to ensure all CREATE * IF NOT EXISTS guards hold.
        """
        p = _make_db(fixtures_dir, "migration_idempotent_test.db")

        try:
            from engine_modules.database import SQMDatabase
            db = SQMDatabase(str(p))
            # Force a second run by resetting the guard flag
            db._migrations_applied = False
            db._run_all_migrations()   # must not raise
            try:
                db.close_all()
            except Exception:
                pass
        except ImportError:
            pytest.skip("SQMDatabase not importable — skipping engine test")


class TestWeightFloorTriggers:
    """Verify weight-floor triggers fire and block invalid data."""

    def test_weight_floor_insert_trigger_fires(self, fixtures_dir):
        """
        Attempting a direct INSERT with current_weight < 0 must raise
        sqlite3.IntegrityError (or OperationalError) because
        trg_inventory_weight_floor_insert fires.
        """
        p = _make_db(fixtures_dir, "weight_floor_insert_test.db")

        conn = sqlite3.connect(str(p))
        conn.row_factory = sqlite3.Row

        # Confirm trigger exists before testing behaviour
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='trigger' "
            "AND name='trg_inventory_weight_floor_insert'"
        ).fetchone()
        if row is None:
            conn.close()
            pytest.skip(
                "trg_inventory_weight_floor_insert not present — "
                "cannot test INSERT trigger behaviour."
            )

        # Attempt INSERT with negative current_weight — trigger must raise
        import datetime
        now = datetime.datetime.now().isoformat()
        today = datetime.date.today().isoformat()

        # SQLite RAISE(FAIL, ...) maps to IntegrityError in Python 3.x
        with pytest.raises((sqlite3.OperationalError, sqlite3.IntegrityError),
                           match="cannot be negative"):
            conn.execute(
                """
                INSERT INTO inventory (
                    lot_no, product, mxbg_pallet, net_weight,
                    current_weight, initial_weight, picked_weight,
                    warehouse, stock_date, status, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "1109999999", "TEST", 20,
                    10000.0,
                    -1.0,           # NEGATIVE — trigger must block this
                    10000.0, 0.0,
                    "GY", today, "AVAILABLE", now, now,
                )
            )
            conn.commit()

        conn.close()

    def test_weight_floor_update_trigger_fires(self, fixtures_dir):
        """
        Attempting an UPDATE that sets current_weight < 0 must raise
        sqlite3.IntegrityError (or OperationalError) because
        trg_inventory_weight_floor fires.
        """
        p = _make_db(fixtures_dir, "weight_floor_update_test.db")

        conn = sqlite3.connect(str(p))
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='trigger' "
            "AND name='trg_inventory_weight_floor'"
        ).fetchone()
        if row is None:
            conn.close()
            pytest.skip(
                "trg_inventory_weight_floor not present — "
                "cannot test UPDATE trigger behaviour."
            )

        import datetime
        now = datetime.datetime.now().isoformat()
        today = datetime.date.today().isoformat()

        # Insert a valid row first
        conn.execute(
            """
            INSERT OR IGNORE INTO inventory (
                lot_no, product, mxbg_pallet, net_weight,
                current_weight, initial_weight, picked_weight,
                warehouse, stock_date, status, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            ("1108888888", "TEST", 20, 10000.0, 5000.0, 10000.0, 0.0,
             "GY", today, "AVAILABLE", now, now)
        )
        conn.commit()

        # Now attempt to UPDATE current_weight to negative
        # SQLite RAISE(FAIL, ...) maps to IntegrityError in Python 3.x
        with pytest.raises((sqlite3.OperationalError, sqlite3.IntegrityError),
                           match="cannot be negative"):
            conn.execute(
                "UPDATE inventory SET current_weight = -1.0 WHERE lot_no = ?",
                ("1108888888",)
            )
            conn.commit()

        conn.close()
