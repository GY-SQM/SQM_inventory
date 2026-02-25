# SQM 4단계 상태 전이 흐름

**작성일:** 2026년 2월 21일  
**목적:** AVAILABLE → RESERVED → PICKED → SOLD 흐름 시각화. 유지보수·인수인계 시 전체 구조 파악용.

---

## 1. 4단계 개요

```
① AVAILABLE     →    ② RESERVED     →    ③ PICKED     →    ④ SOLD
입고 완료              고객 배정 예약        피킹 완료           판매 확정
출고 대기              완료                 컨테이너 적재       출고 완료
```

| 단계 | 상태 | 의미 | 주요 테이블/경로 |
|------|------|------|------------------|
| ① | AVAILABLE | 입고 완료, 출고 가능 | inventory, inventory_tonbag |
| ② | RESERVED | Allocation 예약 완료, 출고 대기 | allocation_plan |
| ③ | PICKED | 피킹 완료, 컨테이너 적재 | picking_table, picking_list_* |
| ④ | SOLD | 판매 확정, 출고 완료 | sold_table |

**보조 상태**
- **DEPLETED**: 재고 0kg 소진 시 (inventory 테이블)
- **RETURNED**: 반품 시 PICKED → AVAILABLE 복원

---

## 2. 진입 경로 (업로드/UI)

| 단계 전환 | 진입 경로 |
|-----------|-----------|
| → RESERVED | Allocation Excel 업로드 (파일/붙여넣기) |
| RESERVED → PICKED | Picking List PDF 업로드 |
| PICKED → SOLD | Sales Order Excel 업로드 |
| (직접) AVAILABLE → PICKED | 빠른 출고(붙여넣기), 배정표 출고, Excel 출고 등 |

---

## 3. 상태 전이 보호 (v6.0.7+)

- **PICKED로의 전환**은 **AVAILABLE** 또는 **RESERVED**에서만 허용.
- **SOLD / DEPLETED / RETURNED / SHIPPED** 상태는 PICKED로 덮어쓰지 않음 (역전 차단).
- 적용 위치:
  - Excel 출고 결과 반영: `status_import_handlers.py` (SOLD 등 → PICKED 차단)
  - 톤백 상태 직접 변경: `tonbag_mixin.update_tonbag_status()` (화이트리스트 검증)

---

## 4. 취소/복원

| 시나리오 | 함수 | 비고 |
|----------|------|------|
| RESERVED → AVAILABLE | cancel_reservation() | allocation_plan CANCELLED + tonbag AVAILABLE |
| PICKED → AVAILABLE (단건) | cancel_outbound_tonbag() | 톤백 복원 + current_weight 복구 + stock_movement |
| PICKED → AVAILABLE (일괄) | cancel_outbound_bulk() | All-or-Nothing 롤백 |

---

**(주) 지와이로지스 2026년 2월 21일**
