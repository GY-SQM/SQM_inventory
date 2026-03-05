# -*- coding: utf-8 -*-
"""
SQM Phase A — Packing List LOT 검증/정규화.
PL lots 개수·중복 검사, list_no 순서 정합성.
"""
import logging
from typing import List, Any, Tuple

logger = logging.getLogger(__name__)


def validate_pl_lots(lots: List[Any], expected_count: int = 24) -> Tuple[bool, str]:
    """
    PL lots 개수·중복 검증.
    Returns (ok, message).
    """
    if not lots:
        return False, "PL lots 비어 있음"
    n = len(lots)
    if expected_count and n != expected_count:
        return False, f"PL {n}개 (기대: {expected_count}개)"
    # 중복 lot_no 검사
    lot_nos = []
    for lot in lots:
        no = getattr(lot, "lot_no", None) or (lot.get("lot_no") if isinstance(lot, dict) else None)
        if no:
            lot_nos.append(str(no).strip())
    if len(lot_nos) != len(set(lot_nos)):
        return False, "PL 내 LOT 번호 중복 있음"
    return True, f"PL {n}개 검증 통과"


def normalize_pl_lots_dedup(lots: List[Any], fingerprint_fn=None) -> List[Any]:
    """
    fingerprint 기준 중복 제거 후 반환. list_no 재부여.
    fingerprint_fn(lot) -> str. None이면 lot_no만 사용.
    """
    if not fingerprint_fn:
        def fingerprint_fn(lot):
            return str(getattr(lot, "lot_no", "") or (lot.get("lot_no") if isinstance(lot, dict) else ""))
    seen = set()
    out = []
    for lot in lots:
        fp = fingerprint_fn(lot)
        if fp and fp in seen:
            continue
        if fp:
            seen.add(fp)
        out.append(lot)
    # list_no 재부여
    for idx, lot in enumerate(out, 1):
        if hasattr(lot, "list_no"):
            lot.list_no = idx
        elif isinstance(lot, dict):
            lot["list_no"] = idx
    return out
