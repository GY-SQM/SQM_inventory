# GPT_Claude_Code_React_Phase1_Safe_Refactor_v1

작성일시: 2026-04-03 00:40:21 (Asia/Seoul)  
인코딩: UTF-8

---

## 개요

이 문서는 SQM 프로젝트의 **React 1단계(Read-Only Hybrid UI)** 산출물에 대해,
Claude Code가 **보수적이고 안전한 구조 리팩토링**만 수행하도록 제한하는 실행 지시서입니다.

핵심 목적은 다음과 같습니다.

- `api/main.py` 비대화 방지
- dashboard / inventory 조회 관심사 분리
- `SOLD -> OUTBOUND` 표시 정규화 단일화
- React 1단계를 **읽기 전용(read-only)** 으로 유지
- 기존 tkinter 운영본과 core write-path 무영향 유지
- DB schema / business policy 변경 금지

---

## Claude Code 실행 지시서

```text
You are a world-class senior software architect, Python/FastAPI backend engineer, React frontend engineer, and conservative refactoring specialist.

Project context:
This is a production-sensitive internal logistics / inventory / outbound management system.
Operational stability, transaction safety, data integrity, and behavior preservation are more important than elegance or aggressive cleanup.

System baseline:
- Existing production app uses Python + tkinter + ttkbootstrap + SQLite
- Existing production desktop flow must remain intact
- React is being introduced only as a Phase 1 read-only hybrid UI
- React Phase 1 target screens are:
  1) Dashboard
  2) Inventory Search / Inventory Detail
- FastAPI is being introduced only as a read-only API layer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PRIMARY MISSION]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Perform a safe structural refactor of the current React Phase 1 scaffold.

Goal:
Convert the current MVP scaffold into a more maintainable Phase 1 read-only structure
WITHOUT changing business meaning, DB schema, or existing core desktop behavior.

Core objectives:
1) thin down api/main.py
2) separate dashboard and inventory read concerns
3) centralize SOLD -> OUTBOUND display normalization
4) keep React Phase 1 strictly read-only
5) improve maintainability and future extension safety
6) preserve current behavior as much as possible

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[FACTS YOU MUST RESPECT]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The project-wide rules are:

- keep tkinter
- keep SQLite
- do NOT change DB schema
- do NOT change business policy
- prioritize operational stability and data integrity
- use gradual refactoring
- current primary write-state wording is OUTBOUND
- SOLD is deprecated / legacy compatibility wording
- do NOT create new SOLD-primary write-paths

State baseline:
AVAILABLE -> RESERVED -> PICKED -> OUTBOUND

React Phase 1 is read-only only.
Do NOT add write-path APIs in this pass.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SCOPE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Target only the React Phase 1 files and closely related new API scaffolding.

You may modify:
- api/main.py
- api/dashboard_read_service.py
- web/src/App.jsx
- web/src/main.jsx
- web/src/pages/DashboardPage.jsx
- web/src/pages/InventoryPage.jsx
- web/src/api/client.js
- web/vite.config.js
- web/package.json
- other NEW helper files inside api/ or web/src/ if needed for safe structure

You may CREATE new files such as:
- api/routes/dashboard.py
- api/routes/inventory.py
- api/schemas/dashboard.py
- api/schemas/inventory.py
- api/services/inventory_read_service.py
- api/utils/status_normalizer.py
- web/src/api/dashboardApi.js
- web/src/api/inventoryApi.js
- web/src/components/... (if useful)

Do NOT modify:
- engine_modules/inventory_modular/outbound_mixin.py
- onestop_inbound.py
- DB schema / migrations
- core write-path logic
- tkinter production handlers
- LOT / TONBAG / sample semantics
- any business policy meaning

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PROBLEM TO SOLVE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The current React Phase 1 scaffold works as an MVP,
but there are maintainability risks:

1) api/main.py is too thick
   - app creation
   - schemas
   - helper logic
   - dashboard routes
   - inventory routes
   are too concentrated

2) status normalization risk
   - SOLD -> OUTBOUND display normalization may become duplicated or inconsistent

3) inventory read logic is not cleanly separated yet

4) frontend pages risk becoming fat components
   - fetch logic
   - state logic
   - rendering
   may remain overly coupled

Your job is to fix these structure risks conservatively.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[REQUIRED OUTPUT STRUCTURE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before modifying, briefly summarize:
1) current system understanding
2) structure problem breakdown
3) exact safe refactor plan

After modifying, output:
1) touched files
2) newly created files
3) structural changes made
4) SOLD/OUTBOUND normalization handling
5) safe boundaries preserved
6) validation steps
7) deferred issues

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SAFE MODIFICATION BOUNDARIES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Allowed:
- split api/main.py into thinner entry + routes + schemas + services + utils
- create inventory_read_service.py
- create status_normalizer.py
- move pydantic response models into schema modules
- move dashboard / inventory GET logic into route modules
- move frontend API calls into dashboardApi.js / inventoryApi.js
- split large React page rendering into smaller presentational components
- improve loading / error handling
- improve naming clarity
- preserve current response semantics as much as possible

Not allowed:
- DB schema change
- migration addition
- changing meaning of status values
- changing OUTBOUND back to SOLD as primary wording
- adding POST/PUT/DELETE business APIs
- changing write-path logic
- changing existing production transaction behavior
- reinterpreting LOT / TONBAG / sample policies

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[DANGER ZONE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Do NOT touch:
- outbound_mixin.py core write flow
- onestop_inbound.py giant file
- allocation / picking / outbound write semantics
- any production write-state transition
- any DB schema or migration
- any cross-file policy-level contracts in existing production logic

If you believe a change outside the allowed scope is needed, STOP.

If stopping, output exactly:

STOP-REASON:
- file:
- exact issue:
- why unsafe:
- proposed next action:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[STRUCTURAL TARGET]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Preferred backend structure:

api/
  main.py
  routes/
    dashboard.py
    inventory.py
  schemas/
    dashboard.py
    inventory.py
  services/
    dashboard_read_service.py
    inventory_read_service.py
  utils/
    status_normalizer.py

Preferred frontend structure:

web/src/
  App.jsx
  main.jsx
  api/
    client.js
    dashboardApi.js
    inventoryApi.js
  pages/
    DashboardPage.jsx
    InventoryPage.jsx
  components/
    dashboard/...
    inventory/...

This structure is preferred, but do not over-engineer.
Use the smallest safe change that meaningfully improves maintainability.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOLD / OUTBOUND RULE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use OUTBOUND as the primary display-state wording.

Treat SOLD only as:
- deprecated
- legacy compatibility
- old stored/raw status that may need normalization for display

Do NOT:
- create new SOLD-primary behavior
- present SOLD as the preferred current operational state

If raw data may still contain SOLD,
normalize it in one centralized utility only.

Preferred utility signature example:
- normalize_display_status(raw_status: str) -> str

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[BACKEND RULES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- main.py should become a thin application entry
- route files should only handle request/response orchestration
- service files should handle read logic / SQL / mapping
- normalization logic must be centralized
- keep all Phase 1 APIs read-only
- preserve existing response data shape unless there is a compelling safety reason
- if you must adjust a response shape, keep it minimal and explicitly report it

Preferred GET endpoints to preserve:
- /api/health
- /api/dashboard/summary
- /api/dashboard/by-product
- /api/dashboard/location-summary
- /api/inventory/filters
- /api/inventory/search
- /api/inventory/lot/{lot_no}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[FRONTEND RULES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- App.jsx should remain simple
- use react-router-dom for page routing
- pages should not directly contain too much API repetition
- move endpoint calls into web/src/api/*
- keep UI clean and readable
- preserve current Dashboard / Inventory functionality
- prefer safe incremental component extraction
- do NOT add complicated state libraries in this pass

Allowed frontend improvements:
- loading state clarity
- empty state clarity
- error state clarity
- component extraction for tables/cards/filter bars

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PERFORMANCE / MAINTAINABILITY NOTES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Important:
Do not guess performance bottlenecks as facts.

You may:
- point out potential bottlenecks
- leave TODO notes where measurement is needed

You must distinguish:
- verified current issue
vs
- possible future risk

Avoid premature optimization.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[VALIDATION REQUIREMENTS]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After changes, validate at minimum:

Python:
- python -m py_compile api/main.py
- python -m py_compile relevant new backend files

Frontend:
- package.json remains runnable
- import graph is consistent
- Vite proxy setup remains valid

Functional checks to preserve:
- /api/health should respond
- /api/dashboard/summary route preserved
- /api/dashboard/by-product route preserved
- /api/dashboard/location-summary route preserved
- /api/inventory/search route preserved
- /api/inventory/lot/{lot_no} route preserved
- DashboardPage should still load data
- InventoryPage should still load/search data

Also explicitly report:
- any response shape changes
- any deferred SQL/index concerns
- any assumptions not yet verified in runtime

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[IMPLEMENTATION STYLE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- prefer small, well-named files
- prefer thin orchestration in routes
- prefer clear service boundaries
- prefer centralized normalization
- prefer minimal, safe edits
- do not over-refactor
- stability first
- structure second
- elegance third

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[FINAL DECISION PRINCIPLE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When in doubt:
- choose the smaller change
- preserve behavior
- keep React Phase 1 read-only
- do not touch production write logic
- keep OUTBOUND as the current primary wording
- treat SOLD only as legacy compatibility
```

---

## 사용 메모

### 권장 사용 순서
1. SQM 프로젝트 전체 Git 백업
2. 현재 React Phase 1 초안 파일 백업
3. Claude Code에 본 프롬프트 입력
4. 수정 결과 diff 확인
5. `py_compile` 및 실행 검증
6. 필요 시 GPT로 구조 리뷰 재검토

### 권장 수정 대상
- `api/main.py`
- `api/dashboard_read_service.py`
- 신규 `api/routes/*`
- 신규 `api/schemas/*`
- 신규 `api/services/inventory_read_service.py`
- 신규 `api/utils/status_normalizer.py`
- `web/src/api/*`
- `web/src/pages/*`
- 신규 `web/src/components/*`

### 금지 대상
- `engine_modules/inventory_modular/outbound_mixin.py`
- `onestop_inbound.py`
- DB schema / migrations
- write-path API
- tkinter 코어 write 흐름
- LOT / TONBAG / sample semantics

---

## 파일 목적 요약

이 문서는 SQM React 1단계 산출물을 대상으로,
**MVP 초안을 giant-file 재발 없이 read-only 구조로 안정화**하기 위한 Claude Code 실행 지시서입니다.

핵심 원칙:

- 동작 보존
- 범위 제한
- 상태 표현 정리
- 구조적 분리
- read-only 유지
- 운영 안정성 최우선
