# GPT_SQM_P0-1_수정대상파일표.md
생성일: 2026-04-04 15:08 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
참조 문서: `MASTER_FINAL_v867_통합완성본.md`, `GPT_SQM_P0-1_초상세_작업지시서.md`

---

## [질문]
다음 단계로 `P0-1_수정대상파일표.md`를 작성해 달라는 요청

## [질문의도]
P0-1 단계에서 실제로 손대야 할 파일을  
**수정 / 신규 생성 / 참조 전용 / 고위험 주의 파일**로 구분해서 고정한다.

이번 문서의 목적은 아래와 같다.

```text
1. P0-1 범위에서 실제 변경 파일을 확정한다
2. P0-2/P0-3/P0-4와 섞이지 않게 선을 긋는다
3. 어디까지 수정하고 어디는 아직 건드리지 말아야 하는지 명확히 한다
4. Claude Code / Cursor / 수동 패치 모두 같은 기준으로 움직이게 한다
```

---

# [응답]

# 1. 분류 원칙

이번 파일표는 아래 4개 분류로 나눈다.

| 분류 | 의미 | P0-1에서의 원칙 |
|---|---|---|
| **A. 직접 수정 파일** | 기존 파일을 실제 수정해야 함 | P0-1에서 수정 가능 |
| **B. 신규 생성 파일** | 이번 단계에서 새로 만들어야 함 | P0-1에서 생성 가능 |
| **C. 참조 전용 파일** | 읽고 구조/연결만 파악 | P0-1에서 원칙적으로 수정 금지 |
| **D. 고위험 주의 파일** | 잘못 건드리면 전체 동작 흔들림 | P0-1에서는 최소 수정 또는 조사만 |

---

# 2. P0-1 전체 범위 한 줄 요약

```text
P0-1은 구조를 고정하는 단계다.
즉, App 삽입 위치, actions router, skeleton file, DB 로그 테이블, 실행 파일 연결 구조까지만 다루고,
실제 입고/출고 동작 로직 변경은 아직 본격적으로 하지 않는다.
```

---

# 3. A. 직접 수정 파일 목록

## A-1. Frontend 직접 수정 파일

| 파일 | 현재 역할 | P0-1 작업 | 우선순위 | 비고 |
|---|---|---|---|---|
| `web/src/App.jsx` | React 메인 라우팅 / 상단 네비게이션 | 메뉴바/모달 삽입 슬롯 확보, import 등록 | 매우 높음 | P0-1 핵심 |
| `web/src/api/` 내 기존 API 래퍼 파일 | 현재 GET API 호출 | `actionApi.js` 연결 방식 참고 후 필요시 공통 helper 정리 | 중간 | 기존 스타일 유지 필요 |

### A-1 세부 지시
#### `web/src/App.jsx`
- [ ] 현재 Route / NavLink 구조 확인
- [ ] `TopMenuBar` import 위치 확보
- [ ] `LotDetailModal`, `InboundParseModal`, `OutboundExecuteModal` import 위치 확보
- [ ] 아직 실제 연결이 아니더라도 placeholder mount 가능 구조 확보
- [ ] 기존 페이지 라우팅을 깨지 않도록 유지

---

## A-2. Backend 직접 수정 파일

| 파일 | 현재 역할 | P0-1 작업 | 우선순위 | 비고 |
|---|---|---|---|---|
| `react_api/main.py` | FastAPI 진입점 | `actions` router 등록, import 정리 | 매우 높음 | P0-1 핵심 |
| `react_api/routes/__init__.py` (존재 시) | 라우트 패키지 정리 | `actions` export 반영 여부 확인 | 중간 | 없으면 생략 가능 |
| `run_react.bat` | React/API 실행 배치 | 현재 실행 흐름 조사, 수정 필요 여부 메모 또는 최소 보정 | 높음 | P0-1 후반 |
| `run_react_api.py` | API 실행 진입점 | host/port/env 로드 방식 점검 | 중간 | 직접 수정 가능성 있음 |
| `run.py` | Tkinter 앱 진입점 | 역할 조사, 필요시 충돌 메모 수준 수정 | 낮음 | P0-1에선 최소 |
| `run_bootstrap.py` | 초기화/부트스트랩 | 역할 조사, 필요시 주석/메모성 보정 | 낮음 | P0-1에선 최소 |

### A-2 세부 지시
#### `react_api/main.py`
- [ ] 기존 router include 방식 확인
- [ ] `actions.py` 등록
- [ ] import 순환 없는지 확인
- [ ] `/docs` 기준 엔드포인트 노출 가능 상태 확보

#### `run_react.bat`
- [ ] 현재 API/Frontend 기동 순서 확인
- [ ] 필요 시 주석 보강
- [ ] 포트/경로/로그 유지 방식 확인
- [ ] 아직 대규모 개편은 금지

---

# 4. B. 신규 생성 파일 목록

## B-1. Frontend 신규 생성 파일

| 파일 | 역할 | P0-1 작업 내용 | 우선순위 |
|---|---|---|---|
| `web/src/components/TopMenuBar.jsx` | 상단 메뉴바 skeleton | placeholder + props + 기본 구조 | 매우 높음 |
| `web/src/components/modals/LotDetailModal.jsx` | LOT 상세 모달 skeleton | open/onClose/lotNo props + placeholder | 매우 높음 |
| `web/src/components/modals/InboundParseModal.jsx` | 입고 파싱 모달 skeleton | upload/preview/confirm placeholder | 매우 높음 |
| `web/src/components/modals/OutboundExecuteModal.jsx` | 출고 실행 모달 skeleton | quantity/destination/submit placeholder | 매우 높음 |
| `web/src/api/actionApi.js` | write API 전용 래퍼 | upload/create/execute/cancel/location 함수 틀 | 매우 높음 |

### B-1 생성 기준
- [ ] 파일은 모두 import 가능한 상태여야 한다
- [ ] placeholder만 있어도 빌드가 깨지지 않아야 한다
- [ ] props 이름은 P0-2/P0-3에서 재사용 가능해야 한다
- [ ] 기존 스타일 체계를 크게 해치지 않아야 한다

---

## B-2. Backend 신규 생성 파일

| 파일 | 역할 | P0-1 작업 내용 | 우선순위 |
|---|---|---|---|
| `react_api/routes/actions.py` | write API 라우터 | endpoint 선언 + placeholder 응답 | 매우 높음 |
| `react_api/schemas/actions.py` | 요청/응답 schema | request/response model skeleton | 매우 높음 |
| `react_api/services/action_service.py` | route-service 중간 계층 | transaction/validation/logging 자리 확보 | 매우 높음 |
| `react_api/services/engine_adapter.py` | engine 래퍼 | process_inbound/outbound/cancel wrapper 자리 확보 | 매우 높음 |
| `react_api/services/__init__.py` (필요 시) | 패키지 인식 | import 안정화 | 중간 |
| `react_api/schemas/__init__.py` (필요 시) | 패키지 인식 | import 안정화 | 중간 |

### B-2 생성 기준
- [ ] `python -m py_compile` 통과
- [ ] router import 통과
- [ ] schema import 통과
- [ ] service ↔ adapter 참조 방향 단순화
- [ ] 아직 실제 engine call이 없어도 파일 구조는 안정적이어야 함

---

# 5. C. 참조 전용 파일 목록

이 파일들은 P0-1에서 **반드시 읽어야 하지만 원칙적으로 수정하지 않는다.**

## C-1. Frontend 참조 전용

| 파일/경로 | 참조 목적 | P0-1 원칙 |
|---|---|---|
| `web/src/pages/` 전체 | 현재 페이지 구조 파악 | 수정 금지, 구조만 파악 |
| `web/src/components/DataTable.jsx` | 공통 컴포넌트 스타일 참고 | 수정 금지 |
| `web/src/api/inventoryApi.js` | 기존 API 래퍼 스타일 참고 | 가능하면 수정 금지 |
| `web/src/api/tabsApi.js` | 기존 GET 호출 규칙 참고 | 가능하면 수정 금지 |

---

## C-2. Backend 참조 전용

| 파일/경로 | 참조 목적 | P0-1 원칙 |
|---|---|---|
| `react_api/routes/inventory.py` | 기존 router 작성 스타일 참고 | 수정 금지 |
| `react_api/routes/dashboard.py` | 응답 형식 / 라우터 등록 스타일 참고 | 수정 금지 |
| `react_api/routes/tabs.py` | 기존 route layout 참고 | 수정 금지 |
| `engine_modules/inventory_modular/query_mixin.py` | LOT 조회 / 조회 계열 함수 확인 | 수정 금지 |
| `engine_modules/inventory_modular/inbound_mixin.py` | 입고 처리 함수 위치 확인 | 수정 금지 |
| `engine_modules/inventory_modular/outbound_mixin.py` | 출고/취소 함수 위치 확인 | 수정 금지 |
| `engine_modules/inventory_modular/tonbag_mixin.py` | 위치 변경 함수 위치 확인 | 수정 금지 |

---

## C-3. DB / 설정 참조 전용

| 파일/경로 | 참조 목적 | P0-1 원칙 |
|---|---|---|
| `data/db/sqm_inventory.db` | 실제 스키마 조회 | 직접 수정 금지 |
| `.env` | 환경변수 구조 파악 | 원칙적으로 수정 금지, 위치/키만 파악 |
| `.env.example` 또는 config 파일 | 설정 체계 파악 | 수정 금지 |

---

# 6. D. 고위험 주의 파일 목록

이 파일들은 수정 가능성이 있더라도 **매우 조심해서 다뤄야 한다.**

| 파일 | 위험 이유 | P0-1 원칙 |
|---|---|---|
| `engine_modules/inventory_modular/outbound_mixin.py` | 핵심 상태 전이 / DB 영향 큼 | 절대 직접 수정 금지 |
| `engine_modules/inventory_modular/inbound_mixin.py` | 입고 생성 핵심 로직 | 절대 직접 수정 금지 |
| `run.py` | Tkinter 전체 기동 | 조사 우선, 최소 수정 |
| `run_bootstrap.py` | 초기화 실패 시 전체 기동 영향 | 조사 우선, 최소 수정 |
| `data/db/sqm_inventory.db` | 실DB 손상 위험 | 직접 수정 금지 |
| `react_api/main.py` | API 전체 진입점 | 최소 범위 수정 원칙 |

---

# 7. P0-1 수정 대상 우선순위

## 7-1. 최우선(즉시 작업)
```text
1. react_api/main.py
2. web/src/App.jsx
3. react_api/routes/actions.py
4. react_api/schemas/actions.py
5. react_api/services/action_service.py
6. react_api/services/engine_adapter.py
7. web/src/api/actionApi.js
8. TopMenuBar / 3개 Modal skeleton
```

## 7-2. 그 다음
```text
9. run_react.bat
10. run_react_api.py
11. routes/__init__.py, services/__init__.py, schemas/__init__.py (필요 시)
```

## 7-3. P0-1에서는 조사만
```text
12. run.py
13. run_bootstrap.py
14. engine_modules/inventory_modular/*
15. data/db/sqm_inventory.db
16. .env / config 계열
```

---

# 8. 파일별 작업 한계선

## 8-1. 여기까지는 해도 된다
- skeleton 파일 생성
- router 등록
- placeholder 응답 구현
- App import 추가
- DB 스키마 조회
- bat/env 구조 분석
- 실행 경로 주석/메모 보강

## 8-2. 아직 하면 안 된다
- engine 로직 본문 수정
- DB 직접 마이그레이션 실행
- 실제 입고/출고 side effect 발생시키는 코드 작성
- parser 실연결 구현
- Tkinter UI 구조 직접 변경
- 전체 배치 실행 흐름 대수술

---

# 9. 실제 작업 순서

## Step 1
- [ ] `react_api/main.py` 확인
- [ ] `App.jsx` 확인
- [ ] 기존 routes/pages/api 구조 표 작성

## Step 2
- [ ] Frontend skeleton 파일 생성
- [ ] Backend skeleton 파일 생성

## Step 3
- [ ] `react_api/main.py`에 `actions` router 등록
- [ ] `App.jsx`에 placeholder import 구조 반영

## Step 4
- [ ] DB 스키마(`audit_log`, `outbound_event_log`) 점검표 작성
- [ ] `run.py`, `run_bootstrap.py`, `run_react.bat`, `.env` 관계 표 작성

## Step 5
- [ ] py_compile
- [ ] import test
- [ ] `/docs` 노출 여부 확인
- [ ] Frontend build/import 오류 확인

---

# 10. 완료 기준

P0-1 수정대상파일표 기준 완료는 아래와 같다.

- [ ] 수정 파일과 신규 파일이 구분되었다
- [ ] 참조 전용 파일과 위험 파일이 구분되었다
- [ ] 우선순위가 확정되었다
- [ ] 작업 한계선이 명확하다
- [ ] 다음 단계(P0-1 DB스키마점검표, 실행파일연동점검표)로 자연스럽게 이어질 수 있다

---

# 11. 루비 최종 판단

이번 파일표의 핵심은 아래 한 줄이다.

```text
P0-1에서는 '어디를 손댈지'를 먼저 고정해야 한다.
이 단계에서 범위가 흐려지면,
P0-2/P0-3/P0-4에서 React, FastAPI, engine, DB, run script가 한꺼번에 엉키게 된다.
```

---

# 12. 다음 단계 권장

다음으로 이어질 가장 적절한 문서는 아래 2개다.

1. `P0-1_DB스키마점검표.md`
2. `P0-1_실행파일연동점검표.md`

루비 권장 순서는 아래다.

```text
1) DB스키마점검표
2) 실행파일연동점검표
```
