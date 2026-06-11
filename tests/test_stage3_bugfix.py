# -*- coding: utf-8 -*-
"""3단계 버그 수정 스모크 테스트 — F-9/11/12, B-11, D-7/8/9"""
import os, sys, sqlite3, pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ═══════════════════════════════════════
# F-9: Ctrl+3 중복 case 제거
# ═══════════════════════════════════════
class TestF9_ShortcutDedup:
    def test_no_duplicate_c3_case(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-core.js'), encoding='utf-8').read()
        # switch 블록에서 C-3 횟수 확인
        import re
        cases = re.findall(r"case 'C-3'", src)
        assert len(cases) == 1, f"C-3 case가 {len(cases)}개 — 중복 남아있음"

    def test_picked_has_cp_shortcut(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-core.js'), encoding='utf-8').read()
        assert "case 'C-p'" in src, "picked 탭 단축키 C-p 없음"
        assert "renderPage('picked')" in src


# ═══════════════════════════════════════
# F-11: renderPage 포워더 별칭 추가
# ═══════════════════════════════════════
class TestF11_RenderPageAlias:
    def test_navigate_and_sync_alias_exists(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-inline.js'), encoding='utf-8').read()
        assert '_navigateAndSync' in src, \
            "sqm-inline.js에 _navigateAndSync 별칭 없음"

    def test_renderpage_forwarder_delegates_to_window(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-inline.js'), encoding='utf-8').read()
        func_start = src.index('function renderPage(route)')
        func_end = src.index('\n  }', func_start) + 4
        func_body = src[func_start:func_end]
        assert 'window.renderPage(route)' in func_body, \
            "renderPage 포워더가 window.renderPage 위임 안 함"


# ═══════════════════════════════════════
# F-12: showToast 안전 폴백
# ═══════════════════════════════════════
class TestF12_ShowToastGuard:
    def test_showtoast_fallback_in_inline(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-inline.js'), encoding='utf-8').read()
        assert 'typeof window.showToast' in src, \
            "sqm-inline.js showToast 안전 폴백 없음"

    def test_showtoast_fallback_has_console_warn(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-inline.js'), encoding='utf-8').read()
        # 폴백 함수 내 console.warn 존재
        fallback_start = src.index('function showToast(type, msg)')
        fallback_end = src.index('\n  }', fallback_start) + 4
        fallback_body = src[fallback_start:fallback_end]
        assert 'console.warn' in fallback_body


# ═══════════════════════════════════════
# B-11: action prefix 명세 주석
# ═══════════════════════════════════════
class TestB11_ActionPrefix:
    def test_action_prefix_documented(self):
        src = open(os.path.join(ROOT, 'backend/api/actions.py'), encoding='utf-8').read()
        assert 'prefix 규칙' in src or 'B-11' in src, \
            "actions.py에 prefix 명세 주석 없음"


# ═══════════════════════════════════════
# D-7: db_schema_mixin 중복 마이그레이션 제거
# ═══════════════════════════════════════
class TestD7_MigrationDedup:
    def test_schema_mixin_no_duplicate_v289(self):
        src = open(os.path.join(ROOT, 'engine_modules/db_schema_mixin.py'), encoding='utf-8').read()
        # _migrate_v289_picking_list 호출이 1개 이하여야 함 (주석 제외 실제 호출)
        lines = [l for l in src.splitlines()
                 if '_migrate_v289_picking_list()' in l and not l.strip().startswith('#')]
        assert len(lines) == 0, \
            f"db_schema_mixin에 _migrate_v289 중복 호출 {len(lines)}개 남아있음"

    def test_schema_mixin_uses_pass(self):
        src = open(os.path.join(ROOT, 'engine_modules/db_schema_mixin.py'), encoding='utf-8').read()
        assert 'D-7' in src or '_run_all_migrations' in src, \
            "D-7 수정 주석 또는 pass 처리 없음"


# ═══════════════════════════════════════
# D-8: 캐시 fallback 로그 debug로 변경
# ═══════════════════════════════════════
class TestD8_CacheLogLevel:
    def test_fetchone_uses_debug_not_warning(self):
        src = open(os.path.join(ROOT, 'engine_modules/database.py'), encoding='utf-8').read()
        assert 'logger.warning("[DB.fetchone] 캐시' not in src, \
            "DB.fetchone 캐시 폴백 로그가 여전히 warning 레벨"

    def test_fetchall_uses_debug_not_warning(self):
        src = open(os.path.join(ROOT, 'engine_modules/database.py'), encoding='utf-8').read()
        assert 'logger.warning("[DB.fetchall] 캐시' not in src, \
            "DB.fetchall 캐시 폴백 로그가 여전히 warning 레벨"

    def test_debug_log_present(self):
        src = open(os.path.join(ROOT, 'engine_modules/database.py'), encoding='utf-8').read()
        assert 'logger.debug("[DB.fetchone] 캐시' in src
        assert 'logger.debug("[DB.fetchall] 캐시' in src


# ═══════════════════════════════════════
# D-9: uvicorn TOCTOU 재시도 로직
# ═══════════════════════════════════════
class TestD9_PortRetry:
    def test_address_already_in_use_retry(self):
        src = open(os.path.join(ROOT, 'main_webview.py'), encoding='utf-8').read()
        assert 'address already in use' in src.lower(), \
            "main_webview.py에 포트 충돌 재시도 로직 없음"

    def test_retry_increments_port(self):
        src = open(os.path.join(ROOT, 'main_webview.py'), encoding='utf-8').read()
        assert 'API_PORT += 1' in src, \
            "포트 재시도 시 API_PORT 증가 로직 없음"

    def test_max_retry_limit(self):
        src = open(os.path.join(ROOT, 'main_webview.py'), encoding='utf-8').read()
        assert '_max_retry' in src, "재시도 횟수 제한 없음"
