# GPT_SQM_MASTER_P2_to_Patch5_통합실행본.md
생성일: 2026-04-04 17:35 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
기준 문서:
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P2_to_Patch5_MASTER.md`
- `GPT_SQM_P2_Patch2_통합MASTER.md`
- `GPT_SQM_P3_Patch3_통합MASTER.md`
- `GPT_SQM_P0_통합체크리스트_v2.md`
- `GPT_SQM_P0_최종_완료보고서_초안.md`

---

## [질문]
지금 밖에 나갈 예정이라 실제 실행은 못 하니,  
**P0 이후 P2부터 시작해서 Patch 5까지 전부를 P0 때처럼 아주 자세하게 미리 정리한 Master.md 파일**을 만들어 달라는 요청

## [질문의도]
다음 실행 세션에서 바로 사용할 수 있도록,  
P2 / P3 / P4 / P5와 Patch 2 / 3 / 4 / 5를 **하나의 초상세 통합 MASTER 문서**로 묶어서  
Claude Code, Cursor, 수동 작업, BAT/PS1 자동화까지 모두 공통으로 참조할 수 있게 만든다.

---

# [응답]

# 0. 이 문서의 성격

이 문서는 **P0 이후 전체 후속 개발의 상위 MASTER**다.

즉, 아래를 한 번에 정의한다.

```text
1. P2 ~ P5 각 단계의 목표
2. Patch 2 ~ Patch 5 각 보강 루프의 목표
3. 단계와 Patch의 연결 관계
4. 실제 수정 범위
5. 테스트 게이트
6. 실패 시 조치
7. 자동화/운영/배포 기준
8. 최종 완료 기준
```

---

# 1. 선행 조건

## 1-1. 반드시 충족되어야 하는 전제
```text
P0-1 완료
P0-2 완료
P0-3 완료
P0-4 완료
즉, P0 전체가 PASS 또는 최소 CONDITIONAL PASS 상태
```

## 1-2. P0가 끝난 상태의 의미
```text
React + FastAPI 경로에서
- read(LOT 상세)
- write loop(upload / preview / inbound / execute / cancel)
- location/update
- 기본 실행 구조(run / bat / ps1 / env)
가 살아 있는 상태
```

## 1-3. 절대 원칙
- 기존 `engine_modules`를 우선 재사용한다
- 테스트 게이트 없이 다음 단계로 넘어가지 않는다
- 실패 시 즉시 중단하고 수정 후 재시도한다
- mock 상태에서 완료 처리하지 않는다
- UI / parser / DB / run 구조를 따로 놀게 하지 않는다
- 문서 / 실행 / 테스트 / 로그 / 결과를 분리 관리한다

---

# 2. 전체 단계 개요

## 2-1. 단계 정의
```text
P2 = UI/UX 고도화 단계
P3 = 운영 자동화 + 반복 실행 구조 고도화 단계
P4 = 통합 안정화 + 환경/실행 구조 정리 단계
P5 = 제품화 직전 최종 검수 + 운영 전환 기준 수립 단계
```

## 2-2. Patch 정의
```text
Patch 2 = parser 연동/preview 품질 고도화
Patch 3 = DB 스키마 / migration / log 구조 정리
Patch 4 = run / bat / ps1 / env / 운영 루프 정리
Patch 5 = 통합 테스트 / 회귀 테스트 / 최종 안정화
```

## 2-3. 단계와 Patch의 관계
```text
P2 ↔ Patch 2
P3 ↔ Patch 3
P4 ↔ Patch 4
P5 ↔ Patch 5
```

하지만 이것은 완전 1:1 봉인 구조가 아니다.

```text
P2는 UI/UX 관점
Patch 2는 parser/preview 관점
P3는 자동화 관점
Patch 3는 DB/로그 구조 관점
P4는 운영 안정화 관점
Patch 4는 실행 파일/env 관점
P5는 최종 제품화 관점
Patch 5는 최종 검증/회귀 관점
```

즉, 서로 다른 축이지만 실전에서는 강하게 묶여 움직인다.

---

# 3. 전체 흐름도

```text
[P0 PASS]
   ↓
[P2 UI/UX 고도화]
   + [Patch 2 parser / preview 고도화]
   ↓
[P3 운영 자동화]
   + [Patch 3 DB / migration / log 구조 정리]
   ↓
[P4 통합 안정화]
   + [Patch 4 run / bat / ps1 / env / 운영 루프 정리]
   ↓
[P5 제품화 직전 검수]
   + [Patch 5 통합/회귀/최종 안정화]
   ↓
[최종 운영 전환]
```

---

# 4. P2 상세 MASTER

# 4-1. P2 목표

P2는 **사용자가 실제로 쓰는 React 화면을 실무 usable 수준까지 끌어올리는 단계**다.

## 핵심 목표
```text
1. Tkinter 대비 React 화면 동등성 확대
2. Return / Move / Scan / Log 등 누락 화면 1차 복구
3. LOT 상세 / Inbound / Outbound 관련 UX 개선
4. 상단 메뉴 / 드롭다운 / 상태표시 정리
5. 필터 / 검색 / 로딩 / 에러 / 결과 메시지 일관화
```

## 핵심 사용자 가치
```text
"작동하는 시스템"을
"실제로 쓸 수 있는 시스템"으로 바꾸는 단계
```

# 4-2. P2 포함 범위
- `web/src/App.jsx`
- `web/src/pages/*`
- `web/src/components/*`
- `web/src/components/modals/*`
- `web/src/api/*`
- 필요 시 `react_api/routes/*` 응답 보강

# 4-3. P2 핵심 작업
## A. 화면 복구
- Return 화면 1차 복구
- Move 화면 1차 복구
- Scan 화면 1차 복구
- Log/History 화면 1차 복구

## B. LOT 상세 고도화
- 상태 표시 정교화
- TONBAG 리스트 가독성 개선
- 이력 / 배정상태 표시 가독성 개선

## C. 공통 UX 정리
- loading 표시
- error 메시지
- success/result 메시지
- 필터/검색/재조회 UX
- 테이블 빈 상태 처리

# 4-4. P2 완료 기준
- [ ] 주요 누락 화면 1차 복구
- [ ] LOT 상세/모달 UX 개선
- [ ] 공통 상태 메시지 통일
- [ ] P0 회귀 없음
- [ ] 사용자가 React UI만으로 흐름 이해 가능

# 4-5. P2 실패 시 조치
- 누락 화면은 1차 usable 기준 우선
- 세부 UX는 P2.1 / P2.2로 분리 가능
- 공통 컴포넌트 과도 리팩토링 금지
- engine 직접 수정 금지

---

# 5. Patch 2 상세 MASTER

# 5-1. Patch 2 목표

Patch 2는 **parser → preview → create_payload 품질 안정화**다.

## 핵심 목표
```text
1. PDF parser 품질 점검 및 보강
2. Excel parser 품질 점검 및 보강
3. preview JSON 구조 표준화
4. warnings 구조 표준화
5. create_payload builder 정리
6. InboundParseModal과 parser 결과의 일관성 확보
```

# 5-2. Patch 2 포함 범위
- `parsers/*`
- `react_api/services/action_service.py`
- `react_api/schemas/actions.py`
- `web/src/components/modals/InboundParseModal.jsx`
- `web/src/api/actionApi.js`

# 5-3. Patch 2 핵심 작업
## A. 입력별 preview 품질
- PDF 정상
- Excel 정상
- 손상 파일
- 빈 파일
- 지원 불가 형식

## B. preview 구조 표준화
권장 예시:

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

## C. warnings 표준화
권장 예시:

```json
[
  {
    "level": "warning",
    "field": "lot_no",
    "message": "LOT number inferred from parser"
  }
]
```

# 5-4. Patch 2 완료 기준
- [ ] PDF/Excel preview 안정
- [ ] warnings 구조 일관성
- [ ] create_payload create 직전 신뢰 가능
- [ ] 손상/빈/지원 불가 처리 명확
- [ ] UI에서 warning/error를 이해 가능

# 5-5. Patch 2 실패 시 조치
- parser 원본 로직 대수술보다 adapter/normalizer 우선
- preview JSON 표준화 우선
- create builder를 별도 레이어로 분리 가능
- warning severity/field 구조 추가

---

# 6. P2 + Patch 2 통합 기준

## 핵심 원칙
```text
UI가 좋아도 preview가 흔들리면 못 쓴다
parser가 좋아도 UI가 불친절하면 못 쓴다
따라서 P2와 Patch 2는 통합 실행이 맞다
```

## 통합 완료 기준
- [ ] InboundParseModal이 parser 결과를 신뢰 가능하게 표시
- [ ] summary / warnings / create_payload가 사용자 판단 도구 역할
- [ ] preview ↔ create 일관성 확보
- [ ] P0 회귀 없음

---

# 7. P3 상세 MASTER

# 7-1. P3 목표

P3는 **운영 자동화와 반복 가능한 실행 체계**를 강화하는 단계다.

## 핵심 목표
```text
1. 단계별 자동 실행 구조 강화
2. 테스트 결과 저장 구조 표준화
3. PASS/FAIL 판독 구조 정리
4. 로그 요약 구조 강화
5. 사람이 중간에 개입할 최소 포인트만 남기기
```

# 7-2. P3 포함 범위
- `09_SCRIPTS/run_all_p0.ps1`
- `09_SCRIPTS/run_stage.ps1`
- `09_SCRIPTS/check_env.ps1`
- `09_SCRIPTS/write_run_log.ps1`
- `07_LOGS/*`
- `08_RESULTS/*`
- `06_REPORTS/*`

# 7-3. P3 핵심 작업
- 반자동 → 준자동 수준으로 고도화
- 단계별 상태 파일 정리
- PASS/FAIL 판독 구조
- 로그 요약 자동화
- 실패 시 중단/재시도 구조 정리

# 7-4. P3 완료 기준
- [ ] 단계별 실행/중단 구조 안정
- [ ] results 구조 안정
- [ ] logs 구조 안정
- [ ] 운영자가 어디서 멈췄는지 즉시 알 수 있음

# 7-5. P3 실패 시 조치
- 완전자동보다 반자동 유지
- PASS 파일 판독 규격 먼저 정리
- 로그 요약은 최소형부터 시작

---

# 8. Patch 3 상세 MASTER

# 8-1. Patch 3 목표

Patch 3는 **audit_log / outbound_event_log / migration 구조 안정화**다.

## 핵심 목표
```text
1. audit_log 최소 필수 컬럼 정리
2. outbound_event_log 최소 필수 컬럼 정리
3. created_at/default/nullability 정리
4. migration 필요 여부 확정
5. logging insert 실패 위험 제거
```

# 8-2. Patch 3 포함 범위
- `react_api/services/action_service.py`
- `react_api/schemas/actions.py`
- `react_api/routes/actions.py`
- migration 초안 파일 (필요 시 신규)
- DB 구조 점검 문서

# 8-3. 최소 필수 컬럼 기준

## audit_log
- id
- action_type
- status
- message
- payload_json
- error_message
- source_module
- created_at

## outbound_event_log
- id
- outbound_id 또는 동등 식별값
- lot_no
- tonbag_no
- event_type
- status
- message
- payload_json
- created_at

# 8-4. Patch 3 완료 기준
- [ ] success/fail 로그 가능
- [ ] created_at 자동 기록 가능
- [ ] payload_json 저장 가능
- [ ] migration 필요 여부 확정
- [ ] 자동화와 연결되는 log 구조 확보

# 8-5. Patch 3 실패 시 조치
- 실DB 직접 변경보다 migration 초안 우선
- naming 불일치는 adapter/service layer에서 임시 흡수 가능
- logging 포맷 통일 우선

---

# 9. P3 + Patch 3 통합 기준

## 핵심 원칙
```text
자동화와 로그 구조는 같이 잡아야 한다
자동화만 있으면 추적이 안 되고,
로그만 좋으면 반복 운영이 안 된다
```

## 통합 완료 기준
- [ ] 단계별 상태 추적 가능
- [ ] success/fail 로그 일관성 확보
- [ ] migration 필요성 명확
- [ ] P0/P2 회귀 없음

---

# 10. P4 상세 MASTER

# 10-1. P4 목표

P4는 **통합 안정화 + 실행 구조 + 환경 구조 + 운영 리스크 정리 단계**다.

## 핵심 목표
```text
1. run.py / run_bootstrap.py / run_react_api.py / run_react.bat 역할 정리
2. .env / .env.example / 설정 구조 정리
3. 포트/경로/env 충돌 제거
4. SQLite 운영 리스크 완화
5. API + Frontend + Tkinter 공존 안정화
```

# 10-2. P4 포함 범위
- `run.py`
- `run_bootstrap.py`
- `run_react_api.py`
- `run_react.bat`
- `.env`
- `.env.example`
- config/settings 관련 파일

# 10-3. P4 핵심 작업
- 실행 진입점 역할 재정리
- env 키 분류
- 포트 정책 정리
- 로그 출력 방식 정리
- 작업 디렉토리/상대경로 정리
- SQLite lock 리스크 메모/정책 정리

# 10-4. P4 완료 기준
- [ ] run 구조 명확
- [ ] env 구조 명확
- [ ] API+Frontend 기본 통합 실행 가능
- [ ] 운영 시 충돌 포인트 식별/완화
- [ ] P0/P2/P3 회귀 없음

# 10-5. P4 실패 시 조치
- run 파일 대수술 금지
- 최소 수정 + 역할 명확화 우선
- env는 공통/API/Frontend/외부연동으로 나누기
- DB lock은 정책 메모부터

---

# 11. Patch 4 상세 MASTER

# 11-1. Patch 4 목표

Patch 4는 **run / bat / ps1 / env / 운영 루프를 실제 운영 가능한 수준으로 정리**하는 것이다.

## 핵심 목표
```text
1. run_all_p0.ps1 / run_stage.ps1 구조 정리
2. run_react.bat / run_react_api.py 구조 정리
3. env 로드 위치 명확화
4. logs / results / reports 연결 강화
5. 다른 PC에서도 재현 가능한 실행 구조 확보
```

# 11-2. Patch 4 포함 범위
- `09_SCRIPTS/*`
- `run_react.bat`
- `run_react_api.py`
- `.env` 구조 문서
- `07_LOGS/*`
- `08_RESULTS/*`

# 11-3. Patch 4 완료 기준
- [ ] 실행 루프 재현 가능
- [ ] 단계별 로그 저장
- [ ] 결과 저장 구조 안정
- [ ] env 해석 구조 명확
- [ ] 실패 시 중단 구조 명확

# 11-4. Patch 4 실패 시 조치
- BAT보다 PS1 중심 운영
- 완전자동보다 반자동/준자동 유지
- PATH/상대경로/권한 문제를 먼저 정리

---

# 12. P4 + Patch 4 통합 기준

## 핵심 원칙
```text
통합 안정화는
실행 파일, 환경변수, 로그, 결과 구조를 같이 정리할 때만 의미가 있다
```

## 통합 완료 기준
- [ ] 실행/환경 구조 이해 가능
- [ ] 자동화 루프와 run 구조 일치
- [ ] 다른 PC/다른 작업자에게 넘겨도 재현 가능
- [ ] 회귀 없음

---

# 13. P5 상세 MASTER

# 13-1. P5 목표

P5는 **제품화 직전 최종 검수 및 운영 전환 기준 수립 단계**다.

## 핵심 목표
```text
1. 문서 / 실행 / 테스트 / 결과를 최종 정리
2. 운영자 인수인계 가능한 패키지 완성
3. 알려진 이슈와 backlog 분리
4. GO / CONDITIONAL GO / NO-GO 판정 기준 수립
```

# 13-2. P5 포함 범위
- `00_MASTER/*`
- `06_REPORTS/*`
- 운영자 가이드
- 최종 패키지 구조
- ZIP 포장 기준
- 배포/복구 기준 문서

# 13-3. P5 핵심 작업
- 최종 완료보고서 확정
- 운영자 1페이지 가이드 확정
- 최종실행팩 구성 최종판
- 배포 순서 확정
- 백업/복구 기준 요약
- 잔여 이슈 Backlog 분리

# 13-4. P5 완료 기준
- [ ] 운영 인수 가능
- [ ] 최종 보고 가능
- [ ] 실행팩 재현 가능
- [ ] 잔여 이슈 분리 완료
- [ ] GO/NO-GO 판정 가능

# 13-5. P5 실패 시 조치
- 조건부 운영 허용 범위 정의
- 운영자/개발자 문서 분리
- 알려진 이슈를 숨기지 말고 문서화

---

# 14. Patch 5 상세 MASTER

# 14-1. Patch 5 목표

Patch 5는 **전체 통합 테스트 / 회귀 테스트 / 최종 안정화**다.

## 핵심 목표
```text
1. P0-2 read 회귀 검증
2. P0-3 write loop 회귀 검증
3. P0-4 integration 회귀 검증
4. P2 / Patch2 / P3 / Patch3 / P4 / Patch4 영향 검증
5. 최종 PASS / CONDITIONAL PASS / FAIL 판정
```

# 14-2. Patch 5 포함 범위
- 테스트체크리스트 전부
- 실행 로그 전부
- results / reports 전부
- 통합 회귀 메모

# 14-3. Patch 5 완료 기준
- [ ] 핵심 read 회귀 없음
- [ ] 핵심 write 회귀 없음
- [ ] location/update 회귀 없음
- [ ] parser preview 품질 유지
- [ ] 자동화/로그 구조 유지
- [ ] 최종 판정 가능

# 14-4. Patch 5 실패 시 조치
- 어떤 단계(P2/P3/P4)가 회귀를 만들었는지 역추적
- 한 번에 큰 수정 금지
- 회귀 항목을 최소 재현 단위로 분리

---

# 15. 공통 실행 원칙

## 15-1. 절대 금지
- P2~P5를 한 번에 전부 실행
- Patch 2~5를 테스트 없이 연쇄 적용
- FAIL 상태에서 다음 단계 진행
- mock으로 완료 처리
- 실DB 직접 수정 남발

## 15-2. 권장 실행 순서
```text
P2 실행 → 테스트 → Patch 2 반영/검증
P3 실행 → 테스트 → Patch 3 반영/검증
P4 실행 → 테스트 → Patch 4 반영/검증
P5 실행 → 테스트 → Patch 5 최종 반영/판정
```

## 15-3. 권장 운영 방식
```text
반자동 게이트형
또는
준자동 게이트형
```

---

# 16. 공통 테스트 게이트

모든 단계는 반드시 아래를 따른다.

```text
Pre-Test
→ 구현
→ Post-Test
→ 실패 시 수정
→ Re-Test
→ PASS
→ 다음 단계
```

---

# 17. 공통 산출물

각 단계마다 아래 3종은 기본으로 만든다.

```text
1. 초상세 작업지시서
2. 테스트체크리스트
3. Claude Code 실행프롬프트
```

권장 추가 산출물:

```text
- 결과 메모
- 회귀 메모
- 변경 요약
- known issues 목록
```

---

# 18. 단계별 요약표

| 단계 | 목표 | 연결 Patch | 핵심 산출물 |
|---|---|---|---|
| P2 | 화면/UX usable 수준 | Patch 2 | UI 설계서/테스트/프롬프트 |
| P3 | 반복 운영 자동화 | Patch 3 | 자동화 설계서/테스트/프롬프트 |
| P4 | 실행/환경 통합 안정화 | Patch 4 | 운영/실행 설계서/테스트/프롬프트 |
| P5 | 최종 검수/운영 전환 | Patch 5 | 완료보고서/판정/배포 기준 |

---

# 19. 다음 세션에서의 권장 실제 진행 순서

```text
1. 먼저 P0 실제 실행
2. P0 PASS 확인
3. P2 + Patch 2 실행
4. 테스트
5. P3 + Patch 3 실행
6. 테스트
7. P4 + Patch 4 실행
8. 테스트
9. P5 + Patch 5 실행
10. 최종 판정
```

---

# 20. 루비 최종 판단

이 MASTER의 핵심은 아래 한 줄이다.

```text
P0 이후 단계는 "문서를 더 만드는 일"이 아니라
"사용성 / 자동화 / 안정화 / 운영전환"을 차례대로 완성하는 일이다.
이 문서는 그 전체 여정을 한 번에 묶어 두는 상위 MASTER다.
```

---

# 21. 다음 단계 권장

다음으로 가장 자연스러운 작업은 아래다.

```text
1. GPT_SQM_P4_Patch4_통합MASTER.md
2. GPT_SQM_Patch4_초상세_작업지시서.md
3. GPT_SQM_Patch4_테스트체크리스트.md
4. GPT_ClaudeCode_P4_Patch4_통합실행프롬프트.md
```
