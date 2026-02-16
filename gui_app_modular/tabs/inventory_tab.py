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
from ..utils.ui_constants import ThemeColors
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 18열 정의: (컬럼ID, 표시명, 기본폭, 정렬, 기본표시여부)
# ═══════════════════════════════════════════════════════════════
INVENTORY_COLUMNS = [
    # v4.0.0: 18열 확정 → v5.6.0: 19열 (잔여 톤백 추가)
    ('row_num',            'No.',            50, 'center', True),   #  1. 순번
    ('lot_no',             'LOT NO',        120, 'center', True),   #  2
    ('sap_no',             'SAP NO',        120, 'center', True),   #  3
    ('bl_no',              'BL NO',         140, 'center', True),   #  4
    ('container_no',       'CONTAINER',     130, 'center', True),   #  5
    ('product',            'PRODUCT',       160, 'center', True),   #  6
    ('mxbg_pallet',        'MXBG',           70, 'center', True),   #  7
    ('avail_bags',         'Avail',          60, 'center', True),   #  8. v5.6.0 잔여 톤백
    ('net_weight',         'NET(Kg)',        100, 'e',      True),   #  9
    ('salar_invoice_no',   'INVOICE NO',    100, 'center', True),   # 10
    ('ship_date',          'SHIP DATE',      95, 'center', True),   # 11
    ('arrival_date',       'ARRIVAL',        95, 'center', True),   # 12
    ('free_time',          'FREE TIME',      80, 'center', True),   # 13
    ('warehouse',          'WH',             80, 'center', True),   # 14
    ('status',             'STATUS',         90, 'center', True),   # 15
    ('customs',            'CUSTOMS',        90, 'center', True),   # 16
    ('current_weight',     'Balance(Kg)',    100, 'e',      True),   # 17
    ('initial_weight',     'Inbound(Kg)',    100, 'e',      True),   # 18
    ('outbound_weight',    'Outbound(Kg)',   100, 'e',      True),   # 19
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
        from ..utils.tree_enhancements import HeaderFilterBar, FooterTotalBar, apply_striped_rows
        
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
            self.tab_inventory, None, inv_filter_cols,
            on_filter=self._on_inv_filter_apply,
            is_dark=_is_dark_filter
        )
        self._inv_filter_bar.pack(fill=X, padx=5, pady=(0, 2))
        
        # v5.0.2: 컬럼 토글 + 표시 모드 바
        try:
            from ..utils.column_toggle import ColumnToggleBar
            
            # 토글 가능한 컬럼 목록
            toggleable_cols = [
                ('sap_no', 'SAP NO'),
                ('bl_no', 'BL NO'),
                ('container_no', 'CONTAINER'),
                ('ship_date', 'SHIP DATE'),          # ✅ v5.0.6 수정
                ('free_time', 'FREE TIME'),          # ✅ v5.0.6 수정
                ('customs', 'CUSTOMS'),
            ]
            
            self._inv_toggle_bar = ColumnToggleBar(
                self.tab_inventory,
                None,  # Treeview는 나중에 연결
                toggleable_cols,
                is_dark=_is_dark_filter
            )
            self._inv_toggle_bar.pack(fill=X, padx=5, pady=(0, 2))
        except (ImportError, Exception) as e:
            logger.debug(f"컬럼 토글바 생성 실패: {e}")
            self._inv_toggle_bar = None
        
        # ═══════════════════════════════════════════════════════
        # 트리뷰 (18열)
        # ═══════════════════════════════════════════════════════
        tree_frame = ttk.Frame(self.tab_inventory)
        tree_frame.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        self._inv_tree_frame = tree_frame

        # 모든 18열로 생성
        all_col_ids = [c[0] for c in INVENTORY_COLUMNS]
        
        # v3.8.9: 트리뷰 스타일 — 테마 인식 (글자 흐림 수정)
        import tkinter.font as tkfont
        _style = ttk.Style()
        _inv_font = tkfont.Font(family='맑은 고딕', size=12)
        _inv_head_font = tkfont.Font(family='맑은 고딕', size=12, weight='bold')
        _row_h = _inv_font.metrics('linespace') + 6
        
        _is_dark_tv = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        if _is_dark_tv:
            _tv_bg, _tv_fg, _tv_field = '#1e1e1e', '#e0e0e0', '#1e1e1e'
            _tv_head_bg, _tv_head_fg = '#333333', ThemeColors.get('bg_card')
        else:
            _tv_bg, _tv_fg, _tv_field = ThemeColors.get('bg_card'), '#1a1a1a', ThemeColors.get('bg_card')
            _tv_head_bg, _tv_head_fg = ThemeColors.get('text_primary'), ThemeColors.get('bg_card')
        
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
        
        # v4.0.0 Q7: 선택 행 하이라이트 강화
        _style.map('Inv.Treeview',
                   background=[('selected', ThemeColors.get('info'))],
                   foreground=[('selected', ThemeColors.get('bg_card'))])
        _style.map('Inv.Treeview',
                   background=[('selected', ThemeColors.get('tree_select_fg'))],
                   foreground=[('selected', ThemeColors.get('bg_card'))])
        
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

        # ═══════════════════════════════════════════════════════
        # v5.5.3 patch_04: 재고 합계 통계 바 (ttk 전환 — 테마 자동 대응)
        # ═══════════════════════════════════════════════════════
        # v5.6.1 patch: 하단 요약바 — 깔끔한 1줄 통합
        # ═══════════════════════════════════════════════════════
        self._inv_stats_frame = ttk.Frame(self.tab_inventory, padding=(8, 5))
        self._inv_stats_frame.pack(fill=X, padx=5, pady=(0, 2))

        # v5.6.9: 하단 요약바 폰트/간격 통일
        _sf = ('맑은 고딕', 11)
        _vf = ('맑은 고딕', 11, 'bold')

        def _add_stat(parent, icon_text, font_l=_sf, font_v=_vf):
            ttk.Label(parent, text=icon_text, font=font_l).pack(side=LEFT, padx=(10, 2))
            lbl = ttk.Label(parent, text="-", font=font_v)
            lbl.pack(side=LEFT, padx=(0, 10))
            return lbl

        self._inv_stat_lots     = _add_stat(self._inv_stats_frame, "📦 LOT:")
        self._inv_stat_tonbags  = _add_stat(self._inv_stats_frame, "🎒 톤백:")
        self._inv_stat_initial  = _add_stat(self._inv_stats_frame, "📥 입고:")
        self._inv_stat_current  = _add_stat(self._inv_stats_frame, "💰 잔량:")
        self._inv_stat_picked   = _add_stat(self._inv_stats_frame, "📤 출고:")
        self._inv_stat_avail    = _add_stat(self._inv_stats_frame, "✅ 가용:")
        self._inv_stat_depleted = _add_stat(self._inv_stats_frame, "❌ 소진:")

        ttk.Separator(self._inv_stats_frame, orient='vertical').pack(side=LEFT, fill=Y, padx=8)
        ttk.Label(self._inv_stats_frame, text="📊 출고율:", font=_sf).pack(side=LEFT, padx=(0, 2))
        self._inv_progress_canvas = tk.Canvas(self._inv_stats_frame,
                                               width=100, height=14, bg='#3d3d3d',
                                               highlightthickness=0)
        self._inv_progress_canvas.pack(side=LEFT, padx=(0, 4))
        self._inv_stat_progress = tk.Label(self._inv_stats_frame, text="0.0%",
                                            font=_vf,
                                            fg=ThemeColors.get('statusbar_icon_ok'))
        self._inv_stat_progress.pack(side=LEFT)

        # 테마 색상
        self._apply_inventory_theme_colors()

        # v4.0.6: 필터바에 treeview 연결
        self._inv_filter_bar.tree = self.tree_inventory
        
        # v5.0.2: 컬럼 토글바에 treeview 연결
        if hasattr(self, '_inv_toggle_bar') and self._inv_toggle_bar:
            self._inv_toggle_bar.tree = self.tree_inventory
        
        # v4.0.6: 하단 NET(KG) / Balance 합계 바
        # v5.6.1: FooterTotalBar 제거 — stats_frame 1줄로 통합
        # self._inv_footer = FooterTotalBar(self.tab_inventory, is_dark=_is_dark_filter)
        # self._inv_footer.pack(fill=X, padx=5, pady=(0, 2))

        # 이벤트
        self.tree_inventory.bind('<Double-1>', self._on_lot_double_click)
        # U5: 우클릭 컨텍스트 메뉴
        self.tree_inventory.bind('<Button-3>', self._on_inventory_right_click)

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

    def _load_inv_search_combos(self) -> None:
        """재고리스트 검색 콤보에 DB 고유값 로드 (오름차순)"""
        try:
            # v5.6.0: 화이트리스트 검증
            ALLOWED_SEARCH_FIELDS = {'sap_no', 'bl_no', 'lot_no'}
            for field in ['sap_no', 'bl_no', 'lot_no']:
                if field not in self._inv_search_combos:
                    continue
                if field not in ALLOWED_SEARCH_FIELDS:
                    continue
                var, cb = self._inv_search_combos[field]
                try:
                    rows = self.engine.db.fetchall(
                        f"SELECT DISTINCT {field} FROM inventory WHERE {field} IS NOT NULL AND {field} != '' ORDER BY {field} ASC")
                    vals = ['전체']
                    for r in rows:
                        v = r[0] if isinstance(r, (list, tuple)) else r.get(field, '')
                        if v:
                            vals.append(str(v))
                    cb['values'] = vals
                except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
                    logger.debug(f"콤보 로드 [{field}]: {e}")
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"콤보 초기화: {e}")

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
        dlg.geometry("700x400")
        dlg.transient(self.root)
        
        cols = ('sub_lt', 'weight', 'status', 'location', 'picked_to', 'outbound_date')
        tree = _ttk.Treeview(dlg, columns=cols, show='headings', height=15)
        
        for col, text, w in [
            ('sub_lt', '톤백#', 60), ('weight', '중량(kg)', 100),
            ('status', '상태', 100), ('location', '위치', 80),
            ('picked_to', '출고처', 120), ('outbound_date', '출고일', 120)
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=w, anchor='center')
        
        status_icons = {'AVAILABLE': '✅ 가용', 'PICKED': '📤 출고'}
        
        for i, tb in enumerate(tonbags):
            status_text = status_icons.get(tb['status'], tb['status'] or '')
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
        tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scroll.pack(side='right', fill='y', pady=5)
        
        total = sum((tb['weight'] or 0) for tb in tonbags)
        avail = sum((tb['weight'] or 0) for tb in tonbags if tb['status'] == 'AVAILABLE')
        _ttk.Label(dlg, text=f"합계: {len(tonbags)}개 / {total:,.0f}kg (가용: {avail:,.0f}kg)",
                  font=('', 13, 'bold')).pack(side='bottom', pady=5)
    
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
        
        movements = self.engine.db.fetchall(
            """SELECT movement_type, qty_kg, customer, movement_date, created_at
               FROM stock_movement WHERE lot_no = ? ORDER BY created_at DESC""",
            (lot_no,)
        )
        
        dlg = tk.Toplevel(self.root)
        dlg.title(f"📊 LOT 이력 — {lot_no}")
        dlg.geometry("600x350")
        dlg.transient(self.root)
        
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
        tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        if not movements:
            _ttk.Label(dlg, text="이력이 없습니다.", foreground='gray').pack(pady=20)

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

    def _refresh_inventory(self) -> None:
        """재고 목록 새로고침 (18열 + 콤보 검색 + Date 기간)"""
        if not hasattr(self, 'tree_inventory'):
            return
        
        # v4.19.1: 필터 드롭다운 채우기 (추가)
        self._populate_filter_dropdowns()
        
        for item in self.tree_inventory.get_children():
            self.tree_inventory.delete(item)

        search_text = self.search_var.get().strip().lower()
        status_filter = self.status_var.get()
        
        # 콤보 검색 조건
        combo_filters = {}
        if hasattr(self, '_inv_search_combos'):
            for field, (var, cb) in self._inv_search_combos.items():
                val = var.get()
                if val and val != '전체':
                    combo_filters[field] = val
        
        # v4.0.6: 헤더 필터바 조건
        if hasattr(self, '_inv_filter_bar'):
            combo_filters.update(self._inv_filter_bar.get_filters())
        
        # Date 기간 조건
        date_from = ''
        date_to = ''
        if hasattr(self, '_date_from_var'):
            date_from = self._date_from_var.get().strip().replace('-', '')
        if hasattr(self, '_date_to_var'):
            date_to = self._date_to_var.get().strip().replace('-', '')

        try:
            inventory = self.engine.get_all_inventory()

            for item in inventory:
                lot_no = str(item.get('lot_no', ''))
                product = str(item.get('product', ''))
                sap_no = str(item.get('sap_no', ''))

                # 즉시 검색 필터
                if search_text:
                    searchable = f"{lot_no} {product} {sap_no} {item.get('bl_no','')}".lower()
                    if search_text not in searchable:
                        continue

                # 상태 필터
                status = item.get('status', 'AVAILABLE')
                if status_filter != "전체" and status != status_filter:
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
                        # v5.6.0/v5.6.9: Avail = 현재 가용 톤백 수 실시간 (출고↓ 반품↑)
                        try:
                            tb_row = self.engine.db.fetchone(
                                "SELECT COUNT(*) as cnt FROM inventory_tonbag "
                                "WHERE lot_no = ? AND status = 'AVAILABLE' AND COALESCE(is_sample,0) = 0",
                                (lot_no,))
                            avail_cnt = tb_row['cnt'] if tb_row and isinstance(tb_row, dict) else (tb_row[0] if tb_row else 0)
                            vals.append(str(avail_cnt))
                        except (ValueError, TypeError, KeyError, AttributeError):
                            vals.append('')
                        continue
                    
                    v = item.get(col_id, '')
                    if v is None:
                        v = ''
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
                    # U2: 상태 아이콘
                    elif col_id == 'status':
                        status_icons = {
                            'AVAILABLE': '✅ 가용',
                            'PICKED': '📤 출고',
                            'RESERVED': '🔒 예약',
                            'SHIPPED': '🚢 선적',
                            'DEPLETED': '❌ 소진',
                        }
                        v = status_icons.get(str(v), str(v))
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
            _stripe_bg = _p.get('tree_stripe', ThemeColors.get('tree_stripe') if not _dk else '#2a2a2a')
            _text_color = '#1a1a1a' if not _dk else '#f0f0f0'  # 다크→밝은색, 라이트→검정

            self.tree_inventory.tag_configure('available',
                background=_p.get('available', ThemeColors.get('available')) if not _dk else '#1b3a2a',
                foreground=_text_color)
            self.tree_inventory.tag_configure('picked',
                background=_p.get('picked', ThemeColors.get('picked')) if not _dk else '#3a1a1a',
                foreground=_text_color)
            self.tree_inventory.tag_configure('reserved',
                background=_p.get('reserved', ThemeColors.get('reserved')) if not _dk else '#3a3a1a',
                foreground=_text_color)
            self.tree_inventory.tag_configure('shipped',
                background=_p.get('shipped', ThemeColors.get('shipped')) if not _dk else '#1a2a3a',
                foreground=_text_color)
            self.tree_inventory.tag_configure('depleted',
                background='#f5f5f5' if not _dk else '#2a2a2a',
                foreground='#999999' if not _dk else '#666666')
            self.tree_inventory.tag_configure('stripe',
                background=_stripe_bg, foreground=_text_color)

            self._refresh_summary()
            
            # v3.9.9: 빈 상태 안내 (데이터 없을 때)
            if not self.tree_inventory.get_children():
                self._show_empty_state_hint()
            else:
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
                    _dk2 = _TC.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
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
    
    def _update_style_toolbar_tree(self, tree: 'ttk.Treeview') -> None:
        """
        v4.2.2: 스타일 툴바의 Treeview 참조 업데이트
        
        Args:
            tree: 연결할 Treeview 객체
        """
        if not hasattr(self, '_inv_style_toolbar') or not self._inv_style_toolbar:
            return
        
        try:
            from ..utils.table_styler import TableStyler
            
            # 툴바 내부의 모든 위젯 순회
            for widget in self._inv_style_toolbar.winfo_children():
                # Checkbutton인 경우 command 재설정
                if isinstance(widget, tk.Checkbutton):
                    # widget의 변수를 가져와서 새로운 command 설정
                    # (기존 코드 구조상 동적으로 재설정하기 어려우므로 스킵)
                    pass
                # Radiobutton인 경우 command 재설정
                elif isinstance(widget, tk.Radiobutton):
                    mode = widget.cget('value')
                    widget.configure(
                        command=lambda m=mode: TableStyler.set_row_height(tree, m)
                    )
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.debug(f"스타일 툴바 업데이트 실패: {e}")

    def _refresh_inv_stats(self) -> None:
        """v3.8.7: 재고 탭 하단 통계 합계 갱신"""
        if not hasattr(self, '_inv_stat_lots'):
            return
        
        try:
            # LOT 통계
            stats = self.engine.db.fetchone("""
                SELECT 
                    COUNT(*) AS total_lots,
                    SUM(CASE WHEN status != 'DEPLETED' THEN 1 ELSE 0 END) AS avail_lots,
                    SUM(CASE WHEN status = 'DEPLETED' THEN 1 ELSE 0 END) AS depleted_lots,
                    COALESCE(SUM(initial_weight), 0) AS total_initial,
                    COALESCE(SUM(current_weight), 0) AS total_current,
                    COALESCE(SUM(picked_weight), 0) AS total_picked
                FROM inventory
            """)
            
            # 톤백 통계 (v3.9.4: 샘플 제외)
            tb_stats = self.engine.db.fetchone("""
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN status='AVAILABLE' THEN 1 ELSE 0 END) AS avail
                FROM inventory_tonbag
                WHERE COALESCE(is_sample, 0) = 0
            """)
            
            if stats:
                total_lots = stats.get('total_lots', 0) or 0
                avail_lots = stats.get('avail_lots', 0) or 0
                depleted = stats.get('depleted_lots', 0) or 0
                initial_mt = (stats.get('total_initial', 0) or 0) / 1000
                current_mt = (stats.get('total_current', 0) or 0) / 1000
                picked_mt = (stats.get('total_picked', 0) or 0) / 1000
                
                self._inv_stat_lots.config(text=f"{total_lots:,}")
                self._inv_stat_initial.config(text=f"{initial_mt:,.1f} MT")
                self._inv_stat_current.config(text=f"{current_mt:,.1f} MT")
                self._inv_stat_picked.config(text=f"{picked_mt:,.1f} MT")
                self._inv_stat_avail.config(text=f"{avail_lots:,}")
                self._inv_stat_depleted.config(text=f"{depleted:,}")
                
                # v3.9.5: 출고 진행률 바 업데이트
                if hasattr(self, '_inv_progress_canvas') and initial_mt > 0:
                    out_mt = initial_mt - current_mt
                    pct = (out_mt / initial_mt * 100) if initial_mt > 0 else 0
                    pct = max(0, min(100, pct))
                    
                    self._inv_progress_canvas.delete('all')
                    fill_w = int(120 * pct / 100)
                    color = ThemeColors.get('badge_db') if pct < 50 else ('#e67e22' if pct < 90 else ThemeColors.get('statusbar_icon_err'))
                    self._inv_progress_canvas.create_rectangle(0, 0, fill_w, 16, fill=color, outline='')
                    
                    self._inv_stat_progress.config(text=f"{pct:.1f}%", fg=color)
            
            if tb_stats:
                tb_total = tb_stats.get('total', 0) or 0
                tb_avail = tb_stats.get('avail', 0) or 0
                self._inv_stat_tonbags.config(text=f"{tb_avail:,}/{tb_total:,}")
                
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"inv_stats 갱신 오류: {e}")

    # ═══════════════════════════════════════════════════════
    # v4.0.6: 필터바 / 합계바 메서드
    # ═══════════════════════════════════════════════════════
    
    def _on_inv_filter_apply(self) -> None:
        """v4.0.6: 재고 필터 적용 시 새로고침"""
        self._refresh_inventory()
    
    def _update_inv_filter_values(self, inventory) -> None:
        """v4.0.6: 필터 드롭다운에 실제 데이터 값 채우기"""
        if not hasattr(self, '_inv_filter_bar'):
            return
        try:
            filter_cols = {
                'lot_no': [], 'sap_no': [], 'bl_no': [],
                'container_no': [], 'product': [], 'status': []
            }
            for item in inventory:
                for col in filter_cols:
                    val = str(item.get(col, '') or '')
                    if val:
                        filter_cols[col].append(val)
            
            for col, vals in filter_cols.items():
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
    
    def _show_empty_state_hint(self) -> None:
        """v3.9.9: 재고 데이터 없을 때 안내 표시"""
        from ..utils.constants import tk
        
        if hasattr(self, '_empty_hint') and self._empty_hint:
            return
        
        try:
            self._empty_hint = tk.Frame(self._inv_tree_frame, bg='#f5f6fa')
            self._empty_hint.place(relx=0.5, rely=0.4, anchor='center')
            
            tk.Label(self._empty_hint, text="📦", bg='#f5f6fa',
                     font=('', 36)).pack(pady=(0, 5))
            tk.Label(self._empty_hint, text="재고 데이터가 없습니다", bg='#f5f6fa',
                     fg=ThemeColors.get('text_secondary'), font=('맑은 고딕', 14, 'bold')).pack()
            tk.Label(self._empty_hint, 
                     text="Ctrl+O: 파일 열기 | Ctrl+N: 입고 | 파일 드래그앤드롭",
                     bg='#f5f6fa', fg='#95a5a6', font=('맑은 고딕', 10)).pack(pady=5)
            
            btn_frame = tk.Frame(self._empty_hint, bg='#f5f6fa')
            btn_frame.pack(pady=10)
            
            from ..utils.constants import ttk
            ttk.Button(btn_frame, text="📁 파일 선택 입고", 
                       command=lambda: self._on_open_file()).pack(side='left', padx=5)
            ttk.Button(btn_frame, text="📝 수동 입고",
                       command=lambda: self._on_new_inbound()).pack(side='left', padx=5)
        except (ImportError, ModuleNotFoundError) as _e:
            logger.debug(f"empty_hint: {_e}")
    
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
            
            # STATUS 목록
            if hasattr(self, '_inv_filter_bar') and hasattr(self._inv_filter_bar, 'status_combo'):
                self._inv_filter_bar.status_combo['values'] = [
                    '전체', 'AVAILABLE', 'RESERVED', 'SHIPPED', 'RETURNED'
                ]
            
            logger.debug("✅ 필터 드롭다운 채우기 완료")
        
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"필터 드롭다운 채우기 실패: {e}")

