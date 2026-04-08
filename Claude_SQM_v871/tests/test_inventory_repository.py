# -*- coding: utf-8 -*-
"""P2-C-03 — InventoryRepository Pilot 테스트."""
import sqlite3
from features.repositories.inventory_repository import InventoryRepository


def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE inventory (
        lot_no TEXT PRIMARY KEY, product TEXT, current_weight REAL, initial_weight REAL,
        picked_weight REAL DEFAULT 0, status TEXT DEFAULT 'AVAILABLE'
    )""")
    conn.execute("""CREATE TABLE inventory_tonbag (
        id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER, weight REAL,
        status TEXT DEFAULT 'AVAILABLE', is_sample INTEGER DEFAULT 0
    )""")
    return conn


def test_import():
    assert InventoryRepository is not None


def test_get_inventory_summary():
    conn = _make_conn()
    conn.execute("INSERT INTO inventory (lot_no, product, current_weight) VALUES ('L1', 'LC', 5000)")
    conn.execute("INSERT INTO inventory (lot_no, product, current_weight) VALUES ('L2', 'LC', 3000)")
    conn.commit()
    repo = InventoryRepository(conn)
    rows = repo.get_inventory_summary()
    assert len(rows) == 1
    r = dict(rows[0])
    assert r['item_count'] == 2
    assert r['total_weight'] == 8000


def test_get_lot_by_no():
    conn = _make_conn()
    conn.execute("INSERT INTO inventory (lot_no, product, current_weight) VALUES ('L1', 'LC', 5000)")
    conn.commit()
    repo = InventoryRepository(conn)
    lot = repo.get_lot_by_no('L1')
    assert lot is not None
    assert lot['product'] == 'LC'


def test_get_lot_by_no_not_found():
    conn = _make_conn()
    repo = InventoryRepository(conn)
    assert repo.get_lot_by_no('NOEXIST') is None


def test_lot_exists():
    conn = _make_conn()
    conn.execute("INSERT INTO inventory (lot_no, product, current_weight) VALUES ('L1', 'LC', 5000)")
    conn.commit()
    repo = InventoryRepository(conn)
    assert repo.lot_exists('L1') is True
    assert repo.lot_exists('L99') is False


def test_tonbag_status_summary():
    conn = _make_conn()
    conn.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, weight, status) VALUES ('L1', 1, 500, 'AVAILABLE')")
    conn.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, weight, status) VALUES ('L1', 2, 500, 'AVAILABLE')")
    conn.execute("INSERT INTO inventory_tonbag (lot_no, sub_lt, weight, status) VALUES ('L1', 3, 500, 'PICKED')")
    conn.commit()
    repo = InventoryRepository(conn)
    summary = repo.get_tonbag_status_summary('L1')
    assert summary.get('AVAILABLE') == 2
    assert summary.get('PICKED') == 1
