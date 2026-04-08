# -*- coding: utf-8 -*-
"""B02: Transaction guard — database.py transaction() 안전성 검증."""
import ast
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class TestTransactionContextManager(unittest.TestCase):
    """database.py transaction() 컨텍스트 매니저 구조 검증."""

    @classmethod
    def setUpClass(cls):
        db_path = os.path.join(PROJECT_ROOT, 'engine_modules', 'database.py')
        with open(db_path, encoding='utf-8') as f:
            cls.source = f.read()
            cls.tree = ast.parse(cls.source, db_path)

    def _find_method(self, class_name, method_name):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                        return item
        return None

    def test_transaction_method_exists(self):
        method = self._find_method('SQMDatabase', 'transaction')
        self.assertIsNotNone(method, "transaction() 메서드가 SQMDatabase에 존재해야 함")

    def test_transaction_has_rollback(self):
        self.assertIn('.rollback()', self.source,
                       "transaction() 내에 rollback() 호출이 있어야 함")

    def test_transaction_has_commit(self):
        self.assertIn('.commit()', self.source,
                       "transaction() 내에 commit() 호출이 있어야 함")

    def test_transaction_catches_all_exceptions(self):
        # transaction() 내에 'except Exception' 패턴이 있어야 함
        self.assertIn('except Exception', self.source,
                       "transaction()이 모든 예외를 잡아 롤백해야 함")

    def test_transaction_reraises(self):
        # rollback 후 raise가 있어야 함
        lines = self.source.splitlines()
        found_rollback = False
        found_raise_after = False
        for line in lines:
            if '.rollback()' in line:
                found_rollback = True
            if found_rollback and line.strip() == 'raise':
                found_raise_after = True
                break
        self.assertTrue(found_raise_after,
                        "rollback 후 예외를 다시 raise해야 함")

    def test_nested_transaction_support(self):
        self.assertIn('in_transaction', self.source,
                       "중첩 트랜잭션 감지 로직이 있어야 함")

    def test_write_lock_used(self):
        self.assertIn('_write_lock', self.source,
                       "스레드 안전을 위한 _write_lock이 사용되어야 함")


class TestOutboundTransactionUsage(unittest.TestCase):
    """outbound_mixin.py 의 주요 작업이 트랜잭션 내에서 실행되는지 검증."""

    @classmethod
    def setUpClass(cls):
        ob_path = os.path.join(PROJECT_ROOT, 'engine_modules', 'inventory_modular', 'outbound_mixin.py')
        with open(ob_path, encoding='utf-8') as f:
            cls.source = f.read()

    def test_reserve_from_allocation_uses_transaction(self):
        # reserve_from_allocation 내에 db.transaction 호출이 있어야 함
        idx = self.source.find('def reserve_from_allocation')
        self.assertNotEqual(idx, -1, "reserve_from_allocation 메서드 존재해야 함")
        # 해당 메서드 범위 내에서 transaction 사용 확인
        method_block = self.source[idx:idx + 5000]
        self.assertIn('self.db.transaction', method_block,
                       "reserve_from_allocation이 db.transaction()을 사용해야 함")

    def test_confirm_outbound_uses_transaction(self):
        idx = self.source.find('def confirm_outbound')
        self.assertNotEqual(idx, -1, "confirm_outbound 메서드 존재해야 함")
        method_block = self.source[idx:idx + 3000]
        self.assertIn('self.db.transaction', method_block,
                       "confirm_outbound이 db.transaction()을 사용해야 함")

    def test_no_raw_begin_commit_outside_transaction(self):
        # db.transaction() 외부에서 직접 BEGIN/COMMIT 호출이 없어야 함
        # (db.execute("BEGIN") 직접 호출은 위험)
        lines = self.source.splitlines()
        raw_begins = [i for i, l in enumerate(lines, 1)
                      if 'execute("BEGIN' in l or "execute('BEGIN" in l]
        # outbound_mixin에서 직접 BEGIN은 없어야 함
        self.assertEqual(len(raw_begins), 0,
                         f"outbound_mixin에서 직접 BEGIN 호출 발견: lines {raw_begins}")


if __name__ == '__main__':
    unittest.main()
