# GPT_SQM_P0-4_위치업데이트_통합실행_초상세_작업지시서.md
생성일: 2026-04-04 15:52 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
참조 문서:
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P0_통합체크리스트_v2.md`
- `GPT_SQM_P0-1_실행파일연동점검표.md`
- `GPT_SQM_P0-3_입고출고_WriteLoop_초상세_작업지시서.md`
- `GPT_SQM_P0-3_입고출고_WriteLoop_테스트체크리스트.md`

---

## [질문]
다음 단계로 **P0-4 위치업데이트+통합실행 초상세 작업지시서**를 작성해 달라는 요청

## [질문의도]
P0-1~P0-3에서 정리한 구조/조회/write loop를 바탕으로,  
마지막 P0 단계인 **위치 업데이트 + 실행 통합 + 회귀 테스트 + 최종 진입 게이트**를 실제로 수행할 수 있도록
작업 범위, 수정 파일, 실행 순서, 충돌 점검, 완료 기준을 초상세 수준으로 정리한다.

---

# [응답]

# 1. P0-4의 목표

P0-4는 P0의 마지막 정리 단계다.  
이번 단계의 본질은 아래와 같다.

```text
1. PUT /location/update 를 실제 engine 로직과 연결한다
2. React/FastAPI/Tkinter 실행 구조를 운영 가능한 수준으로 정리한다
3. run.py / run_bootstrap.py / run_react_api.py / run_react.bat / .env 흐름을 정리한다
4. P0-1~P0-3 기능에 대한 회귀 테스트를 수행한다
5. P1 이상 단계로 넘어갈 수 있는 최종 P0 완료 게이트를 통과한다
```

---

# 2. P0-4 완료 정의

아래 조건이 모두 만족되면 P0-4 완료로 본다.

- [ ] `PUT /location/update` 가 실제 위치 변경 로직과 연결된다
- [ ] 위치 변경 성공/실패/rollback 이 검증된다
- [ ] `run.py`, `run_bootstrap.py`, `run_react_api.py`, `run_react.bat` 역할이 정리된다
- [ ] `.env` 로드 위치와 키 사용 주체가 정리된다
- [ ] API + Frontend 기본 통합 실행이 가능하다
- [ ] P0-2 LOT 상세 모달 회귀 테스트가 통과한다
- [ ] P0-3 write loop 회귀 테스트가 통과한다
- [ ] P0 전체 완료보고서를 작성할 수 있는 상태가 된다

---

# 3. 이번 단계의 직접 근거

마스터 문서는 쓰기 API 추가 대상으로 아래를 명시한다.

- `PUT /location/update`

또한 아래를 요구한다.

- 기존 `engine_modules` 핵심 로직 재사용
- 모든 write API는 트랜잭션 보호
- 실패 시 rollback
- BAT / PowerShell / MASTER 통합 구조 정리
- `.env` 분리
- 사전 테스트 후 실행, 실패 시 중단  
fileciteturn10file0 fileciteturn10file1

따라서 P0-4는 단순 위치 변경 API 추가가 아니라  
**운영 실행 체계 정리 + 회귀 검증 단계**로 봐야 한다.

---

# 4. P0-4 범위

## 포함
- `PUT /location/update`
- 위치 변경 UI/모달/액션 연결
- `run.py` / `run_bootstrap.py` / `run_react_api.py` / `run_react.bat` 역할 정리
- `.env` 로드 구조 정리
- API + Frontend 기본 통합 실행
- P0-2/P0-3 회귀 테스트
- 포트 / DB lock / 경로 / env 충돌 점검

## 제외
- Telegram bridge 통합 최종 자동화
- Security 고도화
- P1 이상의 UI 정교화
- P1 이상의 성능 최적화
- 최종 제품화 문서 패키지 전체 작성

---

# 5. 수정 대상 파일

## 5-1. Frontend 직접 수정 파일
| 파일 | 역할 | P0-4 작업 |
|---|---|---|
| `web/src/api/actionApi.js` | 위치 변경 API 래퍼 | `updateLocation()` 구현 |
| 위치 변경 관련 page / modal 파일 | UI 진입점 | 위치 변경 요청 흐름 구현 |
| `web/src/App.jsx` | mount/state 보조 | 필요 시 연결 |
| 관련 공통 컴포넌트 | 결과 표시 / refresh | 필요 시 최소 보강 |

## 5-2. Backend 직접 수정 파일
| 파일 | 역할 | P0-4 작업 |
|---|---|---|
| `react_api/routes/actions.py` | write API route | `PUT /location/update` 구현 |
| `react_api/schemas/actions.py` | request/response schema | location update schema 확정 |
| `react_api/services/action_service.py` | service layer | location update orchestration |
| `react_api/services/engine_adapter.py` | engine bridge | 실제 위치 변경 wrapper 구현 |
| `react_api/main.py` | 라우터 등록 점검 | 이미 되었다면 점검만 |

## 5-3. 실행/환경 직접 수정 후보
| 파일 | 역할 | P0-4 작업 |
|---|---|---|
| `run_react.bat` | API+Frontend 실행 배치 | 실행 순서/창 유지/로그 보강 |
| `run_react_api.py` | API 진입점 | env/host/port 정리 |
| `run.py` | Tkinter 진입점 | 역할 재확인, 충돌 메모 또는 최소 보강 |
| `run_bootstrap.py` | bootstrap | 초기화 역할 점검 및 최소 보강 |
| `.env` / `.env.example` | 환경변수 | 키 구조 정리 |

## 5-4. 참조/재사용 파일
| 파일 | 목적 |
|---|---|
| `engine_modules/inventory_modular/tonbag_mixin.py` | 위치 변경 로직 확인 |
| `engine_modules/inventory_modular/query_mixin.py` | 변경 후 조회/검증 보조 |
| `data/db/sqm_inventory.db` | rollback/logging/상태 검증 |

---

# 6. 위치 변경 흐름 설계

## 6-1. 목표 흐름
```text
사용자 대상 선택
→ 새 위치 입력
→ PUT /location/update
→ engine_adapter.update_tonbag_location(...) 또는 동등 로직 호출
→ transaction / commit 또는 rollback
→ 결과 표시
→ 관련 화면 재조회
```

## 6-2. 최소 입력
- [ ] 대상 tonbag 식별값 또는 LOT+tonbag 조합
- [ ] 새 위치
- [ ] 필요 시 창고/zone/section
- [ ] reason(선택)
- [ ] 사용자 메타(선택)

## 6-3. 최소 응답 구조
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

---

# 7. location/update 설계 기준

## 7-1. route 책임
- [ ] schema 검증
- [ ] service 호출
- [ ] 공통 응답 반환

## 7-2. service 책임
- [ ] transaction begin/commit/rollback
- [ ] adapter 호출
- [ ] audit_log 기록
- [ ] 필요 시 outbound_event_log와의 충돌 방지
- [ ] 성공/실패 응답 메시지 정리

## 7-3. adapter 책임
- [ ] engine 인스턴스 확보
- [ ] 실제 위치 변경 함수 wrapper
- [ ] 인자 매핑
- [ ] 예외 상위 전달

## 7-4. 절대 금지
- [ ] service에서 위치 변경 핵심 업무 규칙 재구현 금지
- [ ] route에서 DB 직접 변경 금지
- [ ] engine 원본 로직 직접 훼손 금지

---

# 8. 실행 파일 통합 설계

# 8-1. `run.py`
이번 단계에서 해야 할 일:
- [ ] Tkinter 실제 진입점인지 재확인
- [ ] bootstrap 호출 구조 확인
- [ ] API/Frontend와 직접 충돌하는 부분 있는지 메모
- [ ] 필요 시 최소 범위 수정만 수행

# 8-2. `run_bootstrap.py`
이번 단계에서 해야 할 일:
- [ ] DB/폴더/초기화 준비 구조 재확인
- [ ] run.py와 역할 중복 여부 확인
- [ ] .env 또는 config 로드 관여 여부 확인

# 8-3. `run_react_api.py`
이번 단계에서 해야 할 일:
- [ ] FastAPI 진입점/uvicorn 구조 확인
- [ ] host/port/env 로드 방식 정리
- [ ] 필요 시 기본값 정리
- [ ] 실행 실패 시 로그 메시지 개선

# 8-4. `run_react.bat`
이번 단계에서 해야 할 일:
- [ ] API 먼저, Frontend 나중 실행 구조 정리
- [ ] 병렬 실행 방식 정리
- [ ] 창 유지/pause/log 방향 정리
- [ ] 작업 디렉토리/상대경로 안정화
- [ ] 실패 시 바로 창이 닫히지 않게 보강 검토

# 8-5. `.env`
이번 단계에서 해야 할 일:
- [ ] 공통 키 정리
- [ ] API용 키 정리
- [ ] Frontend용 키 정리
- [ ] 외부 연동용 키 정리
- [ ] 실제 로드 위치 문서화

---

# 9. 충돌 점검 기준

## 9-1. 포트 충돌
- [ ] API 포트 고정/환경변수화 여부
- [ ] Frontend 포트 고정/환경변수화 여부
- [ ] 기존 서비스와 충돌 여부

## 9-2. DB lock 충돌
- [ ] Tkinter와 API가 같은 SQLite 파일을 동시에 write 하는지 확인
- [ ] WAL/timeout 정책 확인
- [ ] 장시간 트랜잭션 위험 확인

## 9-3. 경로 충돌
- [ ] upload/temp/log 경로 겹침 여부
- [ ] batch 실행 경로 기준 일관성 확인
- [ ] frontend build/output 경로 충돌 여부

## 9-4. env 해석 충돌
- [ ] API/Tkinter가 같은 키를 서로 다르게 해석하는지
- [ ] dev/prod 키 혼재 여부
- [ ] 기본값 부재로 실행이 깨지는지

---

# 10. 회귀 테스트 범위

## 10-1. P0-2 회귀
- [ ] LOT 상세 모달 오픈
- [ ] LOT 조회 API 호출
- [ ] 기본정보 표시
- [ ] 톤백 목록 표시
- [ ] 이력 표시
- [ ] 배정 상태 표시
- [ ] loading/error/재조회 동작

## 10-2. P0-3 회귀
- [ ] PDF upload preview
- [ ] Excel upload preview
- [ ] inbound/create 성공
- [ ] inbound/create rollback
- [ ] outbound/execute 성공
- [ ] outbound/execute rollback
- [ ] outbound/cancel 성공
- [ ] outbound/cancel rollback
- [ ] audit_log / outbound_event_log 기록

## 10-3. P0-4 신규 테스트
- [ ] location/update 성공
- [ ] location/update 실패 rollback
- [ ] audit_log 기록
- [ ] 화면 재조회/반영 확인

---

# 11. 테스트 지시서

# 11-1. Pre-Test
- [ ] location update 대상 샘플 확보
- [ ] 새 위치 값 샘플 확보
- [ ] 정상/잘못된 위치 값 준비
- [ ] API / Frontend 실행 가능
- [ ] DB 접근 가능
- [ ] 로그 테이블 조회 가능
- [ ] .env 키 확인 완료

# 11-2. 위치 변경 성공 테스트
- [ ] 대상 선택 가능
- [ ] 새 위치 입력 가능
- [ ] `PUT /location/update` 호출 발생
- [ ] 실제 engine 위치 변경 함수 호출
- [ ] DB 반영 성공
- [ ] 결과 메시지 표시
- [ ] 화면 재조회 시 새 위치 반영 확인
- [ ] audit_log 기록 확인

# 11-3. 위치 변경 실패 / rollback 테스트
- [ ] 잘못된 대상
- [ ] 잘못된 위치
- [ ] engine validation 실패
- [ ] rollback 발생
- [ ] 중간 상태 미잔존 확인
- [ ] audit_log 실패 기록 확인
- [ ] 사용자 응답이 실패로 표시되는지 확인

# 11-4. 실행 통합 테스트
- [ ] run_react_api.py로 API 기동
- [ ] run_react.bat로 API+Frontend 기동
- [ ] Frontend 접속 성공
- [ ] health 확인
- [ ] 기본 read/write 기능 샘플 테스트
- [ ] 오류 시 로그 식별 가능

# 11-5. 충돌 테스트
- [ ] 포트 충돌 없음
- [ ] DB lock 치명 충돌 없음
- [ ] temp/log 경로 충돌 없음
- [ ] env 해석 충돌 없음

---

# 12. 완료 기준

## 완료로 인정
- [ ] location/update 실연결 완료
- [ ] 성공/실패/rollback 검증 완료
- [ ] audit_log 기록 확인
- [ ] API + Frontend 기본 통합 실행 가능
- [ ] P0-2/P0-3 회귀 테스트 통과
- [ ] 실행 파일/환경변수 구조 정리 완료

## 완료로 인정하지 않음
- [ ] location/update 버튼만 있고 실제 반영이 없음
- [ ] rollback 검증이 없음
- [ ] 실행 스크립트가 있어도 재현 불가
- [ ] P0-2/P0-3 기능이 회귀로 깨짐
- [ ] 포트/DB/env 충돌이 미정리 상태

---

# 13. 실패 유형별 조치

## 유형 A. 위치 변경 함수 인자 mismatch
- [ ] adapter 인자 매핑 수정
- [ ] engine 직접 수정 대신 wrapper 보강

## 유형 B. rollback 불안정
- [ ] transaction 범위 재조정
- [ ] audit 기록 시점 재조정
- [ ] partial side effect 추적

## 유형 C. run_react.bat 불안정
- [ ] 작업 디렉토리 고정
- [ ] start/pause/log 리다이렉션 보강
- [ ] API/Frontend 시작 순서 정리

## 유형 D. env 불명확
- [ ] 키 분류 재정리
- [ ] 기본값 문서화
- [ ] 로드 위치 명확화

## 유형 E. P0-2/P0-3 회귀
- [ ] 회귀 항목별 우선 복구
- [ ] location/update 변경 범위 최소화

---

# 14. 산출물 목록

- [ ] `PUT /location/update` 구현본
- [ ] `updateLocation()` 프론트 API 함수
- [ ] 위치 변경 UI/모달/액션 연결 코드
- [ ] 실행 파일/환경변수 점검 결과 메모
- [ ] P0 회귀 테스트 결과 메모
- [ ] P0 최종 완료보고서 초안(후속)

---

# 15. P0 최종 완료 게이트

아래를 모두 만족하면 P0 전체 완료로 본다.

- [ ] P0-2 read 동작 안정
- [ ] P0-3 write loop 안정
- [ ] P0-4 location/update 안정
- [ ] rollback / logging 검증 완료
- [ ] API + Frontend 기본 통합 실행 가능
- [ ] 실행 파일/환경변수 구조 정리 완료
- [ ] 남은 이슈가 P1 이상 범위로 정리됨

---

# 16. 루비 최종 권장안

이번 단계의 핵심은 아래 한 줄이다.

```text
P0-4는 새 기능을 크게 더하는 단계가 아니라,
지금까지 만든 read/write 흐름을 운영 가능한 형태로 묶고 검증하는 단계다.
```

따라서 권장 순서는 아래다.

```text
1. location/update
2. 실행 파일/.env 구조 정리
3. P0-2/P0-3 회귀
4. 통합 실행 검증
5. P0 최종 완료보고서
```

---

# 17. 다음 단계 권장

이번 문서 다음으로 가장 효율적인 작업은 아래 2개 중 하나다.

1. `P0-4 테스트체크리스트`
2. `Claude Code용 P0-4 실행 프롬프트`

루비 권장 순서는 아래다.

```text
1) P0-4 테스트체크리스트
2) Claude Code용 P0-4 실행 프롬프트
```
