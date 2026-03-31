SQM v8.6.3 패치 — 2026-03-27 최종판
적용: 압축 풀고 SQM 설치 폴더에 그대로 덮어씌우기
==================================================

 1. gui_app_modular/main_app.py
    → 초기화면 대시보드 + after(0) 즉시 선택 + 사이드바 키 수정

 2. engine_modules/inventory_modular/export_mixin.py
    → Outbound Report 일별 시트 / DN 완료 체크

 3. parsers/allocation_parser.py
    → 본품 먼저 → 샘플 나중 정렬

 4. gui_app_modular/dialogs/lot_status_dialog.py
    → 샘플 표시: 본품 미완료 = '본품 출고 후'

 5. gui_app_modular/utils/tree_enhancements.py
    → make_date_range_bar() + 캘린더 팝업 개선

 6. gui_app_modular/tabs/sold_tab.py
    → 날짜 필터 통일

 7. gui_app_modular/tabs/cargo_overview_tab.py
    → 날짜 필터 통일

 8. gui_app_modular/dialogs/inbound_history_dialog.py
    → 날짜 필터 통일

 9. gui_app_modular/mixins/advanced_dialogs_mixin.py
    → 보고서 날짜 캘린더 + DN 미완료 경고

10. gui_app_modular/dialogs/allocation_dialog.py
    → Allocation 기간 필터 통일

11. gui_app_modular/dialogs/return_statistics_dialog.py
    → 반품 통계 날짜 통일

12. gui_app_modular/mixins/toolbar_mixin.py
    → 툴바 날짜 통일

13. gui_app_modular/dialogs/onestop_outbound.py
    → 원스톱 출고 날짜 통일

14. gui_app_modular/handlers/pdf_handlers.py
    → PDF 보고서 날짜 통일

15. Claude_Code_SQM_MASTER.md
    → v8.6.3 반영 완료본

==================================================
주요 변경 요약
  1. 초기화면 → 대시보드 (after(0) 즉시 선택 보장)
  2. Allocation 파서 본품→샘플 순서 정렬
  3. LOT 현황 샘플 표시 개선
  4. Outbound Report 날짜별 시트 분리
  5. Sales Order DN 전체 출고 완료 시에만 발행
  6. 날짜 입력 UI 13개 메뉴 통일 (make_date_range_bar)
  7. 캘린더 팝업 개선 (연월Combobox/오늘하이라이트/토일색상/호버)
  8. Claude_Code_SQM_MASTER.md v8.6.3 반영