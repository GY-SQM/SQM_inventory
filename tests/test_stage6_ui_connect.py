# -*- coding: utf-8 -*-
"""6단계 — 로직 있지만 UI 미연결 기능 5개 연결 검증"""
import os, sys, pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

HTML  = open(os.path.join(ROOT, 'frontend/index.html'), encoding='utf-8').read()
INLINE = open(os.path.join(ROOT, 'frontend/js/sqm-inline.js'), encoding='utf-8').read()
CORE   = open(os.path.join(ROOT, 'frontend/js/sqm-core.js'), encoding='utf-8').read()


# ═══════════════════════════════════════════════════
# 1. onIntegrityRepair — 정합성 자동 복구
# ═══════════════════════════════════════════════════
class TestIntegrityRepair:
    def test_button_in_html(self):
        assert 'data-action="onIntegrityRepair"' in HTML, \
            "정합성 자동 복구 버튼이 index.html에 없음"

    def test_button_in_integrity_section(self):
        idx = HTML.index('data-action="onIntegrityRepair"')
        section = HTML[max(0, idx-300):idx+100]
        assert '정합성' in section, "정합성 섹션 바깥에 버튼이 배치됨"

    def test_endpoint_uses_fix_integrity_api(self):
        assert "fix-integrity" in INLINE, \
            "onIntegrityRepair ENDPOINT가 fix-integrity API를 사용하지 않음"

    def test_endpoint_is_post(self):
        import re
        m = re.search(r"'onIntegrityRepair':\s*\{m:'([^']+)'", INLINE)
        assert m and m.group(1) == 'POST', \
            f"onIntegrityRepair method가 POST여야 함 (현재: {m.group(1) if m else 'NOT FOUND'})"


# ═══════════════════════════════════════════════════
# 2. onGlobalSearch — 전역 통합 검색
# ═══════════════════════════════════════════════════
class TestGlobalSearch:
    def test_button_in_toolbar(self):
        assert 'data-action="onGlobalSearch"' in HTML, \
            "통합 검색 버튼이 index.html에 없음"

    def test_button_is_topbar(self):
        idx = HTML.index('data-action="onGlobalSearch"')
        nearby = HTML[max(0, idx-100):idx+50]
        assert 'topbar-btn' in nearby, "통합 검색 버튼이 툴바(topbar-btn)에 없음"

    def test_ctrl_f_shortcut(self):
        assert "case 'C-f'" in CORE, "Ctrl+F 단축키가 sqm-core.js에 없음"

    def test_ctrl_f_dispatches_global_search(self):
        idx = CORE.index("case 'C-f'")
        line = CORE[idx:idx+80]
        assert 'onGlobalSearch' in line, "Ctrl+F가 onGlobalSearch를 호출하지 않음"

    def test_endpoint_registered(self):
        assert "'onGlobalSearch'" in INLINE, \
            "onGlobalSearch가 ENDPOINTS에 등록되지 않음"


# ═══════════════════════════════════════════════════
# 3. onOutboundHistory — 출고 이력 조회
# ═══════════════════════════════════════════════════
class TestOutboundHistory:
    def test_button_in_html(self):
        assert 'data-action="onOutboundHistory"' in HTML, \
            "출고 이력 조회 버튼이 index.html에 없음"

    def test_button_in_outbound_menu(self):
        idx = HTML.index('data-action="onOutboundHistory"')
        section = HTML[max(0, idx-500):idx+100]
        assert '출고' in section, "출고 이력 버튼이 출고 메뉴 외부에 있음"

    def test_endpoint_uses_correct_api(self):
        import re
        m = re.search(r"'onOutboundHistory':\s*\{[^}]+u:'([^']+)'", INLINE)
        assert m and 'outbound' in m.group(1), \
            f"onOutboundHistory API URL이 잘못됨: {m.group(1) if m else 'NOT FOUND'}"


# ═══════════════════════════════════════════════════
# 4. onDetailOfOutbound — 출고 상세 내역
# ═══════════════════════════════════════════════════
class TestDetailOfOutbound:
    def test_button_in_html(self):
        assert 'data-action="onDetailOfOutbound"' in HTML, \
            "출고 상세 내역 버튼이 index.html에 없음"

    def test_button_near_outbound_history(self):
        idx_hist = HTML.index('data-action="onOutboundHistory"')
        idx_detail = HTML.index('data-action="onDetailOfOutbound"')
        assert abs(idx_hist - idx_detail) < 300, \
            "출고 상세 버튼이 출고 이력 버튼과 멀리 떨어져 있음"

    def test_endpoint_uses_detail_api(self):
        import re
        m = re.search(r"'onDetailOfOutbound':\s*\{[^}]+u:'([^']+)'", INLINE)
        assert m and 'detail' in m.group(1), \
            f"onDetailOfOutbound API URL이 잘못됨: {m.group(1) if m else 'NOT FOUND'}"


# ═══════════════════════════════════════════════════
# 5. onInventoryTrend — 재고 추이 데이터
# ═══════════════════════════════════════════════════
class TestInventoryTrend:
    def test_button_in_html(self):
        assert 'data-action="onInventoryTrend"' in HTML, \
            "재고 추이 데이터 버튼이 index.html에 없음"

    def test_button_in_inventory_menu(self):
        idx = HTML.index('data-action="onInventoryTrend"')
        section = HTML[max(0, idx-500):idx+100]
        assert '재고' in section, "재고 추이 버튼이 재고 메뉴 외부에 있음"

    def test_button_near_stock_trend_chart(self):
        idx_chart = HTML.index('data-action="onStockTrendChart"')
        idx_trend  = HTML.index('data-action="onInventoryTrend"')
        assert abs(idx_chart - idx_trend) < 300, \
            "재고 추이 데이터 버튼이 재고 추이 차트 버튼과 멀리 떨어져 있음"

    def test_endpoint_uses_inventory_trend_api(self):
        import re
        m = re.search(r"'onInventoryTrend':\s*\{[^}]+u:'([^']+)'", INLINE)
        assert m and 'inventory-trend' in m.group(1), \
            f"onInventoryTrend API URL이 잘못됨: {m.group(1) if m else 'NOT FOUND'}"


# ═══════════════════════════════════════════════════
# 전체 — 5개 버튼 모두 HTML에 있는지 종합 확인
# ═══════════════════════════════════════════════════
class TestAllFiveConnected:
    @pytest.mark.parametrize("action,desc", [
        ("onIntegrityRepair",  "정합성 자동 복구"),
        ("onGlobalSearch",     "통합 검색"),
        ("onOutboundHistory",  "출고 이력 조회"),
        ("onDetailOfOutbound", "출고 상세 내역"),
        ("onInventoryTrend",   "재고 추이 데이터"),
    ])
    def test_button_exists(self, action, desc):
        assert f'data-action="{action}"' in HTML, \
            f"[{desc}] data-action=\"{action}\" 버튼이 index.html에 없음"

    @pytest.mark.parametrize("action,desc", [
        ("onIntegrityRepair",  "정합성 자동 복구"),
        ("onGlobalSearch",     "통합 검색"),
        ("onOutboundHistory",  "출고 이력 조회"),
        ("onDetailOfOutbound", "출고 상세 내역"),
        ("onInventoryTrend",   "재고 추이 데이터"),
    ])
    def test_endpoint_registered(self, action, desc):
        assert f"'{action}'" in INLINE, \
            f"[{desc}] ENDPOINTS에 '{action}' 미등록"
