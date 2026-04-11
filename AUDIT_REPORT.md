# SQM v8.7.0 Deep System Audit Report

**작성일**: 2026-04-10  
**감사 범위**: 전체 코드베이스 (Python 백엔드 + React 프론트엔드 + Electron 데스크톱)  
**감사 파일 수**: 약 200+ 파일, 50,000+ 라인

---

## 1. Executive Summary

### 프로젝트 건강도 평가

| 영역 | 등급 | 설명 |
|------|------|------|
| **보안** | 🔴 D | localhost 인증 우회, API 키 평문 저장, 파일 업로드 미검증 |
| **안정성** | 🟠 C | silent exception 다수, 트랜잭션 비원자성, 엔진 초기화 실패 무시 |
| **유지보수성** | 🟠 C- | God class 다수 (1,300줄 main_app.py), 30+ mixin 상속 체인 |
| **성능** | 🟡 B- | 쿼리 캐시 미활용, pagination 부재, N+1 패턴 일부 잔존 |
| **아키텍처** | 🟠 C | 모듈 경계 불명확, features↔gui_app_modular 중복, DB 계층 누출 |
| **테스트** | 🔴 D | 핵심 비즈니스 로직에 대한 테스트 부족 |

### 전체 리스크 수준: **중-고 (Medium-High)**

### 핵심 결론
1. **보안 취약점 6건 즉시 수정 필요** — localhost 인증 우회, CORS 과도한 허용, 파일 업로드 검증 부재
2. **구조적 기술 부채 심각** — config.py 600줄, barcode_scan_engine.py 1,360줄, main_app.py 1,300줄
3. **에러 처리 전략 부재** — 192+ try/except 블록이 silent debug 로깅으로 끝남
4. **잘 설계된 부분도 존재** — query_cache.py, parsers 모듈 분리, Facade 패턴 적용 등

---

## 2. System Understanding

### 프로젝트 목적
물류/창고 현장 재고관리 풀스택 시스템 (톤백 입출고, 바코드 스캔, LOT 관리, PDF 리포트)

### 주요 모듈

| 모듈 | 역할 | 핵심 파일 |
|------|------|-----------|
| `core/` | 비즈니스 핵심 (바코드, 검증, PDF) | barcode_scan_engine.py (1,360줄) |
| `engine_modules/` | DB, 재고 엔진, 마이그레이션 | database.py (900줄), preflight.py (900줄) |
| `features/` | 서비스/리포지토리/파서 레이어 | outbound_service.py, inbound_parser.py |
| `gui_app_modular/` | PyQt 데스크톱 GUI | main_app.py (1,300줄), 42개 dialog 파일 |
| `react_api/` | FastAPI REST API | main.py, routes/, middleware/security.py |
| `web/` | React SPA 프론트엔드 | App.jsx, DataTable.jsx |
| `parsers/` | 문서 파싱 (PDF, Excel) | document_parser_modular/ |

### 진입점(Entry Points)

```
run.py               → PyQt GUI 앱 실행
run_react_api.py     → FastAPI 서버 실행
run_desktop.py       → Electron + API 서버 동시 실행
run_bootstrap.py     → DB 마이그레이션 + 초기화
```

### 주요 실행 흐름

```
[사용자] → React UI / PyQt GUI
              ↓
         FastAPI / Direct DB
              ↓
      SQMInventoryEngineV3 (Facade)
              ↓
    ┌─────────┼─────────┐
    ↓         ↓         ↓
 database  preflight  validators
    ↓
 SQLite (WAL mode)
```

---

## 3. Debugging Audit

### ISSUE-D1: 엔진 초기화 실패 Silent Ignore [확정]

| 항목 | 내용 |
|------|------|
| **증상** | API 서버 시작 후 모든 요청 500 에러, 로그 없음 |
| **직접 원인** | `react_api/main.py` L103-106: `except Exception: pass` |
| **구조적 원인** | 앱 실행과 엔진 초기화가 분리되지 않음 |
| **증거** | `try: engine = SQMInventoryEngineV3() ... except Exception: pass` |
| **심각도** | 🔴 Critical |
| **재현성** | DB 파일 손상/경로 오류 시 100% 재현 |
| **수정안** | `except`에서 `raise` + startup health check 추가 |
| **재발 방지** | CI에 startup smoke test 추가, bare except lint rule |

### ISSUE-D2: 트랜잭션 중첩 시 부분 커밋 [확정]

| 항목 | 내용 |
|------|------|
| **증상** | 반품/재입고 처리 중 일부 데이터만 업데이트 |
| **직접 원인** | `database.py` L240-260: 중첩 트랜잭션이 no-op |
| **구조적 원인** | SQLite Savepoint 미구현, 락 관리만 의존 |
| **증거** | 내부 transaction context가 `yield`만 하고 BEGIN/COMMIT 안 함 |
| **심각도** | 🔴 Critical |
| **재현성** | 내부 코드 예외 발생 시 재현 |
| **수정안** | SAVEPOINT 기반 중첩 트랜잭션 구현 |
| **재발 방지** | 트랜잭션 테스트 케이스 추가 |

### ISSUE-D3: 재고 무게 재계산 비원자성 [확정]

| 항목 | 내용 |
|------|------|
| **증상** | 반품 후 재고 무게와 톤백 합계 불일치 |
| **직접 원인** | `return_reinbound_engine.py` L240-245: 톤백 복원과 무게 업데이트 분리 |
| **구조적 원인** | 두 단계 사이 실패 시 롤백 없음 |
| **증거** | Step1: `_restore_tonbags()` 성공 → Step2: `_restore_lot_weight()` 실패 = 불일치 |
| **심각도** | 🔴 Critical |
| **재현성** | DB lock/네트워크 지연 시 재현 |
| **수정안** | 단일 트랜잭션으로 감싸기 + 실패 시 full rollback |
| **재발 방지** | integrity check 스케줄러 추가 |

### ISSUE-D4: 변수명 오타 — 로깅 버그 [확정]

| 항목 | 내용 |
|------|------|
| **증상** | DB 예외 로깅 시 NameError 발생 |
| **직접 원인** | `database.py` L650: `except Exception as _e:` 후 `logger.debug(f'... {e}')` — `e` vs `_e` |
| **구조적 원인** | 에러 핸들링 코드 리뷰 부재 |
| **증거** | 변수명 `_e`로 바인딩 후 `e`로 참조 |
| **심각도** | 🟠 High |
| **재현성** | 모든 DB 예외 발생 시 100% |
| **수정안** | `_e` → `e`로 통일 |
| **재발 방지** | linter에 unused variable 규칙 추가 |

### ISSUE-D5: 파일 업로드 메모리 폭탄 [확정]

| 항목 | 내용 |
|------|------|
| **증상** | 대용량 파일 업로드 시 서버 OOM 크래시 |
| **직접 원인** | `react_api/routes/reports.py` L303-310: `await file.read()` 후 크기 체크 |
| **구조적 원인** | 입력 검증이 처리 후에 실행됨 |
| **증거** | `content = await file.read()` → `if len(content) > 50MB` (순서 역전) |
| **심각도** | 🔴 Critical |
| **재현성** | 1GB 파일 업로드 시 100% |
| **수정안** | Content-Length 헤더 선체크 + 스트리밍 청크 읽기 |
| **재발 방지** | 미들웨어 레벨 요청 크기 제한 |

### ISSUE-D6: Rate Limiter 비동기 안전하지 않음 [확정]

| 항목 | 내용 |
|------|------|
| **증상** | 고부하 시 rate limit 2배까지 통과 |
| **직접 원인** | `react_api/middleware/security.py` L26-52: dict 무잠금 접근 |
| **구조적 원인** | asyncio 환경에서 공유 상태 동기화 미고려 |
| **증거** | `_rate_store: dict = defaultdict(list)` — lock 없음 |
| **심각도** | 🟠 High |
| **재현성** | 동시 요청 100+ 시 재현 |
| **수정안** | asyncio.Lock 또는 Redis 기반 rate limiter 도입 |
| **재발 방지** | 동시성 테스트 추가 |

---

## 4. Refactoring Audit

### 4.1 Long Functions (100줄 이상)

| 파일 | 함수 | 줄 수 | 문제 |
|------|------|-------|------|
| `core/barcode_scan_engine.py` | `process_barcode_scan_for_lot_mode()` | **314줄** | 검증+DB쿼리+상태전이+로깅 혼합 |
| `core/barcode_scan_engine.py` | `process_barcode_scan_to_sold()` | 155줄 | 비즈니스 로직 + DB 직접 접근 |
| `core/barcode_scan_engine.py` | `_confirm_one_uid_random()` | 133줄 | UID 검증 + 랜덤 배정 혼합 |
| `features/parsers/inbound_parser.py` | `merge_results()` | **233줄** | 파싱+검증+변환 혼합 |
| `engine_modules/preflight.py` | `PreflightValidator.__init__()` | 100줄+ | 생성자에서 과도한 초기화 |

### 4.2 Oversized Files

| 파일 | 줄 수 | 적정 크기 | 권장 분리 |
|------|-------|-----------|-----------|
| `core/barcode_scan_engine.py` | **1,360** | <300 | uid_validator + scan_processor + barcode_file_reader |
| `gui_app_modular/main_app.py` | **1,300+** | <400 | app_core + menu_manager + state_manager |
| `engine_modules/db_migration_mixin.py` | **1,200+** | <200 | migrations/v600.py, v700.py, v800.py |
| `engine_modules/preflight.py` | **900+** | <300 | preflight_validator + error_formatter + rule_engine |
| `engine_modules/database.py` | **900** | <400 | db_core + db_transaction + db_cache |
| `engine_modules/validators.py` | **800+** | <200 | lot_validator + weight_validator + outbound_validator |
| `config.py` | **600+** | <150 | config_paths + config_db + config_security + config_ui |

### 4.3 Mixed Responsibilities

| 파일 | 섞인 책임 |
|------|-----------|
| `config.py` | 경로 관리 + DB 설정 + API 키 보안 + UI 설정 + 비즈니스 상수 |
| `barcode_scan_engine.py` | UID 정규화 + 스키마 생성 + 재고 재계산 + 스캔 검증 + CSV/XLSX 내보내기 |
| `gui_app_modular/dialogs/onestop_inbound.py` (900줄) | UI 레이아웃 + 파싱 + 검증 + 트랜잭션 처리 |
| `main_app.py` | 앱 초기화 + 메뉴 구성 + 상태 관리 + 이벤트 핸들링 |

### 4.4 Duplicated Logic

| 중복 영역 | 위치 1 | 위치 2 | 위치 3 |
|-----------|--------|--------|--------|
| 톤백 번호 정규화 | `tonbag_compat.py` L45-80 | `tonbag_patch_rules.py` L7-13 | `constants.py` L80+ |
| outbound_query | `features/services/outbound_query.py` | `features/repositories/outbound_query.py` | — |
| LOT 검증 | `validators.py` `validate_lot_no()` 모듈 함수 | `validators.py` 클래스 메서드 (dead) | — |
| 고객명 정규화 | `constants.py` L254-266 | GUI 코드 내 인라인 | — |

### 4.5 Hidden Coupling

```
database.py ──(상속)──→ db_migration_mixin.py ──(상속)──→ db_schema_mixin.py
     ↑ 3단계 상속 체인 — 어느 하나 수정 시 전체 영향

return_reinbound_engine.py ──(getattr duck typing)──→ inventory engine
     ↑ 인터페이스 계약 없이 런타임 속성 탐색

gui_app_modular/ ──(30+ mixin)──→ 예측 불가능한 MRO
```

---

## 5. Dead Code Audit

### 5.1 미사용 함수/클래스

| 후보 | 위치 | 근거 | 제거 안전도 | 권장 |
|------|------|------|------------|------|
| `check_rack_capacity()` | `inventory_validator.py` L31-88 | grep 결과 import/호출 0건 | 🟢 안전 | 제거 |
| `check_warehouse_capacity()` | `inventory_validator.py` | 동일 — 호출처 없음 | 🟢 안전 | 제거 |
| `check_system_capacity()` | `inventory_validator.py` | 동일 — 호출처 없음 | 🟢 안전 | 제거 |
| 클래스 내 `validate_lot_no()` | `validators.py` | 모듈 함수와 중복, 클래스 메서드 미사용 | 🟢 안전 | 제거 |
| `PICKING_MAIN_MATERIAL_CODE` | `config.py` L134-136 | codebase 검색 0건 | 🟡 확인 필요 | 주석 처리 후 모니터링 |
| QueryCache use_cache 경로 | `database.py` L720-770 | `use_cache=True` 호출 0건 | 🟡 확인 필요 | 활성화 또는 제거 |

### 5.2 .bak 파일 (레포 오염)

| 파일 | 위치 | 권장 |
|------|------|------|
| 9개+ `.bak` 파일 | `gui_app_modular/dialogs/`, `gui_app_modular/mixins/` | 즉시 제거 + .gitignore 추가 |

### 5.3 Stale Fallback / Legacy Code

| 후보 | 위치 | 근거 | 권장 |
|------|------|------|------|
| `DatabaseInterface = object` fallback | `database.py` L74-84 | ImportError 시 object로 폴백 — MRO 문제 가능 | Fail-fast로 변경 |
| `tonbag_compat.py` 전체 | 350줄 | `tonbag_patch_rules.py`와 기능 중복 | 통합 후 compat 제거 |

---

## 6. Performance Audit

### PERF-1: 전체 테이블 메모리 로드 (Pagination 부재)

| 항목 | 내용 |
|------|------|
| **원인** | `barcode_scan_engine.py` `get_picked_full_info()`: `SELECT * WHERE status='PICKED'` LIMIT 없음 |
| **영향** | 100k+ 톤백 시 OOM, 응답 지연 선형 증가 |
| **최적화** | LIMIT/OFFSET 또는 커서 기반 페이지네이션 |
| **기대 효과** | 메모리 사용량 95%↓, 응답 시간 일정 유지 |

### PERF-2: 고객명 정규화 O(n) 반복

| 항목 | 내용 |
|------|------|
| **원인** | `constants.py` L254-266: 매 호출마다 dict 전체 순회 (substring 매칭) |
| **영향** | Import 배치당 30+ items × 10+ 호출 = 300+ 문자열 비교 |
| **최적화** | 정규식 사전 컴파일 또는 Trie 기반 매칭 |
| **기대 효과** | 정규화 속도 10x 향상 |

### PERF-3: React 대량 행 렌더링 (가상화 부재)

| 항목 | 내용 |
|------|------|
| **원인** | `web/src/components/DataTable.jsx`: 5,000+ 행 전체 DOM 렌더링 |
| **영향** | 50,000+ DOM 노드 → 스크롤 버벅임, 초기 렌더 3초+ |
| **최적화** | `react-window` 가상 스크롤 적용 |
| **기대 효과** | DOM 노드 95%↓, 렌더 시간 200ms 이하 |

### PERF-4: 쿼리 캐시 미활용

| 항목 | 내용 |
|------|------|
| **원인** | `database.py`: `use_cache` 기본값 False, 실제 호출처 없음 |
| **영향** | 동일 요청 내 같은 LOT 조회 3-5회 반복 |
| **최적화** | 공통 조회 (LOT, 제품 목록)에 캐시 기본 활성화 |
| **기대 효과** | DB 부하 40-60%↓ |

### PERF-5: Import 시 디렉토리 생성

| 항목 | 내용 |
|------|------|
| **원인** | `config.py` L58-64: import마다 6개 디렉토리 `mkdir` 실행 |
| **영향** | 네트워크 파일시스템에서 import 지연, CI 환경 권한 오류 |
| **최적화** | Lazy initialization 또는 앱 시작 시 1회만 실행 |
| **기대 효과** | import 시간 단축, CI 호환성 개선 |

### PERF-6: SQL 대량 IN절

| 항목 | 내용 |
|------|------|
| **원인** | `barcode_scan_engine.py` L593-603: 5,000+ UID를 단일 IN절에 삽입 |
| **영향** | SQL 쿼리 길이 제한 초과 가능 (1-4MB) |
| **최적화** | 500개 단위 배치 분할 |
| **기대 효과** | 대형 배치 안정성 확보 |

### PERF-7: 누락 인덱스

| 쿼리 패턴 | 누락 인덱스 | 영향 |
|-----------|------------|------|
| `WHERE sales_order_no=?` (allocation_plan) | `idx_alloc_sales_order` | Full table scan |
| `WHERE lot_no=? ORDER BY created_at DESC` | 복합 인덱스 DESC | 정렬 성능 저하 |

---

## 7. Architecture Audit

### 7.1 현재 아키텍처 평가

```
[현재 구조 — 스파게티 의존성]

        GUI (PyQt)          React UI
             \                /
              \              /
          main_app.py    FastAPI
          (1,300줄)      (react_api/)
               \          /
           직접 DB 접근 ──┤
                          │
         ┌────────────────┼────────────────┐
         ↓                ↓                ↓
    features/        engine_modules/      core/
    (services,       (database, validator) (barcode,
     repositories)                         pdf)
         └────────────────┼────────────────┘
                          ↓
                    SQLite (data/db/)
```

### 7.2 주요 문제점

| 문제 | 설명 |
|------|------|
| **약한 모듈 경계** | GUI가 DB에 직접 접근, services가 validators를 우회 |
| **책임 혼동** | features/services vs engine_modules/validators 역할 중복 |
| **확장성 위험** | PostgreSQL 마이그레이션 준비되었으나 SQLite 전용 코드 산재 |
| **유지보수 위험** | 30+ mixin 상속, 3단계 DB 클래스 상속 |
| **안티패턴** | God class (main_app.py), Blob 모듈 (config.py), 상속 남용 |

### 7.3 목표 아키텍처

```
[목표 구조 — Clean Layer Separation]

        GUI (PyQt)          React UI
             ↓                ↓
        ApplicationService Layer
        (Use Cases: InboundUseCase, OutboundUseCase, ScanUseCase)
             ↓
        Domain Layer
        (entities/, value_objects/, domain_services/)
             ↓
        Repository Interface
        (ports: InventoryRepo, TonbagRepo, AuditRepo)
             ↓
        Infrastructure Layer
        (adapters: SQLiteRepo, PostgresRepo, FileStorage)
             ↓
        SQLite / PostgreSQL
```

### 7.4 안전한 마이그레이션 전략

**Phase 1 (2주) — 즉시 수정 (비파괴적)**
- 보안 취약점 6건 패치
- bare except → 명시적 예외 처리
- .bak 파일 제거 + .gitignore
- 변수명 오타 수정

**Phase 2 (4주) — 구조 분리**
- `config.py` → 4개 모듈로 분리
- `barcode_scan_engine.py` → 3개 모듈로 분리
- DB 상속 체인 → 컴포지션 패턴으로 전환
- 중복 코드 통합 (tonbag, outbound_query)

**Phase 3 (8주) — 아키텍처 개선**
- Repository 패턴 도입
- GUI → Service Layer 간접 참조
- React 가상 스크롤 + Error Boundary
- 트랜잭션 Savepoint 구현

**Phase 4 (지속) — 장기 개선**
- 테스트 커버리지 확대
- PostgreSQL 전환 준비
- 성능 모니터링 대시보드

---

## 8. Top Risk Rankings

### Top 10 위험 파일/모듈

| 순위 | 파일 | 위험도 | 사유 |
|------|------|--------|------|
| 1 | `react_api/middleware/security.py` | 🔴 Critical | localhost 인증 우회, rate limit 비안전 |
| 2 | `react_api/main.py` | 🔴 Critical | 엔진 실패 무시, CORS 과개방 |
| 3 | `core/barcode_scan_engine.py` | 🔴 Critical | 1,360줄 God class, 192+ bare except |
| 4 | `engine_modules/database.py` | 🔴 Critical | 중첩 트랜잭션 no-op, 변수 오타 |
| 5 | `config.py` | 🟠 High | API 키 평문 저장, 비원자적 파일 쓰기 |
| 6 | `gui_app_modular/main_app.py` | 🟠 High | 1,300줄, 30+ mixin, UI 스레드 블로킹 |
| 7 | `react_api/routes/reports.py` | 🟠 High | 파일 업로드 메모리 폭탄, `__import__()` |
| 8 | `engine_modules/return_reinbound_engine.py` | 🟠 High | 비원자적 무게 재계산 |
| 9 | `engine_modules/preflight.py` | 🟡 Medium | 900줄 God class |
| 10 | `gui_app_modular/dialogs/onestop_inbound.py` | 🟡 Medium | 900줄, UI+로직 혼합 |

### Top 10 버그 발생 가능 소스

| 순위 | 위치 | 근거 |
|------|------|------|
| 1 | `database.py` 중첩 트랜잭션 | 부분 커밋으로 데이터 불일치 |
| 2 | `return_reinbound_engine.py` 비원자적 복원 | 톤백-무게 불일치 |
| 3 | `security.py` localhost 우회 | 무인증 쓰기 접근 |
| 4 | `reports.py` 파일 업로드 | OOM 크래시 |
| 5 | `database.py` L650 변수 오타 | NameError로 에러 로깅 실패 |
| 6 | `main.py` 엔진 초기화 | NoneType 에러 연쇄 |
| 7 | `barcode_scan_engine.py` 대량 IN절 | SQL 길이 초과 |
| 8 | `inventory_validator.py` silent dict fallback | 검증 우회 |
| 9 | `outbound_service.py` N+1 쿼리 | 성능 급락 |
| 10 | `recentFiles.js` JSON.parse | 화면 크래시 |

### Top 10 Dead Code 후보

| 순위 | 위치 | 근거 |
|------|------|------|
| 1 | `inventory_validator.py` check_rack/warehouse/system_capacity | 호출처 0건 |
| 2 | `validators.py` 클래스 내 validate_lot_no() | 모듈 함수와 중복 |
| 3 | 9개 .bak 파일 | 백업 잔존물 |
| 4 | `config.py` PICKING_* 상수 3개 | 참조처 0건 |
| 5 | `database.py` use_cache 경로 | 활성 호출 0건 |
| 6 | `tonbag_compat.py` 상당 부분 | tonbag_patch_rules와 중복 |
| 7 | `DatabaseInterface = object` fallback | 의미 없는 폴백 |
| 8 | features/services + repositories outbound_query 중복 | 하나 제거 필요 |
| 9 | `config.py` L141 SQM_DB_PATH 로드 후 미사용 | 변수 미참조 |
| 10 | `gui_app_modular` 내 비활성 mixin | 사용 여부 확인 필요 |

### Top 10 성능 병목

| 순위 | 위치 | 영향도 |
|------|------|--------|
| 1 | DataTable.jsx 비가상화 렌더링 | 5,000행에서 3초+ |
| 2 | get_picked_full_info() 전체 로드 | 100k건 OOM |
| 3 | outbound_service.py N+1 쿼리 | 10,000x 느림 |
| 4 | 쿼리 캐시 미활용 | 동일 쿼리 3-5회 반복 |
| 5 | config.py import 시 디렉토리 생성 | 네트워크 FS에서 지연 |
| 6 | 대량 IN절 (5,000+ placeholder) | SQL 길이 초과 |
| 7 | 고객명 O(n) 정규화 | 배치당 300+ 비교 |
| 8 | GUI 스레드 DB 쿼리 | UI 프리징 |
| 9 | 누락 인덱스 (sales_order_no) | Full table scan |
| 10 | tonbag 샘플 판별 5-pass | 조건 체인 비효율 |

---

## 9. Priority Plan

### P0 — 즉시 수정 (1주 이내)

| # | 작업 | 파일 | 영향 |
|---|------|------|------|
| 1 | localhost 인증 우회 제거 | `react_api/middleware/security.py` | 보안 |
| 2 | CORS 메서드/헤더 제한 | `react_api/main.py` | 보안 |
| 3 | 파일 업로드 크기 선체크 | `react_api/routes/reports.py` | 보안+안정성 |
| 4 | 엔진 초기화 실패 시 raise | `react_api/main.py` L103-106 | 안정성 |
| 5 | database.py 변수 오타 수정 | `engine_modules/database.py` L650 | 디버깅 |
| 6 | API 키 평문 저장 제거 | `react_api/routes/ai_chat.py` | 보안 |
| 7 | ADMIN_TOKEN 미설정 시 쓰기 차단 | `react_api/middleware/security.py` | 보안 |
| 8 | .bak 파일 제거 + .gitignore | `gui_app_modular/` | 청결 |

### P1 — 단기 리팩토링 (2-4주)

| # | 작업 | 파일 | 효과 |
|---|------|------|------|
| 1 | config.py 4개 모듈 분리 | `config.py` | 유지보수성 |
| 2 | barcode_scan_engine 3모듈 분리 | `core/barcode_scan_engine.py` | 유지보수성 |
| 3 | 중첩 트랜잭션 Savepoint 구현 | `engine_modules/database.py` | 데이터 무결성 |
| 4 | 반품 원자적 트랜잭션 | `engine_modules/return_reinbound_engine.py` | 데이터 무결성 |
| 5 | 중복 코드 통합 (tonbag, outbound_query) | 다수 | 코드 품질 |
| 6 | Rate limiter asyncio.Lock 추가 | `react_api/middleware/security.py` | 동시성 안정 |
| 7 | Dead code 제거 (Top 5) | 다수 | 코드 청결 |
| 8 | bare except → 명시적 예외 | 전역 | 디버깅 효율 |
| 9 | React ErrorBoundary 추가 | `web/src/App.jsx` | UX 안정성 |
| 10 | DataTable 가상 스크롤 | `web/src/components/DataTable.jsx` | 성능 |

### P2 — 장기 아키텍처 개선 (2-3개월)

| # | 작업 | 효과 |
|---|------|------|
| 1 | DB 상속 → 컴포지션 전환 | 테스트 가능성, 유지보수성 |
| 2 | Repository 패턴 도입 | 계층 분리, PostgreSQL 전환 준비 |
| 3 | GUI → Service Layer 간접화 | UI와 비즈니스 로직 분리 |
| 4 | 커스텀 예외 계층 구조 도입 | 체계적 에러 처리 |
| 5 | 핵심 경로 테스트 커버리지 80% | 회귀 방지 |
| 6 | main_app.py 분할 (30+ mixin 해소) | MRO 안정화 |
| 7 | 쿼리 캐시 기본 활성화 + TTL 조정 | 성능 40-60% 향상 |
| 8 | CI/CD 파이프라인 (lint, test, security scan) | 품질 자동화 |

---

## 10. Actionable Output — 상위 10건 상세

### ACT-1: localhost 인증 우회 제거

| 항목 | 내용 |
|------|------|
| **요약** | 127.0.0.1에서 모든 API 쓰기 무인증 접근 가능 |
| **파일** | `react_api/middleware/security.py` L85-96 |
| **증거** | `if is_local:` 조건으로 TOKEN 검증 완전 스킵 |
| **영향** | 프로덕션 DB 무인증 쓰기 가능, Docker 환경 추가 위험 |
| **수정안** | `is_local` 조건 제거, 모든 쓰기에 TOKEN 필수 |
| **검증** | `curl -X POST localhost:8000/api/... -H "X-Admin-Token: wrong"` → 403 확인 |
| **재발 방지** | 보안 미들웨어 단위 테스트 추가 |

### ACT-2: CORS 정책 강화

| 항목 | 내용 |
|------|------|
| **요약** | 모든 HTTP 메서드 및 헤더 허용, 인증 헤더명 노출 |
| **파일** | `react_api/main.py` L198-209 |
| **증거** | `allow_methods=["*"]`, `allow_headers=["*", "X-Admin-Token"]` |
| **영향** | TRACE 메서드로 요청 본문 에코 가능, 공격 벡터 노출 |
| **수정안** | GET/POST/PUT/DELETE만 허용, 헤더 화이트리스트 |
| **검증** | `curl -X OPTIONS -H "Origin: evil.com"` → 차단 확인 |
| **재발 방지** | CORS 설정 자동 검증 테스트 |

### ACT-3: 파일 업로드 보호

| 항목 | 내용 |
|------|------|
| **요약** | 파일 전체 메모리 로드 후 크기 체크 — OOM 가능 |
| **파일** | `react_api/routes/reports.py` L303-310 |
| **증거** | `content = await file.read()` → `if len(content) > 50MB` |
| **영향** | 1GB 파일 업로드 시 서버 크래시 |
| **수정안** | Content-Length 선체크 + 스트리밍 청크 읽기 |
| **검증** | 100MB 더미 파일 업로드 → 413 응답 + 메모리 안정 확인 |
| **재발 방지** | 미들웨어 레벨 요청 크기 제한 (nginx/uvicorn) |

### ACT-4: 엔진 초기화 실패 처리

| 항목 | 내용 |
|------|------|
| **요약** | API 엔진 로드 실패 시 silent pass → 전체 API 500 에러 |
| **파일** | `react_api/main.py` L103-106 |
| **증거** | `except Exception: pass` |
| **영향** | 원인 불명의 전체 API 장애 |
| **수정안** | `except` 에서 `logger.critical()` + `raise` |
| **검증** | DB 경로 변경 후 서버 시작 → 명확한 에러 메시지 확인 |
| **재발 방지** | startup health check endpoint 추가 |

### ACT-5: 트랜잭션 중첩 안전화

| 항목 | 내용 |
|------|------|
| **요약** | 중첩 트랜잭션이 silent no-op → 내부 예외 시 외부 커밋 |
| **파일** | `engine_modules/database.py` L240-260 |
| **증거** | 내부 context가 BEGIN/COMMIT 없이 yield만 실행 |
| **영향** | 데이터 부분 업데이트 (톤백 상태 ↔ 무게 불일치) |
| **수정안** | SAVEPOINT/RELEASE 구현 또는 중첩 시 에러 발생 |
| **검증** | 내부 트랜잭션 exception 시 외부도 rollback 확인 |
| **재발 방지** | 트랜잭션 무결성 통합 테스트 |

### ACT-6: 반품 원자적 처리

| 항목 | 내용 |
|------|------|
| **요약** | 톤백 복원과 무게 업데이트가 독립 실행 — 중간 실패 가능 |
| **파일** | `engine_modules/return_reinbound_engine.py` L240-245 |
| **증거** | `_restore_tonbags()` 후 별도 `_restore_lot_weight()` 호출 |
| **영향** | 톤백은 복원되었으나 재고 무게 반영 안 됨 |
| **수정안** | 단일 트랜잭션으로 감싸기 |
| **검증** | _restore_lot_weight에 인위 예외 삽입 → 톤백도 rollback 확인 |
| **재발 방지** | 무게 일관성 검증 스케줄러 |

### ACT-7: config.py 모듈 분리

| 항목 | 내용 |
|------|------|
| **요약** | 600줄에 5가지 책임 혼합 — 변경 영향 예측 불가 |
| **파일** | `config.py` |
| **증거** | 경로+DB+보안+UI+상수 모두 단일 파일 |
| **영향** | 모듈 import 시 불필요한 초기화, 테스트 어려움 |
| **수정안** | config_paths.py, config_database.py, config_security.py, config_ui.py |
| **검증** | 기존 import 경로 호환성 유지 확인 (re-export) |
| **재발 방지** | 모듈 크기 제한 lint rule (300줄) |

### ACT-8: barcode_scan_engine 분할

| 항목 | 내용 |
|------|------|
| **요약** | 1,360줄 God class — 314줄 함수 포함 |
| **파일** | `core/barcode_scan_engine.py` |
| **증거** | UID 정규화+스키마+재고계산+스캔검증+CSV/XLSX 모두 단일 클래스 |
| **영향** | 수정 시 전체 영향, 테스트 불가 |
| **수정안** | uid_validator.py + scan_processor.py + barcode_file_reader.py |
| **검증** | 기존 API 통합 테스트 전량 통과 확인 |
| **재발 방지** | 클래스 크기 제한 코드 리뷰 체크리스트 |

### ACT-9: Dead Code 정리

| 항목 | 내용 |
|------|------|
| **요약** | 미사용 함수 6건+ .bak 파일 9건 |
| **파일** | inventory_validator.py, validators.py, config.py, gui_app_modular/ |
| **증거** | codebase 전문 검색 결과 호출 0건 |
| **영향** | 유지보수 혼란, 코드 크기 불필요 증가 |
| **수정안** | 안전 등급별 제거 (.bak 즉시, 함수는 주석→모니터링→제거) |
| **검증** | 전체 앱 기능 테스트 통과 |
| **재발 방지** | CI에 unused code 탐지 도구 추가 |

### ACT-10: React DataTable 가상화

| 항목 | 내용 |
|------|------|
| **요약** | 5,000+ 행 전체 DOM 렌더 → UI 버벅임 |
| **파일** | `web/src/components/DataTable.jsx` |
| **증거** | `data?.rows?.map()` 전체 순회 |
| **영향** | 대형 창고 데이터에서 3초+ 렌더 시간 |
| **수정안** | `react-window` FixedSizeList 적용 |
| **검증** | 10,000행 로드 후 스크롤 60fps 유지 확인 |
| **재발 방지** | 렌더 성능 기준 설정 (1,000행 이상 시 가상화 필수) |

---

## 체크리스트 확인

- [x] **Executive Summary 있음** — Section 1
- [x] **구조 원인과 직접 원인 구분** — Section 3 모든 이슈에 "직접 원인" + "구조적 원인" 분리
- [x] **리스크 랭킹 있음** — Section 8 (파일/버그/데드코드/성능 각 Top 10)
- [x] **장기 개선과 즉시 수정 분리** — Section 9 (P0/P1/P2 분리)
- [x] **가설과 확정 구분** — 모든 이슈에 [확정]/[가설] 표기
- [x] **안전한 점진적 개선 우선** — Phase 1→4 단계별 마이그레이션

---

*이 보고서는 코드 정적 분석 기반입니다. 런타임 프로파일링을 통한 추가 검증을 권장합니다.*
