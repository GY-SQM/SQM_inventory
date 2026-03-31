# -*- coding: utf-8 -*-
"""
tests/conftest.py
=================
SQM 공통 pytest fixture — v8.2.3
"""
import pytest
import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ── 인메모리 DB fixture ─────────────────────────────────────
@pytest.fixture
def mem_db():
    """전체 스키마를 포함한 인메모리 SQLite DB."""
    from tests.fixtures.sqm_scenario_data import create_scenario_db
    conn = create_scenario_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def bare_db():
    """최소 스키마만 있는 인메모리 SQLite DB (단위 테스트용)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT UNIQUE NOT NULL,
            sap_no TEXT, bl_no TEXT,
            container_no TEXT, container_id TEXT,
            vessel_id TEXT, voyage_no TEXT,
            product TEXT, product_code TEXT,
            lot_sqm TEXT, mxbg_pallet INTEGER DEFAULT 0,
            net_weight REAL DEFAULT 0,
            gross_weight REAL DEFAULT 0,
            current_weight REAL DEFAULT 0,
            initial_weight REAL DEFAULT 0,
            picked_weight REAL DEFAULT 0,
            salar_invoice_no TEXT,
            ship_date TEXT, arrival_date TEXT,
            con_return TEXT, free_time INTEGER DEFAULT 0,
            warehouse TEXT DEFAULT 'GY',
            stock_date TEXT, status TEXT DEFAULT 'AVAILABLE',
            customer TEXT, sale_ref TEXT,
            location TEXT,
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE inventory_tonbag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_id INTEGER,
            lot_no TEXT NOT NULL,
            sub_lt INTEGER NOT NULL DEFAULT 0,
            tonbag_no TEXT, tonbag_uid TEXT,
            weight REAL DEFAULT 0,
            status TEXT DEFAULT 'AVAILABLE',
            is_sample INTEGER DEFAULT 0,
            location TEXT,
            picked_to TEXT, picked_date TEXT,
            sale_ref TEXT, pick_ref TEXT,
            outbound_date TEXT,
            created_at TEXT, updated_at TEXT,
            UNIQUE(lot_no, sub_lt)
        );
        CREATE TABLE allocation_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT, sold_to TEXT, qty_mt REAL,
            status TEXT DEFAULT 'STAGED',
            sale_ref TEXT, bl_no TEXT,
            source TEXT, source_fingerprint TEXT,
            import_batch_id TEXT, line_no INTEGER,
            gate_status TEXT, fail_code TEXT, fail_reason TEXT,
            workflow_status TEXT, export_type TEXT,
            sub_lt INTEGER,
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE stock_movement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT, movement_type TEXT,
            qty_kg REAL, remarks TEXT,
            created_at TEXT
        );
        CREATE TABLE tonbag_move_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT, sub_lt INTEGER,
            from_location TEXT, to_location TEXT,
            moved_by TEXT, move_reason TEXT,
            batch_id TEXT,
            created_at TEXT, location_updated_at TEXT
        );
        CREATE TABLE picking_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT, sub_lt INTEGER,
            tonbag_id INTEGER, tonbag_uid TEXT,
            picking_no TEXT, sales_order_no TEXT,
            status TEXT DEFAULT 'ACTIVE',
            qty_kg REAL, qty_mt REAL,
            customer TEXT, plan_loading TEXT,
            creation_date TEXT, picking_date TEXT,
            is_sample INTEGER DEFAULT 0
        );
        CREATE TABLE allocation_import_batch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT, source_fingerprint TEXT,
            lot_count INTEGER, total_mt REAL,
            status TEXT DEFAULT 'ACTIVE',
            report_path TEXT,
            created_at TEXT, updated_at TEXT
        );
    """)
    conn.commit()
    yield conn
    conn.close()


# ── 엔진 mock fixture ───────────────────────────────────────
@pytest.fixture
def mock_engine(bare_db):
    """DB 어댑터가 연결된 최소 엔진 mock."""
    from unittest.mock import MagicMock, patch
    from engine_modules.database import SQMDatabase

    # DB 어댑터를 bare_db에 연결
    db = MagicMock(spec=SQMDatabase)
    db.conn = bare_db

    def _fetchone(sql, params=()):
        cur = bare_db.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def _fetchall(sql, params=()):
        cur = bare_db.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def _execute(sql, params=()):
        cur = bare_db.execute(sql, params)
        bare_db.commit()
        return cur

    def _executemany(sql, params_list):
        cur = bare_db.executemany(sql, params_list)
        bare_db.commit()
        return cur

    from contextlib import contextmanager

    @contextmanager
    def _transaction(mode='DEFERRED'):
        try:
            yield
            bare_db.commit()
        except Exception:
            bare_db.rollback()
            raise

    db.fetchone    = _fetchone
    db.fetchall    = _fetchall
    db.execute     = _execute
    db.executemany = _executemany
    db.transaction = _transaction

    engine = MagicMock()
    engine.db = db
    return engine


# ── 샘플 LOT 데이터 헬퍼 ───────────────────────────────────
def insert_lot(db_conn, lot_no='GY-2026-0001', product='Lithium Carbonate',
               weight_kg=500.0, tb_count=1, status='AVAILABLE'):
    """테스트용 LOT + 톤백 삽입."""
    import datetime
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db_conn.execute("""
        INSERT OR IGNORE INTO inventory
        (lot_no, product, initial_weight, current_weight, net_weight,
         status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (lot_no, product, weight_kg * tb_count, weight_kg * tb_count,
          weight_kg * tb_count, status, now, now))

    for i in range(1, tb_count + 1):
        db_conn.execute("""
            INSERT OR IGNORE INTO inventory_tonbag
            (lot_no, sub_lt, tonbag_no, tonbag_uid, weight, status,
             is_sample, created_at, updated_at)
            VALUES (?,?,?,?,?,?,0,?,?)
        """, (lot_no, i, f'TB-{lot_no}-{i:03d}',
              f'UID-{lot_no}-{i:03d}', weight_kg,
              status, now, now))

    # 샘플 (sub_lt=0)
    db_conn.execute("""
        INSERT OR IGNORE INTO inventory_tonbag
        (lot_no, sub_lt, tonbag_no, tonbag_uid, weight, status,
         is_sample, created_at, updated_at)
        VALUES (?,0,'SAMPLE-?','SUID-?',1.0,'AVAILABLE',1,?,?)
    """, (lot_no, now, now))

    db_conn.commit()
