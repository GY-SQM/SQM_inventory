# -*- coding: utf-8 -*-
"""Gemini AI 채팅 API — 자연어로 재고 조회."""
import logging
from fastapi import APIRouter, HTTPException

from react_api.utils.db import now_str
from core.config import DB_PATH

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["ai"])


# ── 1. Gemini AI 가용 여부 확인 ───────────────────────────────────────────────
@router.get("/status")
def ai_status():
    """Gemini API 키 설정 여부 및 가용 상태 확인."""
    try:
        import google.generativeai  # noqa
        api_available = True
    except ImportError:
        api_available = False

    api_key = _load_api_key()
    return {
        "available":   api_available and bool(api_key),
        "has_api_key": bool(api_key),
        "library_ok":  api_available,
        "generated_at": now_str(),
    }


# ── 2. 자연어 재고 조회 ───────────────────────────────────────────────────────
@router.post("/chat")
def ai_chat(payload: dict):
    """
    자연어 질문 → Gemini AI + SQL 실행 → 답변 반환.
    payload: { question: str, history: [...] (선택) }
    """
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "question이 필요합니다.")

    try:
        from features.ai.gemini_chat_query import GeminiChatQuery
        api_key = _load_api_key()
        chat = GeminiChatQuery(db_path=DB_PATH, api_key=api_key)
        result = chat.ask(question)
        return {
            "success":    result.get("success", False),
            "answer":     result.get("answer", ""),
            "data":       result.get("data", []),
            "columns":    result.get("columns", []),
            "row_count":  result.get("row_count", 0),
            "query_type": result.get("query_type", ""),
            "elapsed_ms": result.get("elapsed_ms", 0),
            "generated_at": now_str(),
        }
    except ImportError:
        # Gemini 라이브러리 미설치 → 기본 SQL 조회로 폴백
        return _fallback_query(question)
    except Exception as exc:
        logger.error("ai_chat 실패: %s", exc, exc_info=True)
        # 실패해도 폴백으로 응답
        return _fallback_query(question)


# ── 3. PDF 보고서 생성 ────────────────────────────────────────────────────────
@router.post("/report/daily")
def report_daily():
    """일일 재고 현황 PDF 생성 → 파일 경로 반환."""
    try:
        from gui_app_modular.utils.pdf_report_gen import generate_daily_inventory_report
        from react_api.utils.db import get_engine
        with get_engine() as engine:
            path = generate_daily_inventory_report(engine)
        if not path:
            raise HTTPException(500, "reportlab 미설치 또는 데이터 없음")
        return {"success": True, "path": path, "generated_at": now_str()}
    except ImportError as exc:
        raise HTTPException(501, f"PDF 생성 모듈 없음: {exc}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("report_daily 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"일일 보고서 생성 실패: {exc}")


@router.post("/report/monthly")
def report_monthly(payload: dict):
    """월간 실적 PDF 생성 → 파일 경로 반환.
    payload: { year: int, month: int }
    """
    year  = int(payload.get("year")  or 0)
    month = int(payload.get("month") or 0)
    try:
        from gui_app_modular.utils.pdf_report_gen import generate_monthly_report
        from react_api.utils.db import get_engine
        with get_engine() as engine:
            path = generate_monthly_report(engine, year=year or None, month=month or None)
        if not path:
            raise HTTPException(500, "reportlab 미설치 또는 데이터 없음")
        return {"success": True, "path": path, "generated_at": now_str()}
    except ImportError as exc:
        raise HTTPException(501, f"PDF 생성 모듈 없음: {exc}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("report_monthly 실패: %s", exc, exc_info=True)
        raise HTTPException(500, f"월간 보고서 생성 실패: {exc}")


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────
def _load_api_key() -> str:
    """환경변수에서만 API 키 로드 (평문 파일 로드 제거 — P0-6 보안 패치)."""
    import os
    return os.environ.get("GEMINI_API_KEY", "").strip()


def _fallback_query(question: str) -> dict:
    """Gemini 없을 때 키워드 기반 기본 DB 조회."""
    from react_api.utils.db import get_db
    q = question.lower()
    try:
        with get_db() as db:
            if any(k in q for k in ["재고", "available", "현황"]):
                rows = db.fetchall(
                    """SELECT t.lot_no, i.product, t.status, COUNT(*) AS bags,
                              ROUND(SUM(t.weight),1) AS total_kg
                       FROM inventory_tonbag t
                       LEFT JOIN inventory i ON i.lot_no = t.lot_no
                       WHERE t.status = 'AVAILABLE'
                       GROUP BY t.lot_no, i.product
                       ORDER BY total_kg DESC LIMIT 20"""
                ) or []
                return {
                    "success":  True,
                    "answer":   f"AVAILABLE 재고 LOT {len(rows)}건 조회 결과입니다.",
                    "data":     [dict(r) for r in rows],
                    "columns":  ["lot_no", "product", "status", "bags", "total_kg"],
                    "row_count": len(rows),
                    "query_type": "fallback_available",
                    "elapsed_ms": 0,
                    "generated_at": now_str(),
                }
            elif any(k in q for k in ["출고", "sold", "outbound"]):
                rows = db.fetchall(
                    """SELECT lot_no, customer, sold_qty_kg, delivery_date
                       FROM sold_table
                       ORDER BY delivery_date DESC LIMIT 20"""
                ) or []
                return {
                    "success":  True,
                    "answer":   f"최근 출고 {len(rows)}건 조회 결과입니다.",
                    "data":     [dict(r) for r in rows],
                    "columns":  ["lot_no", "customer", "sold_qty_kg", "delivery_date"],
                    "row_count": len(rows),
                    "query_type": "fallback_sold",
                    "elapsed_ms": 0,
                    "generated_at": now_str(),
                }
            else:
                return {
                    "success":  False,
                    "answer":   "Gemini API 키가 설정되지 않았습니다. Settings > Gemini AI 설정에서 API 키를 입력해 주세요.",
                    "data":     [],
                    "columns":  [],
                    "row_count": 0,
                    "query_type": "no_api_key",
                    "elapsed_ms": 0,
                    "generated_at": now_str(),
                }
    except Exception as exc:
        logger.error("fallback_query 실패: %s", exc)
        return {
            "success": False, "answer": str(exc),
            "data": [], "columns": [], "row_count": 0,
            "query_type": "error", "elapsed_ms": 0,
            "generated_at": now_str(),
        }
