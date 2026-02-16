# -*- coding: utf-8 -*-
"""
SQM Inventory - Settings Dialogs
================================

v3.6.0 - UI 통일성 적용
- 다이얼로그 크기 표준화 (DialogSize)
- 간격 표준화 (Spacing)
- 폰트 스케일링 (FontScale)
"""

import os
import logging

from ..utils.ui_constants import CustomMessageBox, ThemeColors
logger = logging.getLogger(__name__)


class SettingsDialogMixin:
    """
    Settings dialogs mixin
    
    Mixed into SQMInventoryApp class
    """
    
    def _show_api_settings(self) -> None:
        """v3.9.7: API 키 보안 설정 다이얼로그"""
        from ..utils.constants import tk, ttk, X, LEFT, RIGHT, W, E, BOTH, YES
        from ..utils.ui_constants import ThemeColors
        
        try:
            from config import GEMINI_API_KEY, GEMINI_MODEL, API_KEY_SOURCE, save_api_key_secure, save_gemini_model
        except ImportError:
            CustomMessageBox.showerror(self.root, "Error", "Config module not found")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("🔐 API 키 보안 설정")
        dialog.geometry("520x420")
        dialog.resizable(True, True)
        dialog.minsize(400, 350)
        dialog.transient(self.root)
        dialog.grab_set()
        
        _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        _bg = '#1e1e1e' if _is_dark else ThemeColors.get('bg_card')
        _fg = '#e0e0e0' if _is_dark else ThemeColors.get('text_primary')
        dialog.configure(bg=_bg)
        
        # 헤더
        header = tk.Frame(dialog, bg=ThemeColors.get('info'), pady=8)
        header.pack(fill=X)
        tk.Label(header, text="🔐 Gemini API 키 설정", bg=ThemeColors.get('info'), fg='white',
                 font=('맑은 고딕', 13, 'bold')).pack()
        
        body = tk.Frame(dialog, bg=_bg, padx=20, pady=15)
        body.pack(fill=BOTH, expand=YES)
        
        # 현재 상태
        masked = (GEMINI_API_KEY[:10] + "..." + GEMINI_API_KEY[-4:]) if GEMINI_API_KEY and len(GEMINI_API_KEY) > 14 else "미설정"
        source_map = {'ENV': '🟢 환경변수 (가장 안전)', 'KEYRING': '🟢 OS 자격증명', 'INI': '🟡 settings.ini (평문)', 'NONE': '🔴 미설정'}
        source_text = source_map.get(API_KEY_SOURCE, '🔴 미설정')
        
        info_frame = tk.Frame(body, bg=_bg)
        info_frame.pack(fill=X, pady=(0, 10))
        
        tk.Label(info_frame, text="현재 API 키:", bg=_bg, fg=_fg, font=('맑은 고딕', 10)).pack(anchor=W)
        tk.Label(info_frame, text=f"  {masked}", bg=_bg, fg=ThemeColors.get('statusbar_progress'), font=('맑은 고딕', 10, 'bold')).pack(anchor=W)
        tk.Label(info_frame, text=f"  저장 위치: {source_text}", bg=_bg, fg=_fg, font=('맑은 고딕', 9)).pack(anchor=W)
        tk.Label(info_frame, text=f"  모델: {GEMINI_MODEL}", bg=_bg, fg='gray', font=('맑은 고딕', 9)).pack(anchor=W)
        
        ttk.Separator(body).pack(fill=X, pady=10)
        
        # 모델 변경 (다음 실행부터 적용)
        tk.Label(body, text="Gemini 모델 (변경 시 저장 후 다음 실행부터 적용):", bg=_bg, fg=_fg, font=('맑은 고딕', 10)).pack(anchor=W)
        model_var = tk.StringVar(value=GEMINI_MODEL or "gemini-2.5-flash")
        model_entry = ttk.Entry(body, textvariable=model_var, width=55)
        model_entry.pack(fill=X, pady=5)
        
        ttk.Separator(body).pack(fill=X, pady=10)
        
        # 새 API 키 입력
        tk.Label(body, text="새 API 키 입력:", bg=_bg, fg=_fg, font=('맑은 고딕', 10)).pack(anchor=W)
        key_var = tk.StringVar()
        key_entry = ttk.Entry(body, textvariable=key_var, width=55, show='●')
        key_entry.pack(fill=X, pady=5)
        
        # 보기/숨김 토글
        show_var = tk.BooleanVar(value=False)
        def toggle_show():
            key_entry.config(show='' if show_var.get() else '●')
        ttk.Checkbutton(body, text="키 표시", variable=show_var, command=toggle_show).pack(anchor=W)
        
        # 저장 방식 선택
        tk.Label(body, text="저장 방식:", bg=_bg, fg=_fg, font=('맑은 고딕', 10)).pack(anchor=W, pady=(10, 0))
        method_var = tk.StringVar(value='auto')
        methods_frame = tk.Frame(body, bg=_bg)
        methods_frame.pack(fill=X, pady=5)
        ttk.Radiobutton(methods_frame, text="🔒 자동 (keyring 우선)", variable=method_var, value='auto').pack(anchor=W)
        ttk.Radiobutton(methods_frame, text="📄 settings.ini", variable=method_var, value='ini').pack(anchor=W)
        
        result_label = tk.Label(body, text="", bg=_bg, fg=_fg, font=('맑은 고딕', 9))
        result_label.pack(anchor=W, pady=5)
        
        def save_key():
            key = key_var.get().strip()
            model_str = model_var.get().strip()
            if key:
                if not key.startswith('AIza'):
                    result_label.config(text="⚠️ Google API 키 형식이 아닙니다 (AIza...)", fg='#e67e22')
                    return
                method = save_api_key_secure(key)
                if method == 'KEYRING':
                    result_label.config(text="✅ API 키·모델 저장됨 (다음 실행부터 모델 적용)", fg=ThemeColors.get('badge_db'))
                elif method == 'INI':
                    result_label.config(text="✅ API 키·모델 저장됨 (다음 실행부터 모델 적용)", fg='#e67e22')
                else:
                    result_label.config(text="❌ API 키 저장 실패", fg=ThemeColors.get('statusbar_icon_err'))
            if model_str:
                if save_gemini_model(model_str):
                    if not key:
                        result_label.config(text="✅ 모델 저장됨 (다음 실행부터 적용)", fg=ThemeColors.get('badge_db'))
                elif not key:
                    result_label.config(text="❌ 모델 저장 실패", fg=ThemeColors.get('statusbar_icon_err'))
            if not key and not model_str:
                result_label.config(text="⚠️ API 키 또는 모델을 입력하세요", fg=ThemeColors.get('statusbar_icon_err'))
        
        btn_frame = tk.Frame(body, bg=_bg)
        btn_frame.pack(fill=X, pady=10)
        ttk.Button(btn_frame, text="💾 저장", command=save_key, width=12).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="닫기", command=dialog.destroy, width=12).pack(side=RIGHT, padx=5)
        
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def _show_gemini_api_required(self) -> None:
        """Show Gemini API required warning"""

        
        if getattr(self, 'gemini_required_warning_shown', False):
            return
        self.gemini_required_warning_shown = True
        
        guide_msg = """Gemini API Key Required!

For accurate data extraction from PDF documents,
Gemini API is required.

Without API key, these features are limited:
  X SAP NO extraction
  X Salar Invoice No extraction  
  X Ship date/arrival date extraction
  X LOT SQM extraction
  X Product name extraction

========================================

Setup Instructions:

1. Open settings.ini file
2. Enter API_KEY in [GEMINI] section

========================================

Sample:

[GEMINI]
API_KEY = AIzaSyA1B2C3D4E5F6G7H8I9J0...

========================================

Get free API key:
https://aistudio.google.com/apikey

========================================

Open settings.ini now?
"""
        if CustomMessageBox.askyesno(self.root, "Gemini API Required", guide_msg):
            try:
                from config import SETTINGS_FILE
                os.startfile(SETTINGS_FILE)
            except (ImportError, ModuleNotFoundError) as e:
                self._log(f"WARNING Failed to open settings.ini: {e}")
        
        self._set_status("WARNING Gemini API key required - Limited functionality")
    
    def _show_gemini_api_guide(self) -> None:
        """Compatibility redirect to _show_gemini_api_required"""
        self._show_gemini_api_required()
    
    def _toggle_gemini(self) -> None:
        """Toggle Gemini API usage (v3.6.9: Client 재초기화 연동)"""

        
        if hasattr(self, '_gemini_var'):
            self.use_gemini = self._gemini_var.get()
            
            if self.use_gemini:
                # v3.6.9: Client 재초기화 (API 키 변경 반영)
                self._reinit_gemini_clients()
                self._log("Gemini API enabled")
                CustomMessageBox.showinfo(self.root, "Gemini API", "Gemini API is now enabled")
            else:
                self._log("Gemini API disabled")
                CustomMessageBox.showinfo(self.root, "Gemini API", "Gemini API is now disabled")
    
    def _reinit_gemini_clients(self) -> None:
        """v3.6.9: 모든 Gemini Client를 재초기화 (API 키 변경 시)
        
        메인 UI는 변경하지 않고, 백엔드의 Client 인스턴스만 리셋합니다.
        다음 API 호출 시 새로운 키로 Client가 자동 생성됩니다.
        """
        try:
            # 1. 싱글턴 Client 리셋
            try:
                from features.ai.gemini_utils import reset_gemini_client
                reset_gemini_client()
                logger.info("Gemini 싱글턴 Client 리셋 완료")
            except ImportError as _e:
                logger.debug(f"settings_dialog: {_e}")
            
            # 2. document_parser의 gemini 리셋
            if hasattr(self, 'document_parser') and self.document_parser:
                if hasattr(self.document_parser, 'gemini') and self.document_parser.gemini:
                    if hasattr(self.document_parser.gemini, '_init_client'):
                        self.document_parser.gemini._init_client()
                        logger.info("DocumentParser Gemini 리셋 완료")
            
            # 3. AI chat engine 리셋 (있는 경우)
            if hasattr(self, 'chat_engine') and self.chat_engine:
                if hasattr(self.chat_engine, '_init_gemini'):
                    self.chat_engine._init_gemini()
                    logger.info("ChatEngine Gemini 리셋 완료")
            
            self._log("OK Gemini API Client 재초기화 완료")
            
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Gemini 재초기화 실패: {e}")
            self._log(f"WARNING Gemini 재초기화 실패: {e}")
    
    def _test_gemini_api(self) -> None:
        """Test Gemini API connection (v3.6.9: 백그라운드 스레드)"""
        
        self._log("Testing Gemini API connection...")
        self._set_status("Testing API...")
        
        import threading
        
        def _do_test():
            try:
                from config import GEMINI_API_KEY, GEMINI_MODEL
                
                if not GEMINI_API_KEY or GEMINI_API_KEY.startswith('your-'):
                    self.root.after(0, lambda: CustomMessageBox.showerror(self.root, "API Test",
                        "API 키가 설정되지 않았습니다.\n\n"
                        "settings.ini 또는 환경변수 GEMINI_API_KEY를 확인하세요."))
                    self.root.after(0, lambda: self._set_status("Ready"))
                    return
                
                import time
                start = time.time()
                
                from google import genai
                client = genai.Client(api_key=GEMINI_API_KEY)
                
                model_name = GEMINI_MODEL or "gemini-2.5-flash"
                response = client.models.generate_content(
                    model=model_name,
                    contents="Hello, respond with just 'OK'"
                )
                
                elapsed_ms = int((time.time() - start) * 1000)
                
                if response.text:
                    self.root.after(0, lambda: self._log(
                        f"OK Gemini API 연결 성공! (모델: {model_name}, {elapsed_ms}ms)"))
                    self.root.after(0, lambda: CustomMessageBox.showinfo(self.root, "API 테스트",
                        f"✅ Gemini API 연결 성공!\n\n"
                        f"모델: {model_name}\n"
                        f"응답 시간: {elapsed_ms}ms\n"
                        f"응답: {response.text[:50]}"))
                else:
                    self.root.after(0, lambda: CustomMessageBox.showerror(self.root, "API 테스트",
                        "❌ API 응답이 없습니다."))
                        
            except ImportError as e:
                self.root.after(0, lambda: CustomMessageBox.showerror(self.root, "API 테스트",
                    f"google-genai 패키지가 필요합니다.\n\npip install google-genai"))
            except (RuntimeError, ValueError) as e:
                err_msg = str(e)
                err_lower = err_msg.lower()
                
                # v3.6.9: 에러별 구체적 안내
                if '401' in err_lower or 'unauthorized' in err_lower or 'invalid api key' in err_lower:
                    user_msg = (
                        "❌ API 키가 유효하지 않습니다.\n\n"
                        "확인 사항:\n"
                        "• settings.ini의 api_key 값\n"
                        "• 환경변수 GEMINI_API_KEY\n\n"
                        "새 키 발급:\n"
                        "https://aistudio.google.com/apikey"
                    )
                elif '429' in err_lower or 'rate limit' in err_lower or 'quota' in err_lower:
                    user_msg = (
                        "⚠️ API 호출 한도를 초과했습니다.\n\n"
                        "• 잠시 후 다시 시도해주세요\n"
                        "• Google AI Studio에서 할당량 확인\n"
                        "• 무료 플랜: 분당 15회 제한"
                    )
                elif '503' in err_lower or 'unavailable' in err_lower:
                    user_msg = (
                        "⚠️ Gemini API 서비스가 일시 중단 중입니다.\n\n"
                        "• Google 서버 상태를 확인하세요\n"
                        "• 잠시 후 다시 시도해주세요"
                    )
                elif '404' in err_lower or 'not found' in err_lower:
                    user_msg = (
                        f"❌ 모델을 찾을 수 없습니다.\n\n"
                        f"설정된 모델: {model_name}\n\n"
                        f"settings.ini에서 model 값을 확인하세요.\n"
                        f"권장: gemini-2.5-flash"
                    )
                elif 'timeout' in err_lower:
                    user_msg = (
                        "⏱️ API 응답 시간이 초과되었습니다.\n\n"
                        "• 네트워크 연결을 확인하세요\n"
                        "• VPN 사용 시 끄고 재시도"
                    )
                else:
                    user_msg = f"API 테스트 실패:\n{err_msg}"
                
                self.root.after(0, lambda: self._log(f"X API 테스트 실패: {err_msg}"))
                self.root.after(0, lambda msg=user_msg: CustomMessageBox.showerror(
                    self.root, "API 테스트", msg))
            finally:
                self.root.after(0, lambda: self._set_status("Ready"))
        
        thread = threading.Thread(target=_do_test, daemon=True)
        thread.start()
    
    def _test_gemini_api_connection(self) -> None:
        """Test Gemini API connection (background)"""
        if not hasattr(self, 'document_parser') or not self.document_parser:
            self._log("WARNING Gemini API: Parser not initialized")
            return
        
        self._log("Checking Gemini API connection...")
        
        def test_connection():
            """Background API test"""
            try:
                if hasattr(self.document_parser, 'gemini') and self.document_parser.gemini:
                    result = self.document_parser.gemini.is_available()
                    return result
                return False
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"API test error: {e}")
                return False
        
        def on_complete(result):
            """Test complete callback"""
            if result:
                self._log("OK Gemini API connected")
            else:
                self._log("WARNING Gemini API not available")
        
        # Run in background
        if hasattr(self, '_run_background'):
            self._run_background(test_connection, on_complete)
        else:
            result = test_connection()
            on_complete(result)
    
    def _open_ai_chat(self) -> None:
        """v4.1.2: AI 재고 질의 채팅 — API 키 없으면 설정 안내"""

        from ..utils.constants import HAS_GEMINI
        
        if not HAS_GEMINI:
            CustomMessageBox.showinfo(self.root, "🤖 AI 어시스턴트",
                "Gemini API 키가 설정되지 않았습니다.\n\n"
                "설정 방법:\n"
                "1. 🔧 도구 → 🤖 AI 어시스턴트 → ⚙️ API 설정\n"
                "2. Google AI Studio에서 API 키 발급\n"
                "   (https://aistudio.google.com)\n"
                "3. API 키 입력 후 저장\n"
                "4. 프로그램 재시작")
            return
        
        try:
            from features.ai.gemini_chat_gui import GeminiChatWindow
            
            db_path = getattr(self, 'db_path', None)
            if not db_path and hasattr(self, 'engine') and hasattr(self.engine, 'db'):
                db_path = self.engine.db.db_path
            
            chat_window = GeminiChatWindow(parent=self.root, db_path=db_path)
            self._log("AI 채팅 창 열림")
            
        except ImportError as e:
            self._log(f"❌ AI 채팅 모듈 로드 실패: {e}")
            CustomMessageBox.showerror(self.root, "오류",
                f"AI 채팅 모듈을 불러올 수 없습니다.\n\n{e}")
        except (RuntimeError, ValueError, TypeError, OSError) as e:
            self._log(f"❌ AI 채팅 창 오류: {e}")
            CustomMessageBox.showerror(self.root, "오류", f"AI 채팅 창 오류:\n{e}")
    
    def _on_container_suffix_toggle(self) -> None:
        """Toggle container suffix display (-1, -2, etc)"""
        if hasattr(self, '_container_suffix_var'):
            show_suffix = self._container_suffix_var.get()
            self._log(f"Container suffix display: {'ON' if show_suffix else 'OFF'}")
            self._refresh_inventory()
            self._refresh_tonbag()
    
    def _format_container_no(self, container_no: str) -> str:
        """Format container number based on display setting"""
        if not container_no:
            return ''
        
        # Check if suffix should be hidden
        if hasattr(self, '_container_suffix_var') and not self._container_suffix_var.get():
            # Remove -1, -2 suffix
            if '-' in container_no:
                parts = container_no.rsplit('-', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    return parts[0]
        
        return container_no
