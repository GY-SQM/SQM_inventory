# -*- coding: utf-8 -*-
"""DB 연결 및 공통 유틸리티."""
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from engine_modules.database import SQMDatabase
from engine_modules.inventory_modular.engine import SQMInventoryEngineV3

logger = logging.getLogger(__name__)


# ── 싱글톤 엔진: 서버 수명 동안 1회만 생성 ──────────────────────────
_shared_engine: SQMInventoryEngineV3 | None = None


def _get_shared_engine() -> SQMInventoryEngineV3:
    """싱글톤 엔진 반환. 최초 호출 시 1회만 생성."""
    global _shared_engine
    if _shared_engine is None:
        _shared_engine = SQMInventoryEngineV3()
        logger.info("공유 엔진 생성 완료 (싱글톤)")
    return _shared_engine


@contextmanager
def get_db() -> Generator[SQMDatabase, None, None]:
    """DB 연결 (싱글톤). 엔진의 db 인스턴스를 공유하여 dual singleton 방지."""
    yield _get_shared_engine().db


@contextmanager
def get_engine() -> Generator[SQMInventoryEngineV3, None, None]:
    """비즈니스 로직 엔진을 열고, 사용 후 안전하게 닫는다.

    SQMInventoryEngineV3는 InboundMixin, OutboundMixin, TonbagMixin 등
    모든 비즈니스 메서드를 포함한다. Write API에서는 이것을 사용해야 한다.

    ⚠️  [위험4] SQMDatabase는 threading.local 기반 연결을 사용한다.
         FastAPI 라우터는 반드시 async def 가 아닌 def(동기)로 유지해야 한다.
         async def로 변환하면 이벤트 루프에서 스레드 로컬 연결이 공유되어
         SQLite 동시성 오류가 발생할 수 있다.

    P2 개선: 매 요청마다 신규 생성 → 싱글톤 공유 (마이그레이션 반복 제거)
    """
    yield _get_shared_engine()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
