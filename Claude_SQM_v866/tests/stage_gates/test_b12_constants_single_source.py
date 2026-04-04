# -*- coding: utf-8 -*-
"""
B12 Stage-Gate: constants single-source-of-truth 검증 (AST-based)
=================================================================
engine_modules/constants.py에 핵심 비즈니스 상수가 정의되어 있는지 AST로 확인.
(런타임 import는 DB 의존성으로 실패할 수 있으므로 AST 분석 사용)
"""
import ast
import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class TestConstantsSingleSource(unittest.TestCase):
    """engine_modules/constants.py 상수 정의 검증."""

    @classmethod
    def setUpClass(cls):
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'constants.py')
        with open(fp, encoding='utf-8') as f:
            cls.tree = ast.parse(f.read(), fp)
        cls.names = set()
        for node in ast.walk(cls.tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        cls.names.add(t.id)

    def test_constants_file_exists(self):
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'constants.py')
        self.assertTrue(os.path.exists(fp))

    def test_status_available(self):
        self.assertIn('STATUS_AVAILABLE', self.names)

    def test_status_outbound(self):
        self.assertIn('STATUS_OUTBOUND', self.names)

    def test_status_picked(self):
        self.assertIn('STATUS_PICKED', self.names)

    def test_status_reserved(self):
        self.assertIn('STATUS_RESERVED', self.names)

    def test_sample_weight_kg(self):
        self.assertIn('SAMPLE_WEIGHT_KG', self.names)

    def test_default_tonbag_weight(self):
        self.assertIn('DEFAULT_TONBAG_WEIGHT', self.names)

    def test_statuses_current(self):
        self.assertIn('STATUSES_CURRENT', self.names)

    def test_statuses_outbound_all(self):
        self.assertIn('STATUSES_OUTBOUND_ALL', self.names)

    def test_allocation_status_constants(self):
        for name in ['ALLOC_STAGED', 'ALLOC_RESERVED', 'ALLOC_EXECUTED',
                      'ALLOC_CANCELLED', 'ALLOC_REJECTED']:
            self.assertIn(name, self.names, f"{name} not found in constants.py")

    def test_core_constants_reexport_file(self):
        """core/constants.py가 존재하고 engine_modules.constants를 import하는지."""
        fp = os.path.join(PROJECT_ROOT, 'core', 'constants.py')
        if not os.path.exists(fp):
            self.skipTest("core/constants.py not found")
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('engine_modules.constants', src)


if __name__ == '__main__':
    unittest.main()
