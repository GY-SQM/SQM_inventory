# -*- coding: utf-8 -*-
"""[감사 M3 확장] DB 연결 안전화 — 오류가 나도 무조건 rollback+close 를 보장.

배경
----
여러 API 엔드포인트가 `_db()` / `_alloc_db()` 로 raw sqlite 연결을 직접 연 뒤
정상 경로에서만 `commit(); close()` 한다. 중간에 예외가 나면 close 로 못 가
연결이 열린 채 남고, SQLite(WAL)에서 커밋 안 된 쓰기 연결이 남으면 DB 락 →
이후 요청이 `database is locked` 로 멈추거나 잠긴다.

이 컨텍스트 매니저를 `with` 로 쓰면 블록을 어떻게 벗어나든(정상 return/예외)
연결이 반드시 정리된다:
  - 정상 종료 → (readonly 아니면) commit → close
  - 예외 발생 → rollback → close → 예외 재전파(HTTPException 등 그대로 전파)

사용 (기존 팩토리 재사용)
------------------------
    from backend.api.db_session import db_session
    with db_session(_alloc_db) as con:          # 팩토리(콜러블) 그대로 전달
        con.execute(...); rows = con.execute(...).fetchall()
        # 명시적 commit 불필요 — 정상 종료 시 자동. 조기 return 도 안전.

또는 경로로:
    with db_session("/path/to.db", readonly=True) as con:
        ...
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from typing import Callable, Iterator, Union

logger = logging.getLogger(__name__)


def _connect(db_path: str, row_factory, busy_timeout_ms: int) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
    if row_factory is not None:
        con.row_factory = row_factory
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
    return con


@contextmanager
def db_session(
    source: Union[str, Callable[[], sqlite3.Connection]],
    *,
    readonly: bool = False,
    row_factory=sqlite3.Row,
    busy_timeout_ms: int = 3000,
) -> Iterator[sqlite3.Connection]:
    """raw sqlite 연결을 안전하게 열고 반드시 닫는다.

    Args:
        source: 연결 팩토리(콜러블, 예: `_alloc_db`) 또는 DB 경로(str).
        readonly: True 면 정상 종료 시 commit 을 건너뛴다(조회 전용).
        row_factory / busy_timeout_ms: source 가 경로일 때만 적용
            (팩토리는 자체 설정을 이미 갖는다고 가정).
    """
    con = source() if callable(source) else _connect(source, row_factory, busy_timeout_ms)
    try:
        yield con
        if not readonly:
            con.commit()
    except Exception:
        try:
            con.rollback()
        except Exception as _rb:
            logger.debug(f"[db_session] rollback 실패(무시): {_rb}")
        raise
    finally:
        try:
            con.close()
        except Exception as _cl:
            logger.debug(f"[db_session] close 실패(무시): {_cl}")
