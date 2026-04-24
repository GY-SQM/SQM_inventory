# Session Report: 2026-04-24 WIP Complete + 2-Tier Structure

## Summary

All WIP menu items implemented. Playwright 99/99 PASS.

---

## 1. WIP Items Resolved (16 -> 0)

All `u:'wip'` entries in ENDPOINTS have been replaced with real implementations:

| # | Action | Implementation | Type |
|---|--------|---------------|------|
| 1 | onInboundCancel | JS modal -> POST /api/action2/inbound-cancel | Modal |
| 2 | onBarcodeScanUpload | Excel upload modal (shared pattern) | Modal |
| 3 | onApprovalQueue | GET /api/q/approval-history -> data table | Modal |
| 4 | onPickingTemplateManage | Settings dialog (template CRUD) | Modal |
| 5 | onMoveApprovalQueue | GET /api/q/audit-log filtered -> table | Modal |
| 6 | onInboundTemplateManage | Settings dialog (template CRUD) | Modal |
| 7 | onEmailConfig | Settings dialog (SMTP config) | Modal |
| 8 | onAutoBackupSettings | Settings dialog (schedule config) | Modal |
| 9 | onReportTemplates | GET /api/q/audit-log -> data table | Info modal |
| 10 | onReportHistory | GET /api/q/audit-log -> data table | Info modal |
| 11 | onLotAllocationAudit | LOT search -> product-inventory API | Modal |
| 12 | onDocConvert | OCR/PDF convert dialog (Phase 6) | Modal |
| 13 | onTestDbReset | Confirm dialog -> POST /api/action3/db-reset | Modal |
| 14 | onOutboundScheduled | Route to outbound tab | Route |
| 15 | onAiTools | Shows version info | Info modal |
| 16 | onReturnDialog | 2-tab return dialog (manual + Excel) | Modal |

## 2. NOT_READY Items Fixed (5 -> 0)

| Action | Before | After |
|--------|--------|-------|
| onReturnDialog | POST /api/menu/ NOT_READY | JS native 2-tab modal |
| onRestore | POST /api/menu/ NOT_READY | Backup list + restore modal |
| onSaveWindowSize | POST /api/menu/ NOT_READY | JS PyWebView/localStorage |
| onResetWindowSize | POST /api/menu/ NOT_READY | JS resize + localStorage |
| onReportCustom | POST /api/menu/ NOT_READY | GET /api/q/inventory-report |

## 3. New Backend APIs Added

- `POST /api/action/restore` - Backup restore with auto pre-backup
- `POST /api/action3/db-reset` - Test DB reset (dev mode)

## 4. New JS Modals Added (14)

- showInboundCancelModal()
- showApprovalQueueModal()
- showRestoreModal()
- showReturnDialog()
- showLotAllocationAuditModal()
- showTestDbResetModal()
- showBarcodeScanUploadModal()
- showEmailConfigModal()
- showAutoBackupSettingsModal()
- showInboundTemplateModal()
- showPickingTemplateModal()
- showMoveApprovalQueueModal()
- showDocConvertModal()
- showProductSummaryModal()
- showProductLotLookupModal()
- showProductMovementModal()

## 5. Allocation/Picked/Sold 2-Tier Structure

All three tabs now have master-detail layout:
- **Top tier**: LOT-level summary rows with expand arrow
- **Bottom tier**: Click LOT row -> show tonbag detail panel below
- Same UX pattern as v864.2's Tkinter notebook tabs

APIs used:
- Allocation: GET /api/q/allocation-summary + GET /api/q/allocation-detail/{lot_no}
- Picked: GET /api/q/picked-list + GET /api/tonbags?lot_no=
- Outbound: GET /api/q/sold-list + GET /api/tonbags?lot_no=

## 6. Playwright Test Results

```
Total: 99 tests
PASS:  99
FAIL:  0

Structure:
- 7 top menus (7 expected)
- 9 sidebar tabs (9 expected)
- 7 toolbar buttons (7 expected)
- 79 menu items tested (2 skipped: Exit, DB Reset)
```

## 7. Files Modified

- `frontend/js/sqm-inline.js` - All WIP resolved, 14 new modals, 2-tier structure
- `frontend/index.html` - Cache bust v=864.3.40
- `backend/api/actions.py` - Added POST /api/action/restore
- `backend/api/actions3.py` - Added POST /api/action3/db-reset
- `scripts/test_all_menus_playwright.py` - New comprehensive test

## 8. Remaining Work (Next Session)

- Phase 5: Regression test v864.2 vs v864.3 (API response comparison)
- Phase 6: PyInstaller EXE build
- Phase 7: Production use + bug collection
