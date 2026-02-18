# -*- coding: utf-8 -*-
"""
SQM v5.9.5 — Allocation 출고 예약 다이얼로그
=============================================

엑셀 업로드 → 파싱 미리보기 → 예약(RESERVED) 실행 → 현황 조회
"""
import logging
import time
import tkinter as tk
from tkinter import ttk, filedialog, BOTH, X, Y, LEFT, RIGHT, END, VERTICAL

from ..utils.ui_constants import ThemeColors, DialogSize, center_dialog, CustomMessageBox

logger = logging.getLogger(__name__)

ALLOC_PREVIEW_COLUMNS = [
    ("lot_no",        "LOT NO",        110, "center"),
    ("sap_no",        "SAP NO",        100, "center"),
    ("product",       "PRODUCT",       140, "center"),
    ("qty_mt",        "QTY (MT)",       80, "center"),
    ("sold_to",       "CUSTOMER",      130, "center"),
    ("sale_ref",      "SALE REF",      120, "center"),
    ("outbound_date", "OUTBOUND DATE", 100, "center"),
    ("warehouse",     "WH",             60, "center"),
    ("status",        "STATUS",         80, "center"),
]


class AllocationDialog:
    """Allocation 엑셀 → 미리보기 → 예약/실행/취소"""

    def __init__(self, app, engine):
        self.app = app
        self.engine = engine
        self.root = getattr(app, 'root', None)
        self.dialog = None
        self.parsed_rows = []
        self.source_file = ""

    def show(self):
        self.dialog = tk.Toplevel(self.root)
        self.dialog.title("📋 Allocation 출고 예약")
        self.dialog.geometry("1100x650")
        center_dialog(self.dialog, 1100, 650)
        self.dialog.transient(self.root)
        self.dialog.grab_set()
        self._create_widgets()

    def _create_widgets(self):
        top = ttk.Frame(self.dialog, padding=8)
        top.pack(fill=X)

        ttk.Label(top, text="Allocation Excel 파일:").pack(side=LEFT, padx=(0, 5))
        self._file_var = tk.StringVar()
        ttk.Entry(top, textvariable=self._file_var, width=60, state='readonly').pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(top, text="📂 파일 선택", command=self._select_file).pack(side=LEFT, padx=(0, 5))
        ttk.Button(top, text="🔍 파싱", command=self._parse_file).pack(side=LEFT)

        tree_frame = ttk.Frame(self.dialog, padding=8)
        tree_frame.pack(fill=BOTH, expand=True)

        cols = [c[0] for c in ALLOC_PREVIEW_COLUMNS]
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=18)
        for col_id, header, width, anchor in ALLOC_PREVIEW_COLUMNS:
            self.tree.heading(col_id, text=header)
            self.tree.column(col_id, width=width, anchor=anchor, minwidth=40)

        vsb = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        self._summary_var = tk.StringVar(value="파일을 선택하세요")
        ttk.Label(self.dialog, textvariable=self._summary_var, padding=5).pack(fill=X)

        btn_frame = ttk.Frame(self.dialog, padding=8)
        btn_frame.pack(fill=X)

        self.btn_reserve = ttk.Button(btn_frame, text="✅ 예약 실행 (RESERVED)", command=self._on_reserve, state='disabled')
        self.btn_reserve.pack(side=LEFT, padx=5)

        self.btn_status = ttk.Button(btn_frame, text="📊 예약 현황", command=self._show_reservation_status)
        self.btn_status.pack(side=LEFT, padx=5)

        self.btn_cancel_res = ttk.Button(btn_frame, text="❌ 예약 취소", command=self._on_cancel_reservation, state='disabled')
        self.btn_cancel_res.pack(side=LEFT, padx=5)

        self.btn_execute = ttk.Button(btn_frame, text="📦 출고 실행 (PICKED)", command=self._on_execute, state='disabled')
        self.btn_execute.pack(side=LEFT, padx=5)

        self.btn_confirm = ttk.Button(btn_frame, text="🔒 출고 확정 (SOLD)", command=self._on_confirm, state='disabled')
        self.btn_confirm.pack(side=LEFT, padx=5)

        ttk.Button(btn_frame, text="닫기", command=self.dialog.destroy).pack(side=RIGHT, padx=5)

    def _select_file(self):
        path = filedialog.askopenfilename(
            parent=self.dialog, title="Allocation Excel 선택",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if path:
            self._file_var.set(path)
            self.source_file = path

    def _parse_file(self):
        path = self._file_var.get()
        if not path:
            CustomMessageBox.showwarning(self.dialog, "경고", "파일을 먼저 선택하세요.")
            return

        try:
            from parsers.allocation_parser import AllocationParser
            t0 = time.perf_counter()
            parser = AllocationParser()
            result = parser.parse(path)
            elapsed_sec = time.perf_counter() - t0

            self.parsed_rows = result.rows if result else []
            self.tree.delete(*self.tree.get_children())

            for i, row in enumerate(self.parsed_rows):
                vals = (
                    getattr(row, 'lot_no', ''),
                    getattr(row, 'sap_no', ''),
                    getattr(row, 'product', ''),
                    f"{getattr(row, 'qty_mt', 0):.2f}",
                    getattr(row, 'sold_to', ''),
                    getattr(row, 'sale_ref', ''),
                    str(getattr(row, 'outbound_date', '') or ''),
                    getattr(row, 'warehouse', ''),
                    'PENDING',
                )
                self.tree.insert('', END, iid=str(i), values=vals)

            header = result.header if result else None
            customer = getattr(header, 'customer', '?') if header else '?'
            total = getattr(header, 'total_qty', 0) if header else 0
            fname = path.split('/')[-1].split(chr(92))[-1]
            self._summary_var.set(
                f"고객: {customer} | 총 {len(self.parsed_rows)}행 | "
                f"총량: {total:.1f} MT | 파싱: {elapsed_sec:.2f}초 | {fname}"
            )

            if self.parsed_rows:
                self.btn_reserve.config(state='normal')
            else:
                self.btn_reserve.config(state='disabled')

        except (ValueError, TypeError, AttributeError, ImportError) as e:
            logger.error(f"Allocation 파싱 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.dialog, "파싱 오류", f"Allocation 파일 파싱 실패:\n{e}")

    def _on_reserve(self):
        if not self.parsed_rows:
            return

        ok = CustomMessageBox.askyesno(
            self.dialog, "예약 실행",
            f"{len(self.parsed_rows)}개 행의 톤백을 RESERVED 상태로 예약합니다.\n계속하시겠습니까?"
        )
        if not ok:
            return

        try:
            result = self.engine.reserve_from_allocation(
                self.parsed_rows, source_file=self.source_file
            )
            if result.get('success'):
                reserved = result.get('reserved', 0)
                CustomMessageBox.showinfo(
                    self.dialog, "예약 완료",
                    f"✅ {reserved}개 톤백 예약 완료 (RESERVED)"
                )
                errors = result.get('errors', [])
                if errors:
                    CustomMessageBox.showwarning(
                        self.dialog, "일부 경고",
                        f"경고 {len(errors)}건:\n" + "\n".join(errors[:10])
                    )
                self.btn_cancel_res.config(state='normal')
                self.btn_execute.config(state='normal')
                self._refresh_after_action()
            else:
                errors = result.get('errors', [])
                CustomMessageBox.showerror(
                    self.dialog, "예약 실패",
                    f"예약 실패:\n" + "\n".join(errors[:10])
                )
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"예약 실행 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.dialog, "오류", f"예약 실행 중 오류:\n{e}")

    def _on_execute(self):
        """RESERVED → PICKED 전환"""
        ok = CustomMessageBox.askyesno(
            self.dialog, "출고 실행",
            "RESERVED 상태의 톤백을 PICKED로 전환합니다.\n계속하시겠습니까?"
        )
        if not ok:
            return
        try:
            result = self.engine.execute_reserved()
            if result.get('success'):
                CustomMessageBox.showinfo(
                    self.dialog, "출고 실행 완료",
                    f"✅ {result.get('executed', 0)}개 톤백 PICKED 전환 완료"
                )
                self.btn_confirm.config(state='normal')
                self._refresh_after_action()
            else:
                CustomMessageBox.showerror(
                    self.dialog, "출고 실행 실패",
                    "\n".join(result.get('errors', ['알 수 없는 오류']))
                )
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"출고 실행 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.dialog, "오류", str(e))

    def _on_confirm(self):
        """PICKED → SOLD 확정"""
        ok = CustomMessageBox.askyesno(
            self.dialog, "출고 확정",
            "PICKED 상태의 톤백을 SOLD로 확정합니다.\n이 작업은 되돌릴 수 없습니다.\n계속하시겠습니까?"
        )
        if not ok:
            return
        try:
            result = self.engine.confirm_outbound()
            if result.get('success'):
                CustomMessageBox.showinfo(
                    self.dialog, "출고 확정 완료",
                    f"✅ {result.get('confirmed', 0)}개 톤백 SOLD 확정"
                )
                self._refresh_after_action()
            else:
                CustomMessageBox.showerror(
                    self.dialog, "확정 실패",
                    "\n".join(result.get('errors', ['알 수 없는 오류']))
                )
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"출고 확정 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.dialog, "오류", str(e))

    def _on_cancel_reservation(self):
        """예약 취소 (RESERVED → AVAILABLE)"""
        ok = CustomMessageBox.askyesno(
            self.dialog, "예약 취소",
            "RESERVED 상태의 톤백을 모두 AVAILABLE로 되돌립니다.\n계속하시겠습니까?"
        )
        if not ok:
            return
        try:
            result = self.engine.cancel_reservation()
            if result.get('success'):
                CustomMessageBox.showinfo(
                    self.dialog, "예약 취소 완료",
                    f"✅ {result.get('cancelled', 0)}개 톤백 예약 취소됨"
                )
                self._refresh_after_action()
            else:
                CustomMessageBox.showerror(
                    self.dialog, "취소 실패",
                    "\n".join(result.get('errors', ['알 수 없는 오류']))
                )
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"예약 취소 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.dialog, "오류", str(e))

    def _show_reservation_status(self):
        """allocation_plan 테이블에서 현재 예약 현황 표시"""
        try:
            rows = self.engine.db.fetchall(
                """SELECT ap.lot_no, ap.customer, ap.sale_ref, ap.qty_mt,
                          ap.outbound_date, ap.status, ap.source_file,
                          ap.created_at, COUNT(ap.tonbag_id) as tb_count
                   FROM allocation_plan ap
                   WHERE ap.status != 'CANCELLED'
                   GROUP BY ap.lot_no, ap.customer, ap.sale_ref, ap.status
                   ORDER BY ap.created_at DESC"""
            )
            if not rows:
                CustomMessageBox.showinfo(self.dialog, "예약 현황", "현재 예약된 항목이 없습니다.")
                return

            status_win = tk.Toplevel(self.dialog)
            status_win.title("📊 Allocation 예약 현황")
            status_win.geometry("900x400")
            center_dialog(status_win, 900, 400)
            status_win.transient(self.dialog)

            cols = ('lot_no', 'customer', 'sale_ref', 'qty_mt', 'outbound_date', 'status', 'tb_count', 'created_at')
            hdrs = ('LOT NO', 'CUSTOMER', 'SALE REF', 'QTY(MT)', 'DATE', 'STATUS', 'TONBAGS', 'CREATED')
            st = ttk.Treeview(status_win, columns=cols, show='headings', height=15)
            for c, h in zip(cols, hdrs):
                st.heading(c, text=h)
                st.column(c, width=100, anchor='center')
            st.pack(fill=BOTH, expand=True, padx=5, pady=5)

            for r in rows:
                st.insert('', END, values=(
                    r.get('lot_no', ''), r.get('customer', ''),
                    r.get('sale_ref', ''), f"{r.get('qty_mt', 0):.2f}",
                    r.get('outbound_date', ''), r.get('status', ''),
                    r.get('tb_count', 0), r.get('created_at', '')
                ))

        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"예약 현황 조회 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.dialog, "오류", str(e))

    def _refresh_after_action(self):
        """예약/출고/취소 후 앱 재고 새로고침"""
        try:
            if hasattr(self.app, '_refresh_inventory'):
                self.app._refresh_inventory()
            if hasattr(self.app, '_refresh_tonbag'):
                self.app._refresh_tonbag()
        except (RuntimeError, ValueError) as e:
            logger.debug(f"새로고침 실패: {e}")
