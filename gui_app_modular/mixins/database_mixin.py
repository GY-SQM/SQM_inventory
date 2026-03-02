"""
SQM Inventory - Database Mixin
==============================

v2.9.91 - Extracted from gui_app.py

Database operations, connection management, and diagnostics
"""

import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

from ..utils.ui_constants import CustomMessageBox

logger = logging.getLogger(__name__)


class DatabaseMixin:
    """
    Database operations mixin
    
    Mixed into SQMInventoryApp class
    """

    def _init_database(self, db_path: Optional[str] = None) -> None:
        """Initialize database connection"""


        if db_path:
            self.db_path = db_path
        else:
            # Default path
            self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data", "db", "sqm_inventory.db"
            )

        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        try:
            from engine_modules.inventory import InventoryEngine
            self.engine = InventoryEngine(db_path=self.db_path)
            self._log(f"OK Database connected: {self.db_path}")

        except ImportError:
            try:
                from engine import Engine
                self.engine = Engine(db_path=self.db_path)
                self._log("OK Database connected (legacy engine)")
            except ImportError:
                CustomMessageBox.showerror(self.root, "Error", "Database engine not found")
                self.engine = None
        except (sqlite3.Error, OSError) as e:
            CustomMessageBox.showerror(self.root, "Database Error", f"Failed to connect:\n{e}")
            self.engine = None

    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        result = {
            'status': 'unknown',
            'size_mb': 0,
            'tables': [],
            'lot_count': 0,
            'tonbag_count': 0,
            'errors': []
        }

        if not self.engine:
            result['status'] = 'error'
            result['errors'].append('No database connection')
            return result

        try:
            # Check file size
            if os.path.exists(self.db_path):
                result['size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)

            # Check tables
            tables = self.engine.db.fetchall(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            result['tables'] = [t['name'] for t in tables]

            # Count records
            lot_count = self.engine.db.fetchone("SELECT COUNT(*) as cnt FROM inventory")
            result['lot_count'] = lot_count['cnt'] if lot_count else 0

            tonbag_count = self.engine.db.fetchone("SELECT COUNT(*) as cnt FROM inventory_tonbag")
            result['tonbag_count'] = tonbag_count['cnt'] if tonbag_count else 0

            # Check integrity
            integrity = self.engine.db.fetchone("PRAGMA integrity_check")
            if integrity and integrity.get('integrity_check') == 'ok':
                result['status'] = 'healthy'
            else:
                result['status'] = 'warning'
                result['errors'].append('Integrity check failed')

        except (sqlite3.Error, OSError) as e:
            result['status'] = 'error'
            result['errors'].append(str(e))

        return result

    def _optimize_database(self) -> None:
        """Optimize database (VACUUM)"""


        if not self.engine:
            CustomMessageBox.showerror(self.root, "Error", "No database connection")
            return

        if not CustomMessageBox.askyesno(self.root, "Optimize Database",
            "This will optimize the database.\n\n"
            "The application may be unresponsive briefly.\n\n"
            "Continue?"):
            return

        self._set_status("Optimizing database...")
        self._log("Starting database optimization...")

        try:
            # Get size before
            size_before = os.path.getsize(self.db_path) / (1024 * 1024)

            # VACUUM
            self.engine.db.execute("VACUUM")

            # Analyze
            self.engine.db.execute("ANALYZE")

            # Get size after
            size_after = os.path.getsize(self.db_path) / (1024 * 1024)

            saved = size_before - size_after

            self._log(f"OK Database optimized: {size_before:.2f} MB -> {size_after:.2f} MB (saved {saved:.2f} MB)")
            CustomMessageBox.showinfo(self.root, "Optimization Complete",
                f"Database optimized!\n\n"
                f"Before: {size_before:.2f} MB\n"
                f"After: {size_after:.2f} MB\n"
                f"Saved: {saved:.2f} MB")

        except (sqlite3.Error, OSError) as e:
            self._log(f"X Optimization error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Optimization failed:\n{e}")

        self._set_status("Ready")

    def _repair_database(self) -> None:
        """Attempt to repair database"""


        if not CustomMessageBox.askyesno(self.root, "Repair Database",
            "This will attempt to repair the database.\n\n"
            "A backup will be created first.\n\n"
            "Continue?"):
            return

        self._set_status("Repairing database...")
        self._log("Starting database repair...")

        try:
            # Backup first
            backup_path = self.db_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(self.db_path, backup_path)
            self._log(f"Backup created: {backup_path}")

            # Integrity check
            self.engine.db.execute("PRAGMA integrity_check")

            # Reindex
            self.engine.db.execute("REINDEX")

            # Vacuum
            self.engine.db.execute("VACUUM")

            self._log("OK Database repair completed")
            CustomMessageBox.showinfo(self.root, "Repair Complete", "Database repair completed!")

        except (sqlite3.Error, OSError) as e:
            self._log(f"X Repair error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Repair failed:\n{e}\n\nBackup: {backup_path}")

        self._set_status("Ready")

    def _export_database(self) -> None:
        """Export entire database to SQL"""
        from ..utils.constants import filedialog

        output_path = filedialog.asksaveasfilename(
            title="Export Database",
            defaultextension=".sql",
            filetypes=[("SQL files", "*.sql"), ("All files", "*.*")],
            initialfile=f"sqm_inventory_export_{datetime.now().strftime('%Y%m%d')}.sql"
        )

        if not output_path:
            return

        self._set_status("Exporting database...")
        self._log(f"Exporting database to: {output_path}")

        try:
            import sqlite3

            # v3.6.2: with 문으로 connection 누수 방지
            with sqlite3.connect(self.db_path) as conn:
                with open(output_path, 'w', encoding='utf-8') as f:
                    for line in conn.iterdump():
                        f.write(f"{line}\n")

            size = os.path.getsize(output_path) / 1024
            self._log(f"OK Database exported: {size:.1f} KB")

            if CustomMessageBox.askyesno(self.root, "Export Complete",
                f"Database exported!\n\n{output_path}\n\nOpen file location?"):
                import subprocess
                subprocess.Popen(f'explorer /select,"{output_path}"')

        except (sqlite3.Error, OSError) as e:
            self._log(f"X Export error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Export failed:\n{e}")

        self._set_status("Ready")
