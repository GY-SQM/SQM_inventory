"""Inbound parse service mixin extracted from onestop_inbound."""

import logging
import os
import threading
import time
import queue

from core.constants import DEFAULT_TONBAG_WEIGHT
from engine_modules.constants import CARRIER_OPTIONS
from features.parsers.inbound_parser import InboundParser
from .inbound_utils import merge_results
from gui_app_modular.utils.ui_constants import tc

try:
    from features.parsers.onestop_inbound_candidate_patch import (
        parse_bl_with_candidate,
        parse_do_with_candidate,
    )
    _HAS_CANDIDATE_ENGINE = True
except ImportError:
    _HAS_CANDIDATE_ENGINE = False


logger = logging.getLogger(__name__)
ENABLE_PARSE_CONFIRM = False


def _dbg_log(*_args, **_kwargs):
    logger.debug("[DBG] parse service")


DOC_TYPES = [
    ('BL', '① Bill of Loading (선하증권)', True),
    ('PACKING_LIST', '② Packing List (포장명세서)', True),
    ('INVOICE', '③ Invoice, FA (송장)', True),
    ('DO', '④ Delivery Order (인도지시서) (선택사항)', False),
]


class InboundParseService:
    """파싱 서비스 전담 클래스 — Mixin"""

    def _update_parse_hint(self) -> None:
        btn = getattr(self, 'btn_parse', None)
        if not btn:
            return
        if self.file_paths:
            btn.config(state='normal')
        else:
            btn.config(state='disabled')

    def _start_parsing(self) -> None:
        if getattr(self, '_auto_start_parse', False):
            if self.btn_parse and str(self.btn_parse.cget('state')) == 'disabled':
                self.btn_parse.config(state='normal')
            self._do_start_parsing_after_template()
            return
        self._show_preparse_select_dialog()

    def _show_preparse_select_dialog(self) -> None:
        try:
            from gui_app_modular.dialogs.preparse_select_dialog import PreParseSelectDialog
        except ImportError as e:
            logger.error("[onestop] PreParseSelectDialog 로드 실패: %s — 기존 방식으로 진행", e)
            self._show_template_select_before_parse()
            return

        current_tpl = getattr(self, '_inbound_template_data', None) or {}
        current_theme = getattr(self.parent, 'current_theme', 'darkly')

        def _on_execute(template_data: dict, use_multi_template: bool) -> None:
            self._on_preparse_execute(template_data, use_multi_template)

        PreParseSelectDialog(
            parent=self.dialog,
            file_paths=dict(self.file_paths),
            engine=self.engine,
            current_template=current_tpl,
            on_execute=_on_execute,
            current_theme=current_theme,
        )

    def _on_preparse_execute(self, template_data: dict, use_multi_template: bool) -> None:
        if template_data:
            self._inbound_template_data = template_data
            try:
                tname = template_data.get('template_name', '')
                if hasattr(self, '_tpl_var'):
                    self._tpl_var.set(tname)
                self._load_template_combo()
                self._tpl_var.set(tname)
                if hasattr(self, '_update_tpl_selected_label'):
                    self._update_tpl_selected_label()
            except Exception as e:
                logger.warning(f"[UI] template confirmation UI update failed: {e}")
            self._log_safe(
                f"✅ 템플릿 확정: {template_data.get('template_name','')} "
                f"/ {template_data.get('bag_weight_kg', 500)}kg"
            )
            self._apply_template_to_carrier_badge(template_data)

        self._use_multi_template_flag = bool(use_multi_template)
        if use_multi_template:
            self._log_safe("🔍 다중 템플릿 후보 모드: ON")
        else:
            self._log_safe("📌 단일 템플릿 모드: OFF (기존 템플릿만 사용)")

        self._do_start_parsing_after_template()

    def _do_start_parsing_after_template(self) -> None:
        received = []
        missing = []
        do_missing = False
        short_names = {
            'PACKING_LIST': 'Packing List',
            'INVOICE': 'Invoice, FA',
            'BL': 'Bill of Loading',
            'DO': 'Delivery Order',
        }
        for doc_type, _doc_name, _required in DOC_TYPES:
            name = short_names.get(doc_type, doc_type)
            if doc_type in self.file_paths:
                received.append(name)
            else:
                missing.append(name)
                if doc_type == 'DO':
                    do_missing = True

        lines = []
        if received:
            lines.append(f"✅ 들어온 서류: {', '.join(received)}")
        if missing:
            lines.append(f"⚠️ 빠진 서류: {', '.join(missing)}")
        if do_missing:
            lines.append("\n📋 D/O가 빠진 경우에는 입항일 혹은 프리타임을 반드시 입력해야 합니다.")
        lines.append("\n진행할까요?")
        msg = "\n".join(lines)

        if not getattr(self, '_skip_parse_confirm', False):
            from ..utils.custom_messagebox import CustomMessageBox
            proceed = CustomMessageBox.askyesno(self.dialog, "입고 서류 확인", msg)
            if not proceed:
                return

        if missing:
            self._update_progress(0, f"ℹ️ {', '.join(missing)} 미선택 — 해당 정보 생략")

        self.btn_parse.config(state='disabled')
        if self.btn_reparse:
            self.btn_reparse.config(state='disabled')
        self._show_progress_inline()
        self._activate_step(1)

        thread = threading.Thread(target=self._parse_thread, daemon=True)
        thread.start()

    def _parse_thread(self) -> None:
        try:
            self._cross_check_result = None
            _inbound_parser = InboundParser(log_fn=self._log_safe, progress_fn=self._update_progress)
            parser = _inbound_parser.init_parser()

            _tpl = getattr(self, '_inbound_template_data', {}) or {}
            ctx = _inbound_parser.extract_template_hints(_tpl)

            if hasattr(self, '_carrier_label') and self._carrier_label:
                try:
                    self._carrier_label.config(text="  ⏳ 파싱 중...  ", fg=tc('text_primary'), bg=tc('text_muted'))
                except Exception as e:
                    logger.warning(f"[UI] carrier label parsing status update failed: {e}")

            parse_result = _inbound_parser.parse_documents(parser, ctx, self.file_paths)
            pl_result = parse_result['pl']
            inv_result = parse_result['inv']
            bl_result = parse_result['bl']
            do_result = parse_result['do']
            total = parse_result['total']
            self.parsed_results = parse_result['parsed_results']

            self._pt_handle_bl_ui_updates(bl_result, ctx)
            self._update_progress(85, "📊 데이터 병합 중...")
            merge_results(inv_result, pl_result, bl_result, do_result)
            self._pt_handle_missing_dates(do_result)
            self._pt_collect_warnings_and_crosscheck(pl_result, inv_result, bl_result, do_result)
            self._pt_finalize_preview()

            elapsed_sec = time.time() - getattr(self, '_progress_start_time', time.time())
            elapsed_str = f"{elapsed_sec:.1f}초" if elapsed_sec < 60 else f"{int(elapsed_sec // 60)}분 {elapsed_sec % 60:.0f}초"
            self._update_progress(100, f"✅ 파싱 완료 — {len(self.preview_data)}개 LOT ({elapsed_str})")
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, lambda: self._activate_step(2))

            self._pt_parse_confirm(pl_result, elapsed_str)
            self._log_safe(f"✅ 파싱 완료: {len(self.preview_data)} LOT, {total}종 서류 (경과: {elapsed_str})")

        except (RuntimeError, ValueError) as e:
            self._update_progress(0, f"❌ 오류: {e}")
            self._log_safe(f"❌ 파싱 오류: {e}")
            logger.error(f"원스톱 파싱 오류: {e}", exc_info=True)
            self._enable_parse_btn()

    def _pt_handle_bl_ui_updates(self, bl_result, ctx: dict) -> None:
        if not bl_result:
            return
        _carrier_id = getattr(bl_result, 'carrier_id', '')
        if not _carrier_id or _carrier_id == 'UNKNOWN':
            return
        _carrier_name = getattr(bl_result, 'carrier_name', '')
        _badge = f"[선사: {_carrier_name or _carrier_id}]"
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, lambda b=_badge: self._update_carrier_badge(b))
            self.dialog.after(0, lambda: (hasattr(self, 'btn_reparse_carrier') and self.btn_reparse_carrier.config(state='normal')))

        if not ctx['tpl_carrier_id'] or ctx['tpl_carrier_id'] == 'UNKNOWN':
            try:
                _auto_tpl = self._auto_match_template_by_carrier(_carrier_id)
                if _auto_tpl:
                    ctx['tpl_carrier_id'] = _carrier_id
                    ctx['bag_weight'] = int(_auto_tpl.get('bag_weight_kg', ctx['bag_weight']))
                    ctx['hint_packing'] = str(_auto_tpl.get('gemini_hint_packing', '') or '') or ctx['hint_packing']
                    ctx['hint_invoice'] = str(_auto_tpl.get('gemini_hint_invoice', '') or '') or ctx['hint_invoice']
                    ctx['hint_bl'] = str(_auto_tpl.get('gemini_hint_bl', '') or '') or ctx['hint_bl']
                    ctx['bl_format'] = str(_auto_tpl.get('bl_format', '') or '') or ctx['bl_format']
                    self._inbound_template_data = _auto_tpl
                    self._log_safe(
                        f"  🔄 선사 자동 매칭: {_carrier_id} → "
                        f"템플릿 '{_auto_tpl.get('template_name', '')}' "
                        f"({ctx['bag_weight']}kg)"
                    )
                    if self.dialog and self.dialog.winfo_exists():
                        self.dialog.after(0, lambda t=_auto_tpl: self._apply_template_to_carrier_badge(t))
            except (ValueError, KeyError, TypeError, AttributeError) as _ate:
                logger.warning(f"선사 자동 템플릿 매칭 실패(무시): {_ate}")

        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, lambda c=_carrier_id: (hasattr(self, '_carrier_manual_var') and self._carrier_manual_var.set(self._normalize_carrier_for_combo(c))))

    def _pt_init_parser(self, ParserClass):
        gemini_key = os.environ.get('GEMINI_API_KEY', '')
        if not gemini_key:
            try:
                from core.config import get_settings
                settings = get_settings()
                gemini_key = settings.get('gemini_api_key', '')
            except (ImportError, ModuleNotFoundError) as _e:
                logger.debug(f"onestop_inbound: {_e}")
        if not gemini_key or str(gemini_key).strip() == '' or str(gemini_key).startswith('your-'):
            raise RuntimeError("API-only 모드: Gemini API Key가 필요합니다. 설정에서 API Key를 입력하세요.")
        return ParserClass(gemini_api_key=gemini_key)

    def _pt_extract_template_hints(self) -> dict:
        _tpl = getattr(self, '_inbound_template_data', {}) or {}
        _bag_weight = int(_tpl.get('bag_weight_kg') or DEFAULT_TONBAG_WEIGHT)
        _hint_packing = str(_tpl.get('gemini_hint_packing', '') or '')
        _hint_invoice = str(_tpl.get('gemini_hint_invoice', '') or '')
        _hint_bl = str(_tpl.get('gemini_hint_bl', '') or '')
        _bl_format = str(_tpl.get('bl_format', '') or '')
        _tpl_id = _tpl.get('template_id', 'NONE')
        _tpl_carrier_id = str(_tpl.get('carrier_id', '') or '').strip().upper()
        return {
            'bag_weight': _bag_weight,
            'hint_packing': _hint_packing,
            'hint_invoice': _hint_invoice,
            'hint_bl': _hint_bl,
            'bl_format': _bl_format,
            'tpl_id': _tpl_id,
            'tpl_carrier_id': _tpl_carrier_id,
        }

    def _pt_parse_documents(self, parser, ctx: dict):
        parse_order = ['BL', 'PACKING_LIST', 'INVOICE', 'DO']
        to_parse = [(dt, self.file_paths[dt]) for dt in parse_order if dt in self.file_paths]
        total = len(to_parse)
        if total == 0:
            self._update_progress(90, "파싱할 파일이 없습니다")
            return None, None, None, None, 0

        icons = {'PACKING_LIST': '📦', 'INVOICE': '📑', 'BL': '🚢', 'DO': '📋'}
        doc_type_display = {'PACKING_LIST': 'Packing List', 'INVOICE': 'Invoice, FA', 'BL': 'Bill of Loading', 'DO': 'Delivery Order'}
        pl_result = None
        inv_result = None
        bl_result = None
        do_result = None

        for idx, (doc_type, file_path) in enumerate(to_parse):
            fname = os.path.basename(file_path)
            icon = icons.get(doc_type, '📄')
            pct = int(10 + 70 * idx / total)
            doc_name = doc_type_display.get(doc_type, doc_type)
            self._update_progress(pct, f"현재 파싱 중: {doc_name} — {fname}")
            self._log_safe(f"{icon} {doc_type} 파싱: {fname}")

            try:
                if doc_type == 'PACKING_LIST':
                    pl_result = parser.parse_packing_list(file_path, bag_weight_kg=ctx['bag_weight'], gemini_hint=ctx['hint_packing'])
                    self.parsed_results['packing_list'] = pl_result
                elif doc_type == 'INVOICE':
                    inv_result = parser.parse_invoice(file_path, gemini_hint=ctx['hint_invoice'])
                    self.parsed_results['invoice'] = inv_result
                elif doc_type == 'BL':
                    bl_result = self._pt_parse_bl(parser, file_path, ctx)
                    self._pt_handle_bl_carrier_detection(bl_result, ctx)
                elif doc_type == 'DO':
                    if _HAS_CANDIDATE_ENGINE:
                        do_result = parse_do_with_candidate(parser, file_path, log_fn=self._log_safe)
                    else:
                        do_result = parser.parse_do(file_path)
                    self.parsed_results['do'] = do_result
            except (ValueError, TypeError, AttributeError, RuntimeError) as e:
                self._log_safe(f"  ❌ {doc_type} 파싱 오류: {e}")
                logger.error(f"파싱 오류 [{doc_type}]: {e}", exc_info=True)
            else:
                merge_results(inv_result, pl_result, bl_result, do_result)
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(0, lambda: self._push_preview_to_main())
                    if not getattr(self, 'compact_mode', False):
                        self.dialog.after(0, lambda: self._refresh_preview_tree_only())

        return pl_result, inv_result, bl_result, do_result, total

    def _pt_parse_bl(self, parser, file_path: str, ctx: dict):
        if _HAS_CANDIDATE_ENGINE:
            _use_multi = getattr(self, '_use_multi_template_flag', True)
            bl_result = parse_bl_with_candidate(
                parser,
                file_path,
                hint_bl=ctx['hint_bl'],
                bl_format=ctx['bl_format'],
                log_fn=self._log_safe,
                use_multi=_use_multi,
                db_carrier_id=ctx['tpl_carrier_id'],
            )
        else:
            bl_result = parser.parse_bl(file_path, gemini_hint=ctx['hint_bl'], bl_format=ctx['bl_format'])
        self.parsed_results['bl'] = bl_result
        return bl_result

    def _pt_handle_bl_carrier_detection(self, bl_result, ctx: dict):
        if not bl_result:
            return
        _carrier_id = getattr(bl_result, 'carrier_id', '')
        if not _carrier_id or _carrier_id == 'UNKNOWN':
            return
        if not ctx['tpl_carrier_id'] or ctx['tpl_carrier_id'] == 'UNKNOWN':
            try:
                _auto_tpl = self._auto_match_template_by_carrier(_carrier_id)
                if _auto_tpl:
                    ctx['tpl_carrier_id'] = _carrier_id
                    ctx['bag_weight'] = int(_auto_tpl.get('bag_weight_kg', ctx['bag_weight']))
                    ctx['hint_packing'] = str(_auto_tpl.get('gemini_hint_packing', '') or '') or ctx['hint_packing']
                    ctx['hint_invoice'] = str(_auto_tpl.get('gemini_hint_invoice', '') or '') or ctx['hint_invoice']
                    ctx['hint_bl'] = str(_auto_tpl.get('gemini_hint_bl', '') or '') or ctx['hint_bl']
                    ctx['bl_format'] = str(_auto_tpl.get('bl_format', '') or '') or ctx['bl_format']
                    self._inbound_template_data = _auto_tpl
            except (ValueError, KeyError, TypeError, AttributeError) as _ate:
                logger.warning(f"선사 자동 템플릿 매칭 실패(무시): {_ate}")

    def _pt_handle_missing_dates(self, do_result):
        self._do_deferred = False
        _need_date_input = False
        if not do_result:
            _need_date_input = True
            self._log_safe("📋 D/O 미첨부 — 날짜 정보 수동 입력 필요")
        elif self.preview_data and not (self.preview_data[0].get('arrival_date') or '').strip():
            _need_date_input = True
            self._log_safe("📋 D/O에서 입항일 추출 실패 — 수동 입력 필요")

        if _need_date_input and self.preview_data:
            prefilled_ship = self.preview_data[0].get('ship_date', '') if self.preview_data else ''
            date_queue = queue.Queue()

            def _show_date_popup():
                self._hide_progress_popup()
                result = self._ask_missing_dates(prefilled_ship, do_result)
                date_queue.put(result)

            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, _show_date_popup)
                try:
                    user_dates = date_queue.get(timeout=300)
                except queue.Empty:
                    user_dates = None
                if user_dates and not user_dates.get('deferred'):
                    for row in self.preview_data:
                        if user_dates.get('ship_date') and not (row.get('ship_date') or '').strip():
                            row['ship_date'] = user_dates['ship_date']
                        if user_dates.get('arrival_date'):
                            row['arrival_date'] = user_dates['arrival_date']
                        if 'con_return' in user_dates:
                            row['con_return'] = user_dates.get('con_return', '') or ''
                        if user_dates.get('free_time') is not None:
                            row['free_time'] = str(user_dates.get('free_time', ''))

    def _pt_collect_warnings_and_crosscheck(self, pl_result, inv_result, bl_result, do_result):
        _warnings = []
        if not pl_result or not getattr(pl_result, 'lots', None):
            _warnings.append("⚠️ Packing List: LOT 정보 추출 실패")
        if not inv_result or not getattr(inv_result, 'sap_no', None):
            _warnings.append("⚠️ Invoice: SAP번호 추출 실패 — 수동 입력 필요")
        if not bl_result or not getattr(bl_result, 'bl_no', None):
            _warnings.append("⚠️ B/L: BL번호 추출 실패 — 수동 입력 필요")

        self._pt_show_error_recovery_dialog(bl_result, pl_result, inv_result, do_result)
        if _warnings:
            _warn_msg = "\n".join(_warnings)
            self._log_safe(f"\n{'='*40}\n{_warn_msg}\n{'='*40}")

    def _pt_show_error_recovery_dialog(self, bl_result, pl_result, inv_result, do_result):
        try:
            from gui_app_modular.dialogs.parse_error_recovery_dialog import classify_parse_error, show_parse_error_recovery
            _recovery_codes = []
            if bl_result:
                _recovery_codes += classify_parse_error(bl_result)
            if pl_result:
                _recovery_codes += classify_parse_error(pl_result)
            if inv_result:
                _recovery_codes += classify_parse_error(inv_result)
            if do_result:
                _recovery_codes += classify_parse_error(do_result)
            if _recovery_codes and self.dialog and self.dialog.winfo_exists():
                self.dialog.after(100, lambda: None)
                _ = show_parse_error_recovery
        except ImportError as e:
            logger.debug("[onestop] parse_error_recovery_dialog 미존재 — 복구 다이얼로그 생략: %s", e)

    def _pt_finalize_preview(self):
        if self.dialog and self.dialog.winfo_exists() and self.preview_data:
            self.dialog.after(0, lambda: self._push_preview_to_main())
        self._capture_original_preview_state()
        self._sort_col = None
        self._sort_desc = False
        if not getattr(self, 'compact_mode', False):
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, self._update_sort_headings)
            self._update_filter_values_from_preview()
            if self.btn_reset_original and self.btn_reset_original.winfo_exists():
                self.btn_reset_original.config(state='normal' if self._original_preview_data else 'disabled')
        self._update_progress(95, "📋 미리보기 준비...")
        if not getattr(self, 'compact_mode', False) and self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, self._show_preview_table)
        self._display_preview()

    def _pt_parse_confirm(self, pl_result, elapsed_str: str):
        if ENABLE_PARSE_CONFIRM and getattr(self, 'preview_data', None) and len(self.preview_data) > 0:
            try:
                _pl_ok = pl_result and len(getattr(pl_result, 'lots', []) or []) > 0
                if not _pl_ok and len(self.preview_data) > 0:
                    import tkinter.messagebox as _mb
                    _go = _mb.askyesno(
                        "PL 검증 경고",
                        "⚠️ Packing List 파싱 실패 또는 LOT 정보 없음\n\nPL 없이 저장하면 톤백 수/중량 검증이 생략됩니다.\n그래도 저장하시겠습니까?",
                        parent=self.dialog,
                    )
                    if not _go:
                        self._update_progress(0, "⚠️ PL 검증 미통과 — DB 저장 중단")
                        self._log_safe("⚠️ [P3] PL 실패로 인해 DB 저장 취소")
                        return
            except (RuntimeError, ValueError, KeyError, ImportError) as _ce:
                _dbg_log("parse confirm skipped", _ce)
                logger.warning(f"[PARSE-CONFIRM] 다이얼로그 생략: {_ce}")

    def _enable_parse_btn(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, lambda: self.btn_parse.config(state='normal') if self.btn_parse else None)
