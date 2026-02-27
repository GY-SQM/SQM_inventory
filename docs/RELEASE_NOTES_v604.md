# SQM v6.0.4 Release Notes

**Release Date:** 2026-02-21  
**Phase:** process_outbound 1단계 패치 · 반품 형식 통일 · Excel/데이터 입력 원칙 전역 적용

---

## 변경 요약

### 1. process_outbound 1단계 패치 (v5.9.92)

- **DB 마이그레이션**
  - `allocation_plan` 테이블에 **source** 컬럼 추가 (TEXT DEFAULT 'AUTO') — 출고 경로 구분용.
  - `_migrate_v5992_allocation_source()` 추가, `_run_all_migrations()`에서 호출.
- **엔진 (outbound_mixin)**
  - `process_outbound(allocation_data, source='AUTO', stop_at_picked=False)` 시그니처 확장.
  - **source:** AUTO/QUICK/EXCEL 등 — allocation_plan INSERT 시 기록.
  - **stop_at_picked:** True면 톤백 PICKED + allocation_plan 기록만, 재고·outbound·stock_movement 미반영.
  - 단일 출고 시 allocation_plan에 (lot_no, customer, sale_ref, qty_mt, status='PICKED', source) INSERT.
- **빠른 출고 (outbound_handlers)**
  - **최대 8건(LOT) 제한** — 초과 시 경고 후 진행 불가.
  - 실행 시 `process_outbound(..., source='QUICK', stop_at_picked=True)` 호출.
- **배정표(Excel) 출고**
  - `_execute_outbound`: **AllocationRow → dict 리스트** 변환 후 `process_outbound(items, source='EXCEL', stop_at_picked=False)` 단일 호출.
- **Excel 출고 경로에 source='EXCEL' 통일**
  - `simple_excel_outbound.py`, `import_handlers.py`, `features_v2_mixin.py`에서 `process_outbound(..., source='EXCEL', stop_at_picked=False)` 호출.

### 2. 반품 입고 형식 = 입고 형식과 동일

- **반품 템플릿:** 기존 입고 템플릿(재고 리스트 형식)과 동일한 베이스 + **PICKING NO**, **반품사유** 필수 컬럼 추가.
- **RETURN_TEMPLATE_COLUMNS:** `import_handlers`에 정의 — `INVENTORY_TEMPLATE_COLUMNS` + `picking_no`, `return_reason`.
- 반품 입고 시 **데이터 붙여넣기** 또는 **파일 업로드** 선택 후, 입고와 같은 시트 구조(2행=DB필드명, NET(Kg) 등)로 처리.

### 3. 반품 파서 — 입고 형식 Excel/붙여넣기 지원

- **return_inbound_parser.py**
  - 입고 형식 Excel: 헤더에 `lot_no`, `net_weight`(NET(Kg)), `picking_no`, `return_reason`(반품사유) 인식.
  - 중량: **NET(Kg)** 있으면 Kg 기준 → `weight_mt = kg/1000`, 톤백 수 = `int(kg/500)`; 없으면 기존 **WEIGHT(MT)** 사용.
  - **parse_return_inbound_from_rows(rows):** 붙여넣기 행 리스트를 반품 엔진용 `items`로 변환.
- **return_inbound_engine:** 기존 동일 — picking_table 매칭 → return_history, stock_movement, AVAILABLE 복구, RETURNED 처리.

### 4. 반품 입고 UI — 템플릿(붙여넣기) vs 파일 업로드

- **반품 입고 (Excel)** 메뉴 클릭 시 **선택 다이얼로그** 표시.
  - **데이터 붙여넣기** → `_show_return_inbound_spreadsheet_dialog()`: 내장 반품 컬럼 표에 붙여넣기 후 [DB 반영].
  - **파일 업로드** → Excel 선택 후 입고 형식 또는 기존 WEIGHT(MT) 형식 파싱 후 반품 처리.
- **advanced_dialogs_mixin:** `_on_return_inbound_paste_confirm`, `_apply_return_inbound_after_parse`(skip_confirm 지원).

### 5. Excel/데이터 입력 원칙 — 전역 통일 (영구 유효)

- **AGENTS.md**에 **Excel/데이터 입력 원칙 (Upload Principle)** 추가.
  - 프로그램이 사용하는 엑셀/데이터 형식은 **프로그램 내장**.
  - 사용자 입력: **① 데이터 붙여넣기** 또는 **② 파일 업로드**로 통일.
  - 입고·출고·반품·위치·Allocation 등 전체 프로그램에 동일 적용, **프로그램 수명 동안 유효**.
- **ui_constants.py**에 공통 문구 상수:
  - `UPLOAD_CHOICE_HEADER`, `UPLOAD_CHOICE_PASTE`, `UPLOAD_CHOICE_UPLOAD`
  - `UPLOAD_CHOICE_BTN_PASTE` ("📋 데이터 붙여넣기"), `UPLOAD_CHOICE_BTN_UPLOAD` ("📤 파일 업로드").
- **적용 위치:**
  - **import_handlers:** `_show_template_or_upload_choice` — 상수 사용으로 문구·버튼 통일.
  - **톤백 위치 업로드:** 동일 헤더/버튼 문구.
  - **Allocation 입력:** 동일 헤더/버튼 문구.
  - **심플 출고:** 선택 다이얼로그 추가 → 데이터 붙여넣기 시 `_show_simple_outbound_paste_dialog()` (LOT NO, Weight(Kg), Customer, Sale Ref).
  - **다량 반품 탭:** "데이터 입력" 버튼 → 선택(붙여넣기 안내 / 파일 업로드) 후 파일 업로드 시 기존 Excel 처리.

---

## 변경된/추가된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 6.0.4, VERSION_HISTORY(process_outbound 1단계 반영) |
| `engine_modules/db_migration_mixin.py` | _migrate_v5992_allocation_source(), allocation_plan.source 컬럼 |
| `engine_modules/inventory_modular/outbound_mixin.py` | process_outbound(source, stop_at_picked), allocation_plan INSERT |
| `gui_app_modular/handlers/outbound_handlers.py` | 빠른 출고 8건 제한, QUICK/EXCEL 호출, _execute_outbound dict 변환, UPLOAD_CHOICE_* |
| `gui_app_modular/handlers/simple_excel_outbound.py` | process_outbound(..., source='EXCEL'), 선택 다이얼로그·_show_simple_outbound_paste_dialog |
| `gui_app_modular/handlers/import_handlers.py` | process_outbound(..., source='EXCEL'), RETURN_TEMPLATE_COLUMNS, _show_return_inbound_spreadsheet_dialog, _show_template_or_upload_choice |
| `gui_app_modular/mixins/features_v2_mixin.py` | process_outbound(..., source='EXCEL') |
| `AGENTS.md` | Excel/데이터 입력 원칙(Upload Principle) 영구 규칙 섹션 추가 |
| `gui_app_modular/utils/ui_constants.py` | UPLOAD_CHOICE_* 상수 5개 추가 |
| `gui_app_modular/mixins/advanced_dialogs_mixin.py` | 반품 입고 선택·붙여넣기·_apply_return_inbound_after_parse, 다량 반품 데이터 입력 선택·문구 통일 |
| `gui_app_modular/dialogs/tonbag_location_upload.py` | UPLOAD_CHOICE_* 상수로 문구·버튼 통일 |
| `features/parsers/return_inbound_parser.py` | 입고 형식 헤더/ NET_WEIGHT_KG 지원, parse_return_inbound_from_rows 추가 |
| `docs/RELEASE_NOTES_v604.md` | process_outbound 1단계 섹션 및 변경 파일 목록 갱신 |

---

**(주) 지와이로지스 2026년 2월 21일**
