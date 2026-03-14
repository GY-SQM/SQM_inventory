# -*- coding: utf-8 -*-
"""
SQM v7.3.2.1 — 출고 확인 다이얼로그 Mixin
=========================================
CONFIRM 입력 필수 모달 다이얼로그.
"""
import logging
from ..utils.constants import tk
from ..utils.constants import ttk
from datetime import datetime

from ..utils.ui_constants import ThemeColors, Spacing, center_dialog
from ..utils.db_helper import execute as db_execute

logger = logging.getLogger(__name__)


class OutboundConfirmMixin:
    """출고 확인 CONFIRM 다이얼로그."""

    def _open_outbound_confirm(self, lot_no, tonbag_cnt, weight_mt,
                                customer="", callback=None) -> bool:
        """CONFIRM 입력 모달. 확인 시 True, 취소 시 False."""
        result = {'confirmed': False}

        try:
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            bg = ThemeColors.get('bg_primary', is_dark)
            card_bg = ThemeColors.get('bg_card', is_dark)
            fg = ThemeColors.get('text_primary', is_dark)
            fg2 = ThemeColors.get('text_secondary', is_dark)
            accent = ThemeColors.get('danger', is_dark)
            success = ThemeColors.get('success', is_dark)

            root = getattr(self, 'root', None)
            dlg = tk.Toplevel(root)
            dlg.title("출고 확인")
            dlg.geometry("480x420")
            dlg.configure(bg=bg)
            dlg.transient(root)
            dlg.grab_set()
            dlg.resizable(False, False)
            center_dialog(dlg, root)

            # 헤더
            tk.Label(dlg, text="출고 최종 확인", font=('맑은 고딕', 16, 'bold'),
                     fg=accent, bg=bg).pack(pady=(Spacing.MD, Spacing.SM))

            tk.Label(dlg, text="아래 정보를 확인 후 CONFIRM을 입력하세요.",
                     font=('맑은 고딕', 10), fg=fg2, bg=bg).pack(
                pady=(0, Spacing.MD))

            # 정보 카드
            info_frame = tk.Frame(dlg, bg=card_bg, relief='groove', bd=1,
                                  padx=16, pady=12)
            info_frame.pack(fill=tk.X, padx=Spacing.LG, pady=Spacing.XS)

            cards = [
                ("LOT NO", lot_no, '#0ea5e9'),
                ("고객사", customer or "-", '#8b5cf6'),
                ("톤백 수", f"{tonbag_cnt}개", '#f59e0b'),
                ("중량", f"{weight_mt:,.1f} MT" if isinstance(weight_mt, (int, float)) else str(weight_mt), '#10b981'),
            ]
            for label, value, color in cards:
                row_f = tk.Frame(info_frame, bg=card_bg)
                row_f.pack(fill=tk.X, pady=3)
                tk.Label(row_f, text=f"{label}:", font=('맑은 고딕', 10),
                         fg=fg2, bg=card_bg, width=10, anchor='w').pack(
                    side=tk.LEFT)
                tk.Label(row_f, text=value, font=('맑은 고딕', 12, 'bold'),
                         fg=color, bg=card_bg).pack(side=tk.LEFT, padx=8)

            # 구분선
            ttk.Separator(dlg, orient='horizontal').pack(
                fill=tk.X, padx=Spacing.LG, pady=Spacing.MD)

            # CONFIRM 입력
            tk.Label(dlg, text='아래에 "CONFIRM" 을 입력하세요',
                     font=('맑은 고딕', 10, 'bold'), fg=fg, bg=bg).pack(
                pady=(0, Spacing.XS))

            entry_var = tk.StringVar()
            entry = tk.Entry(dlg, textvariable=entry_var,
                             font=('Consolas', 14, 'bold'), justify='center',
                             width=20, relief='solid', bd=2)
            entry.pack(pady=Spacing.XS)
            entry.focus_set()

            # 확인/취소 버튼
            btn_frame = tk.Frame(dlg, bg=bg)
            btn_frame.pack(pady=Spacing.MD)

            confirm_btn = ttk.Button(btn_frame, text="출고 확정",
                                      state=tk.DISABLED)
            confirm_btn.pack(side=tk.LEFT, padx=Spacing.SM)

            cancel_btn = ttk.Button(btn_frame, text="취소",
                                     command=dlg.destroy)
            cancel_btn.pack(side=tk.LEFT, padx=Spacing.SM)

            def _validate(*_args):
                try:
                    txt = entry_var.get().strip().upper()
                    if txt == "CONFIRM":
                        entry.config(bg='#d1fae5', fg='#065f46')
                        confirm_btn.config(state=tk.NORMAL)
                    else:
                        entry.config(bg='#fee2e2', fg='#991b1b')
                        confirm_btn.config(state=tk.DISABLED)
                except Exception as e:
                    logger.debug(f"_validate: {e}")

            entry_var.trace_add('write', _validate)

            def _on_confirm():
                try:
                    # audit_log 기록
                    try:
                        db_execute(self,
                                   "INSERT INTO audit_log (action_type, lot_no, detail) VALUES (?, ?, ?)",
                                   ('OUTBOUND_CONFIRM', lot_no,
                                    f"톤백 {tonbag_cnt}개, {weight_mt} MT, 고객: {customer}"))
                    except Exception as e:
                        logger.debug(f"audit_log 기록 실패: {e}")

                    result['confirmed'] = True
                    if callback:
                        callback()
                    dlg.destroy()
                except Exception as e:
                    logger.error(f"_on_confirm 오류: {e}")

            confirm_btn.config(command=_on_confirm)
            entry.bind('<Return>', lambda e: _on_confirm()
                       if entry_var.get().strip().upper() == "CONFIRM" else None)

            dlg.wait_window(dlg)

        except Exception as e:
            logger.error(f"_open_outbound_confirm 오류: {e}")

        return result['confirmed']
