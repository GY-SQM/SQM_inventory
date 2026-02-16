# -*- coding: utf-8 -*-
"""
SQM Inventory - Context Menu Mixin
==================================

v2.9.91 - Extracted from gui_app.py

Right-click context menus for treeviews
"""

import sqlite3
import logging

from ..utils.ui_constants import CustomMessageBox, ThemeColors
logger = logging.getLogger(__name__)


class ContextMenuMixin:
    """
    Context menu mixin
    
    Mixed into SQMInventoryApp class
    """
    
    def _setup_context_menus(self) -> None:
        """Setup context menus for all treeviews"""
        # Inventory treeview context menu
        if hasattr(self, 'tree_inventory'):
            self._setup_inventory_context_menu()
        
        # Tonbag treeview context menu
        if hasattr(self, 'tree_sublot'):
            self._setup_tonbag_context_menu()
        
        # Search treeview context menu
        if hasattr(self, 'tree_search'):
            self._setup_search_context_menu()
    
    def _setup_inventory_context_menu(self) -> None:
        """Setup inventory treeview context menu"""
        from ..utils.constants import Menu
        
        self.inventory_menu = Menu(self.root, tearoff=0)
        self.inventory_menu.add_command(label="📋 View Details", command=self._view_lot_details)
        self.inventory_menu.add_command(label="🎒 View Tonbags", command=self._view_lot_tonbags)
        self.inventory_menu.add_command(label="📅 LOT 히스토리", command=self._show_lot_history_timeline)
        self.inventory_menu.add_separator()
        self.inventory_menu.add_command(label="✏️ Edit LOT", command=self._edit_lot)
        self.inventory_menu.add_command(label="🗑️ Delete LOT", command=self._delete_lot)
        self.inventory_menu.add_separator()
        self.inventory_menu.add_command(label="📥 Export Selected", command=self._export_selected_lots)
        self.inventory_menu.add_command(label="📋 Copy to Clipboard", command=lambda: self._copy_treeview_selection(self.tree_inventory))
        
        self.tree_inventory.bind('<Button-3>', self._show_inventory_context_menu)
    
    def _show_inventory_context_menu(self, event) -> None:
        """Show inventory context menu"""
        # Select row under cursor
        item = self.tree_inventory.identify_row(event.y)
        if item:
            self.tree_inventory.selection_set(item)
            self.inventory_menu.post(event.x_root, event.y_root)
    
    def _view_lot_details(self) -> None:
        """View LOT details from context menu"""
        selection = self.tree_inventory.selection()
        if not selection:
            return
        
        values = self.tree_inventory.item(selection[0], 'values')
        if values:
            lot_no = values[0]
            # v3.6.2: _show_lot_detail → _show_lot_detail_popup (정확한 메서드명)
            if hasattr(self, '_show_lot_detail_popup'):
                self._show_lot_detail_popup(str(lot_no))
            else:
                logger.warning(f"LOT 상세 팝업 미구현: {lot_no}")
    
    def _view_lot_tonbags(self) -> None:
        """View LOT tonbags from context menu"""
        selection = self.tree_inventory.selection()
        if not selection:
            return
        
        values = self.tree_inventory.item(selection[0], 'values')
        if values:
            lot_no = values[0]
            # Switch to tonbag tab with filter
            if hasattr(self, 'tonbag_search_var'):
                self.tonbag_search_var.set(lot_no)
            if hasattr(self, 'notebook'):
                self.notebook.select(2)  # Tonbag tab
    
    def _edit_lot(self) -> None:
        """Edit LOT from context menu"""
        from ..utils.constants import tk, ttk, BOTH, X, W
        
        selection = self.tree_inventory.selection()
        if not selection:
            return
        
        values = self.tree_inventory.item(selection[0], 'values')
        if not values:
            return
        
        lot_no = values[0]
        
        # Get current LOT data
        lot_data = self.engine.db.fetchone(
            "SELECT * FROM inventory WHERE lot_no = ?",
            (lot_no,)
        )
        
        if not lot_data:
            CustomMessageBox.showerror(self.root, "Error", f"LOT not found: {lot_no}")
            return
        
        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit LOT: {lot_no}")
        dialog.geometry("450x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Form frame
        form_frame = ttk.Frame(dialog, padding=10)
        form_frame.pack(fill=BOTH, expand=True)
        
        # Fields
        fields = {}
        editable_fields = [
            ('sap_no', 'SAP NO'),
            ('bl_no', 'B/L NO'),
            ('product', 'Product'),
            ('container_no', 'Container'),
            ('sold_to', 'Sold To'),
            ('sale_ref', 'Sale Ref'),
            ('warehouse', 'Warehouse'),
            ('remark', 'Remark'),
        ]
        
        for i, (field, label) in enumerate(editable_fields):
            ttk.Label(form_frame, text=f"{label}:").grid(row=i, column=0, sticky=W, pady=3)
            var = tk.StringVar(value=lot_data.get(field, '') or '')
            entry = ttk.Entry(form_frame, textvariable=var, width=35)
            entry.grid(row=i, column=1, pady=3, padx=5)
            fields[field] = var
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=X, pady=10, padx=10)
        
        def save_changes():
            try:
                updates = {field: var.get().strip() for field, var in fields.items()}
                
                # Build update query
                set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
                values = list(updates.values()) + [lot_no]
                
                self.engine.db.execute(
                    f"UPDATE inventory SET {set_clause} WHERE lot_no = ?",
                    values
                )
                
                self._log(f"LOT updated: {lot_no}")
                CustomMessageBox.showinfo(self.root, "Success", f"LOT {lot_no} updated")
                dialog.destroy()
                self._refresh_inventory()
                
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
                CustomMessageBox.showerror(self.root, "Error", f"Update failed: {e}")
        
        ttk.Button(btn_frame, text="Save", command=save_changes).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)
    
    def _delete_lot(self) -> None:
        """Delete LOT from context menu"""

        
        selection = self.tree_inventory.selection()
        if not selection:
            return
        
        values = self.tree_inventory.item(selection[0], 'values')
        if not values:
            return
        
        lot_no = values[0]
        
        if not CustomMessageBox.askyesno(self.root, "Confirm Delete",
            f"Delete LOT {lot_no}?\n\n"
            f"This will also delete all associated tonbags.\n"
            f"This action cannot be undone."):
            return
        
        try:
            with self.engine.db.transaction():
                # Delete tonbags first
                self.engine.db.execute(
                    "DELETE FROM inventory_tonbag WHERE lot_no = ?",
                    (lot_no,)
                )
                # Delete LOT
                self.engine.db.execute(
                    "DELETE FROM inventory WHERE lot_no = ?",
                    (lot_no,)
                )
            
            self._log(f"LOT deleted: {lot_no}")
            CustomMessageBox.showinfo(self.root, "Success", f"LOT {lot_no} deleted")
            self._refresh_inventory()
            self._refresh_tonbag()
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            CustomMessageBox.showerror(self.root, "Error", f"Delete failed: {e}")
    
    def _export_selected_lots(self) -> None:
        """Export selected LOTs to Excel"""
        from ..utils.constants import filedialog, pd, HAS_PANDAS
        
        if not HAS_PANDAS:
            CustomMessageBox.showerror(self.root, "Error", "pandas not installed")
            return
        
        selection = self.tree_inventory.selection()
        if not selection:
            CustomMessageBox.showwarning(self.root, "Warning", "Select LOTs to export")
            return
        
        # Collect selected LOT numbers
        lot_numbers = []
        for item_id in selection:
            values = self.tree_inventory.item(item_id, 'values')
            if values:
                lot_numbers.append(values[0])
        
        if not lot_numbers:
            return
        
        # Get file path
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"selected_lots_{len(lot_numbers)}.xlsx"
        )
        
        if not file_path:
            return
        
        try:
            # Get full data for selected LOTs
            placeholders = ','.join(['?'] * len(lot_numbers))
            lots = self.engine.db.fetchall(
                f"SELECT * FROM inventory WHERE lot_no IN ({placeholders})",
                lot_numbers
            )
            
            df = pd.DataFrame(lots)
            df.to_excel(file_path, index=False)
            
            self._log(f"Exported {len(lot_numbers)} LOTs to {file_path}")
            CustomMessageBox.showinfo(self.root, "Success", f"Exported {len(lot_numbers)} LOTs")
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            CustomMessageBox.showerror(self.root, "Error", f"Export failed: {e}")
    
    def _setup_tonbag_context_menu(self) -> None:
        """Setup tonbag treeview context menu"""
        from ..utils.constants import Menu
        
        self.tonbag_menu = Menu(self.root, tearoff=0)
        self.tonbag_menu.add_command(label="Select for Outbound", command=self._select_tonbag_for_outbound)
        self.tonbag_menu.add_command(label="Deselect", command=self._deselect_tonbag)
        self.tonbag_menu.add_separator()
        self.tonbag_menu.add_command(label="Edit Tonbag", command=self._edit_tonbag)
        self.tonbag_menu.add_command(label="Change Status", command=self._change_tonbag_status)
        self.tonbag_menu.add_separator()
        self.tonbag_menu.add_command(label="Copy to Clipboard", command=lambda: self._copy_treeview_selection(self.tree_sublot))
        
        self.tree_sublot.bind('<Button-3>', self._show_tonbag_context_menu)
    
    def _show_tonbag_context_menu(self, event) -> None:
        """Show tonbag context menu"""
        item = self.tree_sublot.identify_row(event.y)
        if item:
            self.tree_sublot.selection_set(item)
            self.tonbag_menu.post(event.x_root, event.y_root)
    
    def _select_tonbag_for_outbound(self) -> None:
        """Select tonbag for outbound"""
        selection = self.tree_sublot.selection()
        if not selection:
            return
        
        if not hasattr(self, 'selected_tonbags'):
            self.selected_tonbags = set()
        
        for item_id in selection:
            values = self.tree_sublot.item(item_id, 'values')
            if values and values[6] == 'AVAILABLE':  # status column
                self.selected_tonbags.add(item_id)
        
        self._set_status(f"Selected tonbags: {len(self.selected_tonbags)}")
    
    def _deselect_tonbag(self) -> None:
        """Deselect tonbag"""
        selection = self.tree_sublot.selection()
        if not selection:
            return
        
        if hasattr(self, 'selected_tonbags'):
            for item_id in selection:
                self.selected_tonbags.discard(item_id)
        
        self._set_status(f"Selected tonbags: {len(getattr(self, 'selected_tonbags', []))}")
    
    def _edit_tonbag(self) -> None:
        """Edit tonbag from context menu"""

        CustomMessageBox.showinfo(self.root, "Info", "Tonbag edit feature - coming soon")
    
    def _change_tonbag_status(self) -> None:
        """Change tonbag status from context menu"""
        from ..utils.constants import tk, ttk
        
        selection = self.tree_sublot.selection()
        if not selection:
            return
        
        # Get current values
        values = self.tree_sublot.item(selection[0], 'values')
        if not values:
            return
        
        lot_no = values[2]  # lot_no column
        sub_lt = values[3]  # sub_lt column
        current_status = values[6]  # status column
        
        # Status options
        statuses = ['AVAILABLE', 'PICKED', 'SOLD', 'SAMPLE', 'BLOCKED']
        
        # Simple dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Change Status")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"LOT: {lot_no}, Tonbag: {sub_lt}").pack(pady=10)
        ttk.Label(dialog, text=f"Current: {current_status}").pack()
        
        status_var = tk.StringVar(value=current_status)
        combo = ttk.Combobox(dialog, textvariable=status_var, values=statuses, state='readonly')
        combo.pack(pady=10)
        
        def save_status():
            new_status = status_var.get()
            try:
                self.engine.db.execute(
                    "UPDATE inventory_tonbag SET status = ? WHERE lot_no = ? AND sub_lt = ?",
                    (new_status, lot_no, int(sub_lt))
                )
                self._log(f"Tonbag status changed: {lot_no}-{sub_lt} -> {new_status}")
                dialog.destroy()
                self._refresh_tonbag()
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
                CustomMessageBox.showerror(self.root, "Error", f"Status change failed: {e}")
        
        ttk.Button(dialog, text="Save", command=save_status).pack(pady=10)
    
    def _setup_search_context_menu(self) -> None:
        """Setup search treeview context menu"""
        from ..utils.constants import Menu
        
        self.search_menu = Menu(self.root, tearoff=0)
        self.search_menu.add_command(label="Add to Report", command=self._add_to_search_report)
        self.search_menu.add_command(label="View LOT Details", command=self._view_search_lot_details)
        self.search_menu.add_separator()
        self.search_menu.add_command(label="Copy to Clipboard", command=lambda: self._copy_treeview_selection(self.tree_search))
        
        self.tree_search.bind('<Button-3>', self._show_search_context_menu)
    
    def _show_search_context_menu(self, event) -> None:
        """Show search context menu"""
        item = self.tree_search.identify_row(event.y)
        if item:
            self.tree_search.selection_set(item)
            self.search_menu.post(event.x_root, event.y_root)
    
    def _add_to_search_report(self) -> None:
        """Add search result to report"""
        selection = self.tree_search.selection()
        if not selection:
            return
        
        if not hasattr(self, 'selected_search_items'):
            self.selected_search_items = set()
        
        for item_id in selection:
            self.selected_search_items.add(item_id)
        
        self._set_status(f"Report items: {len(self.selected_search_items)}")
    
    def _view_search_lot_details(self) -> None:
        """View LOT details from search result"""
        selection = self.tree_search.selection()
        if not selection:
            return
        
        values = self.tree_search.item(selection[0], 'values')
        if values and len(values) > 3:
            lot_no = values[3]  # lot_no column
            # v3.6.2: _show_lot_detail → _show_lot_detail_popup
            if hasattr(self, '_show_lot_detail_popup'):
                self._show_lot_detail_popup(str(lot_no))
            else:
                logger.warning(f"LOT 상세 팝업 미구현: {lot_no}")
    
    def _show_lot_history_timeline(self) -> None:
        """v3.9.5: LOT 히스토리 타임라인 (입고→출고 추적 뷰)"""
        from ..utils.constants import tk, ttk, BOTH, X, Y, LEFT, RIGHT, YES, W, VERTICAL
        from ..utils.ui_constants import ThemeColors, CustomMessageBox
        
        selection = self.tree_inventory.selection()
        if not selection:
            return
        
        values = self.tree_inventory.item(selection[0], 'values')
        if not values:
            return
        lot_no = str(values[1])
        
        try:
            lot = self.engine.get_lot_detail(lot_no)
            if lot.get('error'):
                CustomMessageBox.showwarning(self.root, "경고", f"LOT 조회 실패: {lot.get('error')}")
                return
        except (ValueError, TypeError, AttributeError) as e:
            CustomMessageBox.showwarning(self.root, "경고", f"LOT 조회 오류: {e}")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"📅 LOT 히스토리 — {lot_no}")
        dialog.geometry("750x580")
        dialog.transient(self.root)
        dialog.grab_set()
        
        _is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'flatly'))
        _bg = '#1e1e1e' if _is_dark else ThemeColors.get('bg_card')
        _fg = '#e0e0e0' if _is_dark else ThemeColors.get('text_primary')
        _accent = ThemeColors.get('statusbar_progress')
        _green = ThemeColors.get('badge_db')
        _orange = '#e67e22'
        _red = ThemeColors.get('statusbar_icon_err')
        
        dialog.configure(bg=_bg)
        
        # 헤더
        header = tk.Frame(dialog, bg=_accent, pady=10)
        header.pack(fill=X)
        tk.Label(header, text="📅 LOT 히스토리 타임라인",
                 bg=_accent, fg='white', font=('맑은 고딕', 14, 'bold')).pack()
        tk.Label(header, text=f"LOT: {lot_no} | SAP: {lot.get('sap_no', '')} | {lot.get('product', '')}",
                 bg=_accent, fg='white', font=('맑은 고딕', 10)).pack()
        
        # 타임라인
        canvas_frame = tk.Frame(dialog, bg=_bg)
        canvas_frame.pack(fill=BOTH, expand=YES, padx=10, pady=5)
        
        canvas = tk.Canvas(canvas_frame, bg=_bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=VERTICAL, command=canvas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=YES)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        inner = tk.Frame(canvas, bg=_bg)
        canvas.create_window((0, 0), window=inner, anchor='nw')
        
        events = []
        
        if lot.get('ship_date'):
            events.append(('🚢', lot['ship_date'], '선적 (Ship)',
                          f"선박: {lot.get('vessel', '')} | BL: {lot.get('bl_no', '')}", _accent))
        
        if lot.get('arrival_date'):
            events.append(('📥', lot['arrival_date'], '입항/입고 (Arrival)',
                          f"창고: {lot.get('warehouse', '')} | NET: {float(lot.get('net_weight', 0) or 0):,.0f}kg | MXBG: {lot.get('mxbg_pallet', '')}",
                          _green))
        
        if lot.get('free_time') and lot.get('arrival_date'):
            try:
                from datetime import datetime, timedelta
                arr = datetime.strptime(lot['arrival_date'], '%Y-%m-%d')
                ft_days = int(lot['free_time'])
                ft_date = (arr + timedelta(days=ft_days)).strftime('%Y-%m-%d')
                events.append(('⏰', ft_date, f'Free Time 만료 ({ft_days}일)',
                              f"컨테이너: {lot.get('container_no', '')}", _orange))
            except (ValueError, TypeError) as _e:
                logger.debug(f'Suppressed (ValueError, TypeError): {_e}')
        
        tonbags = lot.get('tonbags', [])
        for tb in tonbags:
            if tb.get('picked_date'):
                events.append(('📤', tb['picked_date'],
                              f"톤백 #{tb.get('sub_lt', '?')} 출고 (PICKED)",
                              f"출고처: {tb.get('picked_to', '')} | {float(tb.get('weight', 0) or 0):,.1f}kg",
                              _orange))
            if tb.get('outbound_date'):
                events.append(('✅', tb['outbound_date'],
                              f"톤백 #{tb.get('sub_lt', '?')} 확정 (SHIPPED)",
                              "최종 출고 확정", _green))
        
        status = lot.get('status', 'AVAILABLE')
        status_colors = {'AVAILABLE': _green, 'PICKED': _orange,
                        'DEPLETED': _red, 'SHIPPED': _accent}
        events.append(('📌', '현재', f'현재 상태: {status}',
                       f"잔량: {float(lot.get('current_weight', 0) or 0):,.0f}kg / {float(lot.get('initial_weight', 0) or 0):,.0f}kg",
                       status_colors.get(status, _fg)))
        
        events.sort(key=lambda x: x[1] if x[1] != '현재' else 'zzzz')
        
        for idx, (icon, date, title, detail, color) in enumerate(events):
            row = tk.Frame(inner, bg=_bg, pady=8)
            row.pack(fill=X, padx=10)
            
            tk.Label(row, text=date, bg=_bg, fg=color,
                     font=('맑은 고딕', 10, 'bold'), width=12, anchor='e').pack(side=LEFT, padx=(0, 10))
            
            dot = tk.Canvas(row, width=20, height=20, bg=_bg, highlightthickness=0)
            dot.create_oval(4, 4, 16, 16, fill=color, outline=color)
            dot.pack(side=LEFT, padx=5)
            
            content = tk.Frame(row, bg=_bg)
            content.pack(side=LEFT, fill=X, expand=YES)
            tk.Label(content, text=f"{icon} {title}", bg=_bg, fg=_fg,
                     font=('맑은 고딕', 11, 'bold'), anchor=W).pack(anchor=W)
            tk.Label(content, text=detail, bg=_bg, fg='gray',
                     font=('맑은 고딕', 9), anchor=W).pack(anchor=W)
            
            if idx < len(events) - 1:
                tk.Frame(inner, bg=color, height=1).pack(fill=X, padx=50)
        
        # 진행률
        pf = tk.Frame(dialog, bg=_bg, pady=10)
        pf.pack(fill=X, padx=20)
        
        init_w = float(lot.get('initial_weight', 0) or 0)
        curr_w = float(lot.get('current_weight', 0) or 0)
        pct = ((init_w - curr_w) / init_w * 100) if init_w > 0 else 0
        
        tk.Label(pf, text=f"출고 진행률: {pct:.1f}%", bg=_bg, fg=_fg,
                 font=('맑은 고딕', 11, 'bold')).pack(anchor=W)
        
        bar = tk.Canvas(pf, height=20, bg=ThemeColors.get('chart_grid'), highlightthickness=0)
        bar.pack(fill=X, pady=5)
        bar.update_idletasks()
        bw = bar.winfo_width() or 700
        fill_w = max(int(bw * pct / 100), 0)
        bar_c = _green if pct < 50 else (_orange if pct < 90 else _red)
        bar.create_rectangle(0, 0, fill_w, 20, fill=bar_c, outline='')
        
        tk.Label(pf, text=f"입고: {init_w:,.0f}kg | 출고: {init_w-curr_w:,.0f}kg | 잔량: {curr_w:,.0f}kg",
                 bg=_bg, fg='gray', font=('맑은 고딕', 9)).pack(anchor=W)
        
        ttk.Button(dialog, text="닫기", command=dialog.destroy).pack(pady=10)
        
        inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox('all'))
        dialog.bind('<Escape>', lambda e: dialog.destroy())
