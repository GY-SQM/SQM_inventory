# -*- coding: utf-8 -*-
"""
SQM Inventory - Allocation Flow Mixin (HB)
============================================

v8.7.4 - Extracted from outbound_handlers.py

Allocation-related UI handlers (7 functions)
"""

from gui_app_modular.utils.ui_constants import create_themed_toplevel  # v8.0.9
import logging
import sqlite3

from ..utils.ui_constants import CustomMessageBox
logger = logging.getLogger(__name__)


class AllocationFlowMixin:
    """Allocation flow mixin (HB).

    Mixed into OutboundHandlersMixin → SQMInventoryApp.
    """

    def _on_go_allocation_tab(self) -> None:
        """판매 배정 탭으로 이동 (메뉴 공통 진입점) — v8.1.6: 위젯 참조 단일화."""
        notebook = getattr(self, 'notebook', None)
        if not notebook:
            return
        target_tab = getattr(self, 'tab_allocation', None)
        if target_tab is None:
            logger.debug("[출고UI] tab_allocation 미등록 — 탭 이동 스킵")
            return
        try:
            notebook.select(target_tab)
        except Exception as e:
            logger.debug(f"[출고UI] 탭 선택 실패: {e}")

    def _on_allocation_stress_test(self) -> None:
        """🧪 Allocation 7-Gate Stress Test 다이얼로그 (v7.1.2)."""
        try:
            from ..dialogs.Claude_allocation_stress_test_dialog_v712 import AllocationStressTestDialog
            AllocationStressTestDialog(self, self.engine)
        except Exception as e:
            logger.error(f"Stress Test 다이얼로그 오류: {e}")

    def _on_outbound_click(self) -> None:
        """v4.0.5 Phase2: 파일 선택 → 미리보기 팝업 → 사용자 확인 → DB 반영"""
        from ..utils.constants import filedialog

        files = filedialog.askopenfilenames(
            parent=self.root,
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

            _ = AllocationPreviewDialog(
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
        """v4.0.5: 사용자 확인 후 실제 DB 반영. v5.9.92: AllocationRow → dict 변환 후 process_outbound(EXCEL)."""
        try:
            # AllocationRow → dict 리스트 변환 (process_outbound는 dict 기대)
            if hasattr(alloc_data, 'rows'):
                items = []
                for row in alloc_data.rows:
                    items.append({
                        'lot_no': getattr(row, 'lot_no', ''),
                        'weight_kg': (getattr(row, 'qty_mt', 0) or 0) * 1000.0,
                        'qty_mt': getattr(row, 'qty_mt', 0),
                        'customer': getattr(row, 'sold_to', '') or getattr(row, 'customer', ''),
                        'sold_to': getattr(row, 'sold_to', ''),
                        'sale_ref': getattr(row, 'sale_ref', ''),
                    })
            else:
                items = list(preview_items) if preview_items else []

            if not items:
                self._log("⚠️ 출고할 항목 없음")
                CustomMessageBox.showwarning(self.root, "출고", "출고할 항목이 없습니다.")
                return

            if hasattr(self, 'do_action_tx'):
                result = self.do_action_tx(
                    "EXECUTE_OUTBOUND_EXCEL",
                    lambda: self.engine.process_outbound(items, source='EXCEL', stop_at_picked=False),
                    parent=self.root,
                    refresh_mode="deferred",
                )
            else:
                result = self.engine.process_outbound(items, source='EXCEL', stop_at_picked=False)
            processed = result.get('lots_processed', result.get('processed', 0))

            if not result.get('success') and result.get('errors'):
                self._log(f"⚠️ 출고 오류: {result['errors'][:3]}")
                CustomMessageBox.showwarning(
                    self.root, "출고 완료",
                    f"처리: {processed}건\n오류: {result['errors'][0]}")

            # 화면 새로고침 (do_action_tx가 있는 경우 이미 처리됨)
            if not hasattr(self, 'do_action_tx'):
                self._refresh_after_outbound_action("EXECUTE_OUTBOUND_EXCEL")

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

    def _on_allocation_input_unified(self, initial_file: str = None) -> None:
        """Allocation 입력 통합: 파일 불러오기 vs 템플릿 붙여넣기. initial_file 있으면 선택 없이 해당 파일로 열기(드래그 등)."""
        from ..utils.constants import filedialog
        from ..utils.ui_constants import DialogSize, center_dialog

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
        win = create_themed_toplevel(self.root)
        win.title("Allocation 입력")
        pass  # modal
        win.transient(self.root)
        win.grab_set()
        win.geometry(DialogSize.get_geometry(self.root, 'small'))
        win.minsize(420, 260)
        center_dialog(win, self.root)
        f = ttk.Frame(win, padding=(20, 20, 20, 32))
        f.pack(fill=tk.BOTH, expand=True)
        from ..utils.ui_constants import (
            UPLOAD_CHOICE_HEADER, UPLOAD_CHOICE_PASTE, UPLOAD_CHOICE_UPLOAD,
            UPLOAD_CHOICE_BTN_PASTE, UPLOAD_CHOICE_BTN_UPLOAD,
        )
        ttk.Label(f, text=UPLOAD_CHOICE_HEADER, font=('맑은 고딕', 12, 'bold')).pack(anchor='w', pady=(0, 12))
        ttk.Label(f, text=UPLOAD_CHOICE_PASTE, font=('맑은 고딕', 10), wraplength=400, justify=tk.LEFT).pack(anchor='w', pady=(0, 10))
        ttk.Label(f, text=UPLOAD_CHOICE_UPLOAD, font=('맑은 고딕', 10), wraplength=400, justify=tk.LEFT).pack(anchor='w', pady=(0, 24))
        btn_f = ttk.Frame(f)
        btn_f.pack(anchor='center')
        def on_file():
            result[0] = 'file'
            win.destroy()
        def on_paste():
            result[0] = 'paste'
            win.destroy()
        ttk.Button(btn_f, text=UPLOAD_CHOICE_BTN_UPLOAD, command=on_file, width=22).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_f, text=UPLOAD_CHOICE_BTN_PASTE, command=on_paste, width=22).pack(side=tk.LEFT)
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
                    # v8.6.5: 공통 파싱/병합/검증 헬퍼 사용
                    parsed, parse_errors = self._oh_parse_alloc_paste_rows(rows)
                    if parse_errors:
                        logger.warning(f"빠른 출고 파싱 경고: {parse_errors}")
                    if not parsed:
                        msg = "유효한 LOT NO · QTY 행이 없습니다."
                        if parse_errors:
                            msg += "\n\n" + "\n".join(parse_errors[:8])
                        CustomMessageBox.showwarning(self.root, "경고", msg)
                        return

                    merged = self._oh_merge_alloc_lots(parsed)
                    validation_errors = self._oh_validate_alloc_lot_nos(merged)

                    if validation_errors:
                        warn_msg = "다음 LOT에 문제가 있습니다:\n\n" + "\n".join(validation_errors[:10])
                        warn_msg += "\n\n문제 LOT을 제외하고 계속 진행할까요?"
                        if not CustomMessageBox.askyesno(self.root, "LOT 검증 경고", warn_msg):
                            return
                        problem_lots = {e.split(':')[0].replace('❌ ', '').strip() for e in validation_errors}
                        merged = [r for r in merged if r['lot_no'] not in problem_lots]
                        if not merged:
                            CustomMessageBox.showwarning(self.root, "경고", "유효한 LOT이 없습니다.")
                            return

                    for row in merged:
                        try:
                            from engine_modules.constants import get_tonbag_unit_weight
                            unit_w = get_tonbag_unit_weight(self.engine.db, row['lot_no'])
                        except Exception:
                            from engine_modules.constants import DEFAULT_TONBAG_WEIGHT
                            unit_w = DEFAULT_TONBAG_WEIGHT  # v8.6.1
                        unit_mt = unit_w / 1000.0
                        row['sublot_count'] = max(1, int(row['qty_mt'] / unit_mt + 0.001))

                    dlg = AllocationDialog(self, self.engine)
                    dlg.show_with_data(merged)

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
                # v8.6.5: 공통 파싱/병합/검증 헬퍼 사용
                parsed, parse_errors = self._oh_parse_alloc_paste_rows(rows)
                if parse_errors:
                    logger.warning(f"빠른 출고 파싱 경고: {parse_errors}")
                if not parsed:
                    msg = "유효한 LOT NO · QTY 행이 없습니다."
                    if parse_errors:
                        msg += "\n\n" + "\n".join(parse_errors[:8])
                    CustomMessageBox.showwarning(self.root, "경고", msg)
                    return

                merged = self._oh_merge_alloc_lots(parsed)
                validation_errors = self._oh_validate_alloc_lot_nos(merged)

                if validation_errors:
                    warn_msg = "다음 LOT에 문제가 있습니다:\n\n" + "\n".join(validation_errors[:10])
                    warn_msg += "\n\n문제 LOT을 제외하고 계속 진행할까요?"
                    if not CustomMessageBox.askyesno(self.root, "LOT 검증 경고", warn_msg):
                        return
                    problem_lots = {e.split(':')[0].replace('❌ ', '').strip() for e in validation_errors}
                    merged = [r for r in merged if r['lot_no'] not in problem_lots]
                    if not merged:
                        CustomMessageBox.showwarning(self.root, "경고", "유효한 LOT이 없습니다.")
                        return

                for row in merged:
                    try:
                        from engine_modules.constants import get_tonbag_unit_weight
                        unit_w = get_tonbag_unit_weight(self.engine.db, row['lot_no'])
                    except Exception:
                        unit_w = 500.0
                    unit_mt = unit_w / 1000.0
                    row['sublot_count'] = max(1, int(row['qty_mt'] / unit_mt + 0.001))

                dlg = AllocationDialog(self, self.engine)
                dlg.show_with_data(merged)

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

    def _show_allocation_approval_queue(self) -> None:
        """출고 > Allocation 승인 대기 화면."""
        try:
            from ..dialogs.allocation_approval_dialog import AllocationApprovalDialog
            AllocationApprovalDialog(self).show_queue()
        except Exception as e:
            logger.error(f"Allocation 승인 대기 화면 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.root, "오류", f"승인 대기 화면을 열 수 없습니다:\n{e}")

    def _show_allocation_approval_history(self) -> None:
        """출고 > 승인 이력 조회 화면."""
        try:
            from ..dialogs.allocation_approval_dialog import AllocationApprovalDialog
            AllocationApprovalDialog(self).show_history()
        except Exception as e:
            logger.error(f"Allocation 승인 이력 화면 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.root, "오류", f"승인 이력 화면을 열 수 없습니다:\n{e}")

    def _apply_approved_allocation(self) -> None:
        """승인 완료(STAGED/APPROVED) 건을 RESERVED로 반영."""
        if not hasattr(self, "engine") or not self.engine:
            CustomMessageBox.showwarning(self.root, "확인", "엔진이 초기화되지 않았습니다.")
            return
        if not hasattr(self.engine, "apply_approved_allocation_reservations"):
            CustomMessageBox.showwarning(self.root, "기능 없음", "승인분 예약 반영 엔진이 없습니다.")
            return
        if not CustomMessageBox.askyesno(
            self.root,
            "예약 반영",
            "승인 완료된 Allocation(STAGED)을 RESERVED로 반영하시겠습니까?",
        ):
            return
        try:
            if hasattr(self, "do_action_tx"):
                result = self.do_action_tx(
                    "APPLY_APPROVED_ALLOCATION",
                    lambda: self.engine.apply_approved_allocation_reservations(),
                    parent=self.root,
                    refresh_mode="deferred",
                )
            else:
                result = self.engine.apply_approved_allocation_reservations()
            if result.get("success"):
                msg = f"예약 반영 완료: {result.get('applied', 0)}건"
                errs = result.get("errors", [])
                if errs:
                    msg += "\n\n미반영 사유:\n" + "\n".join(errs[:5])
                CustomMessageBox.showinfo(self.root, "완료", msg)
                if not hasattr(self, "do_action_tx"):
                    self._refresh_after_outbound_action("APPLY_APPROVED_ALLOCATION")
            else:
                errs = "\n".join(result.get("errors", [])[:8]) or "반영된 건이 없습니다."
                CustomMessageBox.showwarning(self.root, "예약 반영 결과", errs)
        except Exception as e:
            logger.error(f"승인분 예약 반영 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.root, "오류", f"예약 반영 중 오류가 발생했습니다.\n{e}")
