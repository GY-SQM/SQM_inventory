# -*- coding: utf-8 -*-
"""
Dashboard QueryCache 연결 패치 (개선 #4)
+ inventory_read_service 윈도우 함수 최적화 (개선 #5)
+ ADMIN_TOKEN 보안 경고 (개선 #6)
생성일: 2026-04-08 | SQM v8.7.1
"""

# ================================================================
# PATCH D: react_api/routes/dashboard.py
# DashboardReadService에 QueryCache 연결
# ================================================================

DASHBOARD_PATCHED = '''# -*- coding: utf-8 -*-
"""Dashboard 조회 라우트 — QueryCache 적용 버전."""
import logging
from fastapi import APIRouter, HTTPException
from react_api.schemas.dashboard import (
    DashboardSummaryResponse, ProductSummaryResponse, LocationSummaryResponse,
)
from react_api.dashboard_read_service import DashboardReadService
from react_api.utils.db import get_db

# ★ QueryCache 연결
try:
    from engine_modules.query_cache import cache
    _cache_enabled = True
except ImportError:
    _cache_enabled = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary():
    # ★ 캐시 확인 (10초 TTL)
    if _cache_enabled:
        cached = cache.get("dashboard:summary")
        if cached:
            return DashboardSummaryResponse(**cached)
    try:
        with get_db() as db:
            service = DashboardReadService(db)
            data = service.get_summary()
        # ★ 캐시 저장
        if _cache_enabled:
            cache.set_realtime("dashboard:summary", data, tables=["inventory_tonbag"])
        return DashboardSummaryResponse(**data)
    except Exception as exc:
        logger.error("dashboard_summary 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="대시보드 요약 조회 실패")


@router.get("/by-product", response_model=ProductSummaryResponse)
def dashboard_by_product():
    if _cache_enabled:
        cached = cache.get("dashboard:by_product")
        if cached:
            return ProductSummaryResponse(**cached)
    try:
        with get_db() as db:
            service = DashboardReadService(db)
            data = service.get_by_product()
        if _cache_enabled:
            cache.set_realtime("dashboard:by_product", data, tables=["inventory"])
        return ProductSummaryResponse(**data)
    except Exception as exc:
        logger.error("dashboard_by_product 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="제품별 요약 조회 실패")


@router.get("/location-summary", response_model=LocationSummaryResponse)
def dashboard_location_summary():
    if _cache_enabled:
        cached = cache.get("dashboard:location")
        if cached:
            return LocationSummaryResponse(**cached)
    try:
        with get_db() as db:
            service = DashboardReadService(db)
            data = service.get_location_summary()
        if _cache_enabled:
            cache.set_realtime("dashboard:location", data, tables=["inventory_tonbag"])
        return LocationSummaryResponse(**data)
    except Exception as exc:
        logger.error("dashboard_location_summary 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="위치별 요약 조회 실패")
'''

# ================================================================
# PATCH E: inventory_read_service.py
# COUNT(*) 2번 → 윈도우 함수 1번으로 최적화
# search_inventory() 함수의 SQL 핵심 부분만 교체
# ================================================================

INVENTORY_PATCH_SQL = '''
-- 기존 (2번 DB hit):
-- 1) SELECT COUNT(*) AS total FROM ... WHERE ...
-- 2) SELECT ... FROM ... WHERE ... LIMIT ? OFFSET ?

-- 개선 (1번 DB hit):
SELECT t.id AS tonbag_id, t.lot_no, ...,
       COUNT(*) OVER() AS _total_count   -- ★ 윈도우 함수
FROM inventory_tonbag t
LEFT JOIN inventory i ON i.lot_no = t.lot_no
WHERE {where_sql}
ORDER BY t.lot_no, t.sub_lt, t.id
LIMIT ? OFFSET ?

-- 적용 방법: search_inventory()에서
-- total = rows[0]["_total_count"] if rows else 0
-- (별도 COUNT 쿼리 제거)
'''

# ================================================================
# PATCH F: deploy.bat 에 ADMIN_TOKEN 보안 경고 추가
# ================================================================

ADMIN_TOKEN_CHECK = '''
:: ── ADMIN_TOKEN 보안 점검 ─────────────────────────────────────
echo.
echo [보안 점검] ADMIN_TOKEN 확인 중...
python -c "
import os
token = ''
env_file = r'%PROJECT%\\.env'
try:
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('ADMIN_TOKEN='):
                token = line.strip().split('=',1)[1]
                break
except Exception:
    pass

weak = ['sqm_admin_2026','admin','password','sqm','1234','test']
if token.lower() in weak or len(token) < 12:
    print('  [WARNING] ADMIN_TOKEN이 취약합니다!')
    print(f'  현재값: {token[:4]}****')
    print('  .env 파일에서 ADMIN_TOKEN을 16자 이상 복잡한 값으로 변경하세요.')
    print('  예: ADMIN_TOKEN=SQM@Gwangyang#2026!Secure')
else:
    print(f'  [OK] ADMIN_TOKEN 설정됨 ({len(token)}자)')
" 2>nul || echo   [SKIP] Python 미실행
'''

if __name__ == "__main__":
    print("=== 패치 내용 확인 ===")
    print("[D] Dashboard QueryCache 연결")
    print("[E] inventory_read_service 윈도우 함수 최적화")
    print("[F] ADMIN_TOKEN 보안 경고")
