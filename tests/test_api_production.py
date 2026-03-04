"""
SQM v7.0.0-alpha — FastAPI REST API 테스트
=============================================
pytest + httpx TestClient 기반 엔드포인트 자동 테스트.
"""

import os
import sqlite3
import sys

import pytest

# S3-4: FastAPI/slowapi 미설치 환경에서 전체 skip
_fastapi_available = True
try:
    import fastapi
    import slowapi
except ImportError:
    _fastapi_available = False

pytestmark = pytest.mark.skipif(
    not _fastapi_available,
    reason="FastAPI/slowapi 미설치 — API 테스트 skip"
)

from datetime import date

# 프로젝트 루트 설정
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ═══════════════════════════════════════════
# Mock DB + Engine (API 의존성 대체)
# ═══════════════════════════════════════════

class MockDB:
    """In-memory SQLite mock."""

    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._insert_sample_data()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS inventory (
                lot_no TEXT PRIMARY KEY,
                sap_no TEXT DEFAULT '',
                bl_no TEXT DEFAULT '',
                product TEXT DEFAULT '',
                status TEXT DEFAULT 'AVAILABLE',
                net_weight REAL DEFAULT 0,
                current_weight REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS inventory_tonbag (
                lot_no TEXT,
                sub_lt INTEGER,
                weight REAL DEFAULT 500,
                status TEXT DEFAULT 'AVAILABLE',
                is_sample INTEGER DEFAULT 0,
                picked_to TEXT,
                PRIMARY KEY (lot_no, sub_lt)
            );
            CREATE TABLE IF NOT EXISTS return_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT,
                sub_lt INTEGER,
                return_date TEXT,
                original_customer TEXT DEFAULT '',
                original_sale_ref TEXT DEFAULT '',
                reason TEXT DEFAULT '',
                remark TEXT DEFAULT '',
                weight_kg REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS stock_movement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT,
                movement_type TEXT,
                qty_kg REAL DEFAULT 0,
                remarks TEXT DEFAULT '',
                source_type TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT '',
                method TEXT NOT NULL DEFAULT '',
                path TEXT NOT NULL DEFAULT '',
                username TEXT DEFAULT '',
                role TEXT DEFAULT '',
                status_code INTEGER DEFAULT 0,
                response_time_ms REAL DEFAULT 0,
                client_ip TEXT DEFAULT '',
                user_agent TEXT DEFAULT '',
                request_body TEXT DEFAULT '',
                error_detail TEXT DEFAULT ''
            );
        """)

    def _insert_sample_data(self):
        today = date.today().isoformat()
        # LOT 3개
        for i, (lot, prod, status) in enumerate([
            ('LOT-001', 'Lithium Carbonate', 'AVAILABLE'),
            ('LOT-002', 'Nickel Sulfate', 'PICKED'),
            ('LOT-003', 'Lithium Carbonate', 'SOLD'),
        ]):
            net_w = 5001.0
            self.conn.execute(
                "INSERT INTO inventory VALUES (?,?,?,?,?,?,?)",
                (lot, f'SAP{i+1}', f'BL{i+1}', prod, status, net_w, net_w))
            # 톤백 10개 + 샘플 1개
            for j in range(1, 11):
                self.conn.execute(
                    "INSERT INTO inventory_tonbag VALUES (?,?,?,?,?,?)",
                    (lot, j, 500.0, status, 0, None))
            self.conn.execute(
                "INSERT INTO inventory_tonbag VALUES (?,?,?,?,?,?)",
                (lot, 11, 1.0, status, 1, None))

        # 반품 이력 (LOT-003 → 4회)
        for k in range(4):
            self.conn.execute(
                "INSERT INTO return_history (lot_no, sub_lt, return_date, reason, "
                "original_customer, weight_kg) VALUES (?,?,?,?,?,?)",
                ('LOT-003', k+1, today, '품질 불량', 'CUST_JP', 500.0))

        # stock_movement (출고 이력)
        for lot in ['LOT-002', 'LOT-003']:
            self.conn.execute(
                "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, source_type) "
                "VALUES (?,?,?,?)", (lot, 'PICKED', 5000.0, 'PICKING'))

        self.conn.commit()

    def fetchone(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def commit(self):
        self.conn.commit()


class MockEngine:
    def __init__(self):
        self.db = MockDB()

    def get_return_statistics(self, start_date='', end_date='', lot_no=''):
        return {'by_reason': [], 'by_lot': [], 'by_month': [], 'by_customer': []}


# ═══════════════════════════════════════════
# Fixture: FastAPI TestClient
# ═══════════════════════════════════════════

@pytest.fixture(scope='module')
def client():
    """TestClient with mocked engine."""
    import api.main as api_module
    mock_engine = MockEngine()
    api_module._engine = mock_engine

    from fastapi.testclient import TestClient
    with TestClient(api_module.app) as c:
        yield c


@pytest.fixture(scope='module')
def auth_headers(client):
    """admin 토큰 헤더."""
    resp = client.post("/api/v1/auth/login",
        json={"username": "admin", "password": "admin"})
    token = resp.json()['access_token']
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════
# 테스트
# ═══════════════════════════════════════════

class TestHealthEndpoint:
    def test_health_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'ok'
        assert data['version'] == '7.0.0-alpha'
        assert data['db_connected'] is True

    def test_health_has_timestamp(self, client):
        data = client.get("/api/v1/health").json()
        assert 'timestamp' in data
        assert len(data['timestamp']) > 10


class TestDashboardEndpoint:
    def test_dashboard_returns_cards(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert 'cards' in data
        assert 'available' in data['cards']
        assert 'reserved' in data['cards']
        assert 'picked' in data['cards']
        assert 'sold' in data['cards']

    def test_dashboard_card_structure(self, client, auth_headers):
        data = client.get("/api/v1/dashboard", headers=auth_headers).json()
        avail = data['cards']['available']
        assert 'count' in avail
        assert 'weight_kg' in avail
        assert 'weight_mt' in avail
        assert avail['count'] >= 0

    def test_dashboard_totals(self, client, auth_headers):
        data = client.get("/api/v1/dashboard", headers=auth_headers).json()
        assert data['total_count'] > 0
        assert data['total_kg'] > 0
        assert data['total_mt'] == data['total_kg'] / 1000

    def test_dashboard_return_rate(self, client, auth_headers):
        data = client.get("/api/v1/dashboard", headers=auth_headers).json()
        if data.get('return_rate'):
            rr = data['return_rate']
            assert 'return_count' in rr
            assert 'return_rate' in rr


class TestAlertsEndpoint:
    def test_alerts_returns_list(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/alerts", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_alerts_lot003_has_warning(self, client, auth_headers):
        """LOT-003은 4회 반품 → 알림 발생."""
        data = client.get("/api/v1/dashboard/alerts", headers=auth_headers).json()
        lot003_alerts = [a for a in data if a.get('lot_no') == 'LOT-003']
        assert len(lot003_alerts) >= 1
        assert lot003_alerts[0]['severity'] == 'warning'


class TestInventoryEndpoint:
    def test_inventory_list(self, client, auth_headers):
        resp = client.get("/api/v1/inventory", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_inventory_filter_status(self, client, auth_headers):
        data = client.get("/api/v1/inventory?status=AVAILABLE", headers=auth_headers).json()
        assert all(d['status'] == 'AVAILABLE' for d in data)
        assert len(data) == 1

    def test_inventory_filter_product(self, client, auth_headers):
        data = client.get("/api/v1/inventory?product=Lithium", headers=auth_headers).json()
        assert all('Lithium' in d['product'] for d in data)
        assert len(data) == 2

    def test_inventory_has_tonbag_count(self, client, auth_headers):
        data = client.get("/api/v1/inventory", headers=auth_headers).json()
        for item in data:
            assert 'tonbag_count' in item
            assert item['tonbag_count'] == 10  # 샘플 제외


class TestLotDetailEndpoint:
    def test_lot_detail_found(self, client, auth_headers):
        resp = client.get("/api/v1/inventory/LOT-001", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['lot']['lot_no'] == 'LOT-001'

    def test_lot_detail_tonbags(self, client, auth_headers):
        data = client.get("/api/v1/inventory/LOT-001", headers=auth_headers).json()
        assert len(data['tonbags']) == 11  # 10 톤백 + 1 샘플
        samples = [t for t in data['tonbags'] if t['is_sample']]
        assert len(samples) == 1
        assert samples[0]['weight'] == 1.0

    def test_lot_detail_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/inventory/LOT-NONEXIST", headers=auth_headers)
        assert resp.status_code == 404

    def test_lot_detail_movements(self, client, auth_headers):
        data = client.get("/api/v1/inventory/LOT-002", headers=auth_headers).json()
        assert len(data['movements']) >= 1
        assert data['movements'][0]['movement_type'] == 'PICKED'


class TestReturnsEndpoint:
    def test_returns_stats(self, client, auth_headers):
        resp = client.get("/api/v1/returns/stats", headers=auth_headers)
        assert resp.status_code == 200

    def test_returns_history(self, client, auth_headers):
        resp = client.get("/api/v1/returns/history", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4  # LOT-003 4건

    def test_returns_history_filter_lot(self, client, auth_headers):
        data = client.get("/api/v1/returns/history?lot_no=LOT-003", headers=auth_headers).json()
        assert len(data) == 4
        assert all(d['lot_no'] == 'LOT-003' for d in data)

    def test_returns_history_empty_lot(self, client, auth_headers):
        data = client.get("/api/v1/returns/history?lot_no=LOT-001", headers=auth_headers).json()
        assert len(data) == 0


class TestSwaggerDocs:
    def test_docs_available(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc_available(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200

    def test_openapi_schema(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema['info']['title'] == 'SQM 재고관리 API'
        assert schema['info']['version'] == '7.0.0-alpha'


class TestAuthEndpoints:
    """JWT 인증 테스트."""

    def test_login_success(self, client):
        resp = client.post("/api/v1/auth/login",
            json={"username": "admin", "password": "admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert 'access_token' in data
        assert data['token_type'] == 'bearer'
        assert data['user']['role'] == 'admin'

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/api/v1/auth/login",
            json={"username": "nobody", "password": "test"})
        assert resp.status_code == 400

    def test_me_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_token(self, client):
        login = client.post("/api/v1/auth/login",
            json={"username": "admin", "password": "admin"}).json()
        token = login['access_token']
        resp = client.get("/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data['username'] == 'admin'
        assert data['role'] == 'admin'
        assert data['role_label'] == '관리자'

    def test_token_creation_and_verification(self, client):
        from api.auth import create_access_token, verify_token
        token = create_access_token("test", "viewer", "테스트")
        payload = verify_token(token)
        assert payload is not None
        assert payload['sub'] == 'test'
        assert payload['role'] == 'viewer'

    def test_invalid_token(self, client):
        resp = client.get("/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


class TestRoleBasedAccess:
    """역할 기반 접근 제어 테스트."""

    def test_dashboard_requires_auth(self, client):
        """인증 없이 대시보드 접근 → 401."""
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 401

    def test_dashboard_with_viewer(self, client):
        """viewer 역할로 대시보드 접근 → 200."""
        token = client.post("/api/v1/auth/login",
            json={"username": "viewer", "password": "viewer"}).json()['access_token']
        resp = client.get("/api/v1/dashboard",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_inventory_requires_auth(self, client):
        resp = client.get("/api/v1/inventory")
        assert resp.status_code == 401

    def test_health_no_auth_needed(self, client):
        """헬스 체크는 인증 불요."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200


class TestPostEndpoints:
    """입고/출고/반품 POST 엔드포인트 테스트."""

    def _get_operator_token(self, client):
        return client.post("/api/v1/auth/login",
            json={"username": "operator", "password": "operator"}).json()['access_token']

    def _get_viewer_token(self, client):
        return client.post("/api/v1/auth/login",
            json={"username": "viewer", "password": "viewer"}).json()['access_token']

    def test_inbound_requires_operator(self, client):
        """viewer는 입고 불가 → 403."""
        token = self._get_viewer_token(client)
        resp = client.post("/api/v1/inventory/inbound",
            headers={"Authorization": f"Bearer {token}"},
            json={"lot_no": "LOT-NEW", "product": "LC", "net_weight": 5001,
                  "tonbag_count": 10, "tonbag_weight": 500})
        assert resp.status_code == 403

    def test_inbound_weight_validation(self, client):
        """SQM 원칙: net_weight ≠ count×unit+1 → 400."""
        token = self._get_operator_token(client)
        resp = client.post("/api/v1/inventory/inbound",
            headers={"Authorization": f"Bearer {token}"},
            json={"lot_no": "LOT-BAD", "product": "LC", "net_weight": 9999,
                  "tonbag_count": 10, "tonbag_weight": 500})
        assert resp.status_code == 400
        assert "불일치" in resp.json()['detail']

    def test_outbound_requires_operator(self, client):
        """viewer는 출고 불가."""
        token = self._get_viewer_token(client)
        resp = client.post("/api/v1/inventory/outbound",
            headers={"Authorization": f"Bearer {token}"},
            json={"lot_no": "LOT-001", "customer": "CUST_A", "tonbag_count": 5})
        assert resp.status_code == 403

    def test_return_requires_operator(self, client):
        """viewer는 반품 불가."""
        token = self._get_viewer_token(client)
        resp = client.post("/api/v1/returns/process",
            headers={"Authorization": f"Bearer {token}"},
            json={"lot_no": "LOT-003", "sub_lt": 1, "reason": "품질불량"})
        assert resp.status_code == 403

    def test_inbound_no_auth(self, client):
        """인증 없이 입고 → 401."""
        resp = client.post("/api/v1/inventory/inbound",
            json={"lot_no": "LOT-X", "product": "LC", "net_weight": 5001,
                  "tonbag_count": 10, "tonbag_weight": 500})
        assert resp.status_code == 401


class TestWebSocket:
    """WebSocket 대시보드 테스트."""

    def test_ws_connection(self, client):
        """WebSocket 연결 및 최초 스냅샷 수신."""
        with client.websocket_connect("/ws/dashboard") as ws:
            data = ws.receive_json()
            assert data['type'] == 'dashboard'
            assert 'total_count' in data
            assert 'timestamp' in data

    def test_ws_refresh_command(self, client):
        """refresh 명령 시 즉시 스냅샷."""
        import json
        with client.websocket_connect("/ws/dashboard") as ws:
            _ = ws.receive_json()  # 최초
            ws.send_text(json.dumps({"command": "refresh"}))
            data = ws.receive_json()
            assert data['type'] == 'dashboard'


class TestAuditAndRateLimit:
    """감사 로깅 + Rate Limiting 테스트."""

    def test_audit_endpoint_requires_admin(self, client):
        """감사 로그는 admin만 조회 가능."""
        # viewer → 403
        token = client.post("/api/v1/auth/login",
            json={"username": "viewer", "password": "viewer"}).json()['access_token']
        resp = client.get("/api/v1/audit/logs",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_audit_endpoint_admin_access(self, client, auth_headers):
        """admin은 감사 로그 조회 가능."""
        resp = client.get("/api/v1/audit/logs", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_audit_middleware_module(self):
        """감사 미들웨어 모듈 임포트."""
        from api.audit_middleware import AuditLogMiddleware, get_audit_logs
        assert AuditLogMiddleware is not None
        assert callable(get_audit_logs)

    def test_rate_limit_module(self):
        """Rate limit 모듈 임포트."""
        from api.rate_limit import limiter, rate_limit_exceeded_handler
        assert limiter is not None
        assert callable(rate_limit_exceeded_handler)

    def test_docker_files_exist(self):
        """Docker 파일 존재 확인 (선택 — 없으면 skip)."""
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 필수 파일
        assert os.path.exists(os.path.join(base, 'requirements.txt')), \
            "requirements.txt 필수"
        # 선택 파일 (Docker 배포 환경에서만 필요)
        docker_files = ['Dockerfile', 'docker-compose.yml', '.dockerignore']
        missing = [f for f in docker_files
                   if not os.path.exists(os.path.join(base, f))]
        if missing:
            pytest.skip(f"Docker 파일 미존재 (개발 환경): {', '.join(missing)}")
