# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - SQLite 데이터베이스 모듈
==============================================

v3.6.0: Docstring 보강

모듈 개요:
    SQLite 데이터베이스 연결, 쿼리 실행, 트랜잭션 관리를 담당합니다.
    스레드 안전성, WAL 모드, 네트워크 모드를 자동으로 처리합니다.

주요 클래스:
    - SQMDatabase: SQLite 데이터베이스 관리 클래스

사용 예시:
    >>> from engine_modules.database import SQMDatabase
    >>> db = SQMDatabase('data/inventory.db')
    >>> 
    >>> # 단일 조회
    >>> row = db.fetchone("SELECT * FROM inventory WHERE lot_no = ?", ('1234567890',))
    >>> 
    >>> # 전체 조회
    >>> rows = db.fetchall("SELECT * FROM inventory WHERE status = ?", ('AVAILABLE',))
    >>> 
    >>> # 트랜잭션
    >>> with db.transaction():
    ...     db.execute("INSERT INTO inventory ...")
    ...     db.execute("UPDATE inventory SET ...")
    >>> 
    >>> # 백업
    >>> backup_path = db.create_backup(reason='before_import')

의존성:
    - sqlite3 (내장)
    - threading (내장)

작성자: Ruby
버전: v3.6.0
"""

import sqlite3
import os
import re
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any, TYPE_CHECKING
from contextlib import contextmanager

# 타입 힌팅용 (런타임에는 import 안 함)
if TYPE_CHECKING:
    pass  # 필요시 추가

# 로깅 설정
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# DB 재시도 상수 (v5.1.2)
# ═══════════════════════════════════════════════════════════
DB_MAX_RETRIES = 3          # 최대 재시도 횟수
DB_RETRY_DELAY = 0.5        # 초기 대기 (초)
DB_RETRY_BACKOFF = 2        # 지수 백오프 배율


try:
    from engine_modules.database_interface import DatabaseInterface
except ImportError:
    DatabaseInterface = object  # fallback

from .db_migration_mixin import DatabaseMigrationMixin
# v5.5.3 P9: DatabaseValidationMixin 제거 (전 메서드 database.py에서 재정의 — 죽은 코드)


class SQMDatabase(DatabaseMigrationMixin, DatabaseInterface):
    """
    SQLite 데이터베이스 관리 (v3.9.6: Mixin 분할)

    v5.5.3: db_validation_mixin 제거 (검증/백업은 본 클래스에서 직접 구현)
    v3.9.6: 마이그레이션 → db_migration_mixin.py
    v2.5.4 개선 (검토안 반영):
    1. 스레드 안전성 - check_same_thread=False + 쓰기 락
    2. DB 경로 단일화 - config.DB_PATH 사용
    3. Foreign Key 활성화 - PRAGMA foreign_keys=ON
    4. 네트워크 모드 자동 감지 - UNC 경로 시 WAL OFF

    이전 개선:
    - 트랜잭션 컨텍스트 매니저, Online Backup API
    - 자동 백업, WAL 모드, 입력 검증, 로그 로테이션
    """

    # LOT 번호 유효성 검사 패턴 (10자리 숫자)
    # v2.9.0: 112로 시작한다고 단정하지 않음
    # LOT 검증은 engine_modules.validators.validate_lot_no 단일 소스 사용

    # 백업 설정
    MAX_BACKUPS = 5  # 최대 백업 파일 수

    def __init__(self, db_path: str = None, use_wal: bool = None, network_mode: bool = None) -> None:
        """
        Args:
            db_path: DB 파일 경로 (None이면 config.DB_PATH 사용)
            use_wal: WAL 모드 사용 여부 (None이면 자동 감지)
            network_mode: 네트워크 공유 모드 (None이면 자동 감지)
        """
        # A2: DB 경로 단일화 - config에서 가져오기
        if db_path is None:
            try:
                from core.config import DB_PATH
                db_path = str(DB_PATH)
            except ImportError:
                db_path = os.path.join(os.path.dirname(__file__), 'data', 'sqm_inventory.db')

        self.db_path = db_path
        self.backup_dir = os.path.join(os.path.dirname(db_path) if db_path != ':memory:' else '.', 'backups')

        # 네트워크 모드 자동 감지 (UNC 경로 또는 명시적 설정)
        if network_mode is None:
            self.network_mode = self._detect_network_path(db_path) if db_path != ':memory:' else False
        else:
            self.network_mode = network_mode

        # WAL 모드: 네트워크면 자동으로 OFF
        if use_wal is None:
            self.use_wal = not self.network_mode
        else:
            self.use_wal = use_wal

        # :memory: DB가 아닌 경우에만 디렉토리 생성
        if db_path != ':memory:':
            db_dir = os.path.dirname(db_path)
            if db_dir:  # 빈 문자열이 아닌 경우에만
                os.makedirs(db_dir, exist_ok=True)
            os.makedirs(self.backup_dir, exist_ok=True)

        # A1: 스레드 안전성 - 쓰기 락
        self._write_lock = threading.RLock()
        self._local = threading.local()  # 스레드별 연결 저장

        self._connection = None
        self._cursor = None
        self._last_backup_time = None
        self._in_transaction = False

        self._init_database()
        self._set_busy_timeout()
        self._create_indexes()
        
        # ★★★ v2.9.25: DB 스키마 자동 점검/마이그레이션 ★★★
        self._verify_schema()

        if self.network_mode:
            logger.info(f"네트워크 모드 감지: WAL OFF, synchronous=FULL")

    @staticmethod
    def _detect_network_path(path: str) -> bool:
        """
        네트워크 경로 자동 감지

        - UNC 경로 (\\\\server\\share) → True
        - 일반 경로 → False
        """
        # Windows UNC 경로
        if path.startswith('\\\\') or path.startswith('//'):
            return True
        # 추가 휴리스틱: 환경변수 설정
        if os.environ.get('SQM_NETWORK_MODE', '').lower() in ('1', 'true', 'yes'):
            return True
        return False

    @property
    def conn(self) -> sqlite3.Connection:
        """
        스레드 안전한 DB 연결 반환

        v2.5.4: check_same_thread=False + 스레드별 연결
        """
        # 스레드별 연결 사용 (thread-local)
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                isolation_level=None,  # 수동 트랜잭션 관리
                check_same_thread=False  # A1: 스레드 안전성 핵심
            )
            self._local.conn.row_factory = sqlite3.Row

            # A3: Foreign Key 활성화
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn.execute("PRAGMA busy_timeout=30000")

            # 네트워크 모드에 따른 저널 모드 설정
            if self.network_mode:
                self._local.conn.execute("PRAGMA journal_mode=DELETE")
                self._local.conn.execute("PRAGMA synchronous=FULL")
            elif self.use_wal:
                self._local.conn.execute("PRAGMA journal_mode=WAL")
                self._local.conn.execute("PRAGMA synchronous=NORMAL")

        return self._local.conn

    @property
    def cursor(self) -> sqlite3.Cursor:
        """재사용 가능한 커서"""
        if self._cursor is None:
            self._cursor = self.conn.cursor()
        return self._cursor

    # =========================================================================
    # v2.5.4: 트랜잭션 컨텍스트 매니저 (쓰기 락 포함)
    # =========================================================================

    @contextmanager
    def transaction(self, mode: str = "IMMEDIATE") -> Any:
        """
        트랜잭션 컨텍스트 매니저 - 원자적 작업 보장 (Phase 3: HardStop 통합)

        v2.5.4: 쓰기 락 추가로 스레드 안전성 확보
        v4.2.3: HardStopException은 절대 삼키지 않고 롤백 후 재발생

        사용 예:
            with db.transaction():
                db.execute("INSERT ...")
                db.execute("UPDATE ...")
                # 예외 발생 시 자동 롤백

        Args:
            mode: DEFERRED(기본), IMMEDIATE(쓰기 락 선점), EXCLUSIVE(배타적)
        """
        # 쓰기 락 획득 (스레드 안전성) - v2.5.4 수정
        self._write_lock.acquire()

        # ✅ v2.5.4 수정: 중첩 트랜잭션 시 락을 유지한 채로 yield
        if self._in_transaction:
            try:
                yield
            finally:
                self._write_lock.release()  # RLock 카운터 감소
            return

        self._in_transaction = True
        try:
            self.conn.execute(f"BEGIN {mode}")
            yield
            self.conn.commit()
            logger.debug(f"트랜잭션 커밋 완료 (mode={mode})")
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError, OSError) as e:
            # Phase 3: 모든 예외에서 롤백
            self.conn.rollback()
            logger.error(f"트랜잭션 롤백: {type(e).__name__}: {e}")
            
            # HardStopException은 절대 삼키지 않음
            try:
                from .exceptions import HardStopException
                if isinstance(e, HardStopException):
                    logger.warning(f"HardStopException 감지 - 즉시 재발생")
            except ImportError as _e:
                logger.debug(f"Suppressed: {_e}")
            
            raise  # 모든 예외 재발생
        finally:
            self._in_transaction = False
            self._write_lock.release()

    # =========================================================================
    # v2.5.4: Online Backup API (검토안 B단계)
    # =========================================================================

    def create_backup(self, reason: str = "manual") -> Optional[str]:
        """
        데이터베이스 백업 생성 (Online Backup API 사용)

        sqlite3.Connection.backup()을 사용하여 동시 접근 중에도
        일관된 백업을 생성합니다.

        Args:
            reason: 백업 사유 (manual, before_import, before_delete 등)

        Returns:
            백업 파일 경로 또는 None (실패 시)
        """
        try:
            if not os.path.exists(self.db_path):
                return None

            # 백업 파일명 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"sqm_inventory_{timestamp}_{reason}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)

            # Online Backup API 사용 (일관성 보장)
            with sqlite3.connect(backup_path) as backup_conn:
                self.conn.backup(backup_conn)

            self._last_backup_time = datetime.now()
            logger.info(f"DB 백업 생성 (Online API): {backup_name}")

            # 오래된 백업 정리
            self._cleanup_old_backups()

            return backup_path

        except (sqlite3.Error, OSError) as e:
            logger.error(f"백업 실패: {e}")
            return None

    def _cleanup_old_backups(self) -> None:
        """오래된 백업 파일 정리 (v5.2.0: 공용 함수 위임)"""
        try:
            from utils.backup import cleanup_old_backups_in_dir
            cleanup_old_backups_in_dir(self.backup_dir, self.MAX_BACKUPS, '.db')
        except ImportError:
            # fallback: utils.backup 없을 때
            try:
                backups = sorted([
                    f for f in os.listdir(self.backup_dir) if f.endswith('.db')
                ])
                while len(backups) > self.MAX_BACKUPS:
                    old = backups.pop(0)
                    os.remove(os.path.join(self.backup_dir, old))
                    logger.info(f"오래된 백업 삭제: {old}")
            except (sqlite3.Error, OSError) as e:
                logger.warning(f"백업 정리 실패: {e}")

    def restore_from_backup(self, backup_path: str) -> bool:
        """
        백업에서 복원

        Args:
            backup_path: 백업 파일 경로

        Returns:
            성공 여부
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"백업 파일 없음: {backup_path}")
                return False

            # 현재 연결 종료
            self.close()

            # 복원 전 현재 DB 백업
            self.create_backup("before_restore")

            # 복원 수행
            import shutil
            shutil.copy2(backup_path, self.db_path)

            logger.info(f"DB 복원 완료: {backup_path}")
            return True

        except (sqlite3.Error, OSError) as e:
            logger.error(f"복원 실패: {e}")
            return False

    def get_backup_list(self) -> List[Dict]:
        """백업 목록 조회"""
        backups = []
        try:
            for f in os.listdir(self.backup_dir):
                if f.endswith('.db'):
                    path = os.path.join(self.backup_dir, f)
                    stat = os.stat(path)
                    backups.append({
                        'name': f,
                        'path': path,
                        'size_mb': stat.st_size / 1024 / 1024,
                        'created': datetime.fromtimestamp(stat.st_mtime)
                    })
            backups.sort(key=lambda x: x['created'], reverse=True)
        except (sqlite3.Error, OSError) as e:
            logger.error(f"백업 목록 조회 실패: {e}")
        return backups

    # =========================================================================
    # 개선 #2: WAL 모드
    # =========================================================================

    def _enable_wal_mode(self) -> None:
        """WAL (Write-Ahead Logging) 모드 활성화"""
        try:
            # WAL 모드 설정
            self.execute("PRAGMA journal_mode=WAL")
            # 동기화 모드 (NORMAL이 균형 좋음)
            self.execute("PRAGMA synchronous=NORMAL")
            # 캐시 크기 증가 (기본 -2000 → -8000, 약 8MB)
            self.execute("PRAGMA cache_size=-8000")
            logger.debug("WAL 모드 활성화됨")
        except (sqlite3.Error, OSError) as e:
            logger.warning(f"WAL 모드 설정 실패: {e}")

    # =========================================================================
    # 개선 #3: 입력 유효성 검사
    # =========================================================================

    @classmethod
    def validate_lot_no(cls, lot_no: str, strict: bool = True) -> Tuple[bool, str]:
        """
        LOT 번호 유효성 검사. 단일 소스: engine_modules.validators.validate_lot_no
        strict 인자는 하위 호환용(무시). 검증 기준은 validators와 동일.
        """
        from engine_modules.validators import validate_lot_no as _validate_lot_no
        return _validate_lot_no(lot_no)

    @staticmethod
    def validate_weight(weight: float) -> Tuple[bool, str]:
        """
        무게 유효성 검사

        Args:
            weight: 검사할 무게 (kg)

        Returns:
            (유효 여부, 오류 메시지)
        """
        if weight is None:
            return False, "무게가 None입니다"

        try:
            weight = float(weight)
        except (ValueError, TypeError):
            return False, f"유효하지 않은 무게: {weight}"

        if weight < 0:
            return False, f"무게는 음수일 수 없습니다: {weight}"

        if weight > 50000:  # 50톤 초과
            return False, f"무게가 비정상적으로 큽니다: {weight}kg"

        return True, ""

    @staticmethod
    def validate_sap_no(sap_no: str) -> Tuple[bool, str]:
        """SAP NO 유효성 검사. 단일 소스: engine_modules.validators.validate_sap_no"""
        from core.validators import validate_sap_no as _validate_sap_no
        return _validate_sap_no(sap_no)

    # =========================================================================
    # 개선 #5: DB 락 감지
    # =========================================================================

    def _set_busy_timeout(self) -> None:
        """busy timeout 설정 (락 대기 시간)"""
        try:
            # 30초 대기 후 타임아웃
            self.execute("PRAGMA busy_timeout=30000")
            logger.debug("busy_timeout 설정: 30초")
        except (sqlite3.Error, OSError) as e:
            logger.warning(f"busy_timeout 설정 실패: {e}")

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        SQL 실행 (락 감지 및 재시도 포함)
        v5.1.2: 상수 기반 재시도, 상세 로깅
        """
        retry_delay = DB_RETRY_DELAY

        for attempt in range(DB_MAX_RETRIES):
            try:
                cursor = self.conn.cursor()
                cursor.execute(sql, params)

                # ✅ 트랜잭션 중이면 commit하지 않음 (롤백 가능하도록)
                if not self._in_transaction:
                    self.conn.commit()

                return cursor
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < DB_MAX_RETRIES - 1:
                    logger.warning(
                        f"DB 락 감지, 재시도 {attempt + 1}/{DB_MAX_RETRIES} "
                        f"({retry_delay:.1f}s 대기) SQL: {sql[:80]}"
                    )
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= DB_RETRY_BACKOFF
                else:
                    raise

        raise sqlite3.OperationalError("DB 락 타임아웃")

    def executemany(self, sql: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """
        Batch INSERT/UPDATE용 executemany (락 감지 포함)
        v5.1.2: 상수 기반 재시도
        """
        retry_delay = DB_RETRY_DELAY

        for attempt in range(DB_MAX_RETRIES):
            try:
                cursor = self.conn.cursor()
                cursor.executemany(sql, params_list)

                # ✅ 트랜잭션 중이면 commit하지 않음
                if not self._in_transaction:
                    self.conn.commit()

                return cursor
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < DB_MAX_RETRIES - 1:
                    logger.warning(
                        f"DB 락 감지 (executemany), 재시도 {attempt + 1}/{DB_MAX_RETRIES} "
                        f"({retry_delay:.1f}s 대기)"
                    )
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= DB_RETRY_BACKOFF
                else:
                    raise

        raise sqlite3.OperationalError("DB 락 타임아웃 (executemany)")

    def begin_transaction(self) -> None:
        """
        트랜잭션 시작 (v5.1.2: BEGIN IMMEDIATE 재시도 추가)
        
        ★★★ 중요 ★★★
        - _write_lock 획득
        - _in_transaction = True 설정
        - 중첩 호출 시 락만 유지 (BEGIN 재실행 안 함)
        - SQLITE_BUSY 시 지수 백오프 재시도 (최대 3회)
        """
        self._write_lock.acquire()
        if self._in_transaction:
            # 중첩 트랜잭션: 이미 시작됨 (RLock 카운터만 증가)
            return
        
        # BEGIN IMMEDIATE도 SQLITE_BUSY 가능 → 재시도
        max_retries = 3
        retry_delay = 0.5
        for attempt in range(max_retries):
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                self._in_transaction = True
                logger.debug("트랜잭션 시작 (BEGIN IMMEDIATE)")
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    logger.warning(
                        f"BEGIN IMMEDIATE 락 감지, 재시도 {attempt + 1}/{max_retries} "
                        f"({retry_delay:.1f}s 대기)"
                    )
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self._write_lock.release()
                    raise

    def commit(self) -> None:
        """
        트랜잭션 커밋 (v2.9.51: 락 해제 보장)
        """
        try:
            self.conn.commit()
            logger.debug("트랜잭션 커밋 완료")
        finally:
            self._in_transaction = False
            try:
                self._write_lock.release()
            except RuntimeError as _e:
                logger.debug(f"[database] 무시: {_e}")

    def rollback(self) -> None:
        """
        트랜잭션 롤백 (v2.9.51: 락 해제 보장)
        """
        try:
            self.conn.rollback()
            logger.debug("트랜잭션 롤백 완료")
        finally:
            self._in_transaction = False
            try:
                self._write_lock.release()
            except RuntimeError as _e:
                logger.debug(f"[database] 무시: {_e}")

    class _TransactionContext:
        """
        v5.1.2: 트랜잭션 컨텍스트 매니저
        
        사용법:
            with db.transaction():
                db.execute("INSERT ...")
                db.execute("UPDATE ...")
            # 자동 커밋 또는 예외 시 자동 롤백
        """
        def __init__(self, db_instance):
            self._db = db_instance
        
        def __enter__(self):
            self._db.begin_transaction()
            return self._db
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self._db.commit()
            else:
                logger.error(f"트랜잭션 롤백: {exc_type.__name__}: {exc_val}")
                self._db.rollback()
            return False  # 예외 전파
    
    def transaction(self, mode: str = "IMMEDIATE"):
        """
        v5.1.2: 트랜잭션 컨텍스트 매니저 반환
        v5.1.6: mode 인자 지원 (하위 호환 — 항상 IMMEDIATE)
        
        사용법:
            with db.transaction():
                db.execute("INSERT ...")
            with db.transaction("IMMEDIATE"):  # 동일 동작
                db.execute("UPDATE ...")
        """
        return self._TransactionContext(self)

    def close(self) -> None:
        """
        연결 종료
        v2.5.4: thread-local 연결도 안전하게 종료 (Windows 파일잠김 방지)
        """
        # thread-local 연결 종료
        if hasattr(self, '_local') and hasattr(self._local, 'conn') and self._local.conn:
            try:
                self._local.conn.close()
            except (AttributeError, RuntimeError) as e:
                logger.debug(f'DB 예외 (무시): {e}')  # v2.9.75  # 연결 종료 예외 무시
            finally:
                self._local.conn = None

        # 기존 연결 종료
        if self._cursor:
            try:
                self._cursor.close()
            except (sqlite3.Error, OSError) as e:
                logger.debug(f'DB 예외 (무시): {e}')  # v2.9.75  # 커서 종료 예외 무시
            finally:
                self._cursor = None
        if self._connection:
            try:
                self._connection.close()
            except (sqlite3.Error, OSError) as e:
                logger.debug(f'DB 예외 (무시): {e}')  # v2.9.75  # 메인 연결 종료 예외 무시
            finally:
                self._connection = None

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """
        단일 행 조회 (dict 반환)
        
        v5.0.0: sqlite3.Row를 dict로 변환하여 반환
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> List[dict]:
        """
        다중 행 조회 (list[dict] 반환)
        
        v5.0.0: sqlite3.Row를 dict로 변환하여 반환
        Phase 5: 성능 측정 추가
        """
        try:
            from .performance import monitor
            import time
            start = time.time()
        except ImportError:
            monitor = None
            start = None
        
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        result = cursor.fetchall()
        
        # v5.0.0: sqlite3.Row를 dict로 변환
        result = [dict(row) for row in result] if result else []
        
        # 성능 측정
        if monitor and start:
            elapsed = time.time() - start
            if elapsed > 0.5:  # 0.5초 이상 느린 쿼리만
                logger.warning(f"⚠️ 느린 쿼리 ({elapsed:.3f}s): {sql[:100]}...")
                monitor._record("DB_fetchall", elapsed, "fetchall")
        
        return result

    def insert_returning_id(self, sql: str, params: tuple = ()) -> Optional[int]:
        """
        P3: INSERT 후 생성된 ID 반환 (DB 독립적)
        
        SQLite: cursor.lastrowid
        PostgreSQL 전환 시: RETURNING id 사용으로 오버라이드
        """
        cursor = self.execute(sql, params)
        return cursor.lastrowid if hasattr(cursor, 'lastrowid') else None

    def _init_database(self) -> None:
        """
        데이터베이스 테이블 초기화 (v4.0.3: 섹션별 분리)

        v2.5.4: LOT 단위 통합 재고 관리
        """
        self._init_shipment_table()
        self._init_inventory_table()
        self._init_tonbag_table()
        self._init_outbound_tables()
        self._init_movement_tables()
        self._init_snapshot_tables()
        self._migrate_v243()

    def _init_shipment_table(self) -> None:
        """선적(Shipment) 테이블"""
        self.execute("""
            CREATE TABLE IF NOT EXISTS shipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sap_no TEXT UNIQUE,
                folio TEXT,
                invoice_no TEXT,
                bl_no TEXT,
                do_no TEXT,
                vessel TEXT,
                voyage TEXT,
                product TEXT,
                product_code TEXT,
                customer TEXT,
                origin TEXT,
                destination TEXT,
                ship_date DATE,
                eta_date DATE,
                arrival_date DATE,
                stock_date DATE,
                total_qty_mt REAL,
                total_lots INTEGER,
                total_containers INTEGER,
                unit_price REAL,
                total_amount REAL,
                currency TEXT DEFAULT 'USD',
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        # =====================================================================
        # 재고 (Inventory) 테이블 - LOT 마스터 (v2.5.4 루비리 요청 순서)
        # SAP NO → BL NO → CONTAINER → PRODUCT → LOT NO → LOT SQM →
        # MXBG PALLET → NET WEIGHT → GROSS WEIGHT → SALAR INVOICE NO →
        # 선적일 → 입항일 → FREE TIME → 창고 →
        # ETA BUSAN → Date in stock → Customs → SALE REF (v2.5.4 추가)
    def _init_inventory_table(self) -> None:
        """재고(Inventory) 테이블 — LOT 마스터"""
        # =====================================================================
        self.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id INTEGER,
                list_no INTEGER DEFAULT 0,

                -- ✅ 루비리 요청 순서 (v2.5.4)
                sap_no TEXT,
                bl_no TEXT,
                container_no TEXT,
                product TEXT,
                lot_no TEXT NOT NULL UNIQUE,
                lot_sqm TEXT,
                mxbg_pallet INTEGER DEFAULT 10,  -- 톤백 수 (tonbag_count와 동일. 표준: tonbag_count)
                net_weight REAL DEFAULT 0 CHECK(net_weight >= 0),
                gross_weight REAL DEFAULT 0 CHECK(gross_weight >= 0),
                salar_invoice_no TEXT,
                ship_date DATE,
                arrival_date DATE,
                free_time INTEGER DEFAULT 0,
                warehouse TEXT DEFAULT 'GY',

                -- ✅ v2.5.4 추가 컬럼
                eta_busan DATE,
                stock_date DATE,
                customs TEXT,
                sale_ref TEXT,

                -- 재고 관리 필드 (v3.8.4: CHECK 추가)
                -- ★ 무게 필드 관계 (v5.5.3 문서화):
                --   입고 시: net_weight = initial_weight = current_weight (동일값)
                --   출고 시: current_weight 감소, initial_weight/net_weight 불변
                --   net_weight: PL 원본 순중량 (참조용, 불변)
                --   initial_weight: 입고 시 총중량 (잔여율 계산 기준)
                --   current_weight: 현재 잔여중량 (실시간 변동)
                --   picked_weight: 출고 확정량 (PICKED 상태 합계)
                initial_weight REAL DEFAULT 0 CHECK(initial_weight >= 0),
                current_weight REAL DEFAULT 0 CHECK(current_weight >= 0),
                picked_weight REAL DEFAULT 0 CHECK(picked_weight >= 0),

                -- 추가 메타데이터
                product_code TEXT,
                folio TEXT,
                invoice_no TEXT,
                vessel TEXT,
                location TEXT,
                status TEXT DEFAULT 'AVAILABLE',

                -- 날짜 정보
                inbound_date DATE,
                days_old INTEGER DEFAULT 0,

                -- 출고 정보
                -- ★ 고객명 동의어 (v5.5.3 문서화):
                --   inventory.sold_to = 고객사 (입고 시 매입처)
                --   inventory_tonbag.picked_to = 출고 고객
                --   stock_movement.customer = 거래 이력 고객
                sold_to TEXT,  -- 고객사 (customer와 동일. 표준: customer)
                invoice_date DATE,
                actual_pickup DATE,

                -- 기타
                condition TEXT,
                remark TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,

                FOREIGN KEY (shipment_id) REFERENCES shipment(id)
            )
        """)

        # LOT 상세 (Inventory Detail) 테이블 - 컨테이너/품목 정보 (v2.5.4)
        # 참고용, 출고 차감은 inventory 테이블에서 함
        self.execute("""
            CREATE TABLE IF NOT EXISTS inventory_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,
                lot_no TEXT,

                -- 컨테이너/품목 정보
                container_no TEXT,
                seal_no TEXT,
                product_code TEXT,
                item_seq INTEGER DEFAULT 1,

                -- 무게 정보 (개별 컨테이너)
                bag_count INTEGER DEFAULT 0,
                net_weight REAL DEFAULT 0,
                gross_weight REAL DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (inventory_id) REFERENCES inventory(id),
                UNIQUE (lot_no, container_no)
            )
        """)

    def _init_tonbag_table(self) -> None:
        """톤백(inventory_tonbag) 테이블 + 인덱스 (v4.2.0: UID 추가)"""
        # =====================================================================
        # Sub LOT 테이블 (v2.5.4) - 톤백 단위 관리
        # LOT NO 하나에 MXBG PALLET 수만큼 Sub LOT 생성
        # 출고 시 내림차순 (10 → 9 → 8 → ...) 으로 출고
        # v4.2.0: tonbag_uid 전역 유니크 식별자 추가
        # =====================================================================
        self.execute("""
            CREATE TABLE IF NOT EXISTS inventory_tonbag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,

                -- 🔑 복합 키로 중복 방지
                sap_no TEXT,
                bl_no TEXT,
                lot_no TEXT NOT NULL,
                sub_lt INTEGER NOT NULL,  -- 레거시 호환 (INTEGER)
                
                -- ★ v5.2.0: tonbag_no TEXT (앞자리 0 보존, "001"~"NNN")
                -- 일반: "001","002"... / 샘플: "S00"
                tonbag_no TEXT,
                
                -- ✅ v4.2.0: 톤백 UID (전역 유니크 식별자)
                -- 형식: LOT-01, LOT-02 (일반) / LOT-S0 (샘플)
                tonbag_uid TEXT,

                -- 상세 정보 (v3.8.4: CHECK 추가)
                weight REAL DEFAULT 0 CHECK(weight >= 0),
                status TEXT DEFAULT 'AVAILABLE',

                -- v3.9.1: 샘플 톤백 구분 (0=일반, 1=샘플)
                is_sample INTEGER DEFAULT 0,

                -- ✅ 입고일 (v2.5.4 추가)
                inbound_date DATE,

                -- ✅ 화물 위치 (v2.5.4 추가)
                location TEXT,

                -- 출고 정보
                picked_date DATE,
                picked_to TEXT,  -- 출고 고객 (customer와 동일. 표준: customer)
                pick_ref TEXT,
                sale_ref TEXT,

                -- ✅ 출고일 (v2.5.4 추가) - picked_date와 별도로 관리
                outbound_date DATE,

                -- ✅ 비고란 (v2.5.4 추가) - 사용자 수기 입력용
                remarks TEXT,

                -- 메타데이터
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,

                FOREIGN KEY (inventory_id) REFERENCES inventory(id),
                UNIQUE(sap_no, bl_no, lot_no, sub_lt)
            )
        """)

        # Sub LOT 인덱스 생성 (조회 성능)
        self.execute("CREATE INDEX IF NOT EXISTS idx_sublot_lot ON inventory_tonbag(lot_no)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_sublot_status ON inventory_tonbag(status)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_sublot_sap_bl ON inventory_tonbag(sap_no, bl_no)")
        
        # S1: inventory 핵심 인덱스 (81건+ WHERE lot_no 쿼리 최적화)
        # v5.6.0: idx_inventory_lot 제거 (idx_inventory_lot_no와 중복)
        # v5.6.0: idx_inventory_sap 제거 (idx_inventory_sap_no와 중복)
        self.execute("CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory(status)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product)")
        
        # S1: stock_movement 인덱스 → 테이블 생성 후로 이동 (v3.8.4 bugfix)
        
        # S1: outbound 인덱스 → 테이블 생성 후로 이동 (v3.8.4 bugfix)
        
        # --- v5.3.9 hotfix: 기존 DB(레거시) 스키마에 tonbag_no 컬럼이 없을 수 있음
        # CREATE TABLE IF NOT EXISTS 는 기존 테이블을 ALTER 하지 않으므로, 런타임에서 보강한다.
        try:
            _cols = {r.get('name') for r in self.fetchall('PRAGMA table_info(inventory_tonbag)')}
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError, OSError):
            _cols = set()
        if 'tonbag_no' not in _cols:
            self.execute('ALTER TABLE inventory_tonbag ADD COLUMN tonbag_no TEXT')
            # 레거시 sub_lt(INTEGER) → tonbag_no(TEXT, 앞자리 0 보존)
            self.execute("UPDATE inventory_tonbag SET tonbag_no = printf('%03d', sub_lt) WHERE tonbag_no IS NULL AND sub_lt IS NOT NULL")
            # 샘플 톤백은 고정 키(S00)로 보정 (정책: LOT당 1개)
            try:
                self.execute("UPDATE inventory_tonbag SET tonbag_no = 'S00' WHERE is_sample = 1")
                # v5.5.3: tonbag_uid도 S1→S0 통일 (sub_lt=0과 일치)
                self.execute("UPDATE inventory_tonbag SET tonbag_uid = lot_no || '-S0' WHERE is_sample = 1 AND tonbag_uid LIKE '%-S1'")
            except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError, OSError) as _e:
                logger.debug(f"Suppressed: {_e}")
        
        # ★★★ v5.2.0: 복합 유니크 인덱스 ★★★
        self.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tonbag_lot_sublt ON inventory_tonbag(lot_no, sub_lt)")
        self.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tonbag_bl_lot_no ON inventory_tonbag(bl_no, lot_no, tonbag_no)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_tonbag_tonbag_no ON inventory_tonbag(tonbag_no)")

    def _init_outbound_tables(self) -> None:
        """출고(Outbound) + 출고상세(outbound_item) 테이블"""
        # 출고 (Outbound) 테이블
        self.execute("""
            CREATE TABLE IF NOT EXISTS outbound (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outbound_no TEXT UNIQUE,
                customer TEXT,
                sale_ref TEXT,
                outbound_date DATE,
                destination TEXT,
                total_qty_mt REAL,
                total_lots INTEGER,
                status TEXT DEFAULT 'PENDING',
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 출고 상세 (Outbound Item) 테이블 - LOT 단위
        # v2.5.4: 입고일, 화물위치, 구매처, 배송지 추가
        self.execute("""
            CREATE TABLE IF NOT EXISTS outbound_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outbound_id INTEGER,
                inventory_id INTEGER,
                lot_no TEXT,
                product_code TEXT,
                qty_mt REAL,
                picked_date DATE,
                inbound_date DATE,
                location TEXT,
                customer TEXT,
                destination TEXT,
                FOREIGN KEY (outbound_id) REFERENCES outbound(id),
                FOREIGN KEY (inventory_id) REFERENCES inventory(id)
            )
        """)

        # v3.8.4: outbound 인덱스 (테이블 생성 후)
        # v5.6.0: idx_outbound_lot 제거 (idx_outbound_item_lot와 중복)
        self.execute("CREATE INDEX IF NOT EXISTS idx_outbound_date ON outbound(outbound_date)")

    def _init_movement_tables(self) -> None:
        """재고이동(stock_movement) + 반품(return_history) 테이블"""
        # 재고 이동 이력 테이블
        self.execute("""
            CREATE TABLE IF NOT EXISTS stock_movement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movement_type TEXT,
                movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                lot_no TEXT,
                product_code TEXT,
                qty_kg REAL,
                before_weight REAL,
                after_weight REAL,
                reference_no TEXT,
                reference_type TEXT,
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT DEFAULT 'SYSTEM'
            )
        """)

        # =================================================================
        # v3.7.0: 거래 이력 테이블 불변 트리거 (UPDATE/DELETE 금지)
        # stock_movement는 감사 추적용 이력이므로 수정/삭제 차단
        # =================================================================
        self.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_stock_movement_no_update
            BEFORE UPDATE ON stock_movement
            BEGIN
                SELECT RAISE(ABORT, 'stock_movement is immutable: UPDATE is not allowed. Use correction events instead.');
            END
        """)
        self.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_stock_movement_no_delete
            BEFORE DELETE ON stock_movement
            BEGIN
                SELECT RAISE(ABORT, 'stock_movement is immutable: DELETE is not allowed. Use correction events instead.');
            END
        """)
        logger.info("[스키마] stock_movement 불변 트리거 적용됨 (UPDATE/DELETE 금지)")

        # v3.8.4: stock_movement 인덱스 (테이블 생성 후)
        self.execute("CREATE INDEX IF NOT EXISTS idx_movement_lot ON stock_movement(lot_no)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_movement_date ON stock_movement(movement_date)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_movement_type ON stock_movement(movement_type)")

        # =================================================================
        # v3.8.4: return_history 테이블
        # =================================================================
        self.execute("""
            CREATE TABLE IF NOT EXISTS return_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                sub_lt INTEGER NOT NULL,
                return_date DATE,
                original_customer TEXT,
                original_sale_ref TEXT,
                reason TEXT,
                remark TEXT,
                weight REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lot_no) REFERENCES inventory(lot_no)
            )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_return_lot ON return_history(lot_no)")
        logger.info("[스키마] return_history 테이블 생성 완료")

    def _init_snapshot_tables(self) -> None:
        """재고 스냅샷(inventory_snapshot) 테이블"""
        # v3.8.4: 재고 스냅샷 (일별)
        self.execute("""
            CREATE TABLE IF NOT EXISTS inventory_snapshot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date DATE NOT NULL,
                total_lots INTEGER DEFAULT 0,
                total_tonbags INTEGER DEFAULT 0,
                total_weight_kg REAL DEFAULT 0,
                available_weight_kg REAL DEFAULT 0,
                picked_weight_kg REAL DEFAULT 0,
                product_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_date)
            )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_date ON inventory_snapshot(snapshot_date)")
        logger.info("[스키마] inventory_snapshot 테이블 생성 완료")

    def _migrate_v243(self) -> None:
        """v2.4.3 스키마 마이그레이션 - 출고 리스트 필드 추가 + 톤백 테이블 이름 변경"""

        # 1. 테이블 이름 변경: inventory_sublot → inventory_tonbag
        try:
            # 기존 테이블이 있으면 이름 변경
            self.execute("ALTER TABLE inventory_sublot RENAME TO inventory_tonbag")
            logger.info("[마이그레이션] inventory_sublot → inventory_tonbag 이름 변경됨")
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower() or "already exists" in str(e).lower():
                pass  # 이미 변경됨 또는 테이블 없음
            else:
                logger.debug(f"[마이그레이션] 테이블 이름 변경 스킵: {e}")

        # 2. 컬럼 추가
        migrations = [
            # ★★★ v2.9.24: shipment 테이블 확장 (레코멘드 반영) ★★★
            ("shipment", "port_of_loading", "TEXT"),
            ("shipment", "port_of_discharge", "TEXT"),
            ("shipment", "total_net_weight", "REAL"),
            ("shipment", "total_gross_weight", "REAL"),
            # outbound 테이블
            ("outbound", "destination", "TEXT"),
            ("outbound", "remarks", "TEXT"),
            # outbound_item 테이블 - 입고일, 화물위치, 구매처, 배송지
            ("outbound_item", "inbound_date", "DATE"),
            ("outbound_item", "location", "TEXT"),
            ("outbound_item", "customer", "TEXT"),
            ("outbound_item", "destination", "TEXT"),
            # ★★★ v3.8.4: inventory_tonbag 출고참조 컬럼 추가 ★★★
            ("inventory_tonbag", "sale_ref", "TEXT"),
        ]

        for table, column, col_type in migrations:
            try:
                self.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                logger.info(f"[마이그레이션] {table}.{column} 추가됨")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    pass  # 이미 존재하면 무시
                else:
                    logger.debug(f"[마이그레이션] {table}.{column} 스킵: {e}")
        
        # ★★★ v2.9.89: Picking List 테이블 추가 ★★★
        self._migrate_v289_picking_list()
        
        # ★★★ v3.8.8: 컬럼명 통일 마이그레이션 ★★★
        self._migrate_v388_column_unify()
        
        # ★★★ v3.9.1: 샘플 톤백 is_sample 컬럼 추가 ★★★
        self._migrate_v391_sample_tonbag()
        
        # ★★★ v3.9.6: 검색 성능 인덱스 추가 ★★★
        self._migrate_v396_search_indexes()
    
    
    def _verify_schema(self) -> Dict[str, Any]:
        """
        ★★★ v2.9.25: DB 스키마 자동 점검 ★★★
        
        시작 시 필수 테이블과 컬럼이 존재하는지 확인하고,
        문제가 있으면 로그에 경고를 남깁니다.
        
        Returns:
            점검 결과 딕셔너리
        """
        result = {
            'ok': True,
            'missing_tables': [],
            'missing_columns': {},
            'warnings': []
        }
        
        # 필수 테이블 목록
        required_tables = ['shipment', 'inventory', 'inventory_tonbag', 'outbound', 'outbound_item']
        
        # 필수 컬럼 (테이블: [컬럼 목록])
        required_columns = {
            'shipment': ['sap_no', 'bl_no', 'arrival_date', 'origin', 'destination'],
            'inventory': ['lot_no', 'sap_no', 'product', 'current_weight', 'status'],
            'inventory_tonbag': ['lot_no', 'sub_lt', 'weight', 'status'],
        }
        
        try:
            # 1. 테이블 존재 확인
            existing_tables = self.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
            existing_table_names = {row['name'] for row in existing_tables}
            
            for table in required_tables:
                if table not in existing_table_names:
                    result['missing_tables'].append(table)
                    result['ok'] = False
            
            # 2. 컬럼 존재 확인
            for table, columns in required_columns.items():
                if table not in existing_table_names:
                    continue
                
                existing_cols = self.fetchall(f"PRAGMA table_info({table})")
                existing_col_names = {row['name'] for row in existing_cols}
                
                missing = [col for col in columns if col not in existing_col_names]
                if missing:
                    result['missing_columns'][table] = missing
                    result['ok'] = False
            
            # 3. 결과 로깅
            if result['ok']:
                logger.info("[스키마 점검] ✅ 모든 필수 테이블/컬럼 확인됨")
            else:
                if result['missing_tables']:
                    logger.warning(f"[스키마 점검] ⚠️ 누락된 테이블: {result['missing_tables']}")
                if result['missing_columns']:
                    logger.warning(f"[스키마 점검] ⚠️ 누락된 컬럼: {result['missing_columns']}")
                    
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"[스키마 점검] 오류: {e}")
            result['ok'] = False
            result['warnings'].append(str(e))
        
        return result
    
    def get_schema_status(self) -> Dict[str, Any]:
        """외부에서 스키마 상태 조회용"""
        return self._verify_schema()
    



    def _create_indexes(self) -> None:
        """
        성능 향상을 위한 인덱스 생성 (개선 #4)

        인덱스는 조회 성능을 크게 향상시킵니다.
        - 단일 컬럼 인덱스: 자주 검색되는 컬럼
        - 복합 인덱스: 자주 함께 조회되는 컬럼 조합
        """
        indexes = [
            # inventory 테이블 인덱스 (v2.5.4 - LOT 단위)
            ("idx_inventory_lot_no", "inventory", "lot_no"),
            ("idx_inventory_sap_no", "inventory", "sap_no"),
            ("idx_inventory_status", "inventory", "status"),
            ("idx_inventory_stock_date", "inventory", "stock_date"),
            ("idx_inventory_product", "inventory", "product_code"),
            ("idx_inventory_warehouse", "inventory", "warehouse"),
            # v2.5.4: 복합 인덱스 (LOT + 품목)
            ("idx_inventory_lot_product", "inventory", "lot_no, product_code"),
            ("idx_inventory_sap_status", "inventory", "sap_no, status"),
            ("idx_inventory_product_status", "inventory", "product_code, status"),

            # inventory_detail 테이블 인덱스 (v2.5.4 - 컨테이너 상세)
            ("idx_detail_lot_no", "inventory_detail", "lot_no"),
            ("idx_detail_container", "inventory_detail", "container_no"),
            ("idx_detail_lot_container", "inventory_detail", "lot_no, container_no"),

            # shipment 테이블 인덱스
            ("idx_shipment_sap_no", "shipment", "sap_no"),
            ("idx_shipment_bl_no", "shipment", "bl_no"),
            ("idx_shipment_folio", "shipment", "folio"),
            ("idx_shipment_status", "shipment", "status"),

            # outbound 테이블 인덱스
            ("idx_outbound_sale_ref", "outbound", "sale_ref"),
            ("idx_outbound_customer", "outbound", "customer"),
            ("idx_outbound_date", "outbound", "outbound_date"),

            # outbound_item 테이블 인덱스
            ("idx_outbound_item_lot", "outbound_item", "lot_no"),
            ("idx_outbound_item_inventory", "outbound_item", "inventory_id"),
            ("idx_outbound_item_outbound", "outbound_item", "outbound_id"),

            # stock_movement 테이블 인덱스
            ("idx_movement_lot", "stock_movement", "lot_no"),
            ("idx_movement_type", "stock_movement", "movement_type"),
            ("idx_movement_date", "stock_movement", "created_at"),
        ]

        for idx_name, table, columns in indexes:
            try:
                self.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({columns})")
            except sqlite3.OperationalError as e:
                # 인덱스가 이미 존재하거나 테이블이 없는 경우 무시
                logger.debug(f"인덱스 생성 스킵: {idx_name} - {e}")

        # 테이블 통계 갱신 (쿼리 최적화)
        try:
            self.execute("ANALYZE")
        except (sqlite3.Error, OSError) as e:
            logger.debug(f"ANALYZE 실패: {e}")

