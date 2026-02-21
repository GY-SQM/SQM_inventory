# -*- coding: utf-8 -*-
"""
SQM Inventory - Key Bindings Mixin
==================================

v2.9.91 - Extracted from gui_app.py

Keyboard shortcuts and hotkey handling
"""

import logging
from ..utils.ui_constants import CustomMessageBox, DialogSize, center_dialog, apply_modal_window_options
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class KeyBindingsMixin:
    """
    Keyboard shortcuts mixin
    
    Mixed into SQMInventoryApp class
    """
    
    def _setup_keybindings(self) -> None:
        """Setup all keyboard shortcuts"""
        # File operations
        self.root.bind('<Control-o>', self._on_open_file)
        self.root.bind('<Control-O>', self._on_open_file)
        self.root.bind('<Control-s>', self._on_save)
        self.root.bind('<Control-S>', self._on_save)
        self.root.bind('<Control-Shift-s>', self._on_save_as)
        self.root.bind('<Control-Shift-S>', self._on_save_as)
        
        # Search
        self.root.bind('<Control-f>', self._focus_search)
        self.root.bind('<Control-F>', self._focus_search)
        
        # Refresh
        self.root.bind('<F5>', self._on_refresh_all)
        self.root.bind('<Control-r>', self._on_refresh_all)
        self.root.bind('<Control-R>', self._on_refresh_all)
        
        # Navigation
        self.root.bind('<Control-Tab>', self._next_tab)
        self.root.bind('<Control-Shift-Tab>', self._prev_tab)
        self.root.bind('<Control-1>', lambda e: self._goto_tab(0))
        self.root.bind('<Control-2>', lambda e: self._goto_tab(1))
        self.root.bind('<Control-3>', lambda e: self._goto_tab(2))
        self.root.bind('<Control-4>', lambda e: self._goto_tab(3))
        self.root.bind('<Control-5>', lambda e: self._goto_tab(4))
        
        # Window
        self.root.bind('<F11>', self._toggle_fullscreen)
        self.root.bind('<Escape>', self._on_escape)
        self.root.bind('<Control-q>', self._on_force_quit)
        self.root.bind('<Control-Q>', self._on_force_quit)
        
        # Quick actions
        self.root.bind('<Control-n>', self._on_new_inbound)
        self.root.bind('<Control-N>', self._on_new_inbound)
        self.root.bind('<Control-e>', self._on_export)
        self.root.bind('<Control-E>', self._on_export)
        self.root.bind('<Control-b>', self._on_backup)
        self.root.bind('<Control-B>', self._on_backup)
        
        # Help
        self.root.bind('<F1>', self._show_help)
        
        # 테스트 DB 초기화 단축키 제거 — Ctrl+Shift+X로 실수 시 DB 파일(.db/.shm/.wal) 삭제 사고 방지.
        # 초기화는 메뉴(데이터베이스 > 테스트 DB 초기화)에서만 호출 가능.
        # self.root.bind('<Control-Shift-X>', self._show_test_db_reset_popup)
        
        self._log("Keyboard shortcuts configured")
    
    def _on_open_file(self, event=None) -> None:
        """Open file (Ctrl+O)"""
        if hasattr(self, '_hide_empty_state_hint'):
            self._hide_empty_state_hint()
        from ..utils.constants import filedialog

        file_path = filedialog.askopenfilename(
            title="Open File",
            filetypes=[
                ("All supported", "*.pdf *.xlsx *.xls"),
                ("PDF files", "*.pdf"),
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            import os
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.pdf':
                self._process_inbound(file_path)
            elif ext in ('.xlsx', '.xls'):
                self._process_excel_inbound(file_path)
    
    def _on_save(self, event=None) -> None:
        """Save (Ctrl+S) - Quick export"""
        self._on_export_click(option=3)
    
    def _on_save_as(self, event=None) -> None:
        """Save As (Ctrl+Shift+S) - Export with dialog"""
        self._on_export_click(option=7)
    
    def _focus_search(self, event=None) -> None:
        """Focus search entry (Ctrl+F)"""
        if hasattr(self, 'search_var'):
            # Try to find and focus search entry
            for tab in self.notebook.tabs():
                tab_widget = self.notebook.nametowidget(tab)
                for child in tab_widget.winfo_children():
                    if hasattr(child, 'winfo_children'):
                        for subchild in child.winfo_children():
                            if isinstance(subchild, self.root.nametowidget('.').__class__):
                                # Found entry widget
                                subchild.focus_set()
                                if hasattr(subchild, 'select_range'):
                                    subchild.select_range(0, 'end')
                                return
    
    def _on_refresh_all(self, event=None) -> None:
        """Refresh all tabs (F5, Ctrl+R)"""
        self._refresh_inventory()
        self._refresh_tonbag()
        if hasattr(self, '_refresh_summary'):
            self._refresh_summary()
        # v3.6.2: 대시보드 + 피봇도 새로고침
        if hasattr(self, '_refresh_dashboard'):
            try:
                self._refresh_dashboard()
            except (AttributeError, RuntimeError) as _e:
                logger.debug(f"Dashboard refresh on F5: {_e}")
        self._log("All tabs refreshed")
    
    def _next_tab(self, event=None) -> None:
        """Go to next tab (Ctrl+Tab)"""
        if hasattr(self, 'notebook'):
            current = self.notebook.index('current')
            total = self.notebook.index('end')
            next_tab = (current + 1) % total
            self.notebook.select(next_tab)
    
    def _prev_tab(self, event=None) -> None:
        """Go to previous tab (Ctrl+Shift+Tab)"""
        if hasattr(self, 'notebook'):
            current = self.notebook.index('current')
            total = self.notebook.index('end')
            prev_tab = (current - 1) % total
            self.notebook.select(prev_tab)
    
    def _goto_tab(self, index: int) -> None:
        """Go to specific tab (Ctrl+1~5)"""
        if hasattr(self, 'notebook'):
            total = self.notebook.index('end')
            if 0 <= index < total:
                self.notebook.select(index)
    
    def _toggle_fullscreen(self, event=None) -> None:
        """Toggle fullscreen (F11)"""
        is_fullscreen = getattr(self, '_is_fullscreen', False)
        self._is_fullscreen = not is_fullscreen
        self.root.attributes('-fullscreen', self._is_fullscreen)
    
    def _on_force_quit(self, event=None) -> None:
        """강제 종료 (Ctrl+Q)"""
        try:
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            logger.debug(f"Force quit: {e}")
            import sys
            sys.exit(0)

    def _on_escape(self, event=None) -> None:
        """Handle Escape key"""
        # Exit fullscreen if active
        if getattr(self, '_is_fullscreen', False):
            self._is_fullscreen = False
            self.root.attributes('-fullscreen', False)
            return
        
        # Clear search
        if hasattr(self, 'search_var') and self.search_var.get():
            self.search_var.set('')
            self._refresh_inventory()
            return
        
        # Clear tonbag search
        if hasattr(self, 'tonbag_search_var') and self.tonbag_search_var.get():
            self.tonbag_search_var.set('')
            self._refresh_tonbag()
    
    def _on_new_inbound(self, event=None) -> None:
        """New inbound (Ctrl+N)"""
        if hasattr(self, '_hide_empty_state_hint'):
            self._hide_empty_state_hint()
        if hasattr(self, '_on_pdf_inbound'):
            self._on_pdf_inbound()
    
    def _on_export(self, event=None) -> None:
        """Export (Ctrl+E)"""
        self._on_export_click(option=3)
    
    def _on_backup(self, event=None) -> None:
        """Backup (Ctrl+B)"""
        if hasattr(self, '_on_backup_click'):
            self._on_backup_click()
    
    def _show_help(self, event=None) -> None:
        """Show help dialog (F1)"""

        
        help_text = """SQM Inventory Management System
        
Keyboard Shortcuts:
═══════════════════════════════════════

File Operations:
  Ctrl+O       Open file (PDF/Excel)
  Ctrl+S       Quick export
  Ctrl+Shift+S Export with options
  Ctrl+N       New inbound
  Ctrl+E       Export inventory
  Ctrl+B       Create backup

Navigation:
  Ctrl+Tab     Next tab
  Ctrl+Shift+Tab  Previous tab
  Ctrl+1~5     Go to tab 1~5

Search:
  Ctrl+F       Focus search
  Escape       Clear search

Window:
  F5           Refresh all
  F11          Toggle fullscreen
  Escape       Exit fullscreen

Help:
  F1           Show this help

═══════════════════════════════════════
v2.9.91 - SQM Inventory System
"""
        CustomMessageBox.showinfo(self.root, "Help", help_text)
    
    def _bind_treeview_keys(self, tree, on_delete: Optional[Callable] = None) -> None:
        """Bind common treeview keyboard shortcuts"""
        # Select all
        tree.bind('<Control-a>', lambda e: self._select_all_treeview(tree))
        tree.bind('<Control-A>', lambda e: self._select_all_treeview(tree))
        
        # Copy
        tree.bind('<Control-c>', lambda e: self._copy_treeview_selection(tree))
        tree.bind('<Control-C>', lambda e: self._copy_treeview_selection(tree))
        
        # Delete (if handler provided)
        if on_delete:
            tree.bind('<Delete>', lambda e: on_delete())
    
    def _select_all_treeview(self, tree) -> None:
        """Select all items in treeview"""
        items = tree.get_children()
        tree.selection_set(items)
    
    def _copy_treeview_selection(self, tree) -> None:
        """Copy selected treeview items to clipboard"""
        selection = tree.selection()
        if not selection:
            return
        
        # Build text from selection
        lines = []
        for item_id in selection:
            values = tree.item(item_id, 'values')
            if values:
                lines.append('\t'.join(str(v) for v in values))
        
        if lines:
            text = '\n'.join(lines)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._log(f"Copied {len(lines)} rows to clipboard")

    def _show_test_db_reset_popup(self, event=None) -> None:
        """테스트 DB 초기화 전 확인 팝업 (메뉴에서 호출, 단축키는 실수 방지로 제거됨)"""
        from ..utils.constants import tk, ttk
        popup = tk.Toplevel(self.root)
        popup.title("테스트 DB 초기화")
        apply_modal_window_options(popup)
        popup.transient(self.root)
        popup.grab_set()
        popup.geometry(DialogSize.get_geometry(self.root, 'small'))
        center_dialog(popup, self.root)
        frame = ttk.Frame(popup, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="테스트용 데이터베이스를 초기화합니다.\n모든 재고·톤백·출고 데이터가 삭제됩니다.",
                  font=('맑은 고딕', 11), wraplength=360).pack(anchor='w', pady=(0, 12))
        ttk.Label(frame, text="정말 데이터베이스를 지우시겠습니까?",
                  font=('맑은 고딕', 10), foreground='#e67e22').pack(anchor='w', pady=(0, 16))
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        def do_reset():
            popup.destroy()
            self._reset_test_db()
        ttk.Button(btn_frame, text="예, 초기화", command=do_reset, width=18).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="취소", command=popup.destroy, width=10).pack(side=tk.LEFT)
        popup.bind('<Escape>', lambda e: popup.destroy())
        popup.protocol("WM_DELETE_WINDOW", popup.destroy)

    def _reset_test_db(self) -> None:
        """테스트 DB 초기화 — SQLite만 지원. 연결 종료 후 파일 삭제·재생성."""
        import os
        import shutil
        from datetime import datetime
        if not getattr(self, 'engine', None):
            self._log("⚠️ 엔진이 없습니다.")
            return
        db_path = getattr(self.engine, 'db_path', None)
        if not db_path or db_path == ':memory:':
            self._log("⚠️ 메모리 DB 또는 경로 없음 — 초기화 불가")
            return
        if getattr(self.engine, 'db_type', 'sqlite') != 'sqlite':
            self._log("⚠️ 테스트 DB 초기화는 SQLite에서만 지원합니다.")
            return
        path = os.path.abspath(db_path)
        if not os.path.isfile(path):
            self._log("⚠️ DB 파일이 없습니다.")
            return
        try:
            if hasattr(self.engine, 'db') and hasattr(self.engine.db, 'close'):
                self.engine.db.close()
        except Exception as e:
            logger.debug(f"DB close: {e}")
        backup_dir = os.path.join(os.path.dirname(path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f"sqm_before_reset_{stamp}.db")
        try:
            shutil.copy2(path, backup_path)
            self._log(f"백업: {backup_path}")
        except OSError as e:
            logger.warning(f"백업 실패: {e}")
        try:
            os.remove(path)
        except OSError as e:
            self._log(f"❌ DB 파일 삭제 실패: {e}")
            CustomMessageBox.showerror(self.root, "테스트 DB 초기화", f"파일이 사용 중이거나 권한이 없습니다.\n{e}")
            return
        try:
            self._init_engine()
            self._log("✅ 테스트 DB 초기화 완료.")
            self._refresh_inventory()
            self._refresh_tonbag()
            if hasattr(self, '_refresh_dashboard') and callable(self._refresh_dashboard):
                try:
                    self._refresh_dashboard()
                except Exception as _e:
                    logger.debug(f"Dashboard refresh: {_e}")
            CustomMessageBox.showinfo(self.root, "테스트 DB 초기화", "데이터베이스가 초기화되었습니다.\n재고·톤백 화면이 갱신됩니다.")
        except Exception as e:
            logger.error(f"테스트 DB 초기화 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.root, "테스트 DB 초기화", f"엔진 재생성 실패:\n{e}")
