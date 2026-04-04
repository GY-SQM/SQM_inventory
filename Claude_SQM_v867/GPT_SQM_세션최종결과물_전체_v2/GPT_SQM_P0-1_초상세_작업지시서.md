# GPT_SQM_P0-1_초상세_작업지시서.md
생성일: 2026-04-04 15:03 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip` / 참조: `MASTER_FINAL_v867_통합완성본.md`

---

## [질문]
867 React를 864 Tkinter 수준으로 끌어올리기 위한 작업 중,  
**P0-1만 따로 떼어 초상세 작업지시서**를 작성해 달라는 요청

## [질문의도]
이번 문서는 P0 전체를 다루지 않는다.  
오직 **P0-1 = 구조 준비 + DB 스키마 점검 + 실행 파일 연동 준비**만 다룬다.

즉, 이번 단계의 목표는 아래와 같다.

```text
1. 실제 v867 구조를 재확정한다
2. React/FastAPI/write API를 얹을 수 있는 skeleton을 만든다
3. DB 로그/이벤트 테이블 호환성을 점검한다
4. run.py / run_bootstrap.py / run_react.bat / .env 구조를 점검한다
5. P0-2 이상 단계로 넘어가도 되는 '안정된 출발점'을 만든다
```

---

# [응답]

# 1. P0-1의 위치와 의미

P0-1은 기능 구현 단계가 아니다.  
**P0-2, P0-3, P0-4가 실패하지 않게 만드는 기반 정리 단계**다.

이번 단계에서 다루는 것은 아래 4축이다.

| 축 | 목적 | 결과물 |
|---|---|---|
| 구조 조사 | 실제 수정 위치 확정 | 파일/경로 대응표 |
| skeleton 생성 | Router/Service/Schema/UI 골격 준비 | 신규 파일 뼈대 |
| DB 점검 | `audit_log`, `outbound_event_log` 호환성 확인 | 스키마 점검표 / migration 메모 |
| 실행 체계 점검 | run/bat/.env 흐름 확인 | 실행 경로 정리표 |

---

# 2. P0-1 절대 원칙

이번 단계는 아래 원칙을 강제 적용한다.

```text
- 예전 가정 구조만 믿고 수정하지 않는다
- 실제 v867 코드 구조를 먼저 조사한다
- skeleton만 만든다고 해도 import/등록 상태까지 확인한다
- DB 로그 테이블은 write API 이전에 반드시 점검한다
- run.py / run_bootstrap.py / run_react.bat / .env 위치를 먼저 확정한다
- 테스트 실패 상태에서 다음 단계(P0-2)로 넘어가지 않는다
```

---

# 3. 이번 단계의 직접 근거

이번 P0-1은 아래 기준을 근거로 한다.

1. 기준 원본은 `Claude_SQM_v867.zip`이다.  
2. 실제 상위 구조로 `engine_modules/`, `react_api/`, `web/`, `data/`, `run.py`, `run_bootstrap.py`, `run_react.bat`, `run_react_api.py`가 확인되어 있다.  
3. Recon Phase는 `gui_app_modular/`, `web/`, `react_api/`, `engine_modules/inventory_modular/`를 조사해 메뉴/모달/API/engine 연결표를 만들도록 요구한다.  
4. React 상단 메뉴바와 모달 구현, write API 추가, 기존 `engine_modules` 재사용, rollback, `.env` 분리/입력 검증/로그 강화가 요구된다.  
fileciteturn10file0 fileciteturn10file1 fileciteturn10file2 fileciteturn10file3 fileciteturn10file4

---

# 4. P0-1 최종 완료 정의

P0-1 완료는 아래 8개가 모두 충족되어야 한다.

- [ ] 실제 v867 수정 대상 파일 목록이 확정되었다
- [ ] Frontend/Backend skeleton 파일이 생성되었다
- [ ] actions router가 서버 등록 가능 상태다
- [ ] 공통 응답 포맷이 정의되었다
- [ ] `audit_log` / `outbound_event_log` 구조가 확인되었다
- [ ] migration 필요 여부가 결정되었다
- [ ] `run.py` / `run_bootstrap.py` / `run_react.bat` / `.env` 로드 위치가 정리되었다
- [ ] py_compile / import / basic start 수준 테스트가 통과했다

---

# 5. 작업 범위와 비범위

## 5-1. 이번 단계에서 한다
- 파일/경로 조사
- skeleton 생성
- DB 스키마 점검
- 실행 파일 연동 구조 점검
- 공통 응답 포맷 정리
- 기본 컴파일/등록 테스트

## 5-2. 이번 단계에서 하지 않는다
- LOT 상세 모달 실제 완성
- files/upload 실제 parser 연결
- inbound/create 실제 입고 생성
- outbound/execute / cancel 실작동
- location/update 실작동
- 전체 통합 테스트

즉, 이번 단계는 **구조를 고정하는 단계**다.

---

# 6. 실제 조사 대상 경로

## 6-1. 반드시 열어볼 경로
```text
react_api/
react_api/main.py
react_api/routes/
react_api/services/        (없으면 생성 대상)
react_api/schemas/         (없으면 생성 대상)

web/src/
web/src/App.jsx
web/src/components/
web/src/pages/
web/src/api/

engine_modules/inventory_modular/
data/db/sqm_inventory.db

run.py
run_bootstrap.py
run_react.bat
run_react_api.py
.env / .env.example / settings 관련 파일
```

## 6-2. 조사 목적
| 경로 | 조사 목적 |
|---|---|
| `react_api/main.py` | 라우터 등록 방식 확인 |
| `react_api/routes/` | 기존 GET 라우트 구조 확인 |
| `web/src/App.jsx` | 메뉴바/모달 삽입 위치 확인 |
| `web/src/api/` | 기존 API 호출 스타일 확인 |
| `engine_modules/inventory_modular/` | 재사용 함수 위치와 인자 형태 확인 |
| `data/db/sqm_inventory.db` | 로그/이벤트/감사 테이블 확인 |
| `run.py` | 메인 실행 루프 역할 확인 |
| `run_bootstrap.py` | 부트스트랩/초기화 역할 확인 |
| `run_react.bat` | API+Frontend 실행 방식 확인 |
| `.env` 관련 파일 | 환경변수 분리 방식 확인 |

---

# 7. P0-1 세부 작업지시

# 7-A. 구조 조사 단계

## 목적
실제 수정 파일과 신규 생성 파일을 확정한다.

## 작업
- [ ] `react_api/main.py`의 라우터 등록 방식을 읽는다
- [ ] 기존 routes가 어떻게 분리되어 있는지 표로 적는다
- [ ] `web/src/App.jsx`에서 현재 NavLink/Route 구조를 정리한다
- [ ] `web/src/components/`와 `web/src/pages/`의 역할을 정리한다
- [ ] `web/src/api/` 호출 방식(`fetch`, `axios`, wrapper 함수)을 정리한다
- [ ] `engine_modules/inventory_modular/`에서 아래 후보 함수 위치를 찾는다
  - [ ] `process_inbound`
  - [ ] `process_outbound`
  - [ ] `cancel_outbound_tonbag`
  - [ ] LOT 상세 조회 관련 함수
  - [ ] 위치 변경 관련 함수
- [ ] 조사 결과를 아래 표 형식으로 정리한다

## 조사 결과 기록 형식
| 구분 | 실제 파일 | 역할 | P0-1 처리 |
|---|---|---|---|
| Frontend Route | `web/src/App.jsx` | 상단 라우팅 | 수정 |
| Frontend API | `web/src/api/...` | API 래퍼 | 신규/수정 |
| Backend Main | `react_api/main.py` | FastAPI 진입 | 수정 |
| Backend Route | `react_api/routes/...` | 엔드포인트 | 신규 |
| Engine | `engine_modules/...` | 실제 로직 | 재사용 |
| DB | `data/db/sqm_inventory.db` | 스키마 | 점검 |

## 완료 기준
- [ ] 수정 대상 파일 목록 확정
- [ ] 신규 파일 생성 대상 목록 확정
- [ ] engine 연결 후보 함수 목록 확정

---

# 7-B. Frontend skeleton 생성 단계

## 목적
P0-2/P0-3에서 바로 붙일 수 있는 UI 골격을 만든다.

## 생성 대상 파일
```text
web/src/components/TopMenuBar.jsx
web/src/components/modals/LotDetailModal.jsx
web/src/components/modals/InboundParseModal.jsx
web/src/components/modals/OutboundExecuteModal.jsx
web/src/api/actionApi.js
```

## 작업
- [ ] `TopMenuBar.jsx` 생성
- [ ] `LotDetailModal.jsx` 생성
- [ ] `InboundParseModal.jsx` 생성
- [ ] `OutboundExecuteModal.jsx` 생성
- [ ] `actionApi.js` 생성
- [ ] 각 파일에 기본 export/import 구조를 넣는다
- [ ] 아직 기능이 없어도 빌드가 깨지지 않도록 placeholder를 넣는다
- [ ] `App.jsx`에 나중에 연결할 수 있도록 삽입 위치 주석 또는 슬롯을 만든다

## 최소 구현 기준
### `TopMenuBar.jsx`
- [ ] 컴포넌트 export
- [ ] props 자리 정의
- [ ] 최소 placeholder 렌더링
- [ ] 메뉴 데이터 구조를 배열로 받을 수 있는 형태 준비

### `LotDetailModal.jsx`
- [ ] open / onClose / lotNo props 자리 확보
- [ ] title/header/body/footer 기본 구조 확보
- [ ] 빈 데이터 대응 placeholder 표시

### `InboundParseModal.jsx`
- [ ] open / onClose props
- [ ] 업로드 버튼 placeholder
- [ ] preview 영역 placeholder
- [ ] confirm 버튼 placeholder

### `OutboundExecuteModal.jsx`
- [ ] open / onClose props
- [ ] quantity / destination / selection 자리 확보
- [ ] submit 버튼 placeholder

### `actionApi.js`
- [ ] `/files/upload`
- [ ] `/inbound/create`
- [ ] `/outbound/execute`
- [ ] `/outbound/cancel`
- [ ] `/location/update`
- [ ] 각 함수 이름만 먼저 안정적으로 정의
- [ ] baseURL / 에러처리 helper 자리 확보

## 완료 기준
- [ ] 새 파일 import/export 오류 없음
- [ ] App.jsx에 붙여도 빌드 오류 없음
- [ ] 다음 단계에서 실제 로직만 채우면 되는 골격 완성

---

# 7-C. Backend skeleton 생성 단계

## 목적
write API를 안전하게 붙일 수 있는 최소 백엔드 골격을 만든다.

## 생성 대상 파일
```text
react_api/routes/actions.py
react_api/schemas/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
```

## 작업
- [ ] `actions.py` 생성
- [ ] `schemas/actions.py` 생성
- [ ] `services/action_service.py` 생성
- [ ] `services/engine_adapter.py` 생성
- [ ] `react_api/main.py` 또는 등록부에 `actions` router 등록
- [ ] 공통 JSON 응답 포맷 helper 정의
- [ ] 예외 처리 전략 메모 작성

## 파일별 세부 지시

### `react_api/routes/actions.py`
- [ ] `APIRouter` 선언
- [ ] 아래 엔드포인트 자리 생성
  - [ ] `POST /files/upload`
  - [ ] `POST /inbound/create`
  - [ ] `POST /outbound/execute`
  - [ ] `PUT /outbound/cancel`
  - [ ] `PUT /location/update`
- [ ] 현재는 내부를 placeholder로 둬도 되지만 response shape는 맞춘다
- [ ] schema import 구조가 안정적인지 확인

### `react_api/schemas/actions.py`
- [ ] 업로드 요청/응답 schema
- [ ] inbound create request schema
- [ ] outbound execute request schema
- [ ] outbound cancel request schema
- [ ] location update request schema
- [ ] 공통 success response schema
- [ ] validation 에러를 나중에 확장 가능한 형태로 설계

### `react_api/services/action_service.py`
- [ ] route layer와 engine layer 사이의 중간 계층 자리 확보
- [ ] transaction start/commit/rollback 자리 주석 포함
- [ ] parser 호출 자리 주석 포함
- [ ] audit/event log 기록 자리 주석 포함

### `react_api/services/engine_adapter.py`
- [ ] engine 인스턴스 생성/주입 방식 자리 확보
- [ ] `process_inbound` wrapper 자리 확보
- [ ] `process_outbound` wrapper 자리 확보
- [ ] `cancel_outbound_tonbag` wrapper 자리 확보
- [ ] LOT 조회 wrapper 자리 확보
- [ ] 위치 변경 wrapper 자리 확보

## 완료 기준
- [ ] 서버 import 단계에서 오류 없음
- [ ] `/docs` 또는 라우터 목록에서 actions 엔드포인트 인식 가능
- [ ] schema import 오류 없음
- [ ] service/adapter 파일 참조 경로 확정

---

# 7-D. DB 스키마 점검 단계

## 목적
P0-3의 write API 단계에서 터질 가능성이 높은 DB 불일치를 미리 제거한다.

## 우선 점검 테이블
- [ ] `audit_log`
- [ ] `outbound_event_log`

## 점검 항목
### 공통
- [ ] 테이블 존재 여부
- [ ] 컬럼 목록
- [ ] PK 여부
- [ ] timestamp/datetime 컬럼 여부
- [ ] nullable 여부
- [ ] default 값 여부

### `audit_log`
- [ ] action/event/action_type 컬럼 존재 여부
- [ ] message/detail/data 컬럼 존재 여부
- [ ] created_at / timestamp 류 컬럼 존재 여부
- [ ] user/source/module 류 컬럼 존재 여부

### `outbound_event_log`
- [ ] outbound_id / tonbag_id / lot_no 관련 컬럼 존재 여부
- [ ] event_type / status 관련 컬럼 존재 여부
- [ ] created_at / event_time 관련 컬럼 존재 여부
- [ ] 취소/실행/오류 기록이 가능한 구조인지 확인

## 출력 형식
| 테이블 | 컬럼 | 존재 | 보정 필요 | 비고 |
|---|---|---|---|---|

## migration 판정
- [ ] 컬럼 누락이면 migration 필요
- [ ] 타입 불일치면 migration 필요
- [ ] default/nullability만 문제면 보정 가능 여부 검토
- [ ] migration은 지금 바로 적용하지 않아도 되지만 초안은 작성

## 완료 기준
- [ ] 두 테이블 모두 존재 여부 확인 완료
- [ ] 컬럼 mismatch 여부 확인 완료
- [ ] migration 필요 여부 결정 완료
- [ ] write API 전에 막아야 할 위험 요소 목록화 완료

---

# 7-E. 실행 파일 / 환경변수 점검 단계

## 목적
P0-4 통합 실행 전에 실행 루프가 어떻게 연결되는지 미리 확정한다.

## 점검 대상
- [ ] `run.py`
- [ ] `run_bootstrap.py`
- [ ] `run_react.bat`
- [ ] `run_react_api.py`
- [ ] `.env`
- [ ] `.env.example` 또는 settings/config 파일

## 작업
### `run.py`
- [ ] Tkinter 메인 앱 실행 진입점인지 확인
- [ ] DB 초기화/스타일/부트스트랩 호출 여부 확인
- [ ] React/API와 충돌할 수 있는 부분 메모

### `run_bootstrap.py`
- [ ] 실제로 bootstrap만 하는지
- [ ] run.py가 호출하는지
- [ ] 초기 환경검사나 DB 준비 역할이 있는지 확인

### `run_react_api.py`
- [ ] FastAPI/uvicorn 진입점인지 확인
- [ ] host/port/config 읽는 방식 확인

### `run_react.bat`
- [ ] API와 Frontend를 동시에 띄우는지 확인
- [ ] 순차 실행인지 병렬 실행인지 확인
- [ ] 로그 출력 방식 확인
- [ ] 실패 시 창이 닫히는지 유지되는지 확인

### `.env`
- [ ] 존재 여부
- [ ] 어디서 로드되는지
- [ ] API/Frontend/Tkinter가 공통 사용 가능한 값이 있는지
- [ ] 민감정보 분리 여부

## 출력 형식
| 파일 | 역할 | 현재 상태 | 수정 필요 | 비고 |
|---|---|---|---|---|

## 완료 기준
- [ ] 실행 진입점들의 관계도 작성 완료
- [ ] `.env` 로드 위치 파악 완료
- [ ] API/Frontend/Tkinter 동시 실행 시 충돌 포인트 식별 완료

---

# 8. P0-1 테스트 지시서

# 8-1. Pre-Test

## Backend
- [ ] `python -m py_compile react_api/main.py`
- [ ] `python -m py_compile react_api/routes/actions.py`
- [ ] `python -m py_compile react_api/schemas/actions.py`
- [ ] `python -m py_compile react_api/services/action_service.py`
- [ ] `python -m py_compile react_api/services/engine_adapter.py`

## Frontend
- [ ] import 경로 오류 점검
- [ ] `App.jsx` 연결 후 빌드 오류 점검
- [ ] placeholder component 렌더 오류 점검

## DB
- [ ] DB 파일 접근 가능 여부
- [ ] 스키마 조회 쿼리 실행 가능 여부

## 실행 파일
- [ ] `run.py` 구문 오류 없음
- [ ] `run_bootstrap.py` 구문 오류 없음
- [ ] `run_react_api.py` 구문 오류 없음

---

# 8-2. Post-Test

- [ ] actions router 등록 확인
- [ ] `/docs` 노출 여부 확인
- [ ] placeholder endpoint 응답 형식 확인
- [ ] Frontend skeleton import 성공 확인
- [ ] 모달 placeholder 렌더 성공 확인
- [ ] DB 스키마 점검표 작성 완료
- [ ] run/bat/.env 점검표 작성 완료

---

# 8-3. Re-Test 조건

아래 중 하나라도 실패하면 수정 후 재검사한다.

- [ ] import error
- [ ] circular import
- [ ] router 미등록
- [ ] schema validation import 실패
- [ ] DB 테이블/컬럼 확인 실패
- [ ] `.env` 로드 위치 불명확
- [ ] bat 실행 구조 불명확

---

# 9. 실패 유형별 조치

## 유형 A. import / router 오류
- [ ] 상대경로/절대경로 정리
- [ ] `__init__.py` 필요 여부 확인
- [ ] router 등록 위치 수정
- [ ] schema/service import 방향 단순화

## 유형 B. DB 스키마 불일치
- [ ] 실제 컬럼명 기준으로 점검표 수정
- [ ] migration 초안 작성
- [ ] write API 전에 필요한 최소 컬럼 우선 정의
- [ ] nullable/default로 우회 가능한지 판정

## 유형 C. 실행 진입점 혼선
- [ ] `run.py` / `run_bootstrap.py` 역할 분리 메모 작성
- [ ] `run_react_api.py` 별도 실행 기준 정리
- [ ] `run_react.bat` 실행 순서 명시
- [ ] 포트/경로 충돌 메모 작성

## 유형 D. Frontend skeleton 깨짐
- [ ] placeholder를 더 단순화
- [ ] App.jsx 삽입 위치 재조정
- [ ] 모달 props를 최소화
- [ ] actionApi를 dummy-safe 구조로 변경

---

# 10. P0-1 산출물 목록

## 문서 산출물
- [ ] `GPT_SQM_P0-1_초상세_작업지시서.md`
- [ ] `P0-1_수정대상파일표.md`
- [ ] `P0-1_DB스키마점검표.md`
- [ ] `P0-1_실행파일연동점검표.md`

## 코드 산출물
- [ ] `web/src/components/TopMenuBar.jsx`
- [ ] `web/src/components/modals/LotDetailModal.jsx`
- [ ] `web/src/components/modals/InboundParseModal.jsx`
- [ ] `web/src/components/modals/OutboundExecuteModal.jsx`
- [ ] `web/src/api/actionApi.js`
- [ ] `react_api/routes/actions.py`
- [ ] `react_api/schemas/actions.py`
- [ ] `react_api/services/action_service.py`
- [ ] `react_api/services/engine_adapter.py`

---

# 11. P0-1 → P0-2 진입 게이트

다음 단계(P0-2 LOT 상세 모달 실제 구현)로 넘어가려면 아래가 모두 통과해야 한다.

- [ ] 수정/생성 대상 파일이 확정되었다
- [ ] skeleton 파일이 모두 존재한다
- [ ] actions router가 등록된다
- [ ] 공통 응답 구조가 정리되었다
- [ ] `audit_log` / `outbound_event_log` 위험 요소가 정리되었다
- [ ] `run.py` / `run_bootstrap.py` / `run_react.bat` / `.env` 관계가 정리되었다
- [ ] py_compile / import / basic router 테스트가 통과했다

---

# 12. 루비 최종 권장안

이번 P0-1은 화려한 기능 구현 단계가 아니라 **지반 공사 단계**다.  
여기서 흔들리면 이후 단계에서 아래 문제가 연쇄적으로 발생한다.

```text
- actions router는 생겼는데 engine 연결 방식이 불명확
- files/upload를 만들었는데 parser 연결 경로가 꼬임
- outbound/cancel를 붙였는데 로그 테이블 컬럼이 맞지 않음
- run_react.bat는 돌지만 .env가 분리되어 API/Tkinter 값이 다름
```

따라서 이번 단계의 핵심은 아래 한 줄로 정리된다.

```text
P0-1에서는 '기능'보다 '구조와 경로와 스키마와 실행체계'를 먼저 고정한다.
```

---

# 13. 다음 단계 권장

이번 문서 다음으로 가장 효율적인 작업은 아래 3개 중 하나다.

1. `P0-1_수정대상파일표.md`
2. `P0-1_DB스키마점검표.md`
3. `P0-1_실행파일연동점검표.md`

루비 권장 순서는 아래다.

```text
1) 수정대상파일표
2) DB스키마점검표
3) 실행파일연동점검표
```
