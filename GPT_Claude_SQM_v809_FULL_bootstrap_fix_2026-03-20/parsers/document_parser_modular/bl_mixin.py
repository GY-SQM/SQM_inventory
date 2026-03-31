"""
SQM 재고관리 시스템 - B/L (Bill of Lading) 파서 Mixin
======================================================
v3.6.0: document_parser_v2.py에서 분리
v5.8.6.B: Ship Date 하이브리드 추출 (Gemini 우선 + 정규식 폴백)

작성자: Ruby (남기동)
버전: v5.8.6.B
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

from ..document_models import BLData

logger = logging.getLogger(__name__)


class BLMixin:
    """B/L (Bill of Lading) 파서 Mixin — 좌표 기반 3단계 단독 파서"""

    BL_LABEL_PATTERNS = [
        r"SEA\s+WAYBILL\s*No\.?",
        r"WAYBILL\s*No\.?",
        r"B\s*/\s*L\s*No\.?",
        r"BILL\s+OF\s+LADING\s*No\.?",
        r"\bBL\s*No\.?",
    ]
    # v8.0.0 [BL-FORMAT]: 선사별 BL 번호 형식 직접 지정
    # 형식: (영문접두사, 숫자길이) — 빈 접두사면 순수 숫자
    BL_FORMAT_MAP = {
        'MSC':      [('MSCU', 7), ('MEDU', 7)],   # MSCU1234567
        'MAERSK':   [('', 9), ('', 10)],           # 263764814 (순수 숫자)
        'COSCO':    [('COSU', 7)],                 # COSU1234567
        'EVERGREEN':[('EVER', 7)],                 # EVER1234567
        'CMA CGM':  [('CMA', 7)],                  # CMA1234567
        'HMM':      [('HMMU', 7)],                 # HMMU1234567
        'ONE':      [('ONEU', 7)],                 # ONEU1234567
        'HAPAG':    [('HLCU', 7)],                 # HLCU1234567
        'YANG MING':[('YMLU', 7)],                 # YMLU1234567
        'PIL':      [('PILU', 7)],
        'SITC':     [('SITC', 7)],
    }

    BL_TOKEN_RE = re.compile(r"^[A-Z0-9]{6,25}$")
    CARRIER_RE = re.compile(
        r"(?:MEDU[A-Z0-9]{6,10}|MSCU[A-Z0-9]{6,10}|COSU[A-Z0-9]{6,10}|EVER[A-Z0-9]{6,10}|"
        r"YMLU[A-Z0-9]{6,10}|HMMU[A-Z0-9]{6,10}|ONEU[A-Z0-9]{6,10}|HLCU[A-Z0-9]{6,10}|"
        r"CMA[A-Z0-9]{6,10}|PILU[A-Z0-9]{6,10}|SITC[A-Z0-9]{6,10}|"  # v8.0.0: CMA/PIL/SITC 추가
        r"\d{9,15})"  # 순수 숫자 (MAERSK 등)
    )
    BLACKLIST = {
        "NOT", "COPY", "PAGES", "NEGOTIABLE", "ORIGINAL", "BILL", "LADING", "WAYBILL", "NO",
        "BOOKING", "SEA", "SHIPPER", "CONSIGNEE",
    }
    SHIP_DATE_PATTERNS = [
        re.compile(r"\b\d{1,2}[-/.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/.]\d{4}\b", re.IGNORECASE),
        re.compile(r"\b\d{4}[-/.]\d{2}[-/.]\d{2}\b"),
        re.compile(r"\b\d{1,2}[-/.]\d{2}[-/.]\d{4}\b"),
        re.compile(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b", re.IGNORECASE),
    ]
    SHIPPED_PATTERN = re.compile(r"\bSHIPPED\b.*\bBOARD\b(?:.*\bDATE\b)?", re.IGNORECASE)
    URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)

    def _extract_by_bl_format(self, text: str, bl_format: str) -> str:
        """v8.0.0: bl_format 직접 지정으로 BL 번호 추출.
        형식: '숫자9' → 순수 숫자 9자리
              'MSCU7' → MSCU + 숫자 7자리
        """
        if not bl_format:
            return ''
        import re as _re
        fmt = bl_format.strip()
        try:
            if fmt.startswith('숫자') or fmt.lower().startswith('num'):
                # 순수 숫자 N자리
                n = int(''.join(filter(str.isdigit, fmt)))
                pattern = _re.compile(rf'\b(\d{{{n}}})\b')
            else:
                # 영문접두사 + 숫자N자리
                prefix = ''.join(filter(str.isalpha, fmt)).upper()
                n = int(''.join(filter(str.isdigit, fmt)))
                pattern = _re.compile(rf'\b({_re.escape(prefix)}\d{{{n}}})\b')
            matches = pattern.findall(text)
            if matches:
                return matches[0]
        except Exception as _e:
            logger.debug(f"[BL] bl_format 파싱 실패: {_e}")
        return ''

    def parse_bl(self, pdf_path: str, **kwargs) -> "Optional[BLData]":
        """v9.0: BL PDF 파싱 — 단순화.

        선사 지정 있음 → 선사 전용 규칙으로 직접 추출
        선사 미지정   → keyword_anchor (B/L No. 라벨) 1회만 시도
        """
        logger.info(f"[BL] 파싱 시작: {pdf_path}")
        words     = self._extract_words(pdf_path, max_pages=3)
        full_text = self._extract_text(pdf_path)
        if not words and not full_text:
            raise RuntimeError("[BL] PDF 텍스트 추출 실패")

        carrier_id = str(kwargs.get("carrier_id", "") or "").upper().strip()
        _bl_format = str(kwargs.get("bl_format",  "") or "").strip()
        bl_no  = ""
        method = ""

        # ── 선사 지정 있음 → 선사 전용 규칙 ────────────────────
        if carrier_id or _bl_format:
            # bl_format 직접 지정 (레거시)
            if _bl_format:
                bl_no  = self._extract_by_bl_format(full_text, _bl_format)
                method = f"bl_format({_bl_format})" if bl_no else ""

            # MAERSK → WAYBILL 라인 (옆 코드 + 아래 숫자)
            if not bl_no and carrier_id in ("MAERSK", "MAEU", "MERSK"):
                bl_no  = self._extract_by_waybill_line(words)
                method = "waybill_line" if bl_no else ""

            # 다른 선사 → DB carrier_bl_rule 조회
            if not bl_no and carrier_id:
                bl_no  = self._extract_by_carrier_rule(words, full_text, carrier_id)
                method = f"carrier_rule({carrier_id})" if bl_no else ""

            # 선사 규칙 실패 → keyword_anchor 폴백
            if not bl_no:
                bl_no  = self._extract_by_keyword_anchor(words)
                method = "keyword_anchor_fallback" if bl_no else ""
                if bl_no:
                    logger.warning(f"[BL] 선사({carrier_id}) 규칙 실패 → keyword_anchor 폴백")

        # ── 선사 미지정 → keyword_anchor 1회만 ─────────────────
        else:
            bl_no  = self._extract_by_keyword_anchor(words)
            method = "keyword_anchor" if bl_no else ""

        if not bl_no:
            raise RuntimeError(f"[BL] BL 번호 파싱 실패 (선사={carrier_id or '미지정'})")

        result = BLData()
        result.source_file = pdf_path
        result.parsed_at   = datetime.now()
        result.bl_no       = bl_no
        result.booking_no  = bl_no
        result.raw_text    = full_text[:20000] if full_text else ""

        # v9.1: 좌표 기반 추가 필드 (vessel, voyage, POL, POD)
        try:
            extra = self._extract_bl_extra_fields(words)
            result.vessel            = extra.get("vessel", "")
            result.voyage_no         = extra.get("voyage_no", "")
            result.port_of_loading   = extra.get("port_of_loading", "")
            result.port_of_discharge = extra.get("port_of_discharge", "")
            if extra.get("vessel"):
                logger.info(
                    f"[BL] 추가필드: vessel={extra['vessel']} "
                    f"POD={extra.get('port_of_discharge', '')}"
                )
        except Exception as _e:
            logger.debug(f"[BL] 추가필드 추출 실패(무시): {_e}")

        # Ship Date: 0단계(고정 좌표) → 기존 3단계 폴백
        try:
            ship_date, source, page_no = self._extract_ship_date_by_coord(words), "coord", None
            ship_date = ship_date or None
            if not ship_date:
                ship_date, source, page_no = self._extract_ship_date_v2(words)
            if not ship_date:
                from utils.date_utils import extract_ship_date
                ship_date, source, _estimated = extract_ship_date({}, full_text or "")
                page_no = None
            result.shipped_on_board_date = ship_date
            result.ship_date = ship_date
            if ship_date:
                logger.info(f"[BL] Ship Date: {ship_date} (method={source})")
        except Exception as e:
            logger.debug(f"[BL] Ship Date 추출 실패(무시): {e}")

        logger.info(f"[BL] 파싱 성공: {bl_no} (method={method})")
        result.success = bool(result.bl_no)
        return result

    def _extract_words(self, pdf_path: str, max_pages: int = 3) -> List[Dict]:
        """PyMuPDF 단어 좌표 추출."""
        import fitz
        out: List[Dict] = []
        doc = fitz.open(pdf_path)
        try:
            for page_idx in range(min(max_pages, len(doc))):
                page = doc[page_idx]
                width = float(page.rect.width or 1.0)
                height = float(page.rect.height or 1.0)
                for w in page.get_text("words") or []:
                    x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], str(w[4] or "")
                    t = text.strip()
                    if not t:
                        continue
                    out.append({
                        "text": t, "x0": float(x0), "x1": float(x1),
                        "top": float(y0), "bottom": float(y1),
                        "page": page_idx, "width": width, "height": height,
                    })
        finally:
            doc.close()
        return out

    def _norm(self, token: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", str(token or "").upper())

    def _looks_like_bl(self, token: str) -> bool:
        t = self._norm(token)
        if not t or t in self.BLACKLIST:
            return False
        if not self.BL_TOKEN_RE.match(t):
            return False
        if not re.search(r"\d", t):
            return False
        return True

    def _group_lines(self, words: List[Dict], y_tol: float = 4.0) -> Dict[tuple, List[Dict]]:
        lines: Dict[tuple, List[Dict]] = {}
        for w in words:
            yc = (w["top"] + w["bottom"]) / 2.0
            bucket = int(round(yc / max(0.1, y_tol)))
            key = (w["page"], bucket)
            lines.setdefault(key, []).append(w)
        for key in lines:
            lines[key].sort(key=lambda x: x["x0"])
        return lines

    def _extract_by_carrier_rule(self, words, full_text: str,
                                   carrier_id: str, doc_type: str = 'BL') -> str:
        """v9.1: carrier_bl_rule DB → 좌표 방식 또는 라벨+정규식 방식으로 추출.

        extract_mode:
          'coord'        → x_min/x_max/y_min/y_max 좌표 직접 추출
          'anchor_regex' → anchor_label 탐색 + regex 패턴
          'waybill_line' → MAERSK 전용 waybill_line 메서드
        """
        try:
            db = getattr(self, 'db', None) or getattr(self, '_db', None)
            if not db:
                raise LookupError("no db")

            rows = db.execute(
                "SELECT anchor_label, regex_pattern, field_name, "
                "extraction_method, x_min_pct, x_max_pct, y_min_pct, y_max_pct "
                "FROM carrier_bl_rule "
                "WHERE UPPER(carrier_id)=? AND doc_type=? AND is_active=1 "
                "ORDER BY id",
                (carrier_id.upper(), doc_type.upper())
            ).fetchall()

            for row in (rows or []):
                if hasattr(row, 'keys'):
                    r = dict(row)
                else:
                    keys = ['anchor_label','regex_pattern','field_name',
                            'extraction_method','x_min_pct','x_max_pct',
                            'y_min_pct','y_max_pct']
                    r = dict(zip(keys, row))

                field_name = r.get('field_name', 'bl_no')
                if doc_type == 'BL' and field_name != 'bl_no':
                    continue

                mode    = (r.get('extraction_method') or 'anchor_regex').lower()
                pattern = r.get('regex_pattern') or ''
                anchor  = r.get('anchor_label') or ''

                # ── 좌표 방식 ──────────────────────────────────
                if mode == 'coord':
                    x1 = r.get('x_min_pct') or 0.0
                    x2 = r.get('x_max_pct') or 100.0
                    y1 = r.get('y_min_pct') or 0.0
                    y2 = r.get('y_max_pct') or 100.0
                    val = self._by_coord(words, x1, x2, y1, y2)
                    if val and pattern:
                        m = re.search(pattern, val.replace(' ', ''), re.IGNORECASE)
                        return m.group(0) if m else val.replace(' ', '')
                    if val:
                        return val.replace(' ', '')

                # ── waybill_line 방식 ──────────────────────────
                elif mode == 'waybill_line':
                    val = self._extract_by_waybill_line(words)
                    if val:
                        return val

                # ── anchor_regex 방식 (기본) ───────────────────
                else:
                    val = self._extract_by_anchor_and_pattern(
                        words, full_text, anchor, pattern
                    )
                    if val:
                        return val

        except LookupError:
            logger.debug("[SUPPRESSED] exception in bl_mixin.py")  # noqa
        except Exception as e:
            logger.debug(f"[BL] carrier_rule DB 조회 실패: {e}")

        # BL_FORMAT_MAP 폴백
        fmt = self.BL_FORMAT_MAP.get(carrier_id.upper(), '')
        if fmt:
            return self._extract_by_bl_format(full_text, fmt)
        return ''

    def _by_coord(self, words, x1: float, x2: float,
                  y1: float, y2: float, page: int = 0) -> str:
        """좌표 범위로 텍스트 추출 (공용 헬퍼 v9.1)."""
        if not words:
            return ''
        # 첫 번째 단어에서 페이지 크기 가져오기
        ref = next((w for w in words if w.get('page', 0) == page), None)
        if not ref:
            ref = words[0]
        pw = float(ref.get('width',  595.0) or 595.0)
        ph = float(ref.get('height', 842.0) or 842.0)
        hits = sorted(
            [w for w in words
             if w.get('page', 0) == page
             and x1 <= w['x0']/pw*100 <= x2
             and y1 <= w['top']/ph*100 <= y2],
            key=lambda x: x['x0']
        )
        return ' '.join(w['text'] for w in hits).strip()


    def _extract_by_anchor_and_pattern(self, words, full_text: str,
                                        anchor_label: str, regex_pattern: str) -> str:
        """v9.0: 라벨 앵커 + 정규식 패턴으로 BL 번호 추출.

        anchor_label: 라벨 텍스트 (예: "Vessel No.", "B/L No.")
        regex_pattern: BL 번호 정규식 (예: "[A-Z]{6}[0-9]{6}")
        """
        if not regex_pattern:
            return ''
        try:
            bl_re = re.compile(regex_pattern, re.IGNORECASE)
        except re.error as e:
            logger.warning(f"[BL] 잘못된 regex: {regex_pattern} → {e}")
            return ''

        # full_text 전체 스캔
        for m in bl_re.finditer(full_text or ''):
            token = m.group(0).upper()
            if self._looks_like_bl(token):
                return token

        return ''


    def _extract_bl_extra_fields(self, words) -> dict:
        """v9.1: BL PDF에서 vessel/voyage/POL/POD 좌표 기반 추출.

        MAERSK NON-NEGOTIABLE WAYBILL 고정 레이아웃:
          y≈33.8%  x=5~25%:   SALLY MAERSK  (vessel)
          y≈33.8%  x=26~38%:  604W           (voyage_no)
          y≈36.8%  x=5~26%:   Puerto Angamos, Chile  (port_of_loading)
          y≈36.7%  x=26~46%:  GWANGYANG,SOUTH KOREA  (port_of_discharge)
        """
        if not words:
            return {}

        page_h = float(words[0].get("height", 842.0)) if words else 842.0
        page_w = float(words[0].get("width",  595.0)) if words else 595.0

        def by_xy(x1, x2, y1, y2):
            hits = sorted(
                [w for w in words
                 if x1 <= w["x0"] / page_w * 100 <= x2
                 and y1 <= w["top"] / page_h * 100 <= y2
                 and w.get("page", 0) == 0],
                key=lambda x: x["x0"]
            )
            return " ".join(w["text"] for w in hits).strip()

        # 라벨 행(y≈33.0%)과 값 행(y≈33.8%)을 분리
        vessel  = by_xy(5,  25, 33.3, 34.5)   # 라벨 제외 값만
        voyage  = by_xy(26, 38, 33.3, 34.5)
        pol     = by_xy(5,  26, 36.4, 37.5)
        pod_raw = by_xy(26, 46, 36.3, 37.5)

        # "Vessel" / "Voyage No." 라벨 토큰 제거
        vessel  = re.sub(r"^Vessel\s*", "", vessel, flags=re.IGNORECASE).strip()
        voyage  = re.sub(r"^(Voyage|No\.)\s*", "", voyage, flags=re.IGNORECASE).strip()
        pol     = re.sub(r"^Port\s+of\s+Loading\s*", "", pol, flags=re.IGNORECASE).strip()
        pod     = re.sub(r"^Port\s+of\s+Discharge\s*", "", pod_raw, flags=re.IGNORECASE).strip()

        return {
            "vessel":             vessel,
            "voyage_no":          voyage,
            "port_of_loading":    pol,
            "port_of_discharge":  pod,
        }


    def _extract_by_waybill_line(self, words):
        """v9.0: WAYBILL 라인에서 선사코드 + BL번호 한 번에 추출.
        
        같은 줄: [WAYBILL] ... [MAEU]
        바로 아래:              [263764814]
        결과: MAEU263764814
        """
        if not words:
            return ""
        page_h = float(words[0].get("height", 842.0))
        # 1. 1페이지 상단 20% WAYBILL 탐색
        wbs = [w for w in words
               if "WAYBILL" in str(w.get("text","")).upper()
               and w.get("page",0)==0
               and float(w["top"]) < page_h*0.20]
        if not wbs:
            return ""
        wb   = wbs[0]
        wb_y = float(wb["top"])
        wb_x = float(wb["x0"])
        # 2. 같은 줄 오른쪽 2~4자 영문 = 선사코드
        row = [w for w in words
               if w.get("page",0)==0
               and abs(float(w["top"])-wb_y)<6
               and float(w["x0"])>wb_x
               and re.match(r"^[A-Z]{2,4}$", str(w.get("text","")))]
        if not row:
            return ""
        cw   = row[0]
        code = str(cw["text"]).upper()
        cx   = float(cw["x0"])
        cy   = float(cw["top"])
        # 3. 선사코드 바로 아래 숫자
        nums = [w for w in words
                if w.get("page",0)==0
                and 8<=(float(w["top"])-cy)<=50
                and abs(float(w["x0"])-cx)<=20
                and re.match(r"^[0-9]{7,15}$", str(w.get("text","")))]
        if not nums:
            return ""
        nums.sort(key=lambda x:(float(x["top"])-cy, abs(float(x["x0"])-cx)))
        bl  = str(nums[0]["text"])
        res = code + bl
        logger.info(f"[BL] WAYBILL라인: {code!r}+{bl!r}={res!r}")
        return res

    def _extract_by_keyword_anchor(self, words: List[Dict]) -> str:
        if not words:
            return ""
        patterns = [re.compile(p, re.IGNORECASE) for p in self.BL_LABEL_PATTERNS]
        lines = self._group_lines(words, y_tol=4.0)
        for (_page, _bucket), line in lines.items():
            line_text = " ".join(w["text"] for w in line)
            if not any(p.search(line_text) for p in patterns):
                continue
            page_width = float(line[0].get("width", 1.0))
            candidates = [
                w for w in line
                if w["x0"] > page_width * 0.50 and self._looks_like_bl(w["text"])
            ]
            if candidates:
                # 같은 행의 우측 끝 후보 우선
                best = sorted(candidates, key=lambda x: (x["x0"], len(self._norm(x["text"]))))[-1]
                bl_raw = self._norm(best["text"])
                # v9.0: SCAC 코드 탐색 → 순수숫자 BL에 접두사 붙이기
                if re.match(r"^\d{7,15}$", bl_raw):
                    scac_code = self._find_scac_code(words)
                    if scac_code:
                        bl_raw = scac_code + bl_raw
                return bl_raw
        return ""

    def _extract_by_scac_pattern(self, words: List[Dict]) -> str:
        """v9.0: SCAC 라벨 → 우측 선사코드(4자) → 바로 아래 BL 번호 추출.

        MAERSK NON-NEGOTIABLE WAYBILL 레이아웃:
          같은 줄: [SCAC] [MAEU]   ← SCAC 라벨 + 4자 선사코드
          바로 아래: [B/L No.] [263764814]  ← 숫자 9자리 BL 번호

        이 패턴으로 B/L No. 라벨 없이도 BL 번호 추출 가능.
        """
        if not words:
            return ""

        page_w = float(words[0].get("width", 595.0)) if words else 595.0

        # SCAC 단어 찾기
        scac_words = [w for w in words
                      if str(w.get("text", "")).upper() == "SCAC"
                      and w.get("page", 0) == 0]
        if not scac_words:
            return ""

        for scac in scac_words:
            scac_x = float(scac["x0"])
            scac_y = float(scac["top"])

            # SCAC 오른쪽 같은 줄에서 2~4자 선사코드 탐색
            carrier_code_w = None
            for w in words:
                if w.get("page", 0) != 0:
                    continue
                wx0 = float(w["x0"])
                wy  = float(w["top"])
                txt = str(w.get("text", "")).upper()
                if wx0 <= scac_x:
                    continue
                if abs(wy - scac_y) > 6:    # 같은 줄
                    continue
                if not re.match(r'^[A-Z]{2,4}$', txt):
                    continue
                carrier_code_w = w
                break   # 첫 번째 코드만

            if not carrier_code_w:
                continue

            code_x = float(carrier_code_w["x0"])
            code_y = float(carrier_code_w["top"])

            logger.debug(
                f"[BL] SCAC 패턴: 선사코드='{carrier_code_w['text']}' "
                f"x={code_x/page_w*100:.1f}%"
            )

            # 선사코드 바로 아래 숫자 탐색 (y +8~50px, x ±30px)
            candidates = []
            for w in words:
                if w.get("page", 0) != 0:
                    continue
                wx0 = float(w["x0"])
                wy  = float(w["top"])
                txt = str(w.get("text", ""))
                dy  = wy - code_y
                dx  = abs(wx0 - code_x)
                if not (8 <= dy <= 50):
                    continue
                if dx > 30:
                    continue
                # v9.0: 순수숫자(MAERSK) + 영문+숫자 혼합(MSC/COSCO) 모두 대응
                t_norm = re.sub(r'[^A-Z0-9]', '', txt.upper())
                is_num = bool(re.match(r'^\d{7,15}$', txt))
                is_mix = (
                    bool(re.match(r'^[A-Z0-9]{6,20}$', t_norm))
                    and bool(re.search(r'\d', t_norm))
                    and bool(re.search(r'[A-Z]', t_norm))
                    and t_norm not in {'NEGOTIABLE','WAYBILL','BOOKING','ORIGINAL'}
                )
                if is_num or is_mix:
                    candidates.append((dy, dx, txt))

            if candidates:
                candidates.sort(key=lambda x: (x[0], x[1]))
                bl_no = self._norm(candidates[0][2])
                if self._looks_like_bl(bl_no):
                    # v9.0: SCAC코드 + BL번호 합치기 (MAEU + 263764814 = MAEU263764814)
                    carrier_code = str(carrier_code_w.get("text", "") or "").upper()
                    full_bl_no   = carrier_code + bl_no
                    logger.info(
                        f"[BL] SCAC 패턴 추출: '{carrier_code}' + '{bl_no}' → '{full_bl_no}'"
                    )
                    return full_bl_no

        return ""

    def _extract_by_top_right_zone(self, words: List[Dict]) -> str:
        if not words:
            return ""
        candidates = []
        for w in words:
            if w["page"] != 0:
                continue
            if w["top"] > w["height"] * 0.18:
                continue
            if w["x0"] < w["width"] * 0.55:
                continue
            if self._looks_like_bl(w["text"]):
                candidates.append(w)
        if not candidates:
            return ""
        best = sorted(candidates, key=lambda x: (x["top"], -x["x0"], -len(self._norm(x["text"]))))[0]
        return self._norm(best["text"])

    def _extract_by_carrier_regex(self, text: str) -> str:
        for m in self.CARRIER_RE.finditer(text or ""):
            token = self._norm(m.group(0))
            if self._looks_like_bl(token):
                return token
        return ""

    def _parse_date_from_text(self, text: str):
        from utils.date_utils import normalize_date
        if not text:
            return None
        parsed = normalize_date(text)
        if parsed:
            return parsed
        for pat in self.SHIP_DATE_PATTERNS:
            m = pat.search(text)
            if m:
                parsed = normalize_date(m.group(0))
                if parsed:
                    return parsed
        return None

    def _page_words(self, words: List[Dict], page_idx: int) -> List[Dict]:
        return [w for w in words if int(w.get("page", -1)) == int(page_idx)]

    def _ordered_pages(self, words: List[Dict]) -> List[int]:
        pages = sorted({int(w.get("page", -1)) for w in words if int(w.get("page", -1)) >= 0})
        preferred = [1, 2, 0]
        out = [p for p in preferred if p in pages]
        for p in pages:
            if p not in out:
                out.append(p)
        return out

    def _sanitize_line(self, text: str) -> str:
        s = self.URL_PATTERN.sub("", text or "")
        s = re.sub(r"\[https?://[^\]]*\]", "", s, flags=re.IGNORECASE)
        return s

    def _extract_ship_date_keyword_anchor(self, words: List[Dict]):
        lines = self._group_lines(words, y_tol=4.0)
        pages = self._ordered_pages(words)
        for page in pages:
            page_words = self._page_words(words, page)
            if not page_words:
                continue
            by_line = {k: v for k, v in lines.items() if k[0] == page}
            for (_p, _b), line in by_line.items():
                line_text = " ".join(w["text"] for w in line)
                up = line_text.upper()
                if "SHIPPED" not in up or "BOARD" not in up:
                    continue
                if "PLACE" in up and "ISSUE" in up:
                    continue
                shipped_x = min((w["x0"] for w in line if str(w["text"]).upper().startswith("SHIPPED")), default=line[0]["x0"])
                candidates = []
                for w in page_words:
                    dy = float(w["top"]) - float(line[0]["top"])
                    if not (3 <= dy <= 60):
                        continue
                    if not (shipped_x - 80 <= float(w["x0"]) <= shipped_x + 220):
                        continue
                    d = self._parse_date_from_text(str(w["text"]))
                    if d:
                        candidates.append((abs(float(w["x0"]) - shipped_x), abs(dy), d))
                if candidates:
                    candidates.sort(key=lambda x: (x[0], x[1]))
                    return candidates[0][2], "keyword_anchor", page + 1
        return None, "", None

    def _extract_ship_date_bottom_zone(self, words: List[Dict]):
        pages = self._ordered_pages(words)
        for page in pages:
            page_words = self._page_words(words, page)
            cands = []
            for w in page_words:
                h = float(w.get("height") or 1.0)
                ww = float(w.get("width") or 1.0)
                y_ratio = float(w["top"]) / h
                x_ratio = float(w["x0"]) / ww
                if y_ratio < 0.75:
                    continue
                if not (0.03 <= x_ratio <= 0.55):
                    continue
                d = self._parse_date_from_text(str(w["text"]))
                if d:
                    cands.append((y_ratio, x_ratio, d))
            if cands:
                cands.sort(key=lambda x: (x[0], x[1]))
                return cands[0][2], "bottom_zone_scan", page + 1
        return None, "", None

    def _extract_ship_date_text_proximity(self, words: List[Dict]):
        lines = self._group_lines(words, y_tol=4.0)
        pages = self._ordered_pages(words)
        for page in pages:
            page_lines = [(k, lines[k]) for k in sorted(lines.keys(), key=lambda x: x[1]) if k[0] == page]
            if not page_lines:
                continue
            line_texts = [self._sanitize_line(" ".join(w["text"] for w in ln)) for _k, ln in page_lines]
            if not any(self.SHIPPED_PATTERN.search(t.upper()) for t in line_texts):
                continue
            for i, t in enumerate(line_texts):
                if not self.SHIPPED_PATTERN.search(t.upper()):
                    continue
                direct = self._parse_date_from_text(t)
                if direct:
                    return direct, "full_text_proximity", page + 1
                for j in range(i + 1, min(i + 7, len(line_texts))):
                    near = self._parse_date_from_text(line_texts[j])
                    if near:
                        return near, "full_text_proximity", page + 1
        return None, "", None

    def _extract_ship_date_v2(self, words: List[Dict]):
        d, m, p = self._extract_ship_date_keyword_anchor(words)
        if d:
            return d, m, p
        d, m, p = self._extract_ship_date_bottom_zone(words)
        if d:
            return d, m, p
        d, m, p = self._extract_ship_date_text_proximity(words)
        if d:
            return d, m, p
        return None, "none", None
