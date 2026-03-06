"""
SQM v3.8.4 — 원스톱 입고 팝업
4종 서류(PL, Invoice, BL, DO)를 한 화면에서:
  파일 선택 → 체크 표시 → 파싱 → 미리보기 → DB 업로드

작성일: 2025-02-06
"""
import os
import re
import sys
import csv
from tkinter import messagebox as msgbox
import time
import tkinter as tk
from tkinter import ttk, filedialog, BOTH, YES, X, Y, LEFT, RIGHT, BOTTOM, END, VERTICAL, HORIZONTAL
import logging
import threading
from datetime import datetime, timedelta, date as _date_type
from copy import deepcopy

# 비즈니스 기본값
from core.constants import DEFAULT_WAREHOUSE

from ..utils.ui_constants import ThemeColors, DialogSize, center_dialog, apply_modal_window_options
from core.types import safe_float

# v5.8.7: DatePicker 달력 UI — gui_bootstrap 통일 (ttkbootstrap.DateEntry, 없으면 텍스트 입력 폴백)
from ..utils.gui_bootstrap import DateEntry, HAS_DATEENTRY

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
    ("qc_status",        "QC",               70,  "center"),    ("qc_reason",        "QC REASON",       320,  "w"),

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
        self._last_selected_dir = ""
        
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
        self.btn_reparse = None
        self.btn_bundle_select = None
        self._var_auto_parse_after_bundle = None
        self._var_skip_confirm_on_auto_parse = None
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
        self._auto_start_parse = False
        self._skip_parse_confirm = False
    
    def show(self, initial_files: dict = None, auto_start_parse: bool = False, skip_parse_confirm: bool = False) -> None:
        """팝업 표시.

        Args:
            initial_files: {'DO': 경로} 등 사전 지정 파일
            auto_start_parse: 팝업 오픈 직후 자동 파싱 시작
            skip_parse_confirm: 자동 파싱 시 확인 팝업 생략
        """
        self._initial_files = initial_files or {}
        self._auto_start_parse = bool(auto_start_parse)
        self._skip_parse_confirm = bool(skip_parse_confirm)
        # 초기 파일이 있으면 해당 폴더를 다음 파일 선택의 시작 폴더로 사용
        try:
            for _p in self._initial_files.values():
                if _p and os.path.exists(_p):
                    _d = os.path.dirname(_p)
                    if _d and os.path.isdir(_d):
                        self._last_selected_dir = _d
                        break
        except Exception as e:
            logger.debug(f"초기 폴더 경로 설정 무시: {e}")
        # 새 세트 시작 전 메인 업로드2(파싱 미리보기) 화면은 항상 비운다.
        self._clear_preview_from_main()
        self._create_dialog()
        if self._auto_start_parse and self.file_paths:
            self.dialog.after(250, self._start_parsing)

    def _apply_initial_files(self) -> None:
        """초기 전달 파일을 UI/내부 상태에 반영."""
        if not getattr(self, "_initial_files", None):
            return
        for doc_type, path in self._initial_files.items():
            if doc_type not in self.file_labels or not path:
                continue
            if not os.path.exists(path):
                continue
            self.file_paths[doc_type] = path
            self.file_labels[doc_type].configure(text=os.path.basename(path))
            self.check_labels[doc_type].configure(text="☑")
    
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
        self.dialog.title("📥 입고 — SQM v6.2.3")
        self.dialog.minsize(700, 320)
        apply_modal_window_options(self.dialog)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        try:
            # 컴팩트 창: 업로드3 위치 느낌(메인 우상단)에 배치
            self.dialog.geometry("820x360")
            self.dialog.update_idletasks()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            x = px + max(0, pw - 840)
            y = py + 78
            self.dialog.geometry(f"820x360+{x}+{y}")
        except Exception:
            self.dialog.geometry(DialogSize.get_geometry(self.parent, 'medium'))
            center_dialog(self.dialog, self.parent)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        main = ttk.Frame(self.dialog, padding=6)
        main.pack(fill=BOTH, expand=YES)
        
        # ═══════════════════════════════════════════════════════════
        # 1. 상단: 4종 서류 선택(2x2) + 실행 버튼(가시성 개선)
        # ═══════════════════════════════════════════════════════════
        file_frame = ttk.LabelFrame(main, text="📄 서류 선택", padding=6)
        file_frame.pack(fill=X, pady=(0, 4))
        for i in range(2):
            file_frame.columnconfigure(i, weight=1, uniform='doc')

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
            row = idx // 2
            col = idx % 2
            cell = ttk.Frame(file_frame)
            cell.grid(row=row, column=col, sticky='ew', padx=3, pady=3)
            
            _cell_fg = ThemeColors.get('text_primary', _os_dark)
            top = ttk.Frame(cell)
            top.pack(fill=X)
            lbl = ttk.Label(
                top, text=short_names.get(doc_type, ''),
                font=('맑은 고딕', 11, 'bold'),
                foreground=_cell_fg
            )
            lbl.pack(side=LEFT, padx=(2, 4))
            self._attach_doc_tooltip(lbl, _tooltips.get(doc_type, ''))

            btn_sel = tk.Button(
                top, text="📂 선택",
                command=lambda dt=doc_type: self._select_file(dt),
                font=('맑은 고딕', 10, 'bold'),
                bg=ThemeColors.get('btn_neutral', _os_dark), fg=ThemeColors.get('badge_text', _os_dark),
                padx=6, pady=2, cursor='hand2', bd=0
            )
            btn_sel.pack(side=RIGHT, padx=(0, 2))
            _req = '(필수)' if required else '(선택)'
            self._attach_doc_tooltip(btn_sel, f"클릭하여 {doc_name} 파일 선택 {_req}")

            check_label = ttk.Label(top, text="☐", font=('맑은 고딕', 11, 'bold'))
            check_label.pack(side=RIGHT, padx=(0, 6))
            self.check_labels[doc_type] = check_label

            file_label = ttk.Label(
                cell, text="", foreground=_cell_fg,
                font=('맑은 고딕', 10), anchor='w'
            )
            file_label.pack(fill=X, padx=(2, 2), pady=(1, 0))
            self.file_labels[doc_type] = file_label

        # 드래그앤드롭/캡처 이미지 등 초기 파일 지정
        self._apply_initial_files()

        # 실행 컨트롤 바 (업로드4 과밀 해소)
        action_bar = ttk.Frame(main)
        action_bar.pack(fill=X, pady=(2, 4))

        self.btn_bundle_select = ttk.Button(
            action_bar, text="📁 4종 한 번에(복수선택)",
            command=self._select_all_docs_from_folder, width=14
        )
        self.btn_bundle_select.pack(side=LEFT, padx=(0, 4))
        self._attach_doc_tooltip(
            self.btn_bundle_select,
            "PDF/이미지 파일을 여러 개 선택하면 자동으로 4종(PL/INV/BL/DO)을 매칭합니다. (미선택 시 폴더 선택 폴백)"
        )

        self.btn_parse = ttk.Button(
            action_bar, text="▶ 파싱 시작",
            command=self._start_parsing,
            state='disabled', width=10
        )
        self.btn_parse.pack(side=LEFT, padx=(0, 4))
        self._attach_doc_tooltip(self.btn_parse,
            "선택한 서류를 분석합니다\n\n• Packing List → LOT, 수량, 중량 추출\n• Invoice, FA → SAP번호, 금액 추출\n• Bill of Loading → BL번호, 선박, 일정 추출\n• Delivery Order → 인도장소, Free Time 추출")

        self.btn_reparse = ttk.Button(
            action_bar, text="↻ 다시 파싱",
            command=self._reparse_with_current_files,
            state='disabled', width=10
        )
        self.btn_reparse.pack(side=LEFT, padx=(0, 8))
        self._attach_doc_tooltip(
            self.btn_reparse,
            "이미 선택한 동일 파일로 재파싱합니다.\n파일을 다시 선택하지 않아도 됩니다."
        )
        
        self.parse_hint = ttk.Label(
            action_bar, text="",
            foreground=ThemeColors.get('text_primary', _os_dark), font=('맑은 고딕', 10, 'bold')
        )
        self.parse_hint.pack(side=LEFT, padx=(4, 0))
        self._update_parse_hint()

        # 자동 파싱 옵션은 기능만 유지(체크 UI 제거)
        self._var_auto_parse_after_bundle = tk.BooleanVar(value=True)
        self._var_skip_confirm_on_auto_parse = tk.BooleanVar(value=True)
        
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
        self._progress_inline_stopwatch = ttk.Label(
            self._progress_inline_frame,
            text="⏱ 00:00",
            font=('맑은 고딕', 11, 'bold'),
            foreground=ThemeColors.get('statusbar_progress', _pop_dark)
        )
        self._progress_inline_stopwatch.pack(anchor='w', pady=(2, 0))
        _row2 = ttk.Frame(self._progress_inline_frame)
        _row2.pack(fill=X)
        self._progress_inline_pct_elapsed = ttk.Label(_row2, text="", font=('맑은 고딕', 10), foreground=ThemeColors.get('text_secondary', _pop_dark))
        self._progress_inline_pct_elapsed.pack(side=tk.RIGHT)
        
        _tree_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        
        # ═══════════════════════════════════════════════════════════
        # 4. 하단 한 줄 — 업로드5: 폰트 통일(15), 업로드6: 합계 가운데 배치
        # [엑셀][DB 업로드]  (합계: ... 가운데)  [취소]
        # ═══════════════════════════════════════════════════════════
        btn_frame = ttk.Frame(main)
        btn_frame.pack(side=BOTTOM, fill=X, pady=(8, 0))
        
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
        self._last_parse_elapsed_text = ""
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
            if self.btn_reparse:
                self.btn_reparse.config(state='disabled')
        else:
            if self.btn_parse:
                self.btn_parse.config(state='normal')
            if self.btn_reparse:
                self.btn_reparse.config(state='normal')
            self.parse_hint.config(
                text=f"총 4개 중 {n}개 업로드되었습니다.",
                foreground=ThemeColors.get('text_primary', _hint_dark)
            )

    def _reparse_with_current_files(self) -> None:
        """파일 재선택 없이 현재 file_paths로 재파싱."""
        if 'PACKING_LIST' not in self.file_paths:
            from ..utils.custom_messagebox import CustomMessageBox
            CustomMessageBox.showwarning(self.dialog, "재파싱 불가", "Packing List 파일이 필요합니다.")
            return
        try:
            from ..utils.custom_messagebox import CustomMessageBox
            ok = CustomMessageBox.askyesno(
                self.dialog,
                "재파싱 확인",
                "기존 파싱 결과를 덮어쓰고 재파싱합니다.\n\n계속하시겠습니까?"
            )
        except (ImportError, ModuleNotFoundError):
            from tkinter import messagebox as msgbox
            ok = msgbox.askyesno(
                "재파싱 확인",
                "기존 파싱 결과를 덮어쓰고 재파싱합니다.\n\n계속하시겠습니까?"
            )
        if not ok:
            return
        self._start_parsing()
    
    def _select_file(self, doc_type: str):
        """서류별 파일 선택"""
        type_names = {
            'PACKING_LIST': 'Packing List',
            'INVOICE': 'Invoice, FA',
            'BL': 'Bill of Loading',
            'DO': 'Delivery Order',
        }
        
        # 직전에 선택한 폴더를 계속 열어 파일 선택 시간을 단축한다.
        initial_dir = ""
        try:
            if self._last_selected_dir and os.path.isdir(self._last_selected_dir):
                initial_dir = self._last_selected_dir
            elif doc_type in self.file_paths:
                prev_dir = os.path.dirname(self.file_paths.get(doc_type, ""))
                if prev_dir and os.path.isdir(prev_dir):
                    initial_dir = prev_dir
        except Exception as e:
            logger.debug(f"초기 폴더 계산 무시: {e}")

        file_path = filedialog.askopenfilename(
            parent=self.dialog,
            title=f"{type_names.get(doc_type, doc_type)} 파일 선택",
            initialdir=initial_dir if initial_dir else None,
            filetypes=[
                ("PDF files", "*.pdf"),
                ("Image (D/O 캡처)", "*.png *.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return

        try:
            selected_dir = os.path.dirname(file_path)
            if selected_dir and os.path.isdir(selected_dir):
                self._last_selected_dir = selected_dir
        except Exception as e:
            logger.debug(f"선택 폴더 저장 무시: {e}")
        
        self.file_paths[doc_type] = file_path
        fname = os.path.basename(file_path)
        
        # UI 업데이트
        self.file_labels[doc_type].config(text=fname, foreground=ThemeColors.get('text_primary', ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))))
        self.check_labels[doc_type].config(text="✅")
        
        self._log(f"📂 {doc_type}: {fname}")
        
        # 파싱 버튼 활성화 조건: PL 필수
        self._update_parse_hint()

    def _detect_inbound_docs_local(self, folder: str, file_names: list) -> dict:
        """팝업 내부용 4종 서류 자동 탐지(파일명 키워드)."""
        keyword_map = {
            "PACKING_LIST": ["packing", "pl", "포장", "명세서"],
            "INVOICE": ["invoice", "fa", "송장"],
            "BL": ["seawaybill", "sea waybill", "billoflading", "bill of lading", "b/l", "bl", "선하"],
            "DO": ["delivery", "d/o", "do", "인도"],
        }
        ext_allow = {".pdf", ".png", ".jpg", ".jpeg"}
        bucket = {k: [] for k in keyword_map}
        for name in file_names:
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in ext_allow:
                continue
            key_name = re.sub(r"[\s_\-]+", " ", name.lower())
            for doc_type, keys in keyword_map.items():
                if any(k in key_name for k in keys):
                    bucket[doc_type].append((os.path.getmtime(path), path))
        detected = {}
        for doc_type, candidates in bucket.items():
            if not candidates:
                continue
            candidates.sort(key=lambda x: x[0], reverse=True)
            detected[doc_type] = candidates[0][1]
        return detected

    def _detect_inbound_docs_from_paths(self, file_paths: list) -> dict:
        """파일 다중선택 결과(경로 목록)에서 4종 자동 매칭."""
        keyword_map = {
            "PACKING_LIST": ["packing", "pl", "포장", "명세서"],
            "INVOICE": ["invoice", "fa", "송장"],
            "BL": ["seawaybill", "sea waybill", "billoflading", "bill of lading", "b/l", "bl", "선하"],
            "DO": ["delivery", "d/o", "do", "인도"],
        }
        ext_allow = {".pdf", ".png", ".jpg", ".jpeg"}
        bucket = {k: [] for k in keyword_map}
        for path in file_paths or []:
            if not path or not os.path.isfile(path):
                continue
            name = os.path.basename(path)
            ext = os.path.splitext(name)[1].lower()
            if ext not in ext_allow:
                continue
            key_name = re.sub(r"[\s_\-]+", " ", name.lower())
            for doc_type, keys in keyword_map.items():
                if any(k in key_name for k in keys):
                    bucket[doc_type].append((os.path.getmtime(path), path))
        detected = {}
        for doc_type, candidates in bucket.items():
            if not candidates:
                continue
            candidates.sort(key=lambda x: x[0], reverse=True)
            detected[doc_type] = candidates[0][1]
        return detected

    def _select_all_docs_from_folder(self) -> None:
        """4종 자동 매핑: 파일 다중선택 우선, 취소 시 폴더 선택 fallback."""
        initial_dir = self._last_selected_dir if self._last_selected_dir and os.path.isdir(self._last_selected_dir) else None
        selected_files = ()
        try:
            selected_files = filedialog.askopenfilenames(
                parent=self.dialog,
                title="4종 서류 파일 선택 (복수선택)",
                initialdir=initial_dir,
                filetypes=[
                    ("지원 파일", "*.pdf *.png *.jpg *.jpeg"),
                    ("PDF files", "*.pdf"),
                    ("Image files", "*.png *.jpg *.jpeg"),
                    ("All files", "*.*"),
                ],
            )
        except Exception as e:
            logger.warning(f"4종 파일 다중선택 창 오류(폴더 선택으로 전환): {e}")
        detected = self._detect_inbound_docs_from_paths(list(selected_files or []))
        if not detected:
            folder = filedialog.askdirectory(
                parent=self.dialog,
                title="4종 서류 폴더 선택",
                initialdir=initial_dir,
            )
            if not folder:
                return
            try:
                file_names = os.listdir(folder)
            except Exception as e:
                from ..utils.custom_messagebox import CustomMessageBox
                CustomMessageBox.showerror(self.dialog, "폴더 읽기 실패", str(e))
                return
            if not file_names:
                return
            if self.app and hasattr(self.app, "_detect_inbound_docs_from_folder"):
                detected = self.app._detect_inbound_docs_from_folder(folder, file_names)
            else:
                detected = self._detect_inbound_docs_local(folder, file_names)
            self._last_selected_dir = folder
        elif selected_files:
            first_dir = os.path.dirname(selected_files[0])
            if first_dir and os.path.isdir(first_dir):
                self._last_selected_dir = first_dir
        if not detected:
            return
        _is_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        _fg = ThemeColors.get('text_primary', _is_dark)
        for doc_type, file_path in detected.items():
            if doc_type not in self.file_labels:
                continue
            self.file_paths[doc_type] = file_path
            self.file_labels[doc_type].config(text=os.path.basename(file_path), foreground=_fg)
            self.check_labels[doc_type].config(text="✅")
            self._log(f"📂 {doc_type}: {os.path.basename(file_path)}")
        self._log_selected_doc_paths()
        missing_required = [k for k in ("PACKING_LIST", "INVOICE", "BL") if k not in detected]
        if missing_required:
            from ..utils.custom_messagebox import CustomMessageBox
            miss_txt = ", ".join(missing_required)
            CustomMessageBox.showwarning(self.dialog, "일부 서류 미탐지", f"자동 탐지 누락: {miss_txt}")
        self._update_parse_hint()
        if self._var_auto_parse_after_bundle and self._var_auto_parse_after_bundle.get():
            self.dialog.after(120, self._start_parsing_after_bundle)

    def _start_parsing_after_bundle(self) -> None:
        """4종 일괄 선택 직후 자동 파싱."""
        if not self.dialog or not self.dialog.winfo_exists():
            return
        if 'PACKING_LIST' not in self.file_paths:
            return
        if self.btn_parse and self.btn_parse.instate(['disabled']):
            return
        self._skip_parse_confirm = bool(
            self._var_skip_confirm_on_auto_parse and self._var_skip_confirm_on_auto_parse.get()
        )
        # 사용자 요청: 4종 자동 파싱이어도 D/O 미첨부 시에는
        # 기존과 동일한 "입고 서류 확인" 안내를 파싱 전에 반드시 보여준다.
        if 'DO' not in self.file_paths:
            self._skip_parse_confirm = False
        self._start_parsing()

    def _log_selected_doc_paths(self) -> None:
        """선택된 4종 경로를 한 번에 출력."""
        lines = ["📌 선택 파일 경로(4종)"]
        for key in ("PACKING_LIST", "INVOICE", "BL", "DO"):
            path = str(self.file_paths.get(key, "") or "").strip()
            if path:
                lines.append(f"  - {key}: {path}")
            else:
                lines.append(f"  - {key}: (미선택)")
        self._log_safe("\n".join(lines))

    def _build_crosscheck_guidance(self, xc) -> str:
        """크로스체크 불일치 시 의심 원인/체크리스트 안내."""
        if not xc or bool(getattr(xc, 'is_clean', True)):
            return ""
        items = list(getattr(xc, 'items', []) or [])
        fields = {str(getattr(i, 'field_name', '') or '').strip() for i in items}
        has_lot_mismatch = (
            "LOT 개수" in fields
            or "LOT 번호 (PL Only)" in fields
            or "LOT 번호 (Invoice Only)" in fields
        )
        if not has_lot_mismatch:
            return ""
        return (
            "🧭 의심 원인(자동 분석)\n"
            "- 문서 불일치: PL/Invoice/BL이 같은 선적 세트가 아닐 수 있습니다.\n"
            "- 추출 누락: Invoice 또는 PL에서 일부 LOT가 OCR/API 파싱에 누락됐을 수 있습니다.\n"
            "\n"
            "✅ 바로 확인 체크리스트\n"
            "1) 선택한 파일 3종의 SAP NO/선적번호/폴더명이 동일한지 확인\n"
            "2) Invoice 원문 LOT 목록이 PL LOT 개수와 일치하는지 확인\n"
            "3) 팝업에 표시된 PL Only / Invoice Only LOT를 원문에서 직접 대조\n"
            "4) 스캔 품질(회전/잘림/저해상도) 문제면 PDF 원본으로 재선택 후 재파싱\n"
            "5) 동일 증상이 반복되면 해당 서류 세트만 분리해 1건 단독 파싱"
        )

    def _parse_lot_mismatch_sets(self) -> dict:
        """크로스체크 결과에서 Invoice/PL 전용 LOT 목록 추출."""
        out = {"invoice_only": [], "pl_only": []}
        xc = getattr(self, "_cross_check_result", None)
        if not xc:
            return out
        lot_re = re.compile(r"\b\d{10}\b")
        try:
            for item in list(getattr(xc, "items", []) or []):
                field = str(getattr(item, "field_name", "") or "").strip()
                msg = str(getattr(item, "message", "") or "")
                lots = list(dict.fromkeys(lot_re.findall(msg)))
                if not lots:
                    continue
                if field == "LOT 번호 (Invoice Only)":
                    out["invoice_only"].extend(lots)
                elif field == "LOT 번호 (PL Only)":
                    out["pl_only"].extend(lots)
        except Exception as e:
            logger.debug(f"LOT 불일치 목록 추출 스킵: {e}")
        out["invoice_only"] = list(dict.fromkeys(out["invoice_only"]))
        out["pl_only"] = list(dict.fromkeys(out["pl_only"]))
        return out

    def _open_source_doc_for_lot(self, doc_type: str, lot_no: str) -> None:
        """LOT 클릭 시 해당 원문 파일 열기."""
        # 클릭 즉시 LOT 번호를 클립보드에 복사
        try:
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.clipboard_clear()
                self.dialog.clipboard_append(str(lot_no))
        except Exception as e:
            logger.debug(f"LOT 클립보드 복사 스킵: {e}")

        path = str(self.file_paths.get(doc_type, "") or "").strip()
        if not path or not os.path.exists(path):
            try:
                from ..utils.custom_messagebox import CustomMessageBox
                CustomMessageBox.showwarning(self.dialog, "원문 파일 없음", f"{doc_type} 원문 파일을 찾을 수 없습니다.\nLOT: {lot_no}")
            except Exception:
                pass
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen([path], shell=True)
            self._log_safe(f"📂 원문 열기: {doc_type} (LOT {lot_no}) / 클립보드 복사 완료")
        except Exception as e:
            logger.error(f"원문 파일 열기 실패: {e}")

    def _show_warning_with_lot_links(self, warn_msg: str) -> None:
        """LOT 불일치가 있으면 LOT 클릭으로 원문 열기 가능한 경고창 표시."""
        lot_sets = self._parse_lot_mismatch_sets()
        has_links = bool(lot_sets["invoice_only"] or lot_sets["pl_only"])
        if not has_links:
            from ..utils.custom_messagebox import CustomMessageBox
            CustomMessageBox.showwarning(self.dialog, "파싱 결과 확인", warn_msg)
            return

        popup = tk.Toplevel(self.dialog)
        popup.title("파싱 결과 확인")
        popup.transient(self.dialog)
        popup.grab_set()
        apply_modal_window_options(popup)
        popup.geometry("620x520")
        try:
            center_dialog(popup, self.dialog)
        except Exception as e:
            logger.debug(f"경고창 중앙정렬 스킵: {e}")

        frame = ttk.Frame(popup, padding=10)
        frame.pack(fill=BOTH, expand=YES)

        ttk.Label(
            frame,
            text="⚠️ 불일치 서류의 LOT만 표시합니다. LOT 클릭 시 원문 열기 + 번호 자동 복사",
            font=('맑은 고딕', 10, 'bold')
        ).pack(anchor='w', pady=(0, 6))

        mismatch_lines = []
        for ln in str(warn_msg or "").splitlines():
            s = ln.strip()
            if not s:
                continue
            if ("LOT 개수" in s) or ("LOT 번호 (Invoice Only)" in s) or ("LOT 번호 (PL Only)" in s):
                mismatch_lines.append(s)
        if not mismatch_lines:
            mismatch_lines = ["LOT 불일치가 감지되었습니다. 아래 목록을 확인하세요."]

        txt = tk.Text(frame, height=4, wrap='word')
        txt.pack(fill=X, pady=(0, 8))
        txt.insert('1.0', "\n".join(mismatch_lines))
        txt.configure(state='disabled')

        lots_wrap = ttk.Frame(frame)
        lots_wrap.pack(fill=BOTH, expand=YES)

        if lot_sets["invoice_only"]:
            inv_box = ttk.LabelFrame(lots_wrap, text="Invoice Only LOT (클릭 시 Invoice 열기)", padding=6)
            inv_box.pack(fill=X, pady=(0, 8))
            for lot in lot_sets["invoice_only"]:
                tk.Button(
                    inv_box, text=lot, command=lambda l=lot: self._open_source_doc_for_lot("INVOICE", l),
                    bg="#d97706", fg="white", activebackground="#b45309", activeforeground="white",
                    relief='flat', padx=8, pady=3, cursor='hand2'
                ).pack(side=LEFT, padx=3, pady=2)

        if lot_sets["pl_only"]:
            pl_box = ttk.LabelFrame(lots_wrap, text="PL Only LOT (클릭 시 Packing List 열기)", padding=6)
            pl_box.pack(fill=X, pady=(0, 8))
            for lot in lot_sets["pl_only"]:
                tk.Button(
                    pl_box, text=lot, command=lambda l=lot: self._open_source_doc_for_lot("PACKING_LIST", l),
                    bg="#1d4ed8", fg="white", activebackground="#1e40af", activeforeground="white",
                    relief='flat', padx=8, pady=3, cursor='hand2'
                ).pack(side=LEFT, padx=3, pady=2)

        ttk.Button(frame, text="확인", command=popup.destroy).pack(anchor='e')
    
    # ═══════════════════════════════════════════════════════════
    # 파싱
    # ═══════════════════════════════════════════════════════════
    
    def _start_parsing(self) -> None:
        """v3.8.9: 파싱 시작 — 입고 서류 현황 안내 후 진행 확인"""
        self._last_parse_elapsed_text = ""
        # 한 세트 파싱 시작 시 이전 업로드2 표시를 먼저 클리어
        self._clear_preview_from_main()
        # 두 번째 파싱부터도 시작 순간 기존 표시 데이터가 남지 않도록 즉시 반영
        if getattr(self, 'app', None) and hasattr(self.app, '_set_parsing_preview_data'):
            try:
                self.app._set_parsing_preview_data(None)
                if hasattr(self.app, 'root') and self.app.root and self.app.root.winfo_exists():
                    self.app.root.update_idletasks()
            except Exception as e:
                logger.debug(f"파싱 시작 전 메인 미리보기 즉시 클리어 스킵: {e}")
        self._reset_parse_state_for_new_run()
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
        
        proceed = True
        if not self._skip_parse_confirm:
            from ..utils.custom_messagebox import CustomMessageBox
            proceed = CustomMessageBox.askyesno(
                self.dialog,
                "입고 서류 확인",
                msg
            )
        self._skip_parse_confirm = False
        if not proceed:
            return
        
        if missing:
            self._update_progress(0, f"ℹ️ {', '.join(missing)} 미선택 — 해당 정보 생략")
        self._log_selected_doc_paths()
        
        self.btn_parse.config(state='disabled')
        if self.btn_reparse:
            self.btn_reparse.config(state='disabled')
        self._show_progress_inline()
        
        thread = threading.Thread(
            target=self._parse_thread,
            daemon=True
        )
        thread.start()

    def _reset_parse_state_for_new_run(self) -> None:
        """재파싱/재실행 시 이전 상태 잔존으로 인한 누락을 방지."""
        self.parsed_results = {}
        self.preview_data = []
        self._original_preview_data = []
        self._cross_check_result = None
        self._edited_rows = set()
        self._undo_stack = []
        self._redo_stack = []
        self._view_indices = []
        self._sort_col = None
        self._sort_desc = False
        self._preview_anchor = (0, 0)
        try:
            if self.filter_bar:
                self.filter_bar._reset_filters()
        except Exception as e:
            logger.debug(f"필터 초기화 스킵: {e}")
        try:
            if self.tree and self.tree.winfo_exists():
                for item in self.tree.get_children():
                    self.tree.delete(item)
        except Exception as e:
            logger.debug(f"미리보기 초기화 스킵: {e}")
        self._update_summary()
        self._update_undo_redo_buttons()
    
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
        if getattr(self, '_progress_inline_stopwatch', None):
            self._progress_inline_stopwatch.config(text="⏱ 00:00")
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
        stopwatch = getattr(self, '_progress_inline_stopwatch', None)
        if stopwatch and stopwatch.winfo_ismapped():
            mm, ss = divmod(secs, 60)
            stopwatch.config(text=f"⏱ {mm:02d}:{ss:02d}")
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
            self._cross_check_result = None
            
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
            else:
                dup_lots = list(getattr(pl_result, 'duplicate_skipped_lot_nos', []) or [])
                if dup_lots:
                    preview = ", ".join(dup_lots[:10])
                    if len(dup_lots) > 10:
                        preview += f" 외 {len(dup_lots) - 10}건"
                    _warnings.append(f"⚠️ Packing List: 중복으로 스킵된 LOT {len(dup_lots)}건 — {preview}")
            if not inv_result or not getattr(inv_result, 'sap_no', None):
                _warnings.append("⚠️ Invoice: SAP번호 추출 실패 — 수동 입력 필요")
            if not bl_result or not getattr(bl_result, 'bl_no', None):
                _warnings.append("⚠️ B/L: BL번호 추출 실패 — 수동 입력 필요")

            # v6.2.1: 4종 서류 크로스 체크 엔진 (읽기 전용 검증)
            try:
                from parsers.cross_check_engine import cross_check_documents
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
                    for item in xc.items:
                        _warnings.append(str(item))
                    if xc.has_critical:
                        _warnings.insert(
                            0,
                            f"🚫 심각한 불일치 {xc.critical_count}건 — 서류 확인 후 재파싱 권장",
                        )
                else:
                    self._log_safe("✅ 4종 서류 크로스 체크 통과 — 불일치 없음")
            except (ImportError, Exception) as e:
                logger.debug(f"[CrossCheck] 원스톱 크로스 체크 스킵: {e}")

            _guide = self._build_crosscheck_guidance(getattr(self, '_cross_check_result', None))
            if _guide:
                _warnings.append("")
                _warnings.append(_guide)
            
            if _warnings:
                _warn_msg = "\n".join(_warnings)
                self._log_safe(f"\n{'='*40}\n{_warn_msg}\n{'='*40}")
                # GUI 경고
                def _show_warn():
                    self._show_warning_with_lot_links(_warn_msg)
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
            
            # Phase 0-A(Part3): Gate Validation (QC 표시 + 업로드 버튼 상태 반영)
            try:
                self._run_gate_validation(show_popup=True)
            except Exception as _e:
                logger.debug(f"Gate validation skipped: {_e}")

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
            self._last_parse_elapsed_text = elapsed_str
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
        return set(self._preview_col_names()) - {'no', 'status', 'qc_status', 'qc_reason'}

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

    # v6.2.7: 제품 마스터 콤보박스 생성
    def _create_product_combobox(self, current_val, x, y, w, h):
        """product 열 더블클릭 시 제품 마스터 드롭다운 표시."""
        try:
            from .product_master_helper import get_product_choices, parse_product_choice
            choices = get_product_choices(self.engine.db)
        except Exception:
            choices = ['LITHIUM CARBONATE', 'NICKEL SULFATE HEXAHYDRATE']
        
        combo = ttk.Combobox(self.tree, values=choices, font=('맑은 고딕', 10),
                             state='normal')
        
        # 현재 값과 매칭되는 항목 찾기
        current_upper = current_val.strip().upper()
        matched = False
        for i, ch in enumerate(choices):
            if current_upper in ch.upper():
                combo.current(i)
                matched = True
                break
        if not matched:
            combo.set(current_val)
        
        combo.place(x=x, y=y, width=max(w, 300), height=h)
        
        # 선택 시 product_code 자동 연동
        def _on_product_selected(event=None):
            selected = combo.get()
            try:
                from .product_master_helper import parse_product_choice
                code, full_name = parse_product_choice(selected)
                combo.set(full_name)  # 풀네임만 셀에 저장
                
                # product_code 자동 업데이트
                if code and self._editing_item:
                    row_id = self._editing_item[0]
                    try:
                        row_idx = self._item_to_source_index(row_id)
                        if 0 <= row_idx < len(self.preview_data):
                            self.preview_data[row_idx]['product_code'] = code
                    except (ValueError, TypeError):
                        pass
            except Exception:
                pass
        
        combo.bind('<<ComboboxSelected>>', _on_product_selected)
        return combo

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
        
        # v6.2.7: product 열은 제품 마스터 콤보박스
        if col_name == 'product':
            entry = self._create_product_combobox(current_val, x, y, w, h)
        else:
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
            # v6.2.7: product 변경 시 product_code 자동 연동
            if col_name == 'product' and row_idx < len(self.preview_data):
                try:
                    from .product_master_helper import auto_detect_product_code
                    detected_code = auto_detect_product_code(self.engine.db, new_val)
                    if detected_code:
                        self.preview_data[row_idx]['product_code'] = detected_code
                except Exception:
                    pass
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
        xc = getattr(self, '_cross_check_result', None)
        xc_lot_levels = {}
        xc_global_level = None
        xc_active = bool(xc) and not bool(getattr(xc, 'is_clean', True))
        if xc_active:
            # 크로스체크가 있을 때만 LOT 레벨을 리프레시 1회당 1번 계산해 재사용한다.
            if hasattr(xc, 'get_lot_levels'):
                try:
                    xc_lot_levels = xc.get_lot_levels() or {}
                except Exception as _e:
                    logger.debug(f"onestop_inbound: {_e}")
                    xc_lot_levels = {}
            xc_global_level = getattr(xc, 'global_level', None)

        self._view_indices = self._build_view_indices()
        for pos, src_idx in enumerate(self._view_indices):
            row = self.preview_data[src_idx]
            row['no'] = str(src_idx + 1)
            values = self._row_display_values(row)
            base_tag = 'even' if pos % 2 == 0 else 'odd'
            if src_idx in self._edited_rows:
                tag = 'edited'
            elif xc_active:
                lot_no = (row.get('lot_no') or '').strip()
                lot_level = xc_lot_levels.get(lot_no) if lot_no else None
                effective = None
                if lot_level is not None and xc_global_level is not None:
                    try:
                        effective = max(lot_level, xc_global_level)
                    except Exception as _e:
                        logger.debug(f"onestop_inbound: {_e}")
                        effective = lot_level
                elif lot_level is not None:
                    effective = lot_level
                elif xc_global_level is not None:
                    effective = xc_global_level

                try:
                    level_num = int(effective) if effective is not None else 0
                except (TypeError, ValueError) as _e:
                    logger.debug(f"onestop_inbound: {_e}")
                    level_num = 0

                if level_num >= 3:
                    tag = 'xc_critical'
                elif level_num == 2:
                    tag = 'xc_warning'
                elif level_num == 1:
                    tag = 'xc_info'
                elif hasattr(xc, 'get_row_tag') and lot_no:
                    # 구버전 객체 호환: 계산 실패 시 기존 API로 최종 시도
                    try:
                        tag = xc.get_row_tag(lot_no) or base_tag
                    except Exception as _e:
                        logger.debug(f"onestop_inbound: {_e}")
                        tag = base_tag
                else:
                    tag = base_tag
            else:
                tag = base_tag
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
    
    
    # ═══════════════════════════════════════════════════════════
    # Phase 0-A (Part 3) — Validation Gate + SUSPECT Routing (skeleton)
    #   - OK / SUSPECT / ERROR 를 미리보기(QC 컬럼)로 표시
    #   - ERROR: 업로드 버튼 비활성화(업무 하드스톱), 단 업로드 버튼에서 최종 검증도 재수행됨
    #   - SUSPECT: 업로드는 가능(사용자 확인), 추후 Review Center(Phase B)로 연결
    # ═══════════════════════════════════════════════════════════

    def _run_gate_validation(self, *, show_popup: bool = False) -> dict:
        """미리보기 데이터 기반 QC 검증.
        Returns: dict(level='OK'|'SUSPECT'|'ERROR', errors=[...], warnings=[...])
        """
        report = {"level": "OK", "errors": [], "warnings": []}

        rows = list(getattr(self, "preview_data", []) or [])
        if not rows:
            self._gate_report = report
            return report

        # 1) 기본값 세팅
        for r in rows:
            r["qc_status"] = "OK"
            r["qc_reason"] = ""

        # 2) 프리플라이트(필수필드/형식) — InboundUploadMixin에 구현된 검증을 재사용
        try:
            if hasattr(self, "_preflight_validate_preview_data"):
                errs = list(self._preflight_validate_preview_data() or [])
            else:
                errs = []
        except Exception as e:
            errs = [f"검증 엔진 오류: {e}"]

        # 행 번호 매핑 ("3행: ..." 형태 지원)
        row_err_map = {}  # idx(1-based) -> [msg...]
        for msg in errs:
            m = re.match(r"^(\d+)행\s*:\s*(.+)$", str(msg).strip())
            if m:
                idx = int(m.group(1))
                row_err_map.setdefault(idx, []).append(m.group(2))
            else:
                report["errors"].append(str(msg))

        if errs:
            report["level"] = "ERROR"
            report["errors"].extend([str(x) for x in errs])

            for idx, r in enumerate(rows, 1):
                if idx in row_err_map:
                    r["qc_status"] = "ERROR"
                    r["qc_reason"] = "; ".join([str(x) for x in row_err_map.get(idx, [])])

        # 3) 크로스 체크 결과 기반 SUSPECT 표시 (치명/경고/LOT 불일치 등)
        try:
            xc = getattr(self, "_cross_check_result", None)
            mismatch = self._parse_lot_mismatch_sets() if hasattr(self, "_parse_lot_mismatch_sets") else {"invoice_only": [], "pl_only": []}
            suspect_lots = set((mismatch.get("invoice_only") or []) + (mismatch.get("pl_only") or []))

            has_critical = bool(getattr(xc, "has_critical", False))
            has_any_mismatch = bool(suspect_lots)

            if (has_critical or has_any_mismatch) and report["level"] != "ERROR":
                report["level"] = "SUSPECT"

            if has_critical:
                report["warnings"].append(f"크로스 체크 CRITICAL {getattr(xc, 'critical_count', 0)}건")
            if has_any_mismatch:
                report["warnings"].append(f"LOT 불일치(Invoice Only/PL Only) {len(suspect_lots)}건")

            if report["level"] == "SUSPECT":
                for r in rows:
                    lot = str(r.get("lot_no", "") or "").strip()
                    if has_any_mismatch and lot in suspect_lots:
                        r["qc_status"] = "SUSPECT"
                        if not r.get("qc_reason"):
                            r["qc_reason"] = "LOT 불일치"
                    elif r.get("qc_status") == "OK":
                        # mismatch가 없고 critical만 있는 경우: 전체를 SUSPECT로 표시
                        if has_critical and not has_any_mismatch:
                            r["qc_status"] = "SUSPECT"
                            if not r.get("qc_reason"):
                                r["qc_reason"] = "크로스체크 CRITICAL"
        except Exception as e:
            # 검증 실패는 SUSPECT로만 처리(업무 중단 방지)
            if report["level"] == "OK":
                report["level"] = "SUSPECT"
            report["warnings"].append(f"검증(크로스체크) 스킵: {e}")

        self._gate_report = report

        # 4) 업로드 버튼 상태 반영 (ERROR일 때만 하드스톱)
        try:
            if getattr(self, "btn_upload", None) and self.btn_upload.winfo_exists():
                if report["level"] == "ERROR":
                    self.btn_upload.config(state="disabled")
                else:
                    # required docs 조건은 기존 로직 유지
                    self.btn_upload.config(state="normal" if self._has_required_docs() else "disabled")
        except Exception:
            pass

        # 5) 요약 업데이트
        try:
            self._update_summary()
        except Exception:
            pass


        # 5-1) QC 리포트 자동 저장(운영 추적용) — 실패해도 흐름 유지
        try:
            self._save_qc_report(report)
        except Exception:
            pass

        # 6) 팝업(선택)
        if show_popup and report["level"] in ("SUSPECT", "ERROR"):
            title = "🔎 파싱 검증 결과"
            msg = [f"결과: {report['level']}"]
            if report["level"] == "ERROR":
                msg.append("")
                msg.append("❌ 필수값/형식 오류가 있어 DB 업로드가 차단되었습니다.")
            if report["errors"]:
                msg.append("")
                msg.append("오류 일부:")
                msg.extend(report["errors"][:12])
                if len(report["errors"]) > 12:
                    msg.append("... (더 있음)")
            if report["warnings"]:
                msg.append("")
                msg.append("경고:")
                msg.extend(report["warnings"][:12])
            try:
                msgbox.showwarning(title, "\n".join(msg))
            except Exception:
                pass

        return report



    def _save_qc_report(self, report: dict) -> None:
        """QC 결과를 CSV로 저장합니다. (운영 추적/재현용)
        - 저장 위치: <실행폴더>/reports/YYYY-MM-DD/
        - 파일명: inbound_qc_YYYYMMDD_HHMMSS.csv
        """
        try:
            base = os.path.dirname(os.path.abspath(sys.argv[0]))
        except Exception:
            base = os.getcwd()

        day = datetime.now().strftime("%Y-%m-%d")
        out_dir = os.path.join(base, "reports", day)
        os.makedirs(out_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inbound_qc_{ts}.csv"
        path = os.path.join(out_dir, filename)

        rows = list(getattr(self, "preview_data", []) or [])
        if not rows:
            return

        # 헤더: PREVIEW_COLUMNS + QC Reason
        cols = [c[0] for c in PREVIEW_COLUMNS]
        # 안전장치(구버전/이상키 대응)
        if "qc_reason" not in cols:
            cols.append("qc_reason")

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["qc_level", report.get("level", "")])
            w.writerow(["errors"] + (report.get("errors", []) or []))
            w.writerow(["warnings"] + (report.get("warnings", []) or []))
            w.writerow([])
            w.writerow([c.upper() for c in cols])
            for r in rows:
                w.writerow([str(r.get(c, "") or "") for c in cols])


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
            + (self._format_qc_summary() if hasattr(self, "_format_qc_summary") else "") + (f" | 파싱시간 {self._last_parse_elapsed_text}" if self._last_parse_elapsed_text else "")
        )
    

    def _show_success_and_close(self, count: int):
        def _close():
            if self.dialog and self.dialog.winfo_exists():
                _app = self.app if self.app else None
                _ask_more_inbound = False
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
                _msg = self._build_upload_summary_message(count)
                try:
                    from ..utils.custom_messagebox import CustomMessageBox
                    # 1) 업데이트 요약 확인
                    CustomMessageBox.showinfo(self.dialog, "업데이트 완료 요약", _msg)
                except (ImportError, ModuleNotFoundError):
                    CustomMessageBox.info(None, "완료", _msg)

                # 2) 사용자 확인 후 화면 데이터 정리 (업로드1/업로드2)
                self._reset_after_upload_success()

                # 3) 추가 입고 여부 확인
                try:
                    from ..utils.custom_messagebox import CustomMessageBox
                    _ask_more_inbound = CustomMessageBox.askyesno(
                        self.dialog,
                        "추가 입고 선택 (예=추가 입고 / 아니오=종료)",
                        "추가로 입고 작업을 하시겠습니까?\n\n"
                        "예: 추가 입고 화면을 다시 엽니다.\n"
                        "아니오: 이번 입고 프로세스를 종료합니다."
                    )
                except (ImportError, ModuleNotFoundError):
                    from tkinter import messagebox as msgbox
                    _ask_more_inbound = msgbox.askyesno(
                        "추가 입고 선택 (예=추가 입고 / 아니오=종료)",
                        "추가로 입고 작업을 하시겠습니까?\n\n"
                        "예: 추가 입고 화면을 다시 엽니다.\n"
                        "아니오: 이번 입고 프로세스를 종료합니다."
                    )

                self.dialog.destroy()
                
                # v3.8.9: 업로드 후 재고리스트 탭 이동 + 자동 새로고침
                # dialog.destroy() 후이므로 app.root.after 사용
                if _app:
                    try:
                        _root = getattr(_app, 'root', None)
                        if _root:
                            if hasattr(_app, 'notebook') and hasattr(_app, 'tab_inventory'):
                                _root.after(200, lambda: _app.notebook.select(_app.tab_inventory))
                            if hasattr(_app, '_deferred_refresh_main_tabs'):
                                _app._deferred_refresh_main_tabs(delay_ms=500)
                                logger.info("[onestop] 전체 탭 새로고침 예약 완료 (500ms)")
                            elif hasattr(_app, '_refresh_inventory'):
                                _root.after(500, _app._refresh_inventory)
                                logger.info("[onestop] 재고 새로고침 예약 완료 (500ms)")
                            if _ask_more_inbound and hasattr(_app, '_on_onestop_inbound'):
                                if hasattr(_app, '_reset_inventory_view_for_new_inbound'):
                                    _root.after(300, _app._reset_inventory_view_for_new_inbound)
                                _root.after(700, _app._on_onestop_inbound)
                                logger.info("[onestop] 추가 입고 요청으로 원스톱 입고 재오픈")
                            elif not _ask_more_inbound:
                                logger.info("[onestop] 추가 입고 없음 — 입고 프로세스 종료")
                    except (RuntimeError, ValueError) as e:
                        logger.debug(f"재고 새로고침 호출 실패: {e}")
        
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(100, _close)

    def _build_upload_summary_message(self, count: int) -> str:
        """업로드 완료 요약 문자열 생성."""
        rows = list(getattr(self, 'preview_data', []) or [])
        edited_cnt = len(getattr(self, '_edited_rows', set()) or set())
        sap_set = {str(r.get('sap_no', '') or '').strip() for r in rows if str(r.get('sap_no', '') or '').strip()}
        bl_set = {str(r.get('bl_no', '') or '').strip() for r in rows if str(r.get('bl_no', '') or '').strip()}
        cont_set = {str(r.get('container_no', '') or '').strip() for r in rows if str(r.get('container_no', '') or '').strip()}
        total_net = 0.0
        for r in rows:
            try:
                total_net += safe_float(r.get('net_weight', 0) or 0)
            except (ValueError, TypeError) as _e:
                logger.debug(f"onestop_inbound: {_e}")
        return (
            f"✅ {count}개 LOT 저장 완료\n\n"
            f"- 수정된 행: {edited_cnt}건\n"
            f"- SAP NO: {len(sap_set)}종\n"
            f"- BL NO: {len(bl_set)}종\n"
            f"- 컨테이너: {len(cont_set)}개\n"
            f"- 총 NET: {total_net:,.0f} kg"
        )

    def _reset_after_upload_success(self) -> None:
        """업로드 성공 후 로컬/메인 미리보기 데이터 정리."""
        try:
            self.preview_data = []
            self.parsed_results = {}
            self._original_preview_data = []
            self._cross_check_result = None
            self._edited_rows = set()
            self._undo_stack = []
            self._redo_stack = []
            self._view_indices = []
            if hasattr(self, '_update_summary'):
                self._update_summary()
            if hasattr(self, '_update_undo_redo_buttons'):
                self._update_undo_redo_buttons()
        except (RuntimeError, ValueError, TypeError, AttributeError) as e:
            logger.debug(f"업로드 후 로컬 미리보기 정리 실패: {e}")
        self._clear_preview_from_main()
    
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
            if self.dialog and self.dialog.winfo_exists():
                self._update_parse_hint()
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
