"""
SQM Inventory - Dashboard Tab (v3.8.7)
====================================

v3.6.0 - UI 통일성 적용
- 간격 표준화 (Spacing)
- 컬럼 너비 표준화 (ColumnWidth)
- 폰트 스케일링 (FontScale)

앱 시작 시 첫 화면으로 표시되는 대시보드
- 요약 카드 (총 재고, LOT 수, 금일 입출고)
- 알림 패널 (재고 부족, 무결성 경고)
- 차트 (최근 입출고 추이)
- 빠른 액션 버튼
- 자동 새로고침
"""

from gui_app_modular.utils.ui_constants import create_themed_toplevel  # v8.0.9
from gui_app_modular.utils.ui_constants import is_dark  # v8.0.9
from gui_app_modular.utils.ui_constants import tc
import logging
import sqlite3
from datetime import datetime

from tkinter import ttk
from ..utils.ui_constants import (
    ColumnWidth,
    FontScale,
    ReadableStyle,
    Spacing,
    ThemeColors,
    apply_tooltip,
)

logger = logging.getLogger(__name__)


class DashboardTabMixin:
    """
    대시보드 탭 믹스인
    
    SQMInventoryApp 클래스에 믹스인됩니다.
    """

    def _setup_dashboard_tab(self) -> None:
        """대시보드 탭 — v8.1.9 전면 개편 (3구역 구조)
        1구역: 재고 상태 카드 5개 (상단)
        2구역: 정합성 신호등 + 알림 패널 (중간 좌우)
        3구역: 제품별 현황 테이블 (하단)
        """
        from ..utils.constants import BOTH, LEFT, RIGHT, TOP, YES, X, Y, tk, ttk

        _d = is_dark()

        # ── 색상 팔레트 ───────────────────────────────────────────────
        BG       = ThemeColors.get('bg_primary',   _d)
        BG2      = ThemeColors.get('bg_secondary', _d)
        BG_CARD  = ThemeColors.get('bg_card',      _d)
        FG       = ThemeColors.get('text_primary',  _d)
        FG2      = ThemeColors.get('text_secondary', _d)
        FG_MUTED = ThemeColors.get('text_muted',    _d)
        BORDER   = ThemeColors.get('border',        _d) if 'border' in (
            ThemeColors.DARK if _d else ThemeColors.LIGHT) else (
            '#1a3a5c' if _d else '#e2e8f0')
        ACCENT   = '#00E5A0' if _d else '#0369a1'
        SUCCESS  = '#4caf50' if _d else '#059669'
        WARNING  = '#ffc107' if _d else '#d97706'
        DANGER   = '#f44336' if _d else '#dc2626'

        # 대시보드 전용 (다크: 딥 네이비 베이스 + KPI/섹션은 상태색으로 구분 — 원래 SQM 컬러 UI)
        if _d:
            DASH_BG = '#0b1120'
            DASH_PANEL = '#1e293b'
            DASH_CARD = '#152238'
            DASH_BORDER = '#334155'
            TOTAL_FG = '#2dd4bf'
            _kpi_sub_fg = '#cbd5e1'
            _hdr_integrity_fg = '#6ee7b7'
            _hdr_alert_fg = '#fbbf24'
            _hdr_product_fg = '#38bdf8'
        else:
            DASH_BG = BG
            DASH_PANEL = BG2
            DASH_CARD = BG_CARD
            DASH_BORDER = BORDER
            TOTAL_FG = ACCENT
            _kpi_sub_fg = FG2
            _hdr_integrity_fg = SUCCESS
            _hdr_alert_fg = WARNING
            _hdr_product_fg = ThemeColors.get('info', False)

        # ttk 탭 프레임 배경이 비치지 않도록 전체를 tk 셸로 덮음
        dash_shell = tk.Frame(self.tab_dashboard, bg=DASH_BG)
        dash_shell.pack(fill=BOTH, expand=YES)

        try:
            from ..utils.ui_constants import make_tab_header
            make_tab_header(
                dash_shell, "📊 Dashboard", status_color='#2dd4bf',
                inner_bg=DASH_PANEL, outer_border=DASH_BORDER,
            )
        except Exception as e:
            logger.warning(f'[UI] dashboard_tab: {e}')

        # value_fg 미지정 → KPI 큰 숫자는 카드별 상태색(color) 사용
        self._dashboard_ui_surfaces = {
            'card_bg': DASH_CARD,
            'border': DASH_BORDER,
            'card_title_fg': '#b8c9dc' if _d else FG2,
            'sub_fg': _kpi_sub_fg,
        }
        self._dash_panel_bg = DASH_PANEL
        self._dash_table_header_bg = '#0f172a' if _d else BG2
        _ts_fg = '#f8fafc' if _d else FG
        _ts_sel_bg = ThemeColors.get('tree_select_bg', _d)
        _ts_sel_fg = ThemeColors.get('tree_select_fg', _d)
        self._dash_tree_stripes = (
            DASH_CARD,
            '#1e3a5f' if _d else ThemeColors.get('bg_secondary', False),
            DASH_PANEL, TOTAL_FG, _ts_fg,
        )

        # 상태 카드 액센트 (다크: Material 톤)
        CARD_COLORS = {
            'available': '#4caf50' if _d else '#059669',
            'reserved':  '#ffc107' if _d else '#d97706',
            'picked':    '#9c27b0' if _d else '#7c3aed',
            'sold':      '#2196f3' if _d else '#0369a1',
            'return':    '#ef5350' if _d else '#be185d',
        }

        mc = tk.Frame(dash_shell, bg=DASH_BG)
        mc.pack(
            fill=BOTH, expand=YES,
            padx=Spacing.Tab.OUTER_PADX, pady=(0, Spacing.XS),
        )
        mc.columnconfigure(0, weight=1)

        # ══════════════════════════════════════════════════════════════
        # 1구역: 재고 상태 카드 5개 (상단 가로 한 줄)
        # ══════════════════════════════════════════════════════════════
        zone1 = tk.Frame(mc, bg=DASH_BG)
        zone1.pack(fill=X, pady=(0, 4))
        zone1.columnconfigure(tuple(range(5)), weight=1)
        for i in range(5):
            zone1.columnconfigure(i, weight=1)

        card_defs = [
            ('status_available', '판매가능',      CARD_COLORS['available']),
            ('status_reserved',  '판매배정',      CARD_COLORS['reserved']),
            ('status_picked',    '판매화물 결정', CARD_COLORS['picked']),
            ('status_sold',      '출고완료',      CARD_COLORS['sold']),
            ('status_return',    '반품대기',      CARD_COLORS['return']),
        ]
        self._dashboard_cards = {}
        for col_i, (key, title, color) in enumerate(card_defs):
            card = self._create_dashboard_card(zone1, title, '0개', color)
            card.grid(row=0, column=col_i, sticky='nsew',
                      padx=(0 if col_i == 0 else 4, 0), pady=0)
            self._dashboard_cards[key] = card

        # TOTAL 바
        total_bar = tk.Frame(mc, bg=DASH_PANEL)
        total_bar.pack(fill=X, pady=(0, 6))
        self._dashboard_total_label = tk.Label(
            total_bar,
            text="TOTAL: 계산 중...",
            bg=DASH_PANEL, fg=TOTAL_FG,
            font=('맑은 고딕', 11, 'bold'),
            anchor='w', padx=10, pady=4,
        )
        self._dashboard_total_label.pack(fill=X)

        # ══════════════════════════════════════════════════════════════
        # 2구역: 정합성 신호등(좌) + 알림 패널(우)
        # ══════════════════════════════════════════════════════════════
        zone2 = tk.Frame(mc, bg=DASH_BG)
        zone2.pack(fill=X, pady=(0, 6))

        # ── 좌: 정합성 신호등 ─────────────────────────────────────────
        integrity_outer = tk.Frame(zone2, bg=DASH_BORDER, bd=0)
        integrity_outer.pack(side=LEFT, fill=Y, padx=(0, 4))
        integrity_inner = tk.Frame(integrity_outer, bg=DASH_CARD, padx=12, pady=10)
        integrity_inner.pack(fill=BOTH, expand=YES, padx=1, pady=1)

        # 헤더
        tk.Label(integrity_inner,
                 text="INTEGRITY CHECK  재고 정합성",
                 bg=DASH_CARD, fg=_hdr_integrity_fg,
                 font=('맑은 고딕', 9, 'bold'),
                 anchor='w').pack(fill=X, pady=(0, 8))

        # 신호등 행
        sig_row = tk.Frame(integrity_inner, bg=DASH_CARD)
        sig_row.pack(fill=X, pady=(0, 8))

        # 신호등 도트 (크게)
        self._integrity_signal_dot = tk.Label(
            sig_row, text='🟢',
            font=('맑은 고딕', 22),
            bg=DASH_CARD,
        )
        self._integrity_signal_dot.pack(side=LEFT, padx=(0, 10))

        sig_text = tk.Frame(sig_row, bg=DASH_CARD)
        sig_text.pack(side=LEFT, fill=X, expand=YES)
        self._integrity_signal_label = tk.Label(
            sig_text, text='정합성 OK',
            bg=DASH_CARD, fg=SUCCESS,
            font=('맑은 고딕', 14, 'bold'), anchor='w',
        )
        self._integrity_signal_label.pack(fill=X)
        self._integrity_signal_sub = tk.Label(
            sig_text, text='총입고 = 현재재고 + 출고누계',
            bg=DASH_CARD, fg=FG_MUTED,
            font=('맑은 고딕', 9), anchor='w',
        )
        self._integrity_signal_sub.pack(fill=X)

        # 수치 행들
        int_rows = [
            ('총입고(누계)', '_int_label_total'),
            ('현재재고',     '_int_label_cur'),
            ('출고누계',     '_int_label_out'),
            ('차이',         '_int_label_diff'),
        ]
        for row_title, attr in int_rows:
            row_f = tk.Frame(integrity_inner, bg=DASH_CARD)
            row_f.pack(fill=X, pady=1)
            tk.Frame(row_f, bg=DASH_BORDER, height=1).pack(fill=X, side=TOP)
            lbl_f = tk.Frame(row_f, bg=DASH_CARD)
            lbl_f.pack(fill=X, pady=2)
            tk.Label(lbl_f, text=row_title, bg=DASH_CARD, fg=FG_MUTED,
                     font=('맑은 고딕', 10), width=12, anchor='w').pack(side=LEFT)
            val_lbl = tk.Label(lbl_f, text='—', bg=DASH_CARD, fg=_ts_fg,
                               font=('맑은 고딕', 11, 'bold'), anchor='e')
            val_lbl.pack(side=RIGHT)
            setattr(self, attr, val_lbl)

        # 드릴다운 버튼
        tk.Button(
            integrity_inner,
            text='🔍 불일치 LOT 상세 보기',
            bg=DASH_PANEL, fg=FG2,
            font=('맑은 고딕', 9),
            relief='flat', bd=0, cursor='hand2',
            padx=8, pady=4,
            command=self._on_integrity_drill_down,
        ).pack(fill=X, pady=(8, 0))

        # ── 우: 알림 패널 ─────────────────────────────────────────────
        alert_outer = tk.Frame(zone2, bg=DASH_BORDER, bd=0)
        alert_outer.pack(side=LEFT, fill=BOTH, expand=YES)
        alert_inner = tk.Frame(alert_outer, bg=DASH_CARD)
        alert_inner.pack(fill=BOTH, expand=YES, padx=1, pady=1)

        # 알림 헤더
        alert_hdr = tk.Frame(alert_inner, bg=DASH_PANEL)
        alert_hdr.pack(fill=X)
        tk.Label(alert_hdr, text="⚠️  ALERTS  알림 및 경고",
                 bg=DASH_PANEL, fg=_hdr_alert_fg,
                 font=('맑은 고딕', 9, 'bold'),
                 anchor='w', padx=10, pady=6).pack(side=LEFT)
        self._alert_count_label = tk.Label(
            alert_hdr, text='', bg=DASH_PANEL, fg=DANGER,
            font=('맑은 고딕', 9, 'bold'), padx=8,
        )
        self._alert_count_label.pack(side=RIGHT)

        # 알림 리스트박스
        alert_list_frame = tk.Frame(alert_inner, bg=DASH_CARD)
        alert_list_frame.pack(fill=BOTH, expand=YES, padx=6, pady=6)
        self.alert_listbox = tk.Listbox(
            alert_list_frame,
            bg=DASH_CARD, fg=_ts_fg,
            font=('맑은 고딕', 10),
            selectmode='single',
            relief='flat', bd=0,
            highlightthickness=1,
            highlightbackground=DASH_BORDER,
            highlightcolor=DASH_BORDER,
            selectbackground=_ts_sel_bg,
            selectforeground=_ts_sel_fg,
            activestyle='none',
            height=5,
        )
        alert_vsb = tk.Scrollbar(alert_list_frame, orient='vertical',
                                  command=self.alert_listbox.yview)
        self.alert_listbox.configure(yscrollcommand=alert_vsb.set)
        self.alert_listbox.pack(side=LEFT, fill=BOTH, expand=YES)
        alert_vsb.pack(side=RIGHT, fill=Y)
        self.alert_listbox.bind('<Double-Button-1>', self._on_alert_double_click
                                 if hasattr(self, '_on_alert_double_click') else lambda e: None)

        # KPI 요약 한 줄
        kpi_bar = tk.Frame(alert_inner, bg=DASH_PANEL)
        kpi_bar.pack(fill=X, side=RIGHT if False else 'bottom')
        self._kpi_summary_label = tk.Label(
            kpi_bar, text='',
            bg=DASH_PANEL, fg=FG_MUTED,
            font=('맑은 고딕', 9),
            anchor='w', padx=10, pady=4,
        )
        self._kpi_summary_label.pack(fill=X)

        # ══════════════════════════════════════════════════════════════
        # 3구역: 제품별 현황 테이블 (하단 전체 너비)
        # ══════════════════════════════════════════════════════════════
        zone3 = tk.Frame(mc, bg=DASH_BG)
        zone3.pack(fill=BOTH, expand=YES)

        # 섹션 헤더 + 라디오
        z3_hdr = tk.Frame(zone3, bg=DASH_PANEL)
        z3_hdr.pack(fill=X, pady=(0, 4))
        tk.Label(z3_hdr, text="PRODUCT SUMMARY  제품별 현황",
                 bg=DASH_PANEL, fg=_hdr_product_fg,
                 font=('맑은 고딕', 9, 'bold'),
                 anchor='w', padx=10, pady=5).pack(side=LEFT)

        self._dash_view_mode = tk.StringVar(value='lot')
        for val, lbl in (('lot', '📦 LOT 단위'), ('tonbag', '🎒 톤백 상세')):
            tk.Radiobutton(
                z3_hdr, text=lbl, variable=self._dash_view_mode,
                value=val, command=self._refresh_dashboard_products,
                bg=DASH_PANEL, fg=_ts_fg, selectcolor=DASH_CARD,
                activebackground=DASH_PANEL, activeforeground=_ts_fg,
                font=('맑은 고딕', 10),
            ).pack(side=RIGHT, padx=4)

        # 제품별 트리뷰 (얇은 보더 래퍼)
        product_wrap = tk.Frame(zone3, bg=DASH_BORDER, bd=0)
        product_wrap.pack(fill=BOTH, expand=YES)
        product_frame = tk.Frame(product_wrap, bg=DASH_CARD)
        product_frame.pack(fill=BOTH, expand=YES, padx=1, pady=1)

        _row_h = getattr(ReadableStyle, 'ROW_HEIGHT', 32)
        _dash_tv = 'DashProduct.Treeview'
        try:
            _tv_style = getattr(self.root, 'style', None) or ttk.Style()
            try:
                _base_lay = _tv_style.layout('Treeview')
                if _base_lay:
                    _tv_style.layout(_dash_tv, _base_lay)
            except Exception as _le:
                logger.debug(f'[UI] DashProduct.Treeview layout: {_le}')
            _tv_opts = dict(
                rowheight=max(_row_h - 4, 28),
                font=('맑은 고딕', 10),
                borderwidth=0,
                relief='flat',
                foreground=_ts_fg,
                background=DASH_CARD,
                fieldbackground=DASH_CARD,
            )
            _head_opts = dict(
                font=('맑은 고딕', 10, 'bold'),
                padding=(6, 5),
                relief='flat',
                foreground=_ts_fg,
                background=self._dash_table_header_bg,
            )
            try:
                _tv_style.configure(_dash_tv, parent='Treeview', **_tv_opts)
                _tv_style.configure(f'{_dash_tv}.Heading', parent='Treeview.Heading', **_head_opts)
            except Exception as _pe:
                logger.debug(f'[UI] DashProduct.Treeview parent= fallback: {_pe}')
                _tv_style.configure(_dash_tv, **_tv_opts)
                _tv_style.configure(f'{_dash_tv}.Heading', **_head_opts)
            _tv_style.map(
                _dash_tv,
                background=[('selected', _ts_sel_bg)],
                foreground=[
                    ('selected', _ts_sel_fg),
                    ('!selected', _ts_fg),
                ],
            )
        except Exception as e:
            logger.debug(f'[UI] DashProduct.Treeview: {e}')
            _dash_tv = 'Treeview'

        columns = ("product", "lots", "tonbag_kg", "tonbag_cnt",
                   "sample_kg", "sample_cnt", "total_kg", "total_cnt")
        self.tree_dashboard_product = ttk.Treeview(
            product_frame, columns=columns,
            show="headings", height=Spacing.Tab.TREE_MIN_H,
            style=_dash_tv,
        )
        col_defs = [
            ("product",    "Product",    120, "w"),
            ("lots",       "LOT수",       60, "center"),
            ("tonbag_kg",  "톤백(kg)",   100, "e"),
            ("tonbag_cnt", "톤백수",      60, "center"),
            ("sample_kg",  "샘플(kg)",    80, "e"),
            ("sample_cnt", "샘플수",      60, "center"),
            ("total_kg",   "총무게(kg)", 110, "e"),
            ("total_cnt",  "총개수",      60, "center"),
        ]
        for cid, text, width, anchor in col_defs:
            self.tree_dashboard_product.heading(cid, text=text, anchor='center')
            self.tree_dashboard_product.column(cid, width=width, anchor=anchor)

        prod_vsb = tk.Scrollbar(product_frame, orient='vertical',
                                 command=self.tree_dashboard_product.yview)
        self.tree_dashboard_product.configure(yscrollcommand=prod_vsb.set)
        self.tree_dashboard_product.pack(side=LEFT, fill=BOTH, expand=YES)
        prod_vsb.pack(side=RIGHT, fill=Y)

        # Footer 합계
        try:
            from ..utils.tree_enhancements import TreeviewTotalFooter as _TTF
            self._dash_product_footer = _TTF(
                zone3, self.tree_dashboard_product,
                summable_column_ids=['tonbag_kg', 'sample_kg', 'total_kg'],
                column_display_names={
                    'tonbag_kg': '톤백(kg)',
                    'sample_kg': '샘플(kg)',
                    'total_kg':  '총무게(kg)',
                },
                column_formats={'tonbag_kg': ',.0f', 'sample_kg': ',.0f', 'total_kg': ',.0f'},
                bar_bg=DASH_PANEL,
                accent_color=TOTAL_FG,
                border_color=DASH_BORDER,
                skip_item_tags=('dash_total', 'total'),
            )
            self._dash_product_footer.pack(fill=X)
        except Exception:
            self._dash_product_footer = None

        # 자동새로고침 체크박스
        auto_bar = tk.Frame(mc, bg=DASH_BG)
        auto_bar.pack(fill=X, pady=(4, 0))
        self._auto_refresh_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            auto_bar, text="자동 새로고침 (30초)",
            variable=self._auto_refresh_var,
            bg=DASH_BG, fg=FG_MUTED,
            selectcolor=DASH_CARD, activebackground=DASH_BG,
            font=('맑은 고딕', 9),
            command=self._toggle_auto_refresh
            if hasattr(self, '_toggle_auto_refresh') else lambda: None,
        ).pack(side=LEFT)
        self.dashboard_status = tk.Label(
            auto_bar, text='',
            bg=DASH_BG, fg=FG_MUTED,
            font=('맑은 고딕', 9), anchor='e',
        )
        self.dashboard_status.pack(side=RIGHT, padx=4)

        # 초기 데이터 로드
        self._refresh_dashboard()




    def _create_dashboard_card(self, parent, title: str, value: str, color: str, fonts=None) -> 'ttk.Frame':
        """대시보드 KPI 카드 — 상단 액센트 바 + 딥 서피스 (참고 UI 톤)."""
        from ..utils.constants import tk
        from ..utils.ui_constants import FontScale

        if fonts is None:
            try:
                dpi = parent.winfo_fpixels('1i')
            except (ImportError, ModuleNotFoundError):
                dpi = 96
            fonts = FontScale(dpi)

        sur = getattr(self, '_dashboard_ui_surfaces', None) or {}
        if sur:
            _card_bg = sur.get('card_bg', ThemeColors.get('bg_card', is_dark()))
            _card_fg = sur.get('card_title_fg', ThemeColors.get('text_secondary', is_dark()))
            _border_color = sur.get('border', ThemeColors.get('border', is_dark()))
        else:
            try:
                _dk = is_dark()
                _cp = ThemeColors.get_palette(_dk)
            except (ImportError, ModuleNotFoundError):
                _cp = {'bg_card': ThemeColors.get('bg_card'), 'text_secondary': '#666666'}
            _card_bg = _cp.get('bg_card', ThemeColors.get('bg_card'))
            _card_fg = _cp.get('text_secondary', '#666666')
            _border_color = _cp.get('border', '#e0e0e0')

        outer = tk.Frame(parent, bg=_border_color, bd=0)

        inner = tk.Frame(outer, bg=_card_bg, bd=0)
        inner.pack(fill='both', expand=True, padx=1, pady=1)

        top_accent = tk.Frame(inner, bg=color, height=4)
        top_accent.pack(side='top', fill='x')
        top_accent.pack_propagate(False)

        content = tk.Frame(inner, bg=_card_bg, padx=10, pady=6)
        content.pack(side='top', fill='both', expand=True)

        tk.Label(
            content,
            text=title,
            font=('맑은 고딕', 11),
            bg=_card_bg,
            fg=_card_fg,
        ).pack(anchor='w')

        _val_fg = sur.get('value_fg', color) if sur else color
        value_label = tk.Label(
            content,
            text=value,
            font=('맑은 고딕', 20, 'bold'),
            bg=_card_bg,
            fg=_val_fg,
        )
        value_label.pack(anchor='w', pady=(2, 0))

        _sub_fg = sur.get('sub_fg', _card_fg) if sur else _card_fg
        sub_label = tk.Label(
            content,
            text='',
            font=('맑은 고딕', 13),
            bg=_card_bg,
            fg=_sub_fg,
        )
        sub_label.pack(anchor='w', pady=(2, 0))

        outer.value_label = value_label
        outer.sub_label = sub_label
        outer.color = color

        return outer


    def _refresh_dashboard_integrity(self) -> None:
        """v8.1.9: 정합성 신호등 + 수치 갱신 (새 3구역 대시보드 대응)."""
        try:
            d = self._get_integrity_summary()
            _d   = is_dark()
            _ok  = d.get('ok', True)
            _diff = d.get('diff_kg', 0.0)

            # 신호등 색상
            if _ok:
                dot   = '🟢'
                label = '정합성 OK'
                color = '#4caf50' if _d else '#059669'
            elif abs(_diff) < 10:
                dot   = '🟡'
                label = '경미한 오차'
                color = '#ffc107' if _d else '#d97706'
            else:
                dot   = '🔴'
                label = '불일치 감지!'
                color = '#f44336' if _d else '#dc2626'

            if hasattr(self, '_integrity_signal_dot'):
                self._integrity_signal_dot.config(text=dot)
            if hasattr(self, '_integrity_signal_label'):
                self._integrity_signal_label.config(text=label, fg=color)
            if hasattr(self, '_integrity_signal_sub'):
                sub = '총입고 = 현재재고 + 출고누계' if _ok else                       f'차이 {_diff:+.1f} kg — 드릴다운으로 확인'
                self._integrity_signal_sub.config(text=sub)

            # 수치 라벨
            total_mt = d.get('total_kg', 0) / 1000
            cur_mt   = d.get('cur_kg',   0) / 1000
            out_mt   = d.get('out_kg',   0) / 1000
            diff_mt  = _diff / 1000

            if hasattr(self, '_int_label_total'):
                self._int_label_total.config(
                    text=f"{total_mt:,.1f} MT  (톤백 {d.get('total_cnt',0):,}개)")
            if hasattr(self, '_int_label_cur'):
                self._int_label_cur.config(
                    text=f"{cur_mt:,.1f} MT  (톤백 {d.get('cur_cnt',0):,}개)")
            if hasattr(self, '_int_label_out'):
                self._int_label_out.config(
                    text=f"{out_mt:,.1f} MT  (톤백 {d.get('out_cnt',0):,}개)")
            if hasattr(self, '_int_label_diff'):
                diff_color = color
                self._int_label_diff.config(
                    text=f"{diff_mt:+.3f} MT  ({'✅ OK' if _ok else '❌ 불일치'})",
                    fg=diff_color)

        except Exception as e:
            logger.debug(f"정합성 갱신 오류: {e}")

    def _refresh_dashboard_period_trend(self) -> None:
        """v8.1.5 PATCH-C: 기간별 입고 추이 갱신 — 교차 배경 + 합계 행 추가."""
        try:
            months = self._trend_months_var.get()
            rows = self._get_period_inbound_trend(months if months > 0 else 120)
            if not hasattr(self, '_trend_tree'):
                return
            for item in self._trend_tree.get_children():
                self._trend_tree.delete(item)
            if not rows:
                self._trend_tree.insert('', 'end', values=('데이터 없음', '', '', ''))
                return

            # 스트라이프 태그 설정
            _dk = is_dark()
            _cp = ThemeColors.get_palette(_dk)
            _odd_bg  = _cp.get('bg_secondary', '#0d1b2a' if _dk else '#f0f3f5')
            _even_bg = _cp.get('bg_card',      '#112233' if _dk else '#ffffff')
            _tot_fg  = _cp.get('accent',       '#FF8C00' if _dk else '#c77c2a')
            try:
                self._trend_tree.tag_configure('odd',   background=_odd_bg)
                self._trend_tree.tag_configure('even',  background=_even_bg)
                self._trend_tree.tag_configure('total', font=('맑은 고딕', 9, 'bold'),
                                                         foreground=_tot_fg,
                                                         background=_even_bg)
            except Exception as e:
                logger.warning(f'[UI] dashboard_tab: {e}')
            max_kg = max((float(r.get('kg') or 0) for r in rows), default=1) or 1
            tot_lot = sum(int(r.get('lot_cnt') or 0) for r in rows)
            tot_kg  = sum(float(r.get('kg') or 0) for r in rows)

            for idx, r in enumerate(rows):
                kg = float(r.get('kg') or 0)
                bar_len = int(kg / max_kg * 20)
                bar = '█' * bar_len
                tag = 'odd' if idx % 2 == 0 else 'even'
                self._trend_tree.insert('', 'end', tags=(tag,), values=(
                    r['ym'],
                    f"{int(r.get('lot_cnt') or 0):,}",
                    f"{kg/1000:.1f}",
                    bar,
                ))

            # 합계 행
            self._trend_tree.insert('', 'end', tags=('total',), values=(
                '합  계',
                f"{tot_lot:,}",
                f"{tot_kg/1000:.1f}",
                '',
            ))
        except Exception as e:
            logger.debug(f"기간 추이 갱신 오류: {e}")

    def _on_integrity_drill_down(self) -> None:
        """v7.3.8: 정합성 불일치 LOT 드릴다운 팝업."""
        try:
            import tkinter as tk
            lots = self._get_integrity_mismatch_lots()
            popup = create_themed_toplevel(self.root)
            popup.title("🔎 재고 정합성 불일치 LOT")
            try:
                from gui_app_modular.utils.ui_constants import setup_dialog_geometry_persistence as _sgp
                _sgp(popup, "dashboard_integrity_popup", self.root, "large")
            except Exception as e:
                logger.warning(f'[UI] dashboard_tab: {e}')
            popup.geometry("700x400")
            popup.resizable(True, True)  # v9.0: 크기 조절 허용
            popup.minsize(400, 300)  # v9.0: 최소 크기
            popup.grab_set()
            try:
                import ttkbootstrap as ttk2
            except ImportError:
                import tkinter.ttk as ttk2

            if not lots:
                tk.Label(popup, text="✅ 불일치 LOT 없음 — 정합성 OK",
                         font=('맑은 고딕', 13, 'bold'), fg=tc('success')).pack(pady=40)
                return

            cols = ('lot_no', 'initial', 'cur_kg', 'out_kg', 'diff')
            tree = ttk2.Treeview(popup, columns=cols, show='headings', height=15)
            for cid, txt, w in [
                ('lot_no',  'LOT NO',       130),
                ('initial', '입고중량(kg)',  120),
                ('cur_kg',  '현재재고(kg)',  120),
                ('out_kg',  '출고누계(kg)',  120),
                ('diff',    '차이(kg)',       100),
            ]:
                tree.heading(cid, text=txt, anchor='center')
                tree.column(cid, width=w, anchor='center')
            sb = tk.Scrollbar(popup, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=sb.set)
            tree.pack(side='left', fill='both', expand=True, padx=(8,0), pady=8)
            sb.pack(side='right', fill='y', pady=8)

            for r in lots:
                diff = float(r.get('initial_weight') or 0) - float(r.get('cur_kg') or 0) - float(r.get('out_kg') or 0)
                tree.insert('', 'end', values=(
                    r['lot_no'],
                    f"{r.get('initial_weight',0):,.0f}",
                    f"{r.get('cur_kg',0):,.0f}",
                    f"{r.get('out_kg',0):,.0f}",
                    f"{diff:+,.0f}",
                ))
        except Exception as e:
            logger.error(f"드릴다운 오류: {e}")


    def _refresh_dashboard(self) -> None:
        """대시보드 데이터 새로고침 (v4.0.4: 메인 스레드 직접 실행)"""
        try:
            if not hasattr(self, '_dashboard_cards'):
                return

            # v8.1.9: 3구역 대시보드 갱신 순서
            self._refresh_dashboard_cards()             # 1구역: 상태 카드
            self._refresh_dashboard_integrity()         # 2구역: 정합성 신호등
            # KPI 3종 먼저 수집 → _refresh_dashboard_alerts에서 한 줄 표시
            self._refresh_dashboard_scan_fail()
            self._refresh_dashboard_avg_lot_days()
            self._refresh_dashboard_unassigned_location()
            self._refresh_dashboard_alerts()            # 2구역: 알림 패널
            self._refresh_dashboard_products()          # 3구역: 제품별 현황

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if hasattr(self, 'dashboard_status'):
                self.dashboard_status.config(text=f"마지막 갱신: {now}")
            # v7.3.0: Hero 갱신 시각도 동기화
            if hasattr(self, '_hero_updated_label'):
                self._hero_updated_label.config(text=f"마지막 갱신: {now}")

            logger.debug("대시보드 새로고침 완료")
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"대시보드 새로고침 오류: {e}")

    def _refresh_dashboard_cards(self) -> None:
        """v8.1.5: 5단계 카드 — 톤백/샘플 구분 sub_label 포함."""
        try:
            if not hasattr(self, '_dashboard_cards') or not self._dashboard_cards:
                return

            stats = self._get_status_four_phase_stats()
            total_cnt = stats.get('total_cnt', 0) or 0
            total_kg  = stats.get('total_kg', 0) or 0
            total_mt  = total_kg / 1000.0

            def _sub(kg: float, tb: int, samp: int) -> str:
                """카드 하단: MT + 톤백/샘플 구분."""
                return f"{kg/1000:,.1f} MT" + "\n" + f"톤백 {tb:,}개  /  샘플 {samp:,}개"

            def _set_card(key, cnt, kg, tb=0, samp=0):
                card = self._dashboard_cards.get(key)
                if not card:
                    return
                card.value_label.config(text=f"{cnt}개")
                if hasattr(card, 'sub_label'):
                    card.sub_label.config(
                        text=_sub(kg, tb, samp),
                        justify='left',
                    )

            # 판매가능
            _set_card(
                'status_available',
                stats.get('available_cnt', 0),
                stats.get('available_kg', 0),
                stats.get('avail_tb_cnt', 0),
                stats.get('avail_samp_cnt', 0),
            )

            # 판매배정 (LOT 단위 — 톤백 ID 미확정 포함)
            _rcard = self._dashboard_cards.get('status_reserved')
            if _rcard:
                _lot = int(stats.get('reserved_lot_cnt', stats.get('reserved_cnt', 0)) or 0)
                _tb  = int(stats.get('reserved_tonbag_cnt', 0) or 0)
                _rkg = float(stats.get('reserved_kg', 0) or 0)
                _rcard.value_label.config(text=f"{_lot} LOT")
                if hasattr(_rcard, 'sub_label'):
                    _rcard.sub_label.config(
                        text=(f"{_rkg/1000:,.1f} MT" + "\n" + f"톤백 {_tb:,}개 (상태 RESERVED)"),
                        justify='left',
                    )

            # 판매화물 결정
            _set_card(
                'status_picked',
                stats.get('picked_cnt', 0),
                stats.get('picked_kg', 0),
                stats.get('picked_tb_cnt', 0),
                stats.get('picked_samp_cnt', 0),
            )

            # 출고완료
            _set_card(
                'status_sold',
                stats.get('outbound_cnt', stats.get('sold_cnt', 0)),
                stats.get('outbound_kg', stats.get('sold_kg', 0)),
                stats.get('out_tb_cnt', 0),
                stats.get('out_samp_cnt', 0),
            )

            # 반품대기
            _set_card(
                'status_return',
                stats.get('return_cnt', 0),
                stats.get('return_kg', 0),
                stats.get('ret_tb_cnt', 0),
                stats.get('ret_samp_cnt', 0),
            )

            # TOTAL 바
            if hasattr(self, '_dashboard_total_label'):
                self._dashboard_total_label.config(
                    text=(
                        f"TOTAL: {total_cnt:,}개 / {total_mt:,.1f} MT"
                        "  |  재고 = 판매가능 + 판매배정 + 판매화물 + 반품대기"
                    )
                )

            # Meter 게이지 (4단계 비율)
            if getattr(self, '_has_meters', False):
                try:
                    avail_pct = int((stats.get('available_cnt', 0) / max(total_cnt, 1)) * 100)
                    self._meter_available.configure(amountused=min(avail_pct, 100))
                    out_pct = int((stats.get('picked_cnt', 0) / max(total_cnt, 1)) * 100)
                    self._meter_outbound.configure(amountused=min(out_pct, 100))
                    today_pct = min(50, int((stats.get('sold_cnt', 0) / max(total_cnt, 1)) * 100))
                    self._meter_today.configure(amountused=today_pct)
                except (ValueError, TypeError, KeyError) as me:
                    logger.debug(f"Meter 업데이트 무시: {me}")
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"카드 새로고침 오류: {e}")

    def _refresh_dashboard_alerts(self) -> None:
        """알림 패널 새로고침"""
        from ..utils.constants import END

        try:
            if not hasattr(self, 'alert_listbox'):
                return
            self.alert_listbox.delete(0, END)

            alerts = self._collect_alerts()

            if not alerts:
                self.alert_listbox.insert(END, "✅ 알림이 없습니다")
                if hasattr(self, '_alert_count_label'):
                    self._alert_count_label.config(text='')
            else:
                _err_cnt  = sum(1 for a in alerts if a.get('severity') == 'error')
                _warn_cnt = sum(1 for a in alerts if a.get('severity') == 'warning')
                if hasattr(self, '_alert_count_label'):
                    _dk = is_dark()
                    _danger_c = '#f44336' if _dk else '#dc2626'
                    _warn_c   = '#ffc107' if _dk else '#d97706'
                    _c = _danger_c if _err_cnt else (_warn_c if _warn_cnt else '')
                    _t = f"🔴 {_err_cnt}" if _err_cnt else (f"🟡 {_warn_cnt}" if _warn_cnt else '')
                    self._alert_count_label.config(text=_t, fg=_c)

                for alert in alerts:
                    icon = alert.get('icon', '⚠️')
                    msg  = alert.get('message', '')
                    self.alert_listbox.insert(END, f"{icon} {msg}")
                    idx      = self.alert_listbox.size() - 1
                    severity = alert.get('severity', 'info')
                    _dk = is_dark()
                    _ap = ThemeColors.get_palette(_dk) if hasattr(ThemeColors, 'get_palette') else {}
                    if severity == 'error':
                        self.alert_listbox.itemconfig(idx, fg=_ap.get('danger', '#ff1744'))
                    elif severity == 'warning':
                        self.alert_listbox.itemconfig(idx, fg=_ap.get('warning', '#FF8C00'))
                    else:
                        self.alert_listbox.itemconfig(idx, fg=_ap.get('info', '#00b0ff'))

            # KPI 요약 한 줄 갱신
            if hasattr(self, '_kpi_summary_label'):
                try:
                    _unassigned = getattr(self, '_unassigned_loc_cnt', '?')
                    _scan_fail  = getattr(self, '_scan_fail_rate_str', '?')
                    _avg_days   = getattr(self, '_avg_lot_days_str', '?')
                    self._kpi_summary_label.config(
                        text=f"위치 미배정 {_unassigned}개  |  스캔 실패율 {_scan_fail}  |  LOT 평균 재고기간 {_avg_days}"
                    )
                except Exception as e:
                    logger.warning(f'[UI] dashboard_tab: {e}')
        except Exception as e:
            logger.error(f"알림 새로고침 오류: {e}")

    def _refresh_dashboard_products(self) -> None:
        """v4.0.5 Phase3: 제품별 현황 — 톤백/샘플 구분"""
        from ..utils.constants import END

        try:
            if not hasattr(self, 'tree_dashboard_product'):
                return
            self.tree_dashboard_product.delete(*self.tree_dashboard_product.get_children())

            # v3.8.7: 톤백 데이터 유무에 따라 라디오 메뉴 표시/숨김
            self._update_dash_tonbag_visibility()

            # v4.0.5: 제품별 톤백/샘플 구분 통계
            products = self._get_product_tonbag_sample_breakdown()

            ts = getattr(self, '_dash_tree_stripes', None)
            tr = self.tree_dashboard_product
            if ts and len(ts) >= 5:
                c0, c1, tot_bg, tot_fg, row_fg = ts[0], ts[1], ts[2], ts[3], ts[4]
                tr.tag_configure('dash_r0', background=c0, foreground=row_fg)
                tr.tag_configure('dash_r1', background=c1, foreground=row_fg)
                tr.tag_configure(
                    'dash_total',
                    background=tot_bg,
                    foreground=tot_fg,
                    font=('맑은 고딕', 11, 'bold'),
                )

            # 합계용
            sum_lots = sum_tb_kg = sum_tb_cnt = 0
            sum_sp_kg = sum_sp_cnt = sum_total_kg = sum_total_cnt = 0

            for idx, p in enumerate(products):
                name = p.get('product', 'Unknown') or 'Unknown'
                lots = p.get('lot_count', 0)
                tb_kg = p.get('tonbag_kg', 0)
                tb_cnt = p.get('tonbag_cnt', 0)
                sp_kg = p.get('sample_kg', 0)
                sp_cnt = p.get('sample_cnt', 0)
                t_kg = p.get('total_kg', 0)
                t_cnt = p.get('total_cnt', 0)

                row_tag = ('dash_r0',) if (idx % 2 == 0) else ('dash_r1',)
                if not ts:
                    row_tag = tuple()
                tr.insert('', END, values=(
                    name, lots,
                    f"{tb_kg:,.0f}", tb_cnt,
                    f"{sp_kg:,.0f}", sp_cnt,
                    f"{t_kg:,.0f}", t_cnt
                ), tags=row_tag)

                sum_lots += lots
                sum_tb_kg += tb_kg; sum_tb_cnt += tb_cnt
                sum_sp_kg += sp_kg; sum_sp_cnt += sp_cnt
                sum_total_kg += t_kg; sum_total_cnt += t_cnt

            # 합계 행
            if products:
                tr.insert('', END, values=(
                    '합계', sum_lots,
                    f"{sum_tb_kg:,.0f}", sum_tb_cnt,
                    f"{sum_sp_kg:,.0f}", sum_sp_cnt,
                    f"{sum_total_kg:,.0f}", sum_total_cnt
                ), tags=('dash_total',) if ts else ('total',))
                if not ts:
                    tr.tag_configure('total', font=('', 13, 'bold'))

        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"제품 현황 오류: {e}")


    def _refresh_dashboard_chart(self) -> None:
        """최근 7일 입출고 추이 막대 차트 (stock_movement 기반)."""
        try:
            canvas = getattr(self, 'chart_canvas', None)
            if canvas is None:
                return

            import datetime
            today = datetime.date.today()
            days  = [(today - datetime.timedelta(days=i)) for i in range(6, -1, -1)]
            labels = [d.strftime('%m/%d') for d in days]
            day_strs = [d.strftime('%Y-%m-%d') for d in days]

            # stock_movement 기반 집계
            in_vals, out_vals = [], []
            for ds in day_strs:
                try:
                    r = self.db.fetchone(
                        "SELECT COALESCE(SUM(qty_kg),0) FROM stock_movement "
                        "WHERE movement_type='INBOUND' AND date(created_at)=?", (ds,)
                    )
                    in_vals.append(float(r[0] if r else 0) / 1000)  # MT 단위
                except Exception:
                    in_vals.append(0.0)
                try:
                    r = self.db.fetchone(
                        "SELECT COALESCE(SUM(qty_kg),0) FROM stock_movement "
                        "WHERE movement_type IN ('OUTBOUND','SOLD') AND date(created_at)=?", (ds,)
                    )
                    out_vals.append(float(r[0] if r else 0) / 1000)
                except Exception:
                    out_vals.append(0.0)

            canvas.delete('all')
            W = canvas.winfo_width()  or 200
            H = canvas.winfo_height() or 120
            if W < 10 or H < 10:
                return

            pad_l, pad_r, pad_t, pad_b = 30, 10, 10, 30
            chart_h = H - pad_t - pad_b
            chart_w = W - pad_l - pad_r
            max_val = max(max(in_vals + out_vals, default=0), 1)

            bar_w  = chart_w / (7 * 2 + 7 + 1)
            gap    = bar_w
            col_w  = bar_w * 2 + gap

            # 색상
            try:
                from ..utils.ui_constants import ThemeColors
                _is_dark = is_dark()
                c_in  = '#22c55e' if _is_dark else '#16a34a'
                c_out = '#f97316' if _is_dark else '#ea580c'
                c_txt = '#cbd5e1' if _is_dark else '#334155'
                c_grid= '#334155' if _is_dark else '#e2e8f0'
            except Exception:
                c_in, c_out, c_txt, c_grid = '#22c55e', '#f97316', '#374151', '#e5e7eb'

            # 그리드 라인
            for ratio in [0.25, 0.5, 0.75, 1.0]:
                y = pad_t + chart_h * (1 - ratio)
                canvas.create_line(pad_l, y, W - pad_r, y, fill=c_grid, dash=(2, 3))
                canvas.create_text(pad_l - 2, y, text=f'{max_val*ratio:.0f}',
                                   anchor='e', font=('맑은 고딕', 7), fill=c_txt)

            for i in range(7):
                x0 = pad_l + gap / 2 + i * col_w
                # 입고 막대
                hIn = (in_vals[i] / max_val) * chart_h if max_val else 0
                if hIn > 0:
                    canvas.create_rectangle(
                        x0, pad_t + chart_h - hIn,
                        x0 + bar_w, pad_t + chart_h,
                        fill=c_in, outline='')
                # 출고 막대
                hOut = (out_vals[i] / max_val) * chart_h if max_val else 0
                if hOut > 0:
                    canvas.create_rectangle(
                        x0 + bar_w, pad_t + chart_h - hOut,
                        x0 + bar_w * 2, pad_t + chart_h,
                        fill=c_out, outline='')
                # X축 레이블
                canvas.create_text(
                    x0 + bar_w, H - pad_b + 4,
                    text=labels[i], anchor='n',
                    font=('맑은 고딕', 7), fill=c_txt)

            # 축선
            canvas.create_line(pad_l, pad_t, pad_l, H - pad_b, fill=c_txt)
            canvas.create_line(pad_l, H - pad_b, W - pad_r, H - pad_b, fill=c_txt)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"차트 오류: {e}")

    def _refresh_dashboard_return_rate(self) -> None:
        """반품 현황 패널 갱신."""
        try:
            txt = getattr(self, '_return_info_text', None)
            if txt is None:
                return
            try:
                total_out = (self.db.fetchone(
                    "SELECT COUNT(*) FROM inventory_tonbag WHERE status IN ('OUTBOUND','SOLD')"
                ) or [0])[0]
                total_ret = (self.db.fetchone(
                    "SELECT COUNT(*) FROM inventory_tonbag WHERE status='RETURN'"
                ) or [0])[0]
                rate = (total_ret / total_out * 100) if total_out else 0
                lines_txt = (
                    f"반품 대기:  {total_ret} 개\n"
                    f"출고 완료: {total_out} 개\n"
                    f"반품률:    {rate:.1f}%"
                )
            except Exception:
                lines_txt = "데이터 없음"
            txt.config(state='normal')
            txt.delete('1.0', 'end')
            txt.insert('end', lines_txt)
            txt.config(state='disabled')
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"반품현황 오류: {e}")

    def _refresh_dashboard_scan_fail(self) -> None:
        """스캔 실패율 KPI — KPI 바 캐시 저장."""
        try:
            if hasattr(self, 'engine') and self.engine and hasattr(self.engine, 'db'):
                row = self.engine.db.fetchone(
                    "SELECT COUNT(*) AS total, "
                    "SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) AS failed "
                    "FROM barcode_scan_log WHERE created_at >= date('now','-30 days')"
                )
                if row:
                    total = int((row.get('total') if isinstance(row, dict) else row[0]) or 0)
                    failed = int((row.get('failed') if isinstance(row, dict) else row[1]) or 0)
                    rate = f"{failed/max(total,1)*100:.1f}%" if total > 0 else '0.0%'
                    self._scan_fail_rate_str = rate
                    return
        except Exception as e:
            logger.warning(f'[UI] dashboard_tab: {e}')
        self._scan_fail_rate_str = '-'
        # product footer update
        if hasattr(self, '_dash_product_footer') and self._dash_product_footer:
            self._dash_product_footer.update_totals()

    def _refresh_dashboard_avg_lot_days(self) -> None:
        """LOT 평균 재고기간 KPI — KPI 바 캐시 저장."""
        try:
            if hasattr(self, 'engine') and self.engine and hasattr(self.engine, 'db'):
                row = self.engine.db.fetchone(
                    "SELECT AVG(julianday('now') - julianday(stock_date)) AS avg_days "
                    "FROM inventory WHERE status NOT IN ('DEPLETED','OUTBOUND','SOLD') "
                    "AND stock_date IS NOT NULL AND stock_date != ''"
                )
                if row:
                    avg = row.get('avg_days') if isinstance(row, dict) else row[0]
                    self._avg_lot_days_str = f"{float(avg or 0):.1f}일"
                    return
        except Exception as e:
            logger.warning(f'[UI] dashboard_tab: {e}')
        self._avg_lot_days_str = '-'

    def _refresh_dashboard_unassigned_location(self) -> None:
        """위치 미배정 톤백 KPI — KPI 바 캐시 저장."""
        try:
            if hasattr(self, 'engine') and self.engine and hasattr(self.engine, 'db'):
                row = self.engine.db.fetchone(
                    "SELECT COUNT(*) AS cnt FROM inventory_tonbag "
                    "WHERE (location IS NULL OR location='') "
                    "AND status IN ('AVAILABLE','RESERVED','PICKED') "
                    "AND COALESCE(is_sample,0)=0"
                )
                if row:
                    cnt = int((row.get('cnt') if isinstance(row, dict) else row[0]) or 0)
                    self._unassigned_loc_cnt = cnt
                    return
        except Exception as e:
            logger.warning(f'[UI] dashboard_tab: {e}')
        self._unassigned_loc_cnt = '-'

    def _update_dash_tonbag_visibility(self) -> None:
        """v3.8.7: 대시보드 톤백 라디오 - 톤백 데이터 있을 때만 표시"""
        from ..utils.constants import X

        if not hasattr(self, '_dash_radio_frame'):
            return

        try:
            has_tonbag = False
            if hasattr(self, 'engine') and self.engine and hasattr(self.engine, 'db'):
                row = self.engine.db.fetchone(
                    "SELECT COUNT(*) AS cnt FROM inventory_tonbag LIMIT 1"
                )
                if row:
                    cnt = row['cnt'] if isinstance(row, dict) else row[0]
                    has_tonbag = (cnt > 0)

            is_visible = self._dash_radio_frame.winfo_ismapped()

            if has_tonbag and not is_visible:
                self._dash_radio_frame.pack(fill=X, padx=5, pady=(5, 0))
            elif not has_tonbag and is_visible:
                self._dash_radio_frame.pack_forget()
                self._dash_view_mode.set('lot')

        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.debug(f"대시보드 톤백 라디오 가시성 오류: {e}")
            try:
                if self._dash_radio_frame.winfo_ismapped():
                    self._dash_radio_frame.pack_forget()
            except (RuntimeError, ValueError) as _e:
                logger.debug(f"{type(_e).__name__}: {_e}")
            self._dash_view_mode.set('lot')


    # v4.0.1: 대시보드 데이터/차트는 dashboard_data_mixin.py로 분리
