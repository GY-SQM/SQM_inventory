# -*- coding: utf-8 -*-
"""
SQM Inventory - Theme Mixin
===========================

v3.6.0 - UI 통일성 적용
- 다이얼로그 크기 표준화
- 간격 표준화
- 중앙 배치
"""

import json
import logging
from ..utils.ui_constants import CustomMessageBox, ThemeColors
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class ThemeMixin:
    """
    Theme management mixin
    
    Mixed into SQMInventoryApp class
    """
    
    # Available themes
    LIGHT_THEMES = ['cosmo', 'flatly', 'litera', 'minty', 'lumen', 'sandstone', 'yeti', 'pulse', 'united', 'morph', 'journal', 'simplex', 'cerculean']
    DARK_THEMES = ['darkly', 'cyborg', 'superhero', 'solar', 'vapor']
    
    def _setup_theme(self, theme_name: Optional[str] = None) -> None:
        """Setup application theme"""
        from ..utils.constants import HAS_TTKBOOTSTRAP
        
        if not HAS_TTKBOOTSTRAP:
            self._log("ttkbootstrap not available, using default theme")
            return
        
        # Load saved preference or use provided/default
        if theme_name is None:
            theme_name = self._load_theme_preference()
        
        self.current_theme = theme_name
        
        try:
            pass
            
            # Apply theme
            if hasattr(self.root, 'style'):
                self.root.style.theme_use(theme_name)
            
            # v3.6.2: 가독성 스타일 재적용
            try:
                from ..utils.ui_constants import ReadableStyle
                ReadableStyle.apply(self.root, theme_name)
            except (ImportError, ModuleNotFoundError) as e:
                logger.debug(f"{type(e).__name__}: {e}")
            
            self._log(f"Theme applied: {theme_name}")
            
        except (ImportError, ModuleNotFoundError) as e:
            logger.error(f"Theme setup error: {e}")
    
    def _load_theme_preference(self) -> str:
        """Load theme preference from file"""
        try:
            pref_file = Path(__file__).parent.parent.parent / "theme_preference.json"
            
            if pref_file.exists():
                with open(pref_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('theme', 'flatly')
        except (OSError, IOError, PermissionError) as e:
            logger.error(f"Load theme preference error: {e}")
        
        return 'flatly'  # v3.0: 고급스러운 기본 테마
    
    def _save_theme_preference(self, theme_name: str) -> None:
        """Save theme preference to file"""
        try:
            pref_file = Path(__file__).parent.parent.parent / "theme_preference.json"
            
            with open(pref_file, 'w', encoding='utf-8') as f:
                json.dump({'theme': theme_name}, f)
            
        except (OSError, IOError, PermissionError) as e:
            logger.error(f"Save theme preference error: {e}")
    
    def _change_theme(self, theme_name: str) -> None:
        """Change application theme — 근본 해결: 전역 스타일·메뉴바·트리 일괄 갱신"""
        from ..utils.constants import HAS_TTKBOOTSTRAP
        
        if not HAS_TTKBOOTSTRAP:
            CustomMessageBox.showinfo(self.root, "Info", "Theme change requires ttkbootstrap")
            return
        
        try:
            if hasattr(self.root, 'style'):
                self.root.style.theme_use(theme_name)
            
            self.current_theme = theme_name
            self._save_theme_preference(theme_name)
            
            # 1) 전역 가독성 스타일 재적용 (Treeview/Notebook 등 글씨·배경 동기화)
            try:
                from ..utils.ui_constants import ReadableStyle
                ReadableStyle.apply(self.root, theme_name)
            except (ImportError, Exception) as e:
                logger.debug(f"ReadableStyle 재적용 무시: {e}")
            
            # 2) 트리뷰 태그·그리드 스타일 + 메뉴바 색상 갱신
            self._update_theme_colors()
            
            # 3) 메뉴바가 테마 색상 캐시를 쓰면 재적용 (글씨/배경 동기화)
            try:
                if hasattr(self, 'custom_menubar') and getattr(self.custom_menubar, 'refresh_theme_colors', None):
                    self.custom_menubar.refresh_theme_colors()
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"메뉴바 테마 갱신 무시: {_e}")
            
            # 4) 재고·톤백 트리 리프레시로 화면에 새 색상 반영
            try:
                if hasattr(self, '_deferred_refresh_main_tabs'):
                    self._deferred_refresh_main_tabs(delay_ms=50)
                else:
                    if hasattr(self, '_refresh_inventory'):
                        self._refresh_inventory()
                    if hasattr(self, '_refresh_tonbag'):
                        self._refresh_tonbag()
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"탭 리프레시 무시: {_e}")
            
            # v6.1.1: 50ms 후 2차 적용 (간헐적 타이밍 이슈 보험)
            try:
                self.root.update_idletasks()
                self.root.after(50, self._update_theme_colors)
            except Exception as _e:
                logger.debug(f"2차 적용 무시: {_e}")
            
            self._log(f"Theme changed: {theme_name}")
            
        except (ValueError, TypeError, AttributeError) as e:
            CustomMessageBox.showerror(self.root, "Error", f"Theme change failed:\n{e}")
    
    def _update_theme_colors(self) -> None:
        """v6.1.1: 테마 변경 시 전체 위젯 자동 스캔 + 일괄 갱신 (실패 시 fallback)"""
        try:
            from ..utils.theme_refresh import refresh_all_widgets_for_theme
            stats = refresh_all_widgets_for_theme(self)
            logger.debug(f"[v6.1.1] _update_theme_colors: {stats}")
        except (ImportError, Exception) as e:
            logger.debug(f"theme_refresh 실패, fallback 사용: {e}")
            self._update_theme_colors_fallback()

    def _update_theme_colors_fallback(self) -> None:
        """v6.1.1: theme_refresh 사용 불가 시 기존 방식으로 최소 갱신"""
        from ..utils.ui_constants import ThemeColors
        from tkinter import ttk as _ttk_mod

        is_dark = ThemeColors.is_dark_theme(self.current_theme)
        p = ThemeColors.get_palette(is_dark)
        fg = p['text_primary']
        bg = p['bg_card']
        bg_sec = p['bg_secondary']
        try:
            _st = _ttk_mod.Style()
            for sn in ('Treeview', 'Inv.Treeview', 'Tb.Treeview', 'Cargo.Treeview'):
                try:
                    _st.configure(sn, foreground=fg, background=bg, fieldbackground=bg)
                    _st.map(sn, foreground=[('selected', p['tree_select_fg']), ('!selected', fg)], background=[('selected', p['tree_select_bg'])])
                    _st.configure(f"{sn}.Heading", foreground=fg, background=bg_sec)
                except Exception:
                    pass
        except Exception as _e:
            logger.debug(f"fallback 전역 스타일 갱신 무시: {_e}")

        if hasattr(self, 'tree_inventory'):
            ThemeColors.configure_tags(self.tree_inventory, is_dark)
            try:
                from ..utils.table_styler import TableStyler
                TableStyler.update_grid_style_for_theme(self.tree_inventory, is_dark)
            except (ImportError, Exception):
                pass
        if hasattr(self, 'tree_sublot'):
            ThemeColors.configure_tags(self.tree_sublot, is_dark)
            try:
                from ..utils.table_styler import TableStyler
                TableStyler.update_grid_style_for_theme(self.tree_sublot, is_dark)
            except (ImportError, Exception):
                pass
        try:
            if hasattr(self, '_refresh_toolbar_theme'):
                self._refresh_toolbar_theme()
        except (ValueError, TypeError, AttributeError):
            pass
    
    def _show_theme_selector(self) -> None:
        """Show theme selection dialog"""
        from ..utils.constants import tk, ttk, HAS_TTKBOOTSTRAP, BOTH, X, LEFT, RIGHT, END
        from ..utils.ui_constants import DialogSize, Spacing, FontScale, center_dialog
        
        if not HAS_TTKBOOTSTRAP:

            CustomMessageBox.showinfo(self.root, "Info", "Theme selection requires ttkbootstrap")
            return
        
        # === UI 통일성: 폰트 스케일 ===
        try:
            dpi = self.root.winfo_fpixels('1i')
        except (ImportError, ModuleNotFoundError):
            dpi = 96
        fonts = FontScale(dpi)
        
        # === UI 통일성: 다이얼로그 크기 표준화 (medium) ===
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Theme")
        
        dialog.geometry(DialogSize.get_geometry(self.root, 'medium'))
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)
        
        # === UI 통일성: 간격 표준화 ===
        # Current theme
        ttk.Label(dialog, text=f"Current: {self.current_theme}",
                  font=fonts.heading(bold=True)).pack(pady=Spacing.SM)
        
        # Notebook for light/dark themes
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=BOTH, expand=True, padx=Spacing.SM, pady=Spacing.XS)
        
        # Light themes tab
        light_frame = ttk.Frame(notebook, padding=Spacing.XS)
        notebook.add(light_frame, text="Light Themes")
        
        light_listbox = tk.Listbox(light_frame, height=15, font=fonts.body())
        light_listbox.pack(fill=BOTH, expand=True, padx=Spacing.XS, pady=Spacing.XS)
        
        for theme in self.LIGHT_THEMES:
            light_listbox.insert(END, theme)
            if theme == self.current_theme:
                light_listbox.selection_set(light_listbox.size() - 1)
        
        # Dark themes tab
        dark_frame = ttk.Frame(notebook, padding=Spacing.XS)
        notebook.add(dark_frame, text="Dark Themes")
        
        dark_listbox = tk.Listbox(dark_frame, height=15, font=fonts.body())
        dark_listbox.pack(fill=BOTH, expand=True, padx=Spacing.XS, pady=Spacing.XS)
        
        for theme in self.DARK_THEMES:
            dark_listbox.insert(END, theme)
            if theme == self.current_theme:
                dark_listbox.selection_set(dark_listbox.size() - 1)
        
        # Preview function
        def preview_theme(event=None):
            # Get selected theme
            current_tab = notebook.index(notebook.select())
            
            if current_tab == 0:  # Light
                selection = light_listbox.curselection()
                if selection:
                    theme = light_listbox.get(selection[0])
                    self._change_theme(theme)
            else:  # Dark
                selection = dark_listbox.curselection()
                if selection:
                    theme = dark_listbox.get(selection[0])
                    self._change_theme(theme)
        
        light_listbox.bind('<<ListboxSelect>>', preview_theme)
        dark_listbox.bind('<<ListboxSelect>>', preview_theme)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=X, padx=Spacing.SM, pady=Spacing.SM)
        
        ttk.Button(btn_frame, text="Apply", command=dialog.destroy, width=10).pack(
            side=RIGHT, padx=Spacing.XS
        )
        ttk.Button(btn_frame, text="Reset to Default", width=15,
                   command=lambda: self._change_theme('flatly')).pack(side=LEFT, padx=Spacing.XS)
        
        # === UI 통일성: 중앙 배치 ===
        center_dialog(dialog, self.root)
        
        # ESC로 닫기
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def _toggle_dark_mode_theme(self) -> None:
        """Toggle between light and dark mode"""
        if self.current_theme in self.DARK_THEMES:
            # Switch to light (v3.0: flatly 사용)
            self._change_theme('flatly')
        else:
            # Switch to dark
            self._change_theme('darkly')
