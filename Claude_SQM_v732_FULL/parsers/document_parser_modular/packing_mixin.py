from __future__ import annotations
# -*- coding: utf-8 -*-
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
import re
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
    

    def _validate_pl_rows(self, result) -> list:
        """
        Ruby v2: PL 25케이스(T026~T050) 대응 후처리 검증
        반환: 경고 메시지 리스트 (비어있으면 정상)
        """
        warnings = []
        rows = getattr(result, 'rows', []) or getattr(result, 'lots', [])
        if not rows:
            warnings.append("[T026/T027] PL LOT 행이 0개 — 파싱 실패 의심")
            return warnings

        # ── T028/T029: 합계행·누적행이 상세행으로 섞임 감지 ─────────────
        # lot_no가 공백이거나 'TOTAL'/'ACCUMULATED' 패턴이면 합계행으로 판단
        SUMMARY_PAT = re.compile(r"^(total|accumulated|합계|소계|sum)", re.I)
        clean_rows = []
        for r in rows:
            lot_no = str(getattr(r, 'lot_no', '') or getattr(r, 'lot_sqm', '') or '').strip()
            if SUMMARY_PAT.match(lot_no) or not lot_no:
                warnings.append(f"[T028/T029] 합계/누적 행으로 의심되는 행 감지: lot_no='{lot_no}'")
            else:
                clean_rows.append(r)

        # ── T030: MXBG 열 매핑 오류 — 음수 또는 0인 tonbag 감지 ─────────
        for r in clean_rows:
            tb = getattr(r, 'mxbg_pallet', None) or getattr(r, 'tonbag_count', None)
            if tb is not None:
                try:
                    tb_f = float(tb)
                    if tb_f <= 0:
                        warnings.append(
                            f"[T030/T040/T041] LOT {getattr(r,'lot_no','')} tonbag={tb} — "
                            f"0이하 또는 오인식 의심"
                        )
                    elif tb_f in (1.0, 2.0) and len(clean_rows) > 1:
                        # 10→1, 20→2 오인식 의심 (전체 LOT가 2개 이하가 아닌 경우)
                        warnings.append(
                            f"[T040/T041] LOT {getattr(r,'lot_no','')} tonbag={tb} — "
                            f"10→1 또는 20→2 오인식 의심"
                        )
                except (ValueError, TypeError):
                    pass

        # ── T038/T039: 중량 오인식 감지 (500→5000, 1000→100) ────────────
        for r in clean_rows:
            nw = getattr(r, 'net_weight', None) or getattr(r, 'net_weight_kg', None)
            if nw is not None:
                try:
                    nw_f = float(str(nw).replace(',', ''))
                    if nw_f > 2000:
                        warnings.append(
                            f"[T038] LOT {getattr(r,'lot_no','')} net_weight={nw} — "
                            f"500→5000 오인식 의심 (2000kg 초과)"
                        )
                    elif 0 < nw_f < 100:
                        warnings.append(
                            f"[T039] LOT {getattr(r,'lot_no','')} net_weight={nw} — "
                            f"1000→100 오인식 의심 (100kg 미만)"
                        )
                except (ValueError, TypeError):
                    pass

        # ── T034/T035: 컨테이너 공백 행 감지 ────────────────────────────
        has_container = False
        for r in clean_rows:
            cont = str(getattr(r, 'container', '') or getattr(r, 'container_no', '') or '').strip()
            if cont:
                has_container = True
                break
        if not has_container:
            warnings.append("[T034] 모든 LOT 행의 컨테이너 값이 비어있음")

        # ── T049: 하단 요약 합계 vs rows 합계 불일치 ─────────────────────
        declared_net = getattr(result, 'total_net_weight_kg', None)
        if declared_net and clean_rows:
            computed_net = sum(
                float(str(getattr(r,'net_weight',0) or getattr(r,'net_weight_kg',0) or 0)
                      .replace(',',''))
                for r in clean_rows
            )
            if declared_net and abs(float(declared_net) - computed_net) > 5:
                warnings.append(
                    f"[T049] PL 요약 합계와 행 합계 불일치: "
                    f"요약={declared_net:,.1f}kg  행합={computed_net:,.1f}kg"
                )

        # ── T036: LOT 번호 자릿수 이상 감지 ─────────────────────────────
        for r in clean_rows:
            lot_no = str(getattr(r, 'lot_no', '') or '').strip()
            digits = re.sub(r'\D', '', lot_no)
            if digits and (len(digits) < 8 or len(digits) > 12):
                warnings.append(
                    f"[T036] LOT 번호 자릿수 이상: '{lot_no}' (숫자부 {len(digits)}자리)"
                )

        return warnings

    def parse_packing_list(self, pdf_path: str,
                           bag_weight_kg: int = 500,
                           gemini_hint: str = '') -> Optional[object]:  # Ruby v2 / v7.3.0
        """
        Packing List PDF 파싱.

        Args:
            pdf_path:       Packing List PDF 파일 경로
            bag_weight_kg:  톤백 단가 (500 or 1000) — v7.2.0: 입고 템플릿에서 주입
            gemini_hint:    선사별 추가 힌트 — v7.3.0: Gemini 프롬프트에 주입

        Returns:
            PackingListData: 파싱 결과, 실패 시 None

        Note:
            v5.5.1부터 **모든 파싱은 API(Gemini) 강제** 정책입니다.
            - 키가 없으면 하드-스톱(예외)
            - 실패 시 정규식 폴백을 하지 않습니다.
        """
        from ..document_models import PackingListData, PackingListRow, LOTInfo

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
                bag_weight_kg=bag_weight_kg,   # v7.2.0
                gemini_hint=gemini_hint,        # v7.3.0
            )
        except (ValueError, TypeError, KeyError, IndexError) as gemini_err:
            logger.warning(f"[PACKING_LIST] Gemini 실패, OpenAI 폴백 시도: {gemini_err}")

        if not gemini_result or not getattr(gemini_result, 'success', False) or len(getattr(gemini_result, 'lots', []) or []) == 0:
            try:
                from core.config import OPENAI_API_KEY, DISABLE_OPENAI_FALLBACK
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
        result.duplicate_skipped_lot_nos = list(getattr(gemini_result, 'duplicate_skipped_lot_nos', []) or [])

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
        result.bag_weight_kg = bag_weight_kg          # v7.2.0: 템플릿 단가 저장
        # 총중량 요약(없으면 rows 합으로 보강)
        if not result.total_net_weight_kg:
            result.total_net_weight_kg = sum((r.net_weight or 0.0) for r in result.rows)
        if not result.total_gross_weight_kg:
            result.total_gross_weight_kg = sum((r.gross_weight or 0.0) for r in result.rows)

        # Ruby v2: PL 25케이스 후처리 검증
        _pl_warnings = self._validate_pl_rows(result)
        for _w in _pl_warnings:
            logger.warning(f"[PL_VALIDATE] {_w}")
        result.pl_warnings = _pl_warnings

        logger.info(f"[PACKING_LIST] Gemini 성공(API-Only): {result.total_lots}개 LOT")
        return result