# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - D/O (Delivery Order) 파서 Mixin
======================================================

v3.6.0: document_parser_v2.py에서 분리

모듈 개요:
    D/O(화물인도지시서) PDF를 파싱합니다.
    D/O는 대부분 이미지 PDF이므로 Gemini Vision API를 사용합니다.
    
추출 항목:
    - D/O No
    - B/L No
    - Arrival Date (입항일 - 재고 입고일로 사용)
    - Container & Seal
    - Free Time

작성자: Ruby (남기동)
버전: v3.6.0
"""

import re
import logging
from datetime import datetime, date
from typing import Optional

from ..document_models import DOData, ContainerInfo, FreeTimeInfo

logger = logging.getLogger(__name__)

# Gemini API
try:
    from google import genai
    from google.genai import types
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False


class DOMixin:
    """
    D/O (Delivery Order) 파서 Mixin
    
    화물인도지시서 PDF에서 입항일, Free Time 등을 추출합니다.
    이미지 PDF인 경우 Gemini Vision API를 사용합니다.
    
    Example:
        >>> class MyParser(DOMixin, DocumentParserBase):
        ...     pass
        >>> parser = MyParser(gemini_api_key='your_key')
        >>> do = parser.parse_do('do.pdf')
    """
    
    def parse_do(self, pdf_path: str, use_gemini: bool = True) -> Optional[DOData]:

        """
        D/O PDF 파싱 (API-Only)

        정책(v5.5.1): **모든 파싱은 Gemini API를 강제**합니다.
        - API Key 미설정: 하드-스톱(예외)
        - 파싱 실패: 정규식/로컬 폴백 없음(예외)

        Args:
            pdf_path: D/O PDF 파일 경로
            use_gemini: (호환용) 무시됨. API-Only 강제.

        Returns:
            DOData: 파싱 결과
        """
        # API-Only Gate
        self._require_gemini_api_key()

        logger.info(f"[DO] Gemini API(강제)로 파싱: {pdf_path}")
        from features.ai.gemini_parser import GeminiDocumentParser
        from ..document_models import DOData, ContainerInfo, FreeTimeInfo

        gemini_parser = GeminiDocumentParser(self.gemini_api_key)
        gemini_result = None
        try:
            gemini_result = self._gemini_with_retry(
                gemini_parser.parse_do,
                pdf_path,
                retries=3,
                wait_seconds=1.0,
            )
        except (ValueError, TypeError, KeyError, IndexError) as gemini_err:
            logger.warning(f"[DO] Gemini 실패, OpenAI 폴백 시도: {gemini_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False):
            try:
                from config import OPENAI_API_KEY, DISABLE_OPENAI_FALLBACK
                if DISABLE_OPENAI_FALLBACK:
                    logger.info("[DO] OpenAI 폴백 비활성(설정) — Gemini만 사용")
                elif OPENAI_API_KEY and OPENAI_API_KEY.strip():
                    from features.ai.openai_parser import try_parse_do
                    openai_result = try_parse_do(pdf_path)
                    if openai_result and getattr(openai_result, 'success', False):
                        gemini_result = openai_result
                        logger.info("[DO] OpenAI 폴백으로 파싱 성공")
                    elif openai_result is None:
                        logger.info("[DO] OpenAI 폴백 실패 또는 openai 패키지 미설치(pip install openai)")
                else:
                    logger.info("[DO] OpenAI 폴백 생략: OPENAI_API_KEY 미설정")
            except (ValueError, TypeError, KeyError, IndexError) as fallback_err:
                logger.warning(f"[DO] OpenAI 폴백 시도 중 오류: {fallback_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False):
            msg = getattr(gemini_result, 'error_message', '') if gemini_result else ''
            raise RuntimeError(f"[DO] Gemini 파싱 실패(API-Only). {msg}".strip())

        result = DOData()
        result.source_file = pdf_path
        result.parsed_at = datetime.now()

        # 핵심 필드 매핑 (Gemini: discharge_port/delivery_order_no, OpenAI 폴백: port_of_discharge/do_no)
        result.bl_no = getattr(gemini_result, 'bl_no', '') or ''
        result.vessel = getattr(gemini_result, 'vessel', '') or ''
        result.voyage = getattr(gemini_result, 'voyage', '') or ''
        result.port_of_discharge = getattr(gemini_result, 'discharge_port', '') or getattr(gemini_result, 'port_of_discharge', '') or ''
        result.do_no = getattr(gemini_result, 'delivery_order_no', '') or getattr(gemini_result, 'do_no', '') or ''

        # 컨테이너/Free Time
        result.containers = []
        result.free_time_info = []

        for c in getattr(gemini_result, 'containers', []) or []:
            container_no = getattr(c, 'container_no', '') or ''
            if container_no:
                result.containers.append(ContainerInfo(container_no=container_no))

            # Gemini: free_time_date/return_location, OpenAI 폴백: free_time/return_place
            free_time_date = getattr(c, 'free_time_date', '') or getattr(c, 'free_time', '') or ''
            return_location = getattr(c, 'return_location', '') or getattr(c, 'return_place', '') or ''
            storage_free_days = getattr(c, 'storage_free_days', 0) or 0

            if container_no or free_time_date or return_location:
                result.free_time_info.append(FreeTimeInfo(
                    container_no=container_no,
                    free_time_date=free_time_date,
                    return_location=return_location,
                    storage_free_days=int(storage_free_days or 0),
                ))

        return result

    def _parse_do_gemini(self, pdf_path: str, result: DOData) -> DOData:
        """Gemini Vision API를 사용한 D/O 파싱"""
        if not HAS_NEW_GENAI or not self.gemini_api_key:
            logger.warning("[DO] Gemini API 사용 불가")
            return result
        
        try:
            # PDF를 이미지로 변환
            images = self._pdf_to_images(pdf_path, max_pages=3)
            
            if not images:
                logger.warning("[DO] 이미지 변환 실패")
                return result
            
            # Gemini 클라이언트 생성
            client = genai.Client(api_key=self.gemini_api_key)
            
            # 프롬프트
            prompt = """
이 D/O(Delivery Order/화물인도지시서) 이미지에서 다음 정보를 추출해주세요:

1. D/O No (9자리 숫자)
2. B/L No (9자리 숫자)
3. SAP NO / Order No (22로 시작하는 10자리 숫자)
4. Arrival Date (입항일, YYYY-MM-DD 형식)
5. Container No (ABCD1234567 형식)
6. Seal No
7. Free Time (일수)
8. Vessel Name (선박명)

JSON 형식으로 응답해주세요:
{
    "do_no": "...",
    "bl_no": "...",
    "sap_no": "...",
    "arrival_date": "YYYY-MM-DD",
    "containers": [{"no": "...", "seal": "..."}],
    "free_time_days": 0,
    "vessel": "..."
}
"""
            # 이미지와 프롬프트 전송
            contents = [prompt]
            for img_bytes in images[:2]:  # 최대 2페이지
                contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
            
            response = client.models.generate_content(
                model=getattr(self, 'model_name', 'gemini-2.5-flash'),
                contents=contents
            )
            
            # 응답 파싱
            response_text = response.text
            logger.debug(f"[DO] Gemini 응답: {response_text[:500]}")
            
            # JSON 추출
            import json
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
                
                if data.get('do_no'):
                    result.do_no = data['do_no']
                if data.get('bl_no'):
                    result.bl_no = data['bl_no']
                if data.get('sap_no'):
                    result.sap_no = data['sap_no']
                if data.get('vessel'):
                    result.vessel = data['vessel']
                
                if data.get('arrival_date'):
                    try:
                        parts = data['arrival_date'].split('-')
                        result.arrival_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                    except (ValueError, TypeError, KeyError) as _e:
                        logger.debug(f'Suppressed: {_e}')
                
                if data.get('containers'):
                    for c in data['containers']:
                        container = ContainerInfo(
                            container_no=c.get('no', ''),
                            seal_no=c.get('seal', '')
                        )
                        result.containers.append(container)
                
                if data.get('free_time_days'):
                    result.free_time = FreeTimeInfo(
                        storage_free_days=data['free_time_days']
                    )
                
                logger.info(f"[DO] Gemini 파싱 성공")
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"[DO] Gemini 파싱 오류: {e}")
        
        return result
