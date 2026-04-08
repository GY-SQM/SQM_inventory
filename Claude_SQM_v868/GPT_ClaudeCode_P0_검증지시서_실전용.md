# GPT Claude Code P0 검증 지시서 (실전용)
생성일시: 2026-04-04 16:44 (Asia/Seoul)
기준 원본: Claude_SQM_v867
인코딩: UTF-8
문서 목적: P0 수정 결과를 실제 운영 가능 수준으로 검증하고, 실패 시 자동 수정 후 재검증하며, 텔레그램 브리지 환경에서도 중단 없이 진행하기 위한 Claude Code 실행 기준서

---

## 0. 절대 실행 규칙

### 자율 실행 규칙
- 절대 사용자에게 확인 질문을 하지 말 것.
- 모든 선택은 코드와 로그를 근거로 스스로 판단할 것.
- 파일 덮어쓰기, 테스트 파일 생성, 검증 스크립트 생성은 자동 승인된 것으로 간주할 것.
- 테스트 실패 시 원인을 분석하고 즉시 수정 후 재검증할 것.
- 부분 완료 상태에서 멈추지 말 것.
- 각 단계 완료 후 자동으로 다음 단계로 진행할 것.
- 실제 v867 구조와 현재 수정 상태를 먼저 조사한 뒤 검증할 것.

### 강제 테스트 규칙
모든 단계는 반드시 아래 순서를 따른다.

```text
Pre-Test → 구현/수정 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계
```

테스트 실패 상태에서 다음 단계로 진행 금지.

### 금지 사항
- mock만 통과시키고 실제 engine 호출을 생략하는 행위 금지
- rollback 확인 없이 write API 완료 처리 금지
- 로그 저장 확인 없이 성공 선언 금지
- 파서 실연결 없이 files/upload 완료 처리 금지
- run.py / run_bootstrap.py / run_react.bat 실행 체계 확인 없이 P0 완료 선언 금지
- 실제 구조 조사 없이 임의 경로 가정 후 수정 금지

---

## 1. 이번 검증의 기준 상태

현재 P0 수정 결과는 아래 상태를 기준으로 한다.

### 이미 수정된 핵심 내용
1. `react_api/utils/db.py`
   - `get_engine()` 추가
   - `SQMInventoryEngineV3` 반환 구조로 변경

2. `react_api/services/inbound_write_service.py`
   - `db: SQMDatabase` 의존을 `engine: SQMInventoryEngineV3` 의존으로 전환

3. `react_api/services/outbound_write_service.py`
   - 출고 실행 / 취소를 engine 기반으로 전환
   - 위치 변경은 `update_tonbag_location()` 경유로 전환
   - 7개 hard-stop 검증 반영

4. `react_api/routes/inbound.py`
   - `get_db()` → `get_engine()`

5. `react_api/routes/outbound_write.py`
   - `get_db()` → `get_engine()`

6. `react_api/routes/location.py`
   - `get_db()` → `get_engine()`

7. `react_api/schemas/write_models.py`
   - `LocationUpdateRequest`에 `reason_code`, `operator`, `note` 필드 추가

### 이미 확인된 결과
- 위 7개 파일 `py_compile` 통과
- Engine 6개 메서드 `hasattr` 전부 True
- FastAPI 앱 로드 성공
- 5개 Write 라우트 등록 확인

### 이번 검증의 핵심 의미
기존의 잘못된 DB 직접 호출이 아니라, 실제 업무 엔진을 통한 write API 구조가 형성되었는지 검증하는 단계다.
즉, 이번 검증의 목적은 “코드가 존재한다”가 아니라 “실제 업무 로직이 돈다”를 증명하는 것이다.

---

## 2. 이번 검증의 최종 목표

이번 P0 검증의 최종 목표는 아래 9개를 모두 만족하는 것이다.

1. 5개 Write API가 실제 HTTP 요청으로 정상 동작한다.
2. 모든 write API가 실제 `SQMInventoryEngineV3` 경유로 수행된다.
3. 실패 케이스에서 rollback이 실제로 발생한다.
4. rollback 후 DB side effect가 남지 않는다.
5. `audit_log` 및 `outbound_event_log` 기록이 실제로 남는다.
6. `location/update`의 7개 hard-stop이 케이스별로 검증된다.
7. `files/upload`가 실제 parser와 연결되어 preview 또는 후속 입력에 사용 가능하다.
8. run.py / run_bootstrap.py / run_react.bat / .env 실행 체계가 깨지지 않는다.
9. 결과가 `docs/P0_WRITE_API_VALIDATION_REPORT.md`에 정리된다.

---

## 3. 이번 단계의 검증 범위

### A. API 실호출 검증 대상
```text
POST /files/upload
POST /inbound/create
POST /outbound/execute
PUT  /outbound/cancel
PUT  /location/update
```

### B. 엔진 연결 검증 대상
- `process_inbound`
- `process_outbound`
- `cancel_outbound_tonbag`
- `update_tonbag_location`
- 파일 파싱 관련 연결 함수

### C. 로그 / 트랜잭션 검증 대상
- `audit_log`
- `outbound_event_log`
- commit / rollback 경계
- 실패 후 원상복구 여부

### D. 실행 체계 검증 대상
- `run.py`
- `run_bootstrap.py`
- `run_react.bat`
- `.env`
- API + Frontend + Tkinter 동시 구동 시 충돌 여부

---

## 4. 작업 순서

### Step 1. Recon 재확인
다음 항목을 먼저 조사하고 실제 경로를 확인한다.

1. 현재 등록된 FastAPI write 라우트 실제 경로
2. 각 route가 받는 request schema 이름과 필드
3. service 계층에서 engine을 어떤 방식으로 주입받는지
4. engine이 DB transaction을 내부에서 처리하는지, service에서 처리하는지
5. `audit_log`, `outbound_event_log` 실제 스키마
6. parser 진입점과 업로드 저장 경로
7. 테스트용 DB 또는 복제 DB 사용 가능 여부

산출물:
- `docs/P0_RECON_VALIDATION_MAP.md`

### Step 2. 검증 스크립트 / 테스트 골격 작성
아래 중 실제 프로젝트 구조에 맞는 방식을 선택한다.

권장 우선순위:
1. `pytest` 기반 API 테스트 추가
2. 보조용 smoke script 추가

생성 후보:
- `tests/api/test_p0_write_apis.py`
- `scripts/validate_p0_write_apis.py`

규칙:
- 테스트는 성공 케이스와 실패 케이스를 모두 가진다.
- 실패 케이스는 rollback과 로그 기록까지 검증한다.
- 테스트 데이터는 운영 DB를 직접 오염시키지 않도록 분리 또는 복제 기반으로 한다.

### Step 3. 5개 Write API 실제 HTTP 검증
각 API마다 아래를 모두 검증한다.

#### 3-1. POST /inbound/create
검증 항목:
- 정상 payload에서 성공하는지
- 실제 `process_inbound()`를 타는지
- LOT / inventory / 관련 이력이 생성되는지
- 잘못된 payload에서 4xx 또는 적절한 오류가 발생하는지
- 실패 시 rollback 되는지
- 성공/실패 로그가 남는지

#### 3-2. POST /outbound/execute
검증 항목:
- 정상 payload에서 성공하는지
- 실제 `process_outbound()`를 타는지
- All-or-Nothing 정책이 지켜지는지
- 상태 전이가 맞는지
- 잘못된 tonbag / LOT / 수량에서 hard-stop 되는지
- 실패 시 rollback 되는지
- 성공/실패 로그가 남는지

#### 3-3. PUT /outbound/cancel
검증 항목:
- 정상 취소가 가능한지
- 실제 `cancel_outbound_tonbag()`을 타는지
- 상태 복원이 맞는지
- 이미 취소되었거나 취소 불가 상태에서 차단되는지
- 실패 시 rollback 또는 무변경이 보장되는지
- 로그가 남는지

#### 3-4. PUT /location/update
검증 항목:
- 정상 위치 변경이 가능한지
- 실제 `update_tonbag_location()`을 타는지
- `reason_code`, `operator`, `note`가 정상 전달/기록되는지
- 7개 hard-stop이 각각 기대대로 작동하는지
- 직접 SQL 우회 없이 엔진 검증 경로를 타는지
- 실패 시 rollback 또는 무변경이 보장되는지
- 로그가 남는지

#### 3-5. POST /files/upload
검증 항목:
- PDF 업로드 성공 여부
- Excel 업로드 성공 여부
- 저장 경로 및 파일 권한 문제 없는지
- parser 진입점까지 연결되는지
- preview 또는 파싱 결과 JSON이 정상인지
- 손상 파일 / 빈 파일 / 비지원 형식에서 적절히 실패하는지
- 실패 시 로그가 남는지

### Step 4. 로그 / DB 무결성 검증
반드시 아래를 확인한다.

1. `audit_log` 테이블 존재 여부
2. 컬럼 스키마와 현재 write 이벤트의 호환성
3. `outbound_event_log` 테이블 존재 여부
4. 출고 실행 / 취소 / 위치변경 시 이벤트 기록 여부
5. 실패 케이스에서 에러 로그 또는 감사 로그 기록 여부
6. rollback 후 레코드 찌꺼기(side effect) 여부

필요 시 조치:
- 누락 컬럼 보정
- migration 추가
- 로그 저장 경로 수정
- service ↔ schema 필드 매핑 수정

### Step 5. 실행 체계 통합 점검
다음을 확인한다.

1. `run.py` 단독 실행 영향 없음
2. `run_bootstrap.py` 영향 없음
3. `run_react.bat` 실행 시 API + Frontend 기동 흐름 정상
4. `.env` 로드 위치 및 누락 변수 확인
5. 포트 충돌, DB 락, 경로 충돌 확인
6. Tkinter 앱과 API/Frontend 병행 실행 시 치명 충돌 여부 확인

### Step 6. 실패 시 자동 수정
실패가 발생하면 아래 원칙으로 자동 수정 후 재검증한다.

- import mismatch 수정
- schema 필드명 mismatch 수정
- engine method argument mismatch 수정
- transaction 범위 수정
- rollback 누락 수정
- logger 호출 누락 수정
- parser 출력 포맷 보정
- route ↔ service ↔ engine 매핑 오류 수정

수정 후 반드시 같은 테스트를 다시 수행하고 결과를 비교한다.

### Step 7. 보고서 작성
최종 산출물 파일:
- `docs/P0_WRITE_API_VALIDATION_REPORT.md`

보고서에는 반드시 아래를 포함한다.

1. 조사한 실제 route / service / engine 연결표
2. 테스트한 API 목록
3. 성공 케이스 결과
4. 실패 케이스 결과
5. rollback 검증 결과
6. hard-stop 검증 결과
7. 로그 기록 검증 결과
8. 수정한 파일 목록
9. 남은 리스크
10. 다음 단계 권장안

---

## 5. location/update 7개 hard-stop 검증 규칙

실제 코드 기준으로 7개 hard-stop이 이미 구현되어 있다면, 그 구현을 그대로 검증한다.
코드에서 실제 규칙 수와 내용이 다르면 코드 기준을 우선하고 보고서에 명시한다.

최소 검증 케이스는 아래를 포함한다.

1. 존재하지 않는 tonbag_no
2. 비어 있는 target location
3. 이동 불가 상태의 tonbag
4. 현재 위치와 동일한 위치로 이동 요청
5. 필수 식별자 누락
6. `reason_code` / `operator` / `note` 전달 이상
7. 엔진 내부 검증 실패를 유발하는 불일치 데이터

각 케이스마다 아래를 남긴다.
- 요청 payload
- 기대 결과
- 실제 결과
- DB 변경 여부
- rollback 여부
- 로그 기록 여부

---

## 6. Telegram Bridge 운영 규칙

이번 작업은 Telegram Bridge 환경에서도 중단 없이 진행되어야 한다.

### Telegram에서 허용되는 응답 형식
```text
y
n
yes
no
1
2
3
그냥 작업을 진행해 줘
다음 단계 진행
테스트 실패 원인 먼저 수정해 줘
로그까지 정리하고 계속해 줘
```

### Telegram 메시지에 반드시 포함할 내용
1. Claude 최근 출력 300~500자
2. 현재 질문 / 선택 / 다음 단계 문맥
3. 가능한 응답 방법 안내

### Telegram 알림을 보내야 하는 상황
1. 치명적 DB 손상 위험 감지
2. 테스트 데이터 부족으로 실제 검증 불가
3. 운영 DB 직접 변경 가능성이 높은 경우
4. bridge 또는 실행 스크립트가 실패한 경우
5. 모든 P0 검증이 완료된 경우

### Telegram 알림을 보내지 않고 계속 진행해야 하는 상황
- import 오류
- schema mismatch
- route 등록 누락
- logger 누락
- parser 포맷 mismatch
- 테스트 코드 실패 후 자동 수정 가능한 일반 오류

### Telegram 메시지 예시 템플릿
```text
[P0 검증 진행 중]
- 현재 단계: outbound/execute rollback 검증
- 최근 결과: 정상 케이스 통과, 실패 케이스에서 rollback 누락 발견
- 조치 예정: transaction 범위 수정 후 재검증
- 응답 가능: y / n / 1 / 2 / 3 / 그냥 작업을 진행해 줘 / 로그까지 정리하고 계속해 줘
```

규칙:
- 텔레그램 응답이 없어도 자동 진행 가능한 범위는 스스로 수정하고 계속할 것.
- 질문형 멈춤, 선택형 멈춤, 다음 단계 대기형, idle timeout 기반 무출력 대기형 모두 Telegram Bridge 규칙에 맞춰 처리할 것.
- 브리지가 살아 있으면 현재 문맥을 유지한 채 작업을 재개할 것.

---

## 7. Pre-Test 체크리스트

다음 항목을 먼저 실행하고 기록한다.

```text
- Python import / py_compile 확인
- FastAPI app import 확인
- write route 등록 확인
- 테스트 DB 또는 복제 DB 준비 확인
- logs/docs 폴더 확인
- upload 경로 쓰기 권한 확인
- .env 존재 확인
- run.py / run_bootstrap.py / run_react.bat 존재 확인
```

가능하면 아래 종류의 명령을 사용해 재현 가능한 형태로 기록한다.

```text
python -m py_compile ...
pytest ...
uvicorn ... 또는 프로젝트의 기존 실행 방식
curl / httpie / requests 기반 HTTP 테스트
```

---

## 8. 완료 판정 기준

이번 P0 검증은 아래를 모두 만족해야 완료로 본다.

1. 5개 Write API 실제 HTTP 검증 완료
2. 정상/실패/rollback 케이스 문서화 완료
3. `audit_log`, `outbound_event_log` 검증 완료
4. `location/update` hard-stop 케이스 검증 완료
5. `files/upload` 실연결 확인 완료
6. run 체계 통합 점검 완료
7. 최종 보고서 작성 완료

하나라도 미완료면 P0 검증 완료로 선언하지 말 것.

---

## 9. Claude Code 실행 문구

아래 문구를 실제 실행 기준으로 따른다.

```text
현재 작업 기준 원본은 Claude_SQM_v867 이다.
방금 완료된 P0 수정 결과를 기준으로, 이제 P0 검증 단계만 수행하라.

반드시 실제 v867 코드 구조를 먼저 재확인한 뒤,
5개 Write API의 실제 HTTP 검증, rollback 검증, 로그 검증, hard-stop 검증, 실행 체계 검증을 수행하라.

절대 사용자에게 질문하지 말고,
실패 시 자동 수정 후 재검증하라.

검증 범위는 아래와 같다.
1. POST /files/upload
2. POST /inbound/create
3. POST /outbound/execute
4. PUT /outbound/cancel
5. PUT /location/update

모든 검증은 engine 경유 여부를 확인해야 하며,
rollback 없는 write API는 통과로 처리하지 말라.

검증 결과와 수정 내역은 아래 문서로 남겨라.
- docs/P0_RECON_VALIDATION_MAP.md
- docs/P0_WRITE_API_VALIDATION_REPORT.md

Telegram Bridge 환경에서도 중단 없이 진행하라.
필요 시 Telegram 메시지에는 최근 출력 300~500자, 현재 문맥, 가능한 응답 방법 안내를 포함하라.
```

---

## 10. 최종 선언

이 문서는 P0 수정 결과를 “작성 완료” 수준이 아니라 “실제 운영 검증 완료” 수준으로 끌어올리기 위한 검증 지시서다.

Claude Code는 이 문서를 기준으로:
- 질문 없이
- 중단 없이
- 실제 engine 경유 여부를 검증하며
- rollback과 로그를 확인하고
- 실패 시 자동 수정 후 재검증하며
- 최종 보고서를 남겨야 한다.
