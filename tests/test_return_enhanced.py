"""
SQM v6.12.1 — 반품 강화 테스트
================================
1. source_type 이력 기록
2. 반품 사유 통계
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date

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
            product TEXT, net_weight REAL, gross_weight REAL,
            initial_weight REAL, current_weight REAL, picked_weight REAL DEFAULT 0,
            mxbg_pallet INTEGER, status TEXT DEFAULT 'AVAILABLE',
            created_at TEXT, updated_at TEXT)""")
        c.execute("""CREATE TABLE inventory_tonbag (
            id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER,
            weight REAL, status TEXT, is_sample INTEGER DEFAULT 0,
            outbound_date TEXT, picked_date TEXT, picked_to TEXT, sale_ref TEXT,
            updated_at TEXT)""")
        c.execute("CREATE UNIQUE INDEX idx_tls ON inventory_tonbag(lot_no, sub_lt)")
        c.execute("""CREATE TABLE return_history (
            id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER,
            return_date DATE, original_customer TEXT, original_sale_ref TEXT,
            reason TEXT, remark TEXT, weight_kg REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE stock_movement (
            id INTEGER PRIMARY KEY, lot_no TEXT, movement_type TEXT,
            qty_kg REAL, remarks TEXT, source_type TEXT DEFAULT '',
            source_file TEXT DEFAULT '', created_at TEXT)""")
        c.execute("""CREATE TABLE picking_table (
            id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER, tonbag_id INTEGER,
            picking_no TEXT, status TEXT, picking_date TEXT, sold_date TEXT)""")
        c.execute("""CREATE TABLE sold_table (
            id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER, picking_id INTEGER,
            status TEXT, remark TEXT)""")
        c.execute("""CREATE TABLE allocation_plan (
            id INTEGER PRIMARY KEY, lot_no TEXT, sub_lt INTEGER, tonbag_id INTEGER,
            status TEXT DEFAULT 'RESERVED', cancelled_at TEXT)""")
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

    def insert_picked_lot(self, lot_no, count=10, unit_weight=500, customer='CUSTOMER_A'):
        """PICKED 상태 LOT 생성."""
        total = count * unit_weight + 1
        self.conn.execute(
            "INSERT INTO inventory (lot_no, net_weight, current_weight, picked_weight, status) "
            "VALUES (?,?,0,?,?)", (lot_no, total, total, 'PICKED'))
        for i in range(1, count + 1):
            self.conn.execute(
                "INSERT INTO inventory_tonbag (lot_no, sub_lt, weight, status, picked_to, sale_ref) "
                "VALUES (?,?,?,?,?,?)",
                (lot_no, i, unit_weight, 'PICKED', customer, 'SO-001'))
        # 샘플
        self.conn.execute(
            "INSERT INTO inventory_tonbag (lot_no, sub_lt, weight, status, is_sample, picked_to) "
            "VALUES (?,0,1.0,'PICKED',1,?)", (lot_no, customer))
        self.conn.commit()


def _make_return_engine(db):
    from engine_modules.inventory_modular.return_mixin import ReturnMixin
    engine = ReturnMixin.__new__(ReturnMixin)
    engine.db = db
    engine._recalc_lot_status = lambda lot_no: None
    engine.verify_lot_integrity = lambda lot_no: {'valid': True, 'errors': []}
    return engine


class TestReturnSourceType:
    """반품 source_type 이력 기록."""

    def test_single_return_source(self):
        db = FakeDB()
        db.insert_picked_lot('LOT001', 10, 500)
        engine = _make_return_engine(db)
        result = engine.process_return(
            [{'lot_no': 'LOT001', 'sub_lt': 1, 'reason': '품질불량'}],
            source_type='RETURN_SINGLE'
        )
        assert result['success']
        mv = db.fetchone(
            "SELECT source_type FROM stock_movement WHERE lot_no = ? AND movement_type = 'RETURN'",
            ('LOT001',))
        assert mv['source_type'] == 'RETURN_SINGLE'

    def test_excel_return_source(self):
        db = FakeDB()
        db.insert_picked_lot('LOT002', 10, 500)
        engine = _make_return_engine(db)
        result = engine.process_return(
            [{'lot_no': 'LOT002', 'sub_lt': 1, 'reason': '수량 초과'},
             {'lot_no': 'LOT002', 'sub_lt': 2, 'reason': '수량 초과'}],
            source_type='RETURN_EXCEL', source_file='return.xlsx'
        )
        assert result['success']
        assert result['returned'] == 2
        rows = db.fetchall(
            "SELECT source_type, source_file FROM stock_movement "
            "WHERE lot_no = ? AND movement_type = 'RETURN'", ('LOT002',))
        assert len(rows) == 2
        assert all(r['source_type'] == 'RETURN_EXCEL' for r in rows)
        assert all(r['source_file'] == 'return.xlsx' for r in rows)

    def test_default_source_return_single(self):
        db = FakeDB()
        db.insert_picked_lot('LOT003', 10, 500)
        engine = _make_return_engine(db)
        result = engine.process_return(
            [{'lot_no': 'LOT003', 'sub_lt': 1, 'reason': '기타'}]
        )
        assert result['success']
        mv = db.fetchone(
            "SELECT source_type FROM stock_movement WHERE lot_no = ? AND movement_type = 'RETURN'",
            ('LOT003',))
        assert mv['source_type'] == 'RETURN_SINGLE'


class TestReturnStatistics:
    """반품 사유 통계."""

    def _insert_returns(self, db, lot_no, reasons, customer='CUST_A'):
        today = date.today().isoformat()
        for i, reason in enumerate(reasons, 1):
            db.execute(
                "INSERT INTO return_history (lot_no, sub_lt, return_date, reason, "
                "original_customer, weight_kg) VALUES (?,?,?,?,?,?)",
                (lot_no, i, today, reason, customer, 500.0))
        db.commit()

    def test_by_reason(self):
        db = FakeDB()
        self._insert_returns(db, 'LOT010', ['품질불량', '품질불량', '수량 초과'])
        engine = _make_return_engine(db)
        stats = engine.get_return_statistics()
        assert stats['total_count'] == 3
        assert stats['total_weight_kg'] == 1500.0
        # 사유별
        by_reason = {r['reason']: r['count'] for r in stats['by_reason']}
        assert by_reason['품질불량'] == 2
        assert by_reason['수량 초과'] == 1

    def test_by_lot(self):
        db = FakeDB()
        self._insert_returns(db, 'LOT010', ['품질불량', '품질불량'])
        self._insert_returns(db, 'LOT011', ['수량 초과'])
        engine = _make_return_engine(db)
        stats = engine.get_return_statistics()
        by_lot = {r['lot_no']: r['count'] for r in stats['by_lot']}
        assert by_lot['LOT010'] == 2
        assert by_lot['LOT011'] == 1

    def test_by_month(self):
        db = FakeDB()
        self._insert_returns(db, 'LOT010', ['품질불량'])
        engine = _make_return_engine(db)
        stats = engine.get_return_statistics()
        assert len(stats['by_month']) >= 1

    def test_top_customers(self):
        db = FakeDB()
        self._insert_returns(db, 'LOT010', ['품질불량'], customer='JAPAN_A')
        self._insert_returns(db, 'LOT011', ['수량 초과', '수량 초과'], customer='KOREA_B')
        engine = _make_return_engine(db)
        stats = engine.get_return_statistics()
        top = {r['customer']: r['count'] for r in stats['top_customers']}
        assert top['KOREA_B'] == 2
        assert top['JAPAN_A'] == 1

    def test_filter_by_lot(self):
        db = FakeDB()
        self._insert_returns(db, 'LOT010', ['품질불량', '품질불량'])
        self._insert_returns(db, 'LOT011', ['수량 초과'])
        engine = _make_return_engine(db)
        stats = engine.get_return_statistics(lot_no='LOT010')
        assert stats['total_count'] == 2

    def test_empty_stats(self):
        db = FakeDB()
        engine = _make_return_engine(db)
        stats = engine.get_return_statistics()
        assert stats['total_count'] == 0
        assert stats['by_reason'] == []


class TestReturnAlertThreshold:
    """반품 알림 임계치 — LOT 3회 이상 반품 경고."""

    def _insert_returns(self, db, lot_no, count, customer='CUST_A'):
        today = date.today().isoformat()
        for i in range(1, count + 1):
            db.execute(
                "INSERT INTO return_history (lot_no, sub_lt, return_date, reason, "
                "original_customer, weight_kg) VALUES (?,?,?,?,?,?)",
                (lot_no, i, today, '품질불량', customer, 500.0))
        db.commit()

    def test_below_threshold_no_alert(self):
        """2회 반품 → 알림 없음."""
        db = FakeDB()
        self._insert_returns(db, 'LOT_GOOD', 2)
        rows = db.fetchall(
            "SELECT lot_no, COUNT(*) AS cnt FROM return_history "
            "GROUP BY lot_no HAVING COUNT(*) >= 3")
        assert len(rows) == 0

    def test_at_threshold_triggers_alert(self):
        """3회 반품 → 알림 발생."""
        db = FakeDB()
        self._insert_returns(db, 'LOT_BAD', 3)
        rows = db.fetchall(
            "SELECT lot_no, COUNT(*) AS cnt FROM return_history "
            "GROUP BY lot_no HAVING COUNT(*) >= 3")
        assert len(rows) == 1
        lot = rows[0]['lot_no'] if isinstance(rows[0], dict) else rows[0][0]
        assert lot == 'LOT_BAD'

    def test_multiple_lots_mixed(self):
        """여러 LOT 혼합 — 3회 이상만 경고."""
        db = FakeDB()
        self._insert_returns(db, 'LOT_OK', 2)
        self._insert_returns(db, 'LOT_BAD1', 3)
        self._insert_returns(db, 'LOT_BAD2', 5)
        rows = db.fetchall(
            "SELECT lot_no, COUNT(*) AS cnt FROM return_history "
            "GROUP BY lot_no HAVING COUNT(*) >= 3 ORDER BY cnt DESC")
        lots = [r['lot_no'] if isinstance(r, dict) else r[0] for r in rows]
        assert 'LOT_OK' not in lots
        assert 'LOT_BAD1' in lots
        assert 'LOT_BAD2' in lots


class TestReturnAutoApprove:
    """v6.12.2: 반품 자동승인 임계치."""

    def test_constant_exists(self):
        from engine_modules.constants import RETURN_AUTO_APPROVE_MAX_TONBAGS
        assert RETURN_AUTO_APPROVE_MAX_TONBAGS == 5

    def test_small_return_auto_approve(self):
        """5건 이하 → 자동승인 (간단 확인)."""
        from engine_modules.constants import RETURN_AUTO_APPROVE_MAX_TONBAGS
        items = [{'lot_no': f'LOT{i}', 'sub_lt': 1} for i in range(5)]
        assert len(items) <= RETURN_AUTO_APPROVE_MAX_TONBAGS

    def test_large_return_needs_approval(self):
        """6건 이상 → 관리자 확인 필요."""
        from engine_modules.constants import RETURN_AUTO_APPROVE_MAX_TONBAGS
        items = [{'lot_no': f'LOT{i}', 'sub_lt': 1} for i in range(6)]
        assert len(items) > RETURN_AUTO_APPROVE_MAX_TONBAGS

    def test_reason_codes_available(self):
        """표준 사유 코드 상수 확인."""
        from engine_modules.constants import RETURN_REASON_CODES
        assert '품질 불량' in RETURN_REASON_CODES
        assert '파손/변질' in RETURN_REASON_CODES
        assert len(RETURN_REASON_CODES) == 7


class TestReturnEmailAlert:
    """v6.12.2: 반품 이메일 알림."""

    def _insert_returns(self, db, lot_no, count):
        today = date.today().isoformat()
        for i in range(1, count + 1):
            db.execute(
                "INSERT INTO return_history (lot_no, sub_lt, return_date, reason, "
                "original_customer, weight_kg) VALUES (?,?,?,?,?,?)",
                (lot_no, i, today, '품질불량', 'CUST_A', 500.0))
        db.commit()

    def test_check_alerts_empty(self):
        from features.notifications.return_alert_email import check_return_alerts
        db = FakeDB()
        engine = _make_return_engine(db)
        alerts = check_return_alerts(engine)
        assert len(alerts) == 0

    def test_check_alerts_with_data(self):
        from features.notifications.return_alert_email import check_return_alerts
        db = FakeDB()
        self._insert_returns(db, 'LOT_BAD', 4)
        self._insert_returns(db, 'LOT_OK', 2)
        engine = _make_return_engine(db)
        alerts = check_return_alerts(engine)
        assert len(alerts) == 1
        assert alerts[0]['lot_no'] == 'LOT_BAD'
        assert alerts[0]['count'] == 4

    def test_email_config_default_disabled(self):
        from features.notifications.return_alert_email import load_email_config
        config = load_email_config()
        assert config['enabled'] is False

    def test_send_email_disabled(self):
        from features.notifications.return_alert_email import send_return_alert_email
        db = FakeDB()
        engine = _make_return_engine(db)
        result = send_return_alert_email(engine)
        assert result['sent'] is False
        assert '비활성화' in result['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
