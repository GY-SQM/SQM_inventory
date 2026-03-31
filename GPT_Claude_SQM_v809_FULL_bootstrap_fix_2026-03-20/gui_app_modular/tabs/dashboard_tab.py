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

from gui_app_modular.utils.ui_constants import tc
import logging
import sqlite3
from datetime import datetime

from tkinter import ttk
from ..utils.ui_constants import (
    ColumnWidth,
    FontScale,
    Spacing,
    ThemeColors,
    apply_tooltip,
    is_dark,
)
from ..utils.theme_helpers import safe_is_dark as is_dark

logger = logging.getLogger(__name__)


class DashboardTabMixin:
    """
    대시보드 탭 믹스인
    
    SQMInventoryApp 클래스에 믹스인됩니다.
    """

    def _setup_dashboard_tab(self) -> None:
        """대시보드 탭 설정 (v4.0.3: 섹션별 분리)"""
        from ..utils.constants import (
            BOTH,
            BOTTOM,
            LEFT,
            RIGHT,
            TOP,
            YES,
            E,
            N,
            S,
            W,
            X,
            Y,
            tk,
            ttk,
        )

        # === 팔레트/폰트 초기화 ===
        try:
            dark_mode = is_dark()
            _p = ThemeColors.get_palette(dark_mode)
        except (ImportError, ModuleNotFoundError):
            _p = {'bg_card': ThemeColors.get('bg_card'), 'chart_bg': ThemeColors.get('bg_card'), 'chart_grid': ThemeColors.get('chart_grid'),
                  'text_secondary': '#666666', 'tree_select_bg': ThemeColors.get('statusbar_progress'),
                  'success': ThemeColors.get('badge_db'), 'warning': '#e67e22', 'danger': ThemeColors.get('statusbar_icon_err'),
                  'statusbar_icon_warn': ThemeColors.get('statusbar_icon_warn'), 'text_primary': ThemeColors.get('text_primary')}
        try:
            dpi = self.root.winfo_fpixels('1i')
        except (ImportError, ModuleNotFoundError):
            dpi = 96
        fonts = FontScale(dpi)

        main_container = ttk.Frame(self.tab_dashboard)
        main_container.pack(fill=BOTH, expand=YES, padx=Spacing.SM, pady=Spacing.SM)

        # v4.0.3: 각 섹션을 별도 메서드로 분리
        ctx = {'ttk': ttk, 'tk': tk, '_p': _p, 'fonts': fonts,
               'main_container': main_container, 'Spacing': Spacing,
               'ColumnWidth': ColumnWidth, 'FontScale': FontScale,
               'BOTH': BOTH, 'X': X, 'Y': Y, 'YES': YES,
               'W': W, 'E': E, 'N': N, 'S': S,
               'LEFT': LEFT, 'RIGHT': RIGHT, 'TOP': TOP, 'BOTTOM': BOTTOM}
        self._setup_dash_hero(ctx)   # v7.3.0: Hero 운영 헤더
        self._setup_dash_integrity(ctx)    # v7.3.8: 정합성 패널
        self._setup_dash_period_trend(ctx) # v7.3.8: 기간별 추이
        self._setup_dash_cards(ctx)
        self._setup_dash_gauge(ctx)
        self._setup_dash_charts(ctx)
        self._setup_dash_kpi_cards(ctx)
        self._setup_dash_tonbag_table(ctx)
        self._setup_dash_alerts(ctx)
        self._setup_dash_location_zone(ctx)  # v7.0.1: 위치별 재고 현황
        self._setup_dash_activity(ctx)
    def _setup_dash_hero(self, ctx) -> None:
        """v7.3.1: Hero 운영 헤더 — GPT 배경색+컬러버튼+흐름배지 + Ruby 5단계"""
        tk   = ctx['tk']
        _p   = ctx['_p']
        main_container = ctx['main_container']

        # ── Hero 전용 고정 색상 (팔레트 완전 독립) ────────────────────
        # bg_secondary/primary는 테마마다 달라 사용 금지
        # self.current_theme (올바른 속성명) 으로 dark 판별
        dark_mode = ThemeColors.is_dark_theme(
            getattr(self, 'current_theme', 'darkly')
        )

        hero_bg  = tc('bg_secondary')   # v9.1: tc() 자동 테마
        border_c = '#334155' if dark_mode else '#2d5480'
        text_1   = '#ffffff'   # 항상 흰색
        text_2   = '#cbd5e1'   # 항상 연한 슬레이트
        primary  = '#3b82f6'   # 버튼 파란색 고정
        success  = '#22c55e'   # 버튼 초록색 고정

        hero = tk.Frame(
            main_container,
            bg=hero_bg, bd=1, relief='flat',
            highlightthickness=1,
            highlightbackground=border_c,
        )
        hero.pack(fill='x', pady=(0, 8))

        # ── 좌측: 타이틀 + 부제 + 갱신 시각 ──────────────────────────
        left = tk.Frame(hero, bg=hero_bg)
        left.pack(side='left', fill='y', padx=16, pady=12)

        tk.Label(
            left, text="📊  SQM 재고관리 운영 대시보드",
            bg=hero_bg, fg=text_1,
            font=('맑은 고딕', 14, 'bold'),
        ).pack(anchor='w')

        tk.Label(
            left, text="입고 → 판매배정 → 판매화물 결정 → 출고완료(OUTBOUND)",
            bg=hero_bg, fg=text_2,
            font=('맑은 고딕', 9),
        ).pack(anchor='w', pady=(2, 0))

        self._hero_updated_label = tk.Label(
            left, text="마지막 갱신: —",
            bg=hero_bg, fg=_p.get('text_muted', '#64748b'),
            font=('맑은 고딕', 8),
        )
        self._hero_updated_label.pack(anchor='w', pady=(2, 0))

        # ── 우측: GPT 방식 컬러 버튼 ──────────────────────────────────
        right = tk.Frame(hero, bg=hero_bg)
        right.pack(side='right', fill='y', padx=16, pady=10)

        btn_refresh = tk.Button(
            right, text="🔄 새로고침",
            bg=primary, fg=tc('text_primary'),
            font=('맑은 고딕', 9, 'bold'),
            relief='flat', bd=0, padx=10, pady=5,
            cursor='hand2',
            activebackground=_p.get('btn_outbound_hover', '#1d4ed8'),
            command=self._refresh_dashboard,
        )
        btn_refresh.pack(side='left', padx=(0, 6))
        btn_refresh.bind('<Enter>', lambda e, b=btn_refresh:
                         b.config(bg=_p.get('btn_outbound_hover', '#1d4ed8')))
        btn_refresh.bind('<Leave>', lambda e, b=btn_refresh:
                         b.config(bg=primary))

        btn_excel = tk.Button(
            right, text="📥 통합현황 Excel",
            bg=success, fg=tc('text_primary'),
            font=('맑은 고딕', 9, 'bold'),
            relief='flat', bd=0, padx=10, pady=5,
            cursor='hand2',
            activebackground=_p.get('btn_inbound_hover', '#15803d'),
            command=lambda: self._safe_call('_on_export_cargo_overview'),
        )
        btn_excel.pack(side='left')
        btn_excel.bind('<Enter>', lambda e, b=btn_excel:
                       b.config(bg=_p.get('btn_inbound_hover', '#15803d')))
        btn_excel.bind('<Leave>', lambda e, b=btn_excel:
                       b.config(bg=success))

        # ── GPT 방식: 5단계 운영 흐름 컬러 배지 (Ruby: RETURN 추가) ──
        badge_row = tk.Frame(hero, bg=hero_bg)
        badge_row.pack(fill='x', padx=16, pady=(0, 12))

        STAGES = [
            ('📦 판매가능',        _p.get('success',  '#22c55e')),
            ('📋 판매배정',        _p.get('info',     '#3b82f6')),
            ('🚛 화물결정',        _p.get('warning',  '#f59e0b')),
            ('✅ 출고완료',        _p.get('danger',   '#ef4444')),
            ('🔄 반품대기(RETURN)', '#9b59b6'),          # Ruby 추가
        ]
        for idx, (lbl, color) in enumerate(STAGES):
            tk.Label(
                badge_row, text=lbl,
                bg=color, fg=tc('text_primary'),
                font=('맑은 고딕', 8, 'bold'),
                padx=8, pady=3, relief='flat',
            ).pack(side='left')
            if idx < len(STAGES) - 1:
                tk.Label(
                    badge_row, text=' → ',
                    bg=hero_bg, fg=text_2,
                    font=('맑은 고딕', 9),
                ).pack(side='left')

        self._hero_frame = hero  # 테마 전환 시 재참조용

    def _setup_dash_cards(self, ctx) -> None:
        """섹션 1: 4단계 요약 카드 (v6.0: AVAILABLE / RESERVED / PICKED / SOLD) + TOTAL"""
        from ..utils.constants import X
        ttk, _p, fonts = ctx['ttk'], ctx['_p'], ctx['fonts']
        Spacing = ctx['Spacing']
        main_container = ctx['main_container']

        cards_frame = ttk.Frame(main_container)
        cards_frame.pack(fill=X, pady=(0, Spacing.MD))

        self._dashboard_cards = {}

        # v7.3.0: 5단계 카드 — 판매가능 / 판매배정 / 판매화물 결정 / 출고완료 / 반품대기
        card_configs = [
            ('status_available', '판매가능',         '0개', _p.get('success', '#1abc9c')),
            ('status_reserved',  '판매배정',         '0개', _p.get('primary', '#3498db')),
            ('status_picked',    '판매화물 결정',    '0개', _p.get('warning', '#e67e22')),
            ('status_sold',      '출고완료\n(OUTBOUND)', '0개', _p.get('danger', '#e74c3c')),
            ('status_return',    '반품대기\n(RETURN)',    '0개', '#9b59b6'),
        ]

        for i, (key, title, default, color) in enumerate(card_configs):
            card = self._create_dashboard_card(cards_frame, title, default, color, fonts)
            card.grid(row=0, column=i, padx=Spacing.XS, sticky='nsew')
            self._dashboard_cards[key] = card
            cards_frame.columnconfigure(i, weight=1)

        # TOTAL 바 (항상 일정)
        total_frame = ttk.Frame(cards_frame)
        total_frame.grid(row=1, column=0, columnspan=5, sticky='ew', pady=(Spacing.SM, 0))
        cards_frame.columnconfigure(0, weight=1)
        self._dashboard_total_label = ttk.Label(total_frame, text="TOTAL: 0개 / 0.0 MT", font=('맑은 고딕', 12, 'bold'))
        self._dashboard_total_label.pack(anchor='w')

    def _setup_dash_gauge(self, ctx) -> None:
        """섹션 1-2: 창고 가동률 게이지"""
        ttk = ctx['ttk']
        Spacing = ctx['Spacing']
        main_container = ctx['main_container']
        X, LEFT = ctx['X'], ctx['LEFT']
        # =====================================================
        # 1-2. 창고 가동률 게이지 (v3.6.5: ttkbootstrap Meter)
        # =====================================================
        try:
            from ..utils.constants import HAS_METER, Meter
            if HAS_METER and Meter:
                meter_frame = ttk.Frame(main_container)
                meter_frame.pack(fill=X, pady=(0, Spacing.SM))

                # 판매가능률 미터 (v5.0.7: 콤팩트 - 90px)
                self._meter_available = Meter(
                    meter_frame, bootstyle='success',
                    amountused=0, amounttotal=100,
                    metersize=90, meterthickness=6,
                    subtext='판매가능률', textright='%',
                    stripethickness=4
                )
                self._meter_available.pack(side=LEFT, padx=Spacing.MD)

                # 출고율 미터 (v5.0.7: 콤팩트 - 90px)
                self._meter_outbound = Meter(
                    meter_frame, bootstyle='warning',
                    amountused=0, amounttotal=100,
                    metersize=90, meterthickness=6,
                    subtext='출고율', textright='%',
                    stripethickness=4
                )
                self._meter_outbound.pack(side=LEFT, padx=Spacing.MD)

                # 금일 처리율 미터 (v5.0.7: 콤팩트 - 90px)
                self._meter_today = Meter(
                    meter_frame, bootstyle='info',
                    amountused=0, amounttotal=100,
                    metersize=90, meterthickness=6,
                    subtext='금일처리', textright='%',
                    stripethickness=4
                )
                self._meter_today.pack(side=LEFT, padx=Spacing.MD)

                self._has_meters = True
            else:
                self._has_meters = False
        except (RuntimeError, ValueError):
            self._has_meters = False

    def _setup_dash_integrity(self, ctx) -> None:
        """v7.3.8: 정합성 패널 — 입고총량 = 현재재고 + 출고누계."""
        ttk, tk, _p = ctx['ttk'], ctx['tk'], ctx['_p']
        mc = ctx['main_container']

        frame = ttk.LabelFrame(mc, text="🔍 재고 정합성 현황")
        frame.pack(fill='x', padx=2, pady=(0, 6))

        # ── 상단: 수치 3개 가로 배치 ──────────────────────────────
        row1 = tk.Frame(frame, bg=_p.get('bg_card', '#f8fafc'))
        row1.pack(fill='x', padx=8, pady=(6, 2))

        _bg = _p.get('bg_card', '#f8fafc')
        _c_total  = '#3b82f6'   # 파랑 — 입고 총계
        _c_cur    = '#22c55e'   # 초록 — 현재 재고
        _c_out    = '#ef4444'   # 빨강 — 출고 누계

        def _make_stat(parent, label, color, val_attr, sub_attr):
            box = tk.Frame(parent, bg=_bg, bd=1, relief='flat')
            box.pack(side='left', expand=True, fill='x', padx=4)
            tk.Label(box, text=label, bg=_bg, fg=color,
                     font=('맑은 고딕', 9, 'bold')).pack(anchor='w', padx=6, pady=(4,0))
            lbl_v = tk.Label(box, text='- MT', bg=_bg, fg=color,
                             font=('맑은 고딕', 15, 'bold'))
            lbl_v.pack(anchor='w', padx=6)
            lbl_s = tk.Label(box, text='-개', bg=_bg, fg=_p.get('text_muted','#64748b'),
                             font=('맑은 고딕', 9))
            lbl_s.pack(anchor='w', padx=6, pady=(0,4))
            setattr(self, val_attr, lbl_v)
            setattr(self, sub_attr, lbl_s)

        _make_stat(row1, "📥 총 입고 (누계)", _c_total,
                   '_integ_total_lbl', '_integ_total_sub')
        tk.Label(row1, text='=', bg=_bg, font=('맑은 고딕', 18)).pack(side='left', padx=2)
        _make_stat(row1, "📦 현재 재고", _c_cur,
                   '_integ_cur_lbl', '_integ_cur_sub')
        tk.Label(row1, text='+', bg=_bg, font=('맑은 고딕', 18)).pack(side='left', padx=2)
        _make_stat(row1, "🚢 출고 누계", _c_out,
                   '_integ_out_lbl', '_integ_out_sub')

        # ── 하단: 정합성 판정 + 드릴다운 버튼 ────────────────────
        row2 = tk.Frame(frame, bg=_bg)
        row2.pack(fill='x', padx=8, pady=(2, 6))

        self._integ_result_lbl = tk.Label(
            row2, text="정합성 확인 중...", bg=_bg,
            font=('맑은 고딕', 10, 'bold')
        )
        self._integ_result_lbl.pack(side='left', padx=4)

        self._integ_lot_lbl = tk.Label(
            row2, text="", bg=_bg,
            font=('맑은 고딕', 9), fg=_p.get('text_muted','#64748b')
        )
        self._integ_lot_lbl.pack(side='left', padx=8)

        btn_drill = ttk.Button(
            row2, text="🔎 불일치 LOT 조회",
            command=self._on_integrity_drill_down
        )
        btn_drill.pack(side='right', padx=4)
        self._integ_drill_btn = btn_drill

    def _setup_dash_period_trend(self, ctx) -> None:
        """v7.3.8: 기간별 입고 추이 패널."""
        ttk = ctx['ttk']
        mc = ctx['main_container']

        frame = ttk.LabelFrame(mc, text="📅 기간별 입고 추이")
        frame.pack(fill='x', padx=2, pady=(0, 6))

        # ── 기간 전환 버튼 바 ──────────────────────────────────────
        btn_bar = ttk.Frame(frame)
        btn_bar.pack(fill='x', padx=6, pady=(4, 0))

        self._trend_months_var = getattr(self, '_trend_months_var', None) or __import__('tkinter').IntVar(value=3)

        for label, months in [("이번달", 1), ("최근 3개월", 3), ("최근 6개월", 6), ("전체", 0)]:
            ttk.Radiobutton(
                btn_bar, text=label,
                variable=self._trend_months_var, value=months,
                command=self._refresh_dashboard_period_trend
            ).pack(side='left', padx=4)

        # ── 추이 트리뷰 (월별 행) ──────────────────────────────────
        cols = ('ym', 'lot_cnt', 'kg_mt', 'bar')
        self._trend_tree = ttk.Treeview(
            frame, columns=cols, show='headings', height=5
        )
        for cid, text, w, anchor in [
            ('ym',      '년월',       90,  'center'),
            ('lot_cnt', 'LOT 수',     70,  'center'),
            ('kg_mt',   '중량 (MT)',  100, 'e'),
            ('bar',     '비율',       200, 'w'),
        ]:
            self._trend_tree.heading(cid, text=text)
            self._trend_tree.column(cid, width=w, anchor=anchor)

        _sb = __import__('tkinter').Scrollbar(
            frame, orient='vertical', command=self._trend_tree.yview
        )
        self._trend_tree.configure(yscrollcommand=_sb.set)
        self._trend_tree.pack(side='left', fill='both', expand=True,
                               padx=(6,0), pady=(4,6))
        _sb.pack(side='right', fill='y', pady=(4,6))


    def _setup_dash_charts(self, ctx) -> None:
        """섹션 2: 알림 + 빠른 액션"""
        from ..utils.constants import BOTH, LEFT, RIGHT, YES, X
        ttk, tk, _p = ctx['ttk'], ctx['tk'], ctx['_p']
        Spacing = ctx['Spacing']
        main_container = ctx['main_container']
        # =====================================================
        # 2. 중간: 알림 + 빠른 액션
        # =====================================================

        # v3.8.4: Excel 내보내기 버튼 바
        export_bar = ttk.Frame(main_container)
        export_bar.pack(fill=X, pady=(0, 4))
        btn_dash_export = ttk.Button(
            export_bar, text="📥 Excel 내보내기 (통합현황)",
            command=lambda: self._on_export_click(option=6)
        )
        btn_dash_export.pack(side=RIGHT)
        apply_tooltip(btn_dash_export, "현재 재고·통계 데이터를 Excel(통합현황) 파일로 내보냅니다. 재고 메뉴의 내보내기 옵션 6과 동일합니다.")

        middle_frame = ttk.Frame(main_container)
        middle_frame.pack(fill=BOTH, expand=YES, pady=(0, Spacing.MD))
        middle_frame.columnconfigure(0, weight=2)
        middle_frame.columnconfigure(1, weight=1)
        middle_frame.columnconfigure(2, weight=1)
        middle_frame.rowconfigure(0, weight=1)

        # 2-1. 알림 패널 (v3.6.0 개선)
        alert_frame = ttk.LabelFrame(middle_frame, text="⚠️ 알림 및 경고")
        alert_frame.grid(row=0, column=0, sticky='nsew', padx=(0, Spacing.SM))
        apply_tooltip(alert_frame, "재고 부족, 무결성 경고 등 확인이 필요한 항목이 표시됩니다. 항목을 더블클릭하면 해당 LOT나 화면으로 이동할 수 있습니다.")

        # 알림 리스트 (v5.0.7: 콤팩트 - height=6, font=11)
        self.alert_listbox = tk.Listbox(
            alert_frame,
            height=6,
            font=('맑은 고딕', 11),
            selectbackground=_p.get('tree_select_bg', ThemeColors.get('statusbar_progress')),
            selectforeground=_p.get('tree_select_fg', 'white'),
            activestyle='none',
            bd=1,
            relief='solid',
            highlightthickness=0
        )
        self.alert_listbox.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)

        # 스크롤바 추가
        alert_scrollbar = tk.Scrollbar(alert_frame, orient='vertical', command=self.alert_listbox.yview)
        self.alert_listbox.configure(yscrollcommand=alert_scrollbar.set)

        # 알림 더블클릭 이벤트
        self.alert_listbox.bind('<Double-1>', self._on_alert_double_click)

        # 2-2. 입출고 추이 (v3.6.0: 빠른 액션 → 차트로 변경)
        chart_frame = ttk.LabelFrame(middle_frame, text="📈 최근 7일 입출고")
        chart_frame.grid(row=0, column=1, sticky='nsew')
        apply_tooltip(chart_frame, "최근 7일간 일별 입고·출고량을 막대 그래프로 표시합니다. 파란색=입고, 주황색=출고.")

        # 간단한 텍스트 기반 차트 (v5.0.7: 콤팩트 - 120px)
        self.chart_canvas = tk.Canvas(chart_frame, bg=_p.get('chart_bg', 'white'), height=120, highlightthickness=0)
        self.chart_canvas.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)

        # 범례 (v5.0.7: 콤팩트 - 폰트 11pt)
        _chart_bg = _p.get('chart_bg', 'white')
        legend_frame = tk.Frame(chart_frame, bg=_chart_bg)
        legend_frame.pack(fill=X, padx=Spacing.XS)

        tk.Label(legend_frame, text="■", fg=_p.get('success', ThemeColors.get('badge_db')), bg=_chart_bg, font=('', 11)).pack(side=LEFT)
        tk.Label(legend_frame, text="입고", bg=_chart_bg, font=('맑은 고딕', 10)).pack(side=LEFT, padx=(2, 10))
        tk.Label(legend_frame, text="■", fg=_p.get('warning', '#e67e22'), bg=_chart_bg, font=('', 11)).pack(side=LEFT)
        tk.Label(legend_frame, text="출고", bg=_chart_bg, font=('맑은 고딕', 10)).pack(side=LEFT, padx=(2, 0))

        # 제품별 재고 비율 도넛차트 — 삭제됨 (사장님 지시)

        # 2-3. v6.12.1: 반품률 요약 패널
        return_frame = ttk.LabelFrame(middle_frame, text="🔄 반품 현황")
        return_frame.grid(row=0, column=2, sticky='nsew', padx=(Spacing.SM, 0))
        apply_tooltip(return_frame, "최근 반품 건수, 반품률(출고 대비), 상위 반품 사유를 표시합니다.")

        self._return_info_text = tk.Text(
            return_frame, height=6, font=('맑은 고딕', 10),
            wrap='word', state='disabled', relief='flat',
            bg=_p.get('chart_bg', 'white'),
            highlightthickness=0, bd=0
        )
        self._return_info_text.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)

    def _setup_dash_kpi_cards(self, ctx) -> None:
        """v6.7.2+v6.7.3: 스캔 실패율 + LOT 평균 재고기간 KPI 카드."""
        from ..utils.constants import BOTH, YES, X
        ttk = ctx['ttk']
        tk  = ctx['tk']
        Spacing = ctx['Spacing']
        main_container = ctx['main_container']
        _p = ctx.get('_p', {})
        try:
            from ..utils.ui_constants import ThemeColors
            dark_mode = is_dark()
            _p = ThemeColors.get_palette(dark_mode)
        except Exception:
            logger.debug("[SUPPRESSED] exception in dashboard_tab.py")  # noqa

        kpi_frame = ttk.Frame(main_container)
        kpi_frame.pack(fill=X, pady=(0, Spacing.SM))
        kpi_frame.columnconfigure(0, weight=1)
        kpi_frame.columnconfigure(1, weight=1)
        kpi_frame.columnconfigure(2, weight=1)

        # [P1] v6.8.1: 위치 미배정 톤백 KPI 카드
        # 입고 후 현장 배치가 안 된 톤백 수를 실시간 표시
        loc_frame = ttk.LabelFrame(kpi_frame, text="📍 위치 미배정 톤백")
        loc_frame.grid(row=0, column=2, sticky='nsew', padx=(Spacing.SM, 0))
        self._unassigned_loc_text = tk.Text(
            loc_frame, height=4, font=('맑은 고딕', 10),
            wrap='word', state='disabled', relief='flat',
            bg=_p.get('chart_bg', 'white'), highlightthickness=0, bd=0
        )
        self._unassigned_loc_text.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)

        # 스캔 실패율 카드
        scan_frame = ttk.LabelFrame(kpi_frame, text="🔍 스캔 실패율 (최근 30일)")
        scan_frame.grid(row=0, column=0, sticky='nsew', padx=(0, Spacing.SM))
        self._scan_fail_text = tk.Text(
            scan_frame, height=4, font=('맑은 고딕', 10),
            wrap='word', state='disabled', relief='flat',
            bg=_p.get('chart_bg', 'white'), highlightthickness=0, bd=0
        )
        self._scan_fail_text.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)

        # LOT 평균 재고기간 카드
        days_frame = ttk.LabelFrame(kpi_frame, text="📅 LOT 평균 재고기간")
        days_frame.grid(row=0, column=1, sticky='nsew')
        self._avg_lot_days_text = tk.Text(
            days_frame, height=4, font=('맑은 고딕', 10),
            wrap='word', state='disabled', relief='flat',
            bg=_p.get('chart_bg', 'white'), highlightthickness=0, bd=0
        )
        self._avg_lot_days_text.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)

    def _setup_dash_tonbag_table(self, ctx) -> None:
        """섹션 3: 하단 제품별 요약 + 최근 활동"""
        from ..utils.constants import BOTH, LEFT, YES
        ttk = ctx['ttk']
        Spacing = ctx['Spacing']
        main_container = ctx['main_container']
        # =====================================================
        # 3. 하단: 제품별 요약 (v4.0.5: 전체 너비, 톤백/샘플 구분)
        # =====================================================
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill=BOTH, expand=YES)
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.rowconfigure(0, weight=1)

        # 제품별 요약 (전체 너비)
        product_frame = ttk.LabelFrame(bottom_frame, text="📈 제품별 현황")
        product_frame.grid(row=0, column=0, sticky='nsew')
        apply_tooltip(product_frame, "제품별 LOT 수, 톤백 수, 톤백/샘플 kg, 총 kg 등을 표시합니다. LOT 단위/톤백 상세 전환으로 보기 방식을 바꿀 수 있습니다.")

        # v3.8.7: LOT/톤백 전환 라디오 (v5.0.7: 콤팩트 - font=12)
        from ..utils.constants import tk as _tk
        self._dash_radio_frame = _tk.Frame(product_frame)
        self._dash_view_mode = _tk.StringVar(value='lot')
        _rb_lot = _tk.Radiobutton(self._dash_radio_frame, text="📦 LOT 단위", variable=self._dash_view_mode,
                        value='lot', command=self._refresh_dashboard_products,
                        font=('', 12, 'bold'))
        _rb_lot.pack(side=LEFT, padx=(0, 10))
        apply_tooltip(_rb_lot, "제품별로 LOT 수, 톤백 수, 총 kg 등을 요약해서 표시합니다.")
        _rb_tb = _tk.Radiobutton(self._dash_radio_frame, text="🎒 톤백 상세", variable=self._dash_view_mode,
                        value='tonbag', command=self._refresh_dashboard_products,
                        font=('', 12))
        _rb_tb.pack(side=LEFT)
        apply_tooltip(_rb_tb, "제품별로 일반 톤백과 샘플 톤백을 구분한 상세 수치를 표시합니다.")

        # v4.0.5: 톤백/샘플 구분 컬럼 (v5.0.7: 콤팩트 - height=6)
        columns = ("product", "lots", "tonbag_kg", "tonbag_cnt",
                   "sample_kg", "sample_cnt", "total_kg", "total_cnt")
        self.tree_dashboard_product = ttk.Treeview(
            product_frame, columns=columns, show="headings", height=6
        )

        col_defs = [
            ("product",    "Product",     120, "w"),
            ("lots",       "LOT수",        60, "center"),
            ("tonbag_kg",  "톤백(kg)",     100, "e"),
            ("tonbag_cnt", "톤백수",        60, "center"),
            ("sample_kg",  "샘플(kg)",      80, "e"),
            ("sample_cnt", "샘플수",        60, "center"),
            ("total_kg",   "총무게(kg)",   110, "e"),
            ("total_cnt",  "총개수",        60, "center"),
        ]
        for col_id, text, width, anchor in col_defs:
            self.tree_dashboard_product.heading(col_id, text=text, anchor='center')
            self.tree_dashboard_product.column(col_id, width=width, anchor=anchor)

        self.tree_dashboard_product.pack(fill=BOTH, expand=YES, padx=Spacing.XS, pady=Spacing.XS)

    def _setup_dash_alerts(self, ctx) -> None:
        """섹션 4: 하단 상태바"""
        from ..utils.constants import LEFT, RIGHT, X
        ttk, tk = ctx['ttk'], ctx['tk']
        fonts, Spacing = ctx['fonts'], ctx['Spacing']
        main_container = ctx['main_container']
        # =====================================================
        # 4. 하단 상태바
        # =====================================================
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill=X, pady=(Spacing.SM, 0))

        self.dashboard_status = ttk.Label(
            status_frame,
            text="마지막 갱신: -",
            font=fonts.small()
        )
        self.dashboard_status.pack(side=LEFT)

        # 자동 새로고침 체크박스
        self.auto_refresh_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            status_frame,
            text="자동 새로고침 (30초)",
            variable=self.auto_refresh_var,
            command=self._toggle_auto_refresh
        ).pack(side=RIGHT)

        # 자동 새로고침 타이머 시작
        self._auto_refresh_job = None
        self._start_auto_refresh()

    # ══════════════════════════════════════════════════════════
    # v7.0.1: 위치별 재고 현황 위젯
    # ══════════════════════════════════════════════════════════

    def _setup_dash_location_zone(self, ctx) -> None:
        """구역별 톤백 수량/중량 위젯"""
        from ..utils.constants import ttk

        # tkinter LabelFrame 경로에서는 padding 옵션 미지원일 수 있어 pack padding으로 대체
        frame = ttk.LabelFrame(ctx['main_container'], text="📍 구역별 재고 현황")
        frame.pack(fill='x', padx=5, pady=5)

        # 트리뷰 (구역, 톤백 수, 중량)
        cols = ('zone', 'count', 'weight_mt')
        self._location_zone_tree = ttk.Treeview(
            frame, columns=cols, show='headings', height=5
        )
        self._location_zone_tree.heading('zone', text='구역')
        self._location_zone_tree.heading('count', text='톤백 수')
        self._location_zone_tree.heading('weight_mt', text='중량 (MT)')

        self._location_zone_tree.column('zone', width=80, anchor='center')
        self._location_zone_tree.column('count', width=80, anchor='center')
        self._location_zone_tree.column('weight_mt', width=100, anchor='center')

        self._location_zone_tree.pack(fill='x', padx=5, pady=5)

        # 하단 요약 라벨
        self._location_zone_summary = ttk.Label(frame, text="", font=('', 9))
        self._location_zone_summary.pack(anchor='w', padx=5)

    def _refresh_dashboard_location_zone(self) -> None:
        """위치별 재고 위젯 새로고침"""
        try:
            if not hasattr(self, '_location_zone_tree'):
                return

            stats = self._get_location_zone_stats()

            # 기존 항목 삭제
            for item in self._location_zone_tree.get_children():
                self._location_zone_tree.delete(item)

            # 구역별 데이터 삽입
            for zone in stats['zones']:
                weight_mt = zone['weight'] / 1000  # kg → MT
                self._location_zone_tree.insert('', 'end', values=(
                    zone['zone'],
                    f"{zone['count']:,}",
                    f"{weight_mt:,.1f}"
                ))

            # 미지정 톤백 표시
            no_loc = stats['no_location']
            if no_loc['count'] > 0:
                weight_mt = no_loc['weight'] / 1000
                self._location_zone_tree.insert('', 'end', values=(
                    '(미지정)',
                    f"{no_loc['count']:,}",
                    f"{weight_mt:,.1f}"
                ), tags=('warning',))
                self._location_zone_tree.tag_configure('warning', foreground=tc('danger'))

            # 요약
            total = stats['total_locations'] + no_loc['count']
            summary = f"총 {stats['total_zones']}개 구역, {total}개 톤백"
            if no_loc['count'] > 0:
                summary += f" (미지정 {no_loc['count']}개)"
            self._location_zone_summary.config(text=summary)

        except Exception as e:
            logger.debug(f"location zone refresh error: {e}")

    def _setup_dash_activity(self, ctx) -> None:
        """섹션 5: 초기 대시보드 데이터 로드"""
        self._refresh_dashboard()

    def _create_dashboard_card(self, parent, title: str, value: str, color: str, fonts=None) -> 'ttk.Frame':
        """대시보드 카드 생성 (v3.8.4: 모던 플랫 디자인)"""
        from ..utils.constants import tk
        from ..utils.ui_constants import FontScale

        # === UI 통일성: 간격/폰트 표준화 ===
        if fonts is None:
            try:
                dpi = parent.winfo_fpixels('1i')
            except (ImportError, ModuleNotFoundError):
                dpi = 96
            fonts = FontScale(dpi)

        # v3.6.3: 팔레트 기반 카드 배경색
        try:
            _dk = is_dark()
            _cp = ThemeColors.get_palette(_dk)
        except (ImportError, ModuleNotFoundError):
            _cp = {'bg_card': ThemeColors.get('bg_card'), 'text_secondary': '#666666'}

        _card_bg = _cp.get('bg_card', ThemeColors.get('bg_card'))
        _card_fg = _cp.get('text_secondary', '#666666')
        _border_color = _cp.get('border', '#e0e0e0')

        # ═══ 외부 프레임 (테두리 역할) ═══
        outer = tk.Frame(parent, bg=_border_color, bd=0)

        # ═══ 내부 레이아웃: 좌측 색바 + 콘텐츠 ═══
        inner = tk.Frame(outer, bg=_card_bg, bd=0)
        inner.pack(fill='both', expand=True, padx=1, pady=1)

        # 좌측 색상 바 (세로 4px — 모던 스타일)
        color_bar = tk.Frame(inner, bg=color, width=4)
        color_bar.pack(side='left', fill='y')
        color_bar.pack_propagate(False)

        # 콘텐츠 영역 (v5.0.7: 콤팩트 - 패딩 축소)
        content = tk.Frame(inner, bg=_card_bg, padx=10, pady=6)
        content.pack(side='left', fill='both', expand=True)

        # 제목 (v5.0.7: 콤팩트 - 11pt)
        title_label = tk.Label(
            content,
            text=title,
            font=('맑은 고딕', 11),
            bg=_card_bg,
            fg=_card_fg
        )
        title_label.pack(anchor='w')

        # 값 (v5.0.7: 콤팩트 - 20pt)
        value_label = tk.Label(
            content,
            text=value,
            font=('맑은 고딕', 20, 'bold'),
            bg=_card_bg,
            fg=color
        )
        value_label.pack(anchor='w', pady=(2, 0))

        # 서브텍스트 (전일대비 변화량 등)
        sub_label = tk.Label(
            content,
            text='',
            font=('맑은 고딕', 13),
            bg=_card_bg,
            fg=_card_fg
        )
        sub_label.pack(anchor='w', pady=(2, 0))

        # 레이블 저장 (나중에 업데이트용)
        outer.value_label = value_label
        outer.sub_label = sub_label
        outer.color = color

        return outer


    def _refresh_dashboard_integrity(self) -> None:
        """v7.3.8: 정합성 패널 갱신."""
        try:
            d = self._get_integrity_summary()
            def _mt(kg): return f"{kg/1000:.1f} MT"
            def _cnt(n):  return f"톤백 {n:,}개"

            self._integ_total_lbl.config(text=_mt(d['total_kg']))
            self._integ_total_sub.config(text=f"LOT {d['lot_cnt']:,}개 | 톤백 {d['total_cnt']:,}개")
            self._integ_cur_lbl.config(text=_mt(d['cur_kg']))
            self._integ_cur_sub.config(text=_cnt(d['cur_cnt']))
            self._integ_out_lbl.config(text=_mt(d['out_kg']))
            self._integ_out_sub.config(text=_cnt(d['out_cnt']))

            if d['ok']:
                self._integ_result_lbl.config(
                    text="✅ 정합성 OK — 입고합계 = 현재재고 + 출고누계",
                    fg=tc('success')
                )
                self._integ_lot_lbl.config(text=f"차이: {abs(d['diff_kg']):.1f} kg 이내")
            else:
                self._integ_result_lbl.config(
                    text=f"❌ 불일치 — 차이: {d['diff_kg']:+.1f} kg",
                    fg=tc('danger')
                )
                self._integ_lot_lbl.config(text="👉 [불일치 LOT 조회] 버튼으로 확인하세요")
        except Exception as e:
            logger.debug(f"정합성 갱신 오류: {e}")

    def _refresh_dashboard_period_trend(self) -> None:
        """v7.3.8: 기간별 입고 추이 갱신."""
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
            max_kg = max((r['kg'] for r in rows), default=1) or 1
            for r in rows:
                bar_len = int(r['kg'] / max_kg * 30)
                bar = '█' * bar_len
                self._trend_tree.insert('', 'end', values=(
                    r['ym'],
                    f"{r['lot_cnt']:,}",
                    f"{r['kg']/1000:.1f}",
                    bar
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
                tree.heading(cid, text=txt)
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

            self._refresh_dashboard_cards()
            self._refresh_dashboard_integrity()       # v7.3.8
            self._refresh_dashboard_period_trend()    # v7.3.8
            self._refresh_dashboard_alerts()
            self._refresh_dashboard_products()
            self._refresh_dashboard_location_zone()  # v7.0.1
            self._refresh_dashboard_chart()
            self._refresh_dashboard_return_rate()
            self._refresh_dashboard_scan_fail()              # v6.7.2
            self._refresh_dashboard_avg_lot_days()           # v6.7.3
            self._refresh_dashboard_unassigned_location()    # [P1] v6.8.1

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
        """v7.3.0: 5단계 카드 새로고침 (AVAILABLE/RESERVED/PICKED/OUTBOUND/RETURN) + TOTAL"""
        try:
            if not hasattr(self, '_dashboard_cards') or not self._dashboard_cards:
                return

            stats = self._get_status_four_phase_stats()
            total_cnt = stats.get('total_cnt', 0) or 0
            total_kg = stats.get('total_kg', 0) or 0
            total_mt = total_kg / 1000.0

            def _set_card(key: str, cnt: int, kg: float) -> None:
                card = self._dashboard_cards.get(key)
                if not card:
                    return
                card.value_label.config(text=f"{cnt}개")
                if hasattr(card, 'sub_label'):
                    card.sub_label.config(text=f"{kg/1000:,.1f} MT")

            _set_card('status_available', stats.get('available_cnt', 0), stats.get('available_kg', 0))
            _set_card('status_reserved', stats.get('reserved_cnt', 0), stats.get('reserved_kg', 0))
            _set_card('status_picked', stats.get('picked_cnt', 0), stats.get('picked_kg', 0))
            # v7.2.0: OUTBOUND + SOLD 통합
            _set_card('status_sold', stats.get('outbound_cnt', stats.get('sold_cnt', 0)),
                      stats.get('outbound_kg', stats.get('sold_kg', 0)))
            # v7.2.0: RETURN 카드 신규
            _set_card('status_return', stats.get('return_cnt', 0), stats.get('return_kg', 0))

            if hasattr(self, '_dashboard_total_label'):
                self._dashboard_total_label.config(text=f"TOTAL: {total_cnt}개 / {total_mt:,.1f} MT")

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
                return

            for alert in alerts:
                icon = alert.get('icon', '⚠️')
                msg = alert.get('message', '')
                self.alert_listbox.insert(END, f"{icon} {msg}")

                # 심각도에 따른 색상 (v3.6.3: 팔레트)
                idx = self.alert_listbox.size() - 1
                severity = alert.get('severity', 'info')
                try:
                    _dk = is_dark()
                    _ap = ThemeColors.get_palette(_dk)
                except (ImportError, ModuleNotFoundError):
                    _ap = {'danger': ThemeColors.get('statusbar_icon_err'), 'warning': ThemeColors.get('statusbar_icon_warn')}
                if severity == 'error':
                    self.alert_listbox.itemconfig(idx, fg=_ap.get('danger', ThemeColors.get('statusbar_icon_err')))
                elif severity == 'warning':
                    self.alert_listbox.itemconfig(idx, fg=_ap.get('warning', ThemeColors.get('statusbar_icon_warn')))

        except (ImportError, ModuleNotFoundError) as e:
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

            # 합계용
            sum_lots = sum_tb_kg = sum_tb_cnt = 0
            sum_sp_kg = sum_sp_cnt = sum_total_kg = sum_total_cnt = 0

            for p in products:
                name = p.get('product', 'Unknown') or 'Unknown'
                lots = p.get('lot_count', 0)
                tb_kg = p.get('tonbag_kg', 0)
                tb_cnt = p.get('tonbag_cnt', 0)
                sp_kg = p.get('sample_kg', 0)
                sp_cnt = p.get('sample_cnt', 0)
                t_kg = p.get('total_kg', 0)
                t_cnt = p.get('total_cnt', 0)

                self.tree_dashboard_product.insert('', END, values=(
                    name, lots,
                    f"{tb_kg:,.0f}", tb_cnt,
                    f"{sp_kg:,.0f}", sp_cnt,
                    f"{t_kg:,.0f}", t_cnt
                ))

                sum_lots += lots
                sum_tb_kg += tb_kg; sum_tb_cnt += tb_cnt
                sum_sp_kg += sp_kg; sum_sp_cnt += sp_cnt
                sum_total_kg += t_kg; sum_total_cnt += t_cnt

            # 합계 행
            if products:
                self.tree_dashboard_product.insert('', END, values=(
                    '합계', sum_lots,
                    f"{sum_tb_kg:,.0f}", sum_tb_cnt,
                    f"{sum_sp_kg:,.0f}", sum_sp_cnt,
                    f"{sum_total_kg:,.0f}", sum_total_cnt
                ), tags=('total',))
                self.tree_dashboard_product.tag_configure('total', font=('', 13, 'bold'))

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
                dark_mode = is_dark()
                c_in  = '#22c55e' if dark_mode else '#16a34a'
                c_out = '#f97316' if dark_mode else '#ea580c'
                c_txt = '#cbd5e1' if dark_mode else '#334155'
                c_grid= '#334155' if dark_mode else '#e2e8f0'
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
        """스캔 실패율 KPI 갱신 (stub)."""
        pass

    def _refresh_dashboard_avg_lot_days(self) -> None:
        """LOT 평균 재고기간 KPI 갱신 (stub)."""
        pass

    def _refresh_dashboard_unassigned_location(self) -> None:
        """위치 미배정 톤백 KPI 갱신 (stub)."""
        pass

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
