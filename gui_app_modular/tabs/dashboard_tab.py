# -*- coding: utf-8 -*-
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

import sqlite3
from ..utils.ui_constants import ThemeColors, FontScale, Spacing, ColumnWidth
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DashboardTabMixin:
    """
    대시보드 탭 믹스인
    
    SQMInventoryApp 클래스에 믹스인됩니다.
    """
    
    def _setup_dashboard_tab(self) -> None:
        """대시보드 탭 설정 (v4.0.3: 섹션별 분리)"""
        from ..utils.constants import ttk, tk, BOTH, X, Y, YES, W, E, N, S, LEFT, RIGHT, TOP, BOTTOM
        
        # === 팔레트/폰트 초기화 ===
        try:
            _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
            _p = ThemeColors.get_palette(_is_dark)
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
        self._setup_dash_cards(ctx)
        self._setup_dash_gauge(ctx)
        self._setup_dash_charts(ctx)
        self._setup_dash_tonbag_table(ctx)
        self._setup_dash_alerts(ctx)
        self._setup_dash_activity(ctx)
    def _setup_dash_cards(self, ctx) -> None:
        """섹션 1: 요약 카드"""
        from ..utils.constants import X
        ttk, _p, fonts = ctx['ttk'], ctx['_p'], ctx['fonts']
        Spacing = ctx['Spacing']
        main_container = ctx['main_container']

        cards_frame = ttk.Frame(main_container)
        cards_frame.pack(fill=X, pady=(0, Spacing.MD))
        
        # 카드 스타일 설정
        self._dashboard_cards = {}
        
        card_configs = [
            ('total_weight', '📦 총 재고', '0 kg', _p.get('info', ThemeColors.get('statusbar_progress'))),
            ('total_lots', '📋 총 LOT', '0개', _p.get('success', ThemeColors.get('statusbar_icon_ok'))),
            ('today_inbound', '📥 금일 입고', '0 kg', _p.get('primary', '#9b59b6')),
            ('today_outbound', '📤 금일 출고', '0 kg', _p.get('warning', '#e67e22')),
            ('available_tonbags', '🎒 가용 톤백', '0개', _p.get('badge_db', '#1abc9c')),
        ]
        
        for i, (key, title, default, color) in enumerate(card_configs):
            card = self._create_dashboard_card(cards_frame, title, default, color, fonts)
            card.grid(row=0, column=i, padx=Spacing.XS, sticky='nsew')
            self._dashboard_cards[key] = card
            cards_frame.columnconfigure(i, weight=1)
        
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
            from ..utils.constants import Meter, HAS_METER
            if HAS_METER and Meter:
                meter_frame = ttk.Frame(main_container)
                meter_frame.pack(fill=X, pady=(0, Spacing.SM))
                
                # 가용률 미터 (v5.0.7: 콤팩트 - 90px)
                self._meter_available = Meter(
                    meter_frame, bootstyle='success',
                    amountused=0, amounttotal=100,
                    metersize=90, meterthickness=6,
                    subtext='가용률', textright='%',
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
        
    def _setup_dash_charts(self, ctx) -> None:
        """섹션 2: 알림 + 빠른 액션"""
        from ..utils.constants import BOTH, X, Y, YES, LEFT, RIGHT
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
        
        middle_frame = ttk.Frame(main_container)
        middle_frame.pack(fill=BOTH, expand=YES, pady=(0, Spacing.MD))
        middle_frame.columnconfigure(0, weight=2)
        middle_frame.columnconfigure(1, weight=1)
        middle_frame.columnconfigure(2, weight=1)
        middle_frame.rowconfigure(0, weight=1)
        
        # 2-1. 알림 패널 (v3.6.0 개선)
        alert_frame = ttk.LabelFrame(middle_frame, text="⚠️ 알림 및 경고")
        alert_frame.grid(row=0, column=0, sticky='nsew', padx=(0, Spacing.SM))
        
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
        alert_scrollbar = ttk.Scrollbar(alert_frame, orient='vertical', command=self.alert_listbox.yview)
        self.alert_listbox.configure(yscrollcommand=alert_scrollbar.set)
        
        # 알림 더블클릭 이벤트
        self.alert_listbox.bind('<Double-1>', self._on_alert_double_click)
        
        # 2-2. 입출고 추이 (v3.6.0: 빠른 액션 → 차트로 변경)
        chart_frame = ttk.LabelFrame(middle_frame, text="📈 최근 7일 입출고")
        chart_frame.grid(row=0, column=1, sticky='nsew')
        
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
        
    def _setup_dash_tonbag_table(self, ctx) -> None:
        """섹션 3: 하단 제품별 요약 + 최근 활동"""
        from ..utils.constants import BOTH, X, Y, YES, W, E, N, S, LEFT, RIGHT
        ttk, tk, _p = ctx['ttk'], ctx['tk'], ctx['_p']
        fonts, Spacing = ctx['fonts'], ctx['Spacing']
        ColumnWidth = ctx['ColumnWidth']
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
        
        # v3.8.7: LOT/톤백 전환 라디오 (v5.0.7: 콤팩트 - font=12)
        from ..utils.constants import tk as _tk
        self._dash_radio_frame = _tk.Frame(product_frame)
        self._dash_view_mode = _tk.StringVar(value='lot')
        _tk.Radiobutton(self._dash_radio_frame, text="📦 LOT 단위", variable=self._dash_view_mode,
                        value='lot', command=self._refresh_dashboard_products,
                        font=('', 12, 'bold')).pack(side=LEFT, padx=(0, 10))
        _tk.Radiobutton(self._dash_radio_frame, text="🎒 톤백 상세", variable=self._dash_view_mode,
                        value='tonbag', command=self._refresh_dashboard_products,
                        font=('', 12)).pack(side=LEFT)
        
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
        from ..utils.constants import X, LEFT, RIGHT
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

    def _setup_dash_activity(self, ctx) -> None:
        """섹션 5: 초기 대시보드 데이터 로드"""
        self._refresh_dashboard()
    
    def _create_dashboard_card(self, parent, title: str, value: str, color: str, fonts=None) -> 'ttk.Frame':
        """대시보드 카드 생성 (v3.8.4: 모던 플랫 디자인)"""
        from ..utils.constants import ttk, tk, W, E, N, S, X, Y, LEFT
        from ..utils.ui_constants import Spacing, FontScale
        
        # === UI 통일성: 간격/폰트 표준화 ===
        if fonts is None:
            try:
                dpi = parent.winfo_fpixels('1i')
            except (ImportError, ModuleNotFoundError):
                dpi = 96
            fonts = FontScale(dpi)
        
        # v3.6.3: 팔레트 기반 카드 배경색
        try:
            _dk = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
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
    
    def _refresh_dashboard(self) -> None:
        """대시보드 데이터 새로고침 (v4.0.4: 메인 스레드 직접 실행)"""
        try:
            if not hasattr(self, '_dashboard_cards'):
                return
            
            self._refresh_dashboard_cards()
            self._refresh_dashboard_alerts()
            self._refresh_dashboard_products()
            self._refresh_dashboard_chart()
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if hasattr(self, 'dashboard_status'):
                self.dashboard_status.config(text=f"마지막 갱신: {now}")
            
            logger.debug("대시보드 새로고침 완료")
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"대시보드 새로고침 오류: {e}")
    
    def _refresh_dashboard_cards(self) -> None:
        """v4.0.5 Phase3: 요약 카드 새로고침 — 톤백/샘플 구분"""
        try:
            if not hasattr(self, '_dashboard_cards') or not self._dashboard_cards:
                return
            
            summary = self.engine.get_inventory_summary()
            if not summary:
                return
            
            # 톤백/샘플 구분 통계
            ts = self._get_tonbag_sample_breakdown()
            
            # ── 총 재고 카드 ──
            total_weight = summary.get('available_weight_kg', 0)
            self._dashboard_cards['total_weight'].value_label.config(
                text=f"{total_weight:,.0f} kg"
            )
            if hasattr(self._dashboard_cards['total_weight'], 'sub_label'):
                self._dashboard_cards['total_weight'].sub_label.config(
                    text=f"톤백 {ts['tonbag_kg']:,.0f}kg({ts['tonbag_cnt']}개) | "
                         f"샘플 {ts['sample_kg']:,.0f}kg({ts['sample_cnt']}개)"
                )
            
            # ── 총 LOT 카드 ──
            total_lots = summary.get('total_lots', 0)
            available_lots = summary.get('available_lots', total_lots)
            self._dashboard_cards['total_lots'].value_label.config(
                text=f"{total_lots}개"
            )
            if hasattr(self._dashboard_cards['total_lots'], 'sub_label'):
                pct = int(available_lots / max(total_lots, 1) * 100)
                self._dashboard_cards['total_lots'].sub_label.config(
                    text=f"가용 {available_lots}개 ({pct}%)"
                )
            
            # ── 금일 입고/출고 카드 — 톤백/샘플 구분 ──
            today = datetime.now().strftime('%Y-%m-%d')
            today_ts = self._get_today_tonbag_sample_stats(today)
            
            # v4.1.9: 등록 기준 (created_at)
            inb_created = today_ts.get('inbound_created', {})
            created_kg = inb_created.get('tonbag_kg', 0) + inb_created.get('sample_kg', 0)
            created_cnt = inb_created.get('tonbag_cnt', 0) + inb_created.get('sample_cnt', 0)
            
            # v4.1.9: 입항 기준 (arrival_date)
            inb_arrival = today_ts.get('inbound_arrival', {})
            arrival_kg = inb_arrival.get('tonbag_kg', 0) + inb_arrival.get('sample_kg', 0)
            arrival_cnt = inb_arrival.get('tonbag_cnt', 0) + inb_arrival.get('sample_cnt', 0)
            
            # 메인 표시: 등록 기준
            self._dashboard_cards['today_inbound'].value_label.config(
                text=f"{created_kg:,.0f} kg"
            )
            
            # 서브 레이블: 등록 + 입항 구분 표시
            if hasattr(self._dashboard_cards['today_inbound'], 'sub_label'):
                if created_kg > 0 or arrival_kg > 0:
                    sub_text = f"등록: {created_kg:,.0f}kg ({created_cnt}개)"
                    if arrival_kg != created_kg:  # 입항 수치가 다르면 함께 표시
                        sub_text += f"\n입항: {arrival_kg:,.0f}kg ({arrival_cnt}개)"
                    self._dashboard_cards['today_inbound'].sub_label.config(text=sub_text)
                else:
                    self._dashboard_cards['today_inbound'].sub_label.config(text="금일 입고 없음")
            
            outb = today_ts.get('outbound', {})
            outbound_kg = outb.get('total_kg', 0)
            self._dashboard_cards['today_outbound'].value_label.config(
                text=f"{outbound_kg:,.0f} kg"
            )
            if hasattr(self._dashboard_cards['today_outbound'], 'sub_label'):
                if outbound_kg > 0:
                    self._dashboard_cards['today_outbound'].sub_label.config(
                        text=f"{outbound_kg/1000:,.1f} MT ({outb.get('total_cnt',0)}건)"
                    )
                else:
                    self._dashboard_cards['today_outbound'].sub_label.config(text="금일 출고 없음")
            
            # ── 가용 톤백 카드 ──
            self._dashboard_cards['available_tonbags'].value_label.config(
                text=f"{ts['total_cnt']}개"
            )
            if hasattr(self._dashboard_cards['available_tonbags'], 'sub_label'):
                self._dashboard_cards['available_tonbags'].sub_label.config(
                    text=f"톤백 {ts['tonbag_cnt']}개 | 샘플 {ts['sample_cnt']}개"
                )
            
            # v3.6.5: Meter 게이지 업데이트
            if getattr(self, '_has_meters', False):
                try:
                    avail_pct = int((summary.get('available_lots', total_lots) / max(total_lots, 1)) * 100)
                    self._meter_available.configure(amountused=min(avail_pct, 100))
                    
                    picked = summary.get('picked_lots', 0)
                    out_pct = int((picked / max(total_lots, 1)) * 100)
                    self._meter_outbound.configure(amountused=min(out_pct, 100))
                    
                    # v4.1.9: created_kg 사용
                    today_total = created_kg + outbound_kg
                    daily_avg = max(total_weight * 0.02, 1)
                    today_pct = int((today_total / daily_avg) * 100)
                    self._meter_today.configure(amountused=min(today_pct, 100))
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
                    _dk = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
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
        from ..utils.constants import END, X
        
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
