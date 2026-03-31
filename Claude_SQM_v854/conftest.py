# -*- coding: utf-8 -*-
"""
SQM v7.0.0 — pytest conftest.py
================================
- pytest.ini pythonpath=. 설정으로 루트 자동 인식
- gui_app_modular/handlers 경로 보강 (test_inbound_doc_detector용)
- MockDB fixture 공용 제공
"""
import os
import sys
import sqlite3
import pytest

# handlers 경로만 추가 (test_inbound_doc_detector 전용)
_ROOT = os.path.dirname(os.path.abspath(__file__))
_HANDLERS = os.path.join(_ROOT, 'gui_app_modular', 'handlers')
if _HANDLERS not in sys.path:
    sys.path.insert(0, _HANDLERS)


@pytest.fixture
def mock_db_conn():
    """SQLite in-memory DB — allocation_plan 포함"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('''
        CREATE TABLE IF NOT EXISTS allocation_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT NOT NULL,
            customer TEXT,
            qty_mt REAL,
            status TEXT DEFAULT "PENDING",
            export_type TEXT DEFAULT "D",
            source TEXT DEFAULT "MANUAL",
            line_no INTEGER,
            workflow_status TEXT DEFAULT "PENDING",
            fail_code TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT "AVAILABLE",
            current_weight REAL DEFAULT 0.0,
            arrival_date TEXT,
            ship_date TEXT,
            stock_date TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS inventory_tonbag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT NOT NULL,
            tonbag_no TEXT,
            sub_lt INTEGER DEFAULT 0,
            is_sample INTEGER DEFAULT 0,
            location TEXT,
            warehouse TEXT,
            status TEXT DEFAULT "AVAILABLE",
            weight REAL DEFAULT 0.0
        )
    ''')
    conn.commit()
    yield conn
    conn.close()
