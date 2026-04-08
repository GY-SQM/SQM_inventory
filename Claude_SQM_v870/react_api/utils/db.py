# -*- coding: utf-8 -*-
"""DB 연결 및 공통 유틸리티."""
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from engine_modules.database import SQMDatabase
from engine_modules.inventory_modular.engine import SQMInventoryEngineV3

logger = logging.getLogger(__name__)


@contextmanager
def get_db() -> Generator[SQMDatabase, None, None]:
    """DB 연결을 열고, 사용 후 안전하게 닫는다."""
    db = SQMDatabase()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            logger.debug("DB close 중 무시 가능한 예외", exc_info=True)


@contextmanager
def get_engine() -> Generator[SQMInventoryEngineV3, None, None]:
    """비즈니스 로직 엔진을 열고, 사용 후 안전하게 닫는다.

    SQMInventoryEngineV3는 InboundMixin, OutboundMixin, TonbagMixin 등
    모든 비즈니스 메서드를 포함한다. Write API에서는 이것을 사용해야 한다.

    ⚠️  [위험4] SQMDatabase는 threading.local 기반 연결을 사용한다.
         FastAPI 라우터는 반드시 async def 가 아닌 def(동기)로 유지해야 한다.
         async def로 변환하면 이벤트 루프에서 스레드 로컬 연결이 공유되어
         SQLite 동시성 오류가 발생할 수 있다.
    """
    engine = SQMInventoryEngineV3()
    try:
        yield engine
    finally:
        try:
            engine.close()
        except Exception:
            logger.debug("Engine close 중 무시 가능한 예외", exc_info=True)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
