# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - Invoice 파서 Mixin
=========================================

v3.6.0: document_parser_v2.py에서 분리

모듈 개요:
    Invoice(FA, 상업송장) PDF를 파싱합니다.
    
추출 항목:
    - SAP NO: Ref.SQM/Our Order
    - Invoice No: N° 16130
    - Invoice Date: FECHA/DATE
    - B/L No: BL-AWB-CRT Number
    - 제품 정보, 수량, 금액
    - LOT 목록: N° LOTES

작성자: Ruby (남기동)
버전: v3.6.0
"""

import os
import re
import logging
from datetime import datetime, date
from typing import Optional, List

from ..document_models import InvoiceData
from core.types import safe_float

logger = logging.getLogger(__name__)


class InvoiceMixin:
    """
    Invoice 파서 Mixin
    
    상업송장 PDF에서 SAP NO, LOT 목록, 금액 등을 추출합니다.
    
    Example:
        >>> class MyParser(InvoiceMixin, DocumentParserBase):
        ...     pass
        >>> parser = MyParser()
        >>> invoice = parser.parse_invoice('invoice.pdf')
    """
    
    def parse_invoice(self, pdf_path: str) -> Optional[InvoiceData]:
        """
        Invoice PDF 파싱 (API-Only)

        정책(v5.5.1): **모든 파싱은 Gemini API를 강제**합니다.
        - API Key 미설정: 하드-스톱(예외)
        - 파싱 실패: 정규식/로컬 폴백 없음(예외)

        Args:
            pdf_path: Invoice PDF 파일 경로

        Returns:
            InvoiceData: 파싱 결과
        """
        # API-Only Gate
        self._require_gemini_api_key()

        logger.info(f"[INVOICE] Gemini API(강제)로 파싱: {pdf_path}")
        from features.ai.gemini_parser import GeminiDocumentParser

        gemini_parser = GeminiDocumentParser(self.gemini_api_key)
        gemini_result = None
        try:
            gemini_result = self._gemini_with_retry(
                gemini_parser.parse_invoice,
                pdf_path,
                retries=3,
                wait_seconds=1.0,
            )
        except (ValueError, TypeError, KeyError, IndexError) as gemini_err:
            logger.warning(f"[INVOICE] Gemini 실패, OpenAI 폴백 시도: {gemini_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False):
            try:
                from core.config import OPENAI_API_KEY, DISABLE_OPENAI_FALLBACK
                if DISABLE_OPENAI_FALLBACK:
                    logger.info("[INVOICE] OpenAI 폴백 비활성(설정) — Gemini만 사용")
                elif not OPENAI_API_KEY or not OPENAI_API_KEY.strip():
                    logger.info("[INVOICE] OpenAI 폴백 생략: OPENAI_API_KEY 미설정 (환경변수 또는 settings.ini [OpenAI] api_key)")
                else:
                    from features.ai.openai_parser import try_parse_invoice
                    openai_result = try_parse_invoice(pdf_path)
                    if openai_result and getattr(openai_result, 'success', False):
                        gemini_result = openai_result
                        logger.info("[INVOICE] OpenAI 폴백으로 파싱 성공")
                    elif openai_result is None:
                        logger.info("[INVOICE] OpenAI 폴백 실패 또는 openai 패키지 미설치(pip install openai)")
            except (ValueError, TypeError, KeyError, IndexError) as fallback_err:
                logger.warning(f"[INVOICE] OpenAI 폴백 시도 중 오류: {fallback_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False):
            msg = getattr(gemini_result, 'error_message', '') if gemini_result else ''
            raise RuntimeError(f"[INVOICE] Gemini 파싱 실패(API-Only). {msg}".strip())

        result = InvoiceData()
        result.source_file = pdf_path
        result.parsed_at = datetime.now()

        # Gemini 결과 매핑
        # InvoiceData.customer는 읽기전용 프로퍼티(customer_name 반환) → customer_name에 설정
        result.sap_no = getattr(gemini_result, 'sap_no', '') or ''
        result.invoice_no = getattr(gemini_result, 'invoice_no', '') or ''
        result.salar_invoice_no = result.invoice_no
        result.bl_no = getattr(gemini_result, 'bl_no', '') or ''
        result.customer_name = getattr(gemini_result, 'customer', '') or ''
        result.product_code = getattr(gemini_result, 'product_code', '') or ''
        result.product_name = getattr(gemini_result, 'product', '') or ''
        result.quantity_mt = safe_float(getattr(gemini_result, 'quantity_mt', 0))
        result.unit_price = safe_float(getattr(gemini_result, 'unit_price', 0))
        result.total_amount = safe_float(getattr(gemini_result, 'total_amount', 0))
        result.currency = (getattr(gemini_result, 'currency', 'USD') or 'USD')
        result.incoterm = getattr(gemini_result, 'incoterm', '') or ''
        result.origin = getattr(gemini_result, 'origin', '') or ''
        result.destination = getattr(gemini_result, 'destination', '') or ''
        result.vessel = getattr(gemini_result, 'vessel', '') or ''
        result.net_weight_kg = safe_float(getattr(gemini_result, 'net_weight_kg', 0))
        result.gross_weight_kg = safe_float(getattr(gemini_result, 'gross_weight_kg', 0))
        result.package_type = getattr(gemini_result, 'package_type', '') or ''
        try:
            result.package_count = int(safe_float(getattr(gemini_result, 'package_count', 0)))
        except (ValueError, TypeError):
            result.package_count = 0
        if hasattr(result, 'supplier'):
            result.supplier = getattr(gemini_result, 'supplier', '') or ''

        # LOT 목록 (Gemini: lots / OpenAI: lot_numbers)
        lots = getattr(gemini_result, 'lots', []) or getattr(gemini_result, 'lot_numbers', []) or []
        result.lot_numbers = [str(x).strip() for x in lots if str(x).strip()]

        return result
