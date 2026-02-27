# -*- coding: utf-8 -*-
"""
SQM v6.12.1 — 반품 미리보기 편집 다이얼로그
=============================================
Excel 반품 입고 시 DB 반영 전 미리보기 + 셀 편집 기능.
수동입고 미리보기와 동일한 인라인 편집 패턴.
"""

import logging
import tkinter as tk
from tkinter import ttk
from tkinter.constants import BOTH, LEFT, RIGHT, X, Y, END, VERTICAL

logger = logging.getLogger(__name__)

try:
    from gui_app_modular.utils.gui_bootstrap import (
        DialogSize, center_dialog, apply_modal_window_options
    )
    from gui_app_modular.utils.custom_messagebox import CustomMessageBox
except ImportError:
    DialogSize = None
    center_dialog = None
    apply_modal_window_options = None
    CustomMessageBox = None

try:
    from gui_app_modular.utils.theme_colors import ThemeColors
except ImportError:
    ThemeColors = None


class ReturnInboundPreviewDialog:
    """
    반품 입고 미리보기 + 편집 다이얼로그.

    Args:
        parent: 부모 윈도우
        items: 파싱된 반품 아이템 리스트
            [{'lot_no': ..., 'weight_mt': ..., 'tonbag_count': ..., 'picking_no': ...,
              'reason': ..., 'remark': ...}, ...]
        on_confirm: 확인 시 콜백 — 편집된 items를 인자로 받음
        current_theme: 현재 테마
    """

    EDITABLE_COLS = ('lot_no', 'picking_no', 'reason', 'remark')
    DISPLAY_COLS = ('no', 'lot_no', 'weight_mt', 'tonbag_count', 'picking_no',
                    'reason', 'remark')
    HEADERS = ('#', 'LOT NO', '중량(MT)', '톤백수', 'PICKING NO',
               '반품 사유', '비고')
    WIDTHS = (35, 100, 70, 55, 90, 140, 120)

    def __init__(self, parent, items: list, on_confirm=None,
                 current_theme: str = 'flatly'):
        self.parent = parent
        self.items = items
        self.on_confirm = on_confirm
        self.confirmed = False
        self._editing_item = None

        is_dark = ThemeColors.is_dark_theme(current_theme) if ThemeColors else False
        bg = ThemeColors.get('bg_card', is_dark) if ThemeColors else '#FFFFFF'
        fg = ThemeColors.get('text_primary', is_dark) if ThemeColors else '#000000'

        self.popup = tk.Toplevel(parent)
        self.popup.title(f"🔄 반품 입고 미리보기 ({len(items)}건)")
        if DialogSize:
            self.popup.geometry(DialogSize.get_geometry(parent, 'large'))
        else:
            self.popup.geometry("850x500")
        if apply_modal_window_options:
            apply_modal_window_options(self.popup)
        self.popup.transient(parent)
        self.popup.grab_set()
        if center_dialog:
            center_dialog(self.popup, parent)
        self.popup.configure(bg=bg)

        # ═══ 안내 ═══
        info = tk.Frame(self.popup, bg=bg, pady=5)
        info.pack(fill=X, padx=10)
        tk.Label(info,
                 text=f"총 {len(items)}건 | 사유·비고 셀 더블클릭 편집 가능 | 1건이라도 실패 시 전체 롤백",
                 font=('맑은 고딕', 10), bg=bg, fg='#DC3545').pack(anchor='w')

        # ═══ Treeview ═══
        tree_frame = tk.Frame(self.popup, bg=bg)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(
            tree_frame, columns=self.DISPLAY_COLS, show='headings', height=15
        )
        for cid, hdr, w in zip(self.DISPLAY_COLS, self.HEADERS, self.WIDTHS):
            self.tree.heading(cid, text=hdr)
            anchor = 'e' if cid in ('weight_mt', 'tonbag_count') else 'center'
            self.tree.column(cid, width=w, anchor=anchor)

        sb = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb.pack(side=RIGHT, fill=Y)

        # 데이터 로드
        for idx, item in enumerate(items):
            self.tree.insert('', END, iid=str(idx), values=(
                idx + 1,
                item.get('lot_no', ''),
                f"{item.get('weight_mt', 0):.2f}",
                item.get('tonbag_count', 0),
                item.get('picking_no', ''),
                item.get('reason', ''),
                item.get('remark', ''),
            ))

        self.tree.bind('<Double-1>', self._on_cell_edit)

        # ═══ 하단 버튼 ═══
        btn_bar = tk.Frame(self.popup, bg=bg, pady=8)
        btn_bar.pack(fill=X, padx=10)

        total_mt = sum(it.get('weight_mt', 0) for it in items)
        total_tb = sum(it.get('tonbag_count', 0) for it in items)
        tk.Label(btn_bar,
                 text=f"합계: {total_mt:.1f} MT | 톤백 {total_tb}개 | ⚠️ 매칭 실패 시 전체 중단",
                 font=('맑은 고딕', 9), bg=bg, fg=fg).pack(side=LEFT)

        ttk.Button(btn_bar, text="취소", command=self.popup.destroy).pack(side=RIGHT, padx=5)
        ttk.Button(btn_bar, text="🔄 반품 실행", command=self._on_submit).pack(side=RIGHT, padx=5)

        self.popup.wait_window()

    def _on_cell_edit(self, event):
        """셀 더블클릭 → 인라인 Entry 편집."""
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        col_id = self.tree.identify_column(event.x)
        col_idx = int(col_id.replace('#', '')) - 1
        if col_idx < 0 or col_idx >= len(self.DISPLAY_COLS):
            return
        col_name = self.DISPLAY_COLS[col_idx]
        if col_name not in self.EDITABLE_COLS:
            return

        item = self.tree.identify_row(event.y)
        if not item:
            return

        self._finish_editing()

        bbox = self.tree.bbox(item, col_id)
        if not bbox:
            return
        x, y, w, h = bbox

        current_val = self.tree.set(item, col_name)
        entry = tk.Entry(self.tree, font=('맑은 고딕', 10))
        entry.insert(0, current_val)
        entry.select_range(0, 'end')
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()

        self._editing_item = (item, col_name, entry)
        entry.bind('<Return>', lambda e: self._finish_editing())
        entry.bind('<Escape>', lambda e: self._cancel_editing())
        entry.bind('<FocusOut>', lambda e: self._finish_editing())

    def _finish_editing(self):
        if not self._editing_item:
            return
        item, col_name, entry = self._editing_item
        new_val = entry.get().strip()
        entry.destroy()
        self._editing_item = None

        idx = int(item)
        self.items[idx][col_name] = new_val
        self.tree.set(item, col_name, new_val)

    def _cancel_editing(self):
        if self._editing_item:
            self._editing_item[2].destroy()
            self._editing_item = None

    def _on_submit(self):
        self._finish_editing()
        self.confirmed = True
        self.popup.destroy()
        if self.on_confirm:
            self.on_confirm(self.items)
