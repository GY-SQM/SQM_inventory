# P2-C DB 접근 정책 통일 문서 (P2-C-06)
작성일: 2026-04-08 | SQM v8.7.1

================================================================
## 1. Repository 계층 구조
================================================================

```
BaseRepository (features/repositories/base_repository.py)
├── InboundRepository   (features/repositories/inbound_repository.py)
├── OutboundRepository  (features/repositories/outbound_repository.py)
│   └── uses OutboundQuery
└── InventoryRepository (features/repositories/inventory_repository.py)

Service 계층:
├── OutboundService     (features/services/outbound_service.py)
├── InboundService      (features/services/inbound_service.py)
└── OutboundStateRules  (features/services/outbound_state_rules.py)
```

================================================================
## 2. 단일 책임 원칙 (DB 접근 규칙)
================================================================

| 레이어 | 역할 | DB 직접 접근 |
|--------|------|-------------|
| Repository | SELECT / INSERT / UPDATE / DELETE | ✅ 허용 |
| Service | 파이프라인 조합 + transaction 관리 | ✅ transaction만 |
| UI (handlers/dialogs) | 이벤트 처리 + 화면 갱신 | ❌ 금지 |
| Engine (mixin) | 레거시 — 단계적 대체 예정 | ⚠️ 유지 중 |

================================================================
## 3. 트랜잭션 규칙
================================================================

### 표준 패턴 (반드시 준수)
```python
# ✅ 올바른 방법
with self.db.transaction("IMMEDIATE"):
    self.repo.method_a(...)
    self.repo.method_b(...)
    self.repo.method_c(...)

# ❌ 금지
self.db.execute("UPDATE ...")
self.db.commit()   # 수동 commit 금지
```

### Savepoint 사용 (중첩 필요 시)
```python
# SQMDatabase는 중첩 transaction() 호출 시 자동으로 중첩 처리
# _local.in_transaction 플래그로 이중 BEGIN 방지
with self.db.transaction("IMMEDIATE"):    # 외부
    with self.db.transaction("IMMEDIATE"):  # 내부 — 자동 skip
        ...
```

### 읽기 전용 조회는 transaction 불필요
```python
# ✅ 조회는 transaction 없이
results = self.query.load_picked_tonbags(lot_no)
summary = self.inventory_repo.get_inventory_summary()
```

================================================================
## 4. 금지 패턴
================================================================

```python
# ❌ UI에서 직접 DB 접근
class SomeDialog:
    def on_button_click(self):
        self.engine.db.execute("SELECT ...")  # 금지

# ❌ Repository에서 transaction 직접 관리
class SomeRepository:
    def save(self):
        with self.db.transaction():  # Repository는 transaction 감싸지 않음
            self.db.execute(...)     # Service가 감쌈

# ❌ silent failure
try:
    self.db.execute(...)
except:
    pass   # 반드시 로깅 필요

# ❌ 수동 commit/rollback
self.db.execute(...)
self.db.commit()   # with transaction() 사용할 것
```

================================================================
## 5. 파일 배치 및 import 규칙
================================================================

### 배치 위치
```
Claude_SQM_v871/
  features/
    repositories/
      __init__.py              (기존)
      base_repository.py       (P2-C-02 신규)
      inbound_repository.py    (P2-C-03 수정: BaseRepository 상속)
      outbound_repository.py   (P2-C-04 수정: BaseRepository 상속)
      outbound_query.py        (P2-B-02 신규)
      inventory_repository.py  (P2-C-05 신규)
    services/
      __init__.py              (기존)
      inbound_service.py       (기존)
      outbound_service.py      (P2-B-05 신규)
      outbound_state_rules.py  (P2-B-03 신규)
```

### import 순서 (의존성 방향)
```
base_repository
    ↓
outbound_query / inbound_repository / inventory_repository
    ↓
outbound_repository (uses outbound_query + state_rules)
    ↓
outbound_service / inbound_service (uses repositories)
    ↓
UI (handlers / dialogs) — service만 import
```

================================================================
## 6. P2-C 완료 기준
================================================================

| 항목 | 상태 |
|------|------|
| BaseRepository 생성 | ✅ P2-C-02 |
| InboundRepository 상속 | ✅ P2-C-03 |
| OutboundRepository 상속 | ✅ P2-C-04 |
| InventoryRepository 신규 | ✅ P2-C-05 |
| DB 접근 정책 문서화 | ✅ P2-C-06 |

→ P2-D(React 전환) 진입 가능

================================================================
## 7. P2-D 진입 조건
================================================================

- P2-C 전체 완료 ✅
- pytest tests/ 전체 통과 (PC에서 확인 필요)
- OutboundService.get_dashboard() — React API 엔드포인트 연결 준비
- InventoryRepository.get_inventory_summary() — 대시보드 데이터 소스
