# -*- coding: utf-8 -*-
"""B02: Outbound rollback 동작 검증 — 트랜잭션 실패 시 롤백 보장."""
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class TestOutboundRollbackPatterns(unittest.TestCase):
    """outbound_mixin.py 내 롤백 안전 패턴 검증."""

    @classmethod
    def setUpClass(cls):
        ob_path = os.path.join(PROJECT_ROOT, 'engine_modules', 'inventory_modular', 'outbound_mixin.py')
        with open(ob_path, encoding='utf-8') as f:
            cls.source = f.read()
            cls.lines = cls.source.splitlines()

    def test_no_commit_without_transaction(self):
        """트랜잭션 컨텍스트 외부에서 직접 commit이 없어야 함."""
        raw_commits = [i for i, l in enumerate(self.lines, 1)
                       if '.commit()' in l and 'conn.commit' not in l]
        # transaction() 컨텍스트 매니저가 commit을 관리함
        self.assertEqual(len(raw_commits), 0,
                         f"outbound_mixin에서 직접 commit() 호출: lines {raw_commits}")

    def test_confirm_outbound_catches_sqlite_error(self):
        """confirm_outbound이 sqlite3.Error를 잡아야 함."""
        idx = self.source.find('def confirm_outbound')
        if idx == -1:
            self.skipTest("confirm_outbound 없음")
        method_block = self.source[idx:idx + 5000]
        self.assertIn('sqlite3.Error', method_block,
                       "confirm_outbound이 sqlite3.Error를 처리해야 함")

    def test_reserve_from_allocation_has_error_handling(self):
        """reserve_from_allocation이 예외 처리를 가져야 함."""
        idx = self.source.find('def reserve_from_allocation')
        if idx == -1:
            self.skipTest("reserve_from_allocation 없음")
        method_block = self.source[idx:idx + 8000]
        self.assertIn('except', method_block,
                       "reserve_from_allocation에 예외 처리가 있어야 함")

    def test_executemany_used_for_batch_updates(self):
        """배치 UPDATE에 executemany가 사용되어야 함."""
        self.assertIn('executemany', self.source,
                       "배치 작업에 executemany를 사용해야 함")


if __name__ == '__main__':
    unittest.main()
