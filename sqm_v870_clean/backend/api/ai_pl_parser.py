"""
PL 신뢰도 파서 API — POST /api/ai/parse-pl
PDF 업로드 → Gemini Vision 파싱 → 신뢰도 점수 반환
"""
import logging
import os
import sys
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/api/ai", tags=["AI"])
logger = logging.getLogger(__name__)


def _project_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", ".."))


@router.post("/parse-pl", summary="📄 PL 신뢰도 파서 (Gemini Vision)")
async def parse_pl(file: UploadFile = File(...)):
    """
    Packing List PDF를 업로드하면 각 필드 + 신뢰도 점수를 반환.

    Response:
      success: bool
      fields: folio/vessel/product/customer 각각 {value, confidence, status}
      lots: LOT 목록 (lot_no/container_no/net_weight_kg/mxbg 각각 포함)
      doc_confidence: 전체 평균 신뢰도 (%)
      auto_approve: true이면 자동 저장 가능
      review_needed: true이면 수동 검토 필요
      low_confidence_fields: 70% 미만 필드 목록
    """
    from backend.api.ai_gemini import _fresh_api_key

    key, source, model = _fresh_api_key()
    if not key:
        raise HTTPException(400, "Gemini API 키 없음 — AI 설정에서 키를 등록하세요")

    fname = file.filename or "upload.pdf"
    suffix = os.path.splitext(fname)[-1].lower() or ".pdf"
    content = await file.read()

    if not content:
        raise HTTPException(400, "파일이 비어있습니다")
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(413, "파일 크기 50MB 초과")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        root = _project_root()
        if root not in sys.path:
            sys.path.insert(0, root)

        from features.ai.pl_confidence_parser import parse_pl_with_confidence

        result = parse_pl_with_confidence(tmp_path, api_key=key, model=model)
        result["filename"] = fname
        return result
    except Exception as e:
        logger.exception("parse_pl error")
        raise HTTPException(500, f"파싱 오류: {type(e).__name__}: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
