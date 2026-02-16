# SQM v3.8.8 — 3단계 계층 구조 분석

> 📅 2026-02-08 | Ruby 분석

---

## 1. 프로그램의 본질

SQM은 **입고 → 재고관리 → 출고** 프로그램입니다.

```
┌─────────────────────────────────────────────────────────────┐
│  4종 PDF 서류 ──파싱──→  DB 저장 ──조회──→  재고 화면      │
│                            │                                │
│                        출고 배정 ──→ PICKED → CONFIRMED     │
│                            │                                │
│                         반품 ←── 일부 반환                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Vessel 1번: B/L (선하증권) — 선적 단위

### DB 테이블: `shipment`

| 컬럼 | 역할 | 예시 |
|------|------|------|
| `sap_no` | SAP 발주번호 (UNIQUE) | 2200033057 |
| `bl_no` | 선하증권 번호 | MAEU258468669 |
| `vessel` | 선박명 | CHARLOTTE MAERSK 535W |
| `ship_date` | 선적일 | 2025-09-06 |
| `arrival_date` | 입항일 | 2025-10-17 |
| `total_lots` | 총 LOT 수 | 20 |
| `total_containers` | 총 컨테이너 수 | 5 |

### 현재 프로그램 반영 상태

- **✅ 반영됨**: `inventory` 테이블에 `sap_no`, `bl_no`, `ship_date`, `arrival_date`, `vessel` 컬럼이 개별 LOT마다 저장됨
- **⚠️ 구조적 이슈**: `shipment` 테이블이 존재하지만 **실제로 사용되지 않음**. 입고 시 `shipment` 테이블에 레코드를 생성하지 않고, `inventory` 테이블에 B/L 정보를 직접 중복 저장함
- **영향**: 같은 B/L의 20개 LOT에 동일한 `bl_no`, `sap_no`, `ship_date`가 20번 반복 저장됨 (정규화 위반이지만 기능에는 문제 없음)

### 4종 서류에서 B/L 데이터 추출

```
① Packing List → product, vessel, folio
② Invoice/FA   → salar_invoice_no, ship_date (FECHA), sap_no
③ B/L          → bl_no, ship_date (Shipped on Board)
④ D/O          → arrival_date, free_time, warehouse
```

### 데이터 흐름 (코드 경로)

```
parsers/parser_packing.py    → PackingListData (product, vessel, code, lots[])
parsers/parser_invoice.py    → InvoiceData (salar_invoice_no, invoice_date, sap_no)
parsers/parser_bl_do.py      → BLData (bl_no, ship_date, vessel)
parsers/parser_bl_do.py      → DOData (arrival_date, free_time_info, warehouse)
                ↓
gui_app_modular/dialogs/onestop_inbound.py::_merge_results()
                ↓
         4종 데이터를 18열 미리보기 dict로 병합
                ↓
gui_app_modular/dialogs/onestop_inbound.py::_save_to_db()
                ↓
         LOT별로 packing_dict 생성 → engine.process_inbound() 호출
                ↓
engine_modules/inventory_modular/inbound_mixin.py::process_inbound()
                ↓
         _prepare_lot_data() → lot_data dict (20개 컬럼)
                ↓
         _insert_lot() → INSERT INTO inventory
         _create_tonbags_for_lot() → INSERT INTO inventory_tonbag (10개씩)
```

---

## 3. Vessel 2번: LOT — 화물 단위

### DB 테이블: `inventory`

| 컬럼 | 역할 | 예시 | NOT NULL |
|------|------|------|----------|
| `lot_no` | LOT 번호 (10자리 SQM) | 1125081447 | ✅ UNIQUE |
| `sap_no` | SAP 발주번호 | 2200033057 | |
| `bl_no` | B/L 번호 | MAEU258468669 | |
| `container_no` | 컨테이너 번호 | FFAU535500-6 | |
| `product` | 제품명 | LITHIUM CARBONATE | |
| `product_code` | 제품코드 | MIC9000.00 | |
| `lot_sqm` | LOT SQM 코드 | 977878 | |
| `mxbg_pallet` | 톤백 수량 | 10 | |
| `net_weight` | 순중량 (kg) | 5001.0 | |
| `gross_weight` | 총중량 (kg) | 5131.25 | |
| `initial_weight` | 입고량 (kg) | 5001.0 | |
| `current_weight` | 잔량 (kg) | 5001.0 → 출고 시 감소 | |
| `picked_weight` | 배정량 (kg) | 0 → 출고 시 증가 | |
| `salar_invoice_no` | 인보이스 번호 | 16130 | |
| `ship_date` | 선적일 | 2025-09-06 | |
| `arrival_date` | 입항일 | 2025-10-17 | |
| `free_time` | 무료 보관 일수 | 25 | |
| `warehouse` | 창고 | 광양 | |
| `status` | 상태 | AVAILABLE / DEPLETED | |

### 현재 프로그램 반영 상태

- **✅ 반영됨**: 입고 시 `_prepare_lot_data()`에서 위 20개 컬럼의 lot_data dict 생성 → `_insert_lot()`으로 DB 삽입
- **✅ 반영됨**: 재고 현황 탭 (`inventory_tab.py`)에서 `INVENTORY_COLUMNS` 18개 열로 표시
- **✅ 반영됨**: 출고 시 `current_weight` 감소, `picked_weight` 증가, `status` 변경
- **✅ 반영됨**: 중복 LOT 체크 (`lot_no UNIQUE` + `_check_lot_exists()`)

### LOT 상태 전이

```
AVAILABLE ──출고배정──→ (current_weight 감소)
    │                      │
    │                  전량출고 → DEPLETED
    │                      │
    │                  반품 ←── process_return() → current_weight 복원
    │
    └── status는 current_weight > 0 이면 AVAILABLE, = 0 이면 DEPLETED
```

### 코드 경로 (출고)

```
gui_app_modular/handlers/outbound_processor.py
  → _on_outbound_wizard()          # 출고 마법사 UI
                ↓
engine_modules/inventory_modular/outbound_mixin.py
  → pick_tonbags(lot_no, count)     # 톤백 N개 배정
  → _update_lot_after_pick()        # inventory.current_weight 차감
                ↓
         inventory_tonbag.status = 'PICKED'
         inventory.current_weight -= picked_weight
         inventory.picked_weight += picked_weight
         stock_movement INSERT (이력 기록)
```

### 코드 경로 (반품)

```
gui_app_modular/mixins/advanced_dialogs_mixin.py
  → _show_return_dialog()           # 반품 UI
                ↓
engine_modules/inventory_modular/return_mixin.py
  → process_return(return_data)     # 반품 처리
  → return_single_tonbag()          # 개별 톤백 반품
                ↓
         inventory_tonbag.status = 'AVAILABLE' (복원)
         inventory.current_weight += returned_weight
         inventory.picked_weight -= returned_weight
         return_history INSERT (반품 이력)
         stock_movement INSERT (이동 이력)
```

---

## 4. Vessel 3번: 톤백 — 최소 단위

### DB 테이블: `inventory_tonbag`

| 컬럼 | 역할 | 예시 |
|------|------|------|
| `inventory_id` | LOT FK | 42 |
| `sap_no` | SAP 번호 | 2200033057 |
| `bl_no` | B/L 번호 | MAEU258468669 |
| `lot_no` | LOT 번호 (NOT NULL) | 1125081447 |
| `sub_lt` | 톤백 순번 (NOT NULL) | 1~10 |
| `weight` | 개별 무게 (kg) | 500.1 |
| `status` | 상태 | AVAILABLE / PICKED / SHIPPED |
| `location` | 위치 | A-1-3 |
| `picked_date` | 배정일 | 2025-11-01 |
| `picked_to` | 출고처 | ABC Corp |
| `outbound_date` | 출고일 | 2025-11-05 |
| **UNIQUE** | **(sap_no, bl_no, lot_no, sub_lt)** | 중복 방지 |

### 현재 프로그램 반영 상태

- **✅ 반영됨**: 입고 시 `_create_tonbags_for_lot()`에서 `mxbg_pallet` 수만큼 톤백 자동 생성 (보통 10개)
- **✅ 반영됨**: 톤백 무게 = `net_weight / mxbg_pallet` (균등 배분)
- **✅ 반영됨**: 톤백 탭 (`tonbag_tab.py`)에서 Sub LOT 단위 표시
- **✅ 반영됨**: 출고 시 톤백 단위로 PICK (개별 톤백 status 변경)
- **✅ 반영됨**: 위치 매핑 (`_import_location_excel`) — Excel에서 톤백 위치 일괄 입력

### 톤백 생성 로직 (코드)

```python
# inbound_mixin.py :: process_inbound() 내부
bag_count = mxbg_pallet  # 보통 10
per_bag_weight = net_weight / bag_count  # 5001 / 10 = 500.1kg

for sub_lt in range(1, bag_count + 1):
    INSERT INTO inventory_tonbag (
        inventory_id, sap_no, bl_no, lot_no,
        sub_lt, weight, status, inbound_date
    ) VALUES (
        {inv_id}, '2200033057', 'MAEU258468669', '1125081447',
        {sub_lt}, 500.1, 'AVAILABLE', '2025-10-17'
    )
```

### 톤백 상태 전이

```
AVAILABLE ──pick_tonbags()──→ PICKED ──confirm──→ SHIPPED
    ↑                            │
    └── return_single_tonbag() ──┘  (반품 시 AVAILABLE 복원)
```

---

## 5. 3단계 통합 관계도

```
┌─────────────────────────────────────────────────────────────────┐
│                    Vessel 1: B/L (선적)                         │
│  SAP: 2200033057 | BL: MAEU258468669 | Ship: 2025-09-06       │
│  Vessel: CHARLOTTE MAERSK 535W | Arrival: 2025-10-17          │
│  Invoice: 16130 | Containers: 5 | Free Time: 25일              │
├─────────────────────────────────────────────────────────────────┤
│ Vessel 2: LOT (화물)                                           │
│                                                                 │
│ ┌──────────────┐ ┌──────────────┐     ┌──────────────┐        │
│ │ LOT 1447     │ │ LOT 1448     │ ... │ LOT 2330     │  ×20   │
│ │ Container:   │ │ Container:   │     │ Container:   │        │
│ │ FFAU535500-6 │ │ FFAU535500-6 │     │ TCLU908912-1 │        │
│ │ Net: 5,001kg │ │ Net: 5,001kg │     │ Net: 5,001kg │        │
│ │ MXBG: 10     │ │ MXBG: 10     │     │ MXBG: 10     │        │
│ │ Status:      │ │ Status:      │     │ Status:      │        │
│ │ AVAILABLE    │ │ AVAILABLE    │     │ AVAILABLE    │        │
│ └──────┬───────┘ └──────┬───────┘     └──────┬───────┘        │
│        │                │                     │                │
├────────┼────────────────┼─────────────────────┼────────────────┤
│ Vessel 3: 톤백 (최소 단위)                                     │
│        │                │                     │                │
│   ┌────┴────┐      ┌────┴────┐           ┌────┴────┐          │
│   │ sub 1-10│      │ sub 1-10│           │ sub 1-10│   ×200   │
│   │ 500.1kg │      │ 500.1kg │           │ 500.1kg │          │
│   │ 각각    │      │ 각각    │           │ 각각    │          │
│   │AVAILABLE│      │AVAILABLE│           │AVAILABLE│          │
│   └─────────┘      └─────────┘           └─────────┘          │
└─────────────────────────────────────────────────────────────────┘

1 B/L = 20 LOTs = 200 톤백 = 100,020 kg (총 순중량)
```

---

## 6. 현재 문제점 및 개선 제안

### 해결된 문제들 (v3.8.8)

| 문제 | 원인 | 해결 |
|------|------|------|
| NOT NULL lot_no | PackingData 래핑 → dict 변환 실패 | dict 직접 사용 |
| PackingListData.sap_no 없음 | dataclass 필드 미정의 | 필드 추가 |
| ThemeColors 미정의 | 로컬 import 스코프 문제 | 각 메서드에서 import |
| custom_messagebox 없음 | 파일 자체 누락 | 신규 생성 |
| 재고 화면 비어있음 | parent vs app 참조 오류 | app 별도 전달 |

### 구조적 권고사항

| 항목 | 현재 | 권고 |
|------|------|------|
| shipment 테이블 | 생성만 되고 미사용 | 입고 시 shipment INSERT → inventory.shipment_id 연결 |
| B/L 정보 중복 | 20 LOT × 같은 bl_no 반복 | shipment FK로 정규화 (하지만 현재도 기능적 문제 없음) |
| 파서 객체 접근 | 직접 접근 (pl.sap_no) | 전부 getattr() 통일 (v3.8.8에서 완료) |
| import 경로 | utils vs dialogs 혼재 | 단일 경로로 통일 권장 |

---

## 7. 핵심 파일 맵

```
입고 관련:
  gui_app_modular/dialogs/onestop_inbound.py    (983줄) — 원스톱 입고 UI
  gui_app_modular/handlers/inbound_processor.py  (1155줄) — 입고 처리 핸들러
  engine_modules/inventory_modular/inbound_mixin.py (302줄) — 입고 DB 로직
  parsers/parser_packing.py                       — PL 파싱
  parsers/parser_invoice.py                       — Invoice 파싱
  parsers/parser_bl_do.py                         — BL/DO 파싱

출고 관련:
  gui_app_modular/handlers/outbound_processor.py  — 출고 UI 핸들러
  engine_modules/inventory_modular/outbound_mixin.py — 출고 DB 로직

반품 관련:
  gui_app_modular/mixins/advanced_dialogs_mixin.py — 반품 UI
  engine_modules/inventory_modular/return_mixin.py  — 반품 DB 로직

재고 표시:
  gui_app_modular/tabs/inventory_tab.py (792줄)  — 재고 현황 탭
  gui_app_modular/tabs/tonbag_tab.py (600줄)     — 톤백 상세 탭

공통:
  engine_modules/database.py (1322줄)             — DB 스키마 + 쿼리
  gui_app_modular/utils/custom_messagebox.py      — 메시지박스
  gui_app_modular/mixins/toolbar_mixin.py (713줄) — 메뉴바
```
