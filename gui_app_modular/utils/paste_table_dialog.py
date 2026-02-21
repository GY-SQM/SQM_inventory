# -*- coding: utf-8 -*-
"""
SQM - 스프레드시트형 붙여넣기 테이블 다이얼로그
==============================================
입고 템플릿·로케이션 매핑 등에서 파일 대신 화면에 표를 띄우고 Ctrl+V 붙여넣기 후 업로드.

columns: [(column_id, display_name, width), ...]
on_confirm: callback(rows) — rows = [{"col_id": "value", ...}, ...]
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import List, Tuple, Callable, Optional

from .ui_constants import apply_modal_window_options, center_dialog, ThemeColors

logger = logging.getLogger(__name__)


def _paste_into_tree(tree: ttk.Treeview, columns: List[Tuple[str, str, int]], sep_cell="\t", sep_row="\n"):
    """클립보드 내용을 구분자로 나눠 tree에 행 추가. 헤더 행은 스킵 가능."""
    try:
        raw = tree.winfo_toplevel().clipboard_get()
    except tk.TclError:
        return
    lines = [ln.strip() for ln in raw.strip().split(sep_row) if ln.strip()]
    if not lines:
        return
    col_ids = [c[0] for c in columns]
    ncols = len(col_ids)
    for line in lines:
        parts = [p.strip() for p in line.split(sep_cell)]
        if not any(parts):
            continue
        while len(parts) < ncols:
            parts.append("")
        values = tuple(parts[:ncols])
        tree.insert("", "end", values=values)


def show_paste_table_dialog(
    parent: tk.Misc,
    title: str,
    columns: List[Tuple[str, str, int]],
    instruction: str = "아래 표에 데이터를 붙여넣기(Ctrl+V) 한 뒤 [확인]을 누르세요.",
    confirm_text: str = "확인",
    cancel_text: str = "취소",
    on_confirm: Optional[Callable[[List[dict]], None]] = None,
    min_size: Tuple[int, int] = (720, 420),
) -> None:
    """
    스프레드시트형 테이블 다이얼로그. 컬럼 헤더 표시, Ctrl+V 붙여넣기 지원.

    columns: [(column_id, display_name, width), ...]
    on_confirm(rows): rows = [{"lot_no": "x", "product": "y", ...}, ...]
    """
    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent)
    win.resizable(True, True)
    win.minsize(min_size[0], min_size[1])
    apply_modal_window_options(win)

    frm = ttk.Frame(win, padding=12)
    frm.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frm, text=instruction, font=("맑은 고딕", 10), wraplength=680).pack(anchor=tk.W, pady=(0, 8))

    col_ids = [c[0] for c in columns]
    col_display = [c[1] for c in columns]
    col_widths = [min(c[2], 180) for c in columns]

    tree_frm = ttk.Frame(frm)
    tree_frm.pack(fill=tk.BOTH, expand=True, pady=4)
    tree = ttk.Treeview(tree_frm, columns=col_ids, show="headings", height=16, selectmode="extended")
    scroll_y = ttk.Scrollbar(tree_frm, orient=tk.VERTICAL, command=tree.yview)
    scroll_x = ttk.Scrollbar(tree_frm, orient=tk.HORIZONTAL, command=tree.xview)

    for i, (cid, disp, w) in enumerate(columns):
        tree.heading(cid, text=disp)
        tree.column(cid, width=min(w, 180), anchor="w")

    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    try:
        from ..mixins.theme_mixin import _is_dark_theme
        is_dark = _is_dark_theme(win)
    except Exception:
        is_dark = False
    fg = ThemeColors.get("text_primary", is_dark)
    try:
        tree.tag_configure("cell", foreground=fg)
    except (tk.TclError, TypeError):
        pass

    def _on_paste(event=None):
        _paste_into_tree(tree, columns)
        return "break"

    tree.bind("<Control-v>", _on_paste)
    tree.bind("<Control-V>", _on_paste)

    def _on_confirm():
        rows = []
        for item in tree.get_children():
            vals = tree.item(item, "values")
            row = {}
            for i, cid in enumerate(col_ids):
                row[cid] = (vals[i] if i < len(vals) else "").strip()
            rows.append(row)
        win.destroy()
        if on_confirm and rows:
            try:
                on_confirm(rows)
            except Exception as e:
                logger.exception("paste_table on_confirm: %s", e)

    def _on_cancel():
        win.destroy()

    btn_frm = ttk.Frame(frm)
    btn_frm.pack(fill=tk.X, pady=(12, 0))
    ttk.Button(btn_frm, text=confirm_text, command=_on_confirm).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frm, text=cancel_text, command=_on_cancel).pack(side=tk.LEFT, padx=4)

    win.geometry(f"{min_size[0]}x{min_size[1]}")
    center_dialog(win, parent)
    try:
        tree.focus_set()
    except tk.TclError:
        pass
