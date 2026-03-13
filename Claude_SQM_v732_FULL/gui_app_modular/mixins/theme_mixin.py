# -*- coding: utf-8 -*-
"""
SQM Inventory - Theme Mixin
===========================

v3.6.0 - UI 통일성 적용
- 다이얼로그 크기 표준화
- 간격 표준화
- 중앙 배치
"""

import os
import json
import logging
from ..utils.ui_constants import CustomMessageBox
from pathlib import Path

logger = logging.getLogger(__name__)


class ThemeMixin:
    """
    Theme management mixin
    
    Mixed into SQMInventoryApp class
    """
    
    # v7.3.3: 심플 2-테마 (라이트 1 + 다크 1)
    LIGHT_THEMES = ['flatly']
    DARK_THEMES = ['darkly']
    

    def _load_theme_preference(self) -> str:
        """Load theme preference (RUBI: 단일 다크 기본 + 숨김 오버라이드)

        우선순위:
          1) 환경변수 SQM_THEME (숨김)
          2) setting.ini [UI] theme (숨김/관리자)
          3) theme_preference.json (레거시 호환)
          4) 기본값: darkly (단일 다크)
        """
        # 1) ENV override (hidden switch)
        try:
            env_theme = (os.environ.get("SQM_THEME", "") or "").strip()
            if env_theme:
                return env_theme
        except Exception:
            pass

        # 2) setting.ini override (hidden/admin)
        try:
            import configparser
            ini = configparser.ConfigParser()
            ini_path = Path(__file__).parent.parent.parent / "setting.ini"
            if ini_path.exists():
                ini.read(str(ini_path), encoding="utf-8")
                ini_theme = (ini.get("UI", "theme", fallback="") or "").strip()
                if ini_theme:
                    return ini_theme
        except Exception:
            pass

        # 3) legacy preference file
        try:
            pref_file = Path(__file__).parent.parent.parent / "theme_preference.json"
            if pref_file.exists():
                with open(pref_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    legacy = (data.get('theme', '') or '').strip()
                    if legacy:
                        # v7.3.3: 구 테마를 flatly/darkly로 정규화
                        _OLD_DARKS = {'darkly', 'cyborg', 'superhero', 'solar', 'vapor'}
                        if legacy in _OLD_DARKS:
                            return 'darkly'
                        elif legacy == 'flatly':
                            return 'flatly'
                        else:
                            # 기타 라이트 테마 → flatly로 매핑
                            return 'flatly'
        except (OSError, IOError, PermissionError) as e:
            logger.error(f"Load theme preference error: {e}")

        # 4) default: single dark theme
        return 'darkly'

    
    def _save_theme_preference(self, theme_name: str) -> None:
        """Save theme preference to file"""
        try:
            pref_file = Path(__file__).parent.parent.parent / "theme_preference.json"
            
            with open(pref_file, 'w', encoding='utf-8') as f:
                json.dump({'theme': theme_name}, f)
            
        except (OSError, IOError, PermissionError) as e:
            logger.error(f"Save theme preference error: {e}")
    
    # ttkbootstrap Duplicate element 방지 패치 (1회만 적용)
    _element_create_patched = False

    def _change_theme(self, theme_name: str) -> None:
        """Change application theme — 근본 해결: 전역 스타일·메뉴바·트리 일괄 갱신"""
        from ..utils.constants import HAS_TTKBOOTSTRAP

        if not HAS_TTKBOOTSTRAP:
            CustomMessageBox.showinfo(self.root, "Info", "Theme change requires ttkbootstrap")
            return

        # ★ v7.3.2-fix: ttkbootstrap element_create 중복 에러 방지 (Python 3.14 호환)
        if not ThemeMixin._element_create_patched:
            try:
                import tkinter.ttk as _ttk_mod
                _orig = _ttk_mod.Style.element_create
                def _safe_element_create(self_style, elementname, etype, *args, **kw):
                    try:
                        return _orig(self_style, elementname, etype, *args, **kw)
                    except Exception as _exc:
                        if 'Duplicate element' in str(_exc):
                            pass  # 이미 존재하는 element는 무시
                        else:
                            raise
                _ttk_mod.Style.element_create = _safe_element_create
                ThemeMixin._element_create_patched = True
                logger.debug("[v7.3.2] element_create 중복 방지 패치 적용")
            except Exception as _pe:
                logger.debug(f"element_create 패치 실패: {_pe}")

        try:
            # v7.3.3: GY 색상을 STANDARD_THEMES에 적용 (다크/라이트 분기)
            try:
                from ttkbootstrap.themes.standard import STANDARD_THEMES
                _gy_dark = {
                    'primary': '#10B981', 'secondary': '#64748b',
                    'success': '#10b981', 'info': '#0ea5e9',
                    'warning': '#f59e0b', 'danger': '#ef4444',
                    'light': '#cbd5e1', 'dark': '#0f172a',
                    'bg': '#0b1120', 'fg': '#e2e8f0',
                    'selectbg': '#1d4ed8', 'selectfg': '#ffffff',
                    'border': '#1e3a5f', 'inputfg': '#ffffff',
                    'inputbg': '#111827', 'active': '#1e293b',
                }
                _gy_light = {
                    'primary': '#059669', 'secondary': '#64748b',
                    'success': '#059669', 'info': '#0284c7',
                    'warning': '#d97706', 'danger': '#dc2626',
                    'light': '#f8fafc', 'dark': '#1e293b',
                    'bg': '#f8fafc', 'fg': '#1e293b',
                    'selectbg': '#dbeafe', 'selectfg': '#1e3a5f',
                    'border': '#e2e8f0', 'inputfg': '#1e293b',
                    'inputbg': '#ffffff', 'active': '#e2e8f0',
                }
                _gy = _gy_dark if theme_name == 'darkly' else _gy_light
                if theme_name in STANDARD_THEMES:
                    STANDARD_THEMES[theme_name]['colors'].update(_gy)
            except Exception as _e:
                logger.debug(f"GY colors re-apply: {_e}")

            if hasattr(self.root, 'style'):
                self.root.style.theme_use(theme_name)

            self.current_theme = theme_name
            self._save_theme_preference(theme_name)
            
            # 1) 전역 가독성 스타일 재적용 (Treeview/Notebook 등 글씨·배경 동기화)
            try:
                from ..utils.ui_constants import ReadableStyle, apply_contrast_scrollbar_style, ThemeColors
                ReadableStyle.apply(self.root, theme_name)
                apply_contrast_scrollbar_style(self.root, theme_name)

                # [v6.3.3] 루트 배경 강제 (안전장치)
                is_dark = ThemeColors.is_dark_theme(theme_name)
                bg_color = ThemeColors.get('bg_primary', is_dark)
                try:
                    self.root.configure(background=bg_color)
                except Exception:
                    pass

            except (ImportError, Exception) as e:
                logger.debug(f"ReadableStyle 재적용 무시: {e}")
            
            # 2) 트리뷰 태그·그리드 스타일 + 메뉴바 색상 갱신
            self._update_theme_colors()
            # 메인 노트북 하단 중복 탭줄 재발 방지
            try:
                if hasattr(self, '_enforce_main_notebook_hidden_tabs'):
                    self._enforce_main_notebook_hidden_tabs()
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"메인 노트북 숨김 재적용 무시: {_e}")
            
            # 3) 메뉴바가 테마 색상 캐시를 쓰면 재적용 (글씨/배경 동기화)
            try:
                if hasattr(self, 'custom_menubar') and getattr(self.custom_menubar, 'refresh_theme_colors', None):
                    self.custom_menubar.refresh_theme_colors()
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"메뉴바 테마 갱신 무시: {_e}")
            
            # 4) 재고·톤백 트리 리프레시로 화면에 새 색상 반영
            try:
                self._safe_refresh()
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"탭 리프레시 무시: {_e}")
            
            # v7.3.3: 2차 적용 제거 — 1회 적용으로 충분
            try:
                self.root.update_idletasks()
            except Exception as _e:
                logger.debug(f"update_idletasks: {_e}")

            self._log(f"Theme changed: {theme_name}")

            # v7.3.0: 툴바 빠른 버튼 색상 동기화
            try:
                if hasattr(self, '_refresh_toolbar_colors'):
                    self._refresh_toolbar_colors()
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"toolbar color sync 무시: {_e}")

            # v7.3.3: colorful override 중복 호출 제거 — _update_theme_colors()가 이미 처리
            
        except (ValueError, TypeError, AttributeError) as e:
            CustomMessageBox.showerror(self.root, "Error", f"Theme change failed:\n{e}")
    
    def _update_theme_colors(self) -> None:
        """v6.1.1: 테마 변경 시 전체 위젯 자동 스캔 + 일괄 갱신 (실패 시 fallback)"""
        try:
            from ..utils.theme_refresh import refresh_all_widgets_for_theme
            stats = refresh_all_widgets_for_theme(self)
            logger.debug(f"[v6.2.3] _update_theme_colors: {stats}")
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
                except Exception as _te:
                    logger.debug(f"[테마] Treeview 스타일 적용 실패 ({sn}): {_te}")
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
        """v7.3.3: 테마 선택 → 단순 라이트/다크 토글"""
        self._toggle_dark_mode_theme()
    
    def _toggle_dark_mode_theme(self) -> None:
        """v7.3.3: 라이트 ↔ 다크 토글"""
        from ..utils.ui_constants import ThemeColors
        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'darkly'))
        new_theme = 'flatly' if is_dark else 'darkly'
        self._change_theme(new_theme)
        # DWM 타이틀바 색상 동기화
        try:
            from ..utils.win32_styling import apply_win11_style
            apply_win11_style(self.root, rounded=True, dark_titlebar=(new_theme == 'darkly'))
        except Exception:
            pass
