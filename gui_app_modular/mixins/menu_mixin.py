# -*- coding: utf-8 -*-
"""
SQM 재고관리 - 메뉴 설정 Mixin
==============================

v3.0 - ttkbootstrap 기반 커스텀 메뉴바
v2.9.91 - gui_app.py에서 분리

메뉴바 구성, 단축키 설정
"""

import logging
import os
import configparser

from ..utils.ui_constants import CustomMessageBox
logger = logging.getLogger(__name__)


class MenuMixin:
    """
    메뉴 설정 Mixin
    
    SQMInventoryApp 클래스에 mix-in 됩니다.
    v3.0: ttkbootstrap 기반 커스텀 메뉴바 사용
    """
    
    # 메뉴바 스타일: 'custom' (ttkbootstrap) 또는 'native' (tk.Menu)
    MENUBAR_STYLE = 'custom'

    def _is_developer_mode_enabled(self) -> bool:
        """settings.ini [ui] developer_mode 플래그."""
        cfg = configparser.ConfigParser()
        try:
            cfg.read(os.path.join(os.getcwd(), 'settings.ini'), encoding='utf-8')
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
            logger.debug(f"개발자 모드 설정 읽기 실패(무시): {e}")
            return False
        return cfg.getboolean('ui', 'developer_mode', fallback=False)

    def _set_developer_mode_enabled(self, enabled: bool) -> bool:
        """개발자 모드 플래그 저장."""
        cfg = configparser.ConfigParser()
        settings_path = os.path.join(os.getcwd(), 'settings.ini')
        try:
            cfg.read(settings_path, encoding='utf-8')
            if not cfg.has_section('ui'):
                cfg.add_section('ui')
            cfg.set('ui', 'developer_mode', '1' if enabled else '0')
            with open(settings_path, 'w', encoding='utf-8') as f:
                cfg.write(f)
            return True
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"개발자 모드 설정 저장 실패: {e}", exc_info=True)
            return False
    
    def _setup_menu(self) -> None:
        """메뉴 구성"""
        if self.MENUBAR_STYLE == 'custom':
            self._setup_custom_menu()
        else:
            self._setup_native_menu()
    
    def _setup_custom_menu(self) -> None:
        """v3.0: ttkbootstrap 커스텀 메뉴바"""
        try:
            from .custom_menubar import CustomMenuBar
            
            self.custom_menubar = CustomMenuBar(self.root, self)
            self.recent_menu = self.custom_menubar.get_recent_menu()
            
            self._log("✅ 커스텀 메뉴바 적용")
            logger.info("커스텀 메뉴바 생성 완료")
            
        except (ImportError, ModuleNotFoundError) as e:
            logger.error(f"커스텀 메뉴바 생성 실패: {e}, 네이티브 메뉴바 사용")
            self._setup_native_menu()
    
    def _setup_native_menu(self) -> None:
        """기존 네이티브 메뉴바 (fallback)"""
        from ..utils.constants import tk
        from ..utils.constants import (
            HAS_GEMINI, HAS_DB_PROTECTION, HAS_FEATURES, HAS_FEATURES_V2
        )
        
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # =====================================================
        # 파일 메뉴
        # =====================================================
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        
        from ..menu_registry import (
            FILE_MENU_INBOUND_ITEMS,
            FILE_MENU_INBOUND_RETURN_SUB_ITEMS,
            FILE_MENU_OUTBOUND_ITEMS,
            FILE_MENU_EXPORT_ITEMS,
            FILE_MENU_BACKUP_ITEMS,
        )
        
        file_menu.add_command(
            label="📥 PDF 입고  (Ctrl+I)",
            command=self._on_pdf_inbound
        )
        
        # 출고 서브메뉴 — menu_registry 단일 소스 (Picking List 등 누락 방지)
        outbound_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="📤 출고", menu=outbound_menu)
        for entry in FILE_MENU_OUTBOUND_ITEMS:
            if entry is None:
                outbound_menu.add_separator()
                continue
            label, method_name = entry[0], entry[1]
            optional = entry[2] if len(entry) > 2 else False
            if optional and (not hasattr(self, method_name) or not callable(getattr(self, method_name))):
                continue
            cmd = getattr(self, method_name, None)
            if callable(cmd):
                outbound_menu.add_command(label=label, command=cmd)
        
        file_menu.add_separator()
        
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="📂 최근 파일", menu=self.recent_menu)
        self._update_recent_files_menu()
        
        file_menu.add_separator()
        
        # 업로드 메뉴 — menu_registry 기반 (입고 + 출고 동일 목록)
        _font = ('맑은 고딕', 14)
        upload_menu = tk.Menu(file_menu, tearoff=0, font=_font)
        file_menu.add_cascade(label="📥 업로드 메뉴", menu=upload_menu)
        for entry in FILE_MENU_INBOUND_ITEMS:
            if entry is None:
                upload_menu.add_separator()
                continue
            if entry[1] == "_show_return_dialog":
                continue
            label, method_name = entry[0], entry[1]
            cmd = getattr(self, method_name, None)
            if callable(cmd):
                upload_menu.add_command(label="  " + label, command=cmd, font=_font)
        upload_menu.add_separator()
        for entry in FILE_MENU_OUTBOUND_ITEMS:
            if entry is None:
                upload_menu.add_separator()
                continue
            label, method_name = entry[0], entry[1]
            optional = entry[2] if len(entry) > 2 else False
            if optional and (not hasattr(self, method_name) or not callable(getattr(self, method_name))):
                continue
            cmd = getattr(self, method_name, None)
            if callable(cmd):
                upload_menu.add_command(label="  " + label, command=cmd, font=_font)
        upload_menu.add_separator()
        _return_cmd = getattr(self, "_show_return_dialog", None)
        if callable(_return_cmd):
            return_sub = tk.Menu(upload_menu, tearoff=0, font=_font)
            upload_menu.add_cascade(label="  🔄 반품 (재입고)", menu=return_sub, font=_font)
            for sub_label, mode in FILE_MENU_INBOUND_RETURN_SUB_ITEMS:
                return_sub.add_command(label="  " + sub_label, command=lambda md=mode: _return_cmd(md), font=_font)
        else:
            upload_menu.add_command(
                label="  🔄 반품 (재입고)",
                command=lambda: CustomMessageBox.showinfo(self.root, "반품", "반품 기능 필요"),
                font=_font
            )
        
        export_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="💾 내보내기  (Ctrl+E)", menu=export_menu)
        for label, option in FILE_MENU_EXPORT_ITEMS:
            export_menu.add_command(label=label, command=lambda op=option: self._on_export_click(op))
        
        file_menu.add_separator()
        
        backup_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="🔐 백업  (Ctrl+B)", menu=backup_menu)
        for label, method_name in FILE_MENU_BACKUP_ITEMS:
            cmd = getattr(self, method_name, None)
            if callable(cmd):
                backup_menu.add_command(label=label, command=cmd)
        
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.root.quit)

        # =====================================================
        # 보고서 메뉴 (거래 명세서 등)
        # =====================================================
        report_top_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="보고서", menu=report_top_menu)
        report_top_menu.add_command(label="📄 거래 명세서", command=self._generate_invoice_pdf)
        report_top_menu.add_command(label="📦 재고 현황", command=self._generate_inventory_pdf)
        report_top_menu.add_command(label="📈 입출고 내역", command=self._generate_transaction_pdf)
        report_top_menu.add_command(label="🔖 LOT 상세", command=self._generate_lot_detail_pdf)
        
        # =====================================================
        # 도구 메뉴
        # =====================================================
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도구", menu=tools_menu)
        
        # v5.9.0: 컨테이너 구분 → 필터바 초기화 옆으로 이동 (변수만 초기화)
        if not hasattr(self, '_container_suffix_var'):
            self._container_suffix_var = tk.BooleanVar(value=True)
        tools_menu.add_command(label="📋 D/O 후속 연결", command=self._on_do_update)
        tools_menu.add_separator()
        
        pdf_menu = tk.Menu(tools_menu, tearoff=0)
        tools_menu.add_cascade(label="📄 PDF/이미지 변환", menu=pdf_menu)
        pdf_menu.add_command(label="→ Excel", command=self._convert_pdf_to_excel)
        pdf_menu.add_command(label="→ Word", command=self._convert_pdf_to_word)
        pdf_menu.add_separator()
        pdf_menu.add_command(label="📁 일괄 변환", command=self._batch_convert_pdf_excel)
        pdf_menu.add_command(label="🔍 분석", command=self._analyze_pdf)
        tools_menu.add_separator()
        
        report_menu = tk.Menu(tools_menu, tearoff=0)
        tools_menu.add_cascade(label="📋 PDF 보고서", menu=report_menu)
        report_menu.add_command(label="📦 재고 현황", command=self._generate_inventory_pdf)
        report_menu.add_command(label="📈 입출고 내역", command=self._generate_transaction_pdf)
        report_menu.add_command(label="🔖 LOT 상세", command=self._generate_lot_detail_pdf)
        tools_menu.add_separator()
        
        if HAS_GEMINI:
            api_menu = tk.Menu(tools_menu, tearoff=0)
            tools_menu.add_cascade(label="🤖 Gemini", menu=api_menu)
            self._gemini_var = tk.BooleanVar(value=getattr(self, 'use_gemini', False))
            api_menu.add_checkbutton(label="API 사용", variable=self._gemini_var, command=self._toggle_gemini)
            api_menu.add_separator()
            api_menu.add_command(label="💬 AI 채팅", command=self._open_ai_chat)
            api_menu.add_command(label="⚙️ 설정", command=self._show_api_settings)
            api_menu.add_command(label="🔬 테스트", command=self._test_gemini_api)
            tools_menu.add_separator()
        
        if HAS_DB_PROTECTION:
            db_menu = tk.Menu(tools_menu, tearoff=0)
            tools_menu.add_cascade(label="🛡️ DB 보호", menu=db_menu)
            db_menu.add_command(label="🔍 무결성 검증", command=self._verify_db_integrity)
            db_menu.add_command(label="📋 작업 로그", command=self._show_action_log)
            db_menu.add_command(label="💾 로그 내보내기", command=self._export_action_log)
            db_menu.add_separator()
            db_menu.add_command(label="🔄 체크섬 갱신", command=self._update_checksum)
            tools_menu.add_separator()
        
        tools_menu.add_command(label="🔍 DB 검사", command=self._on_integrity_check)
        tools_menu.add_command(label="🔧 DB 최적화", command=self._on_optimize_db)
        tools_menu.add_separator()
        tools_menu.add_command(label="📋 로그 정리", command=self._on_cleanup_logs)
        tools_menu.add_command(label="ℹ️ DB 정보", command=self._show_db_info)
        tools_menu.add_separator()
        if self._is_developer_mode_enabled():
            tools_menu.add_command(label="🗑️ 테스트 DB 초기화 (데이터 삭제)", command=self._show_test_db_reset_popup)
        
        if HAS_FEATURES:
            tools_menu.add_separator()
            adv_menu = tk.Menu(tools_menu, tearoff=0)
            tools_menu.add_cascade(label="✨ 고급", menu=adv_menu)
            adv_menu.add_command(label="🔬 입고 검증", command=self._dry_run_inbound)
            adv_menu.add_command(label="🔬 출고 검증", command=self._dry_run_outbound)
            adv_menu.add_separator()
            adv_menu.add_command(label="🩺 전체 진단", command=self._run_self_test)
            adv_menu.add_command(label="🧪 단위 테스트", command=self._open_test_runner)
        
        # =====================================================
        # 보기 메뉴 — v6.0.9: 7탭 한글 (custom_menubar와 동일 인덱스)
        # =====================================================
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="보기", menu=view_menu)
        view_menu.add_command(label="🔄 새로고침 (F5)", command=self._refresh_inventory)
        view_menu.add_separator()
        view_menu.add_command(label="📦 판매가능", command=lambda: self.notebook.select(0))
        view_menu.add_command(label="📋 판매배정", command=lambda: self.notebook.select(1))
        view_menu.add_command(label="🚛 판매화물 결정", command=lambda: self.notebook.select(2))
        view_menu.add_command(label="✅ 출고", command=lambda: self.notebook.select(3))
        view_menu.add_command(label="📋 총괄 재고 리스트", command=lambda: self.notebook.select(4))
        view_menu.add_command(label="📊 통계", command=lambda: self.notebook.select(5))
        view_menu.add_command(label="📝 로그", command=lambda: self.notebook.select(6))
        view_menu.add_separator()
        view_menu.add_command(label="🎨 테마 선택", command=self._show_theme_selector)
        
        # =====================================================
        # v2.7 메뉴
        # =====================================================
        if HAS_FEATURES_V2:
            v2_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="🚀 v2.7", menu=v2_menu)
            v2_menu.add_command(label="⚠️ 재고 경고", command=self._show_stock_alerts)
            v2_menu.add_command(label="📦 배치 출고", command=self._show_batch_outbound)
            v2_menu.add_command(label="📈 출고 예측", command=self._show_outbound_prediction)
            v2_menu.add_separator()
            v2_menu.add_command(label="🌙 다크 모드", command=self._toggle_dark_mode)
            v2_menu.add_separator()
            v2_menu.add_command(label="💾 필터 저장", command=self._save_filter_preset)
            v2_menu.add_command(label="📂 필터 불러오기", command=self._load_filter_preset)
            v2_menu.add_separator()
            v2_menu.add_command(label="📊 일일 리포트", command=self._generate_daily_report)
        
        # =====================================================
        # 도움말 메뉴
        # =====================================================
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도움말", menu=help_menu)
        help_menu.add_command(label="⌨️ 단축키", command=self._show_shortcuts)
        help_menu.add_command(label="📖 설명서", command=self._show_manual)
        help_menu.add_separator()
        help_menu.add_command(label="🔬 API 테스트", command=self._test_gemini_api_connection)
        help_menu.add_separator()
        help_menu.add_command(label="ℹ️ 정보", command=self._show_about)
    
    def _setup_keyboard_shortcuts(self) -> None:
        """단축키 설정"""
        shortcuts = [
            ('<Control-i>', self._on_pdf_inbound),
            ('<Control-I>', self._on_pdf_inbound),
            ('<Control-o>', self._on_allocation_input_unified),
            ('<Control-O>', self._on_allocation_input_unified),
            ('<Control-e>', lambda: self._on_export_click(6)),
            ('<Control-E>', lambda: self._on_export_click(6)),
            ('<Control-b>', self._on_backup_click),
            ('<Control-B>', self._on_backup_click),
            ('<Control-f>', self._focus_search),
            ('<Control-F>', self._focus_search),
            ('<F5>', self._refresh_inventory),
        ]
        
        for key, command in shortcuts:
            try:
                self.root.bind(key, lambda e, cmd=command: cmd())
            except (AttributeError, RuntimeError) as ex:
                logger.warning(f"단축키 바인딩 실패 {key}: {ex}")
    
    def _show_shortcuts(self) -> None:
        """단축키 안내"""

        
        shortcuts_text = """
📌 SQM 재고관리 단축키

━━━━━━━━━━━━━━━━━━━━━━━━━━
Ctrl+I    입고 파일 업로드
Ctrl+O    간편 출고
Ctrl+E    Excel 내보내기
Ctrl+B    백업 생성
Ctrl+F    검색창 포커스
F5        새로고침
━━━━━━━━━━━━━━━━━━━━━━━━━━

더블클릭    LOT 상세 / 선택
드래그      파일 업로드
        """
        CustomMessageBox.showinfo(self.root, "⌨️ 단축키", shortcuts_text)
    
    def _show_about(self) -> None:
        """프로그램 정보"""
        from ..utils.constants import __version__, APP_NAME
        
        about_text = f"""
{APP_NAME}
버전: {__version__}

━━━━━━━━━━━━━━━━━━━━━━━━━━
GY Logistics 재고 관리 시스템

• 입고/출고 자동화
• PDF 문서 파싱
• Excel 내보내기
• 실시간 재고 추적
━━━━━━━━━━━━━━━━━━━━━━━━━━

개발: Ruby
        """
        CustomMessageBox.showinfo(self.root, "ℹ️ 프로그램 정보", about_text)
    
    def _show_manual(self) -> None:
        """사용 설명서 표시"""
        import os
        import subprocess
        import platform
        
        manual_path = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'USER_MANUAL_KR.md')
        
        if os.path.exists(manual_path):
            if platform.system() == 'Windows':
                os.startfile(manual_path)
            elif platform.system() == 'Darwin':
                subprocess.run(['open', manual_path])
            else:
                subprocess.run(['xdg-open', manual_path])
        else:

            CustomMessageBox.showinfo(self.root, "설명서", "사용 설명서를 찾을 수 없습니다.\ndocs/USER_MANUAL_KR.md")
