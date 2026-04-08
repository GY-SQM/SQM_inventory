# -*- coding: utf-8 -*-
"""B03: Status flow 안전성 검증."""
import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# 정상 상태 전이 맵
VALID_TRANSITIONS = {
    'AVAILABLE': {'RESERVED', 'PICKED', 'OUTBOUND'},
    'RESERVED': {'PICKED', 'AVAILABLE'},
    'PICKED': {'OUTBOUND', 'AVAILABLE', 'RESERVED'},
    'OUTBOUND': set(),  # 최종 상태 (return 제외)
}

# 금지 전이
ILLEGAL_TRANSITIONS = [
    ('AVAILABLE', 'OUTBOUND'),   # 직접 출고 금지 (PICKED 거쳐야 함) — 일부 빠른 출고 허용
    ('OUTBOUND', 'PICKED'),      # 역방향 전이 금지
]


class TestStatusWritePaths(unittest.TestCase):
    """inventory_tonbag 상태 UPDATE 경로 검증."""

    @classmethod
    def setUpClass(cls):
        cls.sources = {}
        target_files = [
            'engine_modules/inventory_modular/outbound_mixin.py',
            'core/barcode_scan_engine.py',
            'features/parsers/sales_order_engine.py',
            'gui_app_modular/tabs/scan_tab.py',
            'gui_app_modular/handlers/outbound_handlers.py',
            'gui_app_modular/tabs/allocation_tab.py',
        ]
        for f in target_files:
            fp = os.path.join(PROJECT_ROOT, f)
            if os.path.exists(fp):
                with open(fp, encoding='utf-8') as fh:
                    cls.sources[f] = fh.read()

    def test_no_new_sold_write_to_inventory_tonbag(self):
        """inventory_tonbag에 status='SOLD'를 직접 쓰는 코드가 없어야 함."""
        for fname, src in self.sources.items():
            lines = src.splitlines()
            for i, line in enumerate(lines, 1):
                if 'inventory_tonbag' in line and "status" in line:
                    # 같은 줄이나 근처에 SOLD가 있으면 안됨
                    nearby = src[max(0, src.find(line) - 200):src.find(line) + len(line) + 200]
                    if "='SOLD'" in nearby or '="SOLD"' in nearby:
                        # UPDATE inventory_tonbag SET status='SOLD' 패턴 검출
                        if 'UPDATE' in nearby and 'SET' in nearby:
                            self.fail(f"SOLD 직접 쓰기 발견: {fname}:{i}")

    def test_outbound_mixin_uses_status_constant(self):
        """outbound_mixin이 STATUS_OUTBOUND 상수를 사용하는지 확인."""
        src = self.sources.get('engine_modules/inventory_modular/outbound_mixin.py', '')
        self.assertIn('STATUS_OUTBOUND', src,
                       "outbound_mixin이 STATUS_OUTBOUND 상수를 사용해야 함")


class TestNoNewSoldWritePath(unittest.TestCase):
    """SOLD 직접 쓰기 경로 검사."""

    def test_sales_order_engine_tonbag_status_is_outbound(self):
        """sales_order_engine의 inventory_tonbag 상태 변경이 OUTBOUND인지 확인."""
        fp = os.path.join(PROJECT_ROOT, 'features', 'parsers', 'sales_order_engine.py')
        if not os.path.exists(fp):
            self.skipTest("파일 없음")
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        # UPDATE inventory_tonbag SET status='OUTBOUND' 패턴이 있어야 함
        self.assertIn("status='OUTBOUND'", src,
                       "sales_order_engine이 tonbag 상태를 OUTBOUND로 설정해야 함")


class TestDoubleOutboundGuard(unittest.TestCase):
    """이중 출고 차단 메커니즘 검증."""

    def test_double_outbound_guard_exists(self):
        """_co_guard_against_double_outbound 메서드가 존재해야 함."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'inventory_modular', 'outbound_mixin.py')
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('_co_guard_against_double_outbound', src)

    def test_confirm_outbound_calls_guard(self):
        """confirm_outbound이 이중 출고 가드를 호출해야 함."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'inventory_modular', 'outbound_mixin.py')
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        idx = src.find('def confirm_outbound')
        if idx == -1:
            self.skipTest("confirm_outbound 없음")
        method_block = src[idx:idx + 3000]
        self.assertIn('_co_guard_against_double_outbound', method_block)

    def test_preflight_has_already_outbound_code(self):
        """preflight에 ALREADY_OUTBOUND 에러 코드가 있어야 함."""
        fp = os.path.join(PROJECT_ROOT, 'engine_modules', 'preflight.py')
        if not os.path.exists(fp):
            self.skipTest("preflight.py 없음")
        with open(fp, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('ALREADY_OUTBOUND', src)


if __name__ == '__main__':
    unittest.main()
