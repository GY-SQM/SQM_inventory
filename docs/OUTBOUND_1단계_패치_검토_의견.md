# process_outbound 1단계 패치 초안 검토 의견

**기준일:** 2026-02-22  
**대상:** sqm_v592 → sqm_work diff (db_migration_mixin, outbound_mixin, outbound_handlers, simple_excel_outbound, import_handlers, features_v2_mixin)

---

## 1. 전체 평가

- 설계 확정안(OUTBOUND_1단계_설계_확정.md)과 **방향이 일치**합니다.  
  source 컬럼 추가, reserve→execute 인라인 순차 처리, QUICK 시 stop_at_picked=True, 나머지 EXCEL/AUTO 시 SOLD까지 자동, 8개 제한은 빠른 출고만 적용하는 구조가 잘 반영되어 있습니다.
- 아래만 보완하면 적용해도 됩니다.

---

## 2. 반드시 보완할 점

### 2.1 _execute_outbound: alloc_data.rows → dict 리스트로 변환

- **문제:** `alloc_data.rows`는 **AllocationRow(dataclass)** 리스트입니다.  
  새 `process_outbound`는 `alloc.get('lot_no')` 등 **dict**를 전제로 합니다.  
  그대로 `items = alloc_data.rows`로 넘기면 `AttributeError` (dataclass에 `.get` 없음) 가능성이 큽니다.
- **권장:** `_execute_outbound`에서 **dict 리스트로 변환**한 뒤 `process_outbound`에 넘기기.

```python
# 예시 (alloc_data.rows → dict)
if hasattr(alloc_data, 'rows'):
    items = []
    for r in alloc_data.rows:
        qty_mt = getattr(r, 'qty_mt', 0) or 0
        weight_kg = qty_mt * 1000.0 if qty_mt else 0
        items.append({
            'lot_no': getattr(r, 'lot_no', ''),
            'weight_kg': weight_kg,
            'qty_mt': qty_mt,
            'customer': getattr(r, 'sold_to', '') or getattr(r, 'customer', ''),
            'sale_ref': getattr(r, 'sale_ref', ''),
        })
else:
    items = [alloc_data] if isinstance(alloc_data, dict) else list(alloc_data)
result = self.engine.process_outbound(items, source='EXCEL', stop_at_picked=False)
```

- `AllocationRow`는 `qty_mt`, `lot_no`, `sold_to`(또는 property `customer`), `sale_ref`를 갖습니다. weight_kg는 `qty_mt * 1000`으로 두면 됩니다. (sublot_count 기반 계산이 따로 있으면 그 로직에 맞춰 통일.)

---

### 2.2 simple_excel_outbound 호출 방식

- **패치:** `process_outbound({ ... }, source='EXCEL')` 처럼 **단일 dict**를 넘기는 형태로 보입니다.
- **확인:** `process_outbound` 내부는 `if isinstance(allocation_data, dict): allocations = [allocation_data]` 로 리스트로 만들어 처리하므로, 단일 dict 전달은 문제 없습니다.  
  다만 **한 번에 여러 건**을 넘기는 경로(리스트로 한 번에 호출)가 있다면, 그때는 `source='EXCEL'`만 두 번째 인자로 주면 됩니다.  
  현재 패치가 건별로 루프 돌며 `process_outbound(one_dict, source='EXCEL')` 호출이라면 그대로 두어도 됩니다.

---

## 3. 선택 보완(권장)

### 3.1 마이그레이션 호출 순서

- **패치:** `_migrate_v593_allocation_plan()` 다음에 `_migrate_v5992_allocation_source()` 호출을 추가.
- **현재 v592:** `_migrate_v599_missing_columns()`, `_migrate_v600_picking_sold_tables()` 등이 이미 있으므로, 적용 시 **실제 저장소의 run_migrations() 목록**에 맞춰 `_migrate_v5992_allocation_source()`를 **v593 다음, 기존 v599/v600 전후** 중 한 곳에 넣으면 됩니다. (버전 번호만 v5992로 통일되어 있으면 됨.)

### 3.2 v593 CREATE TABLE에 source 넣는 부분

- **패치:** `_migrate_v593_allocation_plan()` 안 CREATE TABLE에 `source TEXT DEFAULT 'ALLOCATION'` 를 넣었고, **기존 DB**용으로는 `_migrate_v5992_allocation_source()`에서 ADD COLUMN으로 추가.
- **의미:** 신규 DB는 처음부터 source 컬럼 보유, 구 DB는 마이그레이션으로 추가.  
  단, **이미 v593으로 allocation_plan이 생성된 DB**에는 CREATE를 다시 타지 않으므로, **반드시** `_migrate_v5992_allocation_source()`가 돌아가야 합니다.  
  그래서 “v593 CREATE 수정”은 선택(신규 설치용)이고, “v5992 ADD COLUMN”은 **필수**로 두는 현재 구조가 맞습니다.

### 3.3 _process_single_outbound

- **현재:** 패치 적용 후 `process_outbound`는 `_process_single_outbound`를 부르지 않고, 전부 인라인 처리합니다.
- **의견:** 다른 호출처가 없다면 **dead code**이므로, 나중 정리 시 제거하거나, “레거시/단건용”으로 남길지 결정하면 됩니다. 패치 자체를 막을 수준은 아닙니다.

---

## 4. outbound 테이블 INSERT

- **패치:** `INSERT INTO outbound (customer, total_qty_mt, outbound_date, created_at) VALUES (...)`  
- **저장소:** `db_schema_mixin` 등에 `outbound` 테이블 정의가 있고, preflight_mixin에는 `outbound_no, customer, sale_ref, outbound_date, total_qty_mt, total_lots, status` 등 다른 컬럼을 쓰는 경로가 있을 수 있습니다.
- **권장:** 실제 DB 스키마(outbound 테이블 컬럼 목록)와 맞는지 한 번 확인하고, 없으면 기존 출고 경로와 동일한 컬럼 세트로 INSERT하도록 맞추면 안전합니다.

---

## 5. 요약

| 항목 | 상태 | 조치 |
|------|------|------|
| source 컬럼 + v5992 마이그레이션 | 적절 | 적용 시 run_migrations 순서만 저장소에 맞추기 |
| process_outbound(source, stop_at_picked) | 설계안 반영 | — |
| 빠른 출고 8개 제한 + QUICK + stop_at_picked=True | 적절 | — |
| 배정표 출고 EXCEL + SOLD까지 | 적절 | — |
| _execute_outbound에서 alloc_data.rows 전달 | **수정 필요** | rows → dict 리스트 변환 후 process_outbound 호출 |
| simple_excel / import_handlers / features_v2 source='EXCEL' | 적절 | — |

**정리:**  
- **반드시:** `_execute_outbound`에서 `alloc_data.rows`(AllocationRow)를 **dict 리스트로 변환**한 뒤 `process_outbound(items, source='EXCEL', stop_at_picked=False)` 호출하도록 보완.  
- 그 외는 설계안과 일치하므로, 위 보완 후 적용해도 됩니다.
