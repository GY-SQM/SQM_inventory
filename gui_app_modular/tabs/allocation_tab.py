"""
v7.0 3단계: ALLOCATION 탭 — allocation_plan(RESERVED) 기반 LOT 리스트 + 전체 배정 보기
"""
import logging
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from ..utils.constants import BOTH, LEFT, VERTICAL, YES, X
from ..utils.ui_constants import CustomMessageBox, Spacing, ThemeColors, apply_tooltip

logger = logging.getLogger(__name__)

ALLOCATION_LOT_COLUMNS = [
    ('row_num', 'No.', 50, 'center'),
    ('lot_no', 'LOT NO', 120, 'center'),
    ('customer', '고객사', 140, 'center'),
    ('total_mt', '배정수량(MT)', 100, 'e'),
    ('tonbag_count', '톤백수', 70, 'e'),
    ('plan_date', '출고예정일', 100, 'center'),
]

ALLOCATION_DETAIL_COLUMNS = [
    ('row_num', 'No.', 50, 'center'),
    ('lot_no', 'LOT NO', 120, 'center'),
    ('tonbag_no', '톤백No', 80, 'center'),
    ('customer', '고객사', 140, 'center'),
    ('qty_mt', '배정수량(MT)', 100, 'e'),
    ('created_at', '배정일', 100, 'center'),
]


class AllocationTabMixin:
    """v7.0: ALLOCATION 탭 — allocation_plan(RESERVED) LOT 리스트 + 전체 배정 보기"""

    def _setup_allocation_tab(self) -> None:
        """ALLOCATION 탭 UI (LOT 리스트 + [전체 배정 보기] + 복귀)"""
        from ..utils.tree_enhancements import TreeviewTotalFooter, apply_striped_rows

        _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        frame = self.tab_allocation

        # 제목
        ttk.Label(frame, text="판매배정 LOT 리스트").pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))

        # 버튼 바: 새로고침 / 취소 3종 (→판매가능, →판매배정, →판매화물결정) / 전체 배정 보기
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))
        ttk.Button(btn_frame, text="🔄 새로고침", command=self._refresh_allocation).pack(side=LEFT, padx=Spacing.XS)
        btn_cancel = ttk.Button(btn_frame, text="❌ 판매 배정 취소 (→ 판매가능)", command=self._on_allocation_cancel_to_available)
        btn_cancel.pack(side=LEFT, padx=Spacing.XS)
        apply_tooltip(btn_cancel, "선택한 LOT 또는 전체 배정을 취소하여 판매가능으로 되돌립니다.")
        btn_show_all = ttk.Button(btn_frame, text="📋 전체 배정 보기", command=self._on_show_all_allocation)
        btn_show_all.pack(side=tk.RIGHT, padx=Spacing.XS)
        apply_tooltip(btn_show_all, "판매 배정 톤백 전체 목록. [← LOT 리스트로]로 복귀.")

        btn_alloc_export = ttk.Button(btn_frame, text="📥 Excel 내보내기", command=self._on_allocation_export_excel)
        btn_alloc_export.pack(side=tk.RIGHT, padx=Spacing.XS)
        apply_tooltip(btn_alloc_export, "현재 판매배정 목록을 Excel로 내보내기")

        self._alloc_btn_cancel = btn_cancel
        self._alloc_btn_show_all = btn_show_all

        # LOT 리스트 컨테이너
        self._alloc_lot_container = ttk.Frame(frame)
        self._alloc_lot_container.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)

        tree_frame = ttk.Frame(self._alloc_lot_container)
        tree_frame.pack(fill=BOTH, expand=YES)
        cols = [c[0] for c in ALLOCATION_LOT_COLUMNS]
        self.tree_allocation = ttk.Treeview(
            tree_frame, columns=cols, show='headings', height=20,
            selectmode='extended', style='Alloc.Treeview' if hasattr(ttk.Style(), 'configure') else None
        )
        for col_id, label, width, anchor in ALLOCATION_LOT_COLUMNS:
            self.tree_allocation.heading(col_id, text=label)
            self.tree_allocation.column(col_id, width=width, anchor=anchor, stretch=True)
        scroll = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree_allocation.yview)
        scroll_x = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree_allocation.xview)
        self.tree_allocation.configure(yscrollcommand=scroll.set, xscrollcommand=scroll_x.set)
        self.tree_allocation.pack(side=LEFT, fill=BOTH, expand=YES)
        scroll.pack(side=tk.RIGHT, fill='y')
        scroll_x.pack(side=tk.BOTTOM, fill='x')
        try:
            apply_striped_rows(self.tree_allocation, _is_dark)
        except Exception as e:
            logger.debug(f"apply_striped_rows: {e}")

        self.tree_allocation.bind('<Double-1>', self._on_allocation_lot_double_click)

        # 하단 통계
        self._alloc_summary_label = ttk.Label(self._alloc_lot_container, text="LOT 0개 / 톤백 0개 / 총 0 MT")
        self._alloc_summary_label.pack(fill=X, pady=(Spacing.XS, 0))

        # 전체 배정 보기 컨테이너 (초기 숨김)
        self._alloc_detail_container = ttk.Frame(frame)
        tb_bar = ttk.Frame(self._alloc_detail_container)
        tb_bar.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))
        ttk.Button(tb_bar, text="← LOT 리스트로", command=self._on_back_to_allocation_lot_list).pack(side=LEFT, padx=Spacing.XS)
        ttk.Button(tb_bar, text="🔄 새로고침", command=self._on_show_all_allocation).pack(side=LEFT, padx=Spacing.XS)
        btn_detail_cancel_selected = ttk.Button(tb_bar, text="❌ 선택 취소 (→ 판매가능)", command=self._on_allocation_detail_cancel_selected)
        btn_detail_cancel_selected.pack(side=LEFT, padx=Spacing.XS)
        btn_detail_cancel_all = ttk.Button(tb_bar, text="❌ 전체 취소 (→ 판매가능)", command=self._on_allocation_detail_cancel_all)
        btn_detail_cancel_all.pack(side=LEFT, padx=Spacing.XS)
        self._alloc_detail_btn_cancel_selected = btn_detail_cancel_selected
        self._alloc_detail_btn_cancel_all = btn_detail_cancel_all
        detail_tree_frame = ttk.Frame(self._alloc_detail_container)
        detail_tree_frame.pack(fill=BOTH, expand=YES)
        detail_cols = [c[0] for c in ALLOCATION_DETAIL_COLUMNS]
        self.tree_allocation_detail = ttk.Treeview(
            detail_tree_frame, columns=detail_cols, show='headings', height=22, selectmode='extended'
        )
        for col_id, label, width, anchor in ALLOCATION_DETAIL_COLUMNS:
            self.tree_allocation_detail.heading(col_id, text=label)
            self.tree_allocation_detail.column(col_id, width=width, anchor=anchor, stretch=True)
        scroll2 = ttk.Scrollbar(detail_tree_frame, orient=VERTICAL, command=self.tree_allocation_detail.yview)
        scroll2_x = ttk.Scrollbar(detail_tree_frame, orient='horizontal', command=self.tree_allocation_detail.xview)
        self.tree_allocation_detail.configure(yscrollcommand=scroll2.set, xscrollcommand=scroll2_x.set)
        self.tree_allocation_detail.pack(side=LEFT, fill=BOTH, expand=YES)
        scroll2.pack(side=tk.RIGHT, fill='y')
        scroll2_x.pack(side=tk.BOTTOM, fill='x')
        # 전체 배정 보기 하단 합계 (건수, 배정수량 MT)
        from ..utils.tree_enhancements import TreeviewTotalFooter
        self._alloc_detail_footer = TreeviewTotalFooter(
            self._alloc_detail_container, self.tree_allocation_detail, ['qty_mt'],
            column_display_names={'qty_mt': '배정수량(MT)'}
        )
        self._alloc_detail_footer.pack(fill=X)

        self._refresh_allocation()

    def _on_allocation_export_excel(self) -> None:
        """판매배정(Allocation) 데이터 Excel 내보내기"""
        try:
            from tkinter import filedialog

            import pandas as pd

            # allocation_plan 데이터 조회
            sql = """
                SELECT ap.id, ap.lot_no, ap.sub_lt, ap.customer, ap.qty_mt, ap.outbound_date, ap.created_at
                FROM allocation_plan ap
                LEFT JOIN inventory_tonbag tb ON ap.tonbag_id = tb.id
                WHERE ap.status = 'RESERVED' AND COALESCE(tb.is_sample, 0) = 0
                ORDER BY ap.lot_no, ap.sub_lt
            """
            rows = self.engine.db.fetchall(sql) if hasattr(self.engine, 'db') and self.engine.db else []

            # fallback: inventory_tonbag에서 RESERVED 조회
            if not rows and getattr(self, '_alloc_fallback', False):
                sql_fb = """
                    SELECT lot_no, sub_lt, picked_to AS customer, weight, outbound_date, updated_at
                    FROM inventory_tonbag
                    WHERE status = 'RESERVED' AND COALESCE(is_sample, 0) = 0
                    ORDER BY lot_no, sub_lt
                """
                fb_rows = self.engine.db.fetchall(sql_fb) if hasattr(self.engine, 'db') and self.engine.db else []
                if fb_rows:
                    # 형식 변환
                    for r in fb_rows:
                        r_dict = dict(r)
                        r_dict['qty_mt'] = (float(r_dict.get('weight') or 0) / 1000.0)
                        r_dict['created_at'] = r_dict.get('updated_at')
                        rows.append(r_dict)

            if not rows:
                if hasattr(self, '_log'):
                    self._log("내보낼 판매배정 데이터가 없습니다.")
                return

            df = pd.DataFrame(rows)
            # 컬럼명 매핑 (보기 좋게)
            col_map = {
                'lot_no': 'LOT NO',
                'sub_lt': 'Sub LOT',
                'customer': '고객사',
                'qty_mt': '배정수량(MT)',
                'outbound_date': '출고예정일',
                'created_at': '배정일',
                'weight': '중량(kg)'
            }
            df.rename(columns=col_map, inplace=True)

            path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[('Excel', '*.xlsx'), ('All', '*.*')],
                initialfile=f"ALLOCATION_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            if path:
                df.to_excel(path, index=False)
                if hasattr(self, '_log'):
                    self._log(f"✅ 판매배정 Excel 저장: {path}")
        except ImportError:
            logger.debug("pandas 없음: Excel 내보내기 스킵")
        except Exception as e:
            logger.debug(f"_on_allocation_export_excel: {e}")

    def _refresh_allocation(self) -> None:
        """ALLOCATION LOT 리스트 새로고침 — allocation_plan WHERE status='RESERVED' GROUP BY lot_no"""
        if not getattr(self, 'tree_allocation', None):
            return
        for item in self.tree_allocation.get_children(''):
            self.tree_allocation.delete(item)
        # 예약 상태 동기화(톤백 상태 기반) — 기존 데이터 불일치 보정
        if hasattr(self.engine, 'db') and self.engine.db and hasattr(self.engine, '_recalc_lot_status'):
            try:
                lot_rows = self.engine.db.fetchall(
                    "SELECT DISTINCT lot_no FROM inventory_tonbag WHERE status IN ('RESERVED','PICKED','SOLD','SHIPPED')"
                )
                for r in lot_rows or []:
                    lot_no = str(r.get('lot_no', '')).strip() if isinstance(r, dict) else ''
                    if lot_no:
                        self.engine._recalc_lot_status(lot_no)
            except Exception as e:
                logger.debug(f"_refresh_allocation status sync skip: {e}")
        try:
            rows = self.engine.db.fetchall("""
                SELECT ap.lot_no, ap.customer,
                    SUM(COALESCE(ap.qty_mt, 0)) AS total_mt,
                    COUNT(*) AS tonbag_count,
                    MAX(ap.outbound_date) AS plan_date
                FROM allocation_plan ap
                LEFT JOIN inventory_tonbag tb ON ap.tonbag_id = tb.id
                WHERE ap.status = 'RESERVED' AND COALESCE(tb.is_sample, 0) = 0
                GROUP BY ap.lot_no
                ORDER BY ap.lot_no
            """) if hasattr(self.engine, 'db') and self.engine.db else []
            self._alloc_fallback = False
            if not rows and hasattr(self.engine, 'db') and self.engine.db:
                fb_rows = self.engine.db.fetchall("""
                    SELECT lot_no,
                        MAX(COALESCE(picked_to, '')) AS customer,
                        SUM(COALESCE(weight, 0)) / 1000.0 AS total_mt,
                        COUNT(*) AS tonbag_count,
                        MAX(outbound_date) AS plan_date
                    FROM inventory_tonbag
                    WHERE status = 'RESERVED' AND COALESCE(is_sample, 0) = 0
                    GROUP BY lot_no
                    ORDER BY lot_no
                """)
                if fb_rows:
                    rows = fb_rows
                    self._alloc_fallback = True
            for idx, r in enumerate(rows or [], 1):
                lot_no = str(r.get('lot_no', ''))
                customer = str(r.get('customer', '') or '-')
                total_mt = float(r.get('total_mt') or 0)
                tonbag_count = int(r.get('tonbag_count') or 0)
                plan_date = str(r.get('plan_date') or '')[:10] if r.get('plan_date') else '-'
                self.tree_allocation.insert('', 'end', values=(
                    str(idx), lot_no, customer, f"{total_mt:,.2f}", str(tonbag_count), plan_date
                ))
            # 통계
            total_lots = len(rows or [])
            total_tb = sum(int(r.get('tonbag_count') or 0) for r in (rows or []))
            total_mt = sum(float(r.get('total_mt') or 0) for r in (rows or []))
            if hasattr(self, '_alloc_summary_label'):
                summary_text = f"LOT {total_lots}개 / 톤백 {total_tb}개 / 총 {total_mt:,.2f} MT"
                if getattr(self, '_alloc_fallback', False):
                    summary_text += "  (톤백 기준 표시)"
                self._alloc_summary_label.config(text=summary_text)
            # allocation_plan은 비어 있는데 RESERVED 톤백이 있는 경우 경고 표시
            if total_lots == 0 and not getattr(self, '_alloc_fallback', False) and hasattr(self.engine, 'db') and self.engine.db:
                try:
                    row = self.engine.db.fetchone(
                        "SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE status = 'RESERVED'"
                    )
                    reserved_cnt = row.get('cnt', 0) if isinstance(row, dict) else (row[0] if row else 0)
                    if reserved_cnt > 0 and hasattr(self, '_alloc_summary_label'):
                        self._alloc_summary_label.config(
                            text=f"LOT 0개 / 톤백 0개 / 총 0 MT  (⚠ RESERVED 톤백 {reserved_cnt}개 — allocation_plan 비어 있음)"
                        )
                except Exception as e:
                    logger.debug(f"_refresh_allocation reserved check: {e}")
        except Exception as e:
            logger.debug(f"_refresh_allocation: {e}")
            if hasattr(self, '_log'):
                self._log(f"⚠️ 배정 목록 조회 오류: {e}")

    def _on_show_all_allocation(self) -> None:
        """전체 배정 보기 — allocation_plan 전체 행 표시"""
        if not getattr(self, 'tree_allocation_detail', None):
            return
        for item in self.tree_allocation_detail.get_children(''):
            self.tree_allocation_detail.delete(item)
        try:
            rows = self.engine.db.fetchall("""
                SELECT ap.id, ap.lot_no, ap.sub_lt, ap.customer, ap.qty_mt, ap.created_at
                FROM allocation_plan ap
                LEFT JOIN inventory_tonbag tb ON ap.tonbag_id = tb.id
                WHERE ap.status = 'RESERVED' AND COALESCE(tb.is_sample, 0) = 0
                ORDER BY ap.lot_no, ap.sub_lt
            """) if hasattr(self.engine, 'db') and self.engine.db else []
            self._alloc_fallback = False
            if not rows and hasattr(self.engine, 'db') and self.engine.db:
                fb_rows = self.engine.db.fetchall("""
                    SELECT id, lot_no, sub_lt, picked_to AS customer, weight, updated_at, outbound_date
                    FROM inventory_tonbag
                    WHERE status = 'RESERVED' AND COALESCE(is_sample, 0) = 0
                    ORDER BY lot_no, sub_lt
                """)
                if fb_rows:
                    rows = fb_rows
                    self._alloc_fallback = True
            for idx, r in enumerate(rows or [], 1):
                plan_id = r.get('id')
                lot_no = str(r.get('lot_no', ''))
                sub_lt = r.get('sub_lt', '')
                tonbag_no = str(sub_lt) if sub_lt is not None else '-'
                customer = str(r.get('customer', '') or '-')
                if getattr(self, '_alloc_fallback', False):
                    qty_mt = float(r.get('weight') or 0) / 1000.0
                    created = str(r.get('updated_at') or r.get('outbound_date') or '')[:10] if (r.get('updated_at') or r.get('outbound_date')) else '-'
                    iid = f"tb_{plan_id}" if plan_id is not None else ''
                else:
                    qty_mt = float(r.get('qty_mt') or 0)
                    created = str(r.get('created_at') or '')[:10] if r.get('created_at') else '-'
                    iid = f"plan_{plan_id}" if plan_id is not None else ''
                self.tree_allocation_detail.insert(
                    '', 'end', iid=iid or None, values=(
                        str(idx), lot_no, tonbag_no, customer, f"{qty_mt:,.2f}", created
                    )
                )
            if hasattr(self, '_alloc_detail_footer') and self._alloc_detail_footer:
                self._alloc_detail_footer.update_totals()
            self._alloc_lot_container.pack_forget()
            self._alloc_detail_container.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)
        except Exception as e:
            logger.debug(f"_on_show_all_allocation: {e}")

    def _on_back_to_allocation_lot_list(self) -> None:
        """LOT 리스트로 복귀"""
        self._alloc_detail_container.pack_forget()
        self._alloc_lot_container.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)
        self._refresh_allocation()

    def _on_allocation_lot_double_click(self, event) -> None:
        """LOT 더블클릭 → 해당 LOT의 RESERVED 톤백 팝업"""
        sel = self.tree_allocation.selection()
        if not sel:
            return
        item = self.tree_allocation.item(sel[0])
        vals = item.get('values', [])
        cols = [c[0] for c in ALLOCATION_LOT_COLUMNS]
        lot_no = ''
        if 'lot_no' in cols and len(vals) > cols.index('lot_no'):
            lot_no = str(vals[cols.index('lot_no')]).strip()
        if lot_no and hasattr(self, '_show_lot_detail_popup'):
            self._show_lot_detail_popup(lot_no, 'allocation')

    def _on_allocation_cancel_to_available(self) -> None:
        """판매 배정(LOT 리스트)에서 취소 → 판매가능. 선택 LOT 또는 전체."""
        root = getattr(self, 'root', None)
        if getattr(self, '_alloc_fallback', False):
            CustomMessageBox.showwarning(
                root, "예약 데이터 없음",
                "allocation_plan 데이터가 없어 취소 작업을 진행할 수 없습니다.\n[설정/도구 → 정합성 검사/복구] 후 다시 시도하세요."
            )
            return
        engine = getattr(self, 'engine', None)
        if not engine or not hasattr(engine, 'cancel_reservation'):
            CustomMessageBox.showwarning(root, "기능 없음", "예약 취소 기능을 사용할 수 없습니다.")
            return
        sel = self.tree_allocation.selection()
        cols = [c[0] for c in ALLOCATION_LOT_COLUMNS]
        if sel:
            lot_nos = []
            for s in sel:
                vals = self.tree_allocation.item(s).get('values', [])
                if 'lot_no' in cols and len(vals) > cols.index('lot_no'):
                    lot_nos.append(str(vals[cols.index('lot_no')]).strip())
            lot_nos = list(dict.fromkeys(lot_nos))
            if not lot_nos:
                return
            if not CustomMessageBox.askyesno(
                root, "판매 배정 취소",
                f"선택한 {len(lot_nos)}개 LOT의 배정을 취소하여 판매가능으로 되돌립니다.\n계속하시겠습니까?"
            ):
                return
            total = 0
            for lot_no in lot_nos:
                r = engine.cancel_reservation(lot_no=lot_no)
                total += r.get('cancelled', 0)
            CustomMessageBox.showinfo(root, "취소 완료", f"{total}건 취소되었습니다. (→ 판매가능)")
        else:
            if not CustomMessageBox.askyesno(
                root, "전체 취소",
                "전체 판매 배정을 취소하여 판매가능으로 되돌립니다.\n계속하시겠습니까?"
            ):
                return
            r = engine.cancel_reservation()
            total = r.get('cancelled', 0)
            CustomMessageBox.showinfo(root, "취소 완료", f"{total}건 취소되었습니다. (→ 판매가능)")
        if hasattr(self, '_deferred_refresh_main_tabs'):
            self._deferred_refresh_main_tabs(delay_ms=50)
        elif hasattr(self, '_refresh_main_tabs'):
            self._refresh_main_tabs()
        else:
            self._refresh_allocation()
            if hasattr(self, '_refresh_tonbag'):
                self._refresh_tonbag()
            if hasattr(self, '_refresh_inventory'):
                self._refresh_inventory()
            if hasattr(self, '_refresh_picked'):
                self._refresh_picked()
            if hasattr(self, '_refresh_sold'):
                self._refresh_sold()

    def _on_allocation_detail_cancel_selected(self) -> None:
        """전체 배정 보기에서 선택한 행만 취소 → 판매가능."""
        root = getattr(self, 'root', None)
        if getattr(self, '_alloc_fallback', False):
            CustomMessageBox.showwarning(
                root, "예약 데이터 없음",
                "allocation_plan 데이터가 없어 취소 작업을 진행할 수 없습니다.\n[설정/도구 → 정합성 검사/복구] 후 다시 시도하세요."
            )
            return
        engine = getattr(self, 'engine', None)
        if not engine or not hasattr(engine, 'cancel_reservation'):
            CustomMessageBox.showwarning(root, "기능 없음", "예약 취소 기능을 사용할 수 없습니다.")
            return
        sel = self.tree_allocation_detail.selection()
        if not sel:
            CustomMessageBox.showwarning(root, "선택 필요", "취소할 행을 선택하세요.")
            return
        plan_ids = []
        for iid in sel:
            if isinstance(iid, str) and iid.startswith("plan_"):
                try:
                    plan_ids.append(int(iid.replace("plan_", "")))
                except ValueError as e:
                    logger.warning(f"[_on_allocation_detail_cancel_selected] Suppressed: {e}")
        if not plan_ids:
            CustomMessageBox.showwarning(root, "선택 필요", "취소할 배정 행을 선택하세요.")
            return
        if not CustomMessageBox.askyesno(
            root, "선택 취소",
            f"선택한 {len(plan_ids)}건을 취소하여 판매가능으로 되돌립니다.\n계속하시겠습니까?"
        ):
            return
        r = engine.cancel_reservation(plan_ids=plan_ids)
        CustomMessageBox.showinfo(root, "취소 완료", r.get('message', f"{r.get('cancelled', 0)}건 취소됨"))
        self._on_show_all_allocation()
        if hasattr(self, '_deferred_refresh_main_tabs'):
            self._deferred_refresh_main_tabs(delay_ms=50)
        elif hasattr(self, '_refresh_main_tabs'):
            self._refresh_main_tabs()
        else:
            self._refresh_allocation()
            if hasattr(self, '_refresh_tonbag'):
                self._refresh_tonbag()
            if hasattr(self, '_refresh_picked'):
                self._refresh_picked()
            if hasattr(self, '_refresh_sold'):
                self._refresh_sold()

    def _on_allocation_detail_cancel_all(self) -> None:
        """전체 배정 보기에서 전체 취소 → 판매가능."""
        root = getattr(self, 'root', None)
        if getattr(self, '_alloc_fallback', False):
            CustomMessageBox.showwarning(
                root, "예약 데이터 없음",
                "allocation_plan 데이터가 없어 취소 작업을 진행할 수 없습니다.\n[설정/도구 → 정합성 검사/복구] 후 다시 시도하세요."
            )
            return
        engine = getattr(self, 'engine', None)
        if not engine or not hasattr(engine, 'cancel_reservation'):
            CustomMessageBox.showwarning(root, "기능 없음", "예약 취소 기능을 사용할 수 없습니다.")
            return
        if not CustomMessageBox.askyesno(
            root, "전체 취소",
            "전체 판매 배정을 취소하여 판매가능으로 되돌립니다.\n계속하시겠습니까?"
        ):
            return
        r = engine.cancel_reservation()
        CustomMessageBox.showinfo(root, "취소 완료", r.get('message', f"{r.get('cancelled', 0)}건 취소됨"))
        self._on_show_all_allocation()
        if hasattr(self, '_deferred_refresh_main_tabs'):
            self._deferred_refresh_main_tabs(delay_ms=50)
        elif hasattr(self, '_refresh_main_tabs'):
            self._refresh_main_tabs()
        else:
            self._refresh_allocation()
            if hasattr(self, '_refresh_tonbag'):
                self._refresh_tonbag()
            if hasattr(self, '_refresh_picked'):
                self._refresh_picked()
            if hasattr(self, '_refresh_sold'):
                self._refresh_sold()
