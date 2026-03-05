# -*- coding: utf-8 -*-
"""
SQM 재고관리 - 메뉴 설정 Mixin
==============================

v3.0 - ttkbootstrap 기반 커스텀 메뉴바
v2.9.91 - gui_app.py에서 분리

메뉴바 구성, 단축키 설정
"""

import logging

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
        """v5.9.8: 네이티브 메뉴바 (fallback) — 7개 메뉴 재구성"""
        from ..utils.constants import tk
        from ..utils.constants import (
            HAS_GEMINI, HAS_DB_PROTECTION, HAS_FEATURES, HAS_FEATURES_V2
        )
        
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # =====================================================
        # 1. 📁 파일
        # =====================================================
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        
        export_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="💾 내보내기  (Ctrl+E)", menu=export_menu)
        export_menu.add_command(label="📋 통관요청 양식", command=lambda: self._on_export_click(1))
        export_menu.add_command(label="📊 루비리 양식", command=lambda: self._on_export_click(3))
        export_menu.add_command(label="📦 톤백 현황", command=lambda: self._on_export_click(4))
        export_menu.add_separator()
        export_menu.add_command(label="📑 통합 현황 ★추천", command=lambda: self._on_export_click(6))
        
        file_menu.add_separator()
        
        backup_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="🔐 백업  (Ctrl+B)", menu=backup_menu)
        backup_menu.add_command(label="💾 백업 생성", command=self._on_backup_click)
        backup_menu.add_command(label="🔄 복원", command=self._on_restore_click)
        backup_menu.add_command(label="📋 백업 목록", command=self._show_backup_list)
        
        file_menu.add_separator()
        
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="📂 최근 파일", menu=self.recent_menu)
        self._update_recent_files_menu()
        
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.root.quit)
        
        # =====================================================
        # 2. 📥 입고
        # =====================================================
        inbound_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="입고", menu=inbound_menu)
        
        inbound_menu.add_command(label="📄 PDF 입고 (원스톱)  Ctrl+I", command=self._on_pdf_inbound)
        inbound_menu.add_command(label="📊 Excel 입고", command=self._bulk_import_inventory_simple)
        inbound_menu.add_separator()
        inbound_menu.add_command(label="📋 D/O 후속 연결", command=self._on_do_update)
        inbound_menu.add_separator()
        inbound_menu.add_command(
            label="🔄 반품 (재입고)",
            command=lambda: self._show_return_dialog() if hasattr(self, '_show_return_dialog')
                    else CustomMessageBox.showinfo(self.root, "반품", "반품 기능 필요")
        )
        
        # =====================================================
        # 3. 📤 출고
        # =====================================================
        outbound_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="출고", menu=outbound_menu)
        
        outbound_menu.add_command(label="📋 간편 출고 (LOT 입력)  Ctrl+O", command=self._on_simple_outbound)
        outbound_menu.add_command(label="📄 배정표 출고 (Excel)", command=self._on_outbound_click)
        outbound_menu.add_separator()
        outbound_menu.add_command(label="📋 Allocation 출고 예약", command=self._on_allocation_dialog)
        
        # =====================================================
        # 4. 📦 재고
        # =====================================================
        inv_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="재고", menu=inv_menu)
        
        inv_menu.add_command(label="🔄 새로고침 (F5)", command=self._refresh_inventory)
        inv_menu.add_separator()
        inv_menu.add_command(label="🏠 홈", command=lambda: self.notebook.select(0))
        inv_menu.add_command(label="📦 재고", command=lambda: self.notebook.select(1))
        inv_menu.add_command(label="🎒 톤백", command=lambda: self.notebook.select(2))
        inv_menu.add_command(label="📊 분석 (피봇)", command=lambda: self.notebook.select(3))
        inv_menu.add_command(label="📝 로그", command=lambda: self.notebook.select(4))
        inv_menu.add_separator()
        inv_menu.add_command(label="🎨 테마 선택", command=self._show_theme_selector)
        
        # =====================================================
        # 5. 📊 보고서
        # =====================================================
        report_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="보고서", menu=report_menu)
        
        report_menu.add_command(label="📦 재고 현황", command=self._generate_inventory_pdf)
        report_menu.add_command(label="📈 입출고 내역", command=self._generate_transaction_pdf)
        report_menu.add_command(label="📝 거래 명세서", command=self._generate_invoice_pdf)
        report_menu.add_command(label="🔖 LOT 상세", command=self._generate_lot_detail_pdf)
        
        # =====================================================
        # 6. ⚙️ 설정/도구
        # =====================================================
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="설정/도구", menu=settings_menu)
        
        if not hasattr(self, '_container_suffix_var'):
            self._container_suffix_var = tk.BooleanVar(value=True)
        
        pdf_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label="📄 PDF/이미지 변환", menu=pdf_menu)
        pdf_menu.add_command(label="→ Excel", command=self._convert_pdf_to_excel)
        pdf_menu.add_command(label="→ Word", command=self._convert_pdf_to_word)
        pdf_menu.add_separator()
        pdf_menu.add_command(label="📁 일괄 변환", command=self._batch_convert_pdf_excel)
        pdf_menu.add_command(label="🔍 분석", command=self._analyze_pdf)
        settings_menu.add_separator()
        
        if HAS_GEMINI:
            api_menu = tk.Menu(settings_menu, tearoff=0)
            settings_menu.add_cascade(label="🤖 Gemini", menu=api_menu)
            self._gemini_var = tk.BooleanVar(value=getattr(self, 'use_gemini', False))
            api_menu.add_checkbutton(label="API 사용", variable=self._gemini_var, command=self._toggle_gemini)
            api_menu.add_separator()
            api_menu.add_command(label="💬 AI 채팅", command=self._open_ai_chat)
            api_menu.add_command(label="⚙️ 설정", command=self._show_api_settings)
            api_menu.add_command(label="🔬 테스트", command=self._test_gemini_api)
            settings_menu.add_separator()
        
        if HAS_DB_PROTECTION:
            db_menu = tk.Menu(settings_menu, tearoff=0)
            settings_menu.add_cascade(label="🛡️ DB 보호", menu=db_menu)
            db_menu.add_command(label="🔍 무결성 검증", command=self._verify_db_integrity)
            db_menu.add_command(label="📋 작업 로그", command=self._show_action_log)
            db_menu.add_command(label="💾 로그 내보내기", command=self._export_action_log)
            db_menu.add_separator()
            db_menu.add_command(label="🔄 체크섬 갱신", command=self._update_checksum)
            settings_menu.add_separator()
        
        settings_menu.add_command(label="🔍 DB 검사", command=self._on_integrity_check)
        settings_menu.add_command(label="🔧 DB 최적화", command=self._on_optimize_db)
        settings_menu.add_separator()
        settings_menu.add_command(label="📋 로그 정리", command=self._on_cleanup_logs)
        settings_menu.add_command(label="ℹ️ DB 정보", command=self._show_db_info)
        settings_menu.add_separator()
        settings_menu.add_command(label="🗑️ 테스트 DB 초기화 (데이터 삭제)", command=self._show_test_db_reset_popup)
        
        if HAS_FEATURES:
            settings_menu.add_separator()
            adv_menu = tk.Menu(settings_menu, tearoff=0)
            settings_menu.add_cascade(label="✨ 고급", menu=adv_menu)
            adv_menu.add_command(label="🔬 입고 검증", command=self._dry_run_inbound)
            adv_menu.add_command(label="🔬 출고 검증", command=self._dry_run_outbound)
            adv_menu.add_separator()
            adv_menu.add_command(label="🩺 전체 진단", command=self._run_self_test)
            adv_menu.add_command(label="🧪 단위 테스트", command=self._open_test_runner)
        
        # =====================================================
        # 7. ❓ 도움말
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
            ('<Control-o>', self._on_simple_outbound),
            ('<Control-O>', self._on_simple_outbound),
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
