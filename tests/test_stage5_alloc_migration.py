# -*- coding: utf-8 -*-
"""5단계 — B-7 alloc_router 이관 검증 테스트"""
import os, sys, pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestB7AllocRouterMigration:
    def test_6_endpoints_in_allocation_api(self):
        src = open(os.path.join(ROOT, 'backend/api/allocation_api.py'), encoding='utf-8').read()
        for ep in ['get_allocation', 'cancel_allocation_by_lot',
                   'update_allocation_by_lot', 'pick_allocation_by_lot',
                   'confirm_allocation_by_lot', 'reset_allocation_by_lot']:
            assert ep in src, f"allocation_api.py에 {ep} 없음"

    def test_alloc_router_deprecated_in_inventory_api(self):
        src = open(os.path.join(ROOT, 'backend/api/inventory_api.py'), encoding='utf-8').read()
        active = [l for l in src.splitlines()
                  if 'alloc_router = APIRouter' in l and not l.strip().startswith('#')]
        assert len(active) == 0, "inventory_api.py에 alloc_router 활성 선언 남아있음"

    def test_init_not_importing_alloc_router(self):
        src = open(os.path.join(ROOT, 'backend/api/__init__.py'), encoding='utf-8').read()
        # alloc_router 가 실제 import 목록에 없는지 확인 (주석 제외)
        active = [l for l in src.splitlines()
                  if 'alloc_router' in l
                  and 'import' in l
                  and not l.strip().startswith('#')
                  and 'alloc_router' in l.split('#')[0]]  # 주석 앞 코드 부분에만 있어야
        assert len(active) == 0, f"__init__.py alloc_router import 남아있음: {active}"

    def test_app_loads_without_error(self):
        """FastAPI 앱이 에러 없이 로드되는지"""
        import importlib
        try:
            from backend.api import app
            assert app is not None
        except Exception as e:
            pytest.fail(f"앱 로드 실패: {e}")

    def test_endpoints_use_ok_response(self):
        """이관된 엔드포인트가 ok 형식 사용하는지"""
        src = open(os.path.join(ROOT, 'backend/api/allocation_api.py'), encoding='utf-8').read()
        # 이관 섹션에서 success: True 패턴 없어야 함
        migrated_start = src.index('[B-7 이관]')
        migrated_body = src[migrated_start:]
        assert '"success": True' not in migrated_body, \
            "이관된 엔드포인트에 {success:True} 패턴 남아있음"
