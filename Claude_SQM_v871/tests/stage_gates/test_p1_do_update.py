# -*- coding: utf-8 -*-
"""P1 D/O Update API 라우트 등록 + 스키마 검증 테스트."""
import pytest
from fastapi.testclient import TestClient
from react_api.main import app

client = TestClient(app)


class TestDoUpdateRouteRegistration:
    def test_do_update_apply_registered(self):
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert '/api/do-update/apply' in paths


class TestDoUpdateSchemaValidation:
    def test_empty_body(self):
        resp = client.post("/api/do-update/apply", json={})
        assert resp.status_code == 422

    def test_missing_lot_no(self):
        resp = client.post("/api/do-update/apply", json={
            "do_no": "TEST-DO", "ship_date": "2026-04-01"
        })
        assert resp.status_code == 422

    def test_valid_request_nonexist_lot(self):
        resp = client.post("/api/do-update/apply", json={
            "lot_no": "NONEXIST999", "do_no": "DO-TEST"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
