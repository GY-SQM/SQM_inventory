"""
SQM v3.8.4 — 원스톱 입고 팝업
4종 서류(PL, Invoice, BL, DO)를 한 화면에서:
  파일 선택 → 체크 표시 → 파싱 → 미리보기 → DB 업로드

작성일: 2025-02-06
"""
import logging
import os
import threading
import time
import tkinter as tk
from copy import deepcopy
from datetime import date as _date_type
from datetime import datetime, timedelta
from tkinter import (
    BOTH,
    BOTTOM,
    END,
    HORIZONTAL,
    LEFT,
    RIGHT,
    VERTICAL,
    YES,
    X,
    Y,
    filedialog,
    ttk,
)

# 비즈니스 기본값
from core.constants import DEFAULT_WAREHOUSE
from core.types import safe_float

# v5.8.7: DatePicker 달력 UI — gui_bootstrap 통일 (ttkbootstrap.DateEntry, 없으면 텍스트 입력 폴백)
from ..utils.gui_bootstrap import HAS_DATEENTRY, DateEntry
from ..utils.tree_enhancements import HeaderFilterBar
from ..utils.ui_constants import (
    DialogSize,
    ThemeColors,
    apply_modal_window_options,
    center_dialog,
)

logger = logging.getLogger(__name__)


# 미리보기 컬럼 정의 — 업로드3: 전 컬럼 가운데 정렬
PREVIEW_COLUMNS = [
    ("no",               "NO",               50,  "center"),
    ("sap_no",           "SAP NO",          110,  "center"),
    ("bl_no",            "BL NO",           150,  "center"),
    ("container_no",     "CONTAINER",       130,  "center"),
    ("product",          "PRODUCT",         180,  "center"),
    ("product_code",     "CODE",            100,  "center"),
    ("lot_no",           "LOT NO",          110,  "center"),
    ("lot_sqm",          "LOT SQM",          80,  "center"),
    ("mxbg_pallet",      "MXBG",             70,  "center"),
    ("net_weight",       "NET(Kg)",          90,  "center"),
    ("gross_weight",     "GROSS(kg)",         90,  "center"),
    ("salar_invoice_no", "INVOICE NO",      120,  "center"),
    ("ship_date",        "SHIP DATE",        90,  "center"),
    ("arrival_date",     "ARRIVAL",          90,  "center"),
    ("con_return",       "CON RETURN",       95,  "center"),
    ("free_time",        "FREE TIME",        80,  "center"),
    ("warehouse",        "WH",              100,  "center"),
    ("status",           "STATUS",           80,  "center"),
]

# 4종 서류 정의 (v3.8.7: 동그라미 번호 순서) — v5.7.5: Invoice/FA, Bill of Loading, Delivery Order
DOC_TYPES = [
    ('PACKING_LIST', '① Packing List (포장명세서)', True),
    ('INVOICE',      '② Invoice, FA (송장)',        True),
    ('BL',           '③ Bill of Loading (선하증권)', True),
    ('DO',           '④ Delivery Order (인도지시서) (선택사항)', False),
]


from .inbound_dialog_base import InboundDialogBase
from .inbound_upload_mixin import InboundUploadMixin

# v5.7.5: 진행률 팝업 조정 — 업로드2: 창·폰트 더 키움
PROGRESS_POPUP_WIDTH = 880
PROGRESS_POPUP_HEIGHT = 380
PROGRESS_POPUP_CLOSE_DELAY_MS = 1600


class OneStopInboundDialog(InboundUploadMixin, InboundDialogBase):
    """v3.8.4 원스톱 입고 팝업
    
    하나의 팝업에서:
    1. 4종 파일 선택 (각각 [파일 선택] 버튼 + ✅ 체크)
    2. [파싱 시작] → 프로그레스 바
    3. 18열 미리보기 테이블
    4. [DB 업로드] 또는 [Excel 내보내기]
    """

    def __init__(self, parent, engine, log_fn=None, app=None):
        self.parent = parent
        self.engine = engine
        self.app = app  # v3.8.8: 메인 앱 참조 (새로고침용)
        self._log = log_fn or (lambda msg, **kw: logger.info(msg))

        # 파일 경로 저장
        self.file_paths = {}  # {doc_type: file_path}

        # 파싱 결과
        self.parsed_results = {}
        self.preview_data = []

        # 업로드 결과
        self.upload_success = False
        # v5.8.9: 컨테이너 번호 접미사(-숫자) 디폴트 숨김, 필요 시 표시
        self._show_container_suffix = False
        # 파싱 결과 팝업에서 DB 업로드 선택 시, 완료 후 엑셀 내보내기 여부 질의
        self._ask_excel_after_upload = False

        # UI 참조
        self.dialog = None
        self.file_labels = {}
        self.check_labels = {}
        self.tree = None
        self.btn_parse = None
        self.btn_upload = None
        self.btn_excel = None
        self.btn_undo = None
        self.btn_redo = None
        self.btn_reset_original = None
        self.filter_bar = None
        self._var_upload_by_view_order = None
        self._editing_item = None
        self._preview_anchor = (0, 0)  # (row_idx, col_idx)
        self._edited_rows = set()
        self._undo_stack = []
        self._redo_stack = []
        self._max_history = 50
        self._sort_col = None
        self._sort_desc = False
        self._view_indices = []
        self._original_preview_data = []

    def show(self, initial_files: dict = None) -> None:
        """팝업 표시. initial_files: { 'DO': 경로 } 등 드래그앤드롭/캡처 이미지 사전 지정."""
        self._initial_files = initial_files or {}
        self._create_dialog()

    def _attach_doc_tooltip(self, widget, text: str):
        """v3.8.9: 문서 위젯에 툴팁 추가"""
        tip = None
        def enter(e):
            nonlocal tip
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{e.x_root+15}+{e.y_root+10}")
            _od = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
            lbl = tk.Label(tip, text=text, justify='left',
                          background=ThemeColors.get('bg_card', _od), foreground=ThemeColors.get('text_primary', _od),
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

    def _create_dialog(self) -> None:
        """원스톱 입고 팝업 생성"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("📥 입고 — SQM v3.9.4")
        self.dialog.minsize(720, 520)
        apply_modal_window_options(self.dialog)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        try:
            self.dialog.state('zoomed')  # v5.9.9: 항상 최대화로 시작
        except tk.TclError:
            self.dialog.geometry(DialogSize.get_geometry(self.parent, 'large'))
            center_dialog(self.dialog, self.parent)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

        main = ttk.Frame(self.dialog, padding=6)
        main.pack(fill=BOTH, expand=YES)

        # ═══════════════════════════════════════════════════════════
        # 1. 상단: 4종 서류 + 파싱 버튼 (1줄 균등 배치)
        # ═══════════════════════════════════════════════════════════
        file_frame = ttk.Frame(main)
        file_frame.pack(fill=X, pady=(0, 4))

        # 6열 그리드: [①PL][②INV][③BL][④DO] [파싱][힌트]
        for i in range(4):
            file_frame.columnconfigure(i, weight=1, uniform='doc')
        file_frame.columnconfigure(4, weight=0)  # 파싱 버튼
        file_frame.columnconfigure(5, weight=0)  # 힌트

        short_names = {
            'PACKING_LIST': '① Packing List',
            'INVOICE':      '② Invoice, FA',
            'BL':           '③ Bill of Loading',
            'DO':           '④ Delivery Order',
        }

        # v3.8.9: 서류별 상세 툴팁 — v5.7.5: Invoice/FA, Bill of Loading, Delivery Order
        _tooltips = {
            'PACKING_LIST': '📦 Packing List (포장명세서)\n\n• LOT번호, 제품명, 수량, 중량 정보 추출\n• 필수 서류 — 없으면 입고 불가\n• PDF 또는 Excel 파일 지원',
            'INVOICE':      '📑 Invoice, FA (송장)\n\n• SAP번호, 단가, 총금액 정보 추출\n• 필수 서류 — 없으면 SAP번호 누락\n• PDF 파일 지원',
            'BL':           '🚢 Bill of Loading (선하증권)\n\n• BL번호, 선박명, 출항일, 도착일 추출\n• 필수 서류 — 없으면 선적 정보 누락\n• PDF 파일 지원',
            'DO':           '📋 Delivery Order (인도지시서)\n\n• 인도 장소, Free Time 정보 추출\n• 선택 서류 — 없어도 입고 가능\n• PDF 파일 지원',
        }

        _os_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        for idx, (doc_type, doc_name, required) in enumerate(DOC_TYPES):
            cell = ttk.Frame(file_frame)
            cell.grid(row=0, column=idx, sticky='ew', padx=(0, 2))

            _cell_fg = ThemeColors.get('text_primary', _os_dark)
            # 서류명
            lbl = ttk.Label(cell, text=short_names.get(doc_type, ''),
                      font=('맑은 고딕', 14, 'bold'),
                      foreground=_cell_fg)
            lbl.pack(side=LEFT, padx=(2, 2))
            self._attach_doc_tooltip(lbl, _tooltips.get(doc_type, ''))

            # 📂 폴더선택 버튼
            btn_sel = tk.Button(cell, text="📂",
                                command=lambda dt=doc_type: self._select_file(dt),
                                font=('', 13), bg=ThemeColors.get('btn_neutral', _os_dark), fg=ThemeColors.get('badge_text', _os_dark),
                                padx=4, pady=1, cursor='hand2', bd=0)
            btn_sel.pack(side=LEFT, padx=(0, 2))
            _req = '(필수)' if required else '(선택)'
            self._attach_doc_tooltip(btn_sel, f"클릭하여 {doc_name} 파일 선택 {_req}")

            # 체크 표시
            check_label = ttk.Label(cell, text="☐", font=('', 15))
            check_label.pack(side=LEFT, padx=(0, 2))
            self.check_labels[doc_type] = check_label

            # 파일명 (동그라미 서류명과 같은 색)
            file_label = ttk.Label(cell, text="", foreground=_cell_fg,
                                   font=('맑은 고딕', 12), anchor='w')
            file_label.pack(side=LEFT, fill=X, expand=True, padx=(0, 2))
            self.file_labels[doc_type] = file_label

        # 드래그앤드롭/캡처 이미지 등 초기 파일 지정
        for doc_type, path in getattr(self, '_initial_files', {}).items():
            if doc_type in self.file_labels and path:
                self.file_paths[doc_type] = path
                self.file_labels[doc_type].configure(text=os.path.basename(path))
                self.check_labels[doc_type].configure(text="☑")

        # [파싱 시작] 버튼
        self.btn_parse = ttk.Button(
            file_frame, text="▶ 파싱 시작",
            command=self._start_parsing,
            state='disabled', width=10
        )
        self.btn_parse.grid(row=0, column=4, padx=(6, 2))
        self._attach_doc_tooltip(self.btn_parse,
            "선택한 서류를 분석합니다\n\n• Packing List → LOT, 수량, 중량 추출\n• Invoice, FA → SAP번호, 금액 추출\n• Bill of Loading → BL번호, 선박, 일정 추출\n• Delivery Order → 인도장소, Free Time 추출")

        self.parse_hint = ttk.Label(
            file_frame, text="",
            foreground='white', font=('맑은 고딕', 12)
        )
        self.parse_hint.grid(row=0, column=5, padx=(2, 4), sticky='w')
        self._update_parse_hint()

        # v5.7.5: 프로그레스 (팝업 + 인라인)
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="")
        self._progress_popup = None
        self._progress_popup_label = None
        self._progress_popup_bar = None

        # ═══════════════════════════════════════════════════════════
        # 1.5 진행 상태 (미리보기 위에 고정 — 진행/데이터 혼동 방지)
        # ═══════════════════════════════════════════════════════════
        _pop_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        progress_section = ttk.LabelFrame(main, text="⏱ 진행 상태", padding=8)
        progress_section.pack(fill=X, pady=(6, 4))
        self._progress_inline_placeholder = ttk.Label(
            progress_section, text="파싱을 시작하면 진행 상황이 여기에 표시됩니다.",
            font=('맑은 고딕', 11), foreground=ThemeColors.get('text_muted', _pop_dark))
        self._progress_inline_placeholder.pack(anchor='w')
        self._progress_inline_frame = ttk.Frame(progress_section)
        # 아래에서 pack하지 않음 — 파싱 시작 시 pack, 완료 후 forget
        self._progress_inline_msg = ttk.Label(self._progress_inline_frame, text="", font=('맑은 고딕', 12, 'bold'))
        self._progress_inline_msg.pack(anchor='w')
        _ps = ttk.Style()
        _ps.configure('Inline.Horizontal.TProgressbar', troughcolor=ThemeColors.get('bg_secondary', _pop_dark), thickness=12)
        self._progress_bar_container = ttk.Frame(self._progress_inline_frame)
        self._progress_bar_container.pack(fill=X, pady=(4, 2))
        self._progress_inline_bar = ttk.Progressbar(self._progress_bar_container, maximum=100, mode='determinate', style='Inline.Horizontal.TProgressbar')
        self._progress_inline_bar.pack(fill=X)
        self._progress_inline_busy = ttk.Label(self._progress_bar_container, text="진행 중 ●", font=('맑은 고딕', 10),
                                               foreground=ThemeColors.get('statusbar_icon_warn', _pop_dark))
        self._progress_inline_busy.place(relx=0, rely=0.5, anchor='w')
        _row2 = ttk.Frame(self._progress_inline_frame)
        _row2.pack(fill=X)
        self._progress_inline_pct_elapsed = ttk.Label(_row2, text="", font=('맑은 고딕', 10), foreground=ThemeColors.get('text_secondary', _pop_dark))
        self._progress_inline_pct_elapsed.pack(side=tk.RIGHT)

        # ═══════════════════════════════════════════════════════════
        # 2. 미리보기 테이블 (v5.9.9: 폰트 20% 축소 — 14pt→11pt, 13pt→10pt)
        # ═══════════════════════════════════════════════════════════
        # v5.7.5: "업로드 2" 삭제 — "(확인 후 업로드)" 문구 제거
        tree_frame = ttk.LabelFrame(main, text="📊 미리보기 (스케일링·처리된 데이터)", padding=4)
        tree_frame.pack(fill=BOTH, expand=YES, pady=(0, 3))

        import tkinter.font as tkfont
        preview_font = tkfont.Font(family='맑은 고딕', size=11)
        heading_font = tkfont.Font(family='맑은 고딕', size=10, weight='bold')
        row_height = preview_font.metrics('linespace') + 6

        _tree_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        _tree_fg = ThemeColors.get('text_primary', _tree_dark)
        style = ttk.Style()
        style.configure('Preview.Treeview',
                        font=('맑은 고딕', 11),
                        rowheight=row_height,
                        foreground=_tree_fg,
                        fieldbackground=ThemeColors.get('bg_card', _tree_dark))
        style.configure('Preview.Treeview.Heading',
                        font=('맑은 고딕', 10, 'bold'))

        columns = tuple(col[0] for col in PREVIEW_COLUMNS)
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            height=18, selectmode='extended',
            style='Preview.Treeview'
        )
        self.tree.tag_configure('odd', background=ThemeColors.get('tree_stripe', _tree_dark), foreground=_tree_fg)
        self.tree.tag_configure('even', background=ThemeColors.get('bg_card', _tree_dark), foreground=_tree_fg)
        self.tree.tag_configure('edited', background=ThemeColors.get('warning', _tree_dark), foreground=_tree_fg)
        # v6.2.1: 크로스 체크 결과 하이라이트 태그
        self.tree.tag_configure('xc_critical', background='#FFCDD2', foreground='#B71C1C')   # 빨강 (심각)
        self.tree.tag_configure('xc_warning', background='#FFE0B2', foreground='#E65100')     # 주황 (주의)
        self.tree.tag_configure('xc_info', background='#FFF9C4', foreground='#F57F17')        # 노랑 (참고)

        for col_id, header, width, anchor in PREVIEW_COLUMNS:
            self.tree.heading(col_id, text=header, command=lambda c=col_id: self._toggle_preview_sort(c))
            self.tree.column(col_id, width=width, anchor=anchor, minwidth=35)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        scrollbar_x.pack(side=BOTTOM, fill=X)
        self.tree.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar_y.pack(side=RIGHT, fill=Y)
        self._setup_preview_edit_bindings()

        # v5.8.9: 컨테이너 번호 접미사(-숫자) 표시 옵션
        self._var_show_container_suffix = tk.BooleanVar(value=False)
        chk_container = ttk.Checkbutton(
            tree_frame, text="컨테이너 번호 접미사(-숫자) 표시",
            variable=self._var_show_container_suffix,
            command=self._on_toggle_container_suffix
        )
        chk_container.pack(anchor='w', padx=4, pady=(2, 0))

        # 컬럼 필터 바(콤보 목록 검색)
        self.filter_bar = HeaderFilterBar(
            main, self.tree,
            filter_columns=[
                ('sap_no', 'SAP', 120),
                ('bl_no', 'BL', 120),
                ('container_no', 'CONTAINER', 120),
                ('product', 'PRODUCT', 140),
                ('status', 'STATUS', 90),
            ],
            on_filter=self._on_change_preview_filter,
            is_dark=_tree_dark
        )
        self.filter_bar.pack(fill=X, pady=(2, 2))

        # ═══════════════════════════════════════════════════════════
        # 4. 하단 한 줄 — 업로드5: 폰트 통일(15), 업로드6: 합계 가운데 배치
        # [엑셀][DB 업로드]  (합계: ... 가운데)  [취소]
        # ═══════════════════════════════════════════════════════════
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=X, pady=(8, 0))

        _font = getattr(self, '_toolbar_font', '맑은 고딕') if hasattr(self, '_toolbar_font') else '맑은 고딕'
        _btn_font_size = 15
        _btn_fg = ThemeColors.get('badge_text', _tree_dark)
        _blue = ThemeColors.get('info', _tree_dark)
        _red = ThemeColors.get('statusbar_icon_err', _tree_dark)

        self.btn_excel = tk.Button(
            btn_frame, text="📥 Excel 내보내기",
            command=self._export_to_excel, state='disabled',
            font=(_font, _btn_font_size, 'bold'), bg=_blue, fg=_btn_fg,
            padx=15, pady=6, cursor='hand2', bd=0
        )
        self.btn_excel.pack(side=LEFT, padx=(0, 5))

        self.btn_undo = tk.Button(
            btn_frame, text="↶ 되돌리기",
            command=self._undo_preview_edit, state='disabled',
            font=(_font, 11, 'bold'), bg=ThemeColors.get('btn_neutral', _tree_dark), fg=_btn_fg,
            padx=10, pady=6, cursor='hand2', bd=0
        )
        self.btn_undo.pack(side=LEFT, padx=(5, 0))
        self.btn_redo = tk.Button(
            btn_frame, text="↷ 다시실행",
            command=self._redo_preview_edit, state='disabled',
            font=(_font, 11, 'bold'), bg=ThemeColors.get('btn_neutral', _tree_dark), fg=_btn_fg,
            padx=10, pady=6, cursor='hand2', bd=0
        )
        self.btn_redo.pack(side=LEFT, padx=(5, 0))

        self.btn_reset_original = tk.Button(
            btn_frame, text="⟲ 원본 초기화",
            command=self._reset_preview_to_original, state='disabled',
            font=(_font, 11, 'bold'), bg=ThemeColors.get('btn_neutral', _tree_dark), fg=_btn_fg,
            padx=10, pady=6, cursor='hand2', bd=0
        )
        self.btn_reset_original.pack(side=LEFT, padx=(5, 0))

        self._var_upload_by_view_order = tk.BooleanVar(value=False)
        chk_upload_order = ttk.Checkbutton(
            btn_frame,
            text="DB 업로드 시 현재 정렬/필터 순서 적용",
            variable=self._var_upload_by_view_order
        )
        chk_upload_order.pack(side=LEFT, padx=(8, 0))

        self.btn_upload = tk.Button(
            btn_frame, text="📤 DB 업로드",
            command=self._on_upload, state='disabled',
            font=(_font, _btn_font_size, 'bold'), bg=_blue, fg=_btn_fg,
            padx=20, pady=8, cursor='hand2', bd=0
        )
        self.btn_upload.pack(side=LEFT, padx=(5, 0))
        self._attach_doc_tooltip(self.btn_upload,
            "미리보기 데이터를 DB에 저장합니다\n\n• 저장 후 재고리스트에 자동 반영\n• 중복 LOT는 자동 스킵\n• 저장 완료 후 재고리스트 화면 표시")

        self.summary_var = tk.StringVar(value="")
        _summary_lbl = ttk.Label(btn_frame, textvariable=self.summary_var,
                                font=('맑은 고딕', 13, 'bold'),
                                foreground=ThemeColors.get('statusbar_progress', _tree_dark))
        _summary_lbl.pack(side=LEFT, fill=X, expand=True, padx=10)

        tk.Button(
            btn_frame, text="❌ 취소",
            command=self._on_cancel,
            font=(_font, _btn_font_size, 'bold'), bg=_red, fg=_btn_fg,
            padx=20, pady=8, cursor='hand2', bd=0
        ).pack(side=RIGHT, padx=(5, 0))

    # ═══════════════════════════════════════════════════════════
    # 파일 선택
    # ═══════════════════════════════════════════════════════════

    def _update_parse_hint(self) -> None:
        """파싱 시작 옆 업로드 상태 문구 갱신: 총 4개 중 N개 업로드되었습니다."""
        n = len(self.file_paths)
        if not getattr(self, 'parse_hint', None):
            return
        _hint_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        if 'PACKING_LIST' not in self.file_paths:
            self.parse_hint.config(
                text="💡 최소 Packing List를 선택하세요",
                foreground=ThemeColors.get('text_muted', _hint_dark)
            )
            if self.btn_parse:
                self.btn_parse.config(state='disabled')
        else:
            if self.btn_parse:
                self.btn_parse.config(state='normal')
            self.parse_hint.config(
                text=f"총 4개 중 {n}개 업로드되었습니다.",
                foreground=ThemeColors.get('text_primary', _hint_dark)
            )

    def _select_file(self, doc_type: str):
        """서류별 파일 선택"""
        type_names = {
            'PACKING_LIST': 'Packing List',
            'INVOICE': 'Invoice, FA',
            'BL': 'Bill of Loading',
            'DO': 'Delivery Order',
        }

        file_path = filedialog.askopenfilename(
            parent=self.dialog,
            title=f"{type_names.get(doc_type, doc_type)} 파일 선택",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("Image (D/O 캡처)", "*.png *.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            return

        self.file_paths[doc_type] = file_path
        fname = os.path.basename(file_path)

        # UI 업데이트
        self.file_labels[doc_type].config(text=fname, foreground=ThemeColors.get('text_primary', ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))))
        self.check_labels[doc_type].config(text="✅")

        self._log(f"📂 {doc_type}: {fname}")

        # 파싱 버튼 활성화 조건: PL 필수
        self._update_parse_hint()

    # ═══════════════════════════════════════════════════════════
    # 파싱
    # ═══════════════════════════════════════════════════════════

    def _start_parsing(self) -> None:
        """v3.8.9: 파싱 시작 — 입고 서류 현황 안내 후 진행 확인"""
        # 들어온 서류 / 빠진 서류 분류
        received = []
        missing = []
        do_missing = False
        short_names = {
            'PACKING_LIST': 'Packing List',
            'INVOICE': 'Invoice, FA',
            'BL': 'Bill of Loading',
            'DO': 'Delivery Order',
        }
        for doc_type, _doc_name, _required in DOC_TYPES:
            name = short_names.get(doc_type, doc_type)
            if doc_type in self.file_paths:
                received.append(name)
            else:
                missing.append(name)
                if doc_type == 'DO':
                    do_missing = True

        # 메시지 구성: 들어온 서류 / 빠진 서류 / D/O 안내 / 진행할까요?
        lines = []
        if received:
            lines.append(f"✅ 들어온 서류: {', '.join(received)}")
        if missing:
            lines.append(f"⚠️ 빠진 서류: {', '.join(missing)}")
        if do_missing:
            lines.append("\n📋 D/O가 빠진 경우에는 입항일 혹은 프리타임을 반드시 입력해야 합니다.")
        lines.append("\n진행할까요?")
        msg = "\n".join(lines)

        from ..utils.custom_messagebox import CustomMessageBox
        proceed = CustomMessageBox.askyesno(
            self.dialog,
            "입고 서류 확인",
            msg
        )
        if not proceed:
            return

        if missing:
            self._update_progress(0, f"ℹ️ {', '.join(missing)} 미선택 — 해당 정보 생략")

        self.btn_parse.config(state='disabled')
        self._show_progress_inline()

        thread = threading.Thread(
            target=self._parse_thread,
            daemon=True
        )
        thread.start()

    def _show_progress_inline(self) -> None:
        """진행 상태를 미리보기 위 인라인 영역에만 표시 (팝업 없음, 움직임 표시 포함)"""
        ph = getattr(self, '_progress_inline_placeholder', None)
        fr = getattr(self, '_progress_inline_frame', None)
        if ph and ph.winfo_ismapped():
            ph.pack_forget()
        if fr:
            fr.pack(fill=X)
        self._progress_start_time = time.time()
        if getattr(self, '_progress_inline_bar', None):
            self._progress_inline_bar['value'] = 0
        if getattr(self, '_progress_inline_msg', None):
            self._progress_inline_msg.config(text="준비 중...")
        if getattr(self, '_progress_inline_pct_elapsed', None):
            self._progress_inline_pct_elapsed.config(text="0%  ·  경과: 0:00")
        if getattr(self, '_progress_inline_busy', None):
            self._progress_inline_busy.config(text="진행 중 ●")
            self._progress_inline_busy.place(relx=0, rely=0.5, anchor='w')
        self._start_progress_elapsed_tick()
        self._start_progress_busy_animation()

    def _hide_progress_inline(self) -> None:
        """진행 완료 후 인라인 영역을 플레이스홀더로 복귀"""
        fr = getattr(self, '_progress_inline_frame', None)
        ph = getattr(self, '_progress_inline_placeholder', None)
        if fr and fr.winfo_ismapped():
            fr.pack_forget()
        if ph:
            ph.pack(anchor='w')

    def _show_progress_popup(self) -> None:
        """작업진행 전용 창 사용 안 함 — 기존 화면(인라인 진행 상태)만 사용"""
        pass

    def _progress_elapsed_tick(self) -> None:
        """경과 시간 표시 업데이트 (1초 간격) — 팝업·인라인 둘 다"""
        start = getattr(self, '_progress_start_time', None)
        if start is None:
            self._progress_elapsed_job = self.dialog.after(1000, self._progress_elapsed_tick) if self.dialog and self.dialog.winfo_exists() else None
            return
        secs = int(time.time() - start)
        if secs >= 3600:
            h, r = divmod(secs, 3600)
            m, s = divmod(r, 60)
            elapsed_text = f"경과: {h}:{m:02d}:{s:02d}"
        else:
            m, s = divmod(secs, 60)
            elapsed_text = f"경과: {m}:{s:02d}"
        # 인라인 경과 (현재 퍼센트 + 경과)
        pct_elapsed = getattr(self, '_progress_inline_pct_elapsed', None)
        if pct_elapsed and pct_elapsed.winfo_ismapped():
            pct = getattr(self, 'progress_var', None)
            pct_val = int(pct.get()) if pct else 0
            pct_elapsed.config(text=f"{pct_val}%  ·  {elapsed_text}")
        self._progress_elapsed_job = self.dialog.after(1000, self._progress_elapsed_tick) if self.dialog and self.dialog.winfo_exists() else None

    def _start_progress_elapsed_tick(self) -> None:
        """경과 시간 타이머 시작"""
        self._progress_elapsed_job = None
        if self.dialog and self.dialog.winfo_exists():
            self._progress_elapsed_job = self.dialog.after(1000, self._progress_elapsed_tick)

    def _stop_progress_elapsed_tick(self) -> None:
        """경과 시간 타이머 중지"""
        if getattr(self, '_progress_elapsed_job', None):
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after_cancel(self._progress_elapsed_job)
            except (tk.TclError, ValueError) as e:
                logger.debug(f"Suppressed: {e}")
        self._progress_elapsed_job = None

    def _progress_busy_tick(self) -> None:
        """진행 중 움직임 표시 — 기존 화면(인라인) 진행 상태 영역에만 표시"""
        phase = getattr(self, '_progress_busy_phase', 0) % 4
        self._progress_busy_phase = phase + 1
        texts = ['진행 중 ●  ', '진행 중 ●● ', '진행 중 ●●●', '진행 중 ●● ']
        inline_busy = getattr(self, '_progress_inline_busy', None)
        if inline_busy and inline_busy.winfo_ismapped():
            inline_busy.config(text=texts[phase])
        self._progress_busy_job = self.dialog.after(400, self._progress_busy_tick) if self.dialog and self.dialog.winfo_exists() else None

    def _start_progress_busy_animation(self) -> None:
        self._progress_busy_phase = 0
        if self.dialog and self.dialog.winfo_exists():
            self._progress_busy_job = self.dialog.after(400, self._progress_busy_tick)

    def _stop_progress_busy_animation(self) -> None:
        if getattr(self, '_progress_busy_job', None):
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after_cancel(self._progress_busy_job)
            except (tk.TclError, ValueError):
                pass
        self._progress_busy_job = None

    def _hide_progress_popup(self) -> None:
        """진행률 팝업 닫기"""
        self._stop_progress_busy_animation()
        self._stop_progress_elapsed_tick()
        try:
            if getattr(self, '_progress_popup', None) and self._progress_popup.winfo_exists():
                self._progress_popup.destroy()
        except Exception as e:
            logger.debug(f"Suppressed: {e}")
        self._progress_popup = None
        self._progress_popup_label = None
        self._progress_popup_bar = None
        self._progress_popup_pct = None
        self._progress_popup_busy = None
        self._progress_popup_elapsed = None

    def _update_progress(self, pct: int, message: str):
        """프로그레스 바 업데이트 (스레드 안전) — 팝업 + 인라인 동기화, 로그 탭에도 기록"""
        def _update():
            self.progress_var.set(pct)
            self.status_var.set(message)
            if message.strip() and getattr(self, '_log', None):
                try:
                    self._log(message)
                except (RuntimeError, ValueError):
                    logger.info(message)
            # 팝업
            bar = getattr(self, '_progress_popup_bar', None)
            if bar and bar.winfo_exists():
                bar['value'] = max(0, min(100, pct))
                if self._progress_popup_label:
                    self._progress_popup_label.config(text=message)
                if getattr(self, '_progress_popup_pct', None):
                    self._progress_popup_pct.config(text=f"{pct}%" if pct >= 0 else "—")
            # 인라인 (미리보기 위) — 기존 화면 프로그레스 바만 사용
            inline_bar = getattr(self, '_progress_inline_bar', None)
            inline_msg = getattr(self, '_progress_inline_msg', None)
            inline_busy = getattr(self, '_progress_inline_busy', None)
            if inline_bar and inline_bar.winfo_ismapped():
                inline_bar['value'] = max(0, min(100, pct))
            if inline_busy and inline_busy.winfo_ismapped():
                relx = max(0, min(1.0, pct / 100.0))
                if relx > 0.92:
                    relx = 0.92
                inline_busy.place(relx=relx, rely=0.5, anchor='w')
            if inline_msg and inline_msg.winfo_ismapped():
                inline_msg.config(text=message)
            if pct >= 100 or (pct == 0 and message.strip().startswith("❌")):
                self._stop_progress_busy_animation()
                if inline_busy and inline_busy.winfo_ismapped():
                    inline_busy.config(text="완료" if pct >= 100 else "오류")
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(PROGRESS_POPUP_CLOSE_DELAY_MS, self._hide_progress_popup)
                self.dialog.after(PROGRESS_POPUP_CLOSE_DELAY_MS + 100, self._hide_progress_inline)
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, _update)

    def _parse_thread(self) -> None:
        """백그라운드 파싱"""
        try:
            from parsers.document_parser_v2 import DocumentParserV2

            gemini_key = os.environ.get('GEMINI_API_KEY', '')
            if not gemini_key:
                try:
                    from core.config import get_settings
                    settings = get_settings()
                    gemini_key = settings.get('gemini_api_key', '')
                except (ImportError, ModuleNotFoundError) as _e:
                    logger.debug(f"onestop_inbound: {_e}")

            # v5.5.1: 모든 파싱은 API(Gemini) 강제
            if not gemini_key or str(gemini_key).strip() == '' or str(gemini_key).startswith('your-'):
                raise RuntimeError("API-only 모드: Gemini API Key가 필요합니다. 설정에서 API Key를 입력하세요.")

            parser = DocumentParserV2(gemini_api_key=gemini_key)

            # 파싱 순서: PL → Invoice → BL → DO
            parse_order = ['PACKING_LIST', 'INVOICE', 'BL', 'DO']
            to_parse = [(dt, self.file_paths[dt]) for dt in parse_order if dt in self.file_paths]
            total = len(to_parse)
            if total == 0:
                self._update_progress(90, "파싱할 파일이 없습니다")
                return

            icons = {'PACKING_LIST': '📦', 'INVOICE': '📑', 'BL': '🚢', 'DO': '📋'}

            pl_result = None
            inv_result = None
            bl_result = None
            do_result = None

            # v5.7.5: 현재 파싱 중인 서류 이름 표시
            doc_type_display = {
                'PACKING_LIST': 'Packing List',
                'INVOICE': 'Invoice, FA',
                'BL': 'Bill of Loading',
                'DO': 'Delivery Order',
            }
            for idx, (doc_type, file_path) in enumerate(to_parse):
                fname = os.path.basename(file_path)
                icon = icons.get(doc_type, '📄')
                pct = int(10 + 70 * idx / total)
                doc_name = doc_type_display.get(doc_type, doc_type)
                self._update_progress(pct, f"현재 파싱 중: {doc_name} — {fname}")
                self._log_safe(f"{icon} {doc_type} 파싱: {fname}")

                try:
                    if doc_type == 'PACKING_LIST':
                        pl_result = parser.parse_packing_list(file_path)
                        self.parsed_results['packing_list'] = pl_result
                        _lots = getattr(pl_result, 'lots', []) if pl_result else []
                        if _lots:
                            _tnw = getattr(pl_result, 'total_net_weight_kg', 0) or 0
                            self._log_safe(f"  ✅ LOTs: {len(_lots)}, Net: {_tnw:,.0f}kg")
                            # v6.2.1: 중복 행 자동 제거 알림
                            _dup_cnt = getattr(pl_result, 'duplicates_removed', 0) or 0
                            if _dup_cnt > 0:
                                self._log_safe(f"  ⚠️ Gemini 응답에서 중복 행 {_dup_cnt}건 자동 제거됨")

                    elif doc_type == 'INVOICE':
                        inv_result = parser.parse_invoice(file_path)
                        self.parsed_results['invoice'] = inv_result
                        if inv_result:
                            self._log_safe(f"  ✅ SAP: {getattr(inv_result, 'sap_no', '')}, Invoice: {getattr(inv_result, 'salar_invoice_no', '')}")

                    elif doc_type == 'BL':
                        bl_result = parser.parse_bl(file_path)
                        self.parsed_results['bl'] = bl_result
                        if bl_result:
                            self._log_safe(f"  ✅ B/L: {getattr(bl_result, 'bl_no', '')}, Containers: {getattr(bl_result, 'total_containers', 0)}")

                    elif doc_type == 'DO':
                        do_result = parser.parse_do(file_path)
                        self.parsed_results['do'] = do_result
                        if do_result:
                            self._log_safe(f"  ✅ D/O: B/L={getattr(do_result, 'bl_no', '')}")

                except (ValueError, TypeError, AttributeError, RuntimeError) as e:
                    self._log_safe(f"  ❌ {doc_type} 파싱 오류: {e}")
                    logger.error(f"파싱 오류 [{doc_type}]: {e}", exc_info=True)
                    # RuntimeError: Gemini API-Only 실패(예: JSON 추출 실패) → 입고 미완료 → 재고/톤백 리스트에 데이터 없음
                    if isinstance(e, RuntimeError) and doc_type == 'PACKING_LIST':
                        self._log_safe("  💡 Packing List 실패 시 입고가 완료되지 않아 톤백 리스트에 표시되지 않습니다.")
                else:
                    # 서류 하나 파싱 직후마다 병합 후 미리보기 테이블·메인 화면에 실시간 반영
                    self._merge_results(inv_result, pl_result, bl_result, do_result)
                    if self.dialog and self.dialog.winfo_exists():
                        self.dialog.after(0, lambda: self._push_preview_to_main())
                        self.dialog.after(0, lambda: self._refresh_preview_tree_only())

            # 병합
            self._update_progress(85, "📊 데이터 병합 중...")
            self._merge_results(inv_result, pl_result, bl_result, do_result)

            # ═══════════════════════════════════════════════════════
            # ★★★ v5.8.7: D/O 없거나 arrival_date 누락 시 사용자 입력
            # ═══════════════════════════════════════════════════════
            self._do_deferred = False  # D/O 추후 첨부 플래그
            _need_date_input = False
            if not do_result:
                _need_date_input = True
                self._log_safe("📋 D/O 미첨부 — 날짜 정보 수동 입력 필요")
            elif self.preview_data and not (self.preview_data[0].get('arrival_date') or '').strip():
                _need_date_input = True
                self._log_safe("📋 D/O에서 입항일 추출 실패 — 수동 입력 필요")

            if _need_date_input and self.preview_data:
                prefilled_ship = ''
                if self.preview_data:
                    prefilled_ship = self.preview_data[0].get('ship_date', '') or ''

                import queue
                date_queue = queue.Queue()

                def _show_date_popup():
                    self._hide_progress_popup()
                    result = self._ask_missing_dates(prefilled_ship, do_result)
                    date_queue.put(result)

                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(0, _show_date_popup)
                    try:
                        user_dates = date_queue.get(timeout=300)
                    except queue.Empty:
                        user_dates = None

                    if user_dates:
                        if user_dates.get('deferred'):
                            # "D/O 추후 첨부" 선택
                            self._do_deferred = True
                            self._log_safe("  📋 D/O 추후 첨부 선택됨 — arrival_date 없이 진행")
                        else:
                            for row in self.preview_data:
                                if user_dates.get('ship_date') and not (row.get('ship_date') or '').strip():
                                    row['ship_date'] = user_dates['ship_date']
                                if user_dates.get('arrival_date'):
                                    row['arrival_date'] = user_dates['arrival_date']
                                # con_return은 입항일/반납일/Free time 중 하나 입력 시 항상 계산되어 반환됨 — 반드시 적용
                                if 'con_return' in user_dates:
                                    row['con_return'] = user_dates.get('con_return', '') or ''
                                if user_dates.get('free_time') is not None:
                                    row['free_time'] = str(user_dates.get('free_time', ''))
                            self._log_safe(f"  ✅ 수동 입력: arrival={user_dates.get('arrival_date')}, con_return={user_dates.get('con_return')}, free_time={user_dates.get('free_time')}")
                    else:
                        self._log_safe("  ⚠️ 날짜 입력 취소 — arrival_date 없이 진행")

            # v3.8.9: 파싱 결과 경고 (누락된 정보)
            _warnings = []
            if not pl_result or not getattr(pl_result, 'lots', None):
                _warnings.append("⚠️ Packing List: LOT 정보 추출 실패")
            if not inv_result or not getattr(inv_result, 'sap_no', None):
                _warnings.append("⚠️ Invoice: SAP번호 추출 실패 — 수동 입력 필요")
            if not bl_result or not getattr(bl_result, 'bl_no', None):
                _warnings.append("⚠️ B/L: BL번호 추출 실패 — 수동 입력 필요")

            # ═══════════════════════════════════════════════════════
            # v6.2.1: 4종 서류 크로스 체크 엔진
            # ※ B/L 파싱·SHIP DATE 파싱 로직은 변경하지 않음 (읽기 전용 검증)
            # ═══════════════════════════════════════════════════════
            self._cross_check_result = None
            try:
                from parsers.cross_check_engine import CheckLevel, cross_check_documents
                xc = cross_check_documents(
                    invoice=inv_result,
                    packing_list=pl_result,
                    bl=bl_result,
                    do=do_result,
                )
                self._cross_check_result = xc

                if not xc.is_clean:
                    self._log_safe(f"\n{'='*40}")
                    self._log_safe(f"🔍 {xc.summary}")
                    for item in xc.items:
                        self._log_safe(f"  {item}")
                    self._log_safe(f"{'='*40}")

                    # 크로스 체크 경고를 _warnings에 병합
                    for item in xc.items:
                        _warnings.append(str(item))

                    # CRITICAL 있으면 서류 확인 권장 메시지 추가
                    if xc.has_critical:
                        _warnings.insert(0,
                            f"🚫 심각한 불일치 {xc.critical_count}건 — "
                            "서류 확인 후 재파싱 권장"
                        )
                else:
                    self._log_safe("✅ 4종 서류 크로스 체크 통과 — 불일치 없음")
            except (ImportError, Exception) as e:
                logger.debug(f"[CrossCheck] 원스톱 크로스 체크 스킵: {e}")

            if _warnings:
                _warn_msg = "\n".join(_warnings)
                self._log_safe(f"\n{'='*40}\n{_warn_msg}\n{'='*40}")
                # GUI 경고
                def _show_warn():
                    from ..utils.custom_messagebox import CustomMessageBox
                    CustomMessageBox.warning(None, "파싱 결과 확인", _warn_msg, parent=self.dialog)
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(500, _show_warn)

            # 병합 직후 메인 화면 재고 리스트에 실시간 반영
            if self.dialog and self.dialog.winfo_exists() and self.preview_data:
                self.dialog.after(0, lambda: self._push_preview_to_main())

            # 파싱 직후 원본 스냅샷(원본 초기화 기준점)
            self._capture_original_preview_state()
            self._sort_col = None
            self._sort_desc = False
            self._update_sort_headings()
            self._update_filter_values_from_preview()
            if self.btn_reset_original and self.btn_reset_original.winfo_exists():
                self.btn_reset_original.config(state='normal' if self._original_preview_data else 'disabled')

            # 표시
            self._update_progress(95, "📋 미리보기 준비...")
            self._display_preview()
            # 파싱 완료 후 DB 업로드·Excel 버튼이 반드시 보이도록 폴백 (순차 삽입 완료 전에도 활성화)
            _preview_len = len(self.preview_data)
            def _ensure_buttons_visible():
                if not self.dialog or not self.dialog.winfo_exists():
                    return
                if _preview_len and getattr(self, 'preview_data', None) and len(self.preview_data) == _preview_len:
                    if getattr(self, 'btn_excel', None) and self.btn_excel.winfo_exists():
                        self.btn_excel.config(state='normal')
                    if getattr(self, 'btn_upload', None) and self.btn_upload.winfo_exists():
                        if self._has_required_docs():
                            self.btn_upload.config(state='normal')
                        else:
                            self.btn_upload.config(state='disabled')
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(400, _ensure_buttons_visible)

            elapsed_sec = time.time() - getattr(self, '_progress_start_time', time.time())
            elapsed_str = f"{elapsed_sec:.1f}초" if elapsed_sec < 60 else f"{int(elapsed_sec // 60)}분 {elapsed_sec % 60:.0f}초"
            self._update_progress(100, f"✅ 파싱 완료 — {len(self.preview_data)}개 LOT ({elapsed_str})")
            self._log_safe(f"✅ 파싱 완료: {len(self.preview_data)} LOT, {total}종 서류 (경과: {elapsed_str})")

        except (RuntimeError, ValueError) as e:
            self._update_progress(0, f"❌ 오류: {e}")
            self._log_safe(f"❌ 파싱 오류: {e}")
            logger.error(f"원스톱 파싱 오류: {e}", exc_info=True)
            self._enable_parse_btn()

    # ═══════════════════════════════════════════════════════════
    # 데이터 병합 (4종 → 18열)
    # ═══════════════════════════════════════════════════════════

    def _merge_results(self, invoice, pl, bl, do) -> list:
        """4종 파싱 결과를 18열 미리보기 데이터로 병합"""
        self.preview_data = []
        self._edited_rows = set()
        self._undo_stack = []
        self._redo_stack = []
        self._update_undo_redo_buttons()

        if not pl or not getattr(pl, 'lots', None):
            if invoice and getattr(invoice, 'lot_numbers', None):
                for idx, lot_no in enumerate(getattr(invoice, 'lot_numbers', []), 1):
                    row = self._empty_row(idx)
                    row['sap_no'] = getattr(invoice, 'sap_no', '') or ''
                    row['lot_no'] = lot_no
                    row['product'] = getattr(invoice, 'product', '') or 'LITHIUM CARBONATE'
                    row['salar_invoice_no'] = getattr(invoice, 'salar_invoice_no', '') or ''
                    row['ship_date'] = str(getattr(invoice, 'invoice_date', '')) if getattr(invoice, 'invoice_date', None) else ''
                    if bl:
                        row['bl_no'] = self._format_bl(getattr(bl, 'bl_no', '') or '')
                    self._fill_do(row, do)
                    row['status'] = 'AVAILABLE'
                    self.preview_data.append(row)
            elif do and getattr(self.engine, 'db', None):
                # D/O만 있는 경우: DB에서 기존 LOT(B/L 기준) 자동 조회해 미리보기 구성
                try:
                    do_bl_raw = str(getattr(do, 'bl_no', '') or '').strip()
                    do_bl_fmt = self._format_bl(do_bl_raw)
                    candidates = [x for x in {do_bl_raw, do_bl_fmt} if x]
                    db_rows = []
                    for c in candidates:
                        rows = self.engine.db.fetchall(
                            "SELECT * FROM inventory WHERE bl_no = ? ORDER BY lot_no",
                            (c,)
                        ) or []
                        if rows:
                            db_rows = rows
                            break
                    for idx, rec in enumerate(db_rows, 1):
                        row = self._empty_row(idx)
                        row['sap_no'] = str(rec.get('sap_no', '') or '')
                        row['bl_no'] = str(rec.get('bl_no', '') or do_bl_fmt or do_bl_raw or '')
                        row['container_no'] = str(rec.get('container_no', '') or '')
                        row['product'] = str(rec.get('product', '') or 'LITHIUM CARBONATE')
                        row['product_code'] = str(rec.get('product_code', '') or '')
                        row['lot_no'] = str(rec.get('lot_no', '') or '')
                        row['lot_sqm'] = str(rec.get('lot_sqm', '') or '')
                        row['mxbg_pallet'] = str(rec.get('mxbg_pallet', '') or '10')
                        _nw = rec.get('net_weight', '')
                        _gw = rec.get('gross_weight', '')
                        row['net_weight'] = f"{float(_nw):,.1f}" if str(_nw) not in ('', 'None', 'none') else ''
                        row['gross_weight'] = f"{float(_gw):,.3f}" if str(_gw) not in ('', 'None', 'none') else ''
                        row['salar_invoice_no'] = str(rec.get('salar_invoice_no', '') or '')
                        row['ship_date'] = str(rec.get('ship_date', '') or '')[:10]
                        row['arrival_date'] = str(rec.get('arrival_date', '') or '')[:10]
                        row['con_return'] = str(rec.get('con_return', '') or '')[:10]
                        row['free_time'] = str(rec.get('free_time', '') or '')
                        row['warehouse'] = str(rec.get('warehouse', '') or DEFAULT_WAREHOUSE)
                        row['status'] = str(rec.get('status', '') or 'AVAILABLE')
                        self._fill_do(row, do)
                        self.preview_data.append(row)
                    if self.preview_data:
                        self._log_safe(f"📎 D/O 기반 DB 자동매칭: {len(self.preview_data)}건 (B/L 기준)")
                except Exception as e:
                    logger.debug(f"D/O 단독 DB 자동매칭 실패: {e}")
            return

        _lots = list(getattr(pl, 'lots', []) or [])
        _lots_sorted = sorted(
            enumerate(_lots, 1),
            key=lambda p: self._lot_order_key(p[1], p[0])
        )
        for idx, (_src, lot) in enumerate(_lots_sorted, 1):
            row = self._empty_row(idx)
            row['sap_no'] = getattr(pl, 'sap_no', '') or (getattr(invoice, 'sap_no', '') if invoice else '') or ''
            row['container_no'] = getattr(lot, 'container_no', '') or ''
            row['product'] = getattr(pl, 'product', '') or 'LITHIUM CARBONATE'
            row['product_code'] = getattr(pl, 'code', '') or ''
            row['lot_no'] = getattr(lot, 'lot_no', '') or ''
            row['lot_sqm'] = getattr(lot, 'lot_sqm', '') or ''

            _mxbg = getattr(lot, 'mxbg_pallet', None)
            row['mxbg_pallet'] = str(_mxbg) if _mxbg else '10'

            _nw = getattr(lot, 'net_weight_kg', None)
            row['net_weight'] = f"{float(_nw):,.1f}" if _nw else ''

            _gw = getattr(lot, 'gross_weight_kg', None)
            row['gross_weight'] = f"{float(_gw):,.3f}" if _gw else ''

            # v3.8.8: B/L ship_date 우선, Invoice 폴백 — 업로드3/4: 파싱값으로 채움 (날짜는 YYYY-MM-DD)
            if bl:
                row['bl_no'] = self._format_bl(getattr(bl, 'bl_no', '') or '')
                _sd = getattr(bl, 'ship_date', None)
                if _sd:
                    row['ship_date'] = str(_sd)[:10] if len(str(_sd)) >= 10 else str(_sd)

            if invoice:
                row['salar_invoice_no'] = getattr(invoice, 'salar_invoice_no', '') or ''
                if not (row.get('ship_date') or '').strip():
                    _id = getattr(invoice, 'invoice_date', None)
                    if _id:
                        row['ship_date'] = str(_id)[:10] if len(str(_id)) >= 10 else str(_id)
                if not row['sap_no']:
                    row['sap_no'] = getattr(invoice, 'sap_no', '') or ''

            self._fill_do(row, do)
            if not (row.get('warehouse') or '').strip():
                row['warehouse'] = DEFAULT_WAREHOUSE
            row['status'] = 'AVAILABLE'
            self.preview_data.append(row)

    def _empty_row(self, no: int) -> dict:
        row = {col[0]: '' for col in PREVIEW_COLUMNS}
        row['no'] = str(no)
        return row

    def _date_str(self, val) -> str:
        """날짜를 YYYY-MM-DD 문자열로. None/'None'/비어있으면 '' 반환 (date.today() 사용 안 함)."""
        if val is None or (isinstance(val, str) and (not val.strip() or val.strip() in ('None', 'none'))):
            return ''
        if hasattr(val, 'isoformat'):
            return str(val.isoformat())[:10]
        s = str(val).strip()
        return s[:10] if len(s) >= 10 and s not in ('None', 'none') else (s if s and s not in ('None', 'none') else '')

    def _format_bl(self, bl_no) -> str:
        if not bl_no:
            return ''
        bl_no = str(bl_no).strip()
        if bl_no.isdigit() and len(bl_no) >= 9:
            return f"MAEU{bl_no}"
        return bl_no

    def _fill_do(self, row: dict, do) -> None:
        """v3.8.8: D/O 데이터로 미리보기 행 보완 (free_time 계산 포함)"""
        if not do:
            return
        if not row.get('bl_no') and getattr(do, 'bl_no', None):
            row['bl_no'] = str(getattr(do, 'bl_no', ''))

        # arrival_date (업로드3/4: D/O 파싱값으로 채움, YYYY-MM-DD)
        # v5.8.8: 날짜가 아닌 값(예: '광양')이면 넣지 않음 — ARRIVAL 컬럼 혼동 방지
        arr = getattr(do, 'arrival_date', None)
        if arr and str(arr) != 'None':
            _s = str(arr).strip()[:10]
            if len(_s) == 10 and _s.count('-') == 2 and _s.replace('-', '').isdigit():
                row['arrival_date'] = _s

        # warehouse
        wh = getattr(do, 'warehouse_name', '') or getattr(do, 'warehouse', '')
        if wh:
            row['warehouse'] = str(wh)

        # FREE TIME = con_return(컨테이너 반납일) - arrival_date (일수). D/O의 Free_Time 컬럼 = 반납일
        ft_infos = getattr(do, 'free_time_info', []) or []
        if ft_infos and arr and str(arr) != 'None':
            try:
                con_return_str = ''
                for ft in ft_infos:
                    ftd = (getattr(ft, 'free_time_date', '') or getattr(ft, 'free_time_until', '')) if not isinstance(ft, dict) else (ft.get('free_time_date') or ft.get('free_time_until') or '')
                    if ftd and str(ftd) != 'None':
                        con_return_str = str(ftd)[:10]
                        break
                if not con_return_str:
                    logger.debug(
                        "[원스톱 미리보기] D/O free_time_info 있으나 반납일 없음 — CON RETURN/FREE TIME 빈칸. 항목 수: %s",
                        len(ft_infos),
                    )
                if con_return_str:
                    con_return_dt = datetime.strptime(con_return_str, '%Y-%m-%d').date()
                    arr_dt = datetime.strptime(str(arr)[:10], '%Y-%m-%d').date()
                    days = (con_return_dt - arr_dt).days
                    row['free_time'] = str(max(0, days))
                    row['con_return'] = str(con_return_str)[:10]
                    logger.debug(
                        "[원스톱 미리보기] D/O 반납일 적용: con_return=%s, free_time(일수)=%s",
                        row['con_return'],
                        row['free_time'],
                    )
            except (ValueError, TypeError) as e:
                logging.getLogger(__name__).debug(f"free_time 계산 실패: {e}")
        # 업로드4: free_time 일수만 있는 경우 (DO.free_time.storage_free_days)
        if not (row.get('free_time') or '').strip():
            ft_single = getattr(do, 'free_time', None)
            if ft_single is not None:
                days_val = getattr(ft_single, 'storage_free_days', None) or (ft_single.get('storage_free_days') if isinstance(ft_single, dict) else None)
                if days_val is not None:
                    row['free_time'] = str(int(days_val))
                    # FREE TIME 일수만 있으면 반납일(con_return) = arrival_date + 일수 로 계산해 CON RETURN에도 표시
                    if not (row.get('con_return') or '').strip() and arr and str(arr) != 'None':
                        try:
                            arr_dt = datetime.strptime(str(arr)[:10], '%Y-%m-%d').date()
                            con_dt = arr_dt + timedelta(days=int(days_val))
                            row['con_return'] = con_dt.strftime('%Y-%m-%d')
                        except (ValueError, TypeError):
                            pass

    # ═══════════════════════════════════════════════════════════
    # ★★★ v5.8.7: 날짜 입력 팝업 (DatePicker 달력 UI)
    # ═══════════════════════════════════════════════════════════

    def _ask_missing_dates(self, prefilled_ship: str = '', do_result=None) -> dict:
        """
        사용자에게 입항일·반납기한·Free time을 물어보는 DatePicker 팝업.
        선적일(Ship Date)은 B/L에서 이미 추출되어 톤백 리스트에 있으므로 묻지 않음.
        
        호출 조건:
            1) D/O 자체가 없을 때
            2) D/O는 있는데 arrival_date 추출 실패 시
        
        UI:
            - 입항일(필수), 컨테이너 반납기한(con_return), Free time(일수).
            - 도착일·con_return·free time 중 하나만 입력해도 나머지 자동 계산. 반납일-입항일=Free time.
            - gui_bootstrap HAS_DATEENTRY면 달력, 없으면 텍스트 입력. "D/O 추후 첨부" 가능.
        
        Returns:
            dict: {'ship_date': str, 'arrival_date': str, 'con_return': str, 'free_time': str}
            또는 {'deferred': True} (D/O 추후 첨부)
            또는 None (취소)
        """
        result_holder = [None]

        def _build_popup():
            win = None
            try:
                win = tk.Toplevel(self.dialog)

                if not do_result:
                    win.title("📋 D/O 미첨부 — 날짜 정보 입력")
                    msg_text = "D/O가 없습니다. 입항일 등을 직접 입력하거나,\n나중에 D/O를 추가할 수 있습니다."
                else:
                    win.title("📋 D/O 파싱 실패 — 날짜 정보 입력")
                    msg_text = "D/O에서 날짜를 읽지 못했습니다.\n직접 입력하거나 나중에 D/O를 다시 첨부할 수 있습니다."

                win.geometry(DialogSize.get_geometry(self.dialog, 'medium'))
                apply_modal_window_options(win)
                win.transient(self.dialog)
                win.grab_set()
                center_dialog(win, self.dialog)

                frame = ttk.Frame(win, padding=20)
                frame.pack(fill=tk.BOTH, expand=True)

                # 안내 메시지
                ttk.Label(frame, text=msg_text,
                         font=('맑은 고딕', 11, 'bold'),
                         wraplength=460).pack(anchor='w', pady=(0, 12))

                # ── 날짜/입력 필드 공통 참조: .get(), .set(val), .widget ──
                class _FieldRef:
                    def __init__(self, get_fn, widget, set_fn):
                        self.get = get_fn
                        self.widget = widget
                        self.set = set_fn

                # ── 헬퍼: DateEntry( gui_bootstrap ) 또는 텍스트 입력 생성 ──
                def _make_date_field(parent, label, hint, prefill='', required=False):
                    """HAS_DATEENTRY면 ttkbootstrap 달력, 없으면 텍스트 입력. _FieldRef 반환( .get/.set/.widget )"""
                    _cal_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
                    lf = ttk.LabelFrame(parent,
                        text=f"{'★ ' if required else ''}{label}{' — 필수' if required else ''}",
                        padding=8)
                    lf.pack(fill=tk.X, pady=(0, 8))

                    var = tk.StringVar(value=prefill)

                    if HAS_DATEENTRY and DateEntry is not None:
                        startdate = None
                        if prefill:
                            try:
                                parts = prefill.split('-')
                                startdate = _date_type(int(parts[0]), int(parts[1]), int(parts[2]))
                            except (ValueError, IndexError):
                                pass
                        de = DateEntry(lf, dateformat='%Y-%m-%d', startdate=startdate,
                                       bootstyle='info', width=16)
                        de.pack(side=tk.LEFT, padx=(0, 8))
                        ttk.Label(lf, text=hint,
                                 font=('맑은 고딕', 9), foreground=ThemeColors.get('text_muted', _cal_dark)).pack(side=tk.LEFT)
                        def _get():
                            return (de.entry.get() or '').strip() if de and de.winfo_exists() else ''
                        def _set(v):
                            if de and de.winfo_exists():
                                try:
                                    parts = str(v).strip().split('-')
                                    if len(parts) == 3:
                                        d = _date_type(int(parts[0]), int(parts[1]), int(parts[2]))
                                        de.configure(startdate=d)
                                        de.entry.delete(0, tk.END)
                                        de.entry.insert(0, d.strftime('%Y-%m-%d'))
                                    else:
                                        de.entry.delete(0, tk.END)
                                        de.entry.insert(0, str(v))
                                except (ValueError, IndexError, TypeError):
                                    de.entry.delete(0, tk.END)
                                    de.entry.insert(0, str(v))
                        return _FieldRef(_get, de, _set)
                    else:
                        entry = ttk.Entry(lf, textvariable=var,
                                         font=('맑은 고딕', 11), width=16)
                        entry.pack(side=tk.LEFT, padx=(0, 8))
                        ttk.Label(lf, text=hint,
                                 font=('맑은 고딕', 9), foreground=ThemeColors.get('text_muted', _cal_dark)).pack(side=tk.LEFT)
                        return _FieldRef(lambda: (var.get() or '').strip(), entry, var.set)

                # ── 선적일(ship_date) 미표시 — B/L에서 추출되므로 톤백 리스트에 이미 있음 ──
                ship_var = None

                arrival_var = _make_date_field(frame,
                    "입항일 (Arrival Date)",
                    "YYYY-MM-DD (예: 2025-10-17)",
                    required=True)

                con_return_ref = _make_date_field(frame,
                    "컨테이너 반납기한 (con_return)",
                    "반납일 YYYY-MM-DD (비우면 Free time 일수로)")

                # Free time은 일수(숫자) 전용 — DateEntry 사용 시 '14' 입력이 깨지므로 항상 Entry
                _ft_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
                lf_ft = ttk.LabelFrame(frame, text="Free time (일수)", padding=8)
                lf_ft.pack(fill=tk.X, pady=(0, 8))
                ft_var = tk.StringVar(value='')
                ft_entry = ttk.Entry(lf_ft, textvariable=ft_var, font=('맑은 고딕', 11), width=10)
                ft_entry.pack(side=tk.LEFT, padx=(0, 8))
                ttk.Label(lf_ft, text="반납일-입항일=Free time (둘 중 하나만 입력 시 나머지 자동 계산·자동 입력 시 상대 필드 비활성화)",
                         font=('맑은 고딕', 9), foreground=ThemeColors.get('text_muted', _ft_dark)).pack(side=tk.LEFT)
                ft_ref = _FieldRef(lambda: (ft_var.get() or '').strip(), ft_entry, ft_var.set)

                # 에러 표시
                err_var = tk.StringVar()
                _err_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
                ttk.Label(frame, textvariable=err_var,
                         font=('맑은 고딕', 10), foreground=ThemeColors.get('danger', _err_dark)).pack(anchor='w', pady=(4, 0))

                # ── con_return ↔ free_time 상호 계산·비활성화 (둘 중 하나 입력 시 상대 필드 자동 계산 후 비활성화) ──
                _updating_silently = {'v': False}
                def _sync_from_con_return(*_):
                    if _updating_silently['v']:
                        return
                    arr = (arrival_var.get() or '').strip()
                    cr = (con_return_ref.get() or '').strip()
                    if not arr or not cr or not _validate_date(arr) or not _validate_date(cr):
                        return
                    try:
                        arr_d = _date_type(*[int(x) for x in arr.split('-')])
                        cr_d = _date_type(*[int(x) for x in cr.split('-')])
                        ft_days = max(0, (cr_d - arr_d).days)
                        _updating_silently['v'] = True
                        ft_ref.set(str(ft_days))
                        ft_entry.config(state='disabled')
                    except (ValueError, IndexError, TypeError):
                        pass
                    finally:
                        _updating_silently['v'] = False
                def _sync_from_ft(*_):
                    if _updating_silently['v']:
                        return
                    arr = (arrival_var.get() or '').strip()
                    ft_raw = (ft_ref.get() or '').strip()
                    if not arr or not ft_raw or not _validate_date(arr):
                        return
                    if not ft_raw.isdigit() or int(ft_raw) < 0:
                        return
                    try:
                        arr_d = _date_type(*[int(x) for x in arr.split('-')])
                        cr_d = arr_d + timedelta(days=int(ft_raw))
                        cr_str = cr_d.strftime('%Y-%m-%d')
                        _updating_silently['v'] = True
                        con_return_ref.set(cr_str)
                        w = con_return_ref.widget
                        if hasattr(w, 'entry'):
                            w.entry.config(state='disabled')
                        else:
                            w.config(state='disabled')
                    except (ValueError, IndexError, TypeError):
                        pass
                    finally:
                        _updating_silently['v'] = False
                def _enable_both():
                    _updating_silently['v'] = True
                    try:
                        ft_entry.config(state='normal')
                        w = con_return_ref.widget
                        if hasattr(w, 'entry'):
                            w.entry.config(state='normal')
                        else:
                            w.config(state='normal')
                    finally:
                        _updating_silently['v'] = False
                # FocusOut 바인딩 (입력 완료 후 상대 필드 계산·비활성화)
                if hasattr(con_return_ref.widget, 'entry'):
                    con_return_ref.widget.entry.bind('<FocusOut>', _sync_from_con_return)
                else:
                    con_return_ref.widget.bind('<FocusOut>', _sync_from_con_return)
                ft_entry.bind('<FocusOut>', _sync_from_ft)

                # ── 날짜 검증 함수 ──
                def _validate_date(s):
                    import re as _re
                    if not s:
                        return True
                    s = s.strip()
                    if _re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', s):
                        try:
                            parts = s.split('-')
                            _date_type(int(parts[0]), int(parts[1]), int(parts[2]))
                            return True
                        except ValueError:
                            return False
                    return False

                # ── 확인 버튼 ── (반납일 또는 Free time 중 하나만 알면 나머지 자동 계산)
                def _on_ok():
                    err_var.set('')
                    try:
                        arr = (arrival_var.get() or '').strip()
                        if not arr:
                            err_var.set("⚠️ 입항일은 필수입니다!")
                            return
                        if not _validate_date(arr):
                            err_var.set("⚠️ 입항일 형식 오류 (YYYY-MM-DD)")
                            return
                        arr_d = _date_type(*[int(x) for x in arr.split('-')])
                    except (ValueError, IndexError, TypeError) as e:
                        err_var.set("⚠️ 입항일 파싱 오류 (YYYY-MM-DD)")
                        logger.debug(f"[_ask_missing_dates] 입항일 파싱: {e}")
                        return
                    # arrival_date > ship_date (선적일이 있으면)
                    if prefilled_ship and _validate_date(prefilled_ship.strip()):
                        try:
                            ship_d = _date_type(*[int(x) for x in prefilled_ship.strip().split('-')])
                            if arr_d <= ship_d:
                                err_var.set("⚠️ 입항일은 선적일보다 이후여야 합니다.")
                                return
                        except (ValueError, IndexError, TypeError):
                            pass
                    ship = ''
                    if ship_var is not None:
                        ship = (ship_var.get() or '').strip()
                        if ship and not _validate_date(ship):
                            err_var.set("⚠️ 선적일 형식 오류 (YYYY-MM-DD)")
                            return
                    con_return_str = (con_return_ref.get() or '').strip()
                    ft_raw = (ft_var.get() or '').strip()
                    free_time_str = ''
                    try:
                        # free_time을 입력했으면 이를 우선 기준으로 con_return을 계산
                        # (DateEntry 표시값 지연 반영/잠금 상태에서도 일관된 결과 보장)
                        if ft_raw:
                            if not ft_raw.isdigit() or int(ft_raw) < 0:
                                err_var.set("⚠️ Free time: 0 이상 일수(숫자) 입력")
                                return
                            free_time_str = ft_raw
                            con_return_d = arr_d + timedelta(days=int(ft_raw))
                            con_return_str = con_return_d.strftime('%Y-%m-%d')
                        elif con_return_str:
                            if not _validate_date(con_return_str):
                                err_var.set("⚠️ 반납기한(con_return): YYYY-MM-DD 형식")
                                return
                            cr_d = _date_type(*[int(x) for x in con_return_str.split('-')])
                            free_time_str = str(max(0, (cr_d - arr_d).days))
                        else:
                            free_time_str = '14'
                            con_return_str = (arr_d + timedelta(days=14)).strftime('%Y-%m-%d')
                    except (ValueError, IndexError, TypeError) as e:
                        err_var.set("⚠️ 반납일/Free time 계산 오류 — 형식 확인")
                        logger.debug(f"[_ask_missing_dates] 반납일·Free time: {e}")
                        return
                    # con_return >= arrival_date (당일 반납 포함 허용)
                    try:
                        cr_d = _date_type(*[int(x) for x in con_return_str.split('-')])
                        if cr_d < arr_d:
                            err_var.set("⚠️ 컨테이너 반납일은 입항일과 같거나 이후여야 합니다.")
                            return
                    except (ValueError, IndexError, TypeError):
                        pass
                    # 사용자 확인 단계: Free time·반납일 표시 후 맞음/다시 입력 선택
                    from ..utils.custom_messagebox import CustomMessageBox
                    confirmed = CustomMessageBox._create_dialog(
                        win, "입력 확인",
                        f"Free time {free_time_str}일, 컨테이너 반납일은 {con_return_str} 입니다.\n\n맞습니까?",
                        'question',
                        [('맞음', True), ('다시 입력', False)],
                        default_button=0
                    )
                    if not confirmed:
                        return  # 다시 입력 — 날짜 팝업 유지, 사용자가 수정 후 재확인 가능
                    result_holder[0] = {
                        'ship_date': ship,
                        'arrival_date': arr,
                        'con_return': con_return_str,
                        'free_time': free_time_str,
                    }
                    win.destroy()
                    return

                # ── D/O 추후 첨부 버튼 ──
                def _on_defer():
                    result_holder[0] = {'deferred': True}
                    win.destroy()

                # ── 취소 ──
                def _on_cancel():
                    result_holder[0] = None
                    win.destroy()

                # ── 버튼 배치 ──
                btn_frame = ttk.Frame(frame)
                btn_frame.pack(fill=tk.X, pady=(12, 0))

                ttk.Button(btn_frame, text="✅ 확인",
                          command=_on_ok, width=10).pack(side=tk.LEFT, padx=(0, 8))

                ttk.Button(btn_frame, text="✏️ 수정",
                          command=_enable_both, width=10).pack(side=tk.LEFT, padx=(0, 8))

                ttk.Button(btn_frame, text="📋 D/O 추후 첨부",
                          command=_on_defer, width=16).pack(side=tk.LEFT, padx=(0, 8))

                ttk.Button(btn_frame, text="❌ 취소",
                          command=_on_cancel, width=10).pack(side=tk.LEFT)

                win.protocol("WM_DELETE_WINDOW", _on_cancel)
                return win

            except Exception as e:
                logger.error(f"[_ask_missing_dates] 팝업 오류: {e}", exc_info=True)
                return None

        if not self.dialog or not self.dialog.winfo_exists():
            return None

        win = _build_popup()
        if win and win.winfo_exists():
            win.wait_window(win)
        return result_holder[0]

    # ═══════════════════════════════════════════════════════════
    # 미리보기 표시
    # ═══════════════════════════════════════════════════════════

    def _push_preview_to_main(self) -> None:
        """파싱된 미리보기 데이터를 메인 화면 재고 리스트에 실시간 반영"""
        if not getattr(self, 'app', None) or not hasattr(self.app, '_set_parsing_preview_data'):
            return
        if not self.preview_data:
            return
        try:
            self.app._set_parsing_preview_data(list(self.preview_data))
        except (RuntimeError, ValueError, TypeError) as e:
            logger.debug(f"푸시 미리보기 실패: {e}")

    def _clear_preview_from_main(self) -> None:
        """메인 화면 파싱 미리보기 해제 후 DB 기준으로 복원"""
        if not getattr(self, 'app', None) or not hasattr(self.app, '_set_parsing_preview_data'):
            return
        try:
            self.app._set_parsing_preview_data(None)
        except (RuntimeError, ValueError, TypeError) as e:
            logger.debug(f"미리보기 해제 실패: {e}")

    def _format_container_display(self, val) -> str:
        """컨테이너 번호: 디폴트로 접미사 -숫자 제거. 표시 옵션 켜면 원문 반환."""
        if not val or not isinstance(val, str):
            return val or ''
        if getattr(self, '_show_container_suffix', False):
            return val.strip()
        s = val.strip()
        if '-' in s:
            pre, _, suf = s.rpartition('-')
            if suf.isdigit():
                return pre
        return s

    def _on_toggle_container_suffix(self) -> None:
        """컨테이너 접미사 표시 체크 시 미리보기 테이블 갱신"""
        var = getattr(self, '_var_show_container_suffix', None)
        self._show_container_suffix = bool(var and var.get())
        if self.preview_data and getattr(self, 'tree', None) and self.tree.winfo_exists():
            self._refresh_preview_tree_only()

    def _row_display_values(self, row: dict) -> tuple:
        """한 행의 표시용 values (container_no는 접미사 옵션 적용)."""
        out = []
        for col in PREVIEW_COLUMNS:
            key = col[0]
            if key == 'container_no':
                out.append(self._format_container_display(row.get(key, '')))
            else:
                out.append(row.get(key, ''))
        return tuple(out)

    def _lot_order_key(self, lot, fallback_idx: int) -> tuple:
        """Packing List 원본 순서를 우선 유지(list_no 기준)."""
        raw = getattr(lot, 'list_no', None)
        if raw is None and isinstance(lot, dict):
            raw = lot.get('list_no')
        try:
            return (0, int(str(raw).strip()))
        except (ValueError, TypeError):
            return (1, int(fallback_idx))

    def _capture_original_preview_state(self) -> None:
        """파싱 직후 원본 데이터 스냅샷 저장."""
        self._original_preview_data = deepcopy(self.preview_data or [])

    def _reset_preview_to_original(self) -> None:
        """원본 초기화: 파싱 직후 상태로 복원."""
        if not self._original_preview_data:
            return
        from ..utils.custom_messagebox import CustomMessageBox
        if not CustomMessageBox.askyesno(self.dialog, "원본 초기화", "현재 편집/정렬/필터 상태를 버리고\n파싱 직후 원본으로 되돌릴까요?"):
            return
        self.preview_data = deepcopy(self._original_preview_data)
        self._edited_rows = set()
        self._undo_stack = []
        self._redo_stack = []
        self._sort_col = None
        self._sort_desc = False
        self._update_sort_headings()
        try:
            if self.filter_bar:
                self.filter_bar._reset_filters()
        except Exception as e:
            logger.debug(f"원본 초기화 필터 리셋 실패(무시): {e}")
        self._update_filter_values_from_preview()
        self._update_undo_redo_buttons()
        self._refresh_preview_tree_only()
        self._update_summary()
        self._push_preview_to_main()

    def _update_sort_headings(self) -> None:
        if not getattr(self, 'tree', None):
            return
        for col_id, header, _w, _a in PREVIEW_COLUMNS:
            suffix = ""
            if col_id == self._sort_col:
                suffix = " ▼" if self._sort_desc else " ▲"
            self.tree.heading(col_id, text=f"{header}{suffix}", command=lambda c=col_id: self._toggle_preview_sort(c))

    def _toggle_preview_sort(self, col_id: str) -> None:
        if self._sort_col == col_id:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col_id
            self._sort_desc = False
        self._update_sort_headings()
        self._refresh_preview_tree_only()

    def _on_change_preview_filter(self) -> None:
        self._refresh_preview_tree_only()

    def _update_filter_values_from_preview(self) -> None:
        if not self.filter_bar:
            return
        for col_id in ('sap_no', 'bl_no', 'container_no', 'product', 'status'):
            vals = [str((r.get(col_id, '') if isinstance(r, dict) else '') or '').strip() for r in (self.preview_data or [])]
            self.filter_bar.update_filter_values(col_id, [v for v in vals if v])

    def _item_to_source_index(self, item_id: str) -> int:
        try:
            return int(str(item_id))
        except (TypeError, ValueError):
            try:
                return self.tree.index(item_id)
            except Exception:
                return -1

    def _matches_preview_filters(self, row: dict) -> bool:
        if not self.filter_bar:
            return True
        filters = self.filter_bar.get_filters()
        if not filters:
            return True
        for col_id, expected in filters.items():
            if str(row.get(col_id, '') or '').strip() != str(expected).strip():
                return False
        return True

    def _preview_sort_key(self, row: dict):
        col = self._sort_col
        if not col:
            return 0
        val = row.get(col, '')
        s = str(val or '').strip()
        if col in {'mxbg_pallet', 'free_time', 'net_weight', 'gross_weight'}:
            try:
                return float(s.replace(',', '')) if s else -1.0
            except ValueError:
                return -1.0
        if col in {'ship_date', 'arrival_date', 'con_return'}:
            return s[:10]
        return s.upper()

    def _build_view_indices(self) -> list:
        indices = [i for i, r in enumerate(self.preview_data or []) if self._matches_preview_filters(r)]
        if self._sort_col:
            indices = sorted(
                indices,
                key=lambda i: self._preview_sort_key(self.preview_data[i]),
                reverse=self._sort_desc
            )
        return indices

    def _get_upload_rows_for_db(self) -> list:
        """DB 업로드 대상 행 순서 결정.

        - 기본: 원본(preview_data) 순서
        - 옵션 체크 시: 현재 화면의 정렬/필터(view) 순서
        """
        rows = list(getattr(self, 'preview_data', []) or [])
        use_view_order = bool(self._var_upload_by_view_order and self._var_upload_by_view_order.get())
        if not use_view_order:
            self._log_safe("📌 DB 업로드 순서: 원본 순서(preview_data)")
            return rows
        indices = self._build_view_indices()
        ordered = [deepcopy(rows[i]) for i in indices if 0 <= i < len(rows)]
        self._log_safe(f"📌 DB 업로드 순서: 화면 정렬/필터 순서 적용 ({len(ordered)}건)")
        return ordered

    def _setup_preview_edit_bindings(self) -> None:
        """업로드1 미리보기: 엑셀형 셀 편집/복사/붙여넣기 바인딩."""
        if not getattr(self, 'tree', None):
            return
        self.tree.bind('<Double-1>', self._on_preview_cell_edit, add='+')
        self.tree.bind('<Button-1>', self._capture_preview_anchor, add='+')
        self.tree.bind('<Control-c>', self._copy_preview_selection, add='+')
        self.tree.bind('<Control-C>', self._copy_preview_selection, add='+')
        self.tree.bind('<Control-v>', self._paste_preview_from_clipboard, add='+')
        self.tree.bind('<Control-V>', self._paste_preview_from_clipboard, add='+')
        self.tree.bind('<Control-x>', self._cut_preview_selection, add='+')
        self.tree.bind('<Control-X>', self._cut_preview_selection, add='+')
        self.tree.bind('<Delete>', self._clear_preview_selection, add='+')
        self.tree.bind('<Control-z>', self._undo_preview_edit, add='+')
        self.tree.bind('<Control-Z>', self._undo_preview_edit, add='+')
        self.tree.bind('<Control-y>', self._redo_preview_edit, add='+')
        self.tree.bind('<Control-Y>', self._redo_preview_edit, add='+')
        if getattr(self, 'dialog', None):
            self.dialog.bind('<Control-z>', self._undo_preview_edit, add='+')
            self.dialog.bind('<Control-Z>', self._undo_preview_edit, add='+')
            self.dialog.bind('<Control-y>', self._redo_preview_edit, add='+')
            self.dialog.bind('<Control-Y>', self._redo_preview_edit, add='+')
            self.dialog.bind('<Control-x>', self._cut_preview_selection, add='+')
            self.dialog.bind('<Control-X>', self._cut_preview_selection, add='+')
            self.dialog.bind('<Delete>', self._clear_preview_selection, add='+')

    def _snapshot_preview_state(self) -> dict:
        return {
            'preview_data': deepcopy(self.preview_data),
            'edited_rows': set(self._edited_rows),
        }

    def _push_undo_snapshot(self) -> None:
        self._undo_stack.append(self._snapshot_preview_state())
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_redo_buttons()

    def _restore_preview_state(self, state: dict) -> None:
        self.preview_data = deepcopy(state.get('preview_data', []))
        self._edited_rows = set(state.get('edited_rows', set()))
        self._refresh_preview_tree_only()
        self._update_summary()
        self._push_preview_to_main()
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self) -> None:
        try:
            if self.btn_undo and self.btn_undo.winfo_exists():
                self.btn_undo.config(state='normal' if self._undo_stack else 'disabled')
            if self.btn_redo and self.btn_redo.winfo_exists():
                self.btn_redo.config(state='normal' if self._redo_stack else 'disabled')
        except (RuntimeError, tk.TclError):
            pass

    def _undo_preview_edit(self, event=None):
        self._finish_preview_editing(save=True)
        if not self._undo_stack:
            return "break"
        self._redo_stack.append(self._snapshot_preview_state())
        state = self._undo_stack.pop()
        self._restore_preview_state(state)
        self._log_safe("↶ 되돌리기 적용")
        return "break"

    def _redo_preview_edit(self, event=None):
        self._finish_preview_editing(save=True)
        if not self._redo_stack:
            return "break"
        self._undo_stack.append(self._snapshot_preview_state())
        state = self._redo_stack.pop()
        self._restore_preview_state(state)
        self._log_safe("↷ 다시실행 적용")
        return "break"

    def _preview_col_names(self) -> list:
        return [c[0] for c in PREVIEW_COLUMNS]

    def _editable_preview_columns(self) -> set:
        # No/Status는 시스템 관리 컬럼으로 편집 제외
        return set(self._preview_col_names()) - {'no', 'status'}

    def _capture_preview_anchor(self, event=None) -> None:
        if not getattr(self, 'tree', None):
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return
        try:
            row_idx = self.tree.index(row_id)  # view index (필터/정렬 반영)
            col_idx = max(0, int(col_id.replace('#', '')) - 1)
            self._preview_anchor = (row_idx, col_idx)
        except (ValueError, TypeError, tk.TclError):
            pass

    def _on_preview_cell_edit(self, event=None) -> None:
        """셀 더블클릭 인라인 편집."""
        if not getattr(self, 'tree', None):
            return
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        col_id = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        if not col_id or not row_id:
            return
        cols = self._preview_col_names()
        try:
            col_idx = int(col_id.replace('#', '')) - 1
        except ValueError:
            return
        if col_idx < 0 or col_idx >= len(cols):
            return
        col_name = cols[col_idx]
        if col_name not in self._editable_preview_columns():
            return
        self._capture_preview_anchor(event)
        self._finish_preview_editing(save=True)
        bbox = self.tree.bbox(row_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        current_val = str(self.tree.set(row_id, col_name))
        entry = tk.Entry(self.tree, font=('맑은 고딕', 10))
        entry.insert(0, current_val.replace(',', ''))
        entry.select_range(0, 'end')
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()
        self._editing_item = (row_id, col_name, entry)
        entry.bind('<Return>', lambda e: self._finish_preview_editing(save=True))
        entry.bind('<Escape>', lambda e: self._finish_preview_editing(save=False))
        entry.bind('<FocusOut>', lambda e: self._finish_preview_editing(save=True))

    def _coerce_preview_value(self, col_name: str, value: str) -> str:
        v = (value or '').strip()
        if col_name in {'mxbg_pallet', 'free_time'}:
            if not v:
                return ''
            try:
                return str(max(0, int(float(v.replace(',', '')))))
            except ValueError:
                return ''
        if col_name in {'net_weight', 'gross_weight'}:
            if not v:
                return ''
            try:
                return f"{float(v.replace(',', '')):,.1f}"
            except ValueError:
                return ''
        if col_name in {'ship_date', 'arrival_date', 'con_return'}:
            if not v:
                return ''
            s = v[:10]
            if len(s) == 10 and s.count('-') == 2 and s.replace('-', '').isdigit():
                return s
            return ''
        return v

    def _update_preview_cell(self, row_idx: int, col_name: str, new_value: str) -> None:
        if row_idx < 0 or row_idx >= len(self.preview_data):
            return
        if col_name not in self._editable_preview_columns():
            return
        coerced = self._coerce_preview_value(col_name, new_value)
        self.preview_data[row_idx][col_name] = coerced
        self._edited_rows.add(row_idx)

    def _finish_preview_editing(self, save: bool = True) -> None:
        if not self._editing_item:
            return
        row_id, col_name, entry = self._editing_item
        raw_val = entry.get().strip()
        entry.destroy()
        self._editing_item = None
        if not save:
            return
        try:
            row_idx = self._item_to_source_index(row_id)
            if row_idx < 0 or row_idx >= len(self.preview_data):
                return
            old_val = str(self.preview_data[row_idx].get(col_name, ''))
            new_val = self._coerce_preview_value(col_name, raw_val)
            if old_val == new_val:
                return
            self._push_undo_snapshot()
            self._update_preview_cell(row_idx, col_name, raw_val)
            self._refresh_preview_tree_only()
            self._update_summary()
            self._push_preview_to_main()
        except (ValueError, TypeError, tk.TclError):
            pass

    def _copy_preview_selection(self, event=None):
        """선택 행 TSV 복사 (엑셀 붙여넣기 호환)."""
        if not getattr(self, 'tree', None):
            return "break"
        items = self.tree.selection()
        if not items:
            focused = self.tree.focus()
            if focused:
                items = (focused,)
        if not items:
            return "break"
        headers = [c[1] for c in PREVIEW_COLUMNS]
        lines = ['\t'.join(headers)]
        for item_id in items:
            vals = self.tree.item(item_id, 'values')
            lines.append('\t'.join(str(v) for v in vals))
        self.tree.clipboard_clear()
        self.tree.clipboard_append('\n'.join(lines))
        return "break"

    def _selected_preview_cells(self):
        """선택 행 + 마지막 클릭 열 기준의 셀 좌표 목록."""
        if not getattr(self, 'tree', None):
            return []
        cols = self._preview_col_names()
        sel_items = list(self.tree.selection())
        if not sel_items:
            focus = self.tree.focus()
            if focus:
                sel_items = [focus]
        if not sel_items:
            return []
        _row_anchor, col_idx = self._preview_anchor
        col_idx = max(0, min(col_idx, len(cols) - 1))
        col_name = cols[col_idx]
        if col_name not in self._editable_preview_columns():
            return []
        out = []
        for item_id in sel_items:
            try:
                row_idx = self._item_to_source_index(item_id)
                if 0 <= row_idx < len(self.preview_data):
                    out.append((row_idx, col_name))
            except (ValueError, TypeError, tk.TclError):
                continue
        return out

    def _clear_preview_selection(self, event=None):
        """Delete: 선택 셀 비우기."""
        cells = self._selected_preview_cells()
        if not cells:
            return "break"
        self._push_undo_snapshot()
        for row_idx, col_name in cells:
            self._update_preview_cell(row_idx, col_name, '')
        self._refresh_preview_tree_only()
        self._update_summary()
        self._push_preview_to_main()
        return "break"

    def _cut_preview_selection(self, event=None):
        """Ctrl+X: 선택 셀 복사 후 비우기."""
        cells = self._selected_preview_cells()
        if not cells:
            return "break"
        values = []
        for row_idx, col_name in cells:
            values.append(str(self.preview_data[row_idx].get(col_name, '') or ''))
        try:
            self.tree.clipboard_clear()
            self.tree.clipboard_append('\n'.join(values))
        except tk.TclError:
            pass
        self._push_undo_snapshot()
        for row_idx, col_name in cells:
            self._update_preview_cell(row_idx, col_name, '')
        self._refresh_preview_tree_only()
        self._update_summary()
        self._push_preview_to_main()
        return "break"

    def _paste_preview_from_clipboard(self, event=None):
        """선택 셀을 시작점으로 TSV 블록 붙여넣기."""
        if not getattr(self, 'tree', None):
            return "break"
        try:
            raw = self.tree.clipboard_get()
        except tk.TclError:
            return "break"
        lines = [ln for ln in raw.replace('\r', '').split('\n') if ln.strip()]
        if not lines:
            return "break"
        start_row, start_col = self._preview_anchor  # start_row는 view index
        cols = self._preview_col_names()
        # 헤더 포함 복사분이면 첫 줄 스킵
        first_parts = [p.strip() for p in lines[0].split('\t')]
        if first_parts and len(first_parts) == len(cols):
            header_names = [c[1] for c in PREVIEW_COLUMNS]
            if all(fp in header_names for fp in first_parts[: min(3, len(first_parts))]):
                lines = lines[1:]
        if lines:
            self._push_undo_snapshot()
        view_items = list(self.tree.get_children())
        for r_off, line in enumerate(lines):
            view_idx = start_row + r_off
            if view_idx >= len(view_items):
                break
            row_idx = self._item_to_source_index(view_items[view_idx])
            if row_idx < 0 or row_idx >= len(self.preview_data):
                continue
            parts = [p.strip() for p in line.split('\t')]
            for c_off, val in enumerate(parts):
                col_idx = start_col + c_off
                if col_idx >= len(cols):
                    break
                col_name = cols[col_idx]
                self._update_preview_cell(row_idx, col_name, val)
        self._refresh_preview_tree_only()
        self._update_summary()
        self._push_preview_to_main()
        return "break"

    def _refresh_preview_tree_only(self) -> None:
        """미리보기 테이블만 현재 preview_data로 갱신 (요약/버튼/팝업 없음). 파싱 중 실시간 표시용."""
        if not getattr(self, 'tree', None) or not self.tree.winfo_exists():
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not self.preview_data:
            return
        # v6.2.1: 크로스 체크 결과에서 행 단위 태그 계산
        xc = getattr(self, '_cross_check_result', None)
        xc_lot_levels = {}
        xc_global_level = None
        if xc and not xc.is_clean:
            # 행마다 get_row_tag를 반복 호출하지 않고, 리프레시 1회당 1회 계산 결과를 재사용한다.
            xc_lot_levels = xc.get_lot_levels()
            xc_global_level = xc.global_level
        self._view_indices = self._build_view_indices()
        for pos, src_idx in enumerate(self._view_indices):
            row = self.preview_data[src_idx]
            row['no'] = str(src_idx + 1)
            values = self._row_display_values(row)
            # 태그 우선순위: edited > xc_critical > xc_warning > xc_info > odd/even
            if src_idx in self._edited_rows:
                tag = 'edited'
            elif xc and not xc.is_clean:
                lot_no = (row.get('lot_no') or '').strip()
                lot_level = xc_lot_levels.get(lot_no)
                effective = None
                if lot_level and xc_global_level:
                    effective = max(lot_level, xc_global_level)
                elif lot_level:
                    effective = lot_level
                elif xc_global_level:
                    effective = xc_global_level

                if effective and int(effective) == 3:
                    tag = 'xc_critical'
                elif effective and int(effective) == 2:
                    tag = 'xc_warning'
                elif effective and int(effective) == 1:
                    tag = 'xc_info'
                else:
                    tag = 'even' if pos % 2 == 0 else 'odd'
            else:
                tag = 'even' if pos % 2 == 0 else 'odd'
            self.tree.insert('', END, iid=str(src_idx), values=values, tags=(tag,))

    def _display_preview(self) -> None:
        """미리보기 테이블 표시 — 한 번에가 아니라 순차적으로 행 추가 (보기 편하게)"""
        def _update():
            if not self.tree:
                return
            self._push_preview_to_main()
            self._refresh_preview_tree_only()
            self._update_summary()
            if self.preview_data and self._has_required_docs():
                self.btn_upload.config(state='normal')
            else:
                self.btn_upload.config(state='disabled')
            if self.preview_data:
                self.btn_excel.config(state='normal')
            self._update_filter_values_from_preview()

        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, _update)

    def _has_required_docs(self) -> bool:
        """필수 서류 3종(Packing List, Invoice, B/L)이 모두 선택·파싱되었는지 확인"""
        for doc_type, _name, required in DOC_TYPES:
            if required and doc_type not in self.file_paths:
                return False
        return True

    def _update_summary(self) -> None:
        """합계행"""
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
            except (ValueError, TypeError) as _e:
                logger.debug(f"onestop_inbound: {_e}")
            try:
                total_net += safe_float(r['net_weight']) if r['net_weight'] else 0
            except (ValueError, TypeError) as _e:
                logger.debug(f"onestop_inbound: {_e}")
            try:
                total_gross += safe_float(r['gross_weight']) if r['gross_weight'] else 0
            except (ValueError, TypeError) as _e:
                logger.debug(f"onestop_inbound: {_e}")

        self.summary_var.set(
            f"합계: {len(self.preview_data)} LOT | "
            f"{len(containers)} 컨테이너 | "
            f"{total_tb} 톤백 | "
            f"Net {total_net:,.0f} kg | "
            f"Gross {total_gross:,.0f} kg"
        )

    def _check_parsing_duplicates(self) -> str:
        """파싱 결과에서 입고 중복 여부 검사 (lot_no 기준). 중복이 있으면 안내 문구 반환, 없으면 빈 문자열."""
        if not self.preview_data:
            return ""
        from collections import Counter
        lot_counts = Counter(str(r.get('lot_no', '')).strip() for r in self.preview_data if str(r.get('lot_no', '')).strip())
        dups = [(lot, cnt) for lot, cnt in lot_counts.items() if cnt > 1]
        if not dups:
            return ""
        parts = [f"LOT NO {lot} ({cnt}건)" for lot, cnt in dups[:10]]
        if len(dups) > 10:
            parts.append(f"외 {len(dups) - 10}건")
        return "중복: " + ", ".join(parts)

    # v5.9.4: _on_upload, _upload_thread, _save_to_db, _export_to_excel
    # → inbound_upload_mixin.py (InboundUploadMixin)으로 분리

    # ═══════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════

    def _show_success_and_close(self, count: int):
        def _close():
            if self.dialog and self.dialog.winfo_exists():
                _app = self.app if self.app else None
                # v5.8.9: 파싱 결과 팝업에서 DB 업로드 선택 시, 완료 후 엑셀 내보내기 여부 질의
                if getattr(self, '_ask_excel_after_upload', False):
                    self._ask_excel_after_upload = False
                    try:
                        from ..utils.custom_messagebox import CustomMessageBox
                        if CustomMessageBox.askyesno(self.dialog, "엑셀 내보내기",
                            "DB 업로드가 완료되었습니다.\n엑셀 내보내기도 하시겠습니까?\n(아니오를 누르면 여기서 종료합니다.)"):
                            self._export_to_excel()
                    except (ImportError, ModuleNotFoundError):
                        pass
                _msg = f"✅ {count}개 LOT 저장 완료"
                try:
                    from ..utils.custom_messagebox import CustomMessageBox
                    CustomMessageBox.showinfo(self.dialog, "업로드 완료", _msg)
                except (ImportError, ModuleNotFoundError):
                    CustomMessageBox.info(None, "완료", _msg)
                self.dialog.destroy()

                # v3.8.9: 업로드 후 재고리스트 탭 이동 + 자동 새로고침
                # dialog.destroy() 후이므로 app.root.after 사용
                if _app:
                    try:
                        _root = getattr(_app, 'root', None)
                        if _root:
                            if hasattr(_app, '_set_parsing_preview_data'):
                                _app._set_parsing_preview_data(None)
                            if hasattr(_app, 'notebook') and hasattr(_app, 'tab_inventory'):
                                _root.after(200, lambda: _app.notebook.select(_app.tab_inventory))
                            if hasattr(_app, '_deferred_refresh_main_tabs'):
                                _app._deferred_refresh_main_tabs(delay_ms=500)
                                logger.info("[onestop] 전체 탭 새로고침 예약 완료 (500ms)")
                            elif hasattr(_app, '_refresh_inventory'):
                                _root.after(500, _app._refresh_inventory)
                                logger.info("[onestop] 재고 새로고침 예약 완료 (500ms)")
                    except (RuntimeError, ValueError) as e:
                        logger.debug(f"재고 새로고침 호출 실패: {e}")

        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(100, _close)

    def _enable_buttons(self) -> None:
        def _u():
            try:
                if self.btn_upload and self.btn_upload.winfo_exists():
                    self.btn_upload.config(state='normal')
                if self.btn_excel and self.btn_excel.winfo_exists():
                    self.btn_excel.config(state='normal')
            except (RuntimeError, ValueError) as _e:
                logger.debug(f'Suppressed: {_e}')
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, _u)

    def _enable_parse_btn(self):
        def _u():
            if self.btn_parse:
                self.btn_parse.config(state='normal')
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, _u)

    def _on_cancel(self):
        self._clear_preview_from_main()
        if self.dialog:
            self.dialog.destroy()

    def _log_safe(self, msg: str):
        try:
            if self._log:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(0, lambda: self._log(msg))
                else:
                    self._log(msg)
        except (RuntimeError, ValueError):
            logger.info(msg)
