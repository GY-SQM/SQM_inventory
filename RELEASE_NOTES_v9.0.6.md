## SQM v9.0.6 — 운영 자동화 + narrow SQL lint

릴리즈일: 2026-07-22
대상: v9.0.5 → v9.0.6
대분류: minor (운영 자동화 + 정밀 lint)

### Step 1: audit_log 자동 정리 윈도우 스케줄러 등록

v8.8.5 description에 "윈도우 스케줄러 자동 디스크 청소 주기 등록"이 있었지만
실제 schtasks 명령은 레포에 없었음 (운영자 수동 등록).
v9.0.5에서 `cleanup_audit()` 함수 + endpoint를 추가했고,
**v9.0.6에서 마침내 자동 스케줄러 등록을 레포에 정식 추가**.

도구 (3개):
- `tools/cleanup_audit_job.py`
  - 단일 Python 스크립트, `core.db_allowed.cleanup_audit(days=30)` 호출
  - JSON 한 줄 출력 → 스케줄러 로그 파싱용
  - 항상 exit 0 (best-effort, silent failure)
- `tools/install_cleanup_scheduler.ps1`
  - `schtasks /Create /SC WEEKLY` (default: 매주 일요일 03:00)
  - 환경변수 override: `SCHEDULE_DAY`, `SCHEDULE_TIME`, `DAYS`, `PYTHON_EXE`
  - idempotent (기존 작업 제거 후 재등록)
- `tools/uninstall_cleanup_scheduler.ps1`
  - `schtasks /Delete`, 미등록 시 no-op

운영 효과:
- audit_log 자동 정리 주기 등록 (사용자 수동 작업 제거)
- 30일 기본, 1~365일 설정 가능

### Step 2: narrow SQL context lint (broad → narrow)

v9.0.0 audit 🟡 #2 (f-string SQL 인벤토리)는 broad regex로 11건 모두
화이트리스트/? 바인딩 보호 중임을 확인. v9.0.6에서는 한 단계 좁혀서
**실제 SQL 실행 호출의 첫 인자**만 검사하는 narrow lint를 추가.

broad (regex, v9.0.0): 11건 모두 검토됨, audit 인벤토리 문서로 영속 검증
narrow (AST, v9.0.6): `cur.execute(f'...')` / `conn.execute(...)` / `con.executescript()`
                      처럼 DB에 직접 전달되는 SQL만 검사
                      → false positive 제거 + **신규 동적 SQL 사전 감지**

기법:
- AST walk (regex 아님) — 정확한 호출 시그니처 파악
- `SAFE_PLACEHOLDER_NAMES`: ph, sets, set_clauses, select_cols, where,
  params, field, tbl 등 value list 빌더/allowlist 결과는 skip
- `.join(...)` Call은 placeholder 빌더로 safe 분류
- `_fstring_only_safe_placeholders()`: 모든 `{var}`가 safe면 f-string skip

### Step 2 보너스: baseline 등록 (운영화)

`tools/lint_sql_context.baseline.json`:
- 첫 가동 시 발견된 11건 모두 검토/등록 (의도된 dynamic)
  - `allocation_api.py:963` — REVERT_MAP 결과 (`src_status` 검증 완료)
  - `inbound.py:2602` — `select_cols` + `order_col` literal 할당
  - `queries3.py:1929` — audit 인벤토리 #1.4 (DB 메타)
  - `status_revert_api.py:207, 448` — string-concat + `_base_query` internal helper
  - `db_session.py:42` — `int()` cast
  - `product_master.py:77`, `__init__.py:49` — literal list
  - `queries.py:447`, `sales_order_validation.py:51` — if/else literal
- baseline 매칭은 `[REVIEWED]` 표시 + exit 0
- baseline 외 신규 발견은 `[WARN]` + exit 1 (CI 가드)

### 테스트
- `tests/test_cleanup_scheduler.py` (15 tests, 누적)
  - `test_cs01~cs06` — job 스크립트 (실행, days 인자, JSON 출력, exit 0)
  - `test_cs10~cs14` — install ps1 (schtasks /Create, /SC WEEKLY, idempotent, env)
  - `test_cs20~cs22` — uninstall ps1 (schtasks /Delete, skip-if-missing)
  - `test_cs30` — 태스크명 일관성
- `tests/test_lint_sql_context.py` (22 tests, 누적)
  - `test_lsc01~lsc03` — 모듈 import, baseline JSON 검증
  - `test_lsc10~lsc13` — `_is_exec_call` 정확성
  - `test_lsc20~lsc23` — `_is_dangerous_sql_arg` 정확성
  - `test_lsc30~lsc34` — `_fstring_only_safe_placeholders` 정확성
  - `test_lsc40~lsc41` — `find_narrow_sql_exec` 합성 검증
  - `test_lsc50` — `partition_by_baseline` 분류 정확성
  - `test_lsc60~lsc61` — main() exit 0/1 CI 통합

### 회귀
- 659 passed (v9.0.5 622 + 신규 37)

### 다음 (v9.0.7+)
- queries3.py L644/653/891 dynamic set → 명시적 allowlist (Phase 2 본격, A 옵션)
- audit endpoint 페이지네이션 / 기간 필터 고도화
- central allowlist stats Prometheus exporter
- Phase 3 (새 시즌) 후보
