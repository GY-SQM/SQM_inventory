# SQM v5.6.9 — 로케이션 양식·다크 가시성·스타일 통일 (GitHub 메모)

## 개요
로케이션 엑셀 양식 확정, 다크 테마 Treeview 가시성 개선, LOT 상세 팝업·하단 요약바 스타일 통일, Avail 컬럼 로직 명시를 반영한 버전입니다.

---

## 주요 수정 사항

### A. 로케이션 엑셀 양식 확정 (tonbag_location_uploader.py)
- **컬럼 정의**
  | 컬럼       | 필수/선택 | 설명           |
  |------------|-----------|----------------|
  | 순번       | -         | 자동 번호      |
  | 입고일     | 선택      |                |
  | BL No      | 선택      | 식별 보조      |
  | lot_no     | 필수      | LOT 매칭 키    |
  | tonbag_no  | 필수      | 톤백 매칭 키   |
  | location   | 필수      | 위치 (예: A-01-01) |
- **로케이션 체계**: 영문-숫자-숫자 (예: A-01-01), 형식 검증 추가

### B. 다크 테마 Treeview 가시성 (ui_constants.py)
- **문제**: 다크 모드에서 데이터 행 글씨와 배경색이 비슷해 안 보임
- **수정**: Treeview 태그(available, picked, stripe 등)에 **전경색 #f0f0f0** 적용
- 테마 변경 시 `configure_tags`에서 foreground 통일

### B-2. 다크 테마 재고/톤백 테이블 글씨·배경 수정 (table_styler.py)
- **문제**: 그리드 적용 후 `set_row_height()`가 스타일을 `RowHeight.xxx`로 바꿔, 테마 갱신이 적용되지 않음. 다크에서 행 배경만 갱신하고 맵 미갱신으로 흰색 행 유지.
- **수정**
  - `set_row_height()`: 이미 `Grid.xxx` 스타일이 있으면 스타일을 바꾸지 않고 해당 스타일에 `rowheight`만 설정해 테마 색 유지.
  - `update_grid_style_for_theme()`: `Grid.` 뿐 아니라 `RowHeight.` 스타일도 동일하게 갱신. 배경·foreground·fieldbackground·`style.map(background=...)`·Heading 전부 갱신해 다크에서 행 배경도 어둡게, 글씨 밝게 표시.
- **연관**: inventory_tab, tonbag_tab에서 `apply_table_style(..., is_dark=...)` 및 테마 변경 시 `update_grid_style_for_theme` 호출; theme_mixin에서 재고/톤백 트리 테마 갱신 호출 추가.

### C. LOT 상세 팝업 스타일 통일 (lot_detail_dialog.py)
- **상단 LOT 정보** (SAP NO, B/L NO 등): 그리드 정렬·간격 통일
- **입고/잔량/출고/출고율**: 폰트 11pt bold 통일
- **톤백 테이블**: 컬럼 너비·정렬 통일, 가시성 개선

### D. 재고/톤백 하단 요약바 스타일 (inventory_tab.py)
- **재고 리스트 하단**: LOT, 톤백, 입고, 잔량, 출고, 가용, 소진 — 폰트 11pt 통일, 간격 10px
- **톤백 리스트 하단**: 기존 11pt 유지, 가시성 일관

### E. Avail 컬럼 로직 명시 (inventory_tab.py)
- **의미**: Avail = 현재 가용 톤백 수(실시간) — 출고 시 감소, 반품 시 증가
- 기존 DB COUNT(AVAILABLE) 로직 유지, 주석으로 명시

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.6.9, VERSION_HISTORY 추가 |
| gui_app_modular/utils/tonbag_location_uploader.py | 로케이션 양식 doc, 영문-숫자-숫자 검증 |
| gui_app_modular/utils/ui_constants.py | configure_tags 다크 전경색 |
| gui_app_modular/utils/table_styler.py | set_row_height Grid 유지, update_grid_style_for_theme 전체 갱신 |
| gui_app_modular/tabs/inventory_tab.py | apply_table_style is_dark, 테마 시 Grid 갱신, 하단 요약바·Avail 주석 |
| gui_app_modular/tabs/tonbag_tab.py | apply_table_style is_dark, 테마 시 Grid 갱신 |
| gui_app_modular/mixins/theme_mixin.py | 재고/톤백 트리 update_grid_style_for_theme 호출 |
| gui_app_modular/dialogs/lot_detail_dialog.py | 폰트·정렬·톤백 테이블 통일 |

---

*작성일: 2026-02-16 | SQM v5.6.9*
