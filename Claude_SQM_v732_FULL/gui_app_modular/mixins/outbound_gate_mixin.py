# -*- coding: utf-8 -*-
"""
SQM v7.3.2 — 출고 사전 확인 게이트 Mixin
==========================================
4-checkbox gate widget: 모든 항목 체크 시 확인 버튼 활성화.
"""
import logging
import tkinter as tk
from tkinter import ttk

from ..utils.ui_constants import ThemeColors, Spacing

logger = logging.getLogger(__name__)


class OutboundGateMixin:
    """출고 사전 확인 4-체크 게이트 위젯."""

    def _build_outbound_gate(self, parent, title="출고 사전 확인",
                             items=None, accent="#f59e0b",
                             on_all_checked=None) -> dict:
        """2x2 그리드 체크 게이트 빌드. 모두 체크 시 확인 버튼 활성화."""
        try:
            if items is None:
                items = ["서류 일치 확인", "수량 일치 확인", "스캔 완료 확인", "위치 확인"]

            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            bg = ThemeColors.get('bg_card', is_dark)
            fg = ThemeColors.get('text_primary', is_dark)
            border_c = ThemeColors.get('border', is_dark)

            root_frame = ttk.Frame(parent)
            root_frame.pack(fill=tk.X, padx=Spacing.SM, pady=Spacing.SM)

            # 타이틀
            ttk.Label(root_frame, text=title,
                      font=('맑은 고딕', 12, 'bold')).pack(
                anchor=tk.W, padx=Spacing.XS, pady=(Spacing.XS, Spacing.SM))

            grid_frame = ttk.Frame(root_frame)
            grid_frame.pack(fill=tk.X, padx=Spacing.SM, pady=Spacing.XS)

            checks = {}
            labels_map = {}

            def _on_toggle(label_text):
                try:
                    var = checks[label_text]
                    new_val = not var.get()
                    var.set(new_val)
                    lbl = labels_map[label_text]
                    if new_val:
                        lbl.config(text=f"  {label_text}", fg=accent)
                    else:
                        lbl.config(text=f"  {label_text}", fg=fg)
                    _check_all()
                except Exception as e:
                    logger.debug(f"_on_toggle: {e}")

            def _check_all():
                try:
                    all_ok = all(v.get() for v in checks.values())
                    if all_ok:
                        confirm_btn.config(state=tk.NORMAL)
                        if on_all_checked:
                            on_all_checked()
                    else:
                        confirm_btn.config(state=tk.DISABLED)
                except Exception as e:
                    logger.debug(f"_check_all: {e}")

            for idx, item_text in enumerate(items):
                row, col = divmod(idx, 2)
                var = tk.BooleanVar(value=False)
                checks[item_text] = var

                cell = tk.Frame(grid_frame, bg=bg, relief='groove', bd=1,
                                padx=8, pady=6)
                cell.grid(row=row, column=col, padx=4, pady=4, sticky='nsew')

                lbl = tk.Label(cell, text=f"  {item_text}",
                               font=('맑은 고딕', 11), fg=fg, bg=bg,
                               cursor='hand2', anchor='w')
                lbl.pack(fill=tk.X)
                lbl.bind('<Button-1>', lambda e, t=item_text: _on_toggle(t))
                labels_map[item_text] = lbl

            grid_frame.columnconfigure(0, weight=1)
            grid_frame.columnconfigure(1, weight=1)

            # 확인 버튼
            confirm_btn = ttk.Button(root_frame, text="출고 확인",
                                     state=tk.DISABLED)
            confirm_btn.pack(pady=(Spacing.SM, Spacing.XS))

            return {
                "checks": checks,
                "confirm_btn": confirm_btn,
                "root": root_frame,
            }
        except Exception as e:
            logger.error(f"_build_outbound_gate 오류: {e}")
            return {"checks": {}, "confirm_btn": None, "root": ttk.Frame(parent)}

    def _reset_outbound_gate(self, gate_refs: dict) -> None:
        """게이트 체크 초기화."""
        try:
            checks = gate_refs.get("checks", {})
            for var in checks.values():
                var.set(False)
            btn = gate_refs.get("confirm_btn")
            if btn:
                btn.config(state=tk.DISABLED)
        except Exception as e:
            logger.debug(f"_reset_outbound_gate: {e}")
