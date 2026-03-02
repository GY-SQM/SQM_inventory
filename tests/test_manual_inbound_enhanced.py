"""
SQM v6.12.1 — 수동입고 강화 테스트
===================================
1. SAP 번호 중복 경고
2. B/L 형식 검증
3. source_type 이력 기록
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class FakeDB:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self._setup()

    def _setup(self):
        c = self.conn
        c.execute("""CREATE TABLE inventory (
            id INTEGER PRIMARY KEY, lot_no TEXT UNIQUE, sap_no TEXT, bl_no TEXT,
            product TEXT, product_code TEXT, lot_sqm TEXT,
            mxbg_pallet INTEGER, net_weight REAL, gross_weight REAL,
            initial_weight REAL, current_weight REAL, picked_weight REAL DEFAULT 0,
            salar_invoice_no TEXT, ship_date TEXT, arrival_date TEXT,
            free_time INTEGER, free_time_date TEXT, warehouse TEXT,
            container_no TEXT, vessel TEXT, stock_date TEXT, location TEXT,
            remark TEXT, status TEXT DEFAULT 'AVAILABLE',
            con_return TEXT, inbound_date TEXT,
            created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE inventory_tonbag (
            id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER,
            weight REAL, status TEXT, is_sample INTEGER DEFAULT 0,
            tonbag_uid TEXT, inventory_id INTEGER,
            sap_no TEXT, bl_no TEXT, tonbag_no TEXT,
            picked_date TEXT, con_return TEXT, inbound_date TEXT,
            created_at TEXT, updated_at TEXT)""")
        c.execute("CREATE UNIQUE INDEX idx_tonbag_lot_sublt ON inventory_tonbag(lot_no, sub_lt)")
        c.execute("""CREATE TABLE stock_movement (
            id INTEGER PRIMARY KEY, lot_no TEXT, movement_type TEXT,
            qty_kg REAL, from_location TEXT, to_location TEXT,
            customer TEXT, movement_date TEXT, remarks TEXT,
            source_type TEXT DEFAULT '', source_file TEXT DEFAULT '',
            created_at TEXT)""")
        c.commit()

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def fetchone(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    class _TxCtx:
        def __init__(self, conn):
            self.conn = conn
        def __enter__(self): return self
        def __exit__(self, *a):
            if a[0]: self.conn.rollback()
            else: self.conn.commit()

    def transaction(self, mode=''):
        return self._TxCtx(self.conn)

    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()


def _make_engine(db):
    from engine_modules.inventory_modular.inbound_mixin import InboundMixin
    engine = InboundMixin.__new__(InboundMixin)
    engine.db = db
    engine._log_operation = lambda *a, **kw: None
    return engine


class TestSAPDuplicateWarning:
    """SAP 번호 중복 경고."""

    def test_first_lot_no_warning(self):
        db = FakeDB()
        engine = _make_engine(db)
        result = engine.process_inbound({
            'lot_no': '1125072350', 'sap_no': 'SAP001', 'net_weight': 5001,
            'mxbg_pallet': 10, 'product': 'LC'
        }, source_type='EXCEL_MANUAL')
        assert result['success']
        assert not any('SAP 번호 중복' in w for w in result['warnings'])

    def test_second_lot_same_sap_warning(self):
        db = FakeDB()
        engine = _make_engine(db)
        # 첫 번째 LOT
        r1 = engine.process_inbound({
            'lot_no': '1125072350', 'sap_no': 'SAP001', 'net_weight': 5001,
            'mxbg_pallet': 10, 'product': 'LC'
        })
        assert r1['success']
        # 두 번째 LOT — 동일 SAP
        r2 = engine.process_inbound({
            'lot_no': '1125072351', 'sap_no': 'SAP001', 'net_weight': 5001,
            'mxbg_pallet': 10, 'product': 'LC'
        })
        assert r2['success']
        assert any('SAP 번호 중복' in w for w in r2['warnings'])


class TestBLFormatWarning:
    """B/L 형식 검증."""

    def test_standard_bl_no_warning(self):
        db = FakeDB()
        engine = _make_engine(db)
        result = engine.process_inbound({
            'lot_no': '1125072360', 'bl_no': 'HDMU1234567', 'net_weight': 5001,
            'mxbg_pallet': 10
        })
        assert result['success']
        assert not any('B/L 번호 형식' in w for w in result['warnings'])

    def test_nonstandard_bl_warning(self):
        db = FakeDB()
        engine = _make_engine(db)
        result = engine.process_inbound({
            'lot_no': '1125072361', 'bl_no': 'ABC123', 'net_weight': 5001,
            'mxbg_pallet': 10
        })
        assert result['success']
        assert any('B/L 번호 형식' in w for w in result['warnings'])


class TestSourceType:
    """source_type 이력 기록."""

    def test_excel_manual_source(self):
        db = FakeDB()
        engine = _make_engine(db)
        result = engine.process_inbound({
            'lot_no': '1125072370', 'net_weight': 5001, 'mxbg_pallet': 10
        }, source_type='EXCEL_MANUAL', source_file='test.xlsx')
        assert result['success']
        mv = db.fetchone(
            "SELECT source_type, source_file FROM stock_movement WHERE lot_no = ?",
            ('1125072370',))
        assert mv['source_type'] == 'EXCEL_MANUAL'
        assert mv['source_file'] == 'test.xlsx'

    def test_pdf_source(self):
        db = FakeDB()
        engine = _make_engine(db)
        result = engine.process_inbound({
            'lot_no': '1125072371', 'net_weight': 5001, 'mxbg_pallet': 10
        }, source_type='PDF', source_file='invoice.pdf')
        assert result['success']
        mv = db.fetchone(
            "SELECT source_type FROM stock_movement WHERE lot_no = ?",
            ('1125072371',))
        assert mv['source_type'] == 'PDF'

    def test_paste_source(self):
        db = FakeDB()
        engine = _make_engine(db)
        result = engine.process_inbound({
            'lot_no': '1125072372', 'net_weight': 5001, 'mxbg_pallet': 10
        }, source_type='EXCEL_PASTE', source_file='(붙여넣기)')
        assert result['success']
        mv = db.fetchone(
            "SELECT source_type, source_file FROM stock_movement WHERE lot_no = ?",
            ('1125072372',))
        assert mv['source_type'] == 'EXCEL_PASTE'

    def test_default_source_unknown(self):
        db = FakeDB()
        engine = _make_engine(db)
        result = engine.process_inbound({
            'lot_no': '1125072373', 'net_weight': 5001, 'mxbg_pallet': 10
        })
        assert result['success']
        mv = db.fetchone(
            "SELECT source_type FROM stock_movement WHERE lot_no = ?",
            ('1125072373',))
        assert mv['source_type'] == 'UNKNOWN'


class TestTonbagPrinciple:
    """대원칙 검증 — source_type과 무관하게 동일."""

    def test_5001kg_10bags(self):
        db = FakeDB()
        engine = _make_engine(db)
        result = engine.process_inbound({
            'lot_no': '1125072380', 'net_weight': 5001, 'mxbg_pallet': 10
        }, source_type='EXCEL_MANUAL')
        assert result['success']
        assert result['created_tonbags'] == 11  # 10 톤백 + 1 샘플
        # 무게 합계 = 5001
        row = db.fetchone(
            "SELECT SUM(weight) as total FROM inventory_tonbag WHERE lot_no = ?",
            ('1125072380',))
        assert abs(row['total'] - 5001.0) < 0.1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
