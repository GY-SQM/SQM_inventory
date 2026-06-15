# SQM Inventory v8.7.9 — 디버깅 백로그 C/D 무결성 강화

**릴리즈 날짜**: 2026-06-15
**브랜치**: `claude/debugging-session-optimization-t3ayma`
**이전 버전**: v8.7.8
**테스트 결과**: 321 passed, 1 deselected

---

## 🎯 주요 변경 사항

이번 릴리즈에서는 영역 C의 잔여 항목과 영역 D(무결성/반품/조정)의 핵심 항목들에 대한 안정화 및 All-or-Nothing 트랜잭션 정책을 강화했습니다.

### [영역 C] 출고 및 스캔 안정화 (C9-C10)
- **C9 (트랜잭션 최적화)**: `barcode_scan_engine.py` 내 중복 `commit()` 호출을 제거하여 트랜잭션 컨텍스트가 커밋 권한을 온전히 소유하도록 정리했습니다.
- **C10 (선적 정합성)**: `shipment_mixin.py`에 선적(SAP) 기준 선적 중량 vs 재고 중량을 대조하는 `get_shipment_integrity_summary` 기능을 추가했습니다.

### [영역 D] 데이터 무결성 및 상태 관리 (D1-D7)
- **D1 (반품 프로세스)**: 반품 처리 시 `auto_finalize_to_available` 옵션을 추가하여, 반품 등록 후 별도의 수동 조작 없이 즉시 가용 재고로 복귀시킬 수 있는 흐름을 구현했습니다.
- **D2/D4 (상태복원 무게 보호)**: 상태 복원(SOLD→PICKED, AVAILABLE→PENDING 등) 후 해당 LOT의 무게를 톤백 상태 기준으로 자동 재계산하도록 수정하여 `initial = current + picked` 공식이 항상 유지되도록 했습니다.
- **D3 (정합성 API 고도화)**: `/api/integrity/check`가 단순 SQL 계산 대신 엔진의 정밀 검증 로직을 사용하도록 하여 `picked > initial` 같은 복합 엣지 케이스까지 감지합니다.
- **D5 (반품 재계산 원자성)**: 반품 재입고 과정 중 무게 재계산 엔진이 실패할 경우 전체 처리를 롤백하도록 수정하여 불완전한 상태 전이를 차단했습니다.
- **D6 (안전 입고)**: `process_inbound_safe`에서 복수 LOT 입고 시 하나라도 실패하면 전체 롤백하는 All-or-Nothing 패턴을 구현하고 Preflight 검증 결과와의 일관성을 강화했습니다.
- **D7 (재고조정 검증)**: 재고조정 실행 시 DB 업데이트 결과(`rowcount`)를 엄격히 확인하여 실제 변경이 일어나지 않은 경우를 실패로 정확히 집계합니다.

---

## 🧪 검증 및 테스트

### 신규 회귀 테스트 추가
- `tests/test_debug_goals_c9_no_manual_commit_in_transaction.py`
- `tests/test_debug_goals_c10_shipment_integrity.py`
- `tests/test_debug_goals_d1_return_auto_finalize.py`
- `tests/test_debug_goals_d2_status_revert_recalc.py`
- `tests/test_debug_goals_d3_integrity_api_full_check.py`
- `tests/test_debug_goals_d4_revert_pending_recalc.py`
- `tests/test_debug_goals_d5_return_rollback_on_recalc_fail.py`
- `tests/test_debug_goals_d6_inbound_safe_atomic.py`
- `tests/test_debug_goals_d7_adjust_rowcount_check.py`

### 테스트 결과 요약
- **전체 테스트**: 321 passed, 1 deselected (정상)
- **All-or-Nothing 검증**: 복수 LOT 처리 중 강제 실패 시 전체 롤백 확인 완료

---

## 📦 기술적 변경 사항
- `preflight_mixin.py`: `process_inbound_safe` 로직이 단일 LOT 호출 방식에서 PackingListData 전체를 원자적으로 처리하는 루프 방식으로 개선되었습니다.
- `return_mixin.py`: `process_return`이 중첩 트랜잭션을 방지하며 `finalize_return_to_available`을 안전하게 연계 호출합니다.
