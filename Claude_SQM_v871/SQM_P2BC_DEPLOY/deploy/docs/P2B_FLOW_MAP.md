# P2B_FLOW_MAP.md — Outbound 흐름 맵 (실제 분석)
# 분석 대상: Claude_SQM_v871/engine_modules/inventory_modular/outbound_mixin.py (4043줄)
# 작성일: 2026-04-08

================================================================
## 1. 실제 상태전이 다이어그램 (v8.7.1 기준)
================================================================

```
[AVAILABLE]
    ↓  reserve_from_allocation()
[RESERVED]
    ↓  execute_reserved()
[PICKED]
    ↓  confirm_outbound()
[OUTBOUND]  ← v7.2.0 신규 (구: SOLD — 레거시 호환만)

취소 경로:
[RESERVED]  → cancel_reservation()     → [AVAILABLE]
[PICKED]    → cancel_outbound_tonbag() → [AVAILABLE]
[RESERVED/PICKED] → 만료/고아 정리     → [CANCELLED]
```

### ★ 핵심 발견 — MASTER 파일과 다른 점
| MASTER 파일 예상 | 실제 v8.7.1 |
|-----------------|-------------|
| ALLOCATION | RESERVED (allocation_plan 테이블) |
| SCANNED | PICKED (gate1_verify_picking) |
| SOLD | OUTBOUND (SOLD는 레거시 deprecated) |

================================================================
## 2. 메서드 역할 분류
================================================================

### [QUERY] — DB 조회 전담 (OutboundQuery로 분리 대상)
- _get_outbound_status(outbound_no) — 출고번호별 상태 조회
- _co_check_double_sold(tonbag_id) — 중복 출고 확인
- _co_verify_weight_conservation(lot_no) — 중량 보존 검증
- _co_load_picked_tonbags(lot_no) — PICKED 톤백 목록 조회
- _co_guard_against_double_outbound(tonbags) — 이중 출고 방지 확인
- _co_validate_customer_sale_ref(tonbags) — 고객/sale_ref 검증
- _er_load_reserved_plans(lot_no, target_date) — RESERVED 계획 조회
- _er_warn_stale_plans(plans) — 만료 예약 경고
- _g1_aggregate_picking_qty(picking_rows) — 피킹 수량 집계
- _ra_g5_batch_validate(allocation_rows) — 사전 검증
- _ra_pre_dup_warnings(allocation_rows) — 중복 경고
- get_outbound_event_log(limit) — 이벤트 로그 조회
- _preflight_alloc_cols() — allocation 컬럼 존재 확인

### [WRITE] — DB 변경 전담 (OutboundRepository로 분리 대상)
- _ra_insert_plan_row(payload) — allocation_plan INSERT
- _er_apply_pick_transition(plan, tb_weight, now) — RESERVED→PICKED 상태 변경
- _er_record_pick_movement(plan, tb_weight, now) — movement 기록
- _er_insert_picking_row(plan, tb_weight, ...) — picking 행 INSERT
- _co_build_sold_row_payload(tb, now) — OUTBOUND 행 데이터 구성
- _co_insert_sold_row(tb, now) — sold(outbound) 행 INSERT
- _co_insert_outbound_movement(tb, now) — movement INSERT
- _update_lot_after_pick(lot_no, weight_kg) — LOT 잔량 업데이트
- _recalc_lot_status(lot_no) — LOT 전체 상태 재계산
- _g1_cancel_excess_allocation(lot_no, ...) — 초과 allocation 취소

### [STATE] — 상태전이 로직 (OutboundStateRules + Service로 분리)
- reserve_from_allocation() — AVAILABLE→RESERVED 예약
- execute_reserved() — RESERVED→PICKED 실행
- confirm_outbound() — PICKED→OUTBOUND 확정
- cancel_outbound_tonbag() — PICKED/SOLD→AVAILABLE 취소
- cancel_outbound_bulk() — 일괄 취소
- cancel_reservation() — RESERVED→AVAILABLE 예약 취소
- revert_picked_to_reserved() — PICKED→RESERVED 롤백
- revert_sold_to_picked() — OUTBOUND→PICKED 롤백
- quick_outbound() — AVAILABLE→OUTBOUND 빠른 출고

### [UI] — 유지 대상 (onestop_outbound.py / outbound_handlers.py)
- outbound_handlers.py 전체 (GUI 이벤트 핸들러)
- onestop_outbound.py 전체 (tkinter 다이얼로그)

### [BIZ] — 비즈니스 로직 (Service로 이관)
- process_outbound() — 출고 처리 메인 진입점
- gate1_verify_picking() — 피킹 검증
- gate1_apply_picking_result() — 피킹 결과 적용
- execute_from_picking() — 피킹에서 실행
- apply_approved_allocation_reservations() — 승인된 예약 적용
- fix_lot_status_integrity() — LOT 상태 정합성 수정
- run_allocation_cleanup() — 할당 정리
- cleanup_orphan_lot_allocations() — 고아 할당 정리
- cleanup_expired_staged_allocations() — 만료 staged 정리

================================================================
## 3. DB 컬럼 상태 맵
================================================================

### tonbag (톤백) 테이블
| 컬럼 | 값 목록 |
|------|---------|
| status | AVAILABLE / RESERVED / PICKED / OUTBOUND / SOLD(레거시) / CANCELLED |

### inventory (LOT) 테이블
| 컬럼 | 값 목록 |
|------|---------|
| status | AVAILABLE / PARTIAL / RESERVED / PICKED / OUTBOUND / SOLD / DEPLETED |

### allocation_plan 테이블
| 컬럼 | 값 목록 |
|------|---------|
| status | STAGED / RESERVED / CANCELLED |
| workflow_status | PENDING_APPROVAL / REJECTED |

================================================================
## 4. 규모 통계
================================================================

- outbound_mixin.py 총 줄수: 4,043줄
- 총 메서드 수: 약 70개
- DB SELECT 패턴: 229건
- DB INSERT/UPDATE/DELETE: 79건
- 분리 대상 메서드: 약 45개
- UI 유지 메서드: 약 25개 (outbound_handlers.py, onestop_outbound.py)
