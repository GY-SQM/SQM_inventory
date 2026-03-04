# SQM v5.9.8 Release Notes

**Release Date:** 2026-02-18  
**Phase:** 출고·반품 패치 (3건)

---

## 변경 요약

### 1. 경로 ③ Excel 출고 — sale_ref / sold_to / qty_mt 전달 (P1)

- **파일:** `gui_app_modular/handlers/import_handlers.py`
- **문제:** Excel 출고 시 `process_outbound()`에 `sale_ref`, `sold_to`, `qty_mt` 키가 누락되어 출고 이력 추적이 불완전함.
- **수정:**
  - `sale_ref` 컬럼 자동 인식 추가 (`sale_ref`, `saleref`, `sales_ref`, `reference`, `ref` 등)
  - 호출 시 `sold_to`, `sale_ref`, `qty_mt`(weight_kg/1000) 전달
- **효과:** Excel 출고 시에도 DB·출고 이력에 판매 참조·고객·수량(MT)이 정상 기록됨.

### 2. 반품 Excel 업로드 — 5종 상태 허용 및 return_qty_kg 확장 (P3)

- **파일:** `gui_app_modular/mixins/advanced_dialogs_mixin.py`
- **문제:** 반품 미리보기에서 **PICKED**만 반품 가능으로 인정하여, SOLD/RESERVED 등 상태 톤백이 불가로 표시됨.
- **수정:**
  - 반품 가능 상태를 `PICKED`, `CONFIRMED`, `SHIPPED`, `SOLD`, `RESERVED` 5종으로 확장
  - Excel 행에 **RETURN QTY (KG)**만 있어도 해당 LOT의 출고된 톤백을 LIFO로 조회해 톤백 단위로 확장 후 `process_return()` 호출
- **효과:** 반품 양식(재고 리스트 + RETURN QTY / RETURN REASON) 업로드 시 일괄 반품이 정상 동작함.

### 3. AllocationParser 고객명 — CATL / Panasonic 등 타이틀 추출 (P2)

- **파일:** `parsers/allocation_parser.py`
- **문제:** 1행 타이틀에서 고객명을 추출할 때 PT LBM, POSCO, Samsung, LG, SK 5개만 하드코딩되어 있어, "Allocation - CATL Korea - ...", "Allocation - Panasonic Energy - ..." 등에서 `header.customer`가 빈값으로 남음.
- **수정:** if-elif 체인을 **패턴 리스트** 방식으로 변경하고, CATL → "CATL Korea", PANASONIC → "Panasonic Energy", BYD, Northvolt 추가.
- **참고:** 행 단위 `SOLD TO` 컬럼은 기존에도 정상 파싱되어 출고 처리에는 영향 없었고, 타이틀 요약/미리보기에서만 고객명이 비어 보이던 문제가 해결됨.

---

## 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 5.9.8, VERSION_HISTORY 추가 |
| `VERSION.txt` | v5.9.8 |
| `updates/latest.json` | version 5.9.8 |
| `gui_app_modular/handlers/import_handlers.py` | sale_ref 컬럼 인식, process_outbound 6키 전달 |
| `gui_app_modular/mixins/advanced_dialogs_mixin.py` | 반품 5종 상태 + return_qty_kg 확장 |
| `parsers/allocation_parser.py` | 고객명 패턴 리스트 (CATL/Panasonic/BYD/Northvolt) |
| `docs/RELEASE_NOTES_v598.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 18일**
