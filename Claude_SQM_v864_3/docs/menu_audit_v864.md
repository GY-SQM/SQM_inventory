# v864 메뉴 동작 전수검사 리포트

조사 기준: `F:\program\SQM_inventory\Claude_SQM_v864_1` 정적 분석 (read-only)
조사일: 2026-04-18
대상: custom_menubar.py (CustomMenuBar), menu_mixin.py (MenuMixin), toolbar_mixin.py (ToolbarMixin),
context_menu_mixin.py (ContextMenuMixin), menu_registry.py, gui_app_modular/tabs/*,
gui_app_modular/handlers/*, gui_app_modular/mixins/*, gui_app_modular/dialogs/*

---

## 0. 요약

| 카테고리 | 수량 |
|---|---|
| 전체 메뉴 항목 (separator 제외) | 약 115개 |
| 정상 연결 확인 | 약 98개 |
| 끊어진 링크 (HIGH/CRITICAL) | 3개 |
| 경고 (조건부 optional, 폴백 없음 등) | 약 14개 |
| DEPRECATED / 불완전 | 2개 |

- CRITICAL 끊김: `_show_product_master`, `_show_product_inventory_report`
  (main_app.py 내에서 `if __name__ == '__main__':` 블록 안쪽에 잘못 들여쓰기되어 정의되어
  Full 앱 실행 시 바인딩되지 않음) — 호출 경로 다수
- Action Bar 버튼 2건 미구현: `_on_backup_db`, `_show_settings_dialog`
- View/보기 메뉴 `_show_theme_selector` — `ThemeMixin`에 존재하여 OK

---

## 1. 메인 메뉴바

custom_menubar.py `CustomMenuBar._create_menus()` 순서:
outbound → file → report → tools → features(no-op) → view → help → product

### 1-1. 📤 출고 메뉴 (탑레벨)

menu_registry.py `FILE_MENU_OUTBOUND_ITEMS` 기반 (custom_menubar.py L137-162, menu_mixin.py L145-155, toolbar_mixin.py L478-508)

| 라벨 | 핸들러 | 상태 | 위치 | 비고 |
|---|---|---|---|---|
| 🚀 즉시 출고 (원스톱) | `_on_s1_onestop_outbound` | 정상 | outbound_handlers.py:2858 | |
| 📤 빠른 출고 (붙여넣기) | `_on_quick_outbound_paste` | 정상 | outbound_handlers.py:1482 | |
| 📋 Picking List 업로드 (PDF) | `_on_picking_list_upload` | 정상 | outbound_handlers.py:1672 | |
| 📊 바코드 스캔 업로드 | `_on_barcode_scan_upload` | 정상 | outbound_handlers.py:2208 | |
| 📷 스캔 탭으로 이동 | `_on_go_scan_tab` | 정상 | outbound_handlers.py:1062 | |
| 📋 Allocation 입력 | `_on_allocation_input_unified` | 정상 | outbound_handlers.py:1302 | |
| ✅ 승인 대기 (optional) | `_show_allocation_approval_queue` | 정상 | outbound_handlers.py:1615 | |
| 📌 예약 반영 (승인분) (optional) | `_apply_approved_allocation` | 정상 | outbound_handlers.py:1633 | |
| 📜 승인 이력 조회 (optional) | `_show_allocation_approval_history` | 정상 | outbound_handlers.py:1624 | |
| 📋 판매 배정 탭으로 이동 | `_on_go_allocation_tab` | 정상 | outbound_handlers.py:1040 | |
| 📋 출고 현황 조회 (optional) | `_show_outbound_history` | 정상 | advanced_dialogs_mixin.py:1060 | |
| 📊 Sales Order 업로드 (optional) | `_on_sales_order_upload` | 정상 | toolbar_mixin.py:1804 | |
| 🔁 Swap 리포트 (optional) | `_show_swap_report_dialog` | 정상 | outbound_handlers.py:2693 | |
| 📦 출고 피킹 템플릿 관리 | `_on_picking_template_manage` | 정상 | advanced_dialogs_mixin.py:2062 | |

### 1-2. 📁 파일 메뉴 (입고 · 내보내기 · 백업 · 도구 · 최근 파일)

`FILE_MENU_INBOUND_ITEMS` 입고 서브메뉴:

| 라벨 | 핸들러 | 상태 | 위치 | 비고 |
|---|---|---|---|---|
| 📄 PDF 스캔 입고 | `_on_pdf_inbound` | 정상 | inbound_processor.py:26 | |
| 📊 엑셀 파일 수동 입고 | `_bulk_import_inventory_simple` | 정상 | import_handlers.py:181 | inbound_handlers.py:172에도 중복 |
| 📋 D/O 후속 연결 | `_on_do_update` | 정상 | inbound_processor.py:151 | |
| 📍 톤백 위치 매핑 (optional) | `_on_tonbag_location_upload` | 정상 | tonbag_tab.py:406 | |
| ✅ 대량 이동 승인 (optional) | `_on_move_approval_queue` | 정상 | advanced_dialogs_mixin.py:2077 | |
| 🔄 반품 (재입고) | `_show_return_dialog` | 정상 | advanced_dialogs_mixin.py:212 | 서브메뉴 전환 |
| 📂 반품 입고 (Excel) | `_on_return_inbound_upload` | 정상 | advanced_dialogs_mixin.py:70 | |
| 📊 반품 사유 통계 | `_show_return_statistics` | 정상 | advanced_dialogs_mixin.py:1520 | |
| 📋 입고 현황 조회 (optional) | `_bulk_import_inventory` | 정상 | bulk_import_mixin.py:21 | |
| 📝 입고 파싱 템플릿 관리 | `_on_inbound_template_manage` | 정상 | advanced_dialogs_mixin.py:2048 | |
| 📦 제품 마스터 관리 | `_show_product_master` | ❌ CRITICAL | main_app.py:1367 (dead) | 섹션 5 참조 |
| ⚙️ 이메일 설정 | `_show_email_config` | 정상 | advanced_dialogs_mixin.py:1576 | |
| 🔍 정합성 검증 (시각화) | `_on_integrity_report_v760` | 정상 | advanced_dialogs_mixin.py:1590 | |
| 🛠️ LOT 상태 정합성 복구 | `_on_fix_lot_status_integrity` | 정상 | toolbar_mixin.py:1353 | |

반품(재입고) 서브메뉴 (`FILE_MENU_INBOUND_RETURN_SUB_ITEMS`):
- "📝 소량 반품 (1~2건)" → `_show_return_dialog(0)` 정상
- "📂 다량 반품 (Excel)" → `_show_return_dialog(1)` 정상

내보내기 (`FILE_MENU_EXPORT_ITEMS` → `_on_export_click(option)`):
모든 4항목 (통관요청/루비리/톤백/통합) 정상 — export_handlers.py:26

백업 (`FILE_MENU_BACKUP_ITEMS`):

| 라벨 | 핸들러 | 상태 | 위치 |
|---|---|---|---|
| 💾 백업 생성 | `_on_backup_click` | 정상 | backup_handlers.py:34 |
| 🔄 복원 | `_on_restore_click` | 정상 | backup_handlers.py:61 |
| 📋 백업 목록 | `_show_backup_list` | 정상 | backup_handlers.py:108 |
| ⏰ 자동 백업 설정 | `_show_auto_backup_settings` | 정상 | backup_handlers.py:219 |

파일 > 도구 서브메뉴 (custom_menubar L223-228):
- 📷 문서 변환 (OCR/PDF) → `_show_doc_convert_safe` → `_show_document_convert_dialog` 존재 (advanced_dialogs_mixin.py:966). 정상
- 🩺 데이터 정합성 검사 → `_show_integrity_check_safe`. 정상

최근 파일: `_update_recent_files_menu` 의존 — 존재 여부 확인 필요(섹션 9)

종료: `self.parent.quit` 정상

### 1-3. 📝 보고서 메뉴 (MENU_REPORT_ITEMS)

| 라벨 | 핸들러 | 상태 | 위치 |
|---|---|---|---|
| 📄 거래명세서 생성 | `_generate_outbound_invoice` | 정상 | advanced_dialogs_mixin.py:1329 |
| 📦 Detail of Outbound | `_on_detail_of_outbound_report` | 정상 | advanced_dialogs_mixin.py:2091 |
| 📋 Sales Order DN | `_on_sales_order_dn_report` | 정상 | advanced_dialogs_mixin.py:2099 |
| 🔍 DN 교차검증 | `_on_dn_cross_check` | 정상 | toolbar_mixin.py:1879 |
| 📝 고객 보고서 생성 (optional) | `_generate_customer_report` | ⚠️ 미구현 | - |
| 📂 보고서 양식 관리 (optional) | `_manage_report_templates` | ⚠️ 미구현 | - |
| 📋 보고서 이력 조회 (optional) | `_show_report_history` | ⚠️ 미구현 | - |
| 📦 재고 현황 보고서 | `_generate_inventory_pdf_report` | 정상 | pdf_report_handler.py:20 |
| 📈 입출고 내역 | `_generate_transaction_pdf` | 정상 | pdf_handlers.py:329 |
| 📅 월간 실적 PDF (optional) | `_generate_monthly_pdf_v398` | 정상 | pdf_handlers.py:581 |
| 📊 일일 현황 PDF (optional) | `_generate_daily_pdf_v398` | 정상 | pdf_handlers.py:554 |
| 🔖 LOT 상세 | `_generate_lot_detail_pdf` | 정상 | pdf_handlers.py:455 |

`optional=True`여서 3개 미구현이어도 메뉴에서 자동 제거됨 → 경고 수준.

### 1-4. 🔧 도구 메뉴

custom_menubar.py `_create_tools_menu` (L261-362):

| 라벨 | 핸들러 | 상태 | 비고 |
|---|---|---|---|
| 📦 제품 마스터 관리 | `_show_product_master` | ❌ CRITICAL | 섹션 5 |
| 📊 제품별 재고 현황 | `_show_product_inventory_report` | ❌ CRITICAL | 섹션 5 |
| 📊 LOT Allocation·톤백 현황 | `_show_lot_allocation_audit_dialog` | 정상 | lot_allocation_audit_mixin.py:247 |
| 📋 D/O 후속 연결 | `_on_do_update` | 정상 | |
| 📄 PDF/이미지 변환 → Excel | `_convert_pdf_to_excel` | 정상 | pdf_handlers.py:27 |
| 📄 → Word | `_convert_pdf_to_word` | 정상 | pdf_handlers.py:80 |
| 📄 → 일괄 변환 | `_batch_convert_pdf_excel` | 정상 | pdf_handlers.py:136 |
| 📄 → 🔍 분석 | `_analyze_pdf` | 정상 | pdf_handlers.py:199 |
| 📷 문서 변환 (OCR/PDF) | `_show_document_convert_dialog` | 정상 | advanced_dialogs_mixin.py:966 |
| 📋 PDF 보고서 → 📦 재고 현황 | `_generate_inventory_pdf_report` | 정상 | pdf_report_handler.py:20 |
| 📋 PDF 보고서 → 📈 입출고 내역 | `_generate_transaction_pdf` | 정상 | |
| 📋 PDF 보고서 → 📤 출고 확인서 | `_generate_outbound_confirm_pdf` | 정상 | pdf_handlers.py:495 |
| 📋 PDF 보고서 → 🔖 LOT 상세 | `_generate_lot_detail_pdf` | 정상 | |
| 📋 PDF 보고서 → 📊 일일 현황 PDF | `_generate_daily_pdf_v398` | 정상 | |
| 📋 PDF 보고서 → 📅 월간 실적 PDF | `_generate_monthly_pdf_v398` | 정상 | |
| 🩺 데이터 정합성 검사 | `_show_integrity_check_safe` | 정상 | custom_menubar.py:774 |
| 🤖 Gemini AI → API 사용 (checkbutton) | `_toggle_gemini` | 정상 | settings_dialog.py:224 |
| 🤖 Gemini AI → 🚢 선사 BL 등록 | `_on_bl_carrier_register` | 정상 | settings_dialog.py:465 |
| 🤖 Gemini AI → 🔬 선사 패턴 분석 | `_on_bl_carrier_analyze` | 정상 | settings_dialog.py:817 |
| 🤖 Gemini AI → 💬 AI 채팅 | `_open_ai_chat` | 정상 | settings_dialog.py:407 |
| 🤖 Gemini AI → ⚙️ API 설정 | `_show_api_settings` | 정상 | settings_dialog.py:34 |
| 🤖 Gemini AI → 🔬 API 테스트 | `_test_gemini_api_connection` | 정상 | settings_dialog.py:374 |
| 🛡️ DB 보호 (조건부 HAS_DB_PROTECTION) → 🔍 무결성 검증 | `_verify_db_integrity` | 정상 | diagnostics_mixin.py:26 |
| 🛡️ DB 보호 → 📋 작업 로그 | `_show_action_log` | 정상 | diagnostics_mixin.py:102 |
| 🛡️ DB 보호 → 💾 로그 내보내기 | `_export_action_log` | 정상 | diagnostics_mixin.py:139 |
| 🛡️ DB 보호 → 🔄 체크섬 갱신 | `_update_checksum` | 정상 | diagnostics_mixin.py:63 |
| 🔍 DB 검사 | `_on_integrity_check` | 정상 | backup_handlers.py:269, toolbar_mixin.py:1381 |
| 🔧 DB 최적화 | `_on_optimize_db` | 정상 | backup_handlers.py:243 |
| 📋 로그 정리 | `_on_cleanup_logs` | 정상 | backup_handlers.py:300 |
| ℹ️ DB 정보 | `_show_db_info` | 정상 | backup_handlers.py:339 |
| 🗑️ 테스트 DB 초기화 (개발자 모드) | `_show_test_db_reset_popup` | 정상 | keybindings_mixin.py:328 |
| ✨ 고급 → 🔬 입고 검증 | `_dry_run_inbound` | 정상 | diagnostics_mixin.py:274 |
| ✨ 고급 → 🔬 출고 검증 | `_dry_run_outbound` | 정상 | diagnostics_mixin.py:328 |
| ✨ 고급 → 🩺 전체 진단 | `_run_self_test` | 정상 | diagnostics_mixin.py:191 |
| ✨ 고급 → 🧪 단위 테스트 | `_open_test_runner` | 정상 | diagnostics_mixin.py:181 |

### 1-5. 👁️ View 메뉴

custom_menubar `_create_view_menu` (L370-407):

| 라벨 | 핸들러 | 상태 |
|---|---|---|
| 🔄 Refresh (F5) | `_refresh_inventory` | 정상 (inventory_tab.py:1038) |
| 📦 Inventory | `notebook.select(tab_inventory)` | 정상 |
| 📋 Allocation | → tab_allocation | 정상 |
| 🚛 Picked | → tab_picked | 정상 |
| 📤 Outbound | → tab_sold | 정상 |
| 🔄 Return | → tab_return | 정상 |
| 🔀 Move | → tab_move | 정상 |
| 📊 Dashboard | → tab_dashboard | 정상 |
| 📝 Log | → tab_log | 정상 |
| 📷 Scan (optional) | → tab_scan | 정상 |
| 🎨 Theme | `_show_theme_selector` | 정상 (theme_mixin.py:294) |

### 1-6. ❓ 도움말 메뉴 (MENU_HELP_ITEMS)

| 라벨 | 핸들러 | 상태 | 위치 |
|---|---|---|---|
| 📖 사용법 | `_show_help` | 정상 | keybindings_mixin.py:264 |
| ⌨️ 단축키 안내 | `_show_shortcuts` | 정상 | menu_mixin.py:352 |
| 📊 STATUS 상태값 안내 (optional) | `_show_status_guide` | 정상 | custom_menubar.py:644 (self 탐색 폴백) |
| 💾 DB 백업/복구 가이드 (optional) | `_show_backup_guide` | 정상 | custom_menubar.py:699 |
| ℹ️ 시스템 정보 (optional) | `_show_system_info` | ⚠️ 미구현 | 자동 제거됨 |
| 📝 버전 정보 | `_show_about` | 정상 | menu_mixin.py:373 |

`_show_status_guide`·`_show_backup_guide`는 CustomMenuBar(self)에만 정의되어 있어
help_menu 빌더에서 `getattr(self.app, ...) or getattr(self, ...)` 2단계 탐색으로 연결됨(custom_menubar.py L422).
toolbar_mixin 쪽 `_build_help_menu`는 `self.app`이 아니라 직접 `getattr(self, ...)` 만 하므로
**⚠️ toolbar 도움말 메뉴에는 위 두 항목이 안 나타날 가능성 있음** (섹션 9 참고).

### 1-7. 📦 품목 메뉴

custom_menubar `_create_product_menu` (L432-441):

| 라벨 | 핸들러 | 상태 | 위치 |
|---|---|---|---|
| 📋 품목별 재고 요약 | `_show_product_summary` | 정상 | product_handlers.py:27 |
| 🔍 품목별 LOT 조회 | `_show_product_lot_lookup` | 정상 | product_handlers.py:128 |
| 📊 품목별 입출고 현황 | `_show_product_movement` | 정상 | product_handlers.py:239 |

### 1-8. 🚀 v2.7 메뉴 (DEPRECATED — 빈 함수)

`_create_features_menu` (L364-368): `pass`만 존재. v8.1.5에서 미사용으로 완전 비활성 결정.
정상 — 메뉴 생성 안 됨.

---

## 2. 툴바 (toolbar_mixin.py)

### 2-1. 메뉴 드롭다운 (_build_all_menus)

7개 드롭다운: 📁 파일 / 📥 입고 / 📤 출고 / 📊 재고 / 📝 보고서 / 🔧 설정/도구 / ❓ 도움말

각 빌더:
- `_build_file_menu` (L568-633): 내보내기/백업/BL 선사 도구/Gemini AI/PDF 변환/종료 — 모두 정상
- `_build_inbound_menu` (L433-476): menu_registry 기반 — 위 입고 메뉴와 동일 매핑
- `_build_outbound_menu` (L478-508): menu_registry 기반
- `_build_report_menu` → `MENU_STOCK_ITEMS` (재고 메뉴) — 정상
- `_build_customer_report_menu` → `MENU_REPORT_ITEMS` — 정상 (위 1-3과 동일)
- `_build_settings_menu` (L635-704): 화면/테마/글꼴/개발자 모드/자동 갱신/정합성 등 — 아래 개별 확인
- `_build_help_menu` (L757-789): `MENU_HELP_ITEMS` — 정상 (단 위 1-6 경고)

### 2-2. 설정/도구 메뉴 개별 항목

| 라벨 | 핸들러 | 상태 | 위치 |
|---|---|---|---|
| 🔄 새로고침 (F5) | `_refresh_all_data` | 정상 | toolbar_mixin.py:1796 |
| 💾 현재 창 크기 저장 | `_on_save_window_size` | 정상 | toolbar_mixin.py:707 |
| ↩️ 기본 창 크기로 초기화 | `_on_reset_window_size` | 정상 | toolbar_mixin.py:722 |
| 🎨 테마 선택 → 각 테마 | `_change_theme(theme)` | 정상 | theme_mixin.py |
| 🔤 글꼴 크기 → 11/13/16 | `_change_font_size(n)` | 정상 | theme_mixin.py |
| 🧪 개발자 모드 (checkbutton) | `_on_toggle_developer_mode` | 정상 | toolbar_mixin.py:743 |
| 🔄 대시보드 자동 갱신 (checkbutton) | `_on_auto_refresh_toggle` | 정상 | toolbar_mixin.py:1304 |
| 🔍 정합성 검사/복구 | `_on_integrity_check` | 정상 | toolbar_mixin.py:1381 |
| 🧪 운영 DB 스키마 점검 (1회) | `_on_operational_schema_check_once` | 정상 | toolbar_mixin.py:1468 |
| 📊 LOT Allocation·톤백 현황 | `_show_lot_allocation_audit_dialog` | 정상 | |
| 🩺 데이터 정합성 검사 | `_run_integrity_check` | 정상 | main_app.py:1239 |
| 🗑️ 테스트 DB 초기화 (dev 모드) | `_show_test_db_reset_popup` | 정상 | |

### 2-3. 우측 퀵 버튼 (right_actions)

- `🔄 새로고침` → `_refresh_all_data` 정상
- `🌙 Dark` / `☀ Light` → `_change_theme('darkly' / 'litera')` 정상

### 2-4. 액션 버튼 바 (_build_action_button_bar, L178-241)

| 라벨 | 핸들러 | 상태 | 비고 |
|---|---|---|---|
| 📄 PDF 입고 | `_on_pdf_inbound` | 정상 | |
| 🚀 즉시 출고 | `_on_s1_onestop_outbound` | 정상 | |
| 🔄 반품 | `_show_return_dialog` | 정상 | |
| 📊 재고 조회 | `_bulk_import_inventory` | 정상 | bulk_import_mixin.py:21 |
| 🔍 정합성 | `_run_integrity_check` | 정상 | |
| 💾 백업 | `_on_backup_db` | ❌ CRITICAL | 섹션 5 |
| ⚙️ 설정 | `_show_settings_dialog` | ❌ CRITICAL | 섹션 5 |

### 2-5. 사이드바 탭 버튼 (_build_sidebar_tab_buttons)

9개 탭: inventory/allocation/picked/sold/return_tab/move/dashboard/log/scan
모두 `_switch_tab(key)` → `notebook.select(tab_xxx)` 정상.

하단 고정 버튼:
- 🌙 테마 전환 → `_toggle_theme_from_sidebar` (내부 `_apply_theme` 또는 `apply_theme` 탐색)
  — ⚠️ ThemeMixin에 `_apply_theme` 존재 여부 불확실(섹션 9)
- ⚙ 설정 → `_on_settings` → fallback `_show_settings_dialog` → ❌ 둘 다 미구현 (섹션 5)

---

## 3. 탭별 내부 기능

### 3-1. Inventory Tab (tabs/inventory_tab.py)

- 버튼 `← LOT 리스트로` → `_on_back_to_lot_list` 정상
- 버튼 `🔄 새로고침` → `_refresh_inv_tonbag_view` 정상
- 스크롤바 바인딩 정상
- `_refresh_inventory` (L1038), `_refresh_inventory_async` (L1390) 정상

### 3-2. Allocation Tab (tabs/allocation_tab.py)

| 버튼/메뉴 | 핸들러 | 상태 |
|---|---|---|
| 📋 전체 배정 보기 | `_on_show_all_allocation` | 정상 |
| 📥 Excel 내보내기 | `_on_allocation_export_excel` | 정상 (L236) |
| ← LOT 리스트로 | `_on_back_to_allocation_lot_list` | 정상 |
| 🔄 새로고침 | `_refresh_allocation` | 정상 (L303) |
| ❌ 판매 배정 취소 (→ 판매가능) | `_on_allocation_cancel_to_available` | 정상 |
| ❌ Sale Ref 취소 | `_on_allocation_cancel_by_sale_ref` | 정상 |
| 📊 LOT 현황 | `_on_open_allocation_lot_overview` | 정상 |
| 전체 초기화 | `_on_allocation_reset_all` | 정상 (L1152) |
| 전체 토글 | `_on_allocation_toggle_select_all` | 정상 (L1267) |
| ❌ 선택 취소 | `_on_allocation_detail_cancel_selected` | 정상 (L1285) |
| ❌ 전체 취소 | `_on_allocation_detail_cancel_all` | 정상 (L1317) |
| 팝업: 전체 취소 (주의) | `_cancel_all_allocations` | 정상 (L837) |

### 3-3. Picked Tab (tabs/picked_tab.py)

- `🔄 새로고침` → `_refresh_picked` 정상 (L216)
- `📋 전체 피킹 보기` → `_on_show_all_picked` 정상
- `📥 Excel 내보내기` → `_on_picked_export_excel` 정상 (L150)
- `_on_picked_toggle_select_all` 정상
- `← LOT 리스트로` → `_on_back_to_picked_lot_list` 정상

### 3-4. Sold Tab (tabs/sold_tab.py)

- `🔄 새로고침` → `_refresh_sold` 정상 (L171)
- `📋 전체 판매 보기` → `_on_show_all_sold` 정상
- `📥 Excel 내보내기` → `_on_sold_export_excel` 정상 (L346)
- `← LOT 리스트로` → `_on_back_to_sold_lot_list` 정상

### 3-5. Cargo Overview Tab (tabs/cargo_overview_tab.py)

- 스코프 라디오 → `_on_cargo_scope_change` 정상
- `🔄 새로고침` → `_refresh_cargo_overview` 정상 (L303)
- 우클릭 메뉴(L286): 새로고침만 — 정상

### 3-6. Return Tab (cargo_overview_tab.py:418)

`_setup_return_tab` 진입점 존재. 내부 상세는 확인 필요(섹션 9).

### 3-7. Move Tab (tabs/move_tab.py)

- `_on_move_scan_uid`, `_on_move_execute`, `_on_move_scan_clear` 정상
- `_refresh_move_tab` 정상 (L304)

### 3-8. Dashboard Tab (tabs/dashboard_tab.py + dashboard_data_mixin.py)

- 제품 라디오 → `_refresh_dashboard_products` 정상
- 자동 갱신 checkbutton → `_toggle_auto_refresh` 정상
- `_refresh_dashboard` (L551), `_refresh_dashboard_cards` (L594), `_refresh_dashboard_alerts` (L738) 등 전부 정상

### 3-9. Log Tab (tabs/log_tab.py)

- `Clear` → `_clear_log` 정상 (L185)
- `Export` → `_export_log` 정상 (L193)

### 3-10. Scan Tab (tabs/scan_tab.py)

- `🔍 조회` → `_on_scan_lookup` 정상 (L356)
- `🗑 지우기` → `_on_scan_clear` 정상 (L257)

### 3-11. Tonbag Tab (tabs/tonbag_tab.py)

| 버튼/메뉴 | 핸들러 | 상태 |
|---|---|---|
| 배치 출고 | `_on_tonbag_batch_outbound` | 정상 |
| 위치 업로드 | `_on_tonbag_location_upload` | 정상 (L406) |
| UID 복사 | `_on_tonbag_copy_uid` | 정상 |
| 출고 취소 | `_on_tonbag_cancel_outbound` | 정상 |
| 라벨 출력 | `_on_tonbag_print_label` | 정상 |
| 필터 새로고침 | `_on_tonbag_filter_refresh` | 정상 |
| 우클릭: 📍 위치 변경 | `_on_tonbag_edit_location` | 정상 |

### 3-12. Outbound Scheduled Tab (tabs/outbound_scheduled_tab.py)

- `_refresh_outbound_scheduled` 정상 (L298)
- `_show_tonbag_included_popup` 정상

---

## 4. 우클릭 / 컨텍스트 메뉴 (context_menu_mixin.py)

### 4-1. Inventory Context Menu (L158-183)
| 라벨 | 핸들러 | 상태 |
|---|---|---|
| 📋 View Details | `_view_lot_details` | 정상 |
| 🎒 View Tonbags | `_view_lot_tonbags` | 정상 |
| 📅 LOT 히스토리 | `_show_lot_history_timeline` | 정상 (L565) |
| ✏️ Edit LOT | `_edit_lot` | 정상 (L218) |
| 🗑️ Delete LOT | `_delete_lot` | 정상 (L312) |
| 📥 Export Selected (DB Full) | `_export_selected_lots` | 정상 (L351) |
| 📥 선택 영역 Excel 저장 (보이는 대로) | `_export_selection_to_excel(tree)` | 정상 |
| 📋 Copy to Clipboard | `_copy_treeview_selection(tree)` | 정상 |

### 4-2. Tonbag Context Menu (L404-424)
| 라벨 | 핸들러 | 상태 |
|---|---|---|
| Select for Outbound | `_select_tonbag_for_outbound` | 정상 |
| Deselect | `_deselect_tonbag` | 정상 |
| Edit Tonbag | `_edit_tonbag` | ⚠️ "coming soon" (stub only) |
| Change Status | `_change_tonbag_status` | 정상 |
| Copy to Clipboard | `_copy_treeview_selection(tree)` | 정상 |

### 4-3. Search Context Menu (L517-534)
| 라벨 | 핸들러 | 상태 |
|---|---|---|
| Add to Report | `_add_to_search_report` | 정상 |
| View LOT Details | `_view_search_lot_details` | 정상 |
| Copy to Clipboard | `_copy_treeview_selection(tree)` | 정상 |

### 4-4. Generic Context Menu (L60-79)

대상 트리: `tree_allocation`, `tree_allocation_detail`, `tree_picked`, `tree_picked_detail`,
`tree_sold`, `tree_sold_detail`

| 라벨 | 핸들러 | 상태 |
|---|---|---|
| 📋 선택 영역 복사 | `_copy_selection_to_clipboard(tree)` | 정상 |
| 📥 선택 영역 Excel 저장 | `_export_selection_to_excel(tree)` | 정상 |
| 📋 붙여넣기 | `_paste_to_tree_placeholder(tree)` | 정상 (사실상 `_on_paste_table` 존재 시 위임) |

### 4-5. Allocation Tab 내부 팝업 (L772)
| 라벨 | 핸들러 | 상태 |
|---|---|---|
| 전체 취소 (주의) | `_cancel_all_allocations` | 정상 |

### 4-6. Tonbag Tab 내부 팝업 (tonbag_tab.py:1272+)
| 라벨 | 핸들러 | 상태 |
|---|---|---|
| 📍 위치 변경 | `_on_tonbag_edit_location` | 정상 |
| 📋 UID 복사 | `_on_tonbag_copy_uid` | 정상 |
| ↩️ 출고 취소 | `_on_tonbag_cancel_outbound` | 정상 |

---

## 5. 발견된 끊어진 링크 (CRITICAL)

### CRIT-1: `_show_product_master`, `_show_product_inventory_report` — Dead Code

위치: `gui_app_modular/main_app.py` L1305-L1380

```python
if __name__ == '__main__':
    main()


    # --------------------------
    # v5.3.1: Manual DB Migration (v5.3.0)
    # --------------------------
    def _on_run_v530_migration(self):
        ...
    def _read_ui_settings(self):
        ...
    def _show_product_inventory_report(self):
        ...
    def _show_product_master(self):
        ...
```

- 4개의 `def`가 `if __name__ == '__main__':` 블록 **내부**에 4-space 들여쓰기로 존재.
- `main_app.py`는 `run.py`/`python -m gui_app_modular` 경유 import 이므로 `__name__ != '__main__'`. 결과: 이 def들은 절대 실행/바인딩되지 않음.
- 클래스 `SQMInventoryAppFull`은 L1211에서 종료됨. 이 4개 def는 어떤 클래스에도 속하지 않음.

영향 메뉴 (모두 하드 호출):
- 🔧 도구 → 📦 제품 마스터 관리 (custom_menubar.py:276)
- 🔧 도구 → 📊 제품별 재고 현황 (custom_menubar.py:277)
- 📁 파일 → 📥 입고 → 📦 제품 마스터 관리 (menu_registry `FILE_MENU_INBOUND_ITEMS` L36)
- 🔧 설정/도구 (toolbar) → 📦 제품 마스터 관리 (MENU_SETTINGS_ITEMS, menu_registry L144)
- 📥 입고 (toolbar) → 📦 제품명 테이블 관리 (toolbar_mixin.py:465, `_safe_call` 경로)
- 🔧 설정/도구 (toolbar) → 📊 제품별 재고 현황 (MENU_SETTINGS_ITEMS L145)

**런타임 증상**: 일부 메뉴는 `callable(cb)` 체크로 항목이 아예 생성되지 않음(custom_menubar._create_tools_menu은 `hasattr`/`callable` 없이 바로 `self.app._show_product_master` 참조 → 해당 라인 `AttributeError` 발생 시 예외). `_safe_call`을 쓰는 toolbar 경로는 "기능 준비 중" 경고창.

권장 조치: `def _show_product_master` 4개 함수 블록을 `if __name__ == '__main__':` 밖으로 빼서 `SQMInventoryAppFull` 클래스 본문 안으로 이동(또는 별도 mixin 생성).

### CRIT-2: Action Bar `_on_backup_db`, `_show_settings_dialog` 미구현

위치: toolbar_mixin.py L204-205
```python
("💾 백업",       "_on_backup_db",             '#64748b', '#475569'),
("⚙️ 설정",       "_show_settings_dialog",     '#64748b', '#475569'),
```

- `_on_backup_db`: 전 코드베이스에 정의 없음 (유사: `_on_backup_click` — 이것이 실제 백업 핸들러).
- `_show_settings_dialog`: 전 코드베이스에 정의 없음.

사이드바 하단 ⚙ 설정 버튼도 `_on_settings` → fallback `_show_settings_dialog`로 동일하게 실패.

**런타임 증상**: 클릭 시 `_safe_call`의 "기능 준비 중" 경고창.

권장 조치:
- "💾 백업" 버튼 라벨 핸들러를 `_on_backup_click`으로 변경하거나 `_on_backup_db` 별칭 메서드 추가
- "⚙️ 설정" 버튼은 `_show_api_settings` 또는 신규 `_show_settings_dialog` 구현 필요

### CRIT-3: (해당 없음 — 그 외는 경고 수준)

---

## 6. 고아 메뉴 (메뉴엔 있지만 핸들러 없음)

CRIT-1, CRIT-2 외에:

- `_generate_customer_report` (MENU_REPORT_ITEMS L126, optional) — optional=True라 자동 생략됨. **경고**
- `_manage_report_templates` (MENU_REPORT_ITEMS L127, optional) — 위와 동일
- `_show_report_history` (MENU_REPORT_ITEMS L129, optional) — 위와 동일
- `_show_system_info` (MENU_HELP_ITEMS L163, optional) — 위와 동일

위 4개는 `optional=True` 덕분에 메뉴 자체가 생성되지 않음. UX상 사라지는 것이지 크래시하지 않음.

---

## 7. 고아 핸들러 (핸들러는 있지만 메뉴 없음)

샘플 검색 결과:
- `_on_pdf_inbound_quick_folder` (inbound_processor.py:50) — 메뉴/툴바 어디서도 호출 안 됨. 단축키 바인딩 가능성은 섹션 9.
- `_generate_inventory_pdf` (pdf_handlers.py:284) — 하지만 `_generate_inventory_pdf_report`가 유사 기능으로 메뉴 연결됨. 구버전 핸들러.
- `_bulk_import_inventory_simple`이 `import_handlers.py:181`과 `inbound_handlers.py:172`에 **중복 정의**. MRO 순서에 따라 하나는 shadow됨.
- `_refresh_dashboard_*`류 일부는 `dashboard_data_mixin.py`에도 있고 `dashboard_tab.py`에도 있음 (동일 mixin에 duplicate). MRO 혼란 위험.

---

## 8. DEPRECATED / 숨겨야 할 메뉴

- **Features v2.7 메뉴**: `_create_features_menu()` 본문 `pass` (custom_menubar.py L364-368). v8.1.5 결정. 이미 비노출. OK.
- **menu_mixin.py `_setup_native_menu`**: `MENUBAR_STYLE = 'custom'`이 기본이라 native 경로는 fallback 전용. 다만 native 경로에도 같은 `_show_product_master`를 직접 참조(L243)하고 있어, fallback 모드에선 동일 CRIT-1 문제 발생.
- **context_menu_mixin.py `_edit_tonbag`**: "coming soon" 스텁. 실제 다이얼로그 없음 — ⚠️ UX상 "준비 중 메시지"로 대체 또는 메뉴 숨김 권장.

---

## 9. 불확실 / 추가 조사 필요 항목

1. **`_update_recent_files_menu`** — custom_menubar.py:808에서 `self.app._update_recent_files_menu()` 호출. 정의 위치 미확인 (window_mixin.py 또는 기타 mixin 추정). 존재 여부 확인 필요.
2. **`_apply_theme` vs `apply_theme`** — `_build_sidebar_tab_buttons` 내 `_toggle_theme_from_sidebar`가 둘 다 fallback 탐색. ThemeMixin에는 `_show_theme_selector`(L294) 존재. `_apply_theme`/`apply_theme` 정의 위치는 별도 확인 필요.
3. **`_on_settings`** — 사이드바 하단 ⚙ 버튼의 1차 핸들러. 전체 검색에서 정의 없음 → `_show_settings_dialog` fallback → CRIT-2.
4. **`_paste_to_tree_placeholder` → `_on_paste_table`** — 글로벌 paste 핸들러 존재 여부(섹션 4-4).
5. **Return Tab 내부 버튼** — `_setup_return_tab`(cargo_overview_tab.py:418) 내부 command 바인딩 디테일은 추가 확인 필요.
6. **Toolbar `_build_help_menu`에서 `_show_status_guide`/`_show_backup_guide` 해결 여부** — custom_menubar는 self 폴백 탐색이지만 toolbar는 `getattr(self, ...)`만 수행. ToolbarMixin에 위 두 메서드 없음 → optional=True로 지정되어 있어 자동 생략. 폴백/기능 미제공 (섹션 1-6 경고).
7. **`_show_document_convert_dialog` 의존성** — 다이얼로그 내부의 외부 모듈 import 성공 여부(OCR 라이브러리) 런타임 의존.
8. **중복 정의 `_bulk_import_inventory_simple`** (import_handlers vs inbound_handlers) — MRO 순서에 따라 실제 실행되는 구현이 무엇인지 확인 필요.

---

## 10. 권장 조치 우선순위

### HIGH
1. **CRIT-1 수정**: `main_app.py`의 `_show_product_master`, `_show_product_inventory_report`, `_on_run_v530_migration`, `_read_ui_settings` 4개를 `if __name__ == '__main__':` 블록 밖으로 이동하여 `SQMInventoryAppFull` 클래스 본문으로 편입. 가장 많은 메뉴 경로에 영향.
2. **CRIT-2 수정**: Action Bar의 `_on_backup_db` → `_on_backup_click`으로 라벨-핸들러 정정, `_show_settings_dialog` → `_show_api_settings` 또는 신규 통합 설정 다이얼로그 구현.
3. 사이드바 하단 ⚙ 설정 버튼: CRIT-2 해결과 병행.

### MEDIUM
4. `_edit_tonbag` stub 제거 또는 실제 구현.
5. `_bulk_import_inventory_simple` 중복 정의 통합 (handlers/inbound_handlers.py 삭제 검토).
6. `optional=True`이지만 실제 미구현인 `_generate_customer_report`, `_manage_report_templates`, `_show_report_history`, `_show_system_info` 메뉴는 registry에서 아예 삭제하거나 stub 구현 추가.
7. toolbar `_build_help_menu`에 `_show_status_guide`/`_show_backup_guide` 폴백 탐색 추가 (custom_menubar처럼 `getattr(self.app, ...) or getattr(self, ...)` 패턴).

### LOW
8. `_on_pdf_inbound_quick_folder` 등 고아 핸들러는 사용하지 않으면 삭제 또는 단축키 연결 명시화.
9. native 메뉴 fallback 경로(`menu_mixin._setup_native_menu`)도 CRIT-1 영향권. 단, 기본값이 'custom'이라 우선순위 낮음.
10. Dashboard 관련 `_refresh_dashboard_*` 중복 정의(dashboard_tab/dashboard_data_mixin) 정리.

---
End of Report
