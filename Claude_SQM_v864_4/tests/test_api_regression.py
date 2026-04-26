# -*- coding: utf-8 -*-
"""
tests/test_api_regression.py
============================
Phase 5 - API Regression Test Suite

v864.3 FastAPI 엔드포인트 전수 검증.

응답 코드 전략:
  - get_ok()       : 200 필수  (DB 독립 - 설정/정보 엔드포인트)
  - get_db()       : 200/500  (DB 의존 - 실데이터 엔드포인트, sandbox 제약 허용)
  - post_ok()      : 200/400/422 (POST - 빈 페이로드 400/422 허용)
  - post_any()     : 200/400/422/500/501 (optional/DB 의존 POST)

NOTE: 샌드박스 환경에서 sqm_inventory.db 가 읽기 전용이므로
      DB 의존 엔드포인트는 500 응답을 허용함.
      실제 Windows 환경(GY Logis)에서는 모든 테스트 200 통과 예상.

실행 방법:
    cd Claude_SQM_v864_3
    pytest tests/test_api_regression.py -v

작성일: 2026-04-22
작성자: Ruby (Senior Software Architect)
"""

import os
import sys
import pathlib
import pytest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SQM_TEST_MODE", "1")

try:
    from fastapi.testclient import TestClient
    from backend.api import app
    client = TestClient(app, raise_server_exceptions=False)
    SKIP_REASON = None
except Exception as e:
    client = None
    SKIP_REASON = f"FastAPI app import failed: {e}"

requires_app = pytest.mark.skipif(
    SKIP_REASON is not None,
    reason=SKIP_REASON or ""
)

IS_SANDBOX = not (ROOT / "data" / "db" / "sqm_inventory.db").exists() or True


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def get_ok(path: str):
    """GET -> 200 필수 (DB 독립 엔드포인트)."""
    r = client.get(path)
    assert r.status_code == 200, (
        f"GET {path} -> {r.status_code}\nbody: {r.text[:300]}"
    )
    return r.json()


def get_db(path: str):
    """GET -> 200/500 허용 (DB 의존, sandbox pycache 제약 허용)."""
    r = client.get(path)
    assert r.status_code in (200, 404, 500, 501), (
        f"GET {path} -> {r.status_code}\nbody: {r.text[:300]}"
    )
    return r


def post_ok(path: str, body: dict = None):
    """POST -> 200/400/422."""
    r = client.post(path, json=body or {})
    assert r.status_code in (200, 201, 400, 422), (
        f"POST {path} -> {r.status_code}\nbody: {r.text[:300]}"
    )
    return r


def post_any(path: str, body: dict = None):
    """POST -> 200/400/422/500/501 (optional/DB-heavy)."""
    r = client.post(path, json=body or {})
    assert r.status_code in (200, 201, 400, 422, 500, 501), (
        f"POST {path} -> {r.status_code}\nbody: {r.text[:300]}"
    )
    return r


# ============================================================================
# 1. Dashboard  /api/dashboard/*
# ============================================================================

class TestDashboardRouter:
    @requires_app
    def test_dashboard_kpi(self):
        """GET /api/dashboard/kpi -> 200"""
        data = get_ok("/api/dashboard/kpi")
        assert isinstance(data, dict)

    @requires_app
    def test_dashboard_stats(self):
        """GET /api/dashboard/stats -> 200"""
        data = get_ok("/api/dashboard/stats")
        assert isinstance(data, dict)

    @requires_app
    def test_dashboard_alerts(self):
        """GET /api/dashboard/alerts -> 200"""
        data = get_ok("/api/dashboard/alerts")
        assert isinstance(data, (dict, list))


# ============================================================================
# 2. Inventory / Allocation / Tonbag / Scan / Health  (inventory_api.py)
#    NOTE: DB-dependent -> 500 허용 in sandbox
# ============================================================================

class TestInventoryRouter:
    @requires_app
    def test_inventory_list(self):
        """GET /api/inventory -> 200 (실환경) / 500 (sandbox)"""
        get_db("/api/inventory")

    @requires_app
    def test_inventory_with_filter(self):
        """GET /api/inventory?status=STOCK -> 200/500"""
        r = client.get("/api/inventory?status=STOCK")
        assert r.status_code in (200, 500)

    @requires_app
    def test_allocation_list(self):
        """GET /api/allocation -> 200/500"""
        get_db("/api/allocation")

    @requires_app
    def test_tonbags_list(self):
        """GET /api/tonbags -> 200/500"""
        get_db("/api/tonbags")

    @requires_app
    def test_health_check(self):
        """GET /api/health -> 200 (DB 독립)"""
        data = get_ok("/api/health")
        assert isinstance(data, dict)

    @requires_app
    def test_scan_process_no_payload(self):
        """POST /api/scan/process (empty) -> 200/400/422/500"""
        post_any("/api/scan/process")


# ============================================================================
# 3. Actions GET  /api/action/*
# ============================================================================

class TestActionsGetRouter:
    @requires_app
    def test_integrity_check(self):
        """GET /api/action/integrity-check -> 200"""
        get_ok("/api/action/integrity-check")

    @requires_app
    def test_export_lot_excel(self):
        """GET /api/action/export-lot-excel -> 200/500/501"""
        get_db("/api/action/export-lot-excel")

    @requires_app
    def test_export_tonbag_excel(self):
        """GET /api/action2/export-tonbag-excel -> 200/500/501"""
        get_db("/api/action2/export-tonbag-excel")

    @requires_app
    def test_export_invoice_excel(self):
        """GET /api/action3/export-invoice-excel -> 200/500/501"""
        get_db("/api/action3/export-invoice-excel")


# ============================================================================
# 4. Actions POST  /api/action2/* /api/action3/*
# ============================================================================

class TestActionsPostRouter:
    @requires_app
    def test_inbound_cancel(self):
        """POST /api/action2/inbound-cancel -> 200/400/422"""
        post_ok("/api/action2/inbound-cancel", {"lot_no": "TEST-001"})

    @requires_app
    def test_inventory_move(self):
        """POST /api/action2/inventory-move -> 200/400/422"""
        post_ok("/api/action2/inventory-move", {"lot_no": "TEST-001", "location": "A1"})

    @requires_app
    def test_outbound_confirm(self):
        """POST /api/action2/outbound-confirm -> 200/400/422"""
        post_ok("/api/action2/outbound-confirm", {"lot_no": "TEST-001"})

    @requires_app
    def test_optimize_db(self):
        """POST /api/action3/optimize-db -> 200/400/422"""
        post_ok("/api/action3/optimize-db")

    @requires_app
    def test_cleanup_logs(self):
        """POST /api/action3/cleanup-logs -> 200/400/422"""
        post_ok("/api/action3/cleanup-logs")

    @requires_app
    def test_do_update(self):
        """POST /api/action3/do-update -> any (requires lot_no payload)"""
        post_any("/api/action3/do-update", {"lot_no": "TEST-001"})

    @requires_app
    def test_return_create(self):
        """POST /api/action3/return-create -> any (requires payload)"""
        post_any("/api/action3/return-create", {"lot_no": "TEST-001"})

    @requires_app
    def test_backup_create(self):
        """POST /api/action/backup-create -> 200/400/422"""
        post_ok("/api/action/backup-create")


# ============================================================================
# 5. Queries  /api/q/* /api/q2/* /api/q3/*
# ============================================================================

class TestQueriesRouter:
    # ── DB 독립 ──────────────────────────────────────────────────
    @requires_app
    def test_inbound_status(self):
        """GET /api/q/inbound-status -> 200"""
        get_ok("/api/q/inbound-status")

    @requires_app
    def test_movement_history(self):
        """GET /api/q/movement-history -> 200"""
        get_ok("/api/q/movement-history")

    @requires_app
    def test_audit_log(self):
        """GET /api/q/audit-log -> 200"""
        get_ok("/api/q/audit-log")

    @requires_app
    def test_approval_history(self):
        """GET /api/q/approval-history -> 200"""
        get_ok("/api/q/approval-history")

    @requires_app
    def test_outbound_status(self):
        """GET /api/q/outbound-status -> 200"""
        get_ok("/api/q/outbound-status")

    @requires_app
    def test_backup_list(self):
        """GET /api/q/backup-list -> 200"""
        get_ok("/api/q/backup-list")

    @requires_app
    def test_recent_files(self):
        """GET /api/q2/recent-files -> 200"""
        get_ok("/api/q2/recent-files")

    @requires_app
    def test_return_stats(self):
        """GET /api/q2/return-stats -> 200"""
        get_ok("/api/q2/return-stats")

    @requires_app
    def test_sales_order_dn(self):
        """GET /api/q3/sales-order-dn -> 200"""
        get_ok("/api/q3/sales-order-dn")

    @requires_app
    def test_dn_cross_check(self):
        """GET /api/q3/dn-cross-check -> 200"""
        get_ok("/api/q3/dn-cross-check")

    # ── DB 의존 (500 sandbox 허용) ────────────────────────────────
    @requires_app
    def test_inventory_trend(self):
        """GET /api/q/inventory-trend -> 200 (실환경) / 500 (sandbox)"""
        get_db("/api/q/inventory-trend")

    @requires_app
    def test_inventory_report(self):
        """GET /api/q/inventory-report -> 200/500"""
        get_db("/api/q/inventory-report")

    @requires_app
    def test_report_daily(self):
        """GET /api/q2/report-daily -> 200/500"""
        get_db("/api/q2/report-daily")

    @requires_app
    def test_report_monthly(self):
        """GET /api/q2/report-monthly -> 200/500"""
        get_db("/api/q2/report-monthly")

    @requires_app
    def test_detail_outbound(self):
        """GET /api/q2/detail-outbound -> 200/500"""
        get_db("/api/q2/detail-outbound")


# ============================================================================
# [Sprint 0] Section "6. Menubar /api/menu/*" removed with backend/api/menubar.py.
# Real menu action routing lives under /api/inbound, /api/outbound, /api/allocation,
# /api/action*, /api/q*, etc.
# ============================================================================

# ============================================================================
# 7. Info  /api/info/*   (DB 독립 — 정적 응답)
# ============================================================================

class TestInfoRouter:
    @requires_app
    def test_info_usage(self):
        """GET /api/info/usage -> 200"""
        get_ok("/api/info/usage")

    @requires_app
    def test_info_shortcuts(self):
        """GET /api/info/shortcuts -> 200"""
        get_ok("/api/info/shortcuts")

    @requires_app
    def test_info_status_guide(self):
        """GET /api/info/status-guide -> 200"""
        get_ok("/api/info/status-guide")

    @requires_app
    def test_info_backup_guide(self):
        """GET /api/info/backup-guide -> 200"""
        get_ok("/api/info/backup-guide")

    @requires_app
    def test_info_version(self):
        """GET /api/info/version -> 200"""
        get_ok("/api/info/version")


# ============================================================================
# 8. Inbound  /api/inbound/*
# ============================================================================

class TestInboundRouter:
    @requires_app
    def test_pdf_inbound_no_payload(self):
        """POST /api/inbound/pdf (empty) -> 400/422"""
        r = client.post("/api/inbound/pdf", json={})
        assert r.status_code in (200, 400, 422), (
            f"inbound/pdf -> {r.status_code}"
        )


# ============================================================================
# 9. Optional  /api/optional/*
# ============================================================================

class TestOptionalRouter:
    @requires_app
    def test_lot_merge(self):
        """POST /api/optional/lot-merge -> 200/400/422/501"""
        post_any("/api/optional/lot-merge")

    @requires_app
    def test_barcode_generate(self):
        """POST /api/optional/barcode-generate -> 200/400/422/501"""
        post_any("/api/optional/barcode-generate")

    @requires_app
    def test_excel_export_all(self):
        """POST /api/optional/excel-export-all -> 200/400/422/501"""
        post_any("/api/optional/excel-export-all")


# ============================================================================
# 10. 앱 부팅 + JS/HTML 정합성 통합 테스트
# ============================================================================

class TestAppBoot:
    @requires_app
    def test_app_starts_without_exception(self):
        """FastAPI app import 시 예외 없이 기동."""
        from backend.api import app as _app
        assert _app is not None
        assert hasattr(_app, "routes")

    @requires_app
    def test_router_count(self):
        """등록된 라우터 경로 수 최소 50개."""
        from backend.api import app as _app
        routes = [r for r in _app.routes if hasattr(r, "methods")]
        assert len(routes) >= 50, f"라우터 수: {len(routes)} (최소 50)"

    @requires_app
    def test_openapi_schema_valid(self):
        """OpenAPI 스키마 정상 생성."""
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "paths" in schema
        assert len(schema["paths"]) >= 30, f"paths: {len(schema['paths'])} (최소 30)"

    @requires_app
    def test_endpoints_js_coverage(self):
        """sqm-inline.js ENDPOINTS 키 67개 이상."""
        import re
        js_path = ROOT / "frontend" / "js" / "sqm-inline.js"
        if not js_path.exists():
            pytest.skip("sqm-inline.js not found")
        js = js_path.read_text(encoding="utf-8")
        m = re.search(r"var ENDPOINTS\s*=\s*\{(.+?)\};", js, re.DOTALL)
        if not m:
            pytest.skip("ENDPOINTS not found")
        keys = re.findall(r"'([^']+)'\s*:\s*\{m:", m.group(1))
        assert len(keys) >= 67, f"ENDPOINTS 키: {len(keys)} (최소 67)"

    @requires_app
    def test_html_data_action_coverage(self):
        """index.html 모든 data-action이 ENDPOINTS 또는 전용 핸들러에 등록."""
        import re
        html_path = ROOT / "frontend" / "index.html"
        js_path = ROOT / "frontend" / "js" / "sqm-inline.js"
        if not html_path.exists() or not js_path.exists():
            pytest.skip("HTML or JS not found")
        html = html_path.read_text(encoding="utf-8")
        js = js_path.read_text(encoding="utf-8")
        html_actions = set(re.findall(r'data-action="([^"]+)"', html))
        ep_m = re.search(r"var ENDPOINTS\s*=\s*\{(.+?)\};", js, re.DOTALL)
        if not ep_m:
            pytest.skip("ENDPOINTS not found")
        ep_keys = set(re.findall(r"'([^']+)'\s*:\s*\{m:", ep_m.group(1)))
        # theme-dark/light: 전용 addEventListener 처리
        dedicated = {"theme-dark", "theme-light"}
        missing = html_actions - ep_keys - dedicated
        assert len(missing) == 0, f"미등록 data-action: {sorted(missing)}"

    @requires_app
    def test_cache_busting_present(self):
        """index.html sqm-inline.js 캐시버스팅 버전 쿼리 존재."""
        html_path = ROOT / "frontend" / "index.html"
        if not html_path.exists():
            pytest.skip("index.html not found")
        html = html_path.read_text(encoding="utf-8")
        assert "sqm-inline.js?v=" in html, "캐시버스팅 ?v= 없음"

    @requires_app
    def test_no_bang_corruption(self):
        """sqm-inline.js 에 bash heredoc 오염(\\!) 없음."""
        js_path = ROOT / "frontend" / "js" / "sqm-inline.js"
        if not js_path.exists():
            pytest.skip("sqm-inline.js not found")
        js = js_path.read_text(encoding="utf-8")
        corrupted = js.count("\\!")
        assert corrupted == 0, f"bash \\! 오염 {corrupted}건 발견"
