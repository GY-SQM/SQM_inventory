# -*- coding: utf-8 -*-
"""
SQM Inventory - Summary Tab
===========================

v3.6.0 - UI 통일성 적용
- 간격 표준화 (Spacing)
- 컬럼 너비 표준화 (ColumnWidth)
- 폰트 스케일링 (FontScale)
"""

import logging

from ..utils.ui_constants import CustomMessageBox, FontScale
logger = logging.getLogger(__name__)


class SummaryTabMixin:
    """
    Summary tab mixin
    
    Mixed into SQMInventoryApp class
    """
    
    def _refresh_summary(self) -> None:
        """Refresh summary tab data"""
        from ..utils.constants import END
        
        try:
            # Guard: 위젯이 아직 생성 안 됐으면 skip
            if not hasattr(self, 'lbl_total_lots'):
                return
            
            # Get summary data from engine
            summary = self.engine.get_inventory_summary()
            
            if not summary:
                return
            
            # Update overall labels
            self.lbl_total_lots.config(text=f"Total LOTs: {summary.get('total_lots', 0)}")
            self.lbl_total_qty.config(text=f"Total Inbound: {summary.get('total_initial_mt', 0):.3f} MT")
            self.lbl_total_balance.config(text=f"Current Balance: {summary.get('total_current_mt', 0):.3f} MT")
            self.lbl_total_picked.config(text=f"Total Outbound: {summary.get('total_picked_mt', 0):.3f} MT")
            self.lbl_available.config(text=f"Available LOTs: {summary.get('available_lots', 0)}")
            self.lbl_depleted.config(text=f"Depleted LOTs: {summary.get('depleted_lots', 0)}")
            
            # Refresh product summary
            self.tree_product.delete(*self.tree_product.get_children())
            
            # v4.19.1: 줄무늬 배경 적용
            for i, product in enumerate(summary.get('by_product', [])):
                tag = 'odd' if i % 2 else 'even'
                self.tree_product.insert('', END, values=(
                    product.get('product', ''),
                    product.get('lot_count', 0),
                    f"{product.get('initial_mt', 0):.3f}",
                    f"{product.get('current_mt', 0):.3f}",
                    f"{product.get('picked_mt', 0):.3f}",
                ), tags=(tag,))
            
            # Refresh customer summary
            self.tree_customer.delete(*self.tree_customer.get_children())
            
            # v4.19.1: 줄무늬 배경 적용
            idx = 0
            for customer in summary.get('by_customer', []):
                if customer.get('customer'):  # Skip empty customers
                    tag = 'odd' if idx % 2 else 'even'
                    self.tree_customer.insert('', END, values=(
                        customer.get('customer', ''),
                        customer.get('lot_count', 0),
                        f"{customer.get('picked_mt', 0):.3f}",
                    ), tags=(tag,))
                    idx += 1
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"Summary refresh error: {e}")
            self._log(f"X Summary refresh error: {e}")
    
    def _generate_summary_report(self) -> None:
        """Generate summary report"""
        from ..utils.constants import filedialog
        
        output_path = filedialog.asksaveasfilename(
            title="Save Summary Report",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="inventory_summary_report.xlsx"
        )
        
        if not output_path:
            return
        
        self._set_status("Generating summary report...")
        self._log("Generating summary report...")
        
        try:
            summary = self.engine.get_inventory_summary()
            
            import pandas as pd
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Overall summary
                overall_df = pd.DataFrame([{
                    'Total LOTs': summary.get('total_lots', 0),
                    'Total Inbound (MT)': summary.get('total_initial_mt', 0),
                    'Current Balance (MT)': summary.get('total_current_mt', 0),
                    'Total Outbound (MT)': summary.get('total_picked_mt', 0),
                    'Available LOTs': summary.get('available_lots', 0),
                    'Depleted LOTs': summary.get('depleted_lots', 0),
                }])
                overall_df.to_excel(writer, sheet_name='Overall', index=False)
                
                # By product
                product_df = pd.DataFrame(summary.get('by_product', []))
                if not product_df.empty:
                    product_df.to_excel(writer, sheet_name='By Product', index=False)
                
                # By customer
                customer_df = pd.DataFrame(summary.get('by_customer', []))
                if not customer_df.empty:
                    customer_df.to_excel(writer, sheet_name='By Customer', index=False)
            
            self._log(f"OK Summary report generated: {output_path}")
            
            if CustomMessageBox.askyesno(self.root, "Report Complete",
                f"Summary report generated!\n\n{output_path}\n\nOpen file?"):
                import os
                os.startfile(output_path)
                
        except (RuntimeError, ValueError) as e:
            self._log(f"X Report error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Report generation failed:\n{e}")
        
        self._set_status("Ready")
    
    def _show_inventory_chart(self) -> None:
        """Show inventory chart (if matplotlib available)"""

        
        try:
            import matplotlib.pyplot as plt
            
            summary = self.engine.get_inventory_summary()
            
            if not summary.get('by_product'):
                CustomMessageBox.showinfo(self.root, "Info", "No data for chart")
                return
            
            # Create chart
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            # By product - bar chart
            products = [p['product'] for p in summary['by_product']]
            current_mt = [p['current_mt'] for p in summary['by_product']]
            
            ax1.barh(products, current_mt, color='steelblue')
            ax1.set_xlabel('Balance (MT)')
            ax1.set_title('Inventory by Product')
            
            # Status - pie chart
            labels = ['Available', 'Depleted']
            sizes = [summary.get('available_lots', 0), summary.get('depleted_lots', 0)]
            colors = ['#2ecc71', '#e74c3c']
            
            ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax2.set_title('LOT Status')
            
            plt.tight_layout()
            plt.show()
            
        except ImportError:
            CustomMessageBox.showwarning(self.root, "Warning", "matplotlib not installed")
        except (AttributeError, RuntimeError) as e:
            CustomMessageBox.showerror(self.root, "Error", f"Chart error: {e}")
