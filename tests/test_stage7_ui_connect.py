# -*- coding: utf-8 -*-
"""7단계 — UI 미연결 기능 6~10번 연결 검증"""
import os, sys, re, pytest

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML   = open(os.path.join(ROOT, 'frontend/index.html'),       encoding='utf-8').read()
INLINE = open(os.path.join(ROOT, 'frontend/js/sqm-inline.js'), encoding='utf-8').read()


def _ep(action):
    """ENDPOINTS 블록에서 해당 액션 항목 추출"""
    m = re.search(r'var ENDPOINTS = \{(.+?)^\s+\};', INLINE, re.DOTALL | re.MULTILINE)
    if not m: return ''
    found = re.search(r"'" + action + r"':\s*\{[^}]+\}", m.group(1))
    return found.group(0) if found else ''


# ═══════════════════════════════════════════════════
# 6. onOptimizeDb — DB 최적화 (VACUUM)
# ═══════════════════════════════════════════════════
class TestOptimizeDb:
    def test_button_in_html(self):
        assert 'data-action="onOptimizeDb"' in HTML

    def test_button_in_db_section(self):
        idx = HTML.index('data-action="onOptimizeDb"')
        section = HTML[max(0, idx-400):idx+100]
        assert 'DB' in section, "DB 최적화 버튼이 DB 메뉴 외부에 있음"

    def test_endpoint_uses_optimize_api(self):
        ep = _ep('onOptimizeDb')
        assert 'optimize-db' in ep, f"onOptimizeDb API URL 잘못됨: {ep}"

    def test_endpoint_is_post(self):
        ep = _ep('onOptimizeDb')
        assert "m:'POST'" in ep, f"onOptimizeDb method가 POST여야 함: {ep}"


# ═══════════════════════════════════════════════════
# 7. onIntegrityReport — 정합성 리포트
# ═══════════════════════════════════════════════════
class TestIntegrityReport:
    def test_button_in_html(self):
        assert 'data-action="onIntegrityReport"' in HTML

    def test_button_near_integrity_check(self):
        idx_check  = HTML.index('data-action="onIntegrityCheck"')
        idx_report = HTML.index('data-action="onIntegrityReport"')
        assert abs(idx_check - idx_report) < 300, "정합성 리포트 버튼이 정합성 검사 버튼과 멀리 떨어짐"

    def test_endpoint_uses_report_api(self):
        ep = _ep('onIntegrityReport')
        assert 'integrity-report' in ep, f"onIntegrityReport API URL 잘못됨: {ep}"

    def test_endpoint_is_get(self):
        ep = _ep('onIntegrityReport')
        assert "m:'GET'" in ep


# ═══════════════════════════════════════════════════
# 8. onProductInventoryReport — 품목별 재고 보고서
# ═══════════════════════════════════════════════════
class TestProductInventoryReport:
    def test_button_in_html(self):
        assert 'data-action="onProductInventoryReport"' in HTML

    def test_button_in_inventory_menu(self):
        idx = HTML.index('data-action="onProductInventoryReport"')
        section = HTML[max(0, idx-600):idx+100]
        assert '재고' in section

    def test_endpoint_uses_product_inventory_api(self):
        ep = _ep('onProductInventoryReport')
        assert 'product-inventory' in ep, f"onProductInventoryReport API URL 잘못됨: {ep}"


# ═══════════════════════════════════════════════════
# 9. onOutboundScheduled — 출고 예약 목록
# ═══════════════════════════════════════════════════
class TestOutboundScheduled:
    def test_button_in_html(self):
        assert 'data-action="onOutboundScheduled"' in HTML

    def test_button_in_outbound_menu(self):
        idx = HTML.index('data-action="onOutboundScheduled"')
        section = HTML[max(0, idx-600):idx+100]
        assert '출고' in section

    def test_endpoint_uses_scheduled_api(self):
        ep = _ep('onOutboundScheduled')
        assert 'scheduled' in ep, f"onOutboundScheduled API URL 잘못됨: {ep}"

    def test_endpoint_is_get_not_js(self):
        ep = _ep('onOutboundScheduled')
        assert "m:'GET'" in ep, f"onOutboundScheduled가 JS 탭이동이 아닌 GET API여야 함: {ep}"


# ═══════════════════════════════════════════════════
# 10. onLotListExcel — LOT 리스트 바로 열기
# ═══════════════════════════════════════════════════
class TestLotListExcel:
    def test_button_in_html(self):
        assert 'data-action="onLotListExcel"' in HTML

    def test_button_near_export_lot(self):
        idx_export = HTML.index('data-action="onExportLot"')
        idx_lot    = HTML.index('data-action="onLotListExcel"')
        assert abs(idx_export - idx_lot) < 300, "LOT 리스트 열기 버튼이 LOT 리스트 Excel 버튼과 멀리 떨어짐"

    def test_endpoint_registered(self):
        ep = _ep('onLotListExcel')
        assert ep, "onLotListExcel ENDPOINTS에 미등록"


# ═══════════════════════════════════════════════════
# 종합 — 6~10번 버튼 + ENDPOINTS 일괄 확인
# ═══════════════════════════════════════════════════
class TestAllTenConnected:
    @pytest.mark.parametrize("action,desc", [
        ("onOptimizeDb",             "DB 최적화"),
        ("onIntegrityReport",        "정합성 리포트"),
        ("onProductInventoryReport", "품목별 재고 보고서"),
        ("onOutboundScheduled",      "출고 예약 목록"),
        ("onLotListExcel",           "LOT 리스트 열기"),
    ])
    def test_button_exists(self, action, desc):
        assert f'data-action="{action}"' in HTML, \
            f"[{desc}] 버튼이 index.html에 없음"

    @pytest.mark.parametrize("action,desc", [
        ("onOptimizeDb",             "DB 최적화"),
        ("onIntegrityReport",        "정합성 리포트"),
        ("onProductInventoryReport", "품목별 재고 보고서"),
        ("onOutboundScheduled",      "출고 예약 목록"),
        ("onLotListExcel",           "LOT 리스트 열기"),
    ])
    def test_endpoint_registered(self, action, desc):
        assert f"'{action}'" in INLINE, \
            f"[{desc}] ENDPOINTS에 '{action}' 미등록"
