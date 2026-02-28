# RELEASE NOTES — v6.2.6

## Release Date
- 2026-02-28

## Summary
- Sales Order 업로드 처리의 성능과 정합성을 강화했습니다.
- 대량 업로드 시 DB 왕복을 줄이고, 부분 처리로 인한 운영 리스크를 방지했습니다.
- 재업로드 운영을 위한 `retry_pending_only`와 감사 로그 기록을 추가했습니다.

## Key Changes
- `features/parsers/sales_order_engine.py`
  - `(lot_no, picking_no, is_sample)` 그룹 선조회 + FIFO 배정 적용
  - `executemany()` 기반 배치 반영으로 대량 업로드 성능 개선
  - 샘플/일반 매칭 강제(`is_sample` 필터) 및 구버전 DB 폴백 처리
  - 부족 수량 시 부분 SOLD 금지, 해당 라인은 `PENDING`으로 보관
  - `retry_pending_only` 모드 추가(PENDING 대상만 재처리)
  - 중복 SO 기본 차단 + 예외 허용 옵션(`allow_duplicate`)
  - 처리시간(`elapsed_ms`) 측정 및 결과/로그 반영
  - `sales_order_import_log` 테이블로 실행 이력 기록
- `engine_modules/db_migration_mixin.py`
  - Sales Order 조회/처리 최적화 인덱스 추가
    - `idx_picking_lot_pick_status_sample_id`
    - `idx_picking_lot_pick_status_id`
    - `idx_sold_order_status`
  - `sales_order_import_log` 테이블 마이그레이션 추가
    - 실행 ID, 파일 해시, 모드, SOLD/PENDING 건수, 경고 JSON, 처리시간 기록

## Compatibility
- 기본 동작은 기존과 동일하게 유지됩니다(`mode="normal"`).
- 신규 모드(`retry_pending_only`)와 중복 허용 옵션은 선택적으로 사용 가능합니다.

## Validation
- 변경 파일 Python 구문 컴파일 검사 통과
- 린트 오류 없음
