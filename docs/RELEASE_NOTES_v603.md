# SQM v6.0.3 Release Notes

**Release Date:** 2026-02-22  
**Phase:** Picking List 파서·엔진 통합 · 툴바 출고 메뉴 정리

---

## 변경 요약

### 1. features/parsers — Picking List 파서·엔진

- **features/parsers/picking_list_parser.py (신규)**
  - SQM(SOQUIMICH LLC.) Picking List PDF 전용 파서.
  - 1순위: **pdfplumber** 텍스트 추출 → 2순위: **Gemini OCR** 폴백(스캔 PDF 등).
  - 추출: Outbound ID, Sales order, Customer reference(Picking No), Invoice account(고객), Creation/Plan Loading Date, 라인별 Batch number(lot_no), Quantity, Unit(MT/KG), Storage location.
  - 반환: `outbound_id`, `sales_order_no`, `picking_no`, `customer`, `items`(list of dict: lot_no, qty_kg, is_sample 등), `total_normal_mt`, `total_sample_kg`, `parse_ok`, `warnings`.
  - 진입점: `parse_picking_list_pdf(pdf_path)` → dict.

- **features/parsers/picking_engine.py (신규)**
  - 파싱 결과를 DB에 반영: **RESERVED → PICKED** 전환, **picking_table** INSERT.
  - 비즈니스 규칙: LOT 단위, qty_kg 기준 부분 처리, 샘플 톤백 별도 처리, All-or-Nothing 트랜잭션.
  - 진입점: `apply_picking_list_to_db(engine, doc, pdf_path)` — 실패 시 `RuntimeError`.

- **의존:** `pdfplumber` 설치 권장 (`pip install pdfplumber`). 미설치 시 Gemini 폴백만 사용.

### 2. 툴바 출고 메뉴 — menu_registry 기반

- **문제:** 툴바(toolbar_mixin)의 "📤 출고 ▼" 메뉴가 하드코딩되어 Picking List 등이 누락됨.
- **해결:** `_build_outbound_menu()`를 **menu_registry 기반**으로 변경.
  - `FILE_MENU_OUTBOUND_ITEMS` 순회 → Allocation 입력, **Picking List 업로드 (PDF)**, 바코드 스캔 등 동일하게 표시.
  - ImportError 시 Allocation + Picking List만 fallback.
  - "📤 빠른 출고 (붙여넣기)"는 구분선 아래 고정.
- **파일:** `gui_app_modular/mixins/toolbar_mixin.py`

### 3. Picking List 미리보기 — dict 형식 지원

- **기존:** `parsers.picking_list_parser.PickingDoc`(속성 기반)만 지원.
- **변경:** **dict 형식**(features.parsers 파싱 결과) 지원.
  - 요약: `customer`, `sales_order_no`, `picking_no`, `plan_loading_date`, `creation_date`.
  - 경고: `warnings`.
  - 테이블: LOT NO, Qty(Kg), 단위, 샘플, Storage location.
- **파일:** `gui_app_modular/dialogs/picking_list_preview_dialog.py`

### 4. Picking List 업로드 흐름

- **outbound_handlers:** `features.parsers.picking_list_parser.parse_picking_list_pdf` **우선** 사용 → 실패 시 `parsers` fallback.
- **DB 반영:** `features.parsers.picking_engine.apply_picking_list_to_db` 존재 시 미리보기에서 "DB 반영 (RESERVED → PICKED)" 버튼 노출 및 실행.
- **파일:** `gui_app_modular/handlers/outbound_handlers.py`

---

## 변경된/추가된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `version.py` | 6.0.3, VERSION_HISTORY 추가 |
| `features/parsers/__init__.py` | **신규** — 파서·엔진 노출 |
| `features/parsers/picking_list_parser.py` | **신규** — Picking List PDF 파서 (pdfplumber + Gemini 폴백) |
| `features/parsers/picking_engine.py` | **신규** — RESERVED→PICKED, picking_table INSERT, apply_picking_list_to_db |
| `gui_app_modular/mixins/toolbar_mixin.py` | 출고 메뉴 menu_registry 기반, Picking List 항목 포함 |
| `gui_app_modular/dialogs/picking_list_preview_dialog.py` | dict 형식 doc 지원 (요약/경고/테이블 분기) |
| `gui_app_modular/handlers/outbound_handlers.py` | features.parsers 파서 우선, DB 반영 apply_picking_list_to_db 연동 |
| `docs/RELEASE_NOTES_v603.md` | **신규** |

---

**(주) 지와이로지스 2026년 2월 22일**
