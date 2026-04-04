# GPT_SQM_867_React_P0_패치설계서.md

작성일: 2026-04-04 14:50 (Asia/Seoul)

# SQM 867 React를 864 Tkinter 수준으로 끌어올리는 P0 패치 설계서

## 0. 문서 목적

이 문서는 `Claude_SQM_v867` 내부의 React/Web UI와 FastAPI 레이어를, 기존 `864 Tkinter UI`의 핵심 업무 흐름과 최소 동등 수준까지 끌어올리기 위한 **P0(최우선) 패치 설계서**이다.

이 문서의 기준은 다음과 같다.

- **기준 업무 원형**: 864 Tkinter UI
- **대상 구현물**: 867 React UI + `react_api`
- **핵심 원칙**:
  1. 기존 `engine_modules` 업무 로직을 재사용한다.
  2. React/FastAPI에 신규 업무 규칙을 임의로 만들지 않는다.
  3. P0에서는 “보기 좋은 UI”보다 “업무 동등성”을 우선한다.
  4. 모든 쓰기 동작은 트랜잭션/롤백/로그를 갖춘다.
  5. 단계별 테스트 게이트를 통과한 뒤 다음 단계로 진행한다.

---

## 1. 현재 상태 진단

### 1-1. 현재 867 구조의 본질

867은 단일 React 앱으로 완전히 이행된 상태가 아니다. 현재 구조는 아래와 같다.

- **기존 Tkinter 데스크톱 본체 유지**
- **별도 React/Web 조회 UI 추가**
- **별도 FastAPI 조회용 API 추가**

즉, 현재 React는 “Tkinter의 완전 대체 UI”가 아니라, **조회 중심 1차 이행본**에 가깝다.

### 1-2. 현재 React가 864 수준에 미달하는 이유

#### A. 메인 화면 동등성 부족
864 Tkinter 기준 주요 탭:
- Inventory
- Allocation
- Picked
- Outbound
- Return
- Move
- Dashboard
- Log
- Scan

867 React 기준 주요 화면:
- Dashboard
- Inventory
- Tonbag
- Allocation
- Outbound
- Picked
- Sold

즉, 아래 핵심 화면이 빠져 있다.
- Return
- Move
- Log
- Scan

#### B. 업무 메뉴 부재
Tkinter에는 입고/출고/도구/보고서/설정 등 대형 업무 메뉴 체계가 있으나, React는 단순 상단 링크 수준이다.

#### C. 모달/다이얼로그 부재
Tkinter에는 아래 업무 다이얼로그가 실사용 수준으로 존재한다.
- LOT 상세
- 원스톱 입고
- 원스톱 출고
- 반품
- 위치 이동
- 승인/미리보기 등

React에는 이에 대응하는 핵심 모달이 사실상 없다.

#### D. 쓰기 API 부재
현재 `react_api`는 GET 중심이며 다음이 없다.
- 입고 생성
- 출고 실행
- 출고 취소
- 위치 업데이트
- 파일 업로드

즉, React는 아직 실행형 업무 화면이 아니다.

---

## 2. P0 범위 정의

## 2-1. P0 목표

P0의 목표는 다음 4가지다.

### 목표 1. 상단 메뉴 구조를 업무용 메뉴 구조로 확장
단순 `NavLink` 바를, 최소한 아래 수준의 드롭다운 메뉴 체계로 올린다.

- 검색
- 도구
- 입고
- 출고
- 현재 탭 표시

### 목표 2. 핵심 업무 모달 3종 구현
- LOT 상세 모달
- 입고 파싱 모달
- 출고 처리 모달

### 목표 3. 쓰기 API 5종 구현
- `POST /inbound/create`
- `POST /outbound/execute`
- `PUT /outbound/cancel`
- `PUT /location/update`
- `POST /files/upload`

### 목표 4. React에서 최소 업무 동등성 확보
아래 흐름이 React에서 가능해야 한다.

1. LOT 조회 → 상세 확인
2. 입고 파일 업로드/파싱 → 생성 실행
3. 출고 대상 선택 → 출고 실행
4. 출고 취소
5. 위치 변경

---

## 2-2. P0에서 의도적으로 제외할 것

다음은 P1/P2로 넘긴다.

- Return 페이지 완전 이식
- Move 페이지 완전 이식
- Scan 페이지 완전 이식
- Log 페이지 완전 이식
- 세부 보고서 화면
- 다중 승인 워크플로 전체 이식
- React 테마/애니메이션 고도화
- 대량 배치처리 UI 세분화
- Telegram Bridge 연계 UI

즉, P0는 **핵심 조작 루프 복구**가 목적이다.

---

## 3. P0 성공 기준 (완료 정의)

다음 조건을 모두 만족해야 P0 완료로 본다.

### 3-1. UI 기준
- 상단 메뉴에 `검색/도구/입고/출고/현재 탭` 표시
- LOT 행 클릭 시 상세 모달 오픈
- 입고 메뉴 클릭 시 입고 파싱 모달 오픈
- 출고 메뉴 클릭 시 출고 처리 모달 오픈

### 3-2. API 기준
- `/docs` 에 쓰기 API 5종 노출
- 요청/응답 스키마 명확
- 성공 시 `{ success, message, data }` 반환
- 실패 시 4xx/5xx + 롤백 + 로그

### 3-3. 업무 기준
- 실제 엔진 함수가 호출됨
- DB 상태 변경이 반영됨
- 취소/오류 시 원복 가능함
- 읽기 화면에서 변경 결과가 즉시 보임

### 3-4. 테스트 기준
- 단위 테스트
- API 스모크 테스트
- UI 수동 점검 체크리스트
- 최소 1회 회귀 점검

---

## 4. 권장 설계 원칙

## 4-1. 신규 업무 규칙 금지
FastAPI 또는 React에 “새로운 출고 규칙/입고 규칙”을 넣지 않는다.  
기존 `engine_modules/inventory_modular/*` 의 업무 규칙을 호출하는 **어댑터 계층**만 추가한다.

## 4-2. 서비스 계층 도입
`react_api` 라우트에서 직접 DB/엔진을 호출하지 말고, 다음 구조를 둔다.

```text
React UI
 -> API Client
 -> FastAPI Router
 -> Service Layer
 -> Engine Adapter
 -> engine_modules
 -> DB
```

## 4-3. 공통 응답 포맷 통일
모든 쓰기 API는 아래 포맷 통일:

```json
{
  "success": true,
  "message": "Operation completed",
  "data": {}
}
```

## 4-4. 트랜잭션 보호
쓰기 API는 반드시:
- begin
- validate
- engine call
- commit
- except -> rollback
- audit log

순서를 갖는다.

## 4-5. React는 얇게, 서버는 명시적으로
검증/조작은 서버 중심으로 두고, React는 입력/표시/상태 갱신에 집중시킨다.

---

## 5. 실제 파일 단위 패치 설계

## 5-1. React 프론트엔드

### A. `web/src/App.jsx`
역할:
- 전체 라우팅
- 상단 내비게이션

P0 수정:
- 기존 단순 `NavLink` 바를 유지하되,
- 그 위 또는 옆에 업무용 메뉴바 추가
- 현재 탭 표시 영역 추가
- 공통 모달 상태 컨테이너 추가

필수 추가 상태:
- `lotDetailModalOpen`
- `inboundModalOpen`
- `outboundModalOpen`
- `activeTabLabel`

권장 방식:
- `LayoutShell` 또는 `TopMenuBar` 컴포넌트 분리

### B. 신규 `web/src/components/TopMenuBar.jsx`
역할:
- 업무용 드롭다운 메뉴 렌더링

메뉴 구조(최소):
- 검색
  - 통합 검색 열기
- 도구
  - Excel 내보내기
  - 정합성 체크
- 입고
  - 입고 파싱 모달 열기
- 출고
  - 출고 처리 모달 열기
- 현재 탭
  - 읽기 전용 표시

P0에서는 “실제 Tkinter 전체 메뉴 완전 복제”가 아니라 최소 업무 동등성 메뉴만 구현

### C. 신규 `web/src/components/modals/LotDetailModal.jsx`
역할:
- LOT 클릭 시 상세 표시

데이터 소스:
- `GET /lot/{lot_no}`

표시 항목:
- 기본 LOT 정보
- 톤백 목록
- 이력 요약
- 배정/출고 상태 요약

P0 버튼:
- 닫기
- 새로고침
- 위치변경 열기(선택)
- 출고 처리 열기(선택)

### D. 신규 `web/src/components/modals/InboundParseModal.jsx`
역할:
- 파일 업로드 → 파싱 결과 미리보기 → 생성 실행

단계:
1. 파일 선택
2. 업로드
3. 파싱 결과 표시
4. LOT 생성 예정 요약
5. 생성 실행

P0에서는 미리보기는 단순 테이블 수준으로 충분

### E. 신규 `web/src/components/modals/OutboundExecuteModal.jsx`
역할:
- LOT/톤백 선택 → 출고 정보 입력 → 실행

입력:
- lot_no 또는 tonbag_id
- quantity
- destination/customer
- optional memo

P0 버튼:
- 실행
- 취소

### F. `web/src/pages/InventoryPage.jsx`
P0 수정:
- LOT 행 클릭 이벤트 추가
- LOT 상세 모달 오픈
- 변경 후 새로고침 기능 추가

### G. `web/src/api/inventoryApi.js`
수정:
- `getLotDetail(lotNo)` 추가
- `updateLocation(payload)` 추가
- 공통 에러 처리 추가

### H. 신규 `web/src/api/actionApi.js`
추가 함수:
- `uploadInboundFile(formData)`
- `createInbound(payload)`
- `executeOutbound(payload)`
- `cancelOutbound(payload)`
- `updateLocation(payload)`

---

## 5-2. FastAPI 백엔드

### A. `react_api/main.py`
수정:
- 신규 write router include
- 태그 정리
- `/docs` 에 노출 확인

### B. 신규 `react_api/routes/actions.py`
역할:
- P0 쓰기 API 집합

엔드포인트:
- `POST /files/upload`
- `POST /inbound/create`
- `POST /outbound/execute`
- `PUT /outbound/cancel`
- `PUT /location/update`

### C. 신규 `react_api/schemas/actions.py`
Pydantic 모델 정의:
- `InboundCreateRequest`
- `OutboundExecuteRequest`
- `OutboundCancelRequest`
- `LocationUpdateRequest`
- `ApiResult`

### D. 신규 `react_api/services/action_service.py`
역할:
- 요청 검증
- 엔진 어댑터 호출
- 트랜잭션/로그 관리

### E. 신규 `react_api/services/engine_adapter.py`
역할:
- 기존 `engine_modules` 함수와 연결

절대 원칙:
- 비즈니스 규칙은 여기서 새로 만들지 않음
- 필요한 매개변수 변환만 수행

---

## 5-3. 엔진 연결 후보

P0에서 연결 우선 후보는 아래와 같다.

### 입고
- `engine_modules/inventory_modular/inbound_mixin.py`
  - `process_inbound`

### 출고
- `engine_modules/inventory_modular/outbound_mixin.py`
  - `process_outbound`
  - `cancel_outbound_tonbag`

### LOT 상세 조회
- `engine_modules/inventory_modular/query_mixin.py`
  - `get_lot_detail`
  - `get_lot_items`

### 위치 변경
- `engine_modules/inventory_modular/tonbag_mixin.py`
  - `update_tonbag_location`
  - 필요 시 batch move 관련 함수

P0 권장:
- 신규 API는 위 엔진 함수 wrapping 방식
- DB 직접 조작 최소화
- 기존 예외 메시지를 사용자 메시지로 정리만 함

---

## 6. 데이터/트랜잭션 설계

## 6-1. 공통 처리 순서

모든 쓰기 API 공통:

```text
request 수신
-> pydantic 검증
-> service validate
-> DB connection/session begin
-> engine adapter call
-> 결과 확인
-> success log
-> commit
-> 응답 반환
```

실패 시:

```text
except
-> rollback
-> error log
-> 에러 응답
```

## 6-2. 로그 설계

P0 최소 로그 항목:
- endpoint
- request summary
- operator
- lot_no / tonbag_id
- success/fail
- error_message
- timestamp

로그 파일 예:
- `logs/react_api_actions.log`

---

## 7. UI 상세 설계

## 7-1. 상단 메뉴바

권장 배치:

```text
[검색] [도구] [입고] [출고]                [현재 탭: Inventory]
```

스타일:
- 복잡한 디자인보다 명확성 우선
- 데스크톱 폭 기준
- 모바일 대응은 P0 범위 밖

## 7-2. LOT 상세 모달

권장 섹션:
1. 기본정보
2. 톤백 목록
3. 상태/배정 요약
4. 최근 이력(가능 시)

폭:
- `max-width: 960px` 정도 권장

## 7-3. 입고 파싱 모달

좌측:
- 파일 업로드
- 옵션 선택

우측:
- 파싱 결과 미리보기
- 생성 예정 LOT 요약

## 7-4. 출고 처리 모달

입력:
- LOT / 톤백
- 수량
- 출고처
- 메모

하단:
- 실행
- 닫기

---

## 8. 마이크로 배치 실행 순서

P0를 아래 4개 배치로 쪼개는 것을 권장한다.

### Batch P0-1: 구조 준비
목표:
- router/service/schema/component 골격 생성
- App.jsx 메뉴바 슬롯 확보
- 공통 응답 포맷 정리

완료 기준:
- 빌드/실행 에러 없음
- `/docs` 에 write endpoints 틀만 노출

### Batch P0-2: LOT 상세 모달
목표:
- Inventory 행 클릭
- LOT 상세 API 호출
- 모달 렌더링

완료 기준:
- LOT 클릭 시 상세 정보 표시

### Batch P0-3: 입고/출고 쓰기 루프
목표:
- 파일 업로드
- 입고 생성
- 출고 실행
- 출고 취소

완료 기준:
- 실제 DB 반영 확인
- 오류 시 rollback 확인

### Batch P0-4: 위치 업데이트 + 회귀 점검
목표:
- 위치 수정 API
- 화면 재조회
- UI/API 스모크 테스트
- P0 체크리스트 완료

완료 기준:
- 위치 변경 성공
- 전체 P0 수동 테스트 통과

---

## 9. 테스트 설계

## 9-1. Pre-Test
- `python -m py_compile react_api/main.py`
- `python -m py_compile react_api/routes/actions.py`
- 프론트 `npm build` 또는 기존 build 명령
- 기존 앱 부팅 확인

## 9-2. API 테스트
최소 케이스:
1. `/api/health`
2. `/lot/{lot_no}`
3. `/files/upload`
4. `/inbound/create`
5. `/outbound/execute`
6. `/outbound/cancel`
7. `/location/update`

## 9-3. UI 수동 테스트
체크리스트:
- 상단 메뉴 클릭 가능
- 모달 열림/닫힘 정상
- 잘못된 입력시 경고
- 성공 후 목록 새로고침
- 실패 후 상태 불일치 없음

## 9-4. 회귀 테스트
- 기존 조회 페이지 깨짐 여부
- Dashboard/Inventory/Allocation/Picked/Outbound 정상 표시
- 기존 GET API 응답 영향 없음

---

## 10. 리스크와 대응

### 리스크 1. 엔진 함수 시그니처 불일치
대응:
- 어댑터 계층에서만 변환
- 라우트에서 직접 호출 금지

### 리스크 2. DB 트랜잭션 경계 불명확
대응:
- service 계층에서 begin/commit/rollback 고정
- 예외 핸들링 중앙화

### 리스크 3. Tkinter 로직과 React 로직이 중복될 위험
대응:
- React는 반드시 engine_modules 재사용
- 신규 SQL 분산 작성 금지

### 리스크 4. 업로드/파싱 단계 복잡도 상승
대응:
- P0에서는 단일 파일/기본 옵션 우선
- 세부 템플릿/복수 캐리어 고도화는 P1

---

## 11. 권장 결과물 목록

P0 완료 후 산출물 권장 목록:

```text
docs/RECON_V867_WEB_MIGRATION_MAP.md
docs/P0_PATCH_DESIGN_v867.md
react_api/routes/actions.py
react_api/services/action_service.py
react_api/services/engine_adapter.py
react_api/schemas/actions.py
web/src/components/TopMenuBar.jsx
web/src/components/modals/LotDetailModal.jsx
web/src/components/modals/InboundParseModal.jsx
web/src/components/modals/OutboundExecuteModal.jsx
web/src/api/actionApi.js
tests/test_react_api_actions.py
tests/test_ui_p0_checklist.md
```

---

## 12. 루비 권장안

가장 안전한 방향은 다음과 같다.

### 권장안 A. “기능 동등성 우선”
React를 예쁘게 다시 만들기보다,
먼저 Tkinter의 핵심 업무 루프를 React에서 수행 가능하게 만든다.

### 권장안 B. “엔진 재사용 100%”
신규 비즈니스 규칙을 React/FastAPI에 만들지 말고,
무조건 기존 `engine_modules`를 감싼다.

### 권장안 C. “P0는 4개 배치로만”
한 번에 대형 패치를 하지 말고,
P0-1 ~ P0-4로 잘라 테스트 게이트를 강제한다.

### 권장안 D. “Return/Move/Scan은 P1”
P0에서 욕심내면 전체가 흔들린다.
P0는 LOT 상세/입고/출고/위치만 먼저 복구한다.

---

## 13. 최종 한 줄 결론

867 React를 864 Tkinter 수준으로 끌어올리는 P0의 핵심은  
**“메뉴바 + 핵심 모달 3종 + 쓰기 API 5종 + 기존 엔진 재사용 어댑터 계층”** 이다.

이 4가지를 먼저 완성해야, 그 다음에 Return/Move/Scan/보고서/고급 워크플로를 안전하게 올릴 수 있다.
