# PRD — DB 연결 안전화 (오류 시 잠김 방지) · [감사 M3 확장]

> 작성 2026-07-12 · 방식: superpowers 브레인스토밍(가/나/다 3문항) 결과 반영
> 관련 원항목: `docs/superpowers/plans/2026-07-11-outbound-transaction-integrity-plan.md` 의 **M3**

## 한 줄 요약
raw SQLite 연결을 쓰는 API 엔드포인트가 **오류 경로에서 연결/트랜잭션을 안 닫아** DB
잠김(락)을 유발하던 문제를, **오류가 나도 무조건 rollback+close 를 보장하는 공용
컨텍스트 매니저**로 전수 교체해 "어느 화면에서 오류가 나도 앱이 멈추지 않게" 만든다.

---

## 배경 / 문제
- 이 앱은 여러 API 화면이 엔진을 거치지 않고 `_db()` / `_alloc_db()` 같은 **raw sqlite
  연결**을 직접 연다. 정상 경로에선 `con.commit(); con.close()` 로 닫지만,
  **중간에 예외가 나면** `close()` 로 못 가고 연결이 열린 채 남는다.
- SQLite(WAL)에서 **커밋 안 된 쓰기 트랜잭션을 쥔 연결**이 남으면 DB에 락이 걸려,
  이후 요청들이 `database is locked` 로 **멈추거나 잠길 수 있다.**
- 평소엔 파이썬 GC 가 유휴 연결을 나중에 정리해줘 "가끔" 발생 → 그래서 여태 미뤄둔
  항목(M3)이었으나, 사용자 최우선 관심사(“단계 넘어갈 때 멈춤”)의 **마지막 계통**이다.

### 실측 누수 표면 (2026-07-12 기준)
`_db()`/`_alloc_db()`/`_db_path()` 팩토리를 정의한 파일 **약 18개**. 연결을 여는 곳 대비
`finally`(오류 시 닫기)가 거의 없다:

| 파일 | 연결 열기(대략) | `finally`(오류시 닫기) |
|---|---|---|
| `allocation_api.py` | ~16 | 3 |
| `inventory_api.py` | ~17 | 3 |
| `actions2.py` | ~9 | 2 |
| `actions3.py` | ~10 | **0** |
| `scan_api.py` | ~6 | **0** |
| `settings.py` | ~9 | 1 |

→ 대부분의 엔드포인트가 **정상 경로에서만 닫고 오류 경로에선 샌다.**

---

## 목표 & 성공 기준  *(브레인스토밍 Q1 → “가: 안정성 중심”)*
- **성공 기준:** *어떤 화면에서 오류가 발생해도, 그 직후 다른 요청이 `database is
  locked` 없이 정상 동작한다.* (= 오류 하나가 앱 전체를 잠그지 못한다.)
- 검증 가능한 형태: “엔드포인트 중간에 예외 주입 → 곧바로 같은/다른 요청 실행 →
  잠김 없이 성공” 회귀 테스트로 못박는다.

## 범위  *(Q2 → “나: 전수, 단계별”)*
raw 연결을 직접 여는 **모든** 백엔드 API 파일. 단, 한 번에 다 바꾸지 않고 **단계(PR)**
로 나눈다:
- **Phase 1 — 배정**: `allocation_api.py` (M3 원지목, 우선순위 최고)
- **Phase 2 — 출고/입고/스캔/재고 핵심**: `actions2/3.py`, `scan_api.py`,
  `inventory_api.py`, `outbound_api.py`(raw 부분)
- **Phase 3 — 나머지**: `settings.py`, `queries*.py`, `status_revert_api.py`,
  `warehouse_api.py`, `product_master.py`, `integrity_api.py`, `location_map_api.py`,
  `inbound.py`(`_open_db`), `inventory_adjust_api.py`, `actions.py` 등

## 비목표 (Out of scope)
- **동작(비즈니스 로직) 변경 없음.** 상태 전이·응답 형태·SQL 결과는 그대로.
  (이번 세션의 raw-SQL 무결성 수정과 달리, 여기선 **연결 수명만** 다룬다.)
- 엔드포인트를 엔진 정식 경로로 재작성하는 대규모 리팩터는 하지 않는다(Q1에서
  “통일/재발방지”가 아닌 “안정성”을 택함). 단, 연결 안전은 공용 도구로 통일한다(Q3).
- 성능 튜닝·커넥션 풀 도입은 범위 밖.

---

## 접근 방식  *(Q3 → “나: 공용 안전장치”)*
연결을 여닫는 로직을 **엔드포인트마다 try/finally 로 흩뿌리지 않고**, 딱 하나의 공용
컨텍스트 매니저를 만들어 모든 화면이 그것을 통해 열게 한다. 한 곳만 올바르면 전
화면이 자동으로 “오류 나도 무조건 rollback+close”가 된다(빠뜨림 위험 제거).

### 설계 개요 — `backend/api/db_session.py` (신규)
```python
from contextlib import contextmanager
import sqlite3

@contextmanager
def db_session(db_path, *, readonly=False, row_factory=sqlite3.Row,
               busy_timeout_ms=3000):
    """raw sqlite 연결을 안전하게 열고, 반드시 닫는다.

    - 정상 종료: readonly 가 아니면 commit, 그리고 close.
    - 예외 발생: rollback 후 close 하고 예외 재전파(락 방지의 핵심).
    - WAL + busy_timeout 등 기존 PRAGMA 를 한 곳에서 일관 적용.
    """
    con = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
    con.row_factory = row_factory
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
    try:
        yield con
        if not readonly:
            con.commit()
    except Exception:
        try: con.rollback()
        except Exception: pass
        raise
    finally:
        try: con.close()
        except Exception: pass
```

### 엔드포인트 채택 패턴 (before → after)
```python
# before — 오류 시 close 로 못 감(누수)
con = _alloc_db()
... 여러 execute ...
con.commit(); con.close()

# after — with 블록을 벗어날 때 무조건 정리(정상=commit+close, 오류=rollback+close)
with db_session(_alloc_db_path()) as con:
    ... 여러 execute ...
    # 명시적 commit 불필요(정상 종료 시 자동). 조기 return 도 안전.
```
- 각 파일의 기존 `_db()`/`_alloc_db()`(연결 반환)은 **경로 반환 헬퍼**(`_db_path()`)로
  대체하거나, `db_session` 이 팩토리를 받도록 얇게 감싼다. 기존 팩토리는 하위호환
  위해 남겨두되 신규 코드는 `db_session` 사용.
- HTTPException 등 **의도된 예외**도 `except Exception` 이 rollback+close 후 재전파하므로
  응답 코드/메시지는 그대로 유지된다(동작 불변).

---

## 검증 방법 (테스트 우선)
1. **컨텍스트 매니저 단위 테스트**: 정상 → commit+close; 예외 → rollback+close(연결
   닫힘 확인, 데이터 미반영 확인).
2. **락-비유발 회귀 테스트(핵심)**: 임시 DB로 엔드포인트 호출 중 예외를 주입(예: 잘못된
   입력/몽키패치)한 뒤, **곧바로 다른 요청을 실행해 `database is locked` 없이 성공**함을
   단언. Phase 1 은 배정 엔드포인트 대표 2~3개로 커버.
3. 각 Phase 마다 전체 스위트 그린(현재 470 passed 기준 + 신규) 확인 후 PR.

## 단계별 산출물 (PR 계획)
- **PR-A (Phase 1)**: `db_session` 헬퍼 + 단위 테스트 + `allocation_api.py` 채택 + 락-비유발
  회귀 테스트.
- **PR-B (Phase 2)**: 출고/입고/스캔/재고 핵심 채택 + 회귀 테스트.
- **PR-C (Phase 3)**: 나머지 전수 채택.
각 PR 은 **동작 불변**을 원칙으로, 연결 수명만 바꾼다.

## 리스크 & 완화
| 리스크 | 완화 |
|---|---|
| `with` 전환 중 기존 `commit` 위치/조기 return 로직이 미묘하게 바뀜 | 파일 단위로 나눠 소규모 diff + 전체 스위트로 회귀 감시 |
| 일부 엔드포인트가 **여러 연결**을 열거나 커밋 타이밍이 특수 | 그런 곳은 채택에서 제외/개별 처리로 표시하고 로그로 남김(무리한 일괄 변환 금지) |
| readonly 판단 실수로 커밋 누락 | 기본 `readonly=False`(commit) — 조회 전용만 명시적으로 표시 |
| 두 연결(엔진 + raw) 동시 사용 구간의 락 | busy_timeout 유지 + 쓰기 후 즉시 close 로 보유시간 최소화 |

## 참고 — 이번 세션 선행 작업과의 관계
- 앞서 async→def 전환(#18·19)으로 “작업 도중 이벤트루프 정지”는 해소됨.
- raw-SQL 무결성 복구(#20·21·22)로 “데이터 어긋남”은 해소됨.
- **본 작업은 그 세 번째 축 — “오류가 만든 락으로 인한 잠김” 을 없앤다.**
