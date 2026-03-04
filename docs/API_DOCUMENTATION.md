# SQM Inventory Management System - API Documentation

## Version: 2.9.41
## Last Updated: 2026-01-17

---

## 📚 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Core Classes](#core-classes)
4. [Inbound Operations](#inbound-operations)
5. [Outbound Operations](#outbound-operations)
6. [Inventory Queries](#inventory-queries)
7. [Export Functions](#export-functions)
8. [Error Handling](#error-handling)
9. [Examples](#examples)

---

## Overview

SQM Inventory Management System은 리튬 화합물 재고 관리를 위한 통합 솔루션입니다.

### Key Features
- **입고 처리**: PDF/Excel 문서 파싱, LOT 등록, 톤백 관리
- **출고 처리**: 배분 처리, 잔량 추적, 상태 관리
- **재고 조회**: 다양한 필터, 요약, 제품별 그룹핑
- **리포트**: 6가지 Excel 양식, PDF 블록 리포트

### Architecture
```
┌─────────────────────────────────────────────────────┐
│                   GUI (gui_app.py)                   │
├─────────────────────────────────────────────────────┤
│                Services Layer                        │
│  (InboundService, OutboundService, InventoryService) │
├─────────────────────────────────────────────────────┤
│                 Engine (engine.py)                   │
│              SQMInventoryEngine                      │
├─────────────────────────────────────────────────────┤
│              Database (SQLite)                       │
│  inventory | tonbag | outbound | stock_movement      │
└─────────────────────────────────────────────────────┘
```

---

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd sqm_inventory

# Install dependencies
pip install -r requirements.txt

# Run GUI
python gui_app.py
```

### Basic Usage

```python
from engine import SQMInventoryEngine

# Initialize
engine = SQMInventoryEngine('inventory.db')

# Process inbound
result = engine.process_inbound({
    'sap_no': '2200001234',
    'bl_no': 'BLEXAMPLE01',
    'product': 'LITHIUM CARBONATE',
    'lots': [
        {'lot_no': '1120000001', 'net_weight': 5000.0, 'bag_count': 5}
    ]
})

# Query inventory
inventory = engine.get_inventory()
summary = engine.get_inventory_summary()

# Process outbound
engine.process_outbound([
    {'lot_no': '1120000001', 'qty_mt': 1.0, 'sold_to': 'CUSTOMER_A'}
])

# Export to Excel
engine.export_to_excel('report.xlsx', option=3)
```

---

## Core Classes

### SQMInventoryEngine

Main engine class for all inventory operations.

```python
class SQMInventoryEngine:
    def __init__(self, db_path: str = 'sqm_inventory.db')
```

**Parameters:**
- `db_path` (str): Path to SQLite database file

**Attributes:**
- `db`: Database connection wrapper
- `validators`: Validation modules

---

## Inbound Operations

### process_inbound()

Process inbound shipment and create inventory records.

```python
def process_inbound(self, packing_data: dict) -> dict
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sap_no` | str | Yes | SAP document number |
| `bl_no` | str | No | Bill of Lading number |
| `product` | str | No | Product name |
| `product_code` | str | No | Product code |
| `customer` | str | No | Customer name |
| `lots` | list[dict] | Yes | List of LOT data |

**LOT Data Structure:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lot_no` | str | Yes | LOT number (10-20 chars) |
| `net_weight` | float | Yes | Net weight in kg |
| `bag_count` | int | No | Number of bags |
| `container_no` | str | No | Container number |
| `gross_weight` | float | No | Gross weight in kg |

**Returns:**

```python
{
    'success': bool,          # True if successful
    'lots_created': int,      # Number of LOTs created
    'lots_skipped': int,      # Number of LOTs skipped
    'shipment_id': int,       # Created shipment ID
    'errors': list[str],      # Error messages
    'warnings': list[str]     # Warning messages
}
```

**Example:**

```python
result = engine.process_inbound({
    'sap_no': '2200001234',
    'bl_no': 'BLMSCUGNP123',
    'product': 'LITHIUM CARBONATE',
    'product_code': 'LC001',
    'lots': [
        {
            'lot_no': '1120000001',
            'net_weight': 5000.0,
            'bag_count': 5,
            'container_no': 'MSKU1234567'
        },
        {
            'lot_no': '1120000002',
            'net_weight': 4500.0,
            'bag_count': 5,
            'container_no': 'MSKU1234568'
        }
    ]
})

if result['success']:
    print(f"Created {result['lots_created']} LOTs")
else:
    print(f"Errors: {result['errors']}")
```

**Validation Rules:**
- SAP NO must be unique
- LOT NO must be 10-20 characters
- Net weight must be > 0
- All-or-Nothing: If any LOT fails, entire inbound is rejected

---

## Outbound Operations

### process_outbound()

Process outbound allocations and update inventory.

```python
def process_outbound(self, outbound_data: list[dict]) -> dict
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lot_no` | str | Yes | LOT number |
| `qty_mt` | float | Yes | Quantity in MT |
| `sold_to` | str | No | Customer/destination |
| `outbound_date` | str | No | Outbound date |

**Returns:**

```python
{
    'success': bool,
    'lots_processed': int,
    'total_picked': float,      # Total MT picked
    'lots_not_found': int,
    'warnings': list[str],
    'errors': list[str]
}
```

**Example:**

```python
result = engine.process_outbound([
    {'lot_no': '1120000001', 'qty_mt': 1.5, 'sold_to': 'CUSTOMER_A'},
    {'lot_no': '1120000002', 'qty_mt': 2.0, 'sold_to': 'CUSTOMER_B'}
])

print(f"Picked: {result['total_picked']} MT")
```

**Status Changes:**
- `AVAILABLE` → `PARTIAL`: After partial outbound
- `PARTIAL` → `DEPLETED`: When current_weight = 0

---

## Inventory Queries

### get_inventory()

Retrieve all inventory records.

```python
def get_inventory(self, status: str = None) -> list[dict]
```

**Returns:** List of inventory dictionaries

```python
[
    {
        'id': 1,
        'lot_no': '1120000001',
        'sap_no': '2200001234',
        'bl_no': 'BLEXAMPLE01',
        'product': 'LITHIUM CARBONATE',
        'initial_weight': 5000.0,
        'current_weight': 4000.0,
        'status': 'PARTIAL'
    },
    ...
]
```

### get_inventory_summary()

Get inventory summary statistics.

```python
def get_inventory_summary(self) -> dict
```

**Returns:**

```python
{
    'total_lots': 10,
    'total_initial_mt': 50.0,
    'total_current_mt': 45.5,
    'total_outbound_mt': 4.5
}
```

### get_inventory_by_product()

Get inventory grouped by product.

```python
def get_inventory_by_product(self) -> list[dict]
```

### get_tonbags()

Get all tonbag (Sub LOT) records.

```python
def get_tonbags(self, lot_no: str = None) -> list[dict]
```

---

## Export Functions

### export_to_excel()

Export inventory to Excel file.

```python
def export_to_excel(self, filepath: str, option: int = 1) -> None
```

**Options:**

| Option | Description |
|--------|-------------|
| 1 | Basic format |
| 2 | Detailed format |
| 3 | Rubylee format |
| 4 | Tonbag format |
| 5 | LOT + Tonbag report |
| 6 | Unified format |

**Example:**

```python
# Export with Rubylee format
engine.export_to_excel('inventory_report.xlsx', option=3)
```

---

## Error Handling

### ValidationResult

```python
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
```

### Common Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `DUPLICATE_SAP` | SAP NO already exists | Use unique SAP NO |
| `EMPTY_LOT_NO` | LOT number is empty | Provide valid LOT NO |
| `INVALID_WEIGHT` | Weight is 0 or negative | Use positive weight |
| `LOT_TOO_LONG` | LOT NO exceeds 20 chars | Shorten LOT NO |

### Error Handling Example

```python
result = engine.process_inbound(data)

if not result['success']:
    for error in result['errors']:
        print(f"Error: {error}")
    for warning in result.get('warnings', []):
        print(f"Warning: {warning}")
```

---

## Examples

### Complete Workflow

```python
from engine import SQMInventoryEngine

# 1. Initialize
engine = SQMInventoryEngine('production.db')

# 2. Inbound
inbound_result = engine.process_inbound({
    'sap_no': '2200001234',
    'bl_no': 'BLMSCUGNP123',
    'product': 'LITHIUM CARBONATE',
    'lots': [
        {'lot_no': '1120000001', 'net_weight': 10000.0, 'bag_count': 10},
        {'lot_no': '1120000002', 'net_weight': 8000.0, 'bag_count': 8}
    ]
})

print(f"Inbound: {inbound_result['lots_created']} LOTs created")

# 3. Check inventory
summary = engine.get_inventory_summary()
print(f"Total: {summary['total_current_mt']} MT")

# 4. Outbound
outbound_result = engine.process_outbound([
    {'lot_no': '1120000001', 'qty_mt': 2.0, 'sold_to': 'CUSTOMER_A'}
])

print(f"Outbound: {outbound_result['total_picked']} MT")

# 5. Export report
engine.export_to_excel('daily_report.xlsx', option=3)

# 6. Cleanup
engine.db.close()
```

### Batch Processing

```python
# Process multiple SAP numbers
sap_numbers = ['2200001', '2200002', '2200003']

for sap_no in sap_numbers:
    data = load_packing_data(sap_no)
    result = engine.process_inbound(data)
    
    if result['success']:
        print(f"✅ {sap_no}: {result['lots_created']} LOTs")
    else:
        print(f"❌ {sap_no}: {result['errors']}")
```

---

## Support

- **Version**: 2.9.41
- **Maintainer**: Rubylee (남기동)
- **License**: Proprietary

For issues or questions, contact the development team.
