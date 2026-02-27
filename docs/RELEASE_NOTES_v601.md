# SQM v6.0.1 Release Notes

**Release Date:** 2026-02-21  
**Phase:** 총괄 화물 리스트 · 상태별 필터 · 헤더 정렬

---

## 변경 요약

### 1. 총괄 화물 리스트 탭 (맨 왼쪽 추가)

- **탭 순서:** 맨 앞에 **📋 총괄 화물 리스트** 탭 추가  
  순서: **총괄 화물 리스트 → 재고리스트 → 출고예정 → 톤백리스트 → 대시보드 → 로그**
- **상태 필터:** **전체 / 판매가능 / 판매배정 / 판매화물 결정 / 출고** 5종, 괄호 안에 해당 상태 LOT 개수 표시
- **데이터 원칙 (해당 화물만 표시):**
  - **판매가능:** 톤백이 모두 AVAILABLE/SAMPLE인 LOT만 (RESERVED/PICKED/SOLD 없음)
  - **판매배정:** 고객 Allocation 테이블(`allocation_plan`, RESERVED)에 포함된 LOT만
  - **판매화물 결정:** 톤백 중 PICKED가 있는 LOT만
  - **출고:** 톤백 중 SOLD가 있는 LOT만
- **파일:** `gui_app_modular/tabs/cargo_overview_tab.py`(신규), `engine_modules/inventory_modular/query_mixin.py`(`get_cargo_overview_lots`, `get_cargo_overview_counts`), `main_app.py`, `tabs/__init__.py`, `mixins/toolbar_mixin.py`, `mixins/keybindings_mixin.py`(Ctrl+6)

### 2. 모든 리스트 헤더 — 오름차순/내림차순 정렬 (▲▼)

- **재고리스트:** 기존 유지 (헤더 클릭 시 정렬, ▲/▼ 표시)
- **총괄 화물 리스트:** 헤더 클릭 시 해당 컬럼 기준 오름차순/내림차순 전환, 헤더에 ▲/▼ 표시
- **출고예정:** 헤더에 정렬 연결 추가, 클릭 시 오름차순/내림차순 전환 및 ▲/▼ 표시
- **톤백리스트:** 톤백 전용 컬럼 정의 사용한 `_sort_tonbag_treeview`로 정렬 통일, 헤더 ▲/▼ 표시
- 숫자 컬럼은 숫자 크기, 그 외는 문자열(대소문자 무시) 기준 정렬
- **파일:** `gui_app_modular/tabs/cargo_overview_tab.py`, `gui_app_modular/tabs/outbound_scheduled_tab.py`(`_sort_outbound_scheduled_tree`), `gui_app_modular/tabs/tonbag_tab.py`(`_sort_tonbag_treeview`)

### 3. 엔진 — 상태별 LOT 조회

- **get_cargo_overview_lots(status_filter):**  
  `None`/전체 → 전체 inventory, `AVAILABLE` → 판매가능 LOT만, `RESERVED` → allocation_plan(RESERVED)에 있는 LOT만, `PICKED`/`SOLD` → 해당 톤백이 있는 LOT만 반환
- **get_cargo_overview_counts():** 상태별 LOT 개수 반환 (콤보 표시용)
- **파일:** `engine_modules/inventory_modular/query_mixin.py`

---

## 변경된/추가된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 6.0.1, VERSION_HISTORY 추가 |
| `gui_app_modular/tabs/cargo_overview_tab.py` | **신규** — 총괄 화물 리스트 탭(상태 필터, 트리, 하단 합계, 헤더 정렬) |
| `engine_modules/inventory_modular/query_mixin.py` | `get_cargo_overview_counts()`, `get_cargo_overview_lots(status_filter)` 추가 |
| `gui_app_modular/main_app.py` | `tab_cargo_overview` 추가, 탭 순서·인덱스·전환 시 새로고침 반영 |
| `gui_app_modular/tabs/__init__.py` | `CargoOverviewTabMixin` export |
| `gui_app_modular/mixins/toolbar_mixin.py` | 탭 버튼·`_tab_index_map`에 총괄 화물 리스트 반영 |
| `gui_app_modular/mixins/keybindings_mixin.py` | Ctrl+6 → 6번째 탭(로그) 이동 |
| `gui_app_modular/tabs/outbound_scheduled_tab.py` | `_sort_outbound_scheduled_tree()` 추가, 헤더 정렬 연결 |
| `gui_app_modular/tabs/tonbag_tab.py` | `_sort_tonbag_treeview()` 추가, 톤백 컬럼 기준 정렬·▲▼ 표시 |
| `docs/RELEASE_NOTES_v601.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 21일**
