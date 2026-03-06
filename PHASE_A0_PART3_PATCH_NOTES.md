# Phase A (A1) + Phase 0-A Part 3 (A3) Combined Patch

이 패치는 기존 `SQM_PhaseA_PATCH_ONLY_v6.3.5A.zip`(A1: 원스톱/BL 강화) 위에
**Validation Gate(Part 3)** 를 합친 통합본입니다.

## 포함 파일
- gui_app_modular/dialogs/onestop_inbound.py
  - QC 컬럼(qc_status) 추가
  - 파싱 완료 직후 Gate Validation 실행(OK/SUSPECT/ERROR)
  - ERROR일 때 업로드 버튼 비활성화
  - 요약줄에 QC 요약 표시
- parsers/document_parser_modular/bl_mixin.py
  - (A1) BL 파싱 후처리 로직 유지

## 적용 순서(권장)
- 이 zip 하나만 덮어쓰기 적용 (A1/A3 따로 적용하지 않아도 됨)

