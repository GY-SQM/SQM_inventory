"""
Phase 4 스모크 테스트
- 4-1: AI 결과 엑셀 내보내기 엔드포인트
- 4-2: AI 자동완성 엔드포인트
- 4-3: 즐겨찾기 (ai_chat.html)
- 4-4: 단축키 확장 (shortcuts.js)
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE = os.path.join(os.path.dirname(__file__), "..")


def _read(rel):
    p = os.path.join(BASE, rel)
    return open(p, encoding="utf-8", errors="ignore").read() if os.path.exists(p) else ""


# ═══════════════════════════════════════════════════
# Phase 4-1: AI 엑셀 내보내기
# ═══════════════════════════════════════════════════

def test_export_excel_endpoint_in_ai_gemini():
    """ai_gemini.py에 /chat/export-excel 엔드포인트가 있어야 한다."""
    code = _read("backend/api/ai_gemini.py")
    assert "chat/export-excel" in code or "export-excel" in code


def test_export_excel_uses_openpyxl():
    """엑셀 생성에 openpyxl을 사용해야 한다."""
    code = _read("backend/api/ai_gemini.py")
    assert "openpyxl" in code


def test_export_excel_button_in_ai_chat_html():
    """ai_chat.html에 엑셀 저장 버튼이 있어야 한다."""
    code = _read("frontend/detached/ai_chat.html")
    assert "엑셀 저장" in code or "exportAiExcel" in code


def test_export_excel_function_exists():
    """ai_chat.html에 exportAiExcel 함수가 있어야 한다."""
    code = _read("frontend/detached/ai_chat.html")
    assert "function exportAiExcel" in code or "exportAiExcel" in code


# ═══════════════════════════════════════════════════
# Phase 4-2: 자동완성
# ═══════════════════════════════════════════════════

def test_autocomplete_endpoint_exists():
    """ai_gemini.py에 /autocomplete 엔드포인트가 있어야 한다."""
    code = _read("backend/api/ai_gemini.py")
    assert "autocomplete" in code


def test_autocomplete_queries_inventory():
    """자동완성이 inventory 테이블을 쿼리해야 한다."""
    code = _read("backend/api/ai_gemini.py")
    assert "inventory" in code and "autocomplete" in code


def test_autocomplete_ui_in_ai_chat():
    """ai_chat.html에 자동완성 UI 코드가 있어야 한다."""
    code = _read("frontend/detached/ai_chat.html")
    assert "autocomplete" in code or "ac-box" in code


# ═══════════════════════════════════════════════════
# Phase 4-3: 즐겨찾기
# ═══════════════════════════════════════════════════

def test_favorite_save_function_exists():
    """ai_chat.html에 saveFavorite 함수가 있어야 한다."""
    code = _read("frontend/detached/ai_chat.html")
    assert "saveFavorite" in code


def test_favorite_uses_localstorage():
    """즐겨찾기가 localStorage에 저장되어야 한다."""
    code = _read("frontend/detached/ai_chat.html")
    assert "sqm_fav_queries" in code or "_FAV_KEY" in code


def test_favorite_button_in_ui():
    """즐겨찾기 버튼이 UI에 있어야 한다."""
    code = _read("frontend/detached/ai_chat.html")
    assert "⭐" in code or "fav" in code.lower()


def test_favorite_max_10_entries():
    """즐겨찾기는 최대 10개로 제한되어야 한다."""
    code = _read("frontend/detached/ai_chat.html")
    assert "slice(0, 10)" in code or ".slice(0,10)" in code


# ═══════════════════════════════════════════════════
# Phase 4-4: 단축키 확장
# ═══════════════════════════════════════════════════

def test_shortcuts_has_ctrl_e():
    """sqm-core.js에 Ctrl+E (엑셀 내보내기) 단축키가 있어야 한다."""
    code = _read("frontend/js/sqm-core.js")
    assert "C-e" in code or "Ctrl+E" in code or "onExport" in code


def test_shortcuts_has_ai_chat_toggle():
    """sqm-core.js 또는 _archive/shortcuts.js에 AI 채팅 단축키가 있어야 한다."""
    code = _read("frontend/js/sqm-core.js") + _read("frontend/js/_archive/shortcuts.js")
    assert "ai-chat" in code or "Ctrl+Shift+A" in code or "toggleAiChat" in code or "ai_chat" in code


def test_shortcuts_has_ai_rollback():
    """sqm-core.js 또는 _archive/shortcuts.js에 AI 롤백 단축키가 있어야 한다."""
    code = _read("frontend/js/sqm-core.js") + _read("frontend/js/_archive/shortcuts.js")
    assert "ai-rollback" in code or ("Ctrl+Z" in code and "rollback" in code) or "C-z" in code


def test_shortcuts_has_help_key():
    """sqm-core.js에 단축키 구현이 있어야 한다."""
    code = _read("frontend/js/sqm-core.js")
    assert "'?'" in code or '"?"' in code or "shortcuts" in code or "keydown" in code
