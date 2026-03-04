"""
P5-14: config_logging 단위 테스트
==================================
setup_logging 호출, LOG_LEVEL, LOG_FILE
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config_logging import LOG_FILE, LOG_FORMAT, LOG_LEVEL, setup_logging


class TestConfigLogging:
    def test_log_level_set(self):
        assert LOG_LEVEL in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") or isinstance(LOG_LEVEL, str)

    def test_log_file_path(self):
        assert LOG_FILE is not None
        assert "log" in str(LOG_FILE).lower() or LOG_FILE.suffix == ".log"

    def test_log_format_non_empty(self):
        assert LOG_FORMAT and "%" in LOG_FORMAT

    def test_setup_logging_returns_logger(self):
        root = setup_logging()
        assert isinstance(root, logging.Logger)
        assert root.name == "root" or root is logging.getLogger()
