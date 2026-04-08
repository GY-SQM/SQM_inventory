# -*- coding: utf-8 -*-
"""
QueryCache v2 — TTL 지능화 (P2 개선 #4)
★ 기존: 모든 쿼리 TTL 60초 고정
★ 개선: 데이터 성격별 TTL 분리
생성일: 2026-04-08 | SQM v8.7.1

배치 위치: engine_modules/query_cache.py (기존 덮어쓰기)
"""
import hashlib
import logging
import time
from functools import wraps
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ================================================================
# TTL 프로파일 — 데이터 성격별 캐시 유효 시간
# ================================================================
TTL_PROFILES = {
    # 실시간성 최우선 (자주 변경)
    "realtime":   10,    # 대시보드 카운트, 현재 재고 수
    # 일반 조회 (적당한 실시간성)
    "inventory":  30,    # 재고 목록, LOT 상태
    "outbound":   30,    # 출고 현황, RESERVED/PICKED 목록
    # 표준 (기본값)
    "default":    60,    # 일반 쿼리
    # 변경 드문 데이터
    "report":     300,   # 출고 이력, stock_movement 집계
    "static":     600,   # 제품 목록, 창고 목록, 설정값
}


class QueryCacheV2:
    """
    TTL 프로파일 기반 지능형 쿼리 캐시
    - 데이터 성격에 따라 자동 TTL 적용
    - 캐시 히트율 추적
    - 특정 테이블 변경 시 관련 캐시 자동 무효화
    """

    def __init__(self):
        self._cache: dict[str, tuple[Any, float, int]] = {}
        # value: (data, timestamp, ttl)
        self.hits   = 0
        self.misses = 0
        self._invalidation_map: dict[str, set] = {}
        # table_name → {cache_keys that depend on this table}

    # ================================================================
    # 핵심 get / set
    # ================================================================

    def get(self, key: str) -> Optional[Any]:
        """캐시 조회 — 만료 시 None 반환"""
        if key not in self._cache:
            self.misses += 1
            return None

        data, ts, ttl = self._cache[key]
        if time.time() - ts > ttl:
            del self._cache[key]
            self.misses += 1
            return None

        self.hits += 1
        return data

    def set(self, key: str, data: Any, ttl: int = None, tables: list = None) -> None:
        """
        캐시 저장
        Args:
            key:    캐시 키
            data:   저장할 데이터
            ttl:    유효 시간 (초). None이면 'default' 프로파일 사용
            tables: 이 캐시가 의존하는 테이블 목록 (무효화용)
        """
        _ttl = ttl if ttl is not None else TTL_PROFILES["default"]
        self._cache[key] = (data, time.time(), _ttl)

        # 테이블 의존성 등록
        if tables:
            for table in tables:
                if table not in self._invalidation_map:
                    self._invalidation_map[table] = set()
                self._invalidation_map[table].add(key)

        # 캐시 크기 제한 (2000개 초과 시 오래된 것 정리)
        if len(self._cache) > 2000:
            self._evict_expired()

    def invalidate_table(self, table: str) -> int:
        """
        특정 테이블 변경 시 관련 캐시 전부 무효화
        Args: table — 변경된 테이블명
        Returns: 무효화된 캐시 수
        """
        keys = self._invalidation_map.get(table, set()).copy()
        count = 0
        for key in keys:
            if key in self._cache:
                del self._cache[key]
                count += 1
        if table in self._invalidation_map:
            del self._invalidation_map[table]
        if count > 0:
            logger.debug(f"캐시 무효화: {table} → {count}개 삭제")
        return count

    def invalidate_all(self) -> None:
        """전체 캐시 초기화"""
        count = len(self._cache)
        self._cache.clear()
        self._invalidation_map.clear()
        logger.info(f"전체 캐시 초기화: {count}개 삭제")

    # ================================================================
    # 편의 메서드 (TTL 프로파일 적용)
    # ================================================================

    def set_realtime(self, key: str, data: Any, tables: list = None) -> None:
        """대시보드 카운트 등 실시간 데이터 (10초)"""
        self.set(key, data, TTL_PROFILES["realtime"], tables)

    def set_inventory(self, key: str, data: Any) -> None:
        """재고 목록 등 (30초)"""
        self.set(key, data, TTL_PROFILES["inventory"],
                 tables=["inventory", "inventory_tonbag"])

    def set_outbound(self, key: str, data: Any) -> None:
        """출고 현황 (30초)"""
        self.set(key, data, TTL_PROFILES["outbound"],
                 tables=["allocation_plan", "picking_table", "sold_table"])

    def set_report(self, key: str, data: Any) -> None:
        """이력 리포트 등 (300초)"""
        self.set(key, data, TTL_PROFILES["report"])

    def set_static(self, key: str, data: Any) -> None:
        """제품 목록 등 거의 변경 없는 데이터 (600초)"""
        self.set(key, data, TTL_PROFILES["static"])

    # ================================================================
    # 진단
    # ================================================================

    def stats(self) -> dict:
        """캐시 히트율 및 현황"""
        total = self.hits + self.misses
        hit_rate = round(self.hits / total * 100, 1) if total > 0 else 0
        return {
            "cache_size":  len(self._cache),
            "hits":        self.hits,
            "misses":      self.misses,
            "hit_rate_pct": hit_rate,
            "tables_tracked": len(self._invalidation_map),
        }

    def _evict_expired(self) -> int:
        """만료된 캐시 정리"""
        now = time.time()
        expired = [
            k for k, (_, ts, ttl) in self._cache.items()
            if now - ts > ttl
        ]
        for k in expired:
            del self._cache[k]
        return len(expired)


# ================================================================
# 전역 캐시 인스턴스 (기존 호환)
# ================================================================
cache = QueryCacheV2()


def cached_query(ttl: int = None, profile: str = "default", tables: list = None):
    """
    TTL 프로파일 기반 캐시 데코레이터

    사용 예:
        @cached_query(profile="inventory")
        def get_inventory(self, status=None): ...

        @cached_query(ttl=30, tables=["inventory_tonbag"])
        def get_tonbags(self, lot_no): ...
    """
    _ttl = ttl if ttl is not None else TTL_PROFILES.get(profile, TTL_PROFILES["default"])

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            key_raw = f"{func.__qualname__}:{args[1:]}:{sorted(kwargs.items())}"
            key = hashlib.md5(key_raw.encode()).hexdigest()

            # 캐시 히트
            cached = cache.get(key)
            if cached is not None:
                return cached

            # 실제 실행
            result = func(*args, **kwargs)
            cache.set(key, result, ttl=_ttl, tables=tables)
            return result

        return wrapper
    return decorator
