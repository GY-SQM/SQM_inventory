# -*- coding: utf-8 -*-
"""
D/O Dispatcher — 선사 자동 판별 & 파서 라우팅  v1.0
파일명 또는 내용 기반으로 선사를 판별하고 적절한 파서를 호출합니다.

■ 지원 선사
  MEDU* / MSCU* / MSDU*  → MSC         (텍스트 PDF, PyMuPDF)
  MAEU* / MSKU* / MRKU*  → Maersk      (이미지 PDF, Gemini OCR)
  COSU* / CBHU*          → COSCO       (추후 확장)
  HLCU* / HLBU*          → Hapag-Lloyd (추후 확장)
  SUDU* / SEJJ*          → Evergreen   (추후 확장)
  기타                   → Gemini OCR fallback

■ 반환 공통 구조 (DoResult)
  모든 파서가 DoResult 를 반환하므로 DB 저장 코드 단일화 가능
"""

import re
import os
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# 공통 반환 구조 — 모든 선사 파서가 이 형식으로 변환
# ──────────────────────────────────────────────────────────

@dataclass
class DoContainerRow:
    container_no: str = ""
    seal_no: str = ""
    size_type: str = ""
    free_time_date: Optional[date] = None
    return_location: str = ""


@dataclass
class DoResult:
    # ── 식별
    carrier: str = ""           # "MSC" | "MAERSK" | "COSCO" | "HAPAG" | "UNKNOWN"
    carrier_code: str = ""      # "MEDU" | "MAEU" | "COSU" | "HLCU"
    do_no: str = ""
    bl_no: str = ""

    # ── 당사자
    shipper: str = ""
    consignee: str = ""

    # ── 선박
    vessel: str = ""
    voyage: str = ""

    # ── 항구
    port_of_loading: str = ""
    port_of_discharge: str = ""

    # ── 날짜
    arrival_date: Optional[date] = None
    issue_date: Optional[date] = None

    # ── 창고 (MSC 한국 전용)
    warehouse_code: str = ""
    warehouse_name: str = ""
    mrn: str = ""
    msn: str = ""

    # ── 화물
    description: str = ""
    gross_weight_kg: float = 0.0
    measurement_cbm: float = 0.0

    # ── 컨테이너
    containers: list = field(default_factory=list)   # List[DoContainerRow]

    # ── 메타
    source_file: str = ""
    parse_method: str = ""      # "pymupdf" | "gemini" | "gemini_fallback"
    parse_ok: bool = False
    parse_errors: list = field(default_factory=list)


# ──────────────────────────────────────────────────────────
# 선사 판별 규칙 테이블
# carrier_code_prefix → (carrier_name, parser_key)
# ──────────────────────────────────────────────────────────

CARRIER_RULES: list[tuple] = [
    # (prefix_pattern, carrier_name, parser_key)
    (r"^MEDU|^MSCU|^MSDU|^MSMU|^MSNU|^TRHU", "MSC",        "msc"),
    (r"^MAEU|^MSKU|^MRKU|^MRSU|^FFAU|^SUDU", "MAERSK",     "maersk"),
    (r"^COSU|^CBHU|^CSNU",                    "COSCO",      "gemini"),
    (r"^HLCU|^HLBU",                          "HAPAG-LLOYD","gemini"),
    (r"^EGLV|^EGHU",                          "EVERGREEN",  "gemini"),
    (r"^YMLU|^YMJA",                          "YM",         "gemini"),
    (r"^ONEY|^NYKU",                          "ONE",        "gemini"),
    (r"^HJSC|^HDMU",                          "HYUNDAI",    "gemini"),
]


def detect_carrier(pdf_path: str) -> tuple[str, str, str]:
    """
    파일명 → (carrier_name, parser_key, carrier_code)
    예: "MEDUFP963970_DO.pdf" → ("MSC", "msc", "MEDU")
    """
    stem = Path(pdf_path).stem.upper()

    for pattern, carrier, parser_key in CARRIER_RULES:
        m = re.match(pattern, stem)
        if m:
            code = stem[:4]
            logger.info(f"[Dispatcher] 선사 감지: {carrier} ({code}) ← {Path(pdf_path).name}")
            return carrier, parser_key, code

    # 파일명으로 판별 불가 → PDF 내용에서 B/L No 추출 후 재시도
    carrier, parser_key, code = _detect_from_content(pdf_path)
    return carrier, parser_key, code


def _detect_from_content(pdf_path: str) -> tuple[str, str, str]:
    """PDF 첫 페이지 텍스트에서 B/L No 패턴으로 선사 판별"""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = doc[0].get_text("text")[:2000]
        doc.close()
        for pattern, carrier, parser_key in CARRIER_RULES:
            # 접두사 4글자 추출 후 매칭
            m = re.search(r"B/L\s*No[.\s]*([A-Z]{4})", text, re.IGNORECASE)
            if m:
                code = m.group(1).upper()
                if re.match(pattern, code):
                    logger.info(f"[Dispatcher] 내용 기반 선사 감지: {carrier} ({code})")
                    return carrier, parser_key, code
    except Exception as e:
        logger.warning(f"[Dispatcher] 내용 기반 감지 실패: {e}")

    logger.warning(f"[Dispatcher] 선사 불명 → Gemini fallback: {Path(pdf_path).name}")
    return "UNKNOWN", "gemini", "????"


# ──────────────────────────────────────────────────────────
# MSC → DoResult 변환
# ──────────────────────────────────────────────────────────

def _from_msc(pdf_path: str) -> DoResult:
    from parsers.msc_do_parser import parse_msc_do, MSCDoData

    raw: MSCDoData = parse_msc_do(pdf_path)
    r = DoResult(
        carrier        = "MSC",
        carrier_code   = "MEDU",
        do_no          = raw.do_no,
        bl_no          = raw.bl_no,
        shipper        = raw.shipper,
        consignee      = raw.consignee,
        vessel         = raw.vessel,
        voyage         = raw.voyage,
        port_of_loading  = raw.port_of_loading,
        port_of_discharge= raw.port_of_discharge,
        arrival_date   = raw.arrival_date,
        issue_date     = raw.issue_date,
        warehouse_code = raw.warehouse_code,
        warehouse_name = raw.warehouse_name,
        mrn            = raw.mrn,
        msn            = raw.msn,
        description    = raw.description,
        gross_weight_kg= raw.gross_weight_kg,
        measurement_cbm= raw.measurement_cbm,
        source_file    = raw.source_file,
        parse_method   = "pymupdf",
        parse_ok       = raw.parse_ok,
        parse_errors   = raw.parse_errors,
    )
    for c in raw.containers:
        r.containers.append(DoContainerRow(
            container_no   = c.container_no,
            seal_no        = c.seal_no,
            size_type      = c.sz_tp,
            free_time_date = c.return_deadline,
        ))
    return r


# ──────────────────────────────────────────────────────────
# Maersk → DoResult 변환
# ──────────────────────────────────────────────────────────

def _from_maersk(pdf_path: str, api_key: str) -> DoResult:
    from parsers.maersk_do_parser import parse_maersk_do, MaerskDoData

    raw: MaerskDoData = parse_maersk_do(pdf_path, api_key=api_key)
    r = DoResult(
        carrier        = "MAERSK",
        carrier_code   = "MAEU",
        do_no          = raw.do_no,
        bl_no          = raw.bl_no,
        shipper        = raw.shipper,
        consignee      = raw.consignee,
        vessel         = raw.vessel,
        voyage         = raw.voyage,
        port_of_loading  = raw.port_of_loading,
        port_of_discharge= raw.port_of_discharge,
        arrival_date   = raw.arrival_date,
        issue_date     = raw.issue_date,
        description    = raw.description,
        gross_weight_kg= raw.gross_weight_kg,
        measurement_cbm= raw.measurement_cbm,
        source_file    = raw.source_file,
        parse_method   = raw.parse_method,
        parse_ok       = raw.parse_ok,
        parse_errors   = raw.parse_errors,
    )
    for c in raw.containers:
        r.containers.append(DoContainerRow(
            container_no   = c.container_no,
            seal_no        = c.seal_no,
            size_type      = c.size_type,
            free_time_date = c.free_time_date,
            return_location= c.return_location,
        ))
    return r


# ──────────────────────────────────────────────────────────
# Gemini 범용 파서 (미지원 선사 fallback)
# ──────────────────────────────────────────────────────────

def _from_gemini_generic(pdf_path: str, api_key: str, carrier: str) -> DoResult:
    """MSC/Maersk 이외 선사 — Gemini OCR 범용 처리"""
    # Maersk 파서의 Gemini 경로를 재사용 (동일 프롬프트 구조)
    from parsers.maersk_do_parser import parse_maersk_do, MaerskDoData

    raw: MaerskDoData = parse_maersk_do(pdf_path, api_key=api_key)
    r = DoResult(
        carrier      = carrier,
        carrier_code = Path(pdf_path).stem[:4].upper(),
        do_no        = raw.do_no,
        bl_no        = raw.bl_no,
        shipper      = raw.shipper,
        consignee    = raw.consignee,
        vessel       = raw.vessel,
        voyage       = raw.voyage,
        arrival_date = raw.arrival_date,
        issue_date   = raw.issue_date,
        description  = raw.description,
        gross_weight_kg = raw.gross_weight_kg,
        measurement_cbm = raw.measurement_cbm,
        source_file  = raw.source_file,
        parse_method = "gemini",
        parse_ok     = raw.parse_ok,
        parse_errors = raw.parse_errors,
    )
    for c in raw.containers:
        r.containers.append(DoContainerRow(
            container_no   = c.container_no,
            seal_no        = c.seal_no,
            size_type      = c.size_type,
            free_time_date = c.free_time_date,
        ))
    return r


# ──────────────────────────────────────────────────────────
# 메인 Dispatcher
# ──────────────────────────────────────────────────────────

def dispatch_do(pdf_path: str, api_key: str = "") -> DoResult:
    """
    D/O PDF 파싱 통합 진입점

    Args:
        pdf_path : D/O PDF 파일 경로
        api_key  : Gemini API Key (이미지 PDF 선사에 필요)

    Returns:
        DoResult — 모든 선사 공통 구조체
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "")

    carrier, parser_key, code = detect_carrier(pdf_path)

    try:
        if parser_key == "msc":
            result = _from_msc(pdf_path)

        elif parser_key == "maersk":
            result = _from_maersk(pdf_path, api_key)

        else:  # "gemini" — 미지원 선사 범용
            result = _from_gemini_generic(pdf_path, api_key, carrier)

    except Exception as e:
        logger.error(f"[Dispatcher] 파싱 예외: {e}")
        result = DoResult(
            carrier      = carrier,
            carrier_code = code,
            source_file  = Path(pdf_path).name,
            parse_ok     = False,
            parse_errors = [str(e)],
        )

    result.carrier      = carrier
    result.carrier_code = code

    status = "✅" if result.parse_ok else "❌"
    logger.info(
        f"[Dispatcher] {status} [{carrier}] {Path(pdf_path).name} | "
        f"BL={result.bl_no} | 입항={result.arrival_date} | "
        f"컨테이너={len(result.containers)}개"
    )
    return result


def dispatch_do_batch(
    pdf_paths: list[str],
    api_key: str = "",
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> list[DoResult]:
    """
    여러 D/O 파일 일괄 파싱

    Args:
        pdf_paths   : PDF 경로 목록
        api_key     : Gemini API Key
        progress_cb : 진행 콜백 fn(current, total, filename)
    """
    results = []
    total = len(pdf_paths)
    for i, path in enumerate(pdf_paths, 1):
        if progress_cb:
            progress_cb(i, total, Path(path).name)
        r = dispatch_do(path, api_key=api_key)
        results.append(r)
    return results


# ──────────────────────────────────────────────────────────
# 선사 등록 헬퍼 (런타임 확장용)
# ──────────────────────────────────────────────────────────

def register_carrier(prefix_pattern: str, carrier_name: str, parser_key: str = "gemini") -> None:
    """
    새 선사를 런타임에 추가

    예:
        register_carrier(r"^WHLC", "WAN HAI", "gemini")
    """
    CARRIER_RULES.insert(0, (prefix_pattern, carrier_name, parser_key))
    logger.info(f"[Dispatcher] 선사 등록: {carrier_name} ({prefix_pattern})")


# ──────────────────────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    paths = sys.argv[1:] or [
        "MEDUFP963988_DO.pdf",
        "MEDUFP963996_DO.pdf",
        "MEDUFP963970_DO.pdf",
    ]
    api_key = os.environ.get("GEMINI_API_KEY", "")

    def progress(cur, tot, name):
        print(f"  [{cur}/{tot}] {name}")

    results = dispatch_do_batch(paths, api_key=api_key, progress_cb=progress)

    print("\n" + "=" * 65)
    for r in results:
        status = "✅" if r.parse_ok else "❌"
        print(f"\n{status} [{r.carrier}] {r.source_file}")
        print(f"   D/O No      : {r.do_no}")
        print(f"   B/L No      : {r.bl_no}")
        print(f"   선박        : {r.vessel} {r.voyage}")
        print(f"   입항일      : {r.arrival_date}")
        print(f"   중량(KGS)   : {r.gross_weight_kg:,.0f}")
        print(f"   컨테이너    : {len(r.containers)}개")
        for c in r.containers:
            ft = c.free_time_date.isoformat() if c.free_time_date else "-"
            print(f"     {c.container_no}  씰:{c.seal_no}  FT:{ft}")
        if r.parse_errors:
            print(f"   오류: {r.parse_errors}")
