# -*- coding: utf-8 -*-
"""
SQM Inventory - Picking Flow Mixin (HC)
=========================================

v8.7.4 - Extracted from outbound_handlers.py

Picking-related UI handlers (8 functions)
"""

from gui_app_modular.utils.ui_constants import create_themed_toplevel  # v8.0.9
import logging
import os
import json
from datetime import datetime

from ..utils.ui_constants import CustomMessageBox
logger = logging.getLogger(__name__)

# v8.0.6 [PICKING-REVIEW] 피킹리스트 첫 행 검수 패치
try:
    from features.parsers.picking_candidate_patch import enrich_picking_doc_with_review
    _HAS_PICKING_REVIEW = True
except ImportError:
    _HAS_PICKING_REVIEW = False


class PickingFlowMixin:
    """Picking flow mixin (HC).

    Mixed into OutboundHandlersMixin → SQMInventoryApp.
    """

    def _on_picking_list_upload(self) -> None:
        """
        v6.9.1: 피킹 리스트 업로드.
        ① PDF 파일 선택 (취소 시 즉시 종료 — UX 개선)
        ② 피킹 템플릿 선택 (고객사 프로파일 팝업)
        ③ Gate-1 교차검증 → RESERVED→PICKED
        """
        # ── v6.9.1 [FIX-4]: PDF 먼저 선택 → 취소 시 템플릿 팝업 안 뜸 ──
        from ..utils.constants import filedialog

        path = filedialog.askopenfilename(
            parent=self.root,
            title="Picking List PDF 선택",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path or not path.strip():
            return

        # ── 템플릿 선택 팝업 (PDF 선택 후) ──────────────────────────────
        _picking_tpl = [None]

        def _on_tpl_chosen(t: dict):
            _picking_tpl[0] = t

        try:
            from ..dialogs.picking_template_dialog import PickingTemplateDialog
            current_theme = getattr(self, '_current_theme', 'darkly')
            PickingTemplateDialog(
                self.root, self.engine,
                current_theme=current_theme,
                on_select_callback=_on_tpl_chosen,
            )
        except Exception as _tpl_err:
            logger.warning(f"[outbound] 피킹 템플릿 팝업 오류(무시): {_tpl_err}")

        if _picking_tpl[0] is None:
            return

        _tpl = _picking_tpl[0]
        logger.info(
            f"[outbound] 피킹 템플릿 선택: {_tpl.get('template_id','?')}: "
            f"/ {_tpl.get('customer','')} / {_tpl.get('bag_weight_kg',500)}kg"
        )

        # ── Gate-1 경로 시도 → 실패 시 레거시 경로 ──
        if self._oh_picking_gate1_flow(path, _tpl):
            return
        self._oh_picking_legacy_flow(path)

    # ── B05 헬퍼: Gate-1 피킹 플로우 ────────────────────────────────
    def _oh_picking_gate1_flow(self, path: str, _tpl: dict) -> bool:
        """Gate-1 교차검증 피킹 플로우. 성공 시 True, ImportError 시 False."""
        try:
            from parsers.document_parser_modular.picking_mixin import PickingListParserMixin
            parser = PickingListParserMixin()
            picking_result = parser.parse_picking_list(path)

            self._oh_picking_inject_tpl_meta(picking_result, _tpl)
            meta = picking_result.meta
            if not picking_result.success:
                errs = '\n'.join(picking_result.errors[:5])
                CustomMessageBox.showerror(
                    self.root, '피킹리스트 파싱 실패',
                    f'PDF 파싱 중 오류:\n\n{errs}'
                )
                return True
            warnings = list(getattr(picking_result, 'warnings', []))
            if warnings:
                top_warnings = '\n'.join(f'- {w}' for w in warnings[:5])
                if not CustomMessageBox.askyesno(
                    self.root, '피킹리스트 경고',
                    f'파싱 경고 {len(warnings)}건이 확인되었습니다.\n\n'
                    f'{top_warnings}\n\n'
                    f'경고를 확인하고 계속 진행하시겠습니까?'
                ):
                    return True
            summary = picking_result.summary
            meta = picking_result.meta
            if not CustomMessageBox.askyesno(
                self.root, '피킹리스트 확인',
                f'[피킹리스트 파싱 완료]\n\n'
                f'피킹 No    : {getattr(meta, "picking_no", "")}\n'
                f'Sales Order: {getattr(meta, "sales_order", "")}\n'
                f'총 LOT     : {summary.get("total_lots", 0)}개\n'
                f'총 중량    : {summary.get("total_mt", 0):.1f} MT\n\n'
                f'Gate-1 교차검증을 진행하시겠습니까?'
            ):
                return True
            if not hasattr(self.engine, 'gate1_verify_picking'):
                CustomMessageBox.showerror(
                    self.root, '기능 없음',
                    'gate1_verify_picking() 미구현'
                )
                return True
            gate1 = self.engine.gate1_verify_picking(
                picking_result, getattr(meta, 'picking_no', '')
            )

            self._save_gate1_result_json(gate1, getattr(meta, 'picking_no', ''))

            if not gate1['passed']:
                self._oh_picking_show_gate1_fail(gate1, meta)
                return True

            if not self._oh_picking_confirm_gate1_proceed(gate1, meta):
                return True

            self._oh_picking_execute_gate1(picking_result, meta, gate1)
            return True
        except ImportError:
            logger.debug("[SUPPRESSED] exception in outbound_handlers.py")  # noqa
            return False

    def _oh_picking_show_gate1_fail(self, gate1: dict, meta) -> None:
        """Gate-1 실패 시 결과 다이얼로그 표시."""
        try:
            from ..dialogs.gate1_result_dialog import Gate1ResultDialog
            current_theme = getattr(self, '_current_theme', 'darkly')
            Gate1ResultDialog(
                self.root, gate1,
                picking_no=getattr(meta, 'picking_no', ''),
                on_proceed=None,
                current_theme=current_theme,
            )
        except ImportError:
            CustomMessageBox.showerror(
                self.root, 'Gate-1 교차검증 실패',
                gate1['error_report'][:800]
            )
        self._save_gate1_report(gate1, getattr(meta, 'picking_no', ''))

    def _oh_picking_confirm_gate1_proceed(self, gate1: dict, meta) -> bool:
        """Gate-1 통과 후 사용자 확인. 진행 시 True."""
        _proceed_flag = [False]

        def _do_execute():
            _proceed_flag[0] = True

        try:
            from ..dialogs.gate1_result_dialog import Gate1ResultDialog
            current_theme = getattr(self, '_current_theme', 'darkly')
            Gate1ResultDialog(
                self.root, gate1,
                picking_no=getattr(meta, 'picking_no', ''),
                on_proceed=_do_execute,
                current_theme=current_theme,
            )
        except ImportError:
            matched = len(gate1['matched_lots'])
            if CustomMessageBox.askyesno(
                self.root, '판매화물 결정 실행',
                f'Gate-1 통과\n\n매칭된 LOT: {matched}개\n\n'
                f'{matched}개 LOT을 [판매화물 결정] 상태로 전환합니다.\n계속하시겠습니까?'
            ):
                _proceed_flag[0] = True

        return _proceed_flag[0]

    def _oh_picking_execute_gate1(self, picking_result, meta, gate1: dict) -> None:
        """Gate-1 통과 후 실제 실행."""
        allow_qty_mismatch = False
        approval_reason = ''
        if gate1.get('requires_approval'):
            allow_qty_mismatch, approval_reason, _approved = self._oh_picking_admin_approval()
            if not _approved:
                return

        if hasattr(self, 'do_action_tx'):
            exec_result = self.do_action_tx(
                "EXECUTE_FROM_PICKING",
                lambda: self.engine.gate1_apply_picking_result(
                    picking_result,
                    picking_no=getattr(meta, 'picking_no', ''),
                    sales_order=getattr(meta, 'sales_order', ''),
                    allow_qty_mismatch=allow_qty_mismatch,
                    approval_reason=approval_reason,
                ),
                parent=self.root,
                refresh_mode="deferred",
            )
        else:
            exec_result = self.engine.gate1_apply_picking_result(
                picking_result,
                picking_no=getattr(meta, 'picking_no', ''),
                sales_order=getattr(meta, 'sales_order', ''),
                allow_qty_mismatch=allow_qty_mismatch,
                approval_reason=approval_reason,
            )
        if exec_result.get('success'):
            CustomMessageBox.showinfo(
                self.root, '판매화물 결정 완료',
                f'처리: {exec_result.get("executed", 0)}개 LOT\n현장 출고 완료 후 [출고 확정]을 실행하세요.'
            )
            if not hasattr(self, 'do_action_tx'):
                self._refresh_after_outbound_action("EXECUTE_FROM_PICKING")
        else:
            errs = '\n'.join(exec_result.get('errors', [])[:3])
            CustomMessageBox.showerror(self.root, '실행 실패', errs)

    def _oh_picking_legacy_flow(self, path: str) -> None:
        """레거시 피킹 파서 경로 (Gate-1 미지원 시 폴백)."""
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
                    logger.debug("[SUPPRESSED] exception in outbound_handlers.py")  # noqa

        if not parse_picking_list_pdf:
            CustomMessageBox.showerror(
                self.root,
                "Picking List 파서 없음",
                "features.parsers 또는 parsers.picking_list_parser를 불러올 수 없습니다.",
            )
            return

        try:
            doc = parse_picking_list_pdf(path)
            if _HAS_PICKING_REVIEW:
                _log_fn = getattr(self, '_append_log', None) or getattr(self, '_log_safe', None)
                doc = enrich_picking_doc_with_review(doc, path, log_fn=_log_fn)
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

    def _save_gate1_result_json(self, gate1: dict, picking_no: str) -> None:
        """v6.12.1: Gate-1 결과를 JSON 파일로 저장 (감사 추적용)."""
        import os
        import json
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f'Gate1_{picking_no}_{ts}.json'
        fpath = os.path.join(os.path.expanduser('~'), 'Desktop', fname)
        try:
            # set은 JSON 직렬화 불가 → list 변환
            serializable = {}
            for k, v in gate1.items():
                if isinstance(v, set):
                    serializable[k] = sorted(v)
                elif k == 'lot_details':
                    serializable[k] = v  # list[dict] — 이미 직렬화 가능
                else:
                    serializable[k] = v
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)
            if hasattr(self, '_log'):
                self._log(f'Gate-1 JSON 저장: {fpath}')
            logger.info(f'[Gate-1] JSON 저장 완료: {fpath}')
        except (OSError, TypeError) as e:
            logger.debug(f'Gate-1 JSON 저장 실패: {e}')

    def _save_gate1_report(self, gate1: dict, picking_no: str) -> None:
        """v6.1.0: Gate-1 실패 에러 리포트를 바탕화면에 텍스트 파일로 저장."""
        import os
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f'Gate1_실패_{picking_no}_{ts}.txt'
        fpath = os.path.join(os.path.expanduser('~'), 'Desktop', fname)
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(gate1.get('error_report', ''))
            if hasattr(self, '_log'):
                self._log(f'Gate-1 에러 리포트 저장: {fpath}')
        except OSError:
            logger.debug(f'Gate-1 리포트 저장 실패: {fpath}')

    def _oh_picking_inject_tpl_meta(self, picking_result, tpl: dict) -> None:
        """피킹 파싱 결과에 템플릿 메타데이터를 주입한다 (v7.4.0)."""
        meta = picking_result.meta
        _inject = [
            ('contact_person',  'contact_person'),
            ('contact_email',   'contact_email'),
            ('port_loading',    'port_loading'),
            ('port_discharge',  'port_discharge'),
            ('delivery_terms',  'delivery_terms'),
        ]
        for tpl_key, meta_attr in _inject:
            tpl_val = tpl.get(tpl_key, '')
            if tpl_val and not getattr(meta, meta_attr, ''):
                setattr(meta, meta_attr, tpl_val)
        _meta_bag = getattr(getattr(picking_result, 'meta', None), 'bag_weight_kg', 0) or 0
        _tpl_bag  = int(tpl.get('bag_weight_kg', 500) or 500)
        _resolved_bag = _meta_bag if _meta_bag >= 100 else _tpl_bag
        if not hasattr(picking_result, '_tpl_customer'):
            picking_result._tpl_customer   = tpl.get('customer', '')
            picking_result._tpl_cust_code  = tpl.get('customer_code', '')
            picking_result._tpl_bag_weight = _resolved_bag
            picking_result._tpl_storage    = tpl.get('storage_location', '1001 GY logistics')

    def _oh_picking_admin_approval(self) -> tuple:
        """관리자 코드 + 승인 사유 입력 플로우.

        Returns:
            (allow_qty_mismatch: bool, approval_reason: str, approved: bool)
            approved=False 이면 호출자는 즉시 return.
        """
        configured_code = str(os.environ.get('SQM_ADMIN_CODE', '')).strip()
        if not configured_code:
            CustomMessageBox.showerror(
                self.root,
                '관리자 코드 미설정',
                '수량 불일치 승인 진행을 위해 SQM_ADMIN_CODE 환경변수를 설정하세요.',
            )
            return False, '', False
        entered = CustomMessageBox.askstring(
            self.root,
            '관리자 승인',
            'Gate-1 수량 불일치 승인 코드 입력:',
            show='*',
        )
        if entered is None:
            return False, '', False
        if str(entered).strip() != configured_code:
            CustomMessageBox.showerror(self.root, '승인 실패', '관리자 코드가 올바르지 않습니다.')
            return False, '', False
        reason = CustomMessageBox.askstring(
            self.root, '승인 사유', '승인 사유를 입력하세요 (필수):',
        )
        if reason is None or not str(reason).strip():
            CustomMessageBox.showwarning(self.root, '승인 중단', '승인 사유는 필수입니다.')
            return False, '', False
        return True, str(reason).strip(), True
