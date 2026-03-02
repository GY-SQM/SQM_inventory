"""
P5-12: core.config 단위 테스트
===============================
core.config import 및 주요 속성 존재·타입
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import (
    BASE_DIR,
    DB_PATH,
    DB_TYPE,
    GEMINI_API_KEY,
    get_db_info,
    get_settings,
)


class TestCoreConfig:
    def test_base_dir_exists(self):
        assert BASE_DIR is not None
        assert hasattr(BASE_DIR, "exists")
        assert BASE_DIR.exists()

    def test_db_path(self):
        assert DB_PATH is not None
        assert str(DB_PATH).endswith(".db") or "db" in str(DB_PATH).lower()

    def test_db_type(self):
        assert DB_TYPE in ("sqlite", "postgresql")

    def test_gemini_api_key_type(self):
        assert isinstance(GEMINI_API_KEY, str)

    def test_get_db_info(self):
        info = get_db_info()
        assert isinstance(info, dict)
        assert "type" in info or "path" in info

    def test_get_settings(self):
        settings = get_settings()
        assert isinstance(settings, dict)
        assert "api_key" in settings or "gemini_api_key" in settings
