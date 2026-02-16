# -*- coding: utf-8 -*-
"""
SQM Inventory - PDF Processing Handlers
=======================================

v2.9.91 - Extracted from gui_app.py

PDF conversion, analysis, and report generation
"""

import os
import logging
from ..utils.ui_constants import CustomMessageBox, apply_tooltip
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFHandlersMixin:
    """
    PDF processing handlers mixin
    
    Mixed into SQMInventoryApp class
    """
    
    def _convert_pdf_to_excel(self) -> None:
        """Convert PDF to Excel"""
        from ..utils.constants import filedialog
        
        pdf_path = filedialog.askopenfilename(
            title="Select PDF to Convert",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if not pdf_path:
            return
        
        self._set_status("Converting PDF to Excel...")
        self._log(f"PDF conversion started: {os.path.basename(pdf_path)}")
        
        try:
            from utils.pdf_converter import PDFConverter
            
            converter = PDFConverter()
            result = converter.to_excel(pdf_path)
            
            if result.success:
                self._log(f"OK Excel conversion complete: {result.output_file}")
                self._log(f"   Pages: {result.page_count}, Tables: {result.table_count}")
                self._log(f"   Time: {result.processing_time:.1f}s")
                
                if CustomMessageBox.askyesno(self.root, "Conversion Complete",
                    f"Excel conversion complete!\n\n"
                    f"File: {os.path.basename(result.output_file)}\n"
                    f"Pages: {result.page_count}\n"
                    f"Tables: {result.table_count}\n\n"
                    f"Open file?"):
                    os.startfile(result.output_file)
            else:
                self._log(f"X Conversion failed: {result.error_message}")
                CustomMessageBox.showerror(self.root, "Conversion Failed", result.error_message)
                
        except ImportError:
            CustomMessageBox.showerror(self.root, "Error", "pdf_converter module not found")
        except (OSError, IOError, PermissionError) as e:
            self._log(f"X Conversion error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Conversion error:\n{e}")
        
        self._set_status("Ready")
    
    def _convert_pdf_to_word(self) -> None:
        """Convert PDF to Word"""
        from ..utils.constants import filedialog
        
        pdf_path = filedialog.askopenfilename(
            title="Select PDF to Convert",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if not pdf_path:
            return
        
        self._set_status("Converting PDF to Word...")
        self._log(f"PDF conversion started: {os.path.basename(pdf_path)}")
        
        try:
            from utils.pdf_converter import PDFConverter
            
            converter = PDFConverter()
            result = converter.to_word(pdf_path)
            
            if result.success:
                self._log(f"OK Word conversion complete: {result.output_file}")
                self._log(f"   Pages: {result.page_count}, Tables: {result.table_count}")
                
                if CustomMessageBox.askyesno(self.root, "Conversion Complete",
                    f"Word conversion complete!\n\n"
                    f"File: {os.path.basename(result.output_file)}\n"
                    f"Pages: {result.page_count}\n\n"
                    f"Open file?"):
                    os.startfile(result.output_file)
            else:
                self._log(f"X Conversion failed: {result.error_message}")
                CustomMessageBox.showerror(self.root, "Conversion Failed", result.error_message)
                
        except ImportError as e:
            if "python-docx" in str(e):
                CustomMessageBox.showerror(self.root, "Error", 
                    "python-docx required for Word conversion\n\n"
                    "pip install python-docx")
            else:
                CustomMessageBox.showerror(self.root, "Error", f"Module error: {e}")
        except (OSError, IOError, PermissionError) as e:
            self._log(f"X Conversion error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Conversion error:\n{e}")
        
        self._set_status("Ready")
    
    def _batch_convert_pdf_excel(self) -> None:
        """Batch convert PDFs in folder to Excel"""
        from ..utils.constants import filedialog
        
        folder_path = filedialog.askdirectory(title="Select PDF Folder")
        
        if not folder_path:
            return
        
        # Count PDF files
        pdf_files = list(Path(folder_path).glob("*.pdf")) + list(Path(folder_path).glob("*.PDF"))
        
        if not pdf_files:
            CustomMessageBox.showinfo(self.root, "No Files", "No PDF files found in folder")
            return
        
        if not CustomMessageBox.askyesno(self.root, "Batch Convert",
            f"Convert {len(pdf_files)} PDF files to Excel?"):
            return
        
        self._set_status("Batch converting...")
        self._log(f"Batch conversion started: {len(pdf_files)} files")
        
        try:
            from utils.pdf_converter import PDFConverter
            converter = PDFConverter()
            
            success_count = 0
            fail_count = 0
            
            for i, pdf_file in enumerate(pdf_files):
                self._set_status(f"Converting {i+1}/{len(pdf_files)}: {pdf_file.name}")
                
                try:
                    result = converter.to_excel(str(pdf_file))
                    if result.success:
                        success_count += 1
                        self._log(f"  OK {pdf_file.name}")
                    else:
                        fail_count += 1
                        self._log(f"  X {pdf_file.name}: {result.error_message}")
                except (ValueError, TypeError, AttributeError) as e:
                    fail_count += 1
                    self._log(f"  X {pdf_file.name}: {e}")
            
            self._log(f"Batch complete: {success_count} success, {fail_count} failed")
            CustomMessageBox.showinfo(self.root, "Batch Complete",
                f"Batch conversion complete!\n\n"
                f"Success: {success_count}\n"
                f"Failed: {fail_count}")
                
        except ImportError:
            CustomMessageBox.showerror(self.root, "Error", "pdf_converter module not found")
        except (RuntimeError, ValueError) as e:
            self._log(f"X Batch error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Batch error:\n{e}")
        
        self._set_status("Ready")
    
    def _analyze_pdf(self) -> None:
        """Analyze PDF structure"""
        from ..utils.constants import tk, ttk, filedialog, BOTH
        
        pdf_path = filedialog.askopenfilename(
            title="Select PDF to Analyze",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if not pdf_path:
            return
        
        self._set_status("Analyzing PDF...")
        self._log(f"PDF analysis: {os.path.basename(pdf_path)}")
        
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            
            try:
                # Build analysis report
                analysis = []
                analysis.append(f"File: {os.path.basename(pdf_path)}")
                analysis.append(f"Pages: {len(doc)}")
                analysis.append(f"Size: {os.path.getsize(pdf_path) / 1024:.1f} KB")
                analysis.append("")
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    analysis.append(f"=== Page {page_num + 1} ===")
                    analysis.append(f"Size: {page.rect.width:.0f} x {page.rect.height:.0f}")
                    
                    # Count images
                    images = page.get_images()
                    analysis.append(f"Images: {len(images)}")
                    
                    # Text blocks
                    blocks = page.get_text("blocks")
                    analysis.append(f"Text blocks: {len(blocks)}")
                    
                    # Tables (if tabula available)
                    try:
                        import tabula
                        tables = tabula.read_pdf(pdf_path, pages=page_num+1, silent=True)
                        analysis.append(f"Tables: {len(tables)}")
                    except (ValueError, TypeError, AttributeError) as _e:
                        logger.debug(f"Suppressed: {_e}")
                    
                    analysis.append("")
            finally:
                doc.close()  # 항상 닫기
            
            # Show result dialog
            dialog = tk.Toplevel(self.root)
            dialog.title(f"PDF Analysis - {os.path.basename(pdf_path)}")
            dialog.geometry("500x400")
            
            text = tk.Text(dialog, wrap='word')
            text.pack(fill=BOTH, expand=True, padx=10, pady=10)
            text.insert('1.0', '\n'.join(analysis))
            text.config(state='disabled')
            
            ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=5)
            
            self._log("PDF analysis complete")
            
        except ImportError:
            CustomMessageBox.showerror(self.root, "Error", 
                "PyMuPDF required for PDF analysis\n\n"
                "pip install pymupdf")
        except (RuntimeError, ValueError) as e:
            self._log(f"X Analysis error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Analysis error:\n{e}")
        
        self._set_status("Ready")
    
    def _generate_inventory_pdf(self) -> None:
        """Generate inventory report PDF"""
        from ..utils.constants import filedialog
        
        output_path = filedialog.asksaveasfilename(
            title="Save Inventory Report",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="inventory_report.pdf"
        )
        
        if not output_path:
            return
        
        self._set_status("Generating report...")
        self._log("Generating inventory PDF report...")
        
        try:
            from pdf_report import PDFReportGenerator
            
            # Get inventory data
            inventory = self.engine.get_all_inventory()
            
            generator = PDFReportGenerator()
            result = generator.generate_inventory_report(inventory, output_path)
            
            if result.get('success'):
                self._log(f"OK Report generated: {output_path}")
                if CustomMessageBox.askyesno(self.root, "Report Complete",
                    f"Inventory report generated!\n\n"
                    f"Records: {len(inventory)}\n\n"
                    f"Open file?"):
                    os.startfile(output_path)
            else:
                CustomMessageBox.showerror(self.root, "Error", result.get('error', 'Unknown error'))
                
        except ImportError:
            CustomMessageBox.showerror(self.root, "Error", "pdf_report module not found")
        except (ValueError, TypeError, AttributeError) as e:
            self._log(f"X Report error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Report error:\n{e}")
        
        self._set_status("Ready")
    
    def _generate_transaction_pdf(self) -> None:
        """Generate transaction report PDF"""
        from ..utils.constants import filedialog
        
        output_path = filedialog.asksaveasfilename(
            title="Save Transaction Report",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="transaction_report.pdf"
        )
        
        if not output_path:
            return
        
        self._set_status("Generating report...")
        self._log("Generating transaction PDF report...")
        
        try:
            from pdf_report import PDFReportGenerator
            
            # Get transaction data (inbound + outbound)
            inbound = self.engine.db.fetchall(
                "SELECT * FROM inventory ORDER BY stock_date DESC LIMIT 100"
            )
            outbound = self.engine.db.fetchall(
                "SELECT * FROM inventory_tonbag WHERE status='PICKED' ORDER BY outbound_date DESC LIMIT 100"
            )
            
            generator = PDFReportGenerator()
            result = generator.generate_transaction_report(
                {'inbound': inbound, 'outbound': outbound}, 
                output_path
            )
            
            if result.get('success'):
                self._log(f"OK Report generated: {output_path}")
                if CustomMessageBox.askyesno(self.root, "Report Complete",
                    f"Transaction report generated!\n\n"
                    f"Open file?"):
                    os.startfile(output_path)
            else:
                CustomMessageBox.showerror(self.root, "Error", result.get('error', 'Unknown error'))
                
        except ImportError:
            CustomMessageBox.showerror(self.root, "Error", "pdf_report module not found")
        except (ValueError, TypeError, AttributeError) as e:
            self._log(f"X Report error: {e}")
            CustomMessageBox.showerror(self.root, "Error", f"Report error:\n{e}")
        
        self._set_status("Ready")
    
    def _generate_invoice_pdf(self) -> None:
        """v4.1.1: 거래명세서 PDF 생성 — 고객/기간 선택 다이얼로그"""
        from ..utils.constants import tk, ttk, filedialog
        
        dialog = tk.Toplevel(self.root)
        dialog.title("📝 거래명세서 생성")
        dialog.geometry("380x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="📝 거래명세서 PDF", font=('맑은 고딕', 14, 'bold')).pack(pady=10)
        
        form = ttk.Frame(dialog, padding=10)
        form.pack(fill='x')
        
        ttk.Label(form, text="고객명 (빈칸=전체):").grid(row=0, column=0, sticky='w', pady=3)
        cust_var = tk.StringVar()
        ttk.Entry(form, textvariable=cust_var, width=25).grid(row=0, column=1, pady=3)
        
        ttk.Label(form, text="시작일 (YYYY-MM-DD):").grid(row=1, column=0, sticky='w', pady=3)
        from_var = tk.StringVar()
        ttk.Entry(form, textvariable=from_var, width=25).grid(row=1, column=1, pady=3)
        
        ttk.Label(form, text="종료일 (YYYY-MM-DD):").grid(row=2, column=0, sticky='w', pady=3)
        to_var = tk.StringVar()
        ttk.Entry(form, textvariable=to_var, width=25).grid(row=2, column=1, pady=3)
        
        def generate():
            dialog.destroy()
            self._set_status("거래명세서 생성 중...")
            try:
                from ..utils.pdf_report_gen import generate_transaction_statement
                filepath = generate_transaction_statement(
                    self.engine,
                    customer=cust_var.get().strip(),
                    date_from=from_var.get().strip(),
                    date_to=to_var.get().strip()
                )
                if filepath and os.path.exists(filepath):
                    if CustomMessageBox.askyesno(self.root, "PDF 완료",
                        f"거래명세서 생성 완료!\n\n{filepath}\n\n파일을 열겠습니까?"):
                        try:
                            os.startfile(filepath)
                        except AttributeError:
                            import subprocess
                            subprocess.Popen(['xdg-open', filepath])
                else:
                    CustomMessageBox.showwarning(self.root, "경고", "PDF 생성 실패\n(해당 데이터 없음 또는 reportlab 미설치)")
            except (OSError, IOError, PermissionError) as e:
                CustomMessageBox.showerror(self.root, "오류", f"PDF 오류:\n{e}")
            self._set_status("Ready")
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=15)
        _b1 = ttk.Button(btn_frame, text="📝 생성", command=generate, width=12)
        _b1.pack(side='left', padx=5)
        apply_tooltip(_b1, "입력한 조건(고객·기간)으로 일일 보고서 PDF를 생성합니다. 저장 위치를 선택할 수 있습니다.")
        _b2 = ttk.Button(btn_frame, text="취소", command=dialog.destroy, width=10)
        _b2.pack(side='left', padx=5)
        apply_tooltip(_b2, "대화상자를 닫습니다. 생성하지 않은 보고서는 저장되지 않습니다.")
    
    def _generate_lot_detail_pdf(self, lot_no: str = None) -> None:
        """v4.1.1: LOT 상세 보고서 PDF — 자체 reportlab 생성"""
        from ..utils.constants import filedialog
        
        # LOT 선택
        if not lot_no:
            selection = self.tree_inventory.selection()
            if not selection:
                CustomMessageBox.showwarning(self.root, "선택 필요", "LOT를 선택해주세요.")
                return
            item = self.tree_inventory.item(selection[0])
            lot_no = str(item['values'][1])  # values[0]=row_num, values[1]=lot_no
        
        self._set_status("LOT 상세 PDF 생성 중...")
        self._log(f"LOT 상세 보고서 생성: {lot_no}")
        
        try:
            from ..utils.pdf_report_gen import generate_outbound_confirmation
            
            # 출고확인서로 대용 (lot_no 기반)
            filepath = generate_outbound_confirmation(
                self.engine, lot_no=lot_no, customer='')
            
            if filepath and os.path.exists(filepath):
                self._log(f"✅ PDF 생성: {filepath}")
                if CustomMessageBox.askyesno(self.root, "PDF 완료",
                    f"LOT 상세 보고서 생성!\n\n{filepath}\n\n파일을 열겠습니까?"):
                    try:
                        os.startfile(filepath)
                    except AttributeError:
                        import subprocess
                        subprocess.Popen(['xdg-open', filepath])
            else:
                CustomMessageBox.showwarning(self.root, "경고",
                    "PDF 생성 실패\n(해당 LOT에 출고 데이터 없음 또는 reportlab 미설치)")
        except (OSError, IOError, PermissionError) as e:
            self._log(f"❌ PDF 오류: {e}")
            CustomMessageBox.showerror(self.root, "오류", f"PDF 오류:\n{e}")
        
        self._set_status("Ready")
    
    def _generate_outbound_confirm_pdf(self) -> None:
        """v4.1.1: 출고확인서 PDF — LOT 선택 후 생성"""
        from ..utils.constants import tk, ttk
        
        selection = self.tree_inventory.selection()
        if not selection:
            CustomMessageBox.showwarning(self.root, "선택 필요", "출고확인서를 생성할 LOT를 선택해주세요.")
            return
        
        item = self.tree_inventory.item(selection[0])
        lot_no = str(item['values'][1])
        
        # 고객명 입력 다이얼로그
        dialog = tk.Toplevel(self.root)
        dialog.title("📤 출고확인서 생성")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"📤 출고확인서 — {lot_no}", font=('맑은 고딕', 12, 'bold')).pack(pady=8)
        
        form = ttk.Frame(dialog, padding=10)
        form.pack(fill='x')
        ttk.Label(form, text="고객명:").pack(side='left', padx=5)
        cust_var = tk.StringVar()
        ttk.Entry(form, textvariable=cust_var, width=25).pack(side='left', padx=5)
        
        def generate():
            dialog.destroy()
            self._set_status("출고확인서 생성 중...")
            try:
                from ..utils.pdf_report_gen import generate_outbound_confirmation
                filepath = generate_outbound_confirmation(
                    self.engine, lot_no=lot_no, customer=cust_var.get().strip())
                if filepath and os.path.exists(filepath):
                    if CustomMessageBox.askyesno(self.root, "PDF 완료",
                        f"출고확인서 생성!\n\n{filepath}\n\n파일을 열겠습니까?"):
                        try:
                            os.startfile(filepath)
                        except AttributeError:
                            import subprocess
                            subprocess.Popen(['xdg-open', filepath])
                else:
                    CustomMessageBox.showwarning(self.root, "경고", "PDF 생성 실패")
            except (OSError, IOError, PermissionError) as e:
                CustomMessageBox.showerror(self.root, "오류", f"PDF 오류:\n{e}")
            self._set_status("Ready")
        
        btn_f = ttk.Frame(dialog)
        btn_f.pack(pady=10)
        _bf1 = ttk.Button(btn_f, text="📤 생성", command=generate, width=12)
        _bf1.pack(side='left', padx=5)
        apply_tooltip(_bf1, "선택한 LOT의 상세 정보(톤백·이력 포함)를 PDF 파일로 저장합니다.")
        _bf2 = ttk.Button(btn_f, text="취소", command=dialog.destroy, width=10)
        _bf2.pack(side='left', padx=5)
        apply_tooltip(_bf2, "대화상자를 닫습니다.")
    
    def _generate_daily_pdf_v398(self) -> None:
        """v3.9.8: 일일 재고 현황 PDF"""
        
        self._set_status("PDF 보고서 생성 중...")
        try:
            from ..utils.pdf_report_gen import generate_daily_inventory_report
            filepath = generate_daily_inventory_report(self.engine)
            
            if filepath and os.path.exists(filepath):
                if CustomMessageBox.askyesno(self.root, "PDF 완료",
                    f"일일 재고 현황 PDF 생성 완료!\n\n{filepath}\n\n파일을 열겠습니까?"):
                    try:
                        os.startfile(filepath)
                    except AttributeError:
                        import subprocess
                        subprocess.Popen(['xdg-open', filepath])
            else:
                CustomMessageBox.showwarning(self.root, "경고", "PDF 생성 실패")
        except ImportError as e:
            CustomMessageBox.showerror(self.root, "오류", 
                f"reportlab 미설치:\npip install reportlab\n\n{e}")
        except (OSError, IOError, PermissionError) as e:
            self._log(f"❌ PDF 생성 오류: {e}")
            CustomMessageBox.showerror(self.root, "오류", f"PDF 생성 오류:\n{e}")
        
        self._set_status("Ready")
    
    def _generate_monthly_pdf_v398(self) -> None:
        """v3.9.8: 월간 실적 PDF"""
        from ..utils.constants import tk, ttk
        
        # 연월 선택 다이얼로그
        from datetime import datetime
        now = datetime.now()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("📅 월간 보고서")
        dialog.geometry("300x180")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="보고서 기간 선택", font=('맑은 고딕', 12, 'bold')).pack(pady=10)
        
        sel_frame = ttk.Frame(dialog)
        sel_frame.pack(pady=10)
        
        ttk.Label(sel_frame, text="연도:").pack(side='left', padx=5)
        year_var = tk.StringVar(value=str(now.year))
        ttk.Combobox(sel_frame, textvariable=year_var, 
                     values=[str(y) for y in range(2024, now.year+1)],
                     state='readonly', width=6).pack(side='left', padx=5)
        
        ttk.Label(sel_frame, text="월:").pack(side='left', padx=5)
        month_var = tk.StringVar(value=str(now.month))
        ttk.Combobox(sel_frame, textvariable=month_var,
                     values=[str(m) for m in range(1, 13)],
                     state='readonly', width=4).pack(side='left', padx=5)
        
        def generate():
            dialog.destroy()
            self._set_status("월간 PDF 생성 중...")
            try:
                from ..utils.pdf_report_gen import generate_monthly_report
                filepath = generate_monthly_report(
                    self.engine, int(year_var.get()), int(month_var.get()))
                
                if filepath and os.path.exists(filepath):
                    if CustomMessageBox.askyesno(self.root, "PDF 완료",
                        f"월간 실적 PDF 생성 완료!\n\n{filepath}\n\n파일을 열겠습니까?"):
                        try:
                            os.startfile(filepath)
                        except AttributeError:
                            import subprocess
                            subprocess.Popen(['xdg-open', filepath])
                else:
                    CustomMessageBox.showwarning(self.root, "경고", "PDF 생성 실패")
            except (OSError, IOError, PermissionError) as e:
                CustomMessageBox.showerror(self.root, "오류", f"PDF 오류:\n{e}")
            self._set_status("Ready")
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        _bd1 = ttk.Button(btn_frame, text="📊 생성", command=generate, width=10)
        _bd1.pack(side='left', padx=5)
        apply_tooltip(_bd1, "현재 재고 기준 일일 재고 현황 PDF를 생성합니다. 저장 위치를 선택할 수 있습니다.")
        _bd2 = ttk.Button(btn_frame, text="취소", command=dialog.destroy, width=10)
        _bd2.pack(side='left', padx=5)
        apply_tooltip(_bd2, "대화상자를 닫습니다.")
