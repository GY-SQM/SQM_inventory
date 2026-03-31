# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime 패키지 공개 API (v7.0.0 완전 구현판)
=========================================================
"""
from .parser_result import ParserResult
from .pattern_registry import PatternProfile, PatternRegistry, DEFAULT_PATTERN_REGISTRY
from .session_manager import DocumentSession, SessionManager
from .cross_validator import cross_validate_session
from .adapters import adapt_bl_result, adapt_pl_result, adapt_fa_result, build_session_from_legacy
from .pl_analytics_writer import (
    append_pl_warnings, get_daily_summary, get_weekly_summary, get_monthly_summary
)
from .session_audit_writer import (
    write_cross_validation_result, query_recent_parse_events, get_parse_error_summary
)

_FULL_API = True

__all__ = [
    "ParserResult",
    "PatternProfile", "PatternRegistry", "DEFAULT_PATTERN_REGISTRY",
    "DocumentSession", "SessionManager",
    "cross_validate_session",
    "adapt_bl_result", "adapt_pl_result", "adapt_fa_result", "build_session_from_legacy",
    "append_pl_warnings", "get_daily_summary", "get_weekly_summary", "get_monthly_summary",
    "write_cross_validation_result", "query_recent_parse_events", "get_parse_error_summary",
]
