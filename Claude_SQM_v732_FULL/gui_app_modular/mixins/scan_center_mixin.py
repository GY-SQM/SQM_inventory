# -*- coding: utf-8 -*-
"""
SQM v7.3.2.1 — 스캔 커맨드 센터 Mixin
=====================================
Picked 탭 내 스캔 제어 패널 + 톤백 상세 + PDA 모드.
"""
import logging
from ..utils.constants import tk
from ..utils.constants import ttk

from ..utils.ui_constants import ThemeColors, Spacing, center_dialog, apply_tooltip
from ..utils.db_helper import fetchone, fetchall

logger = logging.getLogger(__name__)

_TB_DETAIL_COLS = [
    ('sub_lt', '톤백No', 70, 'center'),
    ('status', '상태', 90, 'center'),
    ('weight_kg', '중량(kg)', 90, 'e'),
    ('location', '위치', 80, 'center'),
]


class ScanCenterMixin:
    """스캔 커맨드 센터: 액션 버튼 + 대상 카드 + 톤백 상세 트리."""

    def _build_scan_center(self, parent) -> None:
        """Picked 탭 내 스캔 제어 패널 빌드."""
        try:
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            bg = ThemeColors.get('bg_primary', is_dark)
            card_bg = ThemeColors.get('bg_card', is_dark)
            fg = ThemeColors.get('text_primary', is_dark)
            fg2 = ThemeColors.get('text_secondary', is_dark)
            accent = ThemeColors.get('primary', is_dark)

            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, padx=Spacing.XS, pady=Spacing.XS)

            # 액션 버튼
            btn_bar = ttk.Frame(frame)
            btn_bar.pack(fill=tk.X, pady=(0, Spacing.SM))

            actions = [
                ("파일 업로드", lambda: self._safe_call('_on_upload_scan_file')
                 if hasattr(self, '_safe_call') else None),
                ("실시간 스캔", lambda: self._safe_call('_open_live_scan_session')
                 if hasattr(self, '_safe_call') else None),
                ("리포트", lambda: self._safe_call('_on_scan_report')
                 if hasattr(self, '_safe_call') else None),
                ("새로고침", self._refresh_scan_center),
            ]
            for text, cmd in actions:
                b = ttk.Button(btn_bar, text=text, command=cmd)
                b.pack(side=tk.LEFT, padx=Spacing.XS)

            pda_btn = ttk.Button(btn_bar, text="PDA 모드",
                                  command=self._open_pda_mode)
            pda_btn.pack(side=tk.RIGHT, padx=Spacing.XS)
            apply_tooltip(pda_btn, "바코드 즉시 조회 PDA 팝업")

            # 대상 카드
            self._scan_target_frame = tk.Frame(frame, bg=card_bg,
                                                relief='groove', bd=1,
                                                padx=12, pady=8)
            self._scan_target_frame.pack(fill=tk.X, pady=Spacing.XS)

            self._scan_target_labels = {}
            fields = [
                ('lot_no', 'LOT NO', '-'),
                ('customer', '고객사', '-'),
                ('picking_no', '피킹No', '-'),
                ('tonbag_count', '톤백 수', '0개'),
                ('weight', '중량', '0 kg'),
                ('progress', '진행률', '0%'),
            ]
            for field_id, label, default in fields:
                row_f = tk.Frame(self._scan_target_frame, bg=card_bg)
                row_f.pack(fill=tk.X, pady=1)
                tk.Label(row_f, text=f"{label}:", font=('맑은 고딕', 9),
                         fg=fg2, bg=card_bg, width=8, anchor='w').pack(
                    side=tk.LEFT)
                val_lbl = tk.Label(row_f, text=default,
                                    font=('맑은 고딕', 10, 'bold'),
                                    fg=fg, bg=card_bg)
                val_lbl.pack(side=tk.LEFT, padx=4)
                self._scan_target_labels[field_id] = val_lbl

            # 톤백 상세 Treeview
            ttk.Label(frame, text="톤백 상세").pack(
                anchor=tk.W, padx=Spacing.XS, pady=(Spacing.SM, Spacing.XS))

            tree_frame = ttk.Frame(frame)
            tree_frame.pack(fill=tk.BOTH, expand=True)

            cols = [c[0] for c in _TB_DETAIL_COLS]
            self._scan_tb_tree = ttk.Treeview(
                tree_frame, columns=cols, show='headings', height=8,
                selectmode='browse')
            for col_id, label, width, anchor in _TB_DETAIL_COLS:
                self._scan_tb_tree.heading(col_id, text=label)
                self._scan_tb_tree.column(col_id, width=width, anchor=anchor)

            sb = tk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                              command=self._scan_tb_tree.yview)
            self._scan_tb_tree.configure(yscrollcommand=sb.set)
            self._scan_tb_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            sb.pack(side=tk.RIGHT, fill=tk.Y)

        except Exception as e:
            logger.error(f"_build_scan_center 오류: {e}")

    def _sync_scan_center(self, lot_row=None) -> None:
        """선택된 LOT 정보로 카드 동기화."""
        try:
            labels = getattr(self, '_scan_target_labels', {})
            if not labels:
                return

            if lot_row:
                labels.get('lot_no', tk.Label()).config(
                    text=str(lot_row.get('lot_no', '-')))
                labels.get('customer', tk.Label()).config(
                    text=str(lot_row.get('customer', '-') or '-'))
                labels.get('picking_no', tk.Label()).config(
                    text=str(lot_row.get('picking_no', '-') or '-'))
                cnt = int(lot_row.get('tonbag_count', 0) or 0)
                labels.get('tonbag_count', tk.Label()).config(
                    text=f"{cnt}개")
                wt = float(lot_row.get('total_kg', 0) or 0)
                labels.get('weight', tk.Label()).config(
                    text=f"{wt:,.0f} kg")

                # 진행률 계산
                scanned = int(lot_row.get('scanned', 0) or 0)
                pct = (scanned / cnt * 100) if cnt > 0 else 0
                labels.get('progress', tk.Label()).config(
                    text=f"{pct:.0f}% ({scanned}/{cnt})")

                self._load_tonbag_detail(str(lot_row.get('lot_no', '')))
            else:
                for fid in labels:
                    labels[fid].config(text='-')
        except Exception as e:
            logger.debug(f"_sync_scan_center: {e}")

    def _load_tonbag_detail(self, lot_no) -> None:
        """DB에서 톤백 목록 로드."""
        try:
            tree = getattr(self, '_scan_tb_tree', None)
            if not tree:
                return
            for item in tree.get_children(''):
                tree.delete(item)

            if not lot_no:
                return

            rows = fetchall(self,
                """SELECT sub_lt, status, weight_kg, location
                   FROM inventory_tonbag
                   WHERE lot_no = ?
                   ORDER BY sub_lt""",
                (lot_no,))

            for r in (rows or []):
                tree.insert('', 'end', values=(
                    str(r.get('sub_lt', '')),
                    str(r.get('status', '')),
                    f"{float(r.get('weight_kg', 0) or 0):,.1f}",
                    str(r.get('location', '') or '-'),
                ))
        except Exception as e:
            logger.debug(f"_load_tonbag_detail: {e}")

    def _refresh_scan_center(self) -> None:
        """현재 선택된 LOT로 스캔 센터 새로고침."""
        try:
            tree = getattr(self, 'tree_picked', None)
            if not tree:
                return
            sel = tree.selection()
            if not sel:
                self._sync_scan_center(None)
                return

            item = tree.item(sel[0])
            vals = item.get('values', [])
            if len(vals) >= 6:
                lot_row = {
                    'lot_no': vals[1],
                    'picking_no': vals[2],
                    'customer': vals[3],
                    'tonbag_count': vals[4],
                    'total_kg': str(vals[5]).replace(',', ''),
                }
                self._sync_scan_center(lot_row)
        except Exception as e:
            logger.debug(f"_refresh_scan_center: {e}")

    def _open_pda_mode(self) -> None:
        """PDA 모드 팝업: 바코드 입력 + 즉시 조회."""
        try:
            root = getattr(self, 'root', None)
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            bg = ThemeColors.get('bg_primary', is_dark)
            card_bg = ThemeColors.get('bg_card', is_dark)
            fg = ThemeColors.get('text_primary', is_dark)
            fg2 = ThemeColors.get('text_secondary', is_dark)

            dlg = tk.Toplevel(root)
            dlg.title("PDA 스캔 모드")
            dlg.geometry("480x380")
            dlg.configure(bg=bg)
            dlg.transient(root)
            dlg.resizable(False, False)
            center_dialog(dlg, root)

            tk.Label(dlg, text="PDA 스캔 모드",
                     font=('맑은 고딕', 14, 'bold'), fg=fg, bg=bg).pack(
                pady=(Spacing.MD, Spacing.SM))

            entry_var = tk.StringVar()
            entry = tk.Entry(dlg, textvariable=entry_var,
                             font=('Consolas', 16, 'bold'), justify='center',
                             width=24, relief='solid', bd=2)
            entry.pack(pady=Spacing.SM)
            entry.focus_set()

            result_frame = tk.Frame(dlg, bg=card_bg, relief='groove', bd=1,
                                    padx=16, pady=12)
            result_frame.pack(fill=tk.BOTH, expand=True,
                              padx=Spacing.MD, pady=Spacing.SM)

            result_lbl = tk.Label(result_frame, text="바코드를 스캔하세요",
                                   font=('맑은 고딕', 11), fg=fg2, bg=card_bg,
                                   wraplength=380, justify='left')
            result_lbl.pack(fill=tk.BOTH, expand=True)

            def _pda_lookup(event=None):
                try:
                    barcode = entry_var.get().strip()
                    if not barcode:
                        return
                    entry_var.set('')

                    row = fetchone(self,
                        """SELECT t.tonbag_uid, t.sub_lt, t.lot_no, t.status,
                                  t.weight_kg, t.location
                           FROM inventory_tonbag t
                           WHERE t.tonbag_uid = ? OR t.sub_lt = ?
                           LIMIT 1""",
                        (barcode, barcode))

                    if row:
                        status = str(row.get('status', '')).upper()
                        info = (
                            f"LOT: {row.get('lot_no', '-')}\n"
                            f"중량: {float(row.get('weight_kg', 0) or 0):,.1f} kg\n"
                            f"위치: {row.get('location', '-') or '-'}\n"
                            f"상태: {status}"
                        )
                        color = '#10b981' if status == 'PICKED' else '#f59e0b'
                        result_lbl.config(text=info, fg=color)
                    else:
                        result_lbl.config(text=f"미등록: {barcode}",
                                           fg='#ef4444')
                except Exception as e:
                    logger.debug(f"_pda_lookup: {e}")
                    result_lbl.config(text=f"오류: {e}", fg='#ef4444')

            entry.bind('<Return>', _pda_lookup)

            ttk.Button(dlg, text="닫기", command=dlg.destroy).pack(
                pady=(0, Spacing.MD))
            dlg.bind('<Escape>', lambda e: dlg.destroy())

        except Exception as e:
            logger.error(f"_open_pda_mode 오류: {e}")
