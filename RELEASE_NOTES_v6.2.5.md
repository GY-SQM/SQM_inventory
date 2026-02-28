# RELEASE NOTES — v6.2.5

## Release Date
- 2026-02-27

## Summary
- 빠른 출고(붙여넣기) 안정성/정확성/성능을 강화했습니다.
- 바코드 스캔 출고 확정 흐름에 `sale_ref` 스코프와 실행 직전 재검증을 추가했습니다.
- 운영 적용 편의를 위해 패치 적용/검증 배치 스크립트를 제공했습니다.

## Key Changes
- `paste_table_dialog`
  - 붙여넣기 데이터 행 자동 확장(`MAX_DATA_ROWS=200`)
  - 첫 행 헤더 자동 감지/스킵
  - `on_confirm` 오류 시 다이얼로그 유지
  - 스크롤 영역 갱신 보강
- `outbound_handlers` (빠른 출고 붙여넣기 경로)
  - `qty_mt` 파싱/정규화 및 `QTY <= 0` 필터
  - 동일 LOT 자동 합산
  - LOT 존재/가용 톤백 벌크 사전 검증
  - LOT별 동적 단가 기반 `sublot_count` 계산
- `outbound_mixin.quick_outbound`
  - `AVAILABLE -> PICKED` 직접 전환(이중 UPDATE 제거)
  - `quick_ref` UUID 접미로 충돌 방지
  - `allocation_plan` 직접 `EXECUTED` 적재
  - `sqlite3` 예외 처리 범위 확장
- `barcode_scan_engine` / 바코드 출고 핸들러
  - 스캔 파일 1회 로드 후 재사용
  - UID 클린/정규화, 인코딩 폴백 강화
  - `sale_ref` 단일 스코프 처리
  - 실행 직전 재검증(TOCTOU 방지)

## Added Operational Files
- `BARCODE_SCAN_QA_CHECKLIST_v623.md`
- `paste_table_dialog.patch`
- `outbound_handlers.patch`
- `outbound_mixin.patch`
- `allocation_dialog.patch`
- `apply_patches.bat`
- `check_patches.bat`
- `run.bat`

## Validation
- 수정 파일 대상 Python 구문 컴파일 검사 통과
- 핵심 패치 파일 생성 및 배치 스크립트 실행 준비 완료
