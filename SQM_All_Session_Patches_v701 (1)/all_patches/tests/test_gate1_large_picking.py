# -*- coding: utf-8 -*-
"""
SQM v6.12.1 — Gate-1 교차검증 + 60LOT/300MT 대용량 파싱 테스트
================================================================
"""
import sys
import os
import sqlite3
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


# ═══════════════════════════════════════════════════
# 헬퍼: 인메모리 DB
# ═══════════════════════════════════════════════════
class FakeDB:
    """Gate-1 테스트용 인메모리 DB 래퍼."""

    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self._setup()

    def _setup(self):
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE allocation_plan (
                id INTEGER PRIMARY KEY,
                lot_no TEXT, tonbag_id INTEGER, status TEXT DEFAULT 'RESERVED',
                qty_mt REAL, executed_at TEXT, cancelled_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE inventory_tonbag (
                id INTEGER PRIMARY KEY,
                lot_no TEXT, weight REAL, status TEXT, is_sample INTEGER DEFAULT 0,
                tonbag_uid TEXT, picked_date TEXT, updated_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE stock_movement (
                id INTEGER PRIMARY KEY, lot_no TEXT, movement_type TEXT,
                qty_kg REAL, created_at TEXT
            )
        """)
        self.conn.commit()

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def fetchone(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    class _TxCtx:
        def __init__(self, conn):
            self.conn = conn
        def __enter__(self):
            return self
        def __exit__(self, *a):
            if a[0]:
                self.conn.rollback()
            else:
                self.conn.commit()

    def transaction(self, mode=''):
        return self._TxCtx(self.conn)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def insert_lot(self, lot_no, tonbag_count=10, unit_weight=500):
        """LOT + 톤백 + allocation_plan INSERT."""
        for i in range(tonbag_count):
            tb_id = self.conn.execute(
                "INSERT INTO inventory_tonbag (lot_no, weight, status, is_sample) VALUES (?,?,?,0)",
                (lot_no, unit_weight, 'RESERVED')
            ).lastrowid
            self.conn.execute(
                "INSERT INTO allocation_plan (lot_no, tonbag_id, status) VALUES (?,?,'RESERVED')",
                (lot_no, tb_id)
            )
        # 샘플
        self.conn.execute(
            "INSERT INTO inventory_tonbag (lot_no, weight, status, is_sample) VALUES (?,1.0,'RESERVED',1)",
            (lot_no,)
        )
        self.conn.commit()


# ═══════════════════════════════════════════════════
# 모듈 로드
# ═══════════════════════════════════════════════════
from parsers.document_parser_modular.picking_mixin import (
    PickingListParserMixin, PickingLotItem, PickingListResult, PickingListMeta,
    _normalize_num, RE_QUANTITY, RE_QUANTITY_LOOSE, RE_LOT_ONLY, RE_EURO_NUMBER
)


# ═══════════════════════════════════════════════════
# 1. 정규식 테스트
# ═══════════════════════════════════════════════════
class TestRegexPatterns:
    """정규식 패턴 기본 검증."""

    def test_quantity_standard(self):
        m = RE_QUANTITY.match("Quantity: 5.00 MT")
        assert m
        assert _normalize_num(m.group(1)) == 5.0
        assert m.group(2).upper() == 'MT'

    def test_quantity_euro_format(self):
        """유럽식 숫자: 5.000,00 → 5000.0"""
        val = _normalize_num("5.000,00")
        assert val == 5000.0

    def test_quantity_loose(self):
        m = RE_QUANTITY_LOOSE.match("5.00 MT")
        assert m
        assert m.group(2).upper() == 'MT'

    def test_lot_only_10digit(self):
        m = RE_LOT_ONLY.match("1125072350")
        assert m
        assert m.group(1) == "1125072350"

    def test_lot_only_reject_short(self):
        """9자리 이하 → 매칭 안 됨."""
        m = RE_LOT_ONLY.match("123456789")
        assert m is None


# ═══════════════════════════════════════════════════
# 2. 파서 테스트 — 표준 10LOT
# ═══════════════════════════════════════════════════
class TestPickingParser10LOT:
    """표준 10LOT / 50MT 파싱."""

    def _make_blocks(self, lot_count=10, weight_mt=5.0):
        blocks = ["PICKING LIST", "3073", "80007418", "LBM-LC20250901"]
        blocks += [f"dummy_{i}" for i in range(6)]  # 패딩
        blocks += ["01.01.2025", "FOB", "x", "15 x40'"]
        blocks += [f"dummy_{i}" for i in range(3)]
        for i in range(lot_count):
            lot = f"112507{2350 + i:04d}"
            # 본품
            blocks.append(f"Quantity: {weight_mt:.2f} MT")
            blocks.append(f"Batch number: {lot}")
            blocks.append(f"Storage location: K001")
            # 샘플
            blocks.append(f"Quantity: 1.00 KG")
            blocks.append(f"Batch number: {lot}")
            blocks.append(f"Storage location: K001")
        return blocks

    def test_parse_10lot(self):
        parser = PickingListParserMixin()
        blocks = self._make_blocks(10, 5.0)
        result = parser._parse_blocks(blocks)
        assert result.success
        assert result.summary['total_lots'] == 10
        assert abs(result.summary['total_mt'] - 50.0) < 0.01

    def test_parse_meta(self):
        parser = PickingListParserMixin()
        blocks = self._make_blocks(10, 5.0)
        result = parser._parse_blocks(blocks)
        assert result.meta.sales_order == '80007418'
        assert '15' in result.meta.containers


# ═══════════════════════════════════════════════════
# 3. 대용량 60LOT / 300MT 파싱
# ═══════════════════════════════════════════════════
class TestPickingParser60LOT:
    """60LOT / 300MT 대용량 파싱."""

    def _make_large_blocks(self, lot_count=60, weight_mt=5.0):
        blocks = ["PICKING LIST", "3099", "80009999", "LBM-LC20260101"]
        blocks += [f"dummy_{i}" for i in range(6)]
        blocks += ["15.01.2026", "CIF", "x", "15 x40'"]
        blocks += [f"dummy_{i}" for i in range(3)]
        for i in range(lot_count):
            lot = f"112608{1000 + i:04d}"
            blocks.append(f"Quantity: {weight_mt:.2f} MT")
            blocks.append(f"Batch number: {lot}")
            blocks.append(f"Storage location: K00{(i % 3) + 1}")
            blocks.append(f"Quantity: 1.00 KG")
            blocks.append(f"Batch number: {lot}")
            blocks.append(f"Storage location: K00{(i % 3) + 1}")
        return blocks

    def test_parse_60lot(self):
        parser = PickingListParserMixin()
        blocks = self._make_large_blocks(60, 5.0)
        result = parser._parse_blocks(blocks)
        assert result.success, f"Errors: {result.errors}"
        assert result.summary['total_lots'] == 60
        assert abs(result.summary['total_mt'] - 300.0) < 0.01
        assert result.summary['block_count'] > 350

    def test_parse_60lot_1000kg(self):
        """60LOT × 10MT (1000kg 톤백)."""
        parser = PickingListParserMixin()
        blocks = self._make_large_blocks(60, 10.0)
        result = parser._parse_blocks(blocks)
        assert result.success, f"Errors: {result.errors}"
        assert result.summary['total_lots'] == 60
        assert abs(result.summary['total_mt'] - 600.0) < 0.01

    def test_summary_has_dedup_stats(self):
        parser = PickingListParserMixin()
        blocks = self._make_large_blocks(60)
        result = parser._parse_blocks(blocks)
        assert 'block_count' in result.summary
        assert 'raw_items' in result.summary
        assert 'dedup_removed' in result.summary

    def test_duplicate_lot_detection(self):
        """동일 LOT이 2번 등장 → 중복 경고 + dedup."""
        parser = PickingListParserMixin()
        blocks = self._make_large_blocks(10, 5.0)
        # 동일 LOT 재추가
        blocks.append("Quantity: 5.00 MT")
        blocks.append("Batch number: 1126081000")
        blocks.append("Storage location: K001")
        result = parser._parse_blocks(blocks)
        assert result.success
        assert result.summary['total_lots'] == 10  # dedup → 10개
        assert any('중복' in w for w in result.warnings)


# ═══════════════════════════════════════════════════
# 4. 루즈 매칭 폴백 테스트
# ═══════════════════════════════════════════════════
class TestLooseMatching:
    """Quantity: 라벨 없는 비정형 문서."""

    def test_loose_fallback(self):
        parser = PickingListParserMixin()
        # "Quantity:" 라벨 없이 값만 있음
        blocks = [
            "PICKING LIST", "3073", "80007418", "LBM-LC20250901",
            *[f"d{i}" for i in range(10)],
            "5.00 MT",
            "1125072350",
            "K001",
            "1.00 KG",
            "1125072350",
            "K001",
        ]
        result = parser._parse_blocks(blocks)
        assert result.success
        assert result.summary['total_lots'] == 1
        assert any('루즈' in w for w in result.warnings)


# ═══════════════════════════════════════════════════
# 5. _parse_meta 정규식 하이브리드
# ═══════════════════════════════════════════════════
class TestMetaHybrid:
    """고정 인덱스 실패 시 정규식 보정."""

    def test_regex_fallback_sales_order(self):
        parser = PickingListParserMixin()
        # PICKING LIST 이후 블록 순서가 깨진 문서 (고정 인덱스 → 값이 비정상)
        blocks = [
            "PICKING LIST",
            "",  # idx 0: 비어있음 (picking_no 누락)
            "",  # idx 1: 비어있음 (sales_order 누락)
            "Customer reference: LBM-LC20250901",
            *[f"filler_{i}" for i in range(40)],
            "Sales order: 80007418",  # 정규식이 여기서 잡아야 함
        ]
        meta = parser._parse_meta(blocks)
        assert '80007418' in meta.sales_order

    def test_email_regex(self):
        parser = PickingListParserMixin()
        blocks = [
            "PICKING LIST", *[f"x{i}" for i in range(22)],
            "contact@sqm.com",
            *[f"x{i}" for i in range(20)],
        ]
        meta = parser._parse_meta(blocks)
        assert 'sqm.com' in meta.contact_email


# ═══════════════════════════════════════════════════
# 6. Gate-1 수량 교차 검증 테스트
# ═══════════════════════════════════════════════════
class TestGate1CrossValidation:
    """Gate-1 LOT 대조 + 수량 검증."""

    def _make_gate1_engine(self, db):
        """outbound_mixin의 gate1_verify_picking을 호출할 수 있는 객체."""
        from engine_modules.inventory_modular.outbound_mixin import OutboundMixin
        engine = OutboundMixin.__new__(OutboundMixin)
        engine.db = db
        return engine

    def test_full_match(self):
        """10LOT 전체 매칭 + 수량 일치."""
        db = FakeDB()
        lots = [f"112507{2350 + i:04d}" for i in range(10)]
        for lot in lots:
            db.insert_lot(lot, 10, 500)

        engine = self._make_gate1_engine(db)
        picking = {
            'items': [{'lot_no': lot, 'qty_kg': 5000.0} for lot in lots]
        }
        result = engine.gate1_verify_picking(picking, 'PK-TEST-001')
        assert result['passed']
        assert len(result['matched_lots']) == 10
        assert len(result['qty_mismatches']) == 0
        assert '완전 통과' in result['error_report']

    def test_qty_mismatch(self):
        """수량 불일치 → 조건부 통과."""
        db = FakeDB()
        db.insert_lot('LOT001', 10, 500)  # 10×500 = 5000kg

        engine = self._make_gate1_engine(db)
        picking = {'items': [{'lot_no': 'LOT001', 'qty_kg': 10000.0}]}  # 불일치
        result = engine.gate1_verify_picking(picking, 'PK-TEST-002')
        assert result['passed']  # LOT 매칭은 OK → 조건부 통과
        assert len(result['qty_mismatches']) == 1
        assert '조건부 통과' in result['error_report']

    def test_missing_lot(self):
        """RESERVED에 없는 LOT → 실패."""
        db = FakeDB()
        db.insert_lot('LOT001', 10, 500)

        engine = self._make_gate1_engine(db)
        picking = {
            'items': [
                {'lot_no': 'LOT001', 'qty_kg': 5000.0},
                {'lot_no': 'LOT999', 'qty_kg': 5000.0},  # DB에 없음
            ]
        }
        result = engine.gate1_verify_picking(picking, 'PK-TEST-003')
        assert not result['passed']
        assert 'LOT999' in result['only_in_picking']
        assert '실패' in result['error_report']

    def test_60lot_performance(self):
        """60LOT Gate-1 수행."""
        db = FakeDB()
        lots = [f"112608{1000 + i:04d}" for i in range(60)]
        for lot in lots:
            db.insert_lot(lot, 10, 500)

        engine = self._make_gate1_engine(db)
        picking = {'items': [{'lot_no': lot, 'qty_kg': 5000.0} for lot in lots]}
        result = engine.gate1_verify_picking(picking, 'PK-LARGE-001')
        assert result['passed']
        assert len(result['matched_lots']) == 60
        assert len(result['lot_details']) == 60

    def test_gate1_to_json(self):
        """Gate-1 결과 JSON 직렬화."""
        db = FakeDB()
        db.insert_lot('LOT001', 10, 500)
        engine = self._make_gate1_engine(db)
        picking = {'items': [{'lot_no': 'LOT001', 'qty_kg': 5000.0}]}
        result = engine.gate1_verify_picking(picking, 'PK-JSON')

        from engine_modules.inventory_modular.outbound_mixin import OutboundMixin
        json_str = OutboundMixin._gate1_to_json(result)
        parsed = json.loads(json_str)
        assert parsed['passed'] is True
        assert 'LOT001' in parsed['matched_lots']


# ═══════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
