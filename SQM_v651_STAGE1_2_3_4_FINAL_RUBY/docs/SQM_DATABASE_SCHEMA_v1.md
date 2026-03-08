# SQM DATABASE SCHEMA v1

핵심 DB: `inventory.db`

## 핵심 테이블
- inventory: LOT 요약
- inventory_tonbag: Tonbag 실재고
- outbound / outbound_item / allocation: 출고 계획과 실행
- location_code는 inventory_tonbag에 저장

## 핵심 필드
- inventory.lot_no
- inventory.current_weight
- inventory_tonbag.tonbag_uid
- inventory_tonbag.tonbag_no
- inventory_tonbag.location_code
- inventory_tonbag.status
