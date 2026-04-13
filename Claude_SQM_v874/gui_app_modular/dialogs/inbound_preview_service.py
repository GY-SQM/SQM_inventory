"""
P3-S1 Refactor: InboundPreviewService — 미리보기 기능 전담
gui_app_modular/dialogs/inbound_preview_service.py

책임: 미리보기 테이블 조작 + 편집 + 필터 + 정렬 + Undo/Redo + 복사/붙여넣기
"""

import logging
import tkinter as tk
from tkinter import END, BOTH, YES, X
from copy import deepcopy

from gui_app_modular.utils.ui_constants import tc

logger = logging.getLogger(__name__)

# 미리보기 컬럼 정의 — 재고 탭과 동일한 열 순서
PREVIEW_COLUMNS = [
    ("no",               "NO",               50,  "center"),
    ("lot_no",           "LOT NO",          110,  "center"),
    ("sap_no",           "SAP NO",          110,  "center"),
    ("bl_no",            "BL NO",           150,  "center"),
    ("product",          "PRODUCT",         180,  "center"),
    ("status",           "STATUS",           80,  "center"),
    ("container_no",     "CONTAINER",       130,  "center"),
    ("product_code",     "CODE",            100,  "center"),
    ("lot_sqm",          "LOT SQM",          80,  "center"),
    ("mxbg_pallet",      "MXBG",             70,  "center"),
    ("net_weight",       "NET(Kg)",          90,  "center"),
    ("gross_weight",     "GROSS(kg)",         90,  "center"),
    ("salar_invoice_no", "INVOICE NO",      120,  "center"),
    ("ship_date",        "SHIP DATE",        90,  "center"),
    ("arrival_date",     "ARRIVAL",          90,  "center"),
    ("con_return",       "CON RETURN",       95,  "center"),
    ("free_time",        "FREE TIME",        80,  "center"),
    ("warehouse",        "WH",              100,  "center"),
]


class InboundPreviewService:
    """미리보기 서비스 전담 클래스 — Mixin

    OneStopInboundDialog의 MRO에 합성되어
    self.preview_data / self.tree / self.filter_bar 등에 접근한다.
    """

    # ── 미리보기 데이터 관리 ─────────────────────────────────

    def _push_preview_to_main(self) -> None:
        """미리보기 데이터를 메인 앱 재고 탭에 반영."""
        if not getattr(self, 'app', None) or not hasattr(self.app, '_set_parsing_preview_data'):
            return
        try:
            self.app._set_parsing_preview_data(deepcopy(self.preview_data or []))
        except (RuntimeError, ValueError, TypeError) as e:
            logger.debug(f"미리보기 메인 반영 실패: {e}")

    def _clear_preview_from_main(self) -> None:
        """메인 화면 파싱 미리보기 해제 후 DB 기준으로 복원."""
        if not getattr(self, 'app', None) or not hasattr(self.app, '_set_parsing_preview_data'):
            return
        try:
            self.app._set_parsing_preview_data(None)
        except (RuntimeError, ValueError, TypeError) as e:
            logger.debug(f"미리보기 해제 실패: {e}")

    def _capture_original_preview_state(self) -> None:
        """파싱 직후 원본 데이터 스냅샷 저장."""
        self._original_preview_data = deepcopy(self.preview_data or [])

    def _reset_preview_to_original(self) -> None:
        """원본 초기화: 파싱 직후 상태로 복원."""
        if not self._original_preview_data:
            return
        from ..utils.custom_messagebox import CustomMessageBox
        if not CustomMessageBox.askyesno(self.dialog, "원본 초기화",
                "현재 편집/정렬/필터 상태를 버리고\n파싱 직후 원본으로 되돌릴까요?"):
            return
        self.preview_data = deepcopy(self._original_preview_data)
        self._edited_rows = set()
        self._undo_stack = []
        self._redo_stack = []
        self._sort_col = None
        self._sort_desc = False
        self._update_sort_headings()
        try:
            if self.filter_bar:
                self.filter_bar._reset_filters()
        except Exception as e:
            logger.debug(f"원본 초기화 필터 리셋 실패(무시): {e}")
        self._update_filter_values_from_preview()
        self._update_undo_redo_buttons()
        self._refresh_preview_tree_only()
        self._update_summary()
        self._push_preview_to_main()

    # ── 미리보기 테이블 표시/숨김 ────────────────────────────

    def _show_preview_table(self) -> None:
        """파싱 완료 후 미리보기 테이블 표시."""
        if getattr(self, 'compact_mode', False) or not getattr(self, '_tree_frame', None):
            return
        if getattr(self, "_tree_frame_visible", False):
            return
        try:
            self._tree_frame.pack(fill=BOTH, expand=YES, pady=(0, 3))
            self._tree_frame_visible = True
        except Exception as e:
            logger.warning(f"[UI] show preview table failed: {e}")

    def _hide_preview_table(self) -> None:
        """미리보기 테이블 숨김."""
        if getattr(self, 'compact_mode', False) or not getattr(self, '_tree_frame', None):
            return
        if not getattr(self, "_tree_frame_visible", False):
            return
        try:
            self._tree_frame.pack_forget()
            self._tree_frame_visible = False
        except Exception as e:
            logger.warning(f"[UI] hide preview table failed: {e}")

    # ── 정렬 ────────────────────────────────────────────────

    def _update_sort_headings(self) -> None:
        """미리보기 테이블 정렬 헤더 갱신."""
        if getattr(self, 'compact_mode', False):
            return
        if not getattr(self, 'tree', None) or not self.tree.winfo_exists():
            return
        for col_id, header, _w, _a in PREVIEW_COLUMNS:
            suffix = ""
            if col_id == self._sort_col:
                suffix = " ▼" if self._sort_desc else " ▲"
            self.tree.heading(
                col_id, text=f"{header}{suffix}", anchor='center',
                command=lambda c=col_id: self._toggle_preview_sort(c))

    def _toggle_preview_sort(self, col_id: str) -> None:
        """미리보기 테이블 정렬 토글."""
        if self._sort_col == col_id:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col_id
            self._sort_desc = False
        self._update_sort_headings()
        self._refresh_preview_tree_only()

    def _preview_sort_key(self, row: dict):
        """미리보기 정렬 키 계산."""
        col = self._sort_col
        if not col:
            return 0
        val = row.get(col, '')
        s = str(val or '').strip()
        if col in {'mxbg_pallet', 'free_time', 'net_weight', 'gross_weight'}:
            try:
                return float(s.replace(',', '')) if s else -1.0
            except ValueError:
                return -1.0
        if col in {'ship_date', 'arrival_date', 'con_return'}:
            return s[:10]
        return s.upper()

    # ── 필터 ────────────────────────────────────────────────

    def _on_change_preview_filter(self) -> None:
        """미리보기 필터 변경 핸들러."""
        self._refresh_preview_tree_only()

    def _update_filter_values_from_preview(self) -> None:
        """미리보기 필터 값 갱신."""
        if not self.filter_bar:
            return
        for col_id in ('sap_no', 'bl_no', 'container_no', 'product', 'status'):
            vals = [str((r.get(col_id, '') if isinstance(r, dict) else '') or '').strip()
                    for r in (self.preview_data or [])]
            self.filter_bar.update_filter_values(col_id, [v for v in vals if v])

    def _matches_preview_filters(self, row: dict) -> bool:
        """미리보기 필터 일치 여부 확인."""
        if not self.filter_bar:
            return True
        filters = self.filter_bar.get_filters()
        if not filters:
            return True
        for col_id, expected in filters.items():
            if str(row.get(col_id, '') or '').strip() != str(expected).strip():
                return False
        return True

    def _item_to_source_index(self, item_id) -> int:
        """미리보기 트리 아이템 → 소스 인덱스 변환."""
        try:
            return int(str(item_id))
        except (TypeError, ValueError):
            try:
                return self.tree.index(item_id)
            except Exception as e:
                logger.debug(f"[UI] tree item index lookup failed: {e}")
                return -1

    # ── 뷰 인덱스 빌드 ─────────────────────────────────────

    def _build_view_indices(self) -> list:
        """현재 필터 + 정렬 기준으로 표시할 행 인덱스 목록 계산."""
        indices = [i for i, r in enumerate(self.preview_data or [])
                   if self._matches_preview_filters(r)]
        if self._sort_col:
            indices = sorted(
                indices,
                key=lambda i: self._preview_sort_key(self.preview_data[i]),
                reverse=self._sort_desc
            )
        return indices

    def _get_upload_rows_for_db(self) -> list:
        """DB 업로드 대상 행 순서 결정."""
        rows = list(getattr(self, 'preview_data', []) or [])
        use_view_order = bool(self._var_upload_by_view_order and self._var_upload_by_view_order.get())
        if not use_view_order:
            self._log_safe("📌 DB 업로드 순서: 원본 순서(preview_data)")
            return rows
        indices = self._build_view_indices()
        ordered = [deepcopy(rows[i]) for i in indices if 0 <= i < len(rows)]
        self._log_safe(f"📌 DB 업로드 순서: 화면 정렬/필터 순서 적용 ({len(ordered)}건)")
        return ordered

    # ── 행 표시 값 ──────────────────────────────────────────

    def _row_display_values(self, row: dict) -> tuple:
        """미리보기 트리뷰 한 행의 표시 값."""
        vals = []
        for col_id, *_ in PREVIEW_COLUMNS:
            v = row.get(col_id, '')
            if col_id == 'container_no':
                v = self._format_container_display(v)
            vals.append(str(v or ''))
        return tuple(vals)

    def _lot_order_key(self, lot, fallback_idx: int) -> tuple:
        """LOT 정렬 키 (BL → 컨테이너 → LOT번호 순)."""
        if isinstance(lot, dict):
            bl = lot.get('bl_no', '') or ''
            cn = lot.get('container_no', '') or ''
            ln = lot.get('lot_no', '') or ''
            return (bl, cn, ln, fallback_idx)
        return ('', '', '', fallback_idx)

    def _format_container_display(self, val) -> str:
        """컨테이너 표시 포맷 — 접미사(-숫자) 숨김 옵션 적용."""
        s = str(val or '').strip()
        if not s:
            return ''
        if not getattr(self, '_show_container_suffix', False):
            import re
            s = re.sub(r'-\d+$', '', s)
        return s

    def _on_toggle_container_suffix(self) -> None:
        """컨테이너 접미사 표시 토글."""
        self._show_container_suffix = bool(
            getattr(self, '_var_show_container_suffix', None)
            and self._var_show_container_suffix.get()
        )
        self._refresh_preview_tree_only()

    # ── 미리보기 트리 갱신 ──────────────────────────────────

    def _refresh_preview_tree_only(self) -> None:
        """미리보기 테이블만 현재 preview_data로 갱신."""
        if getattr(self, 'compact_mode', False):
            return
        if not getattr(self, 'tree', None) or not self.tree.winfo_exists():
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not self.preview_data:
            return
        xc = getattr(self, '_cross_check_result', None)
        xc_lot_levels = {}
        xc_global_level = None
        xc_active = bool(xc) and not bool(getattr(xc, 'is_clean', True))
        if xc_active:
            if hasattr(xc, 'get_lot_levels'):
                try:
                    xc_lot_levels = xc.get_lot_levels() or {}
                except (AttributeError, TypeError) as _e:
                    logger.debug(f"onestop_inbound: {_e}")
                    xc_lot_levels = {}
            xc_global_level = getattr(xc, 'global_level', None)

        self._view_indices = self._build_view_indices()
        for pos, src_idx in enumerate(self._view_indices):
            row = self.preview_data[src_idx]
            row['no'] = str(src_idx + 1)
            values = self._row_display_values(row)
            base_tag = 'even' if pos % 2 == 0 else 'odd'
            if src_idx in self._edited_rows:
                tag = 'edited'
            elif xc_active:
                lot_no = (row.get('lot_no') or '').strip()
                lot_level = xc_lot_levels.get(lot_no) if lot_no else None
                effective = None
                if lot_level is not None and xc_global_level is not None:
                    try:
                        effective = max(lot_level, xc_global_level)
                    except (TypeError, ValueError):
                        effective = lot_level
                elif lot_level is not None:
                    effective = lot_level
                elif xc_global_level is not None:
                    effective = xc_global_level
                try:
                    level_num = int(effective) if effective is not None else 0
                except (TypeError, ValueError):
                    level_num = 0
                if level_num >= 3:
                    tag = 'xc_critical'
                elif level_num == 2:
                    tag = 'xc_warning'
                elif level_num == 1:
                    tag = 'xc_info'
                elif hasattr(xc, 'get_row_tag') and lot_no:
                    try:
                        tag = xc.get_row_tag(lot_no) or base_tag
                    except (AttributeError, TypeError, ValueError):
                        tag = base_tag
                else:
                    tag = base_tag
            else:
                tag = base_tag
            self.tree.insert('', END, iid=str(src_idx), values=values, tags=(tag,))

    def _display_preview(self) -> None:
        """미리보기 테이블 표시 (버튼 활성화 포함)."""
        def _update():
            self._push_preview_to_main()
            self._update_summary()
            if self.preview_data and self._has_required_docs():
                self.btn_upload.config(state='normal')
            else:
                self.btn_upload.config(state='disabled')
            if self.preview_data:
                self.btn_excel.config(state='normal')
            if getattr(self, 'compact_mode', False):
                return
            if not getattr(self, 'tree', None) or not self.tree.winfo_exists():
                return
            self._refresh_preview_tree_only()
            self._update_filter_values_from_preview()

        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, _update)

    # ── Undo / Redo ─────────────────────────────────────────

    def _snapshot_preview_state(self) -> dict:
        """미리보기 상태 스냅샷."""
        return {
            'preview_data': deepcopy(self.preview_data),
            'edited_rows': set(self._edited_rows),
        }

    def _push_undo_snapshot(self) -> None:
        """Undo 스냅샷 저장."""
        self._undo_stack.append(self._snapshot_preview_state())
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_redo_buttons()

    def _restore_preview_state(self, state: dict) -> None:
        """미리보기 상태 복원."""
        self.preview_data = deepcopy(state.get('preview_data', []))
        self._edited_rows = set(state.get('edited_rows', set()))
        self._refresh_preview_tree_only()
        self._update_summary()
        self._push_preview_to_main()
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self) -> None:
        """Undo/Redo 버튼 상태 업데이트."""
        try:
            if self.btn_undo and self.btn_undo.winfo_exists():
                self.btn_undo.config(state='normal' if self._undo_stack else 'disabled')
            if self.btn_redo and self.btn_redo.winfo_exists():
                self.btn_redo.config(state='normal' if self._redo_stack else 'disabled')
        except (RuntimeError, tk.TclError):
            pass

    def _undo_preview_edit(self, event=None):
        """미리보기 편집 Undo."""
        self._finish_preview_editing(save=True)
        if not self._undo_stack:
            return "break"
        self._redo_stack.append(self._snapshot_preview_state())
        state = self._undo_stack.pop()
        self._restore_preview_state(state)
        self._log_safe("↶ 되돌리기 적용")
        return "break"

    def _redo_preview_edit(self, event=None):
        """미리보기 편집 Redo."""
        self._finish_preview_editing(save=True)
        if not self._redo_stack:
            return "break"
        self._undo_stack.append(self._snapshot_preview_state())
        state = self._redo_stack.pop()
        self._restore_preview_state(state)
        self._log_safe("↷ 다시실행 적용")
        return "break"

    # ── 셀 편집 ─────────────────────────────────────────────

    def _preview_col_names(self) -> list:
        """미리보기 컬럼 ID 목록."""
        return [c[0] for c in PREVIEW_COLUMNS]

    def _editable_preview_columns(self) -> set:
        """편집 가능 컬럼 (No/Status 제외)."""
        return set(self._preview_col_names()) - {'no', 'status'}

    def _capture_preview_anchor(self, event=None) -> None:
        """마지막 클릭 위치(행, 열) 기록."""
        if not getattr(self, 'tree', None):
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return
        try:
            row_idx = self.tree.index(row_id)
            col_idx = max(0, int(col_id.replace('#', '')) - 1)
            self._preview_anchor = (row_idx, col_idx)
        except (ValueError, TypeError, tk.TclError):
            pass

    def _on_preview_cell_edit(self, event=None) -> None:
        """셀 더블클릭 인라인 편집."""
        if not getattr(self, 'tree', None):
            return
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        col_id = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        if not col_id or not row_id:
            return
        cols = self._preview_col_names()
        try:
            col_idx = int(col_id.replace('#', '')) - 1
        except ValueError:
            return
        if col_idx < 0 or col_idx >= len(cols):
            return
        col_name = cols[col_idx]
        if col_name not in self._editable_preview_columns():
            return
        self._capture_preview_anchor(event)
        self._finish_preview_editing(save=True)
        bbox = self.tree.bbox(row_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        current_val = str(self.tree.set(row_id, col_name))

        if col_name == 'product':
            entry = self._create_product_combobox(current_val, x, y, w, h)
        else:
            entry = tk.Entry(self.tree, font=('맑은 고딕', 10))
            entry.insert(0, current_val.replace(',', ''))
            entry.select_range(0, 'end')
            entry.place(x=x, y=y, width=w, height=h)

        entry.focus_set()
        self._editing_item = (row_id, col_name, entry)
        entry.bind('<Return>', lambda e: self._finish_preview_editing(save=True))
        entry.bind('<Escape>', lambda e: self._finish_preview_editing(save=False))
        entry.bind('<FocusOut>', lambda e: self._finish_preview_editing(save=True))

    def _coerce_preview_value(self, col_name: str, value: str) -> str:
        """미리보기 값 타입 강제 변환."""
        v = (value or '').strip()
        if col_name in {'mxbg_pallet', 'free_time'}:
            if not v:
                return ''
            try:
                return str(max(0, int(float(v.replace(',', '')))))
            except ValueError:
                return ''
        if col_name in {'net_weight', 'gross_weight'}:
            if not v:
                return ''
            try:
                return f"{float(v.replace(',', '')):,.1f}"
            except ValueError:
                return ''
        if col_name in {'ship_date', 'arrival_date', 'con_return'}:
            if not v:
                return ''
            s = v[:10]
            if len(s) == 10 and s.count('-') == 2 and s.replace('-', '').isdigit():
                return s
            return ''
        return v

    def _update_preview_cell(self, row_idx: int, col_name: str, new_value: str) -> None:
        """미리보기 셀 업데이트."""
        if row_idx < 0 or row_idx >= len(self.preview_data):
            return
        if col_name not in self._editable_preview_columns():
            return
        coerced = self._coerce_preview_value(col_name, new_value)
        self.preview_data[row_idx][col_name] = coerced
        self._edited_rows.add(row_idx)

    def _finish_preview_editing(self, save: bool = True) -> None:
        """인라인 편집 완료 처리."""
        if not self._editing_item:
            return
        row_id, col_name, entry = self._editing_item
        raw_val = entry.get().strip()
        entry.destroy()
        self._editing_item = None
        if not save:
            return
        try:
            row_idx = self._item_to_source_index(row_id)
            if row_idx < 0 or row_idx >= len(self.preview_data):
                return
            old_val = str(self.preview_data[row_idx].get(col_name, ''))
            new_val = self._coerce_preview_value(col_name, raw_val)
            if old_val == new_val:
                return
            self._push_undo_snapshot()
            self._update_preview_cell(row_idx, col_name, raw_val)
            if col_name == 'product' and row_idx < len(self.preview_data):
                try:
                    from .product_master_helper import auto_detect_product_code
                    detected_code = auto_detect_product_code(self.engine.db, new_val)
                    if detected_code:
                        self.preview_data[row_idx]['product_code'] = detected_code
                except (ImportError, AttributeError, TypeError) as e:
                    logger.warning(f"[UI] auto detect product code failed: {e}")
            self._refresh_preview_tree_only()
            self._update_summary()
            self._push_preview_to_main()
        except (ValueError, TypeError, tk.TclError):
            pass

    def _create_product_combobox(self, current_val, x, y, w, h):
        """product 열 더블클릭 시 제품 마스터 드롭다운 표시."""
        from tkinter import ttk
        try:
            from .product_master_helper import get_product_choices
            choices = get_product_choices(self.engine.db)
        except (ImportError, AttributeError, TypeError) as e:
            logger.warning(f"[UI] get product choices from master failed: {e}")
            choices = ['LITHIUM CARBONATE', 'NICKEL SULFATE HEXAHYDRATE']

        combo = ttk.Combobox(self.tree, values=choices, font=('맑은 고딕', 10), state='normal')
        current_upper = current_val.strip().upper()
        matched = False
        for i, ch in enumerate(choices):
            if current_upper in ch.upper():
                combo.current(i)
                matched = True
                break
        if not matched:
            combo.set(current_val)
        combo.place(x=x, y=y, width=max(w, 300), height=h)

        def _on_product_selected(event=None):
            selected = combo.get()
            try:
                from .product_master_helper import parse_product_choice
                code, full_name = parse_product_choice(selected)
                combo.set(full_name)
                if code and self._editing_item:
                    row_id = self._editing_item[0]
                    try:
                        row_idx = self._item_to_source_index(row_id)
                        if 0 <= row_idx < len(self.preview_data):
                            self.preview_data[row_idx]['product_code'] = code
                    except (ValueError, TypeError):
                        pass
            except Exception as e:
                logger.warning(f"[UI] product combobox selection handling failed: {e}")

        combo.bind('<<ComboboxSelected>>', _on_product_selected)
        return combo

    # ── 복사 / 붙여넣기 / 잘라내기 ──────────────────────────

    def _setup_preview_edit_bindings(self) -> None:
        """미리보기 편집 키바인딩 설정."""
        if not getattr(self, 'tree', None):
            return
        self.tree.bind('<Double-1>', self._on_preview_cell_edit, add='+')
        self.tree.bind('<Button-1>', self._capture_preview_anchor, add='+')
        self.tree.bind('<Control-c>', self._copy_preview_selection, add='+')
        self.tree.bind('<Control-C>', self._copy_preview_selection, add='+')
        self.tree.bind('<Control-v>', self._paste_preview_from_clipboard, add='+')
        self.tree.bind('<Control-V>', self._paste_preview_from_clipboard, add='+')
        self.tree.bind('<Control-x>', self._cut_preview_selection, add='+')
        self.tree.bind('<Control-X>', self._cut_preview_selection, add='+')
        self.tree.bind('<Delete>', self._clear_preview_selection, add='+')
        self.tree.bind('<Control-z>', self._undo_preview_edit, add='+')
        self.tree.bind('<Control-Z>', self._undo_preview_edit, add='+')
        self.tree.bind('<Control-y>', self._redo_preview_edit, add='+')
        self.tree.bind('<Control-Y>', self._redo_preview_edit, add='+')
        if getattr(self, 'dialog', None):
            self.dialog.bind('<Control-z>', self._undo_preview_edit, add='+')
            self.dialog.bind('<Control-Z>', self._undo_preview_edit, add='+')
            self.dialog.bind('<Control-y>', self._redo_preview_edit, add='+')
            self.dialog.bind('<Control-Y>', self._redo_preview_edit, add='+')
            self.dialog.bind('<Control-x>', self._cut_preview_selection, add='+')
            self.dialog.bind('<Control-X>', self._cut_preview_selection, add='+')
            self.dialog.bind('<Delete>', self._clear_preview_selection, add='+')

    def _copy_preview_selection(self, event=None):
        """선택 행 TSV 복사 (엑셀 호환)."""
        if not getattr(self, 'tree', None):
            return "break"
        items = self.tree.selection()
        if not items:
            focused = self.tree.focus()
            if focused:
                items = (focused,)
        if not items:
            return "break"
        headers = [c[1] for c in PREVIEW_COLUMNS]
        lines = ['\t'.join(headers)]
        for item_id in items:
            vals = self.tree.item(item_id, 'values')
            lines.append('\t'.join(str(v) for v in vals))
        self.tree.clipboard_clear()
        self.tree.clipboard_append('\n'.join(lines))
        return "break"

    def _selected_preview_cells(self):
        """선택 행 + 마지막 클릭 열 기준의 셀 좌표 목록."""
        if not getattr(self, 'tree', None):
            return []
        cols = self._preview_col_names()
        sel_items = list(self.tree.selection())
        if not sel_items:
            focus = self.tree.focus()
            if focus:
                sel_items = [focus]
        if not sel_items:
            return []
        _row_anchor, col_idx = self._preview_anchor
        col_idx = max(0, min(col_idx, len(cols) - 1))
        col_name = cols[col_idx]
        if col_name not in self._editable_preview_columns():
            return []
        out = []
        for item_id in sel_items:
            try:
                row_idx = self._item_to_source_index(item_id)
                if 0 <= row_idx < len(self.preview_data):
                    out.append((row_idx, col_name))
            except (ValueError, TypeError, tk.TclError):
                continue
        return out

    def _clear_preview_selection(self, event=None):
        """Delete: 선택 셀 비우기."""
        cells = self._selected_preview_cells()
        if not cells:
            return "break"
        self._push_undo_snapshot()
        for row_idx, col_name in cells:
            self._update_preview_cell(row_idx, col_name, '')
        self._refresh_preview_tree_only()
        self._update_summary()
        self._push_preview_to_main()
        return "break"

    def _cut_preview_selection(self, event=None):
        """Ctrl+X: 선택 셀 복사 후 비우기."""
        cells = self._selected_preview_cells()
        if not cells:
            return "break"
        values = []
        for row_idx, col_name in cells:
            values.append(str(self.preview_data[row_idx].get(col_name, '') or ''))
        try:
            self.tree.clipboard_clear()
            self.tree.clipboard_append('\n'.join(values))
        except tk.TclError:
            pass
        self._push_undo_snapshot()
        for row_idx, col_name in cells:
            self._update_preview_cell(row_idx, col_name, '')
        self._refresh_preview_tree_only()
        self._update_summary()
        self._push_preview_to_main()
        return "break"

    def _paste_preview_from_clipboard(self, event=None):
        """선택 셀을 시작점으로 TSV 블록 붙여넣기."""
        if not getattr(self, 'tree', None):
            return "break"
        try:
            raw = self.tree.clipboard_get()
        except tk.TclError:
            return "break"
        lines = [ln for ln in raw.replace('\r', '').split('\n') if ln.strip()]
        if not lines:
            return "break"
        start_row, start_col = self._preview_anchor
        cols = self._preview_col_names()
        first_parts = [p.strip() for p in lines[0].split('\t')]
        if first_parts and len(first_parts) == len(cols):
            header_names = [c[1] for c in PREVIEW_COLUMNS]
            if all(fp in header_names for fp in first_parts[:min(3, len(first_parts))]):
                lines = lines[1:]
        if lines:
            self._push_undo_snapshot()
        view_items = list(self.tree.get_children())
        for r_off, line in enumerate(lines):
            view_idx = start_row + r_off
            if view_idx >= len(view_items):
                break
            row_idx = self._item_to_source_index(view_items[view_idx])
            if row_idx < 0 or row_idx >= len(self.preview_data):
                continue
            parts = [p.strip() for p in line.split('\t')]
            for c_off, val in enumerate(parts):
                col_idx = start_col + c_off
                if col_idx >= len(cols):
                    break
                col_name = cols[col_idx]
                self._update_preview_cell(row_idx, col_name, val)
        self._refresh_preview_tree_only()
        self._update_summary()
        self._push_preview_to_main()
        return "break"

    # ── 트리 데이터 동기화 ──────────────────────────────────

    def _sync_tree_edit_to_preview_data(self) -> None:
        """GlobalEditableTree 편집 후 preview_data 동기화."""
        if not hasattr(self, 'tree') or not hasattr(self, 'preview_data'):
            return
        try:
            columns = [c for c, *_ in PREVIEW_COLUMNS]
            if not columns:
                columns = list(self.tree['columns'])
            for item_id in self.tree.get_children():
                values = self.tree.item(item_id, 'values')
                idx = list(self.tree.get_children()).index(item_id)
                if idx < len(self.preview_data):
                    row = self.preview_data[idx]
                    if isinstance(row, dict):
                        for ci, col_id in enumerate(columns):
                            if ci < len(values):
                                row[col_id] = values[ci]
            logger.debug(f"[v8.6.4] preview_data 동기화 완료: {len(self.preview_data)}행")
        except (ValueError, KeyError, TypeError, IndexError) as e:
            logger.warning(f"[v8.6.4] preview_data 동기화 스킵: {e}")
