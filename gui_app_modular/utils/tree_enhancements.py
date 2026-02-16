# -*- coding: utf-8 -*-
"""
SQM v5.5.3 — Treeview 향상: 줄무늬, 필터, 합계
=================================================
v5.5.3 patch_03: tk→ttk 전환으로 테마 자동 대응

재고 리스트 / 톤백 리스트에 공통 적용:
- 줄무늬 행 (striped rows)
- 헤더 필터 Combobox
- 하단 합계 바
"""

import logging
from typing import List, Tuple, Callable
from .ui_constants import ThemeColors

logger = logging.getLogger(__name__)


def apply_striped_rows(tree, is_dark: bool = False) -> None:
    """
    Treeview에 줄무늬 행 적용 (홀수/짝수 교대 배경)

    v5.5.3 patch_03: ThemeColors 참조로 테마 자동 대응
    """
    even_bg = ThemeColors.get('bg_card', is_dark)
    odd_bg = ThemeColors.get('bg_secondary', is_dark) if not is_dark else '#2a2a2a'

    tree.tag_configure('even_row', background=even_bg)
    tree.tag_configure('odd_row', background=odd_bg)

    for idx, item_id in enumerate(tree.get_children('')):
        tag = 'even_row' if idx % 2 == 0 else 'odd_row'
        existing_tags = list(tree.item(item_id, 'tags') or ())
        existing_tags = [t for t in existing_tags if t not in ('even_row', 'odd_row')]
        existing_tags.append(tag)
        tree.item(item_id, tags=tuple(existing_tags))


class HeaderFilterBar:
    """
    Treeview 위에 컬럼별 필터 Combobox 바

    v5.5.3 patch_03: ttk 위젯 사용 → 테마 자동 대응
    
    Usage:
        filter_bar = HeaderFilterBar(parent, tree, columns, on_filter_callback)
        filter_bar.pack(fill='x')
    """

    def __init__(self, parent, tree, filter_columns: List[Tuple[str, str, int]],
                 on_filter: Callable, is_dark: bool = False):
        """
        Args:
            parent: 부모 위젯
            tree: Treeview 위젯
            filter_columns: [(col_id, label, width), ...]
            on_filter: 필터 변경 시 콜백
            is_dark: 하위 호환 (사용하지 않음, ttk가 자동 처리)
        """
        import tkinter as tk
        from tkinter import ttk

        self.tree = tree
        self.on_filter = on_filter
        self.filter_vars = {}
        self.filter_combos = {}

        # ttk.Frame — 테마 색상 자동 적용
        self.frame = ttk.Frame(parent, padding=(5, 2))

        # "필터:" 라벨 (ttk)
        ttk.Label(self.frame, text="🔽 필터:",
                  font=('맑은 고딕', 10, 'bold')).pack(side='left', padx=(0, 8))

        for col_id, label, width in filter_columns:
            ttk.Label(self.frame, text=f"{label}:",
                      font=('맑은 고딕', 9)).pack(side='left', padx=(0, 2))

            var = tk.StringVar(value="전체")
            combo = ttk.Combobox(self.frame, textvariable=var,
                                 values=["전체"], state="readonly",
                                 width=max(width // 10, 8))
            combo.pack(side='left', padx=(0, 8))
            combo.bind('<<ComboboxSelected>>', lambda e: self.on_filter())

            self.filter_vars[col_id] = var
            self.filter_combos[col_id] = combo

        # 초기화 버튼
        ttk.Button(self.frame, text="✖ 초기화", width=8,
                   command=self._reset_filters).pack(side='left', padx=5)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def _reset_filters(self):
        for var in self.filter_vars.values():
            var.set("전체")
        self.on_filter()

    def get_filters(self) -> dict:
        """현재 필터 값 → {'col_id': 'value', ...}. '전체'는 제외."""
        result = {}
        for col_id, var in self.filter_vars.items():
            val = var.get()
            if val and val != "전체":
                result[col_id] = val
        return result

    def update_filter_values(self, col_id: str, values: List[str]) -> None:
        """특정 컬럼의 필터 드롭다운 값 업데이트"""
        if col_id in self.filter_combos:
            seen = set()
            str_vals = []
            for v in values:
                if v is None:
                    continue
                v_str = str(v).strip()
                if v_str and v_str not in seen:
                    seen.add(v_str)
                    str_vals.append(v_str)
            all_values = ["전체"] + sorted(str_vals)
            self.filter_combos[col_id]['values'] = all_values


class FooterTotalBar:
    """
    Treeview 하단 합계 바

    v5.5.3 patch_03: ttk 위젯 사용 → 테마 자동 대응.
    숫자 강조는 bold체로 표현 (배경색 대신).
    
    Usage:
        footer = FooterTotalBar(parent)
        footer.pack(fill='x')
        footer.update({'net_kg': 100000, 'balance_kg': 95000, 'rows': 200})
    """

    def __init__(self, parent, is_dark: bool = False):
        """
        Args:
            parent: 부모 위젯
            is_dark: 하위 호환 (사용하지 않음, ttk가 자동 처리)
        """
        from tkinter import ttk

        self.frame = ttk.Frame(parent, padding=(5, 4))
        self._labels = {}

        fields = [
            ('rows', '📊 행수:', '0'),
            ('net_kg', '📦 NET(Kg):', '0'),
            ('balance_kg', '💰 Balance(Kg):', '0'),
        ]

        for key, label_text, default in fields:
            ttk.Label(self.frame, text=label_text,
                      font=('맑은 고딕', 11, 'bold')).pack(side='left', padx=(10, 2))
            lbl = ttk.Label(self.frame, text=default,
                            font=('맑은 고딕', 12, 'bold'))
            lbl.pack(side='left', padx=(0, 15))
            self._labels[key] = lbl

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def update(self, data: dict) -> None:
        """합계 업데이트. data keys: rows, net_kg, balance_kg"""
        for key, lbl in self._labels.items():
            val = data.get(key, 0)
            if isinstance(val, (int, float)):
                lbl.config(text=f"{val:,.0f}")
            else:
                lbl.config(text=str(val))
