# SQM 재고관리 시스템 v3.8.4 — API 레퍼런스

> 자동 생성: 2026-02-07 13:28
> 소스: engine_modules/

## 목차

1. [CRUDMixin](#crudmixin)
2. [PreflightMixin](#preflightmixin)
3. [ImportMixin](#importmixin)
4. [ReturnMixin](#returnmixin)
5. [TonbagMixin](#tonbagmixin)
6. [ShipmentMixin](#shipmentmixin)
7. [QueryMixin](#querymixin)
8. [ExportMixin](#exportmixin)
9. [OutboundMixin](#outboundmixin)
10. [InboundMixin](#inboundmixin)
11. [SQMInventoryEngineV3](#sqminventoryenginev3)

---

## CRUDMixin

### `add_inventory(`lot_no`, `sap_no=None`, `bl_no=None`, `container_no=None`, `product=None`, `product_code=None`, `mxbg_pallet=20`, `net_weight=10000`, `warehouse='GY'`, `arrival_date=None`, `stock_date=None`, `kwargs`)` → `typing.Dict`

Add single LOT inventory

**Args:**
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
**Returns:**
- Result dict with success, lot_no, tonbags_created

### `delete_inventory(`lot_no`, `force=False`, `confirmed=False`)` → `typing.Dict`

Delete inventory LOT

**Args:**
- lot_no: LOT number
- force: Force delete even if not AVAILABLE (requires confirmed=True)
- confirmed: User confirmation for deletion (required for actual deletion)
**Returns:**
- Result dict
- Note:
- 데이터 보호 정책에 따라 confirmed=True 없이는 삭제되지 않습니다.

### `export_lot_report(`lot_no`, `filepath=None`)` → `typing.Dict`

Export LOT detail report to Excel

**Args:**
- lot_no: LOT number
- filepath: Output file path (optional)
**Returns:**
- Result dict with filepath

### `update_inventory(`lot_no`, `confirmed=False`, `updates`)` → `typing.Dict`

Update inventory fields

**Args:**
- lot_no: LOT number
- confirmed: User confirmation for critical field updates
- **updates: Fields to update (e.g., product='NICKEL', warehouse='GY2')
**Returns:**
- Result dict
- Note:
- 중요 필드(sap_no, bl_no, net_weight 등) 수정 시 confirmed=True 필요

## PreflightMixin

### `preflight_check_inbound(`data`)` → `PreflightResult`

Preflight validation for inbound data (validation only, no execution)

**Args:**
- data: Data list to validate
**Returns:**
- PreflightResult (no exception even on errors)

### `preflight_check_outbound(`data`)` → `PreflightResult`

Preflight validation for outbound data (validation only, no execution)

**Args:**
- data: Data list to validate
**Returns:**
- PreflightResult (no exception even on errors)

### `process_inbound_safe(`packing_data`, `invoice_data=None`, `bl_data=None`, `do_data=None`)` → `typing.Dict`

Safe inbound processing with preflight validation (All-or-Nothing)

**Args:**
- packing_data: PackingListData or dict
- invoice_data: InvoiceData (optional)
- bl_data: BLData (optional)
- do_data: DOData (optional)
**Returns:**
- Processing result dict
**Raises:**
- PreflightError: On validation failure

### `process_outbound_safe(`allocation_data`, `strict=True`)` → `typing.Dict`

Safe outbound processing with preflight validation (All-or-Nothing)

**Args:**
- allocation_data: Outbound allocation data
- strict: If True, warnings also cause stop
**Returns:**
- Processing result dict
**Raises:**
- PreflightError: On validation failure (causes transaction rollback)

## ImportMixin

### `import_from_excel(`excel_path`, `on_progress=None`, `auto_backup=True`)` → `typing.Dict`

Import inventory data from Excel file

**Args:**
- excel_path: Excel file path
- on_progress: Progress callback (current, total)
- auto_backup: Create backup before import
**Returns:**
- Import result dict

## ReturnMixin

### `bulk_return_by_lot(`lot_no`, `reason=None`)` → `typing.Dict`

Return all PICKED tonbags for a LOT

**Args:**
- lot_no: LOT number
- reason: Return reason
**Returns:**
- Result dict

### `get_return_history(`lot_no=None`, `limit=100`)` → `typing.List[typing.Dict]`

Get return history

**Args:**
- lot_no: Optional filter by LOT number
- limit: Maximum records to return
**Returns:**
- List of return records

### `get_returnable_tonbags(`lot_no=None`)` → `typing.List[typing.Dict]`

Get tonbags that can be returned (status = PICKED)

**Args:**
- lot_no: Optional filter by LOT number
**Returns:**
- List of returnable tonbags

### `process_return(`return_data`)` → `typing.Dict`

Process return - change tonbag status from PICKED to AVAILABLE

**Args:**
- return_data: List of return items
- [{'lot_no': '...', 'sub_lt': 1, 'reason': '...', 'remark': '...'}, ...]
**Returns:**
- Processing result dict

### `return_single_tonbag(`lot_no`, `sub_lt`, `reason=None`, `remark=None`)` → `typing.Dict`

Return a single tonbag

**Args:**
- lot_no: LOT number
- sub_lt: Sub LOT number
- reason: Return reason
- remark: Additional remarks
**Returns:**
- Result dict

## TonbagMixin

### `create_tonbags_for_lot(`lot_no`, `count`, `weight_per_bag`, `inbound_date=None`)` → `typing.Dict`

Create tonbags for a LOT

**Args:**
- lot_no: LOT number
- count: Number of tonbags to create
- weight_per_bag: Weight per tonbag (kg)
- inbound_date: Inbound date
**Returns:**
- Result dict

### `delete_tonbag(`lot_no`, `sub_lt`)` → `typing.Dict`

Delete a tonbag (only if AVAILABLE)

**Args:**
- lot_no: LOT number
- sub_lt: Sub LOT number
**Returns:**
- Result dict

### `get_all_sublots_summary()` → `typing.Dict`

Get summary of all sublots

**Returns:**
- Summary dict

### `get_all_tonbags_summary()` → `typing.Dict`

Alias for get_all_sublots_summary

### `get_tonbag_summary(`lot_no`)` → `typing.Dict`

Get tonbag summary for a LOT

**Args:**
- lot_no: LOT number
**Returns:**
- Summary dict with counts and weights

### `update_tonbag_location(`lot_no`, `sub_lt`, `location`)` → `typing.Dict`

Update tonbag location

**Args:**
- lot_no: LOT number
- sub_lt: Sub LOT number
- location: New location
**Returns:**
- Result dict

### `update_tonbag_status(`lot_no`, `sub_lt`, `status`, `picked_to=None`, `pick_ref=None`)` → `typing.Dict`

Update tonbag status

**Args:**
- lot_no: LOT number
- sub_lt: Sub LOT number
- status: New status (AVAILABLE, PICKED, SAMPLE)
- picked_to: Customer name (for PICKED status)
- pick_ref: Sale reference (for PICKED status)
**Returns:**
- Result dict

## ShipmentMixin

### `get_shipment_list()` → `typing.List[typing.Dict]`

Get shipment list

**Returns:**
- List of shipment records

### `parse_documents_for_preview(`packing_list_path`, `invoice_path=None`, `bl_path=None`, `do_path=None`)` → `typing.Dict`

Parse documents for preview (no save)

**Args:**
- packing_list_path: Packing List PDF path (required)
- invoice_path: Invoice PDF path (optional)
- bl_path: B/L PDF path (optional)
- do_path: D/O PDF path (optional)
**Returns:**
- Preview result dict

### `process_shipment_documents(`pdf_files`, `progress_callback=None`)` → `typing.Dict`

Process multiple PDF documents as a shipment

**Args:**
- pdf_files: List of PDF file paths
- progress_callback: Progress callback (pct, msg) -> None
**Returns:**
- Processing result dict

## QueryMixin

### `get_all_inventory()` → `typing.List[typing.Dict]`

전체 재고 조회 (inventory_tab 호환)

### `get_all_tonbags()` → `typing.List[typing.Dict]`

전체 톤백 조회 (tonbag_tab 호환)

### `get_inventory(`status=None`, `product=None`, `lot_no=None`)` → `typing.List[typing.Dict]`

재고 목록 조회

### `get_inventory_by_customer()` → `typing.List[typing.Dict]`

고객별 재고 조회 (톤백 기준)

### `get_inventory_by_product()` → `typing.List[typing.Dict]`

제품별 재고 조회

### `get_inventory_summary()` → `typing.Dict`

재고 요약 조회

### `get_lot_detail(`lot_no`)` → `typing.Dict`

LOT 상세 조회

### `get_lot_items(`lot_no`)` → `typing.List[typing.Dict]`

LOT 항목 조회 (톤백 목록)

### `get_sublots(`lot_no=None`, `status=None`)` → `typing.List[typing.Dict]`

Sub LOT 조회 (inventory_tonbag 기반 그룹 집계)

### `get_tonbags(`lot_no=None`, `status=None`, `sub_lt=None`)` → `typing.List[typing.Dict]`

톤백 조회

### `search_lots(`keyword=None`, `filters`)` → `typing.List[typing.Dict]`

LOT 검색

## ExportMixin

### `export_to_excel(`output_path`, `option=1`)` → `<class 'str'>`

엑셀 내보내기

**Args:**
- output_path: 출력 파일 경로
- option: 내보내기 옵션
- 1: 기본 재고 목록
- 2: 상세 재고
- 3: Ruby 포맷
- 4: 톤백 목록
- 5: LOT-톤백 리포트
- 6: 전체 재고
**Returns:**
- 출력 파일 경로

## OutboundMixin

### `cancel_outbound_bulk(`items`)` → `typing.Dict`

일괄 출고 취소 (All-or-Nothing)

### `cancel_outbound_tonbag(`lot_no`, `sub_lt`)` → `typing.Dict`

출고 취소: 톤백 PICKED → AVAILABLE + inventory.current_weight 복구

### `pick_tonbags(`lot_no`, `count`, `customer=None`, `sub_lot_no=None`)` → `typing.Dict`

톤백 피킹

**Args:**
- lot_no: LOT 번호
- count: 피킹할 톤백 수량
- customer: 고객명
- sub_lot_no: Sub LOT 번호 (선택)
**Returns:**
- dict: {success, message, picked_tonbags, total_weight_kg, errors}

### `process_outbound(`allocation_data`)` → `typing.Dict`

출고 처리 (v3.8.4: All-or-Nothing + 톤백 동기화)

## InboundMixin

### `process_inbound(`packing_data`, `invoice_data=None`, `bl_data=None`, `do_data=None`)` → `typing.Dict`

입고 처리

**Args:**
- packing_data: 패킹 리스트 데이터 (dict 또는 PackingData)
- invoice_data: 인보이스 데이터 (선택)
- bl_data: B/L 데이터 (선택)
- do_data: D/O 데이터 (선택)
**Returns:**
- dict: {success, message, lot_no, created_lots, created_tonbags, errors, warnings}

## SQMInventoryEngineV3

### `close()` → `None`

Close engine

### `get_connection()` → `typing.Any`

Get database connection (SQLite 호환)

**Returns:**
- sqlite3.Connection or equivalent

### `get_statistics()` → `typing.Dict[str, typing.Any]`

Get overall statistics

**Returns:**
- Statistics dict

### `health_check()` → `typing.Dict[str, typing.Any]`

Check system health

**Returns:**
- Health status dict

### `preflight_check_inbound(`data`)` → `PreflightResult`

입고 데이터 Preflight 검증 (실행 전 검증만)

**Args:**
- data: 검증할 데이터 리스트
**Returns:**
- PreflightResult: 검증 결과 (오류 있어도 예외 없음)

### `preflight_check_outbound(`data`)` → `PreflightResult`

출고 데이터 Preflight 검증 (실행 전 검증만)

**Args:**
- data: 검증할 데이터 리스트
**Returns:**
- PreflightResult: 검증 결과 (오류 있어도 예외 없음)

### `process_inbound_safe(`packing_data`, `invoice_data=None`, `bl_data=None`, `do_data=None`)` → `typing.Dict`

입고 처리 - Preflight 검증 적용 (All-or-Nothing)

**Args:**
- packing_data: PackingListData 객체
- invoice_data: InvoiceData 객체 (선택)
- bl_data: BLData 객체 (선택)
- do_data: DOData 객체 (선택)
**Returns:**
- 처리 결과 딕셔너리
**Raises:**
- PreflightError: 검증 실패 시

### `process_outbound_safe(`allocation_data`, `strict=True`)` → `typing.Dict`

출고 처리 - Preflight 검증 적용 (All-or-Nothing)

**Args:**
- allocation_data: 출고 배정 데이터
- strict: True면 WARNING도 중단 (기본: True)
**Returns:**
- 처리 결과 딕셔너리
**Raises:**
- PreflightError: 검증 실패 시 (strict=True이고 오류 있을 때)

---

## 성능 벤치마크

| 항목 | 결과 |
|------|------|
| 엔진 초기화 | 40.5ms |
| 입고 (100건) | 1.6ms/건 |
| 재고 전체조회 | 0.8ms/회 |
| LOT 검색 | 1.4ms/회 |
| 출고 (pick) | 0.6ms/건 |
| 톤백 전체조회 | 4.5ms/회 |
| 요약 조회 | <0.1ms/회 |
| DB 크기 (100 LOT) | 540KB |

## 품질 지표

| 항목 | 수치 |
|------|------|
| 테스트 커버리지 | 90.2% |
| 테스트 케이스 | 1,934 passed / 0 failed |
| 타입힌트 | 98.7% |
| docstring | 100% |
| bare except | 0건 |
| MRO 데드코드 | 0건 |