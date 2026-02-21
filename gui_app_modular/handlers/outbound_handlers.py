# -*- coding: utf-8 -*-
"""
SQM Inventory - Outbound Handlers
=================================

v2.9.91 - Extracted from gui_app.py

Outbound processing: simple outbound, Excel outbound
"""

import logging
import sqlite3

from ..utils.ui_constants import CustomMessageBox, ThemeColors, apply_tooltip
logger = logging.getLogger(__name__)


class OutboundHandlersMixin:
    """
    Outbound handlers mixin
    
    Mixed into SQMInventoryApp class
    """
    
    def _on_simple_outbound(self) -> None:
        """Simple outbound dialog - enter LOT and quantity (v4.0.3: UI 분리)"""
        from ..utils.constants import tk, ttk, VERTICAL, BOTH, LEFT, RIGHT, X, Y, END, W
        from ..utils.constants import HAS_TTKBOOTSTRAP

        # v4.0.3: UI 위젯 생성을 별도 메서드로 분리
        w = self._build_simple_outbound_ui()
        dialog, lot_text, preview_tree = w['dialog'], w['lot_text'], w['preview_tree']
        summary_var, customer_var = w['summary_var'], w['customer_var']
        sale_ref_var, btn_frame = w['sale_ref_var'], w['btn_frame']
        
        def on_preview():
            """Preview: LOT별 톤백 상세 표시 (v3.8.4)"""
            preview_tree.delete(*preview_tree.get_children())
            
            lines_input = lot_text.get("1.0", END).strip().split('\n')
            total_kg = 0
            tonbag_count = 0
            warnings = []
            
            for line in lines_input:
                line = line.strip()
                if not line:
                    continue
                
                parts = [p.strip() for p in line.replace('\t', ',').split(',')]
                if len(parts) < 2:
                    warnings.append(f"형식 오류: {line}")
                    continue
                
                lot_no = parts[0]
                try:
                    qty_mt = float(parts[1])
                except ValueError:
                    warnings.append(f"수량 오류: {line}")
                    continue
                
                qty_kg = qty_mt * 1000
                
                # LOT 존재 확인
                lot_info = self.engine.db.fetchone(
                    "SELECT current_weight, product FROM inventory WHERE lot_no = ?",
                    (lot_no,)
                )
                
                if not lot_info:
                    preview_tree.insert('', END, values=(
                        lot_no, '-', '-', '-', '❌ 미발견', '-'
                    ), tags=('error',))
                    warnings.append(f"LOT 미발견: {lot_no}")
                    continue
                
                avail_kg = lot_info['current_weight'] or 0
                product = lot_info['product'] or '-'
                
                if avail_kg < qty_kg - 0.01:
                    warnings.append(f"재고 부족: {lot_no} (판매가능: {avail_kg:.0f}kg, 요청: {qty_kg:.0f}kg)")
                
                # 판매가능 톤백 조회
                tonbags = self.engine.db.fetchall(
                    """SELECT sub_lt, weight, status, location 
                       FROM inventory_tonbag 
                       WHERE lot_no = ? AND status = 'AVAILABLE'
                       ORDER BY sub_lt DESC""",
                    (lot_no,)
                )
                
                # LOT 헤더 행
                preview_tree.insert('', END, iid=f"LOT_{lot_no}",
                    values=(f"📦 {lot_no}", '', product, f"{avail_kg:,.0f}", 
                            f"요청: {qty_kg:,.0f}kg", ''),
                    tags=('lot_header',))
                
                remaining = qty_kg
                for tb in tonbags:
                    if remaining <= 0.01:
                        break
                    tb_weight = tb['weight'] or 0
                    sub_lt = tb['sub_lt']
                    loc = tb['location'] or ''
                    
                    status = '✅ 출고' if remaining >= tb_weight else '⚠️ 초과'
                    
                    item_id = preview_tree.insert('', END, values=(
                        f"  └ {lot_no}", str(sub_lt), product,
                        f"{tb_weight:,.0f}", status, loc
                    ), tags=('tonbag',))
                    
                    # 자동 선택 (요청 수량 만큼)
                    preview_tree.selection_add(item_id)
                    
                    remaining -= tb_weight
                    total_kg += tb_weight
                    tonbag_count += 1
            
            # 스타일
            preview_tree.tag_configure('error', foreground='red')
            preview_tree.tag_configure('lot_header', background='#E8F0FE', font=('', 13, 'bold'))
            preview_tree.tag_configure('tonbag', foreground=ThemeColors.get('text_primary', False))
            
            summary_var.set(f"톤백 {tonbag_count}개 / {total_kg/1000:.3f} MT 출고 예정")
            
            if warnings:
                CustomMessageBox.showwarning(self.root, "확인 필요", "\n".join(warnings[:10]))
        
        def on_execute():
            """Execute outbound (v3.8.4: 선택된 톤백 기반)"""
            customer = customer_var.get().strip()
            sale_ref = sale_ref_var.get().strip()
            
            if not customer:
                CustomMessageBox.showwarning(self.root, "입력 필요", "고객명을 입력하세요.")
                return
            
            # 선택된 톤백 항목 수집
            selected = preview_tree.selection()
            allocation_items = []
            
            if selected:
                # 선택된 톤백에서 LOT별 수량 집계
                lot_weights = {}
                for item_id in selected:
                    values = preview_tree.item(item_id)['values']
                    tags = preview_tree.item(item_id).get('tags', ())
                    
                    if 'lot_header' in tags:
                        continue  # LOT 헤더는 건너뜀
                    
                    lot_no = str(values[0]).replace('└', '').strip()
                    try:
                        weight = float(str(values[3]).replace(',', ''))
                    except (ValueError, IndexError):
                        continue
                    
                    if lot_no not in lot_weights:
                        lot_weights[lot_no] = 0
                    lot_weights[lot_no] += weight
                
                for lot_no, weight_kg in lot_weights.items():
                    allocation_items.append({
                        'lot_no': lot_no,
                        'weight_kg': weight_kg,
                        'qty_mt': weight_kg / 1000.0,
                        'sold_to': customer,
                        'customer': customer,
                        'sale_ref': sale_ref
                    })
            
            if not allocation_items:
                # Fallback: 텍스트 입력에서 추출
                lines = lot_text.get("1.0", END).strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    parts = [p.strip() for p in line.replace('\t', ',').split(',')]
                    if len(parts) < 2:
                        continue
                    lot_no = parts[0]
                    try:
                        qty_mt = float(parts[1])
                    except ValueError:
                        continue
                    allocation_items.append({
                        'lot_no': lot_no,
                        'qty_mt': qty_mt,
                        'sold_to': customer,
                        'customer': customer,
                        'sale_ref': sale_ref
                    })
            
            if not allocation_items:
                CustomMessageBox.showwarning(self.root, "입력 필요", "Preview 후 톤백을 선택하거나 LOT를 입력하세요.")
                return
            
            # v5.0.9: 톤백/샘플 구분 카운트
            from ..dialogs.allocation_preview import _is_sample_item
            tonbag_items = [i for i in allocation_items if not _is_sample_item(i)]
            sample_items = [i for i in allocation_items if _is_sample_item(i)]
            tonbag_qty = sum(i.get('qty_mt', 0) for i in tonbag_items)
            sample_qty = sum(i.get('qty_mt', 0) for i in sample_items)
            total_qty = tonbag_qty + sample_qty
            
            # Confirm (v5.0.9: 톤백/샘플 구분 표시)
            confirm_msg = (
                f"출고를 진행할까요?\n\n"
                f"고객: {customer}\n"
                f"📦 톤백: {len(tonbag_items)}개 ({tonbag_qty:.3f} MT)\n"
                f"🧪 샘플: {len(sample_items)}개 ({sample_qty:.3f} MT)\n"
                f"합계: {len(allocation_items)}건 ({total_qty:.3f} MT)"
            )
            if not CustomMessageBox.askyesno(self.root, "출고 확인", confirm_msg):
                return
            
            # Execute (v3.8.4: All-or-Nothing)
            try:
                # process_outbound_safe 우선 시도 (All-or-Nothing)
                if hasattr(self.engine, 'process_outbound_safe'):
                    try:
                        result = self.engine.process_outbound_safe(allocation_items)
                    except (ValueError, RuntimeError, sqlite3.OperationalError) as pf_err:
                        # PreflightError 등 출고 검증 에러
                        err_msg = str(pf_err)
                        display_msg = err_msg[:500] + '...' if len(err_msg) > 500 else err_msg
                        self._log(f"❌ 출고 검증 실패 (All-or-Nothing): {display_msg[:200]}")
                        CustomMessageBox.showerror(self.root, "출고 검증 실패",
                            f"All-or-Nothing 검증에서 오류가 발견되어\n전체 출고가 중단되었습니다.\n\n{display_msg}")
                        return
                else:
                    result = self.engine.process_outbound(allocation_items)
                
                if result.get('success') or result.get('processed', 0) > 0:
                    processed = result.get('lots_processed', result.get('processed', 0))
                    picked = result.get('total_picked', 0)
                    msg = (f"출고 완료!\n\n"
                           f"처리: {processed}건\n"
                           f"총 출고: {picked:.3f} MT")
                    
                    if result.get('warnings'):
                        msg += f"\n\n경고:\n" + "\n".join(result['warnings'][:5])
                    
                    CustomMessageBox.showinfo(self.root, "완료", msg)
                    self._log(f"✅ 빠른 출고: {processed}건, {picked:.3f} MT")
                    
                    dialog.destroy()
                    self._refresh_inventory()
                    if hasattr(self, '_refresh_tonbag'):
                        self._refresh_tonbag()
                else:
                    errs = '\n'.join(result.get('errors', ['알 수 없는 오류']))
                    CustomMessageBox.showerror(self.root, "출고 실패", f"출고 처리 실패:\n{errs}")
            
            except (ValueError, RuntimeError, KeyError, sqlite3.OperationalError, sqlite3.IntegrityError) as e:
                logger.error(f"출고 오류: {e}")
                err_msg = str(e)[:500]
                CustomMessageBox.showerror(self.root, "출고 오류", f"출고 처리 중 오류:\n\n{err_msg}")
        
        # Button style
        btn_style = {"bootstyle": "info"} if HAS_TTKBOOTSTRAP else {}
        btn_style_success = {"bootstyle": "success"} if HAS_TTKBOOTSTRAP else {}
        btn_style_secondary = {"bootstyle": "secondary"} if HAS_TTKBOOTSTRAP else {}
        btn_style_outline = {"bootstyle": "outline"} if HAS_TTKBOOTSTRAP else {}
        
        _bp = ttk.Button(btn_frame, text="Preview", command=on_preview, **btn_style)
        _bp.pack(side=LEFT, padx=5)
        apply_tooltip(_bp, "입력한 LOT·수량·출고처로 출고 미리보기를 표시합니다. DB에는 반영되지 않습니다.")
        _be = ttk.Button(btn_frame, text="Execute", command=on_execute, **btn_style_success)
        _be.pack(side=LEFT, padx=5)
        apply_tooltip(_be, "미리보기한 내용으로 실제 출고를 실행합니다. 재고가 차감되고 출고 이력에 기록됩니다.")
        _bc = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, **btn_style_secondary)
        _bc.pack(side=RIGHT, padx=5)
        apply_tooltip(_bc, "출고 대화상자를 닫습니다. 실행하지 않은 출고는 반영되지 않습니다.")
        
        # Get selected LOT from inventory
        def on_get_selected_lot():
            """Get selected LOT from inventory list"""
            selected = self.tree_inventory.selection()
            if selected:
                values = self.tree_inventory.item(selected[0])['values']
                lot_no = values[0]
                current_text = lot_text.get("1.0", END).strip()
                if current_text:
                    lot_text.insert(END, f"\n{lot_no}, ")
                else:
                    lot_text.insert(END, f"{lot_no}, ")
                lot_text.focus_set()
        
        _badd = ttk.Button(btn_frame, text="Add Selected", command=on_get_selected_lot,
                           **btn_style_outline)
        _badd.pack(side=LEFT, padx=20)
        apply_tooltip(_badd, "재고 리스트에서 선택한 LOT를 출고 목록에 추가합니다. 여러 LOT를 쉼표로 구분해 넣을 수 있습니다.")
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 700) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 600) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Key bindings
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def _on_outbound_click(self) -> None:
        """v4.0.5 Phase2: 파일 선택 → 미리보기 팝업 → 사용자 확인 → DB 반영"""
        from ..utils.constants import filedialog
        
        files = filedialog.askopenfilenames(
            title="출고 Allocation Excel 선택",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if not files:
            return
        
        for file_path in files:
            self._preview_outbound(file_path)
    
    def _preview_outbound(self, excel_path: str) -> None:
        """v4.0.5: 출고 Excel → 파싱 → 미리보기 팝업"""
        import os
        
        self._log(f"📤 출고 파일 읽기: {os.path.basename(excel_path)}")
        
        try:
            from parsers.allocation_parser import AllocationParser
            
            parser = AllocationParser()
            alloc_data = parser.parse(excel_path)
            
            if not alloc_data or not alloc_data.rows:
                self._log("⚠️ 출고 데이터 없음")
                CustomMessageBox.showwarning(self.root, "경고", "출고 데이터가 없습니다.")
                return
            
            # AllocationRow → dict 변환 (미리보기용, v5.1.0: 용어 통일)
            preview_items = []
            for row in alloc_data.rows:
                preview_items.append({
                    'lot_no': row.lot_no,
                    'sap_no': row.sap_no,
                    'product': row.product,
                    'qty_mt': row.qty_mt,
                    'sold_to': row.sold_to,           # DB 호환
                    'customer': row.sold_to,           # v5.1.0 표준
                    'sale_ref': row.sale_ref,
                    'sub_lt': row.sub_lt,              # DB 호환
                    'tonbag_no': row.sub_lt,           # v5.1.0 표준
                    'warehouse': row.warehouse,
                    'customs': row.customs,
                    'gross_weight': row.gross_weight,
                })
            
            self._log(f"📋 출고 미리보기: {len(preview_items)}건, {alloc_data.total_qty:.3f} MT")
            
            # 미리보기 팝업 표시 → Execute 클릭 시 _execute_outbound 호출
            self._show_outbound_preview(
                preview_items,
                callback=lambda items: self._execute_outbound(items, alloc_data)
            )
            
        except ImportError:
            self._log("⚠️ AllocationParser 모듈 없음")
            CustomMessageBox.showwarning(self.root, "모듈 없음", "출고 파서 모듈이 필요합니다.")
        except (RuntimeError, ValueError, TypeError) as e:
            logger.error(f"출고 파일 읽기 실패: {e}")
            self._log(f"❌ 출고 파일 오류: {e}")
            CustomMessageBox.show_detailed_error(
                self.root, "출고 파일 오류", 
                f"Excel 파일을 읽는 중 오류가 발생했습니다.\n\n{e}",
                exception=e
            )
    
    def _show_outbound_preview(self, preview_items, callback):
        """
        v5.0.4: Allocation 출고 미리보기 다이얼로그 표시
        
        Args:
            preview_items: Allocation 데이터 리스트
            callback: 확인 시 콜백 함수
        """
        try:
            from ..dialogs.allocation_preview import AllocationPreviewDialog
            
            dialog = AllocationPreviewDialog(
                self.root,
                preview_items,
                on_confirm=callback,
                on_cancel=lambda: self._log("❌ 출고 취소됨")
            )
            
        except ImportError as e:
            self._log(f"⚠️ AllocationPreviewDialog 로딩 실패: {e}")
            # Fallback: 기존 방식
            if callback:
                callback(preview_items)
    
    def _execute_outbound(self, preview_items, alloc_data) -> None:
        """v4.0.5: 사용자 확인 후 실제 DB 반영"""
        try:
            if hasattr(self.engine, 'process_outbound_safe'):
                result = self.engine.process_outbound_safe(alloc_data)
                processed = result.get('lots_processed', 0)
            else:
                # Fallback: 건별 처리
                processed = 0
                errors = []
                for alloc in alloc_data.rows if hasattr(alloc_data, 'rows') else [alloc_data]:
                    try:
                        self.engine.process_outbound(alloc)
                        processed += 1
                    except (ValueError, TypeError, AttributeError) as e:
                        errors.append(str(e))
                
                if errors:
                    self._log(f"⚠️ 출고: {processed}건 성공, {len(errors)}건 오류")
                    CustomMessageBox.showwarning(
                        self.root, "출고 부분 완료",
                        f"처리: {processed}건\n오류: {len(errors)}건\n\n{errors[0]}")
                    if hasattr(self, '_refresh_inventory'):
                        self._refresh_inventory()
                    if hasattr(self, '_refresh_tonbag'):
                        self._refresh_tonbag()
                    return
            
            # 화면 새로고침
            if hasattr(self, '_refresh_inventory'):
                self._refresh_inventory()
            if hasattr(self, '_refresh_tonbag'):
                self._refresh_tonbag()
            if hasattr(self, '_refresh_dashboard'):
                self._refresh_dashboard()
            
            self._log(f"✅ 출고 완료: {processed}건")
            CustomMessageBox.showinfo(self.root, "출고 완료", 
                f"출고 처리가 완료되었습니다.\n\n처리: {processed}건")
            
        except (ValueError, RuntimeError, KeyError, sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as pf_err:
            err_msg = str(pf_err)
            display_msg = err_msg[:500] + '...' if len(err_msg) > 500 else err_msg
            self._log(f"❌ 출고 실패: {display_msg[:200]}")
            CustomMessageBox.show_detailed_error(
                self.root, "출고 처리 실패",
                f"출고 처리 중 오류가 발생했습니다.\n\n{display_msg}",
                exception=pf_err)
    
    def _on_manual_outbound_click(self) -> None:
        """Manual outbound button from tonbag tab"""
        selection = self.tree_sublot.selection()
        if not selection:

            CustomMessageBox.showwarning(self.root, "Select Required", "Please select a tonbag to ship")
            return
        
        item = self.tree_sublot.item(selection[0])
        values = item['values']
        
        if len(values) >= 4:
            lot_no = values[2]  # LOT NO
            sub_lt = values[3]  # Sub LT
            status = values[6] if len(values) > 6 else 'AVAILABLE'
            
            if status == 'AVAILABLE':
                self._show_manual_outbound_dialog(str(lot_no), str(sub_lt))
            else:

                CustomMessageBox.showinfo(self.root, "Info", f"Already shipped (Status: {status})")
    
    # ═══════════════════════════════════════════════════════
    # v3.8.4: 출고 배정표 샘플 Excel 템플릿 다운로드
    # ═══════════════════════════════════════════════════════
    

    # v4.0.1: 출고 템플릿/Allocation은 outbound_template_mixin.py로 분리

    def _build_simple_outbound_ui(self):
        """v4.0.3: Simple Outbound UI 위젯 생성 (~80줄 추출)"""
        from ..utils.constants import tk, ttk, VERTICAL, BOTH, LEFT, RIGHT, X, Y, W

        dialog = tk.Toplevel(self.root)
        dialog.title("Simple Outbound")
        dialog.geometry("700x600")
        dialog.transient(self.root)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # Input area
        input_frame = ttk.LabelFrame(main_frame, text="Outbound Information")
        input_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(input_frame, text="Customer:").grid(row=0, column=0, sticky=W, pady=2)
        customer_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=customer_var, width=30).grid(row=0, column=1, sticky=W, pady=2)

        ttk.Label(input_frame, text="Sales Ref:").grid(row=0, column=2, sticky=W, padx=(20, 0), pady=2)
        sale_ref_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=sale_ref_var, width=20).grid(row=0, column=3, sticky=W, pady=2)

        ttk.Label(input_frame, text="Enter LOT number and quantity (one per line):",
                  font=('', 16)).grid(row=1, column=0, columnspan=4, sticky=W, pady=(10, 2))
        ttk.Label(input_frame, text="Format: LOT_NO, Qty(MT)  e.g.) 1234567890, 5.0",
                  foreground='gray').grid(row=2, column=0, columnspan=4, sticky=W)

        # LOT text
        lot_frame = ttk.Frame(main_frame)
        lot_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        lot_text = tk.Text(lot_frame, height=10, width=60)
        lot_sb = ttk.Scrollbar(lot_frame, orient=VERTICAL, command=lot_text.yview)
        lot_text.configure(yscrollcommand=lot_sb.set)
        lot_text.pack(side=LEFT, fill=BOTH, expand=True)
        lot_sb.pack(side=RIGHT, fill=Y)

        # Preview tree
        preview_frame = ttk.LabelFrame(main_frame, text="Outbound Preview")
        preview_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        columns = ('lot_no', 'sub_lt', 'product', 'weight_kg', 'status', 'location')
        preview_tree = ttk.Treeview(preview_frame, columns=columns, show='headings',
                                     height=10, selectmode='extended')
        for col, text, w in [('lot_no', 'LOT No', 110), ('sub_lt', '톤백#', 55),
                              ('product', 'Product', 80), ('weight_kg', '중량(kg)', 90),
                              ('status', '상태', 80), ('location', '위치', 70)]:
            preview_tree.heading(col, text=text)
            anchor = 'e' if col == 'weight_kg' else 'center' if col in ('sub_lt', 'status') else 'w'
            preview_tree.column(col, width=w, anchor=anchor)
        pv_sb = ttk.Scrollbar(preview_frame, orient=VERTICAL, command=preview_tree.yview)
        preview_tree.configure(yscrollcommand=pv_sb.set)
        preview_tree.pack(side=LEFT, fill=BOTH, expand=True)
        pv_sb.pack(side=RIGHT, fill=Y)

        ttk.Label(main_frame, text="💡 Preview 후 출고할 톤백을 선택하세요 (미선택 시 자동 배정)",
                  foreground='gray', font=('', 16)).pack(pady=(0, 5))
        summary_var = tk.StringVar(value="Click Preview to check outbound details")
        ttk.Label(main_frame, textvariable=summary_var, font=('', 13, 'bold')).pack(pady=5)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=10)

        return {
            'dialog': dialog, 'lot_text': lot_text, 'preview_tree': preview_tree,
            'summary_var': summary_var, 'customer_var': customer_var,
            'sale_ref_var': sale_ref_var, 'btn_frame': btn_frame,
        }

    def _on_allocation_input_unified(self, initial_file: str = None) -> None:
        """Allocation 입력 통합: 파일 불러오기 vs 템플릿 붙여넣기. initial_file 있으면 선택 없이 해당 파일로 열기(드래그 등)."""
        from ..utils.constants import filedialog
        from ..utils.ui_constants import center_dialog, ThemeColors, DialogSize, apply_modal_window_options
        import tkinter as tk
        from tkinter import ttk

        if initial_file:
            try:
                from ..dialogs.allocation_dialog import AllocationDialog
                dlg = AllocationDialog(self, self.engine)
                dlg.show(initial_file=initial_file)
            except (ImportError, AttributeError) as e:
                logger.error(f"Allocation 다이얼로그 오류: {e}", exc_info=True)
                CustomMessageBox.showerror(self.root, "오류", f"Allocation 열기 실패:\n{e}")
            return

        result = [None]
        win = tk.Toplevel(self.root)
        win.title("Allocation 입력")
        apply_modal_window_options(win)
        win.transient(self.root)
        win.grab_set()
        win.geometry(DialogSize.get_geometry(self.root, 'small'))
        win.minsize(420, 260)
        center_dialog(win, self.root)
        f = ttk.Frame(win, padding=(20, 20, 20, 32))
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="Allocation 데이터 입력 방법을 선택하세요.", font=('맑은 고딕', 12, 'bold')).pack(anchor='w', pady=(0, 12))
        ttk.Label(f, text="① Allocation Excel 파일을 불러옵니다.\n   → 미리보기 후 예약(RESERVED) 실행.",
                  font=('맑은 고딕', 10), wraplength=400, justify=tk.LEFT).pack(anchor='w', pady=(0, 10))
        ttk.Label(f, text="② 내장 Allocation 템플릿에 데이터를 붙여넣기(Ctrl+V) 합니다.\n   → 붙여넣기 후 미리보기 → 예약 실행.",
                  font=('맑은 고딕', 10), wraplength=400, justify=tk.LEFT).pack(anchor='w', pady=(0, 24))
        btn_f = ttk.Frame(f)
        btn_f.pack(anchor='center')
        def on_file():
            result[0] = 'file'
            win.destroy()
        def on_paste():
            result[0] = 'paste'
            win.destroy()
        ttk.Button(btn_f, text="📂 파일 불러오기", command=on_file, width=22).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_f, text="📋 템플릿 붙여넣기", command=on_paste, width=22).pack(side=tk.LEFT)
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.wait_window(win)

        choice = result[0]
        if not choice:
            return
        try:
            from ..dialogs.allocation_dialog import AllocationDialog
            dlg = AllocationDialog(self, self.engine)
            if choice == 'file':
                path = filedialog.askopenfilename(
                    parent=self.root, title="Allocation Excel 선택",
                    filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
                )
                if path:
                    dlg.show(initial_file=path)
                return
            if choice == 'paste':
                from ..utils.paste_table_dialog import show_paste_table_dialog
                ALLOC_PASTE_COLUMNS = [
                    ('lot_no', 'LOT NO', 110),
                    ('sap_no', 'SAP NO', 100),
                    ('product', 'Product', 140),
                    ('qty_mt', 'QTY (MT)', 80),
                    ('sold_to', 'CUSTOMER', 130),
                    ('sale_ref', 'SALE REF', 120),
                    ('outbound_date', 'OUTBOUND DATE', 100),
                    ('warehouse', 'WH', 60),
                ]

                def on_paste_confirm(rows: list):
                    if not rows:
                        CustomMessageBox.showwarning(self.root, "경고", "붙여넣기 데이터가 없습니다.")
                        return
                    normalized = []
                    for r in rows:
                        try:
                            qty = float(str(r.get('qty_mt', '0')).replace(',', '').strip() or 0)
                        except (ValueError, TypeError):
                            qty = 0.0
                        if not str(r.get('lot_no', '')).strip():
                            continue
                        row = dict(r)
                        row['qty_mt'] = qty
                        row['sublot_count'] = max(1, int(qty / 0.5))
                        normalized.append(row)
                    if not normalized:
                        CustomMessageBox.showwarning(self.root, "경고", "유효한 LOT NO·QTY 행이 없습니다.")
                        return
                    dlg = AllocationDialog(self, self.engine)
                    dlg.show_with_data(normalized)

                show_paste_table_dialog(
                    self.root,
                    title="📋 Allocation 데이터 (붙여넣기)",
                    columns=ALLOC_PASTE_COLUMNS,
                    instruction="아래 표에 Excel 등에서 복사한 Allocation 데이터를 붙여넣기(Ctrl+V) 한 뒤 [확인]을 누르세요. LOT NO, QTY (MT), CUSTOMER 등.",
                    confirm_text="확인",
                    cancel_text="취소",
                    on_confirm=on_paste_confirm,
                    min_size=(800, 440),
                )
        except (ImportError, AttributeError) as e:
            logger.error(f"Allocation 입력 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.root, "오류", f"Allocation 입력 실패:\n{e}")

    def _on_quick_outbound_paste(self) -> None:
        """빠른 출고: 가운데 선택 창 없이 바로 붙여넣기 테이블만 열기. 컬럼 유지, 확인 시 Allocation 미리보기 → 예약."""
        try:
            from ..dialogs.allocation_dialog import AllocationDialog
            from ..utils.paste_table_dialog import show_paste_table_dialog

            ALLOC_PASTE_COLUMNS = [
                ('lot_no', 'LOT NO', 110),
                ('sap_no', 'SAP NO', 100),
                ('product', 'Product', 140),
                ('qty_mt', 'QTY (MT)', 80),
                ('sold_to', 'CUSTOMER', 130),
                ('sale_ref', 'SALE REF', 120),
                ('outbound_date', 'OUTBOUND DATE', 100),
                ('warehouse', 'WH', 60),
            ]

            def on_paste_confirm(rows: list):
                if not rows:
                    CustomMessageBox.showwarning(self.root, "경고", "붙여넣기 데이터가 없습니다.")
                    return
                normalized = []
                for r in rows:
                    try:
                        qty = float(str(r.get('qty_mt', '0')).replace(',', '').strip() or 0)
                    except (ValueError, TypeError):
                        qty = 0.0
                    if not str(r.get('lot_no', '')).strip():
                        continue
                    row = dict(r)
                    row['qty_mt'] = qty
                    row['sublot_count'] = max(1, int(qty / 0.5))
                    normalized.append(row)
                if not normalized:
                    CustomMessageBox.showwarning(self.root, "경고", "유효한 LOT NO·QTY 행이 없습니다.")
                    return
                dlg = AllocationDialog(self, self.engine)
                dlg.show_with_data(normalized)

            show_paste_table_dialog(
                self.root,
                title="📤 빠른 출고 (붙여넣기)",
                columns=ALLOC_PASTE_COLUMNS,
                instruction="아래 표에 Excel 등에서 복사한 출고 데이터를 붙여넣기(Ctrl+V) 한 뒤 [확인]을 누르세요. LOT NO, QTY (MT), CUSTOMER 등.",
                confirm_text="확인",
                cancel_text="취소",
                on_confirm=on_paste_confirm,
                min_size=(800, 440),
            )
        except (ImportError, AttributeError) as e:
            logger.error(f"빠른 출고 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.root, "오류", f"빠른 출고 열기 실패:\n{e}")

    def _on_allocation_dialog(self) -> None:
        """Allocation 출고 예약 다이얼로그 열기 (v5.9.5). 통합 메뉴에서는 _on_allocation_input_unified 사용."""
        try:
            from ..dialogs.allocation_dialog import AllocationDialog
            dlg = AllocationDialog(self, self.engine)
            dlg.show()
        except (ImportError, AttributeError) as e:
            logger.error(f"Allocation 다이얼로그 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(
                self.root, "오류",
                f"Allocation 다이얼로그를 열 수 없습니다:\n{e}"
            )

    def _on_picking_list_upload(self) -> None:
        """v6.0: Picking List PDF 업로드 — 파일 선택 → 파싱 → 결과 미리보기"""
        from ..utils.constants import filedialog

        path = filedialog.askopenfilename(
            parent=self.root,
            title="Picking List PDF 선택",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path or not path.strip():
            return

        parse_picking_list_pdf = None
        try:
            from features.parsers.picking_list_parser import parse_picking_list_pdf as _parse
            parse_picking_list_pdf = _parse
        except ImportError:
            try:
                from parsers import parse_picking_list_pdf as _parse
                parse_picking_list_pdf = _parse
            except ImportError:
                try:
                    from parsers.picking_list_parser import parse_picking_list_pdf as _parse
                    parse_picking_list_pdf = _parse
                except ImportError:
                    pass

        if not parse_picking_list_pdf:
            CustomMessageBox.showerror(
                self.root,
                "Picking List 파서 없음",
                "features.parsers 또는 parsers.picking_list_parser를 불러올 수 없습니다.",
            )
            return

        try:
            doc = parse_picking_list_pdf(path)
        except Exception as e:
            logger.exception("Picking List PDF 파싱 오류")
            CustomMessageBox.show_detailed_error(
                self.root,
                "파싱 오류",
                "PDF 파싱 중 오류가 발생했습니다.",
                exception=e,
            )
            return

        on_apply = None
        try:
            from features.parsers.picking_engine import apply_picking_list_to_db
            def _apply(d, p):
                apply_picking_list_to_db(self.engine, d, p)
                CustomMessageBox.showinfo(self.root, "완료", "DB 반영이 완료되었습니다.")
            on_apply = _apply
        except ImportError:
            logger.debug("features.parsers.picking_engine 없음 — DB 반영 버튼 비표시")

        from ..dialogs.picking_list_preview_dialog import PickingListPreviewDialog
        PickingListPreviewDialog(self.root, doc, path, on_apply_clicked=on_apply)

    def _on_barcode_scan_upload(self) -> None:
        """v6.0: 바코드 스캔 파일 업로드 (준비 중)"""
        CustomMessageBox.showinfo(
            self.root, "바코드 스캔 업로드",
            "바코드 스캔 파일(CSV/Excel) 업로드 기능은 준비 중입니다.\n"
            "창고 직원이 스캔한 파일을 업로드하면\n"
            "스캔된 톤백만 PICKED → SOLD로 전환됩니다."
        )
