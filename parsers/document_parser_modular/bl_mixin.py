# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - B/L (Bill of Lading) 파서 Mixin
======================================================
v3.6.0: document_parser_v2.py에서 분리
v5.8.6.B: Ship Date 하이브리드 추출 (Gemini 우선 + 정규식 폴백)

작성자: Ruby (남기동)
버전: v5.8.6.B
"""

import re
import logging
from datetime import datetime
from typing import Optional, List

from ..document_models import BLData, ContainerInfo
from core.types import safe_float

logger = logging.getLogger(__name__)


class BLMixin:
    """B/L (Bill of Lading) 파서 Mixin — v5.8.6.B Ship Date 폴백 추가"""
    
    def parse_bl(self, pdf_path: str) -> Optional[BLData]:
        """
        B/L PDF 파싱 (API-Only + Ship Date 폴백)
        ★ v5.8.6.B: Ship Date만 정규식 폴백 추가
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
                gemini_parser.parse_bl, pdf_path,
                retries=3, wait_seconds=1.0,
            )
        except (ValueError, TypeError, KeyError, IndexError) as gemini_err:
            logger.warning(f"[BL] Gemini 실패, OpenAI 폴백 시도: {gemini_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False):
            try:
                from core.config import OPENAI_API_KEY, DISABLE_OPENAI_FALLBACK
                if DISABLE_OPENAI_FALLBACK:
                    logger.info("[BL] OpenAI 폴백 비활성(설정) — Gemini만 사용")
                elif OPENAI_API_KEY and OPENAI_API_KEY.strip():
                    from features.ai.openai_parser import try_parse_bl
                    openai_result = try_parse_bl(pdf_path)
                    if openai_result and getattr(openai_result, 'success', False):
                        gemini_result = openai_result
                        logger.info("[BL] OpenAI 폴백으로 파싱 성공")
                    elif openai_result is None:
                        logger.info("[BL] OpenAI 폴백 실패 또는 openai 패키지 미설치")
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

        # ═══════════════════════════════════════════════════════
        # ★★★ v5.8.6.B: Ship Date 하이브리드 추출 ★★★
        # Gemini 우선 → 실패 시 정규식 폴백
        # ═══════════════════════════════════════════════════════
        try:
            from utils.date_utils import extract_ship_date, extract_pdf_text

            gemini_dict = {}
            for key in ('shipped_on_board_date', 'shipped_date', 'ship_date'):
                val = getattr(gemini_result, key, '')
                if val:
                    gemini_dict[key] = val

            pdf_text = extract_pdf_text(pdf_path)
            ship_date, source, estimated = extract_ship_date(gemini_dict, pdf_text)

            result.shipped_on_board_date = ship_date
            result.ship_date = ship_date
        except Exception as e:
            logger.warning(f"[BL] Ship Date 하이브리드 추출 오류 (기존 방식 사용): {e}")
            # 기존 방식 폴백
            ship_str = (getattr(gemini_result, 'shipped_on_board_date', '') or
                       getattr(gemini_result, 'shipped_date', '') or
                       getattr(gemini_result, 'ship_date', '') or '')
            if ship_str and ship_str != 'NOT_FOUND':
                try:
                    parts = str(ship_str).strip()[:10].split('-')
                    if len(parts) == 3:
                        from datetime import date
                        result.shipped_on_board_date = date(
                            int(parts[0]), int(parts[1]), int(parts[2]))
                        result.ship_date = result.shipped_on_board_date
                except (ValueError, TypeError, IndexError):
                    pass

        # 컨테이너 목록
        containers = getattr(gemini_result, 'containers', []) or []
        result.containers = []
        for c in containers:
            try:
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
