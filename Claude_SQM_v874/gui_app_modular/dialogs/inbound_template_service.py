"""Inbound template service mixin extracted from onestop_inbound."""

import logging
import sqlite3

from engine_modules.constants import CARRIER_OPTIONS
from gui_app_modular.utils.ui_constants import create_themed_toplevel, tc


logger = logging.getLogger(__name__)


class InboundTemplateService:
    """템플릿 서비스 전담 클래스 — Mixin"""

    def _load_template_combo(self):
        try:
            rows = self.engine.db.fetchall(
                "SELECT template_id, template_name, bag_weight_kg, "
                "carrier_id, product_hint, weight_format, "
                "COALESCE(bl_format,'') AS bl_format, "
                "gemini_hint_packing, gemini_hint_invoice, gemini_hint_bl "
                "FROM inbound_template WHERE is_active=1 "
                "ORDER BY carrier_id, bag_weight_kg"
            )
            self._template_map = {}
            names = []
            keys = [
                'template_id', 'template_name', 'bag_weight_kg',
                'carrier_id', 'product_hint', 'weight_format', 'bl_format',
                'gemini_hint_packing', 'gemini_hint_invoice', 'gemini_hint_bl',
            ]
            for r in (rows or []):
                t = dict(r) if hasattr(r, 'keys') else dict(zip(keys, r))
                self._template_map[t['template_name']] = t
                names.append(t['template_name'])
            self._tpl_combo['values'] = names
            default = next((n for n in names if 'UNKNOWN' in n and '500' in n), None)
            if not default and names:
                default = names[0]
            if default:
                self._tpl_var.set(default)
                self._on_template_selected()
        except Exception as e:
            logger.warning(f"[onestop] 템플릿 콤보 로드 실패: {e}")

    def _on_template_selected(self, _event=None):
        name = self._tpl_var.get()
        t = getattr(self, '_template_map', {}).get(name)
        if not t:
            return
        self._inbound_template_data = t
        if hasattr(self, '_update_tpl_selected_label'):
            try:
                self._update_tpl_selected_label()
            except Exception as e:
                logger.warning(f"[UI] template selected label update failed: {e}")
        self._apply_template_to_carrier_badge(t)

    def _normalize_carrier_for_combo(self, raw: str) -> str:
        def _fold(x: str) -> str:
            return (x or "").strip().upper().replace(" ", "_").replace("-", "_")

        r = _fold(raw or "UNKNOWN")
        for opt in CARRIER_OPTIONS:
            if _fold(opt) == r:
                return opt
        s = (raw or "").strip()
        if s in CARRIER_OPTIONS:
            return s
        return "UNKNOWN"

    def _carrier_id_matches_filter(self, filt: str, template_carrier: str) -> bool:
        def _fold(x: str) -> str:
            return (x or "").strip().upper().replace(" ", "_").replace("-", "_")

        return _fold(filt) == _fold(template_carrier or "UNKNOWN")

    def _auto_match_template_by_carrier(self, carrier_id: str) -> dict | None:
        try:
            engine = getattr(self, 'engine', None)
            if not engine:
                return None
            db = getattr(engine, 'db', None) or engine
            conn = getattr(db, 'conn', None) or getattr(db, '_conn', None)
            if not conn:
                return None
            cursor = conn.execute("SELECT * FROM inbound_templates WHERE is_active = 1 ORDER BY is_default DESC, template_name ASC")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            norm_cid = carrier_id.strip().upper().replace(" ", "_").replace("-", "_")
            for row in rows:
                tpl = dict(zip(columns, row))
                tpl_cid = str(tpl.get('carrier_id', '') or '').strip().upper().replace(" ", "_").replace("-", "_")
                if tpl_cid == norm_cid:
                    return tpl
            for row in rows:
                tpl = dict(zip(columns, row))
                if norm_cid in str(tpl.get('template_id', '') or '').upper():
                    return tpl
        except (sqlite3.Error, AttributeError) as e:
            logger.warning(f"[onestop] 선사 자동 템플릿 매칭 DB 조회 실패: {e}")
        return None

    def _on_carrier_combo_selected(self, _event=None) -> None:
        cid = self._normalize_carrier_for_combo((self._carrier_manual_var.get() or "UNKNOWN").strip())
        self._carrier_manual_var.set(cid)
        prev_raw = (getattr(self, "_inbound_template_data", None) or {}).get("carrier_id", "UNKNOWN")
        revert = self._normalize_carrier_for_combo(str(prev_raw or "UNKNOWN"))
        self._show_template_table_picker(carrier_filter=cid, on_cancel_carrier_revert=revert)

    def _show_template_table_picker_for_current_carrier(self) -> None:
        cid = self._normalize_carrier_for_combo((self._carrier_manual_var.get() or "UNKNOWN").strip())
        flt = None if cid == "UNKNOWN" else cid
        self._show_template_table_picker(carrier_filter=flt, on_cancel_carrier_revert=None)

    def _apply_template_to_carrier_badge(self, t: dict) -> None:
        if not t or not hasattr(self, '_carrier_label'):
            return
        cid = self._normalize_carrier_for_combo(str(t.get('carrier_id', 'UNKNOWN') or 'UNKNOWN'))
        try:
            self._carrier_manual_var.set(cid)
        except Exception as e:
            logger.warning("[onestop] carrier_manual_var 설정 생략: %s", e)
        try:
            from features.ai.bl_carrier_registry import CARRIER_TEMPLATES
            _ctpl = CARRIER_TEMPLATES.get(cid)
            cname = _ctpl.carrier_name if _ctpl else cid
        except (ImportError, AttributeError):
            cname = cid
        try:
            if cid == 'UNKNOWN':
                self._carrier_label.config(text="  뱃지 클릭: 템플릿 목록  ", fg=tc('badge_text'), bg=tc('bg_secondary'), cursor='hand2')
            else:
                self._update_carrier_badge(f"[선사: {cname}] (템플릿)", cid)
        except Exception as e:
            logger.warning(f"[UI] carrier badge from template failed: {e}")

    def _on_save_current_as_template(self) -> None:
        try:
            from gui_app_modular.dialogs.inbound_template_dialog import save_template
            cur = getattr(self, '_inbound_template_data', {}) or {}
            t_id = str(cur.get('template_id') or '').strip() or 'TPL_AUTO'
            t_name = str(cur.get('template_name') or '').strip() or '새 템플릿'
            data = {
                'template_id': t_id,
                'template_name': t_name,
                'carrier_id': cur.get('carrier_id', 'UNKNOWN'),
                'bag_weight_kg': int(cur.get('bag_weight_kg', 500)),
                'product_hint': cur.get('product_hint', 'LITHIUM CARBONATE'),
                'weight_format': cur.get('weight_format', 'EURO'),
                'bl_format': str(cur.get('bl_format', '') or ''),
                'gemini_hint_packing': cur.get('gemini_hint_packing', ''),
                'gemini_hint_invoice': cur.get('gemini_hint_invoice', ''),
                'gemini_hint_bl': cur.get('gemini_hint_bl', ''),
                'note': '파싱 결과에서 자동 생성',
                'is_active': 1,
            }
            if save_template(self.engine, data):
                self._load_template_combo()
        except Exception as _e:
            logger.error(f"[템플릿 저장] {_e}")

    def _show_template_table_picker(self, carrier_filter=None, on_cancel_carrier_revert=None) -> None:
        from tkinter import ttk as _ttk

        all_templates = list(getattr(self, '_template_map', {}).values())
        templates = all_templates
        if carrier_filter is not None:
            cf = self._normalize_carrier_for_combo(str(carrier_filter))
            templates = [t for t in all_templates if self._carrier_id_matches_filter(cf, str(t.get('carrier_id', 'UNKNOWN')))]
            if not templates:
                if on_cancel_carrier_revert is not None:
                    try:
                        self._carrier_manual_var.set(self._normalize_carrier_for_combo(on_cancel_carrier_revert))
                    except Exception:
                        pass
                return

        popup = create_themed_toplevel(self.dialog)
        popup.title("📋 파싱 템플릿 선택")
        popup.geometry("780x420")
        popup.resizable(True, True)
        popup.transient(self.dialog)
        popup.grab_set()

        cols = ('sel', 'carrier', 'name', 'bag_kg', 'product', 'bl_format')
        tree = _ttk.Treeview(popup, columns=cols, show='headings', height=12, selectmode='browse')
        for cid, txt, w, anchor in [
            ('sel', '✔', 36, 'center'),
            ('carrier', '선사', 110, 'center'),
            ('name', '템플릿 이름', 220, 'w'),
            ('bag_kg', '톤백 단가', 80, 'center'),
            ('product', '제품 힌트', 160, 'w'),
            ('bl_format', 'BL 형식', 80, 'center'),
        ]:
            tree.heading(cid, text=txt, anchor='center')
            tree.column(cid, width=w, anchor=anchor)
        tree.pack(fill='both', expand=True)

        current = self._tpl_var.get()
        iid_map = {}
        for t in templates:
            name = t.get('template_name', '')
            sel = '✔' if name == current else ''
            iid = tree.insert('', 'end', values=(sel, t.get('carrier_id', 'UNKNOWN'), name, f"{t.get('bag_weight_kg', 500)} kg", (t.get('product_hint', '') or '')[:20], t.get('bl_format', '') or '-'))
            iid_map[iid] = name

        def _do_select(_event=None):
            sel = tree.selection()
            if not sel:
                return
            name = iid_map.get(sel[0], '')
            if name and name in self._template_map:
                self._tpl_var.set(name)
                self._on_template_selected()
                popup.destroy()

        tree.bind('<Double-1>', _do_select)

    def _update_tpl_selected_label(self) -> None:
        lbl = getattr(self, '_tpl_selected_lbl', None)
        if not lbl:
            return
        name = self._tpl_var.get()
        t = getattr(self, '_template_map', {}).get(name, {})
        if name and t:
            carrier = t.get('carrier_id', '')
            bag_kg = t.get('bag_weight_kg', 500)
            bl_fmt = t.get('bl_format', '') or ''
            bl_info = f"  BL:{bl_fmt}" if bl_fmt else ''
            lbl.config(text=f"{carrier} — {name}  ({bag_kg}kg{bl_info})", foreground=tc('info'))
        else:
            lbl.config(text="(미선택)", foreground=tc('text_muted'))

    def _open_template_manager(self):
        try:
            from gui_app_modular.dialogs.inbound_template_dialog import InboundTemplateDialog
            current_theme = getattr(self.parent, 'current_theme', 'darkly')
            InboundTemplateDialog(self.dialog, self.engine, current_theme=current_theme)
            self._load_template_combo()
        except Exception as e:
            logger.error(f"[onestop] 템플릿 관리 다이얼로그 오류: {e}")

    def _show_template_select_before_parse(self) -> None:
        try:
            from gui_app_modular.dialogs.inbound_template_dialog import InboundTemplateDialog
            current_theme = getattr(self.parent, 'current_theme', 'darkly')

            def _on_template_chosen(t: dict):
                self._inbound_template_data = t
                try:
                    tname = t.get('template_name', '')
                    self._tpl_var.set(tname)
                    self._load_template_combo()
                    self._tpl_var.set(tname)
                    if hasattr(self, '_update_tpl_selected_label'):
                        self._update_tpl_selected_label()
                except Exception as e:
                    logger.warning(f"[UI] template selection UI update failed: {e}")
                self._apply_template_to_carrier_badge(t)
                self._do_start_parsing_after_template()

            InboundTemplateDialog(self.dialog, self.engine, current_theme=current_theme, on_select_callback=_on_template_chosen)
        except Exception as e:
            logger.error(f"[onestop] 템플릿 선택 다이얼로그 오류: {e}")
            self._do_start_parsing_after_template()

    def _reparse_after_carrier_change(self) -> None:
        """수동 선사 변경 후 PL/INV 재파싱."""
        cid = getattr(self, '_carrier_manual_var', None)
        cid = cid.get().strip() if cid else 'UNKNOWN'
        if cid == 'UNKNOWN':
            try:
                from ..utils.custom_messagebox import CustomMessageBox
                CustomMessageBox.showwarning(
                    self.dialog, "선사 미선택",
                    "🚢 선사 드롭다운에서 선사를 고르거나, 뱃지를 눌러 템플릿을 선택하세요.\n"
                    "(템플릿에 선사·톤백 단가가 포함됩니다.)"
                )
            except Exception as e:
                logger.warning(f"[UI] show carrier not selected warning failed: {e}")
            return
        if 'PACKING_LIST' not in self.file_paths:
            try:
                from ..utils.custom_messagebox import CustomMessageBox
                CustomMessageBox.showwarning(
                    self.dialog, "재파싱 불가", "Packing List 파일이 없습니다."
                )
            except Exception as e:
                logger.warning(f"[UI] show no packing list warning failed: {e}")
            return
        try:
            from features.ai.bl_carrier_registry import CARRIER_TEMPLATES
            _ctpl = CARRIER_TEMPLATES.get(cid)
            cname = _ctpl.carrier_name if _ctpl else cid
            _tpl = getattr(self, '_inbound_template_data', {}) or {}
            if _ctpl:
                if not _tpl.get('gemini_hint_packing'):
                    _tpl['gemini_hint_packing'] = (
                        f"이 서류는 {cname} 선사의 Packing List입니다. "
                        f"BL번호 형식: {getattr(_ctpl, 'bl_format_hint', '')}"
                    )
                if not _tpl.get('gemini_hint_invoice'):
                    _tpl['gemini_hint_invoice'] = (
                        f"이 서류는 {cname} 선사의 Invoice/FA입니다."
                    )
                self._inbound_template_data = _tpl
        except (ImportError, ValueError, KeyError, AttributeError) as e:
            logger.warning(f"선사 힌트 강제 교체 실패: {e}")
        self._log_safe(f"🚢 선사 재파싱 시작: {cid} → PL/INV 힌트 적용")
        self._do_start_parsing_after_template()

    def _update_carrier_badge(self, badge_text: str, style_carrier_id: str = '') -> None:
        try:
            if not hasattr(self, '_carrier_label') or self._carrier_label is None:
                return
            _style_map = {
                'MSC': ('#FFFFFF', '#0066CC'),
                'MAERSK': ('#FFFFFF', '#009B77'),
                'HMM': ('#FFFFFF', '#E63946'),
                'CMA_CGM': ('#FFFFFF', '#E07B39'),
                'ONE': ('#FFFFFF', '#E91B8B'),
            }
            _carrier_id = (style_carrier_id or '').strip()
            bl_r = self.parsed_results.get('bl')
            if not _carrier_id and bl_r:
                _carrier_id = getattr(bl_r, 'carrier_id', '') or ''
            _fg, _bg = _style_map.get(_carrier_id, ('#333333', '#DDDDDD'))
            self._carrier_label.config(text=f"  {badge_text}  ", fg=_fg, bg=_bg, cursor='hand2')
        except Exception as _e:
            logger.debug(f"[CarrierBadge] UI 업데이트 실패(무시): {_e}")
