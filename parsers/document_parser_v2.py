# -*- coding: utf-8 -*-
"""
SQM v4.0.3 — document_parser_v2.py → Modular V3 래퍼
======================================================
원본 538줄 → 래퍼. 원본: _archive/legacy_parsers_v403/

DocumentParserV2 호출은 내부적으로 DocumentParserV3로 위임됩니다.
외부 인터페이스(클래스명, 함수명)는 동일하게 유지합니다.
"""
import logging
from typing import Optional, Dict, List, Any
from utils.common import safe_float

logger = logging.getLogger(__name__)

# Modular 파서에서 필요한 것들 import
try:
    from .document_parser_modular.parser import DocumentParserV3
except ImportError:
    DocumentParserV3 = None

try:
    from .document_models import ShipmentDocuments
except ImportError:
    ShipmentDocuments = None


class DocumentParserV2:
    """V2 하위 호환 래퍼 → 내부적으로 V3(Modular) 사용
    
    기존 코드에서 DocumentParserV2를 import하는 모든 곳이
    변경 없이 동작합니다.
    """

    def __init__(self, gemini_api_key: str = None):
        # -----------------------------------------------------------------
        # v5.5.1: "모든 파싱은 API" 강제
        # - Gemini API 키가 없으면 파싱 자체를 금지(하드-스톱)
        # - V3(Modular) 초기화 실패를 조용히 무시하지 않음
        # -----------------------------------------------------------------
        self.gemini_api_key = gemini_api_key
        key = (self.gemini_api_key or "").strip()
        if not key or key.startswith('your-'):
            raise RuntimeError(
                "Gemini API Key가 필요합니다. (API-Only 모드) 설정에서 키를 입력한 뒤 다시 시도하세요."
            )

        self._v3 = None
        if not DocumentParserV3:
            raise ImportError("DocumentParserV3를 불러올 수 없습니다. (parsers/document_parser_modular 누락)")

        # V3 파서 초기화 실패는 상위로 올려 UI/엔진에서 처리
        self._v3 = DocumentParserV3(gemini_api_key=gemini_api_key)

    def diagnose_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """PDF 진단"""
        if self._v3 and hasattr(self._v3, 'diagnose_pdf'):
            return self._v3.diagnose_pdf(pdf_path)
        return {'error': 'V3 파서 미초기화', 'file': pdf_path}

    def _detect_document_type(self, text: str, file_path: str = '') -> str:
        """문서 타입 감지"""
        if self._v3 and hasattr(self._v3, '_detect_document_type'):
            return self._v3._detect_document_type(text, file_path)
        return 'UNKNOWN'

    def _extract_text(self, pdf_path: str) -> str:
        """텍스트 추출"""
        if self._v3 and hasattr(self._v3, '_extract_text'):
            return self._v3._extract_text(pdf_path)
        return ''

    def _extract_text_all_pages(self, pdf_path: str) -> List[str]:
        """전체 페이지 텍스트 추출"""
        if self._v3 and hasattr(self._v3, '_extract_text_all_pages'):
            return self._v3._extract_text_all_pages(pdf_path)
        return []

    def parse_packing_list(self, pdf_path: str, **kwargs):
        """패킹리스트 파싱"""
        if self._v3 and hasattr(self._v3, 'parse_packing_list'):
            return self._v3.parse_packing_list(pdf_path, **kwargs)
        return None

    def parse_invoice(self, pdf_path: str, **kwargs):
        """인보이스 파싱"""
        if self._v3 and hasattr(self._v3, 'parse_invoice'):
            return self._v3.parse_invoice(pdf_path, **kwargs)
        return None

    def parse_bl(self, pdf_path: str, **kwargs):
        """B/L 파싱"""
        if self._v3 and hasattr(self._v3, 'parse_bl'):
            return self._v3.parse_bl(pdf_path, **kwargs)
        return None

    def parse_do(self, pdf_path: str, **kwargs):
        """D/O 파싱"""
        if self._v3 and hasattr(self._v3, 'parse_do'):
            return self._v3.parse_do(pdf_path, **kwargs)
        return None

    def parse_document(self, pdf_path: str, doc_type: str = None) -> Optional[Any]:
        """통합 문서 파싱"""
        if self._v3:
            return self._v3.parse_document(pdf_path, doc_type)
        return None

    def parse_shipment_documents(self, folder_path: str, **kwargs):
        """선적 서류 일괄 파싱"""
        if self._v3:
            return self._v3.parse_shipment_documents(folder_path, **kwargs)
        return None


# ─── 모듈 레벨 함수 (하위 호환) ───

def parse_document(pdf_path: str, doc_type: str = None,
                   gemini_api_key: str = None) -> Optional[Any]:
    """모듈 레벨 parse_document"""
    parser = DocumentParserV2(gemini_api_key=gemini_api_key)
    return parser.parse_document(pdf_path, doc_type)


def parse_shipment_documents(folder_path: str,
                             gemini_api_key: str = None, **kwargs):
    """모듈 레벨 parse_shipment_documents"""
    parser = DocumentParserV2(gemini_api_key=gemini_api_key)
    return parser.parse_shipment_documents(folder_path, **kwargs)
