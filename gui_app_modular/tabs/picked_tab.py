# -*- coding: utf-8 -*-
"""
v7.0 4단계: PICKED 탭 — picking_table(ACTIVE) 기반 LOT 리스트 + 전체 피킹 보기
"""
import logging
import tkinter as tk
from tkinter import ttk
from ..utils.ui_constants import ThemeColors, Spacing, apply_tooltip
from ..utils.constants import BOTH, YES, X, LEFT, VERTICAL, RIGHT

logger = logging.getLogger(__name__)

PICKED_LOT_COLUMNS = [
    ('row_num', 'No.', 50, 'center'),
    ('lot_no', 'LOT NO', 120, 'center'),
    ('picking_no', '피킹No', 120, 'center'),
    ('customer', '고객사', 140, 'center'),
    ('tonbag_count', '톤백수', 70, 'e'),
    ('total_kg', '중량(kg)', 100, 'e'),
    ('picking_date', '피킹일', 100, 'center'),
]

PICKED_DETAIL_COLUMNS = [
    ('row_num', 'No.', 50, 'center'),
    ('lot_no', 'LOT NO', 120, 'center'),
    ('tonbag_no', '톤백No', 80, 'center'),
    ('picking_no', '피킹No', 120, 'center'),
    ('customer', '고객사', 140, 'center'),
    ('qty_kg', '중량(kg)', 100, 'e'),
    ('picking_date', '피킹일', 100, 'center'),
]


class PickedTabMixin:
    """v7.0: PICKED 탭 — picking_table(ACTIVE) LOT 리스트 + 전체 피킹 보기"""

    def _setup_picked_tab(self) -> None:
        """PICKED 탭 UI"""
        from ..utils.tree_enhancements import apply_striped_rows

        _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        frame = self.tab_picked

        ttk.Label(frame, text="판매화물 결정 LOT 리스트").pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))
        ttk.Button(btn_frame, text="🔄 새로고침", command=self._refresh_picked).pack(side=LEFT, padx=Spacing.XS)
        btn_revert_picked = ttk.Button(btn_frame, text="↩️ 판매화물 결정 취소 (→ 판매 배정)", command=lambda: self._safe_call('_on_revert_picked_to_reserved'))
        btn_revert_picked.pack(side=LEFT, padx=Spacing.XS)
        apply_tooltip(btn_revert_picked, "판매화물 결정 상태를 판매 배정으로 되돌립니다.")
        btn_show_all = ttk.Button(btn_frame, text="📋 전체 피킹 보기", command=self._on_show_all_picked)
        btn_show_all.pack(side=tk.RIGHT, padx=Spacing.XS)
        apply_tooltip(btn_show_all, "피킹(ACTIVE) 톤백 전체. [← LOT 리스트로]로 복귀.")
        
        btn_picked_export = ttk.Button(btn_frame, text="📥 Excel 내보내기", command=self._on_picked_export_excel)
        btn_picked_export.pack(side=tk.RIGHT, padx=Spacing.XS)
        apply_tooltip(btn_picked_export, "현재 판매화물 결정 목록을 Excel로 내보내기")

        self._picked_lot_container = ttk.Frame(frame)
        self._picked_lot_container.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)

        tree_frame = ttk.Frame(self._picked_lot_container)
        tree_frame.pack(fill=BOTH, expand=YES)
        cols = [c[0] for c in PICKED_LOT_COLUMNS]
        self.tree_picked = ttk.Treeview(
            tree_frame, columns=cols, show='headings', height=20, selectmode='extended'
        )
        for col_id, label, width, anchor in PICKED_LOT_COLUMNS:
            self.tree_picked.heading(col_id, text=label)
            self.tree_picked.column(col_id, width=width, anchor=anchor, stretch=True)
        scroll = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree_picked.yview)
        scroll_x = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree_picked.xview)
        self.tree_picked.configure(yscrollcommand=scroll.set, xscrollcommand=scroll_x.set)
        self.tree_picked.pack(side=LEFT, fill=BOTH, expand=YES)
        scroll.pack(side=tk.RIGHT, fill='y')
        scroll_x.pack(side=tk.BOTTOM, fill='x')
        try:
            apply_striped_rows(self.tree_picked, _is_dark)
        except Exception as e:
            logger.debug(f"apply_striped_rows: {e}")

        self.tree_picked.bind('<Double-1>', self._on_picked_lot_double_click)

        self._picked_summary_label = ttk.Label(self._picked_lot_container, text="LOT 0개 / 톤백 0개 / 총 0 kg")
        self._picked_summary_label.pack(fill=X, pady=(Spacing.XS, 0))

        self._picked_detail_container = ttk.Frame(frame)
        tb_bar = ttk.Frame(self._picked_detail_container)
        tb_bar.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))
        ttk.Button(tb_bar, text="← LOT 리스트로", command=self._on_back_to_picked_lot_list).pack(side=LEFT, padx=Spacing.XS)
        ttk.Button(tb_bar, text="🔄 새로고침", command=self._on_show_all_picked).pack(side=LEFT, padx=Spacing.XS)
        btn_detail_revert_picked = ttk.Button(tb_bar, text="↩️ 판매화물 결정 취소 (→ 판매 배정)", command=lambda: self._safe_call('_on_revert_picked_to_reserved'))
        btn_detail_revert_picked.pack(side=LEFT, padx=Spacing.XS)
        detail_tree_frame = ttk.Frame(self._picked_detail_container)
        detail_tree_frame.pack(fill=BOTH, expand=YES)
        detail_cols = [c[0] for c in PICKED_DETAIL_COLUMNS]
        self.tree_picked_detail = ttk.Treeview(
            detail_tree_frame, columns=detail_cols, show='headings', height=22, selectmode='extended'
        )
        for col_id, label, width, anchor in PICKED_DETAIL_COLUMNS:
            self.tree_picked_detail.heading(col_id, text=label)
            self.tree_picked_detail.column(col_id, width=width, anchor=anchor, stretch=True)
        scroll2 = ttk.Scrollbar(detail_tree_frame, orient=VERTICAL, command=self.tree_picked_detail.yview)
        scroll2_x = ttk.Scrollbar(detail_tree_frame, orient='horizontal', command=self.tree_picked_detail.xview)
        self.tree_picked_detail.configure(yscrollcommand=scroll2.set, xscrollcommand=scroll2_x.set)
        self.tree_picked_detail.pack(side=LEFT, fill=BOTH, expand=YES)
        scroll2.pack(side=tk.RIGHT, fill='y')
        scroll2_x.pack(side=tk.BOTTOM, fill='x')

        self._refresh_picked()

    def _on_picked_export_excel(self) -> None:
        """판매화물 결정(Picked) 데이터 Excel 내보내기"""
        try:
            import pandas as pd
            from tkinter import filedialog
            from datetime import datetime
            
            sql = """
                SELECT lot_no, sub_lt, picking_no, customer, qty_kg, picking_date, created_by
                FROM picking_table
                WHERE status = 'ACTIVE' AND COALESCE(is_sample, 0) = 0
                ORDER BY lot_no, sub_lt
            """
            rows = self.engine.db.fetchall(sql) if hasattr(self.engine, 'db') and self.engine.db else []
            
            if not rows:
                if hasattr(self, '_log'):
                    self._log("내보낼 판매화물 결정 데이터가 없습니다.")
                return

            df = pd.DataFrame(rows)
            col_map = {
                'lot_no': 'LOT NO',
                'sub_lt': 'Sub LOT',
                'picking_no': 'Picking No',
                'customer': '고객사',
                'qty_kg': '중량(kg)',
                'picking_date': '피킹일',
                'created_by': '작업자'
            }
            df.rename(columns=col_map, inplace=True)
            
            path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[('Excel', '*.xlsx'), ('All', '*.*')],
                initialfile=f"PICKED_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            if path:
                df.to_excel(path, index=False)
                if hasattr(self, '_log'):
                    self._log(f"✅ 판매화물 결정 Excel 저장: {path}")
        except ImportError:
            logger.debug("pandas 없음: Excel 내보내기 스킵")
        except Exception as e:
            logger.debug(f"_on_picked_export_excel: {e}")

    def _refresh_picked(self) -> None:
        """PICKED LOT 리스트 — picking_table WHERE status='ACTIVE' GROUP BY lot_no, picking_no"""
        if not getattr(self, 'tree_picked', None):
            return
        for item in self.tree_picked.get_children(''):
            self.tree_picked.delete(item)
        try:
            rows = self.engine.db.fetchall("""
                SELECT lot_no, customer, picking_no,
                    COUNT(*) AS tonbag_count,
                    SUM(COALESCE(qty_kg, 0)) AS total_kg,
                    MIN(picking_date) AS picking_date
                FROM picking_table
                WHERE status = 'ACTIVE' AND COALESCE(is_sample, 0) = 0
                GROUP BY lot_no, picking_no
                ORDER BY picking_date DESC, lot_no
            """) if hasattr(self.engine, 'db') and self.engine.db else []
            for idx, r in enumerate(rows or [], 1):
                lot_no = str(r.get('lot_no', ''))
                picking_no = str(r.get('picking_no', '') or '-')
                customer = str(r.get('customer', '') or '-')
                tonbag_count = int(r.get('tonbag_count') or 0)
                total_kg = float(r.get('total_kg') or 0)
                picking_date = str(r.get('picking_date') or '')[:10] if r.get('picking_date') else '-'
                self.tree_picked.insert('', 'end', values=(
                    str(idx), lot_no, picking_no, customer, str(tonbag_count), f"{total_kg:,.0f}", picking_date
                ))
            total_lots = len(rows or [])
            total_tb = sum(int(r.get('tonbag_count') or 0) for r in (rows or []))
            total_kg = sum(float(r.get('total_kg') or 0) for r in (rows or []))
            if hasattr(self, '_picked_summary_label'):
                self._picked_summary_label.config(
                    text=f"LOT {total_lots}개 / 톤백 {total_tb}개 / 총 {total_kg:,.0f} kg"
                )
        except Exception as e:
            logger.debug(f"_refresh_picked: {e}")

    def _on_show_all_picked(self) -> None:
        """전체 피킹 보기"""
        if not getattr(self, 'tree_picked_detail', None):
            return
        for item in self.tree_picked_detail.get_children(''):
            self.tree_picked_detail.delete(item)
        try:
            rows = self.engine.db.fetchall("""
                SELECT lot_no, sub_lt, picking_no, customer, qty_kg, picking_date
                FROM picking_table
                WHERE status = 'ACTIVE' AND COALESCE(is_sample, 0) = 0
                ORDER BY picking_date DESC, lot_no, sub_lt
            """) if hasattr(self.engine, 'db') and self.engine.db else []
            for idx, r in enumerate(rows or [], 1):
                lot_no = str(r.get('lot_no', ''))
                sub_lt = r.get('sub_lt', '')
                tonbag_no = str(sub_lt) if sub_lt is not None else '-'
                picking_no = str(r.get('picking_no', '') or '-')
                customer = str(r.get('customer', '') or '-')
                qty_kg = float(r.get('qty_kg') or 0)
                picking_date = str(r.get('picking_date') or '')[:10] if r.get('picking_date') else '-'
                self.tree_picked_detail.insert('', 'end', values=(
                    str(idx), lot_no, tonbag_no, picking_no, customer, f"{qty_kg:,.0f}", picking_date
                ))
            self._picked_lot_container.pack_forget()
            self._picked_detail_container.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)
        except Exception as e:
            logger.debug(f"_on_show_all_picked: {e}")

    def _on_back_to_picked_lot_list(self) -> None:
        """LOT 리스트로 복귀"""
        self._picked_detail_container.pack_forget()
        self._picked_lot_container.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)
        self._refresh_picked()

    def _on_picked_lot_double_click(self, event) -> None:
        """LOT 더블클릭 → 해당 LOT PICKED 톤백 팝업"""
        sel = self.tree_picked.selection()
        if not sel:
            return
        item = self.tree_picked.item(sel[0])
        vals = item.get('values', [])
        cols = [c[0] for c in PICKED_LOT_COLUMNS]
        lot_no = ''
        if 'lot_no' in cols and len(vals) > cols.index('lot_no'):
            lot_no = str(vals[cols.index('lot_no')]).strip()
        if lot_no and hasattr(self, '_show_lot_detail_popup'):
            self._show_lot_detail_popup(lot_no, 'picked')
