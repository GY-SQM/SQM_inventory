"""
SQM - 로깅 설정 (P2 config 분할)
================================
경로·포맷·로테이션 설정 및 setup_logging().
config 의존 없이 자체 경로 사용 (순환 참조 방지).
"""

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

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

_STDIO_BRIDGE_INSTALLED = False
_ORIG_STDOUT = sys.__stdout__
_ORIG_STDERR = sys.__stderr__


# 클래스 내부 suppress 로그용 모듈 전역 logger
logger = logging.getLogger(__name__)

class _StreamTeeToLogger:
    """stdout/stderr를 콘솔에 유지하면서 로그 파일에도 기록."""

    def __init__(self, original_stream, logger_obj, level: int):
        self._original = original_stream
        self._logger = logger_obj
        self._level = level
        self._buf = ""
        self._local = threading.local()

    @property
    def encoding(self):
        return getattr(self._original, "encoding", "utf-8")

    def write(self, data):
        if data is None:
            return 0
        s = str(data)
        # 1) 콘솔 출력은 원본 스트림 유지
        try:
            self._original.write(s)
        except (OSError, ValueError) as e:
            logger.debug(f"[write] Suppressed: {e}")
        # 2) 로그 파일에도 동일 메시지 저장
        if getattr(self._local, "in_write", False):
            return len(s)
        self._local.in_write = True
        try:
            self._buf += s
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                msg = line.rstrip()
                if msg:
                    self._logger.log(self._level, msg)
        finally:
            self._local.in_write = False
        return len(s)

    def flush(self):
        try:
            self._original.flush()
        except (OSError, ValueError) as e:
            logger.debug(f"[flush] Suppressed: {e}")
        if self._buf.strip():
            try:
                self._logger.log(self._level, self._buf.strip())
            except (OSError, ValueError) as e:
                logger.debug(f"[flush] Suppressed: {e}")
        self._buf = ""

    def isatty(self):
        return bool(getattr(self._original, "isatty", lambda: False)())


def _install_stdio_bridge(logger_obj):
    """sys.stdout/stderr를 로거로 브리지(중복 설치 방지)."""
    global _STDIO_BRIDGE_INSTALLED
    if _STDIO_BRIDGE_INSTALLED:
        return
    capture_stdio = os.environ.get("SQM_CAPTURE_STDIO", "1").strip().lower()
    if capture_stdio in ("0", "false", "no", "off"):
        return
    sys.stdout = _StreamTeeToLogger(_ORIG_STDOUT, logger_obj, logging.INFO)
    sys.stderr = _StreamTeeToLogger(_ORIG_STDERR, logger_obj, logging.ERROR)
    _STDIO_BRIDGE_INSTALLED = True


def setup_logging():
    """
    로깅 설정 초기화 (로테이션 포함).

    Returns:
        logger: 설정된 루트 로거
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.handlers.clear()

    # 콘솔 핸들러는 원본 stdout에 고정 (stdout/stderr 브리지와 재귀 방지)
    console_handler = logging.StreamHandler(stream=_ORIG_STDOUT)
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

    # warnings.warn(...)도 logging으로 수집
    logging.captureWarnings(True)
    # CMD에 보이는 stdout/stderr를 로그 파일에도 동일 기록
    _install_stdio_bridge(logger)

    return logger
