# SQM Database Schema v1 (v7.0.0 기준)

## 핵심 테이블

### inventory
LOT 단위 재고 현황. 1 LOT = 톤백 N개(500kg) + 샘플 1개(1kg).

### inventory_tonbag
톤백 단위 상세. `tonbag_uid = lot_no-tonbag_no` (UNIQUE 제약).

### outbound_log
출고 이력. **불변 원칙** — 반품 후에도 절대 수정하지 않음.

### return_log (v7.0.0 변경)
반품 이력. 출고 이력과 `outbound_id`로 연결.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| processed_as | TEXT DEFAULT 'REINBOUND' | 정책 식별자 |
| new_location | TEXT | PDA 재스캔 위치 |
| operator_id | TEXT DEFAULT 'SYSTEM' | 작업자 추적 |

> v7.0.0 추가: `ALTER TABLE return_log ADD COLUMN` — 앱 시작 시 자동 마이그레이션

### audit_log
모든 상태 변경 감사 이력.

---

## RETURN_AS_REINBOUND 정책 (v7.0.0)

```
1. 반품 톤백은 신규 row를 생성하지 않는다 (tonbag_uid UNIQUE 준수)
2. 기존 inventory_tonbag row를 UPDATE: status=AVAILABLE, location=새위치
3. current_weight는 inventory 테이블에서 즉시 복구
4. 모든 반품은 return_log에 기록, outbound_id로 원출고 연결
5. outbound_log row는 절대 수정하지 않는다 (불변 이력)
```
