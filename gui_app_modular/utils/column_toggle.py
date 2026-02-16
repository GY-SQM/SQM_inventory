# -*- coding: utf-8 -*-
"""
SQM v5.5.3 — 컬럼 표시/숨김 + 표시 모드 위젯
================================================
v5.5.3 patch_03: tk→ttk 전환으로 테마 자동 대응
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple

logger = logging.getLogger(__name__)


class ColumnToggleBar:
    """
    컬럼 표시/숨김 체크박스 바

    v5.5.3 patch_03: ttk 위젯 사용 → 테마 자동 대응

    Usage:
        toggle_bar = ColumnToggleBar(parent, tree, columns)
        toggle_bar.pack(fill='x')
    """

    def __init__(self, parent, tree, toggle_columns: List[Tuple[str, str]],
                 is_dark: bool = False):
        """
        Args:
            parent: 부모 위젯
            tree: Treeview 위젯
            toggle_columns: [(col_id, label), ...]
            is_dark: 하위 호환 (사용하지 않음)
        """
        self.tree = tree
        self.toggle_vars = {}
        self.toggle_columns = toggle_columns

        # ttk.Frame — 테마 자동 대응
        self.frame = ttk.Frame(parent, padding=(5, 4))

        # 왼쪽: "표시 컬럼:" + 체크박스
        left_frame = ttk.Frame(self.frame)
        left_frame.pack(side='left', fill='x', expand=True)

        ttk.Label(left_frame, text="표시 컬럼:",
                  font=('맑은 고딕', 9, 'bold')).pack(side='left', padx=(0, 10))

        for col_id, label in toggle_columns:
            var = tk.BooleanVar(value=True)
            chk = ttk.Checkbutton(
                left_frame,
                text=label,
                variable=var,
                command=lambda c=col_id, v=var: self._toggle_column(c, v)
            )
            chk.pack(side='left', padx=5)
            self.toggle_vars[col_id] = var

        # 오른쪽: "표시 모드:" + 라디오 버튼
        right_frame = ttk.Frame(self.frame)
        right_frame.pack(side='right', padx=10)

        ttk.Label(right_frame, text="표시 모드:",
                  font=('맑은 고딕', 9)).pack(side='left', padx=(0, 10))

        self.mode_var = tk.StringVar(value="compact")

        modes = [
            ("컬럼", "compact"),
            ("본문", "normal"),
            ("날짜", "comfortable")
        ]

        for label, value in modes:
            rb = ttk.Radiobutton(
                right_frame,
                text=label,
                variable=self.mode_var,
                value=value,
                command=self._change_mode
            )
            rb.pack(side='left', padx=5)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def _toggle_column(self, col_id: str, var: tk.BooleanVar) -> None:
        """컬럼 표시/숨김"""
        if not self.tree:
            logger.warning("Treeview가 연결되지 않음")
            return

        try:
            current_display = self.tree['displaycolumns']

            if not current_display or current_display == '' or current_display == '#all':
                current_display = list(self.tree['columns'])
            else:
                current_display = list(current_display)

            all_cols = list(self.tree['columns'])

            if var.get():
                # 체크 → 표시
                if col_id not in current_display and col_id in all_cols:
                    idx = all_cols.index(col_id)
                    insert_pos = 0
                    for i, c in enumerate(current_display):
                        if c in all_cols and all_cols.index(c) < idx:
                            insert_pos = i + 1
                    current_display.insert(insert_pos, col_id)
            else:
                # 해제 → 숨김
                if col_id in current_display:
                    current_display.remove(col_id)

            self.tree['displaycolumns'] = tuple(current_display)
            logger.debug(f"컬럼 토글: {col_id} → {'표시' if var.get() else '숨김'}")

        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"컬럼 토글 오류: {e}")

    def _change_mode(self) -> None:
        """표시 모드 변경"""
        if not self.tree:
            return

        mode = self.mode_var.get()
        heights = {"compact": 24, "normal": 28, "comfortable": 32}

        try:
            style = ttk.Style()
            style.configure("Treeview", rowheight=heights.get(mode, 28))
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"모드 변경 오류: {e}")

    def get_visible_columns(self) -> List[str]:
        """현재 표시 중인 컬럼 목록"""
        return [col_id for col_id, var in self.toggle_vars.items() if var.get()]


__all__ = ['ColumnToggleBar']
