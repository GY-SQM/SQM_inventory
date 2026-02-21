# -*- coding: utf-8 -*-
"""
총괄 화물 리스트 탭 — 상태별 화물만 표시 (전체/판매가능/판매배정/판매화물 결정/출고)
- 판매배정 = 고객 Allocation(RESERVED) 테이블에 있는 LOT만
- 판매가능 = RESERVED/PICKED/SOLD 없는 LOT만
"""
import logging
from ..utils.ui_constants import ThemeColors, Spacing, get_status_display
from ..utils.constants import ttk, BOTH, YES, LEFT, X

logger = logging.getLogger(__name__)

# 재고 탭과 동일 컬럼 정의 (정렬 헤더 라벨용)
CARGO_OVERVIEW_COLUMNS = [
    ('row_num', 'No.', 50, 'center', True),
    ('lot_no', 'LOT NO', 120, 'center', True),
    ('sap_no', 'SAP NO', 120, 'center', True),
    ('bl_no', 'BL NO', 140, 'center', True),
    ('product', 'PRODUCT', 160, 'center', True),
    ('status', 'STATUS', 90, 'center', True),
    ('current_weight', 'Balance(Kg)', 100, 'e', True),
    ('net_weight', 'NET(Kg)', 100, 'e', True),
    ('container_no', 'CONTAINER', 130, 'center', True),
    ('mxbg_pallet', 'MXBG', 70, 'center', True),
    ('avail_bags', 'Avail', 60, 'center', True),
    ('salar_invoice_no', 'INVOICE NO', 100, 'center', True),
    ('ship_date', 'SHIP DATE', 95, 'center', True),
    ('arrival_date', 'ARRIVAL', 95, 'center', True),
    ('con_return', 'CON RETURN', 95, 'center', True),
    ('free_time', 'FREE TIME', 80, 'center', True),
    ('warehouse', 'WH', 80, 'center', True),
    ('customs', 'CUSTOMS', 90, 'center', True),
    ('initial_weight', 'Inbound(Kg)', 100, 'e', True),
    ('outbound_weight', 'Outbound(Kg)', 100, 'e', True),
]

STATUS_FILTER_MAP = {
    '전체': None,
    '판매가능': 'AVAILABLE',
    '판매배정': 'RESERVED',
    '판매화물 결정': 'PICKED',
    '출고': 'SOLD',
}


class CargoOverviewTabMixin:
    """총괄 화물 리스트 탭 — 상태 필터로 해당 화물만 표시"""

    def _setup_cargo_overview_tab(self) -> None:
        from ..utils.constants import VERTICAL
        from ..utils.tree_enhancements import apply_striped_rows, TreeviewTotalFooter
        from ..utils.ui_constants import apply_tooltip
        import tkinter as tk

        _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        frame = self.tab_cargo_overview

        # 상단: 상태 필터 (전체 / 판매가능 / 판매배정 / 판매화물 결정 / 출고)
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.SM))
        ttk.Label(filter_frame, text="상태:", font=('맑은 고딕', 10, 'bold')).pack(side=LEFT, padx=(0, Spacing.XS))
        self._cargo_status_var = tk.StringVar(value="전체 (0)")
        self._cargo_status_combo = ttk.Combobox(
            filter_frame, textvariable=self._cargo_status_var,
            values=["전체 (0)", "판매가능 (0)", "판매배정 (0)", "판매화물 결정 (0)", "출고 (0)"],
            state="readonly", width=20
        )
        self._cargo_status_combo.pack(side=LEFT, padx=(0, Spacing.SM))
        self._cargo_status_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_cargo_overview())
        apply_tooltip(self._cargo_status_combo, "전체 / 판매가능 / 판매배정 / 판매화물 결정 / 출고 중 선택하면 해당 상태의 화물만 표시됩니다.")

        ttk.Button(filter_frame, text="🔄 새로고침", command=self._refresh_cargo_overview).pack(side=LEFT, padx=Spacing.SM)
        apply_tooltip(filter_frame.winfo_children()[-1], "목록 다시 불러오기")

        # 트리뷰
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)
        all_col_ids = [c[0] for c in CARGO_OVERVIEW_COLUMNS]
        import tkinter.font as tkfont
        _style = ttk.Style()
        _font = tkfont.Font(family='맑은 고딕', size=11)
        _head_font = tkfont.Font(family='맑은 고딕', size=11, weight='bold')
        _row_h = _font.metrics('linespace') + 6
        _tv_bg = ThemeColors.get('bg_card', _is_dark)
        _tv_fg = ThemeColors.get('text_primary', _is_dark)
        _tv_head_bg = ThemeColors.get('bg_secondary', _is_dark)
        _tv_head_fg = ThemeColors.get('text_primary', _is_dark)
        _style.configure('Cargo.Treeview', font=_font, rowheight=_row_h, background=_tv_bg, foreground=_tv_fg, fieldbackground=_tv_bg)
        _style.configure('Cargo.Treeview.Heading', font=_head_font, background=_tv_head_bg, foreground=_tv_head_fg)
        _style.map('Cargo.Treeview', background=[('selected', ThemeColors.get('info'))], foreground=[('selected', ThemeColors.get('bg_card'))])

        self.tree_cargo_overview = ttk.Treeview(
            tree_frame, columns=all_col_ids, show="headings", height=22,
            selectmode='extended', style='Cargo.Treeview'
        )
        self._cargo_sort_column = None
        self._cargo_sort_reverse = False
        for col_id, label, width, anchor, _ in CARGO_OVERVIEW_COLUMNS:
            self.tree_cargo_overview.heading(
                col_id, text=label,
                command=lambda c=col_id: self._sort_cargo_treeview(c)
            )
            self.tree_cargo_overview.column(col_id, width=width, anchor=anchor, stretch=True)
        scroll = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree_cargo_overview.yview)
        self.tree_cargo_overview.configure(yscrollcommand=scroll.set)
        self.tree_cargo_overview.pack(side=LEFT, fill=BOTH, expand=YES)
        scroll.pack(side=tk.RIGHT, fill='y')
        apply_striped_rows(self.tree_cargo_overview, _is_dark)
        ThemeColors.configure_tags(self.tree_cargo_overview, _is_dark)

        # 하단 합계
        summable = ['current_weight', 'net_weight', 'initial_weight', 'outbound_weight']
        self._cargo_footer = TreeviewTotalFooter(
            frame, self.tree_cargo_overview, summable,
            column_display_names={c[0]: c[1] for c in CARGO_OVERVIEW_COLUMNS}
        )
        self._cargo_footer.pack(fill=X)
        self._refresh_cargo_overview()

    def _sort_cargo_treeview(self, col: str) -> None:
        """총괄 화물 트리 헤더 클릭 시 오름차순/내림차순 정렬"""
        tree = self.tree_cargo_overview
        if self._cargo_sort_column == col:
            self._cargo_sort_reverse = not self._cargo_sort_reverse
        else:
            self._cargo_sort_column = col
            self._cargo_sort_reverse = False
        items = [(tree.set(item, col), item) for item in tree.get_children('')]
        numeric_cols = ['net_weight', 'current_weight', 'initial_weight', 'mxbg_pallet', 'free_time', 'row_num']
        if col in numeric_cols:
            def sort_key(x):
                try:
                    return float(str(x[0]).replace(',', ''))
                except (ValueError, TypeError):
                    return 0
        else:
            sort_key = lambda x: (x[0] or '').lower()
        items.sort(key=sort_key, reverse=self._cargo_sort_reverse)
        for idx, (_, item) in enumerate(items):
            tree.move(item, '', idx)
        arrow = " ▼" if self._cargo_sort_reverse else " ▲"
        for c_id, c_label, _, _, _ in CARGO_OVERVIEW_COLUMNS:
            tree.heading(c_id, text=f"{c_label}{arrow}" if c_id == col else c_label)

    def _refresh_cargo_overview(self) -> None:
        """총괄 화물 리스트 새로고침 — 상태별 해당 화물만"""
        if not getattr(self, 'tree_cargo_overview', None):
            return
        for item in self.tree_cargo_overview.get_children(''):
            self.tree_cargo_overview.delete(item)
        raw = (self._cargo_status_var.get() or '').strip()
        status_filter = None
        for label, db_val in STATUS_FILTER_MAP.items():
            if label in raw or (db_val and db_val in raw):
                status_filter = db_val
                break
        try:
            rows = self.engine.get_cargo_overview_lots(status_filter)
        except Exception as e:
            logger.debug(f"총괄 화물 조회: {e}")
            rows = []
        # 상태별 개수로 콤보 values 갱신
        try:
            counts = self.engine.get_cargo_overview_counts()
            cnt_total = counts.get('total', 0)
            cnt_avail = counts.get('AVAILABLE', 0)
            cnt_reserved = counts.get('RESERVED', 0)
            cnt_picked = counts.get('PICKED', 0)
            cnt_sold = counts.get('SOLD', 0)
        except Exception:
            cnt_total = cnt_avail = cnt_reserved = cnt_picked = cnt_sold = 0
        self._cargo_status_combo['values'] = [
            f"전체 ({cnt_total})", f"판매가능 ({cnt_avail})", f"판매배정 ({cnt_reserved})",
            f"판매화물 결정 ({cnt_picked})", f"출고 ({cnt_sold})",
        ]
        # 행 채우기 (재고 탭과 동일 포맷)
        for row_num, item in enumerate(rows, 1):
            lot_no = str(item.get('lot_no', ''))
            status = item.get('status', 'AVAILABLE')
            vals = []
            for col_id, _, _, _, _ in CARGO_OVERVIEW_COLUMNS:
                if col_id == 'row_num':
                    vals.append(str(row_num))
                elif col_id == 'outbound_weight':
                    try:
                        iw = float(item.get('initial_weight', 0) or 0)
                        cw = float(item.get('current_weight', 0) or 0)
                        ow = iw - cw
                        vals.append(f"{ow:,.0f}" if ow > 0 else '0')
                    except (ValueError, TypeError):
                        vals.append('0')
                elif col_id == 'avail_bags':
                    try:
                        tb = self.engine.db.fetchone(
                            "SELECT COUNT(*) as cnt FROM inventory_tonbag WHERE lot_no = ? AND status = 'AVAILABLE' AND COALESCE(is_sample,0) = 0",
                            (lot_no,))
                        cnt = tb.get('cnt', 0) if isinstance(tb, dict) else (tb[0] if tb else 0)
                        vals.append(str(cnt))
                    except (ValueError, TypeError, KeyError):
                        vals.append('')
                elif col_id == 'status':
                    vals.append(get_status_display(status) or status)
                elif col_id in ('net_weight', 'current_weight', 'initial_weight'):
                    v = item.get(col_id, 0)
                    try:
                        vals.append(f"{float(v):,.0f}" if v else '0')
                    except (ValueError, TypeError):
                        vals.append(str(v) if v else '0')
                elif col_id in ('mxbg_pallet', 'free_time'):
                    v = item.get(col_id, '')
                    try:
                        vals.append(f"{int(float(v)):,}" if v else '')
                    except (ValueError, TypeError):
                        vals.append(str(v) if v else '')
                else:
                    v = item.get(col_id, '')
                    vals.append(str(v) if v is not None else '')
            tag = status.lower() if status in ('AVAILABLE', 'PICKED', 'RESERVED', 'SHIPPED', 'DEPLETED') else ''
            row_idx = len(self.tree_cargo_overview.get_children(''))
            tags = [tag] if tag else []
            if row_idx % 2 == 1 and not tag:
                tags.append('stripe')
            self.tree_cargo_overview.insert('', 'end', values=vals, tags=tuple(tags))
        _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        ThemeColors.configure_tags(self.tree_cargo_overview, _is_dark)
        if hasattr(self, '_cargo_footer') and self._cargo_footer:
            self._cargo_footer.update_totals()
