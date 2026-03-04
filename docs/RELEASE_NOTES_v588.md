# SQM v5.8.8 — UI Phase3·Phase4

## 개요
- **Phase3**: 8px 그리드(Spacing) + 폰트 3단계(FontScale) 적용.
- **Phase4**: 다이얼로그 크기 표준화 — `DialogSize.get_geometry(parent, 'small'|'medium'|'large')` + `center_dialog(dialog, parent)`.

---

## v5.8.8에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **Phase3** | column_toggle, toolbar_mixin, inventory_tab, tonbag_tab, help_dialogs, settings_dialog — padx/pady/padding → Spacing.XS/SM/MD/LG, 폰트 → FontScale.heading()/body()/small()/subtitle() |
| **Phase4** | settings_dialog, do_update_dialog, lot_detail_dialog, onestop_inbound, toolbar_mixin(검색), help_dialogs, inventory_tab, tonbag_tab, backup_handlers, context_menu_mixin, drag_drop_mixin, statusbar_mixin, keybindings_mixin, location_upload_preview, allocation_preview, column_mapper_dialog, auto_backup, outbound_preview_dialog, theme_mixin, test_runner_dialog, diagnostics_mixin — geometry 하드코딩 제거, DialogSize + center_dialog |
| **문서** | docs/UI_IMPLEMENTATION_PHASES.md Phase3·Phase4 적용 현황 추가 |
| **버전** | version.py — __version__ = 5.8.8 |

---

## 변경된 파일 요약

| 구분 | 파일 |
|------|------|
| **버전** | version.py, VERSION.txt |
| **문서** | docs/UI_IMPLEMENTATION_PHASES.md, docs/RELEASE_NOTES_v588.md |
| **Phase3** | gui_app_modular/utils/column_toggle.py, mixins/toolbar_mixin.py, tabs/inventory_tab.py, tabs/tonbag_tab.py, dialogs/help_dialogs.py, dialogs/settings_dialog.py |
| **Phase4** | dialogs/settings_dialog.py, do_update_dialog.py, lot_detail_dialog.py, onestop_inbound.py, mixins/toolbar_mixin.py, dialogs/help_dialogs.py, tabs/inventory_tab.py, tabs/tonbag_tab.py, handlers/backup_handlers.py, mixins/context_menu_mixin.py, drag_drop_mixin.py, statusbar_mixin.py, keybindings_mixin.py, dialogs/location_upload_preview.py, allocation_preview.py, column_mapper_dialog.py, auto_backup.py, outbound_preview_dialog.py, mixins/theme_mixin.py, test_runner_dialog.py, mixins/diagnostics_mixin.py |

---

*작성일: 2026-02-17 | SQM v5.8.8*
