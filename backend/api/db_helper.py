"""
SQM DB 연결 헬퍼 (Phase 2-4)
SQLite 연결 실패 시 최대 3회 재시도 + WAL + 권장 PRAGMA 자동 설정.
"""
import sqlite3
import time
import logging

logger = logging.getLogger(__name__)

_DEFAULT_PRAGMAS = [
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA cache_size=5000",
]


def get_db_connection(
    db_path: str,
    timeout: float = 10.0,
    retries: int = 3,
    row_factory: bool = True,
) -> sqlite3.Connection:
    """
    WAL 모드 + 권장 PRAGMA가 설정된 SQLite 연결 반환.
    OperationalError(잠김 등) 발생 시 최대 retries회 재시도.
    모든 재시도 실패 시 마지막 예외를 상위로 전파.
    """
    last_exc: Exception = RuntimeError("DB 연결 실패")
    for attempt in range(1, retries + 1):
        try:
            con = sqlite3.connect(
                db_path,
                timeout=timeout,
                check_same_thread=False,
            )
            if row_factory:
                con.row_factory = sqlite3.Row
            for pragma in _DEFAULT_PRAGMAS:
                try:
                    con.execute(pragma)
                except Exception:
                    pass
            return con
        except sqlite3.OperationalError as e:
            last_exc = e
            if attempt < retries:
                wait = 0.5 * attempt   # 0.5s / 1.0s
                logger.warning(
                    f"[db_helper] DB 연결 실패 ({attempt}/{retries}), "
                    f"{wait}초 후 재시도: {e}"
                )
                time.sleep(wait)
            else:
                logger.error(f"[db_helper] DB 연결 최종 실패: {e}")
    raise last_exc
