# GPT_SQM_P0_통합체크리스트_v2.md
생성일: 2026-04-04 14:59 (Asia/Seoul)  
기준: Claude_SQM_v867 / Claude_SQM_v864_20260329_FULL / MASTER_FINAL_v867_통합완성본.md

---

## [질문]
867 React를 864 Tkinter 수준으로 끌어올리기 위한  
**P0 구현 배치 + Patch 검증 단계 통합 체크리스트 v2**를 작성해 달라는 요청

## [질문의도]
기존에 분리되어 있던 두 축을 하나로 통합한다.

- **P0-1 ~ P0-4**: 무엇을 구현할지 정하는 배치 기준
- **Patch 1 ~ 5**: 어떻게 검증하고 다음 단계로 넘어갈지 정하는 검증 기준

즉, 이번 문서는 다음 원칙으로 작성한다.

```text
구현 배치와 검증 단계를 따로 놀게 두지 않는다.
각 구현 배치마다 연결되는 Patch 검증 단계를 붙인다.
테스트 실패 시 다음 단계로 넘어가지 않는다.
```

---

# 1. 문서 목적

이 문서는 867 React/Web + FastAPI 구조를  
864 Tkinter의 핵심 업무 수준까지 끌어올리기 위한 **P0 실행 기준서**다.

이번 P0의 핵심 목표는 아래 4개다.

```text
1) 상단 메뉴 체계 복구
2) 핵심 모달 3종 복구
3) write API 5종 실연결
4) 기존 engine_modules 재사용 + 트랜잭션/rollback 검증
```

---

# 2. 상위 실행 원칙

## 2-1. 단계 진행 원칙

모든 단계는 반드시 아래 순서를 따른다.

```text
Pre-Test
→ 구현
→ Post-Test
→ 실패 시 수정
→ Re-Test
→ 통과
→ 다음 단계
```

## 2-2. 금지 사항

```text
- 실제 engine_modules 호출 없이 mock로만 완료 처리 금지
- DB rollback 검증 없이 write API 완료 처리 금지
- files/upload가 실제 parser와 연결되지 않은 상태에서 완료 처리 금지
- run.py / run_bootstrap.py / run_react.bat 동작 확인 없이 통합 완료 처리 금지
- tkinter 동등성 핵심 기능 누락 상태에서 P0 완료 선언 금지
```

## 2-3. P0 완료 판정 기준

P0 완료는 아래 조건을 모두 만족해야 한다.

```text
A. 상단 메뉴바가 동작한다
B. LOT 상세 모달이 열린다
C. 입고 파싱 모달이 실제 parser + files/upload와 연결된다
D. 출고 실행/취소가 실제 engine 로직과 연결된다
E. 위치 변경 API가 실제 engine 로직과 연결된다
F. rollback 검증이 끝난다
G. DB 로그/이벤트 테이블 호환성이 확인된다
H. run.py / run_bootstrap.py / run_react.bat 실행 체계가 정리된다
I. API + Frontend + Tkinter 병행 테스트가 끝난다
```

---

# 3. 구현 배치 ↔ Patch 검증 통합 맵

| 구현 배치 | 핵심 구현 내용 | 연결 검증 Patch | 판정 |
|---|---|---|---|
| **P0-1** | 구조 준비 / 공통 뼈대 / 실행 환경 정리 | Patch 3, Patch 4 | 부분 중복 + 통합 필요 |
| **P0-2** | LOT 상세 모달 | Patch 5 | 대부분 비중복 |
| **P0-3** | 입고/출고 write loop | Patch 1, Patch 2 | 중복 높음, 반드시 통합 |
| **P0-4** | 위치 업데이트 + 회귀 + 통합 실행 | Patch 3, Patch 4, Patch 5 | 부분 중복 + 운영 검증 강화 |

---

# 4. P0-1 구조 준비 + Patch 3/4 통합 체크리스트

## 4-1. 목적

React/FASTAPI/write API 패치를 얹을 수 있는 최소 안정 구조를 먼저 만든다.

## 4-2. 구현 범위

### Frontend
- [ ] `web/src/App.jsx`에 메뉴바/모달 삽입 위치 확정
- [ ] `web/src/components/TopMenuBar.jsx` 생성
- [ ] `web/src/components/modals/` 폴더 생성
- [ ] `LotDetailModal.jsx`, `InboundParseModal.jsx`, `OutboundExecuteModal.jsx` 파일 뼈대 생성
- [ ] `web/src/api/actionApi.js` 생성
- [ ] 공통 요청/응답/에러 처리 유틸 정리

### Backend
- [ ] `react_api/routes/actions.py` 생성
- [ ] `react_api/schemas/actions.py` 생성
- [ ] `react_api/services/action_service.py` 생성
- [ ] `react_api/services/engine_adapter.py` 생성
- [ ] `react_api/main.py` 또는 라우터 등록부에 actions 라우트 연결
- [ ] 공통 성공/실패 응답 포맷 정의

### Engine 재사용 연결 준비
- [ ] `inbound_mixin.py` 호출 경로 확인
- [ ] `outbound_mixin.py` 호출 경로 확인
- [ ] `query_mixin.py` LOT 상세 조회 경로 확인
- [ ] `tonbag_mixin.py` 위치 변경 경로 확인
- [ ] 현재 engine 인스턴스 생성/주입 방식 정리

## 4-3. Patch 3: DB 스키마 호환성 체크

- [ ] `audit_log` 테이블 존재 확인
- [ ] `audit_log` 컬럼 목록 확인
- [ ] write API에서 필요한 컬럼과 실제 컬럼 비교
- [ ] `outbound_event_log` 테이블 존재 확인
- [ ] 이벤트 기록에 필요한 컬럼 확인
- [ ] 컬럼 누락 시 migration 스크립트 설계
- [ ] nullable / default / timestamp 호환성 확인
- [ ] rollback 발생 시 로그 기록 정책 확인

## 4-4. Patch 4: 실행 파일 연동 준비

- [ ] `run.py` 역할 확인
- [ ] `run_bootstrap.py` 역할 확인
- [ ] `run_react.bat` 실행 흐름 확인
- [ ] `run_react_api.py` 존재/동작 확인
- [ ] `.env` 로드 위치 확인
- [ ] API/Frontend/Tkinter 각각의 포트/경로 충돌 여부 확인

## 4-5. Pre-Test

- [ ] `python -m py_compile react_api/main.py`
- [ ] `python -m py_compile react_api/routes/actions.py`
- [ ] `python -m py_compile react_api/services/action_service.py`
- [ ] `python -m py_compile react_api/services/engine_adapter.py`
- [ ] Frontend import 오류 점검
- [ ] DB 연결 smoke test

## 4-6. 완료 기준

```text
- actions 라우트가 서버에 등록된다
- 새 컴포넌트/모달 뼈대가 빌드 오류 없이 존재한다
- audit_log / outbound_event_log 호환성이 확인된다
- 실행 파일 구조와 .env 로드 위치가 확정된다
```

## 4-7. 실패 시 조치

- [ ] import 순환 제거
- [ ] DB 컬럼 mismatch 수정
- [ ] actions router 등록 누락 수정
- [ ] 환경변수 로드 누락 수정
- [ ] 기존 실행 경로와 충돌하는 포트/경로 수정

---

# 5. P0-2 LOT 상세 모달 + Patch 5 일부 통합 체크리스트

## 5-1. 목적

Tkinter 수준의 핵심 조회 UX를 React에서 먼저 복구한다.  
이 단계는 Patch 1~4보다 직접 중복이 적으므로 **별도 필수 배치**다.

## 5-2. 구현 범위

### UI
- [ ] `LotDetailModal.jsx` 기본 레이아웃 구현
- [ ] 모달 열기/닫기 동작 구현
- [ ] 로딩 상태 표시
- [ ] 에러 상태 표시
- [ ] 기본정보 섹션 구현
- [ ] 톤백 목록 섹션 구현
- [ ] 이력 섹션 구현
- [ ] 배정 상태 섹션 구현

### 호출 연결
- [ ] Inventory 페이지에서 LOT 클릭 시 모달 오픈
- [ ] Allocation 페이지에서 LOT 클릭 시 모달 오픈
- [ ] Tonbag 페이지에서 관련 LOT로 모달 오픈
- [ ] `/lot/{lot_no}` 또는 동등 조회 API와 연결
- [ ] 데이터 shape mismatch 시 프론트 어댑터 적용

## 5-3. Pre-Test

- [ ] LOT 상세 API 응답 확인
- [ ] LOT 번호 없는 경우 예외 처리 확인
- [ ] 404/500 에러 처리 확인
- [ ] 빈 데이터에서도 모달이 깨지지 않는지 확인

## 5-4. Post-Test / Patch 5 연계 확인

- [ ] 실제 LOT 클릭 → 모달 오픈 확인
- [ ] 모달 닫기 후 다시 열기 확인
- [ ] 다른 LOT로 전환 시 데이터 재조회 확인
- [ ] Tkinter LOT 상세 화면과 주요 항목 비교
- [ ] 필수 항목 누락 여부 점검

## 5-5. 완료 기준

```text
- React에서 LOT 클릭 시 상세 모달이 정상 동작한다
- 기본정보 / 톤백 / 이력 / 배정 상태가 표시된다
- 오류/빈 데이터/재조회 케이스에서 깨지지 않는다
```

## 5-6. 실패 시 조치

- [ ] API 응답 키와 UI 매핑 재점검
- [ ] LOT 식별자 파라미터 전달 방식 수정
- [ ] 이력/배정 상태 데이터가 분리 API면 통합 어댑터 추가
- [ ] 큰 테이블 렌더링 시 pagination 또는 lazy load 검토

---

# 6. P0-3 입고/출고 write loop + Patch 1/2 통합 체크리스트

## 6-1. 목적

React + FastAPI에서 실제 업무 실행 루프를 살린다.

```text
파일 업로드
→ parser 실행
→ 파싱 결과 확인
→ 입고 생성
→ 출고 실행
→ 출고 취소
→ rollback 검증
```

## 6-2. 구현 범위

### API
- [ ] `POST /files/upload`
- [ ] `POST /inbound/create`
- [ ] `POST /outbound/execute`
- [ ] `PUT /outbound/cancel`

### Frontend
- [ ] `InboundParseModal.jsx` 구현
- [ ] 업로드 UI 구현
- [ ] PDF 업로드 구현
- [ ] Excel 업로드 구현
- [ ] 파싱 결과 미리보기 구현
- [ ] 생성 예정 LOT 요약 표시
- [ ] 사용자 확인 후 입고 생성 버튼 구현
- [ ] `OutboundExecuteModal.jsx` 구현
- [ ] 출고 수량 / 출고처 / 대상 톤백 입력 UI 구현
- [ ] 출고 실행 버튼 구현
- [ ] 출고 취소 UI 또는 액션 연결

### Backend Service / Adapter
- [ ] 파일 업로드 저장 처리
- [ ] 파일 유형 판별 처리
- [ ] parser 분기 처리
- [ ] parser 결과 표준 JSON 변환
- [ ] `process_inbound()` 어댑터 연결
- [ ] `process_outbound()` 어댑터 연결
- [ ] `cancel_outbound_tonbag()` 어댑터 연결
- [ ] DB transaction begin/commit/rollback 적용
- [ ] 감사 로그 / 이벤트 로그 기록 연결

## 6-3. Patch 1 실연결 검증

- [ ] `process_inbound()` 실제 호출 테스트
- [ ] 더미 호출이 아닌 DB 변화가 있는 실제 호출 확인
- [ ] `process_outbound()` 실제 호출 테스트
- [ ] `cancel_outbound_tonbag()` 실제 호출 테스트
- [ ] 잘못된 입력에서 rollback 발생 확인
- [ ] rollback 후 DB 원상복구 확인
- [ ] 성공/실패 로그 기록 확인

## 6-4. Patch 2 파서 연동 검증

- [ ] PDF parser → `/files/upload` 실연결 확인
- [ ] Excel parser → `/files/upload` 실연결 확인
- [ ] 파싱 결과 preview JSON 정상화 확인
- [ ] 파싱 결과 → InboundParseModal 자동 채움 확인
- [ ] 파싱 실패 시 사용자 메시지 확인
- [ ] 손상 파일 / 빈 파일 / 지원 안 되는 형식 예외 처리 확인

## 6-5. Pre-Test

- [ ] parser 단독 테스트
- [ ] upload 경로 쓰기 권한 확인
- [ ] inbound/outbound engine 단독 smoke test
- [ ] test DB 또는 복제 DB로 실험 가능 상태 확인

## 6-6. Post-Test

- [ ] PDF 업로드 → preview 성공
- [ ] Excel 업로드 → preview 성공
- [ ] preview → inbound/create 성공
- [ ] outbound/execute 성공
- [ ] outbound/cancel 성공
- [ ] 실패 케이스 rollback 성공

## 6-7. 완료 기준

```text
- 파일 업로드부터 입고 생성까지 실제로 돈다
- 출고 실행/취소가 실제 engine 호출로 돈다
- rollback이 실제로 검증된다
- parser 결과가 입고 모달을 자동 채운다
```

## 6-8. 실패 시 조치

- [ ] parser 출력 포맷을 action schema에 맞게 보정
- [ ] engine 인자 순서/형식 mismatch 수정
- [ ] transaction 범위 재설정
- [ ] cancel 대상 식별자 로직 재점검
- [ ] DB side effect 잔존 여부 재확인

---

# 7. P0-4 위치 업데이트 + 회귀 + 통합 실행 + Patch 3/4/5 통합 체크리스트

## 7-1. 목적

write API를 완성하고, 실제 운영 진입 가능한 실행 체계까지 묶는다.

## 7-2. 구현 범위

### API
- [ ] `PUT /location/update` 구현
- [ ] tonbag/location 식별 파라미터 정의
- [ ] validation 추가
- [ ] 실제 `update_tonbag_location()` 또는 동등 로직 연결
- [ ] 성공/실패 응답 표준화

### Frontend
- [ ] 위치 변경 요청 UI 추가
- [ ] 대상 톤백 선택 흐름 연결
- [ ] 새 위치 입력 필드 구현
- [ ] 성공 후 화면 재조회/알림 처리
- [ ] 실패 시 에러 표시

## 7-3. Patch 3 재검증

- [ ] 위치 변경 시 audit_log 기록 확인
- [ ] outbound_event_log와 충돌 없는지 확인
- [ ] migration 반영 후 기존 조회 API 영향 없는지 확인

## 7-4. Patch 4 실행 체계 반영

- [ ] `run.py` 수정 필요 여부 반영
- [ ] `run_bootstrap.py` 수정 필요 여부 반영
- [ ] `run_react.bat`에서 API + Frontend 동시 실행 반영
- [ ] `.env` 공통 로드 적용
- [ ] 시작 순서 / 포트 / 경로 명시
- [ ] 오류 발생 시 로그 파일 출력 경로 명시

## 7-5. Patch 5 통합 테스트

- [ ] API 서버 기동 확인
- [ ] Frontend 접속 확인
- [ ] 입고 실 테스트
- [ ] 출고 실 테스트
- [ ] 출고 취소 실 테스트
- [ ] 위치 변경 실 테스트
- [ ] LOT 상세 모달 실 테스트
- [ ] tkinter 앱 동시 실행 테스트
- [ ] DB 락/포트 충돌 여부 확인
- [ ] 전체 흐름 회귀 테스트

## 7-6. Pre-Test

- [ ] clean start 가능한지 확인
- [ ] 기존 프로세스 종료 상태 확인
- [ ] 테스트용 데이터셋 준비
- [ ] 로그 디렉토리 준비

## 7-7. 완료 기준

```text
- 위치 변경 API가 실제 engine과 연결된다
- API + Frontend + Tkinter 병행 테스트가 통과한다
- run_react.bat 또는 동등 실행 스크립트가 정리된다
- 전체 P0 흐름이 재현 가능하다
```

## 7-8. 실패 시 조치

- [ ] DB lock 회피 전략 적용
- [ ] 동시 실행 포트 재배치
- [ ] 환경변수 누락 수정
- [ ] 위치 변경 후 캐시/재조회 로직 수정
- [ ] startup order 문제 수정

---

# 8. 단계 간 진입 게이트

## Gate A: P0-1 → P0-2 진입 조건
- [ ] actions/router/schema/service skeleton 완성
- [ ] DB 스키마 위험 요소 식별 완료
- [ ] 실행 파일 구조 파악 완료

## Gate B: P0-2 → P0-3 진입 조건
- [ ] LOT 상세 모달 동작
- [ ] LOT 관련 조회 데이터 shape 확정
- [ ] 에러 핸들링 안정화

## Gate C: P0-3 → P0-4 진입 조건
- [ ] files/upload 실연결 완료
- [ ] inbound/create 실연결 완료
- [ ] outbound/execute/cancel 실연결 완료
- [ ] rollback 검증 완료

## Gate D: P0-4 → P0 완료 조건
- [ ] location/update 실연결 완료
- [ ] run/bat/.env 통합 완료
- [ ] API + Frontend + Tkinter 통합 테스트 완료

---

# 9. 우선순위(P0 내부 재정렬)

루비 권장 실제 실행 순서는 아래와 같다.

```text
1. P0-1 구조 준비 + DB/실행 파일 점검
2. P0-2 LOT 상세 모달
3. P0-3 입고/출고 write loop
4. P0-4 위치 업데이트 + 통합 실행 + 회귀
```

Patch 기준으로 보면 아래처럼 대응한다.

```text
P0-1 ↔ Patch 3 + Patch 4
P0-2 ↔ Patch 5 일부
P0-3 ↔ Patch 1 + Patch 2
P0-4 ↔ Patch 3 + Patch 4 + Patch 5
```

---

# 10. 최종 산출물 체크리스트

## 문서
- [ ] RECON/V867 반영 문서
- [ ] P0 통합 체크리스트 v2
- [ ] P0 테스트 결과 보고서
- [ ] DB migration 메모

## Backend
- [ ] `actions.py`
- [ ] `actions.py` 라우트 등록
- [ ] `schemas/actions.py`
- [ ] `services/action_service.py`
- [ ] `services/engine_adapter.py`

## Frontend
- [ ] `TopMenuBar.jsx`
- [ ] `LotDetailModal.jsx`
- [ ] `InboundParseModal.jsx`
- [ ] `OutboundExecuteModal.jsx`
- [ ] `actionApi.js`

## 실행
- [ ] `run_react.bat` 업데이트
- [ ] `.env` 통합 로드
- [ ] 실행 로그 정리

---

# 11. 최종 판단 문구

이번 통합 체크리스트 v2의 핵심은 아래다.

```text
P0-1~P0-4는 삭제 대상이 아니다.
Patch 1~5도 삭제 대상이 아니다.
둘은 중복되는 것이 아니라,
“구현 배치”와 “검증 단계”라는 서로 다른 축이므로
한 문서 안에서 계층화해서 같이 관리해야 한다.
```

---

# 12. 다음 단계 권장

## 루비 권장안

다음으로 가장 효율적인 작업은 아래 3개 중 하나다.

1. **Claude Code용 실행 프롬프트화**
2. **P0-1만 별도로 떼어 초상세 작업지시서화**
3. **실제 수정 파일별 patch map 작성**

권장 순서는 아래다.

```text
1) P0-1 초상세 지시서
2) Claude Code 실행 프롬프트
3) 실제 patch map
```
