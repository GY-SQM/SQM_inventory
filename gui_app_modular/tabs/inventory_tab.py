# -*- coding: utf-8 -*-
"""
SQM v3.9.1 — 재고 현황 탭 (18열 + 체크박스 열선택)
===================================================
- 18열 전체 표시 (inventory 테이블 매핑)
- ⚙️ 열 선택 체크박스 팝업
- 검색 입력박스 + 상태 필터 유지
- 선택출고/상세보기/선택정보 삭제

★ v5.5.2 UI 기준: 톤백 리스트(tonbag_tab.py)는 이 탭과 동일한 구도로 유지.
  필터/표시 컬럼/버튼/통계 바 순서·스타일을 바꿀 때는 tonbag_tab도 함께 수정할 것.
"""

import sqlite3
import tkinter as tk
from tkinter import ttk
from ..utils.ui_constants import ThemeColors, Spacing, DialogSize, center_dialog, apply_modal_window_options, get_status_display
from ..utils.constants import BOTH, YES, X, Y, LEFT, RIGHT, VERTICAL
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 19열 정의: (컬럼ID, 표시명, 기본폭, 정렬, 기본표시여부)
# 기본 전부 표시 — 필요 시 "표시 컬럼" 체크로 숨김
# ═══════════════════════════════════════════════════════════════
INVENTORY_COLUMNS = [
    ('row_num',            'No.',            50, 'center', True),   #  1. 순번
    ('lot_no',             'LOT NO',        120, 'center', True), #  2
    ('sap_no',             'SAP NO',        120, 'center', True),   #  3
    ('bl_no',              'BL NO',         140, 'center', True),    #  4
    ('product',            'PRODUCT',       160, 'center', True),   #  5
    ('status',             'STATUS',         90, 'center', True),   #  6
    ('current_weight',     'Balance(Kg)',    100, 'e',      True),   #  7
    ('net_weight',         'NET(Kg)',        100, 'e',      True),   #  8
    ('container_no',       'CONTAINER',     130, 'center', True),
    ('mxbg_pallet',        'MXBG',           70, 'center', True),
    ('avail_bags',         'Avail',          60, 'center', True),
    ('salar_invoice_no',   'INVOICE NO',    100, 'center', True),
    ('ship_date',          'SHIP DATE',      95, 'center', True),
    ('arrival_date',       'ARRIVAL',        95, 'center', True),
    ('con_return',         'CON RETURN',     95, 'center', True),
    ('free_time',          'FREE TIME',      80, 'center', True),
    ('warehouse',          'WH',             80, 'center', True),
    ('customs',            'CUSTOMS',        90, 'center', True),
    ('initial_weight',     'Inbound(Kg)',    100, 'e',      True),
    ('outbound_weight',    'Outbound(Kg)',   100, 'e',      True),
]


class InventoryTabMixin:
    """
    재고 현황 탭 Mixin (v3.8.4: 18열)
    """

    def _setup_inventory_tab(self) -> None:
        """재고 현황 탭 설정"""
        from ..utils.constants import ttk, tk, VERTICAL, BOTH, YES, LEFT, RIGHT, X, Y

        _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        _inv_bg = ThemeColors.get('bg_secondary', _is_dark)

        # v7.0: 판매가능 탭 제목
        _title_frame = ttk.Frame(self.tab_inventory)
        _title_frame.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))
        ttk.Label(_title_frame, text="판매가능 LOT 리스트", style='Subtitle.TLabel' if hasattr(ttk.Style(), 'configure') else None).pack(side=LEFT)

        # LOT 리스트 / 톤백 리스트 전환 (v7.0: 재고 리스트 → LOT 리스트 명칭)
        self._inv_view_switch_var = tk.StringVar(value='recovery')
        self._inv_show_all_tonbags = False  # v7.0: [전체 톤백 펼치기] 시 True
        inv_switch_frame = ttk.Frame(self.tab_inventory)
        inv_switch_frame.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))
        ttk.Radiobutton(
            inv_switch_frame, text="📦 LOT 리스트", variable=self._inv_view_switch_var, value='recovery',
            command=self._on_inv_view_switch
        ).pack(side=LEFT, padx=Spacing.XS)
        ttk.Radiobutton(
            inv_switch_frame, text="🎒 톤백 리스트", variable=self._inv_view_switch_var, value='tonbag',
            command=self._on_inv_view_switch
        ).pack(side=LEFT, padx=Spacing.XS)

        # 재고 뷰 컨테이너 (필터/토글/버튼/스플릿 패널)
        self._inv_recovery_container = ttk.Frame(self.tab_inventory)
        self._inv_recovery_container.pack(fill=BOTH, expand=YES)

        # 열 표시 상태 딕셔너리
        self._inv_col_visible = {}
        for col_id, _, _, _, default_visible in INVENTORY_COLUMNS:
            self._inv_col_visible[col_id] = default_visible

        # v3.8.4: 검색 바 삭제 → 검색은 메뉴바 [🔍검색] 팝업으로 이동
        # 검색 관련 변수 초기화 (팝업에서 사용)
        self._inv_search_combos = {}
        self._date_from_var = tk.StringVar()
        self._date_to_var = tk.StringVar()
        self.status_var = tk.StringVar(value="전체")
        self.search_var = tk.StringVar()

        # v3.8.9: LOT/톤백 라디오버튼 삭제 (톤백 상세는 톤백리스트 탭에서 관리)
        self._inv_view_mode = tk.StringVar(value='lot')  # 호환성 유지

        # ═══════════════════════════════════════════════════════
        # v4.0.6: 헤더 필터 바
        # ═══════════════════════════════════════════════════════
        from ..utils.tree_enhancements import HeaderFilterBar, apply_striped_rows, TreeviewTotalFooter
        
        _is_dark_filter = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        inv_filter_cols = [
            ('lot_no',       'LOT NO',     120),
            ('sap_no',       'SAP NO',     120),
            ('bl_no',        'BL NO',      140),
            ('container_no', 'CONTAINER',  130),
            ('product',      'PRODUCT',    160),
            ('status',       'STATUS',      90),
        ]
        self._inv_filter_bar = HeaderFilterBar(
            self._inv_recovery_container, None, inv_filter_cols,
            on_filter=self._on_inv_filter_apply,
            is_dark=_is_dark_filter,
            date_from_var=self._date_from_var,
            date_to_var=self._date_to_var,
            container_suffix_var=getattr(self, '_container_suffix_var', None),
            on_container_suffix_toggle=getattr(self, '_on_container_suffix_toggle', None),
        )
        self._inv_filter_bar.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))

        # v5.0.2: 컬럼 토글 바 (v8.7.0: 전체 19열 + 기본표시여부 반영)
        try:
            from ..utils.column_toggle import ColumnToggleBar
            toggleable_cols = [(c[0], c[1], c[4]) for c in INVENTORY_COLUMNS]
            self._inv_toggle_bar = ColumnToggleBar(
                self._inv_recovery_container,
                None,  # Treeview는 나중에 연결
                toggleable_cols,
                is_dark=_is_dark_filter
            )
            self._inv_toggle_bar.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))
        except (ImportError, Exception) as e:
            logger.debug(f"컬럼 토글바 생성 실패: {e}")
            self._inv_toggle_bar = None
        
        # 재고 탭 Excel 내보내기 + v7.0 2단계: [전체 톤백 펼치기] 버튼
        try:
            from ..utils.ui_constants import apply_tooltip
            inv_btn_frame = ttk.Frame(self._inv_recovery_container)
            inv_btn_frame.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))
            btn_inv_export = ttk.Button(
                inv_btn_frame, text="📥 Excel 내보내기",
                command=lambda: self._on_export_click(option=3)
            )
            btn_inv_export.pack(side=LEFT, padx=Spacing.XS)
            apply_tooltip(btn_inv_export, 'LOT 리스트를 Excel(루비리 양식) 파일로 내보내기')
            btn_show_all_tb = ttk.Button(
                inv_btn_frame, text="📋 전체 톤백 펼치기",
                command=self._on_show_all_tonbags
            )
            btn_show_all_tb.pack(side=RIGHT, padx=Spacing.XS)
            apply_tooltip(btn_show_all_tb, '판매가능 상태 톤백 전체를 한 번에 표시. [← LOT 리스트로]로 복귀.')
        except Exception as _e:
            logger.debug(f"재고 Excel 버튼 생성 실패: {_e}")

        # ═══════════════════════════════════════════════════════
        # v5.9.7: 스플릿 패널 (마스터-상세) — 재고 리스트 + 톤백 상세
        # ═══════════════════════════════════════════════════════
        from ..utils.split_panel import MasterDetailSplitPanel
        self._inv_split_panel = MasterDetailSplitPanel(
            self._inv_recovery_container,
            detail_title="🎒 톤백 상세 (선택 LOT)",
            master_weight=3,
            detail_weight=1
        )
        self._inv_split_panel.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)

        # 마스터 영역: 트리뷰
        tree_frame = ttk.Frame(self._inv_split_panel.get_master_container())
        tree_frame.pack(fill=BOTH, expand=YES)
        self._inv_tree_frame = tree_frame

        # 모든 18열로 생성
        all_col_ids = [c[0] for c in INVENTORY_COLUMNS]
        
        # v3.8.9: 트리뷰 스타일 — 테마 인식 (글자 흐림 수정) | v5.7.5: 가독성 위해 폰트 14로 확대
        import tkinter.font as tkfont
        _style = ttk.Style()
        _inv_font = tkfont.Font(family='맑은 고딕', size=11)
        _inv_head_font = tkfont.Font(family='맑은 고딕', size=11, weight='bold')
        _row_h = _inv_font.metrics('linespace') + 6
        
        _is_dark_tv = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        _tv_bg = ThemeColors.get('bg_card', _is_dark_tv)
        _tv_fg = ThemeColors.get('text_primary', _is_dark_tv)
        _tv_field = _tv_bg
        _tv_head_bg = ThemeColors.get('bg_secondary', _is_dark_tv)
        _tv_head_fg = ThemeColors.get('text_primary', _is_dark_tv)
        
        _style.configure('Inv.Treeview', 
                         font=_inv_font,
                         rowheight=_row_h,
                         background=_tv_bg,
                         foreground=_tv_fg,
                         fieldbackground=_tv_field)
        _style.configure('Inv.Treeview.Heading',
                         font=_inv_head_font,
                         background=_tv_head_bg,
                         foreground=_tv_head_fg)
        
        # v6.1.1: 선택/비선택 행 foreground 명시 (테마 가시성)
        _style.map('Inv.Treeview',
                   background=[('selected', ThemeColors.get('tree_select_bg', _is_dark_tv))],
                   foreground=[
                       ('selected', ThemeColors.get('tree_select_fg', _is_dark_tv)),
                       ('!selected', _tv_fg),
                   ])
        
        self.tree_inventory = ttk.Treeview(
            tree_frame, columns=all_col_ids, show="headings", height=20,
            selectmode='extended', style='Inv.Treeview'
        )

        self._sort_column = None
        self._sort_reverse = False

        # 헤더 + 컬럼 설정
        for col_id, label, width, anchor, visible in INVENTORY_COLUMNS:
            self.tree_inventory.heading(
                col_id, text=label,
                command=lambda c=col_id: self._sort_treeview(self.tree_inventory, c)
            )
            if visible:
                self.tree_inventory.column(col_id, width=width, anchor=anchor, stretch=True)
            else:
                self.tree_inventory.column(col_id, width=0, minwidth=0, stretch=False)
        
        # v4.2.2: 테이블 스타일 적용 (v5.6.9: 다크 테마 시 글씨 가시성)
        try:
            from ..utils.table_styler import apply_table_style
            apply_table_style(
                self.tree_inventory,
                grid_lines=True,
                striped_rows=True,
                row_height='normal',
                is_dark=_is_dark_tv
            )
        except (ImportError, Exception) as e:
            logger.debug(f"테이블 스타일 적용 실패: {e}")

        # 스크롤바
        v_scroll = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree_inventory.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree_inventory.xview)
        self.tree_inventory.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree_inventory.pack(side=LEFT, fill=BOTH, expand=YES)
        v_scroll.pack(side=RIGHT, fill=Y)
        h_scroll.pack(side='bottom', fill=X)

        # 하단 총합 (합계 가능한 숫자 컬럼만)
        inv_sum_cols = ['current_weight', 'net_weight', 'initial_weight', 'outbound_weight', 'mxbg_pallet']
        self._inv_total_footer = TreeviewTotalFooter(
            tree_frame, self.tree_inventory, inv_sum_cols,
            column_display_names={'current_weight': 'Balance(Kg)', 'net_weight': 'NET(Kg)',
                                 'initial_weight': 'Inbound(Kg)', 'outbound_weight': 'Outbound(Kg)', 'mxbg_pallet': 'MXBG'}
        )
        self._inv_total_footer.pack(fill=X, pady=(2, 0))

        # v5.7.5: 하단 요약바 제거 (LOT/톤백/입고/잔량/출고/가용/소진/출고율)

        # 테마 색상
        self._apply_inventory_theme_colors()

        # v4.0.6: 필터바에 treeview 연결
        self._inv_filter_bar.tree = self.tree_inventory
        
        # v5.0.2: 컬럼 토글바에 treeview 연결 (v8.7.0: 초기 displaycolumns 적용)
        if hasattr(self, '_inv_toggle_bar') and self._inv_toggle_bar:
            self._inv_toggle_bar.tree = self.tree_inventory
            self._apply_column_visibility()

        # v4.0.6: 하단 NET(KG) / Balance 합계 바
        # v5.6.1: FooterTotalBar 제거 — stats_frame 1줄로 통합
        # self._inv_footer = FooterTotalBar(self.tab_inventory, is_dark=_is_dark_filter)
        # self._inv_footer.pack(fill=X, padx=5, pady=(0, 2))

        # 이벤트
        self.tree_inventory.bind('<Double-1>', self._on_lot_double_click)
        self.tree_inventory.bind('<<TreeviewSelect>>', self._on_inv_selection_change)
        # U5: 우클릭 컨텍스트 메뉴
        self.tree_inventory.bind('<Button-3>', self._on_inventory_right_click)

        # v5.9.7: 상세 패널 — 선택 LOT의 톤백 테이블
        self._setup_inv_tonbag_detail_panel()

        # 톤백 보기 뷰 (재고리스트 탭 안 메뉴) — 초기에는 숨김
        self._inv_tonbag_container = ttk.Frame(self.tab_inventory)
        tb_bar = ttk.Frame(self._inv_tonbag_container)
        tb_bar.pack(fill=X, padx=Spacing.XS, pady=(0, Spacing.XS))
        ttk.Button(tb_bar, text="← LOT 리스트로", command=self._on_back_to_lot_list).pack(side=LEFT, padx=Spacing.XS)
        ttk.Button(tb_bar, text="🔄 새로고침", command=self._refresh_inv_tonbag_view).pack(side=LEFT, padx=Spacing.XS)
        tb_tree_frame = ttk.Frame(self._inv_tonbag_container)
        tb_tree_frame.pack(fill=BOTH, expand=YES)
        _tb_cols = ('row_num', 'lot_no', 'tonbag_no', 'status', 'weight', 'uid', 'location')
        self._inv_tonbag_tree = ttk.Treeview(tb_tree_frame, columns=_tb_cols, show='headings', height=22, selectmode='extended')
        for cid, txt, w in [
            ('row_num', 'No.', 50), ('lot_no', 'LOT NO', 120), ('tonbag_no', 'TONBAG NO', 90),
            ('status', 'STATUS', 90), ('weight', 'Balance(Kg)', 100), ('uid', 'UID', 120), ('location', 'LOCATION', 100),
        ]:
            self._inv_tonbag_tree.heading(cid, text=txt)
            self._inv_tonbag_tree.column(cid, width=w)
        _sb = ttk.Scrollbar(tb_tree_frame, orient=VERTICAL, command=self._inv_tonbag_tree.yview)
        _sb2 = ttk.Scrollbar(tb_tree_frame, orient='horizontal', command=self._inv_tonbag_tree.xview)
        self._inv_tonbag_tree.configure(yscrollcommand=_sb.set, xscrollcommand=_sb2.set)
        self._inv_tonbag_tree.pack(side=LEFT, fill=BOTH, expand=YES)
        _sb.pack(side='right', fill='y')
        _sb2.pack(side='bottom', fill=X)
        self._inv_tonbag_footer = TreeviewTotalFooter(
            tb_tree_frame, self._inv_tonbag_tree, ['weight'],
            column_display_names={'weight': 'Balance(Kg)'}
        )
        self._inv_tonbag_footer.pack(fill=X, pady=(2, 0))

    def _on_inv_view_switch(self) -> None:
        """재고 보기 / 톤백 보기 전환"""
        mode = getattr(self, '_inv_view_switch_var', None) and self._inv_view_switch_var.get() or 'recovery'
        if mode == 'tonbag':
            self._inv_show_all_tonbags = False
            self._inv_recovery_container.pack_forget()
            self._inv_tonbag_container.pack(fill=tk.BOTH, expand=True, padx=Spacing.XS, pady=Spacing.XS)
            self._refresh_inv_tonbag_view()
        else:
            self._inv_tonbag_container.pack_forget()
            self._inv_recovery_container.pack(fill=tk.BOTH, expand=True)

    def _on_show_all_tonbags(self) -> None:
        """v7.0 2단계: [전체 톤백 펼치기] — 판매가능 톤백 전체 표시, LOT 리스트 숨김"""
        self._inv_show_all_tonbags = True
        self._inv_recovery_container.pack_forget()
        self._inv_tonbag_container.pack(fill=tk.BOTH, expand=True, padx=Spacing.XS, pady=Spacing.XS)
        self._refresh_inv_tonbag_view()

    def _on_back_to_lot_list(self) -> None:
        """v7.0 2단계: [← LOT 리스트로] — 톤백 전체 뷰에서 LOT 리스트로 복귀"""
        self._inv_show_all_tonbags = False
        self._inv_tonbag_container.pack_forget()
        self._inv_recovery_container.pack(fill=tk.BOTH, expand=True)
        if hasattr(self, '_deferred_refresh_main_tabs'):
            self._deferred_refresh_main_tabs(delay_ms=50)
        elif hasattr(self, '_refresh_main_tabs'):
            self._refresh_main_tabs()
        else:
            self._refresh_inventory()

    def _refresh_inv_tonbag_view(self) -> None:
        """재고리스트 탭 내 톤백 보기 트리 새로고침. v7.0: [전체 톤백 펼치기] 시 판매가능 전부 조회."""
        if not hasattr(self, '_inv_tonbag_tree'):
            return
        for c in self._inv_tonbag_tree.get_children():
            self._inv_tonbag_tree.delete(c)
        try:
            if getattr(self, '_inv_show_all_tonbags', False):
                # v7.0 2단계: 전체 톤백 펼치기 — inventory_tonbag WHERE status='AVAILABLE' (샘플 제외)
                rows = self.engine.db.fetchall(
                    """SELECT lot_no, sub_lt, tonbag_no, weight, location, inbound_date, bl_no
                       FROM inventory_tonbag WHERE status = 'AVAILABLE' AND COALESCE(is_sample, 0) = 0
                       ORDER BY lot_no, sub_lt"""
                ) if hasattr(self.engine, 'db') and self.engine.db else []
                for idx, tb in enumerate(rows or [], 1):
                    lot_no = str(tb.get('lot_no', ''))
                    sub_lt = tb.get('sub_lt', '')
                    tonbag_no = tb.get('tonbag_no') or (f"{sub_lt:>3}" if sub_lt != '' else '-')
                    w = float(tb.get('weight', 0) or 0)
                    loc = str(tb.get('location', '') or '')
                    inbound = str(tb.get('inbound_date', '') or '')
                    bl = str(tb.get('bl_no', '') or '')
                    st = inbound or '-'
                    uid = bl
                    self._inv_tonbag_tree.insert('', 'end', values=(idx, lot_no, tonbag_no, st, f"{w:,.0f}", uid, loc))
            else:
                tonbags = self.engine.get_tonbags_with_inventory() if hasattr(self.engine, 'get_tonbags_with_inventory') else []
                if not tonbags and hasattr(self.engine, 'get_tonbags'):
                    tonbags = self.engine.get_tonbags() or []
                for idx, tb in enumerate(tonbags, 1):
                    lot_no = str(tb.get('lot_no', ''))
                    sub_lt = tb.get('sub_lt', '')
                    tonbag_no = tb.get('tonbag_no') or (f"{sub_lt:>3}" if sub_lt != '' else '-')
                    _s = tb.get('tonbag_status') or tb.get('status', 'AVAILABLE')
                    # 판매가능 탭의 톤백 리스트는 AVAILABLE만 표시 (샘플 제외)
                    if _s != 'AVAILABLE':
                        continue
                    if tb.get('is_sample', 0):
                        continue
                    _disp = get_status_display(_s) or _s
                    st = ('✅ ' if _s == 'AVAILABLE' else ('🔒 ' if _s == 'RESERVED' else '')) + _disp
                    w = float(tb.get('weight', tb.get('current_weight', 0)) or 0)
                    uid = str(tb.get('tonbag_uid', ''))
                    loc = str(tb.get('location', ''))
                    self._inv_tonbag_tree.insert('', 'end', values=(idx, lot_no, tonbag_no, st, f"{w:,.0f}", uid, loc))
            if hasattr(self, '_inv_tonbag_footer') and self._inv_tonbag_footer:
                self._inv_tonbag_footer.update_totals()
        except Exception as e:
            logger.debug(f"톤백 보기 새로고침: {e}")

    def _setup_inv_tonbag_detail_panel(self) -> None:
        """재고 탭 상세 패널: 톤백 테이블"""
        from ..utils.constants import ttk, VERTICAL, BOTH, LEFT
        detail_container = self._inv_split_panel.get_detail_container()
        cols = ('sub_lt', 'weight', 'status', 'location', 'picked_to', 'outbound_date')
        self._inv_tonbag_detail_tree = ttk.Treeview(
            detail_container, columns=cols, show='headings', height=8
        )
        for cid, txt, w in [
            ('sub_lt', '톤백#', 60), ('weight', '중량(kg)', 90),
            ('status', '상태', 90), ('location', '위치', 80),
            ('picked_to', '출고처', 120), ('outbound_date', '출고일', 100)
        ]:
            self._inv_tonbag_detail_tree.heading(cid, text=txt)
            self._inv_tonbag_detail_tree.column(cid, width=w)
        sb = ttk.Scrollbar(detail_container, orient=VERTICAL, command=self._inv_tonbag_detail_tree.yview)
        sb_x = ttk.Scrollbar(detail_container, orient='horizontal', command=self._inv_tonbag_detail_tree.xview)
        self._inv_tonbag_detail_tree.configure(yscrollcommand=sb.set, xscrollcommand=sb_x.set)
        self._inv_tonbag_detail_tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb.pack(side='right', fill='y')
        sb_x.pack(side='bottom', fill='x')

    def _on_inv_selection_change(self, event) -> None:
        """재고 선택 변경 → 톤백 상세 패널 갱신"""
        sel = self.tree_inventory.selection()
        if not sel or not hasattr(self, '_inv_tonbag_detail_tree'):
            return
        item = self.tree_inventory.item(sel[0])
        vals = item.get('values', [])
        if len(vals) < 2:
            return
        lot_no = str(vals[1]).strip()
        if not lot_no:
            return
        for c in self._inv_tonbag_detail_tree.get_children():
            self._inv_tonbag_detail_tree.delete(c)
        self._inv_split_panel.set_detail_title(f"🎒 톤백 상세 — {lot_no}")
        try:
            tonbags = self.engine.db.fetchall(
                """SELECT sub_lt, weight, status, location, picked_to, outbound_date
                   FROM inventory_tonbag WHERE lot_no = ? ORDER BY sub_lt""",
                (lot_no,)
            )
            for tb in (tonbags or []):
                _s = tb.get('status', 'AVAILABLE')
                _disp = get_status_display(_s) or _s
                st = ('✅ ' if _s == 'AVAILABLE' else ('🔒 ' if _s == 'RESERVED' else '')) + _disp
                self._inv_tonbag_detail_tree.insert('', 'end', values=(
                    tb.get('sub_lt'), f"{(tb.get('weight') or 0):,.0f}",
                    st, tb.get('location') or '', tb.get('picked_to') or '',
                    str(tb.get('outbound_date') or '')[:10]
                ))
        except Exception as e:
            logger.debug(f"톤백 상세 로드: {e}")

    # ═══════════════════════════════════════════════════════
    # 열 선택 체크박스 팝업
    # ═══════════════════════════════════════════════════════

    def _apply_column_visibility(self) -> None:
        """
        v5.0.2: 열 표시/숨김 적용 (개선)
        
        width=0으로만 하면 헤더는 보이는 문제가 있어서
        displaycolumns를 사용하여 완전히 숨김
        """
        try:
            # 표시할 컬럼만 추출
            visible_columns = []
            for col_id, label, width, anchor, _ in INVENTORY_COLUMNS:
                if self._inv_col_visible.get(col_id, True):
                    visible_columns.append(col_id)
            
            # displaycolumns 설정으로 컬럼 표시/숨김
            self.tree_inventory.configure(displaycolumns=visible_columns)
            
            # 표시되는 컬럼의 너비 재설정
            for col_id, label, width, anchor, _ in INVENTORY_COLUMNS:
                if col_id in visible_columns:
                    self.tree_inventory.column(col_id, width=width, minwidth=40, stretch=True)
            
            logger.debug(f"✅ 컬럼 표시 적용: {len(visible_columns)}개 표시")
            
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"컬럼 표시/숨김 실패: {e}")

    # ═══════════════════════════════════════════════════════
    # 테마 / 검색 / 필터
    # ═══════════════════════════════════════════════════════


    def _execute_inv_combo_search(self) -> None:
        """콤보 검색 실행"""
        self._refresh_inventory()

    def _reset_inv_combo_search(self) -> None:
        """콤보 검색 초기화"""
        for field, (var, cb) in self._inv_search_combos.items():
            var.set('전체')
        if hasattr(self, '_date_from_var'):
            self._date_from_var.set('')
        if hasattr(self, '_date_to_var'):
            self._date_to_var.set('')
        self._refresh_inventory()

    # ═══════════════════════════════════════════════════════
    # U5: 우클릭 컨텍스트 메뉴
    # ═══════════════════════════════════════════════════════
    
    def _on_inventory_right_click(self, event) -> None:
        """재고리스트 우클릭 컨텍스트 메뉴"""
        import tkinter as tk
        
        item_id = self.tree_inventory.identify_row(event.y)
        if not item_id:
            return
        
        self.tree_inventory.selection_set(item_id)
        values = self.tree_inventory.item(item_id)['values']
        if not values:
            return
        
        lot_no = str(values[0]).strip()
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"📋 LOT 복사: {lot_no}", 
                        command=lambda: self._copy_to_clipboard(lot_no))
        menu.add_separator()
        menu.add_command(label="🔍 톤백 상세 보기", 
                        command=lambda: self._show_lot_tonbag_detail(lot_no))
        menu.add_command(label="📤 빠른 출고", 
                        command=lambda: self._quick_outbound_from_context(lot_no))
        menu.add_command(label="🔄 반품 (재입고)", 
                        command=lambda: self._return_from_context(lot_no))
        menu.add_separator()
        menu.add_command(label="📊 LOT 이력 조회", 
                        command=lambda: self._show_lot_history(lot_no))
        menu.add_separator()
        menu.add_command(label="📝 전체 행 복사", 
                        command=lambda: self._copy_row_to_clipboard(values))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def _copy_to_clipboard(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._log(f"📋 클립보드 복사: {text}")
    
    def _copy_row_to_clipboard(self, values) -> None:
        text = '\t'.join(str(v) for v in values)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._log("📋 행 데이터 클립보드 복사")
    
    def _show_lot_tonbag_detail(self, lot_no: str) -> None:
        """LOT 톤백 상세 팝업"""
        import tkinter as tk
        from tkinter import ttk as _ttk
        
        tonbags = self.engine.db.fetchall(
            """SELECT sub_lt, weight, status, location, picked_to, 
                      outbound_date, updated_at
               FROM inventory_tonbag WHERE lot_no = ? ORDER BY sub_lt""",
            (lot_no,)
        )
        
        dlg = tk.Toplevel(self.root)
        dlg.title(f"🎒 톤백 상세 — {lot_no}")
        dlg.geometry(DialogSize.get_geometry(self.root, 'medium'))
        apply_modal_window_options(dlg)
        dlg.transient(self.root)
        center_dialog(dlg, self.root)
        
        cols = ('sub_lt', 'weight', 'status', 'location', 'picked_to', 'outbound_date')
        tree = _ttk.Treeview(dlg, columns=cols, show='headings', height=15)
        
        for col, text, w in [
            ('sub_lt', '톤백#', 60), ('weight', '중량(kg)', 100),
            ('status', '상태', 100), ('location', '위치', 80),
            ('picked_to', '출고처', 120), ('outbound_date', '출고일', 120)
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=w, anchor='center')
        
        for i, tb in enumerate(tonbags):
            _s = tb.get('status', 'AVAILABLE')
            status_text = get_status_display(_s) or _s
            tags = ('stripe',) if i % 2 == 1 else ()
            tree.insert('', 'end', values=(
                tb['sub_lt'], f"{(tb['weight'] or 0):,.0f}",
                status_text, tb['location'] or '',
                tb['picked_to'] or '', str(tb['outbound_date'] or '')[:10]
            ), tags=tags)
        
        _stripe_bg = ThemeColors.get('tree_stripe', getattr(self, '_is_dark', False))
        tree.tag_configure('stripe', background=_stripe_bg)
        
        scroll = _ttk.Scrollbar(dlg, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side='left', fill='both', expand=True, padx=Spacing.XS, pady=Spacing.XS)
        scroll.pack(side='right', fill='y', pady=Spacing.XS)
        
        total = sum((tb['weight'] or 0) for tb in tonbags)
        avail = sum((tb['weight'] or 0) for tb in tonbags if tb['status'] == 'AVAILABLE')
        _ttk.Label(dlg, text=f"합계: {len(tonbags)}개 / {total:,.0f}kg (판매가능: {avail:,.0f}kg)",
                  font=('', 13, 'bold')).pack(side='bottom', pady=Spacing.XS)
    
    def _quick_outbound_from_context(self, lot_no: str) -> None:
        if hasattr(self, '_on_simple_outbound'):
            self._on_simple_outbound()
    
    def _return_from_context(self, lot_no: str) -> None:
        if hasattr(self, '_on_return_process'):
            self._on_return_process()
    
    def _show_lot_history(self, lot_no: str) -> None:
        """LOT 이력 조회"""
        import tkinter as tk
        from tkinter import ttk as _ttk
        
        # customer, movement_date 컬럼 없어도 동작 (base 스키마: movement_type, qty_kg, created_at)
        movements = self.engine.db.fetchall(
            """SELECT movement_type, qty_kg,
                   '' AS customer, created_at AS movement_date, created_at
               FROM stock_movement WHERE lot_no = ? ORDER BY created_at DESC""",
            (lot_no,)
        )
        
        dlg = tk.Toplevel(self.root)
        dlg.title(f"📊 LOT 이력 — {lot_no}")
        dlg.geometry(DialogSize.get_geometry(self.root, 'medium'))
        apply_modal_window_options(dlg)
        dlg.transient(self.root)
        center_dialog(dlg, self.root)
        
        cols = ('type', 'qty', 'customer', 'date', 'created')
        tree = _ttk.Treeview(dlg, columns=cols, show='headings', height=12)
        
        type_icons = {
            'OUTBOUND': '📤 출고', 'INBOUND': '📥 입고',
            'CANCEL_OUTBOUND': '↩️ 취소', 'RETURN': '🔄 반품'
        }
        
        for col, text, w in [
            ('type', '유형', 100), ('qty', '수량(kg)', 100),
            ('customer', '고객', 120), ('date', '날짜', 100), ('created', '등록일', 120)
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=w, anchor='e' if col == 'qty' else 'center')
        
        for i, mv in enumerate(movements):
            tree.insert('', 'end', values=(
                type_icons.get(mv['movement_type'], mv['movement_type']),
                f"{(mv['qty_kg'] or 0):,.0f}",
                mv['customer'] or '',
                str(mv['movement_date'] or '')[:10],
                str(mv['created_at'] or '')[:16]
            ), tags=('stripe',) if i % 2 == 1 else ())
        
        _stripe_bg = ThemeColors.get('tree_stripe', getattr(self, '_is_dark', False))
        tree.tag_configure('stripe', background=_stripe_bg)
        tree.pack(fill='both', expand=True, padx=Spacing.XS, pady=Spacing.XS)
        
        if not movements:
            _ttk.Label(dlg, text="이력이 없습니다.", foreground='gray').pack(pady=Spacing.LG)

    def _apply_inventory_theme_colors(self) -> None:
        """테마 색상 적용 (v5.6.9: Grid 스타일 foreground 갱신 — 다크에서 글씨 보이게)"""
        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        ThemeColors.configure_tags(self.tree_inventory, is_dark)
        try:
            from ..utils.table_styler import TableStyler
            TableStyler.update_grid_style_for_theme(self.tree_inventory, is_dark)
        except (ImportError, Exception) as e:
            logger.debug(f"Grid 스타일 테마 갱신 무시: {e}")

    def _on_search(self, *args) -> None:
        self._refresh_inventory()

    def _on_status_filter(self, event) -> None:
        self._refresh_inventory()

    def _convert_preview_to_inventory_items(self, preview_data: list) -> list:
        """원스톱 파싱 미리보기 데이터를 재고 탭 형식으로 변환 (실시간 표시용)"""
        result = []
        for row in preview_data:
            try:
                nw = row.get('net_weight', '') or '0'
                if isinstance(nw, str):
                    nw = nw.replace(',', '').strip()
                net = float(nw) if nw else 0.0
            except (ValueError, TypeError):
                net = 0.0
            mxbg = row.get('mxbg_pallet', '10') or '10'
            if isinstance(mxbg, str) and mxbg.isdigit():
                mxbg = int(mxbg)
            else:
                try:
                    mxbg = int(float(mxbg))
                except (ValueError, TypeError):
                    mxbg = 10
            result.append({
                'lot_no': str(row.get('lot_no', '')),
                'sap_no': str(row.get('sap_no', '')),
                'bl_no': str(row.get('bl_no', '')),
                'container_no': str(row.get('container_no', '')),
                'product': str(row.get('product', '')),
                'mxbg_pallet': mxbg,
                'avail_bags': mxbg,
                'net_weight': net,
                'salar_invoice_no': str(row.get('salar_invoice_no', '')),
                'ship_date': str(row.get('ship_date', ''))[:10] if row.get('ship_date') else '',
                'arrival_date': str(row.get('arrival_date', ''))[:10] if row.get('arrival_date') else '',
                'con_return': str(row.get('con_return', ''))[:10] if row.get('con_return') else '',
                'free_time': str(row.get('free_time', '')),
                'warehouse': str(row.get('warehouse', '')),
                'status': str(row.get('status', 'AVAILABLE')),
                'customs': '',
                'initial_weight': net,
                'current_weight': net,
            })
        return result

    def _set_parsing_preview_data(self, data) -> None:
        """파싱 미리보기 데이터 설정/해제. None이면 DB 기준으로 복원."""
        self._parsing_preview_data = data
        self._refresh_inventory()

    def _reset_inventory_view_for_new_inbound(self) -> None:
        """추가 입고 시작 전 재고 탭 화면 상태를 초기화한다."""
        try:
            if hasattr(self, 'search_var'):
                self.search_var.set('')
            if hasattr(self, '_date_from_var'):
                self._date_from_var.set('')
            if hasattr(self, '_date_to_var'):
                self._date_to_var.set('')
            if hasattr(self, 'status_var'):
                self.status_var.set('전체')

            # 헤더 필터/콤보 필터 초기화
            if hasattr(self, '_inv_filter_bar') and hasattr(self._inv_filter_bar, '_reset_filters'):
                self._inv_filter_bar._reset_filters()
            elif hasattr(self, '_reset_inv_combo_search'):
                self._reset_inv_combo_search()

            # [전체 톤백 펼치기] 상태라면 LOT 리스트 화면으로 복귀
            if getattr(self, '_inv_show_all_tonbags', False):
                self._on_back_to_lot_list()

            # 선택/상세 패널 초기화
            if hasattr(self, 'tree_inventory') and self.tree_inventory.winfo_exists():
                self.tree_inventory.selection_remove(self.tree_inventory.selection())
            if hasattr(self, '_inv_tonbag_detail_tree') and self._inv_tonbag_detail_tree.winfo_exists():
                for iid in self._inv_tonbag_detail_tree.get_children():
                    self._inv_tonbag_detail_tree.delete(iid)
            if hasattr(self, '_inv_split_panel') and hasattr(self._inv_split_panel, 'set_detail_title'):
                self._inv_split_panel.set_detail_title("🎒 톤백 상세 (선택 LOT)")
        except Exception as e:
            logger.debug(f"추가 입고 전 재고 화면 초기화 무시: {e}")
        self._refresh_inventory()

    def _refresh_inventory(self) -> None:
        """재고 목록 새로고침 (18열 + 콤보 검색 + Date 기간)"""
        if not hasattr(self, 'tree_inventory'):
            return
        
        # v4.19.1: 필터 드롭다운 채우기 (추가)
        self._populate_filter_dropdowns()
        
        for item in self.tree_inventory.get_children():
            self.tree_inventory.delete(item)

        search_text = self.search_var.get().strip().lower()
        # v7.0 2단계: 판매가능 탭 전용 — status 필터 고정 (판매가능만 표시)
        status_filter_normalized = 'AVAILABLE'  # DB 값

        # 콤보 검색 조건
        combo_filters = {}
        if hasattr(self, '_inv_search_combos'):
            for field, (var, cb) in self._inv_search_combos.items():
                val = var.get()
                if val and val != '전체':
                    combo_filters[field] = val
        # v4.0.6: 헤더 필터바 조건 (status는 위에서 별도 처리하므로 제외)
        if hasattr(self, '_inv_filter_bar'):
            for k, v in self._inv_filter_bar.get_filters().items():
                if k != 'status':
                    combo_filters[k] = v
        
        # Date 기간 조건
        date_from = ''
        date_to = ''
        if hasattr(self, '_date_from_var'):
            date_from = self._date_from_var.get().strip().replace('-', '')
        if hasattr(self, '_date_to_var'):
            date_to = self._date_to_var.get().strip().replace('-', '')

        try:
            # 파싱 팝업에서 실시간 푸시된 미리보기 데이터가 있으면 재고 리스트에 표시
            preview = getattr(self, '_parsing_preview_data', None)
            if preview is not None and isinstance(preview, list) and len(preview) > 0:
                inventory = self._convert_preview_to_inventory_items(preview)
                if hasattr(self, '_log'):
                    self._log(f"📋 파싱 미리보기: 재고 리스트에 {len(inventory)}건 표시 (저장 전)")
            else:
                inventory = self.engine.get_all_inventory()

            # Avail 컬럼: LOT별 판매가능 톤백 수 일괄 조회 (샘플 제외)
            # - 행별 쿼리(N+1)로 인한 성능/예외 변동을 줄이고, 기본값 0을 보장한다.
            avail_map = {}
            try:
                avail_rows = self.engine.db.fetchall(
                    "SELECT lot_no, COUNT(*) AS cnt "
                    "FROM inventory_tonbag "
                    "WHERE status = 'AVAILABLE' AND COALESCE(is_sample, 0) = 0 "
                    "GROUP BY lot_no"
                )
                avail_map = {
                    str(r.get('lot_no', '')).strip(): int(r.get('cnt', 0) or 0)
                    for r in (avail_rows or [])
                }
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
                logger.debug(f"Avail 일괄 조회 실패(기본 0 처리): {e}")
                avail_map = {}

            for item in inventory:
                lot_no = str(item.get('lot_no', '')).strip()
                product = str(item.get('product', ''))
                sap_no = str(item.get('sap_no', ''))

                # 즉시 검색 필터
                if search_text:
                    searchable = f"{lot_no} {product} {sap_no} {item.get('bl_no','')}".lower()
                    if search_text not in searchable:
                        continue

                # 상태 필터 (전체 / 판매가능 / 판매배정 / 판매화물 결정 / 출고)
                status = item.get('status', 'AVAILABLE')
                if status_filter_normalized and status != status_filter_normalized:
                    continue
                
                # 콤보 검색 필터 + 헤더 필터바
                skip = False
                for field, val in combo_filters.items():
                    item_val = str(item.get(field, ''))
                    if item_val != val:
                        skip = True
                        break
                if skip:
                    continue
                
                # Date 기간 필터 (arrival_date 기준)
                if date_from or date_to:
                    arrival = str(item.get('arrival_date', '')).replace('-', '')
                    if date_from and arrival and arrival < date_from:
                        continue
                    if date_to and arrival and arrival > date_to:
                        continue

                # v3.9.1: 18열 값 추출
                row_num = len(self.tree_inventory.get_children()) + 1
                vals = []
                for col_id, _, _, _, _ in INVENTORY_COLUMNS:
                    if col_id == 'row_num':
                        vals.append(str(row_num))
                        continue
                    elif col_id == 'outbound_weight':
                        # 출고량 = 입고 - 잔량
                        try:
                            init_w = float(item.get('initial_weight', 0) or 0)
                            curr_w = float(item.get('current_weight', 0) or 0)
                            out_w = init_w - curr_w
                            vals.append(f"{out_w:,.0f}" if out_w > 0 else '0')
                        except (ValueError, TypeError):
                            vals.append('0')
                        continue
                    elif col_id == 'customs_status':
                        vals.append(str(item.get('customs_status', '') or ''))
                        continue
                    elif col_id == 'avail_bags':
                        # Avail = 판매가능(샘플 제외) 톤백 수. 값이 없으면 0을 표시.
                        vals.append(str(avail_map.get(lot_no, 0)))
                        continue
                    
                    v = item.get(col_id, '')
                    if v is None:
                        v = ''
                    # 컨테이너 구분(-1, -2) 옵션: 꺼져 있으면 접미사 제거
                    if col_id == 'container_no' and hasattr(self, '_format_container_no'):
                        v = self._format_container_no(str(v))
                    # 숫자 포맷팅
                    if col_id in ('net_weight', 'current_weight', 'initial_weight'):
                        try:
                            v = f"{float(v):,.0f}" if v else '0'
                        except (ValueError, TypeError):
                            v = str(v)
                    elif col_id in ('mxbg_pallet', 'free_time'):
                        try:
                            v = f"{int(float(v)):,}" if v else ''
                        except (ValueError, TypeError):
                            v = str(v)
                    elif col_id == 'con_return':
                        # CON RETURN은 날짜(YYYY-MM-DD) 형식이므로 앞 10자리만
                        v = str(v)[:10] if v and str(v) not in ('None', 'nan') else ''
                        if not v:
                            # DB에 없으면 arrival_date + free_time으로 계산
                            arr = str(item.get('arrival_date', ''))[:10]
                            ft = str(item.get('free_time', ''))
                            if arr and ft and ft.isdigit():
                                try:
                                    arr_dt = datetime.strptime(arr, '%Y-%m-%d')
                                    ret_dt = arr_dt + timedelta(days=int(ft))
                                    v = ret_dt.strftime('%Y-%m-%d')
                                except (ValueError, TypeError):
                                    pass
                    # U2: 화물 상태 표시 (전체/판매가능/판매배정/판매화물 결정/출고)
                    elif col_id == 'status':
                        v = get_status_display(str(v)) or str(v)
                    else:
                        v = str(v)
                    vals.append(v)

                tag = status.lower() if status in ['AVAILABLE', 'PICKED', 'RESERVED', 'SHIPPED', 'DEPLETED'] else ''
                # U1: 교대 줄무늬 (상태색이 있으면 stripe 제외 → 상태색 우선)
                row_idx = len(self.tree_inventory.get_children())
                tags = [tag] if tag else []
                if row_idx % 2 == 1 and not tag:
                    tags.append('stripe')
                self.tree_inventory.insert('', 'end', values=vals, tags=tuple(tags))

            # ═══ v5.6.1: 상태별 행 배경+전경색 (다크테마 가시성 수정) ═══
            _dk = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
            _p = ThemeColors.get_palette(_dk)
            _stripe_bg = ThemeColors.get('tree_stripe', _dk)
            _text_color = ThemeColors.get('text_primary', _dk)

            self.tree_inventory.tag_configure('available',
                background=ThemeColors.get('available', _dk), foreground=_text_color)
            self.tree_inventory.tag_configure('picked',
                background=ThemeColors.get('picked', _dk), foreground=_text_color)
            self.tree_inventory.tag_configure('reserved',
                background=ThemeColors.get('reserved', _dk), foreground=_text_color)
            self.tree_inventory.tag_configure('shipped',
                background=ThemeColors.get('shipped', _dk), foreground=_text_color)
            self.tree_inventory.tag_configure('depleted',
                background=ThemeColors.get('bg_secondary', _dk), foreground=ThemeColors.get('text_muted', _dk))
            self.tree_inventory.tag_configure('stripe',
                background=_stripe_bg, foreground=_text_color)

            self._refresh_summary()
            if hasattr(self, '_inv_total_footer') and self._inv_total_footer:
                self._inv_total_footer.update_totals()

            # v3.9.9: 빈 상태 안내 — 비표시 (사용자 요청)
            self._hide_empty_state_hint()
            
            # v3.8.7: 재고 탭 하단 통계 갱신
            self._refresh_inv_stats()
            
            # U4: 상태바 실시간 재고 요약 갱신
            if hasattr(self, '_update_statusbar_summary'):
                self._update_statusbar_summary()
            
            # v4.2.2: 테이블 스타일 줄무늬 새로고침
            try:
                from ..utils.table_styler import TableStyler
                TableStyler.refresh_striped_rows(self.tree_inventory)
            except (ImportError, Exception) as e:
                logger.debug(f"줄무늬 새로고침 실패: {e}")
                # Fallback: 기존 방식
                try:
                    from ..utils.tree_enhancements import apply_striped_rows
                    _dk2 = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
                    apply_striped_rows(self.tree_inventory, is_dark=_dk2)
                except (ImportError, Exception) as _e2:
                    logger.debug(f"기존 방식 줄무늬도 실패: {_e2}")
            
            # v4.0.6: 필터 드롭다운 값 업데이트
            self._update_inv_filter_values(inventory)
            
            # v5.6.1: FooterTotalBar 제거 (stats_frame 1줄로 통합)
            # self._update_inv_footer()

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"재고 조회 오류: {e}")
            self._log(f"⚠️ 재고 조회 오류: {e}")
    

    def _refresh_inv_stats(self) -> None:
        """v3.8.7: 재고 탭 하단 통계. v7.0 2단계: 판매가능 탭 — 판매가능(LOT/톤백/무게)만 표시."""
        if not hasattr(self, '_inv_summary_label'):
            return
        try:
            # v7.0: 판매가능만 집계 (LOT 수, 톤백 수, 총 무게)
            stats = self.engine.db.fetchone("""
                SELECT COUNT(*) AS total_lots, COALESCE(SUM(current_weight), 0) AS total_current
                FROM inventory WHERE status = 'AVAILABLE'
            """) if hasattr(self.engine, 'db') and self.engine.db else None
            tb_stats = self.engine.db.fetchone("""
                SELECT COUNT(*) AS total, COALESCE(SUM(weight), 0) AS total_kg
                FROM inventory_tonbag WHERE status = 'AVAILABLE' AND COALESCE(is_sample, 0) = 0
            """) if hasattr(self.engine, 'db') and self.engine.db else None
            total_lots = current_kg = 0
            tb_total = tb_kg = 0
            if stats:
                total_lots = stats.get('total_lots', 0) or 0
                current_kg = (stats.get('total_current', 0) or 0) / 1000.0
            if tb_stats:
                tb_total = tb_stats.get('total') or 0
                tb_kg = (tb_stats.get('total_kg') or 0) / 1000.0
            line = (
                f"📦 판매가능 LOT: {total_lots:,}  🎒 톤백: {tb_total:,}  💰 총 중량: {current_kg:,.1f} MT (LOT) / {tb_kg:,.1f} MT (톤백)"
            )
            self._inv_summary_label.config(text=line)
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"inv_stats 갱신 오류: {e}")

    # ═══════════════════════════════════════════════════════
    # v4.0.6: 필터바 / 합계바 메서드
    # ═══════════════════════════════════════════════════════
    
    def _on_inv_filter_apply(self) -> None:
        """v4.0.6: 재고 필터 적용 시 새로고침"""
        if hasattr(self, '_deferred_refresh_main_tabs'):
            self._deferred_refresh_main_tabs(delay_ms=50)
        elif hasattr(self, '_refresh_main_tabs'):
            self._refresh_main_tabs()
        else:
            self._refresh_inventory()
    
    def _update_inv_filter_values(self, inventory) -> None:
        """v4.0.6: 필터 드롭다운에 실제 데이터 값 채우기. STATUS는 전체/판매가능/판매배정/판매화물 결정/출고 5종 + 개수."""
        if not hasattr(self, '_inv_filter_bar'):
            return
        try:
            filter_cols = {
                'lot_no': [], 'sap_no': [], 'bl_no': [],
                'container_no': [], 'product': [], 'status': []
            }
            for item in inventory:
                for col in filter_cols:
                    if col == 'status':
                        continue
                    val = str(item.get(col, '') or '')
                    if val:
                        filter_cols[col].append(val)

            cnt_total = len(inventory)
            cnt_avail = sum(1 for i in inventory if (i.get('status') or '') == 'AVAILABLE')
            cnt_reserved = sum(1 for i in inventory if (i.get('status') or '') == 'RESERVED')
            cnt_picked = sum(1 for i in inventory if (i.get('status') or '') == 'PICKED')
            cnt_sold = sum(1 for i in inventory if (i.get('status') or '') == 'SOLD')
            status_values = [
                f"전체 ({cnt_total})", f"판매가능 ({cnt_avail})", f"판매배정 ({cnt_reserved})",
                f"판매화물 결정 ({cnt_picked})", f"출고 ({cnt_sold})",
            ]

            for col, vals in filter_cols.items():
                if col == 'status':
                    combo = self._inv_filter_bar.filter_combos.get('status')
                    if combo:
                        combo['values'] = status_values
                        cur = self._inv_filter_bar.filter_vars['status'].get()
                        if cur not in status_values and status_values:
                            self._inv_filter_bar.filter_vars['status'].set(status_values[0])
                else:
                    self._inv_filter_bar.update_filter_values(col, vals)
        except (ValueError, TypeError) as e:
            logger.debug(f"필터 값 업데이트 오류: {e}")
    
    def _update_inv_footer(self) -> None:
        """v4.0.6: 하단 합계 바 — 트리뷰 표시 행 기준"""
        if not hasattr(self, '_inv_footer'):
            return
        try:
            net_total = 0.0
            balance_total = 0.0
            rows = 0
            
            for item_id in self.tree_inventory.get_children(''):
                vals = self.tree_inventory.item(item_id, 'values')
                rows += 1
                # NET(Kg) = index 7, Balance(Kg) = index 15 (INVENTORY_COLUMNS 기준)
                try:
                    net_total += float(str(vals[7]).replace(',', ''))
                except (ValueError, TypeError, IndexError) as _e:
                    logger.debug(f"Suppressed: {_e}")
                try:
                    balance_total += float(str(vals[15]).replace(',', ''))
                except (ValueError, TypeError, IndexError) as _e:
                    logger.debug(f"Suppressed: {_e}")
            
            self._inv_footer.update({
                'rows': rows,
                'net_kg': net_total,
                'balance_kg': balance_total,
            })
        except (ValueError, TypeError) as e:
            logger.debug(f"inv footer 오류: {e}")

    def _refresh_inventory_async(self) -> None:
        def load_data():
            return self.engine.get_all_inventory()
        def update_ui(inventory):
            self._refresh_inventory()
        self._run_background(load_data, update_ui)

    def _on_lot_double_click(self, event) -> None:
        """LOT 더블클릭 → v4.1.0: 상세 추적 팝업"""
        selection = self.tree_inventory.selection()
        if not selection:
            return
        
        item_id = selection[0]
        item = self.tree_inventory.item(item_id)
        values = item.get('values', [])
        tags = item.get('tags', ())
        
        if not values or len(values) < 2:
            return
        
        # values[0] = row_num, values[1] = lot_no (INVENTORY_COLUMNS 기준)
        lot_no = str(values[1]).strip()
        if not lot_no:
            return
        
        # v4.1.0: 상세 추적 팝업 표시
        if hasattr(self, '_show_lot_detail_popup'):
            self._show_lot_detail_popup(lot_no)

    def _sort_treeview(self, tree, col: str) -> None:
        """트리뷰 정렬"""
        if self._sort_column == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col
            self._sort_reverse = False

        items = [(tree.set(item, col), item) for item in tree.get_children('')]

        numeric_cols = ['net_weight', 'gross_weight', 'current_weight', 'initial_weight',
                       'mxbg_pallet', 'free_time']

        if col in numeric_cols:
            def sort_key(x):
                try:
                    return float(x[0].replace(',', ''))
                except (ValueError, TypeError):
                    return 0
        else:
            sort_key = lambda x: x[0].lower() if x[0] else ''

        items.sort(key=sort_key, reverse=self._sort_reverse)

        for index, (_, item) in enumerate(items):
            tree.move(item, '', index)

        # U7: 헤더 정렬 표시 개선 (▲▼)
        arrow = " ▼" if self._sort_reverse else " ▲"
        for c_id, c_label, _, _, _ in INVENTORY_COLUMNS:
            if c_id == col:
                tree.heading(c_id, text=f"{c_label}{arrow}")
            else:
                tree.heading(c_id, text=c_label)
    

    def _hide_empty_state_hint(self) -> None:
        """v3.9.9: 빈 상태 안내 숨김"""
        if hasattr(self, '_empty_hint') and self._empty_hint:
            try:
                self._empty_hint.destroy()
            except (ValueError, TypeError, KeyError) as _e:
                logger.debug(f'Suppressed: {_e}')
            self._empty_hint = None
    
    def _populate_filter_dropdowns(self) -> None:
        """
        v4.19.1: 필터 드롭다운 목록 자동 채우기
        
        호출 시점:
        - 탭 초기화 시
        - 재고 새로고침 시
        """
        try:
            # LOT NO 목록
            if hasattr(self, '_inv_filter_bar') and hasattr(self._inv_filter_bar, 'lot_combo'):
                lots = self.engine.db.fetchall(
                    "SELECT DISTINCT lot_no FROM inventory WHERE lot_no IS NOT NULL ORDER BY lot_no"
                )
                lot_values = ['전체'] + [dict(row)['lot_no'] for row in lots if row]
                self._inv_filter_bar.lot_combo['values'] = lot_values
            
            # SAP NO 목록
            if hasattr(self, '_inv_filter_bar') and hasattr(self._inv_filter_bar, 'sap_combo'):
                saps = self.engine.db.fetchall(
                    "SELECT DISTINCT sap_no FROM inventory "
                    "WHERE sap_no IS NOT NULL AND sap_no != '' "
                    "ORDER BY sap_no"
                )
                sap_values = ['전체'] + [dict(row)['sap_no'] for row in saps if row]
                self._inv_filter_bar.sap_combo['values'] = sap_values
            
            # BL NO 목록
            if hasattr(self, '_inv_filter_bar') and hasattr(self._inv_filter_bar, 'bl_combo'):
                bls = self.engine.db.fetchall(
                    "SELECT DISTINCT bl_no FROM inventory "
                    "WHERE bl_no IS NOT NULL AND bl_no != '' "
                    "ORDER BY bl_no"
                )
                bl_values = ['전체'] + [dict(row)['bl_no'] for row in bls if row]
                self._inv_filter_bar.bl_combo['values'] = bl_values
            
            # CONTAINER 목록
            if hasattr(self, '_inv_filter_bar') and hasattr(self._inv_filter_bar, 'container_combo'):
                containers = self.engine.db.fetchall(
                    "SELECT DISTINCT container_no FROM inventory "
                    "WHERE container_no IS NOT NULL AND container_no != '' "
                    "ORDER BY container_no"
                )
                container_values = ['전체'] + [dict(row)['container_no'] for row in containers if row]
                self._inv_filter_bar.container_combo['values'] = container_values
            
            # PRODUCT 목록
            if hasattr(self, '_inv_filter_bar') and hasattr(self._inv_filter_bar, 'product_combo'):
                products = self.engine.db.fetchall(
                    "SELECT DISTINCT product FROM inventory "
                    "WHERE product IS NOT NULL "
                    "ORDER BY product"
                )
                product_values = ['전체'] + [dict(row)['product'] for row in products if row]
                self._inv_filter_bar.product_combo['values'] = product_values
            
            # STATUS 목록은 _update_inv_filter_values에서 전체/판매가능/판매배정/판매화물 결정/출고(개수)로 설정

            logger.debug("✅ 필터 드롭다운 채우기 완료")
        
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"필터 드롭다운 채우기 실패: {e}")

