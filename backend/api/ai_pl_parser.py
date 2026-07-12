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
def parse_pl(file: UploadFile = File(...)):
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
    content = file.file.read()

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

        # P1(v8.8.x): 문서 신뢰도 점수를 parsing_log 에 영속화 — 역추적용.
        # 비치명: 기록 실패해도 파싱 응답엔 영향 없음.
        try:
            from backend.api import engine, ENGINE_AVAILABLE
            if ENGINE_AVAILABLE and engine is not None:
                _lots = result.get("lots") or []
                engine.db.execute(
                    """INSERT INTO parsing_log
                       (doc_type, source_file, success, lot_count, method,
                        error_msg, confidence_score)
                       VALUES ('PL', ?, ?, ?, 'gemini_confidence', '', ?)""",
                    (fname, 1 if result.get("success") else 0,
                     len(_lots), result.get("doc_confidence")),
                )
        except Exception as _le:
            logger.debug("parse_pl: parsing_log 신뢰도 기록 스킵: %s", _le)

        return result
    except Exception as e:
        logger.exception("parse_pl error")
        raise HTTPException(500, f"파싱 오류: {type(e).__name__}: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception as e:  # MEDIUM: 임시 파일 정리 실패 로깅
            logger.debug("임시 파일 정리 실패: %s", e)
