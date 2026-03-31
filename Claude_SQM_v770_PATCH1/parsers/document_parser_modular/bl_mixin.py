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
    BL_TOKEN_RE = re.compile(r"^[A-Z0-9]{6,25}$")
    CARRIER_RE = re.compile(
        r"(?:MEDU[A-Z0-9]{6,10}|MSCU[A-Z0-9]{6,10}|COSU[A-Z0-9]{6,10}|EVER[A-Z0-9]{6,10}|"
        r"YMLU[A-Z0-9]{6,10}|HMMU[A-Z0-9]{6,10}|ONEU[A-Z0-9]{6,10}|HLCU[A-Z0-9]{6,10}|\d{9,15})"
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

    def parse_bl(self, pdf_path: str,
                  gemini_hint: str = '',
                  carrier_template=None) -> Optional[BLData]:
        """
        B/L PDF 파싱 (좌표 기반 단독).

        Args:
            pdf_path:         B/L PDF 파일 경로
            gemini_hint:      v7.3.0 호환 — 좌표 기반 파서에서는 미사용
            carrier_template: v7.7.2 선사별 CarrierTemplate (선사 사전 감지 결과)
        """
        logger.info(f"[BL] 좌표 기반 단독 파싱 시작: {pdf_path}")
        words = self._extract_words(pdf_path, max_pages=3)
        full_text = self._extract_text(pdf_path)
        if not words and not full_text:
            raise RuntimeError("[BL] PDF 텍스트 추출 실패")

        bl_no = ''
        method = ''

        # v7.7.2: 선사 템플릿이 있으면 carrier-specific 추출 먼저
        if carrier_template:
            try:
                import fitz
                from features.ai.bl_carrier_registry import extract_bl_no_by_template
                doc = fitz.open(pdf_path)
                pages_text = [doc[i].get_text() for i in range(len(doc))]
                doc.close()
                bl_no = extract_bl_no_by_template(pages_text, carrier_template)
                # v7.7.2: 숫자 없는 값(마스킹 등)은 무효 처리
                if bl_no and not re.search(r'\d', bl_no):
                    logger.warning(f"[BL] 선사별 추출값 숫자 없음({bl_no!r}) → 폴백")
                    bl_no = ''
                if bl_no:
                    method = f"carrier_{carrier_template.carrier_id}"
                    logger.info(f"[BL] 선사별 추출 성공: {bl_no} ({carrier_template.carrier_id})")
            except Exception as e:
                logger.debug(f"[BL] 선사별 추출 실패(폴백): {e}")

        # 기존 폴백 전략
        if not bl_no:
            bl_no = self._extract_by_keyword_anchor(words)
            method = "keyword_anchor" if bl_no else method
        if not bl_no:
            bl_no = self._extract_by_top_right_zone(words)
            method = "top_right_zone" if bl_no else method
        if not bl_no:
            bl_no = self._extract_by_carrier_regex(full_text)
            method = "carrier_regex" if bl_no else method
        if not bl_no:
            raise RuntimeError("[BL] BL 번호 파싱 실패(좌표 기반 단독 모드)")

        result = BLData()
        result.source_file = pdf_path
        result.parsed_at = datetime.now()
        result.bl_no = bl_no
        result.booking_no = bl_no
        result.raw_text = full_text[:20000] if full_text else ""

        # Ship Date는 신규 좌표 기반 엔진 우선, 실패 시 기존 하이브리드 폴백
        try:
            ship_date, source, page_no = self._extract_ship_date_v2(words)
            if not ship_date:
                from utils.date_utils import extract_ship_date
                ship_date, source, _estimated = extract_ship_date({}, full_text or "")
                page_no = None
            result.shipped_on_board_date = ship_date
            result.ship_date = ship_date
            if ship_date:
                logger.info(f"[BL] Ship Date 파싱 성공: {ship_date} (method={source}, page={page_no})")
        except Exception as e:
            logger.debug(f"[BL] Ship Date 추출 보조 실패(무시): {e}")

        logger.info(f"[BL] 파싱 성공: {bl_no} (method={method})")
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
                return self._norm(best["text"])
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
