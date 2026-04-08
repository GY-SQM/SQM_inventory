# -*- coding: utf-8 -*-
"""P1 Return API 라우트 등록 + 스키마 검증 테스트."""
import pytest
from fastapi.testclient import TestClient
from react_api.main import app

client = TestClient(app)


class TestReturnRouteRegistration:
    def test_return_list_registered(self):
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert '/api/return/list' in paths

    def test_return_statistics_registered(self):
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert '/api/return/statistics' in paths

    def test_return_single_registered(self):
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert '/api/return/single' in paths

    def test_return_bulk_excel_registered(self):
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert '/api/return/bulk-excel' in paths

    def test_return_bulk_confirm_registered(self):
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert '/api/return/bulk-confirm' in paths


class TestReturnSchemaValidation:
    def test_return_single_empty_body(self):
        resp = client.post("/api/return/single", json={})
        assert resp.status_code == 422

    def test_return_single_invalid_reason(self):
        resp = client.post("/api/return/single", json={
            "lot_no": "TEST001", "sub_lt": 1, "reason_code": "INVALID"
        })
        assert resp.status_code == 422

    def test_return_single_valid_reason_codes(self):
        for reason in ["품질불량", "수량오류", "고객요청", "파손", "기타"]:
            resp = client.post("/api/return/single", json={
                "lot_no": "NONEXIST999", "sub_lt": 1, "reason_code": reason
            })
            # Should not be 422 (validation passes, engine may fail)
            assert resp.status_code != 422

    def test_return_bulk_confirm_empty_items(self):
        resp = client.post("/api/return/bulk-confirm", json={"items": []})
        assert resp.status_code == 422
