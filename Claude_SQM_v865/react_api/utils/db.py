# -*- coding: utf-8 -*-
"""DB 연결 및 공통 유틸리티."""
from datetime import datetime
from engine_modules.database import SQMDatabase


def get_db() -> SQMDatabase:
    return SQMDatabase()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
