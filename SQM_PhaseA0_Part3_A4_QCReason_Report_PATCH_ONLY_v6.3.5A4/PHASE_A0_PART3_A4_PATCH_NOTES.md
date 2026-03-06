# Phase 0-A Part 3 (A4) Patch Notes

- Preview QC에 `QC REASON` 컬럼 추가
- Gate Validation에서 행별 사유(qc_reason) 기록
  - ERROR: 프리플라이트 검증 메시지
  - SUSPECT: LOT 불일치 / 크로스체크 CRITICAL
- QC 결과를 자동으로 CSV로 저장
  - <실행폴더>/reports/YYYY-MM-DD/inbound_qc_YYYYMMDD_HHMMSS.csv
  - UTF-8-SIG(엑셀 한글 깨짐 방지)

변경 파일:
- gui_app_modular/dialogs/onestop_inbound.py
