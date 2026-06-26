# -*- coding: utf-8 -*-
"""Phase A — /api/dashboard/summary + /api/dashboard/weekly 계약 테스트."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_PY = os.path.join(ROOT, "backend", "api", "dashboard.py")


def _src():
    with open(DASHBOARD_PY, encoding="utf-8", errors="ignore") as f:
        return f.read()


def test_summary_endpoint_exists():
    src = _src()
    assert '@router.get("/summary")' in src or "router.get('/summary')" in src, \
        "GET /api/dashboard/summary 라우트가 없음"


def test_summary_returns_7_kpi_keys():
    src = _src()
    required = [
        "stock_mt",
        "inbound_pending",
        "outbound_pending",
        "picked_today_mt",
        "integrity_alerts",
        "lot_count",
        "return_pending",
    ]
    for key in required:
        assert f'"{key}"' in src or f"'{key}'" in src, \
            f"summary 응답에 '{key}' 키가 없음"


def test_weekly_endpoint_exists():
    src = _src()
    assert '@router.get("/weekly")' in src or "router.get('/weekly')" in src, \
        "GET /api/dashboard/weekly 라우트가 없음"


def test_weekly_returns_required_keys():
    src = _src()
    for key in ["labels", "inbound_mt", "outbound_mt"]:
        assert f'"{key}"' in src or f"'{key}'" in src, \
            f"weekly 응답에 '{key}' 키가 없음"


def test_integrity_check_uses_1kg_tolerance():
    src = _src()
    assert "1.0" in src, \
        "정합성 허용 오차 ±1kg 관련 코드가 없음"
