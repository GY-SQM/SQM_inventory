"""
PL Confidence Parser — 신뢰도 기반 Packing List 파서
=====================================================
Gemini Vision으로 PL 파일을 파싱하고 각 필드의 신뢰도(0-100)를 반환.

임계값:
  CONFIDENCE_AUTO (95): 이상이면 자동 통과 (초록)
  CONFIDENCE_WARN (70): 이상이면 경고 표시 (노랑, 자동 통과)
  70 미만: 수동 검토 필요 (빨강)
  doc_confidence >= 85 + 빨강 필드 없음: 전체 자동 DB 저장
"""
import base64
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CONFIDENCE_AUTO = 95
CONFIDENCE_WARN = 70
CONFIDENCE_DOC_AUTO = 85

try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


def _pdf_to_parts(pdf_path: str, max_pages: int = 3) -> list:
    """PDF → Gemini Part 목록 (이미지 변환)"""
    if not HAS_PYMUPDF:
        raise ImportError("PyMuPDF 미설치: pip install pymupdf")
    doc = fitz.open(pdf_path)
    parts = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        parts.append({"data": pix.tobytes("png"), "mime_type": "image/png"})
    doc.close()
    return parts


_PROMPT = """다음 Packing List 문서를 분석하여 아래 JSON 형식으로 반환하라.
각 필드는 value/confidence(0-100)/reason을 포함해야 한다.

신뢰도 기준:
95-100: 문서에 명확히 인쇄, 표준 형식
80-94 : 높은 확신, 경미한 불확실성
70-79 : 중간 확신, 비표준 형식 또는 모호성
50-69 : 낮은 확신, 추정값
0-49  : 확신 없음

반환 형식(JSON만, 다른 텍스트 없음):
{
  "folio":    {"value": "", "confidence": 0, "reason": ""},
  "vessel":   {"value": "", "confidence": 0, "reason": ""},
  "product":  {"value": "", "confidence": 0, "reason": ""},
  "customer": {"value": "", "confidence": 0, "reason": ""},
  "lots": [
    {
      "list_no":       {"value": 1,    "confidence": 0, "reason": ""},
      "lot_no":        {"value": "",   "confidence": 0, "reason": ""},
      "container_no":  {"value": "",   "confidence": 0, "reason": ""},
      "net_weight_kg": {"value": 0.0,  "confidence": 0, "reason": ""},
      "mxbg":          {"value": 10,   "confidence": 0, "reason": ""}
    }
  ]
}

주의:
- 컨테이너 번호는 4알파+7숫자(예: MSCU1234567)이면 신뢰도 높게
- LOT 번호는 10자리 숫자이면 신뢰도 높게
- 중량: 유럽식(5.001=5001kg, 점=천단위) / 미국식(5,001=5001kg, 쉼표=천단위) 구분
- 단위가 MT이면 ×1000 변환 후 kg으로 기재"""


def _conf_status(conf: int) -> str:
    if conf >= CONFIDENCE_AUTO:
        return "green"
    if conf >= CONFIDENCE_WARN:
        return "yellow"
    return "red"


def _annotate_field(item: Any, key: str) -> Dict:
    if not isinstance(item, dict):
        item = {"value": item, "confidence": 50, "reason": "형식 불명확"}
    conf = max(0, min(100, int(item.get("confidence", 50))))
    return {
        "value": item.get("value", ""),
        "confidence": conf,
        "reason": item.get("reason", ""),
        "status": _conf_status(conf),
    }


def _score_result(data: Dict) -> Dict[str, Any]:
    fields = {}
    low_conf = []
    all_scores = []

    for key in ("folio", "vessel", "product", "customer"):
        f = _annotate_field(data.get(key, {}), key)
        fields[key] = f
        all_scores.append(f["confidence"])
        if f["confidence"] < CONFIDENCE_WARN:
            low_conf.append({"field": key, "confidence": f["confidence"]})

    lots_out = []
    for lot in data.get("lots", []):
        lot_out = {}
        lot_scores = []
        lot_id = ""
        for field in ("list_no", "lot_no", "container_no", "net_weight_kg", "mxbg"):
            f = _annotate_field(lot.get(field, {}), field)
            lot_out[field] = f
            lot_scores.append(f["confidence"])
            all_scores.append(f["confidence"])
            if field == "lot_no":
                lot_id = str(f["value"])
            if f["confidence"] < CONFIDENCE_WARN:
                low_conf.append({
                    "field": f"LOT[{lot_id}].{field}",
                    "confidence": f["confidence"]
                })
        lot_out["_avg"] = round(sum(lot_scores) / len(lot_scores), 1) if lot_scores else 0
        lots_out.append(lot_out)

    doc_conf = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    auto_approve = doc_conf >= CONFIDENCE_DOC_AUTO and not low_conf

    return {
        "success": True,
        "fields": fields,
        "lots": lots_out,
        "doc_confidence": doc_conf,
        "auto_approve": auto_approve,
        "review_needed": bool(low_conf),
        "low_confidence_fields": low_conf,
        "error": "",
    }


def parse_pl_with_confidence(
    file_path: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
    """
    Packing List PDF를 파싱하고 신뢰도 점수를 함께 반환.

    Returns dict with keys:
      success, fields, lots, doc_confidence, auto_approve,
      review_needed, low_confidence_fields, error
    """
    if not HAS_GEMINI:
        return {"success": False, "error": "google-genai 미설치: pip install google-genai"}
    if not api_key:
        return {"success": False, "error": "Gemini API 키 없음"}

    ext = Path(file_path).suffix.lower()
    if ext != ".pdf":
        return {"success": False, "error": f"PDF만 지원 (받은 확장자: {ext})"}
    if not HAS_PYMUPDF:
        return {"success": False, "error": "PyMuPDF 미설치: pip install pymupdf"}

    try:
        img_parts = _pdf_to_parts(file_path)
    except Exception as e:
        return {"success": False, "error": f"PDF 변환 실패: {e}"}

    try:
        client = genai.Client(api_key=api_key)
        contents = [_PROMPT]
        for p in img_parts:
            contents.append(
                genai.types.Part.from_bytes(data=p["data"], mime_type=p["mime_type"])
            )
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=4096,
            ),
        )
        raw = (resp.text or "").strip()
    except Exception as e:
        logger.exception("Gemini Vision 호출 실패")
        return {"success": False, "error": f"Gemini 호출 실패: {e}"}

    m = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw)
    if m:
        raw = m.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON 파싱 실패: {e}", "raw": raw[:400]}

    return _score_result(data)
