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

        # v8.1.8: 표준 헤더
        try:
            from ..utils.ui_constants import make_tab_header
            make_tab_header(self.tab_dashboard, "", status_color='#3b82f6')  # v8.6.4: 헤더 텍스트 삭제
        except Exception as e:
            logger.warning(f'[UI] dashboard_tab: {e}')
        _d  = is_dark()
        _p  = ThemeColors.get_palette(_d) if hasattr(ThemeColors, 'get_palette') else {}

        # ── 색상 팔레트 ───────────────────────────────────────────────
        BG       = ThemeColors.get('bg_primary',   _d)
        BG2      = ThemeColors.get('bg_secondary', _d)
        BG_CARD  = ThemeColors.get('bg_card',      _d)
        FG       = ThemeColors.get('text_primary',  _d)
        FG2      = ThemeColors.get('text_secondary',_d)
        FG_MUTED = ThemeColors.get('text_muted',    _d)
        BORDER   = ThemeColors.get('border',        _d) if 'border' in (
            ThemeColors.DARK if _d else ThemeColors.LIGHT) else (
            '#1a3a5c' if _d else '#e2e8f0')
        ACCENT   = '#00d4ff' if _d else '#0056d6'   # v8.6.4 강조색
        SUCCESS  = '#00e676' if _d else '#059669'
        WARNING  = '#FF8C00' if _d else '#d97706'
        DANGER   = '#ff1744' if _d else '#dc2626'

        # 상태 카드 색상
        # v8.6.4: Pro 팔레트 동기화 — Muted Pastel (다크) / Muted Deep (라이트)
        CARD_COLORS = {
            'available': ('#52c87e' if _d else '#147848'),   # 소프트 에메랄드 / 딥 에메랄드
            'reserved':  ('#e8943a' if _d else '#a86020'),   # 소프트 테라코타 / 딥 앰버
            'picked':    ('#a07ee0' if _d else '#6040b0'),   # 소프트 라벤더 / 딥 바이올렛
            'sold':      ('#4ab0e8' if _d else '#1060a8'),   # 소프트 스카이 / 딥 사파이어
            'return':    ('#e06888' if _d else '#a03060'),   # 소프트 로즈 / 딥 루비
        }

        mc = tk.Frame(self.tab_dashboard, bg=BG)
        mc.pack(fill=BOTH, expand=YES, padx=Spacing.Tab.OUTER_PADX, pady=(12, 16))
        mc.columnconfigure(0, weight=1)

        # ══════════════════════════════════════════════════════════════
        # 1구역: 재고 상태 카드 5개 (상단 가로 한 줄)
        # ══════════════════════════════════════════════════════════════
        zone1 = tk.Frame(mc, bg=BG)
        zone1.pack(fill=X, pady=(0, 10))
        zone1.columnconfigure(tuple(range(5)), weight=1)
        for i in range(5):
            zone1.columnconfigure(i, weight=1)

        card_defs = [
            ('status_available', '판매가능',      CARD_COLORS['available'], '판매비중 정'),
            ('status_reserved',  '판매배정',      CARD_COLORS['reserved'],  '예약 확률'),
            ('status_picked',    '판매화물 결정', CARD_COLORS['picked'],    '피킹 확률'),
            ('status_sold',      '출고완료',      CARD_COLORS['sold'],      '이번 달'),
            ('status_return',    '반품대기',      CARD_COLORS['return'],    '반품 처리 중'),
        ]
        self._dashboard_cards = {}
        for col_i, (key, title, color, subtitle) in enumerate(card_defs):
            card = self._create_dashboard_card(zone1, title, '0.0 MT', color, subtitle=subtitle)
            card.grid(row=0, column=col_i, sticky='nsew',
                      padx=(0 if col_i == 0 else 8, 0), pady=0)
            self._dashboard_cards[key] = card

        # v8.6.4: 테마 리프레시 이후 카드 색상 강제 재적용
        def _force_card_colors():
            for _c in self._dashboard_cards.values():
                _clr = getattr(_c, 'color', '#ffffff')
                if hasattr(_c, 'value_label'):
                    _c.value_label.config(fg=_clr)
                if hasattr(_c, 'title_label'):
                    _c.title_label.config(fg=_clr)
        self.tab_dashboard.after(1500, _force_card_colors)
        self.tab_dashboard.after(3000, _force_card_colors)

        # TOTAL 바
        total_bar = tk.Frame(mc, bg=BG2)
        total_bar.pack(fill=X, pady=(4, 12))
        self._dashboard_total_label = tk.Label(
            total_bar,
            text="TOTAL: 계산 중...",
            bg=BG2, fg=ACCENT,
            font=('맑은 고딕', 11, 'bold'),
            anchor='w', padx=10, pady=4,
        )
        self._dashboard_total_label._tc_skip = True
        self._dashboard_total_label.pack(fill=X)

        # ══════════════════════════════════════════════════════════════
        # 2구역: 정합성 신호등(좌) + 알림 패널(우)
        # ══════════════════════════════════════════════════════════════
        zone2 = tk.Frame(mc, bg=BG)
        zone2.pack(fill=X, pady=(0, 12))

        # ── 좌: 정합성 신호등 ─────────────────────────────────────────
        integrity_outer = tk.Frame(zone2, bg=BORDER, bd=0)
        integrity_outer.pack(side=LEFT, fill=Y, padx=(0, 4))
        integrity_inner = tk.Frame(integrity_outer, bg=BG_CARD, padx=12, pady=10)
        integrity_inner.pack(fill=BOTH, expand=YES, padx=1, pady=1)

        # 헤더
        tk.Label(integrity_inner,
                 text="INTEGRITY CHECK  재고 정합성",
                 bg=BG_CARD, fg=FG_MUTED,
                 font=('맑은 고딕', 9, 'bold'),
                 anchor='w').pack(fill=X, pady=(0, 8))

        # 신호등 행
        sig_row = tk.Frame(integrity_inner, bg=BG_CARD)
        sig_row.pack(fill=X, pady=(0, 8))

        # 신호등 도트 (크게)
        self._integrity_signal_dot = tk.Label(
            sig_row, text='🟢',
            font=('맑은 고딕', 22),
            bg=BG_CARD,
        )
        self._integrity_signal_dot.pack(side=LEFT, padx=(0, 10))

        sig_text = tk.Frame(sig_row, bg=BG_CARD)
        sig_text.pack(side=LEFT, fill=X, expand=YES)
        self._integrity_signal_label = tk.Label(
            sig_text, text='정합성 OK',
            bg=BG_CARD, fg=SUCCESS,
            font=('맑은 고딕', 14, 'bold'), anchor='w',
        )
        self._integrity_signal_label.pack(fill=X)
        self._integrity_signal_sub = tk.Label(
            sig_text, text='총입고 = 현재재고 + 출고누계',
            bg=BG_CARD, fg=FG_MUTED,
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
            row_f = tk.Frame(integrity_inner, bg=BG_CARD)
            row_f.pack(fill=X, pady=1)
            tk.Frame(row_f, bg=BORDER, height=1).pack(fill=X, side=TOP)
            lbl_f = tk.Frame(row_f, bg=BG_CARD)
            lbl_f.pack(fill=X, pady=2)
            tk.Label(lbl_f, text=row_title, bg=BG_CARD, fg=FG_MUTED,
                     font=('맑은 고딕', 10), width=12, anchor='w').pack(side=LEFT)
            val_lbl = tk.Label(lbl_f, text='—', bg=BG_CARD, fg=FG,
                               font=('맑은 고딕', 11, 'bold'), anchor='e')
            val_lbl.pack(side=RIGHT)
            setattr(self, attr, val_lbl)

        # 드릴다운 버튼
        tk.Button(
            integrity_inner,
            text='🔍 불일치 LOT 상세 보기',
            bg=BG2, fg=FG2,
            font=('맑은 고딕', 9),
            relief='flat', bd=0, cursor='hand2',
            padx=8, pady=4,
            command=self._on_integrity_drill_down,
        ).pack(fill=X, pady=(8, 0))

        # ── 우: 알림 패널 ─────────────────────────────────────────────
        alert_outer = tk.Frame(zone2, bg=BORDER, bd=0)
        alert_outer.pack(side=LEFT, fill=BOTH, expand=YES)
        alert_inner = tk.Frame(alert_outer, bg=BG_CARD)
        alert_inner.pack(fill=BOTH, expand=YES, padx=1, pady=1)

        # 알림 헤더
        alert_hdr = tk.Frame(alert_inner, bg=BG2)
        alert_hdr.pack(fill=X)
        tk.Label(alert_hdr, text="⚠️  ALERTS  알림 및 경고",
                 bg=BG2, fg=FG_MUTED,
                 font=('맑은 고딕', 12, 'bold'),
                 anchor='w', padx=10, pady=6).pack(side=LEFT)
        self._alert_count_label = tk.Label(
            alert_hdr, text='', bg=BG2, fg=DANGER,
            font=('맑은 고딕', 12, 'bold'), padx=8,
        )
        self._alert_count_label._tc_skip = True
        self._alert_count_label.pack(side=RIGHT)

        # 알림 리스트박스
        alert_list_frame = tk.Frame(alert_inner, bg=BG_CARD)
        alert_list_frame.pack(fill=BOTH, expand=YES, padx=6, pady=6)
        self.alert_listbox = tk.Listbox(
            alert_list_frame,
            bg=BG_CARD, fg=FG,
            font=('맑은 고딕', 13),
            selectmode='single',
            relief='flat', bd=0,
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
        kpi_bar = tk.Frame(alert_inner, bg=BG2)
        kpi_bar.pack(fill=X, side=RIGHT if False else 'bottom')
        self._kpi_summary_label = tk.Label(
            kpi_bar, text='',
            bg=BG2, fg=FG_MUTED,
            font=('맑은 고딕', 9),
            anchor='w', padx=10, pady=4,
        )
        self._kpi_summary_label.pack(fill=X)

        # ══════════════════════════════════════════════════════════════
        # 3구역: 제품별 현황 테이블 (하단 전체 너비)
        # ══════════════════════════════════════════════════════════════
        zone3 = tk.Frame(mc, bg=BG)
        zone3.pack(fill=BOTH, expand=YES, pady=(8, 0))

        # v8.6.4: 제품×상태 매트릭스 테이블 (통합 뷰)
        z3_hdr = tk.Frame(zone3, bg=BG2)
        z3_hdr.pack(fill=X, pady=(0, 4))
        tk.Label(z3_hdr, text="제품별 재고 현황",
                 bg=BG2, fg=FG_MUTED,
                 font=('맑은 고딕', 11, 'bold'),
                 anchor='w', padx=10, pady=5).pack(side=LEFT)

        # MT/LOT/톤백 전환
        self._dash_view_mode = tk.StringVar(value='mt')
        for val, lbl in (('mt', '📊 MT'), ('lot', '📦 LOT'), ('tonbag', '🎒 톤백')):
            tk.Radiobutton(
                z3_hdr, text=lbl, variable=self._dash_view_mode,
                value=val, command=self._refresh_dashboard_products,
                bg=BG2, fg=FG, selectcolor=BG_CARD,
                activebackground=BG2, activeforeground=FG,
                font=('맑은 고딕', 10),
            ).pack(side=RIGHT, padx=4)

        product_frame = tk.Frame(zone3, bg=BG_CARD)
        product_frame.pack(fill=BOTH, expand=YES)

        columns = ("product", "available", "reserved", "picked",
                   "outbound", "return", "total", "sample")
        self.tree_dashboard_product = ttk.Treeview(
            product_frame, columns=columns,
            show="headings", height=Spacing.Tab.TREE_MIN_H,
        )
        col_defs = [
            ("product",   "Product",      160, "w"),
            ("available", "판매가능",       90,  "e"),
            ("reserved",  "판매배정",       90,  "e"),
            ("picked",    "판매화물",       90,  "e"),
            ("outbound",  "출고완료",       90,  "e"),
            ("return",    "반품대기",       90,  "e"),
            ("total",     "합계",          100, "e"),
            ("sample",    "샘플",           70,  "center"),
        ]
        _status_colors = {
            'available': CARD_COLORS['available'],
            'reserved':  CARD_COLORS['reserved'],
            'picked':    CARD_COLORS['picked'],
            'outbound':  CARD_COLORS['sold'],
            'return':    CARD_COLORS['return'],
        }
        for cid, text, width, anchor in col_defs:
            self.tree_dashboard_product.heading(cid, text=text, anchor='center')
            self.tree_dashboard_product.column(cid, width=width, anchor=anchor, stretch=False)

        prod_vsb = tk.Scrollbar(product_frame, orient='vertical',
                                 command=self.tree_dashboard_product.yview)
        self.tree_dashboard_product.configure(yscrollcommand=prod_vsb.set)
        self.tree_dashboard_product.pack(side=LEFT, fill=BOTH, expand=YES)
        prod_vsb.pack(side=RIGHT, fill=Y)
        self._dash_product_footer = None

        # 자동새로고침 체크박스
        auto_bar = tk.Frame(mc, bg=BG)
        auto_bar.pack(fill=X, pady=(4, 0))
        self._auto_refresh_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            auto_bar, text="자동 새로고침 (30초)",
            variable=self._auto_refresh_var,
            bg=BG, fg=FG_MUTED,
            selectcolor=BG_CARD, activebackground=BG,
            font=('맑은 고딕', 9),
            command=self._toggle_auto_refresh
            if hasattr(self, '_toggle_auto_refresh') else lambda: None,
        ).pack(side=LEFT)
        self.dashboard_status = tk.Label(
            auto_bar, text='',
            bg=BG, fg=FG_MUTED,
            font=('맑은 고딕', 9), anchor='e',
        )
        self.dashboard_status.pack(side=RIGHT, padx=4)

        # 초기 데이터 로드
        self._refresh_dashboard()




    def _create_dashboard_card(self, parent, title: str, value: str, color: str,
                               fonts=None, subtitle: str = '') -> 'ttk.Frame':
        """v8.6.4: 대시보드 카드 — TOP 컬러 바 + MT 컬러 값 + 서브타이틀"""
        from ..utils.constants import tk

        try:
            _dk = is_dark()
            _cp = ThemeColors.get_palette(_dk)
        except (ImportError, ModuleNotFoundError):
            _cp = {'bg_card': ThemeColors.get('bg_card', is_dark()), 'text_secondary': '#666666'}

        _card_bg = _cp.get('bg_card', ThemeColors.get('bg_card', is_dark()))
        _card_fg = _cp.get('text_secondary', '#666666')
        _border_color = _cp.get('border', '#e0e0e0')

        outer = tk.Frame(parent, bg=_card_bg, bd=0,
                         highlightbackground=_border_color, highlightthickness=1)
        outer._tc_skip = True

        color_bar = tk.Frame(outer, bg=color, height=4)
        color_bar._tc_skip = True
        color_bar.pack(side='top', fill='x')
        color_bar.pack_propagate(False)

        content = tk.Frame(outer, bg=_card_bg, padx=16, pady=12)
        content._tc_skip = True
        content.pack(side='top', fill='both', expand=True)

        title_row = tk.Frame(content, bg=_card_bg)
        title_row._tc_skip = True
        title_row.pack(fill='x')

        title_label = tk.Label(title_row, text=title,
                               font=('맑은 고딕', 11, 'bold'),
                               bg=_card_bg, fg=color)
        title_label._tc_skip = True
        title_label.pack(side='left')

        if subtitle:
            sub_title_lbl = tk.Label(title_row, text=subtitle,
                                     font=('맑은 고딕', 8),
                                     bg=_card_bg, fg=_card_fg)
            sub_title_lbl._tc_skip = True
            sub_title_lbl.pack(side='right')

        value_label = tk.Label(content, text=value,
                               font=('맑은 고딕', 22, 'bold'),
                               bg=_card_bg, fg=color)
        value_label._tc_skip = True
        value_label.pack(anchor='w', pady=(4, 0))

        sub_label = tk.Label(content, text='',
                             font=('맑은 고딕', 9),
                             bg=_card_bg, fg=_card_fg)
        sub_label._tc_skip = True
        sub_label.pack(anchor='w', pady=(2, 0))

        outer.value_label = value_label
        outer.sub_label = sub_label
        outer.title_label = title_label
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
                color = '#00e676' if _d else '#059669'
            elif abs(_diff) < 10:
                dot   = '🟡'
                label = '경미한 오차'
                color = '#FF8C00' if _d else '#d97706'
            else:
                dot   = '🔴'
                label = '불일치 감지!'
                color = '#ff1744' if _d else '#dc2626'

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
                # v8.6.4: MT 기반 대형 값
                mt = kg / 1000.0
                card.value_label.config(text=f"{mt:,.1f} MT")
                if hasattr(card, 'sub_label'):
                    card.sub_label.config(text=f"{tb} LOT / {samp} 톤백")

            # v8.6.4: 테마 전환 시 카드 색상 동기화
            def _sync_card_colors():
                try:
                    from ..utils.ui_constants import ThemeColors, tc
                    from theme_aware import ThemeAware
                    _dk = ThemeAware.is_dark()
                    _card_bg  = ThemeColors.get('bg_card',      _dk)
                    _card_fg  = ThemeColors.get('text_secondary', _dk)
                    _border   = ThemeColors.get('border',         _dk)
                    _new_colors = {
                        'status_available': '#00e676' if _dk else '#059669',
                        'status_reserved':  '#FF8C00' if _dk else '#d97706',
                        'status_picked':    '#a78bfa' if _dk else '#7c3aed',
                        'status_sold':      '#00b0ff' if _dk else '#0369a1',
                        'status_return':    '#ff6b9d' if _dk else '#be185d',
                    }
                    for key, color in _new_colors.items():
                        card = self._dashboard_cards.get(key)
                        if not card: continue
                        # 카드 배경 갱신
                        for w in card.winfo_children():
                            try:
                                w.config(bg=_card_bg)
                                for ww in w.winfo_children():
                                    try: ww.config(bg=_card_bg)
                                    except Exception: pass
                            except Exception: pass
                        # 좌측 색바 갱신 (첫 번째 자식의 첫 번째 자식)
                        try:
                            inner = card.winfo_children()[0]
                            color_bar = inner.winfo_children()[0]
                            color_bar.config(bg=color)
                        except (IndexError, Exception): pass
                        # 값/제목 레이블 색상 갱신
                        if hasattr(card, 'value_label'):
                            card.value_label.config(fg=color, bg=_card_bg)
                        if hasattr(card, 'title_label'):
                            card.title_label.config(fg=color, bg=_card_bg)
                        if hasattr(card, 'sub_label'):
                            card.sub_label.config(fg=_card_fg, bg=_card_bg)
                        # 외부 테두리 색상 갱신
                        card.config(bg=_border)
                        card.color = color
                except Exception as _ce:
                    logger.debug(f"[DashCard] 색상 동기화 스킵: {_ce}")

            _sync_card_colors()

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
                _rcard.value_label.config(text=f"{_rkg/1000:,.1f} MT")
                if hasattr(_rcard, 'sub_label'):
                    _rcard.sub_label.config(text=f"{_lot} LOT / {_tb} 톤백")

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
                _total_tb = int(stats.get('avail_tb_cnt', 0) or 0) + int(stats.get('reserved_tonbag_cnt', 0) or 0)
                _total_samp = int(stats.get('avail_samp_cnt', 0) or 0)
                self._dashboard_total_label.config(
                    text=(
                        f"전체 재고 {total_mt:,.1f}MT · LOT {total_cnt}개"
                        f" · 톤백 {_total_tb}개 · 샘플 {_total_samp}개"
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
                    _danger_c = '#ff1744' if _dk else '#dc2626'
                    _warn_c   = '#FF8C00' if _dk else '#d97706'
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
        """v8.6.4: 제품×상태 매트릭스 — MT/LOT/톤백 전환 가능."""
        from ..utils.constants import END

        try:
            if not hasattr(self, 'tree_dashboard_product'):
                return
            tree = self.tree_dashboard_product
            tree.delete(*tree.get_children())

            mode = getattr(self, '_dash_view_mode', None)
            mode = mode.get() if mode else 'mt'

            # DB에서 제품×상태별 데이터 조회
            db = getattr(self, 'engine', None)
            if db:
                db = getattr(db, 'db', db)
            if not db:
                return

            # 제품별 상태별 집계
            rows = db.fetchall("""
                SELECT
                    COALESCE(i.product, 'Unknown') AS product,
                    t.status,
                    COALESCE(t.is_sample, 0) AS is_sample,
                    COUNT(*) AS cnt,
                    COALESCE(SUM(t.weight), 0) AS kg
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON t.lot_no = i.lot_no
                GROUP BY COALESCE(i.product, 'Unknown'), t.status, COALESCE(t.is_sample, 0)
            """)

            # 매트릭스 구성
            products = {}
            status_map = {
                'AVAILABLE': 'available', 'RESERVED': 'reserved',
                'PICKED': 'picked', 'OUTBOUND': 'outbound', 'SHIPPED': 'outbound',
                'SOLD': 'outbound', 'RETURNED': 'return', 'RETURN': 'return',
            }
            for r in (rows or []):
                prod = r.get('product', 'Unknown') or 'Unknown'
                status = str(r.get('status', '')).upper()
                is_samp = int(r.get('is_sample', 0) or 0)
                cnt = int(r.get('cnt', 0) or 0)
                kg = float(r.get('kg', 0) or 0)

                if prod not in products:
                    products[prod] = {
                        'available': 0, 'reserved': 0, 'picked': 0,
                        'outbound': 0, 'return': 0, 'sample_cnt': 0, 'sample_kg': 0,
                        'available_cnt': 0, 'reserved_cnt': 0, 'picked_cnt': 0,
                        'outbound_cnt': 0, 'return_cnt': 0,
                    }
                p = products[prod]
                mapped = status_map.get(status, '')
                if is_samp:
                    p['sample_cnt'] += cnt
                    p['sample_kg'] += kg
                elif mapped:
                    p[mapped] += kg
                    p[f'{mapped}_cnt'] += cnt

            # 표시
            sums = {k: 0 for k in ['available', 'reserved', 'picked', 'outbound', 'return',
                                    'total', 'sample']}
            for prod_name in sorted(products.keys()):
                p = products[prod_name]
                total_kg = sum(p[s] for s in ['available', 'reserved', 'picked', 'outbound', 'return'])
                total_cnt = sum(p[f'{s}_cnt'] for s in ['available', 'reserved', 'picked', 'outbound', 'return'])

                if mode == 'mt':
                    vals = (prod_name,
                            f"{p['available']/1000:,.1f}", f"{p['reserved']/1000:,.1f}",
                            f"{p['picked']/1000:,.1f}", f"{p['outbound']/1000:,.1f}",
                            f"{p['return']/1000:,.1f}", f"{total_kg/1000:,.1f}",
                            p['sample_cnt'])
                elif mode == 'lot':
                    vals = (prod_name,
                            p['available_cnt'], p['reserved_cnt'],
                            p['picked_cnt'], p['outbound_cnt'],
                            p['return_cnt'], total_cnt,
                            p['sample_cnt'])
                else:  # tonbag
                    vals = (prod_name,
                            p['available_cnt'], p['reserved_cnt'],
                            p['picked_cnt'], p['outbound_cnt'],
                            p['return_cnt'], total_cnt,
                            p['sample_cnt'])

                tree.insert('', END, values=vals)

                sums['available'] += p['available']
                sums['reserved'] += p['reserved']
                sums['picked'] += p['picked']
                sums['outbound'] += p['outbound']
                sums['return'] += p['return']
                sums['total'] += total_kg
                sums['sample'] += p['sample_cnt']

            # 합계 행
            if products:
                if mode == 'mt':
                    tree.insert('', END, values=(
                        '합계',
                        f"{sums['available']/1000:,.1f}", f"{sums['reserved']/1000:,.1f}",
                        f"{sums['picked']/1000:,.1f}", f"{sums['outbound']/1000:,.1f}",
                        f"{sums['return']/1000:,.1f}", f"{sums['total']/1000:,.1f}",
                        int(sums['sample']),
                    ), tags=('total',))
                else:
                    tree.insert('', END, values=(
                        '합계',
                        sum(products[p]['available_cnt'] for p in products),
                        sum(products[p]['reserved_cnt'] for p in products),
                        sum(products[p]['picked_cnt'] for p in products),
                        sum(products[p]['outbound_cnt'] for p in products),
                        sum(products[p]['return_cnt'] for p in products),
                        sum(sum(products[p][f'{s}_cnt'] for s in ['available','reserved','picked','outbound','return']) for p in products),
                        int(sums['sample']),
                    ), tags=('total',))
                tree.tag_configure('total', font=('맑은 고딕', 11, 'bold'))

        except Exception as e:
            logger.error(f"제품×상태 매트릭스 오류: {e}")


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