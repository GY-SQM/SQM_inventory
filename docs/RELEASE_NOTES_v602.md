# SQM v6.0.2 Release Notes

**Release Date:** 2026-02-21  
**Phase:** 메뉴 단일 소스 · v6.0.0 DB 마이그레이션 · Picking List 파싱 UI

---

## 변경 요약

### 1. 메뉴 단일 소스 (menu_registry)

- **문제:** 커스텀 메뉴(`custom_menubar.py`)와 네이티브 메뉴(`menu_mixin.py`)가 각각 정의되어, Picking List 등이 한쪽에만 있어 누락 발생.
- **해결:** 입고/출고 메뉴 항목을 **한 곳**에서만 정의하도록 `gui_app_modular/menu_registry.py` 추가.
  - `FILE_MENU_INBOUND_ITEMS`: PDF 스캔 입고, 엑셀 수동 입고, D/O 후속 연결, 반품
  - `FILE_MENU_OUTBOUND_ITEMS`: Allocation 입력, **Picking List 업로드 (PDF)**, 바코드 스캔, Sales Order 업로드(optional)
- **효과:** `MENUBAR_STYLE`이 custom이든 native든 동일한 항목 표시. 새 항목은 `menu_registry.py`에만 추가하면 됨.
- **파일:** `gui_app_modular/menu_registry.py`(신규), `gui_app_modular/mixins/custom_menubar.py`, `gui_app_modular/mixins/menu_mixin.py`

### 2. v6.0.0 DB 마이그레이션 (picking_table · sold_table)

- **allocation_plan 확장:** `picking_no`, `bl_no`, `outbound_id` 컬럼 추가.
- **picking_table 신규:** 22개 컬럼(lot_no, tonbag_uid, picking_no, sales_order_no, outbound_id, customer, qty_mt, qty_kg, status 등) + 인덱스 6개.
- **sold_table 신규:** 23개 컬럼(picking_id, sales_order_no, picking_no, sold_qty_mt, ct_plt 등) + 인덱스 7개.
- **inventory_tonbag 확장:** `picking_id`, `sold_id`, `picking_no` 컬럼 추가.
- **파일:** `engine_modules/db_migration_mixin.py` — `_migrate_v600_picking_sold_tables()` 설계안 반영.

### 3. Picking List PDF 파싱 UI

- **기존:** 메뉴에서 "Picking List 업로드" 선택 시 "준비 중" 메시지만 표시.
- **변경:**  
  - 파일 선택(파일 열기 대화상자) → `parsers.parse_picking_list_pdf(path)` 호출 → **파싱 결과 미리보기 다이얼로그** 표시.
- **미리보기 내용:** 요약(파일 경로, Customer reference, Sales order, Plan loading date 등), 경고/오류 목록, 품목·Batch 테이블.  
  선택 시 `features.parsers.picking_engine`이 있으면 "DB 반영 (RESERVED → PICKED)" 버튼 노출.
- **파일:** `gui_app_modular/dialogs/picking_list_preview_dialog.py`(신규), `gui_app_modular/handlers/outbound_handlers.py` — `_on_picking_list_upload()` 구현.

### 4. v6.0.0 마이그레이션 테스트

- **tests/test_migrate_v600.py** 추가.
- Windows/Linux 공통으로 `tempfile.gettempdir()` 사용한 임시 DB로 `_migrate_v600_picking_sold_tables()` 실행 후, 테이블/컬럼/인덱스·멱등성 검증.
- **실행:** `python tests/test_migrate_v600.py`

---

## 변경된/추가된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 6.0.2, VERSION_HISTORY 추가 |
| `gui_app_modular/menu_registry.py` | **신규** — 입고/출고 메뉴 항목 단일 정의 |
| `gui_app_modular/mixins/custom_menubar.py` | menu_registry 기반 입고/출고 메뉴 구성 |
| `gui_app_modular/mixins/menu_mixin.py` | 네이티브 메뉴 출고·업로드 메뉴를 menu_registry 기반으로 구성 |
| `engine_modules/db_migration_mixin.py` | v6.0.0 마이그레이션: allocation_plan 확장, picking_table/sold_table 생성, inventory_tonbag 확장 |
| `gui_app_modular/dialogs/picking_list_preview_dialog.py` | **신규** — Picking List 파싱 결과 미리보기 다이얼로그 |
| `gui_app_modular/handlers/outbound_handlers.py` | _on_picking_list_upload: 파일 선택 → 파싱 → 미리보기 다이얼로그 표시 |
| `tests/test_migrate_v600.py` | **신규** — v6.0.0 마이그레이션 자동 검증 |
| `docs/RELEASE_NOTES_v602.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 21일**
