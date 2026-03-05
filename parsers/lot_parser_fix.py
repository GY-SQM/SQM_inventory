# -*- coding: utf-8 -*-
"""
SQM Phase A — Invoice vs Packing List 24개 검증 및 정합성.
루비(기존) 인라인 로직 대신 단일 진입점으로 검증·보정.
"""
import logging
from typing import List, Any, Tuple

from .invoice_lot_parser import extract_lots_from_pdf, extract_lots_from_text, order_lots_by_text

logger = logging.getLogger(__name__)


def validate_invoice_pl_24(
    inv_lot_numbers: List[str],
    pl_lots: List[Any],
    expected_count: int = 24
) -> Tuple[bool, str, int, int]:
    """
    Invoice LOT 개수 vs PL lots 개수 검증.
    Returns (ok, message, inv_count, pl_count).
    """
    inv_list = [str(x).strip() for x in (inv_lot_numbers or []) if str(x).strip()]
    inv_count = len(inv_list)
    pl_count = len(pl_lots) if pl_lots else 0

    if inv_count != expected_count:
        return False, f"Invoice {inv_count}개 (기대: {expected_count}개)", inv_count, pl_count
    if pl_count != expected_count:
        return False, f"Packing List {pl_count}개 (기대: {expected_count}개)", inv_count, pl_count
    return True, f"Invoice/PL 각 {expected_count}개 일치", inv_count, pl_count


def reconcile_invoice_lots_from_pdf(
    pdf_path: str,
    sap_no: str,
    gemini_lot_numbers: List[str]
) -> List[str]:
    """
    PDF 텍스트 기준으로 Invoice LOT 확정. (Phase A — 루비 인라인 로직 대체)
    - 텍스트에서 N° LOTES 형식만 추출 가능하면 그걸 사용 (24개 오차 없이).
    - 불가하면 gemini_lot_numbers 사용, 중복 제거.
    """
    from .invoice_lot_parser import extract_lots_from_pdf
    if pdf_path:
        lots_from_pdf = extract_lots_from_pdf(pdf_path, sap_no=sap_no)
        if lots_from_pdf:
            return lots_from_pdf
    raw = [str(x).strip() for x in (gemini_lot_numbers or []) if str(x).strip()]
    return list(dict.fromkeys(raw))
