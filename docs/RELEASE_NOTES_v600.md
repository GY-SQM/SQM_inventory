# SQM v6.0.0 Release Notes

**Release Date:** 2026-02-21  
**Phase:** 입고·반품·로케이션 UX 통합 및 메뉴 정리

---

## 변경 요약

### 1. 입고 — 스프레드시트형 붙여넣기

- **템플릿 열기** 선택 시 파일 저장 대화상자 없이 **화면 내 스프레드시트** 표시
- 입고 형식과 동일한 컬럼(No., LOT NO, SAP NO, … NET(Kg), MXBG 등)에 **Ctrl+V** 붙여넣기 후 **[DB 반영]**으로 즉시 반영
- **파일:** `gui_app_modular/handlers/import_handlers.py`, `gui_app_modular/utils/paste_table_dialog.py`(신규)

### 2. 로케이션 매핑 — 스프레드시트형 붙여넣기

- **데이터 붙여넣기** 선택 시 텍스트 박스 대신 **lot_no, tonbag_no, uid, location** 4열 스프레드시트 표시
- 업로드 양식과 동일하게 붙여넣기 후 **[확인]**으로 미리보기 → DB 반영
- **파일:** `gui_app_modular/dialogs/tonbag_location_upload.py`

### 3. 반품 — 소량/다량 분리 및 필수 4열 검증

- **반품 (재입고)** 메뉴를 **소량 반품 (1~2건)** / **다량 반품 (Excel)** 로 분리
- 소량: 단건 입력 다이얼로그, **최소 데이터**(LOT 번호, Tonbag No, 반품 수량) 및 **무게 정합성**(반품 수량 ≤ 톤백 무게) 검증 후 경고
- 다량: 반품 미리보기 테이블에서 **필수 4열** 구분 표시: **Lot No *, BL NO *, 톤백중량(kg) *, 반품수량(갯수) ***
- **반품수량** 표기: 기존 `반품수량(kg)` → **`반품수량(갯수)`** 로 변경
- 업로드 시 네 열(Lot No, BL NO, 톤백중량, 반품수량) 중 하나라도 비어 있으면 **에러 다이얼로그** 표시 및 해당 행 반영 제외
- **파일:** `gui_app_modular/mixins/advanced_dialogs_mixin.py`, `gui_app_modular/mixins/toolbar_mixin.py`

### 4. 출고 결과 — 상세 요약 후 DB 반영

- **출고 결과** 클릭 시 Excel 선택 후 **상세 요약 다이얼로그** 표시 (LOT NO, 톤백 NO, 고객, 출고일, SALE REF, 상태)
- 총 N건 / 적용가능 / 재고없음 / 이미출고 요약 표시, 사용자 **[DB 반영]** 확인 후 반영
- **파일:** `gui_app_modular/handlers/status_import_handlers.py`

### 5. 메뉴 이름 정리

- **PDF 입고 (원스톱)** → **PDF 스캔 입고**
- **Excel 입고** → **엑셀 파일 수동 입고**
- **가상 Allocation Table 생성** 메뉴 제거
- **파일:** `gui_app_modular/mixins/toolbar_mixin.py`, `menu_mixin.py`, `custom_menubar.py`

### 6. 톤백 리스트 — LOCATION 컬럼 보강

- LOCATION 컬럼 너비 110px로 조정, 폴백 경로(get_tonbags + 재고 병합)에서도 `location` 값 설정 보장
- **파일:** `gui_app_modular/tabs/tonbag_tab.py`

---

## 변경된/추가된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 6.0.0, VERSION_HISTORY 추가 |
| `gui_app_modular/utils/paste_table_dialog.py` | **신규** — 스프레드시트형 붙여넣기 공통 다이얼로그 |
| `gui_app_modular/handlers/import_handlers.py` | 입고 스프레드시트 다이얼로그, _import_inbound_from_dataframe |
| `gui_app_modular/dialogs/tonbag_location_upload.py` | 로케이션 4열(lot_no, tonbag_no, uid, location) 스프레드시트 |
| `gui_app_modular/mixins/advanced_dialogs_mixin.py` | 반품 소량 검증·다량 필수4열·반품수량(갯수)·에러 표시 |
| `gui_app_modular/mixins/toolbar_mixin.py` | 반품 소량/다량 메뉴, 입고/출고 메뉴명, 가상 Allocation 제거 |
| `gui_app_modular/handlers/status_import_handlers.py` | 출고 결과 상세 요약 다이얼로그 |
| `gui_app_modular/mixins/menu_mixin.py` | 입고 메뉴명 변경 |
| `gui_app_modular/mixins/custom_menubar.py` | 입고 메뉴명 변경 |
| `gui_app_modular/tabs/tonbag_tab.py` | LOCATION 컬럼 너비·폴백 setdefault |
| `docs/RELEASE_NOTES_v600.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 21일**
