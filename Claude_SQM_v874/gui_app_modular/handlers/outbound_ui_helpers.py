# -*- coding: utf-8 -*-
"""
SQM Inventory - Outbound UI Helpers Mixin (HE)
================================================

v8.7.4 - Extracted from outbound_handlers.py

Other/utility handler functions: revert, barcode scan, swap report, shared helpers
"""

from gui_app_modular.utils.ui_constants import create_themed_toplevel  # v8.0.9
from gui_app_modular.utils.ui_constants import tc
import logging
import csv
import os
from datetime import datetime

from ..utils.ui_constants import CustomMessageBox, setup_dialog_geometry_persistence
from utils.path_utils import get_app_base_dir
logger = logging.getLogger(__name__)


class OutboundUIHelpersMixin:
    """Outbound UI helpers mixin (HE).

    Mixed into OutboundHandlersMixin → SQMInventoryApp.
    """

    def _refresh_after_outbound_action(self, reason: str) -> None:
        """출고/취소 계열 액션 이후 표준 새로고침 진입점.
        v8.1.8: Return / Move 탭 갱신 추가.
        """
        if hasattr(self, 'refresh_bus_deferred'):
            self.refresh_bus_deferred(reason=reason, delay_ms=50)
            return
        self._safe_refresh()
        for fn_name in (
            '_refresh_inventory',
            '_refresh_tonbag',
            '_refresh_allocation',
            '_refresh_picked',
            '_refresh_sold',
            '_refresh_dashboard',
            '_refresh_return_tab',   # v8.1.8: Return 탭
            '_refresh_move_tab',     # v8.1.8: Move 탭
        ):
            fn = getattr(self, fn_name, None)
            if callable(fn):
                try:
                    fn()
                except Exception as _e:
                    logger.debug(f"[refresh_after_outbound] {fn_name}: {_e}")

    def _on_go_scan_tab(self) -> None:
        """📷 스캔 탭으로 이동 (v7.4.0) — v8.1.6: 위젯 참조 단일화."""
        notebook = getattr(self, 'notebook', None)
        if not notebook:
            return
        target_tab = getattr(self, 'tab_scan', None)
        if target_tab is None:
            logger.debug("[스캔탭] tab_scan 미등록 — 탭 이동 스킵")
            return
        try:
            notebook.select(target_tab)
        except Exception as e:
            logger.debug(f"[스캔탭] 탭 선택 실패: {e}")

    def _on_revert_picked_to_reserved(self) -> None:
        """판매화물 결정 취소: PICKED → RESERVED(판매 배정).
        v8.1.8: 탭에서 LOT 선택 시 선택분만, 미선택 시 다이얼로그.
        """
        engine = getattr(self, 'engine', None)
        if not engine or not hasattr(engine, 'revert_picked_to_reserved'):
            CustomMessageBox.showwarning(
                self.root, '기능 없음',
                'revert_picked_to_reserved()를 사용할 수 없습니다.'
            )
            return

        # ── 탭에서 선택된 LOT 먼저 확인 ───────────────────────────────────
        pre_selected = []
        for attr in ('tree_picked', 'tree_picked_detail'):
            tree = getattr(self, attr, None)
            if tree:
                for iid in tree.selection():
                    vals = tree.item(iid).get('values', [])
                    lot_no = str(vals[0]).strip() if vals else ''
                    if lot_no and lot_no not in pre_selected:
                        pre_selected.append(lot_no)
                if pre_selected:
                    break

        # ── 전체 대상 목록 조회 ────────────────────────────────────────────
        try:
            rows = engine.db.fetchall(
                "SELECT DISTINCT lot_no FROM allocation_plan "
                "WHERE status = 'EXECUTED' ORDER BY lot_no"
            )
        except Exception:
            rows = []
        lot_list = [str(r.get('lot_no', '')).strip() for r in (rows or []) if r.get('lot_no')]

        if not lot_list:
            CustomMessageBox.showinfo(
                self.root, '대상 없음',
                '되돌릴 판매화물 결정(PICKED) 건이 없습니다.'
            )
            return

        # 탭 선택 항목이 있으면 바로 실행 ─────────────────────────────────
        if pre_selected:
            msg = (f"선택한 {len(pre_selected)}개 LOT를\n"
                   "판매 배정(RESERVED)으로 되돌립니다.\n계속하시겠습니까?")
            if not CustomMessageBox.askyesno(self.root, '판매화물 결정 취소', msg):
                return
            total, result_msg = self._run_revert_picked_to_reserved(engine, pre_selected)
            CustomMessageBox.showinfo(self.root, '취소 완료', result_msg)
            self._refresh_after_outbound_action("REVERT_PICKED_SELECTED")
            return

        self._show_revert_lot_dialog(
            title='판매화물 결정 취소 (→ 판매 배정)',
            lot_list=lot_list,
            confirm_message='선택한 LOT을 판매 배정(RESERVED)으로 되돌립니다.',
            revert_all_message='전체를 판매 배정으로 되돌립니다.',
            revert_fn=lambda lot_nos: self._run_revert_picked_to_reserved(engine, lot_nos),
        )

    def _run_revert_picked_to_reserved(self, engine, lot_nos):
        total = 0
        for lot_no in lot_nos:
            r = engine.revert_picked_to_reserved(lot_no=lot_no)
            total += r.get('reverted', 0)
        return total, f"{total}건 → 판매 배정(RESERVED)"

    def _on_revert_outbound_to_available(self) -> None:
        """출고 취소: OUTBOUND/SOLD → AVAILABLE 직접 복귀.
        v8.1.8 BUG-A 수정: 'SOLD' 하드코딩 → STATUS_OUTBOUND + 'SOLD' 병행 조회.
        탭에서 LOT 선택 시 선택분만, 미선택 시 다이얼로그 표시.
        """
        engine = getattr(self, 'engine', None)
        if not engine or not hasattr(engine, 'revert_sold_to_picked'):
            CustomMessageBox.showwarning(
                self.root, '기능 없음',
                'revert_sold_to_picked()를 사용할 수 없습니다.'
            )
            return

        # ── 탭에서 선택된 LOT 먼저 확인 (Q2: 선택 우선 방식) ──────────────
        pre_selected = []
        for attr in ('tree_sold', 'tree_sold_detail'):
            tree = getattr(self, attr, None)
            if tree:
                for iid in tree.selection():
                    vals = tree.item(iid).get('values', [])
                    lot_no = str(vals[0]).strip() if vals else ''
                    if lot_no and lot_no not in pre_selected:
                        pre_selected.append(lot_no)
                if pre_selected:
                    break

        # ── 전체 대상 목록 조회 (OUTBOUND + SOLD 모두) ─────────────────────
        try:
            rows = engine.db.fetchall(
                "SELECT DISTINCT lot_no FROM inventory_tonbag "
                "WHERE status IN ('OUTBOUND', 'SOLD') ORDER BY lot_no"
            )
        except Exception:
            rows = []
        lot_list = [str(r.get('lot_no', '')).strip() for r in (rows or []) if r.get('lot_no')]

        if not lot_list:
            CustomMessageBox.showinfo(
                self.root, '대상 없음',
                '되돌릴 출고(OUTBOUND/SOLD) 건이 없습니다.'
            )
            return

        # 탭 선택 항목이 있으면 바로 확인 후 실행 ──────────────────────────
        if pre_selected:
            msg = (f"선택한 {len(pre_selected)}개 LOT의 출고를 취소하여\n"
                   "AVAILABLE(판매가능)으로 되돌립니다.\n계속하시겠습니까?")
            if not CustomMessageBox.askyesno(self.root, '출고 취소', msg):
                return
            total, result_msg = self._run_revert_sold_to_picked(engine, pre_selected)
            CustomMessageBox.showinfo(self.root, '취소 완료', result_msg)
            self._refresh_after_outbound_action("REVERT_OUTBOUND_SELECTED")
            return

        # 선택 없으면 다이얼로그 표시 ─────────────────────────────────────
        self._show_revert_lot_dialog(
            title='출고 취소 (→ AVAILABLE)',
            lot_list=lot_list,
            confirm_message='선택한 LOT을 AVAILABLE(판매가능)으로 되돌립니다.',
            revert_all_message='전체 출고를 취소하여 AVAILABLE로 되돌립니다.',
            revert_fn=lambda lot_nos: self._run_revert_sold_to_picked(engine, lot_nos),
        )

    # 하위 호환 alias — sold_tab의 _safe_call('_on_revert_sold_to_picked') 유지
    _on_revert_sold_to_picked = _on_revert_outbound_to_available

    def _run_revert_sold_to_picked(self, engine, lot_nos):
        """출고 취소 실행 — OUTBOUND/SOLD → AVAILABLE."""
        total = 0
        for lot_no in lot_nos:
            r = engine.revert_sold_to_picked(lot_no=lot_no)
            total += r.get('reverted', 0)
        return total, f"{total}건 → AVAILABLE (출고 취소 완료)"

    def _show_revert_lot_dialog(
        self,
        title,
        lot_list,
        confirm_message,
        revert_all_message,
        revert_fn,
    ) -> None:
        """LOT 목록 다중 선택 다이얼로그 — 일부/전체 취소 공통."""
        import tkinter as tk
        from tkinter import ttk

        d = create_themed_toplevel(self.root)
        d.title(title)
        d.transient(self.root)
        d.grab_set()
        f = ttk.Frame(d, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="취소할 LOT를 선택하세요 (일부 또는 [전체 선택] 후 선택 취소).").pack(anchor=tk.W)
        lb_frame = ttk.Frame(f)
        lb_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 8))
        scroll = tk.Scrollbar(lb_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        lb = tk.Listbox(lb_frame, selectmode=tk.EXTENDED, height=12, yscrollcommand=scroll.set, font=('Consolas', 10))
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=lb.yview)
        for lot in lot_list:
            lb.insert(tk.END, lot)

        def select_all():
            lb.selection_set(0, tk.END)

        def do_revert():
            sel = lb.curselection()
            lot_nos = [lot_list[i] for i in sel] if sel else []
            if not lot_nos:
                CustomMessageBox.showwarning(
                    d, '선택 필요',
                    'LOT을 선택하거나 [전체 선택] 버튼으로 전부 선택한 뒤 [선택 취소]를 누르세요.'
                )
                return
            if len(lot_nos) == len(lot_list):
                msg = revert_all_message
            else:
                msg = f"선택한 {len(lot_nos)}개 LOT에 대해 취소합니다.\n{confirm_message}"
            if not CustomMessageBox.askyesno(d, '확인', msg + '\n계속하시겠습니까?'):
                return
            total, result_msg = revert_fn(lot_nos)
            d.destroy()
            CustomMessageBox.showinfo(self.root, '취소 완료', result_msg)
            self._refresh_after_outbound_action("REVERT_LOT_DIALOG_ACTION")

        btn_f = ttk.Frame(f)
        btn_f.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(btn_f, text="전체 선택", command=select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="선택 취소", command=do_revert).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="닫기", command=d.destroy).pack(side=tk.LEFT, padx=2)
        try:
            from ..utils.ui_constants import setup_dialog_geometry_persistence
            setup_dialog_geometry_persistence(d, "revert_lot_dialog", self.root, "large")
        except Exception:
            d.geometry("500x400")
        d.update_idletasks()
        try:
            from ..utils.ui_constants import center_dialog
            center_dialog(d, self.root)
        except Exception as e:
            logger.debug(f"[출고UI] 다이얼로그 센터링 실패: {e}")

    def _on_barcode_scan_upload(self) -> None:
        """v6.12 Stage3: 바코드 스캔 파일 업로드 → UID 대조 + PICKED→SOLD"""
        from tkinter import filedialog
        import tkinter.messagebox as mb
        import os

        file_path = filedialog.askopenfilename(
            parent=self.root,
            title="바코드 스캔 파일 선택 (CSV/Excel/TXT)",
            filetypes=[("스캔 파일", "*.csv;*.xlsx;*.xls;*.txt"), ("모든 파일", "*.*")]
        )
        if not file_path:
            return

        try:
            from core.barcode_scan_engine import BarcodeScanEngine
            scanner = BarcodeScanEngine(self.engine.db, engine=self.engine)  # v8.0.2 P2

            # Phase3: 랜덤 출고 모드(리오님 운영) — 스캔 즉시 확정(OUT=SOLD)
            #   - 환경변수로 강제 가능: SQM_OUTBOUND_MODE=random_scan_confirm
            outbound_mode = (os.environ.get('SQM_OUTBOUND_MODE', 'random_scan_confirm') or '').strip().lower()

            # v8.6.5: SALE REF 선택 _oh_ 헬퍼 위임
            selected_sale_ref, _sr_cancelled = self._oh_barcode_select_sale_ref(
                scanner,
                prompt_msg="이번 바코드 스캔 대상 SALE REF를 정확히 1개 입력하세요.\n",
                error_msg="유효하지 않은 SALE REF 입니다. 목록의 값 중 1개를 정확히 입력하세요.",
            )
            if _sr_cancelled:
                return

            scanned_codes = scanner.read_scan_file(file_path)
            if not scanned_codes:
                mb.showwarning("스캔 파일 비어있음", "스캔 파일에 유효한 UID가 없습니다.", parent=self.root)
                return

            # ------------------------------
            # Phase 3 (RUBI) : Random Scan Confirm
            # ------------------------------
            if outbound_mode in ('random_scan_confirm', 'random', 'scan_confirm'):
                try:
                    # All-or-Nothing 트랜잭션. Target 초과/UID 오류 1건이라도 있으면 전체 롤백.
                    result = scanner.process_barcode_scan_confirm_out(scanned_codes, sale_ref=selected_sale_ref)
                    if not isinstance(result, dict) or not result.get('success'):
                        err = (result.get('errors') or ['출고 확정 실패'])[0] if isinstance(result, dict) else '출고 확정 실패'
                        mb.showerror('출고 확정 실패', str(err), parent=self.root)
                        return

                    confirmed = int(result.get('confirmed', 0) or 0)
                    # LOT별 진행 현황 요약
                    lot_cnt = len({r.get('lot_no') for r in (result.get('rows') or []) if isinstance(r, dict) and r.get('lot_no')})
                    mb.showinfo(
                        '바코드 스캔 출고 확정 완료',
                        f"✅ 스캔 즉시 확정 완료\n\n- 확정 톤백: {confirmed}건\n- LOT 수: {lot_cnt}개\n\n(Phase3 규칙: 스캔=확정)",
                        parent=self.root,
                    )

                                        # Phase4: 스캔 확정 리포트 자동 저장(CSV)
                    try:
                        from core.config import OUTPUT_DIR
                        report_path = scanner.export_scan_confirm_report_csv(
                            result.get('rows') or [],
                            output_dir=str(OUTPUT_DIR),
                            prefix=f"OUTBOUND_SCAN_{(selected_sale_ref or 'NO_SALEREF')}",
                        )
                        if report_path:
                            logger.info(f"[Phase4] outbound scan report saved: {report_path}")
                    except Exception as _re:
                        logger.debug(f"[Phase4] report export skipped: {_re}")

                    if hasattr(self, '_refresh_after_outbound_action'):
                        self._refresh_after_outbound_action('PHASE3_SCAN_CONFIRM_OUT')
                    if hasattr(self, '_refresh_tonbag_list'):
                        self._refresh_tonbag_list()
                    return
                except Exception as e:
                    # BarcodeScanEngine 내부에서 RuntimeError(json)로 실패 상세를 올 수 있음.
                    mb.showerror('출고 확정 실패', str(e), parent=self.root)
                    return

            expected_uids = scanner.get_picked_uids(sale_ref=selected_sale_ref)
            if not expected_uids:
                lot_reserved = 0
                try:
                    lot_reserved = scanner.get_lot_mode_reserved_count()
                except Exception:
                    lot_reserved = 0
                if lot_reserved <= 0:
                    mb.showwarning(
                        "PICKED 톤백 없음",
                        "PICKED 상태 톤백이 없습니다.\n출고 실행을 먼저 진행하세요.",
                        parent=self.root
                    )
                    return
                if not mb.askyesno(
                    "LOT 단위 예약 스캔",
                    f"PICKED 톤백은 없지만 LOT 단위 예약 {lot_reserved}건이 있습니다.\n"
                    "이번 스캔을 LOT 단위 예약 확정(SOLD)으로 처리할까요?",
                    parent=self.root,
                ):
                    return
                if hasattr(self, 'do_action_tx'):
                    sold_result = self.do_action_tx(
                        "BARCODE_LOT_MODE_TO_SOLD",
                        lambda: scanner.process_barcode_scan_for_lot_mode(file_path),
                        parent=self.root,
                        refresh_mode="deferred",
                    )
                else:
                    sold_result = scanner.process_barcode_scan_for_lot_mode(file_path)

                if not isinstance(sold_result, dict):
                    mb.showerror("오류", "바코드 스캔 결과 형식이 올바르지 않습니다.", parent=self.root)
                    return
                if sold_result.get('success') is False and sold_result.get('sold', 0) <= 0:
                    err = (sold_result.get('errors') or ['처리 실패'])[0]
                    mb.showerror("오류", f"LOT 단위 스캔 처리 실패:\n{err}", parent=self.root)
                    return
                msg = (
                    f"LOT 단위 스캔 출고 완료: {sold_result.get('sold', 0)}건 SOLD 전환\n"
                    f"잔여 LOT 예약: {sold_result.get('remaining_lot_reserved', 0)}건"
                )
                if sold_result.get('not_found'):
                    msg += f"\n⚠️ 미매칭 UID: {len(sold_result.get('not_found', []))}건"
                if sold_result.get('no_plan'):
                    msg += f"\n⚠️ 예약 계획 없는 UID: {len(sold_result.get('no_plan', []))}건"
                mb.showinfo("LOT 단위 스캔 출고 완료", msg, parent=self.root)
                if not hasattr(self, 'do_action_tx'):
                    self._refresh_after_outbound_action("BARCODE_LOT_MODE_TO_SOLD")
                if hasattr(self, '_refresh_tonbag_list'):
                    self._refresh_tonbag_list()
                return

            verify = scanner.verify_outbound_scan(
                expected_uids=expected_uids,
                scanned_uids_raw=scanned_codes,
                outbound_ref=f"SCAN-{os.path.basename(file_path)}",
                scan_file_name=os.path.basename(file_path),
                sale_ref=selected_sale_ref or '',
            )

            if verify['result'] == 'FAIL':
                msg = verify['message'] + "\n\n"
                if verify['missing']:
                    msg += f"누락 UID ({len(verify['missing'])}개):\n"
                    for u in verify['missing'][:10]: msg += f"  - {u}\n"
                if verify['extra']:
                    msg += f"\n초과 UID ({len(verify['extra'])}개):\n"
                    for u in verify['extra'][:10]: msg += f"  - {u}\n"
                mb.showerror("UID 대조 실패 — 출고 중단", msg, parent=self.root)
                return

            if verify.get('result') == 'PASS_SWAP':
                lot_preview = ", ".join((verify.get('swap_lots') or [])[:8])
                if len(verify.get('swap_lots') or []) > 8:
                    lot_preview += f" ... 외 {len(verify.get('swap_lots') or []) - 8}개"
                verify_msg = (
                    f"{verify['message']}\n\n"
                    f"대상 LOT: {lot_preview or '-'}\n"
                    f"같은 LOT 내부에서만 스왑 출고가 허용됩니다."
                )
            else:
                verify_msg = verify['message']

            if not mb.askyesno("UID 대조 통과", f"{verify_msg}\n\nPICKED → SOLD 전환하시겠습니까?", parent=self.root):
                return

            # TOCTOU 방지: 실행 직전에 동일 스캔 데이터로 재검증
            reverify = scanner.verify_outbound_scan(
                expected_uids=expected_uids,
                scanned_uids_raw=scanned_codes,
                outbound_ref=f"SCAN-RECHECK-{os.path.basename(file_path)}",
                scan_file_name=os.path.basename(file_path),
                sale_ref=selected_sale_ref or '',
            )
            if reverify.get('result') == 'FAIL':
                mb.showerror(
                    "재검증 실패",
                    "실행 직전 상태가 변경되어 출고를 중단했습니다.\n"
                    "다시 조회 후 재시도하세요.",
                    parent=self.root,
                )
                return

            if hasattr(self, 'do_action_tx'):
                sold_result = self.do_action_tx(
                    "BARCODE_SCAN_TO_SOLD",
                    lambda: scanner.process_barcode_scan_to_sold(scanned_codes, sale_ref=selected_sale_ref),
                    parent=self.root,
                    refresh_mode="deferred",
                )
            else:
                sold_result = scanner.process_barcode_scan_to_sold(scanned_codes, sale_ref=selected_sale_ref)

            if not isinstance(sold_result, dict):
                mb.showerror("오류", "바코드 스캔 결과 형식이 올바르지 않습니다.", parent=self.root)
                return
            if sold_result.get('success') is False and sold_result.get('sold', 0) <= 0:
                err = (sold_result.get('errors') or ['처리 실패'])[0]
                mb.showerror("오류", f"바코드 스캔 처리 실패:\n{err}", parent=self.root)
                return

            msg = f"출고 완료: {sold_result.get('sold', 0)}건 SOLD 전환\n"
            if sold_result.get('swap_count', 0) > 0:
                msg += f"\n🔁 LOT 내부 Swap 적용: {sold_result.get('swap_count', 0)}건\n"
            if sold_result.get('not_found'):
                msg += f"\n⚠️ 미매칭: {len(sold_result.get('not_found', []))}건\n"
            if sold_result.get('remaining_picked', 0) > 0:
                msg += f"\n⚠️ 잔여 PICKED: {sold_result.get('remaining_picked', 0)}건\n"
            mb.showinfo("바코드 스캔 출고 완료", msg, parent=self.root)

            if not hasattr(self, 'do_action_tx'):
                self._refresh_after_outbound_action("BARCODE_SCAN_TO_SOLD")
            if hasattr(self, '_refresh_tonbag_list'):
                self._refresh_tonbag_list()

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"바코드 스캔 오류: {e}", exc_info=True)
            mb.showerror("오류", f"바코드 스캔 처리 중 오류:\n{e}", parent=self.root)

    def _on_barcode_live_scan(self) -> None:
        """(Phase4) 실시간 바코드 스캔(USB 스캐너 Enter) → 즉시 확정(OUT=SOLD)
        - 파일 업로드 없이, 스캐너가 입력+Enter를 치면 즉시 확정
        - Undo(최근 1건), 리포트 저장 지원
        """

        import tkinter as tk
        from tkinter import ttk
        import tkinter.messagebox as mb

        try:
            from core.barcode_scan_engine import BarcodeScanEngine
            scanner = BarcodeScanEngine(self.engine.db, engine=self.engine)  # v8.0.2 P2
        except Exception as e:
            mb.showerror("오류", f"바코드 엔진 로드 실패: {e}", parent=self.root)
            return

        # v8.6.5: SALE REF 선택 _oh_ 헬퍼 위임(선택 강제: Target 체크 정확도)
        selected_sale_ref, _sr_cancelled = self._oh_barcode_select_sale_ref(
            scanner,
            prompt_msg="실시간 스캔 대상 SALE REF를 정확히 1개 입력하세요.\n",
            error_msg="유효하지 않은 SALE REF 입니다.",
        )
        if _sr_cancelled:
            return

        d = create_themed_toplevel(self.root)
        d.title("📟 실시간 바코드 스캔 (Phase4: 스캔=즉시 확정)")
        d.transient(self.root)
        d.grab_set()
        setup_dialog_geometry_persistence(d, "barcode_live_scan_dialog", self.root, "medium")

        rows_confirmed = []
        var_status = tk.StringVar(value="대기: 바코드를 스캔하면 Enter로 입력됩니다.")
        var_cnt = tk.StringVar(value="확정 0 / 실패 0")

        top = ttk.Frame(d, padding=10)
        top.pack(fill=tk.BOTH, expand=True)

        ttk.Label(top, text="바코드 스캐너 입력창(자동 포커스):").pack(anchor="w")
        ent = ttk.Entry(top, width=40)
        ent.pack(fill=tk.X, pady=(4, 8))
        ent.focus_set()

        ttk.Label(top, textvariable=var_status).pack(anchor="w", pady=(0, 6))

        lb = tk.Listbox(top, height=12)
        lb.pack(fill=tk.BOTH, expand=True)

        btns = ttk.Frame(top)
        btns.pack(fill=tk.X, pady=(8, 0))

        def _update_counter():
            ok = sum(1 for r in rows_confirmed if r.get("success"))
            bad = sum(1 for r in rows_confirmed if not r.get("success"))
            var_cnt.set(f"확정 {ok} / 실패 {bad}")

        def _append_line(msg: str):
            lb.insert(tk.END, msg)
            lb.yview_moveto(1.0)

        def _confirm_from_entry(event=None):
            uid = (ent.get() or "").strip()
            ent.delete(0, tk.END)
            if not uid:
                return
            res = scanner.confirm_one_uid_live(uid, sale_ref=selected_sale_ref, source="live_scan")
            rows_confirmed.append(res)
            if res.get("success"):
                _append_line(f"✅ {res.get('uid')}  LOT={res.get('lot_no')}  {res.get('weight_kg')}kg")
                var_status.set(f"확정 OK: {res.get('uid')}")
            else:
                _append_line(f"❌ {res.get('uid')}  REASON={res.get('reason')}")
                var_status.set(f"확정 FAIL: {res.get('uid')} ({res.get('reason')})")
            _update_counter()
            try:
                if hasattr(self, '_refresh_tonbag_list'):
                    self._refresh_tonbag_list()
            except Exception:
                logger.debug("[SUPPRESSED] exception in outbound_handlers.py")  # noqa
            ent.focus_set()

        def _undo_last():
            res = scanner.undo_last_scan_confirm(sale_ref=selected_sale_ref)
            if res.get("success"):
                _append_line(f"↩️ UNDO OK: {res.get('uid','')}")
                var_status.set("최근 1건 Undo 완료")
                try:
                    if hasattr(self, '_refresh_tonbag_list'):
                        self._refresh_tonbag_list()
                except Exception:
                    logger.debug("[SUPPRESSED] exception in outbound_handlers.py")  # noqa
            else:
                _append_line(f"⚠️ UNDO FAIL: {res.get('message','')}")
                var_status.set(res.get("message","Undo 실패"))
            ent.focus_set()

        def _save_report():
            ok_rows = []
            for r in rows_confirmed:
                if isinstance(r, dict) and r.get("success"):
                    ok_rows.append(r)
            if not ok_rows:
                mb.showwarning("리포트 없음", "확정된 스캔이 없습니다.", parent=d)
                return
            try:
                from core.config import OUTPUT_DIR
                path = scanner.export_scan_confirm_report_csv(
                    rows=[{
                        "sale_ref": rr.get("sale_ref",""),
                        "customer": rr.get("customer",""),
                        "lot_no": rr.get("lot_no",""),
                        "tonbag_id": rr.get("tonbag_id",""),
                        "uid": rr.get("uid",""),
                        "weight_kg": rr.get("weight_kg",""),
                    } for rr in ok_rows],
                    output_dir=str(OUTPUT_DIR),
                    prefix=f"OUTBOUND_LIVE_{(selected_sale_ref or 'NO_SALEREF')}",
                )
                if path:
                    mb.showinfo("저장 완료", f"리포트 저장 완료:\n{path}", parent=d)
                else:
                    mb.showwarning("저장 실패", "리포트 저장에 실패했습니다.", parent=d)
            except Exception as e:
                mb.showerror("오류", f"리포트 저장 실패: {e}", parent=d)
            ent.focus_set()

        ttk.Button(btns, text="Undo(최근 1건)", command=_undo_last).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="리포트 저장(CSV)", command=_save_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="닫기", command=d.destroy).pack(side=tk.RIGHT, padx=2)

        ttk.Label(top, textvariable=var_cnt).pack(anchor="e", pady=(6, 0))

        ent.bind("<Return>", _confirm_from_entry)
        ent.bind("<KP_Enter>", _confirm_from_entry)

        d.update_idletasks()

    def _query_swap_report_rows(
        self,
        start_date: str,
        end_date: str,
        customer: str = "",
        lot_no: str = "",
        operator: str = "",
    ) -> list[dict]:
        """uid_swap_history 기반 Swap 리포트 조회 (기간/고객사/LOT/작업자 필터)."""
        sql = """
            SELECT
                s.created_at,
                s.lot_no,
                COALESCE(st.customer, t.picked_to, '') AS customer,
                COALESCE(st.created_by, 'barcode_scan_swap') AS operator,
                COALESCE(s.expected_uid, '') AS expected_uid,
                COALESCE(s.scanned_uid, '') AS scanned_uid,
                COALESCE(s.reason, '') AS reason
            FROM uid_swap_history s
            LEFT JOIN inventory_tonbag t ON t.id = s.scanned_tonbag_id
            LEFT JOIN (
                SELECT s1.*
                FROM sold_table s1
                INNER JOIN (
                    SELECT tonbag_id, MAX(id) AS max_id
                    FROM sold_table
                    GROUP BY tonbag_id
                ) m ON m.max_id = s1.id
            ) st ON st.tonbag_id = s.scanned_tonbag_id
            WHERE date(s.created_at) BETWEEN date(?) AND date(?)
              AND (? = '' OR s.lot_no LIKE ?)
              AND (? = '' OR COALESCE(st.customer, t.picked_to, '') LIKE ?)
              AND (? = '' OR COALESCE(st.created_by, 'barcode_scan_swap') LIKE ?)
            ORDER BY s.created_at DESC, s.id DESC
            LIMIT 5000
        """
        lot_like = f"%{lot_no.strip()}%" if lot_no.strip() else ""
        customer_like = f"%{customer.strip()}%" if customer.strip() else ""
        operator_like = f"%{operator.strip()}%" if operator.strip() else ""
        try:
            rows = self.engine.db.fetchall(
                sql,
                (
                    start_date.strip(),
                    end_date.strip(),
                    lot_no.strip(),
                    lot_like,
                    customer.strip(),
                    customer_like,
                    operator.strip(),
                    operator_like,
                ),
            )
            return rows or []
        except Exception as e:
            logger.error(f"Swap 리포트 조회 실패: {e}", exc_info=True)
            return []

    def _get_swap_report_save_dir(self, base_date_text: str) -> str:
        """Swap 리포트 저장 경로 고정: reports/swap/YYYY-MM."""
        month_token = datetime.now().strftime("%Y-%m")
        try:
            dt = datetime.strptime(base_date_text.strip(), "%Y-%m-%d")
            month_token = dt.strftime("%Y-%m")
        except (ValueError, TypeError) as e:
            logger.debug(f"[출고UI] 날짜 파싱 실패: {e}")
        root = get_app_base_dir()
        out_dir = os.path.join(root, "reports", "swap", month_token)
        os.makedirs(out_dir, exist_ok=True)
        return out_dir

    def _export_swap_report_csv(self, rows: list[dict], out_path: str) -> None:
        """Swap 리포트 CSV 저장."""
        headers = ["created_at", "lot_no", "customer", "operator", "expected_uid", "scanned_uid", "reason"]
        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(headers)
            for r in rows:
                w.writerow([str(r.get(h, "") or "") for h in headers])

    def _export_swap_report_xlsx(self, rows: list[dict], out_path: str) -> None:
        """Swap 리포트 XLSX 저장."""
        try:
            from openpyxl import Workbook
        except Exception as e:
            raise RuntimeError(f"openpyxl 미설치로 XLSX 저장 불가: {e}")
        wb = Workbook()
        ws = wb.active
        ws.title = "swap_report"
        headers = ["created_at", "lot_no", "customer", "operator", "expected_uid", "scanned_uid", "reason"]
        ws.append(headers)
        for r in rows:
            ws.append([str(r.get(h, "") or "") for h in headers])
        wb.save(out_path)

    def _show_swap_report_dialog(self) -> None:
        """Swap 리포트 팝업 (기간/고객사/LOT/작업자 필터 + CSV/XLSX 저장)."""
        import tkinter as tk
        from tkinter import ttk

        if not hasattr(self, "engine") or not getattr(self.engine, "db", None):
            CustomMessageBox.showwarning(self.root, "경고", "DB 연결이 없어 Swap 리포트를 열 수 없습니다.")
            return
        try:
            from core.barcode_scan_engine import BarcodeScanEngine
            BarcodeScanEngine(self.engine.db, engine=self.engine)  # v8.0.2 P2  # uid_swap_history 테이블 보장
        except Exception as e:
            logger.debug(f"Swap 리포트 테이블 준비 스킵: {e}")

        dlg = create_themed_toplevel(self.root)
        dlg.title("🔁 Swap 리포트")
        dlg.transient(self.root)
        dlg.grab_set()
        setup_dialog_geometry_persistence(dlg, "swap_report_dialog", self.root, "large")
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        today = datetime.now().strftime("%Y-%m-%d")
        start_var = tk.StringVar(value='')
        end_var = tk.StringVar(value='')
        customer_var = tk.StringVar()
        lot_var = tk.StringVar()
        operator_var = tk.StringVar()
        summary_var = tk.StringVar(value="조회 전")

        filter_frm = ttk.LabelFrame(frm, text="조회 조건")
        filter_frm.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(filter_frm, text="시작일(YYYY-MM-DD)").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        _e_start = ttk.Entry(filter_frm, textvariable=start_var, width=14)
        _e_start.grid(row=0, column=1, padx=4, pady=4, sticky="w")
        ttk.Label(filter_frm, text="종료일").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        _e_end = ttk.Entry(filter_frm, textvariable=end_var, width=14)
        _e_end.grid(row=0, column=3, padx=4, pady=4, sticky="w")
        # v8.1.8: 플레이스홀더 연결
        try:
            from gui_app_modular.utils.tree_enhancements import attach_date_placeholder
            attach_date_placeholder(_e_start, start_var)
            attach_date_placeholder(_e_end,   end_var)
        except Exception as e:
            logger.warning(f'[UI] outbound_handlers: {e}')
        ttk.Label(filter_frm, text="고객사").grid(row=0, column=4, padx=4, pady=4, sticky="w")
        ttk.Entry(filter_frm, textvariable=customer_var, width=18).grid(row=0, column=5, padx=4, pady=4, sticky="w")
        ttk.Label(filter_frm, text="LOT").grid(row=0, column=6, padx=4, pady=4, sticky="w")
        ttk.Entry(filter_frm, textvariable=lot_var, width=16).grid(row=0, column=7, padx=4, pady=4, sticky="w")
        ttk.Label(filter_frm, text="작업자").grid(row=0, column=8, padx=4, pady=4, sticky="w")
        ttk.Entry(filter_frm, textvariable=operator_var, width=14).grid(row=0, column=9, padx=4, pady=4, sticky="w")

        cols = ("created_at", "lot_no", "customer", "operator", "expected_uid", "scanned_uid", "reason")
        tree = ttk.Treeview(frm, columns=cols, show="headings", height=16)
        headings = {
            "created_at": "SWAP_AT",
            "lot_no": "LOT NO",
            "customer": "CUSTOMER",
            "operator": "OPERATOR",
            "expected_uid": "EXPECTED UID",
            "scanned_uid": "SCANNED UID",
            "reason": "REASON",
        }
        widths = {
            "created_at": 140,
            "lot_no": 110,
            "customer": 130,
            "operator": 110,
            "expected_uid": 180,
            "scanned_uid": 180,
            "reason": 220,
        }
        for c in cols:
            tree.heading(c, text=headings[c], anchor='center')
            tree.column(c, width=widths[c], anchor="center")
        ysb = tk.Scrollbar(frm, orient="vertical", command=tree.yview)
        xsb = tk.Scrollbar(frm, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        ysb.pack(fill=tk.Y, side=tk.RIGHT)
        xsb.pack(fill=tk.X)
        ttk.Label(frm, textvariable=summary_var).pack(fill=tk.X, pady=(4, 0))

        state = {"rows": []}

        def _load_rows():
            from gui_app_modular.utils.tree_enhancements import parse_date_range
            d_from, d_to = parse_date_range(
                start_var.get().strip(), end_var.get().strip()
            )
            # v8.1.8: 둘 다 비면 전체 기간. 하나라도 있으면 유효성 검사
            if d_from is None and d_to is None:
                # 전체 기간 — BETWEEN 조건 없이 조회
                rows = self._query_swap_report_rows(
                    start_date='2000-01-01',
                    end_date='2099-12-31',
                    customer=customer_var.get().strip(),
                    lot_no=lot_var.get().strip(),
                    operator=operator_var.get().strip(),
                )
            else:
                # 기간 입력 있으면 유효성 검사 후 조회
                _s = d_from or '2000-01-01'
                _e = d_to   or '2099-12-31'
                rows = self._query_swap_report_rows(
                    start_date=_s,
                    end_date=_e,
                    customer=customer_var.get().strip(),
                    lot_no=lot_var.get().strip(),
                    operator=operator_var.get().strip(),
                )
            state["rows"] = rows
            tree.delete(*tree.get_children(""))
            for r in rows:
                tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.get("created_at", ""),
                        r.get("lot_no", ""),
                        r.get("customer", ""),
                        r.get("operator", ""),
                        r.get("expected_uid", ""),
                        r.get("scanned_uid", ""),
                        r.get("reason", ""),
                    ),
                )
            summary_var.set(f"총 {len(rows)}건")

        def _save_csv():
            rows = state.get("rows", [])
            if not rows:
                CustomMessageBox.showwarning(dlg, "저장 불가", "저장할 데이터가 없습니다. 먼저 조회하세요.")
                return
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = self._get_swap_report_save_dir(start_var.get().strip() or today)
            out_name = f"swap_report_{start_var.get().strip()}_{end_var.get().strip()}_{ts}.csv"
            out_path = os.path.join(out_dir, out_name)
            self._export_swap_report_csv(rows, out_path)
            CustomMessageBox.showinfo(dlg, "저장 완료", f"CSV 저장 완료\n{out_path}")

        def _save_xlsx():
            rows = state.get("rows", [])
            if not rows:
                CustomMessageBox.showwarning(dlg, "저장 불가", "저장할 데이터가 없습니다. 먼저 조회하세요.")
                return
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = self._get_swap_report_save_dir(start_var.get().strip() or today)
            out_name = f"swap_report_{start_var.get().strip()}_{end_var.get().strip()}_{ts}.xlsx"
            out_path = os.path.join(out_dir, out_name)
            try:
                self._export_swap_report_xlsx(rows, out_path)
                CustomMessageBox.showinfo(dlg, "저장 완료", f"XLSX 저장 완료\n{out_path}")
            except Exception as e:
                CustomMessageBox.showerror(dlg, "저장 실패", f"XLSX 저장 실패:\n{e}")

        btn_frm = ttk.Frame(frm)
        btn_frm.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btn_frm, text="조회", command=_load_rows).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frm, text="CSV 저장", command=_save_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frm, text="XLSX 저장", command=_save_xlsx).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frm, text="닫기", command=dlg.destroy).pack(side=tk.RIGHT, padx=2)

        _load_rows()

    # ------------------------------------------------------------------
    # Shared allocation paste helpers (_oh_ prefix, v8.6.5 [SRP])
    # ------------------------------------------------------------------

    @staticmethod
    def _oh_parse_alloc_paste_rows(rows: list) -> tuple:
        """Allocation paste 데이터 행 파싱.

        Returns:
            (parsed, parse_errors) — parsed: list[dict], parse_errors: list[str]
        """
        _hdr_kw = {'lot_no', 'lot no', 'lotno', 'sap_no', 'product', 'qty'}
        if rows and str(rows[0].get('lot_no', '')).strip().lower().replace(' ', '_') in _hdr_kw:
            rows = rows[1:]
        parsed = []
        parse_errors = []
        for idx, r in enumerate(rows, 1):
            lot_no = str(r.get('lot_no', '')).strip()
            if not lot_no:
                continue
            raw_qty = str(r.get('qty_mt', '0')).replace(',', '').replace(' ', '').strip()
            try:
                qty = float(raw_qty) if raw_qty else 0.0
            except (ValueError, TypeError):
                parse_errors.append(f"행 {idx}: QTY 파싱 실패 '{r.get('qty_mt', '')}'")
                qty = 0.0
            if qty <= 0:
                parse_errors.append(f"행 {idx}: {lot_no} - QTY <= 0 (건너뜀)")
                continue
            row = dict(r)
            row['lot_no'] = lot_no
            row['qty_mt'] = qty
            parsed.append(row)
        return parsed, parse_errors

    @staticmethod
    def _oh_merge_alloc_lots(parsed: list) -> list:
        """파싱된 행을 LOT별로 qty 합산 병합. merged list 반환."""
        from collections import OrderedDict
        lot_merged = OrderedDict()
        for row in parsed:
            ln = row['lot_no']
            if ln in lot_merged:
                lot_merged[ln]['qty_mt'] += row['qty_mt']
            else:
                lot_merged[ln] = dict(row)
        return list(lot_merged.values())

    def _oh_validate_alloc_lot_nos(self, merged: list) -> list:
        """LOT 가용성 DB 검증. validation_errors list 반환."""
        lot_nos = [r['lot_no'] for r in merged]
        validation_errors = []
        try:
            placeholders = ",".join("?" * len(lot_nos))
            avail_rows = self.engine.db.fetchall(
                f"SELECT lot_no, COUNT(*) as avail_cnt "
                f"FROM inventory_tonbag "
                f"WHERE lot_no IN ({placeholders}) AND status='AVAILABLE' "
                f"AND COALESCE(is_sample,0)=0 "
                f"GROUP BY lot_no",
                tuple(lot_nos),
            )
            avail_map = {r['lot_no']: r['avail_cnt'] for r in avail_rows}
            for row in merged:
                if row['lot_no'] not in avail_map:
                    validation_errors.append(f"❌ {row['lot_no']}: LOT 미등록 또는 가용 톤백 없음")
        except Exception as e:
            logger.warning(f"빠른 출고 사전 검증 실패 (계속 진행): {e}")
        return validation_errors

    # ------------------------------------------------------------------
    # Barcode scan helpers (_oh_ prefix, v8.6.5 [SRP])
    # ------------------------------------------------------------------

    def _oh_barcode_select_sale_ref(
        self,
        scanner,
        prompt_msg: str = "바코드 스캔 대상 SALE REF를 정확히 1개 입력하세요.\n",
        error_msg: str = "유효하지 않은 SALE REF 입니다. 목록의 값 중 1개를 정확히 입력하세요.",
    ) -> tuple:
        """PICKED SALE REF 선택 플로우.

        Returns:
            (selected_sale_ref, cancelled) — cancelled=True 이면 호출자는 즉시 return.
        """
        import tkinter.messagebox as mb
        sale_refs = scanner.get_picked_sale_refs()
        if len(sale_refs) == 1:
            return sale_refs[0], False
        if len(sale_refs) > 1:
            pick_hint = ", ".join(sale_refs[:10])
            if len(sale_refs) > 10:
                pick_hint += f" ... 외 {len(sale_refs) - 10}건"
            selected = CustomMessageBox.askstring(
                self.root,
                "SALE REF 선택",
                prompt_msg + f"(선택 가능: {pick_hint})",
            )
            if not selected:
                return None, True
            selected = selected.strip()
            if selected not in sale_refs:
                mb.showerror("SALE REF 오류", error_msg, parent=self.root)
                return None, True
            return selected, False
        return None, False
