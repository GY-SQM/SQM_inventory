from ..utils.custom_messagebox import CustomMessageBox

"""
SQM v3.8.4 — 통합 메뉴바
=========================
순서: [입고▼] [출고▼] [보고서▼] [🔍검색] │ [파일▼] [설정/도구▼] [도움말▼]
      ← 업무 메뉴 (좌측) →              │  ← 시스템 메뉴 (우측) →
+ 탭 전환 버튼 (균등 배치)
+ 자동 2줄 전환
"""
import logging
import sqlite3
import tkinter as tk
from tkinter import ttk

from utils.ui_debug import log_ui_event, safe_widget_bg  # v5.3.6

from ..utils.ui_constants import (
    DialogSize,
    FontScale,
    FontStyle,
    Spacing,
    ThemeColors,
    apply_modal_window_options,
    center_dialog,
    get_font_scale,
)

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

    def _get_return_doc_review_pending_count(self, days: int = 30) -> int:
        """최근 N일 반품 문서점검 대기건(RETURN_DOC_REVIEW) 개수."""
        try:
            row = self.engine.db.fetchone(
                """
                SELECT COUNT(*) AS cnt
                FROM stock_movement
                WHERE movement_type = 'RETURN_DOC_REVIEW'
                  AND DATE(created_at) >= DATE('now', ?)
                """,
                (f"-{int(days)} days",),
            )
            if not row:
                return 0
            return int((row.get('cnt') if isinstance(row, dict) else row[0]) or 0)
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError, TypeError, KeyError, AttributeError) as e:
            logger.debug(f"반품 문서점검 카운트 조회 오류: {e}")
            return 0

    @staticmethod
    def _format_return_review_badge(count: int) -> str:
        """
        반품 문서점검 메뉴 배지 문자열.
        - 0건: 표시 없음
        - 1~4건: 🟡 [N]
        - 5건 이상: 🔴 [N]
        """
        if count <= 0:
            return ""
        icon = "🔴" if count >= 5 else "🟡"
        return f" {icon} [{count}]"

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

        # Row1: 오른쪽 액션(새로고침/버전 배지)
        self._right_actions = tk.Frame(self._row1, bg=self._tb_bg)
        self._right_actions.pack(side='right', padx=Spacing.MD)
        self._build_refresh_button(self._right_actions)

        # v4.0.0: 오른쪽 버전 배지 (Phase3: FontScale body/heading)
        try:
            from version import APP_NAME, __version__
            ver_frame = tk.Frame(self._right_actions, bg=self._tb_bg)
            ver_frame.pack(side='left', padx=(Spacing.SM, 0))
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
        # v7.0: 4단계 탭 순서 — AVAILABLE(0), ALLOCATION(1), PICKED(2), SOLD(3), 대시보드(4), 로그(5)
        # 4개 메인 + 총괄 재고 리스트 + 통계 + 로그
        self._tab_index_map = {'inventory': 0, 'allocation': 1, 'picked': 2, 'sold': 3, 'cargo_overview': 4, 'dashboard': 5, 'log': 6}
        self._active_tab_key = 'inventory'

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
             '파일 관리 메뉴입니다. 열기, 백업, 복원, 종료를 한 흐름으로 처리합니다. 예: 대량 작업 전 백업을 생성한 뒤 파일 작업을 진행합니다.'),
            ('📥 입고 ▼',      self._build_inbound_menu,
             '입고 처리 메뉴입니다. 입고 등록부터 D/O 후속 연결, 반품 재입고까지 순서대로 진행합니다. 예: 원스톱 입고 후 입고 현황에서 결과를 확인합니다.'),
            ('📤 출고 ▼',      self._build_outbound_menu,
             '출고 실행 메뉴입니다. 배정 입력, 피킹 리스트 업로드, 출고 처리와 이력 확인을 한 번에 수행합니다. 예: 승인 반영 후 피킹 파일을 올려 출고를 진행합니다.'),
            ('📊 재고 ▼',      self._build_report_menu,
             '재고 조회 메뉴입니다. LOT와 톤백 현황 확인, 내보내기 작업을 빠르게 실행합니다. 예: 상태별 재고를 확인한 뒤 통합 현황 파일로 저장합니다.'),
            ('📝 보고서 ▼',    self._build_customer_report_menu,
             '보고서 생성 메뉴입니다. 거래명세서와 고객/기간 보고서를 조건에 맞춰 출력합니다. 예: 기간을 지정한 뒤 PDF 보고서를 생성해 공유하세요.'),
            ('🔧 설정/도구 ▼', self._build_settings_menu,
             '설정 및 점검 메뉴입니다. 테마, API, 정합성 검사와 운영 도구를 관리합니다. 예: 작업 전 정합성 검사를 실행해 경고 항목을 먼저 정리합니다.'),
            ('❓ 도움말 ▼',    self._build_help_menu,
             '도움말 메뉴입니다. 매뉴얼, 단축키, 버전·시스템 정보를 빠르게 확인할 수 있습니다. 예: 기능이 헷갈릴 때 단축키 안내부터 확인하세요.'),
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
                self._attach_tooltip(
                    btn,
                    self._fit_tooltip_length(tooltip, label=text, item_type='cascade')
                )

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

    def _build_refresh_button(self, parent) -> None:
        """메인 화면 새로고침 버튼 (F5)"""
        try:
            btn = tk.Label(
                parent, text='🔄 새로고침',
                font=self._tb_font_scale.body(bold=True),
                bg=self._tb_bg, fg=self._tb_fg_normal,
                anchor='center', justify='center',
                padx=Spacing.SM, pady=Spacing.XS, cursor='hand2'
            )
            btn.pack(side='left')
            btn.bind('<Button-1>', lambda e: self._refresh_all_data())
            btn.bind('<Enter>', lambda e: btn.config(fg=self._tb_fg_hover))
            btn.bind('<Leave>', lambda e: btn.config(fg=self._tb_fg_normal))
            self._refresh_btn = btn
            self._attach_tooltip(btn, "전체 탭 새로고침 (F5)")
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"refresh button: {_e}")

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
        """v6.0.6 3단계: 입고 드롭다운 — menu_registry 기반 (custom_menubar·네이티브 메뉴와 동일 항목)"""
        m = self._create_menu()
        try:
            from ..menu_registry import (
                FILE_MENU_INBOUND_ITEMS,
                FILE_MENU_INBOUND_RETURN_SUB_ITEMS,
            )
            for entry in FILE_MENU_INBOUND_ITEMS:
                if entry is None:
                    m.add_separator()
                    continue
                label, method_name = entry[0], entry[1]
                optional = entry[2] if len(entry) > 2 else False
                if optional and not callable(getattr(self, method_name, None)):
                    continue
                if method_name == "_show_return_dialog":
                    m.add_separator()
                    return_sub = self._create_menu()
                    _show_return = getattr(self, "_show_return_dialog", None)
                    if callable(_show_return):
                        for sub_label, mode in FILE_MENU_INBOUND_RETURN_SUB_ITEMS:
                            return_sub.add_command(label=f"  {sub_label}", command=lambda md=mode: _show_return(md))
                    pending = self._get_return_doc_review_pending_count(30)
                    badge = self._format_return_review_badge(pending)
                    m.add_cascade(label=f"  {label}{badge}", menu=return_sub)
                else:
                    m.add_command(label=f"  {label}", command=lambda mn=method_name: self._safe_call(mn))
        except ImportError:
            self._add_menu_items(m, [
                ('📄 PDF 스캔 입고', lambda: self._safe_call('_on_pdf_inbound')),
                ('📊 엑셀 파일 수동 입고', lambda: self._safe_call('_bulk_import_inventory_simple')),
                ('📂 반품 입고 (Excel)', lambda: self._safe_call('_on_return_inbound_upload')),
                None,
            ])
            return_sub = self._create_menu()
            _show_return = getattr(self, "_show_return_dialog", None)
            if callable(_show_return):
                return_sub.add_command(label="  📝 소량 반품 (1~2건)", command=lambda: _show_return(0))
                return_sub.add_command(label="  📂 다량 반품 (Excel)", command=lambda: _show_return(1))
            pending = self._get_return_doc_review_pending_count(30)
            badge = self._format_return_review_badge(pending)
            m.add_cascade(label=f"  🔄 반품 (재입고){badge}", menu=return_sub)
        return m

    def _build_outbound_menu(self) -> 'tk.Menu':
        """v6.0.2: 출고 드롭다운 — menu_registry 기반 (Picking List·바코드·Sales Order 포함, 누락 방지)"""
        m = self._create_menu()
        items = []
        try:
            from ..menu_registry import FILE_MENU_OUTBOUND_ITEMS
            for entry in FILE_MENU_OUTBOUND_ITEMS:
                if entry is None:
                    items.append(None)
                    continue
                label, method_name = entry[0], entry[1]
                optional = entry[2] if len(entry) > 2 else False
                if optional and not callable(getattr(self, method_name, None)):
                    continue
                items.append((label, lambda mn=method_name: self._safe_call(mn)))
            self._add_menu_items(m, items)
        except ImportError:
            self._add_menu_items(m, [
                ('📋 Allocation 입력 (파일 / 붙여넣기)', lambda: self._safe_call('_on_allocation_input_unified')),
                ('📋 Picking List 업로드 (PDF)', lambda: self._safe_call('_on_picking_list_upload')),
            ])
        return m

    def _build_report_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        self._add_menu_items(m, [
            ('📊 LOT 리스트 Excel',  lambda: self._on_export_click(option=3)),
            ('🎒 톤백리스트 Excel',  lambda: self._on_export_click(option=4)),
            None,
            ('📋 출고 현황 조회', lambda: self._safe_call('_show_outbound_history')),
            ('📊 재고 추이 차트', lambda: self._safe_call('_show_snapshot_chart')),
        ])
        return m

    def _build_customer_report_menu(self) -> 'tk.Menu':
        """v5.5.3: 고객 보고서 메뉴"""
        m = self._create_menu()
        self._add_menu_items(m, [
            ('📄 거래명세서 생성', lambda: self._safe_call('_generate_outbound_invoice')),
            None,
            ('📝 고객 보고서 생성', lambda: self._safe_call('_generate_customer_report')),
            ('📂 보고서 양식 관리', lambda: self._safe_call('_manage_report_templates')),
            None,
            ('📋 보고서 이력 조회', lambda: self._safe_call('_show_report_history')),
        ])
        return m

    def _build_file_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        from ..menu_registry import FILE_MENU_BACKUP_ITEMS, FILE_MENU_EXPORT_ITEMS
        exp = self._create_menu(m)
        for label, option in FILE_MENU_EXPORT_ITEMS:
            exp.add_command(label=f"  {label}", command=lambda op=option: self._on_export_click(option=op))
        m.add_cascade(label="  💾 내보내기", menu=exp)
        m.add_separator()
        bak = self._create_menu(m)
        for label, method_name in FILE_MENU_BACKUP_ITEMS:
            bak.add_command(label=f"  {label}", command=lambda mn=method_name: self._safe_call(mn))
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
        if not hasattr(self, '_dev_mode_var'):
            _dev_on = self._is_developer_mode_enabled() if hasattr(self, '_is_developer_mode_enabled') else False
            self._dev_mode_var = tk.BooleanVar(value=_dev_on)
        m.add_checkbutton(
            label="  🧪 개발자 모드",
            variable=self._dev_mode_var,
            command=self._on_toggle_developer_mode
        )
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
        m.add_command(
            label="  🧪 운영 DB 스키마 점검(1회)",
            command=self._on_operational_schema_check_once
        )
        # v5.5.3: Gemini API → 📁 파일 메뉴로 이동
        m.add_separator()
        # v5.5.3: PDF 변환 → 📁 파일 메뉴로 이동
        m.add_command(label="  🩺 데이터 정합성 검사", command=lambda: self._safe_call('_run_integrity_check'))
        m.add_separator()
        if hasattr(self, '_is_developer_mode_enabled') and self._is_developer_mode_enabled():
            m.add_command(label="  🗑️ 테스트 DB 초기화 (데이터 삭제)", command=lambda: self._safe_call('_show_test_db_reset_popup'))
        return m

    def _on_toggle_developer_mode(self) -> None:
        enabled = bool(getattr(self, '_dev_mode_var', None) and self._dev_mode_var.get())
        ok = self._set_developer_mode_enabled(enabled) if hasattr(self, '_set_developer_mode_enabled') else False
        if not ok:
            CustomMessageBox.showerror(self.root, "개발자 모드", "설정을 저장하지 못했습니다.")
            return
        state_txt = "ON" if enabled else "OFF"
        self._log(f"개발자 모드 변경: {state_txt}")
        CustomMessageBox.showinfo(
            self.root,
            "개발자 모드",
            f"개발자 모드가 {state_txt}로 저장되었습니다.\n메뉴 반영을 위해 앱을 다시 열어주세요."
        )

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
        # 4개 메인(한글) + 총괄 재고 리스트 + 통계 + 로그
        tab_defs = [
            ('inventory', '📦 판매가능',
             'LOT 리스트(판매가능). 필터·검색 후 더블클릭 시 LOT 상세·톤백. [전체 톤백 펼치기]로 해당 상태 톤백 일괄 표시.'),
            ('allocation', '📋 판매배정',
             'LOT 리스트(판매배정). [전체 배정 보기]로 톤백 일괄 표시.'),
            ('picked', '🚛 판매화물 결정',
             'LOT 리스트(판매화물 결정). [전체 피킹 보기].'),
            ('sold', '✅ 출고',
             'LOT/톤백 리스트(출고 완료). [전체 판매 보기].'),
            ('cargo_overview', '📋 총괄 재고 리스트',
             '상태별 화물 한눈에 (전체/판매가능/판매배정/판매화물 결정/출고).'),
            ('dashboard', '📊 대시보드',
             '4단계 현황, 알림, 최근 7일 차트 등.'),
            ('log', '📝 로그',
             '시스템·작업 로그. 오류 추적·동작 확인.'),
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
        """v5.5.3 / v7.0: 밑줄+텍스트 강조. 4개 메인 탭별 밑줄 색(파랑/주황/초록/회색)."""
        _sub_font = self._tb_font_scale.subtitle(bold=True)
        _sub_font_normal = self._tb_font_scale.subtitle(bold=False)
        _dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        tab_colors = {
            'inventory': ThemeColors.get('info', _dark),
            'allocation': ThemeColors.get('warning', _dark),
            'picked': ThemeColors.get('success', _dark),
            'sold': ThemeColors.get('text_muted', _dark) or '#888888',
            'cargo_overview': ThemeColors.get('info', _dark),
        }
        for key, btn in self._tab_buttons.items():
            if key == self._active_tab_key:
                btn.config(bg=self._tb_bg, fg=self._tb_fg_active,
                          relief='flat', font=_sub_font)
                btn._underline.config(bg=tab_colors.get(key, self._tb_underline_color))
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
        """v3.8.9: 검색 팝업 — DB 데이터 로드 + LOT 리스트 필터링"""
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
            """검색 실행 → LOT 리스트 필터링"""
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

            # AVAILABLE(LOT 리스트) 탭으로 이동 + 새로고침
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
        if hasattr(self, '_deferred_refresh_main_tabs'):
            self._deferred_refresh_main_tabs(delay_ms=50)
        else:
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

    def _on_operational_schema_check_once(self) -> None:
        """운영 DB 기준 스키마 점검(1회) — Allocation 원장화 필수 항목 확인."""
        try:
            db = getattr(getattr(self, "engine", None), "db", None)
            if db is None:
                CustomMessageBox.showwarning(self.root, "스키마 점검", "DB 연결이 없어 점검할 수 없습니다.")
                return

            def _table_exists(name: str) -> bool:
                row = db.fetchone(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (name,)
                )
                return bool(row)

            def _index_exists(name: str) -> bool:
                row = db.fetchone(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                    (name,)
                )
                return bool(row)

            def _cols(name: str) -> set:
                rows = db.fetchall(f"PRAGMA table_info({name})") or []
                return {str(r.get("name", "")).strip().lower() for r in rows}

            checks = []
            checks.append(("table:allocation_import_batch", _table_exists("allocation_import_batch")))
            checks.append(("table:lot_reservation", _table_exists("lot_reservation")))

            sm_cols = _cols("stock_movement")
            ap_cols = _cols("allocation_plan")
            req_sm = {"ref_table", "ref_id", "source", "actor", "details_json"}
            req_ap = {"import_batch_id", "line_no", "gate_status", "fail_code", "fail_reason", "validated_at"}
            checks.append(("stock_movement.ref_trace_cols", req_sm.issubset(sm_cols)))
            checks.append(("allocation_plan.gate_cols", req_ap.issubset(ap_cols)))
            checks.append(("index:ux_alloc_line", _index_exists("ux_alloc_line")))
            checks.append(("index:idx_stock_mv_ref", _index_exists("idx_stock_mv_ref")))

            ok_count = sum(1 for _, ok in checks if ok)
            ng = [name for name, ok in checks if not ok]
            lines = [
                f"[운영 DB 스키마 점검 결과] {ok_count}/{len(checks)} 통과",
                "",
            ]
            for name, ok in checks:
                lines.append(f"{'✅' if ok else '❌'} {name}")
            if ng:
                lines += [
                    "",
                    "누락 항목이 있어도 앱 재시작 시 마이그레이션으로 자동 보정될 수 있습니다.",
                    "재시작 후 다시 점검해도 동일하면 알려주세요.",
                ]
                CustomMessageBox.showwarning(self.root, "운영 DB 스키마 점검", "\n".join(lines))
            else:
                CustomMessageBox.showinfo(self.root, "운영 DB 스키마 점검", "\n".join(lines))
        except Exception as e:
            logger.error(f"운영 DB 스키마 점검 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.root, "스키마 점검 오류", str(e))

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
            self._hide_active_menu_tooltip()
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
            self._prepare_menu_tooltip_bindings(menu)
            menu.tk_popup(x, y)
        finally:
            self._hide_active_menu_tooltip()
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
        text = self._fit_tooltip_length(text)
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

    # ---------------------------------------------------------------------
    # 메뉴/서브메뉴 공통 툴팁 엔진
    # 기준:
    # 1) 명시 툴팁이 있으면 우선 사용
    # 2) 없으면 라벨 기반 자동 설명 생성
    # 3) 파괴/위험성 있는 작업(삭제/초기화/종료 등)은 경고성 문구 추가
    # 4) 툴팁은 예시 포함, 길이는 약 120자(100~130자)로 보정
    # ---------------------------------------------------------------------
    def _prepare_menu_tooltip_bindings(self, root_menu: 'tk.Menu') -> None:
        """팝업 직전에 메뉴 트리 전체에 hover 툴팁 바인딩을 준비한다."""
        visited = set()

        def _walk(menu_obj: 'tk.Menu') -> None:
            if menu_obj is None:
                return
            menu_id = str(menu_obj)
            if menu_id in visited:
                return
            visited.add(menu_id)

            if not getattr(menu_obj, '_sqm_menu_tooltip_bound', False):
                try:
                    menu_obj.bind('<<MenuSelect>>', lambda e, m=menu_obj: self._on_menu_select_for_tooltip(m), add='+')
                    menu_obj.bind('<Unmap>', lambda e: self._hide_active_menu_tooltip(), add='+')
                    menu_obj.bind('<Leave>', lambda e: self._hide_active_menu_tooltip(), add='+')
                    menu_obj._sqm_menu_tooltip_bound = True
                except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as e:
                    logger.debug(f"menu tooltip bind skip: {e}")

            try:
                end_idx = menu_obj.index('end')
                if end_idx is None:
                    return
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
                return

            for idx in range(int(end_idx) + 1):
                try:
                    if menu_obj.type(idx) != 'cascade':
                        continue
                    sub_menu_name = menu_obj.entrycget(idx, 'menu')
                    if not sub_menu_name:
                        continue
                    sub_menu = menu_obj.nametowidget(sub_menu_name)
                    _walk(sub_menu)
                except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
                    continue

        _walk(root_menu)

    def _on_menu_select_for_tooltip(self, menu_obj: 'tk.Menu') -> None:
        """활성 메뉴 항목을 감지해 툴팁을 표시한다."""
        try:
            active_idx = menu_obj.index('active')
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
            active_idx = None

        if active_idx is None:
            self._hide_active_menu_tooltip()
            return

        try:
            item_type = menu_obj.type(active_idx)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
            self._hide_active_menu_tooltip()
            return

        if item_type in ('separator', 'tearoff'):
            self._hide_active_menu_tooltip()
            return

        tip_text = self._get_menu_entry_tooltip(menu_obj, int(active_idx), item_type)
        if not tip_text:
            self._hide_active_menu_tooltip()
            return

        try:
            x, y = self.root.winfo_pointerxy()
            self._show_active_menu_tooltip(x + 14, y + 20, tip_text)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
            self._hide_active_menu_tooltip()

    def _get_menu_entry_tooltip(self, menu_obj: 'tk.Menu', idx: int, item_type: str) -> str:
        """명시 툴팁 또는 라벨 기반 자동 툴팁을 반환한다."""
        try:
            raw_label = str(menu_obj.entrycget(idx, 'label') or '')
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
            raw_label = ''
        label = self._normalize_menu_label(raw_label)

        fixed_tip = self._get_fixed_menu_tooltip(label, item_type)
        if fixed_tip:
            return self._fit_tooltip_length(fixed_tip, label=label, item_type=item_type)

        explicit = getattr(menu_obj, '_sqm_entry_tooltips', None)
        if isinstance(explicit, dict):
            value = explicit.get(idx)
            if value:
                return self._fit_tooltip_length(str(value), label=label, item_type=item_type)

        if not label:
            return ''

        inferred = self._infer_menu_tooltip(label, item_type)
        return self._fit_tooltip_length(inferred, label=label, item_type=item_type)

    def _normalize_menu_label(self, label: str) -> str:
        """메뉴 라벨의 장식 문자/여백을 정리해 의미만 남긴다."""
        cleaned = str(label or '').replace('\t', ' ').replace('  ', ' ').strip()
        for token in ['▼', '━━', '→']:
            cleaned = cleaned.replace(token, ' ')
        return " ".join(cleaned.split()).strip(' -')

    def _infer_menu_tooltip(self, label: str, item_type: str) -> str:
        """메뉴 라벨에서 목적을 추론해 툴팁 문구를 생성한다."""
        low = label.lower()
        danger_keywords = ('삭제', '초기화', '종료', '복원', '취소')
        export_keywords = ('내보내기', '저장', 'pdf', 'excel', '리포트', '보고서')
        open_keywords = ('열기', '조회', '설정', '정보', '도움말')

        if item_type == 'cascade':
            if '반품' in label:
                return f"'{label}' 하위 메뉴를 열어 반품 관련 작업을 선택합니다."
            if '백업' in label:
                return f"'{label}' 하위 메뉴를 열어 백업/복원 작업을 선택합니다."
            return f"'{label}' 하위 메뉴를 엽니다."

        if any(k in label for k in danger_keywords):
            return f"'{label}' 작업을 실행합니다. 데이터 변경이 발생할 수 있으니 내용을 확인하세요."
        if any(k in low for k in export_keywords):
            return f"'{label}' 기능을 실행해 파일 생성/내보내기를 진행합니다."
        if any(k in label for k in open_keywords):
            return f"'{label}' 화면 또는 기능을 엽니다."
        if '새로고침' in label:
            return f"'{label}'를 실행해 현재 데이터를 다시 불러옵니다."
        if '검사' in label or '검증' in label:
            return f"'{label}'를 실행해 데이터 상태를 점검합니다."
        return f"'{label}' 기능을 실행합니다."

    def _get_fixed_menu_tooltip(self, label: str, item_type: str) -> str:
        """2차 대상(대표 20개) 메뉴 항목의 고정 툴팁 문구."""
        if item_type not in ('command', 'checkbutton', 'radiobutton', 'cascade'):
            return ''

        # 정규화된 라벨 exact 매칭 + 부분 매칭 혼합
        exact_rules = {
            "백업 생성": "백업 생성 기능입니다. 현재 DB를 안전하게 보관해 복구 기준점을 만듭니다. 예: 대량 입출고 전에 백업을 먼저 생성한 뒤 작업을 시작합니다.",
            "복원": "복원 기능입니다. 선택한 백업 시점으로 DB를 되돌립니다. 예: 잘못 반영된 작업이 생기면 최근 정상 백업을 선택해 즉시 복원합니다.",
            "백업 목록": "백업 목록 조회 기능입니다. 백업 파일과 생성 시점을 확인할 수 있습니다. 예: 복원 전에 최신 정상 백업의 날짜를 먼저 확인합니다.",
            "자동 백업 설정": "자동 백업 설정 기능입니다. 주기 백업으로 운영 중 데이터 손실 위험을 줄입니다. 예: 업무시간에는 30분 또는 1시간 간격으로 설정합니다.",
            "소량 반품 (1~2건)": "소량 반품 처리 기능입니다. 1~2건 반품을 화면에서 바로 재입고로 반영합니다. 예: 단건 반품 접수 시 LOT 확인 후 즉시 처리합니다.",
            "다량 반품 (Excel)": "다량 반품 일괄 처리 기능입니다. 엑셀 반품 데이터를 한 번에 재입고로 반영합니다. 예: 월말 반품 파일을 업로드해 일괄 처리합니다.",
            "D/O 후속 연결": "D/O 후속 연결 기능입니다. 입고 후 도착한 D/O 문서를 기존 LOT 정보에 보강합니다. 예: Free Time 누락 LOT를 선택해 도착 정보를 연결합니다.",
            "Picking List 업로드 (PDF)": "피킹 리스트 업로드 기능입니다. PDF에서 출고 대상 LOT와 수량을 불러옵니다. 예: 선적 전 받은 피킹 PDF를 올려 출고 준비를 시작합니다.",
            "바코드 스캔 업로드 (CSV/Excel)": "바코드 스캔 업로드 기능입니다. 현장 스캔 결과를 출고 데이터에 빠르게 반영합니다. 예: 스캔 CSV/Excel 파일을 올려 피킹 결과를 검증합니다.",
            "일괄 변환": "일괄 변환 기능입니다. 여러 문서를 한 번에 변환해 반복 작업 시간을 줄입니다. 예: 월간 PDF 묶음을 선택해 일괄 변환으로 처리합니다.",
            "분석": "문서 분석 기능입니다. 문서 구조와 필드 인식 가능 여부를 먼저 점검합니다. 예: 신규 양식은 변환 전에 분석으로 품질을 확인합니다.",
            "정합성 검사/복구": "정합성 검사/복구 기능입니다. 데이터 오류를 점검하고 복구 가능한 항목을 안내합니다. 예: 수량 불일치가 보이면 즉시 검사/복구를 실행합니다.",
            "데이터 정합성 검사": "데이터 정합성 검사 기능입니다. 입출고 및 재고 연결 상태를 종합 점검합니다. 예: 마감 전에 검사를 실행해 누락·중복 데이터를 정리합니다.",
            "운영 DB 스키마 점검(1회)": "운영 DB 스키마 점검 기능입니다. 컬럼·인덱스 상태를 1회 확인합니다. 예: 패치 적용 직후 점검을 실행해 누락 스키마를 확인합니다.",
            "테스트 DB 초기화 (데이터 삭제)": "테스트 DB 초기화 기능입니다. 검증용 데이터를 삭제해 환경을 다시 구성합니다. 예: 재테스트 전에 초기화해 깨끗한 상태로 시작합니다.",
            "AI 채팅": "AI 채팅 기능입니다. 업무 문맥 기반 질의응답으로 처리 방향을 빠르게 확인합니다. 예: 반품 분류 기준이 애매하면 AI에 초안을 요청합니다.",
            "API 설정": "API 설정 기능입니다. AI 사용을 위한 키와 모델 옵션을 등록합니다. 예: 신규 PC에서는 키 저장 후 테스트까지 완료합니다.",
            "API 테스트": "API 연결 테스트 기능입니다. 저장된 키의 인증과 응답 상태를 즉시 확인합니다. 예: 키 변경 직후 테스트를 눌러 실패 여부를 먼저 점검합니다.",
            "Excel": "Excel 변환 기능입니다. 선택한 문서를 편집 가능한 엑셀 형식으로 변환합니다. 예: PDF 양식을 Excel로 바꿔 필요한 항목만 정리합니다.",
            "Word": "Word 변환 기능입니다. 선택한 문서를 워드 형식으로 변환해 문구 수정에 사용합니다. 예: 고객 제출 문서를 Word로 변환해 바로 편집합니다.",
        }

        exact_tip = exact_rules.get(label)
        if exact_tip:
            return exact_tip

        partial_rules = [
            ("백업 생성", exact_rules["백업 생성"]),
            ("복원", exact_rules["복원"]),
            ("백업 목록", exact_rules["백업 목록"]),
            ("자동 백업 설정", exact_rules["자동 백업 설정"]),
            ("소량 반품 (1~2건)", exact_rules["소량 반품 (1~2건)"]),
            ("다량 반품 (Excel)", exact_rules["다량 반품 (Excel)"]),
            ("D/O 후속 연결", exact_rules["D/O 후속 연결"]),
            ("Picking List 업로드 (PDF)", exact_rules["Picking List 업로드 (PDF)"]),
            ("바코드 스캔 업로드 (CSV/Excel)", exact_rules["바코드 스캔 업로드 (CSV/Excel)"]),
            ("일괄 변환", exact_rules["일괄 변환"]),
            ("분석", exact_rules["분석"]),
            ("정합성 검사/복구", exact_rules["정합성 검사/복구"]),
            ("데이터 정합성 검사", exact_rules["데이터 정합성 검사"]),
            ("운영 DB 스키마 점검(1회)", exact_rules["운영 DB 스키마 점검(1회)"]),
            ("테스트 DB 초기화 (데이터 삭제)", exact_rules["테스트 DB 초기화 (데이터 삭제)"]),
            ("AI 채팅", exact_rules["AI 채팅"]),
            ("API 설정", exact_rules["API 설정"]),
            ("API 테스트", exact_rules["API 테스트"]),
        ]

        for key, tip in partial_rules:
            if key in label:
                return tip
        return ''

    def _fit_tooltip_length(self, text: str, label: str = '', item_type: str = 'command') -> str:
        """툴팁 문구를 예시 포함 + 약 120자(100~130자)로 보정한다."""
        if not text:
            return ''

        min_len = 100
        max_len = 130
        cleaned = " ".join(str(text).split())
        if not cleaned:
            return ''

        # 예시 문구 강제 포함
        if '예:' not in cleaned:
            example = self._build_tooltip_example(label, item_type)
            if example:
                cleaned = f"{cleaned} {example}"
        cleaned = self._normalize_tooltip_tone(cleaned)

        if len(cleaned) > max_len:
            return cleaned[: max_len - 3].rstrip() + "..."

        if len(cleaned) < min_len:
            filler = self._build_tooltip_filler(label, item_type)
            if filler:
                candidate = f"{cleaned} {filler}"
                if len(candidate) > max_len:
                    return candidate[: max_len - 3].rstrip() + "..."
                cleaned = candidate
        return self._normalize_tooltip_tone(cleaned)

    def _build_tooltip_example(self, label: str, item_type: str) -> str:
        """툴팁에 붙일 예시 문구를 생성한다."""
        label = (label or '').strip()
        if item_type == 'cascade':
            return f"예: '{label or '하위 메뉴'}'를 눌러 세부 작업을 선택합니다."

        if any(k in label for k in ('삭제', '초기화', '복원', '취소')):
            return "예: 실행 전 대상 행/기간을 먼저 확인한 뒤 진행하세요."
        if any(k in label.lower() for k in ('pdf', 'excel', '내보내기', '저장', '보고서', '리포트')):
            return "예: 조건 입력 후 파일 경로를 선택하면 결과 파일이 생성됩니다."
        if any(k in label for k in ('조회', '열기', '설정', '정보', '도움말')):
            return "예: 클릭하면 관련 화면이 열리고 옵션을 바로 바꿀 수 있습니다."
        if '새로고침' in label:
            return "예: 최신 DB 상태를 다시 읽어 목록과 통계를 즉시 갱신합니다."
        if '검사' in label or '검증' in label:
            return "예: 점검 결과의 경고/오류를 확인한 뒤 필요한 조치를 진행합니다."
        return f"예: 클릭하면 '{label or '선택한'}' 작업이 실행됩니다."

    def _build_tooltip_filler(self, label: str, item_type: str) -> str:
        """최소 길이 미달 시 자연스러운 보강 문구를 만든다."""
        if item_type == 'cascade':
            return "마우스를 올린 뒤 클릭하면 연결된 하위 기능 목록을 펼쳐 작업 흐름에 맞게 선택할 수 있습니다."
        if any(k in (label or '') for k in ('삭제', '초기화', '복원', '종료', '취소')):
            return "변경 즉시 데이터에 반영될 수 있으니 현재 상태를 확인하고 필요한 경우 백업 후 진행하는 것을 권장합니다."
        return "작업 전 대상 데이터와 조건을 확인하면 오입력이나 재작업을 줄이고 원하는 결과를 더 빠르게 얻을 수 있습니다."

    def _normalize_tooltip_tone(self, text: str) -> str:
        """툴팁 문장 끝 어미를 '-합니다.' 톤으로 통일한다."""
        if not text:
            return ''
        normalized = str(text)
        replacements = [
            ("하세요.", "합니다."),
            ("하세요", "합니다"),
            ("하십시오.", "합니다."),
            ("하십시오", "합니다"),
            ("해 주세요.", "합니다."),
            ("해 주세요", "합니다"),
            ("해주세요.", "합니다."),
            ("해주세요", "합니다"),
        ]
        for src, dst in replacements:
            normalized = normalized.replace(src, dst)
        return " ".join(normalized.split())

    def _show_active_menu_tooltip(self, x: int, y: int, text: str) -> None:
        """활성 메뉴 항목 툴팁을 화면에 표시한다."""
        tip_win = getattr(self, '_active_menu_tooltip_win', None)
        if tip_win is None or not tip_win.winfo_exists():
            tip_win = tk.Toplevel(self.root)
            tip_win.wm_overrideredirect(True)
            self._active_menu_tooltip_win = tip_win
            _tip_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
            label = tk.Label(
                tip_win,
                justify='left',
                background=ThemeColors.get('bg_card', _tip_dark),
                foreground=ThemeColors.get('text_primary', _tip_dark),
                relief='solid',
                borderwidth=1,
                font=self._tb_font_scale.body(),
                padx=Spacing.SM,
                pady=Spacing.SM,
                wraplength=420,
            )
            label.pack()
            tip_win._sqm_label = label

        try:
            tip_win._sqm_label.config(text=text)
            tip_win.wm_geometry(f"+{int(x)}+{int(y)}")
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
            self._hide_active_menu_tooltip()

    def _hide_active_menu_tooltip(self) -> None:
        """활성 메뉴 툴팁을 숨긴다."""
        tip_win = getattr(self, '_active_menu_tooltip_win', None)
        if tip_win is not None:
            try:
                if tip_win.winfo_exists():
                    tip_win.destroy()
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as e:
                logger.warning(f"[_hide_active_menu_tooltip] Suppressed: {e}")
        self._active_menu_tooltip_win = None

    def _refresh_all_data(self) -> None:
        try:
            for fn in ['_refresh_inventory', '_refresh_allocation', '_refresh_picked', '_refresh_sold', '_refresh_cargo_overview', '_refresh_dashboard']:
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