# -*- coding: utf-8 -*-
"""
P2 Batch B — Outbound 분리 모듈 테스트.
"""
import sqlite3
import pytest


# ═══════════════════════════════════════════════
# OutboundStateRules 테스트
# ═══════════════════════════════════════════════

class TestOutboundStateRules:

    def test_import(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules is not None

    def test_risk_flags_none(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        flags = OutboundStateRules.allocation_risk_flags(1000, 50000)
        assert flags == []

    def test_risk_flags_large_volume(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        flags = OutboundStateRules.allocation_risk_flags(25000, 50000)
        assert "LARGE_VOLUME" in flags

    def test_requires_approval(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules.allocation_requires_approval(25000, 50000) is True
        assert OutboundStateRules.allocation_requires_approval(1000, 50000) is False

    def test_normalize_outbound_date_valid(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules.normalize_outbound_date("2025-06-15") == "2025-06-15"

    def test_normalize_outbound_date_invalid(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        with pytest.raises(ValueError):
            OutboundStateRules.normalize_outbound_date("abc")

    def test_normalize_outbound_date_empty(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        result = OutboundStateRules.normalize_outbound_date("")
        # Should return today's date
        import datetime
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        assert result == today

    def test_random_mode(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        mode = OutboundStateRules.get_allocation_random_mode()
        assert mode in ("random", "seeded")

    def test_strict_mode(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        mode = OutboundStateRules.get_allocation_strict_mode()
        assert isinstance(mode, bool)

    def test_reservation_mode(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules.get_allocation_reservation_mode() == "lot"
        assert OutboundStateRules.get_allocation_reservation_mode("tonbag") == "lot"

    def test_compute_lot_status_available(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        status = OutboundStateRules.compute_lot_status({'AVAILABLE': 10}, 5000)
        assert status == 'AVAILABLE'

    def test_compute_lot_status_partial(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        status = OutboundStateRules.compute_lot_status({'AVAILABLE': 5, 'OUTBOUND': 5}, 2500)
        assert status == 'PARTIAL'

    def test_compute_lot_status_outbound(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        status = OutboundStateRules.compute_lot_status({'OUTBOUND': 10}, 0)
        assert status == 'OUTBOUND'

    def test_compute_lot_status_depleted(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        status = OutboundStateRules.compute_lot_status({}, 0)
        assert status == 'DEPLETED'

    def test_build_allocation_seed(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        seed = OutboundStateRules.build_allocation_seed('LOT001', 'SR001', 5.0, '2025-01-01', 'test.xlsx')
        assert isinstance(seed, str) and len(seed) == 40

    def test_alloc_val_dict(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules.alloc_val({'lot_no': 'L1'}, 'lot_no') == 'L1'
        assert OutboundStateRules.alloc_val({'lot_no': 'L1'}, 'missing', 'default') == 'default'

    def test_parse_allocation_line(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        alloc = {'lot_no': 'LOT001', 'sold_to': 'CUSTOMER1', 'sale_ref': 'SR001',
                 'qty_mt': 5.0, 'outbound_date': '2025-01-01'}
        result = OutboundStateRules.parse_allocation_line(alloc)
        assert result['lot_no'] == 'LOT001'
        assert result['qty_mt'] == 5.0

    def test_validate_line_inputs_ok(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        ctx = {'lot_no': 'L1', 'customer': 'C1', 'qty_mt': 5.0, 'sale_ref': 'SR1', 'unit_val': ''}
        code, msg = OutboundStateRules.validate_line_inputs(ctx, 1)
        assert code == ""

    def test_validate_line_inputs_missing_lot(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        ctx = {'lot_no': '', 'customer': 'C1', 'qty_mt': 5.0, 'sale_ref': 'SR1', 'unit_val': ''}
        code, msg = OutboundStateRules.validate_line_inputs(ctx, 1)
        assert code == "INVALID_LOT"

    def test_validate_line_inputs_zero_qty(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        ctx = {'lot_no': 'L1', 'customer': 'C1', 'qty_mt': 0, 'sale_ref': 'SR1', 'unit_val': ''}
        code, msg = OutboundStateRules.validate_line_inputs(ctx, 1)
        assert code == "ZERO_QTY"

    def test_source_fingerprint_paste(self):
        from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules
        rows = [{'lot_no': 'L1', 'qty_mt': 5.0, 'sold_to': 'C', 'customer': 'C',
                 'sale_ref': 'S', 'outbound_date': '2025-01-01'}]
        fp = OutboundStateRules.compute_allocation_source_fingerprint(rows, "")
        assert len(fp) == 40


# ═══════════════════════════════════════════════
# OutboundQueryRepository 테스트
# ═══════════════════════════════════════════════

class TestOutboundQueryRepository:

    def test_import(self):
        from engine_modules.inventory_modular.outbound_query import OutboundQueryRepository
        assert OutboundQueryRepository is not None

    def test_table_exists_true(self):
        from engine_modules.inventory_modular.outbound_query import OutboundQueryRepository
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE test_t (id INTEGER)")
        repo = OutboundQueryRepository(conn)
        assert repo.table_exists("test_t") is True

    def test_table_exists_false(self):
        from engine_modules.inventory_modular.outbound_query import OutboundQueryRepository
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        repo = OutboundQueryRepository(conn)
        assert repo.table_exists("nonexistent") is False

    def test_get_alloc_plan_cols(self):
        from engine_modules.inventory_modular.outbound_query import OutboundQueryRepository
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE allocation_plan (id INTEGER, lot_no TEXT, status TEXT)")
        repo = OutboundQueryRepository(conn)
        cols = repo.get_alloc_plan_cols()
        assert "id" in cols
        assert "lot_no" in cols

    def test_get_tonbag_status_counts(self):
        from engine_modules.inventory_modular.outbound_query import OutboundQueryRepository
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE inventory_tonbag (lot_no TEXT, status TEXT)")
        conn.execute("INSERT INTO inventory_tonbag VALUES ('L1', 'AVAILABLE')")
        conn.execute("INSERT INTO inventory_tonbag VALUES ('L1', 'AVAILABLE')")
        conn.execute("INSERT INTO inventory_tonbag VALUES ('L1', 'PICKED')")
        conn.commit()
        repo = OutboundQueryRepository(conn)
        counts = repo.get_tonbag_status_counts('L1')
        assert counts.get('AVAILABLE', 0) == 2
        assert counts.get('PICKED', 0) == 1


# ═══════════════════════════════════════════════
# OutboundWriteRepository 테스트
# ═══════════════════════════════════════════════

class TestOutboundWriteRepository:

    def test_import(self):
        from engine_modules.inventory_modular.outbound_repository import OutboundWriteRepository
        assert OutboundWriteRepository is not None

    def test_ensure_outbound_txn_tables(self):
        from engine_modules.inventory_modular.outbound_repository import OutboundWriteRepository
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        repo = OutboundWriteRepository(conn)
        repo.ensure_outbound_txn_tables()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='outbound_event_log'"
        ).fetchone()
        assert row is not None

    def test_insert_plan_row(self):
        from engine_modules.inventory_modular.outbound_repository import OutboundWriteRepository
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE allocation_plan (id INTEGER PRIMARY KEY AUTOINCREMENT, lot_no TEXT, status TEXT)")
        repo = OutboundWriteRepository(conn)
        cols = {'id', 'lot_no', 'status'}
        rid = repo.insert_plan_row({'lot_no': 'L1', 'status': 'RESERVED'}, cols)
        assert rid > 0

    def test_insert_outbound_movement(self):
        from engine_modules.inventory_modular.outbound_repository import OutboundWriteRepository
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE stock_movement (lot_no TEXT, movement_type TEXT, qty_kg REAL, remarks TEXT, created_at TEXT)")
        repo = OutboundWriteRepository(conn)
        repo.insert_outbound_movement('L1', 500.0, 'test', '2025-01-01')
        row = conn.execute("SELECT * FROM stock_movement").fetchone()
        assert row is not None
        assert row['movement_type'] == 'OUTBOUND'


# ═══════════════════════════════════════════════
# OutboundService 테스트
# ═══════════════════════════════════════════════

class TestOutboundService:

    def test_import(self):
        from engine_modules.inventory_modular.outbound_service import OutboundService
        assert OutboundService is not None

    def test_instantiate(self):
        from engine_modules.inventory_modular.outbound_service import OutboundService
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        svc = OutboundService(conn)
        assert svc.query is not None
        assert svc.writer is not None
        assert svc.rules is not None

    def test_delegation_table_exists(self):
        from engine_modules.inventory_modular.outbound_service import OutboundService
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE test_table (id INTEGER)")
        svc = OutboundService(conn)
        assert svc.table_exists("test_table") is True
        assert svc.table_exists("no_table") is False

    def test_delegation_reservation_mode(self):
        from engine_modules.inventory_modular.outbound_service import OutboundService
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        svc = OutboundService(conn)
        assert svc.get_allocation_reservation_mode() == "lot"

    def test_delegation_risk_flags(self):
        from engine_modules.inventory_modular.outbound_service import OutboundService
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        svc = OutboundService(conn)
        flags = svc.allocation_risk_flags(25000, 50000)
        assert "LARGE_VOLUME" in flags


# ═══════════════════════════════════════════════
# OutboundMixin import 테스트
# ═══════════════════════════════════════════════

class TestOutboundMixinImport:

    def test_module_syntax(self):
        import py_compile
        py_compile.compile(
            'engine_modules/inventory_modular/outbound_mixin.py',
            doraise=True
        )

    def test_new_modules_syntax(self):
        import py_compile
        py_compile.compile('engine_modules/inventory_modular/outbound_state_rules.py', doraise=True)
        py_compile.compile('engine_modules/inventory_modular/outbound_query.py', doraise=True)
        py_compile.compile('engine_modules/inventory_modular/outbound_repository.py', doraise=True)
        py_compile.compile('engine_modules/inventory_modular/outbound_service.py', doraise=True)
