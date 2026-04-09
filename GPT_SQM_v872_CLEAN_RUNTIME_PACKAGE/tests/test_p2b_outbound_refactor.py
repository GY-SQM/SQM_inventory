"""
P2-B Outbound 리팩토링 통합 테스트
SQM v8.7.1 실제 상태값 기반
생성일: 2026-04-08
실행: pytest tests/test_p2b_outbound_refactor.py -v
"""
import os
import sqlite3
import tempfile
import pytest
from datetime import datetime


# ================================================================
# 공통 픽스처 — 실제 SQM DB 스키마 기반
# ================================================================

@pytest.fixture
def sqm_db():
    """
    실제 SQM 테이블 구조 기반 임시 DB
    SQMDatabase 대신 sqlite3 직접 사용 (단위 테스트용)
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # dict-like 접근 허용

    # SQM 핵심 테이블 생성
    conn.executescript("""
        CREATE TABLE inventory (
            lot_no TEXT PRIMARY KEY,
            status TEXT DEFAULT 'AVAILABLE',
            current_weight REAL DEFAULT 0,
            initial_weight REAL DEFAULT 0,
            picked_weight  REAL DEFAULT 0,
            product_code TEXT,
            sap_no TEXT,
            bl_no TEXT,
            gross_weight REAL,
            net_weight REAL,
            mxbg_pallet INTEGER,
            sold_to TEXT,
            sale_ref TEXT,
            updated_at TEXT
        );
        CREATE TABLE inventory_tonbag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT,
            sub_lt INTEGER DEFAULT 0,
            weight REAL DEFAULT 0,
            tonbag_uid TEXT,
            status TEXT DEFAULT 'AVAILABLE',
            is_sample INTEGER DEFAULT 0,
            customer TEXT,
            sale_ref TEXT,
            picked_date TEXT,
            outbound_date TEXT,
            updated_at TEXT
        );
        CREATE TABLE allocation_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT,
            tonbag_id INTEGER,
            sub_lt INTEGER DEFAULT 0,
            customer TEXT,
            sale_ref TEXT,
            outbound_date TEXT,
            status TEXT DEFAULT 'STAGED',
            workflow_status TEXT,
            executed_at TEXT,
            cancelled_at TEXT,
            rejected_reason TEXT,
            updated_at TEXT
        );
        CREATE TABLE picking_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT,
            tonbag_id INTEGER,
            sub_lt INTEGER DEFAULT 0,
            tonbag_uid TEXT,
            customer TEXT,
            sale_ref TEXT,
            weight REAL,
            sales_order_no TEXT,
            picking_no TEXT,
            outbound_id TEXT,
            picked_date TEXT,
            created_at TEXT
        );
        CREATE TABLE sold_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT,
            tonbag_id INTEGER,
            sub_lt INTEGER DEFAULT 0,
            tonbag_uid TEXT,
            picking_id INTEGER,
            sold_qty_kg REAL,
            sold_qty_mt REAL,
            gross_weight_kg REAL,
            sold_date TEXT,
            status TEXT DEFAULT 'OUTBOUND',
            created_by TEXT,
            sap_no TEXT,
            bl_no TEXT,
            customer TEXT,
            sku TEXT,
            sales_order_no TEXT,
            picking_no TEXT,
            delivery_date TEXT,
            ct_plt INTEGER DEFAULT 1,
            is_sample INTEGER DEFAULT 0
        );
        CREATE TABLE stock_movement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT,
            movement_type TEXT,
            qty_kg REAL,
            remarks TEXT,
            created_at TEXT
        );
        CREATE TABLE outbound_event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outbound_no TEXT,
            event_type TEXT,
            message TEXT,
            created_at TEXT
        );
        CREATE TABLE outbound (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outbound_no TEXT,
            status TEXT
        );
    """)
    conn.commit()

    # MockDB wrapper — SQMDatabase 인터페이스 흉내
    class MockDB:
        def __init__(self, c):
            self.conn = c
            self._in_tx = False

        def execute(self, sql, params=()):
            return self.conn.execute(sql, params)

        def fetchone(self, sql, params=()):
            row = self.conn.execute(sql, params).fetchone()
            return row

        def fetchall(self, sql, params=()):
            return self.conn.execute(sql, params).fetchall() or []

        def commit(self):
            self.conn.commit()

        def rollback(self):
            self.conn.rollback()

        class _TxCtx:
            def __init__(self, c):
                self.c = c
            def __enter__(self):
                self.c.execute("BEGIN IMMEDIATE")
                return self
            def __exit__(self, exc_type, exc_val, tb):
                if exc_type:
                    self.c.rollback()
                else:
                    self.c.commit()
                return False

        def transaction(self, mode="IMMEDIATE"):
            return self._TxCtx(self.conn)

    db = MockDB(conn)
    yield db
    conn.close()
    os.unlink(db_path)


@pytest.fixture
def seed_lot(sqm_db):
    """테스트용 LOT + 톤백 3개 시드 데이터"""
    sqm_db.execute(
        "INSERT INTO inventory (lot_no, status, current_weight, initial_weight, picked_weight) "
        "VALUES ('LOT-TEST-001', 'AVAILABLE', 3000.0, 3000.0, 0.0)"
    )
    for i in range(1, 4):
        sqm_db.execute(
            "INSERT INTO inventory_tonbag (lot_no, sub_lt, weight, status) "
            "VALUES ('LOT-TEST-001', ?, 1000.0, 'AVAILABLE')",
            (i,)
        )
    sqm_db.commit()
    return "LOT-TEST-001"


# ================================================================
# TC-01: OutboundStateRules
# ================================================================
class TestOutboundStateRules:

    def test_import(self):
        from features.services.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules is not None

    def test_allowed_transitions(self):
        from features.services.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules.can_transition("AVAILABLE",  "RESERVED")  == True
        assert OutboundStateRules.can_transition("RESERVED",   "PICKED")    == True
        assert OutboundStateRules.can_transition("PICKED",     "OUTBOUND")  == True
        assert OutboundStateRules.can_transition("RESERVED",   "AVAILABLE") == True
        assert OutboundStateRules.can_transition("PICKED",     "RESERVED")  == True

    def test_forbidden_transitions(self):
        from features.services.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules.can_transition("AVAILABLE", "OUTBOUND") == False
        assert OutboundStateRules.can_transition("OUTBOUND",  "AVAILABLE") == False
        assert OutboundStateRules.can_transition("OUTBOUND",  "PICKED")   == False
        assert OutboundStateRules.can_transition("CANCELLED", "RESERVED") == False

    def test_final_states(self):
        from features.services.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules.is_final("OUTBOUND")  == True
        assert OutboundStateRules.is_final("SOLD")       == True
        assert OutboundStateRules.is_final("CANCELLED")  == True
        assert OutboundStateRules.is_final("RESERVED")   == False
        assert OutboundStateRules.is_final("PICKED")     == False

    def test_sold_legacy_compatible(self):
        from features.services.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules.is_sold_compatible("OUTBOUND") == True
        assert OutboundStateRules.is_sold_compatible("SOLD")     == True
        assert OutboundStateRules.is_sold_compatible("PICKED")   == False

    def test_validate_transition_error_msg(self):
        from features.services.outbound_state_rules import OutboundStateRules
        r = OutboundStateRules.validate_transition("OUTBOUND", "AVAILABLE")
        assert r["ok"] == False
        assert "불가" in r["error"]

    def test_get_method_for_transition(self):
        from features.services.outbound_state_rules import OutboundStateRules
        assert OutboundStateRules.get_method_for_transition("AVAILABLE", "RESERVED") \
               == "reserve_from_allocation"
        assert OutboundStateRules.get_method_for_transition("RESERVED", "PICKED") \
               == "execute_reserved"
        assert OutboundStateRules.get_method_for_transition("PICKED", "OUTBOUND") \
               == "confirm_outbound"


# ================================================================
# TC-02: OutboundQuery
# ================================================================
class TestOutboundQuery:

    def test_import(self):
        from features.repositories.outbound_query import OutboundQuery
        assert OutboundQuery is not None

    def test_load_reserved_plans_empty(self, sqm_db):
        from features.repositories.outbound_query import OutboundQuery
        q = OutboundQuery(sqm_db)
        assert q.load_reserved_plans() == [] or isinstance(q.load_reserved_plans(), list)

    def test_load_picked_tonbags_empty(self, sqm_db):
        from features.repositories.outbound_query import OutboundQuery
        q = OutboundQuery(sqm_db)
        assert isinstance(q.load_picked_tonbags(), list)

    def test_check_double_sold_false(self, sqm_db):
        from features.repositories.outbound_query import OutboundQuery
        q = OutboundQuery(sqm_db)
        assert q.check_double_sold(9999) == False

    def test_guard_double_outbound_empty(self, sqm_db):
        from features.repositories.outbound_query import OutboundQuery
        q = OutboundQuery(sqm_db)
        assert q.guard_against_double_outbound([]) == []

    def test_verify_weight_conservation_ok(self, sqm_db, seed_lot):
        from features.repositories.outbound_query import OutboundQuery
        q = OutboundQuery(sqm_db)
        r = q.verify_weight_conservation(seed_lot)
        assert r["ok"] == True

    def test_verify_weight_mismatch(self, sqm_db, seed_lot):
        from features.repositories.outbound_query import OutboundQuery
        # 일부러 불일치 유발
        sqm_db.execute(
            "UPDATE inventory SET picked_weight = 9999.0 WHERE lot_no = ?", (seed_lot,)
        )
        sqm_db.commit()
        q = OutboundQuery(sqm_db)
        r = q.verify_weight_conservation(seed_lot)
        assert r["ok"] == False
        assert "불일치" in r["error"]

    def test_aggregate_picking_qty(self, sqm_db):
        from features.repositories.outbound_query import OutboundQuery
        q = OutboundQuery(sqm_db)
        rows = [
            {"lot_no": "LOT-A", "weight": 1000.0},
            {"lot_no": "LOT-A", "weight": 500.0},
            {"lot_no": "LOT-B", "weight": 200.0},
        ]
        result = q.aggregate_picking_qty(rows)
        assert result["LOT-A"]["qty"] == 2
        assert result["LOT-A"]["weight"] == 1500.0
        assert result["LOT-B"]["qty"] == 1


# ================================================================
# TC-03: OutboundRepository
# ================================================================
class TestOutboundRepository:

    def test_import(self):
        from features.repositories.outbound_repository import OutboundRepository
        assert OutboundRepository is not None

    def test_recalc_lot_all_outbound(self, sqm_db, seed_lot):
        from features.repositories.outbound_repository import OutboundRepository
        # 전체 OUTBOUND 상태로 변경
        sqm_db.execute(
            "UPDATE inventory_tonbag SET status='OUTBOUND' WHERE lot_no=?", (seed_lot,)
        )
        sqm_db.commit()
        repo = OutboundRepository(sqm_db)
        result = repo.recalc_lot_status(seed_lot)
        assert result["ok"] == True
        assert result["new_status"] == "OUTBOUND"

    def test_recalc_lot_mixed(self, sqm_db, seed_lot):
        from features.repositories.outbound_repository import OutboundRepository
        # 1개 OUTBOUND, 2개 AVAILABLE
        sqm_db.execute(
            "UPDATE inventory_tonbag SET status='OUTBOUND' WHERE lot_no=? AND sub_lt=1",
            (seed_lot,)
        )
        sqm_db.commit()
        repo = OutboundRepository(sqm_db)
        result = repo.recalc_lot_status(seed_lot)
        assert result["new_status"] == "PARTIAL"

    def test_cancel_allocation_plan(self, sqm_db):
        from features.repositories.outbound_repository import OutboundRepository
        sqm_db.execute(
            "INSERT INTO allocation_plan (lot_no, status) VALUES ('LOT-X', 'RESERVED')"
        )
        sqm_db.commit()
        plan_id = sqm_db.execute(
            "SELECT id FROM allocation_plan WHERE lot_no='LOT-X'"
        ).fetchone()[0]

        repo = OutboundRepository(sqm_db)
        r = repo.cancel_allocation_plan([plan_id], "TEST_CANCEL")
        assert r["ok"] == True
        assert r["cancelled"] == 1

        row = sqm_db.execute(
            "SELECT status FROM allocation_plan WHERE id=?", (plan_id,)
        ).fetchone()
        assert row[0] == "CANCELLED"

    def test_update_lot_after_pick(self, sqm_db, seed_lot):
        from features.repositories.outbound_repository import OutboundRepository
        repo = OutboundRepository(sqm_db)
        r = repo.update_lot_after_pick(seed_lot, 1000.0)
        assert r["ok"] == True
        row = sqm_db.execute(
            "SELECT current_weight, picked_weight FROM inventory WHERE lot_no=?",
            (seed_lot,)
        ).fetchone()
        assert row[0] == 2000.0   # 3000 - 1000
        assert row[1] == 1000.0


# ================================================================
# TC-04: OutboundService 전체 파이프라인
# ================================================================
class TestOutboundService:

    def test_import(self):
        from features.services.outbound_service import OutboundService
        assert OutboundService is not None

    def test_instantiate(self, sqm_db):
        from features.services.outbound_service import OutboundService
        svc = OutboundService(sqm_db)
        assert svc is not None

    def test_execute_reserved_empty(self, sqm_db):
        from features.services.outbound_service import OutboundService
        svc = OutboundService(sqm_db)
        r = svc.execute_reserved()
        assert r["success"] == False
        assert len(r["errors"]) > 0

    def test_confirm_outbound_blocked_without_force_all(self, sqm_db):
        from features.services.outbound_service import OutboundService
        svc = OutboundService(sqm_db)
        r = svc.confirm_outbound(lot_no=None, force_all=False)
        assert r["success"] == False
        assert "CONFIRM_ALL_BLOCKED" in r["errors"][0]

    def test_confirm_outbound_empty(self, sqm_db):
        from features.services.outbound_service import OutboundService
        svc = OutboundService(sqm_db)
        r = svc.confirm_outbound(lot_no="NO-SUCH-LOT")
        assert r["confirmed"] == 0

    def test_full_pipeline_reserved_to_outbound(self, sqm_db, seed_lot):
        """
        핵심 통합 테스트:
        RESERVED → execute_reserved() → PICKED → confirm_outbound() → OUTBOUND
        """
        from features.services.outbound_service import OutboundService

        svc = OutboundService(sqm_db)

        # Step 1: tonbag을 RESERVED로 수동 세팅
        tb_id = sqm_db.execute(
            "SELECT id FROM inventory_tonbag WHERE lot_no=? AND sub_lt=1",
            (seed_lot,)
        ).fetchone()[0]

        sqm_db.execute(
            "UPDATE inventory_tonbag SET status='RESERVED' WHERE id=?", (tb_id,)
        )
        sqm_db.execute(
            "INSERT INTO allocation_plan (lot_no, tonbag_id, sub_lt, customer, sale_ref, "
            "outbound_date, status) VALUES (?, ?, 1, 'TEST-CUST', 'SR-001', '2026-04-08', 'RESERVED')",
            (seed_lot, tb_id)
        )
        sqm_db.commit()

        # Step 2: execute_reserved → PICKED
        r1 = svc.execute_reserved(lot_no=seed_lot)
        assert r1["executed"] == 1, f"execute_reserved 실패: {r1['errors']}"

        tb_status = sqm_db.execute(
            "SELECT status FROM inventory_tonbag WHERE id=?", (tb_id,)
        ).fetchone()[0]
        assert tb_status == "PICKED", f"PICKED 전이 실패: {tb_status}"

        # Step 3: confirm_outbound → OUTBOUND
        r2 = svc.confirm_outbound(lot_no=seed_lot)
        assert r2["confirmed"] == 1, f"confirm_outbound 실패: {r2['errors']}"

        tb_status2 = sqm_db.execute(
            "SELECT status FROM inventory_tonbag WHERE id=?", (tb_id,)
        ).fetchone()[0]
        assert tb_status2 == "OUTBOUND", f"OUTBOUND 전이 실패: {tb_status2}"

    def test_revert_picked_to_reserved(self, sqm_db, seed_lot):
        """PICKED → revert → RESERVED"""
        from features.services.outbound_service import OutboundService
        svc = OutboundService(sqm_db)

        tb_id = sqm_db.execute(
            "SELECT id FROM inventory_tonbag WHERE lot_no=? AND sub_lt=1", (seed_lot,)
        ).fetchone()[0]

        # PICKED + EXECUTED plan 세팅
        sqm_db.execute(
            "UPDATE inventory_tonbag SET status='PICKED' WHERE id=?", (tb_id,)
        )
        sqm_db.execute(
            "INSERT INTO allocation_plan (lot_no, tonbag_id, status) "
            "VALUES (?, ?, 'EXECUTED')",
            (seed_lot, tb_id)
        )
        sqm_db.commit()

        r = svc.revert_picked_to_reserved(lot_no=seed_lot)
        assert r["success"] == True
        assert r["reverted"] == 1

        status = sqm_db.execute(
            "SELECT status FROM inventory_tonbag WHERE id=?", (tb_id,)
        ).fetchone()[0]
        assert status == "RESERVED"

    def test_revert_outbound_to_available(self, sqm_db, seed_lot):
        """OUTBOUND → revert → AVAILABLE"""
        from features.services.outbound_service import OutboundService
        svc = OutboundService(sqm_db)

        tb_id = sqm_db.execute(
            "SELECT id FROM inventory_tonbag WHERE lot_no=? AND sub_lt=1", (seed_lot,)
        ).fetchone()[0]

        sqm_db.execute(
            "UPDATE inventory_tonbag SET status='OUTBOUND' WHERE id=?", (tb_id,)
        )
        sqm_db.execute(
            "INSERT INTO sold_table (lot_no, tonbag_id, status) VALUES (?,?,'OUTBOUND')",
            (seed_lot, tb_id)
        )
        sqm_db.commit()

        r = svc.revert_outbound_to_available(lot_no=seed_lot)
        assert r["success"] == True
        assert r["reverted"] == 1

        status = sqm_db.execute(
            "SELECT status FROM inventory_tonbag WHERE id=?", (tb_id,)
        ).fetchone()[0]
        assert status == "AVAILABLE"

        # sold_table 삭제 확인
        sold = sqm_db.execute(
            "SELECT id FROM sold_table WHERE tonbag_id=?", (tb_id,)
        ).fetchone()
        assert sold is None

    def test_get_dashboard(self, sqm_db):
        from features.services.outbound_service import OutboundService
        svc = OutboundService(sqm_db)
        d = svc.get_dashboard()
        assert "reserved_count" in d
        assert "picked_count"   in d
        assert "stale_count"    in d
        assert d["error"] is None
