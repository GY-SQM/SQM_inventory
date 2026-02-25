# -*- coding: utf-8 -*-
"""
SQM Inventory - Refresh and Filter Mixin
========================================

v2.9.91 - Extracted from gui_app.py

Data refresh, filtering, and sorting functions
"""

import logging

logger = logging.getLogger(__name__)


class RefreshMixin:
    """
    Refresh and filter mixin
    
    Mixed into SQMInventoryApp class
    """
    
    def _on_search_legacy(self, *args) -> None:
        """[LEGACY] Search input changed - InventoryTabMixin 사용"""
        self._refresh_inventory()
    
    def _on_status_filter_legacy(self, event=None) -> None:
        """[LEGACY] Status filter changed - InventoryTabMixin 사용"""
        self._refresh_inventory()
    
    def _on_tonbag_search_legacy(self, *args) -> None:
        """[LEGACY] Tonbag search input changed - TonbagTabMixin 사용"""
        self._refresh_tonbag()
    
    def _on_tonbag_filter_legacy(self, event=None) -> None:
        """[LEGACY] Tonbag status filter changed - TonbagTabMixin 사용"""
        self._refresh_tonbag()

    def _refresh_main_tabs(self) -> None:
        """상위 메뉴 작업 후 필수 탭 즉시 반영"""
        for fn in [
            '_refresh_inventory',
            '_refresh_allocation',
            '_refresh_picked',
            '_refresh_sold',
            '_refresh_tonbag',
            '_refresh_outbound_scheduled',
            '_refresh_dashboard',
            '_refresh_cargo_overview',
        ]:
            if hasattr(self, fn):
                try:
                    getattr(self, fn)()
                except (ValueError, TypeError, RuntimeError) as e:
                    logger.debug(f"{fn} refresh skipped: {e}")

    def _deferred_refresh_main_tabs(self, delay_ms: int = 50) -> None:
        """UI 블로킹 방지용 지연 리프레시 (모달/탭 동기화용)"""
        root = getattr(self, 'root', None)
        if root and root.winfo_exists():
            root.after(delay_ms, self._refresh_main_tabs)
        else:
            self._refresh_main_tabs()
    
    def _focus_search_legacy(self) -> None:
        """Focus on search entry (Ctrl+F)"""
        if hasattr(self, 'search_var'):
            # Find search entry widget
            for widget in self.tab_inventory.winfo_children():
                if isinstance(widget, (self.ttk.Entry if hasattr(self, 'ttk') else object)):
                    widget.focus_set()
                    widget.select_range(0, 'end')
                    break
    
    def _update_recent_files_menu(self) -> None:
        """Update recent files menu"""
        if not hasattr(self, 'recent_menu'):
            return
        
        # Clear existing items
        self.recent_menu.delete(0, 'end')
        
        # Get recent files (from config or history)
        recent_files = getattr(self, 'recent_files', [])
        
        if not recent_files:
            self.recent_menu.add_command(label="(No recent files)", state='disabled')
            return
        
        for file_path in recent_files[:10]:  # Max 10 files
            filename = file_path.split('/')[-1].split('\\')[-1]
            self.recent_menu.add_command(
                label=filename,
                command=lambda p=file_path: self._open_recent_file(p)
            )
    
    def _open_recent_file(self, file_path: str) -> None:
        """Open recent file"""
        import os
        
        if not os.path.exists(file_path):

            CustomMessageBox.showwarning(self.root, "File Not Found", f"File not found:\n{file_path}")
            return
        
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            self._process_inbound(file_path)
        elif ext in ('.xlsx', '.xls'):
            self._process_excel_inbound(file_path)
        else:
            self._log(f"WARNING Unsupported file type: {ext}")
    
    def _add_recent_file(self, file_path: str) -> None:
        """Add file to recent files list"""
        if not hasattr(self, 'recent_files'):
            self.recent_files = []
        
        # Remove if already exists
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        
        # Add to front
        self.recent_files.insert(0, file_path)
        
        # Keep max 20
        self.recent_files = self.recent_files[:20]
        
        # Update menu
        self._update_recent_files_menu()
