# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.session_audit_writer — stub (v7.0.0)
=========================================================
교차 검증 결과 및 파싱 이벤트 감사 로그.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Any, Dict, List

_ANALYTICS_DIR = os.path.join('data', 'analytics')


def _ensure_dir() -> None:
    os.makedirs(_ANALYTICS_DIR, exist_ok=True)


def write_cross_validation_result(
    session_id: str,
    lot_no: str,
    passed: bool,
    errors: List[Dict] = None,
    warnings: List[Dict] = None,
) -> bool:
    """교차 검증 결과 감사 로그 기록"""
    try:
        _ensure_dir()
        path = os.path.join(
            _ANALYTICS_DIR,
            f"cross_validation_{datetime.now().strftime('%Y%m%d')}.json"
        )
        entries: List[Dict[str, Any]] = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                entries = json.load(f)
        entries.append({
            'ts': datetime.now().isoformat(),
            'session_id': session_id,
            'lot_no': lot_no,
            'passed': passed,
            'error_count': len(errors or []),
            'warning_count': len(warnings or []),
            'errors': errors or [],
            'warnings': warnings or [],
        })
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def query_recent_parse_events(limit: int = 20) -> List[Dict[str, Any]]:
    """최근 파싱 이벤트 조회"""
    try:
        _ensure_dir()
        path = os.path.join(
            _ANALYTICS_DIR,
            f"cross_validation_{datetime.now().strftime('%Y%m%d')}.json"
        )
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        return entries[-limit:]
    except Exception:
        return []


def get_parse_error_summary(days: int = 7) -> Dict[str, Any]:
    """파싱 오류 요약"""
    return {
        'period_days': days,
        'total_sessions': 0,
        'total_errors': 0,
        'total_warnings': 0,
        'pass_rate': 100.0,
        'entries': [],
    }
