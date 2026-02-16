# SQM 재고관리 시스템 — 데이터베이스 구조 문서
**버전**: v4.0.9 | **DB 엔진**: SQLite (WAL 모드) | **파일**: `data/db/sqm_inventory.db`

---

## 1. 테이블 총괄

| # | 테이블 | 설명 | 주요 역할 |
|---|--------|------|-----------|
| 1 | **inventory** | 재고 마스터 (LOT 단위) | 핵심. LOT별 재고 현황, 입고/잔량/출고 무게 |
| 2 | **inventory_tonbag** | 톤백 상세 (LOT→톤백) | LOT 하위 개별 톤백 관리. is_sample로 샘플 구분 |
| 3 | **inventory_detail** | 입고 상세 (컨테이너별) | 컨테이너/봉인번호별 상세. 현재 미사용(0행) |
| 4 | **inventory_snapshot** | 일일 스냅샷 | 매일 재고 현황 저장 (추이 분석용) |
| 5 | **shipment** | 선적 정보 | B/L, Invoice, 선박 등 선적 문서 마스터 |
| 6 | **outbound** | 출고 오더 | 출고 건별 고객/수량/상태 |
| 7 | **outbound_item** | 출고 상세 | 출고 건별 LOT/수량 매핑 |
| 8 | **stock_movement** | 재고 이동 이력 | 모든 입출고 트랜잭션 로그 |
| 9 | **return_history** | 반품 이력 | 반품(재입고) 건별 기록 |
| 10 | **picking_list_order** | 피킹리스트 오더 | SQM 출고지시서(Picking List) 메타 |
| 11 | **picking_list_material** | 피킹리스트 자재 | 출고지시서 자재 상세 |
| 12 | **picking_list_detail** | 피킹리스트 상세 | LOT별 피킹 수량/상태 |
| 13 | sqlite_sequence | (시스템) | AUTO_INCREMENT 관리 |
| 14 | sqlite_stat1 | (시스템) | ANALYZE 통계 |

---

## 2. 핵심 테이블 상세

### 2.1 inventory (재고 마스터) — 39열

LOT 단위 재고 관리의 **중심 테이블**. 모든 입고 PDF 파싱 결과가 여기에 저장됩니다.

| 열명 | 타입 | 설명 |
|------|------|------|
| **id** | INTEGER PK | 자동 증가 |
| shipment_id | INTEGER | shipment 테이블 FK |
| list_no | INTEGER | 목록 순번 (기본 0) |
| **sap_no** | TEXT | SAP 관리번호 |
| **bl_no** | TEXT | 선하증권 번호 (B/L) |
| **container_no** | TEXT | 컨테이너 번호 |
| **product** | TEXT | 제품명 (NICKEL SULFATE, LITHIUM CARBONATE 등) |
| **lot_no** | TEXT NOT NULL | **LOT 번호** (SQM 10자리: 112xxxxxxx) |
| lot_sqm | TEXT | SQM 원본 LOT 번호 |
| mxbg_pallet | INTEGER | MXBG/팔레트 수 (기본 10) |
| **net_weight** | REAL | 순중량 (kg) |
| gross_weight | REAL | 총중량 (kg) |
| salar_invoice_no | TEXT | SQM Invoice 번호 |
| **ship_date** | DATE | 선적일 |
| **arrival_date** | DATE | 입항일 |
| free_time | INTEGER | 무료 보관 기간 (일) |
| warehouse | TEXT | 창고 (기본 'GY') |
| eta_busan | DATE | 부산 도착 예정일 |
| stock_date | DATE | 입고 확정일 |
| customs | TEXT | 통관 상태 |
| sale_ref | TEXT | 판매 참조번호 |
| **initial_weight** | REAL | 입고 무게 (kg) |
| **current_weight** | REAL | 현재 잔량 (kg) |
| **picked_weight** | REAL | 출고 지정 무게 (kg) |
| product_code | TEXT | 제품 코드 |
| folio | TEXT | Folio 번호 |
| invoice_no | TEXT | 인보이스 번호 |
| vessel | TEXT | 선박명 |
| location | TEXT | 보관 위치 |
| **status** | TEXT | 상태 (AVAILABLE/PICKED/CONFIRMED/SHIPPED/DEPLETED) |
| inbound_date | DATE | 입고 처리일 |
| days_old | INTEGER | 보관 일수 |
| sold_to | TEXT | 판매처 |
| invoice_date | DATE | 인보이스 발행일 |
| actual_pickup | DATE | 실제 픽업일 |
| condition | TEXT | 상태 메모 |
| remark | TEXT | 비고 |
| created_at | TIMESTAMP | 생성 시각 |
| updated_at | TIMESTAMP | 수정 시각 |

### 2.2 inventory_tonbag (톤백 상세) — 19열

inventory의 하위 테이블. **LOT 1개 = 톤백 N개**. is_sample=1이면 샘플 톤백.

| 열명 | 타입 | 설명 |
|------|------|------|
| **id** | INTEGER PK | 자동 증가 |
| inventory_id | INTEGER | inventory 테이블 FK |
| sap_no | TEXT | SAP 번호 (inventory에서 복사) |
| bl_no | TEXT | B/L 번호 (inventory에서 복사) |
| **lot_no** | TEXT NOT NULL | LOT 번호 |
| **sub_lt** | INTEGER NOT NULL | 톤백 일련번호 (1, 2, 3...) |
| **weight** | REAL | 톤백 무게 (kg) |
| **status** | TEXT | 상태 (AVAILABLE/PICKED/SHIPPED/DEPLETED) |
| inbound_date | DATE | 입고일 |
| location | TEXT | 보관 위치 |
| picked_date | DATE | 출고 지정일 |
| picked_to | TEXT | 출고 대상 (고객명) |
| pick_ref | TEXT | 출고 참조번호 |
| outbound_date | DATE | 출고 완료일 |
| remarks | TEXT | 비고 |
| created_at | TIMESTAMP | 생성 시각 |
| updated_at | TIMESTAMP | 수정 시각 |
| sale_ref | TEXT | 판매 참조 |
| **is_sample** | INTEGER | 샘플 여부 (0=정규, 1=샘플 1kg) |

### 2.3 stock_movement (재고 이동 이력) — 13열

모든 입출고의 **감사 로그**. before/after 무게 기록.

| 열명 | 타입 | 설명 |
|------|------|------|
| **id** | INTEGER PK | 자동 증가 |
| **movement_type** | TEXT | INBOUND / OUTBOUND / RETURN / ADJUST |
| movement_date | TIMESTAMP | 이동 시각 |
| lot_no | TEXT | LOT 번호 |
| product_code | TEXT | 제품 코드 |
| **qty_kg** | REAL | 이동 수량 (kg) |
| before_weight | REAL | 이동 전 잔량 |
| after_weight | REAL | 이동 후 잔량 |
| reference_no | TEXT | 참조 번호 (출고번호 등) |
| reference_type | TEXT | 참조 유형 |
| remarks | TEXT | 비고 |
| created_at | TIMESTAMP | 생성 시각 |
| created_by | TEXT | 처리자 (기본 'SYSTEM') |

### 2.4 return_history (반품 이력) — 10열

| 열명 | 타입 | 설명 |
|------|------|------|
| **id** | INTEGER PK | 자동 증가 |
| lot_no | TEXT NOT NULL | LOT 번호 |
| sub_lt | INTEGER NOT NULL | 톤백 번호 |
| return_date | DATE | 반품일 |
| original_customer | TEXT | 원래 고객 |
| original_sale_ref | TEXT | 원래 판매 참조 |
| reason | TEXT | 반품 사유 |
| remark | TEXT | 비고 |
| weight | REAL | 반품 무게 (kg) |
| created_at | TIMESTAMP | 생성 시각 |

---

## 3. 선적/출고 관련 테이블

### 3.1 shipment (선적 정보) — 30열
B/L, Invoice 등 선적 문서 파싱 결과 저장. inventory 레코드와 shipment_id로 연결.

### 3.2 outbound (출고 오더) — 11열
출고 건별 마스터. 고객, 날짜, 총수량, 상태(PENDING/COMPLETED).

### 3.3 outbound_item (출고 상세) — 11열
출고 건별 LOT/수량 매핑. outbound_id → outbound 테이블 FK.

### 3.4 picking_list_order (피킹리스트) — 27열
SQM 출고지시서 PDF 파싱 결과. 고객정보, 컨테이너, 항구, 일정 등.

### 3.5 picking_list_material / picking_list_detail
피킹리스트의 자재/LOT 상세.

---

## 4. 테이블 관계도 (ERD 요약)

```
shipment (1) ──→ (N) inventory (1) ──→ (N) inventory_tonbag
                     │                        │
                     │                        ├── is_sample=0: 정규 톤백
                     │                        └── is_sample=1: 샘플 톤백
                     │
                     ├──→ (N) stock_movement (입출고 이력)
                     ├──→ (N) outbound_item ──→ outbound
                     └──→ (N) return_history (반품 이력)

picking_list_order ──→ picking_list_material
                   ──→ picking_list_detail

inventory_snapshot (독립: 일일 스냅샷)
inventory_detail (독립: 컨테이너 상세, 현재 미사용)
```

---

## 5. 인덱스 목록 (44개)

| 인덱스명 | 대상 테이블 | 용도 |
|----------|-------------|------|
| idx_inventory_lot_no | inventory | LOT 검색 |
| idx_inventory_sap_no | inventory | SAP 검색 |
| idx_inventory_bl_no | inventory | B/L 검색 |
| idx_inventory_container | inventory | 컨테이너 검색 |
| idx_inventory_product | inventory | 제품 검색 |
| idx_inventory_status | inventory | 상태 필터 |
| idx_inventory_arrival | inventory | 입항일 검색 |
| idx_inventory_invoice | inventory | 인보이스 검색 |
| idx_tonbag_lot_sublt | inventory_tonbag | LOT+톤백 복합 검색 |
| idx_tonbag_sample | inventory_tonbag | 샘플 필터 |
| idx_movement_lot | stock_movement | 이력 검색 |
| idx_movement_date | stock_movement | 날짜 검색 |
| ... (나머지 32개 생략) | | |

---

## 6. DB 파일 위치 및 백업

- **DB 파일**: `data/db/sqm_inventory.db`
- **백업 위치**: `data/db/backups/` (자동 백업)
- **WAL 모드**: 읽기 성능 최적화, 동시 접근 지원
- **네트워크 모드**: 공유폴더 환경 자동 감지 (WAL → DELETE 전환)

---

*문서 생성: SQM v4.0.9 | 최종 갱신: 2026-02-09*
