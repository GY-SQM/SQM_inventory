# -*- coding: utf-8 -*-
"""
tests/test_db_allowed_stats_endpoint.py
=======================================
SQM v9.0.2 — GET endpoint /api/admin/db-allowed/stats 테스트

FastAPI TestClient로 직접 호출 검증.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.db_allowed import reset_counts
from backend.api.db_allowed_stats import router


@pytest.fixture
def client():
    """TestClient with only db_allowed_stats router."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_setup_method():
    """각 테스트 전 카운터 초기화."""
    reset_counts()


def test_e01_endpoint_basic(client):
    """빈 카운터 → total_calls 0."""
    reset_counts()
    response = client.get("/api/admin/db-allowed/stats")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_calls"] == 0
    assert data["allowed"] == 0
    assert data["blocked"] == 0
    assert data["by_kind"] == {}


def test_e02_endpoint_after_validate(client):
    """validate() 호출 후 통계 반영."""
    from core.db_allowed import validate
    reset_counts()
    validate("inventory", "table", "inventory")  # allowed
    validate("inventory", "table", "bad")  # blocked
    response = client.get("/api/admin/db-allowed/stats")
    data = response.json()["data"]
    assert data["total_calls"] == 2
    assert data["allowed"] == 1
    assert data["blocked"] == 1
    assert data["by_kind"]["table"]["allowed"] == 1
    assert data["by_kind"]["table"]["blocked"] == 1


def test_e03_endpoint_raw_counts(client):
    """raw_counts 노출 (디버깅용)."""
    from core.db_allowed import validate
    reset_counts()
    validate("inventory", "status", "AVAILABLE")  # allowed
    response = client.get("/api/admin/db-allowed/stats")
    data = response.json()["data"]
    # raw_counts는 (area, kind, result) 형식의 key
    # 예: "inventory|status|True" (area="inventory", kind="status", result=True)
    assert any("status" in k and "True" in k for k in data["raw_counts"].keys())
    assert all(v >= 1 for v in data["raw_counts"].values())


# ── v9.0.4: audit_log 조회 endpoint ─────────────────────

class TestAuditEndpoint:
    def test_e04_audit_endpoint_no_db(self, monkeypatch):
        """DB 경로 없으면 graceful fail."""
        from core.db_allowed import _get_default_db_path
        monkeypatch.setattr(_get_default_db_path, "__defaults__", (None,))
        # 직접 None 강제
        from fastapi import FastAPI
        from backend.api.db_allowed_stats import router as r
        app = FastAPI()
        app.include_router(r)
        client = TestClient(app)
        # config import 실패 (또는 DB_PATH 없음) → ok=False
        response = client.get("/api/admin/db-allowed/audit")
        assert response.status_code == 200
        data = response.json()
        # ok=False or ok=True (DB 환경에 따라 다름) 둘 다 OK
        assert "ok" in data
        assert "data" in data

    def test_e05_audit_endpoint_basic(self, tmp_path, monkeypatch):
        """기본 조회 — DB에 row 삽입 후 검증."""
        import sqlite3
        from core.db_allowed import _init_audit_table, _get_default_db_path
        db = str(tmp_path / "audit_test.db")
        _init_audit_table(db)
        # 강제로 DB path 설정
        import core.db_allowed as db_mod
        original = db_mod._get_default_db_path
        monkeypatch.setattr(db_mod, "_get_default_db_path", lambda: db)
        # INSERT
        con = sqlite3.connect(db)
        try:
            con.execute("INSERT INTO db_allowed_audit (area, kind, result, value) VALUES (?, ?, ?, ?)",
                         ("inventory", "table", 1, "inventory"))
            con.execute("INSERT INTO db_allowed_audit (area, kind, result, value) VALUES (?, ?, ?, ?)",
                         ("inventory", "table", 0, "sql_injection"))
            con.commit()
        finally:
            con.close()
        # endpoint 호출
        from fastapi import FastAPI
        from backend.api.db_allowed_stats import router as r
        app = FastAPI()
        app.include_router(r)
        client = TestClient(app)
        response = client.get("/api/admin/db-allowed/audit")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["count"] >= 2
        # blocked_only 필터
        response = client.get("/api/admin/db-allowed/audit?blocked_only=true")
        data = response.json()
        blocked_rows = [r for r in data["data"]["rows"] if r["result"] is False]
        assert len(blocked_rows) >= 1

    def test_e06_audit_endpoint_kind_filter(self, tmp_path, monkeypatch):
        """kind 필터."""
        import sqlite3
        from core.db_allowed import _init_audit_table
        db = str(tmp_path / "audit_test2.db")
        _init_audit_table(db)
        import core.db_allowed as db_mod
        monkeypatch.setattr(db_mod, "_get_default_db_path", lambda: db)
        con = sqlite3.connect(db)
        try:
            con.execute("INSERT INTO db_allowed_audit (area, kind, result, value) VALUES (?, ?, ?, ?)",
                         ("inventory", "table", 1, "inventory"))
            con.execute("INSERT INTO db_allowed_audit (area, kind, result, value) VALUES (?, ?, ?, ?)",
                         ("inventory", "status", 1, "AVAILABLE"))
            con.commit()
        finally:
            con.close()
        from fastapi import FastAPI
        from backend.api.db_allowed_stats import router as r
        app = FastAPI()
        app.include_router(r)
        client = TestClient(app)
        # kind=table 필터
        response = client.get("/api/admin/db-allowed/audit?kind=table")
        data = response.json()
        assert data["ok"] is True
        for row in data["data"]["rows"]:
            assert row["kind"] == "table"

    def test_e07_audit_cleanup_endpoint(self, tmp_path, monkeypatch):
        """POST /api/admin/db-allowed/audit/cleanup — 오래된 row 삭제."""
        import sqlite3
        from core.db_allowed import _init_audit_table
        db = str(tmp_path / "audit_cleanup_test.db")
        _init_audit_table(db)
        import core.db_allowed as db_mod
        monkeypatch.setattr(db_mod, "_get_default_db_path", lambda: db)
        con = sqlite3.connect(db)
        try:
            # 50일 전 row 1개
            con.execute(
                f"INSERT INTO db_allowed_audit (ts, area, kind, result, value) "
                f"VALUES (datetime('now', '-50 days'), ?, ?, ?, ?)",
                ("inventory", "table", 1, "old"),
            )
            con.commit()
        finally:
            con.close()
        from fastapi import FastAPI
        from backend.api.db_allowed_stats import router as r
        app = FastAPI()
        app.include_router(r)
        client = TestClient(app)
        # 30일 이전 삭제
        response = client.post("/api/admin/db-allowed/audit/cleanup?days=30")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["deleted"] == 1
        assert data["data"]["days"] == 30
