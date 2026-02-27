# SQM v5.9.9.2 Release Notes

**Release Date:** 2026-02-19  
**Phase:** D/O 미첨부·입고 UX·DB 스키마 개선

---

## 변경 요약

### 1. 재고 없음 화면 — 선택 시 즉시 숨김

- **파일:** `gui_app_modular/tabs/inventory_tab.py`, `gui_app_modular/mixins/keybindings_mixin.py`
- **내용:** "재고 데이터가 없습니다" 안내에서 **파일 선택 입고** 또는 **수동 입고** 클릭 시(또는 Ctrl+O, Ctrl+N) 안내 화면이 즉시 사라짐

### 2. D/O 미첨부 시 날짜 입력 팝업 개선

- **파일:** `gui_app_modular/dialogs/onestop_inbound.py`
- **변경 사항:**
  - **선적일(Ship Date) 항목 제거** — B/L에서 추출되어 톤백 리스트에 이미 있으므로 별도 입력 불필요
  - **입항일·con_return·Free time 상호 계산** — 입항일/반납일(con_return)/Free time 중 하나만 입력해도 나머지 자동 계산
  - **con_return·free_time 적용 보강** — 계산된 값이 미리보기 각 행에 반드시 반영되도록 수정

### 3. inventory_tonbag DB 마이그레이션 (v5.9.1)

- **파일:** `engine_modules/db_schema_mixin.py`, `engine_modules/db_migration_mixin.py`
- **추가 컬럼(6개):** `inventory_id`, `sap_no`, `bl_no`, `inbound_date`, `tonbag_no`, `remarks`
- **백필:** `inventory` 테이블과 `lot_no` 기준으로 기존 데이터 자동 채움 (`inbound_date` = stock_date → arrival_date → ship_date)
- **효과:** `table inventory_tonbag has no column named inventory_id` 등 입고 업로드 실패 방지

### 4. DB 스키마 오류 메시지 개선

- **파일:** `gui_app_modular/utils/upload_error_template.py`, `gui_app_modular/dialogs/inbound_upload_mixin.py`
- **내용:** `no column named` / `no such column` 발생 시 **"DB 스키마 불일치(업데이트 필요)"** 안내 표시 (엑셀 필수 컬럼 누락과 구분)

---

## 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 5.9.9.2, VERSION_HISTORY 추가 |
| `gui_app_modular/tabs/inventory_tab.py` | 재고 없음 화면 버튼 클릭 시 `_hide_empty_state_hint()` 호출 |
| `gui_app_modular/mixins/keybindings_mixin.py` | Ctrl+O/Ctrl+N 시 `_hide_empty_state_hint()` 호출 |
| `gui_app_modular/dialogs/onestop_inbound.py` | 선적일 제거, con_return/Free time 상호 계산·적용 보강 |
| `engine_modules/db_schema_mixin.py` | inventory_tonbag 컬럼 6개 + remarks 추가 |
| `engine_modules/db_migration_mixin.py` | v5.9.1 마이그레이션(6컬럼 + 백필 + tonbag_no 백필) |
| `gui_app_modular/utils/upload_error_template.py` | db_schema, db_error 템플릿 추가 |
| `gui_app_modular/dialogs/inbound_upload_mixin.py` | DB 컬럼 오류 시 db_schema 타입 안내 |
| `docs/RELEASE_NOTES_v5992.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 19일**
