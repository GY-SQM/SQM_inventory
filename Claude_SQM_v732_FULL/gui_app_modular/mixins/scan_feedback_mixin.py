# -*- coding: utf-8 -*-
"""
SQM v7.3.2.1 — 스캔 피드백 (바코드 조회) 패널 Mixin
===================================================
바코드 입력 → 즉시 톤백 정보 조회 및 색상 코드 표시.
"""
import logging
from ..utils.constants import tk
from ..utils.constants import ttk

from ..utils.ui_constants import ThemeColors, Spacing, center_dialog
from ..utils.db_helper import fetchone, fetchall

logger = logging.getLogger(__name__)

_STATUS_COLORS = {
    'AVAILABLE': ('#10b981', '판매가능'),
    'RESERVED':  ('#0ea5e9', '판매배정'),
    'PICKED':    ('#f59e0b', '판매화물 결정'),
    'SOLD':      ('#ef4444', '출고완료'),
    'OUTBOUND':  ('#ef4444', '출고완료'),
    'SHIPPED':   ('#6366f1', '선적'),
}


class ScanFeedbackMixin:
    """바코드 즉시 조회 패널."""

    def _open_scan_feedback_panel(self) -> None:
        """바코드 조회 패널 Toplevel 열기."""
        try:
            root = getattr(self, 'root', None)
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            bg = ThemeColors.get('bg_primary', is_dark)
            card_bg = ThemeColors.get('bg_card', is_dark)
            fg = ThemeColors.get('text_primary', is_dark)
            fg2 = ThemeColors.get('text_secondary', is_dark)

            dlg = tk.Toplevel(root)
            dlg.title("바코드 조회")
            dlg.geometry("480x520")
            dlg.configure(bg=bg)
            dlg.transient(root)
            dlg.resizable(True, True)
            center_dialog(dlg, root)

            # 바코드 입력
            tk.Label(dlg, text="바코드 스캔/입력",
                     font=('맑은 고딕', 12, 'bold'), fg=fg, bg=bg).pack(
                pady=(Spacing.MD, Spacing.SM))

            entry_var = tk.StringVar()
            entry = tk.Entry(dlg, textvariable=entry_var,
                             font=('Consolas', 14, 'bold'), justify='center',
                             width=28, relief='solid', bd=2)
            entry.pack(pady=Spacing.XS)
            entry.focus_set()

            # 결과 영역
            result_frame = tk.Frame(dlg, bg=card_bg, relief='groove', bd=1,
                                    padx=16, pady=12)
            result_frame.pack(fill=tk.BOTH, expand=True,
                              padx=Spacing.MD, pady=Spacing.SM)

            result_label = tk.Label(result_frame, text="바코드를 스캔하세요",
                                    font=('맑은 고딕', 11), fg=fg2,
                                    bg=card_bg, wraplength=400, justify='left')
            result_label.pack(fill=tk.BOTH, expand=True)

            # 이력 영역
            tk.Label(dlg, text="최근 조회 이력",
                     font=('맑은 고딕', 10, 'bold'), fg=fg2, bg=bg).pack(
                anchor=tk.W, padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

            history_list = tk.Listbox(dlg, font=('맑은 고딕', 9), height=3,
                                       bg=card_bg, fg=fg, relief='flat',
                                       selectmode='browse')
            history_list.pack(fill=tk.X, padx=Spacing.MD,
                              pady=(0, Spacing.SM))

            scan_history = []

            def _do_lookup(event=None):
                try:
                    barcode = entry_var.get().strip()
                    if not barcode:
                        return
                    entry_var.set('')

                    row = fetchone(self,
                        """SELECT t.tonbag_uid, t.sub_lt, t.lot_no, t.status,
                                  t.weight_kg, t.location,
                                  i.product_name
                           FROM inventory_tonbag t
                           LEFT JOIN inventory i ON t.lot_no = i.lot_no
                           WHERE t.tonbag_uid = ? OR t.sub_lt = ?
                           LIMIT 1""",
                        (barcode, barcode))

                    if row:
                        status = str(row.get('status', '')).upper()
                        s_color, s_label = _STATUS_COLORS.get(
                            status, ('#94a3b8', status or '알수없음'))
                        lot = row.get('lot_no', '-')
                        product = row.get('product_name', '-') or '-'
                        weight = row.get('weight_kg', 0) or 0
                        location = row.get('location', '-') or '-'
                        uid = row.get('tonbag_uid', barcode)

                        info = (
                            f"LOT: {lot}\n"
                            f"제품: {product}\n"
                            f"중량: {weight:,.1f} kg\n"
                            f"위치: {location}\n"
                            f"상태: {s_label}"
                        )
                        result_label.config(text=info, fg=s_color)
                        result_frame.config(bg=card_bg)

                        # 3초 후 배경 리셋
                        dlg.after(3000, lambda: result_label.config(fg=fg)
                                  if result_label.winfo_exists() else None)
                    else:
                        result_label.config(
                            text=f"미등록 바코드: {barcode}", fg='#94a3b8')

                    # 이력 추가 (최대 3개)
                    scan_history.insert(0, barcode)
                    if len(scan_history) > 3:
                        scan_history.pop()
                    history_list.delete(0, tk.END)
                    for h in scan_history:
                        history_list.insert(tk.END, h)

                except Exception as e:
                    logger.error(f"_do_lookup 오류: {e}")
                    result_label.config(text=f"조회 오류: {e}", fg='#ef4444')

            entry.bind('<Return>', _do_lookup)

            # 닫기
            ttk.Button(dlg, text="닫기", command=dlg.destroy).pack(
                pady=(0, Spacing.MD))
            dlg.bind('<Escape>', lambda e: dlg.destroy())

        except Exception as e:
            logger.error(f"_open_scan_feedback_panel 오류: {e}")
