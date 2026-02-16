# -*- coding: utf-8 -*-
"""
SQM Inventory - Status Import Handlers
======================================

v2.9.91 - Extracted from gui_app.py

Import outbound status and location mapping from Excel
"""

import os
import logging
from ..utils.ui_constants import CustomMessageBox
from datetime import date, datetime

logger = logging.getLogger(__name__)


class StatusImportHandlersMixin:
    """
    Status import handlers mixin
    
    Mixed into SQMInventoryApp class
    """
    
    def _import_outbound_excel(self) -> None:
        """Import outbound status from Excel (tonbag level)"""
        from ..utils.constants import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Select Outbound Status Excel",
            filetypes=[("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        self._set_status("Loading outbound status...")
        self._log(f"Outbound Excel: {os.path.basename(file_path)}")
        
        try:
            import pandas as pd
            
            # Check sheets
            xls = pd.ExcelFile(file_path)
            if 'outbound' in [s.lower() for s in xls.sheet_names]:
                df = pd.read_excel(file_path, sheet_name='outbound')
            else:
                df = pd.read_excel(file_path, sheet_name=0)
            
            self._log(f"  -> {len(df)} rows loaded")
            
            # Normalize column names
            df.columns = [str(c).strip().upper().replace(' ', '_') for c in df.columns]
            
            # Column mapping
            col_map = {
                'LOT_NO': ['LOT_NO', 'LOTNO', 'LOT', 'LOT_NUMBER'],
                'SUB_LT': ['SUB_LT', 'SUBLT', 'SUB_LOT', 'SUBLOT', 'TONBAG_NO', 'TONBAG'],
                'CUSTOMER': ['CUSTOMER', 'PICKED_TO', 'SOLD_TO', 'SOLD', 'BUYER'],
                'OUTBOUND_DATE': ['OUTBOUND_DATE', 'OUTBOUNDDATE', 'PICK_DATE', 'PICKED_DATE', 'SOLD_DATE', 'DATE'],
                'SALE_REF': ['SALE_REF', 'SALEREF', 'PICK_REF', 'SALE_REFERENCE'],
            }
            
            def find_col(candidates):
                for c in candidates:
                    if c in df.columns:
                        return c
                return None
            
            # Required columns
            lot_col = find_col(col_map['LOT_NO'])
            sub_col = find_col(col_map['SUB_LT'])
            
            if not lot_col or not sub_col:
                missing = []
                if not lot_col:
                    missing.append("LOT NO")
                if not sub_col:
                    missing.append("SUB LT (Tonbag No)")
                CustomMessageBox.showerror(self.root, "Error", f"Required columns missing: {missing}")
                return
            
            # Optional columns
            customer_col = find_col(col_map['CUSTOMER'])
            date_col = find_col(col_map['OUTBOUND_DATE'])
            ref_col = find_col(col_map['SALE_REF'])
            
            # Process data
            updated = 0
            not_found = 0
            already_picked = 0
            
            with self.engine.db.transaction():
                for idx, row in df.iterrows():
                    lot_no = str(row.get(lot_col, ''))
                    if not lot_no or lot_no == 'nan':
                        continue
                    
                    # Clean LOT number
                    if '.' in lot_no:
                        lot_no = lot_no.split('.')[0]
                    
                    tonbag_no = self._safe_int(row.get(sub_col, 0))
                    customer = str(row.get(customer_col, '')) if customer_col and pd.notna(row.get(customer_col)) else ''
                    sale_ref = str(row.get(ref_col, '')) if ref_col and pd.notna(row.get(ref_col)) else ''
                    outbound_date = self._safe_date(row.get(date_col)) if date_col else date.today()
                    
                    # Check tonbag exists
                    existing = self.engine.db.fetchone(
                        "SELECT id, status FROM inventory_tonbag WHERE lot_no=? AND sub_lt=?",
                        (lot_no, tonbag_no)
                    )
                    
                    if not existing:
                        not_found += 1
                        continue
                    
                    if existing['status'] == 'PICKED':
                        already_picked += 1
                        continue
                    
                    # Update to picked
                    self.engine.db.execute("""
                        UPDATE inventory_tonbag SET
                            status = 'PICKED',
                            picked_to = ?,
                            pick_ref = ?,
                            outbound_date = ?,
                            picked_date = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE lot_no = ? AND sub_lt = ?
                    """, (customer, sale_ref, outbound_date, outbound_date, lot_no, tonbag_no))
                    updated += 1
            
            self._log(f"OK Outbound: {updated} processed, {not_found} not found, {already_picked} already picked")
            
            # Generate report
            report_path = None
            if updated > 0:
                try:
                    report_path = self._generate_outbound_report(file_path, updated)
                    self._log(f"Report: {report_path}")
                except (ValueError, TypeError, AttributeError) as e:
                    self._log(f"WARNING Report generation failed: {e}")
            
            msg = (f"Outbound Status Import Complete\n\n"
                   f"• Processed: {updated}\n"
                   f"• Not Found: {not_found}\n"
                   f"• Already Picked: {already_picked}")
            
            if report_path:
                msg += f"\n\nReport: {os.path.basename(report_path)}"
                if CustomMessageBox.askyesno(self.root, "Complete", msg + "\n\nOpen report?"):
                    self._open_file(report_path)
            else:
                CustomMessageBox.showinfo(self.root, "Complete", msg)
            
            self._refresh_inventory()
            self._refresh_tonbag()
            
        except (OSError, IOError, PermissionError) as e:
            self._log(f"X Outbound import error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Outbound import failed:\n{e}")
        
        self._set_status("Ready")
    
    def _import_location_excel(self) -> None:
        """Import location mapping from Excel"""
        from ..utils.constants import filedialog
        import re
        
        file_path = filedialog.askopenfilename(
            title="Select Location Mapping Excel",
            filetypes=[("Excel files", "*.xlsx;*.xls;*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        self._set_status("Loading location data...")
        self._log(f"Location Excel: {os.path.basename(file_path)}")
        
        try:
            import pandas as pd
            
            # Read file
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, sheet_name=0)
            
            self._log(f"  -> {len(df)} rows loaded")
            
            # Normalize column names
            df.columns = [str(c).strip().upper().replace(' ', '_') for c in df.columns]
            
            # Column mapping
            col_map = {
                'LOT_NO': ['LOT_NO', 'LOTNO', 'LOT'],
                'SUB_LT': ['SUB_LT', 'SUBLT', 'SUB_LOT', 'SUBLOT', 'TONBAG_NO', 'TONBAG'],
                'LOCATION': ['LOCATION', 'LOC', 'WAREHOUSE_LOCATION', 'POSITION'],
            }
            
            def find_col(candidates):
                for c in candidates:
                    c_norm = c.upper().replace(' ', '_')
                    if c_norm in df.columns:
                        return c_norm
                return None
            
            # Required columns
            lot_col = find_col(col_map['LOT_NO'])
            sub_col = find_col(col_map['SUB_LT'])
            loc_col = find_col(col_map['LOCATION'])
            
            if not lot_col or not sub_col or not loc_col:
                missing = []
                if not lot_col:
                    missing.append("LOT NO")
                if not sub_col:
                    missing.append("SUB LT")
                if not loc_col:
                    missing.append("LOCATION")
                CustomMessageBox.showerror(self.root, "Error", f"Required columns missing: {missing}")
                return
            
            # Process data
            updated = 0
            skipped = 0
            not_found = []
            
            with self.engine.db.transaction():
                for idx, row in df.iterrows():
                    # LOT NO
                    lot_raw = row.get(lot_col)
                    if pd.isna(lot_raw):
                        skipped += 1
                        continue
                    
                    if isinstance(lot_raw, (int, float)):
                        lot_no = str(int(lot_raw))
                    else:
                        lot_no = str(lot_raw).strip().split('.')[0]
                    
                    if not lot_no or len(lot_no) != 10:
                        skipped += 1
                        continue
                    
                    # SUB LT
                    sub_raw = row.get(sub_col)
                    if pd.isna(sub_raw):
                        skipped += 1
                        continue
                    
                    try:
                        sub_lt = int(float(sub_raw))
                    except (ValueError, TypeError):
                        skipped += 1
                        continue
                    
                    # LOCATION
                    loc_raw = row.get(loc_col)
                    if pd.isna(loc_raw):
                        skipped += 1
                        continue
                    
                    location = str(loc_raw).strip().upper()
                    
                    # Validate location format (G5-01-02-03 or similar)
                    if not re.match(r'^G[56]-\d{2}-\d{2}-\d{2}$', location):
                        self._log(f"WARNING Invalid location format: {location}")
                        # Still save even if format doesn't match
                    
                    # Update tonbag
                    existing = self.engine.db.fetchone(
                        "SELECT id FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
                        (lot_no, sub_lt)
                    )
                    
                    if existing:
                        self.engine.db.execute(
                            "UPDATE inventory_tonbag SET location = ? WHERE lot_no = ? AND sub_lt = ?",
                            (location, lot_no, sub_lt)
                        )
                        updated += 1
                    else:
                        not_found.append(f"{lot_no}-{sub_lt}")
            
            # Result message
            msg = f"Location Update Complete\n\nUpdated: {updated}\nSkipped: {skipped}"
            
            if not_found:
                msg += f"\n\nNot Found ({len(not_found)}):\n"
                msg += "\n".join(not_found[:10])
                if len(not_found) > 10:
                    msg += f"\n... and {len(not_found) - 10} more"
            
            self._log(f"OK Location: {updated} updated, {skipped} skipped, {len(not_found)} not found")
            CustomMessageBox.showinfo(self.root, "Location Update Complete", msg)
            
            self._refresh_inventory()
            self._refresh_tonbag()
            
        except (RuntimeError, ValueError) as e:
            self._log(f"X Location import error: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox.showerror(self.root, "Error", f"Location import failed:\n{e}")
        
        self._set_status("Ready")
    
    def _generate_outbound_report(self, source_file: str, count: int) -> str:
        """Generate outbound report after import"""
        import pandas as pd
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = f"output/outbound_report_{timestamp}.xlsx"
        os.makedirs("output", exist_ok=True)
        
        # Get recent outbound tonbags
        recent = self.engine.db.fetchall("""
            SELECT
                t.sap_no as SAP_NO, t.bl_no as BL_NO, t.lot_no as LOT_NO,
                t.sub_lt as Tonbag, t.weight as Weight_kg,
                t.outbound_date as Outbound_Date, t.picked_to as Customer,
                t.pick_ref as Sale_Ref
            FROM inventory_tonbag t
            WHERE t.status = 'PICKED'
            ORDER BY t.updated_at DESC
            LIMIT ?
        """, (count + 50,))
        
        # Summary
        summary_data = {
            'Item': ['Source File', 'Process Time', 'Processed Count'],
            'Value': [os.path.basename(source_file), 
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                     str(count)]
        }
        
        with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            if recent:
                pd.DataFrame(recent).to_excel(writer, sheet_name='Outbound Details', index=False)
        
        return report_path
    
    def _generate_inbound_report(self, source_file: str, lot_count: int, tonbag_count: int) -> str:
        """Generate inbound report after import"""
        import pandas as pd
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = f"output/inbound_report_{timestamp}.xlsx"
        os.makedirs("output", exist_ok=True)
        
        # Get recent tonbags
        recent_tonbags = self.engine.db.fetchall("""
            SELECT
                t.sap_no as SAP_NO, t.bl_no as BL_NO, t.lot_no as LOT_NO,
                t.sub_lt as Tonbag, t.weight as Weight_kg,
                t.inbound_date as Inbound_Date, t.location as Location,
                i.product_code as Product, i.container_no as Container
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON t.lot_no = i.lot_no
            WHERE t.status = 'AVAILABLE'
            ORDER BY t.created_at DESC
            LIMIT ?
        """, (tonbag_count + 100,))
        
        # LOT summary
        lot_summary = self.engine.db.fetchall("""
            SELECT
                lot_no as LOT_NO, product_code as Product, sap_no as SAP_NO,
                COUNT(*) as Tonbags,
                ROUND(initial_weight, 1) as Initial_kg,
                ROUND(current_weight, 1) as Current_kg,
                inbound_date as Inbound_Date, status as Status
            FROM inventory
            WHERE status = 'AVAILABLE'
            GROUP BY lot_no
            ORDER BY inbound_date DESC, lot_no
            LIMIT ?
        """, (lot_count + 50,))
        
        # Summary
        summary_data = {
            'Item': ['Source File', 'Process Time', 'LOT Count', 'Tonbag Count'],
            'Value': [os.path.basename(source_file),
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                     str(lot_count),
                     str(tonbag_count)]
        }
        
        with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            if lot_summary:
                pd.DataFrame(lot_summary).to_excel(writer, sheet_name='LOT Summary', index=False)
            
            if recent_tonbags:
                pd.DataFrame(recent_tonbags).to_excel(writer, sheet_name='Tonbag Details', index=False)
        
        return report_path
    
    def _safe_int(self, val, default: int = 0) -> int:
        """Safe integer conversion"""
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default
    
    def _safe_date(self, val) -> date:
        """Safe date conversion"""
        import pandas as pd
        
        if pd.isna(val):
            return date.today()
        if isinstance(val, str):
            try:
                return datetime.strptime(val, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return date.today()
        if hasattr(val, 'date'):
            return val.date()
        return date.today()
    
    def _open_file_in_explorer(self, file_path: str) -> None:
        """Open file with system default application"""
        import subprocess
        import platform
        
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', file_path])
            else:  # Linux
                subprocess.call(['xdg-open', file_path])
        except (FileNotFoundError, OSError, PermissionError) as e:
            self._log(f"WARNING Could not open file: {e}")
