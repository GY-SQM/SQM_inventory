# -*- coding: utf-8 -*-
"""
ocr_utils.py - Phase B3/B4 검수센터 OCR + Gemini 폴백

- run_ocr: pytesseract로 이미지에서 텍스트 추출
- run_ocr_with_gemini_fallback: OCR 실패/빈 결과 시 Gemini Vision으로 재시도
"""
import io
import logging
import os

logger = logging.getLogger(__name__)

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from PIL import Image
except Exception:
    Image = None


def run_ocr(pil_image) -> str:
    """PIL Image에서 pytesseract로 텍스트 추출. 실패 시 빈 문자열."""
    if pil_image is None or Image is None:
        return ""
    if pytesseract is None:
        logger.debug("pytesseract 미설치")
        return ""
    try:
        out = pytesseract.image_to_string(pil_image, lang="eng+kor")
        return (out or "").strip()
    except Exception as e:
        logger.warning("OCR(tesseract) 실패: %s", e)
        return ""


def _get_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key and not key.startswith("your-"):
        return key
    try:
        from core.config import get_settings
        key = (get_settings() or {}).get("gemini_api_key", "") or ""
        return str(key).strip()
    except Exception as e:
        logger.debug("get_settings: %s", e)
    return ""


def run_ocr_with_gemini_fallback(pil_image, api_key: str = None) -> str:
    """
    OCR 먼저 시도, 결과가 비어 있거나 너무 짧으면 Gemini Vision으로 재시도.
    pil_image: PIL.Image, api_key: None이면 설정/환경변수에서 조회.
    """
    text = run_ocr(pil_image)
    if text and len(text.strip()) >= 2:
        return text.strip()
    api_key = api_key or _get_gemini_api_key()
    if not api_key:
        return text.strip() if text else ""
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        logger.debug("google-genai 미설치: %s", e)
        return text.strip() if text else ""
    if pil_image is None or Image is None:
        return text.strip() if text else ""
    buf = io.BytesIO()
    try:
        pil_image.save(buf, format="PNG")
        img_bytes = buf.getvalue()
    except Exception as e:
        logger.warning("이미지 PNG 인코딩 실패: %s", e)
        return text.strip() if text else ""
    try:
        client = genai.Client(api_key=api_key)
        contents = [
            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            "Extract all text from this image. Return only the extracted text, no explanation.",
        ]
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=contents,
        )
        out = ""
        if response and response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    out += part.text
        out = (out or "").strip()
        if out:
            logger.debug("Gemini fallback OCR: %d chars", len(out))
            return out
    except Exception as e:
        logger.warning("Gemini OCR fallback 실패: %s", e)
    return text.strip() if text else ""
