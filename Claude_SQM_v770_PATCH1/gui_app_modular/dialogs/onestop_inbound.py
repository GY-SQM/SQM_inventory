"""
SQM v3.8.4 — 원스톱 입고 팝업
4종 서류(PL, Invoice, BL, DO)를 한 화면에서:
  파일 선택 → 체크 표시 → 파싱 → 미리보기 → DB 업로드

작성일: 2025-02-06
"""
from engine_modules.constants import STATUS_AVAILABLE
import os
import time
import tkinter as tk
from tkinter import ttk, filedialog, BOTH, YES, X, Y, LEFT, RIGHT, BOTTOM, END, VERTICAL, HORIZONTAL
import logging
import threading
from datetime import datetime, timedelta, date as _date_type
from copy import deepcopy

# 비즈니스 기본값
from core.constants import DEFAULT_WAREHOUSE

from ..utils.ui_constants import (
    ThemeColors, DialogSize, center_dialog, apply_modal_window_options,
    setup_dialog_geometry_persistence,
)
from core.types import safe_float
from ..utils.tree_enhancements import HeaderFilterBar

# v5.8.7: DatePicker 달력 UI — gui_bootstrap 통일 (ttkbootstrap.DateEntry, 없으면 텍스트 입력 폴백)
from ..utils.gui_bootstrap import DateEntry, HAS_DATEENTRY

logger = logging.getLogger(__name__)


# 미리보기 컬럼 정의 — 종전 4개 파일 입고 테이블(재고 탭)과 동일한 열 순서
PREVIEW_COLUMNS = [
    ("no",               "NO",               50,  "center"),
    ("lot_no",           "LOT NO",          110,  "center"),
    ("sap_no",           "SAP NO",          110,  "center"),
    ("bl_no",            "BL NO",           150,  "center"),
    ("product",          "PRODUCT",         180,  "center"),
    ("status",           "STATUS",           80,  "center"),
    ("container_no",     "CONTAINER",       130,  "center"),
    ("product_code",     "CODE",            100,  "center"),
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
]

# v7.4.0: 서류 순서 BL→PL→INV→DO (BL 먼저 → 선사 감지 → 맞춤 힌트 적용)
DOC_TYPES = [
    ('BL',           '① Bill of Loading (선하증권)', True),
    ('PACKING_LIST', '② Packing List (포장명세서)', True),
    ('INVOICE',      '③ Invoice, FA (송장)',        True),
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
        # v7.8.0: 개별 재파싱 — 실패 서류 추적 + 재파싱 버튼 참조
        self._failed_doc_types = set()
        self._doc_reparse_buttons = {}
        # v6.4.0: 빠른 PDF 스캔 자동 파싱 플래그 (show() 호출 전 기본값)
        self._auto_start_parse   = False
        self._skip_parse_confirm = False
        # v6.4.0 PATCH_PACKAGE: compact 모드 — 원스톱 창은 작게, 파싱 결과는 메인 창에만 표시
        self.compact_mode = True
        self._compact_tree_frame = None
    
    def show(
        self,
        initial_files: dict = None,
        auto_start_parse: bool = False,
        skip_parse_confirm: bool = False,
    ) -> None:
        """팝업 표시.
        initial_files      : { 'DO': 경로 } 등 드래그앤드롭/캡처 이미지 사전 지정.
        auto_start_parse   : True 이면 팝업이 열리자마자 파싱 자동 시작 (빠른 폴더 스캔).
        skip_parse_confirm : True 이면 파싱 시작 확인 팝업 생략.
        """
        self._initial_files      = initial_files or {}
        self._auto_start_parse   = bool(auto_start_parse)
        self._skip_parse_confirm = bool(skip_parse_confirm)
        logger.info(
            "OneStopInboundDialog.show(files=%s, auto_start=%s, skip_confirm=%s)",
            list((initial_files or {}).keys()),
            auto_start_parse,
            skip_parse_confirm,
        )
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
    

    # =========================================================================
    # v7.0.0: _create_dialog 분리 — 4개 서브메서드 (테스트 가시성 확보)
    # =========================================================================
    def _build_inbound_doc_frame(self, main) -> None:
        """문서 파일 선택 프레임 (PL/INV/BL/DO + 파싱 버튼)"""
        self._build_inbound_doc_frame_impl(main)

    def _build_inbound_progress_frame(self, main) -> None:
        """진행 상태 프레임 (⏱ 파싱 진행 표시)"""
        self._build_inbound_progress_frame_impl(main)

    def _build_inbound_preview_frame(self, main) -> None:
        """미리보기 프레임 (📊 Treeview)"""
        self._build_inbound_preview_frame_impl(main)

    def _build_inbound_button_frame(self, main) -> None:
        """버튼 프레임 (업로드/취소/내보내기 등)"""
        self._build_inbound_button_frame_impl(main)


    def _build_inbound_doc_frame_impl(self, main) -> None:
        pass  # 실제 구현은 _create_dialog 본문에 포함

    def _build_inbound_progress_frame_impl(self, main) -> None:
        pass

    def _build_inbound_preview_frame_impl(self, main) -> None:
        pass

    def _build_inbound_button_frame_impl(self, main) -> None:
        pass

    def _create_dialog(self) -> None:
        """원스톱 입고 팝업 생성"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("📥 입고 — SQM v6.2.3")
        apply_modal_window_options(self.dialog)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        if getattr(self, 'compact_mode', False):
            self.dialog.geometry("1180x340")
            self.dialog.minsize(1080, 300)
            self.dialog.resizable(True, True)
            center_dialog(self.dialog, self.parent)
        else:
            self.dialog.minsize(720, 520)
            try:
                sw = self.parent.winfo_screenwidth()
                sh = self.parent.winfo_screenheight()
                w = min(1100, int(sw * 0.72))
                h = min(780, int(sh * 0.82))
                x = (sw - w) // 2
                y = max(30, (sh - h) // 2)
                self.dialog.geometry(f"{w}x{h}+{x}+{y}")
            except Exception:
                self.dialog.geometry(DialogSize.get_geometry(self.parent, 'large'))
                center_dialog(self.dialog, self.parent)
            setup_dialog_geometry_persistence(self.dialog, "onestop_inbound_dialog", self.parent)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # ═══ v7.7.2: Canvas + Scrollbar 래퍼 (가로/세로 스크롤) ═══
        _h_scroll = ttk.Scrollbar(self.dialog, orient=HORIZONTAL)
        _h_scroll.pack(side=BOTTOM, fill=X)

        _outer = ttk.Frame(self.dialog)
        _outer.pack(fill=BOTH, expand=YES)

        _v_scroll = ttk.Scrollbar(_outer, orient=VERTICAL)
        _v_scroll.pack(side=RIGHT, fill=Y)

        _canvas = tk.Canvas(
            _outer, highlightthickness=0,
            xscrollcommand=_h_scroll.set,
            yscrollcommand=_v_scroll.set,
        )
        _canvas.pack(side=LEFT, fill=BOTH, expand=YES)
        _h_scroll.config(command=_canvas.xview)
        _v_scroll.config(command=_canvas.yview)

        main = ttk.Frame(_canvas, padding=6)
        _win_id = _canvas.create_window((0, 0), window=main, anchor='nw')

        def _on_main_configure(_e):
            _canvas.configure(scrollregion=_canvas.bbox('all'))

        def _on_canvas_configure(_e):
            if main.winfo_reqwidth() < _e.width:
                _canvas.itemconfig(_win_id, width=_e.width)

        main.bind('<Configure>', _on_main_configure)
        _canvas.bind('<Configure>', _on_canvas_configure)

        def _on_mousewheel(_e):
            if _canvas.winfo_exists():
                _canvas.yview_scroll(int(-1 * (_e.delta / 120)), 'units')

        def _on_shift_mousewheel(_e):
            if _canvas.winfo_exists():
                _canvas.xview_scroll(int(-1 * (_e.delta / 120)), 'units')

        _canvas.bind_all('<MouseWheel>', _on_mousewheel)
        _canvas.bind_all('<Shift-MouseWheel>', _on_shift_mousewheel)
        self._scroll_canvas = _canvas  # 정리용 참조 보관
        
        # ═══════════════════════════════════════════════════════════
        # 1. 상단: 4종 서류 + 파싱 버튼 (1줄 균등 배치)
        # ═══════════════════════════════════════════════════════════
        file_frame = ttk.Frame(main)
        file_frame.pack(fill=X, pady=(0, 4))
        
        # 7열 그리드: [①PL][②INV][③BL][④DO] [파싱][다시파싱][힌트]
        for i in range(4):
            file_frame.columnconfigure(i, weight=1, uniform='doc')
        file_frame.columnconfigure(4, weight=0)  # 파싱 버튼
        file_frame.columnconfigure(5, weight=0)  # 다시 파싱 버튼
        file_frame.columnconfigure(6, weight=0)  # 힌트
        
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

            # v7.8.0: 개별 재파싱 버튼 (초기 hidden)
            _reparse_btn = tk.Button(
                cell, text="↻", font=('', 11), width=2,
                bg=ThemeColors.get('btn_neutral', _os_dark),
                fg=ThemeColors.get('badge_text', _os_dark),
                padx=1, pady=0, cursor='hand2', bd=0,
                state='disabled',
                command=lambda dt=doc_type: self._reparse_single_doc(dt),
            )
            _reparse_btn.pack(side=LEFT, padx=(0, 1))
            _reparse_btn.pack_forget()  # 초기에는 숨김
            self._doc_reparse_buttons[doc_type] = _reparse_btn

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

        self.btn_reparse = ttk.Button(
            file_frame, text="↻ 다시 파싱",
            command=self._reparse_with_current_files,
            state='disabled', width=10
        )
        self.btn_reparse.grid(row=0, column=5, padx=(0, 2))
        self._attach_doc_tooltip(
            self.btn_reparse,
            "이미 선택한 동일 파일로 재파싱합니다.\n파일을 다시 선택하지 않아도 됩니다."
        )

        # v7.4.0: 선사 변경 후 PL/INV 재파싱 버튼
        self.btn_reparse_carrier = ttk.Button(
            file_frame, text="🚢 선사 재파싱",
            command=self._reparse_after_carrier_change,
            state='disabled', width=12
        )
        self.btn_reparse_carrier.grid(row=0, column=6, padx=(0, 2))
        self._attach_doc_tooltip(
            self.btn_reparse_carrier,
            "수동으로 선사를 변경한 후 PL/INV를 해당 선사 힌트로 재파싱합니다.\n"
            "BL 자동 감지 실패 시 → 선사 Combobox 선택 → 이 버튼 클릭"
        )

        # v7.4.0: DO 나중에 추가 버튼
        self.btn_add_do_later = ttk.Button(
            file_frame, text="📋 D/O 나중에",
            command=self._on_add_do_later,
            state='normal', width=12
        )
        self.btn_add_do_later.grid(row=0, column=7, padx=(0, 2))
        self._attach_doc_tooltip(
            self.btn_add_do_later,
            "D/O 없이 입고 후 나중에 D/O를 추가합니다.\n"
            "메뉴 → 입고 → [D/O 후속 연결]과 동일한 기능입니다."
        )

        self.parse_hint = ttk.Label(
            file_frame, text="",
            foreground='white', font=('맑은 고딕', 12)
        )
        self.parse_hint.grid(row=0, column=8, padx=(2, 4), sticky='w')
        self._update_parse_hint()
        
        # v6.5.0: 빠른 폴더 스캔 자동 파싱 — 3단계 안전 타이밍
        #   1) update_idletasks() — 모든 pending UI 이벤트 즉시 처리
        #   2) after_idle()       — 이벤트 루프가 완전히 idle 상태 확인
        #   3) after(500)         — Windows 렌더링 여유 시간 500ms 확보
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
            except Exception:
                pass

        # ── v7.2.0: 입고 파싱 템플릿 선택 행 ─────────────────────────────────
        _tpl_row = ttk.Frame(main)
        _tpl_row.pack(fill=X, pady=(0, 2))
        _os_dark_tpl = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        ttk.Label(
            _tpl_row, text="📋 파싱 템플릿:",
            font=('맑은 고딕', 11, 'bold'),
            foreground=ThemeColors.get('text_primary', _os_dark_tpl)
        ).pack(side=LEFT, padx=(4, 4))

        self._tpl_var = tk.StringVar(value='')
        self._tpl_combo = ttk.Combobox(
            _tpl_row, textvariable=self._tpl_var,
            state='readonly', font=('맑은 고딕', 11), width=32
        )
        self._tpl_combo.pack(side=LEFT, padx=(0, 6))
        self._tpl_combo.bind('<<ComboboxSelected>>', self._on_template_selected)

        ttk.Button(
            _tpl_row, text='⚙ 템플릿 관리',
            command=self._open_template_manager
        ).pack(side=LEFT, padx=2)

        # 선택된 단가 표시 뱃지
        self._tpl_badge = tk.Label(
            _tpl_row, text='',
            font=('맑은 고딕', 11, 'bold'),
            fg='#1A5276', bg='#AED6F1',
            relief='flat', padx=10, pady=4, bd=0
        )
        self._tpl_badge.pack(side=LEFT, padx=(4, 0))

        # 파싱 템플릿 초기 로드
        self._inbound_template_data: dict = {}  # 선택된 템플릿 전체 데이터
        self._load_template_combo()

        # ── v6.4.0: 선사 뱃지 행 (BL 파싱 후 선사 정보 표시) ──────────────
        _carrier_row = ttk.Frame(main)
        _carrier_row.pack(fill=X, pady=(0, 2))
        _os_dark2 = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        ttk.Label(
            _carrier_row,
            text="🚢 선사:",
            font=('맑은 고딕', 12, 'bold'),
            foreground=ThemeColors.get('text_primary', _os_dark2)
        ).pack(side=LEFT, padx=(4, 4))
        # 뱃지 라벨 — BL 파싱 완료 후 _update_carrier_badge()로 갱신
        self._carrier_label = tk.Label(
            _carrier_row,
            text="  (BL 파싱 전)  ",
            font=('맑은 고딕', 12, 'bold'),
            fg="#888888",
            bg=("#2b2b2b" if _os_dark2 else "#f0f0f0"),
            relief="flat", padx=8, pady=2, bd=0
        )
        self._carrier_label.pack(side=LEFT, padx=(0, 8))
        self._attach_doc_tooltip(
            self._carrier_label,
            "BL 파싱 후 선사 정보가 자동으로 표시됩니다.\n"
            "  MSC    → 파란색 뱃지\n"
            "  Maersk → 초록색 뱃지\n"
            "  HMM    → 빨간색 뱃지\n"
            "  기타   → 회색 뱃지"
        )

        # v7.3.9: 수동 선사 선택 Combobox (자동 감지 실패 시 직접 선택)
        ttk.Label(
            _carrier_row,
            text="수동 선택:",
            font=('맑은 고딕', 10),
            foreground=ThemeColors.get('text_muted', _os_dark2)
        ).pack(side=LEFT, padx=(8, 2))
        try:
            from engine_modules.constants import CARRIER_OPTIONS
            _carrier_opts = CARRIER_OPTIONS
        except ImportError:
            _carrier_opts = ['UNKNOWN', 'MSC', 'MAERSK', 'CMA_CGM',
                             'COSCO', 'EVERGREEN', 'ONE', 'HMM',
                             'SINOKOR', 'KMTC', 'HEUNG_A', 'OTHER']
        self._carrier_manual_var = tk.StringVar(value='UNKNOWN')
        self._carrier_combo = ttk.Combobox(
            _carrier_row,
            textvariable=self._carrier_manual_var,
            values=_carrier_opts,
            state='readonly',
            width=14,
            font=('맑은 고딕', 10)
        )
        self._carrier_combo.pack(side=LEFT, padx=(0, 4))
        self._carrier_combo.bind('<<ComboboxSelected>>', self._on_carrier_manual_select)
        self._attach_doc_tooltip(
            self._carrier_combo,
            "BL 자동 감지 실패 시 선사를 직접 선택하세요.\n"
            "선택하면 해당 선사 힌트로 PL/INV 재파싱 버튼이 활성화됩니다."
        )
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
        # 2. 미리보기 테이블 — compact_mode에서는 생성 생략, 결과는 메인 창에만 표시
        # ═══════════════════════════════════════════════════════════
        _tree_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        self._var_show_container_suffix = tk.BooleanVar(value=False)
        if not getattr(self, 'compact_mode', False):
            self._tree_frame_visible = False
            tree_frame = ttk.LabelFrame(main, text="📊 미리보기 (스케일링·처리된 데이터)", padding=4)
            self._tree_frame = tree_frame
            import tkinter.font as tkfont
            preview_font = tkfont.Font(family='맑은 고딕', size=11)
            _ = tkfont.Font(family='맑은 고딕', size=10, weight='bold')  # heading_font reserved
            row_height = preview_font.metrics('linespace') + 6
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
            self.tree._disable_global_editable = True
            self.tree.tag_configure('odd', background=ThemeColors.get('tree_stripe', _tree_dark), foreground=_tree_fg)
            self.tree.tag_configure('even', background=ThemeColors.get('bg_card', _tree_dark), foreground=_tree_fg)
            self.tree.tag_configure('edited', background=ThemeColors.get('warning', _tree_dark), foreground=_tree_fg)
            self.tree.tag_configure('xc_critical', background='#FFCDD2', foreground='#B71C1C')
            self.tree.tag_configure('xc_warning', background='#FFE0B2', foreground='#E65100')
            self.tree.tag_configure('xc_info', background='#FFF3CD', foreground='#795548')
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
            chk_container = ttk.Checkbutton(
                tree_frame, text="컨테이너 번호 접미사(-숫자) 표시",
                variable=self._var_show_container_suffix,
                command=self._on_toggle_container_suffix
            )
            chk_container.pack(anchor='w', padx=4, pady=(2, 0))
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
        else:
            self.tree = None
            self.filter_bar = None
            self._tree_frame = None
            self._tree_frame_visible = False
        
        # ═══════════════════════════════════════════════════════════
        # 4. 하단 버튼 — v7.7.2: 2행 배치 (행1=주요 액션, 행2=편집 보조)
        # ═══════════════════════════════════════════════════════════
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=X, pady=(6, 0))

        _font = getattr(self, '_toolbar_font', '맑은 고딕') if hasattr(self, '_toolbar_font') else '맑은 고딕'

        # ── 행1: 주요 액션 ──
        btn_row1 = ttk.Frame(btn_frame)
        btn_row1.pack(fill=X, pady=(0, 2))

        self.btn_excel = tk.Button(
            btn_row1, text="📥 Excel 내보내기",
            command=self._export_to_excel, state='disabled',
            font=(_font, 12, 'bold'), bg='#D6EAF8', fg='#1A5276',
            padx=12, pady=4, cursor='hand2', bd=0
        )
        self.btn_excel.pack(side=LEFT, padx=(0, 4))

        self.btn_upload = tk.Button(
            btn_row1, text="📤 DB 업로드",
            command=self._on_upload, state='disabled',
            font=(_font, 12, 'bold'), bg='#D5F5E3', fg='#1E8449',
            padx=12, pady=4, cursor='hand2', bd=0
        )
        self.btn_upload.pack(side=LEFT, padx=(0, 4))
        self._attach_doc_tooltip(self.btn_upload,
            "미리보기 데이터를 DB에 저장합니다\n\n• 저장 후 재고리스트에 자동 반영\n• 중복 LOT는 자동 스킵\n• 저장 완료 후 재고리스트 화면 표시")

        self._var_upload_by_view_order = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            btn_row1,
            text="정렬순서 적용",
            variable=self._var_upload_by_view_order
        ).pack(side=LEFT, padx=(4, 0))

        tk.Button(
            btn_row1, text="❌ 취소",
            command=self._on_cancel,
            font=(_font, 12, 'bold'), bg='#F5B7B1', fg='#78281F',
            padx=12, pady=4, cursor='hand2', bd=0
        ).pack(side=RIGHT, padx=(4, 0))

        self.summary_var = tk.StringVar(value="")
        ttk.Label(btn_row1, textvariable=self.summary_var,
                  font=('맑은 고딕', 12, 'bold'),
                  foreground=ThemeColors.get('statusbar_progress', _tree_dark)
        ).pack(side=RIGHT, padx=8)

        # ── 행2: 편집 보조 (작게) ──
        btn_row2 = ttk.Frame(btn_frame)
        btn_row2.pack(fill=X)

        self.btn_undo = tk.Button(
            btn_row2, text="↶ 되돌리기",
            command=self._undo_preview_edit, state='disabled',
            font=(_font, 10), bg='#E8E8E8', fg='#555555',
            padx=8, pady=2, cursor='hand2', bd=0
        )
        self.btn_undo.pack(side=LEFT, padx=(0, 3))
        self.btn_redo = tk.Button(
            btn_row2, text="↷ 다시실행",
            command=self._redo_preview_edit, state='disabled',
            font=(_font, 10), bg='#E8E8E8', fg='#555555',
            padx=8, pady=2, cursor='hand2', bd=0
        )
        self.btn_redo.pack(side=LEFT, padx=(0, 3))
        self.btn_reset_original = tk.Button(
            btn_row2, text="⟲ 원본 초기화",
            command=self._reset_preview_to_original, state='disabled',
            font=(_font, 10), bg='#E8E8E8', fg='#555555',
            padx=8, pady=2, cursor='hand2', bd=0
        )
        self.btn_reset_original.pack(side=LEFT)
    
    # ═══════════════════════════════════════════════════════════
    # 파일 선택
    # ═══════════════════════════════════════════════════════════
    
    def _update_parse_hint(self) -> None:
        """파싱 시작 옆 업로드 상태 문구 갱신: 총 4개 중 N개 업로드되었습니다."""
        n = len(self.file_paths)
        if not getattr(self, 'parse_hint', None):
            return
        _hint_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        if 'BL' not in self.file_paths and 'PACKING_LIST' not in self.file_paths:
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
        if 'BL' not in self.file_paths and 'PACKING_LIST' not in self.file_paths:
            from ..utils.custom_messagebox import CustomMessageBox
            CustomMessageBox.showwarning(self.dialog, "재파싱 불가", "BL 또는 Packing List 파일이 필요합니다.")
            return
        try:
            from ..utils.custom_messagebox import CustomMessageBox
            ok = CustomMessageBox.askyesno(
                self.dialog,
                "재파싱 확인",
                "기존 미리보기 결과를 덮어쓰고 재파싱합니다.\n\n계속하시겠습니까?"
            )
        except (ImportError, ModuleNotFoundError):
            from tkinter import messagebox as msgbox
            ok = msgbox.askyesno(
                "재파싱 확인",
                "기존 미리보기 결과를 덮어쓰고 재파싱합니다.\n\n계속하시겠습니까?"
            )
        if not ok:
            return
        self._start_parsing()

    # ═══════════════════════════════════════════════════════════
    # v7.8.0: 개별 서류 재파싱
    # ═══════════════════════════════════════════════════════════

    def _reparse_single_doc(self, doc_type: str) -> None:
        """실패한 서류 한 종만 재파싱 (성공한 서류 결과 유지)."""
        if doc_type not in self.file_paths:
            from ..utils.custom_messagebox import CustomMessageBox
            CustomMessageBox.showwarning(
                self.dialog, "재파싱 불가",
                f"{doc_type} 파일이 선택되지 않았습니다."
            )
            return

        # 버튼 비활성화 (중복 클릭 방지)
        if doc_type in self._doc_reparse_buttons:
            self._doc_reparse_buttons[doc_type].config(state='disabled')
        if doc_type in self.check_labels:
            self.check_labels[doc_type].configure(text="⏳")

        self._log_safe(f"↻ {doc_type} 개별 재파싱 시작...")

        import threading
        t = threading.Thread(
            target=self._reparse_single_doc_thread,
            args=(doc_type,),
            daemon=True,
        )
        t.start()

    def _reparse_single_doc_thread(self, doc_type: str) -> None:
        """개별 재파싱 백그라운드 스레드."""
        try:
            from parsers.document_parser_modular import DocumentParserV3 as DocumentParserV2

            gemini_key = os.environ.get('GEMINI_API_KEY', '')
            if not gemini_key:
                try:
                    from core.config import get_settings
                    gemini_key = get_settings().get('gemini_api_key', '')
                except Exception:
                    pass
            if not gemini_key:
                raise RuntimeError("Gemini API Key가 필요합니다.")

            parser = DocumentParserV2(gemini_api_key=gemini_key)
            file_path = self.file_paths[doc_type]

            _tpl = getattr(self, '_inbound_template_data', {}) or {}
            _bag_weight = int(_tpl.get('bag_weight_kg', 500))
            _hint_packing = str(_tpl.get('gemini_hint_packing', '') or '')
            _hint_invoice = str(_tpl.get('gemini_hint_invoice', '') or '')
            _hint_bl = str(_tpl.get('gemini_hint_bl', '') or '')

            # v7.8.0: 선사 힌트 재활용 (이전 파싱에서 감지된 선사 정보)
            _carrier_tmpl = None
            if doc_type == 'BL' and 'BL' in self.file_paths:
                try:
                    import fitz
                    _bl_doc = fitz.open(self.file_paths['BL'])
                    _page0 = _bl_doc[0].get_text() if len(_bl_doc) > 0 else ''
                    _bl_doc.close()
                    from features.ai.bl_carrier_registry import detect_carrier
                    _carrier_tmpl = detect_carrier(_page0)
                except Exception:
                    pass

            result = None
            if doc_type == 'PACKING_LIST':
                result = parser.parse_packing_list(
                    file_path, bag_weight_kg=_bag_weight,
                    gemini_hint=_hint_packing,
                )
                self.parsed_results['packing_list'] = result
            elif doc_type == 'INVOICE':
                result = parser.parse_invoice(
                    file_path, gemini_hint=_hint_invoice,
                )
                self.parsed_results['invoice'] = result
            elif doc_type == 'BL':
                result = parser.parse_bl(
                    file_path, gemini_hint=_hint_bl,
                    carrier_template=_carrier_tmpl,
                )
                self.parsed_results['bl'] = result
            elif doc_type == 'DO':
                result = parser.parse_do(file_path)
                self.parsed_results['do'] = result

            # 결과 재병합
            _pl = self.parsed_results.get('packing_list')
            _inv = self.parsed_results.get('invoice')
            _bl = self.parsed_results.get('bl')
            _do = self.parsed_results.get('do')
            self._merge_results(_inv, _pl, _bl, _do)

            # 성공 여부 판단
            has_error = bool(getattr(result, 'error_message', ''))
            if doc_type == 'PACKING_LIST' and not getattr(result, 'lots', []):
                has_error = True
            if doc_type == 'INVOICE' and not getattr(result, 'sap_no', ''):
                has_error = True
            if doc_type == 'BL' and not getattr(result, 'bl_no', ''):
                has_error = True

            if has_error:
                self._log_safe(f"  ⚠️ {doc_type} 재파싱 완료 — 여전히 문제 있음")
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(0, lambda: (
                        self._doc_reparse_buttons.get(doc_type) and
                        self._doc_reparse_buttons[doc_type].config(state='normal')
                    ))
            else:
                self._failed_doc_types.discard(doc_type)
                self._log_safe(f"  ✅ {doc_type} 재파싱 성공!")
                if self.dialog and self.dialog.winfo_exists():
                    def _update_ui():
                        if doc_type in self.check_labels:
                            self.check_labels[doc_type].configure(text="✅")
                        if doc_type in self._doc_reparse_buttons:
                            self._doc_reparse_buttons[doc_type].pack_forget()
                    self.dialog.after(0, _update_ui)

            # 미리보기 갱신
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, lambda: self._push_preview_to_main())
                if not getattr(self, 'compact_mode', False):
                    self.dialog.after(0, lambda: self._refresh_preview_tree_only())

        except Exception as e:
            self._log_safe(f"  ❌ {doc_type} 재파싱 실패: {e}")
            logger.error(f"개별 재파싱 오류 [{doc_type}]: {e}", exc_info=True)
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, lambda: (
                    self.check_labels.get(doc_type) and
                    self.check_labels[doc_type].configure(text="⚠️"),
                    self._doc_reparse_buttons.get(doc_type) and
                    self._doc_reparse_buttons[doc_type].config(state='normal'),
                ))

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
    
    # ═══════════════════════════════════════════════════════════
    # 파싱
    # ═══════════════════════════════════════════════════════════
    
    # ── v7.2.0: 입고 파싱 템플릿 관련 메서드 ───────────────────────────────

    def _load_template_combo(self):
        """DB에서 활성 템플릿 목록을 콤보박스에 로드."""
        try:
            rows = self.engine.db.fetchall(
                "SELECT template_id, template_name, bag_weight_kg, "
                "carrier_id, product_hint, weight_format, "
                "gemini_hint_packing, gemini_hint_invoice, gemini_hint_bl "
                "FROM inbound_template WHERE is_active=1 "
                "ORDER BY carrier_id, bag_weight_kg"
            )
            self._template_map = {}  # display_name → template dict
            names = []
            KEYS = ['template_id','template_name','bag_weight_kg',
                    'carrier_id','product_hint','weight_format',
                    'gemini_hint_packing','gemini_hint_invoice','gemini_hint_bl']
            for r in (rows or []):
                t = dict(r) if hasattr(r, 'keys') else dict(zip(KEYS, r))
                self._template_map[t['template_name']] = t
                names.append(t['template_name'])
            self._tpl_combo['values'] = names
            # 기본값: UNKNOWN_500
            default = next((n for n in names if 'UNKNOWN' in n and '500' in n), None)
            if not default and names:
                default = names[0]
            if default:
                self._tpl_var.set(default)
                self._on_template_selected()
        except Exception as e:
            logger.debug(f"[onestop] 템플릿 콤보 로드 실패: {e}")

    def _on_template_selected(self, _event=None):
        """콤보박스 선택 → 뱃지 업데이트 + 템플릿 데이터 로드."""
        name = self._tpl_var.get()
        t = getattr(self, '_template_map', {}).get(name)
        if not t:
            return
        bag = t.get('bag_weight_kg', 500)
        self._inbound_template_data = t
        # 뱃지 색상: 500=밝은파랑, 1000=밝은주황
        _bg = '#AED6F1' if bag == 500 else '#FAD7A0'
        _fg = '#1A5276' if bag == 500 else '#784212'
        try:
            self._tpl_badge.config(
                text=f'  ⚖️ {bag:,} kg/백  ', bg=_bg, fg=_fg
            )
        except Exception:
            pass
        logger.debug(f"[onestop] 템플릿 선택: {name} / {bag}kg")

    def _open_template_manager(self):
        """템플릿 관리 다이얼로그 열기 (콜백 없음 → 관리 전용)."""
        try:
            from gui_app_modular.dialogs.inbound_template_dialog import InboundTemplateDialog
            current_theme = getattr(self.parent, 'current_theme', 'flatly')
            InboundTemplateDialog(self.dialog, self.engine, current_theme=current_theme)
            # 관리 후 콤보박스 갱신
            self._load_template_combo()
        except Exception as e:
            logger.error(f"[onestop] 템플릿 관리 다이얼로그 오류: {e}")

    def _start_parsing(self) -> None:
        """
        v7.3.0: 파싱 시작 — 템플릿 선택 → 서류 확인 → 파싱 실행
        파싱 전 반드시 템플릿 선택 다이얼로그를 먼저 표시.
        """
        # v6.4.0: auto_start_parse 모드 — 버튼 강제 활성화 후 실행
        if getattr(self, '_auto_start_parse', False):
            if self.btn_parse and str(self.btn_parse.cget('state')) == 'disabled':
                self.btn_parse.config(state='normal')

        # ── v7.3.0: 파싱 전 템플릿 선택 다이얼로그 ──────────────────────────
        # auto_start_parse(빠른 폴더 스캔) 모드이면 현재 선택 그대로 사용
        if getattr(self, '_auto_start_parse', False):
            # 자동 모드: 이미 선택된 템플릿으로 바로 진행
            self._do_start_parsing_after_template()
        else:
            # 일반 모드: 템플릿 선택 다이얼로그 먼저 표시
            self._show_template_select_before_parse()

    def _show_template_select_before_parse(self) -> None:
        """파싱 전 템플릿 선택 다이얼로그 표시."""
        try:
            from gui_app_modular.dialogs.inbound_template_dialog import InboundTemplateDialog
            current_theme = getattr(self.parent, 'current_theme', 'flatly')

            def _on_template_chosen(t: dict):
                """템플릿 선택 완료 콜백 → 파싱 진행."""
                # 선택된 템플릿 적용
                self._inbound_template_data = t
                # 콤보박스 + 뱃지 동기화
                try:
                    tname = t.get('template_name', '')
                    self._tpl_var.set(tname)
                    bag = int(t.get('bag_weight_kg', 500))
                    _bg = '#AED6F1' if bag == 500 else '#FAD7A0'
                    _fg = '#1A5276' if bag == 500 else '#784212'
                    self._tpl_badge.config(
                        text=f'  ⚖️ {bag:,} kg/백  ', bg=_bg, fg=_fg)
                    # 콤보 목록도 최신화
                    self._load_template_combo()
                    self._tpl_var.set(tname)
                except Exception:
                    pass
                self._log_safe(
                    f"✅ 템플릿 선택: {t.get('template_name','')} "
                    f"/ {t.get('bag_weight_kg',500)}kg")
                # 실제 파싱 진행
                self._do_start_parsing_after_template()

            InboundTemplateDialog(
                self.dialog,
                self.engine,
                current_theme=current_theme,
                on_select_callback=_on_template_chosen,
            )
        except Exception as e:
            logger.error(f"[onestop] 템플릿 선택 다이얼로그 오류: {e}")
            # 오류 시 현재 선택 그대로 파싱 진행
            self._do_start_parsing_after_template()

    def _do_start_parsing_after_template(self) -> None:
        """템플릿 선택 완료 후 기존 파싱 흐름 진행 (서류 확인 → 파싱 실행)."""
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
        
        # v6.4.0: skip_parse_confirm=True (빠른 폴더 스캔) 이면 확인 팝업 생략
        if not getattr(self, '_skip_parse_confirm', False):
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
        if self.btn_reparse:
            self.btn_reparse.config(state='disabled')
        self._show_progress_inline()
        
        thread = threading.Thread(
            target=self._parse_thread,
            daemon=True
        )
        self._parse_worker_thread = thread
        self._ui_sample_ready = False
        self._ui_sample_cancelled = False
        self._ui_date_ready = False
        thread.start()
        self._poll_worker_ui()

    def _poll_worker_ui(self):
        """메인 스레드에서 워커 스레드의 UI 요청을 50ms 간격으로 폴링."""
        thread = getattr(self, '_parse_worker_thread', None)
        if not thread:
            return

        # 1) 샘플 미리보기 요청
        if getattr(self, '_ui_sample_ready', False):
            self._ui_sample_ready = False
            try:
                edits = self._show_sample_preview_dialog()
            except Exception as e:
                logger.error(f"샘플 미리보기 오류: {e}", exc_info=True)
                self._log_safe(f"⚠️ 샘플 미리보기 오류: {e}")
                edits = {'common': {}, 'containers': {}}
            if edits is None:
                self._ui_sample_cancelled = True
            else:
                self._ui_sample_cancelled = False
                self._apply_sample_edits(edits)
            self._ui_sample_event.set()

        # 2) 날짜 입력 요청
        if getattr(self, '_ui_date_ready', False):
            self._ui_date_ready = False
            try:
                self._hide_progress_popup()
                user_dates = self._ask_missing_dates(
                    self._ui_date_prefilled_ship,
                    self._ui_date_do_result
                )
            except Exception as e:
                logger.error(f"날짜 입력 오류: {e}", exc_info=True)
                self._log_safe(f"⚠️ 날짜 입력 오류: {e}")
                user_dates = None

            if user_dates:
                if user_dates.get('deferred'):
                    self._do_deferred = True
                    self._log_safe("  📋 D/O 추후 첨부 선택됨 — arrival_date 없이 진행")
                else:
                    for row in self.preview_data:
                        if user_dates.get('ship_date') and not (row.get('ship_date') or '').strip():
                            row['ship_date'] = user_dates['ship_date']
                        if user_dates.get('arrival_date'):
                            row['arrival_date'] = user_dates['arrival_date']
                        if 'con_return' in user_dates:
                            row['con_return'] = user_dates.get('con_return', '') or ''
                        if user_dates.get('free_time') is not None:
                            row['free_time'] = str(user_dates.get('free_time', ''))
                    self._log_safe(
                        f"  ✅ 수동 입력: arrival={user_dates.get('arrival_date')}, "
                        f"con_return={user_dates.get('con_return')}, "
                        f"free_time={user_dates.get('free_time')}"
                    )
            else:
                self._log_safe("  ⚠️ 날짜 입력 취소 — arrival_date 없이 진행")
            self._ui_date_event.set()

        # 스레드 살아있으면 계속 폴링
        if thread.is_alive():
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(50, self._poll_worker_ui)

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
            from parsers.document_parser_modular import DocumentParserV3 as DocumentParserV2  # v7.5.0: V3 마이그레이션
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

            # ── v7.2.0: 선택된 템플릿에서 bag_weight_kg 주입 ─────────────────
            # ── v7.3.0: gemini_hint 3종 추출 ────────────────────────────────
            _tpl = getattr(self, '_inbound_template_data', {}) or {}
            _bag_weight       = int(_tpl.get('bag_weight_kg', 500))
            _hint_packing     = str(_tpl.get('gemini_hint_packing', '') or '')
            _hint_invoice     = str(_tpl.get('gemini_hint_invoice', '') or '')
            _hint_bl          = str(_tpl.get('gemini_hint_bl',      '') or '')
            _tpl_id           = _tpl.get('template_id', 'NONE')
            logger.info(
                f"[onestop] 파싱 템플릿: {_tpl_id} / {_bag_weight}kg "
                f"/ 힌트PL={bool(_hint_packing)} INV={bool(_hint_invoice)} BL={bool(_hint_bl)}"
            )

            # v6.4.0: 파싱 시작 시 선사 뱃지 초기화
            if hasattr(self, '_carrier_label') and self._carrier_label:
                try:
                    self._carrier_label.config(
                        text="  ⏳ 파싱 중...  ",
                        fg="#666666", bg="#E8E8E8"
                    )
                except Exception:
                    pass
            # v7.3.9: 파싱 순서 변경 BL → PL → Invoice → DO
            parse_order = ['BL', 'PACKING_LIST', 'INVOICE', 'DO']
            to_parse = [(dt, self.file_paths[dt]) for dt in parse_order if dt in self.file_paths]
            total = len(to_parse)
            if total == 0:
                self._update_progress(90, "파싱할 파일이 없습니다")
                return

            # ═══ v7.7.2: 선사 사전 감지 (BL 파싱 전) ═══
            _carrier_tmpl = None
            _carrier_id = ''
            _carrier_name = ''

            if 'BL' in self.file_paths:
                try:
                    import fitz
                    _bl_doc = fitz.open(self.file_paths['BL'])
                    _page0_text = _bl_doc[0].get_text() if len(_bl_doc) > 0 else ''
                    _bl_doc.close()

                    from features.ai.bl_carrier_registry import detect_carrier
                    _carrier_tmpl = detect_carrier(_page0_text)
                    if _carrier_tmpl:
                        _carrier_id = _carrier_tmpl.carrier_id
                        _carrier_name = _carrier_tmpl.carrier_name
                        self._log_safe(f"🔍 선사 사전 감지: {_carrier_name} ({_carrier_id})")

                        # UI 뱃지 업데이트
                        if self.dialog and self.dialog.winfo_exists():
                            _badge = f"[선사: {_carrier_name}]"
                            self.dialog.after(0, lambda b=_badge: self._update_carrier_badge(b))

                        # 힌트 주입 (템플릿 힌트 우선, 없을 때만 선사 힌트 적용)
                        if not _hint_bl:
                            _hint_bl = _carrier_tmpl.bl_no_prompt_hint or ''
                        if not _hint_packing and hasattr(_carrier_tmpl, 'bl_format_hint'):
                            _hint_packing = (
                                f"이 서류는 {_carrier_name} 선사의 Packing List입니다. "
                                f"BL번호 형식: {_carrier_tmpl.bl_format_hint}"
                            )
                        if not _hint_invoice:
                            _hint_invoice = f"이 서류는 {_carrier_name} 선사의 Invoice/FA입니다."
                    else:
                        self._log_safe("🔍 선사 미확인 — 기본(default) 힌트로 진행")
                except Exception as _e:
                    logger.debug(f"선사 사전 감지 실패(무시): {_e}")
            
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
                        pl_result = parser.parse_packing_list(
                            file_path,
                            bag_weight_kg=_bag_weight,
                            gemini_hint=_hint_packing,     # v7.3.0
                        )
                        self.parsed_results['packing_list'] = pl_result
                        _lots = getattr(pl_result, 'lots', []) if pl_result else []
                        if _lots:
                            _tnw = getattr(pl_result, 'total_net_weight_kg', 0) or 0
                            self._log_safe(f"  ✅ LOTs: {len(_lots)}, Net: {_tnw:,.0f}kg")
                    
                    elif doc_type == 'INVOICE':
                        inv_result = parser.parse_invoice(
                            file_path,
                            gemini_hint=_hint_invoice,     # v7.3.0
                        )
                        self.parsed_results['invoice'] = inv_result
                        if inv_result:
                            self._log_safe(f"  ✅ SAP: {getattr(inv_result, 'sap_no', '')}, Invoice: {getattr(inv_result, 'salar_invoice_no', '')}")
                    
                    elif doc_type == 'BL':
                        bl_result = parser.parse_bl(
                            file_path,
                            gemini_hint=_hint_bl,
                            carrier_template=_carrier_tmpl,  # v7.7.2: 선사별 BL 파싱
                        )
                        self.parsed_results['bl'] = bl_result
                        if bl_result:
                            # v7.7.2: 선사 사전 감지에서 못 잡은 경우 → BL 파싱 결과에서 재시도
                            if not _carrier_id:
                                _carrier_id = getattr(bl_result, 'carrier_id', '') or ''
                                _carrier_name = getattr(bl_result, 'carrier_name', '') or ''
                            # carrier_id/name 주입 (BLMixin이 설정하지 않으므로)
                            if _carrier_id and not getattr(bl_result, 'carrier_id', ''):
                                bl_result.carrier_id = _carrier_id
                                bl_result.carrier_name = _carrier_name
                            # 로그
                            _badge_txt = f"[선사: {_carrier_name or _carrier_id}]" if _carrier_id else "[선사: 미확인]"
                            self._log_safe(
                                f"  ✅ B/L: {getattr(bl_result, 'bl_no', '')} "
                                f"{_badge_txt}  "
                                f"Containers: {getattr(bl_result, 'total_containers', 0)}"
                            )
                            # v7.7.2: 선사 뱃지 UI 업데이트 (사전 감지에서 이미 했을 수 있지만 fallback)
                            if not _carrier_tmpl and self.dialog and self.dialog.winfo_exists():
                                self.dialog.after(
                                    0,
                                    lambda b=_badge_txt: self._update_carrier_badge(b)
                                )
                            # v7.4.0: 선사 재파싱 버튼 활성화
                            if self.dialog and self.dialog.winfo_exists():
                                self.dialog.after(0, lambda: (
                                    hasattr(self, 'btn_reparse_carrier') and
                                    self.btn_reparse_carrier.config(state='normal')
                                ))
                    
                    elif doc_type == 'DO':
                        do_result = parser.parse_do(file_path)
                        self.parsed_results['do'] = do_result
                        if do_result:
                            self._log_safe(f"  ✅ D/O: B/L={getattr(do_result, 'bl_no', '')}")
                
                except (ValueError, TypeError, AttributeError, RuntimeError) as e:
                    self._log_safe(f"  ❌ {doc_type} 파싱 오류: {e}")
                    logger.error(f"파싱 오류 [{doc_type}]: {e}", exc_info=True)
                    # v7.8.0: 실패 서류 추적
                    self._failed_doc_types.add(doc_type)
                    # RuntimeError: Gemini API-Only 실패(예: JSON 추출 실패) → 입고 미완료 → 재고/톤백 리스트에 데이터 없음
                    if isinstance(e, RuntimeError) and doc_type == 'PACKING_LIST':
                        self._log_safe("  💡 Packing List 실패 시 입고가 완료되지 않아 톤백 리스트에 표시되지 않습니다.")
                else:
                    # 서류 하나 파싱 직후마다 병합 후 미리보기 테이블·메인 화면에 실시간 반영
                    self._merge_results(inv_result, pl_result, bl_result, do_result)
                    if self.dialog and self.dialog.winfo_exists():
                        self.dialog.after(0, lambda: self._push_preview_to_main())
                        if not getattr(self, 'compact_mode', False):
                            self.dialog.after(0, lambda: self._refresh_preview_tree_only())
            
            # 병합
            self._update_progress(85, "📊 데이터 병합 중...")
            self._merge_results(inv_result, pl_result, bl_result, do_result)

            # v7.7.2: 디버그 로그
            self._log_safe(
                f"📋 preview_data: {len(self.preview_data)}건, "
                f"auto_start={getattr(self, '_auto_start_parse', False)}"
            )

            # ═══════════════════════════════════════════════════════
            # ★★★ v7.9.0: 샘플 미리보기 확인 (Flag+Event 방식, 데드락 해결)
            # ═══════════════════════════════════════════════════════
            if self.preview_data and not getattr(self, '_auto_start_parse', False):
                self._update_progress(87, "📋 샘플 확인 대기 중...")
                self._ui_sample_event = threading.Event()
                self._ui_sample_ready = True  # 메인 스레드 폴링이 감지
                self._ui_sample_event.wait(timeout=600)
                if not self._ui_sample_event.is_set():
                    self._update_progress(0, "❌ 샘플 확인 시간 초과")
                    self._log_safe("❌ 샘플 확인 시간 초과 — 파싱 중단")
                    self._enable_parse_btn()
                    return
                if getattr(self, '_ui_sample_cancelled', False):
                    self._update_progress(0, "❌ 사용자 취소")
                    self._log_safe("❌ 샘플 확인에서 취소 — 파싱 중단")
                    self._enable_parse_btn()
                    return
                # _apply_sample_edits는 메인 스레드(_poll_worker_ui)에서 완료됨

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
                self._ui_date_prefilled_ship = prefilled_ship
                self._ui_date_do_result = do_result
                self._ui_date_event = threading.Event()
                self._ui_date_ready = True  # 메인 스레드 폴링이 감지
                self._ui_date_event.wait(timeout=300)
                if not self._ui_date_event.is_set():
                    self._log_safe("  ⚠️ 날짜 입력 시간 초과 — arrival_date 없이 진행")
                # 날짜 적용은 메인 스레드(_poll_worker_ui)에서 완료됨
            
            # v3.8.9: 파싱 결과 경고 (누락된 정보)
            _warnings = []
            if not pl_result or not getattr(pl_result, 'lots', None):
                _warnings.append("⚠️ Packing List: LOT 정보 추출 실패")
            if not inv_result or not getattr(inv_result, 'sap_no', None):
                _warnings.append("⚠️ Invoice: SAP번호 추출 실패 — 수동 입력 필요")
            if not bl_result or not getattr(bl_result, 'bl_no', None):
                _warnings.append("⚠️ B/L: BL번호 추출 실패 — 수동 입력 필요")

            # v7.8.0: 파싱 실패 디버그 리포트 경로 안내
            try:
                from pathlib import Path as _Path
                _debug_dir = _Path(__file__).resolve().parent.parent.parent / "logs" / "parse_debug"
                if _debug_dir.exists():
                    _debug_files = sorted(_debug_dir.glob("parse_fail_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                    # 최근 60초 이내 생성된 파일만 안내
                    import time as _time
                    _now = _time.time()
                    _recent = [f for f in _debug_files[:10] if (_now - f.stat().st_mtime) < 60]
                    if _recent:
                        _warnings.append(f"📂 파싱 디버그 리포트 {len(_recent)}건 저장됨: {_debug_dir}")
            except Exception:
                pass

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
            
            if _warnings:
                _warn_msg = "\n".join(_warnings)
                self._log_safe(f"\n{'='*40}\n{_warn_msg}\n{'='*40}")
                # GUI 경고
                def _show_warn():
                    from ..utils.custom_messagebox import CustomMessageBox
                    try:
                        CustomMessageBox.showwarning(self.dialog, "파싱 결과 확인", _warn_msg)
                    except Exception as e:
                        logger.warning(f"파싱 결과 경고창 표시 실패: {e}")
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(500, _show_warn)
            
            # v7.8.0: 소프트 실패 감지 (파서가 에러 메시지를 설정하거나 핵심 데이터 누락)
            if pl_result and (getattr(pl_result, 'error_message', '') or not getattr(pl_result, 'lots', [])):
                self._failed_doc_types.add('PACKING_LIST')
            if inv_result and (getattr(inv_result, 'error_message', '') or not getattr(inv_result, 'sap_no', '')):
                self._failed_doc_types.add('INVOICE')
            if bl_result and (getattr(bl_result, 'error_message', '') or not getattr(bl_result, 'bl_no', '')):
                self._failed_doc_types.add('BL')
            if do_result and getattr(do_result, 'error_message', ''):
                self._failed_doc_types.add('DO')

            # v7.8.0: 실패 서류 재파싱 버튼 표시
            if self._failed_doc_types and self.dialog and self.dialog.winfo_exists():
                def _activate_reparse_btns():
                    for _dt in self._failed_doc_types:
                        if _dt in self._doc_reparse_buttons:
                            btn = self._doc_reparse_buttons[_dt]
                            btn.pack(side=LEFT, padx=(0, 1))  # 다시 표시
                            btn.config(state='normal')
                        if _dt in self.check_labels:
                            self.check_labels[_dt].configure(text="⚠️")
                self.dialog.after(0, _activate_reparse_btns)

            # 병합 직후 메인 화면 재고 리스트에 실시간 반영
            if self.dialog and self.dialog.winfo_exists() and self.preview_data:
                self.dialog.after(0, lambda: self._push_preview_to_main())

            # 파싱 직후 원본 스냅샷(원본 초기화 기준점)
            self._capture_original_preview_state()
            self._sort_col = None
            self._sort_desc = False
            # v6.5.0: tkinter UI는 메인 스레드에서만 호출 — after(0)으로 위임
            if not getattr(self, 'compact_mode', False):
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(0, self._update_sort_headings)
                self._update_filter_values_from_preview()
                if self.btn_reset_original and self.btn_reset_original.winfo_exists():
                    self.btn_reset_original.config(state='normal' if self._original_preview_data else 'disabled')
            
            # 표시
            self._update_progress(95, "📋 미리보기 준비...")
            if not getattr(self, 'compact_mode', False) and self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, self._show_preview_table)
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
    # v7.7.1: 파싱 샘플 미리보기 다이얼로그
    # ═══════════════════════════════════════════════════════════

    # v7.9.0: BL 공통 필드 — 수정 시 전체 LOT에 적용 (BL NO 최상단)
    _SAMPLE_COMMON_FIELDS = [
        ('bl_no',            'BL NO'),
        ('sap_no',           'SAP NO'),
        ('product',          'PRODUCT'),
        ('product_code',     'CODE'),
        ('salar_invoice_no', 'INVOICE NO'),
        ('ship_date',        'SHIP DATE'),
        ('arrival_date',     'ARRIVAL'),
        ('con_return',       'CON RETURN'),
        ('free_time',        'FREE TIME'),
        ('warehouse',        'WH'),
    ]
    # v7.9.0: LOT 개별 필드 (CONTAINER는 컨테이너 그룹으로 이동)
    _SAMPLE_LOT_FIELDS = [
        ('lot_sqm',      'LOT SQM'),
        ('mxbg_pallet',  'MXBG'),
        ('net_weight',   'NET(Kg)'),
        ('gross_weight', 'GROSS(Kg)'),
    ]

    def _show_sample_preview_dialog(self):
        """
        v7.9.0: BL 공통 + 컨테이너 그룹별 미리보기.
        Returns: {'common': {field: value}, 'containers': {orig_cn: new_cn}} or None (취소)
        """
        current_theme = getattr(self.parent, 'current_theme', 'flatly')
        colors = ThemeColors.get_colors(current_theme)
        is_dark = ThemeColors.is_dark_theme(current_theme)

        bg = colors.get('bg_card', '#162033' if is_dark else '#FFFFFF')
        fg = colors.get('text_primary', '#E5E7EB' if is_dark else '#0F172A')
        fg2 = colors.get('text_secondary', '#9CA3AF' if is_dark else '#475569')
        bg_input = colors.get('bg_secondary', '#111B2E' if is_dark else '#F1F5F9')
        border_c = colors.get('border', '#1E293B' if is_dark else '#E2E8F0')
        accent = colors.get('info', '#22C5D6' if is_dark else '#2563EB')
        btn_ok_bg = colors.get('btn_inbound', '#059669')
        btn_cancel_bg = colors.get('btn_neutral', '#475569' if is_dark else '#64748B')

        sample_row = self.preview_data[0]
        total_lots = len(self.preview_data)

        # ── 컨테이너별 그룹핑 ──
        container_groups = {}  # container_no → {'indices': [...], 'lots': [...]}
        for idx, row in enumerate(self.preview_data):
            cn = (row.get('container_no') or '').strip()
            if cn not in container_groups:
                container_groups[cn] = {'indices': [], 'lots': []}
            container_groups[cn]['indices'].append(idx)
            container_groups[cn]['lots'].append(row.get('lot_no', '') or '')
        total_containers = len(container_groups)

        dlg = tk.Toplevel(self.dialog)
        dlg.title(f"파싱 결과 샘플 확인 — LOT {total_lots}개 / 컨테이너 {total_containers}개")
        dlg.configure(bg=bg)
        dlg.resizable(True, True)
        dlg.transient(self.dialog)
        dlg.grab_set()

        result = [None]  # mutable container for closure

        # ── 스크롤 가능한 메인 프레임 ──
        canvas = tk.Canvas(dlg, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(dlg, orient=VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=bg)

        scroll_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        canvas.bind('<MouseWheel>', _on_mousewheel)
        scroll_frame.bind('<MouseWheel>', _on_mousewheel)

        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=YES, padx=2, pady=2)

        # ── 헤더 ──
        hdr = tk.Label(
            scroll_frame,
            text=f"파싱 결과 샘플 확인  —  LOT {total_lots}개 / 컨테이너 {total_containers}개",
            font=('맑은 고딕', 14, 'bold'), bg=bg, fg=fg, anchor='w'
        )
        hdr.pack(fill=X, padx=16, pady=(16, 4))

        sub = tk.Label(
            scroll_frame,
            text="아래 파싱 결과를 확인하고, 틀린 부분이 있으면 수정 후 '확인'을 누르세요.",
            font=('맑은 고딕', 10), bg=bg, fg=fg2, anchor='w'
        )
        sub.pack(fill=X, padx=16, pady=(0, 12))

        common_entries = {}     # field_key → Entry widget
        container_entries = {}  # orig_container_no → Entry widget

        # ── BL 공통 정보 그룹 ──
        lf_common = tk.LabelFrame(
            scroll_frame,
            text=f"  BL 공통 정보  (수정 시 전체 {total_lots}개 LOT에 적용)  ",
            font=('맑은 고딕', 11, 'bold'),
            bg=bg, fg=accent,
            bd=1, relief='groove', labelanchor='nw',
        )
        lf_common.pack(fill=X, padx=16, pady=(0, 10))

        for field_key, label_text in self._SAMPLE_COMMON_FIELDS:
            row_fr = tk.Frame(lf_common, bg=bg)
            row_fr.pack(fill=X, padx=12, pady=3)

            lbl = tk.Label(
                row_fr, text=f"{label_text}:", width=14, anchor='e',
                font=('맑은 고딕', 11), bg=bg, fg=fg
            )
            lbl.pack(side=LEFT, padx=(0, 8))

            val = str(sample_row.get(field_key, '') or '')
            ent = tk.Entry(
                row_fr, font=('맑은 고딕', 11),
                bg=bg_input, fg=fg,
                insertbackground=fg,
                relief='solid', bd=1,
                highlightcolor=accent,
                highlightbackground=border_c,
                highlightthickness=1,
            )
            ent.insert(0, val)
            ent.pack(side=LEFT, fill=X, expand=YES, padx=(0, 12))
            common_entries[field_key] = ent

        # ── 컨테이너별 그룹 ──
        for group_idx, (cn, group) in enumerate(container_groups.items()):
            lot_count = len(group['lots'])
            display_cn = cn if cn else '(미지정)'
            lot_list_str = ', '.join(group['lots'][:6])
            if lot_count > 6:
                lot_list_str += f' ... (+{lot_count - 6})'

            lf_cn = tk.LabelFrame(
                scroll_frame,
                text=f"  컨테이너 {group_idx + 1}  ·  LOT {lot_count}개  ",
                font=('맑은 고딕', 11, 'bold'),
                bg=bg, fg=accent,
                bd=1, relief='groove', labelanchor='nw',
            )
            lf_cn.pack(fill=X, padx=16, pady=(0, 8))

            # CONTAINER 입력 필드
            cn_row = tk.Frame(lf_cn, bg=bg)
            cn_row.pack(fill=X, padx=12, pady=3)
            tk.Label(
                cn_row, text="CONTAINER:", width=14, anchor='e',
                font=('맑은 고딕', 11), bg=bg, fg=fg
            ).pack(side=LEFT, padx=(0, 8))
            cn_ent = tk.Entry(
                cn_row, font=('맑은 고딕', 11),
                bg=bg_input, fg=fg,
                insertbackground=fg,
                relief='solid', bd=1,
                highlightcolor=accent,
                highlightbackground=border_c,
                highlightthickness=1,
            )
            cn_ent.insert(0, cn)
            cn_ent.pack(side=LEFT, fill=X, expand=YES, padx=(0, 12))
            container_entries[cn] = cn_ent

            # LOT 목록 (읽기전용)
            lot_row = tk.Frame(lf_cn, bg=bg)
            lot_row.pack(fill=X, padx=12, pady=(0, 6))
            tk.Label(
                lot_row, text="LOTs:", width=14, anchor='e',
                font=('맑은 고딕', 10), bg=bg, fg=fg2
            ).pack(side=LEFT, padx=(0, 8))
            tk.Label(
                lot_row, text=lot_list_str, anchor='w',
                font=('맑은 고딕', 10), bg=bg, fg=fg2
            ).pack(side=LEFT, fill=X, expand=YES)

        # ── 안내 문구 ──
        info_lbl = tk.Label(
            scroll_frame,
            text=(
                f"BL 공통 정보를 수정하면 전체 {total_lots}개 LOT에 일괄 적용됩니다.\n"
                f"컨테이너명을 수정하면 해당 그룹의 LOT에만 적용됩니다."
            ),
            font=('맑은 고딕', 10), bg=bg, fg=fg2, anchor='w', justify='left'
        )
        info_lbl.pack(fill=X, padx=16, pady=(4, 8))

        # ── 버튼 ──
        btn_frame = tk.Frame(scroll_frame, bg=bg)
        btn_frame.pack(fill=X, padx=16, pady=(4, 16))

        def _on_confirm():
            common = {}
            for field_key, _ in self._SAMPLE_COMMON_FIELDS:
                common[field_key] = common_entries[field_key].get().strip()
            containers = {}
            for orig_cn, ent in container_entries.items():
                containers[orig_cn] = ent.get().strip()
            result[0] = {'common': common, 'containers': containers}
            dlg.destroy()

        def _on_cancel():
            result[0] = None
            dlg.destroy()

        btn_ok = tk.Button(
            btn_frame, text="  확인 — 파싱 계속  ",
            font=('맑은 고딕', 12, 'bold'),
            bg=btn_ok_bg, fg='white',
            activebackground=colors.get('btn_inbound_hover', '#34D399'),
            activeforeground='white',
            relief='flat', bd=0, cursor='hand2',
            command=_on_confirm,
        )
        btn_ok.pack(side=LEFT, padx=(0, 12))

        btn_cancel = tk.Button(
            btn_frame, text="  취소  ",
            font=('맑은 고딕', 12),
            bg=btn_cancel_bg, fg='white',
            activebackground=colors.get('btn_neutral_hover', '#64748B'),
            activeforeground='white',
            relief='flat', bd=0, cursor='hand2',
            command=_on_cancel,
        )
        btn_cancel.pack(side=LEFT)

        # ── 다이얼로그 크기·위치 ──
        dlg.update_idletasks()
        w = 600
        h = min(800, dlg.winfo_screenheight() - 100)
        dlg.geometry(f"{w}x{h}")
        dlg.minsize(500, 500)
        px = self.dialog.winfo_x() + (self.dialog.winfo_width() - w) // 2
        py = self.dialog.winfo_y() + max(0, (self.dialog.winfo_height() - h) // 2)
        dlg.geometry(f"+{max(0, px)}+{max(0, py)}")

        dlg.lift()
        dlg.focus_force()
        dlg.attributes('-topmost', True)
        dlg.after(200, lambda: dlg.attributes('-topmost', False))

        dlg.protocol('WM_DELETE_WINDOW', _on_cancel)
        dlg.wait_window()
        return result[0]

    def _apply_sample_edits(self, edits: dict) -> None:
        """
        v7.9.0: 샘플 미리보기에서 수정된 값을 preview_data에 적용.
        - common: 모든 LOT에 적용 (BL 공통)
        - containers: 컨테이너 그룹별 적용 {orig_cn: new_cn}
        """
        if not edits or not self.preview_data:
            return

        common = edits.get('common', {})
        containers = edits.get('containers', {})

        changed_common = []
        # 공통 필드: 원래 값과 다르면 전체 LOT에 적용
        original = self.preview_data[0]
        for key, new_val in common.items():
            old_val = str(original.get(key, '') or '')
            if new_val != old_val:
                changed_common.append(key)
                for row in self.preview_data:
                    row[key] = new_val

        # 컨테이너별 적용: 해당 그룹의 LOT에만 container_no 변경
        changed_containers = []
        if containers:
            # 현재 preview_data에서 컨테이너 그룹 재구성
            cn_groups = {}
            for idx, row in enumerate(self.preview_data):
                cn = (row.get('container_no') or '').strip()
                if cn not in cn_groups:
                    cn_groups[cn] = []
                cn_groups[cn].append(idx)

            for orig_cn, new_cn in containers.items():
                if new_cn != orig_cn and orig_cn in cn_groups:
                    changed_containers.append(f"{orig_cn or '(미지정)'}→{new_cn}")
                    for idx in cn_groups[orig_cn]:
                        self.preview_data[idx]['container_no'] = new_cn

        if changed_common:
            self._log_safe(f"  ✏️ 샘플 수정(공통→전체 LOT): {', '.join(changed_common)}")
        if changed_containers:
            self._log_safe(f"  ✏️ 컨테이너 변경: {', '.join(changed_containers)}")
        if not changed_common and not changed_containers:
            self._log_safe("  ✅ 샘플 확인 완료 — 수정 없음")

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
                    row['status'] = STATUS_AVAILABLE
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
                        row['status'] = str(rec.get('status', '') or STATUS_AVAILABLE)
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
            row['status'] = STATUS_AVAILABLE
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
                
                win.geometry("520x580")
                win.minsize(480, 520)
                apply_modal_window_options(win)
                win.transient(self.dialog)
                win.grab_set()
                center_dialog(win, self.dialog)

                frame = ttk.Frame(win, padding=24)
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
                btn_frame.pack(fill=tk.X, pady=(16, 8))
                
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

    def _show_preview_table(self) -> None:
        """v6.5.0: 파싱 완료 후 미리보기 테이블 표시. compact_mode에서는 no-op."""
        if getattr(self, 'compact_mode', False) or not getattr(self, '_tree_frame', None):
            return
        if getattr(self, "_tree_frame_visible", False):
            return
        try:
            self._tree_frame.pack(fill=BOTH, expand=YES, pady=(0, 3))
            self._tree_frame_visible = True
        except Exception:
            pass

    def _hide_preview_table(self) -> None:
        """v6.5.0: 미리보기 테이블 숨김. compact_mode에서는 no-op."""
        if getattr(self, 'compact_mode', False) or not getattr(self, '_tree_frame', None):
            return
        if not getattr(self, "_tree_frame_visible", False):
            return
        try:
            self._tree_frame.pack_forget()
            self._tree_frame_visible = False
        except Exception:
            pass

    def _update_sort_headings(self) -> None:
        if getattr(self, 'compact_mode', False):
            return
        if not getattr(self, 'tree', None) or not self.tree.winfo_exists():
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

    # v6.2.7: 제품 마스터 콤보박스 생성
    def _create_product_combobox(self, current_val, x, y, w, h):
        """product 열 더블클릭 시 제품 마스터 드롭다운 표시."""
        try:
            from .product_master_helper import get_product_choices
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
        if getattr(self, 'compact_mode', False):
            return
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
        """미리보기 테이블 표시 — 한 번에가 아니라 순차적으로 행 추가 (보기 편하게). compact_mode에서는 메인 창만 갱신."""
        def _update():
            self._push_preview_to_main()
            self._update_summary()
            if self.preview_data and self._has_required_docs():
                self.btn_upload.config(state='normal')
            else:
                self.btn_upload.config(state='disabled')
            if self.preview_data:
                self.btn_excel.config(state='normal')
            if getattr(self, 'compact_mode', False):
                return
            if not getattr(self, 'tree', None) or not self.tree.winfo_exists():
                return
            self._refresh_preview_tree_only()
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
                            _app._safe_refresh()
                            logger.info("[onestop] 전체 탭 새로고침 완료")
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
    
    # ─────────────────────────────────────────────────────────────
    # v6.4.0: 선사 뱃지 UI 업데이트
    # ─────────────────────────────────────────────────────────────


    def _reparse_after_carrier_change(self) -> None:
        """v7.4.0: 수동 선사 변경 후 PL/INV 재파싱."""
        cid = getattr(self, '_carrier_manual_var', None)
        cid = cid.get().strip() if cid else 'UNKNOWN'
        if cid == 'UNKNOWN':
            try:
                from ..utils.custom_messagebox import CustomMessageBox
                CustomMessageBox.showwarning(
                    self.dialog, "선사 미선택",
                    "먼저 '수동 선택' Combobox에서 선사를 선택하세요."
                )
            except Exception:
                pass
            return
        if 'PACKING_LIST' not in self.file_paths:
            try:
                from ..utils.custom_messagebox import CustomMessageBox
                CustomMessageBox.showwarning(
                    self.dialog, "재파싱 불가", "Packing List 파일이 없습니다."
                )
            except Exception:
                pass
            return
        try:
            from features.ai.bl_carrier_registry import CARRIER_TEMPLATES
            _ctpl = CARRIER_TEMPLATES.get(cid)
            cname = _ctpl.carrier_name if _ctpl else cid
            # 힌트 강제 교체
            _tpl = getattr(self, '_inbound_template_data', {}) or {}
            if _ctpl:
                if not _tpl.get('gemini_hint_packing'):
                    _tpl['gemini_hint_packing'] = (
                        f"이 서류는 {cname} 선사의 Packing List입니다. "
                        f"BL번호 형식: {getattr(_ctpl, 'bl_format_hint', '')}"
                    )
                if not _tpl.get('gemini_hint_invoice'):
                    _tpl['gemini_hint_invoice'] = (
                        f"이 서류는 {cname} 선사의 Invoice/FA입니다."
                    )
                self._inbound_template_data = _tpl
        except Exception as e:
            logger.debug(f"선사 힌트 강제 교체 실패: {e}")
        self._log_safe(f"🚢 선사 재파싱 시작: {cid} → PL/INV 힌트 적용")
        self._start_parsing()

    def _on_add_do_later(self) -> None:
        """v7.4.0: D/O 나중에 추가 — do_update_dialog로 연결."""
        try:
            from ..dialogs.do_update_dialog import DoUpdateDialog
            current_theme = getattr(self.parent, 'current_theme', 'flatly')
            DoUpdateDialog(self.dialog, self.engine, current_theme=current_theme)
            self._log_safe("📋 D/O 후속 연결 다이얼로그 열림")
        except Exception as e:
            logger.error(f"D/O 나중에 추가 오류: {e}")
            try:
                from ..utils.custom_messagebox import CustomMessageBox
                CustomMessageBox.showerror(
                    self.dialog, "오류",
                    f"D/O 다이얼로그를 열 수 없습니다.\n{e}\n\n"
                    f"메뉴 → 입고 → [D/O 후속 연결] 을 사용하세요."
                )
            except Exception:
                pass

    def _on_carrier_manual_select(self, event=None) -> None:
        """v7.3.9: 수동 선사 선택 → 배지 색상 갱신 + parsed_results 반영."""
        try:
            cid = self._carrier_manual_var.get().strip()
            if not cid or cid == 'UNKNOWN':
                self._carrier_label.config(
                    text="  (선사 미선택)  ",
                    fg="#888888",
                    bg="#E8E8E8"
                )
                return
            # 선사명 조회
            try:
                from features.ai.bl_carrier_registry import CARRIER_TEMPLATES
                _ctpl = CARRIER_TEMPLATES.get(cid)
                cname = _ctpl.carrier_name if _ctpl else cid
            except Exception:
                cname = cid

            # 배지 갱신
            self._update_carrier_badge(f"[선사: {cname}] (수동선택)")

            # parsed_results의 bl 결과에도 carrier_id 주입
            bl_r = self.parsed_results.get('bl')
            if bl_r:
                try:
                    bl_r.carrier_id   = cid
                    bl_r.carrier_name = cname
                except Exception:
                    pass

            self._log_safe(f"🚢 선사 수동 선택: {cname} ({cid})")
            # 선사 재파싱 버튼 활성화
            if hasattr(self, 'btn_reparse_carrier'):
                try:
                    self.btn_reparse_carrier.config(state='normal')
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"수동 선사 선택 오류: {e}")

    def _update_carrier_badge(self, badge_text: str) -> None:
        """
        BL 파싱 후 선사 뱃지를 입고 다이얼로그 BL 버튼 아래 라벨에 표시.
        badge_text 예시: "[선사: Mediterranean Shipping Company]"
        선사별 전경색(fg) + 배경색(bg) 적용.
        """
        try:
            if not hasattr(self, '_carrier_label') or self._carrier_label is None:
                return  # 위젯 미생성 시 무시 (로그에는 이미 출력됨)
            # 선사별 (전경색, 배경색) 매핑 — v7.7.2: 밝은 파스텔 톤
            _style_map = {
                "MSC":     ("#154360", "#AED6F1"),  # 진한남색 글씨 / 밝은 파랑
                "MAERSK":  ("#0E6251", "#A3E4D7"),  # 진한초록 글씨 / 밝은 그린
                "HMM":     ("#78281F", "#F5B7B1"),  # 진한빨강 글씨 / 밝은 레드
                "CMA_CGM": ("#784212", "#FAD7A0"),  # 진한갈색 글씨 / 밝은 오렌지
                "ONE":     ("#6C3483", "#D7BDE2"),  # 진한보라 글씨 / 밝은 핑크
            }
            _carrier_id = ""
            bl_r = self.parsed_results.get('bl')
            if bl_r:
                _carrier_id = getattr(bl_r, 'carrier_id', '')
            _fg, _bg = _style_map.get(_carrier_id, ("#555555", "#E8E8E8"))  # 기본 회색
            self._carrier_label.config(
                text=f"  {badge_text}  ",
                fg=_fg, bg=_bg
            )
        except Exception as _e:
            logger.debug(f"[CarrierBadge] UI 업데이트 실패(무시): {_e}")

    def _enable_parse_btn(self):
        def _u():
            if self.dialog and self.dialog.winfo_exists():
                self._update_parse_hint()
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, _u)
    
    def _on_cancel(self):
        self._clear_preview_from_main()
        # v7.7.2: 스크롤 바인딩 정리
        try:
            c = getattr(self, '_scroll_canvas', None)
            if c and c.winfo_exists():
                c.unbind_all('<MouseWheel>')
                c.unbind_all('<Shift-MouseWheel>')
        except Exception:
            pass
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
