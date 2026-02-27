# SQM v5.7.0 ~ v5.7.4 — 입고 Gate-1, 톤백 정합성, 크로스 검증, Excel 입고, 컬럼 토글 #all 수정 (GitHub 메모)

## 개요
입고 전 PL+FA+BL 필수 3종 검증(Gate-1), 톤백 무게 정합성·주석 강화, 크로스 검증 시 샘플 포함 합산, Excel 입고용 `add_inventory_from_dict` 추가, 표시 컬럼 체크 해제 시 **Invalid column index #all** 에러 수정을 반영한 버전입니다.

---

## 버전별 요약

| 버전 | 요약 |
|------|------|
| 5.7.0 | 입고 Gate-1 강화 — PL+FA+BL 필수 3종 없으면 DB 업로드 차단, D/O 후속 연결 정책 명확화 |
| 5.7.1 | 톤백 무게 정합성 — per_bag 주석 강화, NET/Balance/Inbound 톤백 개별 무게만 사용 |
| 5.7.2 | 크로스 검증 샘플 포함 합산 — 정합성 경고 0건 (5001=500×10+1) |
| 5.7.3 | Excel 입고 — add_inventory_from_dict 추가(CRUDMixin), GUI tonbags 호환, gemini_chat_gui 정리 |
| 5.7.4 | 표시 컬럼 체크 해제 시 Invalid column index #all 수정 — 재고 리스트·톤백 리스트 공통 |

---

## 주요 수정 사항

### A. 입고 Gate-1 강화 (v5.7.0)
- **PL+FA+BL 필수 3종**: Packing List, FA, BL이 모두 없으면 DB 업로드 차단
- **D/O 후속 연결 정책**: D/O만 있는 경우 후속 문서 연결 정책 명확화

### B. 톤백 무게 정합성 (v5.7.1)
- **per_bag 주석 강화**: `(총무게 - 1kg 샘플) / 톤백수` 등 주석·상수 명확화
- **NET/Balance/Inbound**: 톤백 개별 무게만 사용하도록 로직 확인·정리 (tonbag_tab)

### C. 크로스 검증·정합성 (v5.7.2)
- **샘플 포함 합산**: 크로스 검증 시 샘플 1kg 포함한 합산으로 정합성 경고 0건 목표 (예: 5001 = 500×10 + 1)
- integrity_mixin 등에서 샘플 포함 합산 로직 반영

### D. Excel 입고 및 GUI 정리 (v5.7.3)
- **add_inventory_from_dict**: CRUDMixin에 Excel 입고용 메서드 추가, GUI tonbags 호환
- **gemini_chat_gui**: 코드 정리

### E. 기타
- 하단 요약 1줄 정리
- LOT 팝업 다크 전경색(fg) 개선
- 톤백 STATUS 인덱스
- 샘플 S 표기

### F. 표시 컬럼 토글 #all 에러 수정 (v5.7.4)
- **에러**: 표시 컬럼 체크 해제 시 `Invalid column index #all` 발생 — 재고 리스트·톤백 리스트 동일.
- **원인**: Treeview `displaycolumns`가 빈값/`#all`/`('#all',)` 등으로 반환될 때, 체크 해제 후 다시 설정할 때 `#all`이 그대로 들어가 Tk가 컬럼 인덱스로 해석함.
- **수정**: `column_toggle.py` `_toggle_column()`에서 (1) `#all`·`('#all',)`을 실제 컬럼 목록으로 정규화, (2) 목록 내 `#all` 필터링, (3) 빈 tuple 방지(최소 1컬럼 유지).

---

## 변경된 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| version.py | __version__ = 5.7.4, VERSION_HISTORY 5.7.0~5.7.4 |
| gui_app_modular/utils/column_toggle.py | v5.7.4: displaycolumns #all 정규화·필터링, Invalid column index #all 수정 (재고/톤백 공통) |
| engine_modules/inventory_modular/crud_mixin.py | add_inventory_from_dict (Excel 입고) |
| engine_modules/inventory_modular/inbound_mixin.py | Gate-1(PL+FA+BL), per_bag 주석·상수 |
| engine_modules/inventory_modular/integrity_mixin.py | 크로스 검증 샘플 포함 합산 |
| engine_modules/inventory_modular/query_mixin.py | 톤백 STATUS 인덱스 등 |
| engine_modules/validators.py | 검증 관련 |
| features/ai/gemini_chat_gui.py | 정리 |
| gui_app_modular/dialogs/lot_detail_dialog.py | 다크 fg |
| gui_app_modular/dialogs/onestop_inbound.py | Gate-1 연동 |
| gui_app_modular/tabs/inventory_tab.py | 하단 요약 1줄 등 |
| gui_app_modular/tabs/tonbag_tab.py | NET/Balance/Inbound 톤백 개별 무게만 사용 |

---

*작성일: 2026-02-16 | SQM v5.7.4*
