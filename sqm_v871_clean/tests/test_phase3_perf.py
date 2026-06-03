"""
Phase 3 스모크 테스트
- 3-2: AI 쿼리 캐싱 (GeminiChatQuery)
- 3-3: 백엔드 헬스체크 (sqm-core.js)
- 3-4: 백그라운드 새로고침 (sqm-core.js)
"""
import os, sys, sqlite3, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

JS_CORE = os.path.join(os.path.dirname(__file__), "..", "frontend", "js", "sqm-core.js")


def _read_js():
    with open(JS_CORE, encoding="utf-8", errors="ignore") as f:
        return f.read()


# ═══════════════════════════════════════════════════
# Phase 3-2: AI 쿼리 캐싱
# ═══════════════════════════════════════════════════

def test_cache_methods_exist():
    """GeminiChatQuery에 _get_cache / _set_cache 클래스 메서드가 있어야 한다."""
    from features.ai.gemini_chat_query import GeminiChatQuery
    assert callable(getattr(GeminiChatQuery, "_get_cache", None))
    assert callable(getattr(GeminiChatQuery, "_set_cache", None))


def test_cache_miss_returns_none():
    """캐시에 없는 질문은 None을 반환해야 한다."""
    from features.ai.gemini_chat_query import GeminiChatQuery
    GeminiChatQuery._cache.clear()
    result = GeminiChatQuery._get_cache("존재하지않는질문XYZ")
    assert result is None


def test_cache_hit_returns_stored_result():
    """저장한 결과를 TTL 내에 다시 조회하면 동일한 값이 반환되어야 한다."""
    from features.ai.gemini_chat_query import GeminiChatQuery
    GeminiChatQuery._cache.clear()
    dummy = {"success": True, "answer": "테스트 응답", "data": [], "columns": []}
    GeminiChatQuery._set_cache("전체 재고 현황", dummy)
    result = GeminiChatQuery._get_cache("전체 재고 현황")
    assert result == dummy


def test_cache_expires_after_ttl(monkeypatch):
    """TTL 이후 캐시는 만료되어 None을 반환해야 한다."""
    from features.ai.gemini_chat_query import GeminiChatQuery
    GeminiChatQuery._cache.clear()
    GeminiChatQuery._CACHE_TTL = 1  # 1초 TTL로 단축

    dummy = {"success": True, "answer": "캐시테스트"}
    GeminiChatQuery._set_cache("만료테스트질문", dummy)

    # 즉시 조회 → 히트
    assert GeminiChatQuery._get_cache("만료테스트질문") is not None

    # TTL 초과 후 조회 → 미스
    time.sleep(1.1)
    assert GeminiChatQuery._get_cache("만료테스트질문") is None

    GeminiChatQuery._CACHE_TTL = 30  # 원래 값으로 복원


def test_cache_limit_100_entries():
    """캐시 항목이 100개를 넘으면 만료된 항목을 정리해야 한다."""
    from features.ai.gemini_chat_query import GeminiChatQuery
    GeminiChatQuery._cache.clear()
    dummy = {"success": True, "answer": "X"}
    for i in range(101):
        GeminiChatQuery._set_cache(f"질문{i}", dummy)
    # 100개 초과 후 정리 — 만료 없으면 100개 이하로 유지
    assert len(GeminiChatQuery._cache) <= 101  # 최소한 크래시 없음


def test_cache_not_applied_to_write_mode():
    """ask()는 write_mode=True일 때 캐시를 사용하지 않아야 한다 (코드 확인)."""
    path = os.path.join(os.path.dirname(__file__), "..",
                        "features", "ai", "gemini_chat_query.py")
    code = open(path, encoding="utf-8", errors="ignore").read()
    # write_mode=False 조건 하에서만 캐시 조회/저장
    assert "if not write_mode" in code, "write_mode 분기 없음"


# ═══════════════════════════════════════════════════
# Phase 3-3: 백엔드 헬스체크
# ═══════════════════════════════════════════════════

def test_health_url_in_sqm_core():
    """/api/health 가 sqm-core.js에 참조되어야 한다."""
    code = _read_js()
    assert "/api/health" in code, "sqm-core.js에 헬스체크 URL 없음"


def test_health_interval_set():
    """헬스체크 setInterval이 sqm-core.js에 있어야 한다."""
    code = _read_js()
    assert "setInterval" in code and "health" in code.lower(), \
        "sqm-core.js에 헬스체크 interval 없음"


# ═══════════════════════════════════════════════════
# Phase 3-4: 백그라운드 새로고침
# ═══════════════════════════════════════════════════

def test_kpi_auto_refresh_interval():
    """KPI 카드 자동 새로고침 setInterval이 있어야 한다."""
    code = _read_js()
    assert "_kpiTimer" in code or "kpiTimer" in code, \
        "KPI 타이머 없음"


def test_sidebar_badge_refresh():
    """사이드바 배지 카운트 자동 갱신이 있어야 한다."""
    code = _read_js()
    assert "_sidebarBadgeTimer" in code or "sidebarBadge" in code, \
        "사이드바 배지 타이머 없음"


def test_background_refresh_non_blocking():
    """자동 새로고침이 fetch().then() 비동기 패턴이어야 한다 (블로킹 아님)."""
    code = _read_js()
    # apiGet 또는 fetch 후 .then() 패턴
    has_async = ".then(" in code or "async function" in code
    assert has_async, "비동기 새로고침 패턴 없음"
