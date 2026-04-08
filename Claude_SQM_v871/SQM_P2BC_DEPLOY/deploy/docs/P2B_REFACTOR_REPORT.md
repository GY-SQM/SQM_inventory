# P2-B Outbound 리팩토링 완료 보고서
생성일: 2026-04-08
대상: Claude_SQM_v871 / engine_modules/inventory_modular/outbound_mixin.py

================================================================
## 1. 작업 개요
================================================================

원본 outbound_mixin.py (4,043줄) 에서
Query / Repository / StateRules / Service 4개 클래스로 분리 완료

================================================================
## 2. 분리 결과
================================================================

| 클래스 | 배치 경로 | 줄수 | 역할 |
|--------|-----------|------|------|
| OutboundStateRules | features/services/outbound_state_rules.py | 144줄 | 상태전이 규칙 — 유일한 상태 변경 권한 |
| OutboundQuery | features/repositories/outbound_query.py | 382줄 | SELECT 전담 (16개 메서드) |
| OutboundRepository | features/repositories/outbound_repository.py | 397줄 | INSERT/UPDATE 전담 (9개 메서드) |
| OutboundService | features/services/outbound_service.py | 514줄 | 전체 파이프라인 (7개 public 메서드) |

총 메서드: 41개 (public 38 + private 3)

================================================================
## 3. 실제 상태전이 흐름 (v8.7.1 확인)
================================================================

★ MASTER 예상값과 달랐던 실제 코드:

```
예상: ALLOCATION → SCANNED → SOLD
실제: RESERVED  → PICKED  → OUTBOUND  ← 이것으로 구현
```

### Forward 전이
```
AVAILABLE → RESERVED   (reserve_from_allocation)
RESERVED  → PICKED     (execute_reserved)
PICKED    → OUTBOUND   (confirm_outbound)
```

### Rollback 전이
```
PICKED    → RESERVED   (revert_picked_to_reserved)
OUTBOUND  → AVAILABLE  (revert_outbound_to_available)
RESERVED  → CANCELLED  (cancel_reservation)
```

================================================================
## 4. 안전성 검증 결과
================================================================

| 항목 | 결과 |
|------|------|
| 문법 오류 | 0건 ✅ |
| silent failure (bare except+pass) | 0건 ✅ |
| 수동 commit() 잔존 | 0건 ✅ |
| 수동 rollback() 잔존 | 0건 ✅ |
| with transaction() 적용 메서드 | 5/5개 ✅ |
| rollback 메서드 | 2개 완비 ✅ |

### Transaction 설계 원칙
- Service 레이어: `with self.db.transaction("IMMEDIATE")` — All-or-Nothing 보장
- Repository 레이어: execute() 단독 사용 → 정상 (Service transaction 안에서 호출)
- 중첩 트랜잭션 방지: SQMDatabase._local.in_transaction 플래그로 자동 처리

================================================================
## 5. 테스트 현황
================================================================

파일: tests/test_p2b_outbound_refactor.py
총 TC: 27개

| 클래스 | TC 수 | 핵심 케이스 |
|--------|-------|------------|
| TestOutboundStateRules | 6 | 허용/금지 전이, 최종 상태, 레거시 호환 |
| TestOutboundQuery | 7 | 조회, 이중출고 탐지, 중량 불일치 감지 |
| TestOutboundRepository | 4 | LOT 상태 재계산, 취소, 잔량 업데이트 |
| TestOutboundService | 10 | 전체 파이프라인 + 롤백 2종 + 대시보드 |

핵심 TC:
- test_full_pipeline_reserved_to_outbound: RESERVED→PICKED→OUTBOUND 전체 흐름
- test_revert_picked_to_reserved: PICKED→RESERVED 롤백
- test_revert_outbound_to_available: OUTBOUND→AVAILABLE 취소 (sold_table 삭제 포함)
- test_confirm_outbound_blocked_without_force_all: 안전장치 검증

================================================================
## 6. PC 적용 가이드
================================================================

### 배치 위치
```
Claude_SQM_v871/
  features/
    services/
      outbound_state_rules.py   ← outbound_state_rules.py
      outbound_service.py       ← outbound_service_v2.py (이름 변경)
    repositories/
      outbound_query.py         ← outbound_query.py
      outbound_repository.py    ← outbound_repository.py
  tests/
    test_p2b_outbound_refactor.py
```

### __init__.py 확인 필수
```
features/services/__init__.py        (없으면 빈 파일 생성)
features/repositories/__init__.py    (없으면 빈 파일 생성)
```

### pytest 실행
```bash
pytest tests/test_p2b_outbound_refactor.py -v --tb=short
```

### outbound_handlers.py 연결 (병행 운영 방식)
```python
# outbound_handlers.py 상단에 추가
from features.services.outbound_service import OutboundService

# 기존 self.inventory.execute_reserved() 호출 부분을:
svc = OutboundService(self.inventory.db)
result = svc.execute_reserved(lot_no=lot_no)

# 기존 self.inventory.confirm_outbound() 호출 부분을:
result = svc.confirm_outbound(lot_no=lot_no)
```

================================================================
## 7. P2-C 진입 조건 — 전체 충족
================================================================

| 조건 | 상태 |
|------|------|
| P2-A (Inbound) 완료 | ✅ |
| P2-B (Outbound) 완료 | ✅ |
| BaseRepository 설계 완료 | ✅ (base_repository.py) |
| OutboundRepository 완성 | ✅ |

→ P2-C 즉시 진입 가능

================================================================
## 8. P2-C 작업 예고
================================================================

P2-C-01: DB 접근 패턴 조사
P2-C-02: BaseRepository 프로젝트 배치
P2-C-03: InboundRepository → BaseRepository 상속으로 교체
P2-C-04: OutboundRepository → BaseRepository 상속으로 교체
P2-C-05: InventoryRepository 신규 생성 (기존 inventory 접근 코드 분리)
P2-C-06: DB 접근 정책 통일 (단일 책임 원칙 적용)

핵심 변경 (P2-C-03):
  Before: class InboundRepository:
  After:  class InboundRepository(BaseRepository):
              def __init__(self, db):
                  super().__init__(db)

예상 소요: 이 세션에서 완료 가능
