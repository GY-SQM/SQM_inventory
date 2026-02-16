# -*- coding: utf-8 -*-
"""
SQM Inventory - Helper Functions
================================

v2.9.91 - Common utility functions

Date parsing, format conversion, file operations
"""

import os
import re
import logging
from datetime import date, datetime
from typing import Optional, List, Any
from utils.common import normalize_column_name, safe_float, safe_str, safe_int  # noqa: F401 (re-export)

logger = logging.getLogger(__name__)


def safe_date(value: Any, default: Optional[date] = None) -> Optional[date]:
    """
    Safe date conversion → date 객체 반환. 문자열(포맷)이 필요하면 safe_utils.safe_date 또는 safe_date_str 사용.

    Supports formats:
    - datetime object
    - date object
    - "YYYY-MM-DD"
    - "YYYYMMDD"
    - "DD/MM/YYYY"
    - "MM/DD/YYYY"
    
    Args:
        value: Value to convert
        default: Default if conversion fails
        
    Returns:
        Date object or default
    """
    if value is None:
        return default or date.today()
    
    if isinstance(value, datetime):
        return value.date()
    
    if isinstance(value, date):
        return value
    
    if hasattr(value, 'date'):  # pandas Timestamp
        return value.date()
    
    # String parsing
    value_str = str(value).strip()
    
    # Try common formats
    formats = [
        '%Y-%m-%d',
        '%Y%m%d',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%Y.%m.%d',
        '%d.%m.%Y',
        '%Y/%m/%d',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(value_str, fmt).date()
        except ValueError:
            continue
    
    return default or date.today()


# 용도별 별칭 (DEBUGGING_RISK_OVERVIEW: safe_date 용도별 정리)
safe_date_to_date = safe_date  # 날짜 객체 필요 시. 문자열 필요 시 safe_utils.safe_date_str


def format_weight(weight_kg: float, unit: str = 'MT') -> str:
    """
    Format weight value
    
    Args:
        weight_kg: Weight in kg
        unit: Output unit ('MT', 'kg', 'auto')
        
    Returns:
        Formatted string
    """
    if unit == 'MT':
        return f"{weight_kg / 1000:.3f} MT"
    elif unit == 'kg':
        return f"{weight_kg:,.0f} kg"
    else:  # auto
        if weight_kg >= 1000:
            return f"{weight_kg / 1000:.3f} MT"
        else:
            return f"{weight_kg:.1f} kg"


def format_number(value: float, decimals: int = 0) -> str:
    """
    Format number with thousands separator
    
    Args:
        value: Number to format
        decimals: Decimal places
        
    Returns:
        Formatted string
    """
    if decimals > 0:
        return f"{value:,.{decimals}f}"
    else:
        return f"{value:,.0f}"


def validate_lot_no(lot_no: str) -> bool:
    """
    Validate LOT number format
    
    Format: 10 digits (YYMMDDXXXX)
    
    Args:
        lot_no: LOT number to validate
        
    Returns:
        True if valid
    """
    if not lot_no:
        return False
    
    lot_no = str(lot_no).strip()
    
    # Must be 10 digits
    if not re.match(r'^\d{10}$', lot_no):
        return False
    
    return True


def validate_sap_no(sap_no: str) -> bool:
    """
    Validate SAP number format
    
    Format: Starts with 45, 10 digits total
    
    Args:
        sap_no: SAP number to validate
        
    Returns:
        True if valid
    """
    if not sap_no:
        return False
    
    sap_no = str(sap_no).strip()
    
    # Must be 10 digits starting with 45
    if not re.match(r'^45\d{8}$', sap_no):
        return False
    
    return True


def find_column(df_columns: List[str], candidates: List[str]) -> Optional[str]:
    """
    Find matching column name from candidates
    
    Args:
        df_columns: DataFrame column names
        candidates: Possible column names to match
        
    Returns:
        Matching column name or None
    """
    # Normalize DataFrame columns
    norm_columns = {normalize_column_name(c): c for c in df_columns}
    
    # Try each candidate
    for candidate in candidates:
        norm_candidate = normalize_column_name(candidate)
        if norm_candidate in norm_columns:
            return norm_columns[norm_candidate]
    
    return None


def get_file_extension(file_path: str) -> str:
    """
    Get file extension (lowercase, without dot)
    
    Args:
        file_path: File path
        
    Returns:
        Extension (e.g., 'xlsx', 'pdf')
    """
    if not file_path:
        return ""
    
    _, ext = os.path.splitext(file_path)
    return ext.lower().lstrip('.')


def ensure_directory(dir_path: str) -> bool:
    """
    Ensure directory exists
    
    Args:
        dir_path: Directory path
        
    Returns:
        True if directory exists or was created
    """
    if not dir_path:
        return False
    
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except OSError as e:
        logger.error(f"Failed to create directory {dir_path}: {e}")
        return False


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate string to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if not text:
        return ""
    
    text = str(text)
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def clean_lot_no(value: Any) -> str:
    """
    Clean and normalize LOT number
    
    Handles:
    - Float values (removes .0)
    - String with decimals
    - Leading/trailing whitespace
    
    Args:
        value: Raw LOT value
        
    Returns:
        Cleaned LOT number string
    """
    if value is None:
        return ""
    
    # Handle numeric types
    if isinstance(value, (int, float)):
        return str(int(value))
    
    # Handle strings
    value_str = str(value).strip()
    
    # Remove decimal part if present
    if '.' in value_str:
        value_str = value_str.split('.')[0]
    
    return value_str


def parse_weight_string(value: str) -> float:
    """
    Parse weight from string
    
    Handles:
    - "1,234.56"
    - "1234.56 kg"
    - "1.234 MT"
    
    Args:
        value: Weight string
        
    Returns:
        Weight in kg
    """
    if not value:
        return 0.0
    
    value_str = str(value).strip().upper()
    
    # Check for MT unit
    is_mt = 'MT' in value_str
    
    # Remove non-numeric characters except . and ,
    cleaned = re.sub(r'[^\d.,]', '', value_str)
    
    # Handle comma as thousands separator
    if ',' in cleaned and '.' in cleaned:
        # Assume format: 1,234.56
        cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        # Assume format: 1234,56 (European)
        cleaned = cleaned.replace(',', '.')
    
    try:
        weight = float(cleaned)
        if is_mt:
            weight *= 1000  # Convert to kg
        return weight
    except ValueError:
        return 0.0
