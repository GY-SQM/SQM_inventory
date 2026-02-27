# SQM v3.8.4 엔진 API Reference

**자동 생성일**: 2026-02-07 13:24
**소스**: engine_modules/ 디렉토리

---

## 입고 (Inbound)

### `process_inbound(**packing_data**, invoice_data=None, bl_data=None, do_data=None) → Dict`

입고 처리

**파라미터:**
- packing_data: 패킹 리스트 데이터 (dict 또는 PackingData)
- invoice_data: 인보이스 데이터 (선택)
- bl_data: B/L 데이터 (선택)
- do_data: D/O 데이터 (선택)

**반환값:**
- dict: {success, message, lot_no, created_lots, created_tonbags, errors, warnings}

*소스: engine_modules/inventory_modular/inbound_mixin.py*

---

### `process_inbound_safe(**packing_data**, invoice_data=None, bl_data=None, do_data=None) → Dict`

입고 처리 - Preflight 검증 적용 (All-or-Nothing)

**파라미터:**
- packing_data: PackingListData 객체
- invoice_data: InvoiceData 객체 (선택)
- bl_data: BLData 객체 (선택)
- do_data: DOData 객체 (선택)

**반환값:**
- 처리 결과 딕셔너리

*소스: engine_modules/preflight_mixin.py*

---

### `preflight_check_inbound(**data**) → PreflightResult`

입고 데이터 Preflight 검증 (실행 전 검증만)

**파라미터:**
- data: 검증할 데이터 리스트

**반환값:**
- PreflightResult: 검증 결과 (오류 있어도 예외 없음)

*소스: engine_modules/preflight_mixin.py*

---

## 출고 (Outbound)

### `process_outbound(**allocation_data**) → Dict`

출고 처리 (v3.8.4: All-or-Nothing + 톤백 동기화)


*소스: engine_modules/inventory_modular/outbound_mixin.py*

---

### `process_outbound_safe(**allocation_data**, strict=True) → Dict`

출고 처리 - Preflight 검증 적용 (All-or-Nothing)

**파라미터:**
- allocation_data: 출고 배정 데이터
- strict: True면 WARNING도 중단 (기본: True)

**반환값:**
- 처리 결과 딕셔너리

*소스: engine_modules/preflight_mixin.py*

---

### `preflight_check_outbound(**data**) → PreflightResult`

출고 데이터 Preflight 검증 (실행 전 검증만)

**파라미터:**
- data: 검증할 데이터 리스트

**반환값:**
- PreflightResult: 검증 결과 (오류 있어도 예외 없음)

*소스: engine_modules/preflight_mixin.py*

---

### `pick_tonbags(**lot_no**, **count**, customer=None, sub_lot_no=None) → Dict`

톤백 피킹

**파라미터:**
- lot_no: LOT 번호
- count: 피킹할 톤백 수량
- customer: 고객명
- sub_lot_no: Sub LOT 번호 (선택)

**반환값:**
- dict: {success, message, picked_tonbags, total_weight_kg, errors}

*소스: engine_modules/inventory_modular/outbound_mixin.py*

---

### `cancel_outbound_tonbag(**lot_no**, **sub_lt**) → Dict`

출고 취소: 톤백 PICKED → AVAILABLE + inventory.current_weight 복구


*소스: engine_modules/inventory_modular/outbound_mixin.py*

---

### `cancel_outbound_bulk(**items**) → Dict`

일괄 출고 취소 (All-or-Nothing)


*소스: engine_modules/inventory_modular/outbound_mixin.py*

---

## 조회 (Query)

### `get_inventory(status=None, product=None, lot_no=None) → List`

재고 목록 조회


*소스: engine_modules/inventory_modular/query_mixin.py*

---

### `get_lot_detail(**lot_no**) → Dict`

LOT 상세 조회


*소스: engine_modules/inventory_modular/query_mixin.py*

---

### `get_tonbags(lot_no=None, status=None, sub_lt=None) → List`

톤백 조회


*소스: engine_modules/inventory_modular/query_mixin.py*

---

### `get_sublots(lot_no=None, status=None) → List`

Sub LOT 조회 (inventory_tonbag 기반 그룹 집계)


*소스: engine_modules/inventory_modular/query_mixin.py*

---

### `get_inventory_summary() → Dict`

재고 요약 조회


*소스: engine_modules/inventory_modular/query_mixin.py*

---

### `get_inventory_by_product() → List`

제품별 재고 조회


*소스: engine_modules/inventory_modular/query_mixin.py*

---

### `get_inventory_by_customer() → List`

고객별 재고 조회 (톤백 기준)


*소스: engine_modules/inventory_modular/query_mixin.py*

---

### `search_lots(keyword=None, **filters**) → List`

LOT 검색


*소스: engine_modules/inventory_modular/query_mixin.py*

---

### `get_shipment_list() → List`

Get shipment list


**반환값:**
- List of shipment records

*소스: engine_modules/inventory_modular/shipment_mixin.py*

---

## 톤백 (Tonbag)

### `get_tonbag_summary(**lot_no**) → Dict`

Get tonbag summary for a LOT

**파라미터:**
- lot_no: LOT number

**반환값:**
- Summary dict with counts and weights

*소스: engine_modules/inventory_modular/tonbag_mixin.py*

---

### `get_all_sublots_summary() → Dict`

Get summary of all sublots


**반환값:**
- Summary dict

*소스: engine_modules/inventory_modular/tonbag_mixin.py*

---

### `get_all_tonbags_summary() → Dict`

Alias for get_all_sublots_summary


*소스: engine_modules/inventory_modular/tonbag_mixin.py*

---

### `update_tonbag_location(**lot_no**, **sub_lt**, **location**) → Dict`

Update tonbag location

**파라미터:**
- lot_no: LOT number
- sub_lt: Sub LOT number
- location: New location

**반환값:**
- Result dict

*소스: engine_modules/inventory_modular/tonbag_mixin.py*

---

### `update_tonbag_status(**lot_no**, **sub_lt**, **status**, picked_to=None, pick_ref=None) → Dict`

Update tonbag status

**파라미터:**
- lot_no: LOT number
- sub_lt: Sub LOT number
- status: New status (AVAILABLE, PICKED, SAMPLE)
- picked_to: Customer name (for PICKED status)
- pick_ref: Sale reference (for PICKED status)

**반환값:**
- Result dict

*소스: engine_modules/inventory_modular/tonbag_mixin.py*

---

### `create_tonbags_for_lot(**lot_no**, **count**, **weight_per_bag**, inbound_date=None) → Dict`

Create tonbags for a LOT

**파라미터:**
- lot_no: LOT number
- count: Number of tonbags to create
- weight_per_bag: Weight per tonbag (kg)
- inbound_date: Inbound date

**반환값:**
- Result dict

*소스: engine_modules/inventory_modular/tonbag_mixin.py*

---

### `delete_tonbag(**lot_no**, **sub_lt**) → Dict`

Delete a tonbag (only if AVAILABLE)

**파라미터:**
- lot_no: LOT number
- sub_lt: Sub LOT number

**반환값:**
- Result dict

*소스: engine_modules/inventory_modular/tonbag_mixin.py*

---

## CRUD

### `add_inventory(**lot_no**, sap_no=None, bl_no=None, container_no=None, product=None, product_code=None, mxbg_pallet=20, net_weight=10000, warehouse='GY', arrival_date=None, stock_date=None, **kwargs**) → Dict`

Add single LOT inventory

**파라미터:**
- lot_no: LOT number (required)
- sap_no: SAP number
- bl_no: B/L number
- container_no: Container number
- product: Product name
- product_code: Product code
- mxbg_pallet: Number of tonbags (default 20)
- net_weight: Total weight in kg (default 10000)
- warehouse: Warehouse code (default 'GY')
- arrival_date: Arrival date
- stock_date: Stock date
- **kwargs: Additional fields

**반환값:**
- Result dict with success, lot_no, tonbags_created

*소스: engine_modules/inventory_modular/crud_mixin.py*

---

### `update_inventory(**lot_no**, confirmed=False, **updates**) → Dict`

Update inventory fields

**파라미터:**
- lot_no: LOT number
- confirmed: User confirmation for critical field updates
- **updates: Fields to update (e.g., product='NICKEL', warehouse='GY2')

**반환값:**
- Result dict

*소스: engine_modules/inventory_modular/crud_mixin.py*

---

### `delete_inventory(**lot_no**, force=False, confirmed=False) → Dict`

Delete inventory LOT

**파라미터:**
- lot_no: LOT number
- force: Force delete even if not AVAILABLE (requires confirmed=True)
- confirmed: User confirmation for deletion (required for actual deletion)

**반환값:**
- Result dict

*소스: engine_modules/inventory_modular/crud_mixin.py*

---

### `export_lot_report(**lot_no**, filepath=None) → Dict`

Export LOT detail report to Excel

**파라미터:**
- lot_no: LOT number
- filepath: Output file path (optional)

**반환값:**
- Result dict with filepath

*소스: engine_modules/inventory_modular/crud_mixin.py*

---

## Export

## 반품 (Return)

### `process_return(**return_data**) → Dict`

Process return - change tonbag status from PICKED to AVAILABLE

**파라미터:**
- return_data: List of return items
- [{'lot_no': '...', 'sub_lt': 1, 'reason': '...', 'remark': '...'}, ...]

**반환값:**
- Processing result dict

*소스: engine_modules/inventory_modular/return_mixin.py*

---

## 선적 (Shipment)

### `parse_documents_for_preview(**packing_list_path**, invoice_path=None, bl_path=None, do_path=None) → Dict`

Parse documents for preview (no save)

**파라미터:**
- packing_list_path: Packing List PDF path (required)
- invoice_path: Invoice PDF path (optional)
- bl_path: B/L PDF path (optional)
- do_path: D/O PDF path (optional)

**반환값:**
- Preview result dict

*소스: engine_modules/inventory_modular/shipment_mixin.py*

---

### `process_shipment_documents(**pdf_files**, progress_callback=None) → Dict`

Process multiple PDF documents as a shipment

**파라미터:**
- pdf_files: List of PDF file paths
- progress_callback: Progress callback (pct, msg) -> None

**반환값:**
- Processing result dict

*소스: engine_modules/inventory_modular/shipment_mixin.py*

---

## Import

### `import_from_excel(**excel_path**, on_progress=None, auto_backup=True) → Dict`

Import inventory data from Excel file

**파라미터:**
- excel_path: Excel file path
- on_progress: Progress callback (current, total)
- auto_backup: Create backup before import

**반환값:**
- Import result dict

*소스: engine_modules/inventory_modular/import_mixin.py*

---

## 검증 (Validation)

## 데이터 모델

| 모델 | 설명 | 소스 |
|------|------|------|
| InvoiceData | 상업송장 파싱 결과 | parsers/document_models.py |
| PackingListData | 포장명세서 파싱 결과 | parsers/document_models.py |
| BLData | 선하증권 파싱 결과 | parsers/document_models.py |
| DOData | 화물인도지시서 파싱 결과 | parsers/document_models.py |
| ValidationResult | 검증 결과 | engine_modules/validators.py |
| PreflightResult | Preflight 검증 결과 | preflight.py |

