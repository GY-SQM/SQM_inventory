# SQM 재고관리 시스템 API Reference v3.6.8

**버전**: 3.6.8  
**최종 업데이트**: 2025-02-05

---

## 목차

1. [Engine API](#engine-api)
2. [에러 복구 모듈](#에러-복구-모듈)
3. [성능 최적화 모듈](#성능-최적화-모듈)
4. [유효성 검증](#유효성-검증)
5. [백업 관리](#백업-관리)
6. [유틸리티 함수](#유틸리티-함수)

---

## Engine API

### SQMInventoryEngine

메인 재고 관리 엔진 클래스.

```python
from engine import SQMInventoryEngine

engine = SQMInventoryEngine(db_path="inventory.db")
```

#### 입고 처리

```python
# 단일 LOT 입고
result = engine.process_inbound({
    'lot_no': 'LOT-001',
    'net_weight': 5000.0,
    'bag_count': 5,
    'sap_no': 'SAP12345',
    'bl_no': 'BL98765'
})

# 반환값
# {
#     'success': True,
#     'lot_no': 'LOT-001',
#     'created_tonbags': 5,
#     'message': '입고 완료'
# }
```

#### 출고 처리

```python
# 톤백 피킹
result = engine.pick_tonbags("LOT-001", count=3)

# 출고 처리
result = engine.process_outbound([
    {'lot_no': 'LOT-001', 'qty': 3}
])
```

#### 재고 조회

```python
# 전체 재고
inventory = engine.get_inventory()

# LOT 상세
detail = engine.get_lot_detail("LOT-001")

# 톤백 요약
summary = engine.get_tonbag_summary("LOT-001")
# {
#     'lot_no': 'LOT-001',
#     'total_count': 10,
#     'available_count': 7,
#     'picked_count': 3,
#     'total_weight': 5000.0,
#     'available_weight': 3500.0
# }
```

#### CRUD 메서드

```python
# 재고 추가
engine.add_inventory(lot_no="NEW-001", total_weight=1000)

# 재고 삭제
engine.delete_inventory("LOT-001", force=True)

# 재고 검색
results = engine.search_lots(keyword="LOT", status="available")

# 재고 업데이트
engine.update_inventory(lot_no="LOT-001", remarks="업데이트됨")
```

---

## 에러 복구 모듈

### utils.error_recovery

자동 재시도, DB 무결성 검사, 복구 기능 제공.

#### retry_on_failure 데코레이터

```python
from utils.error_recovery import retry_on_failure

@retry_on_failure(max_retries=3, delay=0.5, backoff=2.0)
def risky_operation():
    # 실패 시 자동 재시도
    pass
```

**파라미터**:
- `max_retries` (int): 최대 재시도 횟수 (기본: 3)
- `delay` (float): 초기 대기 시간 (초)
- `backoff` (float): 대기 시간 배수
- `exceptions` (tuple): 재시도할 예외 타입
- `on_retry` (callable): 재시도 시 콜백

#### RecoveryManager

```python
from utils.error_recovery import RecoveryManager

manager = RecoveryManager(db_path="inventory.db")

# 무결성 검사
is_ok, message = manager.check_integrity()

# 자동 복구
result = manager.check_and_recover()
```

#### UserNotification

```python
from utils.error_recovery import UserNotification

notif = UserNotification()
notif.add("warning", "주의", "디스크 공간 부족")

# 읽지 않은 알림
unread = notif.get_unread()

# 읽음 표시
notif.mark_read(0)
```

#### SafeTransaction

```python
from utils.error_recovery import SafeTransaction

with SafeTransaction(conn) as tx:
    conn.execute("INSERT ...")
    # 예외 발생 시 tx.success = False
    
if tx.success:
    print("트랜잭션 성공")
```

---

## 성능 최적화 모듈

### utils.performance

쿼리 캐싱, 벌크 연산, DB 최적화 기능.

#### QueryCache

```python
from utils.performance import QueryCache

cache = QueryCache(maxsize=1000, ttl=300)

# 캐시 설정/조회
cache.set("key", "value")
result = cache.get("key")  # "value" 또는 None

# 무효화
cache.invalidate("key")
cache.clear()

# 통계 (property)
stats = cache.stats
# {'hits': 10, 'misses': 3, 'hit_rate': 76.9}
```

#### BulkOperator

```python
from utils.performance import BulkOperator

bulk = BulkOperator(conn)

# 벌크 삽입
result = bulk.insert_many("table_name", [
    {'col1': 'val1', 'col2': 'val2'},
    {'col1': 'val3', 'col2': 'val4'},
])
# {'success': True, 'inserted': 2, 'errors': []}
```

#### optimize_db

```python
from utils.performance import optimize_db

# VACUUM + ANALYZE + WAL 모드 설정
result = optimize_db("inventory.db")
```

---

## 유효성 검증

### engine_modules.validators

데이터 유효성 검증 함수 및 클래스.

#### validate_lot_no

```python
from engine_modules.validators import validate_lot_no

is_valid, message = validate_lot_no("LOT-001")
# (True, "유효한 LOT 번호")

is_valid, message = validate_lot_no("")
# (False, "LOT 번호가 비어있습니다")
```

#### validate_weight

```python
from engine_modules.validators import validate_weight

is_valid, message = validate_weight(100.5)
# (True, "유효한 무게")

is_valid, message = validate_weight(-10)
# (False, "무게는 0보다 커야 합니다")
```

#### ValidationResult

```python
from engine_modules.validators import ValidationResult

result = ValidationResult(
    is_valid=True,
    message="검증 성공",
    warnings=["경고 메시지"]
)

if result.is_valid:
    print(result.message)
```

---

## 백업 관리

### utils.backup

자동 백업 생성, 복원, 정리 기능.

#### BackupManager

```python
from utils.backup import BackupManager

manager = BackupManager(
    db_path="inventory.db",
    backup_dir="./backups"
)

# 백업 생성
backup_path, message = manager.create_backup()

# 백업 목록
backups = manager.list_backups()
# [{'filename': 'sqm_20250205_120000.db', 'size': 1024000, ...}]

# 백업 복원
success, message = manager.restore_backup(backup_path)

# 오래된 백업 정리 (내부 메서드)
manager._cleanup_old_backups(keep_count=10)
```

---

## 유틸리티 함수

### utils.safe_conversions

안전한 타입 변환 함수.

```python
from utils.safe_conversions import safe_str, safe_float, safe_int, safe_date

safe_str(None)       # ""
safe_float("123.45") # 123.45
safe_int("100")      # 100
safe_date("2025-02-05")  # date(2025, 2, 5)
```

### utils.column_aliases

컬럼명 정규화 및 매핑.

```python
from utils.column_aliases import ColumnMapper

mapper = ColumnMapper()

# 행 정규화
normalized = mapper.normalize_row({'LOT NO': 'TEST', 'WEIGHT': 100})
# {'lot_no': 'TEST', 'weight': 100}
```

### utils.config_manager

설정 파일 관리.

```python
from utils.config_manager import ConfigManager

config = ConfigManager("settings.ini")

# 값 조회/설정
value = config.get("db_path")
config.set("db_path", "/new/path")
```

---

## 변경 이력

### v3.6.8 (2025-02-05)

- 버그 수정: crud_mixin.py `remark` → `remarks` 컬럼명
- 버그 수정: logger.py `self.logger` 참조 오류
- 테스트: 1308 passed, 커버리지 75.7%
- 에러 복구 모듈 별칭 추가

### v3.6.7 (2025-02-04)

- GUI 테스트 0/14 → 41/41 전환
- 테스트 커버리지 64.2%
- 전체 테스트 1026 passed

---

**문서 자동 생성**: Sphinx autodoc  
**소스 코드**: [GitHub Repository]
