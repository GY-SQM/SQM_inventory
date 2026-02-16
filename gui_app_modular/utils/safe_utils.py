# -*- coding: utf-8 -*-
"""
SQM 재고관리 - GUI 공통 유틸리티
================================

v2.9.91 - gui_app.py에서 분리된 공통 함수들

기존 gui_app.py의 24개 중복 safe_* 함수를 통합
"""

import sqlite3
from datetime import datetime
from typing import Any, Optional
import logging

# P5-7: 단일 소스 core.types (re-export 유지)
from core.types import safe_float, safe_str, safe_int  # noqa: F401 (re-export)

logger = logging.getLogger(__name__)


def safe_date(val: Any, default: str = '', output_format: str = '%Y-%m-%d') -> str:
    """안전한 날짜 변환 → 문자열 반환 (포맷 지정). 날짜 객체가 필요하면 helpers.safe_date_to_date 사용."""
    if val is None:
        return default
    
    if isinstance(val, datetime):
        return val.strftime(output_format)
    
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('none', 'nat', 'null', '-'):
        return default
    
    # 다양한 날짜 형식 시도
    date_formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%d.%m.%Y',
        '%d/%m/%Y',
        '%Y%m%d',
        '%Y-%m-%d %H:%M:%S',
    ]
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(val_str[:19], fmt)
            return parsed.strftime(output_format)
        except ValueError:
            continue
    
    # pandas Timestamp 처리
    try:
        import pandas as pd
        if pd.notna(val):
            ts = pd.to_datetime(val)
            return ts.strftime(output_format)
    except (ValueError, TypeError, KeyError) as _e:
        logger.debug(f"Suppressed: {_e}")
    
    return default


# 용도별 별칭 (DEBUGGING_RISK_OVERVIEW: safe_date 용도별 정리)
safe_date_str = safe_date  # 문자열 필요 시. 날짜 객체 필요 시 helpers.safe_date_to_date

# P1: format_number, format_weight_*, find_column 단일 소스
from .formatters import (  # noqa: F401
    find_column,
    format_number,
    format_weight,
    format_weight_kg,
    format_weight_mt,
)


# ─── v3.6.6: DB 쿼리 안전 유틸리티 ─────────────────

def safe_db_query(engine, query_fn, default=None, label="DB query"):
    """
    engine을 안전하게 사용하는 래퍼
    
    Usage:
        result = safe_db_query(self.engine, lambda e: e.get_all_inventory(), default=[])
    
    Args:
        engine: SQMInventoryEngine 인스턴스 (None 가능)
        query_fn: engine을 인자로 받는 callable
        default: 실패 시 반환할 기본값
        label: 에러 로깅용 라벨
    
    Returns:
        query_fn의 결과 또는 default
    """
    if engine is None:
        logger.warning(f"[{label}] engine이 None입니다")
        return default
    try:
        return query_fn(engine)
    except (ValueError, TypeError, AttributeError) as e:
        logger.error(f"[{label}] 오류: {e}")
        return default


def safe_cursor_query(engine, sql, params=(), fetchone=False, default=None, label="cursor query"):
    """
    cursor를 안전하게 생성/사용/정리하는 유틸리티
    
    Usage:
        rows = safe_cursor_query(self.engine, "SELECT * FROM inventory WHERE status=?", 
                                 params=('AVAILABLE',), default=[])
        count = safe_cursor_query(self.engine, "SELECT COUNT(*) FROM inventory",
                                  fetchone=True, default=0)
    """
    if engine is None:
        logger.warning(f"[{label}] engine이 None입니다")
        return default
    
    cursor = None
    try:
        conn = engine.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        
        if fetchone:
            row = cursor.fetchone()
            return (row[0] if row else default)
        else:
            return cursor.fetchall()
    except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
        logger.error(f"[{label}] 오류: {e}")
        return default
    finally:
        if cursor:
            try:
                cursor.close()
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                logger.debug(f"safe_utils: {_e}")
