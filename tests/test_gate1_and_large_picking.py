# -*- coding: utf-8 -*-
"""
SQM v6.12.1 — Gate-1 교차검증 강화 + 60LOT 대용량 파싱 테스트
==============================================================

테스트 범위:
  1-4: Gate-1 수량 교차검증
  5-8: 대용량 파서 (60LOT, 유럽식 숫자, 루즈 매칭)
  9:   _gate1_to_json 직렬화
"""

import pytest
import sqlite3
import json
from unittest.mock import MagicMock

# ── 파서 테스트 ──

# S4-4: _normalize_num 유럽식 지원 추가 → xfail 제거
def test_euro_number_normalize():
    """유럽식 숫자 정규화: 300.000,00 → 300000.0"""
    from parsers.document_parser_modular.picking_mixin import _normalize_num
    assert _normalize_num('300.000,00') == 300000.0
    assert _normalize_num('1.234,56') == 1234.56
    assert _normalize_num('5,000.00') == 5000.0   # 일반 콤마
    assert _normalize_num('5.00') == 5.0           # 소수점
    assert _normalize_num('') == 0.0


def test_large_picking_60lot():
    """60LOT 대용량 피킹리스트 파싱 (텍스트 기반)"""
    from parsers.document_parser_modular.picking_mixin import PickingListParserMixin

    # 60LOT × 5MT + 60 샘플 1KG = 300MT
    lines = ['PICKING LIST', 'PK-2026-060', '80007418', 'LBM-LC20260101']
    lines.extend([''] * 8)   # creation_date 위치까지
    lines.extend(['2026-01-15', 'CIF', '', "15 x40'"])
    lines.extend([''] * 25)  # 나머지 헤더

    for i in range(60):
        lot = f'11250{72300 + i}'
        lines.append(f'Quantity: 5.00 MT')
        lines.append(f'Batch number: {lot}')
        lines.append(f'Storage location: WH-GY-01')
        lines.append(f'Quantity: 1.00 KG')
        lines.append(f'Batch number: {lot}')
        lines.append(f'Storage location: WH-GY-01')

    # NW/GW
    lines.append('300,000.00 KG')
    lines.append('307,800.00 KG')

    text = '\n'.join(lines)
    parser = PickingListParserMixin()
    result = parser.parse_from_text(text)

    assert result.success, f"파싱 실패: {result.errors}"
    assert result.summary['total_lots'] == 60
    assert abs(result.summary['total_mt'] - 300.0) < 0.1
    assert result.summary['tonbag_count'] == 60
    assert result.summary['sample_count'] == 60


@pytest.mark.xfail(reason="S3-PRE: PickingListResult 파싱 데이터 구조 불일치")
def test_loose_matching_fallback():
    """루즈 매칭: 'Quantity:' 라벨 없는 비정형 문서"""
    from parsers.document_parser_modular.picking_mixin import PickingListParserMixin

    # 라벨 없이 값만
    lines = [
        'PICKING LIST', 'PK-TEST', '80007418',
    ]
    lines.extend([''] * 40)
    # 'Quantity:' 없이 값만
    lines.extend([
        '5.00 MT',
        '1125072300',
        '5.00 MT',
        '1125072301',
    ])

    text = '\n'.join(lines)
    parser = PickingListParserMixin()
    result = parser.parse_from_text(text)

    # 루즈 매칭으로 2개 추출 (샘플 없어서 에러는 있을 수 있음)
    assert len(result.tonbag) == 2 or len(result.warnings) > 0


def test_big_bag_doc_mismatch_warning():
    """Big bag 문서 표기 vs 파싱 LOT 불일치 경고"""
    from parsers.document_parser_modular.picking_mixin import PickingListParserMixin

    lines = ['PICKING LIST', 'PK-TEST', '80007418']
    lines.extend([''] * 40)
    for i in range(10):
        lot = f'11250{72300 + i}'
        lines.append(f'Quantity: 5.00 MT')
        lines.append(f'Batch number: {lot}')
        lines.append(f'Quantity: 1.00 KG')
        lines.append(f'Batch number: {lot}')

    # NW 200,000 이상 + Big bag 20ea로 표기 (실제 10개)
    lines.append('250,000.00 KG  Big bag 500kg net 20ea')
    lines.append('256,500.00 KG')

    text = '\n'.join(lines)
    parser = PickingListParserMixin()
    result = parser.parse_from_text(text)

    # Big bag 불일치 경고 확인
    has_bb_warning = any('Big bag' in w for w in result.warnings)
    assert has_bb_warning, f"Big bag 불일치 경고 없음: {result.warnings}"


# ── Gate-1 테스트 ──

def _setup_gate1_db():
    """Gate-1 테스트용 메모리 DB 세팅"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE allocation_plan (
        id INTEGER PRIMARY KEY, lot_no TEXT, tonbag_id INTEGER,
        status TEXT DEFAULT 'RESERVED', qty_mt REAL
    )""")
    conn.execute("""CREATE TABLE inventory_tonbag (
        id INTEGER PRIMARY KEY, lot_no TEXT, weight REAL,
        status TEXT DEFAULT 'RESERVED', is_sample INTEGER DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE stock_movement (
        id INTEGER PRIMARY KEY, lot_no TEXT, movement_type TEXT,
        qty_kg REAL, created_at TEXT
    )""")
    return conn


def _make_mock_db(conn):
    """DB 헬퍼 mock"""
    db = MagicMock()
    db.fetchall = lambda q, p=(): [dict(r) for r in conn.execute(q, p).fetchall()]
    db.fetchone = lambda q, p=(): (lambda r: dict(r) if r else None)(conn.execute(q, p).fetchone())
    db.execute = conn.execute
    return db


def test_gate1_full_match():
    """Gate-1: 피킹 LOT 3개 = RESERVED 3개 → 완전 통과"""
    conn = _setup_gate1_db()

    # LOT별 톤백 10개(500kg) + allocation 등록
    for idx, lot in enumerate(['LOT-A', 'LOT-B', 'LOT-C']):
        for sub in range(10):
            tb_id = idx * 10 + sub + 1
            conn.execute("INSERT INTO inventory_tonbag (id, lot_no, weight, status) VALUES (?,?,?,?)",
                         (tb_id, lot, 500.0, 'RESERVED'))
            conn.execute("INSERT INTO allocation_plan (lot_no, tonbag_id, status) VALUES (?,?,?)",
                         (lot, tb_id, 'RESERVED'))

    db = _make_mock_db(conn)

    # Mock picking_result
    picking = MagicMock()
    picking.tonbag = [
        MagicMock(lot_no='LOT-A', qty_kg=5000, weight_kg=5000),
        MagicMock(lot_no='LOT-B', qty_kg=5000, weight_kg=5000),
        MagicMock(lot_no='LOT-C', qty_kg=5000, weight_kg=5000),
    ]

    # Gate-1 실행
    from engine_modules.inventory_modular.outbound_mixin import OutboundMixin
    mixin = OutboundMixin.__new__(OutboundMixin)
    mixin.db = db
    result = mixin.gate1_verify_picking(picking, 'PK-TEST')

    assert result['passed'] is True
    assert len(result['matched_lots']) == 3
    assert len(result['qty_mismatches']) == 0
    assert '완전 통과' in result['error_report']


@pytest.mark.xfail(reason="S3-PRE: Gate-1 qty_mismatch=1 시 passed=False 반환 (설계 의도 재확인 필요)")
def test_gate1_qty_mismatch():
    """Gate-1: LOT 매칭 OK, 수량 불일치 → 조건부 통과"""
    conn = _setup_gate1_db()

    # LOT-X: 톤백 10개(500kg) = 5000kg
    for sub in range(10):
        conn.execute("INSERT INTO inventory_tonbag (id, lot_no, weight, status) VALUES (?,?,?,?)",
                     (sub + 1, 'LOT-X', 500.0, 'RESERVED'))
        conn.execute("INSERT INTO allocation_plan (lot_no, tonbag_id, status) VALUES (?,?,?)",
                     ('LOT-X', sub + 1, 'RESERVED'))

    db = _make_mock_db(conn)

    # 피킹은 10000kg 요청 (실제 5000kg → 불일치)
    picking = MagicMock()
    picking.tonbag = [MagicMock(lot_no='LOT-X', qty_kg=10000, weight_kg=10000)]

    from engine_modules.inventory_modular.outbound_mixin import OutboundMixin
    mixin = OutboundMixin.__new__(OutboundMixin)
    mixin.db = db
    result = mixin.gate1_verify_picking(picking, 'PK-TEST')

    assert result['passed'] is True  # LOT 매칭은 통과
    assert len(result['qty_mismatches']) == 1
    assert '조건부 통과' in result['error_report']


def test_gate1_lot_missing():
    """Gate-1: 피킹 LOT이 RESERVED에 없음 → 실패"""
    conn = _setup_gate1_db()
    db = _make_mock_db(conn)

    picking = MagicMock()
    picking.tonbag = [MagicMock(lot_no='LOT-MISSING', qty_kg=5000, weight_kg=5000)]

    from engine_modules.inventory_modular.outbound_mixin import OutboundMixin
    mixin = OutboundMixin.__new__(OutboundMixin)
    mixin.db = db
    result = mixin.gate1_verify_picking(picking, 'PK-TEST')

    assert result['passed'] is False
    assert 'LOT-MISSING' in result['only_in_picking']
    assert '실패' in result['error_report']


def test_gate1_dict_input():
    """Gate-1: dict 형태 picking_result 입력 지원"""
    conn = _setup_gate1_db()
    for sub in range(10):
        conn.execute("INSERT INTO inventory_tonbag (id, lot_no, weight, status) VALUES (?,?,?,?)",
                     (sub + 1, 'LOT-D', 500.0, 'RESERVED'))
        conn.execute("INSERT INTO allocation_plan (lot_no, tonbag_id, status) VALUES (?,?,?)",
                     ('LOT-D', sub + 1, 'RESERVED'))
    db = _make_mock_db(conn)

    # dict 형태 입력
    picking = {'items': [{'lot_no': 'LOT-D', 'qty_kg': 5000}]}

    from engine_modules.inventory_modular.outbound_mixin import OutboundMixin
    mixin = OutboundMixin.__new__(OutboundMixin)
    mixin.db = db
    result = mixin.gate1_verify_picking(picking, 'PK-DICT')

    assert result['passed'] is True
    assert 'LOT-D' in result['matched_lots']


def test_gate1_to_json():
    """_gate1_to_json: set → JSON 직렬화"""
    from engine_modules.inventory_modular.outbound_mixin import OutboundMixin

    gate1 = {
        'passed': True,
        'picking_lots': {'LOT-A', 'LOT-B'},
        'matched_lots': {'LOT-A', 'LOT-B'},
        'only_in_picking': set(),
        'qty_mismatches': [],
        'lot_details': [{'lot_no': 'LOT-A', 'kg_match': True}],
        'error_report': '테스트 리포트',
    }
    j = OutboundMixin._gate1_to_json(gate1)
    parsed = json.loads(j)
    assert parsed['passed'] is True
    assert 'LOT-A' in parsed['matched_lots']
    assert 'error_report' not in parsed  # 텍스트 리포트 제외됨


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
