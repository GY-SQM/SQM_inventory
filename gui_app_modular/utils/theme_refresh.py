# -*- coding: utf-8 -*-
"""
SQM v6.1.1 - 테마 변경 시 전체 위젯 자동 갱신 엔진
====================================================

테마 토글 때 화면에 존재하는 모든 Treeview(+ 네이티브 위젯)를
자동 탐색하여 색상을 일괄 재적용합니다.

사용법:
    from gui_app_modular.utils.theme_refresh import refresh_all_widgets_for_theme
    stats = refresh_all_widgets_for_theme(self)
"""

import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)


def _walk_widgets(root_widget):
    """루트 위젯부터 모든 자식 위젯을 스택으로 탐색하는 제너레이터."""
    visited = set()
    stack = [root_widget]
    while stack:
        w = stack.pop()
        w_id = id(w)
        if w_id in visited:
            continue
        visited.add(w_id)
        yield w
        try:
            children = w.winfo_children()
            stack.extend(children)
        except (tk.TclError, RuntimeError):
            pass


def _safe_lookup(style: ttk.Style, widget_class: str, option: str, fallback: str) -> str:
    """ttk.Style.lookup()을 안전하게 호출."""
    try:
        value = style.lookup(widget_class, option)
        if not value or str(value).strip() == '':
            return fallback
        return str(value)
    except (tk.TclError, RuntimeError, ValueError):
        return fallback


def _is_dark_color(color_str: str) -> bool:
    """색상 문자열의 명도로 다크 여부 판별."""
    if not color_str:
        return False
    try:
        c = color_str.strip().lower()
        if c in ('white', '#ffffff', '#fff'):
            return False
        if c in ('black', '#000000', '#000'):
            return True
        if c.startswith('#'):
            h = c.lstrip('#')
            if len(h) == 3:
                h = ''.join([ch * 2 for ch in h])
            if len(h) >= 6:
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                return brightness < 128
        return False
    except (ValueError, IndexError):
        return False


def get_theme_colors_from_style() -> dict:
    """현재 ttk.Style에서 Treeview 관련 색상을 동적으로 조회."""
    style = ttk.Style()
    fg = _safe_lookup(style, "Treeview", "foreground", "")
    bg = _safe_lookup(style, "Treeview", "background", "")
    field_bg = _safe_lookup(style, "Treeview", "fieldbackground", bg)
    if not fg or fg.strip() == '':
        fg = _safe_lookup(style, ".", "foreground", "#000000")
    if not bg or bg.strip() == '':
        bg = _safe_lookup(style, ".", "background", "#ffffff")
    if not field_bg or field_bg.strip() == '':
        field_bg = bg
    sel_bg = _safe_lookup(style, "Treeview", "selectbackground", "#0078D7")
    sel_fg = _safe_lookup(style, "Treeview", "selectforeground", "#ffffff")
    if not sel_bg or sel_bg.strip() == '':
        sel_bg = "#0078D7"
    if not sel_fg or sel_fg.strip() == '':
        sel_fg = "#ffffff"
    heading_fg = _safe_lookup(style, "Treeview.Heading", "foreground", fg)
    heading_bg = _safe_lookup(style, "Treeview.Heading", "background", bg)
    is_dark = _is_dark_color(bg)
    return {
        'fg': fg, 'bg': bg, 'field_bg': field_bg,
        'sel_fg': sel_fg, 'sel_bg': sel_bg,
        'heading_fg': heading_fg, 'heading_bg': heading_bg,
        'is_dark': is_dark,
    }


def _refresh_single_treeview(tree: ttk.Treeview, colors: dict, style: ttk.Style) -> None:
    """단일 Treeview의 태그 + 스타일을 현재 테마에 맞게 갱신."""
    fg = colors['fg']
    bg = colors['bg']
    is_dark = colors['is_dark']
    sel_fg = colors['sel_fg']
    sel_bg = colors['sel_bg']
    for tag_name in ('odd', 'even', 'stripe', 'oddrow', 'evenrow'):
        try:
            existing = tree.tag_configure(tag_name)
            if existing:
                tree.tag_configure(tag_name, foreground=fg)
        except (tk.TclError, ValueError):
            pass
    try:
        from gui_app_modular.utils.ui_constants import ThemeColors
        ThemeColors.configure_tags(tree, is_dark)
    except (ImportError, Exception) as e:
        logger.debug(f"ThemeColors.configure_tags skip: {e}")
        for tag_name in ('available', 'picked', 'reserved', 'shipped', 'depleted'):
            try:
                tree.tag_configure(tag_name, foreground=fg)
            except (tk.TclError, ValueError):
                pass
    try:
        style_name = tree.cget('style') or 'Treeview'
        style.configure(style_name, foreground=fg, background=bg, fieldbackground=colors['field_bg'])
        style.map(style_name,
                  foreground=[('selected', sel_fg), ('!selected', fg)],
                  background=[('selected', sel_bg)])
        heading_style = f"{style_name}.Heading" if style_name != 'Treeview' else 'Treeview.Heading'
        style.configure(heading_style, foreground=colors['heading_fg'], background=colors['heading_bg'])
    except (tk.TclError, ValueError, RuntimeError) as e:
        logger.debug(f"Treeview style update skip: {e}")
    try:
        from gui_app_modular.utils.table_styler import TableStyler
        TableStyler.update_grid_style_for_theme(tree, is_dark)
    except (ImportError, Exception):
        pass


def _refresh_native_widget(widget, colors: dict) -> None:
    """tk.Text, tk.Label, tk.Listbox fg/bg를 테마와 충돌 시에만 동기화."""
    is_dark = colors['is_dark']
    theme_fg = colors['fg']
    theme_bg = colors['bg']
    sel_bg = colors.get('sel_bg', '#0078D7')
    sel_fg = colors.get('sel_fg', '#ffffff')

    def _brightness_of(color_value: str):
        """
        위젯 기준 실제 RGB 밝기(0~255) 계산.
        시스템 색상명(SystemWindowText 등)도 winfo_rgb로 해석 가능.
        """
        try:
            r16, g16, b16 = widget.winfo_rgb(color_value)
            r8, g8, b8 = r16 / 257.0, g16 / 257.0, b16 / 257.0
            return (r8 * 299 + g8 * 587 + b8 * 114) / 1000.0
        except (tk.TclError, RuntimeError, ValueError):
            return None

    try:
        current_fg = str(widget.cget('fg')) if hasattr(widget, 'cget') else ''
        current_bg = str(widget.cget('bg')) if hasattr(widget, 'cget') else ''
    except (tk.TclError, RuntimeError):
        return
    if not current_fg:
        return
    fg_b = _brightness_of(current_fg)
    bg_b = _brightness_of(current_bg)

    # 색상을 해석할 수 없거나 대비가 부족하면 테마 색으로 강제 동기화
    needs_fix = fg_b is None or bg_b is None
    if not needs_fix:
        low_contrast = abs(fg_b - bg_b) < 80
        wrong_bg_for_theme = (is_dark and bg_b > 170) or ((not is_dark) and bg_b < 85)
        wrong_fg_for_theme = (is_dark and fg_b < 120) or ((not is_dark) and fg_b > 180)
        needs_fix = low_contrast or wrong_bg_for_theme or wrong_fg_for_theme

    if needs_fix:
        try:
            widget.configure(fg=theme_fg)
            widget.configure(bg=theme_bg)
            if isinstance(widget, tk.Listbox):
                widget.configure(selectbackground=sel_bg, selectforeground=sel_fg)
            if isinstance(widget, tk.Text):
                widget.configure(insertbackground=theme_fg)
        except (tk.TclError, RuntimeError):
            pass


def refresh_all_widgets_for_theme(app) -> dict:
    """테마 변경 시 화면의 모든 위젯을 자동 탐색하여 색상 일괄 갱신."""
    stats = {'treeviews': 0, 'native_widgets': 0, 'is_dark': False}
    try:
        try:
            from fixes.global_tree_style import apply_global_tree_style
            apply_global_tree_style()
        except (ImportError, Exception) as e:
            logger.debug(f"global_tree_style 재적용 skip: {e}")
        colors = get_theme_colors_from_style()
        stats['is_dark'] = colors['is_dark']
        style = ttk.Style()
        for w in _walk_widgets(app.root):
            if isinstance(w, ttk.Treeview):
                _refresh_single_treeview(w, colors, style)
                stats['treeviews'] += 1
            elif isinstance(w, (tk.Text, tk.Listbox)):
                _refresh_native_widget(w, colors)
                stats['native_widgets'] += 1
            elif isinstance(w, tk.Label) and not isinstance(w, ttk.Label):
                _refresh_native_widget(w, colors)
                stats['native_widgets'] += 1
        logger.info(f"[v6.2.3] Theme refresh: Treeview={stats['treeviews']}, Native={stats['native_widgets']}, dark={stats['is_dark']}")
    except Exception as e:
        logger.error(f"[v6.2.3] Theme refresh 실패: {e}")
    return stats


def debug_dump_widget_theme_status(app) -> str:
    """현재 화면의 모든 위젯 테마 상태를 덤프 (디버그용)."""
    lines = ["=" * 70, "SQM v6.2.3 Widget Theme Status Dump", "=" * 70]
    colors = get_theme_colors_from_style()
    lines.append(f"Theme colors: fg={colors['fg']}, bg={colors['bg']}, dark={colors['is_dark']}\n")
    tree_count = 0
    problems = []
    for w in _walk_widgets(app.root):
        if isinstance(w, ttk.Treeview):
            tree_count += 1
            sn = w.cget('style') or 'Treeview'
            tag_info = []
            for tag in ('odd', 'even', 'available', 'picked', 'reserved'):
                try:
                    cfg = w.tag_configure(tag)
                    if cfg:
                        tfg = cfg.get('foreground', '')
                        if isinstance(tfg, (list, tuple)):
                            tfg = tfg[0] if tfg else ''
                        tag_info.append(f"{tag}:fg={tfg}")
                except Exception as _te:
                    logging.getLogger(__name__).debug(f"[테마] 태그 정보 조회 실패: {_te}")
            lines.append(f"  [TV#{tree_count}] style={sn} | {', '.join(tag_info) if tag_info else 'no tags'}")
            for tag in ('odd', 'even'):
                try:
                    cfg = w.tag_configure(tag)
                    tfg = str(cfg.get('foreground', ''))
                    if colors['is_dark'] and tfg.lower() in ('black', '#000000', ''):
                        problems.append(f"⚠️ TV#{tree_count}({sn}): '{tag}' fg='{tfg}' on DARK")
                    elif not colors['is_dark'] and tfg.lower() in ('white', '#ffffff'):
                        problems.append(f"⚠️ TV#{tree_count}({sn}): '{tag}' fg='{tfg}' on LIGHT")
                except Exception as _te:
                    logging.getLogger(__name__).debug(f"[테마] 색상 검사 실패: {_te}")
    lines.append(f"\nTotal Treeviews: {tree_count}")
    if problems:
        lines.append("\n─── PROBLEMS ───")
        lines.extend(f"  {p}" for p in problems)
    else:
        lines.append("✅ No visibility problems detected")
    lines.append("=" * 70)
    return "\n".join(lines)
