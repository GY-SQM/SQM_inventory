# -*- coding: utf-8 -*-
"""
SQM v7.3.2 — 실시간 바코드 스캔 세션 Mixin
=============================================
모달 스캔 세션: 바코드 입력 → 중복 체크 → DB 검증 → LOT 매칭 → 진행률 표시.
"""
import logging
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from ..utils.ui_constants import ThemeColors, Spacing, center_dialog
from ..utils.db_helper import fetchone, execute as db_execute

logger = logging.getLogger(__name__)

_HIST_COLS = [
    ('time', '시간', 70, 'center'),
    ('barcode', '바코드', 120, 'center'),
    ('result', '결과', 80, 'center'),
    ('detail', '상세', 140, 'w'),
]


class LiveScanMixin:
    """실시간 바코드 스캔 세션 (모달)."""

    def _open_live_scan_session(self, lot_no="", tonbag_count=0) -> None:
        """스캔 세션 모달 열기."""
        try:
            root = getattr(self, 'root', None)
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            bg = ThemeColors.get('bg_primary', is_dark)
            card_bg = ThemeColors.get('bg_card', is_dark)
            fg = ThemeColors.get('text_primary', is_dark)
            fg2 = ThemeColors.get('text_secondary', is_dark)
            success_c = ThemeColors.get('success', is_dark)
            danger_c = ThemeColors.get('danger', is_dark)
            warn_c = ThemeColors.get('warning', is_dark)

            dlg = tk.Toplevel(root)
            dlg.title(f"실시간 스캔 — {lot_no}" if lot_no else "실시간 스캔")
            dlg.geometry("520x540")
            dlg.configure(bg=bg)
            dlg.transient(root)
            dlg.grab_set()
            dlg.resizable(True, True)
            center_dialog(dlg, root)

            # 세션 상태
            state = {
                'scanned_set': set(),
                'scanned_list': [],
                'session_ok': 0,
                'session_err': 0,
                'lot_no': lot_no,
                'expected': tonbag_count,
            }

            # 헤더
            hdr_f = tk.Frame(dlg, bg=bg)
            hdr_f.pack(fill=tk.X, padx=Spacing.SM, pady=Spacing.SM)
            tk.Label(hdr_f, text="실시간 스캔",
                     font=('맑은 고딕', 14, 'bold'), fg=fg, bg=bg).pack(
                side=tk.LEFT)
            if lot_no:
                tk.Label(hdr_f, text=f"  LOT: {lot_no}",
                         font=('맑은 고딕', 11), fg=ThemeColors.get('info', is_dark),
                         bg=bg).pack(side=tk.LEFT, padx=8)

            # 바코드 입력
            entry_var = tk.StringVar()
            entry = tk.Entry(dlg, textvariable=entry_var,
                             font=('Consolas', 14, 'bold'), justify='center',
                             width=30, relief='solid', bd=2)
            entry.pack(pady=Spacing.SM)
            entry.focus_set()

            # 상태 라벨
            status_lbl = tk.Label(dlg, text="바코드를 스캔하세요",
                                   font=('맑은 고딕', 11), fg=fg2, bg=bg)
            status_lbl.pack(pady=Spacing.XS)

            # 진행률
            progress_frame = tk.Frame(dlg, bg=bg)
            progress_frame.pack(fill=tk.X, padx=Spacing.MD, pady=Spacing.XS)

            progress_lbl = tk.Label(progress_frame,
                                     text=f"0 / {tonbag_count}",
                                     font=('맑은 고딕', 10), fg=fg2, bg=bg)
            progress_lbl.pack(side=tk.RIGHT)

            progress_bar = ttk.Progressbar(progress_frame, maximum=max(tonbag_count, 1),
                                           value=0, length=300)
            progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

            # 카운터
            counter_f = tk.Frame(dlg, bg=bg)
            counter_f.pack(fill=tk.X, padx=Spacing.MD, pady=Spacing.XS)

            ok_lbl = tk.Label(counter_f, text="성공: 0",
                               font=('맑은 고딕', 10, 'bold'),
                               fg=success_c, bg=bg)
            ok_lbl.pack(side=tk.LEFT, padx=8)
            err_lbl = tk.Label(counter_f, text="오류: 0",
                                font=('맑은 고딕', 10, 'bold'),
                                fg=danger_c, bg=bg)
            err_lbl.pack(side=tk.LEFT, padx=8)

            # 이력 Treeview
            ttk.Label(dlg, text="스캔 이력 (최근 10건)").pack(
                anchor=tk.W, padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

            tree_frame = ttk.Frame(dlg)
            tree_frame.pack(fill=tk.BOTH, expand=True,
                            padx=Spacing.MD, pady=(0, Spacing.SM))

            cols = [c[0] for c in _HIST_COLS]
            hist_tree = ttk.Treeview(tree_frame, columns=cols,
                                      show='headings', height=8,
                                      selectmode='none')
            for col_id, label, width, anchor in _HIST_COLS:
                hist_tree.heading(col_id, text=label)
                hist_tree.column(col_id, width=width, anchor=anchor)
            hist_tree.pack(fill=tk.BOTH, expand=True)

            # 태그
            hist_tree.tag_configure('ok', foreground=success_c)
            hist_tree.tag_configure('dup', foreground=warn_c)
            hist_tree.tag_configure('err', foreground=danger_c)

            def _add_history(barcode, result_text, detail, tag='ok'):
                try:
                    now = datetime.now().strftime('%H:%M:%S')
                    hist_tree.insert('', 0, values=(now, barcode, result_text, detail),
                                     tags=(tag,))
                    # 최대 10건
                    children = hist_tree.get_children('')
                    if len(children) > 10:
                        for old in children[10:]:
                            hist_tree.delete(old)
                except Exception as e:
                    logger.debug(f"_add_history: {e}")

            def _do_scan(event=None):
                try:
                    barcode = entry_var.get().strip()
                    if not barcode:
                        return
                    entry_var.set('')

                    # 중복 체크
                    if barcode in state['scanned_set']:
                        state['session_err'] += 1
                        status_lbl.config(text=f"중복 스캔: {barcode}", fg=warn_c)
                        _add_history(barcode, '중복', '이미 스캔됨', 'dup')
                        if hasattr(self, '_on_scan_error'):
                            self._on_scan_error('ERR_DUP', uid=barcode,
                                                 lot_no=state['lot_no'],
                                                 parent=dlg)
                        _update_counters()
                        return

                    # DB 조회
                    row = fetchone(self,
                        """SELECT t.tonbag_uid, t.sub_lt, t.lot_no, t.status
                           FROM inventory_tonbag t
                           WHERE t.tonbag_uid = ? OR t.sub_lt = ?
                           LIMIT 1""",
                        (barcode, barcode))

                    if not row:
                        state['session_err'] += 1
                        status_lbl.config(text=f"미등록 바코드: {barcode}",
                                           fg=danger_c)
                        _add_history(barcode, '미등록', 'DB에 없음', 'err')
                        if hasattr(self, '_on_scan_error'):
                            self._on_scan_error('ERR_UNKNOWN', uid=barcode,
                                                 lot_no=state['lot_no'],
                                                 parent=dlg)
                        _update_counters()
                        return

                    tb_lot = str(row.get('lot_no', ''))
                    tb_status = str(row.get('status', '')).upper()

                    # LOT 검증
                    if state['lot_no'] and tb_lot != state['lot_no']:
                        state['session_err'] += 1
                        status_lbl.config(
                            text=f"LOT 불일치: {barcode} (LOT={tb_lot})",
                            fg=danger_c)
                        _add_history(barcode, 'LOT불일치',
                                     f"기대:{state['lot_no']} 실제:{tb_lot}", 'err')
                        if hasattr(self, '_on_scan_error'):
                            self._on_scan_error('ERR_WRONG_LOT', uid=barcode,
                                                 extra=f"expected={state['lot_no']},actual={tb_lot}",
                                                 lot_no=state['lot_no'],
                                                 parent=dlg)
                        _update_counters()
                        return

                    # 상태 검증
                    if tb_status not in ('PICKED', 'RESERVED', 'AVAILABLE'):
                        state['session_err'] += 1
                        status_lbl.config(
                            text=f"상태 오류: {barcode} ({tb_status})",
                            fg=warn_c)
                        _add_history(barcode, '상태오류', tb_status, 'err')
                        if hasattr(self, '_on_scan_error'):
                            self._on_scan_error('ERR_STATUS', uid=barcode,
                                                 extra=tb_status,
                                                 lot_no=state['lot_no'],
                                                 parent=dlg)
                        _update_counters()
                        return

                    # 성공
                    state['scanned_set'].add(barcode)
                    state['scanned_list'].append(barcode)
                    state['session_ok'] += 1
                    status_lbl.config(text=f"OK: {barcode}", fg=success_c)
                    _add_history(barcode, 'OK', f"LOT={tb_lot}", 'ok')

                    if hasattr(self, 'reset_scan_error_counter'):
                        self.reset_scan_error_counter()

                    # outbound_scan_log
                    try:
                        db_execute(self,
                            "INSERT INTO outbound_scan_log (lot_no, tonbag_uid, status, weight_kg) "
                            "VALUES (?, ?, 'SCANNED', 0)",
                            (tb_lot, barcode))
                    except Exception as e:
                        logger.debug(f"scan_log insert: {e}")

                    _update_counters()

                except Exception as e:
                    logger.error(f"_do_scan 오류: {e}")
                    status_lbl.config(text=f"오류: {e}", fg=danger_c)

            def _update_counters():
                try:
                    ok_lbl.config(text=f"성공: {state['session_ok']}")
                    err_lbl.config(text=f"오류: {state['session_err']}")
                    scanned = state['session_ok']
                    expected = state['expected']
                    progress_bar.config(value=scanned)
                    progress_lbl.config(text=f"{scanned} / {expected}")
                except Exception as e:
                    logger.debug(f"_update_counters: {e}")

            entry.bind('<Return>', _do_scan)

            # 하단 버튼
            btn_f = tk.Frame(dlg, bg=bg)
            btn_f.pack(fill=tk.X, padx=Spacing.MD, pady=Spacing.SM)

            def _finalize():
                try:
                    # 탭 새로고침
                    for fn in ('_refresh_picked', '_refresh_sold',
                               '_refresh_scan_center'):
                        if hasattr(self, fn):
                            try:
                                getattr(self, fn)()
                            except Exception:
                                pass

                    # 게이트 자동 체크
                    gate = getattr(self, '_outbound_gate_refs', None)
                    if gate and 'checks' in gate:
                        scan_check = gate['checks'].get('스캔 완료 확인')
                        if scan_check and state['session_ok'] > 0:
                            scan_check.set(True)

                    # 요약 표시
                    if hasattr(self, '_show_session_summary_popup'):
                        self._show_session_summary_popup(
                            state['lot_no'],
                            state['session_ok'],
                            state['session_err'],
                            tonbag_count=state['expected'],
                            parent=dlg)

                    dlg.destroy()
                except Exception as e:
                    logger.error(f"_finalize 오류: {e}")

            ttk.Button(btn_f, text="세션 종료 및 확정",
                       command=_finalize).pack(side=tk.LEFT, padx=4)
            ttk.Button(btn_f, text="취소",
                       command=dlg.destroy).pack(side=tk.RIGHT, padx=4)

            dlg.bind('<Escape>', lambda e: dlg.destroy())

        except Exception as e:
            logger.error(f"_open_live_scan_session 오류: {e}")
