# -*- coding: utf-8 -*-
"""
SQM Inventory - Sidebar Navigation Mixin
=========================================

v7.3.2.1 - Left navigation sidebar replacing notebook tab headers.

Provides a sleek left-side navigation panel (140px) with:
- SQM logo at top
- Icon + label menu buttons with accent bar
- Active state highlighting
- Dark / Light theme color sync

Usage:
    class SQMInventoryApp(SidebarMixin, ...):
        def _setup_ui(self):
            ...
            self._build_sidebar()   # after notebook is created
"""

import logging
from ..utils.constants import tk
from ..utils.constants import ttk

from ..utils.ui_constants import ThemeColors, Spacing

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Color palettes (keyed by dark/light)
# ─────────────────────────────────────────────────────────────
_SIDEBAR_PALETTE = {
    True: {   # dark
        'bg':        '#0b1120',
        'hover':     '#1e293b',
        'active':    '#1e3a5f',
        'fg_normal': '#94a3b8',
        'fg_active': '#e2e8f0',
        'accent':    '#10B981',
        'logo_fg':   '#e2e8f0',
        'border':    '#1e3a5f',
    },
    False: {  # light
        'bg':        '#f1f5f9',
        'hover':     '#e2e8f0',
        'active':    '#dbeafe',
        'fg_normal': '#64748b',
        'fg_active': '#1e293b',
        'accent':    '#059669',
        'logo_fg':   '#1e293b',
        'border':    '#e2e8f0',
    },
}


class SidebarMixin:
    """Left navigation sidebar mixin.

    Mixed into ``SQMInventoryApp``.  Call ``_build_sidebar()`` **after**
    ``self.notebook`` and all ``self.tab_*`` frames have been created.

    Attributes written
    ------------------
    _sidebar_frame : tk.Frame
        The sidebar container.
    _sidebar_btns : dict[str, dict]
        ``{menu_id: {frame, accent, icon_lbl, text_lbl}}``.
    _sidebar_active : str | None
        Currently highlighted menu id.
    _sidebar_status_lbl : tk.Label
        Small status label at sidebar bottom.
    """

    # Menu definition -------------------------------------------------------
    # (menu_id, icon_emoji, label_text, tab_attribute_name)
    SIDEBAR_MENUS = [
        ("inventory",  "\U0001F4E6", "판매가능",   "tab_inventory"),
        ("allocation", "\U0001F4CB", "판매배정",   "tab_allocation"),
        ("picked",     "\U0001F3AF", "화물결정",   "tab_picked"),
        ("sold",       "\U0001F69A", "출고",       "tab_sold"),
        ("scan",       "\U0001F50D", "스캔",       "tab_scan"),
        ("overview",   "\U0001F4CA", "총괄재고",   "tab_cargo_overview"),
        ("dashboard",  "\U0001F4C8", "통계",       "tab_dashboard"),
        ("log",        "\U0001F4DD", "로그",       "tab_log"),
    ]

    SIDEBAR_WIDTH = 140

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _build_sidebar(self) -> None:
        """Create the left sidebar next to the notebook.

        Restructures the layout so that ``self.main_frame`` contains a
        horizontal split: ``[sidebar | notebook]``.  Notebook tab headers
        are hidden via a scoped custom style (not global).
        """
        try:
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly')
            )
            palette = _SIDEBAR_PALETTE[is_dark]

            # --- Hide notebook tab headers (scoped style, not global) ---
            try:
                style = ttk.Style()
                style.layout('Sidebar.TNotebook.Tab', [])
                self.notebook.configure(style='Sidebar.TNotebook')
            except (tk.TclError, RuntimeError, ValueError) as exc:
                logger.debug(f"[sidebar] 노트북 탭 헤더 숨김 실패: {exc}")

            # --- Detach notebook, rebuild layout in main_frame ---
            try:
                self.notebook.pack_forget()
            except (tk.TclError, AttributeError) as exc:
                logger.debug(f"[sidebar] notebook pack_forget: {exc}")

            # Sidebar frame (fixed width, packed left in main_frame)
            self._sidebar_frame = tk.Frame(
                self.main_frame,
                bg=palette['bg'],
                width=self.SIDEBAR_WIDTH,
                highlightthickness=0,
            )
            self._sidebar_frame.pack(side='left', fill='y')
            self._sidebar_frame.pack_propagate(False)

            # Right border separator
            sep = tk.Frame(self.main_frame, bg=palette['border'], width=1)
            sep.pack(side='left', fill='y')

            # Re-pack notebook (same parent main_frame, no in_= needed)
            self.notebook.pack(side='left', fill='both', expand=True)

            # --- Build sidebar contents ---
            self._sidebar_btns = {}
            self._sidebar_active = None

            # Logo / brand
            logo_frame = tk.Frame(self._sidebar_frame, bg=palette['bg'])
            logo_frame.pack(fill='x', pady=(18, 20))

            logo_lbl = tk.Label(
                logo_frame,
                text="SQM",
                font=('맑은 고딕', 18, 'bold'),
                fg=palette['accent'],
                bg=palette['bg'],
                anchor='center',
            )
            logo_lbl.pack()

            sub_lbl = tk.Label(
                logo_frame,
                text="재고관리",
                font=('맑은 고딕', 9),
                fg=palette['fg_normal'],
                bg=palette['bg'],
                anchor='center',
            )
            sub_lbl.pack()

            # Menu buttons
            for menu_id, icon, label, tab_attr in self.SIDEBAR_MENUS:
                btn_info = self._build_sidebar_btn(
                    self._sidebar_frame, menu_id, icon, label, tab_attr, palette
                )
                self._sidebar_btns[menu_id] = btn_info

            # Spacer (push status to bottom)
            spacer = tk.Frame(self._sidebar_frame, bg=palette['bg'])
            spacer.pack(fill='both', expand=True)

            # Bottom status label
            self._sidebar_status_lbl = tk.Label(
                self._sidebar_frame,
                text="v7.3.2.1",
                font=('맑은 고딕', 8),
                fg=palette['fg_normal'],
                bg=palette['bg'],
                anchor='center',
            )
            self._sidebar_status_lbl.pack(side='bottom', fill='x', pady=(0, 10))

            # Default active: first menu item
            first_id = self.SIDEBAR_MENUS[0][0]
            self._sidebar_set_active(first_id)

            logger.info("[sidebar] 사이드바 빌드 완료")

        except Exception as exc:
            logger.error(f"[sidebar] _build_sidebar 실패: {exc}", exc_info=True)

    # ------------------------------------------------------------------
    # Single button builder
    # ------------------------------------------------------------------

    def _build_sidebar_btn(
        self,
        parent: tk.Frame,
        menu_id: str,
        icon: str,
        label: str,
        tab_attr: str,
        palette: dict,
    ) -> dict:
        """Build a single sidebar navigation button.

        Parameters
        ----------
        parent : tk.Frame
            Sidebar frame.
        menu_id : str
            Unique identifier for this menu entry.
        icon : str
            Emoji icon string.
        label : str
            Korean display label.
        tab_attr : str
            Attribute name on ``self`` for the target notebook tab frame
            (e.g. ``"tab_inventory"``).
        palette : dict
            Current color palette.

        Returns
        -------
        dict
            ``{frame, accent, icon_lbl, text_lbl}`` widget references.
        """
        try:
            btn_frame = tk.Frame(
                parent,
                bg=palette['bg'],
                cursor='hand2',
            )
            btn_frame.pack(fill='x', pady=1)

            # Accent bar (3px left edge)
            accent = tk.Frame(
                btn_frame,
                bg=palette['bg'],
                width=3,
            )
            accent.pack(side='left', fill='y')

            # Content area
            content = tk.Frame(btn_frame, bg=palette['bg'])
            content.pack(side='left', fill='both', expand=True, padx=(6, 8), pady=6)

            # Icon label
            icon_lbl = tk.Label(
                content,
                text=icon,
                font=('Segoe UI Emoji', 13),
                fg=palette['fg_normal'],
                bg=palette['bg'],
                anchor='w',
            )
            icon_lbl.pack(side='left', padx=(0, 6))

            # Text label
            text_lbl = tk.Label(
                content,
                text=label,
                font=('맑은 고딕', 10),
                fg=palette['fg_normal'],
                bg=palette['bg'],
                anchor='w',
            )
            text_lbl.pack(side='left', fill='x', expand=True)

            # --- Bindings ---
            def _on_click(event=None):
                self._sidebar_set_active(menu_id)
                self._sidebar_switch_tab(tab_attr, label)

            def _on_enter(event=None):
                if self._sidebar_active != menu_id:
                    for w in (btn_frame, content, icon_lbl, text_lbl):
                        try:
                            w.configure(bg=palette['hover'])
                        except (tk.TclError, AttributeError):
                            pass

            def _on_leave(event=None):
                if self._sidebar_active != menu_id:
                    for w in (btn_frame, content, icon_lbl, text_lbl):
                        try:
                            w.configure(bg=palette['bg'])
                        except (tk.TclError, AttributeError):
                            pass

            for w in (btn_frame, content, icon_lbl, text_lbl):
                w.bind('<Button-1>', _on_click)
                w.bind('<Enter>', _on_enter)
                w.bind('<Leave>', _on_leave)

            return {
                'frame': btn_frame,
                'accent': accent,
                'icon_lbl': icon_lbl,
                'text_lbl': text_lbl,
                'content': content,
            }

        except Exception as exc:
            logger.error(
                f"[sidebar] _build_sidebar_btn 실패 (menu_id={menu_id}): {exc}",
                exc_info=True,
            )
            return {'frame': None, 'accent': None, 'icon_lbl': None, 'text_lbl': None, 'content': None}

    # ------------------------------------------------------------------
    # Active state management
    # ------------------------------------------------------------------

    def _sidebar_set_active(self, menu_id: str) -> None:
        """Highlight *menu_id* as active and dim all others.

        Parameters
        ----------
        menu_id : str
            The id of the menu item to activate.
        """
        try:
            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly')
            )
            palette = _SIDEBAR_PALETTE[is_dark]

            self._sidebar_active = menu_id

            for mid, refs in self._sidebar_btns.items():
                if any(v is None for v in refs.values()):
                    continue

                if mid == menu_id:
                    # Active state
                    active_bg = palette['active']
                    for w in (refs['frame'], refs.get('content'), refs['icon_lbl'], refs['text_lbl']):
                        if w:
                            try:
                                w.configure(bg=active_bg)
                            except (tk.TclError, AttributeError):
                                pass
                    try:
                        refs['accent'].configure(bg=palette['accent'])
                    except (tk.TclError, AttributeError):
                        pass
                    try:
                        refs['icon_lbl'].configure(fg=palette['fg_active'])
                        refs['text_lbl'].configure(fg=palette['fg_active'])
                    except (tk.TclError, AttributeError):
                        pass
                else:
                    # Normal (inactive) state
                    normal_bg = palette['bg']
                    for w in (refs['frame'], refs.get('content'), refs['icon_lbl'], refs['text_lbl']):
                        if w:
                            try:
                                w.configure(bg=normal_bg)
                            except (tk.TclError, AttributeError):
                                pass
                    try:
                        refs['accent'].configure(bg=palette['bg'])
                    except (tk.TclError, AttributeError):
                        pass
                    try:
                        refs['icon_lbl'].configure(fg=palette['fg_normal'])
                        refs['text_lbl'].configure(fg=palette['fg_normal'])
                    except (tk.TclError, AttributeError):
                        pass

        except Exception as exc:
            logger.error(f"[sidebar] _sidebar_set_active 실패: {exc}", exc_info=True)

    # ------------------------------------------------------------------
    # Tab switching
    # ------------------------------------------------------------------

    def _sidebar_switch_tab(self, tab_attr: str, label: str) -> None:
        """Select the notebook tab identified by *tab_attr*.

        Parameters
        ----------
        tab_attr : str
            Attribute name on ``self`` (e.g. ``"tab_inventory"``).
        label : str
            Human-readable label for logging.
        """
        try:
            tab_frame = getattr(self, tab_attr, None)
            if tab_frame is None:
                logger.warning(f"[sidebar] 탭 프레임 없음: {tab_attr}")
                return

            self.notebook.select(tab_frame)
            logger.debug(f"[sidebar] 탭 전환: {label} ({tab_attr})")

        except (tk.TclError, ValueError, AttributeError) as exc:
            logger.error(f"[sidebar] _sidebar_switch_tab 실패 ({tab_attr}): {exc}")

    # ------------------------------------------------------------------
    # Theme refresh
    # ------------------------------------------------------------------

    def _refresh_sidebar_colors(self) -> None:
        """Resync all sidebar widget colors after a theme change."""
        try:
            if not hasattr(self, '_sidebar_frame') or self._sidebar_frame is None:
                return

            is_dark = ThemeColors.is_dark_theme(
                getattr(self, 'current_theme', 'flatly')
            )
            palette = _SIDEBAR_PALETTE[is_dark]

            # Sidebar frame background
            try:
                self._sidebar_frame.configure(bg=palette['bg'])
            except (tk.TclError, AttributeError):
                pass

            # Walk all direct children of sidebar and set bg
            try:
                for child in self._sidebar_frame.winfo_children():
                    try:
                        child.configure(bg=palette['bg'])
                    except (tk.TclError, AttributeError):
                        pass
                    # Recursively update nested children
                    for sub in child.winfo_children():
                        try:
                            sub.configure(bg=palette['bg'])
                        except (tk.TclError, AttributeError):
                            pass
            except (tk.TclError, AttributeError):
                pass

            # Status label
            try:
                if hasattr(self, '_sidebar_status_lbl') and self._sidebar_status_lbl:
                    self._sidebar_status_lbl.configure(
                        bg=palette['bg'],
                        fg=palette['fg_normal'],
                    )
            except (tk.TclError, AttributeError):
                pass

            # Re-apply active state highlight
            active_id = getattr(self, '_sidebar_active', None)
            if active_id:
                self._sidebar_set_active(active_id)

            logger.debug("[sidebar] 사이드바 색상 새로고침 완료")

        except Exception as exc:
            logger.error(f"[sidebar] _refresh_sidebar_colors 실패: {exc}", exc_info=True)
