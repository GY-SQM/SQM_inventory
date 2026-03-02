# -*- coding: utf-8 -*-
"""
SQM v6.2.7 — 제품 마스터 헬퍼 + 리포트 테스트
"""

import os
import sys
import importlib.util
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# tkinter 없는 환경에서도 테스트 가능하도록 직접 import
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_helper_path = os.path.join(_base, 'gui_app_modular', 'dialogs', 'product_master_helper.py')
_spec = importlib.util.spec_from_file_location("product_master_helper", _helper_path)
_helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helper)

_dialog_path = os.path.join(_base, 'gui_app_modular', 'dialogs', 'product_master_dialog.py')
_spec2 = importlib.util.spec_from_file_location("product_master_dialog", _dialog_path)
_dialog = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(_dialog)

get_product_choices = _helper.get_product_choices
parse_product_choice = _helper.parse_product_choice
get_product_code_map = _helper.get_product_code_map
auto_detect_product_code = _helper.auto_detect_product_code
get_product_inventory_report = _helper.get_product_inventory_report
ensure_product_master_table = _dialog.ensure_product_master_table


from tests.conftest import inbound_lot


@pytest.fixture
def db(engine):
    ensure_product_master_table(engine.db)
    return engine.db


class TestGetProductChoices:
    """콤보박스 선택지 생성."""

    def test_returns_list(self, db):
        choices = get_product_choices(db)
        assert isinstance(choices, list)
        assert len(choices) >= 8

    def test_format_with_code(self, db):
        choices = get_product_choices(db, include_code=True)
        assert any('LCA' in c and '—' in c for c in choices)

    def test_format_without_code(self, db):
        choices = get_product_choices(db, include_code=False)
        assert any('Lithium Carbonate' in c for c in choices)
        assert not any('—' in c for c in choices)


class TestParseProductChoice:
    """콤보박스 선택값 파싱."""

    def test_with_code(self):
        code, name = parse_product_choice("LCA — Lithium Carbonate Anhydrous")
        assert code == "LCA"
        assert name == "Lithium Carbonate Anhydrous"

    def test_without_code(self):
        code, name = parse_product_choice("Lithium Carbonate")
        assert code == ""
        assert name == "Lithium Carbonate"

    def test_empty(self):
        code, name = parse_product_choice("")
        assert code == ""
        assert name == ""


class TestAutoDetectProductCode:
    """제품명 → 코드 자동감지."""

    def test_exact_match(self, db):
        code = auto_detect_product_code(db, "Lithium Carbonate Anhydrous")
        assert code == "LCA"

    def test_case_insensitive(self, db):
        code = auto_detect_product_code(db, "LITHIUM CARBONATE ANHYDROUS")
        assert code == "LCA"

    def test_partial_match(self, db):
        code = auto_detect_product_code(db, "LITHIUM CARBONATE")
        assert code in ("LCA", "")  # 포함 매칭 또는 키워드 매칭

    def test_nickel_sulfate(self, db):
        code = auto_detect_product_code(db, "Nickel Sulfate Hexahydrate")
        assert code == "NSH"

    def test_keyword_fallback(self, db):
        code = auto_detect_product_code(db, "IRON PHOSPHATE BATTERY GRADE")
        assert code == "LFP"

    def test_empty(self, db):
        code = auto_detect_product_code(db, "")
        assert code == ""

    def test_unknown(self, db):
        code = auto_detect_product_code(db, "RANDOM CHEMICAL XYZ")
        assert code == ""


class TestGetProductCodeMap:
    """full_name → code 매핑."""

    def test_returns_dict(self, db):
        m = get_product_code_map(db)
        assert isinstance(m, dict)
        assert len(m) > 0

    def test_contains_lca(self, db):
        m = get_product_code_map(db)
        assert 'LITHIUM CARBONATE ANHYDROUS' in m
        assert m['LITHIUM CARBONATE ANHYDROUS'] == 'LCA'


class TestProductInventoryReport:
    """제품별 재고 리포트."""

    def test_empty_db(self, db):
        """재고 없을 때 빈 리스트."""
        report = get_product_inventory_report(db)
        assert isinstance(report, list)

    def test_with_inventory(self, engine, db):
        """재고 있을 때 리포트 생성."""
        inbound_lot(engine, {
            'lot_no': 'RPT00001',
            'product': 'LITHIUM CARBONATE',
            'mxbg_pallet': 10,
            'net_weight': 5001.0,
        })
        inbound_lot(engine, {
            'lot_no': 'RPT00002',
            'product': 'NICKEL SULFATE',
            'mxbg_pallet': 5,
            'net_weight': 2501.0,
        })

        report = get_product_inventory_report(db)
        assert len(report) >= 1  # 최소 1개 제품

    def test_report_fields(self, engine, db):
        """리포트 필드 구조."""
        inbound_lot(engine, {
            'lot_no': 'RPT00010',
            'product': 'Lithium Carbonate Anhydrous',
            'mxbg_pallet': 10,
            'net_weight': 5001.0,
        })

        report = get_product_inventory_report(db)
        assert len(report) >= 1

        # 첫 번째 항목 필드 확인
        item = report[0]
        item = dict(item) if not isinstance(item, dict) else item
        assert 'lot_count' in item
        assert 'total_kg' in item or 'total' in item
