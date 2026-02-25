# -*- coding: utf-8 -*-
"""
SQM v5.9.5 — Allocation 출고 예약 다이얼로그
=============================================

엑셀 업로드 → 파싱 미리보기 → 예약(RESERVED) 실행 → 현황 조회
"""
import logging
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, BOTH, X, Y, LEFT, RIGHT, END, VERTICAL

from ..utils.ui_constants import (
    ThemeColors, DialogSize, center_dialog, CustomMessageBox, apply_modal_window_options,
    setup_dialog_geometry_persistence,
)
try:
    from ..utils.gui_bootstrap import ScrolledFrame as _ScrolledFrame
except ImportError:
    _ScrolledFrame = None

logger = logging.getLogger(__name__)

# 5 MT = 5000 kg = 500kg 톤백 10개 → qty_mt * 2. 이 미만(10 kg 미만)은 샘플 행으로 1건당 1개 샘플.
SAMPLE_MT_THRESHOLD = 0.01  # 10 kg 이하는 샘플 행


def _allocation_tonbag_sample_counts(rows: list) -> tuple:
    """Allocation 행에서 500kg 톤백 개수와 샘플(1kg) 개수 계산. (tonbag_500, sample_count)"""
    tonbag_500 = 0
    sample_count = 0
    for r in rows:
        qty = 0.0
        if hasattr(r, 'get'):
            qty = float(r.get('qty_mt') or 0)
        else:
            qty = float(getattr(r, 'qty_mt', 0) or 0)
        if qty >= SAMPLE_MT_THRESHOLD:
            tonbag_500 += int(round(qty * 1000 / 500))  # MT → 500kg 단위
        else:
            sample_count += 1
    return tonbag_500, sample_count


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

    def show(self, initial_file: str = None):
        """다이얼로그 표시. initial_file이 있으면 해당 파일 로드 후 파싱"""
        self.dialog = tk.Toplevel(self.root)
        self.dialog.title("📋 판매 배정 출고 예약")
        setup_dialog_geometry_persistence(self.dialog, "allocation_dialog", self.root, "large")
        self.dialog.transient(self.root)
        self.dialog.grab_set()
        _is_dark = ThemeColors.is_dark_theme(getattr(self.app, 'current_theme', 'flatly'))
        _bg = ThemeColors.get('bg_card', _is_dark)
        self.dialog.configure(bg=_bg)
        self._create_widgets()
        self.dialog.update_idletasks()
        if initial_file:
            self._file_var.set(initial_file)
            self.source_file = initial_file
            self.dialog.after(100, self._parse_file)

    def show_with_data(self, rows: list):
        """붙여넣기 등으로 받은 데이터(dict 리스트)로 다이얼로그 표시. 파일 없이 미리보기 → 예약."""
        self.parsed_rows = rows
        self.source_file = "(붙여넣기)"
        self.dialog = tk.Toplevel(self.root)
        self.dialog.title("📋 판매 배정 출고 예약")
        setup_dialog_geometry_persistence(self.dialog, "allocation_dialog", self.root, "large")
        self.dialog.transient(self.root)
        self.dialog.grab_set()
        _is_dark = ThemeColors.is_dark_theme(getattr(self.app, 'current_theme', 'flatly'))
        _bg = ThemeColors.get('bg_card', _is_dark)
        self.dialog.configure(bg=_bg)
        self._create_widgets()
        self.dialog.update_idletasks()
        self._file_var.set("(붙여넣기 데이터)")
        self._fill_tree_from_parsed_rows()
        total_mt = sum(float(r.get('qty_mt') or 0) for r in rows)
        tb500, samp = _allocation_tonbag_sample_counts(rows)
        self._summary_var.set(
            f"고객: (붙여넣기) | 총 {len(rows)}행 | 총량: {total_mt:.4f} MT | 500kg {tb500}개, 샘플 {samp}개"
        )
        if self.parsed_rows:
            self.btn_reserve.config(state='normal')

    def _create_widgets(self):
        top = ttk.Frame(self.dialog, padding=8)
        top.pack(fill=X)

        ttk.Label(top, text="판매 배정 Excel 파일:").pack(side=LEFT, padx=(0, 5))
        self._file_var = tk.StringVar()
        ttk.Entry(top, textvariable=self._file_var, width=60, state='readonly').pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(top, text="📂 파일 선택", command=self._select_file).pack(side=LEFT, padx=(0, 5))

        # 데이터가 많을 때 창 전체를 스크롤할 수 있도록 본문을 ScrolledFrame으로 감쌈
        if _ScrolledFrame is not None:
            body_container = _ScrolledFrame(self.dialog, autohide=True)
            body_container.pack(fill=BOTH, expand=True)
        else:
            body_container = ttk.Frame(self.dialog)
            body_container.pack(fill=BOTH, expand=True)

        tree_frame = ttk.Frame(body_container, padding=8)
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
        try:
            from ..utils.tree_enhancements import TreeviewTotalFooter
            self._alloc_total_footer = TreeviewTotalFooter(
                tree_frame, self.tree, ['qty_mt'],
                column_display_names={'qty_mt': 'QTY (MT)'},
                column_formats={'qty_mt': ',.4f'},
            )
            self._alloc_total_footer.pack(fill=tk.X, pady=(2, 0))
        except (ImportError, Exception):
            self._alloc_total_footer = None

        self._summary_var = tk.StringVar(value="파일을 선택하세요")
        ttk.Label(body_container, textvariable=self._summary_var, padding=5).pack(fill=X)

        btn_frame = ttk.Frame(body_container, padding=8)
        btn_frame.pack(fill=X)

        self.btn_reserve = ttk.Button(btn_frame, text="✅ 예약 실행 (RESERVED)", command=self._on_reserve, state='disabled')
        self.btn_reserve.pack(side=LEFT, padx=5)

        self.btn_status = ttk.Button(btn_frame, text="📊 예약 현황", command=self._show_reservation_status)
        self.btn_status.pack(side=LEFT, padx=5)

        self.btn_cancel_res = ttk.Button(btn_frame, text="❌ 예약 취소", command=self._on_cancel_reservation, state='disabled')
        self.btn_cancel_res.pack(side=LEFT, padx=5)

        self.btn_reset_lot = ttk.Button(
            btn_frame, text="🧹 LOT 예약 초기화", command=self._on_reset_reservation_for_lots, state='disabled'
        )
        self.btn_reset_lot.pack(side=LEFT, padx=5)

        self.btn_execute = ttk.Button(btn_frame, text="📦 출고 실행 (PICKED)", command=self._on_execute, state='disabled')
        self.btn_execute.pack(side=LEFT, padx=5)

        self.btn_confirm = ttk.Button(btn_frame, text="🔒 출고 확정 (SOLD)", command=self._on_confirm, state='disabled')
        self.btn_confirm.pack(side=LEFT, padx=5)

        ttk.Button(btn_frame, text="닫기", command=self.dialog.destroy).pack(side=RIGHT, padx=5)

    def _select_file(self):
        path = filedialog.askopenfilename(
            parent=self.dialog, title="판매 배정 Excel 선택",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if path:
            self._file_var.set(path)
            self.source_file = path
            self._parse_file()  # 파일 선택 시 자동 파싱

    def _parse_file(self):
        """Allocation Excel 파싱 — 백그라운드 스레드에서 실행하여 UI 블로킹 방지."""
        path = self._file_var.get()
        if not path:
            CustomMessageBox.showwarning(self.dialog, "경고", "파일을 먼저 선택하세요.")
            return

        self._summary_var.set("⏳ 파일 파싱 중... (잠시 기다려주세요)")
        self.btn_reserve.config(state='disabled')
        self.tree.delete(*self.tree.get_children())

        def _worker():
            result_data = {'result': None, 'elapsed': 0.0, 'error': None}
            try:
                from parsers.allocation_parser import AllocationParser
                t0 = time.perf_counter()
                parser = AllocationParser()
                result_data['result'] = parser.parse(path)
                result_data['elapsed'] = time.perf_counter() - t0
            except (ValueError, TypeError, AttributeError, ImportError) as e:
                result_data['error'] = e
                logger.error(f"Allocation 파싱 오류: {e}", exc_info=True)
            try:
                self.dialog.after(0, lambda: self._apply_parse_result(path, result_data))
            except (tk.TclError, RuntimeError):
                logger.debug("다이얼로그 종료로 apply 스킵")

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_parse_result(self, path: str, data: dict):
        """파싱 결과를 메인 스레드에서 UI에 반영."""
        try:
            if not self.dialog.winfo_exists():
                return
        except (tk.TclError, RuntimeError):
            return
        if data.get('error'):
            self._summary_var.set("파일을 선택하세요")
            CustomMessageBox.showerror(
                self.dialog, "파싱 오류",
                f"Allocation 파일 파싱 실패:\n{data['error']}"
            )
            return

        result = data.get('result')
        elapsed_sec = data.get('elapsed', 0)

        self.parsed_rows = result.rows if result else []
        self.tree.delete(*self.tree.get_children())

        for i, row in enumerate(self.parsed_rows):
            vals = (
                getattr(row, 'lot_no', ''),
                getattr(row, 'sap_no', ''),
                getattr(row, 'product', ''),
                f"{getattr(row, 'qty_mt', 0):.4f}",
                getattr(row, 'sold_to', ''),
                getattr(row, 'sale_ref', ''),
                str(getattr(row, 'outbound_date', '') or ''),
                getattr(row, 'warehouse', ''),
                'PENDING',
            )
            self.tree.insert('', END, iid=str(i), values=vals)

        header = result.header if result else None
        customer = getattr(header, 'customer', '?') if header else '?'
        total = getattr(result, 'total_qty', None)
        if total is None and self.parsed_rows:
            total = sum(float(getattr(r, 'qty_mt', 0) or 0) for r in self.parsed_rows)
        elif total is None:
            total = 0.0
        fname = path.split('/')[-1].split(chr(92))[-1]
        tb500, samp = _allocation_tonbag_sample_counts(self.parsed_rows)
        self._summary_var.set(
            f"고객: {customer} | 총 {len(self.parsed_rows)}행 | 총량: {total:.4f} MT | "
            f"500kg {tb500}개, 샘플 {samp}개 | 파싱: {elapsed_sec:.2f}초 | {fname}"
        )

        if self.parsed_rows:
            self.btn_reserve.config(state='normal')
            if hasattr(self, 'btn_reset_lot'):
                self.btn_reset_lot.config(state='normal')
        else:
            self.btn_reserve.config(state='disabled')
            if hasattr(self, 'btn_reset_lot'):
                self.btn_reset_lot.config(state='disabled')
        if getattr(self, '_alloc_total_footer', None):
            self._alloc_total_footer.update_totals()

    def _fill_tree_from_parsed_rows(self):
        """parsed_rows( dict 리스트 )로 트리 채우기. show_with_data용."""
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.parsed_rows):
            if hasattr(row, 'get'):
                vals = (
                    str(row.get('lot_no', '')),
                    str(row.get('sap_no', '')),
                    str(row.get('product', '')),
                    f"{float(row.get('qty_mt') or 0):.4f}",
                    str(row.get('sold_to') or row.get('customer', '')),
                    str(row.get('sale_ref', '')),
                    str(row.get('outbound_date', '') or ''),
                    str(row.get('warehouse', '')),
                    'PENDING',
                )
            else:
                vals = (
                    getattr(row, 'lot_no', ''),
                    getattr(row, 'sap_no', ''),
                    getattr(row, 'product', ''),
                    f"{getattr(row, 'qty_mt', 0):.4f}",
                    getattr(row, 'sold_to', ''),
                    getattr(row, 'sale_ref', ''),
                    str(getattr(row, 'outbound_date', '') or ''),
                    getattr(row, 'warehouse', ''),
                    'PENDING',
                )
            self.tree.insert('', END, iid=str(i), values=vals)
        if getattr(self, '_alloc_total_footer', None):
            self._alloc_total_footer.update_totals()

    def _on_reserve(self):
        if not self.parsed_rows:
            return

        dup = self._check_duplicate_allocation_file()
        if dup.get('is_duplicate'):
            dup_msg = (
                f"[중복 파일 감지]\n"
                f"파일: {dup.get('file_name', '')}\n"
                f"예약 건수: {dup.get('count', 0)}\n\n"
                "선택하세요:\n"
                "• 기존 예약 진행 → [출고 실행]\n"
                "• 다시 예약 → [예약 취소] 후 재시도\n\n"
                "이번 예약을 계속 진행할까요?"
            )
            if not CustomMessageBox.askyesno(self.dialog, "중복 Allocation", dup_msg):
                return

        warnings = self._build_reserve_shortage_warnings()
        if warnings:
            warn_msg = (
                "[가용 수량 부족 경고 (샘플 포함 기준)]\n"
                + "\n".join(warnings[:10])
                + "\n\n계속 진행하면 일부 LOT은 예약되지 않습니다.\n계속 진행하시겠습니까?"
            )
            if not CustomMessageBox.askyesno(self.dialog, "가용 수량 부족", warn_msg):
                return

        history_lots = self._check_reserved_history_lots()
        if history_lots:
            preview = ", ".join(history_lots[:10])
            more = f"\n... 외 {len(history_lots) - 10}건" if len(history_lots) > 10 else ""
            history_msg = (
                "[예약 이력 경고]\n"
                "다음 LOT은 과거에 한 번이라도 예약된 이력이 있습니다.\n"
                f"{preview}{more}\n\n"
                "그래도 이번 예약을 진행할까요?"
            )
            if not CustomMessageBox.askyesno(self.dialog, "예약 이력 경고", history_msg):
                return

        tb500, samp = _allocation_tonbag_sample_counts(self.parsed_rows)
        confirm_msg = (
            f"500kg 제품 {tb500}개 및 샘플(1kg) {samp}개 판매 배정합니다.\n계속하시겠습니까?"
        )
        ok = CustomMessageBox.askyesno(self.dialog, "예약 실행", confirm_msg)
        if not ok:
            return

        try:
            result = self.engine.reserve_from_allocation(
                self.parsed_rows, source_file=self.source_file
            )
            if result.get('success'):
                reserved = result.get('reserved', 0)
                requested_rows = result.get('requested_rows', len(self.parsed_rows))
                requested_slots = tb500 + samp  # 요청한 톤백/샘플 수 (행 수와 단위 다름)
                msg = f"✅ 요청: {requested_rows}행 (500kg {tb500}개 + 샘플 {samp}개) → 실제 예약 톤백: {reserved}개"
                if requested_slots > 0 and reserved < requested_slots:
                    msg += f"\n\n(요청 톤백/샘플 수({requested_slots}개)보다 적게 예약된 경우, 해당 LOT에 가용 톤백이 없거나 이미 예약/출고된(중복 배정) LOT입니다.)"
                errors = result.get('errors', [])
                if errors:
                    msg += "\n\n(미예약 사유: " + "; ".join(errors[:5]) + ")"
                CustomMessageBox.showinfo(self.dialog, "예약 완료", msg)
                self.btn_cancel_res.config(state='normal')
                self.btn_execute.config(state='normal')
                self._deferred_refresh_after_action()
            else:
                errors = result.get('errors', [])
                CustomMessageBox.showerror(
                    self.dialog, "예약 실패",
                    f"예약 실패:\n" + "\n".join(errors[:10])
                )
                self._show_lot_status_popup()
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"예약 실행 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.dialog, "오류", f"예약 실행 중 오류:\n{e}")

    def _check_duplicate_allocation_file(self) -> dict:
        """같은 Allocation 파일이 이미 예약됐는지 확인 (basename 기준)."""
        if not self.source_file or self.source_file == '(붙여넣기)':
            return {'is_duplicate': False}
        if not hasattr(self.engine, 'db') or not self.engine.db:
            return {'is_duplicate': False}
        try:
            import os
            fname = os.path.basename(self.source_file)
            row = self.engine.db.fetchone(
                "SELECT COUNT(*) AS cnt FROM allocation_plan WHERE status = 'RESERVED' AND source_file LIKE ?",
                (f"%{fname}",)
            )
            cnt = row.get('cnt', 0) if isinstance(row, dict) else (row[0] if row else 0)
            return {'is_duplicate': cnt > 0, 'count': int(cnt), 'file_name': fname}
        except Exception as e:
            logger.debug(f"중복 Allocation 확인 실패: {e}")
            return {'is_duplicate': False}

    def _check_reserved_history_lots(self) -> list:
        """과거 예약 이력이 있는 LOT 목록 반환 (allocation_plan 기준)."""
        if not getattr(self, 'parsed_rows', None):
            return []
        if not hasattr(self.engine, 'db') or not self.engine.db:
            return []
        lot_set = []
        for r in self.parsed_rows:
            lot_no = (r.get('lot_no') if hasattr(r, 'get') else getattr(r, 'lot_no', '')).strip()
            if lot_no:
                lot_set.append(lot_no)
        lot_set = list(dict.fromkeys(lot_set))
        if not lot_set:
            return []
        try:
            placeholders = ",".join("?" * len(lot_set))
            rows = self.engine.db.fetchall(
                f"SELECT DISTINCT lot_no FROM allocation_plan WHERE lot_no IN ({placeholders})",
                tuple(lot_set),
            )
            lots = [str(r.get('lot_no', '')).strip() for r in (rows or []) if (r.get('lot_no') if isinstance(r, dict) else None)]
            return [l for l in lots if l]
        except Exception as e:
            logger.debug(f"예약 이력 확인 실패: {e}")
            return []

    def _build_reserve_shortage_warnings(self) -> list:
        """예약 전 LOT별 가용(샘플 포함) 수량 부족 경고 메시지 생성."""
        warnings = []
        if not hasattr(self.engine, 'db') or not self.engine.db:
            return warnings

        by_lot = {}
        for r in self.parsed_rows:
            lot_no = (r.get('lot_no') if hasattr(r, 'get') else getattr(r, 'lot_no', '')).strip()
            if not lot_no:
                continue
            qty_mt = 0.0
            sublot_count = 0
            if hasattr(r, 'get'):
                qty_mt = float(r.get('qty_mt') or 0)
                sublot_count = int(r.get('sublot_count') or r.get('tonbag_count') or 0)
            else:
                qty_mt = float(getattr(r, 'qty_mt', 0) or 0)
                sublot_count = int(getattr(r, 'sublot_count', 0) or getattr(r, 'tonbag_count', 0) or 0)
            weight_kg = qty_mt * 1000.0 if qty_mt > 0 else sublot_count * 500
            need_count = sublot_count if sublot_count > 0 else max(1, int(weight_kg / 500))
            by_lot[lot_no] = by_lot.get(lot_no, 0) + need_count

        for lot_no, need_count in by_lot.items():
            row = self.engine.db.fetchone(
                """SELECT
                    SUM(CASE WHEN status = 'AVAILABLE' THEN 1 ELSE 0 END) AS avail_total,
                    SUM(CASE WHEN status = 'AVAILABLE' AND COALESCE(is_sample, 0) = 1 THEN 1 ELSE 0 END) AS avail_sample
                FROM inventory_tonbag WHERE lot_no = ?""",
                (lot_no,)
            )
            avail_total = row.get('avail_total', 0) if isinstance(row, dict) else (row[0] if row else 0)
            avail_sample = row.get('avail_sample', 0) if isinstance(row, dict) else (row[1] if row else 0)
            if avail_total < need_count:
                warnings.append(
                    f"{lot_no}: 요청 {need_count}개 / 가용(전체) {avail_total}개 "
                    f"(샘플 {avail_sample}개 포함)"
                )

        return warnings

    def _show_lot_status_popup(self) -> None:
        """예약 실패 시 LOT별 상태(샘플 포함) 팝업 표시."""
        if not hasattr(self.engine, 'db') or not self.engine.db:
            return
        lot_nos = []
        for r in self.parsed_rows:
            lot_no = (r.get('lot_no') if hasattr(r, 'get') else getattr(r, 'lot_no', '')).strip()
            if lot_no:
                lot_nos.append(lot_no)
        if not lot_nos:
            return
        # 중복 제거 유지 순서
        seen = set()
        lot_nos = [l for l in lot_nos if not (l in seen or seen.add(l))]

        lines = ["[LOT 상태 요약]", "LOT\tAVAIL\tSAMPLE\tRESERVED\tPICKED\tSOLD"]
        for lot_no in lot_nos:
            row = self.engine.db.fetchone(
                """SELECT
                    SUM(CASE WHEN status = 'AVAILABLE' THEN 1 ELSE 0 END) AS avail_total,
                    SUM(CASE WHEN status = 'AVAILABLE' AND COALESCE(is_sample, 0) = 1 THEN 1 ELSE 0 END) AS avail_sample,
                    SUM(CASE WHEN status = 'RESERVED' THEN 1 ELSE 0 END) AS reserved_cnt,
                    SUM(CASE WHEN status = 'PICKED' THEN 1 ELSE 0 END) AS picked_cnt,
                    SUM(CASE WHEN status = 'SOLD' THEN 1 ELSE 0 END) AS sold_cnt
                FROM inventory_tonbag WHERE lot_no = ?""",
                (lot_no,)
            )
            if not row:
                lines.append(f"{lot_no}: 상태 없음")
                continue
            avail_total = row.get('avail_total', 0)
            avail_sample = row.get('avail_sample', 0)
            reserved_cnt = row.get('reserved_cnt', 0)
            picked_cnt = row.get('picked_cnt', 0)
            sold_cnt = row.get('sold_cnt', 0)
            lines.append(
                f"{lot_no}\t{avail_total}\t{avail_sample}\t{reserved_cnt}\t{picked_cnt}\t{sold_cnt}"
            )
            if len(lines) >= 16:
                lines.append("... (이하 생략)")
                break

        CustomMessageBox.showinfo(self.dialog, "LOT 상태 확인", "\n".join(lines))

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
                self._deferred_refresh_after_action()
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
                self._deferred_refresh_after_action()
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
                self._deferred_refresh_after_action()
            else:
                CustomMessageBox.showerror(
                    self.dialog, "취소 실패",
                    "\n".join(result.get('errors', ['알 수 없는 오류']))
                )
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"예약 취소 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.dialog, "오류", str(e))

    def _on_reset_reservation_for_lots(self) -> None:
        """현재 Allocation LOT들에 대한 예약(RESERVED)만 초기화."""
        if not self.parsed_rows:
            return
        lot_nos = []
        for r in self.parsed_rows:
            lot_no = (r.get('lot_no') if hasattr(r, 'get') else getattr(r, 'lot_no', '')).strip()
            if lot_no:
                lot_nos.append(lot_no)
        if not lot_nos:
            return
        # 중복 제거 유지 순서
        seen = set()
        lot_nos = [l for l in lot_nos if not (l in seen or seen.add(l))]

        if not CustomMessageBox.askyesno(
            self.dialog, "LOT 예약 초기화",
            f"현재 Allocation LOT {len(lot_nos)}개에 대해\n"
            f"RESERVED 상태만 AVAILABLE로 되돌립니다.\n"
            f"(PICKED/SOLD는 변경하지 않습니다)\n\n계속하시겠습니까?"
        ):
            return
        total = 0
        try:
            for lot_no in lot_nos:
                r = self.engine.cancel_reservation(lot_no=lot_no)
                total += r.get('cancelled', 0)
            CustomMessageBox.showinfo(
                self.dialog, "초기화 완료",
                f"예약 초기화 완료: {total}건 (RESERVED → AVAILABLE)"
            )
            self._deferred_refresh_after_action()
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"LOT 예약 초기화 오류: {e}", exc_info=True)
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
            status_win.title("📊 판매 배정 예약 현황")
            setup_dialog_geometry_persistence(status_win, "allocation_status_win", self.dialog, "large")
            _is_dark = ThemeColors.is_dark_theme(getattr(self.app, 'current_theme', 'flatly'))
            status_win.configure(bg=ThemeColors.get('bg_card', _is_dark))
            status_win.transient(self.dialog)

            cols = ('lot_no', 'customer', 'sale_ref', 'qty_mt', 'outbound_date', 'status', 'tb_count', 'created_at')
            hdrs = ('LOT NO', 'CUSTOMER', 'SALE REF', 'QTY(MT)', 'DATE', 'STATUS', 'TONBAGS', 'CREATED')
            tree_frame = ttk.Frame(status_win)
            tree_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
            st = ttk.Treeview(tree_frame, columns=cols, show='headings', height=15)
            scroll = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=st.yview)
            st.configure(yscrollcommand=scroll.set)
            st.pack(side=LEFT, fill=BOTH, expand=True)
            scroll.pack(side=RIGHT, fill=Y)
            for c, h in zip(cols, hdrs):
                st.heading(c, text=h)
                st.column(c, width=100, anchor='center')

            for r in rows:
                st.insert('', END, values=(
                    r.get('lot_no', ''), r.get('customer', ''),
                    r.get('sale_ref', ''), f"{r.get('qty_mt', 0):.4f}",
                    r.get('outbound_date', ''), r.get('status', ''),
                    r.get('tb_count', 0), r.get('created_at', '')
                ))
            # 하단 합계 (건수, 톤백 수, 무게)
            total_mt = sum(float(r.get('qty_mt', 0) or 0) for r in rows)
            total_tb = sum(int(r.get('tb_count', 0) or 0) for r in rows)
            footer = ttk.Frame(status_win, padding=(5, 4))
            footer.pack(fill=tk.X)
            ttk.Label(
                footer,
                text=f"건수: {len(rows)} LOT  |  톤백: {total_tb}개  |  QTY(MT) 합계: {total_mt:,.4f}",
                font=('맑은 고딕', 10, 'bold'),
            ).pack(anchor=tk.W)

        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"예약 현황 조회 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.dialog, "오류", str(e))

    def _deferred_refresh_after_action(self):
        """grab 해제 후 50ms 지연으로 리프레시 — 모달 안에서의 무거운 Treeview 갱신 블로킹 방지."""
        try:
            self.dialog.grab_release()
        except (tk.TclError, RuntimeError):
            pass
        if hasattr(self.app, '_deferred_refresh_main_tabs'):
            self.app._deferred_refresh_main_tabs(delay_ms=50)
        else:
            root = getattr(self.app, 'root', None)
            if root and root.winfo_exists():
                root.after(50, self._refresh_after_action)
            else:
                self._refresh_after_action()

    def _refresh_after_action(self):
        """예약/출고/취소 후 앱 전체 탭 새로고침 (판매 배정/판매화물 결정/출고 탭 포함)"""
        try:
            if hasattr(self.app, '_refresh_main_tabs'):
                self.app._refresh_main_tabs()
            else:
                if hasattr(self.app, '_refresh_inventory'):
                    self.app._refresh_inventory()
                if hasattr(self.app, '_refresh_tonbag'):
                    self.app._refresh_tonbag()
                if hasattr(self.app, '_refresh_outbound_scheduled'):
                    self.app._refresh_outbound_scheduled()
                if hasattr(self.app, '_refresh_allocation'):
                    self.app._refresh_allocation()
                if hasattr(self.app, '_refresh_picked'):
                    self.app._refresh_picked()
                if hasattr(self.app, '_refresh_sold'):
                    self.app._refresh_sold()
        except (RuntimeError, ValueError) as e:
            logger.debug(f"새로고침 실패: {e}")
