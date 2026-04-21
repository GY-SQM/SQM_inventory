# -*- coding: utf-8 -*-
"""
tests/test_boot_markers.py
==========================
Smoke / regression tests for Phase 5-A: JSON-lines logging.

Tests:
    1. test_config_logging_importable   — setup_logging can be imported
    2. test_json_formatter_valid_output — formatter produces valid JSON
    3. test_json_formatter_fields       — required fields present in output
"""

import json
import logging
import sys
import os

import pytest


def test_config_logging_importable():
    """config_logging.setup_logging is importable without errors."""
    from config_logging import setup_logging  # noqa: F401
    assert callable(setup_logging), "setup_logging must be callable"


def test_json_formatter_valid_output():
    """_SQMJsonFormatter.format() returns a parseable JSON string."""
    from config_logging import _SQMJsonFormatter

    formatter = _SQMJsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    # Must parse without raising
    parsed = json.loads(output)
    assert isinstance(parsed, dict), "Output must be a JSON object"


def test_json_formatter_fields():
    """_SQMJsonFormatter output contains ts, level, logger, msg fields."""
    from config_logging import _SQMJsonFormatter

    formatter = _SQMJsonFormatter()
    record = logging.LogRecord(
        name="sqm.engine",
        level=logging.WARNING,
        pathname=__file__,
        lineno=42,
        msg="테스트 메시지 %s",
        args=("Phase5",),
        exc_info=None,
    )
    parsed = json.loads(formatter.format(record))

    assert "ts" in parsed, "Field 'ts' must be present"
    assert "level" in parsed, "Field 'level' must be present"
    assert "logger" in parsed, "Field 'logger' must be present"
    assert "msg" in parsed, "Field 'msg' must be present"

    assert parsed["level"] == "WARNING"
    assert parsed["logger"] == "sqm.engine"
    assert parsed["msg"] == "테스트 메시지 Phase5"
    # ts must look like an ISO datetime (contains 'T')
    assert "T" in parsed["ts"], f"ts must be ISO 8601, got: {parsed['ts']}"
