# -*- coding: utf-8 -*-
"""Phase 2: 쓰기 API 엔드포인트 테스트.

Pre-Test + Post-Test 통합.
- 라우트 등록 확인
- 스키마 유효성 검증
- 서비스 함수 호출 가능 확인
"""
import sys
import os
import pytest

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient
from react_api.main import app

_ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
_WRITE_HEADERS = {"X-Admin-Token": _ADMIN_TOKEN} if _ADMIN_TOKEN else {}
client = TestClient(app, headers=_WRITE_HEADERS)


class TestRouteRegistration:
    """모든 쓰기 API가 등록되어 있는지 확인."""

    def _get_paths(self):
        return [r.path for r in app.routes]

    def test_inbound_create_registered(self):
        paths = self._get_paths()
        assert "/api/inbound/create" in paths

    def test_outbound_execute_registered(self):
        paths = self._get_paths()
        assert "/api/outbound/execute" in paths

    def test_outbound_cancel_registered(self):
        paths = self._get_paths()
        assert "/api/outbound/cancel" in paths

    def test_location_update_registered(self):
        paths = self._get_paths()
        assert "/api/location/update" in paths

    def test_files_upload_registered(self):
        paths = self._get_paths()
        assert "/api/files/upload" in paths


class TestHealthEndpoint:
    """기존 GET API가 여전히 작동하는지 확인."""

    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True


class TestSchemaValidation:
    """잘못된 요청은 422를 반환해야 한다."""

    def test_inbound_create_empty_body(self):
        resp = client.post("/api/inbound/create", json={})
        assert resp.status_code == 422

    def test_inbound_create_missing_lot(self):
        resp = client.post("/api/inbound/create", json={
            "product_name": "NSH",
            "bl_no": "BL123",
            "total_weight_kg": 1000,
            "bag_count": 1,
        })
        assert resp.status_code == 422

    def test_outbound_execute_empty_items(self):
        resp = client.post("/api/outbound/execute", json={
            "items": [],
            "customer": "TestCo",
        })
        assert resp.status_code == 422

    def test_outbound_cancel_empty_body(self):
        resp = client.put("/api/outbound/cancel", json={})
        assert resp.status_code == 422

    def test_location_update_empty_body(self):
        resp = client.put("/api/location/update", json={})
        assert resp.status_code == 422

    def test_files_upload_no_file(self):
        resp = client.post("/api/files/upload")
        assert resp.status_code == 422


class TestInboundCreateIntegration:
    """입고 API 실제 호출 (DB 연결 필요)."""

    def test_inbound_create_valid_request(self):
        resp = client.post("/api/inbound/create", json={
            "lot_no": "TEST000001",
            "product_name": "NSH",
            "bl_no": "TESTBL001",
            "total_weight_kg": 25000,
            "bag_count": 25,
            "sap_no": "SAP001",
            "location": "A-1",
            "source_type": "WEB_TEST",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "message" in data


class TestOutboundIntegration:
    """출고 API 실제 호출."""

    def test_outbound_execute_valid(self):
        resp = client.post("/api/outbound/execute", json={
            "items": [{"lot_no": "NONEXIST01", "sub_lt": 1}],
            "customer": "TestCustomer",
            "source": "WEB_TEST",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data

    def test_outbound_cancel_valid(self):
        resp = client.put("/api/outbound/cancel", json={
            "lot_no": "NONEXIST01",
            "sub_lt": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data


class TestLocationUpdate:
    """위치 변경 API."""

    def test_location_update_nonexist(self):
        resp = client.put("/api/location/update", json={
            "lot_no": "NONEXIST01",
            "sub_lt": 1,
            "new_location": "B-2",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False  # 존재하지 않는 톤백


class TestFileUpload:
    """파일 업로드 API."""

    def test_upload_invalid_extension(self):
        import io
        resp = client.post(
            "/api/files/upload",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "지원하지 않는" in data["message"]
