# -*- coding: utf-8 -*-
"""
SQM v7.3.2 — 스캔 탭
=====================
바코드 입력 → 조회 → 출고 확정/배정 취소. 이력 20건 표시.
"""
import logging
import tkinter as tk
from tkinter import ttk

from ..utils.constants import BOTH, YES, LEFT, RIGHT, X, Y, VERTICAL
from ..utils.ui_constants import ThemeColors, Spacing, apply_tooltip
from ..utils.db_helper import fetchone, fetchall, execute as db_execute

logger = logging.getLogger(__name__)

_STATUS_BADGE = {
    'AVAILABLE': ('\u25cf 판매가능', '#10b981'),
    'RESERVED':  ('\u25cf 판매배정', '#0ea5e9'),
    'PICKED':    ('\u25cf 판매화물 결정', '#f59e0b'),
    'SOLD':      ('\u25cf 출고완료', '#ef4444'),
    'OUTBOUND':  ('\u25cf 출고완료', '#ef4444'),
    'SHIPPED':   ('\u25cf 선적', '#6366f1'),
}

_HIST_COLUMNS = [
    ('time', '시간', 80, 'center'),
    ('barcode', '바코드', 130, 'center'),
    ('lot_no', 'LOT', 110, 'center'),
    ('status', '상태', 90, 'center'),
    ('action', '처리', 100, 'center'),
]


class ScanTabMixin:
    """스캔 탭: 바코드 조회 + 출고 확정 + 배정 취소."""

    def _setup_scan_tab(self) -> None:
        """스캔 탭 UI 구성."""
        try:
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            bg = ThemeColors.get('bg_primary', is_dark)
            card_bg = ThemeColors.get('bg_card', is_dark)
            fg = ThemeColors.get('text_primary', is_dark)
            fg2 = ThemeColors.get('text_secondary', is_dark)

            frame = getattr(self, 'tab_scan', None)
            if not frame:
                logger.warning("tab_scan 프레임 없음")
                return

            # 상단: 바코드 입력
            input_f = ttk.Frame(frame)
            input_f.pack(fill=X, padx=Spacing.SM, pady=Spacing.SM)

            ttk.Label(input_f, text="바코드 스캔:",
                      font=('맑은 고딕', 11, 'bold')).pack(
                side=LEFT, padx=(0, Spacing.SM))

            self._scan_tab_var = tk.StringVar()
            self._scan_tab_entry = tk.Entry(
                input_f, textvariable=self._scan_tab_var,
                font=('Consolas', 16, 'bold'), width=28,
                relief='solid', bd=2)
            self._scan_tab_entry.pack(side=LEFT, padx=Spacing.XS)
            self._scan_tab_entry.bind('<Return>', lambda e: self._do_scan_lookup())
            self._scan_tab_entry.focus_set()

            ttk.Button(input_f, text="조회",
                       command=self._do_scan_lookup).pack(
                side=LEFT, padx=Spacing.XS)

            # 결과 카드
            self._scan_result_frame = tk.Frame(frame, bg=card_bg,
                                                relief='groove', bd=1,
                                                padx=16, pady=12)
            self._scan_result_frame.pack(fill=X, padx=Spacing.SM,
                                          pady=Spacing.XS)

            self._scan_result_labels = {}
            fields = [
                ('lot_no', 'LOT NO', '-'),
                ('product', '제품', '-'),
                ('weight', '중량', '-'),
                ('location', '위치', '-'),
                ('status', '상태', '-'),
            ]
            for field_id, label, default in fields:
                row_f = tk.Frame(self._scan_result_frame, bg=card_bg)
                row_f.pack(fill=X, pady=2)
                tk.Label(row_f, text=f"{label}:", font=('맑은 고딕', 10),
                         fg=fg2, bg=card_bg, width=8, anchor='w').pack(
                    side=LEFT)
                val_lbl = tk.Label(row_f, text=default,
                                    font=('맑은 고딕', 11, 'bold'),
                                    fg=fg, bg=card_bg)
                val_lbl.pack(side=LEFT, padx=8)
                self._scan_result_labels[field_id] = val_lbl

            # 상태 배지
            self._scan_status_badge = tk.Label(
                self._scan_result_frame, text="",
                font=('맑은 고딕', 12, 'bold'), bg=card_bg)
            self._scan_status_badge.pack(anchor=tk.E, pady=(Spacing.XS, 0))

            # 액션 버튼
            action_f = ttk.Frame(frame)
            action_f.pack(fill=X, padx=Spacing.SM, pady=Spacing.SM)

            self._scan_btn_sold = ttk.Button(
                action_f, text="출고 확정 (PICKED -> SOLD)",
                command=self._do_scan_confirm_sold, state=tk.DISABLED)
            self._scan_btn_sold.pack(side=LEFT, padx=Spacing.XS)
            apply_tooltip(self._scan_btn_sold,
                          "선택된 톤백을 PICKED에서 SOLD로 변경합니다.")

            self._scan_btn_cancel = ttk.Button(
                action_f, text="배정 취소 (-> AVAILABLE)",
                command=self._do_scan_cancel, state=tk.DISABLED)
            self._scan_btn_cancel.pack(side=LEFT, padx=Spacing.XS)
            apply_tooltip(self._scan_btn_cancel,
                          "선택된 톤백의 배정을 취소하고 AVAILABLE로 변경합니다.")

            # LOT 모드 버튼
            self._scan_btn_lot_bind = ttk.Button(
                action_f, text="LOT 예약 연결",
                command=self._do_scan_bind_reserved, state=tk.DISABLED)
            self._scan_btn_lot_bind.pack(side=LEFT, padx=Spacing.XS)
            apply_tooltip(self._scan_btn_lot_bind,
                          "AVAILABLE 톤백을 LOT모드 예약에 연결합니다 (→RESERVED).")

            self._scan_btn_lot_pick = ttk.Button(
                action_f, text="LOT 즉시 PICKED",
                command=self._do_scan_pick_execute, state=tk.DISABLED)
            self._scan_btn_lot_pick.pack(side=LEFT, padx=Spacing.XS)
            apply_tooltip(self._scan_btn_lot_pick,
                          "AVAILABLE 톤백을 LOT모드 예약에 연결하고 즉시 PICKED 처리합니다.")

            # 이력 Treeview
            ttk.Label(frame, text="스캔 이력 (최근 20건)",
                      font=('맑은 고딕', 10, 'bold')).pack(
                anchor=tk.W, padx=Spacing.SM, pady=(Spacing.SM, Spacing.XS))

            hist_frame = ttk.Frame(frame)
            hist_frame.pack(fill=BOTH, expand=YES,
                            padx=Spacing.SM, pady=(0, Spacing.SM))

            cols = [c[0] for c in _HIST_COLUMNS]
            self._scan_hist_tree = ttk.Treeview(
                hist_frame, columns=cols, show='headings', height=12,
                selectmode='none')
            for col_id, label, width, anchor in _HIST_COLUMNS:
                self._scan_hist_tree.heading(col_id, text=label)
                self._scan_hist_tree.column(col_id, width=width, anchor=anchor)

            sb = tk.Scrollbar(hist_frame, orient=VERTICAL,
                              command=self._scan_hist_tree.yview)
            self._scan_hist_tree.configure(yscrollcommand=sb.set)
            self._scan_hist_tree.pack(side=LEFT, fill=BOTH, expand=YES)
            sb.pack(side=RIGHT, fill=Y)

            self._scan_hist_tree.tag_configure('ok', foreground='#10b981')
            self._scan_hist_tree.tag_configure('err', foreground='#ef4444')
            self._scan_hist_tree.tag_configure('warn', foreground='#f59e0b')

            # 마지막 조회 결과 임시 저장
            self._scan_last_row = None

        except Exception as e:
            logger.error(f"_setup_scan_tab 오류: {e}")

    def _do_scan_lookup(self) -> None:
        """바코드 조회 실행."""
        try:
            barcode = self._scan_tab_var.get().strip()
            if not barcode:
                return
            self._scan_tab_var.set('')

            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            fg = ThemeColors.get('text_primary', is_dark)
            card_bg = ThemeColors.get('bg_card', is_dark)

            row = fetchone(self,
                """SELECT t.tonbag_uid, t.sub_lt, t.lot_no, t.status,
                          t.weight_kg, t.location,
                          i.product_name
                   FROM inventory_tonbag t
                   LEFT JOIN inventory i ON t.lot_no = i.lot_no
                   WHERE t.tonbag_uid = ? OR t.sub_lt = ?
                   LIMIT 1""",
                (barcode, barcode))

            labels = self._scan_result_labels
            badge = self._scan_status_badge

            if row:
                self._scan_last_row = row
                lot = str(row.get('lot_no', '-'))
                product = str(row.get('product_name', '-') or '-')
                weight = float(row.get('weight_kg', 0) or 0)
                location = str(row.get('location', '-') or '-')
                status = str(row.get('status', '')).upper()

                labels.get('lot_no', tk.Label()).config(text=lot)
                labels.get('product', tk.Label()).config(text=product)
                labels.get('weight', tk.Label()).config(
                    text=f"{weight:,.1f} kg")
                labels.get('location', tk.Label()).config(text=location)
                labels.get('status', tk.Label()).config(text=status)

                # 상태 배지
                badge_text, badge_color = _STATUS_BADGE.get(
                    status, (status, '#94a3b8'))
                badge.config(text=badge_text, fg=badge_color)

                # 버튼 활성화
                if status == 'PICKED':
                    self._scan_btn_sold.config(state=tk.NORMAL)
                    self._scan_btn_cancel.config(state=tk.NORMAL)
                    self._scan_btn_lot_bind.config(state=tk.DISABLED)
                    self._scan_btn_lot_pick.config(state=tk.DISABLED)
                elif status == 'AVAILABLE':
                    self._scan_btn_sold.config(state=tk.DISABLED)
                    self._scan_btn_cancel.config(state=tk.NORMAL)
                    self._scan_btn_lot_bind.config(state=tk.NORMAL)
                    self._scan_btn_lot_pick.config(state=tk.NORMAL)
                elif status == 'RESERVED':
                    self._scan_btn_sold.config(state=tk.DISABLED)
                    self._scan_btn_cancel.config(state=tk.NORMAL)
                    self._scan_btn_lot_bind.config(state=tk.DISABLED)
                    self._scan_btn_lot_pick.config(state=tk.DISABLED)
                else:
                    self._scan_btn_sold.config(state=tk.DISABLED)
                    self._scan_btn_cancel.config(state=tk.DISABLED)
                    self._scan_btn_lot_bind.config(state=tk.DISABLED)
                    self._scan_btn_lot_pick.config(state=tk.DISABLED)

                self._add_scan_history(barcode, lot, status, '조회', 'ok')
            else:
                self._scan_last_row = None
                for key in labels:
                    labels[key].config(text='-')
                badge.config(text='미등록', fg='#94a3b8')
                self._scan_btn_sold.config(state=tk.DISABLED)
                self._scan_btn_cancel.config(state=tk.DISABLED)
                self._scan_btn_lot_bind.config(state=tk.DISABLED)
                self._scan_btn_lot_pick.config(state=tk.DISABLED)
                self._add_scan_history(barcode, '-', '-', '미등록', 'err')

        except Exception as e:
            logger.error(f"_do_scan_lookup 오류: {e}")

    def _do_scan_confirm_sold(self) -> None:
        """PICKED -> SOLD 전환."""
        try:
            row = self._scan_last_row
            if not row:
                return

            uid = row.get('tonbag_uid', '')
            lot_no = row.get('lot_no', '')
            status = str(row.get('status', '')).upper()

            if status != 'PICKED':
                from tkinter import messagebox
                messagebox.showwarning("출고 확정",
                                       "PICKED 상태의 톤백만 출고 확정 가능합니다.",
                                       parent=getattr(self, 'root', None))
                return

            from tkinter import messagebox
            if not messagebox.askyesno("출고 확정",
                                        f"톤백 {uid}을 출고 확정(SOLD)하시겠습니까?",
                                        parent=getattr(self, 'root', None)):
                return

            ok1 = db_execute(self,
                "UPDATE inventory_tonbag SET status = 'SOLD' WHERE tonbag_uid = ?",
                (uid,))
            ok2 = db_execute(self,
                "UPDATE picking_table SET status = 'SOLD' WHERE lot_no = ? AND sub_lt = ? AND status = 'ACTIVE'",
                (lot_no, row.get('sub_lt', '')))

            if ok1:
                db_execute(self,
                    "INSERT INTO audit_log (action_type, lot_no, tonbag_id, detail) "
                    "VALUES (?, ?, ?, ?)",
                    ('SCAN_SOLD', lot_no, uid, 'PICKED->SOLD (스캔탭)'))
                self._add_scan_history(uid, lot_no, 'SOLD', '출고확정', 'ok')
                self._scan_btn_sold.config(state=tk.DISABLED)
                self._scan_btn_cancel.config(state=tk.DISABLED)

                # 새로고침
                for fn in ('_refresh_picked', '_refresh_sold'):
                    if hasattr(self, fn):
                        try:
                            getattr(self, fn)()
                        except Exception:
                            pass
            else:
                self._add_scan_history(uid, lot_no, 'ERROR', '실패', 'err')

        except Exception as e:
            logger.error(f"_do_scan_confirm_sold 오류: {e}")

    def _do_scan_cancel(self) -> None:
        """배정 취소: -> AVAILABLE."""
        try:
            row = self._scan_last_row
            if not row:
                return

            uid = row.get('tonbag_uid', '')
            lot_no = row.get('lot_no', '')

            from tkinter import messagebox
            if not messagebox.askyesno("배정 취소",
                                        f"톤백 {uid}의 배정을 취소하시겠습니까?",
                                        parent=getattr(self, 'root', None)):
                return

            ok = db_execute(self,
                "UPDATE inventory_tonbag SET status = 'AVAILABLE' WHERE tonbag_uid = ?",
                (uid,))

            if ok:
                db_execute(self,
                    "INSERT INTO audit_log (action_type, lot_no, tonbag_id, detail) "
                    "VALUES (?, ?, ?, ?)",
                    ('SCAN_CANCEL', lot_no, uid, '배정취소->AVAILABLE (스캔탭)'))
                self._add_scan_history(uid, lot_no, 'AVAILABLE', '배정취소', 'warn')
                self._scan_btn_sold.config(state=tk.DISABLED)
                self._scan_btn_cancel.config(state=tk.DISABLED)

                for fn in ('_refresh_picked', '_refresh_inventory'):
                    if hasattr(self, fn):
                        try:
                            getattr(self, fn)()
                        except Exception:
                            pass
            else:
                self._add_scan_history(uid, lot_no, 'ERROR', '실패', 'err')

        except Exception as e:
            logger.error(f"_do_scan_cancel 오류: {e}")

    def _add_scan_history(self, barcode, lot_no, status, action,
                           tag='ok') -> None:
        """이력 Treeview에 추가 (최대 20건)."""
        try:
            tree = getattr(self, '_scan_hist_tree', None)
            if not tree:
                return

            from datetime import datetime
            now = datetime.now().strftime('%H:%M:%S')

            tree.insert('', 0, values=(now, barcode, lot_no, status, action),
                         tags=(tag,))

            # 최대 20건 유지
            children = tree.get_children('')
            if len(children) > 20:
                for old in children[20:]:
                    tree.delete(old)

        except Exception as e:
            logger.debug(f"_add_scan_history: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # v7.3.2 Phase3 포팅: LOT 모드 스캔 핸들러
    # ═══════════════════════════════════════════════════════════════════

    def _do_scan_bind_reserved(self) -> None:
        """현재 UID를 LOT모드 RESERVED 행에 연결(AVAILABLE->RESERVED)."""
        row = self._scan_last_row
        if not row:
            return
        uid = row.get('tonbag_uid', '') or row.get('sub_lt', '')
        if not uid:
            return
        engine = getattr(self, 'engine', None)
        if not engine or not hasattr(engine, 'safe_bind_scanned_uid_to_reserved_plan'):
            return

        try:
            lot_no = str(row.get('lot_no', '') or '')
            result = engine.safe_bind_scanned_uid_to_reserved_plan(
                scanned_uid=uid,
                lot_no=lot_no,
                actor='scan_tab',
                auto_pick=False,
            )
            if result.get("success"):
                self._add_scan_history(uid, lot_no, 'RESERVED', 'LOT연결', 'ok')
                self._scan_btn_lot_bind.config(state=tk.DISABLED)
                self._scan_btn_lot_pick.config(state=tk.DISABLED)
                self._scan_btn_cancel.config(state=tk.NORMAL)
                # 상태 배지 갱신
                badge = self._scan_status_badge
                badge.config(text='\u25cf 판매배정', fg='#0ea5e9')
                # 새로고침
                for fn in ('_refresh_allocation', '_refresh_inventory'):
                    if hasattr(self, fn):
                        try:
                            getattr(self, fn)()
                        except Exception:
                            pass
            else:
                msg = "\n".join(result.get("errors", ["알 수 없는 오류"]))
                self._add_scan_history(uid, lot_no, 'ERROR', 'LOT연결실패', 'err')
                from tkinter import messagebox
                messagebox.showwarning("LOT 예약 연결 실패", msg,
                                       parent=getattr(self, 'root', None))
        except Exception as e:
            logger.error(f"_do_scan_bind_reserved 오류: {e}", exc_info=True)

    def _do_scan_pick_execute(self) -> None:
        """현재 UID를 LOT모드 예약에 연결하고 즉시 PICKED 처리."""
        row = self._scan_last_row
        if not row:
            return
        uid = row.get('tonbag_uid', '') or row.get('sub_lt', '')
        if not uid:
            return
        engine = getattr(self, 'engine', None)
        if not engine or not hasattr(engine, 'execute_lot_mode_scanned_outbound'):
            return

        try:
            lot_no = str(row.get('lot_no', '') or '')
            result = engine.execute_lot_mode_scanned_outbound(
                scanned_uid=uid,
                lot_no=lot_no,
                actor='scan_tab',
            )
            if result.get("success"):
                self._add_scan_history(uid, lot_no, 'PICKED', 'LOT즉시PICK', 'ok')
                self._scan_btn_lot_bind.config(state=tk.DISABLED)
                self._scan_btn_lot_pick.config(state=tk.DISABLED)
                self._scan_btn_sold.config(state=tk.NORMAL)
                self._scan_btn_cancel.config(state=tk.NORMAL)
                badge = self._scan_status_badge
                badge.config(text='\u25cf 판매화물 결정', fg='#f59e0b')
                for fn in ('_refresh_allocation', '_refresh_picked', '_refresh_inventory'):
                    if hasattr(self, fn):
                        try:
                            getattr(self, fn)()
                        except Exception:
                            pass
            else:
                msg = "\n".join(result.get("errors", ["알 수 없는 오류"]))
                self._add_scan_history(uid, lot_no, 'ERROR', 'PICK실패', 'err')
                from tkinter import messagebox
                messagebox.showwarning("LOT 즉시 PICKED 실패", msg,
                                       parent=getattr(self, 'root', None))
        except Exception as e:
            logger.error(f"_do_scan_pick_execute 오류: {e}", exc_info=True)
