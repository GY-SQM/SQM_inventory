# -*- coding: utf-8 -*-
"""
SQM Inventory - Export Handlers
===============================

v2.9.91 - Extracted from gui_app.py

Excel export functions
"""

import os
import logging
from ..utils.ui_constants import CustomMessageBox
import subprocess
import platform
from datetime import date

logger = logging.getLogger(__name__)


class ExportHandlersMixin:
    """
    Export handlers mixin
    
    Mixed into SQMInventoryApp class
    """
    
    def _on_export_click(self, option: int = 1) -> None:
        """
        Export button click
        
        Args:
            option: Export format
                1 = Customs format
                3 = Ruby format (18 columns)
                4 = Sub LOT format
                5 = LOT format
                6 = Combined format (LOT + Tonbag)
                7 = Detailed inventory
        """
        from ..utils.constants import filedialog
        
        today_str = date.today().strftime('%Y_%m_%d')
        
        # File names by option
        option_config = {
            1: ("SQM-Customs-{}.xlsx", "Customs"),
            3: ("SQM-Inventory-{}.xlsx", "Inventory (Ruby)"),
            4: ("SQM-SubLOT-{}.xlsx", "Sub LOT"),
            5: ("SQM-LOT-{}.xlsx", "LOT"),
            6: ("SQM-Combined-{}.xlsx", "Combined (LOT+Tonbag)"),
            7: ("SQM-DetailedInventory-{}.xlsx", "Detailed Inventory"),
        }
        
        file_template, option_name = option_config.get(option, option_config[1])
        default_name = file_template.format(today_str)
        
        file_path = filedialog.asksaveasfilename(
            title=f"Save Location ({option_name})",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        # Start task
        self._start_task("Excel Export", f"Exporting... ({option_name})")
        self._log(f"Excel export [{option_name}]: {os.path.basename(file_path)}")
        
        try:
            self._log("Loading data...")
            self._log("Creating Excel...")
            
            self.engine.export_to_excel(file_path, option=option)
            
            self._end_task(True, f"OK Export complete: {os.path.basename(file_path)}")
            self._log(f"OK Export complete: {file_path}")
            
            # Option-specific message
            messages = {
                3: "Export complete (Ruby format)\n\n18 columns",
                4: "Export complete (Sub LOT)\n\nTonbag level details",
                6: "Export complete (Combined)\n\nLOT + Tonbag combined",
                7: "Export complete (Detailed)\n\nAll tonbag details (14 columns)",
            }
            msg = messages.get(option, "Export complete")
            
            if CustomMessageBox.askyesno(self.root, "Complete", f"{msg}\n\nOpen file?"):
                self._open_file(file_path)
                
        except (OSError, IOError, PermissionError) as e:
            self._end_task(False, f"Export failed: {str(e)[:50]}...")
            self._log(f"X Export failed: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Export failed\n{e}")
    
    def _open_file(self, file_path: str) -> None:
        """Open file with default application"""

        
        try:
            system = platform.system()
            if system == 'Windows':
                os.startfile(file_path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', file_path], check=True)
            else:  # Linux
                subprocess.run(['xdg-open', file_path], check=True)
            self._log(f"File opened: {os.path.basename(file_path)}")
        except (OSError, IOError, PermissionError) as e:
            self._log(f"WARNING Failed to open file: {e}")
            CustomMessageBox.showwarning(self.root, "Open Failed", f"Cannot open file.\n\n{file_path}")
    
    def _export_tonbag_list(self) -> None:
        """Export tonbag list to Excel"""
        from ..utils.constants import pd, HAS_PANDAS, filedialog
        
        if not HAS_PANDAS:
            CustomMessageBox.showerror(self.root, "Error", "pandas not installed")
            return
        
        try:
            # Get tonbag data
            tonbags = self.engine.get_all_tonbags()
            
            if not tonbags:
                CustomMessageBox.showwarning(self.root, "Warning", "No tonbag data")
                return
            
            # Select save path
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialfile=f"tonbag_list_{len(tonbags)}.xlsx"
            )
            
            if not file_path:
                return
            
            # Create DataFrame
            df = pd.DataFrame(tonbags)
            df.to_excel(file_path, index=False)
            
            self._log(f"Tonbag list exported: {file_path}")
            CustomMessageBox.showinfo(self.root, "Complete", 
                f"Tonbag list exported.\n\n"
                f"Records: {len(tonbags)}\n"
                f"File: {file_path}")
            
            if CustomMessageBox.askyesno(self.root, "Open", "Open file?"):
                self._open_file(file_path)
            
        except (RuntimeError, ValueError) as e:
            logger.error(f"Tonbag export error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Export failed: {e}")
