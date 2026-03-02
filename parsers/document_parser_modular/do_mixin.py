"""
SQM 재고관리 시스템 - D/O (Delivery Order) 파서 Mixin
======================================================
v3.6.0: document_parser_v2.py에서 분리
v5.8.6.B: Arrival Date 하이브리드 추출 + Free Time 계산 복원

작성자: Ruby (남기동)
버전: v5.8.6.B
"""

import logging
import re
from datetime import date, datetime
from typing import Optional

from ..document_models import ContainerInfo, DOData, FreeTimeInfo

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
    ★ v5.8.6.B: Arrival Date 하이브리드 + Free Time 계산 복원
    """

    def parse_do(self, pdf_path: Optional[str] = None, image_bytes: Optional[bytes] = None,
                 image_path: Optional[str] = None, use_gemini: bool = True) -> Optional[DOData]:
        """
        D/O 파싱: PDF 파일 또는 캡처 이미지(바이트/경로)를 Gemini API로 파싱.
        pdf_path, image_bytes, image_path 중 하나만 지정. 이미지 시 PDF 전용 폴백(정규식/OCR)은 생략.
        """
        self._require_gemini_api_key()

        # 단일 경로로 이미지 파일이 전달된 경우 (기존 호출 호환)
        if pdf_path and not image_path and not image_bytes:
            low = pdf_path.lower()
            if low.endswith(('.png', '.jpg', '.jpeg')):
                image_path = pdf_path
                pdf_path = None

        # 캡처 이미지 경로 → 바이트 로드
        if image_path and not image_bytes:
            try:
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
            except OSError as e:
                logger.warning(f"[DO] 이미지 파일 읽기 실패: {image_path} — {e}")
                raise RuntimeError(f"[DO] 이미지 파일을 열 수 없습니다: {image_path}") from e

        use_image = image_bytes is not None
        source_label = image_path or (pdf_path or "이미지(바이트)")

        if use_image:
            mime_type = "image/jpeg" if (image_path or "").lower().endswith((".jpg", ".jpeg")) else "image/png"
            logger.info(f"[DO] Gemini API로 캡처 이미지 파싱: {source_label}")
        else:
            if not pdf_path:
                raise ValueError("[DO] pdf_path, image_bytes, image_path 중 하나는 필수입니다.")
            logger.info(f"[DO] Gemini API(강제)로 파싱: {pdf_path}")

        from features.ai.gemini_parser import GeminiDocumentParser

        from ..document_models import ContainerInfo, DOData, FreeTimeInfo

        gemini_parser = GeminiDocumentParser(self.gemini_api_key)
        gemini_result = None
        try:
            if use_image:
                gemini_result = self._gemini_with_retry(
                    lambda: gemini_parser.parse_do_from_image(image_bytes, mime_type),
                    retries=3, wait_seconds=1.0,
                )
            else:
                gemini_result = self._gemini_with_retry(
                    gemini_parser.parse_do, pdf_path,
                    retries=3, wait_seconds=1.0,
                )
        except (ValueError, TypeError, KeyError, IndexError) as gemini_err:
            logger.warning(f"[DO] Gemini 실패, OpenAI 폴백 시도: {gemini_err}")

        if not use_image and (not gemini_result or not getattr(gemini_result, 'success', False)):
            try:
                from core.config import DISABLE_OPENAI_FALLBACK, OPENAI_API_KEY
                if not DISABLE_OPENAI_FALLBACK and OPENAI_API_KEY and OPENAI_API_KEY.strip():
                    from features.ai.openai_parser import try_parse_do
                    openai_result = try_parse_do(pdf_path)
                    if openai_result and getattr(openai_result, 'success', False):
                        gemini_result = openai_result
                        logger.info("[DO] OpenAI 폴백으로 파싱 성공")
            except (ValueError, TypeError, KeyError, IndexError) as fallback_err:
                logger.warning(f"[DO] OpenAI 폴백 시도 중 오류: {fallback_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False):
            msg = getattr(gemini_result, 'error_message', '') if gemini_result else ''
            raise RuntimeError(f"[DO] Gemini 파싱 실패(API-Only). {msg}".strip())

        result = DOData()
        result.source_file = pdf_path or image_path or ""
        result.parsed_at = datetime.now()

        # 핵심 필드 매핑
        result.bl_no = getattr(gemini_result, 'bl_no', '') or ''
        result.vessel = getattr(gemini_result, 'vessel', '') or ''
        result.voyage = getattr(gemini_result, 'voyage', '') or ''
        result.port_of_discharge = (getattr(gemini_result, 'discharge_port', '') or
                                    getattr(gemini_result, 'port_of_discharge', '') or '')
        result.do_no = (getattr(gemini_result, 'delivery_order_no', '') or
                       getattr(gemini_result, 'do_no', '') or '')

        # ═══════════════════════════════════════════════════════
        # ★★★ v5.8.6.B: Arrival Date 하이브리드 추출 ★★★
        # Gemini 우선 → 정규식 → all_dates_found 추정
        # ═══════════════════════════════════════════════════════
        try:
            from utils.date_utils import (
                calculate_free_time_status,
                extract_arrival_date,
                extract_pdf_text,
            )

            # Gemini 결과를 dict로 변환
            gemini_dict = {}
            for key in ('arrival_date', 'eta_date', 'eta', 'vessel_arrival',
                       'eta_busan', 'issue_date', 'all_dates_found'):
                val = getattr(gemini_result, key, None)
                if val:
                    gemini_dict[key] = val

            # PDF 텍스트 추출 (정규식 폴백용 — 캡처 이미지일 땐 생략)
            pdf_text = extract_pdf_text(pdf_path) if pdf_path else ""

            # 하이브리드 추출
            arrival_date, source, estimated = extract_arrival_date(gemini_dict, pdf_text)
            result.arrival_date = arrival_date

            # ★★★ Free Time 계산 (arrival_date가 있을 때만) ★★★
            if arrival_date:
                ft_status = calculate_free_time_status(arrival_date)
                logger.info(f"[DO] Free Time: {ft_status['message']}")
                # DOData에 free_time_status 속성이 없으면 무시 (호환성)
                try:
                    result.free_time_status = ft_status
                except AttributeError as e:
                    logger.debug(f"Suppressed: {e}")

        except ImportError:
            logger.debug("[DO] date_utils 미설치 — 기존 매핑 사용")
            # 기존 방식 폴백
            arr_str = getattr(gemini_result, 'arrival_date', '') or ''
            if arr_str and str(arr_str).strip() and str(arr_str) != 'None':
                try:
                    parts = str(arr_str).strip()[:10].split('-')
                    if len(parts) == 3:
                        result.arrival_date = date(
                            int(parts[0]), int(parts[1]), int(parts[2]))
                except (ValueError, TypeError, IndexError) as e:
                    logger.debug(f"Suppressed: {e}")
        except Exception as e:
            logger.warning(f"[DO] Arrival Date 하이브리드 추출 오류: {e}")
            # 기존 방식 폴백
            arr_str = getattr(gemini_result, 'arrival_date', '') or ''
            if arr_str and str(arr_str).strip() and str(arr_str) not in ('None', 'NOT_FOUND'):
                try:
                    parts = str(arr_str).strip()[:10].split('-')
                    if len(parts) == 3:
                        result.arrival_date = date(
                            int(parts[0]), int(parts[1]), int(parts[2]))
                except (ValueError, TypeError, IndexError) as e:
                    logger.debug(f"Suppressed: {e}")

        # 컨테이너/Free Time
        result.containers = []
        result.free_time_info = []

        # [디버그] D/O con_return(반납일) 파싱 시작 — 사용자 확인용
        _containers_raw = getattr(gemini_result, 'containers', []) or []
        print(f"\n[DO con_return 파싱] 시작 — 소스: {source_label}")
        print(f"[DO con_return 파싱] Gemini 컨테이너 수: {len(_containers_raw)}")

        for c in _containers_raw:
            if hasattr(c, 'container_no'):
                container_no = getattr(c, 'container_no', '') or ''
            else:
                container_no = (c.get('container_no', '') if isinstance(c, dict) else '') or ''
            if container_no:
                result.containers.append(ContainerInfo(container_no=container_no))

            # v5.8.6.B: con_return_date 호환 + D/O 프리타임 컬럼(반납일) 다중 키 수용
            if isinstance(c, dict):
                free_time_date = (c.get('con_return_date') or c.get('free_time_date') or
                                c.get('free_time') or c.get('con_return') or c.get('return_date') or '')
            else:
                free_time_date = (getattr(c, 'con_return_date', '') or
                                getattr(c, 'free_time_date', '') or
                                getattr(c, 'free_time', '') or '')
            if free_time_date:
                free_time_date = str(free_time_date).strip()[:10]
                if not re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', free_time_date):
                    free_time_date = ''
            if free_time_date:
                print(f"[DO con_return 추출됨] container_no={container_no or '(없음)'}, con_return(반납일)={free_time_date}")
            else:
                _hint = list(c.keys())[:10] if isinstance(c, dict) else "객체(con_return_date/free_time_date/free_time 속성 확인)"
                print(f"[DO con_return 미추출] container_no={container_no or '(없음)'} — 반납일 없음 또는 YYYY-MM-DD 아님. 참고: {_hint}")
            return_location = (
                (getattr(c, 'return_location', '') if hasattr(c, 'return_location') else '')
                or (getattr(c, 'return_place', '') if hasattr(c, 'return_place') else '')
                or (c.get('return_place') or c.get('return_location', '') if isinstance(c, dict) else '')
            )
            storage_free_days = getattr(c, 'storage_free_days', 0) or 0

            if container_no or free_time_date or return_location:
                result.free_time_info.append(FreeTimeInfo(
                    container_no=container_no,
                    free_time_date=free_time_date,
                    return_location=return_location,
                    storage_free_days=int(storage_free_days or 0),
                ))

        # [디버그] Gemini 결과 요약 — con_return 추출 여부
        _with_date = [(getattr(ft, 'container_no', ''), getattr(ft, 'free_time_date', '')) for ft in result.free_time_info if (getattr(ft, 'free_time_date', '') or '').strip()]
        if _with_date:
            print(f"[DO con_return 파싱] Gemini에서 반납일 추출된 항목 수: {len(_with_date)} — {_with_date}")
        else:
            print("[DO con_return 파싱] Gemini에서 반납일 0건 — 이유: API 응답 containers[]에 con_return_date/free_time_date/free_time(날짜형) 없음. OCR 폴백 시도 예정.")

        # 반납일 공통값 보급: 한 컨테이너라도 반납일이 있으면 빈 free_time_info에 동일값 적용 (D/O에서 하나만 적힌 경우)
        first_date = ''
        for ft in result.free_time_info:
            d = (getattr(ft, 'free_time_date', '') or '').strip()
            if d and re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', d[:10]):
                first_date = d[:10]
                break
        if first_date:
            for ft in result.free_time_info:
                if not (getattr(ft, 'free_time_date', '') or '').strip():
                    ft.free_time_date = first_date
                    logger.info(f"[DO] 반납일 공통 적용: {first_date}")

        # ★ OCR 폴백: Gemini로 반납일이 하나도 없을 때만 "절대 안 죽는" OCR로 Free Time 표 추출 후 병합
        _need_ocr = (
            result.containers
            and (
                not result.free_time_info
                or all(not (getattr(ft, 'free_time_date', '') or '').strip() for ft in result.free_time_info)
            )
        )
        _ocr_source = pdf_path or image_path
        if _need_ocr and _ocr_source:
            print(f"[DO con_return 파싱] OCR 폴백 실행 — Free Time 표 직접 추출 시도: {_ocr_source}")
            try:
                from parsers.do_free_time_ocr import (
                    normalize_container,
                    parse_do_free_time,
                )
                ocr_result = parse_do_free_time(_ocr_source)
                free_time_map = ocr_result.get("free_time_map") or {}
                if free_time_map:
                    print(f"[DO con_return 파싱] OCR 폴백 추출됨: {free_time_map}")
                    # 기존 free_time_info에 반납일 채우기
                    for ft in result.free_time_info:
                        cno = (getattr(ft, 'container_no', '') or '').strip()
                        if not cno:
                            continue
                        norm = normalize_container(cno)
                        if norm in free_time_map and not (getattr(ft, 'free_time_date', '') or '').strip():
                            ft.free_time_date = free_time_map[norm]
                            logger.info(f"[DO] OCR 폴백 반납일 적용: {cno} -> {free_time_map[norm]}")
                    # 컨테이너는 있는데 free_time_info에 없는 경우 추가
                    for c in result.containers:
                        cno = (getattr(c, 'container_no', '') or '').strip()
                        if not cno:
                            continue
                        norm = normalize_container(cno)
                        if norm not in free_time_map:
                            continue
                        if any(
                            (getattr(ft, 'container_no', '') or '').strip()
                            and normalize_container((getattr(ft, 'container_no', '') or '')) == norm
                            for ft in result.free_time_info
                        ):
                            continue
                        result.free_time_info.append(FreeTimeInfo(
                            container_no=cno,
                            free_time_date=free_time_map[norm],
                            return_location="",
                            storage_free_days=0,
                        ))
                        logger.info(f"[DO] OCR 폴백 FreeTimeInfo 추가: {cno} -> {free_time_map[norm]}")
                for err in ocr_result.get("errors") or []:
                    logger.debug("[DO] OCR 폴백: %s", err)
                if not free_time_map:
                    print(f"[DO con_return 파싱] OCR 폴백 후에도 반납일 0건 — 이유: {ocr_result.get('errors', [])}")
            except Exception as ocr_err:
                logger.debug("[DO] OCR 폴백 실패(무시): %s", ocr_err)
                print(f"[DO con_return 파싱] OCR 폴백 실패 — 이유: {ocr_err}")
        elif _need_ocr and not _ocr_source:
            print("[DO con_return 파싱] OCR 폴백 미실행 — PDF/이미지 경로 없음 (캡처 바이트만 전달된 경우)")

        # [디버그] 최종 con_return 요약
        _final = [(getattr(ft, 'container_no', ''), getattr(ft, 'free_time_date', '')) for ft in result.free_time_info if (getattr(ft, 'free_time_date', '') or '').strip()]
        if _final:
            print(f"[DO con_return 파싱] 최종 반납일 적용됨 (재고 CON RETURN에 사용): {_final}\n")
        else:
            print("[DO con_return 파싱] 최종 반납일 없음 — 재고 화면 CON RETURN·FREE TIME 비게 됨. D/O 문서의 'Free Time' 또는 '프리타임' 컬럼(날짜) 확인.\n")

        # Free Time(컨테이너 반납일) 미추출 시 로그 — D/O 문서에 "프리타임"/Free Time 컬럼(반납일) 확인
        if result.containers and (not result.free_time_info or all(not (getattr(ft, 'free_time_date', '') or '').strip() for ft in result.free_time_info)):
            logger.warning("[DO] 컨테이너 반납일(con_return_date/Free Time/프리타임) 미추출 — 재고 리스트 CON RETURN·FREE TIME 공백. D/O 문서의 반납일 컬럼 확인.")

        return result

    def _parse_do_gemini(self, pdf_path: str, result: DOData) -> DOData:
        """Gemini Vision API를 사용한 D/O 파싱 (레거시 — parse_do에서 직접 호출하지 않음)"""
        if not HAS_NEW_GENAI or not self.gemini_api_key:
            logger.warning("[DO] Gemini API 사용 불가")
            return result

        try:
            images = self._pdf_to_images(pdf_path, max_pages=3)
            if not images:
                logger.warning("[DO] 이미지 변환 실패")
                return result

            client = genai.Client(api_key=self.gemini_api_key)

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
            contents = [prompt]
            for img_bytes in images[:2]:
                contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

            response = client.models.generate_content(
                model=getattr(self, 'model_name', 'gemini-2.5-flash'),
                contents=contents
            )

            response_text = response.text
            logger.debug(f"[DO] Gemini 응답: {response_text[:500]}")

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

                # ★ v5.8.6.B: normalize_date 사용
                if data.get('arrival_date'):
                    try:
                        from utils.date_utils import normalize_date
                        result.arrival_date = normalize_date(data['arrival_date'])
                    except ImportError:
                        try:
                            parts = data['arrival_date'].split('-')
                            result.arrival_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                        except (ValueError, TypeError, KeyError) as e:
                            logger.debug(f"Suppressed: {e}")

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

                logger.info("[DO] Gemini 파싱 성공")

        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"[DO] Gemini 파싱 오류: {e}")

        return result
