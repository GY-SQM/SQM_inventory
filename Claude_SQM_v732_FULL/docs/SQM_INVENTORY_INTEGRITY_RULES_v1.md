# SQM 재고 무결성 규칙 v1 (v7.0.0 기준)

## 핵심 불변 조건

```
1 LOT = 톤백 N개(500kg 또는 1000kg) + 샘플 1개(1kg)
LOT 총무게 = (톤백수 × 단가) + 1kg  예: 10개 × 500kg + 1kg = 5,001kg
tonbag_uid = lot_no-tonbag_no  (UNIQUE 제약, 절대 중복 불가)
```

## 구조 제약

| 단위 | 최대 |
|------|------|
| Rack 당 톤백 | 20개 |
| 창고 당 톤백 | 3,500개 |
| 시스템 전체 | 7,000개 |

## 상태 전이 규칙

```
AVAILABLE → RESERVED → PICKED → SOLD
반품 시: SOLD → AVAILABLE (RETURN_AS_REINBOUND — UPDATE 방식)
```

## RETURN_AS_REINBOUND 무결성 원칙 (v7.0.0)

1. **INSERT 금지**: 반품 시 신규 tonbag row 생성 금지
2. **UPDATE 전용**: 기존 row의 status, location만 변경
3. **중량 불변**: 반품 후 tonbag 중량은 원본 그대로 유지
4. **이중반품 차단**: return_log 기존 기록 확인 후 처리
5. **outbound_log 불변**: 반품 후 출고 이력 절대 수정 금지
6. **원출고 연결**: return_log.outbound_id = outbound_log.outbound_id

## 샘플 무게 처리

- 샘플 톤백: `is_sample=1`, `weight_kg=1`, `tonbag_no='S00'`
- 판매가능 재고 계산 시 샘플 1kg 반드시 제외
- 중량 계산: `available_weight = current_weight - 1` (샘플 제외)
