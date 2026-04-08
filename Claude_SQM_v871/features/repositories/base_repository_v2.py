"""
BaseRepository — SQM 모든 Repository의 공통 기반 클래스
P2-C-02: 프로젝트 배치 후 InboundRepository / OutboundRepository 상속 적용
생성일: 2026-04-08 | SQM v8.7.1

★ SQM DB 인터페이스 (SQMDatabase):
  - self.db.execute(sql, params)
  - self.db.fetchone(sql, params)
  - self.db.fetchall(sql, params)
  - with self.db.transaction("IMMEDIATE"):  ← 표준 트랜잭션
  - self.db.commit() / self.db.rollback()

배치 위치: features/repositories/base_repository.py
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """
    SQM Repository 공통 기반
    - db 주입 표준화
    - 공통 조회 헬퍼
    - 공통 오류 처리
    """

    def __init__(self, db):
        """
        Args: db — SQMDatabase 인스턴스
              (engine 기반 Repository는 engine.db 를 전달)
        """
        self.db = db
        self._log = logging.getLogger(self.__class__.__name__)

    # ================================================================
    # 공통 조회 헬퍼
    # ================================================================

    def _fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """SELECT 1건 — 실패 시 None 반환"""
        try:
            return self.db.fetchone(sql, params)
        except Exception as e:
            self._log.error(f"fetchone 실패: {sql[:60]}... | {e}")
            return None

    def _fetch_all(self, sql: str, params: tuple = ()) -> list:
        """SELECT 다건 — 실패 시 빈 목록 반환"""
        try:
            return self.db.fetchall(sql, params) or []
        except Exception as e:
            self._log.error(f"fetchall 실패: {sql[:60]}... | {e}")
            return []

    def _execute(self, sql: str, params: tuple = ()) -> bool:
        """INSERT/UPDATE/DELETE — 실패 시 False 반환
        ★ 반드시 with self.db.transaction() 블록 안에서 호출"""
        try:
            self.db.execute(sql, params)
            return True
        except Exception as e:
            self._log.error(f"execute 실패: {sql[:60]}... | {e}")
            return False

    def table_exists(self, table_name: str) -> bool:
        """테이블 존재 여부"""
        row = self._fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return row is not None

    def row_count(self, table_name: str, where: str = '', params: tuple = ()) -> int:
        """테이블 행 수"""
        sql = f"SELECT COUNT(*) FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        row = self._fetch_one(sql, params)
        if row is None:
            return 0
        return int(row[0] if not hasattr(row, 'keys') else list(row)[0])

    def get_pragma_columns(self, table_name: str) -> set:
        """테이블 컬럼명 집합 반환 (PRAGMA table_info)"""
        rows = self._fetch_all(f"PRAGMA table_info({table_name})")
        return {
            str(r.get('name', '') if hasattr(r, 'keys') else r[1]).lower()
            for r in rows
        }
