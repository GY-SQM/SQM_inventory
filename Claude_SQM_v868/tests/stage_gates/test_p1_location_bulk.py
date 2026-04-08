# -*- coding: utf-8 -*-
"""P1 Location Bulk API 라우트 등록 + 스키마 검증 테스트."""
import pytest
from fastapi.testclient import TestClient
from react_api.main import app

client = TestClient(app)


class TestLocationBulkRouteRegistration:
    def test_single_update_registered(self):
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert '/api/location/single-update' in paths

    def test_bulk_upload_registered(self):
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert '/api/location/bulk-upload' in paths

    def test_bulk_update_registered(self):
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert '/api/location/bulk-update' in paths


class TestLocationBulkSchemaValidation:
    def test_single_update_empty(self):
        resp = client.post("/api/location/single-update", json={})
        assert resp.status_code == 422

    def test_single_update_nonexist(self):
        resp = client.post("/api/location/single-update", json={
            "lot_no": "NONEXIST999", "sub_lt": 1, "location": "A-01-01"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    def test_bulk_update_empty_items(self):
        resp = client.post("/api/location/bulk-update", json={"items": []})
        assert resp.status_code == 422
