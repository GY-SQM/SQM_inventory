# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - Invoice 파서 Mixin
=========================================

v9.0: Gemini API 완전 제거 — PyMuPDF 좌표 기반 파싱으로 전환

고객사(SQM SALAR SpA)가 단일이므로 양식이 항상 동일
→ 각 필드의 고정 좌표로 직접 추출 (API 비용 없음, 속도 빠름)

추출 항목:
    - Invoice No:   우상단 N° 번호
    - Date:         FECHA/DATE 오른쪽
    - SAP No:       Ref.SQM/Our Order 오른쪽
    - BL No:        BL-AWB-CRT Number 아래 + vessel로 선사코드 추론
    - Vessel:       Transporte/Transport 오른쪽
    - Origin:       Origen/Origin 오른쪽
    - Destination:  Destino/Destination 오른쪽
    - Quantity MT:  Cantidad 컬럼 숫자
    - Product Code: 제품코드 컬럼
    - Product Name: 제품명 컬럼
    - Unit Price:   Precio Unit 컬럼
    - Total Amount: Valor Total 컬럼
    - Net Weight:   KG Netos 오른쪽
    - Gross Weight: KG Bruto 오른쪽
    - LOT 목록:     N° LOTES: 다음 텍스트

작성자: Ruby (남기동)
버전: v9.0
"""

import logging
import re
from datetime import datetime
from typing import Optional, List

from core.types import safe_float
from ..document_models import InvoiceData

logger = logging.getLogger(__name__)
# ── SQM SALAR SpA 고정 상수 (고객 단일, 제품 단일) ──────────
_CUSTOMER_NAME  = "SOQUIMICH LLC"
_PRODUCT_NAME   = "LITHIUM CARBONATE - BATTERY GRADE - MICRONIZED"
_PRODUCT_CODE   = "MIC9000.00"
_CURRENCY       = "USD"
_SUPPLIER_NAME  = "SQM SALAR SpA"



# ── 선사명 → SCAC 코드 매핑 ────────────────────────────────
_VESSEL_TO_SCAC = {
    'MAERSK': 'MAEU',
    'MSC':    'MEDU',
    'COSCO':  'COSU',
    'CMA CGM':'CMDU',
    'HAPAG':  'HLCU',
    'HMM':    'HDMU',
    'ONE':    'ONEY',
    'EVERGREEN': 'EGLV',
    'YANG MING': 'YMLU',
    'PIL':    'PILU',
}


def _get_scac_from_vessel(vessel: str) -> str:
    """vessel 문자열에서 선사 SCAC 코드 추론."""
    if not vessel:
        return ''
    v = vessel.upper()
    for kw, scac in _VESSEL_TO_SCAC.items():
        if kw in v:
            return scac
    return ''


def _parse_euro_number(s: str) -> float:
    """유럽식 숫자 파싱: 1.573.034,54 → 1573034.54"""
    s = re.sub(r'[^\d,.]', '', str(s or ''))
    if not s:
        return 0.0
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


class InvoiceMixin:
    """Invoice 파서 Mixin — v9.0 좌표 기반 완전 독립 파서."""

    def parse_invoice(self, pdf_path: str, **kwargs) -> Optional[InvoiceData]:
        """SQM SALAR SpA Invoice(FA) 좌표 기반 파싱.

        Gemini API 완전 제거. PyMuPDF로 PDF 좌표 직접 추출.
        고객사 단일(SQM SALAR SpA) → 양식 고정 → 좌표 고정.
        """
        logger.info(f"[INVOICE] 좌표 기반 파싱 시작: {pdf_path}")
        try:
            import fitz
            doc  = fitz.open(pdf_path)
            page = doc[0]
            W    = page.rect.width
            H    = page.rect.height
            words_raw = page.get_text("words")
            # 전체 텍스트 (LOT 파싱용)
            full_text = page.get_text("text") or ""
            doc.close()
        except Exception as e:
            raise RuntimeError(f"[INVOICE] PDF 읽기 실패: {e}")

        words = [
            {'text': w[4], 'x0': float(w[0]), 'x1': float(w[2]),
             'top': float(w[1]), 'bottom': float(w[3])}
            for w in words_raw
        ]

        def by_xy(x1, x2, y1, y2) -> str:
            hits = sorted(
                [w for w in words
                 if x1 <= w['x0']/W*100 <= x2
                 and y1 <= w['top']/H*100 <= y2],
                key=lambda x: x['x0']
            )
            return ' '.join(w['text'] for w in hits)

        def label_right(label_text: str, y_tol: float = 3.0) -> str:
            """라벨 단어 찾기 → 같은 줄 오른쪽 값 반환"""
            label_up = label_text.upper()
            for w in words:
                line = ' '.join(
                    ww['text'] for ww in words
                    if abs(ww['top'] - w['top']) < y_tol
                ).upper()
                if label_up in line and w['x0']/W*100 > 50:
                    same_row = sorted(
                        [ww for ww in words
                         if abs(ww['top'] - w['top']) < y_tol
                         and ww['x0'] > w['x1']],
                        key=lambda x: x['x0']
                    )
                    return ' '.join(ww['text'] for ww in same_row)
            return ''

        # ── 필드 추출 ────────────────────────────────────────────

        # Invoice No: 우상단 N° 옆 숫자
        invoice_no = re.sub(r'[^\d]', '',
                             by_xy(74, 95, 11, 13))

        # Date: FECHA/DATE 오른쪽
        date_raw = re.sub(r'^[:\s]+', '',
                          by_xy(77, 95, 21, 23)).strip()
        # "31.01.2026" → "2026-01-31"
        invoice_date = ''
        dm = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_raw)
        if dm:
            invoice_date = f"{dm.group(3)}-{dm.group(2).zfill(2)}-{dm.group(1).zfill(2)}"

        # SAP No: Ref.SQM/Our Order 오른쪽
        sap_raw = by_xy(78, 95, 33, 35)
        sap_no  = re.sub(r'[^\d]', '', sap_raw)[:10]

        # Vessel: Transporte/Transport 오른쪽 (y=44.7%)
        vessel = by_xy(53, 73, 44, 46)

        # BL No: BL-AWB-CRT 아래 숫자 + 선사코드 접두사
        bl_num_raw = by_xy(79, 92, 44, 46)
        bl_digits  = re.sub(r'[^\d]', '', bl_num_raw)
        scac       = _get_scac_from_vessel(vessel)
        bl_no      = (scac + bl_digits) if (scac and bl_digits) else bl_digits

        # Origin / Destination
        origin      = by_xy(53, 73, 40, 42)
        destination = by_xy(74, 95, 40, 42)

        # Incoterm
        incoterm = by_xy(5, 15, 42, 44)

        # Quantity MT: 좌측 숫자 (y≈49%)
        qty_raw = by_xy(13, 21, 49, 51)
        quantity_mt = _parse_euro_number(qty_raw)

        # Product Code: x=27%
        prod_code = _PRODUCT_CODE  # v9.1: 고정 상수

        # Product Name: x=38~52%, y=49~52%
        # v9.1: 제품명/제품코드는 고정 상수 (SQM SALAR SpA 단일 제품)
        prod_name = _PRODUCT_NAME

        # Unit Price: x=68~78%
        unit_price = _parse_euro_number(by_xy(68, 78, 49, 51))

        # Total Amount: x=84~95%
        total_amount = _parse_euro_number(by_xy(84, 95, 49, 51))

        # Net Weight: "80.016KG" 파싱
        nw_raw   = by_xy(60, 73, 69, 71)
        nw_clean = re.sub(r'KG[^\d]*', '', nw_raw, flags=re.I)
        net_weight_kg = _parse_euro_number(nw_clean) * 1000 \
                        if _parse_euro_number(nw_clean) < 1000 \
                        else _parse_euro_number(nw_clean)

        # Gross Weight: x=88~95%
        gw_raw         = by_xy(88, 96, 69, 71)
        gross_weight_kg = _parse_euro_number(gw_raw) * 1000 \
                          if _parse_euro_number(gw_raw) < 1000 \
                          else _parse_euro_number(gw_raw)

        # Package Count
        pkg_raw   = by_xy(62, 67, 71, 73)
        try:
            package_count = int(float(re.sub(r'[^\d]', '', pkg_raw) or '0'))
        except (ValueError, TypeError):
            package_count = 0

        # Package Type
        package_type = by_xy(80, 96, 71, 74)

        # LOT 목록: N° LOTES: 다음 텍스트 파싱
        lot_numbers: List[str] = []
        lot_section = re.search(
            r'N[°o]?\s*LOTES\s*:(.*?)(?=Monto|Banco|$)',
            full_text, re.DOTALL | re.IGNORECASE
        )
        if lot_section:
            lot_text = lot_section.group(1)
            lot_numbers = re.findall(r'(\d{10})/[\d,.]+T?', lot_text)

        # ── 결과 조립 ────────────────────────────────────────────
        result = InvoiceData()
        result.source_file      = pdf_path
        result.parsed_at        = datetime.now()
        result.customer_name  = _CUSTOMER_NAME
        if hasattr(result, "supplier"):
            result.supplier = _SUPPLIER_NAME
        result.invoice_no       = invoice_no
        result.salar_invoice_no = invoice_no
        result.invoice_date     = invoice_date
        result.sap_no           = sap_no
        result.bl_no            = bl_no
        result.vessel           = vessel
        result.origin           = origin
        result.destination      = destination
        result.incoterm         = incoterm
        result.product_code     = prod_code
        result.product_name     = prod_name
        result.quantity_mt      = quantity_mt
        result.unit_price       = unit_price
        result.total_amount     = total_amount
        result.currency         = 'USD'
        result.net_weight_kg    = net_weight_kg
        result.gross_weight_kg  = gross_weight_kg
        result.package_count    = package_count
        result.package_type     = package_type
        result.lot_numbers      = lot_numbers
        result.success          = bool(sap_no and invoice_no)
        result.error_message    = ''
        result.raw_response     = ''

        logger.info(
            f"[INVOICE] 좌표 파싱 완료: inv={invoice_no} sap={sap_no} "
            f"bl={bl_no} lots={len(lot_numbers)}개"
        )
        return result
