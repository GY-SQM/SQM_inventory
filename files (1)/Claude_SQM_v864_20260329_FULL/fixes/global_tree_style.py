# -*- coding: utf-8 -*-
"""v8.6.4: Treeview 글로벌 스타일 — 다크/라이트 모드 대응."""
import logging
logger = logging.getLogger(__name__)


def apply_global_tree_style(root, is_dark: bool) -> None:
    """Treeview 전체에 다크/라이트 색상 적용."""
    try:
        import tkinter.ttk as ttk
        style = ttk.Style(root)

        if is_dark:
            bg      = "#1e293b"
            fg      = "#f1f5f9"
            sel_bg  = "#0ea5e9"
            sel_fg  = "#ffffff"
            head_bg = "#0f172a"
            head_fg = "#94a3b8"
            row_odd = "#1e293b"
            row_even= "#162032"
        else:
            bg      = "#ffffff"
            fg      = "#1e293b"
            sel_bg  = "#3b82f6"
            sel_fg  = "#ffffff"
            head_bg = "#f1f5f9"
            head_fg = "#374151"
            row_odd = "#ffffff"
            row_even= "#f8fafc"

        style.configure("Treeview",
            background=bg, foreground=fg,
            fieldbackground=bg,
            selectbackground=sel_bg,
            selectforeground=sel_fg,
            rowheight=26,
        )
        style.configure("Treeview.Heading",
            background=head_bg,
            foreground=head_fg,
            relief="flat",
        )
        style.map("Treeview",
            background=[("selected", sel_bg)],
            foreground=[("selected", sel_fg)],
        )
        # 행 색상 태그
        style.configure("odd.Treeview",  background=row_odd)
        style.configure("even.Treeview", background=row_even)

    except Exception as e:
        logger.debug(f"[TreeStyle] 적용 스킵: {e}")
