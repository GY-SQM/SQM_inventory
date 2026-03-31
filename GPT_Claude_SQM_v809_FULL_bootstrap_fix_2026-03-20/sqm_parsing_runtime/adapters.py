# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.adapters (v9.0 Phase4)
==========================================
도메인 Data 클래스를 ParserResult로 변환.

v9.0 Phase4 변경사항:
  - PackingListData, InvoiceData, BLData, DOData 모두 success 직접 필드 보유
  - getattr fallback은 하위 호환을 위해 유지
  - 이 모듈은 현재 운영 코드에서 직접 호출되지 않음 (예비용)
"""
import logging
from typing import Any
from sqm_parsing_runtime.parser_result import ParserResult

logger = logging.getLogger(__name__)


def adapt_packing_list(pl_result: Any) -> ParserResult:
    """PackingListData → ParserResult 변환.
    v9.0 Phase4: PackingListData에 success 직접 필드 추가됨.
    getattr fallback 유지 (하위 호환).
    """
    r = ParserResult(doc_type="PACKING_LIST")
    if pl_result is None:
        return r
    # v9.0 Phase4: PackingListData.success는 이제 직접 필드
    # (Phase2에서 bool 필드로 추가됨 — lots > 0 으로 packing_mixin에서 세팅)
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
    """InvoiceData → ParserResult 변환. v9.0 Phase4: success 직접 필드."""
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
    """BLData → ParserResult 변환. v9.0 Phase4: success 직접 필드."""
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
