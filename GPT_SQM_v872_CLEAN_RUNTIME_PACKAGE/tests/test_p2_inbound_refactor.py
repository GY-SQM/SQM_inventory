"""
P2_BATCH_A 통합 테스트 — onestop_inbound 구조 분리 검증
======================================================

테스트 대상:
  1. InboundParser import 및 기본 동작
  2. InboundValidator import 및 기본 동작
  3. InboundRepository import 및 기본 동작
  4. InboundService 파이프라인 동작
  5. onestop_inbound.py 정상 import
"""
import sys
import os

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestInboundParser:
    """S2: InboundParser 분리 검증"""

    def test_import(self):
        from features.parsers.inbound_parser import InboundParser
        assert InboundParser is not None

    def test_instantiate(self):
        from features.parsers.inbound_parser import InboundParser
        parser = InboundParser(log_fn=lambda msg: None)
        assert parser is not None

    def test_empty_row(self):
        from features.parsers.inbound_parser import InboundParser
        row = InboundParser.empty_row(1)
        assert row['no'] == '1'
        assert 'lot_no' in row
        assert 'bl_no' in row
        assert 'net_weight' in row

    def test_format_bl(self):
        from features.parsers.inbound_parser import InboundParser
        assert InboundParser.format_bl('') == ''
        assert InboundParser.format_bl('123456789') == 'MAEU123456789'
        assert InboundParser.format_bl('MSCU12345') == 'MSCU12345'

    def test_date_str(self):
        from features.parsers.inbound_parser import InboundParser
        assert InboundParser.date_str(None) == ''
        assert InboundParser.date_str('None') == ''
        assert InboundParser.date_str('2024-01-15') == '2024-01-15'

    def test_lot_order_key(self):
        from features.parsers.inbound_parser import InboundParser
        # dict with list_no
        assert InboundParser.lot_order_key({'list_no': 3}, 1) == (0, 3)
        assert InboundParser.lot_order_key({'list_no': None}, 5) == (1, 5)

    def test_fill_do_no_do(self):
        from features.parsers.inbound_parser import InboundParser
        row = InboundParser.empty_row(1)
        InboundParser.fill_do(row, None)
        assert row['arrival_date'] == ''

    def test_merge_results_empty(self):
        from features.parsers.inbound_parser import InboundParser
        parser = InboundParser(log_fn=lambda msg: None)
        result = parser.merge_results(None, None, None, None)
        assert result == []

    def test_extract_template_hints_empty(self):
        from features.parsers.inbound_parser import InboundParser
        parser = InboundParser(log_fn=lambda msg: None)
        ctx = parser.extract_template_hints({})
        assert 'bag_weight' in ctx
        assert 'hint_packing' in ctx
        assert 'tpl_carrier_id' in ctx

    def test_extract_template_hints_with_data(self):
        from features.parsers.inbound_parser import InboundParser
        parser = InboundParser(log_fn=lambda msg: None)
        ctx = parser.extract_template_hints({
            'bag_weight_kg': 1000,
            'template_id': 'MSC_DEFAULT',
            'carrier_id': '',
        })
        assert ctx['bag_weight'] == 1000
        assert ctx['tpl_carrier_id'] == 'MSC'  # template_id 추론


class TestInboundValidator:
    """S3: InboundValidator 분리 검증"""

    def test_import(self):
        from features.validators.inbound_validator import InboundValidator
        assert InboundValidator is not None

    def test_validate_date_valid(self):
        from features.validators.inbound_validator import InboundValidator
        assert InboundValidator.validate_date('2024-01-15') is True
        assert InboundValidator.validate_date('') is True

    def test_validate_date_invalid(self):
        from features.validators.inbound_validator import InboundValidator
        assert InboundValidator.validate_date('invalid') is False
        assert InboundValidator.validate_date('2024-13-01') is False

    def test_calc_dates(self):
        from features.validators.inbound_validator import InboundValidator
        cr, ft, err = InboundValidator.calc_dates('2024-01-15', '', '14')
        assert cr == '2024-01-29'
        assert ft == '14'
        assert err == ''

    def test_calc_dates_from_con_return(self):
        from features.validators.inbound_validator import InboundValidator
        cr, ft, err = InboundValidator.calc_dates('2024-01-15', '2024-01-25', '')
        assert ft == '10'
        assert err == ''

    def test_calc_dates_error(self):
        from features.validators.inbound_validator import InboundValidator
        _, _, err = InboundValidator.calc_dates('invalid', '', '')
        assert err != ''

    def test_preflight_validate_ok(self):
        from features.validators.inbound_validator import InboundValidator
        rows = [{'lot_no': 'LOT001', 'product': 'X', 'net_weight': 100, 'mxbg_pallet': 10}]
        errors = InboundValidator.preflight_validate(rows)
        assert len(errors) == 0

    def test_preflight_validate_missing_lot(self):
        from features.validators.inbound_validator import InboundValidator
        rows = [{'lot_no': '', 'product': 'X', 'net_weight': 100, 'mxbg_pallet': 10}]
        errors = InboundValidator.preflight_validate(rows)
        assert any('LOT NO' in e for e in errors)

    def test_preflight_validate_duplicate_lot(self):
        from features.validators.inbound_validator import InboundValidator
        rows = [
            {'lot_no': 'LOT001', 'product': 'X', 'net_weight': 100, 'mxbg_pallet': 10},
            {'lot_no': 'LOT001', 'product': 'Y', 'net_weight': 200, 'mxbg_pallet': 10},
        ]
        errors = InboundValidator.preflight_validate(rows)
        assert any('중복' in e for e in errors)

    def test_has_required_docs(self):
        from features.validators.inbound_validator import InboundValidator
        docs = [('BL', '', True), ('PL', '', True), ('DO', '', False)]
        assert InboundValidator.has_required_docs({'BL': 'a', 'PL': 'b'}, docs) is True
        assert InboundValidator.has_required_docs({'BL': 'a'}, docs) is False


class TestInboundRepository:
    """S4: InboundRepository 분리 검증"""

    def test_import(self):
        from features.repositories.inbound_repository import InboundRepository
        assert InboundRepository is not None

    def test_build_doc_dicts_no_docs(self):
        from features.repositories.inbound_repository import InboundRepository

        class MockEngine:
            pass

        repo = InboundRepository(MockEngine())
        inv, bl, do = repo.build_doc_dicts(None, None, None)
        assert inv is None
        assert bl is None
        assert do is None

    def test_build_packing_dict(self):
        from features.repositories.inbound_repository import InboundRepository

        class MockEngine:
            pass

        repo = InboundRepository(MockEngine())
        row = {
            'lot_no': 'LOT001', 'lot_sqm': '500', 'sap_no': 'SAP001',
            'bl_no': 'BL001', 'container_no': 'CONT001',
            'product': 'LITHIUM CARBONATE', 'product_code': 'LC01',
            'net_weight': '1000', 'gross_weight': '1100',
            'mxbg_pallet': '10', 'salar_invoice_no': 'INV001',
            'ship_date': '2024-01-15', 'arrival_date': '2024-02-01',
            'con_return': '2024-02-15', 'free_time': '14',
            'warehouse': 'WH01',
        }
        packing = repo.build_packing_dict(row, None, None, None, None)
        assert packing['lot_no'] == 'LOT001'
        assert packing['net_weight'] == 1000.0
        assert packing['mxbg_pallet'] == 10


class TestInboundService:
    """S5: InboundService 파이프라인 검증"""

    def test_import(self):
        from features.services.inbound_service import InboundService
        assert InboundService is not None

    def test_instantiate(self):
        from features.services.inbound_service import InboundService

        class MockEngine:
            def process_inbound(self, **kw):
                return {'success': True}
            def inventory_lot_exists(self, lot_no):
                return False

        svc = InboundService(MockEngine())
        assert svc.parser is not None
        assert svc.validator is not None
        assert svc.repository is not None

    def test_validate_preview(self):
        from features.services.inbound_service import InboundService

        class MockEngine:
            pass

        svc = InboundService(MockEngine())
        rows = [{'lot_no': 'LOT001', 'product': 'X', 'net_weight': 100, 'mxbg_pallet': 10}]
        errors = svc.validate_preview(rows)
        assert len(errors) == 0

    def test_validate_date(self):
        from features.services.inbound_service import InboundService

        class MockEngine:
            pass

        svc = InboundService(MockEngine())
        assert svc.validate_date('2024-01-15') is True
        assert svc.validate_date('invalid') is False

    def test_calc_dates(self):
        from features.services.inbound_service import InboundService

        class MockEngine:
            pass

        svc = InboundService(MockEngine())
        cr, ft, err = svc.calc_dates('2024-01-15', '', '14')
        assert cr == '2024-01-29'
        assert err == ''

    def test_check_required_docs(self):
        from features.services.inbound_service import InboundService

        class MockEngine:
            pass

        svc = InboundService(MockEngine())
        docs = [('BL', '', True), ('PL', '', True), ('DO', '', False)]
        assert svc.check_required_docs({'BL': 'a', 'PL': 'b'}, docs) is True


class TestOnestopInboundImport:
    """S6: onestop_inbound.py 정상 import 확인"""

    def test_module_syntax(self):
        """onestop_inbound.py 구문 검사"""
        import py_compile
        py_compile.compile(
            os.path.join(PROJECT_ROOT, 'gui_app_modular', 'dialogs', 'onestop_inbound.py'),
            doraise=True,
        )

    def test_mixin_syntax(self):
        """inbound_upload_mixin.py 구문 검사"""
        import py_compile
        py_compile.compile(
            os.path.join(PROJECT_ROOT, 'gui_app_modular', 'dialogs', 'inbound_upload_mixin.py'),
            doraise=True,
        )

    def test_preview_columns_consistent(self):
        """InboundParser의 PREVIEW_COLUMNS와 onestop_inbound의 PREVIEW_COLUMNS 일치 확인"""
        from features.parsers.inbound_parser import PREVIEW_COLUMNS as parser_cols

        # onestop_inbound의 PREVIEW_COLUMNS를 직접 파일에서 파싱
        import ast
        src = open(os.path.join(PROJECT_ROOT, 'gui_app_modular', 'dialogs', 'onestop_inbound.py'),
                   'r', encoding='utf-8').read()
        # 첫 번째 PREVIEW_COLUMNS 정의 찾기
        idx = src.find('PREVIEW_COLUMNS = [')
        assert idx >= 0, "PREVIEW_COLUMNS not found in onestop_inbound.py"
        end = src.find('\n]', idx)
        snippet = src[idx:end+2]
        ns = {}
        exec(snippet, ns)
        orig_cols = ns['PREVIEW_COLUMNS']

        assert len(parser_cols) == len(orig_cols), \
            f"Column count mismatch: parser={len(parser_cols)} orig={len(orig_cols)}"
        for i, (pc, oc) in enumerate(zip(parser_cols, orig_cols)):
            assert pc[0] == oc[0], f"Column {i} key mismatch: {pc[0]} != {oc[0]}"
