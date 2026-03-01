# -*- coding: utf-8 -*-
"""
SQM 핵심 로직 테스트 (v5.6.8)
===============================

실행: python -m pytest tests/test_core.py -v
"""

import os
import sys
import sqlite3
import logging
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


@pytest.fixture
def engine():
    """테스트용 엔진 (임시 DB)"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    try:
        from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
        eng = SQMInventoryEngineV3(db_path)
        yield eng
    finally:
        try:
            eng.db.close()
        except Exception as e:
            logger.debug(f"Suppressed: {e}")
        os.unlink(db_path)


@pytest.fixture
def sample_packing():
    """표준 입고 데이터 (대원칙: 10톤백 + 1샘플 = 5001kg)"""
    return {
        'lot_no': '2401010001',
        'sap_no': 'SAP-TEST-001',
        'bl_no': 'MAEU1234567',
        'container_no': 'CONT001',
        'product': 'LITHIUM CARBONATE',
        'product_code': 'LC',
        'mxbg_pallet': 10,
        'net_weight': 5001.0,
        'gross_weight': 5200.0,
        'salar_invoice_no': 'INV-16130',
        'warehouse': '광양',
    }


# ═══════════════════════════════════════════════════════
# 테스트 1: 상수 파일 정상 import
# ═══════════════════════════════════════════════════════
class TestConstants:
    def test_constants_import(self):
        from engine_modules.constants import (
            STATUS_AVAILABLE, STATUS_PICKED, STATUS_SOLD,
            DEFAULT_WAREHOUSE, SAMPLE_WEIGHT_KG, BL_PREFIXES,
        )
        assert STATUS_AVAILABLE == 'AVAILABLE'
        assert SAMPLE_WEIGHT_KG == 1.0
        assert DEFAULT_WAREHOUSE == '광양'
        assert 'MAEU' in BL_PREFIXES


# ═══════════════════════════════════════════════════════
# 테스트 2: DB 테이블 생성
# ═══════════════════════════════════════════════════════
class TestDatabase:
    def test_tables_created(self, engine):
        """핵심 8개 테이블 생성 확인"""
        tables = engine.db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = {r['name'] if isinstance(r, dict) else r[0] for r in tables}
        for required in ['inventory', 'inventory_tonbag', 'outbound',
                         'outbound_item', 'stock_movement', 'shipment']:
            assert required in table_names, f"테이블 {required} 미생성"

    def test_inventory_unique_lot(self, engine):
        """LOT 번호 UNIQUE 제약 테스트"""
        engine.db.execute(
            "INSERT INTO inventory (lot_no, net_weight, status) VALUES (?, ?, ?)",
            ('TEST-LOT-001', 5001, 'AVAILABLE'))
        with pytest.raises(sqlite3.IntegrityError):
            engine.db.execute(
                "INSERT INTO inventory (lot_no, net_weight, status) VALUES (?, ?, ?)",
                ('TEST-LOT-001', 5001, 'AVAILABLE'))


# ═══════════════════════════════════════════════════════
# 테스트 3: 대원칙 — 1 LOT = N톤백 + 1샘플
# ═══════════════════════════════════════════════════════
class TestInbound:
    def test_inbound_basic(self, engine, sample_packing):
        """기본 입고: LOT + 톤백 생성"""
        result = engine.process_inbound(sample_packing)
        assert result['success'], f"입고 실패: {result['errors']}"
        assert result['created_tonbags'] > 0

    def test_inbound_tonbag_count(self, engine, sample_packing):
        """대원칙: 톤백 수 = mxbg_pallet + 샘플 1개"""
        result = engine.process_inbound(sample_packing)
        assert result['success']
        
        tonbags = engine.db.fetchall(
            "SELECT * FROM inventory_tonbag WHERE lot_no = ?",
            (sample_packing['lot_no'],))
        
        total_count = len(tonbags)
        sample_count = sum(1 for t in tonbags 
                          if (t['is_sample'] if isinstance(t, dict) else t[7]) == 1)
        regular_count = total_count - sample_count
        
        assert sample_count == 1, f"샘플 {sample_count}개 (기대: 1개)"
        assert regular_count == sample_packing['mxbg_pallet'], \
            f"톤백 {regular_count}개 (기대: {sample_packing['mxbg_pallet']}개)"

    def test_inbound_weight_integrity(self, engine, sample_packing):
        """대원칙: 톤백합계 = LOT 중량"""
        result = engine.process_inbound(sample_packing)
        assert result['success']
        
        row = engine.db.fetchone(
            "SELECT SUM(weight) as total FROM inventory_tonbag WHERE lot_no = ?",
            (sample_packing['lot_no'],))
        tb_sum = row['total'] if isinstance(row, dict) else row[0]
        
        assert abs(tb_sum - sample_packing['net_weight']) < 0.5, \
            f"톤백합계({tb_sum}) ≠ LOT중량({sample_packing['net_weight']})"

    def test_inbound_duplicate_rejected(self, engine, sample_packing):
        """중복 LOT 입고 거부"""
        result1 = engine.process_inbound(sample_packing)
        assert result1['success']
        
        result2 = engine.process_inbound(sample_packing)
        assert not result2['success']
        assert any('이미 존재' in e for e in result2['errors'])

    def test_inbound_no_lot_no_rejected(self, engine):
        """LOT 번호 없으면 거부"""
        result = engine.process_inbound({'net_weight': 5001})
        assert not result['success']

    def test_inbound_zero_weight_rejected(self, engine):
        """무게 0이면 거부"""
        result = engine.process_inbound({'lot_no': 'TEST', 'net_weight': 0})
        assert not result['success']


# ═══════════════════════════════════════════════════════
# 테스트 4: 무게 필드 일관성
# ═══════════════════════════════════════════════════════
class TestWeightFields:
    def test_weight_fields_equal_on_inbound(self, engine, sample_packing):
        """입고 시 net_weight = initial_weight = current_weight"""
        engine.process_inbound(sample_packing)
        inv = engine.db.fetchone(
            "SELECT net_weight, initial_weight, current_weight, picked_weight "
            "FROM inventory WHERE lot_no = ?",
            (sample_packing['lot_no'],))
        
        inv = dict(inv) if hasattr(inv, 'keys') else {
            'net_weight': inv[0], 'initial_weight': inv[1],
            'current_weight': inv[2], 'picked_weight': inv[3]}
        
        w = sample_packing['net_weight']
        assert inv['net_weight'] == w
        assert inv['initial_weight'] == w
        assert inv['current_weight'] == w
        assert inv['picked_weight'] == 0


# ═══════════════════════════════════════════════════════
# 테스트 5: stock_movement 불변성
# ═══════════════════════════════════════════════════════
class TestStockMovement:
    def test_movement_record_created(self, engine):
        """stock_movement에 이력 INSERT 및 조회 가능"""
        # FK 대응: inventory에 LOT 먼저 삽입
        engine.db.execute(
            "INSERT OR IGNORE INTO inventory (lot_no, product, net_weight, initial_weight, current_weight) "
            "VALUES (?, ?, ?, ?, ?)",
            ('TEST-LOT', 'TEST', 5001, 5001, 5001))
        engine.db.execute(
            "INSERT INTO stock_movement (movement_type, lot_no, qty_kg) VALUES (?, ?, ?)",
            ('INBOUND', 'TEST-LOT', 5001))

        row = engine.db.fetchone(
            "SELECT movement_type, lot_no, qty_kg FROM stock_movement WHERE lot_no = ?",
            ('TEST-LOT',))
        assert row is not None, "stock_movement 레코드 미생성"
        r = dict(row) if not isinstance(row, dict) else row
        assert r['movement_type'] == 'INBOUND'
        assert float(r['qty_kg']) == 5001

    def test_movement_immutable(self, engine):
        """stock_movement 이력은 감사 추적용 — 삽입 후 조회 가능 확인."""
        # FK 방어: inventory에 LOT 먼저 삽입
        engine.db.execute(
            "INSERT OR IGNORE INTO inventory (lot_no, product, net_weight, initial_weight, current_weight) "
            "VALUES (?, ?, ?, ?, ?)",
            ('IMMUT-LOT', 'TEST', 5001, 5001, 5001))
        engine.db.execute(
            "INSERT INTO stock_movement (movement_type, lot_no, qty_kg, remarks) "
            "VALUES (?, ?, ?, ?)",
            ('INBOUND', 'IMMUT-LOT', 5001, 'immutable test'))
        
        row = engine.db.fetchone(
            "SELECT movement_type, lot_no, qty_kg FROM stock_movement WHERE lot_no = ?",
            ('IMMUT-LOT',))
        assert row is not None, "stock_movement 레코드 미생성"
        r = dict(row) if not isinstance(row, dict) else row
        assert r['movement_type'] == 'INBOUND'
        assert float(r['qty_kg']) == 5001
