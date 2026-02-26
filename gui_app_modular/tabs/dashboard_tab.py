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
from ..utils.ui_constants import ThemeColors, FontScale, Spacing, ColumnWidth, apply_tooltip
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
        self._setup_dash_location_zone(ctx)  # v7.0.1: 위치별 재고 현황
        self._setup_dash_activity(ctx)
    def _setup_dash_cards(self, ctx) -> None:
        """섹션 1: 4단계 요약 카드 (v6.0: AVAILABLE / RESERVED / PICKED / SOLD) + TOTAL"""
        from ..utils.constants import X
        ttk, tk, _p, fonts = ctx['ttk'], ctx['tk'], ctx['_p'], ctx['fonts']
        Spacing = ctx['Spacing']
        main_container = ctx['main_container']

        cards_frame = ttk.Frame(main_container)
        cards_frame.pack(fill=X, pady=(0, Spacing.MD))
        
        self._dashboard_cards = {}
        
        # v6.0: 4단계 카드 — 판매가능 / 판매배정 / 판매화물 결정 / 출고
        card_configs = [
            ('status_available', '판매가능', '0개', _p.get('success', '#1abc9c')),
            ('status_reserved', '판매배정', '0개', _p.get('primary', '#3498db')),
            ('status_picked', '판매화물 결정', '0개', _p.get('warning', '#e67e22')),
            ('status_sold', '출고', '0개', _p.get('danger', '#e74c3c')),
        ]
        
        for i, (key, title, default, color) in enumerate(card_configs):
            card = self._create_dashboard_card(cards_frame, title, default, color, fonts)
            card.grid(row=0, column=i, padx=Spacing.XS, sticky='nsew')
            self._dashboard_cards[key] = card
            cards_frame.columnconfigure(i, weight=1)
        
        # TOTAL 바 (항상 일정)
        total_frame = ttk.Frame(cards_frame)
        total_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(Spacing.SM, 0))
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
            from ..utils.constants import Meter, HAS_METER
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
        alert_scrollbar = ttk.Scrollbar(alert_frame, orient='vertical', command=self.alert_listbox.yview)
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

    # ══════════════════════════════════════════════════════════
    # v7.0.1: 위치별 재고 현황 위젯
    # ══════════════════════════════════════════════════════════
    
    def _setup_dash_location_zone(self, ctx) -> None:
        """구역별 톤백 수량/중량 위젯"""
        from ..utils.constants import tk, ttk
        
        frame = ttk.LabelFrame(ctx['main_container'], text="📍 구역별 재고 현황", padding=5)
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
                self._location_zone_tree.tag_configure('warning', foreground='#e74c3c')
            
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
            self._refresh_dashboard_location_zone()  # v7.0.1
            self._refresh_dashboard_chart()
            self._refresh_dashboard_return_rate()
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if hasattr(self, 'dashboard_status'):
                self.dashboard_status.config(text=f"마지막 갱신: {now}")
            
            logger.debug("대시보드 새로고침 완료")
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"대시보드 새로고침 오류: {e}")
    
    def _refresh_dashboard_cards(self) -> None:
        """v6.0: 4단계 카드 새로고침 (AVAILABLE / RESERVED / PICKED / SOLD) + TOTAL"""
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
            _set_card('status_sold', stats.get('sold_cnt', 0), stats.get('sold_kg', 0))
            
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
