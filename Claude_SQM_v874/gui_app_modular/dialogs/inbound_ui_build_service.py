"""
입고 다이얼로그 UI 빌드 서비스 (STEP 1-7)
- UI 빌드 관련 메서드 분리
"""
import tkinter as tk
from tkinter import ttk
from .inbound_template_service import InboundTemplateService
from .inbound_parse_service import InboundParseService
from .inbound_progress_helper import InboundProgressHelper
from .inbound_date_dialog import InboundDateDialogMixin

class InboundUIBuildService(
    InboundTemplateService,
    InboundParseService,
    InboundProgressHelper,
    InboundDateDialogMixin,
):
    """
    입고 다이얼로그 UI 빌드 서비스
    - UI 빌드 관련 메서드 제공
    """
    # ── UI 빌드 메서드 (STEP 1-7) ─────────────────────────────
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

    # ── _create_dialog 헬퍼 ─────────────────────────────────
    def _cd_setup_window(self) -> ttk.Frame:
        """다이얼로그 윈도우 생성 + 크기/모달 설정. main Frame 반환."""
        from gui_app_modular.utils.ui_constants import center_dialog, apply_modal_window_options
        from gui_app_modular.utils.ui_constants import DialogSize, is_dark, ThemeColors
        import logging
        logger = logging.getLogger("inbound_ui_build_service")
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
        main.pack(fill=tk.BOTH, expand=tk.YES)
        return main

    def _cd_build_step_indicator(self, main: ttk.Frame):
        from gui_app_modular.utils.ui_constants import is_dark, ThemeColors
        _is_dark = is_dark()
        _bg      = ThemeColors.get('bg_secondary', _is_dark)
        _accent  = ThemeColors.get('accent',       _is_dark)
        _muted   = ThemeColors.get('text_muted',   _is_dark)
        _border  = ThemeColors.get('border',       _is_dark)
        _text    = ThemeColors.get('text_primary',  _is_dark)

        step_fr = tk.Frame(main, bg=_bg, pady=6)
        step_fr.pack(fill=tk.X, pady=(0, 6))

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
            ).pack(side=tk.LEFT, padx=(0, 4))
            txt_fr = tk.Frame(cell, bg=_bg)
            txt_fr.pack(side=tk.LEFT)
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
        self._current_step = 0

        tk.Frame(main, bg=_border, height=1).pack(fill=tk.X, pady=(0, 6))

    def _create_dialog(self) -> None:
        """원스톱 입고 팝업 생성"""
        main = self._cd_setup_window()
        self._cd_build_step_indicator(main)
        self._cd_build_doc_file_section(main)
        self._cd_build_carrier_and_progress(main)
        self._cd_build_preview_table(main)
        self._build_inbound_action_buttons(main, is_dark())

    def _cd_build_doc_file_section(self, main: ttk.Frame):
        ... # (기존 구현 전체 복사)

    def _cd_build_parse_action_buttons(self, file_frame: ttk.Frame):
        ... # (기존 구현 전체 복사)

    def _cd_build_carrier_and_progress(self, main: ttk.Frame):
        ... # (기존 구현 전체 복사)

    def _cd_build_preview_table(self, main: ttk.Frame):
        ... # (기존 구현 전체 복사)

    def _build_inbound_action_buttons(self, main, _tree_dark: bool) -> None:
        ... # (기존 구현 전체 복사)
