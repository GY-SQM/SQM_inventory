# GPT_ClaudeCode_P0-3_실행프롬프트.md
생성일: 2026-04-04 15:47 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
참조 문서:
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P0-3_입고출고_WriteLoop_초상세_작업지시서.md`
- `GPT_SQM_P0-3_입고출고_WriteLoop_테스트체크리스트.md`
- `GPT_SQM_P0-1_DB스키마점검표.md`
- `GPT_SQM_P0-1_완료보고서.md`

---

## [질문]
계속 진행해서 **Claude Code용 P0-3 실행 프롬프트**를 작성해 달라는 요청

## [질문의도]
Claude Code가 바로 실행할 수 있도록  
P0-3 단계인 **입고/출고 write loop 구현 작업**을  
실행 지시문 형태로 정리한다.

이번 문서의 목적은 아래와 같다.

```text
1. Claude Code가 P0-3 목표를 정확히 이해하게 한다
2. parser / engine / rollback / logging까지 실제로 연결하게 한다
3. 수정 파일과 구현 순서를 고정한다
4. mock 수준이 아니라 실제 업무 쓰기 루프가 되도록 강제한다
```

---

# [응답]

# 1. Claude Code 실행 프롬프트

아래 내용을 Claude Code에 그대로 투입한다.

---

## SYSTEM / MASTER EXECUTION PROMPT

현재 작업 기준 원본은 `Claude_SQM_v867` 이다.  
기존 가정 구조만 믿고 진행하지 말고 반드시 실제 v867 코드 구조를 먼저 조사한 뒤 수정하라.

이번 작업은 **P0-3: 입고/출고 write loop 구현 단계**다.  
목표는 React + FastAPI에서 아래 실제 업무 흐름을 완성하는 것이다.

```text
files/upload
→ parser preview
→ inbound/create
→ outbound/execute
→ outbound/cancel
→ transaction / rollback / logging
```

### 절대 목표
다음 6가지를 반드시 만족해야 한다.

```text
1. /files/upload 가 실제 parser와 연결된다
2. /inbound/create 가 실제 process_inbound() 또는 동등 로직과 연결된다
3. /outbound/execute 가 실제 process_outbound() 또는 동등 로직과 연결된다
4. /outbound/cancel 이 실제 cancel_outbound_tonbag() 또는 동등 로직과 연결된다
5. 모든 write 동작은 transaction + rollback 구조를 가진다
6. audit_log / outbound_event_log 기록이 실제로 남는다
```

### 절대 금지
다음은 금지한다.

```text
- preview만 만들고 create를 mock으로 처리하는 것 금지
- execute/cancel 버튼만 만들고 실제 engine 호출 없이 완료 처리 금지
- FastAPI/service 층에 완전 신규 업무 로직 구현 금지
- 기존 parser / engine_modules 조사 없이 임의 구현 금지
- rollback 검증 없이 완료 처리 금지
- 테스트 실패 상태에서 다음 단계로 넘어가기 금지
```

### 구현 원칙
- 기존 `engine_modules` 핵심 로직을 반드시 재사용하라
- FastAPI/service 는 orchestration / validation / transaction / logging만 담당하라
- parser는 기존 `parsers/` 구조를 최대한 재사용하라
- preview JSON은 표준화하되, parser 원본 로직은 최소 수정 원칙을 지켜라
- Frontend는 modal UX를 실사용 가능한 수준으로 만들되 구조를 크게 흔들지 말라
- 실패 시 rollback 결과와 로그 기록까지 함께 검증하라

---

# 2. 실제 조사 대상

먼저 아래 파일/경로를 조사하라.

```text
react_api/routes/actions.py
react_api/schemas/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
react_api/main.py

web/src/components/modals/InboundParseModal.jsx
web/src/components/modals/OutboundExecuteModal.jsx
web/src/api/actionApi.js
web/src/App.jsx
관련 page 파일

engine_modules/inventory_modular/inbound_mixin.py
engine_modules/inventory_modular/outbound_mixin.py
engine_modules/inventory_modular/query_mixin.py

parsers/
data/db/sqm_inventory.db
```

조사 후 아래를 확정하라.

- 기존 parser 진입 경로
- `process_inbound()` 실제 위치와 인자 형태
- `process_outbound()` 실제 위치와 인자 형태
- `cancel_outbound_tonbag()` 실제 위치와 인자 형태
- 로그 테이블(`audit_log`, `outbound_event_log`) 실제 컬럼 구조
- 현재 React에서 입고/출고 모달을 여는 가장 자연스러운 진입점

---

# 3. 수정 대상 파일

이번 단계의 직접 수정 대상은 아래를 기준으로 한다.

```text
web/src/components/modals/InboundParseModal.jsx
web/src/components/modals/OutboundExecuteModal.jsx
web/src/api/actionApi.js
web/src/App.jsx                         (필요 시)
관련 page 파일                         (필요 시)

react_api/routes/actions.py
react_api/schemas/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
react_api/main.py                       (등록 점검 수준)
```

참조/재사용 대상은 아래다.

```text
engine_modules/inventory_modular/inbound_mixin.py
engine_modules/inventory_modular/outbound_mixin.py
parsers/
data/db/sqm_inventory.db
```

---

# 4. 구현 순서

아래 순서를 반드시 지켜라.

## Step 1. Recon
- parser 구조 조사
- inbound/outbound/cancel engine 함수 조사
- 로그 테이블 구조 조사
- 현재 모달 진입점 조사
- 실제 API payload/응답 형태 초안 작성

## Step 2. `/files/upload` 구현
- 기존 parser 재사용
- 파일 형식 판별 로직 추가
- PDF / Excel preview 지원
- preview / summary / warnings / create용 payload 반환
- 손상 파일 / 지원 불가 형식 / 빈 파일 예외 처리

## Step 3. `/inbound/create` 구현
- preview 결과 기반 payload 수신
- 실제 `process_inbound()` 또는 동등 로직 호출
- transaction begin/commit/rollback 적용
- audit_log 기록
- 사용자 응답 메시지 정리

## Step 4. `/outbound/execute` 구현
- 대상 / 수량 / destination 수신
- 실제 `process_outbound()` 또는 동등 로직 호출
- transaction begin/commit/rollback 적용
- audit_log / outbound_event_log 기록
- 결과 메시지 정리

## Step 5. `/outbound/cancel` 구현
- 취소 대상 식별값 수신
- 실제 `cancel_outbound_tonbag()` 또는 동등 로직 호출
- transaction begin/commit/rollback 적용
- audit_log / outbound_event_log 기록
- 결과 메시지 정리

## Step 6. Frontend 모달 연결
### `InboundParseModal.jsx`
- 파일 선택
- 업로드 실행
- preview 표시
- warnings 표시
- confirm create
- 성공/실패 표시
- 중복 클릭 방지

### `OutboundExecuteModal.jsx`
- 대상 표시/선택
- quantity 입력
- destination 입력
- execute 실행
- cancel 실행 또는 별도 취소 액션 연결
- 성공/실패 표시
- 중복 클릭 방지

## Step 7. 안정화
- API 응답 포맷 정리
- 에러 메시지 정리
- rollback 검증
- side effect 잔존 여부 점검
- 로그 기록 검증

---

# 5. API 설계 기준

## `POST /files/upload`
다음 구조를 목표로 하라.

```json
{
  "success": true,
  "message": "Preview generated",
  "data": {
    "file_type": "pdf",
    "parser_type": "inbound",
    "preview": {},
    "summary": {},
    "warnings": [],
    "create_payload": {}
  }
}
```

### 최소 요구
- preview
- summary
- warnings
- create_payload

---

## `POST /inbound/create`
다음 구조를 목표로 하라.

```json
{
  "success": true,
  "message": "Inbound created",
  "data": {
    "created_lots": [],
    "count": 0,
    "warnings": []
  }
}
```

---

## `POST /outbound/execute`
다음 구조를 목표로 하라.

```json
{
  "success": true,
  "message": "Outbound executed",
  "data": {
    "processed": [],
    "summary": {}
  }
}
```

---

## `PUT /outbound/cancel`
다음 구조를 목표로 하라.

```json
{
  "success": true,
  "message": "Outbound canceled",
  "data": {
    "restored": [],
    "summary": {}
  }
}
```

---

# 6. Adapter / Service 책임 분리

## `engine_adapter.py`
아래만 담당하라.

- engine 인스턴스 확보
- engine 함수 wrapper
- 인자 shape 맞춤
- 결과 값 표준화 보조
- 예외 상위 전달

## `action_service.py`
아래만 담당하라.

- request 검증 이후 orchestration
- parser 호출
- transaction begin / commit / rollback
- audit_log / outbound_event_log 기록
- 공통 응답 구조 반환

### 절대 금지
- service 안에서 engine 핵심 업무 규칙 재구현 금지
- route 안에서 transaction / engine 직접 뒤섞기 금지

---

# 7. rollback / logging 기준

## rollback이 반드시 검증되어야 하는 경우
- preview는 성공했으나 create 실패
- execute 중간 실패
- cancel 중간 실패
- 로그 기록 중 예외
- validation 실패 후 partial side effect 발생 가능 구간

## 반드시 확인할 것
- 실패 후 DB 원상복구
- 중간 상태가 남지 않음
- 응답이 success로 잘못 내려가지 않음
- audit_log에 실패/성공 기록이 남음
- outbound_event_log에 execute/cancel 이력이 남음

---

# 8. 테스트 게이트

각 단계는 아래 순서를 반드시 따른다.

```text
Pre-Test → 구현 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계
```

## Pre-Test
- parser 단독 실행 가능 여부 확인
- 정상 PDF 샘플 확보
- 정상 Excel 샘플 확보
- 손상/잘못된 파일 샘플 확보
- 출고 가능한 테스트 대상 확보
- 취소 가능한 테스트 대상 확보
- 로그 테이블 스키마 확인
- frontend/backend import 오류 없음 확인

## Post-Test
다음을 모두 확인하라.

### upload / preview
- PDF upload preview 성공
- Excel upload preview 성공
- 지원 불가 형식 오류 처리
- 손상 파일 오류 처리

### inbound/create
- create 성공
- create 실패 rollback 검증
- 중간 데이터 미잔존 확인
- audit_log 기록 확인

### outbound/execute
- execute 성공
- execute 실패 rollback 검증
- 상태 변화 확인
- outbound_event_log 기록 확인

### outbound/cancel
- cancel 성공
- cancel 실패 rollback 검증
- 상태 복구 확인
- outbound_event_log 취소 기록 확인

### modal UX
- InboundParseModal 실사용 가능
- OutboundExecuteModal 실사용 가능
- loading / error / result 표시
- 중복 클릭 방지

---

# 9. 완료 기준

다음 조건이 모두 만족되면 이번 단계를 완료로 본다.

```text
1. upload → preview → create 가 실제로 돈다
2. execute 가 실제 engine 호출로 돈다
3. cancel 이 실제 engine 호출로 돈다
4. rollback 이 실제로 검증된다
5. audit_log / outbound_event_log 가 남는다
6. 프론트 모달이 실사용 가능한 수준이다
```

다음 중 하나라도 해당하면 완료로 인정하지 않는다.

```text
- preview만 되고 create는 mock
- execute/cancel가 버튼만 있고 실제 상태 변화가 없음
- rollback 검증이 없음
- 실패 후 DB 상태가 남음
- 로그 기록이 없음
- 모달 UX가 실사용 불가
```

---

# 10. 출력 형식

작업 종료 후 아래 형식으로 결과를 정리하라.

## 1) 수정 파일 목록
- 실제 수정 파일
- 신규 생성 파일
- 변경 이유 1줄 요약

## 2) parser/engine 연결 요약
- parser 경로
- inbound wrapper 경로
- outbound wrapper 경로
- cancel wrapper 경로

## 3) 테스트 결과
- upload preview PASS/FAIL
- inbound/create PASS/FAIL
- outbound/execute PASS/FAIL
- outbound/cancel PASS/FAIL
- rollback PASS/FAIL
- logging PASS/FAIL

## 4) 남은 이슈
- P0에서 허용 가능한 보류 항목
- P1/P4로 넘길 항목

---

# 11. 최종 실행 선언

이번 작업은 **P0-3 입고/출고 write loop 실제 구현**이다.  
질문 없이, 중단 없이, 테스트 게이트를 통과하며 진행하라.

필요한 경우에만 최소 범위로 parser/API/UI를 보강하되,
기존 parser와 기존 engine_modules 로직 재사용을 우선하라.

작업 완료 후에는 반드시
- 수정 파일 목록
- parser/engine 연결 요약
- 테스트 결과
- rollback/logging 결과
를 남겨라.

---

# 12. 루비 최종 권장안

이번 프롬프트의 핵심은 아래 한 줄이다.

```text
P0-3은 "API를 만드는 작업"이 아니라,
실제 업무 쓰기 루프를 React/FastAPI에서 안전하게 재생시키는 작업이다.
```

---

# 13. 다음 단계 권장

이 문서 다음으로 가장 자연스러운 작업은 아래다.

1. **P0-4 위치업데이트+통합실행 초상세 작업지시서**
2. **Claude Code용 P0-4 실행 프롬프트**

루비 권장 순서는 아래다.

```text
1) P0-4 초상세 작업지시서
2) P0-4 실행 프롬프트
```
