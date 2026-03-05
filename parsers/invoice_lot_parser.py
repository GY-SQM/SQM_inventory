# -*- coding: utf-8 -*-
"""
SQM Phase A — Invoice (FA) LOT 파싱: N° LOTES 형식만 1회 추출, 24개 오차 없이.
PDF 텍스트에서 "LOT번호/중량T" 패턴만 사용하여 Ref.SQM 등 다른 10자리 숫자 포함 방지.
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# LOT 형식만: 10자리숫자 + / + 중량(숫자,유럽식) + T (예: 1126010240/5,001T)
WEIGHTED_RE = re.compile(r'\b(\d{10})\s*/\s*\d[\d\.,]*\s*T\b', re.IGNORECASE)
ANCHOR_RE = re.compile(r'(N\s*[°ºo]?\s*LOTES?\s*:?)', re.IGNORECASE)
STOP_RE = re.compile(
    r'\b(BL[-\s]*AWB|Ref\.?\s*SQM|Our\s+Order|NET\s+WEIGHT|GROSS\s+WEIGHT|TOTAL\s+AMOUNT|INCOTERM)\b',
    re.IGNORECASE
)
BLOCK_MAX = 2200


def extract_lots_from_text(text: str, sap_no: str = "") -> List[str]:
    """
    N° LOTES 블록에서 LOT번호/중량T 형식만 추출. 순서 유지, 중복 제거.
    """
    if not text or not text.strip():
        return []
    normalized = re.sub(r'[\r\n\t]+', ' ', text)
    normalized = re.sub(r'\s+', ' ', normalized)
    out: List[str] = []
    seen = set()
    sap_clean = str(sap_no or '').strip()

    for m in ANCHOR_RE.finditer(normalized):
        block = normalized[m.end(): m.end() + BLOCK_MAX]
        stop_m = STOP_RE.search(block)
        if stop_m:
            block = block[:stop_m.start()]
        for lot_no in WEIGHTED_RE.findall(block):
            lot_no = str(lot_no).strip()
            if not lot_no or lot_no == sap_clean or lot_no in seen:
                continue
            seen.add(lot_no)
            out.append(lot_no)
    return out


def order_lots_by_text(text: str, lot_numbers: List[str]) -> List[str]:
    """원문 등장 순서대로 재정렬."""
    if not text or not lot_numbers:
        return list(lot_numbers) if lot_numbers else []
    unique_order = list(dict.fromkeys(str(x).strip() for x in lot_numbers if str(x).strip()))
    indexed = []
    for idx, ln in enumerate(unique_order):
        pos = text.find(ln)
        indexed.append((pos if pos >= 0 else 10**9 + idx, idx, ln))
    indexed.sort(key=lambda x: (x[0], x[1]))
    return [x[2] for x in indexed]


def extract_lots_from_pdf(pdf_path: str, sap_no: str = "") -> List[str]:
    """
    PDF에서 텍스트 추출 후 N° LOTES 형식만 1회 추출. 24개 오차 없이.
    텍스트 추출 실패 시 빈 리스트 반환.
    """
    try:
        import fitz
        doc = fitz.open(pdf_path)
        try:
            chunks = [page.get_text("text") or "" for page in doc]
            text = "\n".join(chunks)
        finally:
            doc.close()
    except Exception as e:
        logger.debug(f"[invoice_lot_parser] PDF 텍스트 추출 실패: {e}")
        return []

    lots = extract_lots_from_text(text, sap_no=sap_no)
    if not lots:
        return []
    lots = list(dict.fromkeys(lots))
    ordered = order_lots_by_text(text, lots)
    if len(ordered) == len(lots):
        lots = ordered
    logger.info(f"[invoice_lot_parser] 원문 기준 1회 추출: {len(lots)}개 (N° LOTES 형식만)")
    return lots
