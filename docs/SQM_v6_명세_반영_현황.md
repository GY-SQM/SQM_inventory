# SQM v6.0 설계 명세 반영 현황 (2월 20일 명세 기준)

**확인일:** 2026-02-21

---

## 요약: **아직 반영되지 않음**

아래 ①~④ 항목은 설계서에만 있고, 현재 코드베이스에는 **구현되어 있지 않습니다.**

---

## ① Picking List PDF 업로드 처리

| 설계 내용 | 현재 상태 |
|-----------|-----------|
| `process_picking_list(pdf_path)` | **미구현** (함수 없음) |
| Picking List PDF → OCR → LOT번호 + 수량 추출 | **미구현** |
| 매칭 톤백만 RESERVED → PICKED, 나머지 RESERVED 유지 | **미구현** |
| `parsers/picking_list_parser.py` 또는 동일 역할 모듈 | **없음** (설계 검토안 `PICKING_LIST_PARSER_DESIGN_REVIEW.md`만 존재) |

**참고:** DB에 `picking_list_order`, `picking_list_detail` 테이블(v289)은 있으나, “PDF 업로드 → OCR → RESERVED→PICKED” 플로우와는 별개 스키마/용도입니다.

---

## ② 바코드 스캔 파일 업로드 (CSV/Excel)

| 설계 내용 | 현재 상태 |
|-----------|-----------|
| `process_barcode_scan(file_path)` | **미구현** (함수 없음) |
| CSV/Excel → 스캔 코드 목록 읽기 `_read_scan_file()` | **미구현** |
| PICKED 톤백 중 스캔된 것만 SOLD, 나머지 PICKED 유지 | **미구현** |
| 잔여 PICKED 경고 팝업 | **미구현** |

**참고:** `gui_app_modular/utils/tonbag_location_uploader.py`는 **로케이션 업데이트용** Excel(UID 또는 lot_no+tonbag_no+location) 처리만 하며, “스캔 파일 → PICKED→SOLD” 처리와는 다릅니다.

---

## ③ 대시보드 4단계 카드 (AVAILABLE / RESERVED / PICKED / SOLD)

| 설계 내용 | 현재 상태 |
|-----------|-----------|
| 카드 4개: AVAILABLE, RESERVED, PICKED, SOLD (개수/MT) | **미반영** |
| TOTAL: XX개 / XX.X MT 하단 표시 | **미반영** |

**현재 대시보드 카드:**  
`dashboard_tab.py` 기준  
- 총 재고, 총 LOT, 금일 입고, 금일 출고, 가용 톤백  
→ 상태별 4단계(AVAILABLE / RESERVED / PICKED / SOLD) 카드는 없음.

---

## ④ 메뉴 추가 (업로드 메뉴)

| 설계 내용 | 현재 상태 |
|-----------|-----------|
| `📋 Picking List 업로드 (PDF)` | **없음** |
| `📊 바코드 스캔 업로드 (CSV/Excel)` | **없음** |

**현재 업로드 메뉴** (`menu_mixin.py`):  
- PDF 스캔 입고, 엑셀 수동 입고, D/O 후속 연결, 출고(Excel), 반품(재입고)  
→ Picking List PDF / 바코드 스캔 업로드 메뉴는 없음.

---

## 정리

- **Picking List PDF 처리**, **바코드 스캔 CSV/Excel 처리**, **대시보드 4단계 카드**, **해당 메뉴 2개**는 모두 **아직 반영되지 않은 상태**입니다.
- 반영하려면  
  - 엔진: `process_picking_list`, `process_barcode_scan`, `_read_scan_file` 및 DB/트랜잭션 연동  
  - 파서: Picking List PDF 파서(OCR 연동)  
  - GUI: 업로드 메뉴 2개, 바코드 스캔 결과/잔여 PICKED 경고 팝업  
  - 대시보드: 상태별 4카드 + TOTAL 표시  
  를 새로 구현해야 합니다.

*문서 버전: 1.0*
