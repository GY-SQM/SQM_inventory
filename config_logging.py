# -*- coding: utf-8 -*-
"""
SQM - 로깅 설정 (P2 config 분할)
================================
경로·포맷·로테이션 설정 및 setup_logging().
config 의존 없이 자체 경로 사용 (순환 참조 방지).
"""

import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# 프로젝트 루트 (이 파일 위치 기준)
_BASE_DIR = Path(__file__).parent.absolute()
_LOG_DIR = _BASE_DIR / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_LEVEL = os.environ.get('SQM_LOG_LEVEL', 'INFO')
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_SIZE_MB = 10
LOG_BACKUP_COUNT = 5
LOG_KEEP_DAYS = 30
LOG_FILE = _LOG_DIR / "sqm_inventory.log"


def setup_logging():
    """
    로깅 설정 초기화 (로테이션 포함).

    Returns:
        logger: 설정된 루트 로거
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console_handler)

    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        logger.warning(f"파일 로깅 설정 실패: {e}")

    return logger
