# SQM v5.9.3 Release Notes — 출고/반품 로직 강화

**Release Date:** 2026-02-18

---

## 개요

Phase 2 — 출고(Outbound) 및 반품(Return) 로직을 전면 강화하여, Allocation 엑셀 기반의 안정적 출고 워크플로우를 구현했습니다.

---

## A-1: Allocation 파서 안정화

| 항목 | 변경 |
|------|------|
| 과학표기법 방어 | LOT NO, SAP NO가 `2.2E+09` 형태로 읽힐 때 정수 변환 |
| Total/합계 행 필터링 | "Total", "합계", "Subtotal", "소계"로 시작하는 행 자동 스킵 |
| GW 단위 자동 변환 | 10 미만이면 MT로 간주 → ×1000 변환 (0.51MT → 510kg) |

**수정 파일:** `parsers/allocation_parser.py`

---

## A-2: RESERVED 상태 + allocation_plan 테이블

### 새 상태 플로우

```
입고 → AVAILABLE → RESERVED → PICKED → SOLD
                                 └─→ DEPLETED (전량 출고 시)
```

- **STATUS_RESERVED**: Allocation 엑셀로 톤백 지정 완료, 출고일 대기 상태
- **engine_modules/constants.py**, **core/constants.py**에 추가

### allocation_plan 테이블 (신규)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동 증가 |
| lot_no | TEXT | LOT 번호 |
| tonbag_id | INTEGER | 톤백 FK |
| sub_lt | INTEGER | 톤백 번호 |
| customer | TEXT | 고객사 |
| sale_ref | TEXT | SALE REF |
| qty_mt | REAL | 수량(MT) |
| outbound_date | TEXT | 출고 예정일 |
| status | TEXT | RESERVED/EXECUTED/CANCELLED |
| source_file | TEXT | 원본 파일명 |
| executed_at | TEXT | 실행 일시 |
| cancelled_at | TEXT | 취소 일시 |

**인덱스:** `lot_no`, `status`, `outbound_date`

---

## A-3: 출고 실행 로직

| 메서드 | 기능 |
|--------|------|
| `reserve_from_allocation()` | Allocation 데이터 → RESERVED 예약 (All-or-Nothing) |
| `execute_reserved()` | RESERVED → PICKED 전환 (날짜/LOT 필터 지원) |
| `confirm_outbound()` | PICKED → SOLD 확정 |
| `cancel_reservation()` | RESERVED → AVAILABLE 복원 + allocation_plan CANCELLED |

**수정 파일:** `engine_modules/inventory_modular/outbound_mixin.py`

---

## A-4: 반품 로직 보완

- **SOLD 반품 지원:** SOLD → AVAILABLE 복원 + current_weight 복구
- **RESERVED 반품 지원:** RESERVED → AVAILABLE + allocation_plan CANCELLED
- RESERVED 반품 시 current_weight는 변경하지 않음 (아직 출고 실행 전이므로)

**수정 파일:** `engine_modules/inventory_modular/return_mixin.py`

---

## 수정된 파일 목록 (7개)

1. `parsers/allocation_parser.py` — 파서 안정화
2. `engine_modules/constants.py` — STATUS_RESERVED 추가
3. `core/constants.py` — STATUS_RESERVED re-export
4. `engine_modules/db_migration_mixin.py` — allocation_plan 마이그레이션
5. `engine_modules/inventory_modular/outbound_mixin.py` — 예약/실행/확정/취소 메서드
6. `engine_modules/inventory_modular/return_mixin.py` — SOLD/RESERVED 반품
7. `version.py`, `VERSION.txt`, `updates/latest.json` — 버전 업데이트
