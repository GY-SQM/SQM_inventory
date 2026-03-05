# -*- coding: utf-8 -*-
"""
SQM v6.0.0 — Picking List PDF 파서
=====================================

SQM(SOQUIMICH LLC.)이 발행하는 Picking List PDF 전용 파서.

파싱 전략:
    1순위: pdfplumber 텍스트 추출 (빠르고 정확)
    2순위: Gemini OCR 폴백 (스캔 PDF 등 텍스트 추출 실패 시)

추출 데이터:
    헤더: Outbound ID, Sales order, Customer reference(Picking No),
          Invoice account(고객), Creation Date, Plan Loading Date
    라인: Batch number(lot_no), Quantity, Unit(MT/KG), Storage location
          → MT = 일반 톤백 (500kg/bag × N bag)
          → KG with qty=1.0 = 샘플 톤백

사용 예:
    parser = PickingListParser()
    result = parser.parse("/path/to/picking_list.pdf")
    # result["items"] → [{"lot_no": "1125072340", "qty_kg": 5000.0, ...}, ...]
"""

import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# 정규식 패턴 (Picking List PDF 전용)
# ─────────────────────────────────────────

# 헤더 패턴
_RE_OUTBOUND_ID   = re.compile(r"Outbound\s+ID[\s:]+(\d+)", re.IGNORECASE)
_RE_SALES_ORDER   = re.compile(r"Sales\s+order[\s:]+(\d+)", re.IGNORECASE)
_RE_CUSTOMER_REF  = re.compile(r"Customer\s+reference[\s:]+([\w\-]+)", re.IGNORECASE)
_RE_INVOICE_ACCT  = re.compile(r"Invoice\s+account\s+(.+?)(?:\n|Enterprise)", re.IGNORECASE | re.DOTALL)
_RE_CREATION_DATE = re.compile(r"Creation\s+Date[\s:]+([\d]{1,2}[\.\-/][\d]{1,2}[\.\-/][\d]{2,4})", re.IGNORECASE)
_RE_PLAN_LOADING  = re.compile(r"Plan\s+Loading\s+Date[\s:]+([\d]{1,2}[\.\-/][\d]{1,2}[\.\-/][\d]{2,4})", re.IGNORECASE)

# 톤백 라인 패턴
# 예) "Quantity: 5.00 MT  Batch number: 1125072340  Storage location: 1001 GY logistics"
# 예) "Quantity: 1.00 KG  Batch number: 1125072340  Storage location: 1001 GY logistics"
_RE_TONBAG_LINE = re.compile(
    r"Quantity:\s*([\d.]+)\s*(MT|KG)\s+"
    r"Batch\s+number:\s*(\d{10,})\s+"
    r"Storage\s+location:\s*(.+?)(?:\s*$)",
    re.IGNORECASE | re.MULTILINE
)


def _parse_date(raw: str) -> Optional[str]:
    """
    날짜 문자열 → YYYY-MM-DD 변환
    지원 형식: 15.01.2026 / 2026-01-15 / 15/01/2026
    """
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw  # 파싱 실패 시 원본 반환


class PickingListParser:
    """
    Picking List PDF → 구조화된 dict 반환

    반환 구조:
    {
        "outbound_id"      : "80007418",
        "sales_order_no"   : "3073",
        "picking_no"       : "LBM-LC20250901",   # Customer reference
        "customer"         : "LBM NEW ENERGY (AP) PTE LTD",
        "creation_date"    : "2026-01-15",
        "plan_loading_date": "2026-01-29",
        "source_file"      : "LBM_AP_SO_3073_Picking_list.pdf",
        "items": [
            {
                "lot_no"          : "1125072340",
                "qty_mt"          : 5.0,
                "qty_kg"          : 5000.0,
                "unit"            : "MT",
                "is_sample"       : False,
                "storage_location": "1001 GY logistics"
            },
            ...
        ],
        "total_normal_mt"  : 305.0,
        "total_sample_kg"  : 61.0,
        "total_lots"       : 61,
        "parse_method"     : "pdfplumber",   # or "gemini"
        "parse_ok"         : True,
        "warnings"         : []
    }
    """

    def parse(self, pdf_path: str) -> dict:
        """
        PDF 파일 파싱 메인 진입점
        pdfplumber 우선 → 실패 시 Gemini 폴백
        """
        import os
        source_file = os.path.basename(pdf_path)
        result = self._empty_result(source_file)

        # ── 1순위: pdfplumber ──
        try:
            text = self._extract_text_pdfplumber(pdf_path)
            if text and len(text.strip()) > 100:
                self._parse_text(text, result)
                result["parse_method"] = "pdfplumber"
                logger.info(
                    f"[PickingListParser] pdfplumber 파싱 완료: "
                    f"LOT {result['total_lots']}개 / "
                    f"일반 {result['total_normal_mt']}MT / "
                    f"샘플 {result['total_sample_kg']}KG"
                )
                if result["total_lots"] > 0:
                    result["parse_ok"] = True
                    return result
                else:
                    result["warnings"].append(
                        "pdfplumber: 텍스트 추출 성공했으나 Batch number 0건 → Gemini 폴백"
                    )
            else:
                result["warnings"].append("pdfplumber: 텍스트 추출 실패 → Gemini 폴백")
        except Exception as e:
            logger.warning(f"[PickingListParser] pdfplumber 오류: {e} → Gemini 폴백")
            result["warnings"].append(f"pdfplumber 오류: {e}")

        # ── 2순위: Gemini OCR 폴백 ──
        try:
            text = self._extract_text_gemini(pdf_path)
            if text:
                result2 = self._empty_result(source_file)
                self._parse_text(text, result2)
                result2["parse_method"] = "gemini"
                result2["warnings"] = result["warnings"]
                if result2["total_lots"] > 0:
                    result2["parse_ok"] = True
                    logger.info(
                        f"[PickingListParser] Gemini 폴백 성공: "
                        f"LOT {result2['total_lots']}개"
                    )
                    return result2
                else:
                    result2["warnings"].append("Gemini: Batch number 0건 파싱 실패")
                    return result2
        except Exception as e:
            logger.error(f"[PickingListParser] Gemini 폴백 오류: {e}")
            result["warnings"].append(f"Gemini 오류: {e}")

        result["parse_ok"] = False
        return result

    # ─────────────────────────────────────
    # pdfplumber 텍스트 추출
    # ─────────────────────────────────────
    def _extract_text_pdfplumber(self, pdf_path: str) -> str:
        """전체 페이지 텍스트 합치기"""
        import pdfplumber
        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
        return "\n".join(pages_text)

    # ─────────────────────────────────────
    # Gemini OCR 폴백
    # ─────────────────────────────────────
    def _extract_text_gemini(self, pdf_path: str) -> str:
        """
        Gemini API로 PDF 텍스트 추출 (기존 gemini_parser.py 재사용)
        pdfplumber 실패 시에만 호출
        """
        try:
            # 기존 SQM Gemini 파이프라인 재사용
            import importlib
            gemini_parser = importlib.import_module("features.ai.gemini_parser")

            prompt = (
                "이 Picking List PDF에서 다음을 정확히 추출해주세요:\n"
                "1. Outbound ID\n"
                "2. Sales order 번호\n"
                "3. Customer reference (Picking No)\n"
                "4. Invoice account (고객명)\n"
                "5. Creation Date\n"
                "6. Plan Loading Date\n"
                "7. 각 라인의 Quantity, Unit(MT/KG), Batch number, Storage location\n\n"
                "형식: 원문 텍스트 그대로 출력 (파싱하기 쉽게)"
            )
            result = gemini_parser.parse_pdf_text(pdf_path, prompt)
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            logger.warning(f"[PickingListParser] Gemini 모듈 로드 실패: {e}")
            return ""

    # ─────────────────────────────────────
    # 텍스트 → 구조화 파싱
    # ─────────────────────────────────────
    def _parse_text(self, text: str, result: dict) -> None:
        """추출된 텍스트에서 헤더 + 라인 파싱"""
        self._parse_header(text, result)
        self._parse_items(text, result)
        self._calc_totals(result)

    def _parse_header(self, text: str, result: dict) -> None:
        """헤더 정보 추출"""
        # Outbound ID
        m = _RE_OUTBOUND_ID.search(text)
        if m:
            result["outbound_id"] = m.group(1).strip()

        # Sales order
        m = _RE_SALES_ORDER.search(text)
        if m:
            result["sales_order_no"] = m.group(1).strip()

        # Customer reference (Picking No)
        m = _RE_CUSTOMER_REF.search(text)
        if m:
            result["picking_no"] = m.group(1).strip()

        # Invoice account (고객명)
        m = _RE_INVOICE_ACCT.search(text)
        if m:
            customer = m.group(1).strip()
            # 멀티라인에서 첫 줄만
            result["customer"] = customer.split("\n")[0].strip()

        # Creation Date
        m = _RE_CREATION_DATE.search(text)
        if m:
            result["creation_date"] = _parse_date(m.group(1))

        # Plan Loading Date
        m = _RE_PLAN_LOADING.search(text)
        if m:
            result["plan_loading_date"] = _parse_date(m.group(1))

    def _parse_items(self, text: str, result: dict) -> None:
        """
        톤백 라인 파싱
        중복 lot_no+unit 조합은 1개로 합산 (같은 LOT 여러 페이지에 걸친 경우 방지)
        """
        seen = set()  # (lot_no, unit) 중복 방지

        for m in _RE_TONBAG_LINE.finditer(text):
            qty_raw  = float(m.group(1))
            unit     = m.group(2).upper().strip()   # MT or KG
            lot_no   = m.group(3).strip()
            storage  = m.group(4).strip()

            # 중복 체크 (같은 LOT+unit 조합)
            key = (lot_no, unit)
            if key in seen:
                continue
            seen.add(key)

            # 수량 → KG 변환
            if unit == "MT":
                qty_kg  = qty_raw * 1000.0
                qty_mt  = qty_raw
                is_sample = False
            else:  # KG
                qty_kg  = qty_raw
                qty_mt  = qty_raw / 1000.0
                is_sample = (qty_raw <= 1.0)  # 1KG 이하 = 샘플

            result["items"].append({
                "lot_no"          : lot_no,
                "qty_mt"          : round(qty_mt, 4),
                "qty_kg"          : round(qty_kg, 4),
                "unit"            : unit,
                "is_sample"       : is_sample,
                "storage_location": storage,
            })

    def _calc_totals(self, result: dict) -> None:
        """합계 계산"""
        normal_items = [i for i in result["items"] if not i["is_sample"]]
        sample_items = [i for i in result["items"] if i["is_sample"]]

        result["total_normal_mt"] = round(sum(i["qty_mt"] for i in normal_items), 3)
        result["total_sample_kg"] = round(sum(i["qty_kg"] for i in sample_items), 3)
        result["total_lots"]      = len(normal_items)  # 샘플 제외한 일반 LOT 수

    # ─────────────────────────────────────
    # 빈 결과 템플릿
    # ─────────────────────────────────────
    @staticmethod
    def _empty_result(source_file: str = "") -> dict:
        return {
            "outbound_id"      : None,
            "sales_order_no"   : None,
            "picking_no"       : None,
            "customer"         : None,
            "creation_date"    : None,
            "plan_loading_date": None,
            "source_file"      : source_file,
            "items"            : [],
            "total_normal_mt"  : 0.0,
            "total_sample_kg"  : 0.0,
            "total_lots"       : 0,
            "parse_method"     : None,
            "parse_ok"         : False,
            "warnings"         : [],
        }
