# 📚 SQM Inventory v3.2 - 개발자 가이드

> **대상**: Python 초보~중급 개발자  
> **목적**: 시스템 이해, 유지보수, 기능 추가  
> **버전**: v3.2.0  
> **작성일**: 2025-01-25

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [개발 환경 설정](#2-개발-환경-설정)
3. [프로젝트 구조](#3-프로젝트-구조)
4. [아키텍처](#4-아키텍처)
5. [핵심 모듈 설명](#5-핵심-모듈-설명)
6. [GUI 모듈화 구조](#6-gui-모듈화-구조)
7. [데이터베이스](#7-데이터베이스)
8. [검증 시스템](#8-검증-시스템)
9. [테스트](#9-테스트)
10. [코딩 규칙](#10-코딩-규칙)
11. [기능 추가 가이드](#11-기능-추가-가이드)
12. [디버깅 가이드](#12-디버깅-가이드)
13. [배포](#13-배포)
14. [FAQ](#14-faq)

---

## 1. 프로젝트 개요

### 1.1 시스템 목적

화학제품(리튬카보네이트, 니켈설페이트) 물류창고의 재고 관리 시스템입니다.

```
📦 실제 창고 흐름:
배 도착 → 컨테이너 하역 → 창고 입고 → 고객 주문 → 출고 → 배송
         (D/O, B/L)    (톤백 생성)              (LIFO)
```

### 1.2 주요 용어

| 용어 | 설명 | 예시 |
|------|------|------|
| SAP 번호 | 배송 그룹 번호 | SAP202500001 |
| B/L 번호 | 선하증권 번호 | MAEU2500001234 |
| LOT 번호 | 제품 묶음 번호 | 1125080001 |
| 톤백 | 포장 단위 (500kg) | 1125080001-15 |
| Sub LOT | 톤백 일련번호 | 01, 02, 03... |
| LIFO | 후입선출 | 나중 입고분 먼저 출고 |

### 1.3 데이터 계층

```
SAP (1개)
  └── B/L (1개)
       └── 컨테이너 (3~5개)
            └── LOT (4개)
                 └── 톤백 (10~20개)
```

### 1.4 v3.2 핵심 변경사항

| 항목 | v2.x | v3.2 |
|------|------|------|
| 톤백 출고 | 부분 출고 가능 | **전량 출고만** |
| 검증 | 수동 | **Preflight 자동** |
| 트랜잭션 | 부분 커밋 가능 | **All-or-Nothing** |
| GUI 구조 | 단일 파일 | **모듈화 (Mixins)** |
| 테마 | cosmo | **flatly** |
| 대시보드 | 없음 | **첫 화면** |

---

## 2. 개발 환경 설정

### 2.1 시스템 요구사항

- Python 3.10 이상
- Windows 10/11 (GUI 개발 시)
- 메모리: 4GB 이상
- 저장공간: 500MB 이상

### 2.2 설치

```bash
# 1. 프로젝트 복제/다운로드
cd sqm_v3.2

# 2. 가상환경 생성 (권장)
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 실행 테스트
python run.py
```

### 2.3 requirements.txt 주요 패키지

```
openpyxl>=3.1.0      # Excel 처리
pandas>=2.0.0        # 데이터 처리
ttkbootstrap>=1.10.0 # 모던 UI
reportlab>=4.0.0     # PDF 생성
PyMuPDF>=1.23.0      # PDF 파싱
pytest>=7.4.0        # 테스트
```

### 2.4 추천 도구

| 도구 | 용도 |
|------|------|
| VS Code | 코드 편집 |
| DB Browser for SQLite | DB 확인 |
| Git | 버전 관리 |
| pytest | 테스트 |

---

## 3. 프로젝트 구조

### 3.1 핵심 디렉토리

```
sqm_v3.2/
├── run.py                   ★ 진입점 (유일)
├── SQM_실행.bat             Windows 실행
├── gui_app_modular/        ★★★ GUI 모듈 (핵심)
│   ├── main_app.py         메인 앱 클래스
│   ├── mixins/             기능별 믹스인
│   ├── tabs/               탭별 UI
│   ├── handlers/           이벤트 핸들러
│   ├── dialogs/            다이얼로그
│   └── utils/              유틸리티
│
├── engine_modules/         ★★★ 비즈니스 로직
│   ├── inventory_modular/  재고 엔진 (모듈화)
│   ├── database.py         DB 연결
│   └── validators.py       검증기
│
├── parsers/                문서 파싱
├── tests/                  테스트
└── docs/                   문서
```

### 3.2 주요 파일

| 파일 | 설명 |
|------|------|
| `gui_app_modular/main_app.py` | GUI 메인 클래스 |
| `engine_modules/inventory_modular/engine.py` | 재고 엔진 Facade |
| `tonbag_integrity.py` | 톤백 무결성 검증 |
| `ui_ops_helper.py` | UI 운영 헬퍼 |
| `ocr_auto_tuner.py` | OCR 자동 튜닝 |

---

## 4. 아키텍처

### 4.1 레이어 구조

```
┌─────────────────────────────────────────┐
│          Presentation Layer             │
│  gui_app_modular/ (Tkinter + ttkbootstrap)
├─────────────────────────────────────────┤
│          Application Layer              │
│  UIOperationsHelper, OCRAutoTuner       │
├─────────────────────────────────────────┤
│           Business Layer                │
│  InventoryEngine (Facade 패턴)          │
│  PreflightValidator, TonbagIntegrity    │
├─────────────────────────────────────────┤
│            Data Layer                   │
│  DatabaseConnection (SQLite + WAL)      │
└─────────────────────────────────────────┘
```

### 4.2 Mixin 패턴

GUI는 Mixin 패턴으로 기능별 분리:

```python
class SQMInventoryApp(
    WindowMixin,       # 창 관리
    MenuMixin,         # 메뉴 설정
    ThemeMixin,        # 테마 관리
    RefreshMixin,      # 데이터 새로고침
    DragDropMixin,     # 드래그 앤 드롭
    DashboardTabMixin, # 대시보드 탭
    # ...
):
    pass
```

### 4.3 Facade 패턴

InventoryEngine은 복잡한 내부 로직을 숨김:

```python
class InventoryEngine(
    InboundMixin,
    OutboundMixin,
    QueryMixin,
    TonbagMixin,
    ExportMixin
):
    def process_inbound(self, data):
        # 단일 진입점
        pass
```

---

## 5. 핵심 모듈 설명

### 5.1 InventoryEngine

모든 재고 작업의 진입점:

```python
from engine_modules.inventory_modular import InventoryEngine

engine = InventoryEngine(db_path="./data/db/sqm_inventory.db")

# 입고
result = engine.process_inbound({
    'lot_no': '2025-LC-001',
    'product_name': 'Lithium Carbonate',
    'initial_weight': 10000,
    'arrival_date': '2025-01-25',
    'tonbag_count': 20
})

# 출고 (Preflight 자동)
result = engine.process_outbound({
    'lot_no': '2025-LC-001',
    'outbound_weight': 2500,
    'customer': 'POSCO'
})

# 조회
inventory = engine.get_all_inventory()
tonbags = engine.get_tonbags_by_lot('2025-LC-001')

engine.close()
```

### 5.2 TonbagIntegrityValidator

톤백 무결성 검증 (v3.2 핵심):

```python
from tonbag_integrity import TonbagIntegrityValidator

validator = TonbagIntegrityValidator(engine)

result = validator.validate()
if not result['valid']:
    fixed = validator.fix_integrity_issues()
```

**핵심 규칙:**
- 톤백은 부분 출고 불가 (전량만)
- `inventory.current_weight = SUM(AVAILABLE 톤백)`

### 5.3 UIOperationsHelper

UI 운영 편의:

```python
from ui_ops_helper import UIOperationsHelper

helper = UIOperationsHelper(parent, progressbar, label)

# 에러 표시
helper.show_error("작업 실패", exception=e)

# 작업 복구
helper.start_work('inbound', {'files': file_list})
helper.complete_work({'result': 'success'})
```

### 5.4 OCRAutoTuner

API Rate Limit 자동 조절:

```python
from ocr_auto_tuner import get_ocr_tuner

tuner = get_ocr_tuner()
result = tuner.execute(ocr_function, image_data)
# 429 발생 시 자동 동시성 감소
```

---

## 6. GUI 모듈화 구조

### 6.1 Mixin 작성

```python
# gui_app_modular/mixins/my_mixin.py
import logging
logger = logging.getLogger(__name__)

class MyMixin:
    """내 기능 Mixin"""
    
    def _setup_my_feature(self) -> None:
        """초기화"""
        pass
    
    def _my_method(self) -> None:
        """기능 메서드"""
        try:
            # 로직
            self._log("✅ 완료")
        except Exception as e:
            logger.error(f"오류: {e}")
```

### 6.2 새 탭 추가

```python
# gui_app_modular/tabs/my_tab.py
class MyTabMixin:
    def _setup_my_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📋 내 탭")
        
        ttk.Button(frame, text="작업", 
                   command=self._on_action).pack()
```

### 6.3 main_app.py에 등록

```python
from .tabs import MyTabMixin

class SQMInventoryApp(
    # 기존 Mixin들...
    MyTabMixin,  # 새 탭 추가
):
    pass
```

---

## 7. 데이터베이스

### 7.1 연결

```python
from engine_modules.database import DatabaseConnection

with DatabaseConnection(db_path) as db:
    rows = db.fetchall("SELECT * FROM inventory")
    db.execute("UPDATE ...")
    db.commit()
```

### 7.2 트랜잭션

```python
with DatabaseConnection(db_path) as db:
    try:
        db.execute("INSERT ...")
        db.execute("INSERT ...")
        db.commit()  # 모두 성공
    except:
        db.rollback()  # 전체 롤백
        raise
```

### 7.3 주요 테이블

```sql
inventory          -- 재고 (LOT 단위)
inventory_tonbag   -- 톤백 (개별 포장)
inbound_history    -- 입고 이력
outbound_history   -- 출고 이력
```

---

## 8. 검증 시스템

### 8.1 Preflight 검증

```python
# 출고 전 시뮬레이션
preflight = engine.preflight_outbound({
    'lot_no': '2025-LC-001',
    'outbound_weight': 2500
})

if not preflight['valid']:
    print(f"오류: {preflight['errors']}")
```

### 8.2 검증 계층

```
StrictValidator      → 데이터 형식
PreflightValidator   → 비즈니스 로직
TonbagIntegrity      → 무결성
DB Constraints       → DB 레벨
```

---

## 9. 테스트

### 9.1 실행

```bash
# 전체 테스트
pytest tests/ -v

# 커버리지
pytest tests/ --cov=. --cov-report=html

# 특정 파일
pytest tests/test_inventory.py -v
```

### 9.2 테스트 작성

```python
import pytest
from engine_modules.inventory_modular import InventoryEngine

@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = InventoryEngine(str(db_path))
    yield engine
    engine.close()

def test_inbound(engine):
    result = engine.process_inbound({
        'lot_no': 'TEST-001',
        'product_name': 'Test',
        'initial_weight': 1000,
        'arrival_date': '2025-01-25'
    })
    assert result['success'] is True
```

### 9.3 현재 상태

```
테스트: 387 passed, 45 skipped
커버리지: 89.6%
```

---

## 10. 코딩 규칙

### 10.1 네이밍

```python
class MyClass:           # PascalCase
def my_function():       # snake_case
def _private_method():   # _prefix
MAX_VALUE = 100          # UPPER_CASE
```

### 10.2 타입 힌트

```python
def process(data: Dict[str, Any]) -> Dict[str, Any]:
    """함수 설명"""
    pass
```

### 10.3 예외 처리

```python
# ❌ 나쁨
except:
    pass

# ✅ 좋음
except ValueError as e:
    logger.warning(f"값 오류: {e}")
```

### 10.4 로깅

```python
import logging
logger = logging.getLogger(__name__)

logger.info("정보")
logger.warning("경고")
logger.error("오류")
logger.exception("예외 + 트레이스백")
```

---

## 11. 기능 추가 가이드

### 11.1 체크리스트

- [ ] 요구사항 분석
- [ ] 테스트 먼저 작성
- [ ] 구현
- [ ] 문서화
- [ ] 테스트 실행

### 11.2 예제: 새 보고서

```python
# handlers/report_handlers.py
def generate_my_report(self):
    data = self.engine.get_data()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in data:
        ws.append(row)
    
    wb.save(filepath)
```

---

## 12. 디버깅 가이드

### 12.1 로그 확인

```python
import logging
logging.basicConfig(level=logging.DEBUG)
# 파일: ./logs/sqm_inventory.log
```

### 12.2 DB 확인

```python
result = engine.db.fetchall("SELECT * FROM inventory LIMIT 10")
for row in result:
    print(dict(row))
```

### 12.3 정합성 검사

```python
inv = engine.db.fetchone("SELECT SUM(current_weight) FROM inventory")
tb = engine.db.fetchone("""
    SELECT SUM(weight) FROM inventory_tonbag 
    WHERE status='AVAILABLE'
""")
print(f"차이: {abs(inv - tb)}")
```

### 12.4 일반 오류

| 오류 | 해결 |
|------|------|
| UNIQUE constraint | 중복 확인 후 삽입 |
| database is locked | WAL 모드 또는 재시도 |
| GUI 멈춤 | 백그라운드 스레드 사용 |

---

## 13. 배포

### 13.1 패키징

```bash
zip -r sqm_v3.2.zip sqm_v3.2 \
    -x "*.db" -x "*__pycache__*"
```

### 13.2 체크리스트

- [ ] 버전 업데이트
- [ ] 테스트 통과
- [ ] 문서 업데이트
- [ ] 민감 정보 제거

---

## 14. FAQ

### Q: 새 필드 추가?

```python
db.execute("ALTER TABLE inventory ADD COLUMN new_field TEXT")
```

### Q: 백그라운드 작업?

```python
import threading

def _run_background(self, work_fn, on_success):
    def wrapper():
        result = work_fn()
        self.root.after(0, lambda: on_success(result))
    
    threading.Thread(target=wrapper, daemon=True).start()
```

---

## 부록

### 버전 히스토리

| 버전 | 변경 |
|------|------|
| v3.2.0 | 톤백 전량출고, 대시보드 |
| v2.9.99 | Preflight 강화 |

### 연락처

- **개발**: Ruby (루비리)

---

*Last Updated: 2025-01-25*
