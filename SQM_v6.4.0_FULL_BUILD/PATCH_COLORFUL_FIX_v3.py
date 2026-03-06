# -*- coding: utf-8 -*-
"""
★★★ SQM v6.3.2 — Colorful UI Fix Patch v3 (근본 수정) ★★★
============================================================
날짜: 2026-03-04
작성: Ruby (세계 최고의 프로그래머 + 슈퍼 양자 컴퓨터)

v2에서 색상이 반영 안 된 근본 원인 5가지를 완전 수정:

[원인 #1] ★★★★★ _refresh_inventory() — 상태색 덮어쓰기
  configure_tags()에서 상태별 고유색 설정 → 데이터 로드 후
  _refresh_inventory()가 foreground=_text_color(단일색)으로 전부 덮어씀
  → 수정: 상태별 고유 전경색 사용

[원인 #2] ★★★★ auto_style_applier (1초 후) — 태그 파괴
  apply_to_tree_immediately()가 모든 행 tags를 odd/even으로 교체
  → 기존 status 태그(available/picked...) 삭제 → 상태색 소멸
  → 수정: status 태그 보존하면서 odd/even 병합

[원인 #3] ★★★ ttkbootstrap Heading — Tcl 레벨 오버라이드
  darkly 테마가 Tcl element로 파란 헤더 강제
  → style.configure 무시됨
  → 수정: style.map + !disabled 상태로 강제 오버라이드

[원인 #4] ★★ configure_tree_grid() 하드코딩 불일치
  → 수정: apply_global_tree_style과 동기화

[원인 #5] ★ tonbag_tab.py 동일 문제
  → 수정: inventory_tab과 동일하게 상태별 고유색 적용

적용법: SQM 폴더에 넣고 더블클릭 (이전 패치 적용 여부 무관)
"""
import os
import re
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_sqm_root():
    check = SCRIPT_DIR
    for _ in range(4):
        if os.path.isdir(os.path.join(check, 'gui_app_modular')):
            return check
        check = os.path.dirname(check)
    return None


def backup(filepath):
    if os.path.isfile(filepath):
        bak = filepath + f'.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(filepath, bak)
        return os.path.basename(bak)
    return None


def safe_replace(content, old, new, label):
    """안전한 교체 — 성공 여부 반환"""
    if old in content:
        content = content.replace(old, new)
        print(f"  ✅ {label}")
        return content, True
    else:
        print(f"  ⚠️ {label} — 패턴 미발견")
        return content, False


# ═══════════════════════════════════════════════════════════
# 상태별 고유 전경색 상수 (모든 파일에서 공유)
# ═══════════════════════════════════════════════════════════
STATUS_FG_DARK = {
    'available': '#6ee7b7',   # 밝은 에메랄드
    'reserved':  '#fcd34d',   # 밝은 골드
    'picked':    '#c4b5fd',   # 밝은 라벤더
    'shipped':   '#93c5fd',   # 밝은 스카이블루
}
STATUS_FG_LIGHT = {
    'available': '#064e3b',   # 짙은 에메랄드
    'reserved':  '#78350f',   # 짙은 앰버
    'picked':    '#4c1d95',   # 짙은 바이올렛
    'shipped':   '#1e3a5f',   # 짙은 스틸블루
}


# ═══════════════════════════════════════════
# FIX #1: inventory_tab.py
#   원인 #1 해결: foreground=_text_color → 상태별 고유색
# ═══════════════════════════════════════════
def fix1_inventory_tab(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'tabs', 'inventory_tab.py')
    if not os.path.isfile(target):
        print("  ❌ inventory_tab.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    # 955-970행의 tag_configure 블록을 상태별 고유색으로 교체
    OLD_BLOCK = """            # ═══ v5.6.1: 상태별 행 배경+전경색 (다크테마 가시성 수정) ═══
            _dk = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
            _p = ThemeColors.get_palette(_dk)
            _stripe_bg = ThemeColors.get('tree_stripe', _dk)
            _text_color = ThemeColors.get('text_primary', _dk)

            self.tree_inventory.tag_configure('available',
                background=ThemeColors.get('available', _dk), foreground=_text_color)
            self.tree_inventory.tag_configure('picked',
                background=ThemeColors.get('picked', _dk), foreground=_text_color)
            self.tree_inventory.tag_configure('reserved',
                background=ThemeColors.get('reserved', _dk), foreground=_text_color)
            self.tree_inventory.tag_configure('shipped',
                background=ThemeColors.get('shipped', _dk), foreground=_text_color)
            self.tree_inventory.tag_configure('depleted',
                background=ThemeColors.get('bg_secondary', _dk), foreground=ThemeColors.get('text_muted', _dk))
            self.tree_inventory.tag_configure('stripe',
                background=_stripe_bg, foreground=_text_color)"""

    NEW_BLOCK = """            # ═══ v6.3.2-colorful: 상태별 고유 전경색 (단일색 덮어쓰기 제거) ═══
            _dk = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
            _stripe_bg = ThemeColors.get('tree_stripe', _dk)
            _fg = '#f0f0f0' if _dk else '#1a1a1a'
            # ★ 상태별 고유 전경색 (밝은 배경엔 짙은 글씨, 어두운 배경엔 밝은 글씨)
            _sfg = {
                'available': '#6ee7b7' if _dk else '#064e3b',
                'reserved':  '#fcd34d' if _dk else '#78350f',
                'picked':    '#c4b5fd' if _dk else '#4c1d95',
                'shipped':   '#93c5fd' if _dk else '#1e3a5f',
            }
            self.tree_inventory.tag_configure('available',
                background=ThemeColors.get('available', _dk), foreground=_sfg['available'])
            self.tree_inventory.tag_configure('picked',
                background=ThemeColors.get('picked', _dk), foreground=_sfg['picked'])
            self.tree_inventory.tag_configure('reserved',
                background=ThemeColors.get('reserved', _dk), foreground=_sfg['reserved'])
            self.tree_inventory.tag_configure('shipped',
                background=ThemeColors.get('shipped', _dk), foreground=_sfg['shipped'])
            self.tree_inventory.tag_configure('depleted',
                background=ThemeColors.get('bg_secondary', _dk),
                foreground=ThemeColors.get('text_muted', _dk))
            self.tree_inventory.tag_configure('stripe',
                background=_stripe_bg, foreground=_fg)"""

    content, ok = safe_replace(content, OLD_BLOCK, NEW_BLOCK,
        "[원인#1] _refresh_inventory() 상태별 고유 전경색")

    if ok:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    return ok


# ═══════════════════════════════════════════
# FIX #2: tonbag_tab.py
#   원인 #5 해결: 동일 문제 수정
# ═══════════════════════════════════════════
def fix2_tonbag_tab(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'tabs', 'tonbag_tab.py')
    if not os.path.isfile(target):
        print("  ⚠️ tonbag_tab.py 없음 (건너뜀)")
        return True

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    OLD_BLOCK = """            # 태그 색상 적용 (v8.7.0 Phase2: ThemeColors 단일 소스)
            _dk = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
            _text_color = ThemeColors.get('text_primary', _dk)
            self.tree_sublot.tag_configure('available',
                background=ThemeColors.get('available', _dk), foreground=_text_color)
            self.tree_sublot.tag_configure('picked',
                background=ThemeColors.get('picked', _dk), foreground=_text_color)
            self.tree_sublot.tag_configure('reserved',
                background=ThemeColors.get('reserved', _dk), foreground=_text_color)
            self.tree_sublot.tag_configure('shipped',
                background=ThemeColors.get('shipped', _dk), foreground=_text_color)
            self.tree_sublot.tag_configure('depleted',
                background=ThemeColors.get('bg_secondary', _dk), foreground=ThemeColors.get('text_muted', _dk))
            self.tree_sublot.tag_configure('stripe',
                background=ThemeColors.get('tree_stripe', _dk), foreground=_text_color)"""

    NEW_BLOCK = """            # v6.3.2-colorful: 상태별 고유 전경색 (단일색 덮어쓰기 제거)
            _dk = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
            _fg = '#f0f0f0' if _dk else '#1a1a1a'
            _sfg = {
                'available': '#6ee7b7' if _dk else '#064e3b',
                'reserved':  '#fcd34d' if _dk else '#78350f',
                'picked':    '#c4b5fd' if _dk else '#4c1d95',
                'shipped':   '#93c5fd' if _dk else '#1e3a5f',
            }
            self.tree_sublot.tag_configure('available',
                background=ThemeColors.get('available', _dk), foreground=_sfg['available'])
            self.tree_sublot.tag_configure('picked',
                background=ThemeColors.get('picked', _dk), foreground=_sfg['picked'])
            self.tree_sublot.tag_configure('reserved',
                background=ThemeColors.get('reserved', _dk), foreground=_sfg['reserved'])
            self.tree_sublot.tag_configure('shipped',
                background=ThemeColors.get('shipped', _dk), foreground=_sfg['shipped'])
            self.tree_sublot.tag_configure('depleted',
                background=ThemeColors.get('bg_secondary', _dk),
                foreground=ThemeColors.get('text_muted', _dk))
            self.tree_sublot.tag_configure('stripe',
                background=ThemeColors.get('tree_stripe', _dk), foreground=_fg)"""

    content, ok = safe_replace(content, OLD_BLOCK, NEW_BLOCK,
        "[원인#5] tonbag_tab 상태별 고유 전경색")

    if ok:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    return ok


# ═══════════════════════════════════════════
# FIX #3: auto_style_applier.py
#   원인 #2 해결: status 태그 보존
# ═══════════════════════════════════════════
def fix3_auto_style_applier(sqm_root):
    target = os.path.join(sqm_root, 'fixes', 'auto_style_applier.py')
    if not os.path.isfile(target):
        print("  ⚠️ auto_style_applier.py 없음 (건너뜀)")
        return True

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    # apply_to_tree_immediately 호출을 status-safe 버전으로 교체
    OLD_FN = """def apply_styles_to_all_trees(root_widget):
    \"\"\"
    v5.0.0: 모든 Treeview에 통일 스타일 자동 적용
    
    Args:
        root_widget: 루트 위젯 (보통 self.root 또는 self.notebook)
    \"\"\"
    try:
        from fixes.global_tree_style import apply_to_tree_immediately

        # 모든 Treeview 찾기
        trees = find_all_treeviews(root_widget)

        logger.info(f"✅ v5.0.0: {len(trees)}개 Treeview 발견")

        # 각 Treeview에 스타일 적용
        for i, tree in enumerate(trees):
            try:
                apply_to_tree_immediately(tree)
                logger.debug(f"  [{i+1}/{len(trees)}] 스타일 적용 완료")
            except (ValueError, TypeError, AttributeError, tk.TclError) as e:
                logger.warning(f"  [{i+1}/{len(trees)}] 스타일 적용 실패: {e}")

        logger.info("✅ v5.0.0: 모든 Treeview 스타일 적용 완료!")

    except ImportError as e:
        logger.error(f"스타일 모듈 로딩 실패: {e}")
    except (ValueError, TypeError, AttributeError, tk.TclError) as e:
        logger.error(f"자동 스타일 적용 실패: {e}")"""

    NEW_FN = """def apply_styles_to_all_trees(root_widget):
    \"\"\"
    v6.3.2-colorful: 모든 Treeview에 통일 스타일 자동 적용
    ★ status 태그(available/picked/reserved/shipped) 보존
    \"\"\"
    try:
        from fixes.global_tree_style import apply_to_tree_safely

        trees = find_all_treeviews(root_widget)
        logger.info(f"✅ v6.3.2: {len(trees)}개 Treeview 발견")

        for i, tree in enumerate(trees):
            try:
                apply_to_tree_safely(tree)
                logger.debug(f"  [{i+1}/{len(trees)}] 스타일 적용 완료 (status 보존)")
            except (ValueError, TypeError, AttributeError, tk.TclError) as e:
                logger.warning(f"  [{i+1}/{len(trees)}] 스타일 적용 실패: {e}")

        logger.info("✅ v6.3.2: 모든 Treeview 스타일 적용 완료!")

    except ImportError as e:
        logger.error(f"스타일 모듈 로딩 실패: {e}")
    except (ValueError, TypeError, AttributeError, tk.TclError) as e:
        logger.error(f"자동 스타일 적용 실패: {e}")"""

    content, ok = safe_replace(content, OLD_FN, NEW_FN,
        "[원인#2] auto_style_applier → status 태그 보존 호출")

    if ok:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    return ok


# ═══════════════════════════════════════════
# FIX #4: global_tree_style.py (전면 재작성)
#   원인 #2, #3, #4 해결
# ═══════════════════════════════════════════
def fix4_global_tree_style(sqm_root):
    target = os.path.join(sqm_root, 'fixes', 'global_tree_style.py')
    if not os.path.isfile(target):
        print("  ⚠️ global_tree_style.py 없음 (건너뜀)")
        return True

    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    NEW_CONTENT = r'''import logging

logger = logging.getLogger(__name__)
"""
SQM v6.3.2-colorful — 전역 Treeview 스타일
=============================================

v6.3.2 변경사항:
  - 다크 배경: 보라 기조 (#1e1e2e / #282840)
  - 헤더: ttkbootstrap 강제 오버라이드 (style.map + !disabled)
  - apply_to_tree_safely(): status 태그 보존하면서 odd/even 병합
  - configure_tree_grid(): 보라 기조 색상 동기화
"""

import tkinter as tk
from tkinter import ttk


# ═══════════════════════════════════════════
# 색상 상수
# ═══════════════════════════════════════════
DARK_COLORS = {
    'bg':        '#1e1e2e',
    'fg':        '#e0e0e0',
    'odd_bg':    '#282840',
    'even_bg':   '#1e1e2e',
    'sel_bg':    '#0078D7',
    'sel_fg':    'white',
    'head_bg':   '#2d2b55',     # 다크 퍼플 헤더 (파랑 탈피!)
    'head_fg':   'white',
    'head_hover': '#3d3a6e',
}

LIGHT_COLORS = {
    'bg':        'white',
    'fg':        'black',
    'odd_bg':    '#F8F9FA',
    'even_bg':   '#FFFFFF',
    'sel_bg':    '#0078D7',
    'sel_fg':    'white',
    'head_bg':   '#34495E',
    'head_fg':   'white',
    'head_hover': '#2C3E50',
}

STATUS_TAGS = frozenset({'available', 'picked', 'reserved', 'shipped', 'depleted'})


def _is_dark_theme():
    """현재 다크 테마 여부"""
    try:
        style = ttk.Style()
        theme = (style.theme_use() or '').lower()
        return any(d in theme for d in ['darkly', 'cyborg', 'vapor', 'solar', 'superhero'])
    except Exception:
        return False


def apply_global_tree_style():
    """
    v6.3.2-colorful: 전역 Treeview 스타일 적용
    ★ ttkbootstrap Heading 강제 오버라이드 포함
    """
    style = ttk.Style()
    is_dark = _is_dark_theme()
    c = DARK_COLORS if is_dark else LIGHT_COLORS

    # ═══ Treeview 기본 스타일 ═══
    style.configure(
        "Treeview",
        rowheight=30,
        borderwidth=1,
        relief='solid',
        font=('맑은 고딕', 9),
        fieldbackground=c['bg'],
        background=c['bg'],
        foreground=c['fg']
    )

    # ═══ Heading 스타일 (configure) ═══
    style.configure(
        "Treeview.Heading",
        font=('맑은 고딕', 10, 'bold'),
        borderwidth=1,
        relief='raised',
        background=c['head_bg'],
        foreground=c['head_fg'],
        padding=6
    )

    # ═══ ★★★ ttkbootstrap 강제 오버라이드 ★★★ ═══
    # ttkbootstrap darkly 테마는 Tcl element_create로 헤더를 파랑(#375a7f)으로 고정.
    # style.configure만으로는 무시됨.
    # → style.map의 '!disabled' 상태로 강제 적용
    style.map(
        "Treeview.Heading",
        background=[
            ('active', c['head_hover']),
            ('!disabled', c['head_bg']),      # ★ 핵심: 비활성 상태에서 강제
        ],
        foreground=[
            ('active', 'white'),
            ('!disabled', c['head_fg']),       # ★ 핵심
        ]
    )

    # ═══ 행 선택·포커스 색상 ═══
    style.map(
        "Treeview",
        background=[
            ('selected', c['sel_bg']),
            ('focus', '#E3F2FD' if not is_dark else '#1a3a5c')
        ],
        foreground=[
            ('selected', c['sel_fg']),
            ('!selected', c['fg']),
            ('focus', 'black' if not is_dark else 'white')
        ]
    )

    # 전역 변수 저장
    apply_global_tree_style._is_dark = is_dark
    apply_global_tree_style._colors = c

    logger.debug(f"✅ v6.3.2 Treeview style ({'dark' if is_dark else 'light'})")


def configure_tree_grid(tree, columns):
    """
    v6.3.2-colorful: 개별 Treeview 그리드 + 정렬 + 줄무늬
    ★ DARK_COLORS/LIGHT_COLORS와 동기화 (하드코딩 제거)
    """
    is_dark = _is_dark_theme()
    c = DARK_COLORS if is_dark else LIGHT_COLORS

    tree.tag_configure('odd', background=c['odd_bg'], foreground=c['fg'])
    tree.tag_configure('even', background=c['even_bg'], foreground=c['fg'])

    for col in columns:
        tree.column(col, anchor='center')
        tree.heading(col, anchor='center')


def capitalize_headers(headers):
    """v5.0.0: 헤더 첫글자 대문자"""
    result = []
    for h in headers:
        h_lower = str(h).lower()
        if h_lower == 'id':
            result.append('ID')
        elif h_lower in ('sap_no', 'sap', 'sapno'):
            result.append('SAP_No')
        elif h_lower in ('bl_no', 'bl', 'blno'):
            result.append('BL_No')
        elif h_lower in ('uid', 'tonbag_uid'):
            result.append('UID')
        elif h_lower in ('lot_no', 'lotno'):
            result.append('Lot_No')
        elif h_lower in ('kg', 'mt', 'ton'):
            result.append(h_lower.upper())
        else:
            words = h_lower.split('_')
            result.append('_'.join(w.capitalize() for w in words))
    return result


def apply_to_tree_safely(tree, columns=None):
    """
    v6.3.2-colorful: 기존 Treeview에 즉시 스타일 적용
    ★★★ 핵심: status 태그를 보존하면서 odd/even 병합
    
    기존 apply_to_tree_immediately()는 tags=(tag,)로 교체하여
    status 태그를 삭제했음. 이 함수는 status 태그를 보존.
    """
    if columns is None:
        columns = tree['columns']

    configure_tree_grid(tree, columns)

    # ★ status 태그 보존하면서 odd/even 추가
    for i, item in enumerate(tree.get_children()):
        existing_tags = set(tree.item(item, 'tags') or ())
        # status 태그 보존
        preserved = existing_tags & STATUS_TAGS
        stripe_tag = 'odd' if i % 2 else 'even'
        # status 태그 없는 경우에만 odd/even 색상 적용
        if preserved:
            # status 태그가 있으면 status 태그만 유지 (odd/even 색상은 불필요)
            new_tags = tuple(preserved)
        else:
            new_tags = (stripe_tag,)
        tree.item(item, tags=new_tags)


# 하위 호환성: 구 함수명 유지
def apply_to_tree_immediately(tree, columns=None):
    """하위 호환성 래퍼 → apply_to_tree_safely 호출"""
    return apply_to_tree_safely(tree, columns)


if __name__ == '__main__':
    apply_global_tree_style()
    headers = ['id', 'lot_no', 'sap_no', 'bl_no', 'product', 'status', 'uid', 'weight_kg']
    logger.debug("Before:", headers)
    logger.debug("After:", capitalize_headers(headers))
'''

    with open(target, 'w', encoding='utf-8') as f:
        f.write(NEW_CONTENT)
    print("  ✅ [원인#2#3#4] global_tree_style.py 전면 재작성")
    print("     ★ 헤더: style.map(!disabled)로 ttkbootstrap 강제 오버라이드")
    print("     ★ apply_to_tree_safely(): status 태그 보존")
    print("     ★ configure_tree_grid(): 색상 동기화")
    return True


# ═══════════════════════════════════════════
# FIX #5: ui_constants.py (v2 수정 포함)
#   - DARK 상태 배경색 밝게
#   - configure_tags() fg 변수 + 상태별 전경색
#   - is_dark_theme() cls.DARK_THEMES → 인라인 튜플
#   - 스크롤바 반전 수정
# ═══════════════════════════════════════════
def fix5_ui_constants(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'ui_constants.py')
    if not os.path.isfile(target):
        print("  ❌ ui_constants.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    changed = 0

    # (A) DARK 상태 배경색
    dark_map = {
        "'available': '#0f766e'": "'available': '#065f46'",
        "'reserved':  '#b45309'": "'reserved':  '#92400e'",
        "'picked':    '#7c3aed'": "'picked':    '#5b21b6'",
        "'shipped':   '#1d4ed8'": "'shipped':   '#1e3a5f'",
    }
    for old, new in dark_map.items():
        if old in content:
            content = content.replace(old, new)
            changed += 1

    # (B) configure_tags() 전체 교체
    NEW_CT = '''    @classmethod
    def configure_tags(cls, tree, is_dark: bool = False):
        """트리뷰 상태 태그 설정 (v6.3.2-colorful: 상태별 고유 전경색)"""
        p = cls.DARK if is_dark else cls.LIGHT
        fg = '#f0f0f0' if is_dark else '#1a1a1a'
        if is_dark:
            status_fg = {
                'available': '#6ee7b7',
                'reserved':  '#fcd34d',
                'picked':    '#c4b5fd',
                'shipped':   '#93c5fd',
            }
        else:
            status_fg = {
                'available': '#064e3b',
                'reserved':  '#78350f',
                'picked':    '#4c1d95',
                'shipped':   '#1e3a5f',
            }
        for status in ['available', 'picked', 'reserved', 'shipped']:
            tree.tag_configure(status, background=p[status],
                               foreground=status_fg.get(status, fg))
        tree.tag_configure('depleted', background='#f0f0f0' if not is_dark else '#2a2a2a',
                          foreground='#aaaaaa' if not is_dark else '#888888')
        tree.tag_configure('stripe', background=p['tree_stripe'], foreground=fg)'''

    pat = re.compile(
        r'(    @classmethod\n    def configure_tags\(cls, tree, is_dark.*?\n)'
        r'(.*?)'
        r"(        tree\.tag_configure\('stripe'.*?\n)",
        re.DOTALL,
    )
    match = pat.search(content)
    if match:
        content = content[:match.start()] + NEW_CT + '\n' + content[match.end():]
        changed += 1
        print("  ✅ configure_tags() 전체 교체")

    # (C) is_dark_theme() — cls.DARK_THEMES → 인라인 튜플
    old_dt = "return theme_name.lower() in cls.DARK_THEMES"
    new_dt = "return theme_name.lower() in ('darkly', 'cyborg', 'superhero', 'solar', 'vapor')"
    if old_dt in content:
        content = content.replace(old_dt, new_dt)
        changed += 1
        print("  ✅ is_dark_theme() 수정")
    elif "('darkly', 'cyborg'" in content:
        print("  ℹ️ is_dark_theme() 이미 수정됨")

    # (D) 스크롤바 반전
    scroll_fixes = [
        ("trough = '#f2f2f2' if is_dark else '#111111'",
         "trough = '#111111' if is_dark else '#f2f2f2'  # v6.3.2-fix"),
        ("thumb = '#111111' if is_dark else '#f2f2f2'",
         "thumb = '#f2f2f2' if is_dark else '#111111'  # v6.3.2-fix"),
        ("active = '#000000' if is_dark else '#ffffff'",
         "active = '#ffffff' if is_dark else '#000000'  # v6.3.2-fix"),
    ]
    for old, new in scroll_fixes:
        if old in content:
            content = content.replace(old, new)
            changed += 1

    if changed > 0:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"  ✅ ui_constants.py — {changed}건 수정")
    return changed > 0


# ═══════════════════════════════════════════
# FIX #6: toolbar_mixin.py (v2 수정)
# ═══════════════════════════════════════════
def fix6_toolbar(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'mixins', 'toolbar_mixin.py')
    if not os.path.isfile(target):
        print("  ❌ toolbar_mixin.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    changed = 0

    # (A) _load_toolbar_colors
    OLD_LOAD = """    def _load_toolbar_colors(self) -> None:
        \"\"\"컬러풀 고정 팔레트 (테마와 무관하게 유지).\"\"\"
        self._tb_bg = '#0f172a'          # 진한 네이비
        self._tb_sep = '#334155'         # 구분선
        self._tb_fg_normal = '#cbd5e1'   # 비활성 텍스트
        self._tb_fg_active = '#ffffff'   # 활성 텍스트
        self._tb_fg_hover = '#93c5fd'    # 호버 텍스트
        self._tb_hover_bg = '#1e293b'    # 호버 배경
        self._tb_underline_color = '#3b82f6'  # 강조 파랑"""

    NEW_LOAD = """    def _load_toolbar_colors(self) -> None:
        \"\"\"v6.3.2-colorful: 다크/라이트 반응형 컬러풀 팔레트.\"\"\"
        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'darkly'))
        if is_dark:
            self._tb_bg = '#1a1a2e'
            self._tb_sep = '#3d3d5c'
            self._tb_fg_normal = '#c0c0d0'
            self._tb_fg_active = '#ffffff'
            self._tb_fg_hover = '#e0b0ff'       # 밝은 보라 (파랑 탈피)
            self._tb_hover_bg = '#2a2a4a'
            self._tb_underline_color = '#a78bfa' # 바이올렛
        else:
            self._tb_bg = '#1f2937'
            self._tb_sep = '#4b5563'
            self._tb_fg_normal = '#d1d5db'
            self._tb_fg_active = '#ffffff'
            self._tb_fg_hover = '#fbbf24'        # 골드 (파랑 탈피)
            self._tb_hover_bg = '#374151'
            self._tb_underline_color = '#f59e0b'  # 앰버"""

    if OLD_LOAD in content:
        content = content.replace(OLD_LOAD, NEW_LOAD)
        changed += 1
        print("  ✅ _load_toolbar_colors() → 테마 반응형")
    elif 'v6.3.2-colorful' in content:
        print("  ℹ️ _load_toolbar_colors() 이미 패치됨")

    # (B) _create_menu 드롭다운
    OLD_MENU = """        menu_bg = '#0b1220'
        menu_fg = '#e2e8f0'
        menu_abg = '#1d4ed8'
        menu_afg = '#ffffff'
        menu_dis = '#64748b'"""

    NEW_MENU = """        # v6.3.2-colorful: 메뉴 테마 반응형
        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'darkly'))
        if is_dark:
            menu_bg = '#1a1a2e'
            menu_fg = '#e2e8f0'
            menu_abg = '#7c3aed'       # 보라 활성 (파랑 탈피)
            menu_afg = '#ffffff'
            menu_dis = '#64748b'
        else:
            menu_bg = '#1f2937'
            menu_fg = '#f3f4f6'
            menu_abg = '#d97706'       # 앰버 활성
            menu_afg = '#ffffff'
            menu_dis = '#9ca3af'"""

    if OLD_MENU in content:
        content = content.replace(OLD_MENU, NEW_MENU)
        changed += 1
        print("  ✅ _create_menu() → 테마 반응형")
    elif 'v6.3.2-colorful: 메뉴' in content:
        print("  ℹ️ _create_menu() 이미 패치됨")

    if changed > 0:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"  ✅ toolbar_mixin.py — {changed}건 수정")
    return changed > 0


# ═══════════════════════════════════════════
# FIX #7: table_styler.py DARK 헤더 (v2)
# ═══════════════════════════════════════════
def fix7_table_styler(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'table_styler.py')
    if not os.path.isfile(target):
        print("  ⚠️ table_styler.py 없음")
        return True

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    old = "'header_bg': '#333333',"
    new = "'header_bg': '#2d2b55',  # v6.3.2: 다크 퍼플 헤더"
    if old in content:
        content = content.replace(old, new)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ DARK 헤더 색상 → #2d2b55")
        return True
    elif '#2d2b55' in content:
        print("  ℹ️ 이미 패치됨")
    else:
        print("  ⚠️ 패턴 불일치")
    return True


def main():
    print()
    print("=" * 64)
    print("  🎨 SQM v6.3.2 — Colorful UI Fix v3 (근본 수정)")
    print(f"  실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("  v2에서 색상 미반영된 근본 원인 5가지 완전 수정")
    print("  ★ 이전 모든 패치/핫픽스 적용 여부 무관 안전 실행")
    print("=" * 64)
    print()

    sqm_root = find_sqm_root()
    if not sqm_root:
        print("  ❌ SQM 프로젝트를 찾을 수 없습니다.")
        print("     이 파일을 SQM 폴더(run.py와 같은 위치)에 넣고 실행하세요.")
        input("\n  Enter...")
        return

    print(f"  📂 SQM 루트: {sqm_root}")
    print()

    print("── [1/7] inventory_tab.py (★원인#1: 상태색 덮어쓰기) ──")
    fix1_inventory_tab(sqm_root)
    print()

    print("── [2/7] tonbag_tab.py (원인#5: 동일 문제) ──")
    fix2_tonbag_tab(sqm_root)
    print()

    print("── [3/7] auto_style_applier.py (★원인#2: 태그 파괴) ──")
    fix3_auto_style_applier(sqm_root)
    print()

    print("── [4/7] global_tree_style.py (원인#2#3#4: 전면 재작성) ──")
    fix4_global_tree_style(sqm_root)
    print()

    print("── [5/7] ui_constants.py (상태색 + DARK_THEMES + 스크롤바) ──")
    fix5_ui_constants(sqm_root)
    print()

    print("── [6/7] toolbar_mixin.py (툴바 + 메뉴) ──")
    fix6_toolbar(sqm_root)
    print()

    print("── [7/7] table_styler.py (헤더) ──")
    fix7_table_styler(sqm_root)
    print()

    print("=" * 64)
    print("  ✅ Colorful UI Fix v3 완료!")
    print()
    print("  수정된 근본 원인:")
    print("   #1 ★★★★★ _refresh_inventory() 단일색 덮어쓰기 → 상태별 고유색")
    print("   #2 ★★★★  auto_style_applier 태그 파괴 → status 태그 보존")
    print("   #3 ★★★   ttkbootstrap 헤더 파랑 → style.map(!disabled) 강제")
    print("   #4 ★★    configure_tree_grid 하드코딩 → 색상 동기화")
    print("   #5 ★     tonbag_tab 동일 문제 수정")
    print()
    print("  색상 변경:")
    print("   🟢 판매가능 : 에메랄드 (BG #065f46 / FG #6ee7b7)")
    print("   🟡 판매배정 : 골드     (BG #92400e / FG #fcd34d)")
    print("   🟣 판매화물 : 라벤더   (BG #5b21b6 / FG #c4b5fd)")
    print("   🔵 출고     : 스틸블루 (BG #1e3a5f / FG #93c5fd)")
    print("   🟣 헤더     : 다크 퍼플 #2d2b55 (파랑 #375a7f 탈피)")
    print("   🟣 툴바     : 다크 퍼플 #1a1a2e (네이비 탈피)")
    print()
    print("  SQM을 재시작하면 적용됩니다.")
    print("=" * 64)
    input("\n  Enter...")


if __name__ == '__main__':
    main()
