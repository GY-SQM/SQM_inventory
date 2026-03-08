# SQM INVENTORY INTEGRITY RULES v1

## 하드스톱 조건
- LOT mismatch
- Tonbag duplicate
- Invalid location
- Rack capacity 초과
- Warehouse / System capacity 초과
- 이미 SHIPPED / RETURNED / HOLD / DAMAGED 상태의 Tonbag 재출고 시도

## 핵심 공식
- (LOT 총중량 - sample 1kg) / mxbg_pallet = 톤백 단위 무게
- inventory.current_weight ≈ 정책상 재고로 포함되는 tonbag weight 합계
- Lot / Tonbag / Weight / Location 4축은 항상 일치해야 함
