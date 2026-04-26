# -*- coding: utf-8 -*-
"""
[Sprint 2-V] AI Chat — Gemini natural-language inventory query
v864-2 source: features/ai/gemini_chat_gui.py + gemini_chat_query.py
포팅 형태: REST API (POST /api/ai/chat)
"""
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Body

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["ai"])


def _db_path():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    return os.path.join(root, "data", "db", "sqm_inventory.db")


def _get_api_key() -> Optional[str]:
    """settings.ini → keyring → env 순으로 조회."""
    # 1. config._load_settings()
    try:
        from config import _load_settings
        s = _load_settings() or {}
        k = s.get("api_key") or s.get("gemini_api_key")
        if k: return str(k).strip()
    except Exception:
        pass
    # 2. keyring
    try:
        import keyring
        k = keyring.get_password("SQM_Inventory", "GEMINI_API_KEY")
        if k: return str(k).strip()
    except Exception:
        pass
    # 3. env
    return (os.environ.get("GEMINI_API_KEY") or "").strip() or None


_chat_singleton = None


def _get_chat():
    """GeminiChatQuery singleton (재사용)."""
    global _chat_singleton
    if _chat_singleton is not None:
        return _chat_singleton
    api_key = _get_api_key()
    if not api_key:
        raise HTTPException(503, "Gemini API 키 미설정 (설정 → API 키)")
    try:
        from features.ai.gemini_chat_query import GeminiChatQuery
    except ImportError as e:
        raise HTTPException(500, f"GeminiChatQuery import 실패: {e}")
    _chat_singleton = GeminiChatQuery(db_path=_db_path(), api_key=api_key)
    return _chat_singleton


@router.get("/status", summary="AI Chat 상태 조회 [Sprint 2-V]")
def ai_status():
    api_key = _get_api_key()
    return {
        "ok": True,
        "data": {
            "configured": bool(api_key),
            "key_masked": (api_key[:4] + "***" + api_key[-4:]) if api_key and len(api_key) > 8 else "***",
            "model": "gemini-2.5-flash",
            "history_count": len(_chat_singleton.chat_history) if _chat_singleton else 0,
        },
    }


@router.post("/chat", summary="🤖 자연어 재고 조회 [Sprint 2-V]")
def ai_chat(payload: dict = Body(...)):
    """
    payload: { question: str }
    Gemini AI 가 자연어 질문을 분석 → SQL 생성 → DB 조회 → 답변.
    """
    q = (payload or {}).get("question") or ""
    q = str(q).strip()
    if not q:
        raise HTTPException(400, "question 필수")

    chat = _get_chat()
    try:
        result = chat.ask(q)
        # QueryResult dataclass → dict
        if hasattr(result, "__dict__"):
            d = {
                "success":    getattr(result, "success", False),
                "query_type": getattr(result, "query_type", ""),
                "sql":        getattr(result, "sql", ""),
                "data":       getattr(result, "data", []),
                "columns":    getattr(result, "columns", []),
                "row_count":  getattr(result, "row_count", 0),
                "answer":     getattr(result, "answer", ""),
                "error":      getattr(result, "error", ""),
            }
        else:
            d = result if isinstance(result, dict) else {"answer": str(result)}
        return {"ok": bool(d.get("success", True)), "data": d, "message": d.get("answer", "")[:200]}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[ai/chat] 에러: {e}")
        raise HTTPException(500, f"AI Chat 에러: {e}")


@router.post("/clear-history", summary="대화 히스토리 초기화 [Sprint 2-V]")
def clear_history():
    global _chat_singleton
    if _chat_singleton:
        try:
            _chat_singleton.chat_history.clear()
        except Exception:
            pass
    return {"ok": True, "message": "히스토리 초기화됨"}
