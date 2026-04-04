# -*- coding: utf-8 -*-
"""DB 연결 및 공통 유틸리티."""
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from engine_modules.database import SQMDatabase

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


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
