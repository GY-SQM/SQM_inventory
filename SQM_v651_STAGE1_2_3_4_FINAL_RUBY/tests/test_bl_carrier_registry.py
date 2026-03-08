"""
test_bl_carrier_registry.py — SQM v6.4.0
==========================================
BL 선사 탐지 + BL No 정규식 추출 회귀 방지 테스트

실행: pytest tests/test_bl_carrier_registry.py -v

주요 케이스:
  T01~T03: MSC 선사 탐지
  T04~T06: Maersk 선사 탐지
  T07~T09: BL No 정규식 추출
  T10~T12: 오탐 방지
  T13~T15: Maersk bl_equals_booking_no
  T16~T17: 미탐/UNKNOWN 처리
  T18~T20: 실제 PDF 통합 테스트 (pdfplumber)
"""

import re
import pytest

# ─── 레지스트리 임포트 ───────────────────────────────────────────────────────
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from features.ai.bl_carrier_registry import (
        detect_carrier,
        extract_bl_no_by_template,
        build_bl_prompt,
        get_carrier_summary,
        CARRIER_TEMPLATES,
        CarrierTemplate,
    )
    _REGISTRY_AVAILABLE = True
except ImportError:
    _REGISTRY_AVAILABLE = False

skip_if_no_registry = pytest.mark.skipif(
    not _REGISTRY_AVAILABLE,
    reason="bl_carrier_registry.py 미설치"
)

# ─── 테스트용 샘플 텍스트 ────────────────────────────────────────────────────
MSC_PAGE0 = (
    "MEDITERRANEAN SHIPPING COMPANY S.A. SEA WAYBILL No. MEDUFP963996\n"
    "NOT NEGOTIABLE - COPY\n"
    "NO.& SEQUENCE OF SEA WAYBILLS\n"
    "SHIPPER: SQM SALAR SpA\n"
)
MSC_RIDER = (
    "MEDITERRANEAN SHIPPING COMPANY S.A. SEA WAYBILL No. MEDUFP963996\n"
    "RIDER PAGE\n"
    "MSNU7490553 Seal Number: FX41543044\n"
    "TCLU4987755 Seal Number: FX41630707\n"
)
MAERSK_PAGE0 = (
    "NON-NEGOTIABLE WAYBILL SCAC MAEU\n"
    "B/L No. 263764814\n"
    "Shipper: SQM SALAR SpA\n"
    "Booking No. 263764814\n"
)
MAERSK_PAGE1 = "B/L: 263764814 Page : 2\n"
MAERSK_PAGE2 = "B/L: 263764814 Page : 3\n"
UNKNOWN_PAGE0 = (
    "SOME UNKNOWN CARRIER\n"
    "BILL OF LADING\n"
    "B/L No. XYZ9999999\n"
)


# ════════════════════════════════════════════════════════════════
# T01~T03: MSC 선사 탐지
# ════════════════════════════════════════════════════════════════
@skip_if_no_registry
@pytest.mark.carrier
class TestMscDetection:
    def test_T01_msc_detected_by_page0(self):
        """T01: MSC 1페이지 텍스트에서 선사 탐지"""
        tmpl = detect_carrier(MSC_PAGE0)
        assert tmpl is not None
        assert tmpl.carrier_id == "MSC"

    def test_T02_msc_carrier_name(self):
        """T02: MSC carrier_name 정확성"""
        tmpl = detect_carrier(MSC_PAGE0)
        assert "Mediterranean" in tmpl.carrier_name

    def test_T03_msc_score_beats_unknown(self):
        """T03: MSC는 UNKNOWN보다 탐지 점수 높음"""
        tmpl_msc     = detect_carrier(MSC_PAGE0)
        tmpl_unknown = detect_carrier(UNKNOWN_PAGE0)
        assert tmpl_msc is not None
        # UNKNOWN은 MSC로 탐지되면 안 됨
        assert tmpl_unknown is None or tmpl_unknown.carrier_id != "MSC"


# ════════════════════════════════════════════════════════════════
# T04~T06: Maersk 선사 탐지
# ════════════════════════════════════════════════════════════════
@skip_if_no_registry
@pytest.mark.carrier
class TestMaerskDetection:
    def test_T04_maersk_detected_by_page0(self):
        """T04: Maersk 1페이지 텍스트에서 선사 탐지"""
        tmpl = detect_carrier(MAERSK_PAGE0)
        assert tmpl is not None
        assert tmpl.carrier_id == "MAERSK"

    def test_T05_maersk_bl_equals_booking_flag(self):
        """T05: Maersk는 bl_equals_booking_no=True"""
        tmpl = detect_carrier(MAERSK_PAGE0)
        assert tmpl.bl_equals_booking_no is True

    def test_T06_maersk_not_msc(self):
        """T06: Maersk 문서가 MSC로 오탐되지 않음"""
        tmpl = detect_carrier(MAERSK_PAGE0)
        assert tmpl.carrier_id != "MSC"


# ════════════════════════════════════════════════════════════════
# T07~T09: BL No 정규식 추출
# ════════════════════════════════════════════════════════════════
@skip_if_no_registry
@pytest.mark.carrier
class TestBlNoExtraction:
    def test_T07_msc_bl_no_extracted(self):
        """T07: MSC BL No 정규식 추출 정확성"""
        tmpl = detect_carrier(MSC_PAGE0)
        bl_no = extract_bl_no_by_template([MSC_PAGE0], tmpl)
        assert bl_no == "MEDUFP963996"

    def test_T08_maersk_bl_no_extracted(self):
        """T08: Maersk BL No 정규식 추출 정확성"""
        tmpl = detect_carrier(MAERSK_PAGE0)
        bl_no = extract_bl_no_by_template(
            [MAERSK_PAGE0, MAERSK_PAGE1, MAERSK_PAGE2], tmpl
        )
        assert bl_no == "263764814"

    def test_T09_maersk_bl_no_from_page2(self):
        """T09: Maersk BL No — 1페이지 없어도 2페이지에서 추출"""
        tmpl = CARRIER_TEMPLATES["MAERSK"]
        bl_no = extract_bl_no_by_template(
            ["", MAERSK_PAGE1, MAERSK_PAGE2], tmpl
        )
        assert bl_no == "263764814"


# ════════════════════════════════════════════════════════════════
# T10~T12: 오탐 방지
# ════════════════════════════════════════════════════════════════
@skip_if_no_registry
@pytest.mark.carrier
class TestFalsePositivePrevention:
    def test_T10_msc_rider_container_not_bl_no(self):
        """T10: MSC Rider Page 컨테이너 번호가 BL No로 오탐되지 않음"""
        tmpl = CARRIER_TEMPLATES["MSC"]
        # Rider page만 입력 (1페이지에 SEA WAYBILL No. 없음)
        rider_only = MSC_RIDER.replace("SEA WAYBILL No. MEDUFP963996", "")
        bl_no = extract_bl_no_by_template([rider_only], tmpl)
        # MSNU7490553 등이 BL No로 추출되면 안 됨
        assert bl_no != "MSNU7490553"
        assert bl_no != "TCLU4987755"

    def test_T11_msc_scope_page0_only(self):
        """T11: MSC page_scope=page0 — 2페이지 이후 탐색 안 함"""
        tmpl = CARRIER_TEMPLATES["MSC"]
        assert tmpl.bl_page_scope == "page0"

    def test_T12_maersk_booking_no_not_alone(self):
        """T12: Maersk Booking No만으로 BL No 오탐 방지 (B/L 라벨 필수)"""
        # "Booking No. 263764814"만 있는 텍스트 — B/L 라벨 없음
        booking_only = "Booking No. 263764814\nSome other content\n"
        tmpl = CARRIER_TEMPLATES["MAERSK"]
        bl_no = extract_bl_no_by_template([booking_only], tmpl)
        # Booking No 라벨만으로는 추출되면 안 됨 (B/L No 라벨 필요)
        # 현재 패턴은 B/L 라벨 기반이므로 이 케이스에서 빈 문자열 반환이어야 함
        assert bl_no == ""  # 또는 assert bl_no != "263764814"


# ════════════════════════════════════════════════════════════════
# T13~T15: bl_equals_booking_no 플래그
# ════════════════════════════════════════════════════════════════
@skip_if_no_registry
@pytest.mark.carrier
class TestBlEqualsBookingFlag:
    def test_T13_msc_bl_equals_booking_false(self):
        """T13: MSC bl_equals_booking_no=False"""
        tmpl = CARRIER_TEMPLATES["MSC"]
        assert tmpl.bl_equals_booking_no is False

    def test_T14_maersk_bl_equals_booking_true(self):
        """T14: Maersk bl_equals_booking_no=True"""
        tmpl = CARRIER_TEMPLATES["MAERSK"]
        assert tmpl.bl_equals_booking_no is True

    def test_T15_all_templates_have_flag(self):
        """T15: 모든 템플릿에 bl_equals_booking_no 필드 존재"""
        for cid, tmpl in CARRIER_TEMPLATES.items():
            assert hasattr(tmpl, "bl_equals_booking_no"), \
                f"{cid} 템플릿에 bl_equals_booking_no 필드 없음"


# ════════════════════════════════════════════════════════════════
# T16~T17: 미탐 / UNKNOWN 처리
# ════════════════════════════════════════════════════════════════
@skip_if_no_registry
@pytest.mark.carrier
class TestUnknownHandling:
    def test_T16_unknown_carrier_returns_none(self):
        """T16: 등록되지 않은 선사 → None 반환 (범용 파싱 fallback)"""
        tmpl = detect_carrier(UNKNOWN_PAGE0)
        assert tmpl is None

    def test_T17_empty_text_returns_none(self):
        """T17: 빈 텍스트 → None 반환"""
        tmpl = detect_carrier("")
        assert tmpl is None


# ════════════════════════════════════════════════════════════════
# T18~T20: 실제 PDF 통합 테스트
# ════════════════════════════════════════════════════════════════
PDF_MSC    = "/mnt/user-data/uploads/2200034276_BL.pdf"
PDF_MAERSK = "/mnt/user-data/uploads/2200034275_BL.pdf"

def _has_pdfplumber() -> bool:
    try:
        import pdfplumber
        return True
    except ImportError:
        return False

skip_if_no_pdf = pytest.mark.skipif(
    not _has_pdfplumber(),
    reason="pdfplumber 미설치"
)

@skip_if_no_registry
@skip_if_no_pdf
@pytest.mark.carrier
class TestRealPdfIntegration:
    def _load_pages(self, pdf_path: str) -> list:
        import pdfplumber
        with pdfplumber.open(pdf_path) as p:
            return [(pg.extract_text() or "") for pg in p.pages[:3]]

    @pytest.mark.skipif(not os.path.exists(PDF_MSC), reason="MSC 샘플 PDF 없음")
    def test_T18_real_msc_pdf_detection(self):
        """T18: 실제 MSC BL PDF 선사 탐지"""
        pages = self._load_pages(PDF_MSC)
        tmpl  = detect_carrier(pages[0])
        assert tmpl is not None
        assert tmpl.carrier_id == "MSC"

    @pytest.mark.skipif(not os.path.exists(PDF_MSC), reason="MSC 샘플 PDF 없음")
    def test_T19_real_msc_pdf_bl_no(self):
        """T19: 실제 MSC BL PDF BL No 추출"""
        pages = self._load_pages(PDF_MSC)
        tmpl  = detect_carrier(pages[0])
        bl_no = extract_bl_no_by_template(pages, tmpl)
        assert bl_no == "MEDUFP963996"

    @pytest.mark.skipif(not os.path.exists(PDF_MAERSK), reason="Maersk 샘플 PDF 없음")
    def test_T20_real_maersk_pdf_bl_no(self):
        """T20: 실제 Maersk BL PDF BL No 추출"""
        pages = self._load_pages(PDF_MAERSK)
        tmpl  = detect_carrier(pages[0])
        bl_no = extract_bl_no_by_template(pages, tmpl)
        assert bl_no == "263764814"
        assert tmpl.bl_equals_booking_no is True
