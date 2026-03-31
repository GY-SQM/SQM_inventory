# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.adapters (v7.7.0)
=====================================
레거시 파서 결과를 ParserResult로 변환.
"""
import logging
from typing import Any
from sqm_parsing_runtime.parser_result import ParserResult

logger = logging.getLogger(__name__)


def adapt_packing_list(pl_result: Any) -> ParserResult:
    """PackingListResult → ParserResult 변환."""
    r = ParserResult(doc_type="PACKING_LIST")
    if pl_result is None:
        return r
    r.success = getattr(pl_result, "success", False)
    r.raw_response = getattr(pl_result, "raw_response", "")
    r.data = {
        "lots": getattr(pl_result, "lots", []),
        "total_net_weight_kg": getattr(pl_result, "total_net_weight_kg", 0),
        "total_gross_weight_kg": getattr(pl_result, "total_gross_weight_kg", 0),
        "product": getattr(pl_result, "product", ""),
        "folio": getattr(pl_result, "folio", ""),
    }
    return r


def adapt_invoice(inv_result: Any) -> ParserResult:
    """InvoiceResult → ParserResult 변환."""
    r = ParserResult(doc_type="INVOICE")
    if inv_result is None:
        return r
    r.success = getattr(inv_result, "success", False)
    r.data = {
        "sap_no": getattr(inv_result, "sap_no", ""),
        "salar_invoice_no": getattr(inv_result, "salar_invoice_no", ""),
        "lot_numbers": getattr(inv_result, "lot_numbers", []),
    }
    return r


def adapt_bl(bl_result: Any) -> ParserResult:
    """BLResult → ParserResult 변환."""
    r = ParserResult(doc_type="BL")
    if bl_result is None:
        return r
    r.success = getattr(bl_result, "success", False)
    r.carrier_id = getattr(bl_result, "carrier_id", "")
    r.data = {
        "bl_no": getattr(bl_result, "bl_no", ""),
        "ship_date": getattr(bl_result, "ship_date", ""),
        "vessel": getattr(bl_result, "vessel", ""),
    }
    return r


def adapt_bl_result(bl_result) -> 'ParserResult':
    """adapt_bl 별칭 (하위호환)."""
    return adapt_bl(bl_result)


def adapt_pl_result(pl_result) -> 'ParserResult':
    """adapt_packing_list 별칭 (하위호환)."""
    return adapt_packing_list(pl_result)


def adapt_fa_result(inv_result) -> 'ParserResult':
    """adapt_invoice 별칭 (FA = Invoice, 하위호환)."""
    return adapt_invoice(inv_result)


def build_session_from_legacy(bl=None, pl=None, fa=None, do=None):
    """레거시 파서 결과 4종 → DocumentSession 조립."""
    from sqm_parsing_runtime.session_manager import SessionManager
    bl_no = getattr(bl, 'bl_no', '') if bl else ''
    sap_no = getattr(fa, 'sap_no', '') if fa else ''
    mgr = SessionManager()
    session = mgr.create_session(bl_no=bl_no, sap_no=sap_no)
    if bl:  session.add_document('BL', adapt_bl(bl))
    if pl:  session.add_document('PACKING_LIST', adapt_packing_list(pl))
    if fa:  session.add_document('INVOICE', adapt_invoice(fa))
    return session
