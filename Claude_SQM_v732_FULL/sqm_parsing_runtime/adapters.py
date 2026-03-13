# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.adapters — stub (v7.0.0)
============================================
레거시 파서 결과를 ParserResult / DocumentSession으로 변환.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from .parser_result import ParserResult
from .session_manager import DocumentSession, SessionManager

_default_mgr = SessionManager()


def adapt_bl_result(legacy_result: Dict[str, Any]) -> ParserResult:
    """레거시 BL 파싱 결과 → ParserResult"""
    r = ParserResult(doc_type='BL')
    r.lot_no = str(legacy_result.get('lot_no') or '')
    r.bl_no = str(legacy_result.get('bl_no') or legacy_result.get('BL_NO') or '')
    r.vessel = str(legacy_result.get('vessel') or legacy_result.get('VESSEL') or '')
    r.port_of_loading = str(legacy_result.get('pol') or '')
    r.port_of_discharge = str(legacy_result.get('pod') or '')
    r.raw_text = str(legacy_result.get('raw_text') or '')
    r.parse_success = bool(legacy_result.get('success', True))
    return r


def adapt_pl_result(legacy_result: Dict[str, Any]) -> ParserResult:
    """레거시 PL 파싱 결과 → ParserResult"""
    r = ParserResult(doc_type='PACKING_LIST')
    r.lot_no = str(legacy_result.get('lot_no') or '')
    r.items = legacy_result.get('items') or legacy_result.get('rows') or []
    r.raw_text = str(legacy_result.get('raw_text') or '')
    r.parse_success = bool(legacy_result.get('success', True))
    return r


def adapt_fa_result(legacy_result: Dict[str, Any]) -> ParserResult:
    """레거시 Invoice(FA) 파싱 결과 → ParserResult"""
    r = ParserResult(doc_type='INVOICE')
    r.lot_no = str(legacy_result.get('lot_no') or '')
    r.bl_no = str(legacy_result.get('bl_no') or '')
    r.items = legacy_result.get('items') or []
    r.raw_text = str(legacy_result.get('raw_text') or '')
    r.parse_success = bool(legacy_result.get('success', True))
    return r


def build_session_from_legacy(
    bl_data: Optional[Dict] = None,
    pl_data: Optional[Dict] = None,
    fa_data: Optional[Dict] = None,
    lot_no: str = "",
) -> DocumentSession:
    """레거시 파싱 결과 dict들로 DocumentSession 생성"""
    session = _default_mgr.create_session(lot_no=lot_no)
    if bl_data:
        session.add_document('BL', adapt_bl_result(bl_data))
    if pl_data:
        session.add_document('PACKING_LIST', adapt_pl_result(pl_data))
    if fa_data:
        session.add_document('INVOICE', adapt_fa_result(fa_data))
    return session
