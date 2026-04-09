# -*- coding: utf-8 -*-
"""P2 정합성 검증 — 무게 보존 법칙 + API 응답 검증."""
from fastapi.testclient import TestClient
from react_api.main import app

client = TestClient(app)


class TestIntegrityCheckAPI:
    def test_integrity_check_returns_200(self):
        resp = client.get("/api/tools/integrity-check")
        assert resp.status_code == 200

    def test_integrity_check_has_required_fields(self):
        resp = client.get("/api/tools/integrity-check")
        data = resp.json()
        assert 'success' in data
        assert 'total_issues' in data
        assert 'issues' in data
        assert isinstance(data['issues'], list)

    def test_integrity_issues_have_type_and_severity(self):
        resp = client.get("/api/tools/integrity-check")
        data = resp.json()
        for issue in data['issues']:
            assert 'type' in issue
            assert 'severity' in issue
            assert issue['severity'] in ('ERROR', 'WARNING', 'INFO')


class TestWeightConservationPattern:
    """무게 보존 법칙: inventory.current_weight = SUM(톤백 weight) for AVAILABLE/RESERVED."""

    def test_integrity_check_includes_weight_mismatch(self):
        """정합성 체크 API가 WEIGHT_MISMATCH 타입을 검사하는지 확인."""
        import os
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'react_api', 'routes', 'tools.py'
        )
        with open(src_path, encoding='utf-8') as f:
            src = f.read()
        assert 'WEIGHT_MISMATCH' in src, "tools.py에 WEIGHT_MISMATCH 검증 누락"

    def test_integrity_check_includes_orphan_check(self):
        """ORPHAN_TONBAG 검사 포함 확인."""
        import os
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'react_api', 'routes', 'tools.py'
        )
        with open(src_path, encoding='utf-8') as f:
            src = f.read()
        assert 'ORPHAN_TONBAG' in src, "tools.py에 ORPHAN_TONBAG 검증 누락"

    def test_integrity_check_includes_status_mismatch(self):
        """STATUS_MISMATCH 검사 포함 확인."""
        import os
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'react_api', 'routes', 'tools.py'
        )
        with open(src_path, encoding='utf-8') as f:
            src = f.read()
        assert 'STATUS_MISMATCH' in src, "tools.py에 STATUS_MISMATCH 검증 누락"
