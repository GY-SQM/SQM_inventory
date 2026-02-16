# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - B/L (Bill of Lading) 파서 Mixin
======================================================

v3.6.0: document_parser_v2.py에서 분리

모듈 개요:
    B/L(선하증권) PDF를 파싱합니다.
    
추출 항목:
    - B/L No: 258468669
    - Booking No: 258468669
    - SAP NO: 2200033057
    - 선적 정보: Shipper, Consignee, Vessel, Port
    - 컨테이너 정보: Container No, Seal No, Size, Weight
    - 운임 정보: Freight

작성자: Ruby (남기동)
버전: v3.6.0
"""

import re
import logging
from datetime import datetime
from typing import Optional, List

from ..document_models import BLData, ContainerInfo
from core.types import safe_float

logger = logging.getLogger(__name__)


class BLMixin:
    """
    B/L (Bill of Lading) 파서 Mixin
    
    선하증권 PDF에서 B/L 번호, 컨테이너 정보, 선적 정보를 추출합니다.
    
    Example:
        >>> class MyParser(BLMixin, DocumentParserBase):
        ...     pass
        >>> parser = MyParser()
        >>> bl = parser.parse_bl('bl.pdf')
    """
    
    def parse_bl(self, pdf_path: str) -> Optional[BLData]:
        """
        B/L PDF 파싱 (API-Only)

        정책(v5.5.1): **모든 파싱은 Gemini API를 강제**합니다.
        - API Key 미설정: 하드-스톱(예외)
        - 파싱 실패: 정규식/로컬 폴백 없음(예외)

        Args:
            pdf_path: B/L PDF 파일 경로

        Returns:
            BLData: 파싱 결과
        """
        # API-Only Gate
        self._require_gemini_api_key()

        logger.info(f"[BL] Gemini API(강제)로 파싱: {pdf_path}")
        from features.ai.gemini_parser import GeminiDocumentParser
        from ..document_models import BLData, ContainerInfo

        gemini_parser = GeminiDocumentParser(self.gemini_api_key)
        gemini_result = None
        try:
            gemini_result = self._gemini_with_retry(
                gemini_parser.parse_bl,
                pdf_path,
                retries=3,
                wait_seconds=1.0,
            )
        except (ValueError, TypeError, KeyError, IndexError) as gemini_err:
            logger.warning(f"[BL] Gemini 실패, OpenAI 폴백 시도: {gemini_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False):
            try:
                from config import OPENAI_API_KEY, DISABLE_OPENAI_FALLBACK
                if DISABLE_OPENAI_FALLBACK:
                    logger.info("[BL] OpenAI 폴백 비활성(설정) — Gemini만 사용")
                elif OPENAI_API_KEY and OPENAI_API_KEY.strip():
                    from features.ai.openai_parser import try_parse_bl
                    openai_result = try_parse_bl(pdf_path)
                    if openai_result and getattr(openai_result, 'success', False):
                        gemini_result = openai_result
                        logger.info("[BL] OpenAI 폴백으로 파싱 성공")
                    elif openai_result is None:
                        logger.info("[BL] OpenAI 폴백 실패 또는 openai 패키지 미설치(pip install openai)")
                else:
                    logger.info("[BL] OpenAI 폴백 생략: OPENAI_API_KEY 미설정")
            except (ValueError, TypeError, KeyError, IndexError) as fallback_err:
                logger.warning(f"[BL] OpenAI 폴백 시도 중 오류: {fallback_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False):
            msg = getattr(gemini_result, 'error_message', '') if gemini_result else ''
            raise RuntimeError(f"[BL] Gemini 파싱 실패(API-Only). {msg}".strip())

        result = BLData()
        result.source_file = pdf_path
        result.parsed_at = datetime.now()

        # Gemini 결과 매핑(핵심 필드)
        result.bl_no = getattr(gemini_result, 'bl_no', '') or ''
        result.shipper = getattr(gemini_result, 'shipper', '') or ''
        result.consignee = getattr(gemini_result, 'consignee', '') or ''
        result.vessel = getattr(gemini_result, 'vessel', '') or ''

        # 컨테이너 목록
        containers = getattr(gemini_result, 'containers', []) or []
        result.containers = []
        for c in containers:
            try:
                # gross_weight_kg(Gemini) 또는 weight_kg(OpenAI 폴백) 지원
                w = float(getattr(c, 'gross_weight_kg', None) or getattr(c, 'weight_kg', 0) or 0)
                result.containers.append(ContainerInfo(
                    container_no=getattr(c, 'container_no', '') or '',
                    seal_no=getattr(c, 'seal_no', '') or '',
                    size_type=getattr(c, 'size_type', '') or '',
                    weight_kg=w,
                    measurement_cbm=float(getattr(c, 'measurement_m3', 0.0) or 0.0),
                    package_count=int(getattr(c, 'package_qty', 0) or 0),
                ))
            except (ValueError, TypeError, KeyError, IndexError) as _e:
                logger.debug(f"Suppressed: {_e}")
                continue

        return result
