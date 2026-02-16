# -*- coding: utf-8 -*-
"""
core.config — 설정 진입점 (P4)
==============================
루트 config 모듈 re-export. from core.config import DB_PATH 등 사용.
"""
from config import (
    BASE_DIR,
    DATA_DIR,
    DB_DIR,
    OUTPUT_DIR,
    BACKUP_DIR,
    LOG_DIR,
    TEMP_DIR,
    DB_TYPE,
    DB_PATH,
    get_db_info,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    SETTINGS_FILE,
    validate_api_key,
    save_api_key_secure,
)

__all__ = [
    'BASE_DIR',
    'DATA_DIR',
    'DB_DIR',
    'OUTPUT_DIR',
    'BACKUP_DIR',
    'LOG_DIR',
    'TEMP_DIR',
    'DB_TYPE',
    'DB_PATH',
    'get_db_info',
    'GEMINI_API_KEY',
    'GEMINI_MODEL',
    'OPENAI_API_KEY',
    'OPENAI_MODEL',
    'SETTINGS_FILE',
    'validate_api_key',
    'save_api_key_secure',
]
