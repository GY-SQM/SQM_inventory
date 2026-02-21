# -*- coding: utf-8 -*-
from ..utils.custom_messagebox import CustomMessageBox
"""
SQM v3.8.4 — 통합 메뉴바
=========================
순서: [입고▼] [출고▼] [보고서▼] [🔍검색] │ [파일▼] [설정/도구▼] [도움말▼]
      ← 업무 메뉴 (좌측) →              │  ← 시스템 메뉴 (우측) →
+ 탭 전환 버튼 (균등 배치)
+ 자동 2줄 전환
"""
import sqlite3
import logging
import tkinter as tk
from tkinter import ttk
from ..utils.ui_constants import ThemeColors, Spacing, FontScale, FontStyle, get_font_scale, DialogSize, center_dialog, apply_modal_window_options
from utils.ui_debug import log_ui_event, safe_widget_bg  # v5.3.6

logger = logging.getLogger(__name__)

FONT_CANDIDATES = ['NanumSquare', 'NanumSquareRound', '나눔스퀘어', 'Malgun Gothic', '맑은 고딕']


def _pick_font(root) -> str:
    import tkinter.font as tkfont
    available = tkfont.families()
    for f in FONT_CANDIDATES:
        if f in available:
            return f
    return '맑은 고딕'


class ToolbarMixin:
    """v3.8.4: 통합 메뉴바 (ThemeColors 단일 소스, Phase5: 메뉴 헬퍼·미니멀)"""

    def _load_toolbar_colors(self) -> None:
        """ThemeColors 단일 소스 — 툴바는 항상 다크 스타일 (Phase2/5)"""
        try:
            import ttkbootstrap as ttk_bs
            sc = ttk_bs.Style().colors
            _dark = True
            self._tb_bg = ThemeColors.get('statusbar_bg', _dark)
            self._tb_sep = ThemeColors.get('border', _dark)
            self._tb_fg_normal = ThemeColors.get('text_secondary', _dark)
            self._tb_fg_active = ThemeColors.get('statusbar_fg', _dark)
            self._tb_fg_hover = ThemeColors.get('text_primary', _dark)
            self._tb_hover_bg = ThemeColors.get('bg_hover', _dark)
            self._tb_underline_color = str(sc.info) if getattr(sc, 'info', None) else ThemeColors.get('info', _dark)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
            _dark = True
            self._tb_bg = ThemeColors.get('statusbar_bg', _dark)
            self._tb_sep = ThemeColors.get('border', _dark)
            self._tb_fg_normal = ThemeColors.get('text_secondary', _dark)
            self._tb_fg_active = ThemeColors.get('statusbar_fg', _dark)
            self._tb_fg_hover = ThemeColors.get('text_primary', _dark)
            self._tb_hover_bg = ThemeColors.get('bg_hover', _dark)
            self._tb_underline_color = ThemeColors.get('info', _dark)

    def _setup_toolbar(self) -> None:
        self._toolbar_font = _pick_font(self.root)
        self._tb_font_scale = get_font_scale() or FontScale()
        logger.info(f"[v3.8.4] 폰트: {self._toolbar_font}")

        # ThemeColors에서 동적 로드
        self._load_toolbar_colors()

        # 컨테이너 서픽스 변수 초기화
        self._container_suffix_var = tk.BooleanVar(value=True)

        self._toolbar_container = tk.Frame(self.root)
        self._toolbar_container.pack(fill='x')

        # Row1: 메뉴 버튼 (Phase3: Spacing 8px 그리드)
        self._row1 = tk.Frame(self._toolbar_container, bg=self._tb_bg, pady=Spacing.XS)
        self._row1.pack(fill='x')
        
        # v4.0.0: 오른쪽 버전 배지 (Phase3: FontScale body/heading)
        try:
            from version import __version__, APP_NAME
            ver_frame = tk.Frame(self._row1, bg=self._tb_bg)
            ver_frame.pack(side='right', padx=Spacing.MD)
            _vf = self._tb_font_scale
            tk.Label(ver_frame, text=f"📦 {APP_NAME}", bg=self._tb_bg, fg=ThemeColors.get('statusbar_progress'),
                     font=_vf.body(bold=True)).pack(side='left')
            tk.Label(ver_frame, text=f"  v{__version__}", bg=self._tb_bg, fg=ThemeColors.get('statusbar_icon_warn', True),
                     font=_vf.heading()).pack(side='left')
        except (ImportError, ModuleNotFoundError) as _e:
            logger.debug(f'Suppressed: {_e}')
        # Row2: 탭 버튼 (v3.8.9: 항상 표시)
        self._row2 = tk.Frame(self._toolbar_container, bg=self._tb_bg, pady=Spacing.XS)
        self._row2.pack(fill='x')
        self._row2_visible = True

        # v3.8.9: 메뉴 버튼 — 왼쪽 정렬, 최대 너비 제한
        self._menu_frame = tk.Frame(self._row1, bg=self._tb_bg)
        self._menu_frame.pack(side='left', fill='x')

        # === 7개 메뉴 버튼 (균등) ===
        self._all_menu_btns = []
        self._all_dropdown_menus = []  # v5.4.1: theme refresh 대상 tk.Menu들
        self._build_all_menus()

        # 구분선
        self._sep_line = tk.Frame(self._row2, bg=self._tb_sep, height=1)
        self._sep_line.pack(fill='x', padx=Spacing.SM, pady=(0, Spacing.XS))

        # === 탭 전환 (Row2에 고정, 왼쪽 정렬) ===
        self._sec_tabs = tk.Frame(self._row2, bg=self._tb_bg)
        self._sec_tabs.pack(side='left', padx=Spacing.SM)
        self._build_tab_buttons()

        # v3.8.9: overflow 체크 비활성화 (탭은 항상 row2에 고정)
        # self.root.bind('<Configure>', self._check_toolbar_overflow)
        self._tab_index_map = {'cargo_overview': 0, 'inventory': 1, 'outbound_scheduled': 2, 'tonbag': 3, 'dashboard': 4, 'log': 5}
        self._active_tab_key = 'cargo_overview'

    # ═══════════════════════════════════════════════════════
    # 메뉴 생성 헬퍼 (v3.8.4: 항목 간격 확대)
    # ═══════════════════════════════════════════════════════

    def _create_menu(self, parent=None) -> 'tk.Menu':
        """간격 넓은 팝업 메뉴 생성 (v3.8.4)"""
        # v5.4.1: 드롭다운 메뉴 색상(라이트/다크) 강제 고정 — Windows tk_popup 리셋 방지
        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        menu_bg = ThemeColors.get('bg_card', is_dark)
        menu_fg = ThemeColors.get('text_primary', is_dark)
        menu_abg = ThemeColors.get('bg_hover', is_dark)
        menu_afg = ThemeColors.get('text_primary', is_dark)
        menu_dis = ThemeColors.get('text_muted', is_dark)
        f = self._toolbar_font
        p = parent or self.root
        _menu_font = self._tb_font_scale.get_font(FontStyle.SUBTITLE)
        m = tk.Menu(p, tearoff=0, font=(f, _menu_font[1]),
                    activeborderwidth=3,
                    borderwidth=3,
                    relief='flat',
                    background=menu_bg, foreground=menu_fg,
                    activebackground=menu_abg, activeforeground=menu_afg,
                    disabledforeground=menu_dis)
        # v5.4.1: 일부 Windows/Tk 조합에서 초기 옵션이 덮이는 케이스 대비
        try:
            m.config(bg=menu_bg, fg=menu_fg, activebackground=menu_abg, activeforeground=menu_afg,
                     disabledforeground=menu_dis)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")
        return m

    def _add_menu_item(self, menu, label: str, command, icon_pad: bool = True) -> None:
        """여백 포함 메뉴 항목 추가 (위아래 간격 확보)"""
        padded = f"  {label}  " if not label.startswith('  ') else f"{label}  "
        menu.add_command(label=padded, command=command)

    def _add_menu_items(self, menu: 'tk.Menu', items: list) -> None:
        """Phase5: (label, command) 또는 None(구분선) 리스트로 메뉴 일괄 구성"""
        for item in items:
            if item is None:
                menu.add_separator()
            else:
                label, cmd = item[0], item[1]
                menu.add_command(label=f"  {label}" if not str(label).startswith('  ') else label, command=cmd)

    # ═══════════════════════════════════════════════════════
    # 7개 메뉴 버튼 (균등 배치)
    # ═══════════════════════════════════════════════════════

    def _build_all_menus(self) -> None:
        """7개 드롭다운 메뉴 (밑줄 스타일) + 툴팁"""
        menus = [
            ('📁 파일 ▼',      self._build_file_menu,
             '파일 메뉴: 데이터베이스 열기/저장/백업, 설정 파일, 최근 파일, 종료 등 파일 관련 기능'),
            ('📥 입고 ▼',      self._build_inbound_menu,
             '입고 메뉴: 원스톱 입고(PDF/엑셀), 로케이션 업로드, 입고 이력 조회 등 입고 처리 기능'),
            ('📤 출고 ▼',      self._build_outbound_menu,
             '출고 메뉴: 선택 출고, 출고 템플릿, 출고 이력, 반품(재입고) 등 출고·반품 관련 기능'),
            ('📊 재고 ▼',      self._build_report_menu,
             '재고 메뉴: 재고 현황·통계, 대시보드, LOT/톤백 조회, 엑셀 내보내기 등 재고 조회·보고 기능'),
            ('📝 보고서 ▼',    self._build_customer_report_menu,
             '보고서 메뉴: 고객별·기간별 보고서, PDF/엑셀 출력 등 보고서 생성·출력 기능'),
            ('🔧 설정/도구 ▼', self._build_settings_menu,
             '설정/도구 메뉴: API 키·테마 설정, 데이터 검증, 마이그레이션, 개발자 도구 등'),
            ('❓ 도움말 ▼',    self._build_help_menu,
             '도움말 메뉴: 단축키, 사용 안내, 정보·버전, 로그 보기 등'),
        ]

        for item in menus:
            text = item[0]
            builder = item[1]
            tooltip = item[2] if len(item) > 2 else ""
            # v5.7.5: 상단 메뉴가 가장 크게 (Phase3: FontScale.heading + Spacing)
            _btn_font = self._tb_font_scale.heading()
            btn = tk.Label(self._menu_frame, text=text,
                          font=_btn_font,
                          bg=self._tb_bg, fg=self._tb_fg_normal,
                          anchor='center', justify='center',
                          padx=Spacing.SM, pady=Spacing.SM, cursor='hand2')
            btn.pack(side='left', padx=Spacing.XS)

            # 밑줄 인디케이터 (숨긴 상태로 생성)
            underline = tk.Frame(btn, height=2, bg=self._tb_underline_color)
            btn._underline = underline
            btn._menu_active = False

            menu = builder()
            try:
                self._all_dropdown_menus.append(menu)
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"Suppressed: {_e}")
            btn.bind('<Button-1>', lambda e, m=menu, b=btn: self._show_menu(m, b))

            def make_enter(button):
                def on_enter(e):
                    if not button._menu_active:
                        button.config(fg=self._tb_fg_hover)
                return on_enter

            def make_leave(button):
                def on_leave(e):
                    if not button._menu_active:
                        button.config(fg=self._tb_fg_normal)
                return on_leave

            btn.bind('<Enter>', make_enter(btn))
            btn.bind('<Leave>', make_leave(btn))
            self._all_menu_btns.append(btn)
            if tooltip:
                self._attach_tooltip(btn, tooltip)

        # v5.7.5: 검색 버튼 UI 제거 (메뉴 끝 검색 버튼 삭제)

    def _build_search_button(self) -> None:
        """v5.5.3 patch_02: 검색 — Outline 버튼 (드롭다운 메뉴가 아님을 시각적으로 구분)
        
        ttkbootstrap의 bootstyle='outline-info'를 사용하면:
          - 테두리 + 텍스트만 info 색상
          - 배경은 투명
          - 호버 시 배경이 info 색상으로 채워짐
          - 테마 변경 시 자동 대응
        """
        f = self._toolbar_font

        try:
            import ttkbootstrap as ttk_bs
            # ttkbootstrap Outline 버튼 (테마 자동 대응)
            self._search_btn = ttk_bs.Button(
                self._menu_frame,
                text='🔍 검색',
                bootstyle='outline-info',
                command=self._show_search_popup,
                padding=(Spacing.MD, Spacing.XS),
            )
            # 폰트 크기 적용
            try:
                self._search_btn.configure(
                    style=self._create_search_btn_style(f)
                )
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"Suppressed: {_e}")
        except (ImportError, Exception):
            # ttkbootstrap 없으면 tk.Label + relief='solid' 폴백
            self._search_btn = tk.Label(
                self._menu_frame, text='🔍 검색',
                font=self._tb_font_scale.body(bold=True),
                bg=self._tb_bg, fg=self._tb_underline_color,
                anchor='center', justify='center',
                padx=Spacing.MD, pady=Spacing.XS, cursor='hand2',
                relief='solid', borderwidth=1,
                highlightbackground=self._tb_underline_color,
            )
            self._search_btn.bind('<Button-1>', lambda e: self._show_search_popup())

            def _search_enter(e):
                self._search_btn.config(bg=self._tb_underline_color, fg=ThemeColors.get('statusbar_fg', True))
            def _search_leave(e):
                self._search_btn.config(bg=self._tb_bg, fg=self._tb_underline_color)
            self._search_btn.bind('<Enter>', _search_enter)
            self._search_btn.bind('<Leave>', _search_leave)

        self._search_btn.pack(side='right', padx=(Spacing.SM, Spacing.SM))

    def _create_search_btn_style(self, font_family: str) -> str:
        """검색 버튼 전용 스타일 (폰트 크기 조정)"""
        import ttkbootstrap as ttk_bs
        style = ttk_bs.Style()
        style_name = 'Search.TButton'
        try:
            _sz = self._tb_font_scale.get_size(FontStyle.BODY)
            style.configure(style_name, font=(font_family, _sz, 'bold'))
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")
        return style_name

    def _build_inbound_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        self._add_menu_items(m, [
            ('📥 PDF 스캔 입고',       lambda: self._safe_call('_on_pdf_inbound')),
            ('📝 엑셀 파일 수동 입고',  lambda: self._safe_call('_bulk_import_inventory_simple')),
            None,
            ('📋 입고현황 불러오기',    lambda: self._safe_call('_bulk_import_inventory')),
            ('📍 톤백 위치 매핑',      lambda: self._safe_call('_on_tonbag_location_upload')),
            None,
        ])
        return_sub = self._create_menu()
        return_sub.add_command(label="  📝 소량 반품 (1~2건)", command=lambda: self._show_return_dialog(0))
        return_sub.add_command(label="  📂 다량 반품 (Excel)", command=lambda: self._show_return_dialog(1))
        m.add_cascade(label="  🔄 반품 (재입고)", menu=return_sub)
        return m

    def _build_outbound_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        self._add_menu_items(m, [
            ('📋 Allocation 입력 (파일 / 붙여넣기)', lambda: self._safe_call('_on_allocation_input_unified')),
            ('📤 빠른 출고 (붙여넣기)', lambda: self._safe_call('_on_quick_outbound_paste')),
        ])
        return m

    def _build_report_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        self._add_menu_items(m, [
            ('📊 재고리스트 Excel',  lambda: self._on_export_click(option=3)),
            ('🎒 톤백리스트 Excel',  lambda: self._on_export_click(option=4)),
            None,
            ('📋 입출고 이력 조회', lambda: self._safe_call('_show_outbound_history')),
            ('📊 재고 추이 차트', lambda: self._safe_call('_show_snapshot_chart')),
            ('📄 거래명세서 생성', lambda: self._safe_call('_generate_outbound_invoice')),
        ])
        return m

    def _build_customer_report_menu(self) -> 'tk.Menu':
        """v5.5.3: 고객 보고서 메뉴"""
        m = self._create_menu()
        self._add_menu_items(m, [
            ('📝 고객 보고서 생성', lambda: self._safe_call('_generate_customer_report')),
            ('📂 보고서 양식 관리', lambda: self._safe_call('_manage_report_templates')),
            None,
            ('📋 보고서 이력 조회', lambda: self._safe_call('_show_report_history')),
        ])
        return m

    def _build_file_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        exp = self._create_menu(m)
        exp.add_command(label="  📋 통관요청 양식", command=lambda: self._on_export_click(option=1))
        exp.add_command(label="  📊 루비리 양식", command=lambda: self._on_export_click(option=2))
        exp.add_command(label="  🎒 톤백 현황", command=lambda: self._on_export_click(option=4))
        exp.add_command(label="  ⭐ 통합 현황", command=lambda: self._on_export_click(option=6))
        m.add_cascade(label="  💾 내보내기", menu=exp)
        m.add_separator()
        bak = self._create_menu(m)
        bak.add_command(label="  💾 백업 생성", command=lambda: self._on_backup('create'))
        bak.add_command(label="  🔄 복원", command=lambda: self._on_backup('restore'))
        bak.add_command(label="  📋 백업 목록", command=lambda: self._on_backup('list'))
        bak.add_command(label="  ⏰ 자동 백업 설정", command=lambda: self._safe_call('_show_auto_backup_settings'))
        m.add_cascade(label="  🔐 백업", menu=bak)
        m.add_separator()
        # v5.5.3: Gemini API (설정/도구에서 이동)
        try:
            from ..utils.constants import HAS_GEMINI
            if HAS_GEMINI:
                if not hasattr(self, '_gemini_var'):
                    self._gemini_var = tk.BooleanVar(value=getattr(self, 'use_gemini', False))
                api_sub = self._create_menu(m)
                api_sub.add_checkbutton(
                    label="  API 사용",
                    variable=self._gemini_var,
                    command=lambda: self._safe_call('_toggle_gemini')
                )
                api_sub.add_separator()
                api_sub.add_command(label="  💬 AI 채팅", command=lambda: self._safe_call('_open_ai_chat'))
                api_sub.add_command(label="  ⚙️ API 설정", command=lambda: self._safe_call('_show_api_settings'))
                api_sub.add_command(label="  🔬 API 테스트", command=lambda: self._safe_call('_test_gemini_api_connection'))
                m.add_cascade(label="  🤖 Gemini (API)", menu=api_sub)
            else:
                api_sub = self._create_menu(m)
                api_sub.add_command(label="  ⚙️ API 설정", command=lambda: self._safe_call('_show_api_settings'))
                api_sub.add_command(label="  🔬 API 테스트", command=lambda: self._safe_call('_test_gemini_api_connection'))
                m.add_cascade(label="  🤖 Gemini (API)", menu=api_sub)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"toolbar_mixin: Gemini 메뉴 추가 스킵: {_e}")
        # v5.5.3: PDF 변환 (설정/도구에서 이동)
        pdf_sub = self._create_menu(m)
        pdf_sub.add_command(label="  → Excel", command=lambda: self._safe_call('_convert_pdf_to_excel'))
        pdf_sub.add_command(label="  → Word", command=lambda: self._safe_call('_convert_pdf_to_word'))
        pdf_sub.add_separator()
        pdf_sub.add_command(label="  📁 일괄 변환", command=lambda: self._safe_call('_batch_convert_pdf_excel'))
        pdf_sub.add_command(label="  🔍 분석", command=lambda: self._safe_call('_analyze_pdf'))
        m.add_cascade(label="  📄 PDF/이미지 변환", menu=pdf_sub)
        m.add_separator()
        m.add_command(label="  ❌ 종료", command=self.root.quit)
        return m

    def _build_settings_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        # 화면
        m.add_command(label="━━ 🖥️ 화면 ━━", state='disabled', font=self._tb_font_scale.heading())
        m.add_command(label="  🔄 새로고침 (F5)", command=self._refresh_all_data)
        # 테마
        theme = self._create_menu(m)
        theme.add_command(label="━━ ☀️ Light ━━", state='disabled', font=self._tb_font_scale.heading())
        for t in ['flatly', 'cosmo', 'litera', 'minty', 'journal', 'yeti', 'morph']:
            theme.add_command(label=f"  ☀️ {t.capitalize()}", command=lambda th=t: self._change_theme(th))
        theme.add_separator()
        theme.add_command(label="━━ 🌙 Dark ━━", state='disabled', font=self._tb_font_scale.heading())
        for t in ['darkly', 'cyborg', 'superhero', 'solar', 'vapor']:
            theme.add_command(label=f"  🌙 {t.capitalize()}", command=lambda th=t: self._change_theme(th))
        m.add_cascade(label="  🎨 테마 선택", menu=theme)
        # 글꼴 크기
        fsize = self._create_menu(m)
        fsize.add_command(label="  작게 (11pt)", command=lambda: self._change_font_size(11))
        fsize.add_command(label="  보통 (13pt)", command=lambda: self._change_font_size(13))
        fsize.add_command(label="  크게 (16pt)", command=lambda: self._change_font_size(16))
        m.add_cascade(label="  🔤 글꼴 크기", menu=fsize)
        m.add_separator()
        # 도구
        m.add_command(label="━━ 🔧 도구 ━━", state='disabled', font=self._tb_font_scale.heading())
        # v5.9.0: 컨테이너 구분 옵션은 필터바 초기화 옆으로 이동
        # v3.8.4: 대시보드 자동 갱신
        if not hasattr(self, '_auto_refresh_var'):
            self._auto_refresh_var = tk.BooleanVar(value=False)
        m.add_checkbutton(
            label="  🔄 대시보드 자동 갱신 (30초)",
            variable=self._auto_refresh_var,
            command=self._on_auto_refresh_toggle
        )
        # v3.8.4: 정합성 검사
        m.add_command(
            label="  🔍 정합성 검사/복구",
            command=self._on_integrity_check
        )
        # v5.5.3: Gemini API → 📁 파일 메뉴로 이동
        m.add_separator()
        # v5.5.3: PDF 변환 → 📁 파일 메뉴로 이동
        m.add_command(label="  🩺 데이터 정합성 검사", command=lambda: self._safe_call('_run_integrity_check'))
        m.add_separator()
        m.add_command(label="  🗑️ 테스트 DB 초기화 (데이터 삭제)", command=lambda: self._safe_call('_show_test_db_reset_popup'))
        return m

    def _build_help_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        try:
            from version import __version__
            version_label = f"📝 버전 정보 (v{__version__})"
        except ImportError:
            version_label = "📝 버전 정보"
        self._add_menu_items(m, [
            ('📖 사용법 — 사용 설명서 열기', lambda: self._safe_call('_show_help')),
            ('⌨️ 단축키 안내 — 키보드 단축키 목록', lambda: self._safe_call('_show_shortcuts')),
            None,
            ('ℹ️ 시스템 정보 — Python·DB·경로 등', lambda: self._safe_call('_show_system_info')),
            (version_label + " — 앱 버전·라이선스", lambda: self._safe_call('_show_about')),
        ])
        return m

    # ═══════════════════════════════════════════════════════
    # 탭 버튼 (균등 배치)
    # ═══════════════════════════════════════════════════════

    def _build_tab_buttons(self) -> None:
        """v5.5.3 patch_01: 탭 버튼 — 밑줄+텍스트 스타일 (메뉴와 통일)"""
        f = self._toolbar_font
        tab_defs = [
            ('cargo_overview', '📋 총괄 화물 리스트',
             '상태별 화물만 표시: 전체 / 판매가능 / 판매배정(Allocation) / 판매화물 결정 / 출고. 헤더 클릭으로 오름·내림차순 정렬.'),
            ('inventory', '📦 재고리스트',
             'LOT 단위 재고 현황. 필터·기간·상태로 검색하고, 더블클릭 시 LOT 상세·톤백 목록을 볼 수 있습니다.'),
            ('outbound_scheduled', '📋 출고예정',
             '재고 리스트에서 Allocation(예약) 삭감 반영. Balance=잔량-예약. LOT 더블클릭 시 출고 이력 팝업(Excel/PDF 출력).'),
            ('tonbag',    '🎒 톤백리스트',
             '톤백 단위 현황. 선택 후 일괄 출고·라벨 출력 등이 가능합니다.'),
            ('dashboard', '📊 대시보드',
             'AVAILABLE/RESERVED/PICKED/SOLD 4단계 현황, 알림, 최근 7일 차트 등 대시보드를 표시합니다.'),
            ('log',       '📝 로그',
             '시스템·작업 로그를 확인합니다. 오류 추적이나 동작 확인에 사용하세요.'),
        ]
        self._tab_buttons = {}
        # v5.7.5: 탭은 상단 메뉴보다 작게 (Phase3: FontScale.small + Spacing)
        _tab_font = self._tb_font_scale.small()
        for key, text, tip in tab_defs:
            wrapper = tk.Frame(self._sec_tabs, bg=self._tb_bg)
            wrapper.pack(side='left', padx=Spacing.XS)

            btn = tk.Label(wrapper, text=text, font=_tab_font,
                          bg=self._tb_bg, fg=self._tb_fg_normal,
                          anchor='center', justify='center',
                          padx=Spacing.SM, pady=Spacing.XS, cursor='hand2')
            btn.pack()

            # 밑줄 (비활성 시 숨김)
            underline = tk.Frame(wrapper, height=2, bg=self._tb_underline_color)
            btn._underline = underline
            btn._wrapper = wrapper

            btn.bind('<Button-1>', lambda e, k=key: self._switch_tab(k))
            btn.bind('<Enter>', lambda e, b=btn, k=key: self._tab_hover_enter(b, k))
            btn.bind('<Leave>', lambda e, b=btn, k=key: self._tab_hover_leave(b, k))
            if tip:
                self._attach_tooltip(btn, tip)
            self._tab_buttons[key] = btn

    # ═══════════════════════════════════════════════════════
    # 자동 2줄 전환
    # ═══════════════════════════════════════════════════════

    def _check_toolbar_overflow(self, event=None) -> None:
        try:
            self.root.update_idletasks()

            win_w = self.root.winfo_width()
            need_w = self._menu_frame.winfo_reqwidth() + self._sec_tabs.winfo_reqwidth() + 60
            if need_w > win_w and not self._row2_visible:
                self._sec_tabs.pack_forget()
                self._sec_tabs.pack(in_=self._row2, fill='x', expand=True, padx=Spacing.SM)
                self._row2.pack(fill='x')
                self._row2_visible = True
            elif need_w <= win_w and self._row2_visible:
                self._sec_tabs.pack_forget()
                self._row2.pack_forget()
                self._sec_tabs.pack(in_=self._row1, fill='x', expand=True, padx=Spacing.SM, pady=(Spacing.XS, 0))
                self._row2_visible = False
        except (RuntimeError, ValueError) as _e:
            logger.debug(f"{type(_e).__name__}: {_e}")
        except (RuntimeError, ValueError) as _e:
            logger.debug(f"toolbar_mixin: {_e}")

    # ═══════════════════════════════════════════════════════
    # 탭 전환
    # ═══════════════════════════════════════════════════════

    def _switch_tab(self, tab_key: str):
        idx = self._tab_index_map.get(tab_key)
        if idx is not None and hasattr(self, 'notebook'):
            try:
                self.notebook.select(idx)
                self._active_tab_key = tab_key
                self._highlight_active_tab()
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"{type(_e).__name__}: {_e}")
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"toolbar_mixin: {_e}")

    def _highlight_active_tab(self) -> None:
        """v5.5.3 patch_01: 밑줄+텍스트로 활성 탭 강조 (Phase3: FontScale.subtitle + Spacing)"""
        _sub_font = self._tb_font_scale.subtitle(bold=True)
        _sub_font_normal = self._tb_font_scale.subtitle(bold=False)
        for key, btn in self._tab_buttons.items():
            if key == self._active_tab_key:
                btn.config(bg=self._tb_bg, fg=self._tb_fg_active,
                          relief='flat', font=_sub_font)
                btn._underline.config(bg=self._tb_underline_color)
                btn._underline.pack(fill='x', padx=Spacing.XS, pady=(Spacing.XS, 0))
            else:
                btn.config(bg=self._tb_bg, fg=self._tb_fg_normal,
                          relief='flat', font=_sub_font_normal)
                btn._underline.pack_forget()

    def _tab_hover_enter(self, btn, key: str) -> None:
        """v5.5.3 patch_01: 호버 — 텍스트 색상만 변경"""
        if key != self._active_tab_key:
            btn.config(fg=self._tb_fg_hover)

    def _tab_hover_leave(self, btn, key: str) -> None:
        """v5.5.3 patch_01: 호버 해제"""
        if key != self._active_tab_key:
            btn.config(fg=self._tb_fg_normal)

    # ═══════════════════════════════════════════════════════
    # 🔍 검색 팝업
    # ═══════════════════════════════════════════════════════

    def _show_search_popup(self) -> None:
        """v3.8.9: 검색 팝업 — DB 데이터 로드 + 재고리스트 필터링"""
        f = self._toolbar_font
        popup = tk.Toplevel(self.root)
        popup.title("🔍 검색")
        popup.geometry(DialogSize.get_geometry(self.root, 'medium'))
        apply_modal_window_options(popup)
        popup.transient(self.root)
        popup.grab_set()
        center_dialog(popup, self.root)

        main = tk.Frame(popup, padx=Spacing.LG, pady=Spacing.MD)
        main.pack(fill='both', expand=True)

        # v3.8.9: 검색 필터용 안정적 StringVar (팝업 닫혀도 유지)
        if not hasattr(self, '_search_filter_vars'):
            self._search_filter_vars = {
                'sap_no': tk.StringVar(self.root, value='전체'),
                'bl_no': tk.StringVar(self.root, value='전체'),
                'lot_no': tk.StringVar(self.root, value='전체'),
                'status': tk.StringVar(self.root, value='전체'),
                'date_from': tk.StringVar(self.root, value=''),
                'date_to': tk.StringVar(self.root, value=''),
            }
        
        svars = self._search_filter_vars
        _lab_font = self._tb_font_scale.heading()
        _body_font = self._tb_font_scale.body()

        # 콤보박스: SAP NO, BL NO, LOT NO (Phase3: Spacing + FontScale)
        combos = {}
        for row_idx, (field, label) in enumerate([
            ('sap_no', 'SAP NO'), ('bl_no', 'BL NO'), ('lot_no', 'LOT NO')
        ]):
            tk.Label(main, text=label, font=_lab_font, anchor='w'
                     ).grid(row=row_idx, column=0, sticky='w', pady=Spacing.SM)
            cb = ttk.Combobox(main, textvariable=svars[field],
                              state='readonly', width=28, font=_body_font)
            cb.grid(row=row_idx, column=1, sticky='ew', padx=(Spacing.SM, 0), pady=Spacing.SM)
            combos[field] = cb
            
            # v3.8.9: DB에서 값 로드
            # v5.6.0: SQL 인젝션 방지 — 화이트리스트 검증
            ALLOWED_FIELDS = {'sap_no', 'bl_no', 'lot_no', 'status', 'product', 'warehouse'}
            try:
                if field not in ALLOWED_FIELDS:
                    logger.warning(f"허용되지 않은 필드: {field}")
                    continue
                rows = self.engine.db.fetchall(
                    f"SELECT DISTINCT {field} FROM inventory "
                    f"WHERE {field} IS NOT NULL AND {field} != '' "
                    f"ORDER BY {field} ASC"
                )
                vals = ['전체']
                for r in rows:
                    v = r.get(field, '') if isinstance(r, dict) else (r[0] if r else '')
                    if v:
                        vals.append(str(v))
                cb['values'] = vals
                logger.debug(f"검색 팝업 [{field}]: {len(vals)-1}개 로드")
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                logger.debug(f"{type(_e).__name__}: {_e}")
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                logger.debug(f"검색 팝업 [{field}] 로드 실패: {_e}")
                cb['values'] = ['전체']

        # Date (Arrival Date 기준)
        tk.Label(main, text='Arrival Date', font=_lab_font, anchor='w'
                 ).grid(row=3, column=0, sticky='w', pady=Spacing.SM)
        df = tk.Frame(main)
        df.grid(row=3, column=1, sticky='ew', padx=(Spacing.SM, 0), pady=Spacing.SM)
        tk.Entry(df, textvariable=svars['date_from'], width=12, font=_body_font
                 ).pack(side='left')
        tk.Label(df, text=' ~ ', font=_body_font).pack(side='left')
        tk.Entry(df, textvariable=svars['date_to'], width=12, font=_body_font
                 ).pack(side='left')
        _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        _small_font = self._tb_font_scale.small()
        tk.Label(df, text='  (YYYY-MM-DD)', font=_small_font, fg=ThemeColors.get('text_muted', _is_dark)
                 ).pack(side='left', padx=Spacing.XS)

        # 상태
        tk.Label(main, text='상태', font=_lab_font, anchor='w'
                 ).grid(row=4, column=0, sticky='w', pady=Spacing.SM)
        ttk.Combobox(main, textvariable=svars['status'],
                     values=['전체', 'AVAILABLE', 'PICKED', 'SHIPPED', 'DEPLETED'],
                     state='readonly', width=28, font=_body_font
                     ).grid(row=4, column=1, sticky='ew', padx=(Spacing.SM, 0), pady=Spacing.SM)

        main.columnconfigure(1, weight=1)

        def do_search():
            """검색 실행 → 재고리스트 필터링"""
            # _inv_search_combos를 StringVar 기반으로 설정
            self._inv_search_combos = {}
            for field in ('sap_no', 'bl_no', 'lot_no'):
                self._inv_search_combos[field] = (svars[field], None)
            
            # Date, Status 반영
            if hasattr(self, '_date_from_var'):
                self._date_from_var.set(svars['date_from'].get())
            if hasattr(self, '_date_to_var'):
                self._date_to_var.set(svars['date_to'].get())
            if hasattr(self, 'status_var'):
                self.status_var.set(svars['status'].get())
            
            # 재고리스트 탭으로 이동 + 새로고침
            try:
                self.notebook.select(self.tab_inventory)
            except (AttributeError, RuntimeError) as _e:
                logger.debug(f"{type(_e).__name__}: {_e}")
            if hasattr(self, '_refresh_inventory'):
                self._refresh_inventory()
            popup.destroy()

        def do_reset():
            """초기화"""
            for key in svars:
                if key in ('date_from', 'date_to'):
                    svars[key].set('')
                else:
                    svars[key].set('전체')

        # v3.8.9: 버튼 크기 통일 (Phase3: Spacing + FontScale)
        _btn_font = self._tb_font_scale.body(bold=True)
        _btn_w = 12
        bf = tk.Frame(main)
        bf.grid(row=5, column=0, columnspan=2, pady=(Spacing.LG, 0))
        _popup_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        _btn_fg = ThemeColors.get('badge_text', _popup_dark)
        tk.Button(bf, text='🔍 검색', font=_btn_font, bg=ThemeColors.get('statusbar_progress'), fg=_btn_fg,
                 bd=0, width=_btn_w, pady=Spacing.SM, cursor='hand2',
                 command=do_search).pack(side='left', padx=Spacing.SM)
        tk.Button(bf, text='🔄 초기화', font=_btn_font, bg=ThemeColors.get('btn_neutral', _popup_dark), fg=_btn_fg,
                 bd=0, width=_btn_w, pady=Spacing.SM, cursor='hand2',
                 command=do_reset).pack(side='left', padx=Spacing.SM)

        popup.bind('<Escape>', lambda e: popup.destroy())
        popup.bind('<Return>', lambda e: do_search())

    # ═══════════════════════════════════════════════════════
    # 컨테이너 서픽스
    # ═══════════════════════════════════════════════════════

    def _on_container_suffix_toggle(self) -> None:
        """컨테이너 -1, -2 서픽스 표시 토글 — 재고/톤백 테이블의 CONTAINER 열 표시를 갱신합니다."""
        show = self._container_suffix_var.get()
        self._log(f"📦 컨테이너 구분: {'ON' if show else 'OFF'}")
        if hasattr(self, '_refresh_inventory'):
            self._refresh_inventory()
        if hasattr(self, '_refresh_tonbag'):
            self._refresh_tonbag()

    def _format_container_no(self, container_no: str) -> str:
        """컨테이너 번호 표시: _container_suffix_var가 꺼져 있으면 끝의 -1, -2 접미사를 제거합니다."""
        if not container_no:
            return ''
        if not getattr(self, '_container_suffix_var', None):
            return str(container_no)
        if not self._container_suffix_var.get():
            s = str(container_no).strip()
            if '-' in s:
                parts = s.rsplit('-', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    return parts[0].strip()
        return str(container_no)

    def _on_auto_refresh_toggle(self) -> None:
        """v3.8.4: 대시보드 자동 갱신 30초 토글"""
        enabled = self._auto_refresh_var.get()
        self._log(f"🔄 자동 갱신: {'ON (30초)' if enabled else 'OFF'}")
        if enabled:
            self._schedule_auto_refresh()
        
    def _schedule_auto_refresh(self) -> None:
        """30초 타이머로 대시보드 갱신 + DB 변경 감지 (v3.8.4)"""
        if not getattr(self, '_auto_refresh_var', None):
            return
        if not self._auto_refresh_var.get():
            return
        try:
            # DB 파일 변경 감지
            db_changed = self._check_db_modified()
            if db_changed:
                if hasattr(self, '_refresh_inventory'):
                    self._refresh_inventory()
                if hasattr(self, '_refresh_tonbag'):
                    self._refresh_tonbag()
                self._log("🔄 DB 변경 감지 → 자동 새로고침")
            
            if hasattr(self, '_refresh_dashboard'):
                self._refresh_dashboard()
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"자동 갱신 오류: {e}")
        # 30초 후 재호출
        if hasattr(self, 'root'):
            self.root.after(30000, self._schedule_auto_refresh)

    def _check_db_modified(self) -> bool:
        """v3.8.4: DB 파일 수정 시간 비교"""
        import os
        try:
            db_path = getattr(self, 'db_path', None)
            if not db_path or not os.path.exists(db_path):
                return False
            
            mtime = os.path.getmtime(db_path)
            last = getattr(self, '_last_db_mtime', 0)
            
            if mtime > last:
                self._last_db_mtime = mtime
                return last > 0  # 최초 실행 시는 False
            return False
        except (OSError, IOError, PermissionError):
            return False

    def _on_integrity_check(self) -> None:
        """v3.8.7: 정합성 검사 + 18열 데이터 누락 진단"""
        from ..utils.custom_messagebox import CustomMessageBox
        try:
            from core.validators import InventoryValidator
            validator = InventoryValidator(db=self.engine.db)
            
            # 1. 기존 정합성 검사
            result = validator.check_data_integrity()
            issues = []
            if result.errors:
                for e in result.errors:
                    issues.append(f"🔴 {e}")
            if result.warnings:
                for w in result.warnings:
                    issues.append(f"🟡 {w}")
            
            # 2. v3.8.7: 18열 데이터 누락 진단
            total_cnt = self.engine.db.fetchone("SELECT COUNT(*) AS cnt FROM inventory")
            total = (total_cnt['cnt'] if total_cnt else 0) if total_cnt else 0
            
            if total > 0:
                key_cols = [
                    ('lot_no', 'LOT NO'), ('sap_no', 'SAP NO'), ('bl_no', 'BL NO'),
                    ('container_no', 'CONTAINER'), ('product', 'PRODUCT'),
                    ('product_code', 'CODE'), ('lot_sqm', 'LOT SQM'),
                    ('mxbg_pallet', 'MXBG'), ('net_weight', 'NET(Kg)'),
                    ('gross_weight', 'GROSS(Kg)'), ('salar_invoice_no', 'INVOICE NO'),
                    ('ship_date', 'SHIP DATE'), ('arrival_date', 'ARRIVAL'),
                    ('free_time', 'FREE TIME'), ('warehouse', 'WH'),
                    ('status', 'STATUS'), ('current_weight', 'Balance'),
                    ('initial_weight', '입고량'),
                ]
                
                issues.append("")
                issues.append("━━━ 18열 데이터 완성도 ━━━")
                
                for col_db, col_label in key_cols:
                    # v5.6.0: 화이트리스트 검증 (key_cols는 하드코딩이지만 안전장치)
                    ALLOWED_COLS = {k for k, _ in key_cols}
                    if col_db not in ALLOWED_COLS:
                        continue
                    try:
                        filled_row = self.engine.db.fetchone(
                            f"SELECT COUNT(*) AS cnt FROM inventory "
                            f"WHERE {col_db} IS NOT NULL AND {col_db} != '' AND {col_db} != 0"
                        )
                        filled = (filled_row['cnt'] if filled_row else 0) if filled_row else 0
                        empty = total - filled
                        pct = filled / total * 100
                        
                        if empty > 0:
                            icon = '🔴' if pct < 50 else ('🟡' if pct < 80 else '🟢')
                            issues.append(f"{icon} {col_label:12s}: {filled}/{total} ({pct:.0f}%) — {empty}개 누락")
                        else:
                            issues.append(f"✅ {col_label:12s}: {total}/{total} (100%)")
                    except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError):
                        issues.append(f"⚪ {col_label:12s}: 확인 불가")
            
            if not issues:
                CustomMessageBox.showinfo(self.root, "✅ 정합성 검사", "모든 데이터가 정상입니다.")
                return
            
            msg = "\n".join(issues[:30])
            if len(issues) > 30:
                msg += f"\n... 외 {len(issues) - 30}건"
            
            # 복구 질문
            if result.errors or result.warnings:
                if CustomMessageBox.askyesno(self.root, "⚠️ 정합성 검사 + 18열 진단",
                    f"{msg}\n\n자동 복구를 실행할까요?"):
                    
                    fix_result = validator.fix_data_integrity(dry_run=False)
                    fixes = fix_result.get('fixes', [])
                    if fixes:
                        self._log(f"✅ 정합성 복구: {len(fixes)}건")
                        CustomMessageBox.showinfo(self.root, "복구 완료",
                            f"복구 완료: {len(fixes)}건\n\n" + "\n".join(fixes[:10]))
                        self._refresh_inventory()
                    else:
                        CustomMessageBox.showinfo(self.root, "복구", "복구할 항목이 없습니다.")
            else:
                CustomMessageBox.showinfo(self.root, "📊 18열 데이터 진단", msg)
                
        except (RuntimeError, ValueError) as e:
            CustomMessageBox.showerror(self.root, "오류", f"정합성 검사 오류:\n{e}")

    # ═══════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════
    def _restore_toolbar_chain_bg(self):
        """v5.3.5: restore toolbar/menu parent frame chain bg to theme bg.
        Fix for Windows light theme where tk_popup/grab_release refresh resets bg.
        """
        for name in ('_toolbar', '_row0', '_row1', '_menu_frame', '_row2', '_sec_tabs'):
            try:
                w = getattr(self, name, None)
                if w and w.winfo_exists():
                    w.config(bg=self._tb_bg)
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"Suppressed: {_e}")



    
    def _refresh_toolbar_theme(self) -> None:
        """v5.4.0: Apply current ThemeColors palette to existing toolbar widgets.
        Fix: light theme switching leaving toolbar colors stale or mismatched.
        """
        try:
            self._load_toolbar_colors()
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        # restore container chain bg first
        try:
            self._restore_toolbar_chain_bg()
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        for w in (getattr(self, '_toolbar_container', None), getattr(self, '_row1', None),
                  getattr(self, '_row2', None), getattr(self, '_menu_frame', None),
                  getattr(self, '_sec_tabs', None)):
            try:
                if w and w.winfo_exists():
                    w.config(bg=self._tb_bg)
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"Suppressed: {_e}")

        # v5.5.3 patch_01: 모든 메뉴 버튼 동일 스타일 적용
        for b in getattr(self, '_all_menu_btns', []):
            try:
                if not b.winfo_exists():
                    continue
                b.config(bg=self._tb_bg,
                         fg=self._tb_fg_active if getattr(b, '_menu_active', False) else self._tb_fg_normal)
                # 밑줄 색상도 테마에 맞게 갱신
                if hasattr(b, '_underline') and b._underline.winfo_exists():
                    b._underline.config(bg=self._tb_underline_color)
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"Suppressed: {_e}")


        # v5.4.1: 드롭다운 tk.Menu 팔레트도 테마에 맞게 재동기화(화이트 모드 검정 변색 방지)
        try:
            is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
            menu_bg = ThemeColors.get('bg_card', is_dark)
            menu_fg = ThemeColors.get('text_primary', is_dark)
            menu_abg = ThemeColors.get('bg_hover', is_dark)
            menu_afg = ThemeColors.get('text_primary', is_dark)
            menu_dis = ThemeColors.get('text_muted', is_dark)
            for m in getattr(self, '_all_dropdown_menus', []):
                try:
                    if m and m.winfo_exists():
                        m.config(bg=menu_bg, fg=menu_fg, activebackground=menu_abg, activeforeground=menu_afg, disabledforeground=menu_dis)
                except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                    logger.debug(f"Suppressed: {_e}")
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        # v5.5.3 patch_01: 탭 버튼도 테마 갱신
        try:
            if hasattr(self, '_tab_buttons'):
                self._highlight_active_tab()
                for key, btn in self._tab_buttons.items():
                    if hasattr(btn, '_wrapper') and btn._wrapper.winfo_exists():
                        btn._wrapper.config(bg=self._tb_bg)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        # v5.5.3 patch_02: 검색 버튼 밑줄 색상 갱신 (폴백 tk.Label용)
        try:
            sb = getattr(self, '_search_btn', None)
            if sb and sb.winfo_exists() and isinstance(sb, tk.Label):
                sb.config(fg=self._tb_underline_color,
                          highlightbackground=self._tb_underline_color)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        try:
            self.root.after_idle(lambda: self.root.update_idletasks())
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
            try:
                self.root.update_idletasks()
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"Suppressed: {_e}")

    def _show_menu(self, menu, btn) -> None:
        """
        v5.0.9: tk_popup + after()로 확실한 색상 복구
        
        Windows White 테마에서 tk_popup() 후 grab_release() 시
        tkinter가 내부적으로 위젯 배경을 시스템 기본색으로 리셋하는 문제.
        after()로 지연 복구 + 부모 프레임 배경까지 재설정으로 100% 해결.
        """
        # 모든 버튼 비활성
        for b in self._all_menu_btns:
            b._menu_active = False
            try:
                b.config(fg=self._tb_fg_normal)
                if hasattr(b, '_underline'):
                    b._underline.pack_forget()
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"Suppressed: {_e}")

        # 현재 버튼만 활성 (밑줄 + 흰색 텍스트)
        btn._menu_active = True
        btn.config(fg=self._tb_fg_active)
        if hasattr(btn, '_underline'):
            btn._underline.place(relx=0, rely=1.0, relwidth=1.0, anchor='sw')
        
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height()
        
        def _restore_all_buttons():
            """모든 버튼 + 부모 프레임 색상 강제 복구"""
            try:
                # v5.3.6: capture before state for anomaly logging
                _before = {
                    'tb_bg': getattr(self, '_tb_bg', None),
                    'menu_frame_bg': safe_widget_bg(getattr(self, '_menu_frame', None)),
                    'row1_bg': safe_widget_bg(getattr(self, '_row1', None)),
                }

                # v5.3.5: 상위 체인까지 통째로 bg 복구
                self._restore_toolbar_chain_bg()
                # 부모 프레임 배경도 재설정 (White 테마 핵심!)
                if hasattr(self, '_menu_frame') and self._menu_frame.winfo_exists():
                    self._menu_frame.config(bg=self._tb_bg)
                if hasattr(self, '_row1') and self._row1.winfo_exists():
                    self._row1.config(bg=self._tb_bg)
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"[toolbar_mixin] 무시: {_e}")
            
            for b in self._all_menu_btns:
                b._menu_active = False
                try:
                    if not b.winfo_exists():
                        continue
                    # v5.5.3 patch_01: 텍스트 색상만 복구 (배경 변경 없음)
                    mx = b.winfo_pointerx() - b.winfo_rootx()
                    my = b.winfo_pointery() - b.winfo_rooty()
                    is_hover = (0 <= mx <= b.winfo_width() and
                               0 <= my <= b.winfo_height())
                    b.config(fg=self._tb_fg_hover if is_hover else self._tb_fg_normal)
                    if hasattr(b, '_underline'):
                        b._underline.pack_forget()
                except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                    logger.debug(f"Suppressed: {_e}")
            
            # 강제 화면 갱신 (White 테마에서 필수)
            try:
                self.root.update_idletasks()

                # v5.3.6: detect light theme bg reset and log once per restore call
                _after = {
                    'menu_frame_bg': safe_widget_bg(getattr(self, '_menu_frame', None)),
                    'row1_bg': safe_widget_bg(getattr(self, '_row1', None)),
                }
                try:
                    exp = getattr(self, '_tb_bg', None)
                    if exp and (_after.get('menu_frame_bg') not in (None, exp) or _after.get('row1_bg') not in (None, exp)):
                        log_ui_event('UI_BG_ANOMALY_TOOLBAR', {
                            'expected': exp,
                            'before': _before,
                            'after': _after,
                        })
                except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                    logger.debug(f"Suppressed: {_e}")
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"[toolbar_mixin] 무시: {_e}")
        
        try:
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"[toolbar_mixin] 무시: {_e}")
            
            btn._menu_active = False
            
            # v5.3.5: after_idle 1회 + after()로 지연 복구 (50/200/500/1000ms)
            # White 테마에서 tkinter 내부 갱신이 느릴 수 있으므로 4회 보장
            try:
                self.root.after_idle(_restore_all_buttons)
                self.root.after(50, _restore_all_buttons)
                self.root.after(200, _restore_all_buttons)
                self.root.after(500, _restore_all_buttons)
                self.root.after(1000, _restore_all_buttons)
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
                _restore_all_buttons()
    
    def _safe_call(self, method_name: str):
        """메서드 안전 호출 (존재하지 않으면 경고 메시지)"""
        fn = getattr(self, method_name, None)
        if fn and callable(fn):
            fn()
        else:
            logger.warning(f"메서드 미정의: {method_name}")
            try:
                CustomMessageBox.warning(None, "기능 준비 중", f"'{method_name}' 기능은 아직 구현되지 않았습니다.")
            except (ImportError, ModuleNotFoundError) as _e:
                logger.debug(f"{type(_e).__name__}: {_e}")
            except (ImportError, ModuleNotFoundError) as _e:
                logger.debug(f"toolbar_mixin: {_e}")

    def _attach_tooltip(self, widget, text: str):
        tip_win = None
        after_id = None
        def show():
            nonlocal tip_win
            if tip_win: return
            x = widget.winfo_rootx() + 10
            y = widget.winfo_rooty() + widget.winfo_height() + 5
            tip_win = tk.Toplevel(widget)
            tip_win.wm_overrideredirect(True)
            tip_win.wm_geometry(f"+{x}+{y}")
            _tip_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
            tk.Label(tip_win, text=text, justify='left',
                     background=ThemeColors.get('bg_card', _tip_dark), foreground=ThemeColors.get('text_primary', _tip_dark),
                     relief='solid', borderwidth=1,
                     font=self._tb_font_scale.body(), padx=Spacing.SM, pady=Spacing.SM,
                     wraplength=350).pack()
        def schedule(e):
            nonlocal after_id
            cancel(e)
            after_id = widget.after(400, show)
        def cancel(e):
            nonlocal tip_win, after_id
            if after_id: widget.after_cancel(after_id); after_id = None
            if tip_win: tip_win.destroy(); tip_win = None
        widget.bind('<Enter>', schedule, add='+')
        widget.bind('<Leave>', cancel, add='+')
        widget.bind('<Button-1>', cancel, add='+')

    def _refresh_all_data(self) -> None:
        try:
            for fn in ['_refresh_inventory', '_refresh_outbound_scheduled', '_refresh_tonbag', '_refresh_dashboard']:
                if hasattr(self, fn): getattr(self, fn)()
            self._log("🔄 전체 새로고침 완료")
        except (RuntimeError, OSError) as e:
            logger.error(f"새로고침: {e}")

    def _change_font_size(self, size: int):
        try:
            import tkinter.font as tkfont
            for name in ["TkDefaultFont", "TkTextFont"]:
                tkfont.nametofont(name).configure(size=size)
            self._log(f"🔤 글꼴 크기: {size}pt")
        except (RuntimeError, ValueError) as e:
            logger.error(f"글꼴 크기: {e}")