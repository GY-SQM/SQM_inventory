# -*- coding: utf-8 -*-
"""
SQM v7.3.2 — 스캔 오류 분류/처리 Mixin
========================================
ERR_DUP, ERR_WRONG_LOT, ERR_UNKNOWN, ERR_STATUS, ERR_DB 분류 및 배너 표시.
"""
import logging
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from ..utils.ui_constants import ThemeColors, Spacing, center_dialog
from ..utils.db_helper import execute as db_execute

logger = logging.getLogger(__name__)


class ScanErrorMixin:
    """스캔 오류 분류, 카운터, 배너, 세션 요약."""

    ERR_CONFIG = {
        'ERR_DUP': {
            'icon': '\U0001f501', 'level': 'warn', 'color': '#f59e0b',
            'label': '중복 스캔', 'action': '이미 스캔된 바코드입니다.',
            'auto_clear': True,
        },
        'ERR_WRONG_LOT': {
            'icon': '\u274c', 'level': 'error', 'color': '#ef4444',
            'label': 'LOT 불일치', 'action': '대상 LOT와 다른 바코드입니다.',
            'auto_clear': False,
        },
        'ERR_UNKNOWN': {
            'icon': '\u2753', 'level': 'error', 'color': '#ef4444',
            'label': '미등록 바코드', 'action': 'DB에 존재하지 않는 바코드입니다.',
            'auto_clear': False,
        },
        'ERR_STATUS': {
            'icon': '\u26a0\ufe0f', 'level': 'warn', 'color': '#f59e0b',
            'label': '상태 오류', 'action': '출고 가능 상태가 아닙니다.',
            'auto_clear': False,
        },
        'ERR_DB': {
            'icon': '\U0001f4a5', 'level': 'critical', 'color': '#dc2626',
            'label': 'DB 오류', 'action': '데이터베이스 접근 오류가 발생했습니다.',
            'auto_clear': False,
        },
    }

    def _classify_scan_error(self, uid, expected_lot="", actual_lot="",
                              actual_status="", is_dup=False,
                              db_error=False) -> str:
        """스캔 결과를 오류 유형으로 분류."""
        try:
            if db_error:
                return 'ERR_DB'
            if is_dup:
                return 'ERR_DUP'
            if expected_lot and actual_lot and expected_lot != actual_lot:
                return 'ERR_WRONG_LOT'
            if actual_status and actual_status.upper() not in ('PICKED', 'RESERVED', 'AVAILABLE'):
                return 'ERR_STATUS'
            if not actual_lot:
                return 'ERR_UNKNOWN'
            return ''
        except Exception as e:
            logger.debug(f"_classify_scan_error: {e}")
            return 'ERR_DB'

    def _on_scan_error(self, err_type, uid="", extra="", parent=None,
                        lot_no="") -> None:
        """오류 배너 표시 + 카운터 증가 + 로그 기록."""
        try:
            cfg = self.ERR_CONFIG.get(err_type, self.ERR_CONFIG['ERR_UNKNOWN'])

            # 배너
            self._show_scan_error_banner(parent, err_type, uid, cfg)

            # 카운터
            self._inc_error_counter(err_type, uid, parent)

            # DB 로그
            self._log_scan_error(err_type, uid, extra, lot_no)

        except Exception as e:
            logger.error(f"_on_scan_error 오류: {e}")

    def _show_scan_error_banner(self, parent, err_type, uid, cfg) -> None:
        """오류 배너 임시 표시 (5초 후 자동 제거)."""
        try:
            target = parent or getattr(self, 'root', None)
            if not target:
                return

            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            bg = cfg['color']
            fg = '#ffffff'

            banner = tk.Frame(target, bg=bg, height=36)
            banner.pack(fill=tk.X, padx=0, pady=0, side=tk.TOP)
            banner.pack_propagate(False)

            text = f" {cfg['icon']} {cfg['label']}: {uid}  —  {cfg['action']}"
            tk.Label(banner, text=text, font=('맑은 고딕', 10, 'bold'),
                     fg=fg, bg=bg).pack(side=tk.LEFT, padx=Spacing.SM)

            close_btn = tk.Label(banner, text="  X  ", font=('맑은 고딕', 9, 'bold'),
                                 fg=fg, bg=bg, cursor='hand2')
            close_btn.pack(side=tk.RIGHT, padx=4)
            close_btn.bind('<Button-1>', lambda e: banner.destroy())

            if cfg.get('auto_clear', False):
                target.after(5000, lambda: banner.destroy()
                             if banner.winfo_exists() else None)

        except Exception as e:
            logger.debug(f"_show_scan_error_banner: {e}")

    def _inc_error_counter(self, err_type, uid, parent=None) -> None:
        """연속 오류 카운터. 3회 경고, 5회 차단."""
        try:
            if not hasattr(self, '_scan_error_count'):
                self._scan_error_count = 0
            self._scan_error_count += 1

            if self._scan_error_count >= 5:
                root = parent or getattr(self, 'root', None)
                if root:
                    from tkinter import messagebox
                    messagebox.showerror(
                        "스캔 차단",
                        f"연속 오류 {self._scan_error_count}회 발생.\n"
                        "스캔을 일시 중지합니다. 상태를 확인하세요.",
                        parent=root)
            elif self._scan_error_count >= 3:
                logger.warning(
                    f"연속 스캔 오류 {self._scan_error_count}회 "
                    f"(최근: {err_type}, uid={uid})")
        except Exception as e:
            logger.debug(f"_inc_error_counter: {e}")

    def reset_scan_error_counter(self) -> None:
        """성공 스캔 시 카운터 리셋."""
        try:
            self._scan_error_count = 0
        except Exception as e:
            logger.debug(f"reset_scan_error_counter: {e}")

    def _log_scan_error(self, err_type, uid, extra, lot_no) -> None:
        """audit_log에 스캔 오류 기록."""
        try:
            detail = f"err={err_type}, uid={uid}"
            if extra:
                detail += f", extra={extra}"
            db_execute(self,
                       "INSERT INTO audit_log (action_type, event_type, lot_no, detail) "
                       "VALUES (?, ?, ?, ?)",
                       ('SCAN_ERROR', err_type, lot_no, detail))
        except Exception as e:
            logger.debug(f"_log_scan_error: {e}")

    def _show_session_summary_popup(self, lot_no, session_ok, session_err,
                                     tonbag_count=0, parent=None) -> None:
        """스캔 세션 완료 요약 팝업."""
        try:
            root = parent or getattr(self, 'root', None)
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly'))
            bg = ThemeColors.get('bg_primary', is_dark)
            fg = ThemeColors.get('text_primary', is_dark)
            card_bg = ThemeColors.get('bg_card', is_dark)
            success_c = ThemeColors.get('success', is_dark)
            danger_c = ThemeColors.get('danger', is_dark)

            dlg = tk.Toplevel(root)
            dlg.title("스캔 세션 결과")
            dlg.geometry("380x320")
            dlg.configure(bg=bg)
            dlg.transient(root)
            dlg.grab_set()
            dlg.resizable(False, False)
            center_dialog(dlg, root)

            total = session_ok + session_err
            rate = (session_ok / total * 100) if total > 0 else 0
            status_text = "완료" if session_err == 0 else "일부 오류"
            status_color = success_c if session_err == 0 else danger_c

            tk.Label(dlg, text="스캔 세션 결과",
                     font=('맑은 고딕', 14, 'bold'), fg=fg, bg=bg).pack(
                pady=(Spacing.MD, Spacing.SM))

            tk.Label(dlg, text=status_text,
                     font=('맑은 고딕', 18, 'bold'), fg=status_color,
                     bg=bg).pack(pady=Spacing.XS)

            info_f = tk.Frame(dlg, bg=card_bg, relief='groove', bd=1,
                              padx=16, pady=12)
            info_f.pack(fill=tk.X, padx=Spacing.LG, pady=Spacing.SM)

            rows = [
                ("LOT NO", lot_no),
                ("대상 톤백", f"{tonbag_count}개"),
                ("성공", f"{session_ok}건"),
                ("오류", f"{session_err}건"),
                ("성공률", f"{rate:.1f}%"),
            ]
            for label, value in rows:
                row_f = tk.Frame(info_f, bg=card_bg)
                row_f.pack(fill=tk.X, pady=2)
                tk.Label(row_f, text=f"{label}:", font=('맑은 고딕', 10),
                         fg=ThemeColors.get('text_secondary', is_dark),
                         bg=card_bg, width=10, anchor='w').pack(side=tk.LEFT)
                tk.Label(row_f, text=value, font=('맑은 고딕', 11, 'bold'),
                         fg=fg, bg=card_bg).pack(side=tk.LEFT, padx=8)

            ttk.Button(dlg, text="닫기", command=dlg.destroy).pack(
                pady=Spacing.MD)

            dlg.bind('<Escape>', lambda e: dlg.destroy())

        except Exception as e:
            logger.error(f"_show_session_summary_popup 오류: {e}")
