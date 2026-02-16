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
| gui_app_modular/dialogs/lot_detail_dialog.py | 폰트·정렬·톤백 테이블 통일 |
| gui_app_modular/tabs/inventory_tab.py | 하단 요약바 폰트·간격, Avail 주석 |

---

*작성일: 2026-02-16 | SQM v5.6.9*
