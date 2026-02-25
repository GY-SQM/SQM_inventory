# -*- coding: utf-8 -*-
"""
SQM - 스프레드시트형 붙여넣기 테이블 다이얼로그
==============================================
입고 템플릿·로케이션 매핑 등에서 파일 대신 화면에 표를 띄우고 Ctrl+V 붙여넣기 후 업로드.
데이터 영역은 Entry 그리드로 구현해 가로·세로 셀 경계선이 보이도록 함.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import List, Tuple, Callable, Optional

from .ui_constants import apply_modal_window_options, center_dialog, ThemeColors

logger = logging.getLogger(__name__)

# 데이터 행 수 (가로·세로 선이 보이는 그리드)
DEFAULT_DATA_ROWS = 20


def _paste_into_grid(entries: List[List[tk.Entry]], ncols: int, sep_cell="\t", sep_row="\n") -> None:
    """클립보드 내용을 구분자로 나눠 Entry 그리드에 채움."""
    try:
        raw = entries[0][0].winfo_toplevel().clipboard_get()
    except tk.TclError:
        return
    lines = [ln.strip() for ln in raw.strip().split(sep_row) if ln.strip()]
    if not lines:
        return
    for row_idx, line in enumerate(lines):
        if row_idx >= len(entries):
            break
        parts = [p.strip() for p in line.replace("\r", "").split(sep_cell)]
        for col_idx in range(ncols):
            val = parts[col_idx] if col_idx < len(parts) else ""
            try:
                entries[row_idx][col_idx].delete(0, tk.END)
                entries[row_idx][col_idx].insert(0, val)
            except (tk.TclError, IndexError):
                pass


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
    스프레드시트형 테이블 다이얼로그. 컬럼 헤더 + 데이터 셀에 가로·세로 경계선 표시, Ctrl+V 붙여넣기 지원.
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
    ncols = len(col_ids)
    nrows = DEFAULT_DATA_ROWS

    try:
        from ..mixins.theme_mixin import _is_dark_theme
        is_dark = _is_dark_theme(win)
    except Exception:
        is_dark = False
    bg_cell = ThemeColors.get("bg_card", is_dark) or "#FFFFFF"
    fg_cell = ThemeColors.get("text_primary", is_dark) or "#333333"
    header_bg = ThemeColors.get("btn_report", is_dark) or "#4472C4"

    # 헤더 행 (가로·세로 선 있게 Label + relief)
    header_frm = tk.Frame(frm)
    header_frm.pack(fill=tk.X, pady=(0, 0))
    for col_idx, (cid, disp, w) in enumerate(columns):
        width_chars = max(4, min(w // 8, 24))
        lbl = tk.Label(
            header_frm,
            text=disp,
            width=width_chars,
            anchor="center",
            font=("맑은 고딕", 9, "bold"),
            relief="ridge",
            bd=1,
            bg=header_bg,
            fg="#FFFFFF",
        )
        lbl.grid(row=0, column=col_idx, sticky="nsew", padx=(0, 0), pady=(0, 0))
    header_frm.grid_columnconfigure(list(range(ncols)), weight=1)

    # 데이터 영역: Entry 그리드 (가로·세로 선이 보이도록 relief + bd)
    table_container = tk.Frame(frm)
    table_container.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

    canvas = tk.Canvas(table_container, highlightthickness=0)
    scroll_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=canvas.yview)
    scroll_x = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL, command=canvas.xview)

    inner = tk.Frame(canvas)
    inner.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    entries: List[List[tk.Entry]] = []
    for row_idx in range(nrows):
        row_entries = []
        for col_idx in range(ncols):
            width_chars = max(4, min(col_widths[col_idx] // 8, 24))
            e = tk.Entry(
                inner,
                width=width_chars,
                font=("맑은 고딕", 9),
                relief="solid",
                bd=1,
                bg=bg_cell,
                fg=fg_cell,
                insertbackground=fg_cell,
            )
            e.grid(row=row_idx, column=col_idx, sticky="nsew", padx=0, pady=0)
            row_entries.append(e)
        entries.append(row_entries)
    for c in range(ncols):
        inner.grid_columnconfigure(c, weight=1)
    for r in range(nrows):
        inner.grid_rowconfigure(r, weight=0)

    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _on_paste(event=None):
        _paste_into_grid(entries, ncols)
        return "break"

    inner.bind("<Control-v>", _on_paste)
    inner.bind("<Control-V>", _on_paste)
    for row_entries in entries:
        for e in row_entries:
            e.bind("<Control-v>", _on_paste)
            e.bind("<Control-V>", _on_paste)

    def _on_confirm():
        rows = []
        for row_entries in entries:
            row = {}
            for i, e in enumerate(row_entries):
                cid = col_ids[i] if i < len(col_ids) else ""
                try:
                    row[cid] = (e.get() or "").strip()
                except (tk.TclError, TypeError):
                    row[cid] = ""
            if any(row.get(cid) for cid in col_ids):
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
        if entries and entries[0]:
            entries[0][0].focus_set()
    except tk.TclError:
        pass
