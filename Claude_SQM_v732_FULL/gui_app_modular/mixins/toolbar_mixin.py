# -*- coding: utf-8 -*-
from ..utils.custom_messagebox import CustomMessageBox
"""
SQM v7.3.2.1 — 커스텀 타이틀바 + 분리 메뉴
==========================================
커스텀 타이틀바: 왼쪽 메뉴 + 오른쪽 회사명·창 컨트롤 (1줄 통합)
입고/출고 메뉴 분리
"""
import sqlite3
import logging
from ..utils.ui_constants import ThemeColors, Spacing, FontScale, FontStyle, get_font_scale, DialogSize, center_dialog, apply_modal_window_options
from ..utils.constants import tk, tkfont, ttk

logger = logging.getLogger(__name__)

FONT_CANDIDATES = ['NanumSquare', 'NanumSquareRound', '나눔스퀘어', 'Malgun Gothic', '맑은 고딕']


def _pick_font(root) -> str:
    if tkfont is None:
        return '맑은 고딕'
    available = tkfont.families()
    for f in FONT_CANDIDATES:
        if f in available:
            return f
    return '맑은 고딕'


class ToolbarMixin:
    """v7.3.2: 커스텀 타이틀바 — 메뉴(왼) + 회사명·창컨트롤(오른) 1줄 통합"""

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
        if count <= 0:
            return ""
        icon = "🔴" if count >= 5 else "🟡"
        return f" {icon} [{count}]"

    def _load_toolbar_colors(self) -> None:
        """ThemeColors 단일 소스 — 헤더는 항상 다크 네이비"""
        _dark = True
        self._tb_bg = '#0b1120'       # 딥 네이비 블랙
        self._tb_fg = '#e2e8f0'       # 밝은 슬레이트
        self._tb_accent = '#10B981'   # 에메랄드
        self._tb_border = '#1e3a5f'   # 네이비 보더
        try:
            import ttkbootstrap as ttk_bs
            sc = ttk_bs.Style().colors
            self._tb_underline_color = str(sc.info) if getattr(sc, 'info', None) else ThemeColors.get('info', _dark)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
            self._tb_underline_color = ThemeColors.get('info', _dark)

    def _setup_toolbar(self) -> None:
        """v7.3.2: 커스텀 타이틀바 — 메뉴(왼) + 회사명·창컨트롤(오른) 1줄 통합"""
        self._toolbar_font = _pick_font(self.root)
        self._tb_font_scale = get_font_scale() or FontScale()
        logger.info(f"[v7.3.2] 폰트: {self._toolbar_font}")

        self._load_toolbar_colors()

        # 컨테이너 서픽스 변수 초기화
        self._container_suffix_var = tk.BooleanVar(value=True)

        # ── 커스텀 타이틀바: OS 타이틀바 제거 ──
        self.root.overrideredirect(True)

        # 윈도우 상태 추적
        self._win_is_maximized = False
        self._win_normal_geo = None  # 최초 geometry 이후 설정

        # 신호등 호환성 유지 (숨김 상태)
        self._signal_lights = {}

        # ── 타이틀바 프레임 ──
        self._titlebar = tk.Frame(self.root, bg=self._tb_bg, height=38)
        self._titlebar.pack(fill='x', side='top')
        self._titlebar.pack_propagate(False)

        # 왼쪽: 메뉴 영역
        self._menu_frame_left = tk.Frame(self._titlebar, bg=self._tb_bg)
        self._menu_frame_left.pack(side='left', fill='y', padx=(6, 0))

        # 오른쪽: 창 컨트롤 (닫기, 최대화, 최소화)
        self._build_window_controls()

        # 오른쪽: 타이틀 텍스트 (컨트롤 왼쪽)
        _title_text = "(주)지와이로지스 — SQM 재고관리 시스템"
        try:
            from version import __version__
            _title_text += f" v{__version__}"
        except ImportError:
            pass
        self._title_label = tk.Label(
            self._titlebar, text=_title_text,
            bg=self._tb_bg, fg='#94a3b8',
            font=(self._toolbar_font, 10),
        )
        self._title_label.pack(side='right', padx=(20, 12))

        # ── 메뉴 구성 ──
        self._all_dropdown_menus = []
        self._all_menu_btns = []
        self._menubar = None  # 네이티브 메뉴바 사용 안 함

        self._build_menu_file()
        self._build_menu_inbound()
        self._build_menu_outbound()
        self._build_menu_report()
        self._build_menu_tools()
        self._build_menu_help()

        # ── 드래그 이동 + 리사이즈 ──
        self._setup_titlebar_drag()
        self._setup_resize_handles()

        # Windows 태스크바 표시 보장
        self.root.after(50, self._ensure_taskbar_visible)

        # Alt+F4 지원
        self.root.bind('<Alt-F4>', lambda e: self._on_titlebar_close())

        # 호환성
        self._toolbar_container = tk.Frame(self.root)
        self._tab_buttons = {}
        self._row1 = self._titlebar
        self._row2 = tk.Frame(self.root)
        self._menu_frame = self._titlebar
        self._sec_tabs = tk.Frame(self.root)
        self._right_actions = tk.Frame(self.root)
        self._row2_visible = False

        # 탭 인덱스 맵 (Notebook 기반)
        self._tab_index_map = {
            'inventory': 0, 'allocation': 1, 'picked': 2, 'sold': 3,
            'scan': 4, 'cargo_overview': 5, 'dashboard': 6, 'log': 7
        }
        self._active_tab_key = 'inventory'

    # ═══════════════════════════════════════════════════════
    # 커스텀 타이틀바: 메뉴버튼 + 창 컨트롤 + 드래그/리사이즈
    # ═══════════════════════════════════════════════════════

    def _add_titlebar_menu(self, label: str) -> 'tk.Menu':
        """타이틀바에 메뉴 라벨 + 드롭다운 Menu 추가 후 Menu 반환.
        overrideredirect 환경에서 tk.Menubutton이 드롭다운을 열지 못하므로
        tk.Label + tk_popup 수동 호출 방식 사용."""
        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        menu = tk.Menu(self.root, tearoff=0, font=(self._toolbar_font, 10),
                       bg=ThemeColors.get('bg_card', is_dark),
                       fg=ThemeColors.get('text_primary', is_dark),
                       activebackground=ThemeColors.get('bg_hover', is_dark),
                       activeforeground=ThemeColors.get('text_primary', is_dark),
                       relief='flat', bd=1)

        btn = tk.Label(
            self._menu_frame_left,
            text=f" {label} ",
            font=(self._toolbar_font, 10, 'bold'),
            bg=self._tb_bg, fg=self._tb_fg,
            cursor='hand2',
            padx=6, pady=8,
        )
        btn.pack(side='left')

        # 클릭 시 드롭다운 표시
        def _show_menu(event=None):
            x = btn.winfo_rootx()
            y = btn.winfo_rooty() + btn.winfo_height()
            try:
                menu.tk_popup(x, y)
            finally:
                try:
                    menu.grab_release()
                except tk.TclError:
                    pass

        btn.bind('<Button-1>', _show_menu)

        # 호버 효과
        def _on_enter(e):
            try:
                btn.config(bg=self._tb_border)
            except tk.TclError:
                pass

        def _on_leave(e):
            try:
                btn.config(bg=self._tb_bg)
            except tk.TclError:
                pass

        btn.bind('<Enter>', _on_enter)
        btn.bind('<Leave>', _on_leave)

        self._all_dropdown_menus.append(menu)
        self._all_menu_btns.append(btn)
        return menu

    def _build_window_controls(self) -> None:
        """최소화, 최대화/복원, 닫기 버튼"""
        ctrl = tk.Frame(self._titlebar, bg=self._tb_bg)
        ctrl.pack(side='right', fill='y')

        _btn_font = (self._toolbar_font, 13)
        _w = 5

        # 닫기 ✕
        self._close_btn = tk.Button(
            ctrl, text='✕', command=self._on_titlebar_close,
            font=_btn_font, bg=self._tb_bg, fg=self._tb_fg,
            activebackground='#ef4444', activeforeground='#ffffff',
            bd=0, relief='flat', width=_w, cursor='hand2')
        self._close_btn.pack(side='right', fill='y')
        self._close_btn.bind('<Enter>', lambda e: self._close_btn.config(bg='#ef4444', fg='#ffffff'))
        self._close_btn.bind('<Leave>', lambda e: self._close_btn.config(bg=self._tb_bg, fg=self._tb_fg))

        # 최대화/복원 ☐
        self._max_btn = tk.Button(
            ctrl, text='☐', command=self._on_titlebar_maximize,
            font=_btn_font, bg=self._tb_bg, fg=self._tb_fg,
            activebackground='#374151', activeforeground='#ffffff',
            bd=0, relief='flat', width=_w, cursor='hand2')
        self._max_btn.pack(side='right', fill='y')
        self._max_btn.bind('<Enter>', lambda e: self._max_btn.config(bg='#374151'))
        self._max_btn.bind('<Leave>', lambda e: self._max_btn.config(bg=self._tb_bg))

        # 최소화 ─
        self._min_btn = tk.Button(
            ctrl, text='─', command=self._on_titlebar_minimize,
            font=_btn_font, bg=self._tb_bg, fg=self._tb_fg,
            activebackground='#374151', activeforeground='#ffffff',
            bd=0, relief='flat', width=_w, cursor='hand2')
        self._min_btn.pack(side='right', fill='y')
        self._min_btn.bind('<Enter>', lambda e: self._min_btn.config(bg='#374151'))
        self._min_btn.bind('<Leave>', lambda e: self._min_btn.config(bg=self._tb_bg))

    def _on_titlebar_close(self) -> None:
        """닫기 — _on_closing 우선 호출"""
        if hasattr(self, '_on_closing') and callable(self._on_closing):
            self._on_closing()
        else:
            self.root.destroy()

    def _on_titlebar_minimize(self) -> None:
        """최소화 (Windows ctypes 사용)"""
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
        except Exception as _e:
            logger.debug(f"minimize fallback: {_e}")
            try:
                self.root.overrideredirect(False)
                self.root.iconify()
                self.root.bind('<Map>', self._on_deiconify)
            except Exception:
                pass

    def _on_deiconify(self, event=None) -> None:
        """최소화 복원 시 overrideredirect 재설정"""
        try:
            self.root.overrideredirect(True)
            self.root.unbind('<Map>')
            self.root.after(50, self._ensure_taskbar_visible)
        except Exception as _e:
            logger.debug(f"deiconify: {_e}")

    def _on_titlebar_maximize(self) -> None:
        """최대화 / 복원 토글"""
        if self._win_is_maximized:
            # 복원
            if self._win_normal_geo:
                self.root.geometry(self._win_normal_geo)
            self._win_is_maximized = False
            self._max_btn.config(text='☐')
        else:
            # 현재 geometry 저장
            self._win_normal_geo = self.root.geometry()
            # 작업 영역 크기 (태스크바 제외)
            try:
                import ctypes
                from ctypes import wintypes
                rect = wintypes.RECT()
                ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                self.root.geometry(f"{w}x{h}+{rect.left}+{rect.top}")
            except Exception:
                sw = self.root.winfo_screenwidth()
                sh = self.root.winfo_screenheight() - 48
                self.root.geometry(f"{sw}x{sh}+0+0")
            self._win_is_maximized = True
            self._max_btn.config(text='❐')

    def _setup_titlebar_drag(self) -> None:
        """타이틀바 드래그로 창 이동 + 더블클릭 최대화"""
        self._drag_data = {'x': 0, 'y': 0, 'dragging': False}

        def _start_drag(event):
            self._drag_data['x'] = event.x
            self._drag_data['y'] = event.y
            self._drag_data['dragging'] = True

        def _do_drag(event):
            if not self._drag_data.get('dragging'):
                return
            if self._win_is_maximized:
                # 최대화 상태에서 드래그 시 복원
                self._on_titlebar_maximize()
                return
            x = self.root.winfo_x() + event.x - self._drag_data['x']
            y = self.root.winfo_y() + event.y - self._drag_data['y']
            self.root.geometry(f"+{x}+{y}")

        def _stop_drag(event):
            self._drag_data['dragging'] = False

        def _double_click(event):
            self._on_titlebar_maximize()

        # 타이틀바, 타이틀 레이블, 메뉴 프레임에 드래그 바인딩
        for widget in [self._titlebar, self._title_label, self._menu_frame_left]:
            widget.bind('<Button-1>', _start_drag, add='+')
            widget.bind('<B1-Motion>', _do_drag, add='+')
            widget.bind('<ButtonRelease-1>', _stop_drag, add='+')
            widget.bind('<Double-Button-1>', _double_click, add='+')

    def _setup_resize_handles(self) -> None:
        """창 가장자리 리사이즈 핸들 (하단, 우측, 우하단)"""
        EDGE = 5

        # 우하단 코너 그립
        self._resize_grip = tk.Frame(self.root, bg=self._tb_border,
                                     width=EDGE * 3, height=EDGE * 3, cursor='size_nw_se')
        self._resize_grip.place(relx=1.0, rely=1.0, anchor='se')

        # 우측 엣지
        self._resize_right = tk.Frame(self.root, bg='', width=EDGE, cursor='sb_h_double_arrow')
        self._resize_right.place(relx=1.0, rely=0, relheight=1.0, width=EDGE, anchor='ne')

        # 하단 엣지
        self._resize_bottom = tk.Frame(self.root, bg='', height=EDGE, cursor='sb_v_double_arrow')
        self._resize_bottom.place(relx=0, rely=1.0, relwidth=1.0, height=EDGE, anchor='sw')

        # 리사이즈 데이터
        self._resize_data = {'edge': None, 'x': 0, 'y': 0, 'geo': ''}

        def _start_resize(edge):
            def handler(event):
                import re as _re
                self._resize_data['edge'] = edge
                self._resize_data['x'] = event.x_root
                self._resize_data['y'] = event.y_root
                self._resize_data['geo'] = self.root.geometry()
            return handler

        def _do_resize(event):
            edge = self._resize_data.get('edge')
            if not edge:
                return
            import re as _re
            dx = event.x_root - self._resize_data['x']
            dy = event.y_root - self._resize_data['y']
            match = _re.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', self._resize_data['geo'])
            if not match:
                return
            w, h, x, y = int(match[1]), int(match[2]), int(match[3]), int(match[4])
            min_w, min_h = 900, 600

            if 'e' in edge:
                w = max(min_w, w + dx)
            if 's' in edge:
                h = max(min_h, h + dy)

            self.root.geometry(f"{w}x{h}+{x}+{y}")

        def _stop_resize(event):
            self._resize_data['edge'] = None

        # 각 엣지에 이벤트 바인딩
        for widget, edge in [
            (self._resize_grip, 'se'),
            (self._resize_right, 'e'),
            (self._resize_bottom, 's'),
        ]:
            widget.bind('<Button-1>', _start_resize(edge))
            widget.bind('<B1-Motion>', _do_resize)
            widget.bind('<ButtonRelease-1>', _stop_resize)

    def _ensure_taskbar_visible(self) -> None:
        """Windows 태스크바에 아이콘 표시 보장"""
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080

            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

            # 태스크바 갱신
            self.root.withdraw()
            self.root.after(10, self.root.deiconify)
        except Exception as _e:
            logger.debug(f"태스크바 표시: {_e}")

    # ═══════════════════════════════════════════════════════
    # 메뉴 생성 헬퍼
    # ═══════════════════════════════════════════════════════

    def _create_menu(self, parent=None) -> 'tk.Menu':
        """드롭다운 팝업 메뉴 생성"""
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
        try:
            m.config(bg=menu_bg, fg=menu_fg, activebackground=menu_abg, activeforeground=menu_afg,
                     disabledforeground=menu_dis)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")
        return m

    def _add_menu_item(self, menu, label: str, command, icon_pad: bool = True) -> None:
        padded = f"  {label}  " if not label.startswith('  ') else f"{label}  "
        menu.add_command(label=padded, command=command)

    def _add_menu_items(self, menu: 'tk.Menu', items: list) -> None:
        for item in items:
            if item is None:
                menu.add_separator()
            else:
                label, cmd = item[0], item[1]
                menu.add_command(label=f"  {label}" if not str(label).startswith('  ') else label, command=cmd)

    # ═══════════════════════════════════════════════════════
    # Menubutton 기반 6개 메뉴 구성 (파일, 입고, 출고, 보고서, 도구, 도움말)
    # ═══════════════════════════════════════════════════════

    def _build_menu_file(self) -> None:
        """파일 메뉴 (내보내기, 백업, AI, PDF, 종료)"""
        m = self._add_titlebar_menu("파일")

        # 내보내기
        try:
            from ..menu_registry import FILE_MENU_EXPORT_ITEMS, FILE_MENU_BACKUP_ITEMS
            exp = tk.Menu(m, tearoff=0, font=(self._toolbar_font, 10))
            for label, option in FILE_MENU_EXPORT_ITEMS:
                exp.add_command(label=f"  {label}", command=lambda op=option: self._on_export_click(option=op))
            m.add_cascade(label="  💾 내보내기", menu=exp)
            m.add_separator()
            bak = tk.Menu(m, tearoff=0, font=(self._toolbar_font, 10))
            for label, method_name in FILE_MENU_BACKUP_ITEMS:
                bak.add_command(label=f"  {label}", command=lambda mn=method_name: self._safe_call(mn))
            bak.add_command(label="  ⏰ 자동 백업 설정", command=lambda: self._safe_call('_show_auto_backup_settings'))
            m.add_cascade(label="  🔐 백업", menu=bak)
        except Exception as _e:
            logger.debug(f"파일 메뉴 registry: {_e}")

        m.add_separator()
        # BL 선사 도구
        try:
            from ..menu_registry import FILE_MENU_AI_TOOLS_ITEMS as _ai_items
            _bl_sub = tk.Menu(m, tearoff=0, font=(self._toolbar_font, 10))
            for _entry in _ai_items:
                if _entry is None:
                    _bl_sub.add_separator()
                    continue
                _lbl, _mth = _entry[0], _entry[1]
                _bl_sub.add_command(label=f"  {_lbl}", command=lambda mn=_mth: self._safe_call(mn))
            m.add_cascade(label="  🚢 BL 선사 도구", menu=_bl_sub)
            m.add_separator()
        except Exception:
            pass

        # Gemini API
        try:
            from ..utils.constants import HAS_GEMINI
            if HAS_GEMINI:
                if not hasattr(self, '_gemini_var'):
                    self._gemini_var = tk.BooleanVar(value=getattr(self, 'use_gemini', False))
                api_sub = tk.Menu(m, tearoff=0, font=(self._toolbar_font, 10))
                api_sub.add_checkbutton(label="  API 사용", variable=self._gemini_var,
                                        command=lambda: self._safe_call('_toggle_gemini'))
                api_sub.add_separator()
                api_sub.add_command(label="  💬 AI 채팅", command=lambda: self._safe_call('_open_ai_chat'))
                api_sub.add_command(label="  ⚙️ API 설정", command=lambda: self._safe_call('_show_api_settings'))
                api_sub.add_command(label="  🔬 API 테스트", command=lambda: self._safe_call('_test_gemini_api_connection'))
                m.add_cascade(label="  🤖 Gemini (API)", menu=api_sub)
            else:
                api_sub = tk.Menu(m, tearoff=0, font=(self._toolbar_font, 10))
                api_sub.add_command(label="  ⚙️ API 설정", command=lambda: self._safe_call('_show_api_settings'))
                api_sub.add_command(label="  🔬 API 테스트", command=lambda: self._safe_call('_test_gemini_api_connection'))
                m.add_cascade(label="  🤖 Gemini (API)", menu=api_sub)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Gemini 메뉴: {_e}")

        # PDF 변환
        pdf_sub = tk.Menu(m, tearoff=0, font=(self._toolbar_font, 10))
        pdf_sub.add_command(label="  → Excel", command=lambda: self._safe_call('_convert_pdf_to_excel'))
        pdf_sub.add_command(label="  → Word", command=lambda: self._safe_call('_convert_pdf_to_word'))
        pdf_sub.add_separator()
        pdf_sub.add_command(label="  📁 일괄 변환", command=lambda: self._safe_call('_batch_convert_pdf_excel'))
        pdf_sub.add_command(label="  🔍 분석", command=lambda: self._safe_call('_analyze_pdf'))
        m.add_cascade(label="  📄 PDF/이미지 변환", menu=pdf_sub)

        m.add_separator()
        m.add_command(label="  ❌ 종료", command=self.root.quit)

    def _build_menu_inbound(self) -> None:
        """📥 입고 메뉴 (독립)"""
        m = self._add_titlebar_menu("📥 입고")
        try:
            from ..menu_registry import FILE_MENU_INBOUND_ITEMS, FILE_MENU_INBOUND_RETURN_SUB_ITEMS
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
                    return_sub = tk.Menu(m, tearoff=0, font=(self._toolbar_font, 10))
                    _show_return = getattr(self, "_show_return_dialog", None)
                    if callable(_show_return):
                        for sub_label, mode in FILE_MENU_INBOUND_RETURN_SUB_ITEMS:
                            return_sub.add_command(label=f"  {sub_label}", command=lambda md=mode: _show_return(md))
                    pending = self._get_return_doc_review_pending_count(30)
                    badge = self._format_return_review_badge(pending)
                    m.add_cascade(label=f"  {label}{badge}", menu=return_sub)
                else:
                    m.add_command(label=f"  {label}", command=lambda mn=method_name: self._safe_call(mn))
        except Exception as _e:
            logger.warning(f"입고 메뉴 registry: {_e}")
            self._add_menu_items(m, [
                ('📄 PDF 스캔 입고', lambda: self._safe_call('_on_pdf_inbound')),
                ('⚡ 빠른 PDF 스캔 (폴더)', lambda: self._safe_call('_on_pdf_inbound_quick_folder')),
                ('📊 엑셀 파일 수동 입고', lambda: self._safe_call('_bulk_import_inventory_simple')),
                ('📂 반품 입고 (Excel)', lambda: self._safe_call('_on_return_inbound_upload')),
                ('📦 제품명 테이블 관리', lambda: self._safe_call('_show_product_master')),
            ])

    def _build_menu_outbound(self) -> None:
        """📤 출고 메뉴 (독립)"""
        m = self._add_titlebar_menu("📤 출고")
        try:
            from ..menu_registry import FILE_MENU_OUTBOUND_ITEMS
            for entry in FILE_MENU_OUTBOUND_ITEMS:
                if entry is None:
                    m.add_separator()
                    continue
                label, method_name = entry[0], entry[1]
                optional = entry[2] if len(entry) > 2 else False
                if optional and not callable(getattr(self, method_name, None)):
                    continue
                m.add_command(label=f"  {label}", command=lambda mn=method_name: self._safe_call(mn))
        except Exception as _e:
            logger.warning(f"출고 메뉴 registry: {_e}")
            self._add_menu_items(m, [
                ('📋 Allocation 입력', lambda: self._safe_call('_on_allocation_input_unified')),
                ('📋 Picking List 업로드', lambda: self._safe_call('_on_picking_list_upload')),
                ('📤 빠른 출고 (붙여넣기)', lambda: self._safe_call('_on_quick_outbound_paste')),
                ('🚀 S1 원스톱 출고', lambda: self._safe_call('_on_s1_onestop_outbound')),
            ])

    def _build_menu_report(self) -> None:
        """보고서 메뉴"""
        m = self._add_titlebar_menu("보고서")

        # 재고 리포트
        m.add_command(label="━━ 📊 재고 ━━", state='disabled')
        self._add_menu_items(m, [
            ('📊 LOT 리스트 Excel', lambda: self._on_export_click(option=3)),
            ('🎒 톤백리스트 Excel', lambda: self._on_export_click(option=4)),
            None,
            ('📋 출고 현황 조회', lambda: self._safe_call('_show_outbound_history')),
            ('📊 재고 추이 차트', lambda: self._safe_call('_show_snapshot_chart')),
        ])
        m.add_separator()

        # 고객 보고서
        m.add_command(label="━━ 📝 고객 보고서 ━━", state='disabled')
        self._add_menu_items(m, [
            ('📄 거래명세서 생성', lambda: self._safe_call('_generate_outbound_invoice')),
            None,
            ('📝 고객 보고서 생성', lambda: self._safe_call('_generate_customer_report')),
            ('📂 보고서 양식 관리', lambda: self._safe_call('_manage_report_templates')),
            None,
            ('📋 보고서 이력 조회', lambda: self._safe_call('_show_report_history')),
        ])

    def _build_menu_tools(self) -> None:
        """도구 메뉴"""
        m = self._add_titlebar_menu("도구")

        # 화면
        m.add_command(label="  🔄 새로고침 (F5)", command=self._refresh_all_data)
        m.add_separator()

        # v7.3.2: 테마 — 라이트/다크 단순 토글
        m.add_command(label="  🎨 테마 전환 (라이트/다크)", command=self._toggle_dark_mode_theme)

        # 글꼴 크기
        fsize = tk.Menu(m, tearoff=0, font=(self._toolbar_font, 10))
        fsize.add_command(label="  작게 (11pt)", command=lambda: self._change_font_size(11))
        fsize.add_command(label="  보통 (13pt)", command=lambda: self._change_font_size(13))
        fsize.add_command(label="  크게 (16pt)", command=lambda: self._change_font_size(16))
        m.add_cascade(label="  🔤 글꼴 크기", menu=fsize)
        m.add_separator()

        # 개발자 모드
        if not hasattr(self, '_dev_mode_var'):
            _dev_on = self._is_developer_mode_enabled() if hasattr(self, '_is_developer_mode_enabled') else False
            self._dev_mode_var = tk.BooleanVar(value=_dev_on)
        m.add_checkbutton(label="  🧪 개발자 모드", variable=self._dev_mode_var,
                          command=self._on_toggle_developer_mode)

        # 자동 갱신
        if not hasattr(self, '_auto_refresh_var'):
            self._auto_refresh_var = tk.BooleanVar(value=False)
        m.add_checkbutton(label="  🔄 대시보드 자동 갱신 (30초)", variable=self._auto_refresh_var,
                          command=self._on_auto_refresh_toggle)
        m.add_separator()

        # 정합성
        m.add_command(label="  🔍 정합성 검사/복구", command=self._on_integrity_check)
        m.add_command(label="  🧪 운영 DB 스키마 점검(1회)", command=self._on_operational_schema_check_once)
        m.add_separator()
        m.add_command(label="  🩺 데이터 정합성 검사", command=lambda: self._safe_call('_run_integrity_check'))
        m.add_separator()
        if hasattr(self, '_is_developer_mode_enabled') and self._is_developer_mode_enabled():
            m.add_command(label="  🗑️ 테스트 DB 초기화 (데이터 삭제)", command=lambda: self._safe_call('_show_test_db_reset_popup'))

    def _build_menu_help(self) -> None:
        """도움말 메뉴"""
        m = self._add_titlebar_menu("도움말")

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

    # ═══════════════════════════════════════════════════════
    # 호환성: 기존 메서드 유지 (탭 전환, 검색 등)
    # ═══════════════════════════════════════════════════════

    # _build_all_menus / _build_tab_buttons 제거됨 (Notebook 탭 직접 사용)
    # _build_refresh_button / _build_quick_theme_buttons 제거됨 (메뉴 안으로 이동)

    def _build_all_menus(self) -> None:
        """호환성 stub — 이미 _setup_toolbar에서 메뉴 구성됨"""
        pass

    def _build_tab_buttons(self) -> None:
        """호환성 stub — Notebook 탭 헤더로 대체"""
        pass

    def _build_refresh_button(self, parent) -> None:
        """호환성 stub"""
        pass

    def _build_quick_theme_buttons(self, parent) -> None:
        """호환성 stub"""
        pass

    def _switch_tab(self, tab_key: str):
        idx = self._tab_index_map.get(tab_key)
        if idx is not None and hasattr(self, 'notebook'):
            try:
                self.notebook.select(idx)
                self._active_tab_key = tab_key
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"_switch_tab: {_e}")

    def _highlight_active_tab(self) -> None:
        """호환성 stub — Notebook 자체 탭 사용"""
        pass

    def _tab_hover_enter(self, btn, key: str) -> None:
        pass

    def _tab_hover_leave(self, btn, key: str) -> None:
        pass

    def _check_toolbar_overflow(self, event=None) -> None:
        pass

    # ═══════════════════════════════════════════════════════
    # 기존 메뉴 빌더 (호환용 — _build_inbound_menu 등)
    # ═══════════════════════════════════════════════════════

    def _build_inbound_menu(self) -> 'tk.Menu':
        """호환용 입고 메뉴 (기존 코드에서 호출될 수 있음)"""
        m = self._create_menu()
        try:
            from ..menu_registry import FILE_MENU_INBOUND_ITEMS, FILE_MENU_INBOUND_RETURN_SUB_ITEMS
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
        except Exception as _e:
            logger.debug(f"입고 메뉴 빌드: {_e}")
        return m

    def _build_outbound_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        try:
            from ..menu_registry import FILE_MENU_OUTBOUND_ITEMS
            for entry in FILE_MENU_OUTBOUND_ITEMS:
                if entry is None:
                    m.add_separator()
                    continue
                label, method_name = entry[0], entry[1]
                optional = entry[2] if len(entry) > 2 else False
                if optional and not callable(getattr(self, method_name, None)):
                    continue
                m.add_command(label=f"  {label}", command=lambda mn=method_name: self._safe_call(mn))
        except Exception as _e:
            logger.debug(f"출고 메뉴 빌드: {_e}")
        return m

    def _build_report_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        self._add_menu_items(m, [
            ('📊 LOT 리스트 Excel', lambda: self._on_export_click(option=3)),
            ('🎒 톤백리스트 Excel', lambda: self._on_export_click(option=4)),
            None,
            ('📋 출고 현황 조회', lambda: self._safe_call('_show_outbound_history')),
            ('📊 재고 추이 차트', lambda: self._safe_call('_show_snapshot_chart')),
        ])
        return m

    def _build_customer_report_menu(self) -> 'tk.Menu':
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
        return self._create_menu()

    def _build_settings_menu(self) -> 'tk.Menu':
        return self._create_menu()

    def _build_help_menu(self) -> 'tk.Menu':
        return self._create_menu()

    # ═══════════════════════════════════════════════════════
    # 테마 전환 지원
    # ═══════════════════════════════════════════════════════

    def _refresh_toolbar_colors(self) -> None:
        """v7.3.2: 테마 전환 시 툴바 색상 동기화 (헤더 바 제거됨)"""
        try:
            self._load_toolbar_colors()
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"toolbar color refresh: {_e}")

    def _restore_toolbar_chain_bg(self):
        """호환성: 테마 전환 시 배경 복원"""
        for name in ('_toolbar_container', '_row1', '_row2'):
            try:
                w = getattr(self, name, None)
                if w and w.winfo_exists():
                    w.config(bg=self._tb_bg)
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                logger.debug(f"Suppressed: {_e}")

    def _refresh_toolbar_theme(self) -> None:
        """v7.3.2: 테마 전환 시 커스텀 타이틀바·메뉴 색상 동기화"""
        try:
            self._load_toolbar_colors()
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        try:
            self._restore_toolbar_chain_bg()
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        # 타이틀바 프레임 색상 갱신
        try:
            for attr in ('_titlebar', '_menu_frame_left'):
                w = getattr(self, attr, None)
                if w and w.winfo_exists():
                    w.config(bg=self._tb_bg)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        # Menubutton 색상 갱신
        try:
            for btn in getattr(self, '_all_menu_btns', []):
                if btn and btn.winfo_exists():
                    btn.config(bg=self._tb_bg, fg=self._tb_fg,
                               activebackground=self._tb_border, activeforeground=self._tb_fg)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        # 타이틀 레이블
        try:
            if hasattr(self, '_title_label') and self._title_label.winfo_exists():
                self._title_label.config(bg=self._tb_bg)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        # 창 컨트롤 버튼
        try:
            for attr in ('_close_btn', '_max_btn', '_min_btn'):
                btn = getattr(self, attr, None)
                if btn and btn.winfo_exists():
                    btn.config(bg=self._tb_bg, fg=self._tb_fg)
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        # 드롭다운 메뉴 색상 동기화
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
                        m.config(bg=menu_bg, fg=menu_fg, activebackground=menu_abg,
                                 activeforeground=menu_afg, disabledforeground=menu_dis)
                except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
                    logger.debug(f"Suppressed: {_e}")
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError) as _e:
            logger.debug(f"Suppressed: {_e}")

        try:
            self.root.after_idle(lambda: self.root.update_idletasks())
        except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
            pass

    def _show_menu(self, menu, btn) -> None:
        """호환성: tk_popup 래퍼"""
        try:
            x = btn.winfo_rootx()
            y = btn.winfo_rooty() + btn.winfo_height()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except (ValueError, TypeError, KeyError, AttributeError, tk.TclError):
                pass

    # ═══════════════════════════════════════════════════════
    # 🔍 검색 팝업
    # ═══════════════════════════════════════════════════════

    def _show_search_popup(self) -> None:
        """v3.8.9: 검색 팝업 — DB 데이터 로드 + LOT 리스트 필터링"""
        _ = self._toolbar_font
        popup = tk.Toplevel(self.root)
        popup.title("🔍 검색")
        popup.geometry(DialogSize.get_geometry(self.root, 'medium'))
        apply_modal_window_options(popup)
        popup.transient(self.root)
        popup.grab_set()
        center_dialog(popup, self.root)

        main = tk.Frame(popup, padx=Spacing.LG, pady=Spacing.MD)
        main.pack(fill='both', expand=True)

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

            ALLOWED_FIELDS = {'sap_no', 'bl_no', 'lot_no', 'status', 'product', 'warehouse'}
            try:
                if field not in ALLOWED_FIELDS:
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
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                logger.debug(f"검색 팝업 [{field}] 로드 실패: {_e}")
                cb['values'] = ['전체']

        tk.Label(main, text='Arrival Date', font=_lab_font, anchor='w'
                 ).grid(row=3, column=0, sticky='w', pady=Spacing.SM)
        df = tk.Frame(main)
        df.grid(row=3, column=1, sticky='ew', padx=(Spacing.SM, 0), pady=Spacing.SM)
        tk.Entry(df, textvariable=svars['date_from'], width=12, font=_body_font).pack(side='left')
        tk.Label(df, text=' ~ ', font=_body_font).pack(side='left')
        tk.Entry(df, textvariable=svars['date_to'], width=12, font=_body_font).pack(side='left')
        _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        _small_font = self._tb_font_scale.small()
        tk.Label(df, text='  (YYYY-MM-DD)', font=_small_font, fg=ThemeColors.get('text_muted', _is_dark)
                 ).pack(side='left', padx=Spacing.XS)

        tk.Label(main, text='상태', font=_lab_font, anchor='w'
                 ).grid(row=4, column=0, sticky='w', pady=Spacing.SM)
        ttk.Combobox(main, textvariable=svars['status'],
                     values=['전체', 'AVAILABLE', 'PICKED', 'SHIPPED', 'DEPLETED'],
                     state='readonly', width=28, font=_body_font
                     ).grid(row=4, column=1, sticky='ew', padx=(Spacing.SM, 0), pady=Spacing.SM)

        main.columnconfigure(1, weight=1)

        def do_search():
            self._inv_search_combos = {}
            for field in ('sap_no', 'bl_no', 'lot_no'):
                self._inv_search_combos[field] = (svars[field], None)
            if hasattr(self, '_date_from_var'):
                self._date_from_var.set(svars['date_from'].get())
            if hasattr(self, '_date_to_var'):
                self._date_to_var.set(svars['date_to'].get())
            if hasattr(self, 'status_var'):
                self.status_var.set(svars['status'].get())
            try:
                self.notebook.select(self.tab_inventory)
            except (AttributeError, RuntimeError) as _e:
                logger.debug(f"search: {_e}")
            if hasattr(self, '_refresh_inventory'):
                self._refresh_inventory()
            popup.destroy()

        def do_reset():
            for key in svars:
                if key in ('date_from', 'date_to'):
                    svars[key].set('')
                else:
                    svars[key].set('전체')

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
        show = self._container_suffix_var.get()
        self._log(f"📦 컨테이너 구분: {'ON' if show else 'OFF'}")
        self._safe_refresh()

    def _format_container_no(self, container_no: str) -> str:
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
        enabled = self._auto_refresh_var.get()
        self._log(f"🔄 자동 갱신: {'ON (30초)' if enabled else 'OFF'}")
        if enabled:
            self._schedule_auto_refresh()

    def _schedule_auto_refresh(self) -> None:
        if not getattr(self, '_auto_refresh_var', None):
            return
        if not self._auto_refresh_var.get():
            return
        try:
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
        if hasattr(self, 'root'):
            self.root.after(30000, self._schedule_auto_refresh)

    def _check_db_modified(self) -> bool:
        import os
        try:
            db_path = getattr(self, 'db_path', None)
            if not db_path or not os.path.exists(db_path):
                return False
            mtime = os.path.getmtime(db_path)
            last = getattr(self, '_last_db_mtime', 0)
            if mtime > last:
                self._last_db_mtime = mtime
                return last > 0
            return False
        except (OSError, IOError, PermissionError):
            return False

    def _on_fix_lot_status_integrity(self) -> None:
        from ..utils.custom_messagebox import CustomMessageBox
        ans = CustomMessageBox.ask(
            self,
            title="LOT 상태 정합성 복구",
            message=(
                "LOT 상태를 톤백 기준으로 일괄 보정합니다.\n\n"
                "• LOT=SOLD 이지만 AVAILABLE 톤백 잔존 → AVAILABLE\n"
                "• LOT=AVAILABLE 이지만 전체 SOLD → SOLD\n\n"
                "계속하시겠습니까?"
            )
        )
        if not ans:
            return
        try:
            result = self.engine.fix_lot_status_integrity()
            if result.get('success'):
                _cnt = result.get('fixed', 0)
                _details = '\n'.join(result.get('details', [])[:20])
                msg = f"복구 완료: {_cnt}건\n\n{_details}" if _cnt else "정합성 이상 없음"
                CustomMessageBox.info(self, title="복구 완료", message=msg)
            else:
                CustomMessageBox.error(
                    self, title="오류",
                    message='\n'.join(result.get('errors', ['알 수 없는 오류']))
                )
        except Exception as e:
            CustomMessageBox.error(self, title="오류", message=str(e))

    def _on_integrity_check(self) -> None:
        from ..utils.custom_messagebox import CustomMessageBox
        try:
            from core.validators import InventoryValidator
            validator = InventoryValidator(db=self.engine.db)
            result = validator.check_data_integrity()
            issues = []
            if result.errors:
                for e in result.errors:
                    issues.append(f"🔴 {e}")
            if result.warnings:
                for w in result.warnings:
                    issues.append(f"🟡 {w}")

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
        try:
            db = getattr(getattr(self, "engine", None), "db", None)
            if db is None:
                CustomMessageBox.showwarning(self.root, "스키마 점검", "DB 연결이 없어 점검할 수 없습니다.")
                return

            def _table_exists(name: str) -> bool:
                row = db.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
                return bool(row)

            def _index_exists(name: str) -> bool:
                row = db.fetchone("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,))
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
            lines = [f"[운영 DB 스키마 점검 결과] {ok_count}/{len(checks)} 통과", ""]
            for name, ok in checks:
                lines.append(f"{'✅' if ok else '❌'} {name}")
            if ng:
                lines += ["", "누락 항목이 있어도 앱 재시작 시 마이그레이션으로 자동 보정될 수 있습니다.",
                           "재시작 후 다시 점검해도 동일하면 알려주세요."]
                CustomMessageBox.showwarning(self.root, "운영 DB 스키마 점검", "\n".join(lines))
            else:
                CustomMessageBox.showinfo(self.root, "운영 DB 스키마 점검", "\n".join(lines))
        except Exception as e:
            logger.error(f"운영 DB 스키마 점검 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.root, "스키마 점검 오류", str(e))

    def _on_toggle_developer_mode(self) -> None:
        enabled = bool(getattr(self, '_dev_mode_var', None) and self._dev_mode_var.get())
        ok = self._set_developer_mode_enabled(enabled) if hasattr(self, '_set_developer_mode_enabled') else False
        if not ok:
            CustomMessageBox.showerror(self.root, "개발자 모드", "설정을 저장하지 못했습니다.")
            return
        state_txt = "ON" if enabled else "OFF"
        self._log(f"개발자 모드 변경: {state_txt}")
        CustomMessageBox.showinfo(
            self.root, "개발자 모드",
            f"개발자 모드가 {state_txt}로 저장되었습니다.\n메뉴 반영을 위해 앱을 다시 열어주세요."
        )

    # ═══════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════

    def _safe_call(self, method_name: str):
        fn = getattr(self, method_name, None)
        if fn and callable(fn):
            fn()
        else:
            logger.warning(f"메서드 미정의: {method_name}")
            try:
                CustomMessageBox.showwarning(None, "기능 준비 중", f"'{method_name}' 기능은 아직 구현되지 않았습니다.")
            except (ImportError, ModuleNotFoundError) as _e:
                logger.debug(f"safe_call: {_e}")

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
            for fn in ['_refresh_inventory', '_refresh_allocation', '_refresh_picked', '_refresh_sold', '_refresh_cargo_overview', '_refresh_dashboard']:
                if hasattr(self, fn): getattr(self, fn)()
            self._log("🔄 전체 새로고침 완료")
        except (RuntimeError, OSError) as e:
            logger.error(f"새로고침: {e}")

    def _change_font_size(self, size: int):
        try:
            if tkfont is None:
                raise RuntimeError("tkfont unavailable")
            for name in ["TkDefaultFont", "TkTextFont"]:
                tkfont.nametofont(name).configure(size=size)
            self._log(f"🔤 글꼴 크기: {size}pt")
        except (RuntimeError, ValueError, AttributeError) as e:
            logger.error(f"글꼴 크기: {e}")

    def _create_search_btn_style(self, font_family: str) -> str:
        """호환성 stub"""
        return 'TButton'

    def _update_signal_lights(self, status: str = 'ok') -> None:
        """신호등 업데이트: ok=초록, warn=노랑, error=빨강"""
        if not hasattr(self, '_signal_lights'):
            return
        colors = {
            'ok': {'green': '#22c55e', 'yellow': '#4a5568', 'red': '#4a5568'},
            'warn': {'green': '#4a5568', 'yellow': '#eab308', 'red': '#4a5568'},
            'error': {'green': '#4a5568', 'yellow': '#4a5568', 'red': '#ef4444'},
        }
        c = colors.get(status, colors['ok'])
        for name, color in c.items():
            try:
                self._signal_lights[name].config(fg=color)
            except (tk.TclError, KeyError):
                pass
