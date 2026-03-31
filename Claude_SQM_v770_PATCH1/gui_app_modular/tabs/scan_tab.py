# -*- coding: utf-8 -*-
"""
scan_tab.py — SQM 스캔 탭 (v7.4.0)

바코드/QR 스캔 입력 + 빠른처리 4버튼 + 스캔 이력 표시.

빠른처리 버튼:
  📋 배정 등록   → AVAILABLE  → RESERVED  (allocation 등록)
  🚛 화물 결정   → RESERVED   → PICKED    (picking 확정)
  ✅ 출고확정     → PICKED     → OUTBOUND  (출고 완료)
  🔄 반품등록     → OUTBOUND   → RETURN    (반품 입고 대기)
"""

import logging
import datetime
from engine_modules.constants import (
    STATUS_AVAILABLE, STATUS_RESERVED, STATUS_PICKED,
)  # v7.5.0: 하드코딩 상수 → 중앙화
import tkinter as tk

logger = logging.getLogger(__name__)


class ScanTabMixin:
    """스캔 탭 UI + 이벤트 핸들러."""

    # ──────────────────────────────────────────────
    # 탭 셋업
    # ──────────────────────────────────────────────
    def _setup_scan_tab(self) -> None:
        """스캔 탭 초기화."""
        try:
            import ttkbootstrap as ttk
        except ImportError:
            import tkinter.ttk as ttk

        try:
            from ..utils.constants import BOTH, LEFT, RIGHT, X, Y, YES, VERTICAL
        except Exception:
            BOTH = 'both'; LEFT = 'left'; RIGHT = 'right'
            X = 'x'; Y = 'y'; YES = True; VERTICAL = 'vertical'

        try:
            from ..utils.ui_constants import ThemeColors, Spacing
        except Exception:
            class ThemeColors:
                @staticmethod
                def get(k, d='#ffffff'): return d
                @staticmethod
                def is_dark_theme(t): return 'dark' in str(t).lower()
            class Spacing:
                XS = 4; SM = 8; MD = 12

        frame = self.tab_scan
        # ── 상단: 스캔 입력 영역 ────────────────────
        scan_input_frame = ttk.LabelFrame(frame, text="📷 바코드 / QR 스캔 입력")
        scan_input_frame.pack(fill=X, padx=Spacing.SM, pady=Spacing.SM)

        inner = ttk.Frame(scan_input_frame)
        inner.pack(fill=X, padx=Spacing.SM, pady=Spacing.SM)

        ttk.Label(inner, text="톤백 번호:").pack(side=LEFT, padx=(0, Spacing.XS))
        self._scan_entry_var = tk.StringVar()
        self._scan_entry = ttk.Entry(inner, textvariable=self._scan_entry_var, width=32,
                                     font=('맑은 고딕', 13))
        self._scan_entry.pack(side=LEFT, padx=Spacing.XS)
        self._scan_entry.bind('<Return>', self._on_scan_enter)

        btn_scan_exec = ttk.Button(inner, text="🔍 조회", command=self._on_scan_lookup,
                                   bootstyle='primary')
        btn_scan_exec.pack(side=LEFT, padx=Spacing.XS)

        btn_scan_clear = ttk.Button(inner, text="🗑 지우기", command=self._on_scan_clear,
                                    bootstyle='secondary-outline')
        btn_scan_clear.pack(side=LEFT, padx=Spacing.XS)

        # 조회 결과 표시 레이블
        self._scan_result_var = tk.StringVar(value="톤백 번호를 입력하거나 스캔하세요.")
        lbl_result = ttk.Label(scan_input_frame, textvariable=self._scan_result_var,
                               font=('맑은 고딕', 11))
        lbl_result.pack(padx=Spacing.SM, pady=(0, Spacing.SM))

        # ── 중단: 빠른처리 4버튼 ────────────────────
        quick_frame = ttk.LabelFrame(frame, text="⚡ 빠른처리")
        quick_frame.pack(fill=X, padx=Spacing.SM, pady=(0, Spacing.SM))

        btn_bar = ttk.Frame(quick_frame)
        btn_bar.pack(fill=X, padx=Spacing.SM, pady=Spacing.SM)

        QUICK_BTNS = [
            ("📋 배정 등록",  '#3b82f6', self._on_quick_allocate),
            ("🚛 화물 결정",  '#f97316', self._on_quick_pick),
            ("✅ 출고확정",   '#22c55e', self._on_quick_outbound),
            ("🔄 반품등록",   '#14b8a6', self._on_quick_return),
        ]

        for label, color, cmd in QUICK_BTNS:
            btn = tk.Button(
                btn_bar, text=label, command=cmd,
                bg=color, fg='#ffffff',
                font=('맑은 고딕', 12, 'bold'),
                relief='flat', padx=18, pady=10, cursor='hand2',
                activebackground=color, activeforeground='#ffffff'
            )
            btn.pack(side=LEFT, padx=Spacing.SM, pady=Spacing.XS)

        # ── 하단: 스캔 이력 ─────────────────────────
        hist_frame = ttk.LabelFrame(frame, text="📋 스캔 이력")
        hist_frame.pack(fill=BOTH, expand=YES, padx=Spacing.SM, pady=(0, Spacing.SM))

        cols = ('time', 'tonbag_uid', 'lot_no', 'action', 'result')
        self.tree_scan_hist = ttk.Treeview(
            hist_frame, columns=cols, show='headings', height=15
        )
        col_cfg = [
            ('time',       '시간',       120, 'center'),
            ('tonbag_uid', '톤백번호',   160, 'w'),
            ('lot_no',     'LOT번호',    140, 'w'),
            ('action',     '처리',        90, 'center'),
            ('result',     '결과',       260, 'w'),
        ]
        for cid, label, width, anchor in col_cfg:
            self.tree_scan_hist.heading(cid, text=label)
            self.tree_scan_hist.column(cid, width=width, anchor=anchor, stretch=True)

        scr = tk.Scrollbar(hist_frame, orient=VERTICAL, command=self.tree_scan_hist.yview)
        self.tree_scan_hist.configure(yscrollcommand=scr.set)
        self.tree_scan_hist.pack(side=LEFT, fill=BOTH, expand=YES)
        scr.pack(side=RIGHT, fill=Y)

        # 이력 태그
        self.tree_scan_hist.tag_configure('ok',   foreground='#22c55e')
        self.tree_scan_hist.tag_configure('fail', foreground='#ef4444')
        self.tree_scan_hist.tag_configure('warn', foreground='#f97316')

        # 포커스
        self._scan_entry.focus_set()

    # ──────────────────────────────────────────────
    # 내부 헬퍼
    # ──────────────────────────────────────────────
    def _scan_get_uid(self) -> str:
        """입력창에서 톤백 UID 반환."""
        return (self._scan_entry_var.get() or '').strip()

    def _scan_add_hist(self, uid: str, lot_no: str, action: str, result: str, ok: bool) -> None:
        """이력 트리뷰에 한 줄 추가."""
        now = datetime.datetime.now().strftime('%H:%M:%S')
        tag = 'ok' if ok else 'fail'
        tree = getattr(self, 'tree_scan_hist', None)
        if tree:
            tree.insert('', 0, values=(now, uid, lot_no, action, result), tags=(tag,))

    def _scan_lookup_tonbag(self, uid: str):
        """DB에서 톤백 조회 → dict or None."""
        try:
            row = self.db.fetchone(
                "SELECT lot_no, sub_lt, status, weight, location, is_sample "
                "FROM inventory_tonbag WHERE tonbag_uid=?", (uid,)
            )
            if row:
                if isinstance(row, dict):
                    return row
                return dict(zip(('lot_no','sub_lt','status','weight','location','is_sample'), row))
        except Exception as e:
            logger.error(f"스캔 조회 오류: {e}")
        return None

    # ──────────────────────────────────────────────
    # 이벤트 핸들러
    # ──────────────────────────────────────────────
    def _on_scan_enter(self, event=None) -> None:
        self._on_scan_lookup()

    def _on_scan_clear(self) -> None:
        self._scan_entry_var.set('')
        self._scan_result_var.set("톤백 번호를 입력하거나 스캔하세요.")
        if hasattr(self, '_scan_entry'):
            self._scan_entry.focus_set()

    def _on_scan_lookup(self) -> None:
        """톤백 UID 조회 후 결과 표시."""
        uid = self._scan_get_uid()
        if not uid:
            self._scan_result_var.set("⚠️ 톤백 번호를 입력하세요.")
            return
        tb = self._scan_lookup_tonbag(uid)
        if not tb:
            self._scan_result_var.set(f"❌ 없음: {uid}")
            self._scan_add_hist(uid, '-', '조회', '톤백 없음', False)
            return
        lot   = tb.get('lot_no', '-')
        stat  = tb.get('status', '-')
        wt    = tb.get('weight', 0)
        loc   = tb.get('location') or '-'
        samp  = '(샘플)' if tb.get('is_sample') or tb.get('sub_lt') == 0 else ''
        self._scan_result_var.set(
            f"✅ LOT: {lot}  상태: {stat}  무게: {wt}kg  위치: {loc}  {samp}"
        )

    def _on_quick_allocate(self) -> None:
        """📋 배정 등록: AVAILABLE → RESERVED."""
        import tkinter.messagebox as msgbox
        uid = self._scan_get_uid()
        if not uid:
            msgbox.showwarning("입력 없음", "톤백 번호를 스캔하거나 입력하세요.", parent=self)
            return
        tb = self._scan_lookup_tonbag(uid)
        if not tb:
            self._scan_add_hist(uid, '-', '배정등록', '톤백 없음', False)
            return
        if tb.get('status') != STATUS_AVAILABLE:
            msg = f"AVAILABLE 상태가 아님 (현재: {tb.get('status')})"
            self._scan_add_hist(uid, tb.get('lot_no','-'), '배정등록', msg, False)
            msgbox.showwarning("상태 오류", msg, parent=self)
            return
        # 배정 등록은 Allocation 다이얼로그로 위임
        msgbox.showinfo("배정 등록",
                        f"LOT {tb.get('lot_no')} 배정은\n메뉴 → 배정 업로드 / 판매배정 탭을 이용하세요.",
                        parent=self)
        self._scan_add_hist(uid, tb.get('lot_no','-'), '배정등록', '다이얼로그로 이동', True)

    def _on_quick_pick(self) -> None:
        """🚛 화물 결정: RESERVED → PICKED."""
        import tkinter.messagebox as msgbox
        uid = self._scan_get_uid()
        if not uid:
            msgbox.showwarning("입력 없음", "톤백 번호를 스캔하거나 입력하세요.", parent=self)
            return
        tb = self._scan_lookup_tonbag(uid)
        if not tb:
            self._scan_add_hist(uid, '-', '화물결정', '톤백 없음', False)
            return
        if tb.get('is_sample') or tb.get('sub_lt') == 0:
            msg = "샘플 톤백은 화물 결정 불가"
            self._scan_add_hist(uid, tb.get('lot_no','-'), '화물결정', msg, False)
            msgbox.showwarning("샘플 차단", msg, parent=self)
            return
        if tb.get('status') != STATUS_RESERVED:
            msg = f"RESERVED 상태가 아님 (현재: {tb.get('status')})"
            self._scan_add_hist(uid, tb.get('lot_no','-'), '화물결정', msg, False)
            msgbox.showwarning("상태 오류", msg, parent=self)
            return
        ok = msgbox.askyesno("화물 결정", f"톤백 {uid}\nRESERVED → PICKED 처리합니까?", parent=self)
        if not ok:
            return
        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.execute(
                "UPDATE inventory_tonbag SET status='PICKED', updated_at=? WHERE tonbag_uid=?",
                (now, uid)
            )
            self._scan_add_hist(uid, tb.get('lot_no','-'), '화물결정', 'PICKED 전환 완료', True)
            self._scan_result_var.set(f"✅ {uid} → PICKED 완료")
        except Exception as e:
            self._scan_add_hist(uid, tb.get('lot_no','-'), '화물결정', str(e), False)

    def _on_quick_outbound(self) -> None:
        """✅ 출고확정: PICKED → OUTBOUND."""
        import tkinter.messagebox as msgbox
        uid = self._scan_get_uid()
        if not uid:
            msgbox.showwarning("입력 없음", "톤백 번호를 스캔하거나 입력하세요.", parent=self)
            return
        tb = self._scan_lookup_tonbag(uid)
        if not tb:
            self._scan_add_hist(uid, '-', '출고확정', '톤백 없음', False)
            return
        if tb.get('is_sample') or tb.get('sub_lt') == 0:
            msg = "샘플 톤백은 출고 불가"
            self._scan_add_hist(uid, tb.get('lot_no','-'), '출고확정', msg, False)
            msgbox.showwarning("샘플 차단", msg, parent=self)
            return
        if tb.get('status') != STATUS_PICKED:
            msg = f"PICKED 상태가 아님 (현재: {tb.get('status')})"
            self._scan_add_hist(uid, tb.get('lot_no','-'), '출고확정', msg, False)
            msgbox.showwarning("상태 오류", msg, parent=self)
            return
        ok = msgbox.askyesno("출고 확정", f"톤백 {uid}\nPICKED → OUTBOUND 처리합니까?", parent=self)
        if not ok:
            return
        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.execute(
                "UPDATE inventory_tonbag SET status='OUTBOUND', updated_at=? WHERE tonbag_uid=?",
                (now, uid)
            )
            self._scan_add_hist(uid, tb.get('lot_no','-'), '출고확정', 'OUTBOUND 전환 완료', True)
            self._scan_result_var.set(f"✅ {uid} → OUTBOUND 완료")
        except Exception as e:
            self._scan_add_hist(uid, tb.get('lot_no','-'), '출고확정', str(e), False)

    def _on_quick_return(self) -> None:
        """🔄 반품등록: OUTBOUND → RETURN."""
        import tkinter.messagebox as msgbox
        uid = self._scan_get_uid()
        if not uid:
            msgbox.showwarning("입력 없음", "톤백 번호를 스캔하거나 입력하세요.", parent=self)
            return
        tb = self._scan_lookup_tonbag(uid)
        if not tb:
            self._scan_add_hist(uid, '-', '반품등록', '톤백 없음', False)
            return
        if tb.get('is_sample') or tb.get('sub_lt') == 0:
            msg = "샘플 톤백은 반품 불가"
            self._scan_add_hist(uid, tb.get('lot_no','-'), '반품등록', msg, False)
            msgbox.showwarning("샘플 차단", msg, parent=self)
            return
        if tb.get('status') != 'OUTBOUND':
            msg = f"OUTBOUND 상태가 아님 (현재: {tb.get('status')})"
            self._scan_add_hist(uid, tb.get('lot_no','-'), '반품등록', msg, False)
            msgbox.showwarning("상태 오류", msg, parent=self)
            return
        ok = msgbox.askyesno("반품 등록", f"톤백 {uid}\nOUTBOUND → RETURN 처리합니까?", parent=self)
        if not ok:
            return
        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.execute(
                "UPDATE inventory_tonbag SET status='RETURN', updated_at=? WHERE tonbag_uid=?",
                (now, uid)
            )
            self._scan_add_hist(uid, tb.get('lot_no','-'), '반품등록', 'RETURN 전환 완료', True)
            self._scan_result_var.set(f"✅ {uid} → RETURN 완료")
        except Exception as e:
            self._scan_add_hist(uid, tb.get('lot_no','-'), '반품등록', str(e), False)
