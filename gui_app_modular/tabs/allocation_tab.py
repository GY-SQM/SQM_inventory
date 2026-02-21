# -*- coding: utf-8 -*-
"""
v7.0 3단계: ALLOCATION 탭 — allocation_plan(RESERVED) 기반 LOT 리스트 + 전체 배정 보기
"""
import logging
import tkinter as tk
from tkinter import ttk
from ..utils.ui_constants import ThemeColors, Spacing, apply_tooltip
from ..utils.constants import BOTH, YES, X, LEFT, VERTICAL

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
        from ..utils.tree_enhancements import apply_striped_rows, TreeviewTotalFooter

        _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        frame = self.tab_allocation

        # 제목
        ttk.Label(frame, text="판매배정 LOT 리스트").pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))

        # 버튼 바: 검색/고객사 필터(선택) + [전체 배정 보기]
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))
        ttk.Button(btn_frame, text="🔄 새로고침", command=self._refresh_allocation).pack(side=LEFT, padx=Spacing.XS)
        btn_show_all = ttk.Button(btn_frame, text="📋 전체 배정 보기", command=self._on_show_all_allocation)
        btn_show_all.pack(side=RIGHT, padx=Spacing.XS)
        apply_tooltip(btn_show_all, "배정(RESERVED) 톤백 전체 목록. [← LOT 리스트로]로 복귀.")

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
        self.tree_allocation.configure(yscrollcommand=scroll.set)
        self.tree_allocation.pack(side=LEFT, fill=BOTH, expand=YES)
        scroll.pack(side=tk.RIGHT, fill='y')
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
        self.tree_allocation_detail.configure(yscrollcommand=scroll2.set)
        self.tree_allocation_detail.pack(side=LEFT, fill=BOTH, expand=YES)
        scroll2.pack(side=tk.RIGHT, fill='y')

        self._refresh_allocation()

    def _refresh_allocation(self) -> None:
        """ALLOCATION LOT 리스트 새로고침 — allocation_plan WHERE status='RESERVED' GROUP BY lot_no"""
        if not getattr(self, 'tree_allocation', None):
            return
        for item in self.tree_allocation.get_children(''):
            self.tree_allocation.delete(item)
        try:
            rows = self.engine.db.fetchall("""
                SELECT lot_no, customer,
                    SUM(COALESCE(qty_mt, 0)) AS total_mt,
                    COUNT(*) AS tonbag_count,
                    MAX(outbound_date) AS plan_date
                FROM allocation_plan
                WHERE status = 'RESERVED'
                GROUP BY lot_no
                ORDER BY lot_no
            """) if hasattr(self.engine, 'db') and self.engine.db else []
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
                self._alloc_summary_label.config(
                    text=f"LOT {total_lots}개 / 톤백 {total_tb}개 / 총 {total_mt:,.2f} MT"
                )
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
                SELECT ap.lot_no, ap.sub_lt, ap.customer, ap.qty_mt, ap.created_at
                FROM allocation_plan ap
                WHERE ap.status = 'RESERVED'
                ORDER BY ap.lot_no, ap.sub_lt
            """) if hasattr(self.engine, 'db') and self.engine.db else []
            for idx, r in enumerate(rows or [], 1):
                lot_no = str(r.get('lot_no', ''))
                sub_lt = r.get('sub_lt', '')
                tonbag_no = str(sub_lt) if sub_lt is not None else '-'
                customer = str(r.get('customer', '') or '-')
                qty_mt = float(r.get('qty_mt') or 0)
                created = str(r.get('created_at') or '')[:10] if r.get('created_at') else '-'
                self.tree_allocation_detail.insert('', 'end', values=(
                    str(idx), lot_no, tonbag_no, customer, f"{qty_mt:,.2f}", created
                ))
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
