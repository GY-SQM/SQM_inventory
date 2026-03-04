# 업로드하신 내용 요약 — SQM v6.0 “3개 테이블” DB 설계

업로드하신 문서는 **SQM v6.0에서 사용할 3개 이력 테이블의 DB 스키마와 마이그레이션 설계**입니다.

---

## 1. 핵심 개념 (업로드 문서 기준)

- **inventory_tonbag.status** 흐름:  
  `AVAILABLE → RESERVED → PICKED → SOLD`
- 각 단계별 **이력을 별도 테이블에 기록**:
  - RESERVED 이력 → **reservation_table**
  - PICKED 이력 → **picking_table**
  - SOLD 이력 → **sold_table**

---

## 2. 테이블 관계도 (업로드 문서)

```
inventory (LOT 단위)
    └── inventory_tonbag (톤백 단위, status)
            ├── reservation_table   ← RESERVED 이력
            ├── picking_table       ← PICKED 이력
            └── sold_table          ← SOLD 이력
```

- **reservation_table**  
  Allocation 배정 시 생성.  
  `lot_no`, `tonbag_id`, `sub_lt`, `allocation_id`, `sale_ref`, `customer`, `product`, `reserved_qty_mt/kg`, `status`(ACTIVE/CANCELLED/PROCEEDED), `reserved_date` 등.
- **picking_table**  
  Picking List 수신 시 생성.  
  `reservation_id`로 reservation 연결, `tonbag_uid`, `picking_list_no/file`, `picked_qty_mt/kg`, `status`(ACTIVE/SOLD/RETURNED), `warehouse`, `location` 등.
- **sold_table**  
  바코드 스캔 시 생성.  
  `picking_id`, `reservation_id`로 연결, `scan_file`, `scan_code`, `sold_qty_mt/kg`, `sold_date`, 운송 정보 등.

---

## 3. Ruby 추천안 “B안” (업로드 문서)

- **기존 테이블 유지**  
  - **inventory_tonbag** 에 컬럼만 추가:  
    `tonbag_uid`, `reserved_id`, `picking_id`
- **신규 테이블 3개**  
  - reservation_table  
  - picking_table  
  - sold_table  
- **마이그레이션**  
  - DB 백업 → inventory_tonbag 컬럼 추가 → 3테이블 생성 → 기존 RESERVED/PICKED 데이터 이전 → `tonbag_uid` 자동 생성(GY-YYYY-00001 형식)

---

## 4. 업로드 문서에 포함된 구체적 내용

| 항목 | 설명 |
|------|------|
| **reservation_table** | CREATE TABLE + 인덱스 전체 SQL, 데이터 예시 |
| **picking_table** | CREATE TABLE + 인덱스 전체 SQL, 데이터 예시 |
| **sold_table** | CREATE TABLE + 인덱스 전체 SQL, 데이터 예시 |
| **3테이블 연결 흐름** | reservation → picking → sold 예시 (id/lot_no/sub_lt/tonbag_uid) |
| **대시보드용 집계** | inventory_tonbag 기준 AVAILABLE/RESERVED/PICKED/SOLD 건수·MT 쿼리 |
| **기존 테이블과 역할 정리** | inventory, inventory_tonbag, stock_movement, outbound vs 신규 3테이블 |
| **B안 마이그레이션 스크립트** | Python `run_migration(db_path)` — 백업, 컬럼 추가, 3테이블 생성, 기존 데이터 이전, tonbag_uid 생성 |

---

## 5. 현재 SQM 코드와의 차이

| 구분 | 업로드 문서 | 현재 SQM 코드 (v593/v600) |
|------|-------------|----------------------------|
| RESERVED 이력 | **reservation_table** (신규 테이블) | **allocation_plan** (기존 테이블 유지, reservation_table 미생성) |
| picking_table | reservation_id → **reservation_table(id)** | reservation_id → **allocation_plan(id)** |
| sold_table | reservation_id → **reservation_table(id)** | reservation_id → **allocation_plan(id)** |
| inventory_tonbag 추가 컬럼 | tonbag_uid, reserved_id, picking_id | tonbag_uid는 별도 마이그레이션(v5.9.1 등)에서 있을 수 있음; reserved_id, picking_id는 현재 마이그레이션에 없음 |

즉, 업로드하신 문서는 **“reservation_table을 새로 만들고, 3테이블을 그 스키마대로 정확히 설계·마이그레이션하자”**는 설계안이고,  
현재 코드는 **“reservation 이력은 allocation_plan으로 계속 쓰고, picking_table·sold_table만 신규 생성”**한 상태입니다.

---

## 6. 한 줄 요약

업로드하신 내용은 **SQM v6.0용 “reservation_table + picking_table + sold_table” 3개 테이블의 완전한 DB 스키마 정의, 관계도, B안(기존 테이블 최소 수정 + 신규 3테이블 생성), 그리고 그에 맞춘 Python 마이그레이션 스크립트까지 포함한 설계 문서**입니다.
