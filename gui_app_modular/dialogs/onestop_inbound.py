"""
from ..utils.custom_messagebox import CustomMessageBox
SQM v3.8.4 — 원스톱 입고 팝업
4종 서류(PL, Invoice, BL, DO)를 한 화면에서:
  파일 선택 → 체크 표시 → 파싱 → 미리보기 → DB 업로드

작성일: 2025-02-06
"""
import sqlite3
import os
import tkinter as tk
from tkinter import ttk, filedialog, BOTH, YES, X, Y, LEFT, RIGHT, BOTTOM, END, VERTICAL, HORIZONTAL
import logging
import threading
from datetime import datetime

# 비즈니스 기본값
from engine_modules.constants import DEFAULT_WAREHOUSE

from ..utils.ui_constants import ThemeColors

logger = logging.getLogger(__name__)

def _safe_float(val, default: float = 0.0) -> float:
    """안전한 float 변환"""
    if not val:
        return default
    try:
        return float(str(val).replace(',', '').strip())
    except (ValueError, TypeError):
        return default


# 미리보기 18열 헤더 정의 (v3.8.8: 재고탭과 헤더명 통일)
PREVIEW_COLUMNS = [
    ("no",               "NO",               50,  "center"),
    ("sap_no",           "SAP NO",          110,  "center"),
    ("bl_no",            "BL NO",           150,  "center"),
    ("container_no",     "CONTAINER",       130,  "center"),
    ("product",          "PRODUCT",         180,  "w"),
    ("product_code",     "CODE",            100,  "center"),
    ("lot_no",           "LOT NO",          110,  "center"),
    ("lot_sqm",          "LOT SQM",          80,  "center"),
    ("mxbg_pallet",      "MXBG",             70,  "center"),
    ("tonbag_count",     "TONBAG",            70,  "center"),
    ("net_weight",       "NET(Kg)",           90,  "e"),
    ("gross_weight",     "GROSS(kg)",         90,  "e"),
    ("salar_invoice_no", "INVOICE NO",      120,  "center"),
    ("ship_date",        "SHIP DATE",        90,  "center"),
    ("arrival_date",     "ARRIVAL",           90,  "center"),
    ("free_time",        "FREE TIME",        80,  "center"),
    ("warehouse",        "WH",              100,  "w"),
    ("status",           "STATUS",           80,  "center"),
]

# 4종 서류 정의 (v3.8.7: 동그라미 번호 순서)
DOC_TYPES = [
    ('PACKING_LIST', '① Packing List (포장명세서)', True),
    ('INVOICE',      '② Invoice / Factura (송장)',  True),
    ('BL',           '③ B/L (선하증권)',            True),
    ('DO',           '④ D/O (인도지시서) (선택사항)', False),
]


from .inbound_dialog_base import InboundDialogBase


class OneStopInboundDialog(InboundDialogBase):
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
        
        # UI 참조
        self.dialog = None
        self.file_labels = {}
        self.check_labels = {}
        self.tree = None
        self.btn_parse = None
        self.btn_upload = None
        self.btn_excel = None
    
    def show(self) -> None:
        """팝업 표시"""
        self._create_dialog()
    
    def _attach_doc_tooltip(self, widget, text: str):
        """v3.8.9: 문서 위젯에 툴팁 추가"""
        tip = None
        def enter(e):
            nonlocal tip
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{e.x_root+15}+{e.y_root+10}")
            lbl = tk.Label(tip, text=text, justify='left',
                          background='#ffffcc', foreground='#333333',
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
        self.dialog.geometry("1500x800")
        # v3.8.8: transient 제거 → 최대화/최소화 버튼 표시
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        # ★ v3.8.8: 시작 시 최대화
        try:
            self.dialog.state('zoomed')  # Windows 최대화
        except tk.TclError:
            try:
                self.dialog.attributes('-zoomed', True)  # Linux
            except tk.TclError as _e:
                logger.debug(f"[onestop_inbound] 무시: {_e}")
        
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
            'BL':           '③ BL',
            'DO':           '④ DO',
        }
        
        # v3.8.9: 서류별 상세 툴팁
        _tooltips = {
            'PACKING_LIST': '📦 Packing List (포장명세서)\n\n• LOT번호, 제품명, 수량, 중량 정보 추출\n• 필수 서류 — 없으면 입고 불가\n• PDF 또는 Excel 파일 지원',
            'INVOICE':      '📑 Invoice / Factura (송장)\n\n• SAP번호, 단가, 총금액 정보 추출\n• 필수 서류 — 없으면 SAP번호 누락\n• PDF 파일 지원',
            'BL':           '🚢 B/L (선하증권)\n\n• BL번호, 선박명, 출항일, 도착일 추출\n• 필수 서류 — 없으면 선적 정보 누락\n• PDF 파일 지원',
            'DO':           '📋 D/O (인도지시서)\n\n• 인도 장소, Free Time 정보 추출\n• 선택 서류 — 없어도 입고 가능\n• PDF 파일 지원',
        }
        
        for idx, (doc_type, doc_name, required) in enumerate(DOC_TYPES):
            cell = ttk.Frame(file_frame)
            cell.grid(row=0, column=idx, sticky='ew', padx=(0, 2))
            
            # 서류명
            lbl = ttk.Label(cell, text=short_names.get(doc_type, ''),
                      font=('맑은 고딕', 14, 'bold'))
            lbl.pack(side=LEFT, padx=(2, 2))
            self._attach_doc_tooltip(lbl, _tooltips.get(doc_type, ''))
            
            # 📂 폴더선택 버튼
            btn_sel = tk.Button(cell, text="📂",
                                command=lambda dt=doc_type: self._select_file(dt),
                                font=('', 13), bg='#555555', fg='white',
                                padx=4, pady=1, cursor='hand2', bd=0)
            btn_sel.pack(side=LEFT, padx=(0, 2))
            _req = '(필수)' if required else '(선택)'
            self._attach_doc_tooltip(btn_sel, f"클릭하여 {doc_name} 파일 선택 {_req}")
            
            # 체크 표시
            check_label = ttk.Label(cell, text="☐", font=('', 15))
            check_label.pack(side=LEFT, padx=(0, 2))
            self.check_labels[doc_type] = check_label
            
            # 파일명 (숨김 — 체크되면 표시)
            file_label = ttk.Label(cell, text="", foreground='#aaaaaa',
                                   font=('맑은 고딕', 12), anchor='w')
            file_label.pack(side=LEFT, fill=X, expand=True, padx=(0, 2))
            self.file_labels[doc_type] = file_label
        
        # [파싱 시작] 버튼
        self.btn_parse = ttk.Button(
            file_frame, text="▶ 파싱 시작",
            command=self._start_parsing,
            state='disabled', width=10
        )
        self.btn_parse.grid(row=0, column=4, padx=(6, 2))
        self._attach_doc_tooltip(self.btn_parse,
            "선택한 서류를 분석합니다\n\n• Packing List → LOT, 수량, 중량 추출\n• Invoice → SAP번호, 금액 추출\n• B/L → BL번호, 선박, 일정 추출\n• D/O → 인도장소, Free Time 추출")
        
        self.parse_hint = ttk.Label(
            file_frame, text="",
            foreground='white', font=('맑은 고딕', 12)
        )
        self.parse_hint.grid(row=0, column=5, padx=(2, 4), sticky='w')
        
        # ═══════════════════════════════════════════════════════════
        # 2. 프로그레스 바 + 상태 (v3.8.7: 왼쪽 정렬, 전체 폭)
        # ═══════════════════════════════════════════════════════════
        progress_frame = ttk.Frame(main)
        progress_frame.pack(fill=X, pady=(0, 3))
        
        self.status_var = tk.StringVar(value="")
        ttk.Label(progress_frame, textvariable=self.status_var,
                  font=('맑은 고딕', 13, 'bold')).pack(side=LEFT)
        
        self.progress_pct = tk.StringVar(value="")
        ttk.Label(progress_frame, textvariable=self.progress_pct,
                  font=('맑은 고딕', 12)).pack(side=LEFT, padx=(8, 4))
        
        self.progress_var = tk.DoubleVar(value=0)
        # v3.8.8: 프로그레스 바 밝은 노란색
        _ps = ttk.Style()
        _ps.configure('Yellow.Horizontal.TProgressbar',
                       troughcolor='#333333', background='#f1c40f',
                       thickness=18)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var,
            maximum=100, mode='determinate',
            style='Yellow.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        # ═══════════════════════════════════════════════════════════
        # 3. 미리보기 테이블 (v3.8.7: 폰트 20% 확대)
        # ═══════════════════════════════════════════════════════════
        tree_frame = ttk.LabelFrame(main, text="📊 미리보기 (확인 후 업로드)", padding=4)
        tree_frame.pack(fill=BOTH, expand=YES, pady=(0, 3))
        
        # ★ v3.8.7: 미리보기 Treeview 폰트 20% 확대 (기본 9pt → 11pt)
        import tkinter.font as tkfont
        preview_font = tkfont.Font(family='맑은 고딕', size=14)
        heading_font = tkfont.Font(family='맑은 고딕', size=13, weight='bold')
        row_height = preview_font.metrics('linespace') + 8
        
        style = ttk.Style()
        style.configure('Preview.Treeview',
                        font=('맑은 고딕', 14),
                        rowheight=row_height)
        style.configure('Preview.Treeview.Heading',
                        font=('맑은 고딕', 13, 'bold'))
        
        columns = tuple(col[0] for col in PREVIEW_COLUMNS)
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            height=18, selectmode='browse',
            style='Preview.Treeview'
        )
        
        for col_id, header, width, anchor in PREVIEW_COLUMNS:
            self.tree.heading(col_id, text=header)
            self.tree.column(col_id, width=width, anchor=anchor, minwidth=35)
        
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        scrollbar_x.pack(side=BOTTOM, fill=X)
        self.tree.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar_y.pack(side=RIGHT, fill=Y)
        
        # 합계행
        self.summary_var = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.summary_var,
                  font=('맑은 고딕', 13, 'bold'),
                  foreground='#4fc3f7').pack(fill=X, pady=(2, 0))
        
        # ═══════════════════════════════════════════════════════════
        # 4. 하단 버튼
        # ═══════════════════════════════════════════════════════════
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=X, pady=(8, 0))
        
        _font = getattr(self, '_toolbar_font', '맑은 고딕') if hasattr(self, '_toolbar_font') else '맑은 고딕'
        
        # 우측: DB 업로드 (맨 오른쪽)
        self.btn_upload = tk.Button(
            btn_frame, text="📤 DB 업로드",
            command=self._on_upload, state='disabled',
            font=(_font, 17, 'bold'), bg=ThemeColors.get('statusbar_icon_err'), fg='white',
            padx=20, pady=8, cursor='hand2', bd=0
        )
        self.btn_upload.pack(side=RIGHT, padx=(5, 0))
        self._attach_doc_tooltip(self.btn_upload,
            "미리보기 데이터를 DB에 저장합니다\n\n• 저장 후 재고리스트에 자동 반영\n• 중복 LOT는 자동 스킵\n• 저장 완료 후 재고리스트 화면 표시")
        
        # 우측: 취소 (DB 업로드 왼쪽)
        tk.Button(
            btn_frame, text="❌ 취소",
            command=self._on_cancel,
            font=(_font, 17, 'bold'), bg=ThemeColors.get('statusbar_icon_warn'), fg='white',
            padx=20, pady=8, cursor='hand2', bd=0
        ).pack(side=RIGHT, padx=(5, 0))
        
        # v3.8.8: 좌측: Excel 내보내기 (큰 글씨)
        self.btn_excel = tk.Button(
            btn_frame, text="📥 Excel 내보내기",
            command=self._export_to_excel, state='disabled',
            font=(_font, 15, 'bold'), bg=ThemeColors.get('badge_db'), fg='white',
            padx=15, pady=6, cursor='hand2', bd=0
        )
        self.btn_excel.pack(side=LEFT, padx=(0, 5))
    
    # ═══════════════════════════════════════════════════════════
    # 파일 선택
    # ═══════════════════════════════════════════════════════════
    
    def _select_file(self, doc_type: str):
        """서류별 파일 선택"""
        type_names = {
            'PACKING_LIST': 'Packing List',
            'INVOICE': 'Invoice / Factura',
            'BL': 'B/L (선하증권)',
            'DO': 'D/O (인도지시서)',
        }
        
        file_path = filedialog.askopenfilename(
            parent=self.dialog,
            title=f"{type_names.get(doc_type, doc_type)} 파일 선택",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        self.file_paths[doc_type] = file_path
        fname = os.path.basename(file_path)
        
        # UI 업데이트
        self.file_labels[doc_type].config(text=fname, foreground='black')
        self.check_labels[doc_type].config(text="✅")
        
        self._log(f"📂 {doc_type}: {fname}")
        
        # 파싱 버튼 활성화 조건: PL 필수
        if 'PACKING_LIST' in self.file_paths:
            self.btn_parse.config(state='normal')
            selected = sum(1 for _ in self.file_paths.values())
            self.parse_hint.config(
                text=f"✅ {selected}종 선택 완료 — [파싱 시작] 클릭",
                foreground='white'
            )
        else:
            self.parse_hint.config(
                text="💡 최소 Packing List를 선택하세요",
                foreground='#aaa'
            )
    
    # ═══════════════════════════════════════════════════════════
    # 파싱
    # ═══════════════════════════════════════════════════════════
    
    def _start_parsing(self) -> None:
        """v3.8.9: 파싱 시작 — 누락 서류 경고 후 진행"""
        # 서류 누락 검사
        missing_required = []
        missing_optional = []
        for doc_type, doc_name, required in DOC_TYPES:
            if doc_type not in self.file_paths:
                if required:
                    missing_required.append(doc_name)
                else:
                    missing_optional.append(doc_name)
        
        # 경고 메시지 구성
        if missing_required:
            warning_lines = ["⚠️ 다음 필수 서류가 선택되지 않았습니다:\n"]
            for name in missing_required:
                warning_lines.append(f"  • {name}")
            warning_lines.append("\n선택하지 않은 서류의 정보는 누락됩니다.")
            if missing_optional:
                warning_lines.append(f"\n📋 선택 서류 미선택: {', '.join(missing_optional)}")
            warning_lines.append("\n계속 진행하시겠습니까?")
            proceed = msgbox.askyesno(
                "서류 누락 확인",
                "\n".join(warning_lines),
                parent=self.dialog
            )
            if not proceed:
                return
        elif missing_optional:
            # 선택 서류만 누락 — 정보 안내만
            self._update_progress(0, f"ℹ️ {', '.join(missing_optional)} 미선택 — 해당 정보 생략")
        
        self.btn_parse.config(state='disabled')
        
        thread = threading.Thread(
            target=self._parse_thread,
            daemon=True
        )
        thread.start()
    
    def _update_progress(self, pct: int, message: str):
        """프로그레스 바 업데이트 (스레드 안전)"""
        def _update():
            self.progress_var.set(pct)
            self.progress_pct.set(f"{pct}%" if pct > 0 else "")
            self.status_var.set(message)
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, _update)
    
    def _parse_thread(self) -> None:
        """백그라운드 파싱"""
        try:
            from parsers.document_parser_v2 import DocumentParserV2
            
            gemini_key = os.environ.get('GEMINI_API_KEY', '')
            if not gemini_key:
                try:
                    from config import get_settings
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
            
            for idx, (doc_type, file_path) in enumerate(to_parse):
                fname = os.path.basename(file_path)
                icon = icons.get(doc_type, '📄')
                pct = int(10 + 70 * idx / total)
                
                self._update_progress(pct, f"{icon} [{idx+1}/{total}] {doc_type} 파싱: {fname}")
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
            
            # 병합
            self._update_progress(85, "📊 데이터 병합 중...")
            self._merge_results(inv_result, pl_result, bl_result, do_result)
            
            # v3.8.9: 파싱 결과 경고 (누락된 정보)
            _warnings = []
            if not pl_result or not getattr(pl_result, 'lots', None):
                _warnings.append("⚠️ Packing List: LOT 정보 추출 실패")
            if not inv_result or not getattr(inv_result, 'sap_no', None):
                _warnings.append("⚠️ Invoice: SAP번호 추출 실패 — 수동 입력 필요")
            if not bl_result or not getattr(bl_result, 'bl_no', None):
                _warnings.append("⚠️ B/L: BL번호 추출 실패 — 수동 입력 필요")
            
            if _warnings:
                _warn_msg = "\n".join(_warnings)
                self._log_safe(f"\n{'='*40}\n{_warn_msg}\n{'='*40}")
                # GUI 경고
                def _show_warn():
                    CustomMessageBox.warning(None, "파싱 결과 확인", _warn_msg, parent=self.dialog)
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(500, _show_warn)
            
            # 표시
            self._update_progress(95, "📋 미리보기 준비...")
            self._display_preview()
            
            self._update_progress(100, f"✅ 파싱 완료 — {len(self.preview_data)}개 LOT")
            self._log_safe(f"✅ 파싱 완료: {len(self.preview_data)} LOT, {total}종 서류")
        
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
            return
        
        for idx, lot in enumerate(getattr(pl, 'lots', []) or [], 1):
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
            
            # v3.8.8: B/L ship_date 우선, Invoice는 폴백
            if bl:
                row['bl_no'] = self._format_bl(getattr(bl, 'bl_no', '') or '')
                _sd = getattr(bl, 'ship_date', None)
                if _sd:
                    row['ship_date'] = str(_sd)
            
            if invoice:
                row['salar_invoice_no'] = getattr(invoice, 'salar_invoice_no', '') or ''
                if not row['ship_date']:
                    _id = getattr(invoice, 'invoice_date', None)
                    if _id:
                        row['ship_date'] = str(_id)
                if not row['sap_no']:
                    row['sap_no'] = getattr(invoice, 'sap_no', '') or ''
            
            self._fill_do(row, do)
            row['status'] = 'AVAILABLE'
            self.preview_data.append(row)
    
    def _empty_row(self, no: int) -> dict:
        row = {col[0]: '' for col in PREVIEW_COLUMNS}
        row['no'] = str(no)
        return row
    
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
        
        # arrival_date
        arr = getattr(do, 'arrival_date', None)
        if arr and str(arr) != 'None':
            row['arrival_date'] = str(arr)
        
        # warehouse
        wh = getattr(do, 'warehouse_name', '') or getattr(do, 'warehouse', '')
        if wh:
            row['warehouse'] = str(wh)
        
        # free_time 계산: free_time_info[0].free_time_date - arrival_date
        ft_infos = getattr(do, 'free_time_info', []) or []
        if ft_infos and arr and str(arr) != 'None':
            try:
                # free_time_date 추출 (첫 번째 컨테이너)
                ft_date_str = ''
                for ft in ft_infos:
                    ftd = getattr(ft, 'free_time_date', '') if not isinstance(ft, dict) else ft.get('free_time_date', '')
                    if ftd and str(ftd) != 'None':
                        ft_date_str = str(ftd)[:10]
                        break
                
                if ft_date_str:
                    ft_dt = _dt.strptime(ft_date_str, '%Y-%m-%d').date()
                    arr_dt = _dt.strptime(str(arr)[:10], '%Y-%m-%d').date()
                    days = (ft_dt - arr_dt).days
                    row['free_time'] = str(max(0, days))
            except (ValueError, TypeError) as e:
                logging.getLogger(__name__).debug(f"free_time 계산 실패: {e}")
    
    # ═══════════════════════════════════════════════════════════
    # 미리보기 표시
    # ═══════════════════════════════════════════════════════════
    
    def _display_preview(self) -> None:
        """미리보기 테이블 표시 (메인 스레드)"""
        def _update():
            if not self.tree:
                return
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            for row in self.preview_data:
                values = tuple(row.get(col[0], '') for col in PREVIEW_COLUMNS)
                self.tree.insert('', END, values=values)
            
            self._update_summary()
            
            # v5.7.0: 필수 3종(PL+FA+BL) 모두 있을 때만 DB 업로드 허용
            if self.preview_data and self._has_required_docs():
                self.btn_upload.config(state='normal')
            else:
                self.btn_upload.config(state='disabled')
            if self.preview_data:
                self.btn_excel.config(state='normal')
        
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
                total_net += _safe_float(r['net_weight']) if r['net_weight'] else 0
            except (ValueError, TypeError) as _e:
                logger.debug(f"onestop_inbound: {_e}")
            try:
                total_gross += _safe_float(r['gross_weight']) if r['gross_weight'] else 0
            except (ValueError, TypeError) as _e:
                logger.debug(f"onestop_inbound: {_e}")
        
        self.summary_var.set(
            f"합계: {len(self.preview_data)} LOT | "
            f"{len(containers)} 컨테이너 | "
            f"{total_tb} 톤백 | "
            f"Net {total_net:,.0f} kg | "
            f"Gross {total_gross:,.0f} kg"
        )
    
    # ═══════════════════════════════════════════════════════════
    # DB 업로드
    # ═══════════════════════════════════════════════════════════
    
    def _on_upload(self) -> None:
        """DB 업로드 (v3.8.8: 중복 LOT 사전 경고 + 위젯 안전 처리)"""
        if not self.preview_data:
            return
        # v5.7.0: 필수 3종(PL+FA+BL) 없으면 업로드 차단
        if not self._has_required_docs():
            missing = [name for (dt, name, req) in DOC_TYPES if req and dt not in self.file_paths]
            try:
                from ..utils.custom_messagebox import CustomMessageBox
                CustomMessageBox.showwarning(
                    self.dialog, "필수 서류 누락",
                    "DB 업로드를 하려면 다음 3종 서류가 모두 필요합니다:\n\n"
                    "  • ① Packing List (포장명세서)\n"
                    "  • ② Invoice / Factura (송장)\n"
                    "  • ③ B/L (선하증권)\n\n"
                    f"누락: {', '.join(missing)}\n\n"
                    "D/O(인도지시서)는 선택사항이며, 나중에 [📋 D/O 후속 연결] 메뉴로 보충할 수 있습니다."
                )
            except (ImportError, ModuleNotFoundError):
                from tkinter import messagebox
                messagebox.showwarning("필수 서류 누락", "Packing List, Invoice, B/L 3종 모두 필요합니다.")
            return

        # v3.8.8: 중복 LOT 사전 체크
        dup_lots = []
        if hasattr(self.engine, '_check_lot_exists') or hasattr(self.engine, 'db'):
            try:
                db = getattr(self.engine, 'db', None)
                if db:
                    for row in self.preview_data:
                        lot_no = row.get('lot_no', '')
                        if lot_no:
                            existing = db.fetchone(
                                "SELECT 1 FROM inventory WHERE lot_no = ?", (lot_no,))
                            if existing:
                                dup_lots.append(lot_no)
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
                logger.debug(f"중복 체크 오류: {e}")
        
        if dup_lots:
            try:
                from ..utils.custom_messagebox import CustomMessageBox
                dup_msg = ', '.join(dup_lots[:5])
                if len(dup_lots) > 5:
                    dup_msg += f" 외 {len(dup_lots) - 5}건"
                ok = CustomMessageBox.askyesno(
                    self.dialog, "⚠️ 중복 LOT 경고",
                    f"다음 {len(dup_lots)}개 LOT가 이미 DB에 존재합니다:\n\n"
                    f"{dup_msg}\n\n"
                    f"중복 LOT는 건너뛰고 나머지만 입고합니다.\n계속하시겠습니까?"
                )
            except (ImportError, ModuleNotFoundError):
                ok = msgbox.askyesno("⚠️ 중복 LOT 경고",
                    f"{len(dup_lots)}개 LOT 중복! 건너뛰고 계속?")
            if not ok:
                return
        
        try:
            from ..utils.custom_messagebox import CustomMessageBox
            ok = CustomMessageBox.askyesno(
                self.dialog, "DB 업로드 확인",
                f"{len(self.preview_data)}개 LOT를 데이터베이스에 저장합니다.\n\n"
                f"이 작업은 되돌릴 수 없습니다.\n계속하시겠습니까?"
            )
        except (ImportError, ModuleNotFoundError):
            ok = msgbox.askyesno("DB 업로드 확인",
                f"{len(self.preview_data)}개 LOT 저장?")
        
        if not ok:
            return
        
        # v3.8.8: 위젯 존재 확인 후 비활성화
        try:
            if self.btn_upload and self.btn_upload.winfo_exists():
                self.btn_upload.config(state='disabled')
            if self.btn_excel and self.btn_excel.winfo_exists():
                self.btn_excel.config(state='disabled')
        except (RuntimeError, ValueError) as _e:
            logger.debug(f'Suppressed: {_e}')
        
        thread = threading.Thread(target=self._upload_thread, daemon=True)
        thread.start()
    
    def _upload_thread(self) -> None:
        """백그라운드 DB 업로드"""
        try:
            self._update_progress(0, "📤 DB 업로드 시작...")
            
            pl = self.parsed_results.get('packing_list')
            invoice = self.parsed_results.get('invoice')
            bl = self.parsed_results.get('bl')
            do = self.parsed_results.get('do')
            
            if not pl or not getattr(pl, 'lots', None):
                self._update_progress(0, "❌ Packing List 없음")
                self._enable_buttons()
                return
            # v5.7.0: 필수 3종(PL+FA+BL) 없으면 업로드 중단 — 중복/부분 업로드 방지
            if not invoice:
                self._update_progress(0, "❌ FA(송장) 필수 — 3종(PL+FA+BL) 모두 필요")
                self._enable_buttons()
                return
            if not bl:
                self._update_progress(0, "❌ B/L(선하증권) 필수 — 3종(PL+FA+BL) 모두 필요")
                self._enable_buttons()
                return

            success, failed_rows = self._save_to_db(pl, invoice, bl, do)
            
            if success:
                total = len(self.preview_data)
                self._update_progress(100, f"✅ 업로드 완료: {total} LOT")
                self._log_safe(f"✅ DB 업로드 완료: {total} LOT")
                self.upload_success = True
                self._show_success_and_close(total)
            else:
                self._update_progress(0, "❌ 업로드 실패")
                
                # v4.2.1: 상세 실패 팝업 표시 (실패한 행 번호 포함)
                try:
                    from ..utils.upload_error_dialog import show_upload_error_dialog
                    from ..utils.upload_error_template import UploadErrorTemplate
                    
                    rows_for_msg = failed_rows if failed_rows else [{'row': '?', 'value': '업로드 실패', 'column': ''}]
                    error_msg = UploadErrorTemplate.format_multiple_errors(
                        errors=[{
                            'type': 'missing_required',
                            'rows': rows_for_msg
                        }],
                        total_rows=len(self.preview_data)
                    )
                    
                    show_upload_error_dialog(
                        self.dialog,
                        "입고 업로드 실패",
                        error_msg
                    )
                except (ImportError, Exception) as _e:
                    # 팝업 실패 시 기존 방식으로 표시
                    from ..utils.ui_constants import CustomMessageBox
                    CustomMessageBox.showerror(
                        self.dialog,
                        "업로드 실패",
                        "입고 처리 중 오류가 발생했습니다.\n로그를 확인하세요."
                    )
                
                self._enable_buttons()
        
        except (ValueError, TypeError, AttributeError) as e:
            self._update_progress(0, f"❌ 오류: {e}")
            self._log_safe(f"❌ 업로드 오류: {e}")
            logger.error(f"업로드 오류: {e}", exc_info=True)
            
            # v4.2.1: 예외 발생 시에도 상세 팝업 표시
            try:
                from ..utils.upload_error_dialog import show_upload_error_dialog
                from ..utils.upload_error_template import UploadErrorTemplate
                
                error_msg = UploadErrorTemplate.format_multiple_errors(
                    errors=[{
                        'type': 'file_format',
                        'rows': [{'row': '?', 'value': str(e), 'column': ''}]
                    }],
                    total_rows=len(self.preview_data) if hasattr(self, 'preview_data') else 0
                )
                
                show_upload_error_dialog(
                    self.dialog,
                    "입고 처리 오류",
                    error_msg
                )
            except (ImportError, Exception):
                # 팝업 실패 시 기존 방식
                from ..utils.ui_constants import CustomMessageBox
                CustomMessageBox.showerror(
                    self.dialog,
                    "오류",
                    f"입고 처리 오류:\n{e}"
                )
            
            self._enable_buttons()
    
    def _save_to_db(self, pl, invoice, bl, do):
        """engine.process_inbound를 LOT별로 호출하여 DB 저장
        
        v3.8.8: 이중 트랜잭션 제거 — process_inbound 내부 트랜잭션에 위임
        각 LOT가 독립적으로 커밋됨. 중복 LOT는 자동 건너뜀.
        
        Returns:
            (success: bool, failed_rows: list) — 실패 시 실패한 행 정보 [{'row': N, 'value': msg, 'column': ''}, ...]
        """
        try:
            if not hasattr(self.engine, 'process_inbound'):
                self._log_safe("❌ engine.process_inbound 메서드 없음")
                return False, []

            _lots = getattr(pl, 'lots', []) or []
            total = len(_lots)
            if total == 0:
                return False, []

            created_lots = []
            skipped_lots = []
            errors = []
            failed_rows = []  # 업로드 실패 요약용: [{'row': Excel행, 'value': 오류메시지, 'column': ''}, ...]
            
            for idx, lot in enumerate(_lots):
                pct = 10 + int(80 * (idx + 1) / total)
                lot_no = getattr(lot, 'lot_no', '') or ''
                self._update_progress(pct, f"📦 LOT {idx+1}/{total}: {lot_no}")
                
                # v3.8.8: 중복 LOT 건너뛰기 (에러 대신 skip)
                if lot_no:
                    try:
                        existing = self.engine.db.fetchone(
                            "SELECT 1 FROM inventory WHERE lot_no = ?", (lot_no,))
                        if existing:
                            self._log_safe(f"  ⏭ LOT {lot_no}: 이미 존재 (건너뜀)")
                            skipped_lots.append(lot_no)
                            continue
                    except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                        logger.debug(f'Suppressed: {_e}')
                
                # PackingData 호환 dict
                # v3.8.8: free_time 계산 (None 안전 처리)
                _arrival_raw = getattr(do, 'arrival_date', None) if do else None
                _arrival = str(_arrival_raw) if _arrival_raw and str(_arrival_raw) != 'None' else ''
                _free_time = 0
                _free_time_date = ''
                if do:
                    _free_time_date = str(getattr(do, 'free_time_date', '') or '')
                    if not _free_time_date:
                        # free_time_info 리스트에서 추출
                        ft_infos = getattr(do, 'free_time_info', []) or []
                        for ft in ft_infos:
                            ftd = getattr(ft, 'free_time_date', '') or (ft.get('free_time_date', '') if isinstance(ft, dict) else '')
                            if ftd:
                                _free_time_date = str(ftd)
                                break
                    
                    # 계산: free_time_date - arrival_date
                    if _free_time_date and _arrival:
                        try:
                            _ft_dt = _dt.strptime(str(_free_time_date)[:10], '%Y-%m-%d').date()
                            _arr_dt = _dt.strptime(str(_arrival)[:10], '%Y-%m-%d').date()
                            _free_time = (_ft_dt - _arr_dt).days
                            if _free_time < 0:
                                _free_time = 0
                        except (ValueError, TypeError):
                            _free_time = 0
                
                packing_dict = {
                    'lot_no': getattr(lot, 'lot_no', '') or '',
                    'lot_sqm': getattr(lot, 'lot_sqm', '') or '',
                    'sap_no': getattr(pl, 'sap_no', '') or (getattr(invoice, 'sap_no', '') if invoice else '') or '',
                    'bl_no': self._format_bl(
                        (getattr(bl, 'bl_no', '') if bl else '') or 
                        (getattr(do, 'bl_no', '') if do else '') or ''
                    ),
                    'container_no': getattr(lot, 'container_no', '') or '',
                    'product': getattr(pl, 'product', '') or 'LITHIUM CARBONATE',
                    'product_code': getattr(pl, 'code', '') or '',
                    'net_weight': getattr(lot, 'net_weight_kg', 0) or 0,
                    'gross_weight': getattr(lot, 'gross_weight_kg', 0) or 0,
                    'mxbg_pallet': getattr(lot, 'mxbg_pallet', 10) or 10,
                    'salar_invoice_no': getattr(invoice, 'salar_invoice_no', '') if invoice else '',
                    'ship_date': str(getattr(bl, 'ship_date', '')) if bl and getattr(bl, 'ship_date', None) else (
                        str(getattr(invoice, 'invoice_date', '')) if invoice and getattr(invoice, 'invoice_date', None) else ''
                    ),
                    'arrival_date': _arrival,
                    'free_time': _free_time,
                    'free_time_date': _free_time_date,
                    'warehouse': str(getattr(do, 'warehouse', DEFAULT_WAREHOUSE)) if do else DEFAULT_WAREHOUSE,
                    'vessel': getattr(pl, 'vessel', '') or '',
                }
                
                # invoice_data dict
                inv_dict = None
                if invoice:
                    inv_dict = {
                        'sap_no': getattr(invoice, 'sap_no', '') or '',
                        'salar_invoice_no': getattr(invoice, 'salar_invoice_no', '') or '',
                        'invoice_date': str(getattr(invoice, 'invoice_date', '')) if getattr(invoice, 'invoice_date', None) else '',
                    }
                
                # bl_data dict
                bl_dict = None
                if bl:
                    bl_dict = {
                        'bl_no': self._format_bl(getattr(bl, 'bl_no', '') or ''),
                        'ship_date': str(getattr(bl, 'ship_date', '')) if getattr(bl, 'ship_date', None) else '',
                        'vessel': getattr(bl, 'vessel', '') or '',
                    }
                
                # do_data dict
                do_dict = None
                if do:
                    do_dict = {
                        'bl_no': str(getattr(do, 'bl_no', '')),
                        'arrival_date': str(getattr(do, 'arrival_date', '')),
                        'free_time': str(getattr(do, 'free_time', '')),
                        'warehouse': str(getattr(do, 'warehouse', '')),
                    }
                
                try:
                    result = self.engine.process_inbound(
                        packing_data=packing_dict,
                        invoice_data=inv_dict,
                        bl_data=bl_dict,
                        do_data=do_dict
                    )
                    
                    if result.get('success'):
                        created_lots.append(getattr(lot, "lot_no", ""))
                    else:
                        err_msg = result.get('message', '') or ', '.join(result.get('errors', []))
                        errors.append(f"LOT {getattr(lot, 'lot_no', '')}: {err_msg}")
                        # Excel 행 번호: 헤더 1행 + 데이터는 2부터 (idx 0 → 행 2)
                        failed_rows.append({'row': idx + 2, 'value': err_msg, 'column': 'LOT NO'})
                
                except (ValueError, TypeError, AttributeError) as e:
                    errors.append(f"LOT {getattr(lot, 'lot_no', '')}: {e}")
                    failed_rows.append({'row': idx + 2, 'value': str(e), 'column': 'LOT NO'})
            
            if errors:
                self._log_safe(f"⚠️ 일부 오류: {len(errors)}건")
                for e in errors[:5]:
                    self._log_safe(f"  - {e}")
            
            if skipped_lots:
                self._log_safe(f"⏭ 중복 건너뜀: {len(skipped_lots)}건")
            
            # v3.8.8: 각 LOT는 process_inbound 내부에서 개별 트랜잭션 처리됨
            # 외부 commit/rollback 불필요
            if created_lots:
                self._log_safe(f"✅ 저장 완료: {len(created_lots)}건")
                return True, []
            else:
                self._log_safe(f"❌ 저장된 LOT 없음 (오류 {len(errors)}건, 건너뜀 {len(skipped_lots)}건)")
                return False, failed_rows

        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"DB 저장 실패: {e}", exc_info=True)
            self._log_safe(f"❌ DB 저장 실패: {e}")
            return False, []
    
    # ═══════════════════════════════════════════════════════════
    # Excel 내보내기
    # ═══════════════════════════════════════════════════════════
    
    def _export_to_excel(self) -> None:
        """미리보기 데이터 Excel 내보내기"""
        if not self.preview_data:
            return
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            
            save_path = filedialog.asksaveasfilename(
                parent=self.dialog, title="Excel 내보내기",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialfile=f"입고미리보기_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            if not save_path:
                return
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "입고 미리보기"
            
            headers = [col[1] for col in PREVIEW_COLUMNS]
            hfill = PatternFill(start_color="2c6fbb", end_color="2c6fbb", fill_type="solid")
            hfont = Font(color="FFFFFF", bold=True, size=10)
            border = Border(left=Side(style='thin'), right=Side(style='thin'),
                           top=Side(style='thin'), bottom=Side(style='thin'))
            
            for ci, h in enumerate(headers, 1):
                cell = ws.cell(row=1, column=ci, value=h)
                cell.fill = hfill
                cell.font = hfont
                cell.alignment = Alignment(horizontal='center')
                cell.border = border
            
            for ri, row_data in enumerate(self.preview_data, 2):
                for ci, (col_id, _, _, _) in enumerate(PREVIEW_COLUMNS, 1):
                    cell = ws.cell(row=ri, column=ci, value=row_data.get(col_id, ''))
                    cell.border = border
            
            for ci, (_, h, w, _) in enumerate(PREVIEW_COLUMNS, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = max(w / 7, len(h) + 2)
            
            wb.save(save_path)
            self._log_safe(f"📥 Excel 저장: {save_path}")
        
        except (ValueError, TypeError, AttributeError) as e:
            self._log_safe(f"❌ Excel 오류: {e}")
    
    # ═══════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════
    
    def _show_success_and_close(self, count: int):
        def _close():
            if self.dialog and self.dialog.winfo_exists():
                # v3.8.9: app 참조를 destroy 전에 확보
                _app = self.app if self.app else None
                
                try:
                    from ..utils.custom_messagebox import CustomMessageBox
                    CustomMessageBox.showinfo(self.dialog, "업로드 완료",
                        f"✅ {count}개 LOT 저장 완료")
                except (ImportError, ModuleNotFoundError):
                    CustomMessageBox.info(None, "완료", f"✅ {count}개 LOT 저장 완료")
                
                self.dialog.destroy()
                
                # v3.8.9: 업로드 후 재고리스트 탭 이동 + 자동 새로고침
                # dialog.destroy() 후이므로 app.root.after 사용
                if _app:
                    try:
                        _root = getattr(_app, 'root', None)
                        if _root:
                            if hasattr(_app, 'notebook') and hasattr(_app, 'tab_inventory'):
                                _root.after(200, lambda: _app.notebook.select(_app.tab_inventory))
                            if hasattr(_app, '_refresh_inventory'):
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
