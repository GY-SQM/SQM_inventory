# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - D/O (Delivery Order) 파서 Mixin
======================================================
v3.6.0: document_parser_v2.py에서 분리
v5.8.6.B: Arrival Date 하이브리드 추출 + Free Time 계산 복원

작성자: Ruby (남기동)
버전: v5.8.6.B
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
    ★ v5.8.6.B: Arrival Date 하이브리드 + Free Time 계산 복원
    """
    

    def _parse_do_maersk_coord(self, pdf_path: str) -> "Optional[DOData]":
        """v9.1: MAERSK D/O 발급확인서 PyMuPDF 좌표 기반 파싱.

        Gemini API 불필요. 고정 레이아웃 → 100% 좌표 직접 추출.

        추출 필드:
            do_no, bl_no, vessel, voyage_no
            port_of_loading, port_of_discharge
            issue_date, arrival_date
            gross_weight_kg, cbm
            containers[]: {container_no, free_time, return_yard}
        """
        from core.pdf_engine import open_pdf
        import re

        try:
            doc  = open_pdf(pdf_path)
            page = doc[0]
            W    = page.rect.width
            H    = page.rect.height
            words_raw = page.get_text("words")
            doc.close()
        except Exception as e:
            raise RuntimeError(f"[DO-MAERSK] PDF 읽기 실패: {e}")

        words = [
            {"text": w[4], "x0": float(w[0]), "x1": float(w[2]),
             "top": float(w[1]), "bottom": float(w[3])}
            for w in words_raw
        ]

        def by_xy(x1, x2, y1, y2):
            hits = sorted(
                [w for w in words
                 if x1 <= w["x0"]/W*100 <= x2
                 and y1 <= w["top"]/H*100 <= y2],
                key=lambda x: x["x0"]
            )
            return " ".join(w["text"] for w in hits).strip()

        def clean_date(s):
            m = re.search(r"(\d{4}-\d{2}-\d{2})", s)
            return m.group(1) if m else ""

        def clean_num(s):
            return re.sub(r"[^\d.]", "", s.replace(",", ""))

        # ── 핵심 필드 추출 ─────────────────────────────────────
        do_no  = by_xy(57, 95, 3.5, 5.0)
        bl_no  = by_xy(57, 95, 6.8, 8.0)
        vessel = by_xy(7,  27, 27.5, 30.0)
        voyage = by_xy(27, 48, 27.5, 30.0)
        pol    = by_xy(7,  27, 31.5, 33.5)
        pod    = by_xy(27, 48, 31.5, 33.5)

        # D/O 발행일: x=76% y=83~85%
        issue_date  = clean_date(by_xy(74, 95, 83.0, 85.0))
        # 선박 입항일: x=5~28% y=87~89%
        arrival_date = clean_date(by_xy(5, 28, 87.0, 89.5))

        # 총중량/CBM
        gw_raw  = by_xy(60, 72, 38.0, 40.0)
        cbm_raw = by_xy(80, 95, 38.0, 40.0)
        try:
            gross_weight_kg = float(clean_num(gw_raw)) if gw_raw else 0.0
        except (ValueError, TypeError):
            gross_weight_kg = 0.0
        try:
            cbm = float(clean_num(cbm_raw)) if cbm_raw else 0.0
        except (ValueError, TypeError):
            cbm = 0.0

        # ── 컨테이너 목록 (4개 행) ─────────────────────────────
        containers = []
        CT_RE = re.compile(r"^[A-Z]{4}\d{7}$")
        DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
        YARD_RE = re.compile(r"^[A-Z]{6,8}$")

        for y1, y2 in [(37.5,39.5),(39.5,41.5),(41.5,43.5),(43.5,45.5)]:
            ct = by_xy(5, 20, y1, y2)
            if ct and CT_RE.match(ct):
                containers.append(ct)

        # ── Free Time + 반납지 목록 ────────────────────────────
        free_time_rows = []
        ft_y_ranges = [(56.5,58.5),(58.5,60.5),(60.5,62.5),(62.5,64.5)]
        for y1, y2 in ft_y_ranges:
            ct_txt = by_xy(55, 66, y1, y2)
            # 날짜: 슬래시 사이
            raw_ft = by_xy(66, 79, y1, y2)
            ft_match = DATE_RE.search(raw_ft)
            ft_date = ft_match.group(0) if ft_match else ""

            # 반납지: 6~8자 대문자 코드
            raw_yd = by_xy(78, 88, y1, y2)
            yd_parts = [p for p in raw_yd.split() if YARD_RE.match(p)]
            return_yard = yd_parts[0] if yd_parts else ""

            if ct_txt and CT_RE.match(ct_txt):
                free_time_rows.append({
                    "container_no": ct_txt,
                    "free_time":    ft_date,
                    "return_yard":  return_yard,
                })

        # ── DOData 조립 ────────────────────────────────────────
        from ..document_models import DOData, ContainerInfo, FreeTimeInfo

        result = DOData()
        result.source_file   = pdf_path
        result.do_no         = do_no
        result.bl_no         = bl_no
        result.vessel        = vessel
        result.voyage_no     = voyage
        result.port_of_loading   = pol
        result.port_of_discharge = pod
        result.issue_date    = issue_date
        result.arrival_date  = arrival_date
        result.gross_weight_kg = gross_weight_kg
        result.cbm           = cbm
        result.carrier_id    = "MAERSK"

        # 컨테이너 목록
        # v8.5.5 [PATCH2]: free_time_date 키 추가 → inbound_mixin 호환
        # 가장 늦은 반납일을 대표값으로 사용
        _all_ft_dates = [r["free_time"] for r in free_time_rows if r.get("free_time")]
        _max_ft_date  = max(_all_ft_dates) if _all_ft_dates else ""

        # v8.5.9: free_time_info 리스트도 함께 구성 (_fill_do가 이 필드를 읽음)
        result.free_time_info = []

        for i, ct_no in enumerate(containers):
            ft_info = free_time_rows[i] if i < len(free_time_rows) else {}
            _ft = ft_info.get("free_time", "") or _max_ft_date
            _return_yard = ft_info.get("return_yard", "")
            ci = ContainerInfo()
            ci.container_no   = ct_no
            ci.free_time      = _ft          # 기존 키 유지
            ci.free_time_date = _ft          # inbound_mixin 호환 키 추가
            ci.return_yard    = _return_yard
            if hasattr(result, "containers"):
                result.containers.append(ci)

            # v8.5.9: FreeTimeInfo도 동시 생성 → _fill_do의 CON RETURN / FREE TIME 계산에 사용
            if ct_no or _ft:
                result.free_time_info.append(FreeTimeInfo(
                    container_no=ct_no,
                    free_time_date=_ft,
                    return_location=_return_yard,
                    storage_free_days=0,
                ))

        result.success = bool(result.do_no and result.bl_no)
        logger.info(
            f"[DO-MAERSK] 좌표 파싱 v8.5.9: do={do_no} bl={bl_no} "
            f"containers={len(containers)}개 max_con_return={_max_ft_date}"
        )
        return result

    def _parse_do_msc_coord(self, pdf_path: str) -> "Optional[DOData]":
        """MSC Sea Waybill·D/O 계열 PDF 좌표 기반 파싱 (Gemini 없이 시도).

        bl_mixin MSC 박스와 동일. 양식이 다른 입항 D/O는 실패 후 carrier_rule·Gemini 폴백.
        """
        from core.pdf_engine import open_pdf
        import re as _re
        from ..document_models import DOData, ContainerInfo, FreeTimeInfo

        try:
            doc = open_pdf(pdf_path)
            page = doc[0]
            w_page = page.rect.width
            h_page = page.rect.height
            words_raw = page.get_text("words")
            doc.close()
        except Exception as e:
            raise RuntimeError(f"[DO-MSC] PDF 읽기 실패: {e}") from e

        words = [
            {"text": w[4], "x0": float(w[0]), "x1": float(w[2]),
             "top": float(w[1]), "bottom": float(w[3])}
            for w in words_raw
        ]

        def by_xy(x1: float, x2: float, y1: float, y2: float) -> str:
            hits = sorted(
                [x for x in words
                 if x1 <= x["x0"] / w_page * 100 <= x2
                 and y1 <= x["top"] / h_page * 100 <= y2],
                key=lambda t: t["x0"],
            )
            return " ".join(t["text"] for t in hits).strip()

        # v8.4.5: 실제 MSC D/O(MEDUFP963970) 직접 측정 결과
        # BL No(MEDUFP963970): x=59.9%, y=7.2% — 구좌표(y=2~4.5%)는 D/O No 영역 → 오추출
        # D/O No(26032314Y6OD): x=59.9%, y=4.0% ← 구좌표가 이 행을 잡았던 것
        bl_no_raw = by_xy(57.0, 80.0, 7.0, 8.0)
        medu_re = _re.compile(r"\b((?:MEDU|MSCU)[A-Z0-9]{6,10})\b")
        mm = medu_re.search(bl_no_raw)
        bl_no = mm.group(1) if mm else ""

        # Vessel(MSC IRENE): x=7.7%, y=28.7% — y상한 31.5→30.0으로 줄여 "Port of Loading" 행 제외
        vessel = by_xy(3.0, 23.0, 28.0, 30.0)
        # Voyage(FY611A): x=29.1%, y=28.7%
        voyage = by_xy(26.0, 40.0, 28.0, 30.0)
        pol = by_xy(30.0, 58.0, 28.0, 31.5)
        pod = by_xy(30.0, 58.0, 31.0, 34.5)
        ship_raw = by_xy(15.0, 55.0, 86.0, 95.0)

        issue_d = None
        date_pats = [
            _re.compile(r"\d{1,2}-[A-Za-z]{3}-\d{4}"),
            _re.compile(r"\d{4}-\d{2}-\d{2}"),
            _re.compile(r"\d{1,2}/\d{1,2}/\d{4}"),
        ]
        ship_token = ""
        for pat in date_pats:
            dm = pat.search(ship_raw)
            if dm:
                ship_token = dm.group(0)
                break
        if ship_token:
            issue_d = self._parse_do_msc_date_token(ship_token)

        try:
            doc2 = open_pdf(pdf_path)
            all_text = " ".join(
                doc2[i].get_text("text") or "" for i in range(min(3, len(doc2)))
            )
            doc2.close()
        except Exception as e:
            logger.debug(f"[DO-MSC] 전체 텍스트 읽기 생략: {e}")
            all_text = bl_no_raw

        ct_re = _re.compile(r"\b([A-Z]{4}\d{7})\b")
        seal_re = _re.compile(r"\b(ML-CL\d{7}|FX\d{8})\b")
        containers_found = list(dict.fromkeys(ct_re.findall(all_text)))
        seals_found = list(dict.fromkeys(seal_re.findall(all_text)))

        result = DOData()
        result.source_file = pdf_path
        result.bl_no = bl_no
        result.vessel = vessel
        result.voyage = voyage
        result.port_of_loading = pol
        result.port_of_discharge = pod
        if issue_d is not None:
            result.issue_date = issue_d
        result.carrier_id = "MSC"

        # ── v8.2.4: MSC D/O 실제 샘플 기반 추가 필드 추출 ──────────────
        # D/O No: 상단 'D/O No.' 오른쪽
        do_no_raw = by_xy(30.0, 80.0, 2.0, 6.0)
        do_no_m = _re.search(r'D/O\s*No\.?\s*([A-Z0-9]{8,20})', do_no_raw, _re.IGNORECASE)
        if do_no_m:
            result.do_no = do_no_m.group(1).strip()

        # 총 중량: "123,150 KGS" 패턴
        wt_m = _re.search(r'(\d[\d,]+)\s*KGS', all_text, _re.IGNORECASE)
        if wt_m:
            try:
                result.gross_weight_kg = float(wt_m.group(1).replace(',', ''))
            except ValueError as _e:
                logger.debug(f"[SUPPRESSED] exception in do_mixin.py: {_e}")  # noqa

        # 선박 입항일: (For Local Use) 섹션 — MRN/MSN 사이에 위치
        # 구조: 선박 입항일 → 3. → MRN → / → MSN → [날짜]
        arrival_m = _re.search(
            r'선박\s*입항일(?:[\s\S]{1,80}?)(\d{4}-\d{1,2}-\d{1,2})',
            all_text
        )
        if arrival_m:
            try:
                from datetime import date as _date
                parts = arrival_m.group(1).split('-')
                result.arrival_date = _date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, IndexError) as _e:
                logger.debug(f"[SUPPRESSED] exception in do_mixin.py: {_e}")  # noqa

        # v8.5.6 [PATCH3-BUG1]: MSC DO Vessel 좌표 실패 시 텍스트 정규식 폴백
        # 좌표 by_xy(3~23%, 28~30%)가 이 양식에서 빈 문자열 반환하는 케이스 대응
        if not result.vessel:
            _vessel_patterns = [
                _re.compile(r'Ocean Vessel\s*\n([^\n]+)', _re.IGNORECASE),
                _re.compile(r'(MSC\s+[A-Z]+)', _re.IGNORECASE),
                _re.compile(r'(HMM\s+[A-Z]+)', _re.IGNORECASE),
                _re.compile(r'([A-Z]{2,}\s+[A-Z]{4,})\s+(?:FY|\d{3,})', _re.IGNORECASE),
            ]
            for _vpat in _vessel_patterns:
                _vm = _vpat.search(all_text)
                if _vm:
                    result.vessel = _vm.group(1).strip()
                    logger.info(f"[DO-MSC] Vessel 텍스트폴백: {result.vessel}")
                    break

        # MRN / MSN: "26MSCU3082I / 0001" 패턴
        mrn_m = _re.search(r'(\d{2}MSCU[A-Z0-9]+)\s*/\s*(\d+)', all_text)
        if mrn_m:
            if hasattr(result, 'mrn'):
                result.mrn = mrn_m.group(1)
            if hasattr(result, 'msn'):
                result.msn = mrn_m.group(2)

        # ── v8.5.5 [PATCH2]: 반납기한 추출 ─────────────────────────────
        # 기존: 반납기한.{0,30}? → 실패 (키워드 후 날짜가 30자 이상 떨어짐)
        # 신규: 컨테이너번호 / / / YYYY-MM-DD 패턴으로 직접 추출
        #       예: MSDU7521485 / / / 2026-04-04
        _con_ret_re = _re.compile(r'[A-Z]{4}\d{7}\s*/\s*/\s*/\s*(\d{4}-\d{2}-\d{2})')
        _ret_dates = _con_ret_re.findall(all_text)
        # 반납일은 동일 날짜가 다수 — 가장 늦은 날짜를 대표값으로 사용
        free_time_val = max(_ret_dates) if _ret_dates else ''
        # 폴백: 기존 정규식도 시도
        if not free_time_val:
            ft_m = _re.search(r'반납기한.{0,200}?(\d{4}-\d{1,2}-\d{1,2})', all_text, _re.DOTALL)
            free_time_val = ft_m.group(1) if ft_m else ''

        # v8.5.9: free_time_info 리스트도 함께 구성 (_fill_do가 이 필드를 읽음)
        result.free_time_info = []

        for i, ct_no in enumerate(containers_found):
            ci = ContainerInfo()
            ci.container_no = ct_no
            if i < len(seals_found):
                ci.seal_no = seals_found[i]
            if free_time_val:
                ci.free_time      = free_time_val   # ContainerInfo.free_time = 반납일(str)
                ci.free_time_date = free_time_val   # inbound_mixin 키 호환
            result.containers.append(ci)

            # v8.5.9: FreeTimeInfo도 동시 생성 → _fill_do의 CON RETURN / FREE TIME 계산에 사용
            if ct_no or free_time_val:
                result.free_time_info.append(FreeTimeInfo(
                    container_no=ct_no,
                    free_time_date=free_time_val,
                    return_location="",
                    storage_free_days=0,
                ))

        result.success = bool(result.bl_no)
        logger.info(
            f"[DO-MSC] 좌표 파싱 v8.5.9: bl={bl_no} do={getattr(result,'do_no','')} "
            f"arrival={result.arrival_date} vessel={vessel} "
            f"ct={len(containers_found)} seal={len(seals_found)} wt={result.gross_weight_kg} "
            f"con_return={free_time_val or '(없음)'}"
        )
        return result

    def _parse_do_msc_date_token(self, token: str) -> Optional[date]:
        """MSC D/O 하단 날짜 토큰 → date."""
        token = (token or "").strip()
        if not token:
            return None
        pairs = (
            ("%d-%b-%Y", r"^\d{1,2}-[A-Za-z]{3}-\d{4}$"),
            ("%Y-%m-%d", r"^\d{4}-\d{2}-\d{2}$"),
            ("%d/%m/%Y", r"^\d{1,2}/\d{1,2}/\d{4}$"),
        )
        for fmt, pat in pairs:
            if re.match(pat, token, re.I):
                try:
                    return datetime.strptime(token, fmt).date()
                except ValueError as _e:
                    logger.debug(f"[SUPPRESSED] exception in do_mixin.py: {_e}")  # noqa
        return None

    def _extract_do_by_carrier_rule(self, pdf_path: str,
                                     carrier_id: str) -> "Optional[DOData]":
        """v9.1: carrier_bl_rule DB의 DO 규칙으로 타선사 D/O 파싱.

        extract_mode = 'coord'        → 좌표 직접 추출
        extract_mode = 'anchor_regex' → 라벨 탐색 + 정규식
        extract_mode = 'label_right'  → 라벨 오른쪽 값 추출
        """
        from core.pdf_engine import open_pdf
        import re as _re
        from ..document_models import DOData, ContainerInfo

        try:
            db = getattr(self, 'db', None) or getattr(self, '_db', None)
            if not db:
                return None
            rows = db.execute(
                "SELECT field_name, anchor_label, regex_pattern, "
                "extraction_method, x_min_pct, x_max_pct, y_min_pct, y_max_pct "
                "FROM carrier_bl_rule "
                "WHERE UPPER(carrier_id)=? AND doc_type='DO' AND is_active=1 "
                "ORDER BY id",
                (carrier_id.upper(),)
            ).fetchall()
            if not rows:
                return None
        except Exception as e:
            logger.debug(f"[DO-RULE] DB 조회 실패: {e}")
            return None

        # PDF 텍스트 + 단어 추출
        try:
            doc  = open_pdf(pdf_path)
            page = doc[0]
            W    = page.rect.width
            H    = page.rect.height
            words_raw  = page.get_text("words")
            full_text  = page.get_text("text") or ""
            doc.close()
        except Exception as e:
            logger.debug(f"[DO-RULE] PDF 읽기 실패: {e}")
            return None

        words = [
            {"text": w[4], "x0": float(w[0]), "x1": float(w[2]),
             "top": float(w[1]), "bottom": float(w[3]),
             "page": 0, "width": W, "height": H}
            for w in words_raw
        ]

        def by_coord(x1, x2, y1, y2):
            hits = sorted(
                [w for w in words
                 if x1 <= w["x0"]/W*100 <= x2
                 and y1 <= w["top"]/H*100 <= y2],
                key=lambda x: x["x0"]
            )
            return " ".join(w["text"] for w in hits).strip()

        def anchor_right(label: str, pat: str = "") -> str:
            label_up = label.upper()
            for w in words:
                line = " ".join(
                    ww["text"] for ww in words
                    if abs(ww["top"] - w["top"]) < 4
                ).upper()
                if label_up in line:
                    same = sorted(
                        [ww for ww in words
                         if abs(ww["top"] - w["top"]) < 4
                         and ww["x0"] > w["x1"]],
                        key=lambda x: x["x0"]
                    )
                    val = " ".join(ww["text"] for ww in same).strip()
                    if pat:
                        m = _re.search(pat, val.replace(" ", ""), _re.I)
                        return m.group(0) if m else ""
                    return val
            return ""

        # ── 필드 추출 ──────────────────────────────────────────
        extracted = {}
        containers = []

        for row in rows:
            if hasattr(row, "keys"):
                r = dict(row)
            else:
                keys = ["field_name","anchor_label","regex_pattern",
                        "extraction_method","x_min_pct","x_max_pct",
                        "y_min_pct","y_max_pct"]
                r = dict(zip(keys, row))

            field  = r.get("field_name", "")
            mode   = (r.get("extraction_method") or "anchor_regex").lower()
            pat    = r.get("regex_pattern") or ""
            anchor = r.get("anchor_label") or ""
            x1 = r.get("x_min_pct") or 0.0
            x2 = r.get("x_max_pct") or 100.0
            y1 = r.get("y_min_pct") or 0.0
            y2 = r.get("y_max_pct") or 100.0

            if mode == "coord":
                raw = by_coord(x1, x2, y1, y2)
                if raw and pat:
                    # 컨테이너는 여러 행 반복
                    if field == "container":
                        found = _re.findall(pat, raw.replace(" ", ""), _re.I)
                        containers.extend(found)
                        continue
                    m = _re.search(pat, raw.replace(" ", ""), _re.I)
                    val = m.group(0) if m else raw.replace(" ", "")
                else:
                    val = raw.replace(" ", "")
                if field == "container":
                    if val:
                        containers.append(val)
                else:
                    extracted[field] = val

            elif mode in ("anchor_regex", "label_right"):
                val = anchor_right(anchor, pat)
                if field == "container":
                    if val:
                        containers.append(val)
                else:
                    extracted[field] = val

        if not extracted.get("bl_no") and not extracted.get("do_no"):
            return None

        # ── DOData 조립 ────────────────────────────────────────
        from datetime import datetime
        result = DOData()
        result.source_file        = pdf_path
        result.do_no              = extracted.get("do_no", "")
        result.bl_no              = extracted.get("bl_no", "")
        result.vessel             = extracted.get("vessel", "")
        result.voyage_no          = extracted.get("voyage_no", "")
        result.port_of_loading    = extracted.get("port_of_loading", "")
        result.port_of_discharge  = extracted.get("port_of_discharge", "")
        result.issue_date         = extracted.get("issue_date", "")
        result.arrival_date       = extracted.get("arrival_date", "")
        result.carrier_id         = carrier_id

        # free_time은 모든 컨테이너에 동일 적용
        ft = extracted.get("free_time", "")
        ry = extracted.get("return_yard", "")

        # v8.5.9: free_time_info 리스트도 함께 구성 (_fill_do가 이 필드를 읽음)
        result.free_time_info = []

        for ct_no in containers:
            ci = ContainerInfo()
            ci.container_no = ct_no
            ci.free_time    = ft
            ci.free_time_date = ft  # v8.5.9: inbound_mixin 호환
            ci.return_yard  = ry
            if hasattr(result, "containers"):
                result.containers.append(ci)

            # v8.5.9: FreeTimeInfo도 동시 생성
            if ct_no or ft:
                from ..document_models import FreeTimeInfo as _FTI
                result.free_time_info.append(_FTI(
                    container_no=ct_no,
                    free_time_date=ft,
                    return_location=ry,
                    storage_free_days=0,
                ))

        result.success = bool(result.do_no or result.bl_no)
        logger.info(
            f"[DO-RULE] carrier_rule 파싱 v8.5.9: carrier={carrier_id} "
            f"do={result.do_no} bl={result.bl_no} ct={len(containers)}개 "
            f"con_return={ft or '(없음)'}"
        )
        return result


    # ══════════════════════════════════════════════════════════════════════
    # v8.6.4: parse_do 분해 — 서브메서드 2개
    # ══════════════════════════════════════════════════════════════════════

    def _do_extract_arrival_date(self, result, all_text: str) -> None:
        """v8.6.4: D/O Arrival Date 정규식 폴백 추출 (parse_do 분해 1/2)."""
        import re as _re
        if result.arrival_date:
            return
        for pat in [r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
                    r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b']:
            m = _re.search(pat, all_text or '')
            if m:
                try:
                    from utils.common import norm_date_any
                    parsed = norm_date_any(m.group(1))
                    if parsed:
                        result.arrival_date = parsed
                        return
                except Exception as _e:
                    logger.debug(f"[SUPPRESSED] exception in do_mixin.py: {_e}")  # noqa

    def _do_propagate_free_time(self, result) -> None:
        """v8.6.4: free_time_info 공통 반납일 보급 (parse_do 분해 2/2)."""
        if not getattr(result, 'free_time_info', None):
            return
        sample = next(
            (fi.con_return for fi in result.free_time_info
             if getattr(fi, 'con_return', None)), None
        )
        if not sample:
            return
        for fi in result.free_time_info:
            if not getattr(fi, 'con_return', None):
                try:
                    fi.con_return = sample
                except Exception as _e:
                    logger.debug(f"[SUPPRESSED] exception in do_mixin.py: {_e}")  # noqa

    def parse_do(self, pdf_path: Optional[str] = None, image_bytes: Optional[bytes] = None,
                 image_path: Optional[str] = None, use_gemini: bool = True) -> Optional[DOData]:
        """
        D/O 파싱: PDF 파일 또는 캡처 이미지(바이트/경로)를 Gemini API로 파싱.
        pdf_path, image_bytes, image_path 중 하나만 지정. 이미지 시 PDF 전용 폴백(정규식/OCR)은 생략.
        """
        # ── v9.1: 0단계 — Gemini 없이 직접 파싱 ────────────────────────
        _carrier = str(getattr(self, '_last_carrier_id', '') or '').upper()

        # v8.2.4: 파일명으로 선사 자동 감지 (MEDUFP963988_DO.pdf 형식)
        if pdf_path and not _carrier:
            import re as _fn_re, os as _os
            _stem = _os.path.basename(pdf_path).upper()
            _MSC_PREFIX = ('MEDU', 'MSCU', 'MSDU', 'MSMU', 'MSNU')
            _MRK_PREFIX = ('MAEU', 'MSKU', 'MRKU', 'FFAU')
            if any(_stem.startswith(p) for p in _MSC_PREFIX):
                _carrier = 'MSC'
                logger.info(f"[DO] 파일명 기반 선사 감지: MSC ← {_os.path.basename(pdf_path)}")
            elif any(_stem.startswith(p) for p in _MRK_PREFIX):
                _carrier = 'MAERSK'
                logger.info(f"[DO] 파일명 기반 선사 감지: MAERSK ← {_os.path.basename(pdf_path)}")

        if pdf_path and not image_bytes and _carrier:

            # [A] MAERSK → 고정 좌표 파싱
            if _carrier in ('MAERSK', 'MAEU'):
                try:
                    _r = self._parse_do_maersk_coord(pdf_path)
                    if _r and _r.success:
                        logger.info("[DO] MAERSK 좌표 파싱 성공")
                        return _r
                    logger.debug("[DO] MAERSK 좌표 실패 → carrier_rule 시도")
                except Exception as _e:
                    logger.debug(f"[DO] MAERSK 좌표 예외: {_e}")

            # [B-MSC] MSC → 고정 좌표 파싱 (v8.2.4: 실제 샘플 기반 강화)
            if _carrier in ("MSC", "MEDU", "MSCU"):
                try:
                    _r = self._parse_do_msc_coord(pdf_path)
                    if _r and _r.success:
                        logger.info("[DO] MSC 좌표 파싱 성공")
                        return _r
                    logger.debug("[DO] MSC 좌표 실패 → carrier_rule 시도")
                except Exception as _e:
                    logger.debug(f"[DO] MSC 좌표 예외: {_e}")

            # [C] 모든 선사 → carrier_bl_rule DB 좌표/규칙 파싱
            try:
                _r = self._extract_do_by_carrier_rule(pdf_path, _carrier)
                if _r and _r.success:
                    logger.info(f"[DO] carrier_rule 파싱 성공: {_carrier}")
                    return _r
                logger.debug(f"[DO] carrier_rule 실패({_carrier}) → Gemini 폴백")
            except Exception as _e:
                logger.debug(f"[DO] carrier_rule 예외: {_e}")

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
        from ..document_models import DOData, ContainerInfo, FreeTimeInfo

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
                from core.config import OPENAI_API_KEY, DISABLE_OPENAI_FALLBACK
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
                extract_arrival_date, extract_pdf_text,
                calculate_free_time_status
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
        logger.info(f"\n[DO con_return 파싱] 시작 — 소스: {source_label}")
        logger.info(f"[DO con_return 파싱] Gemini 컨테이너 수: {len(_containers_raw)}")

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
                logger.info(f"[DO con_return 추출됨] container_no={container_no or '(없음)'}, con_return(반납일)={free_time_date}")
            else:
                _hint = list(c.keys())[:10] if isinstance(c, dict) else "객체(con_return_date/free_time_date/free_time 속성 확인)"
                logger.info(f"[DO con_return 미추출] container_no={container_no or '(없음)'} — 반납일 없음 또는 YYYY-MM-DD 아님. 참고: {_hint}")
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
            logger.info(f"[DO con_return 파싱] Gemini에서 반납일 추출된 항목 수: {len(_with_date)} — {_with_date}")
        else:
            logger.info("[DO con_return 파싱] Gemini에서 반납일 0건 — 이유: API 응답 containers[]에 con_return_date/free_time_date/free_time(날짜형) 없음. OCR 폴백 시도 예정.")

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
            logger.info(f"[DO con_return 파싱] OCR 폴백 실행 — Free Time 표 직접 추출 시도: {_ocr_source}")
            try:
                from parsers.do_free_time_ocr import parse_do_free_time, normalize_container
                ocr_result = parse_do_free_time(_ocr_source)
                free_time_map = ocr_result.get("free_time_map") or {}
                if free_time_map:
                    logger.info(f"[DO con_return 파싱] OCR 폴백 추출됨: {free_time_map}")
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
                    logger.info(f"[DO con_return 파싱] OCR 폴백 후에도 반납일 0건 — 이유: {ocr_result.get('errors', [])}")
            except Exception as ocr_err:
                logger.debug("[DO] OCR 폴백 실패(무시): %s", ocr_err)
                logger.info(f"[DO con_return 파싱] OCR 폴백 실패 — 이유: {ocr_err}")
        elif _need_ocr and not _ocr_source:
            logger.info("[DO con_return 파싱] OCR 폴백 미실행 — PDF/이미지 경로 없음 (캡처 바이트만 전달된 경우)")

        # [디버그] 최종 con_return 요약
        _final = [(getattr(ft, 'container_no', ''), getattr(ft, 'free_time_date', '')) for ft in result.free_time_info if (getattr(ft, 'free_time_date', '') or '').strip()]
        if _final:
            logger.info(f"[DO con_return 파싱] 최종 반납일 적용됨 (재고 CON RETURN에 사용): {_final}\n")
        else:
            logger.info("[DO con_return 파싱] 최종 반납일 없음 — 재고 화면 CON RETURN·FREE TIME 비게 됨. D/O 문서의 'Free Time' 또는 '프리타임' 컬럼(날짜) 확인.")

        # Free Time(컨테이너 반납일) 미추출 시 로그 — D/O 문서에 "프리타임"/Free Time 컬럼(반납일) 확인
        if result.containers and (not result.free_time_info or all(not (getattr(ft, 'free_time_date', '') or '').strip() for ft in result.free_time_info)):
            logger.warning("[DO] 컨테이너 반납일(con_return_date/Free Time/프리타임) 미추출 — 재고 리스트 CON RETURN·FREE TIME 공백. D/O 문서의 반납일 컬럼 확인.")

        # v9.0 [Phase3]: DOResult → DOData 통합 필드 복사
        if gemini_result and not getattr(result, 'success', False):
            result.success = getattr(gemini_result, 'success', bool(result.do_no or result.bl_no))
            result.error_message = getattr(gemini_result, 'error_message', '') or ''
            result.raw_response = getattr(gemini_result, 'raw_response', '') or ''
        elif not getattr(result, 'success', False):
            result.success = bool(result.do_no or result.bl_no)
        return result
    # DEAD CODE REMOVED v8.6.4: _parse_do_gemini()
    # 사유: 전체 코드베이스에서 호출 없음 (2026-03-28 감사)
    # 원본 132줄 제거
