# -*- coding: utf-8 -*-
"""
SQM v6.3.2 v5.1-NAVY — 최종 Treeview 오버라이드
=================================================
main_app.py after(1500)에서 호출.
STANDARD_THEMES 수정으로 대부분의 위젯 색상은 자동 처리.
이 모듈은 Treeview 특화 추가 작업만 담당:
  1. Heading 이중 안전장치
  2. 상태별 행 색상 (available/picked/reserved/shipped)
  3. _refresh_inventory monkey-patch (데이터 로드 후 상태색 유지)
"""
import logging
from tkinter import ttk

logger = logging.getLogger(__name__)

STATUS_TAGS = frozenset({'available', 'picked', 'reserved', 'shipped', 'depleted'})

# Treeview Heading (v7.7.0: premium navy palette)
HEAD = {'bg': '#162033', 'fg': '#E5E7EB', 'hover': '#1E293B'}

# 상태별 색상 (다크/라이트)
S_DARK = {
    'available': ('#064E3B', '#6EE7B7'),
    'reserved':  ('#78350F', '#FCD34D'),
    'picked':    ('#4C1D95', '#C4B5FD'),
    'shipped':   ('#1E3A5F', '#93C5FD'),
    'depleted':  ('#111B2E', '#6B7280'),
    'stripe':    ('#111B2E', '#E5E7EB'),
    'odd':       ('#111B2E', '#E5E7EB'),
    'even':      ('#0B1220', '#E5E7EB'),
}
S_LIGHT = {
    'available': ('#D1FAE5', '#064E3B'),
    'reserved':  ('#FEF3C7', '#78350F'),
    'picked':    ('#EDE9FE', '#4C1D95'),
    'shipped':   ('#DBEAFE', '#1E3A5F'),
    'depleted':  ('#F1F5F9', '#94A3B8'),
    'stripe':    ('#F8FAFC', '#0F172A'),
    'odd':       ('#F8FAFC', '#0F172A'),
    'even':      ('#FFFFFF', '#0F172A'),
}


def _is_dark(theme=None):
    if theme is None:
        try:
            theme = ttk.Style().theme_use() or ''
        except Exception:
            theme = ''
    return theme.lower() == 'darkly'


def apply_colorful_overrides(app):
    """최종 오버라이드 (after 1500ms에서 호출)"""
    try:
        style = ttk.Style()
        actual = style.theme_use() or 'darkly'
        dark = _is_dark(actual)

        # 1. current_theme 재동기화
        if hasattr(app, 'current_theme'):
            app.current_theme = actual

        # 2. Heading 이중 보험 (STANDARD_THEMES가 커버 못하는 경우)
        style.configure('Treeview.Heading',
            background=HEAD['bg'], foreground=HEAD['fg'],
            font=('맑은 고딕', 10, 'bold'))
        style.map('Treeview.Heading',
            background=[('active', HEAD['hover']), ('!disabled', HEAD['bg'])],
            foreground=[('active', HEAD['fg']), ('!disabled', HEAD['fg'])])

        # 3. Treeview 본문
        if dark:
            style.configure('Treeview',
                fieldbackground='#0B1220', background='#0B1220',
                foreground='#E5E7EB', rowheight=36,
                font=('맑은 고딕', 13))
            style.map('Treeview',
                background=[('selected', '#2563EB')],
                foreground=[('selected', '#FFD700'), ('!selected', '#E5E7EB')])

        # 4. 모든 Treeview 상태색 적용
        _apply_all(app, dark)

        # 5. monkey-patch (_refresh 후 상태색 유지)
        _install_hooks(app, dark)

        logger.info(f"[v5.1-NAVY] override OK (theme={actual}, dark={dark})")
    except Exception as e:
        logger.error(f"[v5.1-NAVY] override error: {e}")
        import traceback; traceback.print_exc()


def _apply_tags(tree, dark):
    """Treeview 상태 태그 색상"""
    palette = S_DARK if dark else S_LIGHT
    for tag, (bg, fg) in palette.items():
        tree.tag_configure(tag, background=bg, foreground=fg)


def _apply_all(app, dark):
    """모든 주요 Treeview에 적용"""
    n = 0
    for attr in ['tree_inventory', 'tree_sublot', 'tree_allocation',
                 'tree_picked', 'tree_sold', 'tree_overview']:
        tree = getattr(app, attr, None)
        if tree:
            try:
                _apply_tags(tree, dark)
                n += 1
            except Exception:
                pass
    logger.info(f"[v5.1-NAVY] status tags → {n} trees")


def _install_hooks(app, dark):
    """_refresh_inventory monkey-patch (상태색 덮어쓰기 방지)"""
    if getattr(app, '_v5_hooked', False):
        return

    for method, tree_attr in [
        ('_refresh_inventory', 'tree_inventory'),
        ('_refresh_sublot_list', 'tree_sublot'),
    ]:
        orig = getattr(app, method, None)
        tree = getattr(app, tree_attr, None)
        if not orig or not tree:
            continue

        def make_hook(fn, tw, dk):
            def hooked(*a, **kw):
                r = fn(*a, **kw)
                try:
                    _apply_tags(tw, dk)
                except Exception:
                    pass
                return r
            return hooked

        setattr(app, method, make_hook(orig, tree, dark))
        logger.info(f"[v5.1-NAVY] hook → {method}")

    app._v5_hooked = True
