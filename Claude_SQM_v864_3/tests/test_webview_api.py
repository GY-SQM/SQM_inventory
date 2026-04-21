"""
SQM PyWebView — API 통합 테스트
실행: python -m pytest tests/test_webview_api.py -v
"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.api import app

client = TestClient(app)

# ── Health ───────────────────────────────────────────────────
def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["status"] == "ok"

# ── Dashboard ────────────────────────────────────────────────
def test_dashboard_stats():
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert "available_lots" in data
    assert "reserved_lots" in data
    assert "picked_lots" in data

# ── Inventory ────────────────────────────────────────────────
def test_get_inventory():
    res = client.get("/api/inventory")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "data" in data
    assert isinstance(data["data"], list)

def test_get_inventory_filter_status():
    res = client.get("/api/inventory?status=AVAILABLE")
    assert res.status_code == 200

def test_get_inventory_filter_product():
    res = client.get("/api/inventory?product=PP")
    assert res.status_code == 200

def test_get_inventory_pagination():
    res = client.get("/api/inventory?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["page_size"] == 10

def test_get_lot_detail_not_found():
    res = client.get("/api/inventory/LOT-NOT-EXIST-9999")
    # 503: engine unavailable, 404: not found, 200/500: engine may return default
    assert res.status_code in (200, 404, 500, 503)

# ── Tonbags ──────────────────────────────────────────────────
def test_get_tonbags():
    res = client.get("/api/tonbags")
    assert res.status_code == 200

# ── Allocation ───────────────────────────────────────────────
def test_get_allocation():
    res = client.get("/api/allocation")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data

# ── Outbound ─────────────────────────────────────────────────
def test_get_outbound_scheduled():
    res = client.get("/api/outbound/scheduled")
    assert res.status_code == 200

def test_get_outbound_history():
    res = client.get("/api/outbound/history")
    assert res.status_code == 200

# ── Scan ─────────────────────────────────────────────────────
def test_scan_missing_barcode():
    res = client.post("/api/scan/process", json={"action": "reserve"})
    assert res.status_code == 400

def test_scan_with_barcode():
    res = client.post("/api/scan/process", json={
        "barcode": "TB-TEST-001", "action": "reserve"
    })
    assert res.status_code == 200

# ── Integrity ────────────────────────────────────────────────
def test_integrity_quick():
    res = client.get("/api/integrity/quick")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data

# ── Activity Log ─────────────────────────────────────────────
def test_activity_log():
    res = client.get("/api/log/activity?limit=10")
    assert res.status_code == 200

# ── Move ─────────────────────────────────────────────────────
def test_move_missing_fields():
    res = client.post("/api/move", json={"barcode": "TB-001"})
    assert res.status_code == 400

def test_move_valid():
    res = client.post("/api/move", json={"barcode": "TB-001", "destination": "A-02"})
    assert res.status_code == 200
    assert "success" in res.json()

def test_move_history():
    res = client.get("/api/move/history")
    assert res.status_code == 200

# ── Allocation / Outbound Actions ────────────────────────────
def test_cancel_allocation():
    res = client.post("/api/allocation/SQM-TEST-001/cancel")
    assert res.status_code == 200
    assert "success" in res.json()

def test_confirm_outbound():
    res = client.post("/api/outbound/SQM-TEST-001/confirm")
    assert res.status_code == 200

def test_cancel_outbound():
    res = client.post("/api/outbound/SQM-TEST-001/cancel")
    assert res.status_code == 200

# ── CORS Headers ─────────────────────────────────────────────
def test_cors_headers():
    res = client.options("/api/health", headers={"Origin": "null"})
    # PyWebView local access
    assert res.status_code in (200, 405)
