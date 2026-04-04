# GPT_ClaudeCode_P0-4_실행프롬프트.md
생성일: 2026-04-04 15:58 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
참조 문서:
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P0-4_위치업데이트_통합실행_초상세_작업지시서.md`
- `GPT_SQM_P0-4_테스트체크리스트.md`
- `GPT_SQM_P0-3_입고출고_WriteLoop_테스트체크리스트.md`

---

## [질문]
다음 단계로 **Claude Code용 P0-4 실행 프롬프트**를 작성

## [질문의도]
Claude Code가 바로 실행할 수 있도록  
P0 마지막 단계인 `location/update + 실행 통합 + 회귀 검증` 작업을
실행 지시문 형태로 정리한다.

---

# [응답]

# 1. Claude Code 실행 프롬프트

아래 내용을 Claude Code에 그대로 투입한다.

---

## SYSTEM / MASTER EXECUTION PROMPT

현재 작업 기준 원본은 `Claude_SQM_v867` 이다.  
기존 가정 구조만 믿고 진행하지 말고 반드시 실제 v867 코드 구조를 먼저 조사한 뒤 수정하라.

이번 작업은 **P0-4: 위치업데이트 + 통합실행 + 회귀 검증 단계**다.  
목표는 아래 흐름을 실제로 완성하고 안정화하는 것이다.

```text
PUT /location/update
→ engine 위치 변경 로직 연결
→ transaction / rollback / audit_log
→ run.py / run_bootstrap.py / run_react_api.py / run_react.bat / .env 정리
→ P0-2 / P0-3 회귀 테스트
→ P0 전체 완료 게이트 통과
```

### 절대 목표
다음 6가지를 반드시 만족해야 한다.

```text
1. /location/update 가 실제 engine 위치 변경 로직과 연결된다
2. 성공/실패/rollback 이 실제로 검증된다
3. audit_log 기록이 남는다
4. API + Frontend 기본 통합 실행이 가능하다
5. P0-2 회귀 테스트가 통과한다
6. P0-3 회귀 테스트가 통과한다
```

### 절대 금지
다음은 금지한다.

```text
- location/update 버튼만 만들고 실제 반영 없이 완료 처리 금지
- route/service 층에서 위치 변경 핵심 업무 규칙 재구현 금지
- 실행 스크립트가 재현 불가한 상태로 완료 처리 금지
- rollback 검증 없이 완료 처리 금지
- P0-2 또는 P0-3 회귀가 깨진 상태에서 다음 단계로 넘어가기 금지
```

### 구현 원칙
- 기존 tonbag/location 관련 engine 로직을 반드시 재사용하라
- action_service 는 orchestration / validation / transaction / logging만 담당하라
- run 파일들은 역할 정리와 최소 범위 보강만 하라
- .env 구조는 공통/API/Frontend/외부연동으로 분류하라
- 통합 실행은 API + Frontend 기본 재현 가능 상태를 목표로 하라

---

# 2. 실제 조사 대상

먼저 아래 파일/경로를 조사하라.

```text
react_api/routes/actions.py
react_api/schemas/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
web/src/api/actionApi.js
위치 변경 관련 page / modal / action 진입점

engine_modules/inventory_modular/tonbag_mixin.py
engine_modules/inventory_modular/query_mixin.py

run.py
run_bootstrap.py
run_react_api.py
run_react.bat
.env
.env.example 또는 settings/config 파일
```

조사 후 아래를 확정하라.

- 실제 위치 변경 engine 함수 위치와 인자 형태
- 현재 위치 변경 UI 진입점
- run.py / run_bootstrap.py 역할 구분
- run_react_api.py host/port/env 로드 방식
- run_react.bat 실행 순서/경로/로그 방식
- .env 키 구조와 사용 주체

---

# 3. 수정 대상 파일

이번 단계의 직접 수정 대상은 아래를 기준으로 한다.

```text
react_api/routes/actions.py
react_api/schemas/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
web/src/api/actionApi.js
위치 변경 관련 page / modal / action 파일
run_react_api.py
run_react.bat
run.py                 (필요 시 최소 범위)
run_bootstrap.py       (필요 시 최소 범위)
.env.example 또는 설정 문서
```

참조/재사용 대상은 아래다.

```text
engine_modules/inventory_modular/tonbag_mixin.py
engine_modules/inventory_modular/query_mixin.py
data/db/sqm_inventory.db
```

---

# 4. 구현 순서

아래 순서를 반드시 지켜라.

## Step 1. Recon
- 위치 변경 engine 함수 조사
- 위치 변경 UI 진입점 조사
- 실행 파일/환경변수 구조 조사
- 포트/DB/env 충돌 가능성 조사

## Step 2. `/location/update` 구현
- schema 확정
- route 구현
- action_service orchestration 구현
- engine_adapter wrapper 구현
- transaction / rollback / audit_log 적용

## Step 3. Frontend 연결
- `updateLocation()` API 함수 구현
- 위치 변경 입력 흐름 구현
- 성공/실패 결과 표시
- 변경 후 화면 재조회

## Step 4. 실행 구조 정리
- run_react_api.py host/port/env 정리
- run_react.bat API→Frontend 실행 순서 정리
- 작업 디렉토리/로그/pause 정책 정리
- run.py / run_bootstrap.py 역할 재확인 및 최소 보강
- .env 키 분류 정리

## Step 5. 회귀 테스트
- P0-2 LOT 상세 모달 회귀
- P0-3 write loop 회귀
- location/update 성공/실패/rollback 테스트
- 포트/DB/env 충돌 점검

---

# 5. `/location/update` 기준

다음 구조를 목표로 하라.

```json
{
  "success": true,
  "message": "Location updated",
  "data": {
    "target": {},
    "old_location": "",
    "new_location": "",
    "summary": {}
  }
}
```

최소 입력은 아래를 기준으로 하라.

```text
target tonbag 식별값
new location
reason(optional)
```

---

# 6. 책임 분리 원칙

## route
- schema 검증
- service 호출
- 응답 반환

## action_service
- transaction begin/commit/rollback
- adapter 호출
- audit_log 기록
- 응답 구조 정리

## engine_adapter
- 실제 위치 변경 engine wrapper
- 인자 매핑
- 예외 상위 전달

### 절대 금지
- service에서 위치 변경 핵심 비즈니스 로직 재구현 금지
- route에서 DB 직접 수정 금지

---

# 7. 테스트 게이트

각 단계는 아래 순서를 반드시 따른다.

```text
Pre-Test → 구현 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계
```

## Pre-Test
- 위치 변경 대상 샘플 확보
- 정상/비정상 위치 값 확보
- API/Frontend 실행 가능 확인
- audit_log 테이블 확인
- P0-2/P0-3 테스트 샘플 준비

## Post-Test
다음을 모두 확인하라.

### location/update
- 성공 호출
- 실패 rollback
- 재조회 반영
- audit_log 기록

### 실행 구조
- run_react_api.py 기동
- run_react.bat 기동
- Frontend 접속
- health 확인
- 오류 시 로그 식별 가능

### 회귀
- LOT 상세 모달 정상
- upload preview 정상
- inbound/create 정상/rollback
- outbound/execute 정상/rollback
- outbound/cancel 정상/rollback

### 충돌
- 포트 충돌 없음
- DB lock 치명 문제 없음
- env 해석 충돌 없음

---

# 8. 완료 기준

다음 조건이 모두 만족되면 이번 단계를 완료로 본다.

```text
1. /location/update 실동작
2. rollback 검증 완료
3. audit_log 기록 확인
4. API + Frontend 기본 통합 실행 가능
5. P0-2 회귀 통과
6. P0-3 회귀 통과
7. 실행 파일/환경변수 구조 정리 완료
```

다음 중 하나라도 해당하면 완료로 인정하지 않는다.

```text
- location/update 가 mock 또는 부분 동작
- rollback 검증이 없음
- 통합 실행이 재현 불가
- P0-2/P0-3 기능이 회귀로 깨짐
- 포트/DB/env 충돌이 미정리
```

---

# 9. 출력 형식

작업 종료 후 아래 형식으로 결과를 정리하라.

## 1) 수정 파일 목록
- 실제 수정 파일
- 신규 생성 파일
- 변경 이유 1줄 요약

## 2) 위치 변경 연결 요약
- route 경로
- service 함수
- adapter wrapper
- engine 함수 위치

## 3) 실행 구조 요약
- run.py 역할
- run_bootstrap.py 역할
- run_react_api.py 실행 방식
- run_react.bat 실행 방식
- .env 키 분류

## 4) 테스트 결과
- location/update PASS/FAIL
- rollback PASS/FAIL
- audit_log PASS/FAIL
- P0-2 회귀 PASS/FAIL
- P0-3 회귀 PASS/FAIL
- 충돌 점검 PASS/FAIL

## 5) 남은 이슈
- P1 이상으로 넘길 항목
- 운영 전 추가 확인 항목

---

# 10. 최종 실행 선언

이번 작업은 **P0-4 위치업데이트 + 통합실행 + 회귀 검증**이다.  
질문 없이, 중단 없이, 테스트 게이트를 통과하며 진행하라.

작업 완료 후에는 반드시
- 수정 파일 목록
- 위치 변경 연결 요약
- 실행 구조 요약
- 테스트 결과
를 남겨라.

---

# 11. 루비 최종 권장안

```text
P0-4는 기능 추가보다
지금까지 만든 전체 흐름을 운영 가능한 상태로 묶고
회귀 없이 통과시키는 단계다.
```
