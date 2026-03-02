"""
SQM 재고관리 시스템 - Packing List 파서 Mixin
==============================================

v3.6.0: document_parser_v2.py에서 분리

모듈 개요:
    Packing List(포장명세서) PDF를 파싱합니다.
    
추출 항목:
    - Folio: 3770868
    - Product: LITHIUM CARBONATE
    - Packing: MX 500 Kg
    - Code: MIC9000.00/500 KG
    - Vessel: CHARLOTTE MAERSK 535W
    - LOT 상세: 컨테이너, LOT NO, 중량 등

작성자: Ruby (남기동)
버전: v3.6.0
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Gemini API
try:
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False


class PackingMixin:
    """
    Packing List 파서 Mixin
    
    포장명세서 PDF에서 LOT 목록, 중량, 컨테이너 정보를 추출합니다.
    Gemini API 사용 가능 시 우선 사용합니다.
    
    Example:
        >>> class MyParser(PackingMixin, DocumentParserBase):
        ...     pass
        >>> parser = MyParser(gemini_api_key='your_key')
        >>> packing = parser.parse_packing_list('packing.pdf')
    """

    def parse_packing_list(self, pdf_path: str) -> Optional['PackingListData']:
        """
        Packing List PDF 파싱
        
        Args:
            pdf_path: Packing List PDF 파일 경로
        
        Returns:
            PackingListData: 파싱 결과, 실패 시 None
        
        Note:
            v5.5.1부터 **모든 파싱은 API(Gemini) 강제** 정책입니다.
            - 키가 없으면 하드-스톱(예외)
            - 실패 시 정규식 폴백을 하지 않습니다.
        """
        from ..document_models import LOTInfo, PackingListData, PackingListRow

        # API-Only Gate
        self._require_gemini_api_key()

        logger.info("[PACKING_LIST] Gemini API(강제)로 파싱")
        from features.ai.gemini_parser import GeminiDocumentParser

        gemini_parser = GeminiDocumentParser(self.gemini_api_key)
        gemini_result = None
        try:
            gemini_result = self._gemini_with_retry(
                gemini_parser.parse_packing_list,
                pdf_path,
                retries=3,
                wait_seconds=1.0,
            )
        except (ValueError, TypeError, KeyError, IndexError) as gemini_err:
            logger.warning(f"[PACKING_LIST] Gemini 실패, OpenAI 폴백 시도: {gemini_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False) or len(getattr(gemini_result, 'lots', []) or []) == 0:
            try:
                from core.config import DISABLE_OPENAI_FALLBACK, OPENAI_API_KEY
                if DISABLE_OPENAI_FALLBACK:
                    logger.info("[PACKING_LIST] OpenAI 폴백 비활성(설정) — Gemini만 사용")
                elif not OPENAI_API_KEY or not OPENAI_API_KEY.strip():
                    logger.info("[PACKING_LIST] OpenAI 폴백 생략: OPENAI_API_KEY 미설정 (환경변수 또는 settings.ini [OpenAI] api_key)")
                else:
                    from features.ai.openai_parser import try_parse_packing_list
                    openai_result = try_parse_packing_list(pdf_path)
                    if openai_result and getattr(openai_result, 'success', False) and len(getattr(openai_result, 'lots', []) or []) > 0:
                        gemini_result = openai_result
                        logger.info("[PACKING_LIST] OpenAI 폴백으로 파싱 성공")
                    elif openai_result is None:
                        logger.info("[PACKING_LIST] OpenAI 폴백 실패 또는 openai 패키지 미설치(pip install openai)")
            except (ValueError, TypeError, KeyError, IndexError) as fallback_err:
                logger.warning(f"[PACKING_LIST] OpenAI 폴백 시도 중 오류: {fallback_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False) or len(getattr(gemini_result, 'lots', []) or []) == 0:
            msg = getattr(gemini_result, 'error_message', '') if gemini_result else ''
            raise RuntimeError(f"[PACKING_LIST] Gemini 파싱 실패(API-Only). {msg}".strip())

        result = PackingListData()
        result.source_file = pdf_path
        result.parsed_at = datetime.now()
        result.folio = gemini_result.folio
        result.product = gemini_result.product
        result.packing = gemini_result.packing
        result.code = gemini_result.code
        result.vessel = gemini_result.vessel
        result.customer = gemini_result.customer
        result.destination = gemini_result.destination
        result.total_net_weight_kg = gemini_result.total_net_weight_kg
        result.total_gross_weight_kg = gemini_result.total_gross_weight_kg

        for lot in gemini_result.lots:
            row = PackingListRow(
                list_no=lot.list_no,
                container=lot.container_no,
                lot_no=lot.lot_no,
                lot_sqm=lot.lot_sqm,
                mxbg_pallet=lot.mxbg,
                plastic_jars=1,
                net_weight=lot.net_weight_kg,
                gross_weight=lot.gross_weight_kg,
                del_no=getattr(lot, 'del_no', '') or '',
                al_no=getattr(lot, 'al_no', '') or '',
            )
            result.rows.append(row)
            # LOTInfo로 정규화 (하위 로직에서 필드/정합성 검증이 흔들리지 않게)
            result.lots.append(LOTInfo(
                list_no=lot.list_no,
                container_no=lot.container_no,
                lot_no=lot.lot_no,
                lot_sqm=lot.lot_sqm,
                mxbg_pallet=lot.mxbg,
                plastic_jars=1,
                net_weight_kg=lot.net_weight_kg,
                gross_weight_kg=lot.gross_weight_kg,
                del_no=getattr(lot, 'del_no', '') or '',
                al_no=getattr(lot, 'al_no', '') or '',
            ))

        # 요약 값 보강
        result.total_lots = len(result.rows) or len(result.lots)
        result.total_maxibag = sum((r.mxbg_pallet or 0) for r in result.rows)
        result.total_plastic_jars = result.total_lots  # 정책: LOT당 1개
        result.containers = sorted({r.container for r in result.rows if r.container})
        # 총중량 요약(없으면 rows 합으로 보강)
        if not result.total_net_weight_kg:
            result.total_net_weight_kg = sum((r.net_weight or 0.0) for r in result.rows)
        if not result.total_gross_weight_kg:
            result.total_gross_weight_kg = sum((r.gross_weight or 0.0) for r in result.rows)

        logger.info(f"[PACKING_LIST] Gemini 성공(API-Only): {result.total_lots}개 LOT")
        return result
