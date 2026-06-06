"""
SQM 공통 입력값 검증 헬퍼 (Phase 2-3)
API 경계에서 잘못된 값을 명확한 메시지로 차단.
"""
from datetime import datetime, timedelta
from typing import Any


def validate_lot_no(lot_no: Any) -> list[str]:
    errors = []
    v = (lot_no or "").strip()
    if not v:
        errors.append("LOT 번호는 필수입니다.")
    elif len(v) > 50:
        errors.append(f"LOT 번호가 너무 깁니다 (최대 50자): {v[:20]}…")
    return errors


def validate_quantity(qty: Any, field: str = "수량") -> list[str]:
    errors = []
    try:
        v = float(qty)
        if v < 0:
            errors.append(f"{field}은 음수일 수 없습니다: {v}")
        if v > 9_999_999:
            errors.append(f"{field}이 비정상적으로 큽니다: {v}")
    except (TypeError, ValueError):
        errors.append(f"{field} 값이 숫자가 아닙니다: {qty!r}")
    return errors


def validate_date(date_str: Any, field: str = "날짜",
                  allow_future_days: int = 1) -> list[str]:
    """날짜 문자열 검증. allow_future_days=1이면 오늘+1일까지 허용."""
    errors = []
    if not date_str:
        return errors   # 빈 날짜는 호출자가 필수 여부 판단
    s = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            d = datetime.strptime(s, fmt)
            limit = datetime.now() + timedelta(days=allow_future_days)
            if d > limit:
                errors.append(
                    f"{field}이 너무 미래입니다 ({s}). "
                    f"최대 {allow_future_days}일 후까지만 허용됩니다."
                )
            if d.year < 2000:
                errors.append(f"{field}이 너무 과거입니다 ({s}).")
            return errors
        except ValueError:
            continue
    errors.append(f"{field} 형식이 올바르지 않습니다 (YYYY-MM-DD): {s!r}")
    return errors


def validate_weight(weight: Any, field: str = "중량(kg)") -> list[str]:
    errors = []
    if weight is None:
        return errors
    try:
        v = float(weight)
        if v < 0:
            errors.append(f"{field}은 음수일 수 없습니다: {v}")
        if v > 100_000_000:
            errors.append(f"{field}이 비정상적으로 큽니다: {v}")
    except (TypeError, ValueError):
        errors.append(f"{field} 값이 숫자가 아닙니다: {weight!r}")
    return errors


def collect_errors(*error_lists) -> list[str]:
    """여러 검증 결과를 하나의 리스트로 합침."""
    result = []
    for lst in error_lists:
        result.extend(lst)
    return result
