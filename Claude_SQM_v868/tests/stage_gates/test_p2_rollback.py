# -*- coding: utf-8 -*-
"""P2 Rollback 보호 패턴 검증 테스트."""
import ast
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read_source(rel_path):
    with open(os.path.join(PROJECT_ROOT, rel_path), encoding='utf-8') as f:
        return f.read()


class TestWriteServiceRollbackPattern:
    """모든 Write 서비스에 try/except + 에러 응답 패턴이 있는지 검증."""

    WRITE_SERVICES = [
        'react_api/services/inbound_write_service.py',
        'react_api/services/outbound_write_service.py',
        'react_api/services/return_write_service.py',
        'react_api/services/do_update_service.py',
        'react_api/services/location_bulk_service.py',
    ]

    def test_all_write_services_have_error_handling(self):
        for path in self.WRITE_SERVICES:
            src = _read_source(path)
            assert 'except Exception' in src or 'except Exception as' in src, \
                f"{path}: except Exception 누락"

    def test_all_write_services_have_logging(self):
        for path in self.WRITE_SERVICES:
            src = _read_source(path)
            assert 'logger.exception' in src or 'logger.error' in src, \
                f"{path}: logger 에러 기록 누락"

    def test_all_write_services_return_success_false_on_error(self):
        for path in self.WRITE_SERVICES:
            src = _read_source(path)
            assert '"success": False' in src or "'success': False" in src, \
                f"{path}: success: False 응답 누락"


class TestWriteRouteEnginePattern:
    """모든 Write 라우트에서 get_engine() 컨텍스트 매니저를 사용하는지 검증."""

    WRITE_ROUTES = [
        'react_api/routes/inbound.py',
        'react_api/routes/outbound_write.py',
        'react_api/routes/location.py',
        'react_api/routes/return_write.py',
    ]

    def test_all_write_routes_use_get_engine(self):
        for path in self.WRITE_ROUTES:
            src = _read_source(path)
            assert 'get_engine' in src, f"{path}: get_engine 사용 누락"

    def test_all_write_routes_use_write_response(self):
        for path in self.WRITE_ROUTES:
            src = _read_source(path)
            assert 'WriteResponse' in src, f"{path}: WriteResponse 사용 누락"


class TestDoUpdateRollbackInService:
    """do_update_service에 rollback이 명시적으로 있는지 검증."""

    def test_has_rollback(self):
        src = _read_source('react_api/services/do_update_service.py')
        assert 'rollback' in src

    def test_has_commit(self):
        src = _read_source('react_api/services/do_update_service.py')
        assert 'commit' in src


class TestLocationBulkRollbackInService:
    """location_bulk_service에 rollback이 명시적으로 있는지 검증."""

    def test_has_rollback(self):
        src = _read_source('react_api/services/location_bulk_service.py')
        assert 'rollback' in src

    def test_has_commit(self):
        src = _read_source('react_api/services/location_bulk_service.py')
        assert 'commit' in src
