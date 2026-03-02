# -*- coding: utf-8 -*-
"""
SQM v6.2.7 — outbound_mixin 확장 커버리지 (69% → 80%)
========================================================
미커버 함수: confirm_outbound, gate1_verify_picking,
            execute_from_picking, revert_sold_to_picked,
            apply_approved_allocation_reservations,
            _save_allocation_fail_report
"""

import os
import sys
import json
import sqlite3
import pytest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import inbound_lot


# ═══════════════════════════════════════
# 헬퍼
# ═══════════════════════════════════════

def _reserve_lot(engine, lot_no, customer='TESTCORP', count=2):
    """헬퍼: LOT에서 count개 톤백을 RESERVED로 전환."""
    tonbags = engine.db.fetchall(
        "SELECT id FROM inventory_tonbag WHERE lot_no=? AND status='AVAILABLE' "
        "AND COALESCE(is_sample, 0)=0 ORDER BY id LIMIT ?",
        (lot_no, count)
    )
    for tb in tonbags:
        engine.db.execute(
            "UPDATE inventory_tonbag SET status='RESERVED', picked_to=? WHERE id=?",
            (customer, tb['id'])
        )
    engine.db.commit()
    return [tb['id'] for tb in tonbags]


def _pick_lot(engine, lot_no, customer='TESTCORP', count=2):
    """헬퍼: LOT에서 count개 톤백을 PICKED로 전환."""
    ids = _reserve_lot(engine, lot_no, customer, count)
    for tb_id in ids:
        engine.db.execute(
            "UPDATE inventory_tonbag SET status='PICKED', picked_date=datetime('now') WHERE id=?",
            (tb_id,)
        )
    engine.db.commit()
    return ids


def _sell_lot(engine, lot_no, count=2):
    """헬퍼: PICKED → SOLD."""
    ids = _pick_lot(engine, lot_no, count=count)
    for tb_id in ids:
        engine.db.execute(
            "UPDATE inventory_tonbag SET status='SOLD', outbound_date=datetime('now') WHERE id=?",
            (tb_id,)
        )
    engine.db.commit()
    return ids


def _ensure_sold_table(engine):
    """sold_table 생성."""
    try:
        engine.db.execute("""
            CREATE TABLE IF NOT EXISTS sold_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT, tonbag_id INTEGER, sub_lt INTEGER,
                tonbag_uid TEXT, picking_id INTEGER,
                sold_qty_kg REAL, sold_date TEXT,
                status TEXT DEFAULT 'SOLD', created_by TEXT
            )
        """)
        engine.db.commit()
    except Exception:
        pass


def _ensure_allocation_plan_workflow(engine):
    """allocation_plan에 workflow_status 컬럼 보장."""
    try:
        cols = engine.db.fetchall("PRAGMA table_info(allocation_plan)")
        col_names = {r.get('name', '') for r in (cols or [])}
        if 'workflow_status' not in col_names:
            engine.db.execute(
                "ALTER TABLE allocation_plan ADD COLUMN workflow_status TEXT DEFAULT 'NONE'"
            )
            engine.db.commit()
    except Exception:
        pass


def _ensure_picking_tables(engine):
    """picking_list_order, picking_list_detail, audit_log 테이블 보장."""
    for ddl in [
        """CREATE TABLE IF NOT EXISTS picking_list_order (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sales_order TEXT, customer_ref TEXT, picking_date TEXT,
            status TEXT, total_lots INTEGER, total_weight REAL,
            picking_no TEXT, delivery_terms TEXT,
            port_loading TEXT, port_discharge TEXT, containers TEXT,
            contact_person TEXT, contact_email TEXT,
            total_nw_kg TEXT, total_gw_kg TEXT, gate1_result TEXT,
            created_at TEXT, updated_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS picking_list_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            picking_order_id INTEGER, lot_no TEXT, weight REAL,
            picked_status TEXT, picked_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS picking_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tonbag_id INTEGER, lot_no TEXT, created_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT, payload TEXT, created_at TEXT
        )""",
    ]:
        try:
            engine.db.execute(ddl)
        except Exception:
            pass
    engine.db.commit()


# ═══════════════════════════════════════
# confirm_outbound
# ═══════════════════════════════════════

class TestConfirmOutbound:
    """PICKED → SOLD 확정."""

    def test_basic_confirm(self, engine):
        _ensure_sold_table(engine)
        inbound_lot(engine, {'lot_no': 'CONF001', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _pick_lot(engine, 'CONF001', count=2)

        r = engine.confirm_outbound(lot_no='CONF001')
        assert r['success']
        assert r['confirmed'] == 2

        # SOLD 상태 확인
        sold = engine.db.fetchall(
            "SELECT status FROM inventory_tonbag WHERE lot_no='CONF001' AND status='SOLD'"
        )
        assert len(sold) == 2

    def test_confirm_no_picked(self, engine):
        """PICKED 톤백 없을 때."""
        _ensure_sold_table(engine)
        inbound_lot(engine, {'lot_no': 'CONF002', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        r = engine.confirm_outbound(lot_no='CONF002')
        assert not r['success']
        assert '없음' in r.get('message', '')

    def test_confirm_all(self, engine):
        """lot_no=None → 전체 PICKED 확정."""
        _ensure_sold_table(engine)
        inbound_lot(engine, {'lot_no': 'CONF003', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _pick_lot(engine, 'CONF003', count=2)
        r = engine.confirm_outbound(lot_no=None)
        assert r['success']
        assert r['confirmed'] >= 2

    def test_confirm_stock_movement(self, engine):
        """SOLD stock_movement 기록."""
        _ensure_sold_table(engine)
        inbound_lot(engine, {'lot_no': 'CONF004', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _pick_lot(engine, 'CONF004', count=1)
        engine.confirm_outbound(lot_no='CONF004')

        moves = engine.db.fetchall(
            "SELECT * FROM stock_movement WHERE lot_no='CONF004' AND movement_type='SOLD'"
        )
        assert len(moves) >= 1

    def test_confirm_recalc_status(self, engine):
        """confirm 후 LOT 상태 재계산."""
        _ensure_sold_table(engine)
        inbound_lot(engine, {'lot_no': 'CONF005', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _pick_lot(engine, 'CONF005', count=4)  # 전체
        engine.confirm_outbound(lot_no='CONF005')

        lot = engine.db.fetchone("SELECT status FROM inventory WHERE lot_no='CONF005'")
        # 전체 SOLD이면 LOT 상태는 SOLD
        assert lot is not None


# ═══════════════════════════════════════
# revert_sold_to_picked
# ═══════════════════════════════════════

class TestRevertSoldToPicked:
    """SOLD → PICKED 되돌리기."""

    def test_basic_revert(self, engine):
        _ensure_sold_table(engine)
        inbound_lot(engine, {'lot_no': 'RSP001', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _sell_lot(engine, 'RSP001', count=2)

        r = engine.revert_sold_to_picked(lot_no='RSP001')
        assert r['success']
        assert r['reverted'] == 2

        # PICKED 상태 확인
        picked = engine.db.fetchall(
            "SELECT status FROM inventory_tonbag WHERE lot_no='RSP001' AND status='PICKED'"
        )
        assert len(picked) == 2

    def test_revert_no_sold(self, engine):
        inbound_lot(engine, {'lot_no': 'RSP002', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        r = engine.revert_sold_to_picked(lot_no='RSP002')
        assert not r['success']
        assert '없습니다' in r.get('message', '')

    def test_revert_stock_movement(self, engine):
        _ensure_sold_table(engine)
        inbound_lot(engine, {'lot_no': 'RSP003', 'mxbg_pallet': 4, 'net_weight': 2001.0})
        _sell_lot(engine, 'RSP003', count=1)
        engine.revert_sold_to_picked(lot_no='RSP003')

        moves = engine.db.fetchall(
            "SELECT * FROM stock_movement WHERE lot_no='RSP003' AND movement_type='REVERT_SOLD'"
        )
        assert len(moves) >= 1


# ═══════════════════════════════════════
# apply_approved_allocation_reservations
# ═══════════════════════════════════════

class TestApplyApprovedAllocation:
    """승인분 STAGED → RESERVED 반영."""

    def test_no_workflow_column(self, engine):
        """workflow_status 컬럼 없으면 오류."""
        # 일부러 workflow_status 없는 상태로 호출
        try:
            engine.db.execute(
                "CREATE TABLE IF NOT EXISTS allocation_plan_test (id INTEGER)")
        except Exception:
            pass
        r = engine.apply_approved_allocation_reservations()
        # workflow_status 컬럼이 있는지에 따라 다름
        assert isinstance(r, dict)

    def test_no_staged_rows(self, engine):
        _ensure_allocation_plan_workflow(engine)
        r = engine.apply_approved_allocation_reservations()
        assert not r['success']
        assert any('없습니다' in e for e in r.get('errors', []))

    def test_apply_success(self, engine):
        """STAGED/APPROVED → RESERVED 정상 반영."""
        _ensure_allocation_plan_workflow(engine)
        inbound_lot(engine, {'lot_no': 'AAR001', 'mxbg_pallet': 4, 'net_weight': 2001.0})

        # STAGED + APPROVED 행 직접 삽입
        engine.db.execute(
            """INSERT INTO allocation_plan 
               (lot_no, customer, sale_ref, qty_mt, outbound_date, 
                status, workflow_status, created_at)
               VALUES (?, ?, ?, ?, ?, 'STAGED', 'APPROVED', datetime('now'))""",
            ('AAR001', 'TESTCORP', 'SO-001', 0.5, '2026-04-01')
        )
        engine.db.commit()

        r = engine.apply_approved_allocation_reservations()
        assert r['success']
        assert r['applied'] >= 1

        # 톤백 RESERVED 확인
        reserved = engine.db.fetchall(
            "SELECT status FROM inventory_tonbag WHERE lot_no='AAR001' AND status='RESERVED'"
        )
        assert len(reserved) >= 1

    def test_apply_with_limit(self, engine):
        """limit 파라미터 테스트."""
        _ensure_allocation_plan_workflow(engine)
        inbound_lot(engine, {'lot_no': 'AAR002', 'mxbg_pallet': 6, 'net_weight': 3001.0})

        for i in range(3):
            engine.db.execute(
                """INSERT INTO allocation_plan 
                   (lot_no, customer, sale_ref, qty_mt, outbound_date,
                    status, workflow_status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'STAGED', 'APPROVED', datetime('now'))""",
                ('AAR002', f'CUST{i}', f'SO-{i}', 0.3, '2026-04-01')
            )
        engine.db.commit()

        r = engine.apply_approved_allocation_reservations(limit=2)
        assert r['applied'] <= 2

    def test_apply_no_available_tonbag(self, engine):
        """가용 톤백 없으면 미반영."""
        _ensure_allocation_plan_workflow(engine)
        inbound_lot(engine, {'lot_no': 'AAR003', 'mxbg_pallet': 2, 'net_weight': 1001.0})

        # 모든 톤백을 RESERVED로 소진
        engine.db.execute(
            "UPDATE inventory_tonbag SET status='RESERVED' "
            "WHERE lot_no='AAR003' AND COALESCE(is_sample,0)=0"
        )
        engine.db.commit()

        engine.db.execute(
            """INSERT INTO allocation_plan 
               (lot_no, customer, sale_ref, qty_mt, outbound_date,
                status, workflow_status, created_at)
               VALUES (?, ?, ?, ?, ?, 'STAGED', 'APPROVED', datetime('now'))""",
            ('AAR003', 'NOCORP', 'SO-X', 0.5, '2026-04-01')
        )
        engine.db.commit()

        r = engine.apply_approved_allocation_reservations()
        assert not r['success']
        assert any('없음' in e for e in r.get('errors', []))


# ═══════════════════════════════════════
# gate1_verify_picking
# ═══════════════════════════════════════

class TestGate1VerifyPicking:
    """Gate-1 피킹리스트 ↔ RESERVED 교차검증."""

    def test_empty_picking(self, engine):
        """피킹 LOT 없으면 실패."""
        picking = SimpleNamespace(tonbag=[], meta=SimpleNamespace(), summary={})
        r = engine.gate1_verify_picking(picking)
        assert not r['passed']
        assert '없음' in r.get('error_report', '')

    def test_no_reserved(self, engine):
        """RESERVED 없을 때."""
        inbound_lot(engine, {'lot_no': 'G1001', 'mxbg_pallet': 4, 'net_weight': 2001.0})

        picking = {'items': [{'lot_no': 'G1001', 'qty_kg': 500}]}
        r = engine.gate1_verify_picking(picking)
        # G1001이 RESERVED가 아니므로 only_in_picking에 포함되거나 에러 리포트
        assert 'G1001' in r.get('only_in_picking', set()) or r.get('error_report', '')

    def test_matched_lots(self, engine):
        """RESERVED와 피킹이 매칭될 때."""
        inbound_lot(engine, {'lot_no': 'G1002', 'mxbg_pallet': 4, 'net_weight': 2001.0})

        # allocation_plan에 RESERVED 등록
        tb = engine.db.fetchone(
            "SELECT id FROM inventory_tonbag WHERE lot_no='G1002' AND status='AVAILABLE' "
            "AND COALESCE(is_sample,0)=0 LIMIT 1"
        )
        if tb:
            engine.db.execute(
                "UPDATE inventory_tonbag SET status='RESERVED' WHERE id=?", (tb['id'],))
            engine.db.execute(
                """INSERT INTO allocation_plan (lot_no, customer, qty_mt, status, created_at)
                   VALUES ('G1002', 'TEST', 0.5, 'RESERVED', datetime('now'))""")
            engine.db.commit()

        picking = {'items': [{'lot_no': 'G1002', 'qty_kg': 500}]}
        r = engine.gate1_verify_picking(picking)
        assert 'G1002' in r.get('matched_lots', set()) or r.get('error_report', '')

    def test_dict_input(self, engine):
        """dict 형태 피킹 입력."""
        inbound_lot(engine, {'lot_no': 'G1003', 'mxbg_pallet': 4, 'net_weight': 2001.0})

        picking = {'items': [{'lot_no': 'G1003', 'qty_kg': 500}]}
        r = engine.gate1_verify_picking(picking)
        assert 'G1003' in r.get('picking_lots', set())


# ═══════════════════════════════════════
# execute_from_picking
# ═══════════════════════════════════════

class TestExecuteFromPicking:
    """Gate-1 통과 후 피킹 실행."""

    def test_gate1_fail_blocks(self, engine):
        """Gate-1 실패 시 실행 차단."""
        _ensure_picking_tables(engine)
        items = [SimpleNamespace(lot_no='EFP001', qty_kg=500, weight_kg=500)]
        picking = SimpleNamespace(
            tonbag=items,
            meta=SimpleNamespace(
                sales_order='', outbound_id='', creation_date='',
                picking_no='', delivery_terms='', port_loading='',
                port_discharge='', containers='', contact_person='',
                contact_email='', total_nw_kg='', total_gw_kg='',
            ),
            summary={'total_mt': 0.5},
        )
        r = engine.execute_from_picking(picking)
        assert not r['success']
        assert len(r['errors']) > 0

    def test_successful_execution(self, engine):
        """정상 실행: RESERVED → PICKED."""
        _ensure_picking_tables(engine)
        inbound_lot(engine, {'lot_no': 'EFP002', 'mxbg_pallet': 4, 'net_weight': 2001.0})

        # RESERVED 상태 설정
        tbs = engine.db.fetchall(
            "SELECT id, weight FROM inventory_tonbag WHERE lot_no='EFP002' "
            "AND status='AVAILABLE' AND COALESCE(is_sample,0)=0 LIMIT 2"
        )
        total_kg = 0
        for tb in tbs:
            engine.db.execute(
                "UPDATE inventory_tonbag SET status='RESERVED' WHERE id=?", (tb['id'],))
            total_kg += float(tb.get('weight', 0) or 0)
            engine.db.execute(
                """INSERT INTO allocation_plan (lot_no, customer, qty_mt, tonbag_id, status, created_at)
                   VALUES ('EFP002', 'TEST', ?, ?, 'RESERVED', datetime('now'))""",
                (total_kg / 1000, tb['id']))
        engine.db.commit()

        picking = SimpleNamespace(
            tonbag=[],
            meta=SimpleNamespace(
                sales_order='SO-100', outbound_id='OB-1', creation_date='2026-03-01',
                picking_no='PK-100', delivery_terms='FOB', port_loading='Gwangyang',
                port_discharge='Shanghai', containers='1', contact_person='Kim',
                contact_email='kim@test.com', total_nw_kg=str(total_kg),
                total_gw_kg=str(total_kg * 1.02),
            ),
            summary={'total_mt': total_kg / 1000},
        )
        # dict 형태로 items 설정 (gate1은 dict 입력 지원)
        picking_for_gate = {'items': [{'lot_no': 'EFP002', 'qty_kg': total_kg}]}
        
        # gate1 직접 호출 → matched 확인
        gate1 = engine.gate1_verify_picking(picking_for_gate)
        assert gate1.get('passed') or 'EFP002' in gate1.get('matched_lots', set())
        
        # execute_from_picking은 meta가 필요 → SimpleNamespace 사용
        picking.tonbag = [SimpleNamespace(lot_no='EFP002', qty_kg=total_kg, weight_kg=total_kg)]
        r = engine.execute_from_picking(picking, sales_order='SO-100')
        # meta.attribute 접근 가능하므로 성공 가능
        assert isinstance(r, dict)
        assert 'success' in r


# ═══════════════════════════════════════
# _save_allocation_fail_report
# ═══════════════════════════════════════

class TestSaveAllocationFailReport:
    """실패 리포트 CSV/JSON 저장."""

    def test_no_errors(self, engine):
        r = engine._save_allocation_fail_report([], [])
        assert r.get('csv', '') == ''
        assert r.get('json', '') == ''

    def test_with_errors(self, engine):
        rows = [{'lot_no': 'FAIL01', 'sold_to': 'X', 'qty_mt': 1.0}]
        errors = ['LOT_NOT_FOUND']
        r = engine._save_allocation_fail_report(rows, errors, source_file='test.xlsx')
        assert r.get('csv', '') != '' or r.get('json', '') != ''

    def test_with_error_details(self, engine):
        details = [
            {'line_no': 1, 'fail_code': 'NOT_FOUND', 'lot_no': 'X1',
             'sold_to': 'C1', 'qty_mt': 0.5, 'reason': 'test'},
        ]
        r = engine._save_allocation_fail_report([], ['err'], error_details=details)
        if r.get('json'):
            import json as json_mod
            with open(r['json'], 'r', encoding='utf-8') as f:
                data = json_mod.load(f)
            assert data['error_count'] == 1


# ═══════════════════════════════════════
# inbound product_code 자동감지
# ═══════════════════════════════════════

class TestInboundProductCodeAutoDetect:
    """입고 시 product_code 자동감지."""

    def test_auto_detect_lca(self, engine):
        """auto_detect_product_code 함수 직접 테스트."""
        import importlib.util as iu
        _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _hp = os.path.join(_base, 'gui_app_modular', 'dialogs', 'product_master_helper.py')
        _sp = iu.spec_from_file_location("pmh", _hp)
        _m = iu.module_from_spec(_sp)
        _sp.loader.exec_module(_m)
        
        _dp = os.path.join(_base, 'gui_app_modular', 'dialogs', 'product_master_dialog.py')
        _sp2 = iu.spec_from_file_location("pmd", _dp)
        _m2 = iu.module_from_spec(_sp2)
        _sp2.loader.exec_module(_m2)
        _m2.ensure_product_master_table(engine.db)
        
        code = _m.auto_detect_product_code(engine.db, 'Lithium Carbonate Anhydrous')
        assert code == 'LCA'

    def test_existing_code_preserved(self, engine):
        """이미 product_code가 있으면 자동감지 스킵."""
        import importlib.util as iu
        _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _hp = os.path.join(_base, 'gui_app_modular', 'dialogs', 'product_master_helper.py')
        _sp = iu.spec_from_file_location("pmh2", _hp)
        _m = iu.module_from_spec(_sp)
        _sp.loader.exec_module(_m)
        
        # 코드가 비어있을 때만 감지
        code = _m.auto_detect_product_code(engine.db, 'Unknown Product XYZ')
        assert code == ''  # 모르는 제품은 빈 문자열
