============================================================
  Claude_SQM_v857_PATCH (출고 보고서 자동 생성)
  기준: v8.5.6 (P2 적용 후)
  생성: 2026-03-26
  버전: v8.5.7
============================================================

[개요]
  출고 보고서(Detail of Outbound) Excel+PDF 자동 생성.
  sold_table INSERT 보강 + 과거 출고 건 역보정 마이그레이션.

[적용 순서]
  ① 패치 파일 5개 덮어쓰기
  ② 프로그램 실행 (자동 마이그레이션 실행됨)
  ③ python -m pytest → 기존 통과 수 유지 확인
  ④ reportlab 설치 (PDF 생성 시):
     pip install reportlab

[패치 파일 — 5개 (덮어쓰기)]
  version.py                                         v8.5.7
  engine_modules/db_migration_mixin.py               v8.5.7 마이그레이션 추가
  engine_modules/inventory_modular/outbound_mixin.py sold_table INSERT 11개 필드 보강
  engine_modules/inventory_modular/export_mixin.py   출고 보고서 함수 신규
  gui_app_modular/handlers/export_handlers.py        옵션 10번 추가

[주요 변경 상세]

  1. sold_table INSERT 보강 (outbound_mixin.py)
     기존: lot_no, tonbag_id, sub_lt, tonbag_uid, picking_id,
           sold_qty_kg, sold_date, status, created_by (9개)
     추가: sap_no, bl_no, customer, sku, sales_order_no,
           picking_no, delivery_date, ct_plt, sold_qty_mt,
           gross_weight_kg, is_sample (11개)
     → inventory/picking_table/allocation_plan JOIN으로 자동 수집

  2. DB 마이그레이션 (db_migration_mixin.py)
     ① sold_table 컬럼 추가: gross_weight_kg, sold_qty_mt, is_sample
     ② 과거 OUTBOUND 톤백 → sold_table 누락 행 자동 INSERT
     ③ 기존 빈 필드(sap_no, bl_no 등) inventory JOIN 보정

  3. 출고 보고서 (export_mixin.py)
     _export_outbound_report(output_path, sale_ref, outbound_date, lot_no)
     - Excel: 본품+샘플 행 분리, 합계행, 컬러 헤더
     - PDF: landscape A4, 한글 폰트 자동 감지, reportlab
     - 필터: sale_ref, outbound_date, lot_no (선택)

  4. 메뉴 (export_handlers.py)
     옵션 10 = "Outbound Report"
     파일명: Detail_of_Outbound_YYYY_MM_DD.xlsx

[교차검증]
  ① SQL 오염: 0건 ✅
  ② status 방향: OUTBOUND 유지 ✅
  ③ 예외처리: try/except 유지 ✅
  ④ py_compile: 5개 전 파일 통과 ✅
  ⑤ 미채택 항목: 미포함 ✅

[보고서 출력 형식]
  ■ Outbound report
  ■ Date : 2026-03-24
                                           NW    GW    CT
  Destination | Date | LOT NO | SAP NO | BL NO | Sales order No | ...
  JAKARTA     | 03-24| 112508 | 220003 | MAEU  | MSO-260318     | ...
  JAKARTA (S) | 03-24| 112508 | 220003 | MAEU  | MSO-260318     | ... (샘플)
============================================================
