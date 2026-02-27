# SQM Inventory Management System - API Reference v3.1

> **완전한 API 레퍼런스** - 모든 공개 API와 사용 예제

---

## 목차

1. [개요](#1-개요)
2. [빠른 시작](#2-빠른-시작)
3. [핵심 모듈](#3-핵심-모듈)
4. [InventoryEngine API](#4-inventoryengine-api)
5. [Database API](#5-database-api)
6. [Parser API](#6-parser-api)
7. [Validation API](#7-validation-api)
8. [UI Helper API](#8-ui-helper-api)
9. [OCR Tuner API](#9-ocr-tuner-api)
10. [Tonbag Integrity API](#10-tonbag-integrity-api)
11. [Dashboard Provider API](#11-dashboard-provider-api)
12. [통합 예제](#12-통합-예제)
13. [에러 처리](#13-에러-처리)
14. [성능 최적화](#14-성능-최적화)
15. [마이그레이션 가이드](#15-마이그레이션-가이드)

---

## 1. 개요

### 1.1 시스템 소개

SQM Inventory Management System v3.1은 리튬카보네이트(Lithium Carbonate)와 
니켈설페이트(Nickel Sulfate) 재고 관리를 위한 종합 시스템입니다.

### 1.2 핵심 원칙

| 원칙 | 설명 |
|------|------|
| **All-or-Nothing** | 트랜잭션 중 오류 발생 시 전체 롤백 |
| **Preflight 검증** | 실제 처리 전 시뮬레이션으로 오류 예방 |
| **톤백 전량 출고** | 톤백은 부분 출고 불가, 전량만 출고 |
| **데이터 무결성** | inventory ↔ tonbag 합계 항상 일치 |

### 1.3 아키텍처 개요

```
┌─────────────────────────────────────────────────────────┐
│                      GUI Layer                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ gui_app_modular/ (main_app.py + mixins + tabs)  │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                    Helper Layer                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ UIOperations │ │ OCRAutoTuner │ │ Dashboard    │    │
│  │ Helper       │ │              │ │ Provider     │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
├─────────────────────────────────────────────────────────┤
│                   Business Layer                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ InventoryEngine (Facade)                        │   │
│  │  ├── InboundMixin                               │   │
│  │  ├── OutboundMixin                              │   │
│  │  ├── QueryMixin                                 │   │
│  │  ├── TonbagMixin                                │   │
│  │  └── ExportMixin                                │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                  Validation Layer                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ Preflight    │ │ Strict       │ │ Tonbag       │    │
│  │ Validator    │ │ Validator    │ │ Integrity    │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
├─────────────────────────────────────────────────────────┤
│                    Data Layer                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ DatabaseConnection (SQLite + WAL mode)          │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 빠른 시작

### 2.1 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# 필수 패키지
pip install openpyxl pandas ttkbootstrap reportlab
pip install google-generativeai  # Gemini API 사용 시
```

### 2.2 기본 사용법

```python
from engine_modules.inventory_modular import InventoryEngine

# 1. 엔진 초기화
engine = InventoryEngine(db_path="./data/db/sqm_inventory.db")

# 2. 재고 조회
inventory = engine.get_all_inventory()
print(f"총 {len(inventory)}개 LOT")

# 3. 입고 처리
result = engine.process_inbound({
    'lot_no': '2025-LC-001',
    'product_name': 'Lithium Carbonate',
    'initial_weight': 10000,  # kg
    'arrival_date': '2025-01-25',
    'tonbag_count': 20
})

if result['success']:
    print(f"입고 완료: {result['lot_no']}")
else:
    print(f"입고 실패: {result['errors']}")

# 4. 출고 처리 (Preflight 포함)
result = engine.process_outbound({
    'lot_no': '2025-LC-001',
    'outbound_weight': 2500,  # kg
    'customer': 'POSCO',
    'outbound_date': '2025-01-26'
})

# 5. 종료
engine.close()
```

---

## 3. 핵심 모듈

### 3.1 모듈 맵

| 모듈 | 파일 위치 | 설명 |
|------|----------|------|
| `InventoryEngine` | `engine_modules/inventory_modular/engine.py` | 재고 관리 Facade |
| `DatabaseConnection` | `engine_modules/database.py` | DB 연결 관리 |
| `GeminiDocumentParser` | `gemini_parser.py` | AI 문서 파싱 |
| `PreflightValidator` | `preflight.py` | 사전 검증 |
| `StrictValidator` | `strict_validator.py` | 엄격한 데이터 검증 |
| `TonbagIntegrityValidator` | `tonbag_integrity.py` | 톤백 무결성 검증 |
| `OCRAutoTuner` | `ocr_auto_tuner.py` | OCR 동시성 자동 조절 |
| `UIOperationsHelper` | `ui_ops_helper.py` | UI 운영 편의 기능 |
| `DashboardProvider` | `dashboard_provider.py` | 대시보드 데이터 제공 |

### 3.2 Import 예제

```python
# 핵심 엔진
from engine_modules.inventory_modular import InventoryEngine

# 검증
from preflight import PreflightValidator
from strict_validator import StrictValidator
from tonbag_integrity import TonbagIntegrityValidator

# 파서
from gemini_parser import GeminiDocumentParser
from parsers import DocumentParserV2

# 헬퍼
from ui_ops_helper import UIOperationsHelper, ErrorDialog, SmoothProgress
from ocr_auto_tuner import OCRAutoTuner, get_ocr_tuner
from dashboard_provider import DashboardProvider
```

---

## 4. InventoryEngine API

### 4.1 초기화

```python
from engine_modules.inventory_modular import InventoryEngine

engine = InventoryEngine(
    db_path: str = None,           # DB 경로 (기본: ./data/db/sqm_inventory.db)
    auto_backup: bool = True,      # 자동 백업 활성화
    enable_logging: bool = True    # 로깅 활성화
)
```

### 4.2 재고 조회 메서드

#### get_all_inventory()

```python
inventory_list = engine.get_all_inventory()

# 반환값: List[Dict]
# [
#     {
#         'id': 1,
#         'lot_no': '2025-LC-001',
#         'product_name': 'Lithium Carbonate',
#         'initial_weight': 10000.0,
#         'current_weight': 7500.0,
#         'arrival_date': '2025-01-15',
#         'status': 'AVAILABLE',
#         'tonbag_count': 20,
#         'available_tonbags': 15,
#         'created_at': '2025-01-15 10:00:00'
#     },
#     ...
# ]
```

#### get_lot_info(lot_no)

```python
lot = engine.get_lot_info("2025-LC-001")

# 반환값: Dict | None
# {
#     'lot_no': '2025-LC-001',
#     'product_name': 'Lithium Carbonate',
#     'initial_weight': 10000.0,
#     'current_weight': 7500.0,
#     'arrival_date': '2025-01-15',
#     'status': 'AVAILABLE',
#     'tonbags': [
#         {'tonbag_id': '2025-LC-001-01', 'weight': 500, 'status': 'AVAILABLE'},
#         {'tonbag_id': '2025-LC-001-02', 'weight': 500, 'status': 'SOLD'},
#         ...
#     ]
# }
```

#### get_inventory_summary()

```python
summary = engine.get_inventory_summary()

# 반환값: Dict
# {
#     'total_lots': 45,
#     'total_weight_kg': 225000.0,
#     'total_weight_mt': 225.0,
#     'by_product': {
#         'Lithium Carbonate': 150000.0,
#         'Nickel Sulfate': 75000.0
#     },
#     'by_status': {
#         'AVAILABLE': 40,
#         'PARTIAL': 3,
#         'DEPLETED': 2
#     },
#     'total_tonbags': 450,
#     'available_tonbags': 380
# }
```

#### search_inventory(query, filters)

```python
# 검색 (다양한 필터 지원)
results = engine.search_inventory(
    query="LC-001",                    # 텍스트 검색
    filters={
        'product': 'Lithium Carbonate',
        'status': 'AVAILABLE',
        'date_from': '2025-01-01',
        'date_to': '2025-01-31',
        'weight_min': 1000,
        'weight_max': 10000
    }
)

# 반환값: List[Dict]
```

### 4.3 입고 처리 메서드

#### process_inbound(data)

```python
result = engine.process_inbound({
    # 필수 필드
    'lot_no': '2025-LC-001',              # LOT 번호
    'product_name': 'Lithium Carbonate',  # 제품명
    'initial_weight': 10000,              # 초기 중량 (kg)
    'arrival_date': '2025-01-25',         # 입고일
    
    # 선택 필드
    'tonbag_count': 20,                   # 톤백 수량 (기본: 자동 계산)
    'tonbag_weight': 500,                 # 개별 톤백 중량 (기본: 500kg)
    'supplier': 'SQM Chile',              # 공급사
    'warehouse': '창고A',                 # 창고
    'container_no': 'MSKU1234567',        # 컨테이너 번호
    'bl_no': 'MAEU2500001234',            # B/L 번호
    'sap_no': 'SAP202500001',             # SAP 번호
    'notes': '비고 내용'                  # 비고
})

# 반환값: Dict
# {
#     'success': True,
#     'lot_no': '2025-LC-001',
#     'message': '입고 완료: 20개 톤백 생성',
#     'tonbags_created': 20,
#     'total_weight': 10000.0,
#     'errors': [],
#     'warnings': []
# }
```

#### process_inbound_batch(data_list)

```python
# 여러 LOT 일괄 입고
results = engine.process_inbound_batch([
    {'lot_no': '2025-LC-001', 'product_name': 'LC', 'initial_weight': 10000, ...},
    {'lot_no': '2025-LC-002', 'product_name': 'LC', 'initial_weight': 8000, ...},
])

# 반환값: Dict
# {
#     'success': True,          # 전체 성공 여부
#     'total_count': 2,
#     'success_count': 2,
#     'failed_count': 0,
#     'results': [...]          # 개별 결과
# }
```

### 4.4 출고 처리 메서드

#### preflight_outbound(data)

```python
# 출고 전 사전 검증 (DB 변경 없음)
preflight = engine.preflight_outbound({
    'lot_no': '2025-LC-001',
    'outbound_weight': 2500,
    'customer': 'POSCO'
})

# 반환값: Dict
# {
#     'valid': True,
#     'errors': [],
#     'warnings': ['5개 톤백 중 일부만 출고됩니다'],
#     'simulation': {
#         'lot_no': '2025-LC-001',
#         'current_weight': 10000,
#         'outbound_weight': 2500,
#         'remaining_weight': 7500,
#         'tonbags_to_sell': 5,
#         'selected_tonbags': ['2025-LC-001-01', '2025-LC-001-02', ...]
#     }
# }
```

#### process_outbound(data)

```python
result = engine.process_outbound({
    # 필수 필드
    'lot_no': '2025-LC-001',
    'outbound_weight': 2500,           # kg
    'outbound_date': '2025-01-26',
    
    # 선택 필드
    'customer': 'POSCO',               # 고객사
    'destination': '포항 본사',        # 목적지
    'vehicle_no': '12가3456',          # 차량번호
    'sale_reference': 'SO-2025-001',   # 판매 참조번호
    'notes': '비고'
})

# 반환값: Dict
# {
#     'success': True,
#     'lot_no': '2025-LC-001',
#     'outbound_weight': 2500.0,
#     'remaining_weight': 7500.0,
#     'tonbags_sold': 5,
#     'sold_tonbags': ['2025-LC-001-01', ...],
#     'message': '출고 완료',
#     'errors': [],
#     'warnings': []
# }
```

#### process_outbound_batch(data_list)

```python
# 여러 LOT 일괄 출고 (All-or-Nothing)
results = engine.process_outbound_batch([
    {'lot_no': '2025-LC-001', 'outbound_weight': 2500, ...},
    {'lot_no': '2025-LC-002', 'outbound_weight': 3000, ...},
])

# 하나라도 실패하면 전체 롤백
```

### 4.5 톤백 관리 메서드

#### get_tonbags_by_lot(lot_no)

```python
tonbags = engine.get_tonbags_by_lot("2025-LC-001")

# 반환값: List[Dict]
# [
#     {
#         'tonbag_id': '2025-LC-001-01',
#         'lot_no': '2025-LC-001',
#         'sub_lot': 1,
#         'weight': 500.0,
#         'status': 'AVAILABLE',
#         'location': 'A-01-01',
#         'sold_to': None
#     },
#     ...
# ]
```

#### get_available_tonbags(lot_no)

```python
# AVAILABLE 상태 톤백만 조회
available = engine.get_available_tonbags("2025-LC-001")
```

#### update_tonbag_location(tonbag_id, location)

```python
engine.update_tonbag_location("2025-LC-001-01", "B-02-03")
```

### 4.6 내보내기 메서드

#### export_to_excel(filepath, format_type)

```python
# Excel 내보내기
engine.export_to_excel(
    filepath="./output/inventory_2025.xlsx",
    format_type=6  # 통합 재고현황
)

# format_type:
# 1 = 기존 양식 (통관요청)
# 3 = 루비리 양식 (18컬럼)
# 4 = 톤백 현황 (Sub LOT)
# 6 = 통합 재고현황 (LOT + 톤백) ★추천
```

### 4.7 유틸리티 메서드

```python
# DB 최적화
engine.optimize_database()

# 무결성 검사
result = engine.check_integrity()

# 백업 생성
backup_path = engine.create_backup()

# 백업 복원
engine.restore_from_backup(backup_path)

# 연결 종료
engine.close()
```

---

## 5. Database API

### 5.1 DatabaseConnection

```python
from engine_modules.database import DatabaseConnection

# 컨텍스트 매니저 사용 (권장)
with DatabaseConnection(db_path) as db:
    # 조회
    rows = db.fetchall("SELECT * FROM inventory WHERE status = ?", ('AVAILABLE',))
    
    # 단일 조회
    row = db.fetchone("SELECT * FROM inventory WHERE lot_no = ?", (lot_no,))
    
    # 실행
    db.execute("UPDATE inventory SET status = ? WHERE lot_no = ?", ('SOLD', lot_no))
    
    # 커밋
    db.commit()
```

### 5.2 트랜잭션 관리

```python
with DatabaseConnection(db_path) as db:
    try:
        db.execute("INSERT INTO inventory ...")
        db.execute("INSERT INTO inventory_tonbag ...")
        db.execute("INSERT INTO inbound_history ...")
        db.commit()  # 모두 성공 시
    except Exception as e:
        db.rollback()  # 하나라도 실패 시 전체 롤백
        raise
```

### 5.3 스키마

```sql
-- 재고 테이블
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_no TEXT UNIQUE NOT NULL,
    sap_no TEXT,
    bl_no TEXT,
    container_no TEXT,
    product_name TEXT NOT NULL,
    initial_weight REAL NOT NULL,
    current_weight REAL NOT NULL,
    arrival_date TEXT,
    stock_date TEXT,
    warehouse TEXT,
    supplier TEXT,
    status TEXT DEFAULT 'AVAILABLE',
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 톤백 테이블
CREATE TABLE inventory_tonbag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tonbag_id TEXT UNIQUE NOT NULL,
    inventory_id INTEGER,
    lot_no TEXT NOT NULL,
    sub_lot INTEGER NOT NULL,
    weight REAL DEFAULT 500,
    status TEXT DEFAULT 'AVAILABLE',
    location TEXT,
    sold_to TEXT,
    sold_date TEXT,
    sale_reference TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(lot_no, sub_lot),
    FOREIGN KEY (lot_no) REFERENCES inventory(lot_no)
);

-- 출고 이력
CREATE TABLE outbound_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_no TEXT NOT NULL,
    tonbag_id TEXT,
    outbound_weight REAL NOT NULL,
    outbound_date TEXT,
    customer TEXT,
    destination TEXT,
    vehicle_no TEXT,
    sale_reference TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 입고 이력
CREATE TABLE inbound_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_no TEXT NOT NULL,
    product_name TEXT,
    weight REAL NOT NULL,
    tonbag_count INTEGER,
    arrival_date TEXT,
    supplier TEXT,
    container_no TEXT,
    bl_no TEXT,
    sap_no TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Parser API

### 6.1 GeminiDocumentParser

```python
from gemini_parser import GeminiDocumentParser

parser = GeminiDocumentParser(
    api_key="your-gemini-api-key",   # 필수
    model="gemini-1.5-flash",        # 모델
    timeout_seconds=60,              # 타임아웃
    max_retries=3                    # 재시도 횟수
)
```

#### parse_packing_list()

```python
result = parser.parse_packing_list("packing_list.pdf")

# 반환값
# {
#     'success': True,
#     'document_type': 'PACKING_LIST',
#     'lot_numbers': ['1125080001', '1125080002'],
#     'weights': [7500.0, 8000.0],
#     'total_weight': 15500.0,
#     'bag_count': 31,
#     'container_no': 'MSKU1234567',
#     'raw_response': '...'
# }
```

#### parse_invoice()

```python
result = parser.parse_invoice("invoice.pdf")

# 반환값
# {
#     'success': True,
#     'document_type': 'INVOICE',
#     'invoice_no': 'INV-2025-001',
#     'total_amount': 50000.0,
#     'currency': 'USD',
#     'items': [
#         {'description': 'Lithium Carbonate', 'quantity': 10, 'unit_price': 5000}
#     ]
# }
```

#### parse_bl()

```python
result = parser.parse_bl("bl.pdf")

# 반환값
# {
#     'success': True,
#     'document_type': 'BL',
#     'bl_no': 'MAEU2500001234',
#     'vessel_name': 'EVER GIVEN',
#     'port_of_loading': 'ANTOFAGASTA',
#     'port_of_discharge': 'BUSAN',
#     'containers': ['MSKU1234567', 'MSKU7654321']
# }
```

#### parse_do()

```python
result = parser.parse_do("do.pdf")

# 반환값
# {
#     'success': True,
#     'document_type': 'DO',
#     'do_no': 'DO-2025-001',
#     'arrival_date': '2025-01-25',
#     'release_date': '2025-01-26'
# }
```

#### parse_auto() - 자동 감지

```python
result = parser.parse_auto("unknown_document.pdf")

# 문서 타입 자동 감지 후 적절한 파서 호출
# 반환값에 'document_type' 포함
```

### 6.2 DocumentParserV2 (로컬 파싱)

```python
from parsers import DocumentParserV2

parser = DocumentParserV2()

# PDF 분석
analysis = parser.analyze_pdf("document.pdf")
# {
#     'page_count': 3,
#     'is_text_pdf': True,
#     'is_image_pdf': False,
#     'detected_type': 'PACKING_LIST',
#     'confidence': 85
# }

# 텍스트 추출
text = parser.extract_text("document.pdf")
```

---

## 7. Validation API

### 7.1 PreflightValidator

```python
from preflight import PreflightValidator

validator = PreflightValidator(engine)

# 단일 출고 검증
result = validator.validate_outbound({
    'lot_no': '2025-LC-001',
    'outbound_weight': 2500
})

# 반환값
# {
#     'valid': True,
#     'errors': [],
#     'warnings': ['출고 후 잔량이 30% 미만입니다'],
#     'simulation': {...}
# }

# 배치 검증
results = validator.validate_batch([
    {'lot_no': '2025-LC-001', 'outbound_weight': 2500},
    {'lot_no': '2025-LC-002', 'outbound_weight': 3000},
])
```

### 7.2 StrictValidator

```python
from strict_validator import StrictValidator

validator = StrictValidator()

# LOT 번호 검증
try:
    validator.validate_lot_no("2025-LC-001")  # OK
    validator.validate_lot_no("")              # raises ValidationError
except ValidationError as e:
    print(f"검증 실패: {e}")

# 중량 검증
validator.validate_weight(1000.0)   # OK
validator.validate_weight(-100)     # raises ValidationError
validator.validate_weight(0)        # raises ValidationError

# 날짜 검증
validator.validate_date("2025-01-25")    # OK
validator.validate_date("25-01-2025")    # raises ValidationError
validator.validate_date("invalid")       # raises ValidationError

# 복합 검증
validator.validate_inbound_data({
    'lot_no': '2025-LC-001',
    'product_name': 'Lithium Carbonate',
    'initial_weight': 10000,
    'arrival_date': '2025-01-25'
})
```

### 7.3 ValidationError

```python
from strict_validator import ValidationError

try:
    validator.validate_weight(-100)
except ValidationError as e:
    print(f"에러 코드: {e.code}")      # E004
    print(f"에러 메시지: {e.message}") # 중량은 양수여야 합니다
    print(f"필드: {e.field}")          # weight
```

---

## 8. UI Helper API

### 8.1 UIOperationsHelper

```python
from ui_ops_helper import UIOperationsHelper

helper = UIOperationsHelper(
    parent=root,                    # Tkinter root
    progressbar=progress_bar,       # ttk.Progressbar
    progress_label=label,           # ttk.Label (선택)
    log_callback=log_function       # 로그 콜백 (선택)
)
```

#### 에러 다이얼로그

```python
try:
    risky_operation()
except Exception as e:
    helper.show_error(
        message="작업 중 오류 발생",
        exception=e,
        title="오류",
        on_retry=lambda: risky_operation()
    )
```

#### 작업 복구 시스템

```python
# 작업 시작 기록
helper.start_work('inbound', {
    'files': ['file1.pdf', 'file2.pdf'],
    'total_count': 2
})

# 진행률 업데이트
for i, file in enumerate(files):
    process_file(file)
    helper.update_progress(
        progress=(i + 1) / len(files),
        message=f"처리 중: {file}"
    )

# 작업 완료
helper.complete_work({
    'processed': len(files),
    'success': True
})

# 또는 작업 실패
helper.fail_work("파일 처리 실패", exception=e)
```

#### 앱 시작 시 복구 확인

```python
def on_app_start():
    helper.check_recovery(
        on_recover=lambda work: resume_work(work),
        on_discard=lambda: print("미완료 작업 무시됨")
    )
```

### 8.2 SmoothProgress

```python
from ui_ops_helper import SmoothProgress

# 부드러운 진행률 (공유폴더 지연 대응)
progress = SmoothProgress(
    progressbar=progress_bar,
    label=progress_label,
    smoothing=0.15  # 부드러움 정도 (0~1)
)

# 시작
progress.start()

# 진행률 설정 (부드럽게 변화)
for i in range(100):
    progress.set_progress(i / 100, f"{i}% 완료")
    time.sleep(0.1)

# 완료
progress.complete("작업 완료!")

# 리셋
progress.reset()
```

### 8.3 ErrorDialog

```python
from ui_ops_helper import ErrorDialog

# 독립 에러 다이얼로그
ErrorDialog.show(
    parent=root,
    title="오류 발생",
    message="파일을 처리하는 중 오류가 발생했습니다.",
    details="상세 에러 정보:\n" + traceback.format_exc(),
    log_file="./logs/error.log",
    on_retry=retry_function,
    on_copy=lambda: copy_to_clipboard(error_info)
)
```

---

## 9. OCR Tuner API

### 9.1 OCRAutoTuner

```python
from ocr_auto_tuner import OCRAutoTuner, get_ocr_tuner, TunerState

# 전역 인스턴스 사용 (권장)
tuner = get_ocr_tuner()

# 또는 직접 생성
tuner = OCRAutoTuner(
    min_workers=1,               # 최소 동시성
    max_workers=5,               # 최대 동시성
    initial_workers=3,           # 초기 동시성
    cooldown_seconds=30,         # 쿨다운 시간
    circuit_open_seconds=60,     # 서킷 오픈 시간
    on_state_change=callback     # 상태 변경 콜백
)
```

#### OCR 함수 래핑 실행

```python
def ocr_function(image_data):
    # Gemini API 호출 등
    return result

# 자동 튜닝 적용
result = tuner.execute(ocr_function, image_data)
# 429 발생 시 자동으로 동시성 감소
```

#### 상태 및 통계

```python
# 현재 상태
state = tuner.state
# TunerState.NORMAL     - 정상 운영
# TunerState.THROTTLED  - 감속 중
# TunerState.COOLDOWN   - 쿨다운 대기
# TunerState.CIRCUIT_OPEN - 회로 차단

# 권장 동시성
workers = tuner.recommended_workers

# 통계
stats = tuner.get_stats()
# {
#     'state': 'normal',
#     'current_workers': 3,
#     'total_requests': 100,
#     'success_count': 98,
#     'error_count': 2,
#     'success_rate': '98.0%',
#     'avg_response_time': '1.50s',
#     'rate_limited_count': 2,
#     'recent_429_1min': 0
# }

# 리셋
tuner.reset()
```

### 9.2 상태 변경 콜백

```python
def on_tuner_state_change(old_state, new_state, workers):
    print(f"OCR Tuner: {old_state} → {new_state} (workers: {workers})")
    
    if new_state == TunerState.CIRCUIT_OPEN:
        show_warning("API 과부하, 잠시 대기...")

tuner = OCRAutoTuner(on_state_change=on_tuner_state_change)
```

---

## 10. Tonbag Integrity API

### 10.1 TonbagIntegrityValidator

```python
from tonbag_integrity import TonbagIntegrityValidator

validator = TonbagIntegrityValidator(engine)

# 전체 무결성 검증
result = validator.validate()
# {
#     'valid': True,
#     'errors': [],
#     'warnings': ['LOT 2025-LC-003: 장기 미출고 (90일)'],
#     'checked_lots': 45,
#     'checked_tonbags': 450,
#     'mismatched_lots': []
# }

# 특정 LOT 검증
result = validator.validate_lot("2025-LC-001")

# 자동 복구
fixed = validator.fix_integrity_issues()
# {
#     'fixed_count': 2,
#     'details': [
#         'LOT 2025-LC-001: current_weight 수정 (10000 → 7500)',
#         'LOT 2025-LC-002: 누락 톤백 1개 복구'
#     ]
# }
```

### 10.2 톤백 규칙

```python
# v3.1 핵심 규칙:

# 1. 부분 출고 불가
#    톤백은 AVAILABLE(전량) 또는 SOLD(전량판매)만 가능
#    부분 출고된 톤백 상태는 존재하지 않음

# 2. 재고 합계 일치
#    inventory.current_weight = SUM(AVAILABLE 톤백 weight)

# 3. SOLD 톤백 = 재고 기여도 0

# 출고 시 톤백 선택 로직
def select_tonbags_for_outbound(lot_no, target_weight):
    """LIFO 방식으로 톤백 선택"""
    available = engine.get_available_tonbags(lot_no)
    selected = []
    remaining = target_weight
    
    # 역순 (LIFO)
    for tonbag in reversed(available):
        if tonbag['weight'] <= remaining:
            selected.append(tonbag)
            remaining -= tonbag['weight']
        # else: 스킵 (부분출고 불가)
    
    return selected
```

---

## 11. Dashboard Provider API

### 11.1 DashboardProvider

```python
from dashboard_provider import DashboardProvider

provider = DashboardProvider(engine)

# 대시보드 전체 데이터
data = provider.get_dashboard_data()
# {
#     'summary': {
#         'total_weight': 225000.0,
#         'total_lots': 45,
#         'today_inbound': 2,
#         'today_outbound': 5,
#         'available_tonbags': 380
#     },
#     'alerts': [
#         {'type': 'warning', 'message': 'LOT 2025-LC-001: 재고 부족 (< 10%)'},
#         {'type': 'info', 'message': '오늘 출고 예정: 3건'}
#     ],
#     'by_product': [
#         {'name': 'Lithium Carbonate', 'weight': 150000, 'lots': 30},
#         {'name': 'Nickel Sulfate', 'weight': 75000, 'lots': 15}
#     ],
#     'recent_activity': [
#         {'type': 'inbound', 'lot_no': '2025-LC-010', 'weight': 10000, 'time': '10:30'},
#         {'type': 'outbound', 'lot_no': '2025-LC-005', 'weight': 2500, 'time': '09:15'}
#     ]
# }
```

### 11.2 개별 메서드

```python
# 요약 정보
summary = provider.get_summary()

# 알림 목록
alerts = provider.get_alerts()

# 제품별 현황
by_product = provider.get_by_product()

# 최근 활동
activity = provider.get_recent_activity(limit=10)

# 재고 추이 (차트용)
trend = provider.get_inventory_trend(days=30)
# [
#     {'date': '2025-01-01', 'inbound': 10000, 'outbound': 5000, 'balance': 220000},
#     ...
# ]
```

---

## 12. 통합 예제

### 12.1 완전한 입고 워크플로우

```python
from engine_modules.inventory_modular import InventoryEngine
from gemini_parser import GeminiDocumentParser
from ui_ops_helper import UIOperationsHelper
from ocr_auto_tuner import get_ocr_tuner
from datetime import datetime

def process_inbound_workflow(pdf_files, progress_callback=None):
    """PDF 파일들을 파싱하여 입고 처리"""
    
    engine = InventoryEngine()
    parser = GeminiDocumentParser(api_key="...")
    tuner = get_ocr_tuner()
    
    results = []
    
    for i, pdf_file in enumerate(pdf_files):
        try:
            # 1. 진행률 업데이트
            if progress_callback:
                progress_callback(i / len(pdf_files), f"파싱 중: {pdf_file}")
            
            # 2. PDF 파싱 (OCR 튜닝 적용)
            parse_result = tuner.execute(
                parser.parse_packing_list,
                pdf_file
            )
            
            if not parse_result['success']:
                results.append({
                    'file': pdf_file,
                    'success': False,
                    'error': '파싱 실패'
                })
                continue
            
            # 3. 입고 데이터 준비
            for j, lot_no in enumerate(parse_result['lot_numbers']):
                inbound_data = {
                    'lot_no': lot_no,
                    'product_name': 'Lithium Carbonate',
                    'initial_weight': parse_result['weights'][j],
                    'arrival_date': datetime.now().strftime('%Y-%m-%d'),
                    'container_no': parse_result.get('container_no')
                }
                
                # 4. 실제 입고
                result = engine.process_inbound(inbound_data)
                results.append({
                    'lot_no': lot_no,
                    'success': result['success'],
                    'message': result.get('message', '')
                })
        
        except Exception as e:
            results.append({
                'file': pdf_file,
                'success': False,
                'error': str(e)
            })
    
    engine.close()
    return results
```

### 12.2 GUI 통합 예제

```python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from engine_modules.inventory_modular import InventoryEngine
from ui_ops_helper import UIOperationsHelper, SmoothProgress

class SimpleInventoryApp:
    def __init__(self, root):
        self.root = root
        self.engine = InventoryEngine()
        
        # UI 설정
        self.progress_bar = ttk.Progressbar(root, length=300)
        self.progress_bar.pack(pady=10)
        
        self.progress_label = ttk.Label(root, text="Ready")
        self.progress_label.pack()
        
        # 헬퍼 초기화
        self.helper = UIOperationsHelper(
            parent=root,
            progressbar=self.progress_bar,
            progress_label=self.progress_label
        )
        self.smooth_progress = SmoothProgress(
            self.progress_bar,
            self.progress_label
        )
        
        # 버튼
        ttk.Button(root, text="입고", command=self.on_inbound).pack()
        ttk.Button(root, text="출고", command=self.on_outbound).pack()
        
        # 앱 시작 시 복구 확인
        self.helper.check_recovery(
            on_recover=self.resume_work,
            on_discard=lambda: print("무시됨")
        )
    
    def on_inbound(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if not files:
            return
        
        # 작업 시작 기록
        self.helper.start_work('inbound', {'files': list(files)})
        self.smooth_progress.start()
        
        try:
            for i, file in enumerate(files):
                # 처리...
                self.smooth_progress.set_progress(
                    (i + 1) / len(files),
                    f"처리 중: {file}"
                )
            
            self.helper.complete_work({'processed': len(files)})
            self.smooth_progress.complete("완료!")
            messagebox.showinfo("완료", f"{len(files)}개 파일 처리 완료")
            
        except Exception as e:
            self.helper.fail_work(str(e), exception=e)
            self.helper.show_error("입고 처리 실패", exception=e)
    
    def on_outbound(self):
        # 출고 로직...
        pass
    
    def resume_work(self, work_data):
        """미완료 작업 재개"""
        files = work_data.get('files', [])
        # 이어서 처리...

# 실행
if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleInventoryApp(root)
    root.mainloop()
```

---

## 13. 에러 처리

### 13.1 에러 코드

| 코드 | 설명 | 해결 방법 |
|------|------|----------|
| `E001` | LOT 번호 없음 | LOT 번호 입력 필요 |
| `E002` | LOT 번호 중복 | 다른 LOT 번호 사용 |
| `E003` | 재고 부족 | 출고량 조정 또는 다른 LOT 선택 |
| `E004` | 유효하지 않은 중량 | 양수 값 입력 |
| `E005` | 날짜 형식 오류 | YYYY-MM-DD 형식 사용 |
| `E006` | DB 연결 실패 | DB 경로 및 권한 확인 |
| `E007` | 톤백 무결성 오류 | `validator.fix_integrity_issues()` 실행 |
| `E008` | Preflight 검증 실패 | 오류 메시지 확인 후 수정 |
| `E009` | API Rate Limit (429) | OCR Tuner가 자동 조절, 잠시 대기 |
| `E010` | Circuit Breaker Open | 60초 대기 후 재시도 |
| `E011` | 파일 접근 오류 | 파일 경로 및 권한 확인 |
| `E012` | 트랜잭션 롤백 | 로그 확인 후 재시도 |

### 13.2 예외 처리 패턴

```python
from strict_validator import ValidationError

def safe_operation():
    try:
        result = engine.process_outbound(data)
        if not result['success']:
            # 비즈니스 로직 오류 (검증 실패 등)
            handle_business_error(result['errors'])
        return result
        
    except ValidationError as e:
        # 검증 오류
        logger.warning(f"검증 실패: {e.code} - {e.message}")
        show_validation_error(e)
        
    except Exception as e:
        # 예상치 못한 오류
        logger.exception(f"예상치 못한 오류: {e}")
        show_unexpected_error(e)
```

---

## 14. 성능 최적화

### 14.1 대량 데이터 처리

```python
# ❌ 비효율적
for item in large_list:
    engine.process_inbound(item)  # 매번 커밋

# ✅ 효율적 - 배치 처리
engine.process_inbound_batch(large_list)  # 한 번에 커밋
```

### 14.2 쿼리 최적화

```python
# ❌ N+1 문제
lots = engine.get_all_inventory()
for lot in lots:
    tonbags = engine.get_tonbags_by_lot(lot['lot_no'])

# ✅ 한 번에 조회
lots_with_tonbags = engine.get_all_inventory(include_tonbags=True)
```

### 14.3 DB 최적화

```python
# 주기적 최적화 (주 1회 권장)
engine.optimize_database()

# VACUUM + ANALYZE + REINDEX 수행
```

### 14.4 메모리 관리

```python
# 대량 데이터 처리 시 제너레이터 사용
def process_large_data():
    for chunk in engine.get_inventory_chunks(chunk_size=1000):
        process_chunk(chunk)
        # 청크 처리 후 메모리 해제
```

---

## 15. 마이그레이션 가이드

### 15.1 v2.x → v3.1

```python
# v2.x (기존)
from engine_modules.inventory import SQMInventoryEngine
engine = SQMInventoryEngine(db_path)
engine.add_inventory(lot_no, product, mxbg_pallet, net_weight)

# v3.1 (신규)
from engine_modules.inventory_modular import InventoryEngine
engine = InventoryEngine(db_path)
engine.process_inbound({
    'lot_no': lot_no,
    'product_name': product,
    'tonbag_count': mxbg_pallet,
    'initial_weight': net_weight
})
```

### 15.2 주요 변경사항

| 항목 | v2.x | v3.1 |
|------|------|------|
| 메인 클래스 | `SQMInventoryEngine` | `InventoryEngine` |
| 입고 메서드 | `add_inventory()` | `process_inbound()` |
| 출고 메서드 | `process_outbound()` | `process_outbound()` (동일) |
| 톤백 부분출고 | 가능 | **불가** |
| Preflight | 없음 | 자동 적용 |
| 트랜잭션 | 수동 | All-or-Nothing 자동 |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v3.2.0 | 2025-01-25 | 톤백 전량 출고, OCR Tuner, UI Helper, Dashboard |
| v2.9.99 | 2025-01-24 | Preflight 검증 강화 |
| v2.9.90 | 2025-01-20 | 모듈화 구조 개선 |

---

## 지원

- **문서**: `docs/` 폴더
- **담당**: Ruby (루비리)

---

*Last Updated: 2025-01-25*
