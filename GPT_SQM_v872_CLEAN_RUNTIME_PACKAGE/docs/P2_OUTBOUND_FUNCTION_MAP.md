# P2 Batch B — OutboundMixin 기능 맵
작성일: 2026-04-07

## 대상: engine_modules/inventory_modular/outbound_mixin.py (4043줄)

## 메서드별 역할 분류

### 조회 (Query) — outbound_query.py 이관 대상
| 메서드 | 줄 | 역할 |
|---|---|---|
| _table_exists | 58 | 테이블 존재 확인 |
| get_outbound_event_log | 88 | 출고 이벤트 로그 조회 |
| _get_outbound_status | 114 | 출고번호별 상태 조회 |
| _has_allocation_source_fingerprint_column | 530 | 컬럼 존재 확인 |
| _ra_get_alloc_plan_cols | 1182 | allocation_plan 컬럼 조회 |
| _er_load_reserved_plans | 2297 | RESERVED 계획 조회 |
| _co_load_picked_tonbags | 2641 | PICKED 톤백 조회 |
| _preflight_alloc_cols | 4013 | allocation_plan 컬럼 사전검사 |

### 상태 규칙 (State Rules) — outbound_state_rules.py 이관 대상
| 메서드 | 줄 | 역할 |
|---|---|---|
| _recalc_lot_status | 1073 | LOT 상태 재계산 규칙 |
| _allocation_risk_flags | 1155 | 승인 위험 플래그 |
| _allocation_requires_approval | 1163 | 승인 필요 여부 |
| _normalize_outbound_date | 394 | 출고일 정규화 |
| _get_allocation_random_mode | 473 | 랜덤 모드 조회 |
| _get_allocation_strict_mode | 494 | Strict 모드 조회 |
| _get_allocation_reservation_mode | 512 | 예약 모드 조회 |

### 쓰기 (Repository) — outbound_repository.py 이관 대상
| 메서드 | 줄 | 역할 |
|---|---|---|
| _ensure_outbound_txn_tables | 69 | 테이블 생성 |
| _update_lot_after_pick | 825 | 피킹 후 LOT 업데이트 |
| _ra_insert_plan_row | 1204 | allocation_plan 행 삽입 |
| _ra_build_plan_payload | 1219 | allocation_plan 페이로드 빌드 |
| _co_insert_sold_row | 2787 | sold_table 출고 이력 |
| _co_insert_outbound_movement | 2811 | stock_movement 출고 이력 |
| _er_apply_pick_transition | 2372 | RESERVED→PICKED 전환 |
| _er_record_pick_movement | 2402 | PICKED 이력 기록 |
| _er_insert_picking_row | 2412 | picking_table 이력 |

### 서비스 (오케스트레이션) — 유지 (outbound_mixin.py)
| 메서드 | 줄 | 역할 |
|---|---|---|
| process_outbound | 608 | 출고 처리 메인 |
| _process_single_outbound | 676 | 단일 출고 처리 |
| cancel_outbound_tonbag | 849 | 출고 취소 |
| cancel_outbound_bulk | 978 | 일괄 출고 취소 |
| reserve_from_allocation | 1698 | Allocation 예약 메인 |
| execute_reserved | 2446 | RESERVED→PICKED 실행 |
| confirm_outbound | 2869 | PICKED→OUTBOUND 확정 |
| gate1_verify_picking | 2952 | Gate-1 교차검증 |
| gate1_apply_picking_result | 3275 | Gate-1 결과 적용 |
| cancel_reservation | 3449 | 예약 취소 |
| revert_picked_to_reserved | 3650 | PICKED→RESERVED 복원 |
| revert_sold_to_picked | 3708 | SOLD→AVAILABLE 복원 |
| quick_outbound | 3817 | 빠른 출고 |

### 유틸 (Static/Pure) — outbound_state_rules.py 이관 대상
| 메서드 | 줄 | 역할 |
|---|---|---|
| _build_allocation_seed | 586 | Allocation 시드 생성 |
| _compute_allocation_source_fingerprint | 540 | 소스 핑거프린트 계산 |
| _ra_alloc_val | 1197 | dict/dataclass 값 접근 |
| _ra_parse_allocation_line | 1274 | Allocation 행 파싱 |
| _ra_validate_line_inputs | 1300 | 행 유효성 검증 |

### 정리/클린업
| 메서드 | 줄 | 역할 |
|---|---|---|
| cleanup_orphan_lot_allocations | 130 | 고아 레코드 정리 |
| cleanup_expired_staged_allocations | 208 | 만료 STAGED 정리 |
| fix_lot_status_integrity | 252 | LOT 상태 정합성 복구 |
| run_allocation_cleanup | 326 | 전체 정리 일괄 실행 |
| clear_pending_allocation_on_exit | 343 | 종료 시 대기건 정리 |
