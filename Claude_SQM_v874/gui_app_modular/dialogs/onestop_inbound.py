"""
SQM v3.8.4 — 원스톱 입고 팝업 (P3-S1 Refactored)
4종 서류(PL, Invoice, BL, DO)를 한 화면에서:
  파일 선택 → 체크 표시 → 파싱 → 미리보기 → DB 업로드

작성일: 2025-02-06
P3-S1 리팩토링: 2026-04-12
"""
# ══════════════════════════════════════════════════════════════
# 🎨 색상 사용 원칙 (v3.8.0 — 절대 준수)
# ══════════════════════════════════════════════════════════════
# ✅ 올바른 방법: tc() 함수 사용 (라이트/다크 자동 전환)
#     from gui_app_modular.utils.ui_constants import tc
#     label.config(fg=tc('text_primary'), bg=tc('bg_primary'))
# ══════════════════════════════════════════════════════════════

from gui_app_modular.utils.ui_constants import create_themed_toplevel  # v8.0.9
from gui_app_modular.utils.ui_constants import tc
from engine_modules.constants import CARRIER_OPTIONS, STATUS_AVAILABLE
from features.parsers.inbound_parser import InboundParser  # P2 리팩토링
from features.validators.inbound_validator import InboundValidator  # P2 리팩토링
from features.services.inbound_service import InboundService  # P2 리팩토링
# v8.0.6 [MULTI-TEMPLATE] 다중 템플릿 후보 엔진 연결
try:
    from features.parsers.onestop_inbound_candidate_patch import (
        parse_bl_with_candidate,
        parse_do_with_candidate,
    )
    _HAS_CANDIDATE_ENGINE = True
except ImportError:
    _HAS_CANDIDATE_ENGINE = False
import os
import time
import json
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, BOTH, YES, X, Y, LEFT, RIGHT, BOTTOM, END, VERTICAL, HORIZONTAL
import logging
from engine_modules.constants import DEFAULT_TONBAG_WEIGHT  # v8.6.1
import threading
from datetime import datetime, timedelta, date as _date_type
from copy import deepcopy

# 비즈니스 기본값
from core.constants import DEFAULT_WAREHOUSE

from ..utils.ui_constants import (
    ThemeColors, DialogSize, center_dialog, apply_modal_window_options,
    setup_dialog_geometry_persistence, is_dark,
)
from core.types import safe_float
from ..utils.tree_enhancements import HeaderFilterBar

# v5.8.7: DatePicker 달력 UI
from ..utils.gui_bootstrap import DateEntry, HAS_DATEENTRY

# P3-S1: Mixin imports
from .inbound_utils import (
    merge_results, empty_row, date_str, format_bl, fill_do,
    amd_validate_date, amd_calc_dates
)
from .inbound_preview_service import InboundPreviewService, PREVIEW_COLUMNS
from .inbound_parse_service import InboundParseService, DOC_TYPES
from .inbound_template_service import InboundTemplateService
from .inbound_progress_helper import InboundProgressHelper
from .inbound_date_dialog import InboundDateDialogMixin
from .inbound_dialog_base import InboundDialogBase
from .inbound_upload_mixin import InboundUploadMixin
from .inbound_ui_build_service import InboundUIBuildService
from .inbound_write_service import InboundWriteService

logger = logging.getLogger(__name__)
ENABLE_PARSE_CONFIRM = False  # v8.1.x: 파싱 결과 확인 팝업 비활성화


def _dbg_log(msg: str) -> None:
    logger.debug(f'[DBG] {msg}')


# v5.7.5: 진행률 팝업 조정
PROGRESS_POPUP_WIDTH = 880
PROGRESS_POPUP_HEIGHT = 380
PROGRESS_POPUP_CLOSE_DELAY_MS = 1600


class OneStopInboundDialog(
    InboundPreviewService,
    InboundWriteService,
    InboundParseService,
    InboundUIBuildService,
    InboundUploadMixin,
    InboundDialogBase,
):
    """v3.8.4 원스톱 입고 팝업 (P3-S1 Refactored)

    하나의 팝업에서:
    1. 4종 파일 선택 (각각 [파일 선택] 버튼 + ✅ 체크)
    2. [파싱 시작] → 프로그레스 바
    3. 18열 미리보기 테이블
    4. [DB 업로드] 또는 [Excel 내보내기]

    메서드 분배:
    - InboundPreviewService: 미리보기 테이블 조작/편집/필터
    - InboundWriteService: DB 저장 전후 처리, 성공 표시, 정리
    - InboundParseService: 파싱 스레드, 파싱 전후 처리
    - InboundUIBuildService: UI 생성, _create_dialog
    - InboundTemplateService: 파싱 템플릿 관리
    - InboundProgressHelper: 진행률 표시
    - InboundDateDialogMixin: 날짜 입력 다이얼로그
    - InboundUploadMixin: DB 업로드, Excel 내보내기
    - InboundDialogBase: 공통 기능
    """

    def __init__(self, parent, engine, log_fn=None, app=None):
        self.parent = parent
        self.engine = engine
        self.app = app
        self._log = log_fn or (lambda msg, **kw: logger.info(msg))

        # 파일 경로 저장
        self.file_paths = {}
        self._last_selected_dir = ""

        # 파싱 결과
        self.parsed_results = {}
        self.preview_data = []

        # 업로드 결과
        self.upload_success = False
        self._show_container_suffix = False
        self._ask_excel_after_upload = False

        # UI 참조
        self.dialog = None
        self.file_labels = {}
        self.check_labels = {}
        self.tree = None
        self.btn_parse = None
        self.btn_reparse = None
        self.btn_upload = None
        self.btn_excel = None
        self.btn_undo = None
        self.btn_redo = None
        self.btn_reset_original = None
        self.filter_bar = None
        self._var_upload_by_view_order = None
        self._editing_item = None
        self._preview_anchor = (0, 0)
        self._edited_rows = set()
        self._undo_stack = []
        self._redo_stack = []
        self._max_history = 50
        self._sort_col = None
        self._sort_desc = False
        self._view_indices = []
        self._original_preview_data = []
        self._auto_start_parse = False
        self._skip_parse_confirm = False
        self.compact_mode = True
        self._compact_tree_frame = None

    def show(
        self,
        initial_files: dict = None,
        auto_start_parse: bool = False,
        skip_parse_confirm: bool = False,
    ) -> None:
        """팝업 표시."""
        self._initial_files = initial_files or {}
        self._auto_start_parse = bool(auto_start_parse)
        self._skip_parse_confirm = bool(skip_parse_confirm)
        logger.info(
            "OneStopInboundDialog.show(files=%s, auto_start=%s, skip_confirm=%s)",
            list((initial_files or {}).keys()),
            auto_start_parse,
            skip_parse_confirm,
        )
        try:
            for _p in self._initial_files.values():
                if _p and os.path.exists(_p):
                    _d = os.path.dirname(_p)
                    if _d and os.path.isdir(_d):
                        self._last_selected_dir = _d
                        break
        except (OSError, IOError, PermissionError) as e:
            logger.warning(f"초기 폴더 경로 설정 무시: {e}")
        self._create_dialog()

    # ── UI 위젯 헬퍼 ────────────────────────────────────────

    def _attach_doc_tooltip(self, widget, text: str):
        """문서 위젯에 툴팁 추가"""
        tip = None
        def enter(e):
            nonlocal tip
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{e.x_root+15}+{e.y_root+10}")
            _od = is_dark()
            lbl = tk.Label(tip, text=text, justify='left',
                          background=ThemeColors.get('bg_card', _od),
                          foreground=ThemeColors.get('text_primary', _od),
                          relief='solid', borderwidth=1,
                          font=('맑은 고딕', 11), padx=8, pady=6)
            lbl.pack()
        def leave(e):
            nonlocal tip
            if tip:
                tip.destroy()
                tip = None
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

    # ── _create_dialog: UI 빌드 (InboundUIBuildService 위임) ──

    def _cd_setup_window(self) -> ttk.Frame:
        """다이얼로그 윈도우 생성 + 크기/모달 설정."""
        self.dialog = create_themed_toplevel(self.parent)
        try:
            from version import __version__ as _sqm_ver
        except ImportError:
            _sqm_ver = "8.1.1"
        self.dialog.title(f"📥 입고 — SQM v{_sqm_ver}")
        apply_modal_window_options(self.dialog)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        if getattr(self, 'compact_mode', False):
            self.dialog.geometry("1180x560")
            self.dialog.minsize(900, 420)
            self.dialog.resizable(True, True)
            center_dialog(self.dialog, self.parent)
        else:
            self.dialog.minsize(720, 520)
            try:
                sw = self.parent.winfo_screenwidth()
                sh = self.parent.winfo_screenheight()
                w = min(1320, int(sw * 0.82))
                h = min(900, int(sh * 0.88))
                x = (sw - w) // 2
                y = max(30, (sh - h) // 2)
                self.dialog.geometry(f"{w}x{h}+{x}+{y}")
            except Exception as e:
                logger.warning(f"[UI] dialog geometry calculation failed: {e}")
                self.dialog.geometry(DialogSize.get_geometry(self.parent, 'large'))
                center_dialog(self.dialog, self.parent)
            setup_dialog_geometry_persistence(self.dialog, "onestop_inbound_dialog", self.parent)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        main = ttk.Frame(self.dialog, padding=6)
        main.pack(fill=BOTH, expand=YES)
        return main

    def _cd_build_step_indicator(self, main: ttk.Frame):
        """상단 진행 단계 표시 (Flexport 스타일 ①②③④)."""
        _is_dark = is_dark()
        _bg      = ThemeColors.get('bg_secondary', _is_dark)
        _accent  = ThemeColors.get('accent',       _is_dark)
        _muted   = ThemeColors.get('text_muted',   _is_dark)
        _border  = ThemeColors.get('border',       _is_dark)
        _text    = ThemeColors.get('text_primary',  _is_dark)

        step_fr = tk.Frame(main, bg=_bg, pady=6)
        step_fr.pack(fill=X, pady=(0, 6))

        STEPS = [
            ('①', '서류 선택', '파일 업로드'),
            ('②', '파싱 실행', 'AI 분석'),
            ('③', '결과 확인', '미리보기'),
            ('④', 'DB 저장',   '입고 완료'),
        ]
        step_fr.columnconfigure(tuple(range(len(STEPS) * 2 - 1)), weight=1)
        for col_i, (num, title, sub) in enumerate(STEPS):
            col = col_i * 2
            cell = tk.Frame(step_fr, bg=_bg)
            cell.grid(row=0, column=col, padx=8)
            tk.Label(
                cell, text=num,
                bg=_accent if col_i == 0 else _bg,
                fg='#0f172a' if col_i == 0 else _muted,
                font=('맑은 고딕', 11, 'bold'),
                width=3, relief='flat',
            ).pack(side=LEFT, padx=(0, 4))
            txt_fr = tk.Frame(cell, bg=_bg)
            txt_fr.pack(side=LEFT)
            tk.Label(
                txt_fr, text=title,
                bg=_bg,
                fg=_accent if col_i == 0 else _text,
                font=('맑은 고딕', 10, 'bold' if col_i == 0 else 'normal'),
            ).pack(anchor='w')
            tk.Label(
                txt_fr, text=sub,
                bg=_bg, fg=_muted,
                font=('맑은 고딕', 8),
            ).pack(anchor='w')
            if col_i < len(STEPS) - 1:
                tk.Label(
                    step_fr, text='›',
                    bg=_bg, fg=_muted,
                    font=('', 16),
                ).grid(row=0, column=col + 1)

        self._step_labels = [
            step_fr.grid_slaves(row=0, column=i*2)[0]
            for i in range(len(STEPS))
            if step_fr.grid_slaves(row=0, column=i*2)
        ]
        self._step_fr_ref  = step_fr
        self._step_bg      = _bg
        self._step_accent  = _accent
        self._step_muted   = _muted
        self._step_text    = _text

        tk.Frame(main, bg=_border, height=1).pack(fill=X, pady=(0, 6))

    def _cd_build_parse_action_buttons(self, file_frame: ttk.Frame):
        """파싱 액션 버튼 행."""
        actions = ttk.Frame(file_frame)
        actions.pack(fill=X, pady=(4, 0))

        self.btn_folder = ttk.Button(
            actions, text="📁 멀티 선택",
            command=self._select_folder, width=13,
        )
        self.btn_folder.pack(side=LEFT, padx=(0, 6))
        self._attach_doc_tooltip(self.btn_folder,
            "Ctrl+클릭으로 BL·PL·FA·DO 파일을 한번에 선택합니다.\n"
            "파일명/내용 기반으로 서류 유형을 자동 감지합니다.")

        self.btn_parse = ttk.Button(
            actions, text="▶  파싱 시작",
            command=self._start_parsing,
            state='disabled', width=14,
            style='Accent.TButton',
        )
        self.btn_parse.pack(side=LEFT, padx=(0, 6))
        self._attach_doc_tooltip(self.btn_parse,
            "선택한 서류를 분석합니다\n\n• Bill of Loading → BL번호, 선박, 일정 추출\n"
            "• Packing List → LOT, 수량, 중량 추출\n"
            "• Invoice, FA → SAP번호, 금액 추출\n"
            "• Delivery Order → 인도장소, Free Time 추출")

        self.btn_reparse = ttk.Button(
            actions, text="↻ 다시 파싱",
            command=self._reparse_with_current_files,
            state='disabled', width=11,
        )
        self.btn_reparse.pack(side=LEFT, padx=(0, 6))

        self.btn_reparse_carrier = ttk.Button(
            actions, text="🚢 선사 재파싱",
            command=self._reparse_after_carrier_change,
            state='disabled', width=14,
        )
        self.btn_reparse_carrier.pack(side=LEFT, padx=(0, 10))

        self.parse_hint = ttk.Label(
            actions, text="",
            foreground=tc('text_primary'), font=('맑은 고딕', 12),
        )
        self.parse_hint.pack(side=LEFT, fill=X, expand=True, padx=(4, 0))
        self._update_parse_hint()

        if getattr(self, '_auto_start_parse', False):
            def _deferred_start():
                try:
                    if self.dialog and self.dialog.winfo_exists():
                        self._log("⚡ 자동 파싱 시작 (빠른 스캔 모드)")
                        self.dialog.after(500, self._start_parsing)
                except Exception as _e:
                    logger.warning("자동 파싱 예약 실패: %s", _e)
            try:
                self.dialog.update_idletasks()
                self.dialog.after_idle(_deferred_start)
            except Exception as e:
                logger.warning(f"[UI] deferred start scheduling failed: {e}")

    def _cd_build_carrier_and_progress(self, main: ttk.Frame):
        """선사/템플릿 선택 + 프로그레스 바 구성."""
        _tpl_row = ttk.Frame(main)
        _tpl_row.pack(fill=X, pady=(0, 2))
        _os_dark_tpl = is_dark()

        self._tpl_var = tk.StringVar(value='')
        self._tpl_combo = ttk.Combobox(
            self.dialog, textvariable=self._tpl_var, state='readonly', width=1
        )
        self._tpl_combo.bind('<<ComboboxSelected>>', self._on_template_selected)

        ttk.Label(
            _tpl_row, text="적용 템플릿:",
            font=('맑은 고딕', 11, 'bold'),
            foreground=ThemeColors.get('text_primary', _os_dark_tpl)
        ).pack(side=LEFT, padx=(4, 4))

        self._tpl_selected_lbl = ttk.Label(
            _tpl_row, text="(미선택)",
            font=('맑은 고딕', 11), foreground=tc('text_muted')
        )
        self._tpl_selected_lbl.pack(side=LEFT, padx=(0, 8))

        ttk.Separator(_tpl_row, orient='vertical').pack(
            side=LEFT, fill='y', padx=(8, 8), pady=2)
        self.btn_add_do_later = ttk.Button(
            _tpl_row, text="📋 D/O 나중에",
            command=self._on_add_do_later, state='normal', width=20)
        self.btn_add_do_later.pack(side=LEFT, padx=2)

        self._inbound_template_data: dict = {}
        self._carrier_manual_var = tk.StringVar(value='UNKNOWN')
        self._load_template_combo()

        _carrier_row = ttk.Frame(main)
        _carrier_row.pack(fill=X, pady=(0, 2))
        _os_dark2 = is_dark()
        ttk.Label(
            _carrier_row, text="🚢 선사:",
            font=('맑은 고딕', 12, 'bold'),
            foreground=ThemeColors.get('text_primary', _os_dark2)
        ).pack(side=LEFT, padx=(4, 4))
        self._carrier_pick_combo = ttk.Combobox(
            _carrier_row,
            textvariable=self._carrier_manual_var,
            values=list(CARRIER_OPTIONS),
            state='readonly', width=16, font=('맑은 고딕', 11),
        )
        self._carrier_pick_combo.pack(side=LEFT, padx=(0, 8))
        self._carrier_pick_combo.bind(
            '<<ComboboxSelected>>', self._on_carrier_combo_selected)
        self._carrier_label = tk.Label(
            _carrier_row,
            text="  뱃지 클릭: 템플릿 목록  ",
            font=('맑은 고딕', 12, 'bold'),
            fg=tc('badge_text'), bg=tc('bg_secondary'),
            relief="flat", padx=8, pady=2, bd=0, cursor="hand2",
        )
        self._carrier_label.pack(side=LEFT, padx=(0, 8))
        self._carrier_label.bind(
            '<Button-1>', lambda _e: self._show_template_table_picker_for_current_carrier())

        # 프로그레스 바
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="")
        self._progress_popup = None
        self._progress_popup_label = None
        self._progress_popup_bar = None

        _pop_dark = is_dark()
        progress_section = ttk.LabelFrame(main, text="⏱ 진행 상태", padding=8)
        progress_section.pack(fill=X, pady=(6, 4))
        self._progress_inline_placeholder = ttk.Label(
            progress_section, text="파싱을 시작하면 진행 상황이 여기에 표시됩니다.",
            font=('맑은 고딕', 11), foreground=ThemeColors.get('text_muted', _pop_dark))
        self._progress_inline_placeholder.pack(anchor='w')
        self._progress_inline_frame = ttk.Frame(progress_section)
        self._progress_inline_msg = ttk.Label(self._progress_inline_frame, text="", font=('맑은 고딕', 12, 'bold'))
        self._progress_inline_msg.pack(anchor='w')
        _ps = ttk.Style()
        _ps.configure('Inline.Horizontal.TProgressbar',
                      troughcolor=ThemeColors.get('bg_secondary', _pop_dark), thickness=12)
        self._progress_bar_container = ttk.Frame(self._progress_inline_frame)
        self._progress_bar_container.pack(fill=X, pady=(4, 2))
        self._progress_inline_bar = ttk.Progressbar(
            self._progress_bar_container, maximum=100, mode='determinate',
            style='Inline.Horizontal.TProgressbar')
        self._progress_inline_bar.pack(fill=X)
        self._progress_inline_busy = ttk.Label(
            self._progress_bar_container, text="진행 중 ●", font=('맑은 고딕', 10),
            foreground=ThemeColors.get('statusbar_icon_warn', _pop_dark))
        self._progress_inline_busy.place(relx=0, rely=0.5, anchor='w')
        _row2 = ttk.Frame(self._progress_inline_frame)
        _row2.pack(fill=X)
        self._progress_inline_pct_elapsed = ttk.Label(
            _row2, text="", font=('맑은 고딕', 10),
            foreground=ThemeColors.get('text_secondary', _pop_dark))
        self._progress_inline_pct_elapsed.pack(side=tk.RIGHT)

    def _cd_build_preview_table(self, main: ttk.Frame):
        """미리보기 Treeview + 필터바 구성."""
        _tree_dark = is_dark()
        self._var_show_container_suffix = tk.BooleanVar(value=False)
        if not getattr(self, 'compact_mode', False):
            self._tree_frame_visible = False
            tree_frame = ttk.LabelFrame(main, text="📊 미리보기 (스케일링·처리된 데이터)", padding=4)
            self._tree_frame = tree_frame
            import tkinter.font as tkfont
            preview_font = tkfont.Font(family='맑은 고딕', size=11)
            row_height = preview_font.metrics('linespace') + 6
            _tree_fg = ThemeColors.get('text_primary', _tree_dark)
            style = ttk.Style()
            style.configure('Preview.Treeview',
                            font=('맑은 고딕', 11), rowheight=row_height,
                            foreground=_tree_fg,
                            fieldbackground=ThemeColors.get('bg_card', _tree_dark))
            style.configure('Preview.Treeview.Heading',
                            font=('맑은 고딕', 10, 'bold'), anchor='center')
            columns = tuple(col[0] for col in PREVIEW_COLUMNS)
            self.tree = ttk.Treeview(
                tree_frame, columns=columns, show="headings",
                height=18, selectmode='extended', style='Preview.Treeview')
            self.tree._enable_global_editable = True
            self.tree._on_tree_data_changed = self._sync_tree_edit_to_preview_data
            self.tree.tag_configure('odd', background=ThemeColors.get('tree_stripe', _tree_dark), foreground=_tree_fg)
            self.tree.tag_configure('even', background=ThemeColors.get('bg_card', _tree_dark), foreground=_tree_fg)
            self.tree.tag_configure('edited', background=ThemeColors.get('warning', _tree_dark), foreground=_tree_fg)
            self.tree.tag_configure('xc_critical', background=tc('picked'), foreground=tc('danger'))
            self.tree.tag_configure('xc_warning', background=tc('picked'), foreground=tc('warning'))
            self.tree.tag_configure('xc_info', background=tc('reserved'), foreground=tc('text_muted'))
            for col_id, header, width, anchor in PREVIEW_COLUMNS:
                self.tree.heading(
                    col_id, text=header, anchor='center',
                    command=lambda c=col_id: self._toggle_preview_sort(c))
                self.tree.column(col_id, width=width, anchor=anchor, minwidth=35)
            scrollbar_y = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
            scrollbar_x = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.tree.xview)
            self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
            scrollbar_x.pack(side=BOTTOM, fill=X)
            self.tree.pack(side=LEFT, fill=BOTH, expand=YES)
            scrollbar_y.pack(side=RIGHT, fill=Y)
            self._setup_preview_edit_bindings()
            chk_container = ttk.Checkbutton(
                tree_frame, text="컨테이너 번호 접미사(-숫자) 표시",
                variable=self._var_show_container_suffix,
                command=self._on_toggle_container_suffix)
            chk_container.pack(anchor='w', padx=4, pady=(2, 0))
            self.filter_bar = HeaderFilterBar(
                main, self.tree,
                filter_columns=[
                    ('sap_no', 'SAP', 120), ('bl_no', 'BL', 120),
                    ('container_no', 'CONTAINER', 120), ('product', 'PRODUCT', 140),
                    ('status', 'STATUS', 90),
                ],
                on_filter=self._on_change_preview_filter, is_dark=_tree_dark)
            self.filter_bar.pack(fill=X, pady=(2, 2))
        else:
            self.tree = None
            self.filter_bar = None
            self._tree_frame = None
            self._tree_frame_visible = False

    def _build_inbound_action_buttons(self, main, _tree_dark: bool) -> None:
        """하단 액션 버튼 바."""
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=X, pady=(8, 0))
        _font = '맑은 고딕'
        _btn_font_size = 15
        _btn_fg = ThemeColors.get('badge_text', _tree_dark)
        _blue = ThemeColors.get('info', _tree_dark)
        _red = ThemeColors.get('statusbar_icon_err', _tree_dark)

        self.btn_excel = tk.Button(
            btn_frame, text="📥 Excel 내보내기",
            command=self._export_to_excel, state='disabled',
            font=(_font, _btn_font_size, 'bold'), bg=_blue, fg=_btn_fg,
            padx=15, pady=6, cursor='hand2', bd=0)
        self.btn_excel.pack(side=LEFT, padx=(0, 5))

        self.btn_undo = tk.Button(
            btn_frame, text="↶ 되돌리기",
            command=self._undo_preview_edit, state='disabled',
            font=(_font, 11, 'bold'), bg=ThemeColors.get('btn_neutral', _tree_dark), fg=_btn_fg,
            padx=10, pady=6, cursor='hand2', bd=0)
        self.btn_undo.pack(side=LEFT, padx=(5, 0))
        self.btn_redo = tk.Button(
            btn_frame, text="↷ 다시실행",
            command=self._redo_preview_edit, state='disabled',
            font=(_font, 11, 'bold'), bg=ThemeColors.get('btn_neutral', _tree_dark), fg=_btn_fg,
            padx=10, pady=6, cursor='hand2', bd=0)
        self.btn_redo.pack(side=LEFT, padx=(5, 0))

        self.btn_reset_original = tk.Button(
            btn_frame, text="⟲ 원본 초기화",
            command=self._reset_preview_to_original, state='disabled',
            font=(_font, 11, 'bold'), bg=ThemeColors.get('btn_neutral', _tree_dark), fg=_btn_fg,
            padx=10, pady=6, cursor='hand2', bd=0)
        self.btn_reset_original.pack(side=LEFT, padx=(5, 0))

        self._var_upload_by_view_order = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            btn_frame, text="DB 업로드 시 현재 정렬/필터 순서 적용",
            variable=self._var_upload_by_view_order).pack(side=LEFT, padx=(8, 0))

        self.btn_upload = tk.Button(
            btn_frame, text="📤 DB 업로드",
            command=self._on_upload, state='disabled',
            font=(_font, _btn_font_size, 'bold'), bg=_blue, fg=_btn_fg,
            padx=20, pady=8, cursor='hand2', bd=0)
        self.btn_upload.pack(side=LEFT, padx=(5, 0))

        _green = '#27ae60'
        self.btn_save_template = tk.Button(
            btn_frame, text="📋 템플릿 저장",
            command=self._on_save_current_as_template, state='disabled',
            font=(_font, _btn_font_size - 1, 'bold'), bg=_green, fg=_btn_fg,
            padx=12, pady=8, cursor='hand2', bd=0)
        self.btn_save_template.pack(side=LEFT, padx=(5, 0))

        self.summary_var = tk.StringVar(value="")
        ttk.Label(btn_frame, textvariable=self.summary_var,
                  font=('맑은 고딕', 13, 'bold'),
                  foreground=ThemeColors.get('statusbar_progress', _tree_dark)
                  ).pack(side=LEFT, fill=X, expand=True, padx=10)

        tk.Button(
            btn_frame, text="❌ 취소",
            command=self._on_cancel,
            font=(_font, _btn_font_size, 'bold'), bg=_red, fg=_btn_fg,
            padx=20, pady=8, cursor='hand2', bd=0
        ).pack(side=RIGHT, padx=(5, 0))

    # ── 파일 선택 ───────────────────────────────────────────

    def _select_folder(self) -> None:
        """멀티파일 선택 → 자동 서류 감지."""
        initial_dir = ""
        try:
            if self._last_selected_dir and os.path.isdir(self._last_selected_dir):
                initial_dir = self._last_selected_dir
        except (OSError, IOError, PermissionError) as e:
            logger.debug(f"[UI] initial dir lookup: {e}")
        _dlg = self.dialog
        try:
            if _dlg and _dlg.winfo_exists():
                _dlg.withdraw()
        except (RuntimeError, tk.TclError) as e:
            logger.debug(f"[UI] dialog withdraw skipped: {e}")
        selected = filedialog.askopenfilenames(
            parent=self.parent,
            title="입고 서류 선택 (Ctrl+클릭으로 BL, PL, FA, DO 한번에 선택)",
            initialdir=initial_dir if initial_dir else None,
            filetypes=[("PDF files", "*.pdf *.PDF"), ("Image (D/O 캡처)", "*.png *.jpg *.jpeg"), ("All files", "*.*")],
        )
        try:
            if _dlg and _dlg.winfo_exists():
                _dlg.deiconify()
                _dlg.lift()
                _dlg.focus_force()
        except (RuntimeError, tk.TclError) as e:
            logger.debug(f"[UI] dialog restore skipped: {e}")
        if not selected:
            self._log("⚠️ 파일 선택이 취소되었습니다.")
            return
        try:
            first_dir = os.path.dirname(selected[0])
            if first_dir and os.path.isdir(first_dir):
                self._last_selected_dir = first_dir
        except (OSError, IOError, PermissionError) as e:
            logger.debug(f"[UI] folder remember: {e}")
        try:
            from gui_app_modular.handlers.inbound_doc_detector import InboundDocDetector
            detector = InboundDocDetector(log_fn=self._log)
            folder = os.path.dirname(selected[0])
            file_names = [os.path.basename(p) for p in selected]
            detected = detector.detect_from_folder(folder, file_names)
        except (ImportError, AttributeError, OSError) as e:
            logger.error(f"[onestop] 서류 자동 감지 실패: {e}")
            detected = {}
        if not detected and selected:
            self._log("🔄 자동 감지 실패 — 선택 순서대로 BL→PL→FA→DO 배정")
            _fallback_order = ['BL', 'PACKING_LIST', 'INVOICE', 'DO']
            for i, path in enumerate(selected):
                if i < len(_fallback_order):
                    detected[_fallback_order[i]] = path
        registered = []
        _success_c = ThemeColors.get('success', is_dark())
        for doc_type in ['BL', 'PACKING_LIST', 'INVOICE', 'DO']:
            if doc_type not in detected:
                continue
            path = detected[doc_type]
            fname = os.path.basename(path)
            self.file_paths[doc_type] = path
            try:
                self.file_labels[doc_type].config(text=fname, foreground=ThemeColors.get('text_primary', is_dark()))
                self.check_labels[doc_type].config(text="✅", fg=_success_c)
            except (RuntimeError, tk.TclError, KeyError) as e:
                logger.debug(f"[UI] doc label update skipped: {e}")
            self._log(f"📂 {doc_type}: {fname}")
            registered.append(doc_type)
        if registered:
            self._log(f"📁 멀티 선택 완료: {len(registered)}종 ({', '.join(registered)})")
            if any(v for v in self.file_paths.values()):
                self._activate_step(0)
            self._update_parse_hint()

    def _select_file(self, doc_type: str):
        """서류별 파일 선택."""
        type_names = {'PACKING_LIST': 'Packing List', 'INVOICE': 'Invoice, FA',
                      'BL': 'Bill of Loading', 'DO': 'Delivery Order'}
        initial_dir = ""
        try:
            if self._last_selected_dir and os.path.isdir(self._last_selected_dir):
                initial_dir = self._last_selected_dir
            elif doc_type in self.file_paths:
                prev_dir = os.path.dirname(self.file_paths.get(doc_type, ""))
                if prev_dir and os.path.isdir(prev_dir):
                    initial_dir = prev_dir
        except (OSError, IOError, PermissionError) as e:
            logger.debug(f"[UI] initial dir calc: {e}")
        _dlg = self.dialog
        try:
            if _dlg and _dlg.winfo_exists():
                _dlg.withdraw()
        except (RuntimeError, tk.TclError) as e:
            logger.debug(f"[UI] dialog withdraw before file picker: {e}")
            _dlg = None
        file_path = filedialog.askopenfilename(
            parent=self.parent,
            title=f"{type_names.get(doc_type, doc_type)} 파일 선택",
            initialdir=initial_dir if initial_dir else None,
            filetypes=[("PDF files", "*.pdf"), ("Image (D/O 캡처)", "*.png *.jpg *.jpeg"), ("All files", "*.*")])
        try:
            if _dlg and _dlg.winfo_exists():
                _dlg.deiconify()
                _dlg.lift()
                _dlg.focus_force()
        except (RuntimeError, tk.TclError) as e:
            logger.debug(f"[UI] dialog restore after file picker: {e}")
        if not file_path:
            return
        try:
            selected_dir = os.path.dirname(file_path)
            if selected_dir and os.path.isdir(selected_dir):
                self._last_selected_dir = selected_dir
        except (OSError, IOError, PermissionError) as e:
            logger.debug(f"[UI] selected dir save: {e}")
        self.file_paths[doc_type] = file_path
        fname = os.path.basename(file_path)
        self.file_labels[doc_type].config(text=fname, foreground=ThemeColors.get('text_primary', is_dark()))
        self.check_labels[doc_type].config(text="✅")
        self._log(f"📂 {doc_type}: {fname}")
        if any(v for v in self.file_paths.values()):
            self._activate_step(0)
        self._update_parse_hint()

    # ── 오케스트레이션 ──────────────────────────────────────

    def _activate_step(self, step_index: int) -> None:
        """진행 단계 배지 활성화."""
        if not hasattr(self, '_step_labels') or not self._step_labels:
            return
        try:
            accent = getattr(self, '_step_accent', '#22d3ee')
            bg     = getattr(self, '_step_bg',     '#1e293b')
            muted  = getattr(self, '_step_muted',  '#475569')
            text   = getattr(self, '_step_text',   '#f1f5f9')
            for i, cell in enumerate(self._step_labels):
                if not cell.winfo_exists():
                    continue
                is_active = (i == step_index)
                is_done   = (i < step_index)
                children = cell.winfo_children()
                if children:
                    badge = children[0]
                    if is_active:
                        badge.config(bg=accent, fg='#0f172a')
                    elif is_done:
                        badge.config(bg='#166534', fg='#4ade80')
                    else:
                        badge.config(bg=bg, fg=muted)
                    badge.config(highlightthickness=0, relief='flat')
                    if len(children) > 1:
                        txt_fr = children[1]
                        for lbl in txt_fr.winfo_children():
                            font = lbl.cget('font') or ''
                            is_title = 'bold' in str(font)
                            if is_active:
                                lbl.config(fg=accent if is_title else text)
                            elif is_done:
                                lbl.config(fg='#4ade80' if is_title else muted)
                            else:
                                lbl.config(fg=muted)
            self._current_step = step_index
        except Exception as e:
            logger.warning(f"[_activate_step] UI 스텝 활성화 실패: {e}")

    def _update_parse_hint(self) -> None:
        """파싱 시작 옆 업로드 상태 문구 갱신."""
        n = len(self.file_paths)
        if not getattr(self, 'parse_hint', None):
            return
        _hint_dark = is_dark()
        if 'BL' not in self.file_paths and 'PACKING_LIST' not in self.file_paths:
            self.parse_hint.config(
                text="💡 최소 Packing List를 선택하세요",
                foreground=ThemeColors.get('text_muted', _hint_dark))
            if self.btn_parse:
                self.btn_parse.config(state='disabled')
            if self.btn_reparse:
                self.btn_reparse.config(state='disabled')
        else:
            if self.btn_parse:
                self.btn_parse.config(state='normal')
            if self.btn_reparse:
                self.btn_reparse.config(state='normal')
            self.parse_hint.config(
                text=f"총 4개 중 {n}개 업로드되었습니다.",
                foreground=ThemeColors.get('text_primary', _hint_dark))

    def _reparse_with_current_files(self) -> None:
        """파일 재선택 없이 현재 file_paths로 재파싱."""
        if 'BL' not in self.file_paths and 'PACKING_LIST' not in self.file_paths:
            from ..utils.custom_messagebox import CustomMessageBox
            CustomMessageBox.showwarning(self.dialog, "재파싱 불가", "BL 또는 Packing List 파일이 필요합니다.")
            return
        from ..utils.custom_messagebox import CustomMessageBox
        ok = CustomMessageBox.askyesno(
            self.dialog, "재파싱 확인",
            "기존 미리보기 결과를 덮어쓰고 재파싱합니다.\n\n계속하시겠습니까?")
        if not ok:
            return
        self._do_start_parsing_after_template()

    def _update_summary(self) -> None:
        """합계행 갱신."""
        if not self.preview_data:
            self.summary_var.set("")
            return
        containers = set(r['container_no'] for r in self.preview_data if r['container_no'])
        total_tb = 0
        total_net = 0.0
        total_gross = 0.0
        for r in self.preview_data:
            try:
                total_tb += int(r.get('mxbg_pallet', '10')) if r.get('mxbg_pallet', '') else 0
            except (ValueError, TypeError) as e:
                logger.debug(f"summary tonbag parse: {e}")
            try:
                total_net += safe_float(r['net_weight']) if r['net_weight'] else 0
            except (ValueError, TypeError) as e:
                logger.debug(f"summary net_weight parse: {e}")
            try:
                total_gross += safe_float(r['gross_weight']) if r['gross_weight'] else 0
            except (ValueError, TypeError) as e:
                logger.debug(f"summary gross_weight parse: {e}")
        self.summary_var.set(
            f"합계: {len(self.preview_data)} LOT | "
            f"{len(containers)} 컨테이너 | "
            f"{total_tb} 톤백 | "
            f"Net {total_net:,.0f} kg | "
            f"Gross {total_gross:,.0f} kg"
        )

    # ── 유틸리티 ────────────────────────────────────────────

    def _log_safe(self, msg: str):
        """스레드 안전 로그."""
        try:
            if self._log:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(0, lambda: self._log(msg))
                else:
                    self._log(msg)
        except (RuntimeError, ValueError):
            logger.info(msg)

    def _on_cancel(self):
        """취소."""
        self._clear_preview_from_main()
        if self.dialog:
            self.dialog.destroy()

    def _enable_parse_btn(self):
        """파싱 버튼 재활성화."""
        def _u():
            if self.dialog and self.dialog.winfo_exists():
                self._update_parse_hint()
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, _u)
