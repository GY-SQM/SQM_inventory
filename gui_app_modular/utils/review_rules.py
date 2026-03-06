# -*- coding: utf-8 -*-
"""
review_rules.py - Phase B3/B4 검수센터 규칙 로드 및 자동 적용

- load_rules: DB review_rules 테이블에서 (doc_type, field)별 규칙 목록 조회
- extract_text_by_rule: fitz 페이지에서 규칙 ROI로 텍스트 추출
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import fitz
except Exception:
    fitz = None


def load_rules(db: Any, doc_type: str = None, field: str = None) -> List[Dict]:
    """
    review_rules 테이블에서 규칙 조회.
    db: engine.db (execute 가능한 연결), doc_type/field None이면 전체.
    반환: [{"doc_type", "field", "page_no", "x0","y0","x1","y1", "zoom", "sample_value", "created_at"}, ...]
    """
    if db is None:
        return []
    try:
        if doc_type is not None and field is not None:
            cursor = db.execute(
                """SELECT doc_type, field, page_no, x0, y0, x1, y1, zoom, sample_value, created_at
                   FROM review_rules WHERE doc_type = ? AND field = ?
                   ORDER BY page_no, id""",
                (doc_type, field),
            )
        elif doc_type is not None:
            cursor = db.execute(
                """SELECT doc_type, field, page_no, x0, y0, x1, y1, zoom, sample_value, created_at
                   FROM review_rules WHERE doc_type = ?
                   ORDER BY field, page_no, id""",
                (doc_type,),
            )
        else:
            cursor = db.execute(
                """SELECT doc_type, field, page_no, x0, y0, x1, y1, zoom, sample_value, created_at
                   FROM review_rules ORDER BY doc_type, field, page_no, id"""
            )
        rows = cursor.fetchall() if hasattr(cursor, "fetchall") else []
    except Exception as e:
        logger.debug("load_rules: %s", e)
        return []
    keys = ["doc_type", "field", "page_no", "x0", "y0", "x1", "y1", "zoom", "sample_value", "created_at"]
    out = []
    for row in rows:
        if len(row) >= len(keys):
            out.append(dict(zip(keys, row[: len(keys)])))
        elif len(row) == 10:
            out.append(dict(zip(keys, row)))
    return out


def extract_text_by_rule(page, rule: Dict, zoom: float = None) -> str:
    """
    fitz 페이지에서 rule의 ROI(x0,y0,x1,y1, zoom)로 텍스트 추출.
    rule에 저장된 좌표는 캔버스(줌 적용) 기준이므로, 페이지 좌표로 변환 후 get_text("words")와 교집합.
    """
    if fitz is None or page is None or not rule:
        return ""
    try:
        z = float(rule.get("zoom") or zoom or 1.0)
        x0 = float(rule.get("x0", 0))
        y0 = float(rule.get("y0", 0))
        x1 = float(rule.get("x1", 0))
        y1 = float(rule.get("y1", 0))
        rx0, rx1 = x0 / z, x1 / z
        ry0, ry1 = y0 / z, y1 / z
        rect = fitz.Rect(rx0, ry0, rx1, ry1)
        words = page.get_text("words") or []
        picked = []
        for w in words:
            wx0, wy0, wx1, wy1, word = w[0], w[1], w[2], w[3], w[4]
            wrect = fitz.Rect(wx0, wy0, wx1, wy1)
            if rect.intersects(wrect):
                picked.append((wy0, wx0, word))
        picked.sort(key=lambda t: (t[0], t[1]))
        return " ".join([p[2] for p in picked]).strip()
    except Exception as e:
        logger.debug("extract_text_by_rule: %s", e)
        return ""
