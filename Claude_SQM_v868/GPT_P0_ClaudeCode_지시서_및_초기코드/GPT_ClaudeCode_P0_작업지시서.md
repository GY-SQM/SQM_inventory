# GPT Claude Code P0 작업지시서
생성일: 2026-04-04 16:25 (Asia/Seoul)
대상 원본: `Claude_SQM_v867.zip`
기준 문서: `MASTER_FINAL_v867_통합완성본.md`, `붙여넣은 텍스트 (1).txt`
인코딩: UTF-8

---

## [질문]
P0 기준으로 Claude Code에서 수행할 작업 지시서 및 코딩 초안을 작성해 달라는 요청

## [질문의도]
이 문서는 Claude Code가 **질문 없이**, **Recon부터**, **P0-1 ~ P0-4 순서로**, **테스트 게이트를 통과하면서** 작업하도록 하기 위한 실행 지시서다.

이 문서는 아래 목표를 가진다.

1. React 상단 메뉴바를 Tkinter 메뉴 구조에 맞춘 드롭다운으로 확장
2. LOT 상세 / 입고 파싱 / 출고 처리 모달 구현
3. GET 중심 FastAPI에 쓰기 API 5종 추가
4. 기존 `engine_modules` 재사용
5. 트랜잭션 / rollback / 로그 검증
6. run/bat/.env 통합 점검

---

## [응답]

## 1. 절대 실행 규칙

아래 규칙은 예외 없이 따른다.

```text
- 절대 사용자에게 질문하지 말 것
- 실제 v867 구조 조사 없이 임의 패치 먼저 하지 말 것
- 테스트 실패 시 자동 수정 후 재시도할 것
- 부분 완료 상태로 멈추지 말 것
- 각 단계는 반드시 Pre-Test → 구현 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계 순서로 진행할 것
- write API는 반드시 transaction + rollback 검증 포함
- mock 완료 처리 금지
```

---

## 2. 작업 목표 요약

이번 P0의 핵심 목표는 아래 4개다.

```text
P0-1 구조 준비 + DB/실행 파일 점검
P0-2 LOT 상세 모달 구현
P0-3 입고/출고 write loop 구현
P0-4 위치 업데이트 + 통합 실행 + 회귀 테스트
```

추가 목표:

```text
POST /files/upload
POST /inbound/create
POST /outbound/execute
PUT  /outbound/cancel
PUT  /location/update
```

---

## 3. Recon Phase (무조건 선행)

### 목적
실제 v867 구조를 먼저 조사하고, 수정 파일을 확정한다.

### 조사 대상

```text
gui_app_modular/
web/
react_api/
engine_modules/inventory_modular/
run.py
run_bootstrap.py
run_react.bat
run_react_api.py
```

### 조사 항목

1. Tkinter 메뉴바 정의 파일/함수
2. Tkinter LOT 상세 / 입고 / 출고 관련 다이얼로그 파일
3. React 상단 내비게이션 구현 파일
4. React 페이지/모달 위치
5. FastAPI read-only 라우트 위치
6. `process_inbound`, `process_outbound`, `cancel_outbound_tonbag`, `update_tonbag_location`, `get_lot_detail`, `get_lot_items` 위치 및 시그니처
7. `.env` 로드 위치와 실행 진입점
8. audit_log / outbound_event_log 스키마 호환성

### 산출물

아래 문서를 먼저 작성한다.

```text
docs/RECON_V867_WEB_MIGRATION_MAP.md
```

필수 포함 항목:

- Tkinter 메뉴 ↔ React 메뉴 대응표
- Tkinter 다이얼로그 ↔ React 모달 대응표
- read API ↔ write API 확장표
- engine 함수 ↔ adapter 연결표
- 실제 수정 파일 목록

### Recon 완료 조건

```text
- 메뉴 대응표 완성
- 모달 대응표 완성
- 쓰기 API 후보 함수 표 완성
- 수정 파일 목록 확정
```

Recon 완료 전에는 실제 패치를 시작하지 말 것.

---

## 4. P0-1 구조 준비 + DB/실행 파일 점검

### 구현 대상

#### Frontend

```text
web/src/components/TopMenuBar.jsx
web/src/components/modals/LotDetailModal.jsx
web/src/components/modals/InboundParseModal.jsx
web/src/components/modals/OutboundExecuteModal.jsx
web/src/api/actionApi.js
```

#### Backend

```text
react_api/routes/actions.py
react_api/schemas/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
```

#### 라우터 등록

- `react_api/main.py` 또는 기존 라우터 등록부에 `actions` 라우트 연결

### 해야 할 일

1. 새 파일 골격 생성
2. import 경로 정리
3. 공통 응답 포맷 정의
4. 공통 에러 포맷 정의
5. audit_log / outbound_event_log 컬럼 확인
6. migration 필요 시 별도 스크립트 또는 메모 생성
7. run.py / run_bootstrap.py / run_react.bat / run_react_api.py 역할 정리
8. `.env` 로드 위치 정리

### Pre-Test

```bash
python -m py_compile react_api/main.py
python -m py_compile react_api/routes/actions.py
python -m py_compile react_api/services/action_service.py
python -m py_compile react_api/services/engine_adapter.py
```

필요 시 추가:

```bash
python -m py_compile run.py
python -m py_compile run_bootstrap.py
```

### 완료 기준

```text
- 새 라우트/서비스/스키마/컴포넌트 골격 생성 완료
- actions router 등록 완료
- DB 로그 테이블 호환성 확인 완료
- 실행 파일 구조 파악 완료
```

---

## 5. P0-2 LOT 상세 모달 구현

### 구현 대상

```text
LotDetailModal.jsx
Inventory/Allocation/Tonbag 관련 페이지의 LOT 클릭 연결
lot detail 조회 API 재사용 또는 adapter 정리
```

### UI 필수 항목

- 기본정보
- 톤백 목록
- 이력
- 배정 상태
- 로딩 상태
- 에러 상태
- 닫기 버튼

### 해야 할 일

1. `GET /lot/{lot_no}` 또는 동등 API 응답 구조 확인
2. React 쪽 데이터 매핑 함수 작성
3. Inventory / Allocation / Tonbag 화면에서 LOT 클릭 시 모달 오픈
4. LOT 변경 시 재조회
5. 빈 데이터 / 404 / 500 처리

### Pre-Test

- LOT 상세 API 응답 샘플 3건 확인
- 없는 LOT 번호 요청 시 오류 처리 확인
- null / 빈 배열 렌더링 확인

### Post-Test

```text
- LOT 클릭 → 모달 오픈
- 모달 닫기 정상
- 다른 LOT 전환 시 재조회 정상
- Tkinter LOT 상세 화면과 핵심 항목 비교 완료
```

### 완료 기준

```text
- React LOT 상세 모달 정상 동작
- 기본정보 / 톤백 / 이력 / 배정 상태 표시
- 빈 데이터/오류 케이스 안정 처리
```

---

## 6. P0-3 입고/출고 write loop 구현

### 구현 대상 API

```text
POST /files/upload
POST /inbound/create
POST /outbound/execute
PUT  /outbound/cancel
```

### 구현 대상 UI

```text
InboundParseModal.jsx
OutboundExecuteModal.jsx
```

### 핵심 연결 원칙

FastAPI에서 신규 업무 규칙을 만들지 말고 아래 engine 함수를 감싸는 adapter 계층만 둔다.

```text
process_inbound
process_outbound
cancel_outbound_tonbag
```

### 해야 할 일

#### Upload / Parser
1. PDF 업로드 처리
2. Excel 업로드 처리
3. 파일 형식 판별
4. 기존 parser 분기
5. preview JSON 표준화
6. InboundParseModal 자동 채움

#### Inbound
1. 생성 예정 LOT 요약 표시
2. 사용자 확인 후 `POST /inbound/create`
3. 실제 `process_inbound()` 연결
4. transaction / commit / rollback 처리

#### Outbound
1. 대상 톤백 / 수량 / 출고처 입력 UI
2. `POST /outbound/execute`
3. 실제 `process_outbound()` 연결
4. `PUT /outbound/cancel`
5. 실제 `cancel_outbound_tonbag()` 연결
6. 실패 시 rollback 검증

### Pre-Test

```text
- parser 단독 테스트
- upload 경로 쓰기 권한 확인
- inbound/outbound engine 단독 smoke test
- test DB 또는 복제 DB 준비
```

### Post-Test

```text
- PDF 업로드 → preview 성공
- Excel 업로드 → preview 성공
- preview → inbound/create 성공
- outbound/execute 성공
- outbound/cancel 성공
- 실패 케이스 rollback 성공
```

### 완료 기준

```text
- 업로드 → 파싱 → 미리보기 → 입고 생성 루프 동작
- 출고 실행/취소 루프 동작
- rollback 실제 검증 완료
```

---

## 7. P0-4 위치 업데이트 + 통합 실행 + 회귀

### 구현 대상 API

```text
PUT /location/update
```

### engine 연결 후보

```text
update_tonbag_location
```

### 해야 할 일

1. tonbag/location 식별 파라미터 정의
2. validation 추가
3. 실제 위치 변경 engine 연결
4. 성공/실패 응답 표준화
5. 위치 변경 후 화면 재조회
6. audit_log 기록 확인
7. outbound_event_log 충돌 여부 확인
8. `run_react.bat` 에 API + Frontend 동시 실행 정리
9. `.env` 공통 로드 정리
10. API + Frontend + Tkinter 동시 실행 테스트

### Pre-Test

```text
- clean start 가능 여부 확인
- 기존 프로세스 종료 상태 확인
- 테스트용 데이터셋 준비
- 로그 디렉토리 준비
```

### Post-Test

```text
- location/update 성공
- 위치 반영 후 재조회 정상
- API 서버 기동 정상
- Frontend 접속 정상
- Tkinter 동시 실행 충돌 없음
- 전체 회귀 테스트 통과
```

### 완료 기준

```text
- 위치 변경 API 실연결 완료
- run/bat/.env 통합 점검 완료
- API + Frontend + Tkinter 병행 테스트 완료
```

---

## 8. 구현 파일 우선순위

### Backend 우선 파일

```text
react_api/main.py
react_api/routes/actions.py
react_api/schemas/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
engine_modules/inventory_modular/inbound_mixin.py
engine_modules/inventory_modular/outbound_mixin.py
engine_modules/inventory_modular/query_mixin.py
engine_modules/inventory_modular/tonbag_mixin.py
```

### Frontend 우선 파일

```text
web/src/App.jsx
web/src/components/TopMenuBar.jsx
web/src/components/modals/LotDetailModal.jsx
web/src/components/modals/InboundParseModal.jsx
web/src/components/modals/OutboundExecuteModal.jsx
web/src/api/actionApi.js
```

---

## 9. 테스트 게이트

```text
Gate A: P0-1 → P0-2
- actions/router/schema/service skeleton 완성
- DB 스키마 위험 요소 식별 완료
- 실행 파일 구조 파악 완료

Gate B: P0-2 → P0-3
- LOT 상세 모달 동작
- LOT 관련 데이터 shape 확정
- 에러 핸들링 안정화

Gate C: P0-3 → P0-4
- files/upload 실연결 완료
- inbound/create 실연결 완료
- outbound/execute/cancel 실연결 완료
- rollback 검증 완료

Gate D: P0-4 → P0 완료
- location/update 실연결 완료
- run/bat/.env 통합 완료
- API + Frontend + Tkinter 통합 테스트 완료
```

---

## 10. Claude Code에 직접 넣을 실행 프롬프트

아래 프롬프트를 Claude Code system prompt 또는 작업 지시용 md 파일로 사용한다.

```text
현재 작업 기준 원본은 Claude_SQM_v867 이다.
기존 가정 구조만 믿고 진행하지 말고 반드시 실제 v867 코드 구조를 먼저 조사한 뒤 수정하라.

절대 규칙:
1. 사용자에게 질문하지 말 것
2. Recon 완료 전 실제 패치 시작 금지
3. 모든 단계는 Pre-Test → 구현 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계 순서로 진행할 것
4. 테스트 실패 상태에서 다음 단계로 진행 금지
5. write API는 반드시 transaction + rollback 검증 포함
6. FastAPI에서 신규 업무 규칙을 만들지 말고 기존 engine_modules를 adapter로 감싸서 재사용할 것
7. 부분 완료 상태로 종료하지 말 것

이번 P0의 목표:
- React 상단 메뉴바를 Tkinter 메뉴 구조에 맞춘 드롭다운으로 확장
- LOT 상세 / 입고 파싱 / 출고 처리 모달 구현
- POST /files/upload
- POST /inbound/create
- POST /outbound/execute
- PUT  /outbound/cancel
- PUT  /location/update
- run/bat/.env 통합 점검

반드시 다음 순서로 진행:
1. Recon Phase
2. P0-1 구조 준비 + DB/실행 파일 점검
3. P0-2 LOT 상세 모달
4. P0-3 입고/출고 write loop
5. P0-4 위치 업데이트 + 통합 실행 + 회귀

Recon 산출물:
- docs/RECON_V867_WEB_MIGRATION_MAP.md

작업 후 반드시 남길 산출물:
- 수정 파일 목록
- 테스트 결과 요약
- 실패 후 수정 내역
- 남은 리스크
```

---

## 11. 권장 실행 명령 예시

```bash
claude --dangerously-skip-permissions --system-prompt-file "GPT_ClaudeCode_P0_작업지시서.md"
```

또는

```bash
claude --dangerously-skip-permissions < "GPT_ClaudeCode_P0_작업지시서.md"
```

---

## 12. 최종 판단

이번 문서는 바로 Claude Code에 넣어 실행 가능한 수준의 P0 작업지시서다.
단, 실제 함수명/호출 인자/라우터 등록 위치는 Recon Phase에서 v867 실구조 기준으로 먼저 확정해야 한다.
