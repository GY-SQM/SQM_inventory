# Picking List 파싱 데이터 열 구성 및 판매화물 결정(PICKED) 흐름

## 1) 파싱 데이터는 어떤 열(필드)로 구성되는가

파싱 결과는 **한 개의 테이블**이 아니라 **3단계 구조**입니다.

### 1.1 최상위: `PickingListResult`

| 필드(열) | 타입 | 설명 |
|----------|------|------|
| `meta` | PickingListMeta | 헤더/메타 정보 |
| `tonbag` | List[PickingLotItem] | 본품(톤백) 배치 목록 — **판매화물 결정 시 핵심** |
| `sample` | List[PickingLotItem] | 샘플 배치 목록 |
| `summary` | dict | 집계 (total_lots, total_mt, total_sample_kg 등) |
| `errors` | List[str] | 검증/파싱 오류 메시지 |
| `success` | bool | 파싱·하드스톱 통과 여부 |

### 1.2 메타: `PickingListMeta`

| 필드(열) | 타입 | DB/화면 사용 |
|----------|------|----------------|
| `picking_no` | str | picking_list_order.picking_no |
| `sales_order` | str | picking_list_order.sales_order |
| `outbound_id` | str | picking_list_order.customer_ref |
| `creation_date` | str | picking_list_order.picking_date |
| `delivery_terms` | str | picking_list_order.delivery_terms |
| `containers` | str | picking_list_order.containers |
| `cutoff_date` | str | (보조) |
| `plan_loading_date` | str | (보조) |
| `contact_person` | str | picking_list_order.contact_person |
| `contact_email` | str | picking_list_order.contact_email |
| `port_loading` | str | picking_list_order.port_loading |
| `port_discharge` | str | picking_list_order.port_discharge |
| `total_nw_kg` | str | picking_list_order.total_nw_kg |
| `total_gw_kg` | str | picking_list_order.total_gw_kg |

### 1.3 품목 행: `PickingLotItem` (tonbag / sample 각 1행 = 1배치)

| 필드(열) | 타입 | 설명 |
|----------|------|------|
| `lot_no` | str | 배치(LOT) 번호 — **Gate-1·execute_from_picking에서 사용** |
| `weight_kg` | float | 중량(kg). MT는 이미 ×1000 변환됨 |
| `unit` | str | 'MT' 또는 'KG' |
| `storage` | str | Storage location (보조) |

### 1.4 집계: `result.summary` (dict)

| 키 | 타입 | 설명 |
|----|------|------|
| `total_lots` | int | LOT 개수 |
| `total_mt` | float | 본품 총 MT |
| `total_sample_kg` | float | 샘플 총 kg |
| `lot_integrity` | bool | 톤백 LOT 집합 == 샘플 LOT 집합 |
| `tonbag_count` | int | 톤백 배치 수 |
| `sample_count` | int | 샘플 배치 수 |

---

## 2) “테이블”처럼 보는 방법 (표시용)

- **본품(톤백) 테이블**: `result.tonbag` → 열 = **lot_no, weight_kg, unit, storage**
- **샘플 테이블**: `result.sample` → 열 = **lot_no, weight_kg, unit, storage**
- **헤더 1행**: `result.meta` → 위 메타 필드들

`expand_tonbags(result)`로 만드는 “출고 행”은 다음 열을 가집니다.  
(판매화물 결정 실행 경로에서는 **사용하지 않고**, LOT 단위로 DB를 갱신합니다.)

- **expand_tonbags 행**: type, lot_no, sub_lt, weight_kg, storage, status

---

## 3) 이 파싱 데이터로 판매 화물 결정(PICKED)까지 진행해도 되는지

**별 문제 없습니다.**  
파싱 결과가 가진 열이 Gate-1·execute_from_picking·DB에 모두 맞게 사용됩니다.

### 3.1 흐름 요약

1. **PDF 업로드** → `parse_picking_list(path)` → `PickingListResult`
2. **확인 다이얼로그** → `meta.picking_no`, `meta.sales_order`, `summary.total_lots`, `summary.total_mt` 사용
3. **Gate-1** → `picking_result.tonbag`에서 **lot_no**만 추출 → `allocation_plan`의 RESERVED LOT와 교차검증
4. **판매화물 결정 실행** → `execute_from_picking(picking_result, ...)`  
   - **meta**: sales_order, outbound_id, creation_date, picking_no, delivery_terms, port_loading, port_discharge, containers, contact_person, contact_email, total_nw_kg, total_gw_kg → **picking_list_order** INSERT  
   - **summary**: total_mt → **total_weight** (kg 단위로 ×1000)  
   - **gate1['matched_lots']**: 각 **lot_no**마다  
     - `allocation_plan` status → 'EXECUTED', executed_at 갱신  
     - `inventory_tonbag` status → PICKED, picked_date 갱신  
     - `picking_list_detail`에 picking_order_id, **lot_no**, weight, picked_status, picked_at INSERT

### 3.2 열 매핑 검증

| 필요한 값 | 출처 | 비고 |
|-----------|------|------|
| LOT 목록 | `picking_result.tonbag` 각 항목의 **lot_no** | Gate-1·execute 모두 사용 |
| sales_order | `meta.sales_order` | picking_list_order, 확인 메시지 |
| picking_no | `meta.picking_no` | picking_list_order, Gate-1 리포트 |
| total_weight(kg) | `summary['total_mt'] * 1000` | picking_list_order.total_weight |
| 기타 메타 | `meta.*` (outbound_id, creation_date, delivery_terms, ports, containers, contact_*, total_nw_kg, total_gw_kg) | getattr(meta, 이름, '')로 안전 접근 |

- `gate1_verify_picking`은 **picking_result.tonbag**만 사용하며, 각 요소에서 **lot_no**는 `getattr(item, 'lot_no', ...)`로 읽습니다.  
- `execute_from_picking`은 **meta**와 **summary**만 추가로 사용하며, 실제 DB 갱신은 **gate1['matched_lots']**의 **lot_no**와 DB의 **inventory_tonbag** 조회 결과로 수행합니다.

### 3.3 결론

- 파싱 데이터의 **열 구성**(meta, tonbag/sample의 lot_no·weight_kg·unit·storage, summary)은 현재 **Gate-1 → 판매화물 결정(PICKED)** 흐름에서 요구하는 항목을 모두 포함합니다.
- **picking_list_order** / **picking_list_detail** / **allocation_plan** / **inventory_tonbag**와의 매핑도 위와 같이 일치하므로, **이 파싱 데이터 테이블(구조)이면 프로그램에서 판매 화물 결정(PICKED)까지 진행하는 데 별 문제 없습니다.**
