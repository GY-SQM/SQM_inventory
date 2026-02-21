# SQM v6.0.5 Release Notes

**Release Date:** 2026-02-21  
**Phase:** 상태명 한글화 2단계 — PDF·Excel·컨텍스트 메뉴 한글 표시

---

## 변경 요약

### 1. 상태 표시 상수 보강 (ui_constants)

- **STATUS_DISPLAY**에 `'RETURNED': '반품'` 추가.
- **STATUS_DISPLAY_TO_DB** 추가: 한글 표시명 → DB 값 역매핑. 필터·다이얼로그 저장 시 한글 선택값을 DB 값으로 변환할 때 사용.

### 2. PDF 재고 상세 — STATUS 컬럼 한글

- **pdf_report_gen.py**  
  - "LOT별 재고 상세" 테이블의 **STATUS** 컬럼을 DB 값(AVAILABLE 등) 대신 **한글**(판매가능 등)로 출력.
  - `get_status_display(status_raw)`로 변환 후 테이블 행에 반영.

### 3. 톤백 컨텍스트 메뉴 — 한글 기준 동작

- **context_menu_mixin.py**
  - **Select for outbound:** 톤백 트리 상태 컬럼이 한글이므로, `'판매가능'` 또는 `STATUS_DISPLAY_TO_DB.get(표시값) == 'AVAILABLE'` 로 비교하도록 수정.
  - **상태 변경 다이얼로그:**
    - 제목/라벨 한글: "상태 변경", "현재", "저장", "LOT / 톤백".
    - 콤보 옵션 한글만 사용: 판매가능, 판매배정, 판매화물 결정, 출고, 소진, 선적, 반품.
    - 저장 시 `STATUS_DISPLAY_TO_DB`로 한글 → DB 값 변환 후 UPDATE.
    - 톤백 트리 컬럼 순서에 맞게 lot_no/sub_lt 사용, 톤백 번호 표시값(S0, 1, 2 등)을 sub_lt 정수로 파싱해 DB 업데이트에 사용.

### 4. 출고 이력 Excel — 상태 컬럼 한글

- **outbound_scheduled_tab.py**  
  - LOT 출고 이력 Excel 저장 시 **상태** 컬럼을 DB 값이 아닌 **한글**로 저장.
  - `get_status_display(st_raw)`로 변환 후 시트에 기록.

---

## 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 6.0.5, VERSION_HISTORY 추가 |
| `gui_app_modular/utils/ui_constants.py` | STATUS_DISPLAY에 RETURNED, STATUS_DISPLAY_TO_DB 추가 |
| `gui_app_modular/utils/pdf_report_gen.py` | 재고 상세 PDF STATUS 컬럼 한글 표시 |
| `gui_app_modular/mixins/context_menu_mixin.py` | 톤백 선택·상태 변경 한글 표시 및 저장 시 DB 값 변환 |
| `gui_app_modular/tabs/outbound_scheduled_tab.py` | 출고 이력 Excel 상태 컬럼 한글 |
| `docs/RELEASE_NOTES_v605.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 21일**
