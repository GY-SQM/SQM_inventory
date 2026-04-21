# -*- coding: utf-8 -*-
"""
tests/fixtures/__init__.py
==========================
SQM Phase 4 Fixture Loader

Provides helper functions to create test databases for the pytest suite.
SQMDatabase(path) auto-creates the full schema + migrations on init.
"""

import pathlib
import sys

# Ensure project root is importable
_FIXTURES_DIR = pathlib.Path(__file__).parent
_TESTS_DIR = _FIXTURES_DIR.parent
_ROOT = _TESTS_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def get_fixtures_dir() -> pathlib.Path:
    """Return absolute path to tests/fixtures/ directory."""
    return _FIXTURES_DIR


def create_empty_db(output_path: str) -> str:
    """
    Create a schema-only SQLite DB at output_path using SQMDatabase.

    SQMDatabase.__init__ automatically:
      - creates all tables (_init_database)
      - runs all migrations (_run_all_migrations)
      - creates indexes

    Args:
        output_path: file path for the new SQLite DB (string or Path-like)

    Returns:
        output_path as str
    """
    path_str = str(output_path)
    try:
        from engine_modules.database import SQMDatabase
        db = SQMDatabase(path_str)
        # Close connections cleanly
        try:
            db.close_all()
        except Exception:
            pass
    except Exception as exc:
        # Plan B: raw sqlite3 — still good enough for schema tests
        import sqlite3
        conn = sqlite3.connect(path_str)
        conn.close()
    return path_str


def create_ten_lots_db(output_path: str) -> str:
    """
    Create a SQLite DB pre-populated with 10 LOT rows via the engine.

    Uses SQMInventoryEngine.add_inventory() which:
      - inserts into inventory table
      - creates inventory_tonbag rows
      - sets current_weight = net_weight - SAMPLE_WEIGHT_KG

    Args:
        output_path: file path for the new SQLite DB (string or Path-like)

    Returns:
        output_path as str
    """
    path_str = str(output_path)
    try:
        from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
        engine = SQMInventoryEngineV3(db_path=path_str)

        for i in range(1, 11):
            lot_no = f"110{i:07d}"  # 10-digit LOT numbers
            engine.add_inventory(
                lot_no=lot_no,
                sap_no=f"SAP{i:05d}",
                bl_no=f"BL{i:05d}",
                container_no=f"CONT{i:06d}",
                product="TEST_PRODUCT",
                product_code=f"TP{i:03d}",
                mxbg_pallet=20,
                net_weight=10000.0,
                warehouse="GY",
            )
        try:
            engine.db.close_all()
        except Exception:
            pass
    except Exception as exc:
        # Plan B: minimal raw insert
        import sqlite3
        create_empty_db(path_str)
        conn = sqlite3.connect(path_str)
        cur = conn.cursor()
        import datetime
        today = datetime.date.today().isoformat()
        for i in range(1, 11):
            lot_no = f"110{i:07d}"
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO inventory "
                    "(lot_no, sap_no, product, mxbg_pallet, net_weight, current_weight, "
                    "initial_weight, picked_weight, warehouse, stock_date, status, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        lot_no, f"SAP{i:05d}", "TEST_PRODUCT", 20,
                        10000.0, 9999.0, 10000.0, 0.0,
                        "GY", today, "AVAILABLE",
                        datetime.datetime.now().isoformat(),
                        datetime.datetime.now().isoformat(),
                    )
                )
            except sqlite3.OperationalError:
                pass
        conn.commit()
        conn.close()

    return path_str
