# -*- coding: utf-8 -*-
"""B05: outbound_handlers.py 분할 후 스모크 테스트."""
import ast
import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class TestOutboundHandlersSplit(unittest.TestCase):
    """outbound_handlers.py 분할 검증."""

    @classmethod
    def setUpClass(cls):
        fp = os.path.join(PROJECT_ROOT, 'gui_app_modular', 'handlers', 'outbound_handlers.py')
        with open(fp, encoding='utf-8') as f:
            cls.source = f.read()
            cls.tree = ast.parse(cls.source, fp)

    def _get_method_lines(self, method_name):
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
                return node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
        return None

    def test_py_compile(self):
        """파일이 컴파일 가능해야 함."""
        import py_compile
        fp = os.path.join(PROJECT_ROOT, 'gui_app_modular', 'handlers', 'outbound_handlers.py')
        py_compile.compile(fp, doraise=True)

    def test_picking_upload_extracted(self):
        """_on_picking_list_upload에서 헬퍼가 추출되었어야 함."""
        self.assertIn('_oh_picking_gate1_flow', self.source)
        self.assertIn('_oh_picking_legacy_flow', self.source)
        self.assertIn('_oh_picking_show_gate1_fail', self.source)
        self.assertIn('_oh_picking_confirm_gate1_proceed', self.source)
        self.assertIn('_oh_picking_execute_gate1', self.source)

    def test_picking_upload_reduced(self):
        """_on_picking_list_upload 메서드가 축소되었어야 함."""
        lines = self._get_method_lines('_on_picking_list_upload')
        self.assertIsNotNone(lines)
        self.assertLess(lines, 80, f"_on_picking_list_upload은 80줄 미만이어야 함 (현재 {lines}줄)")


class TestPublicSignatureStable(unittest.TestCase):
    """공개 메서드 시그니처 보존 확인."""

    @classmethod
    def setUpClass(cls):
        fp = os.path.join(PROJECT_ROOT, 'gui_app_modular', 'handlers', 'outbound_handlers.py')
        with open(fp, encoding='utf-8') as f:
            cls.tree = ast.parse(f.read(), fp)
        cls.methods = set()
        for node in ast.walk(cls.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cls.methods.add(node.name)

    def test_public_methods_exist(self):
        """핵심 공개 메서드가 존재해야 함."""
        required = [
            '_on_picking_list_upload',
            '_on_barcode_scan_upload',
            '_on_barcode_live_scan',
        ]
        for m in required:
            self.assertIn(m, self.methods, f"{m} 메서드가 유지되어야 함")

    def test_helpers_use_oh_prefix(self):
        """추출된 헬퍼는 _oh_ 접두사를 사용해야 함."""
        oh_methods = [m for m in self.methods if m.startswith('_oh_')]
        self.assertGreater(len(oh_methods), 0, "_oh_ 접두사 헬퍼가 있어야 함")


if __name__ == '__main__':
    unittest.main()
