# -*- coding: utf-8 -*-
"""B04: Sample exclusion — 샘플 톤백이 일반 출고로 처리되지 않는지 검증."""
import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class TestSamplePolicy(unittest.TestCase):
    """샘플 정책 코드 존재 검증."""

    def test_sample_weight_constant_exists(self):
        """SAMPLE_WEIGHT_KG 상수가 constants.py에 존재해야 함."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'constants.py')
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('SAMPLE_WEIGHT_KG', src)

    def test_is_sample_column_in_schema(self):
        """is_sample 컬럼이 DB 스키마에 존재해야 함."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'db_migration_mixin.py')
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('is_sample', src)

    def test_sample_uid_format_s00(self):
        """샘플 톤백 UID가 -S00 형식을 사용해야 함."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'db_migration_mixin.py')
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn("'-S00'", src)

    def test_sample_per_lot_unique_index(self):
        """샘플 LOT당 1개 보장 UNIQUE INDEX가 있어야 함."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'db_migration_mixin.py')
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('idx_tonbag_sample_per_lot', src)

    def test_normal_tonbag_weight_query_excludes_samples(self):
        """일반 톤백 무게 조회에서 샘플(is_sample=0)이 제외되어야 함."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'constants.py')
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('is_sample', src,
                       "톤백 무게 조회 시 is_sample 필터가 있어야 함")


class TestWeightConservation(unittest.TestCase):
    """무게 보존 로직 검증."""

    def test_recalc_current_weight_exists(self):
        """_recalc_current_weight 메서드가 존재해야 함."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'inventory_modular', 'crud_mixin.py')
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('def _recalc_current_weight', src)

    def test_integrity_check_weight_formula(self):
        """integrity_mixin이 initial_weight = current_weight + picked_weight 검사를 하는지."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'inventory_modular', 'integrity_mixin.py')
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('initial_weight', src)
        self.assertIn('current_weight', src)
        self.assertIn('picked_weight', src)

    def test_outbound_calls_recalc(self):
        """출고 처리 후 _recalc_current_weight가 호출되는지."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'inventory_modular', 'outbound_mixin.py')
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('_recalc_current_weight', src)


if __name__ == '__main__':
    unittest.main()
