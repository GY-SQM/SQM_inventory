# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.pl_analytics_writer — stub (v7.0.0)
=========================================================
PL 파싱 경고/통계 기록 (data/analytics/ JSON).
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

_ANALYTICS_DIR = os.path.join('data', 'analytics')


def _ensure_dir() -> None:
    os.makedirs(_ANALYTICS_DIR, exist_ok=True)


def _today_path() -> str:
    return os.path.join(_ANALYTICS_DIR, f"pl_warnings_{datetime.now().strftime('%Y%m%d')}.json")


def append_pl_warnings(
    session_id: str,
    lot_no: str,
    warnings: List[str],
    source_file: str = "",
) -> bool:
    """오늘 날짜 JSON에 PL 경고 추가"""
    try:
        _ensure_dir()
        path = _today_path()
        entries: List[Dict[str, Any]] = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                entries = json.load(f)
        entries.append({
            'ts': datetime.now().isoformat(),
            'session_id': session_id,
            'lot_no': lot_no,
            'warnings': warnings,
            'source_file': source_file,
            'warning_count': len(warnings),
        })
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _load_entries_for_dates(start: datetime, end: datetime) -> List[Dict]:
    entries: List[Dict] = []
    _ensure_dir()
    cur = start
    while cur <= end:
        path = os.path.join(_ANALYTICS_DIR, f"pl_warnings_{cur.strftime('%Y%m%d')}.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    entries.extend(json.load(f))
            except Exception:
                pass
        cur += timedelta(days=1)
    return entries


def _summarize(entries: List[Dict]) -> Dict[str, Any]:
    return {
        'total_sessions': len(entries),
        'total_pl_warnings': sum(e.get('warning_count', 0) for e in entries),
        'total_cross_errors': 0,
        'total_cross_warnings': 0,
        'entries': entries[:50],  # 최근 50건
    }


def get_daily_summary() -> Dict[str, Any]:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return _summarize(_load_entries_for_dates(today, today))


def get_weekly_summary() -> Dict[str, Any]:
    today = datetime.now()
    start = today - timedelta(days=today.weekday())
    return _summarize(_load_entries_for_dates(start, today))


def get_monthly_summary() -> Dict[str, Any]:
    today = datetime.now()
    start = today.replace(day=1)
    return _summarize(_load_entries_for_dates(start, today))
