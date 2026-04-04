# GPT_SQM_P2_to_Patch5_MASTER.md
생성일: 2026-04-04 17:02 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
기준 문서:
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P0_통합체크리스트_v2.md`
- `GPT_SQM_P0_최종_완료보고서_초안.md`
- `GPT_SQM_P0_통합인덱스_마스터팩.md`

---

## [질문]
지금 외부에 있어서 실행을 할 수 없으니, 그동안에  
**P2부터 Patch 5까지를 P0 때처럼 자세하게 모두 정리한 MASTER MD 파일**을 만들 수 있는지 요청

## [질문의도]
실제 실행은 나중에 하더라도,  
그 전에 **P2 ~ P5와 Patch 2 ~ Patch 5를 포괄하는 상위 통합 기준 문서**를 먼저 만들어 두어  
다음 실행 세션에서 바로 Claude Code / Cursor / 수동 작업에 투입할 수 있는 상태를 만든다.

---

# [응답]

# 1. 이 문서의 역할

이 문서는 **P2 ~ P5 + Patch 2 ~ Patch 5**의 상위 통합 MASTER 문서다.

즉, 아래 역할을 수행한다.

```text
1. P0 이후의 후속 단계 전체 로드맵을 한 문서에서 본다
2. P2, P3, P4, P5 각 단계의 목적과 범위를 고정한다
3. Patch 2, 3, 4, 5를 어떤 위치에서 어떻게 수행할지 고정한다
4. 실행 순서 / 테스트 게이트 / 실패 시 조치 / 완료 기준을 통합한다
5. 다음 세션에서 바로 실행 가능한 기준 문서로 사용한다
```

---

# 2. 전제 조건

이 MASTER는 아래를 전제로 한다.

## 2-1. 선행 조건
```text
P0-1 완료
P0-2 완료
P0-3 완료
P0-4 완료
즉, P0 전체가 PASS 또는 최소 CONDITIONAL PASS 상태
```

## 2-2. 기본 철학
```text
P0 = 기반 복구
P2~P5 = 고도화 / 안정화 / 운영화 / 제품화
Patch 2~5 = parser / DB / 실행체계 / 통합검증의 실전 반복 루프
```

## 2-3. 절대 원칙
- 실제 코드 구조를 먼저 조사한다
- 기존 `engine_modules` 로직을 우선 재사용한다
- 테스트 게이트 없이 다음 단계로 넘어가지 않는다
- 실패 시 즉시 중단하고 수정 후 재시도한다
- 문서, 실행, 테스트, 로그를 분리 관리한다

---

# 3. 전체 범위 요약

## 3-1. 단계 구분
```text
P2 = UI/UX 확장 + 화면 고도화 + 사용성 개선
P3 = 운영 자동화 + 알림 + 로그 분석 + 반복 실행 체계
P4 = 통합 안정화 + 보안/권한/배포 준비 + 운영 표준화
P5 = 제품화 직전 정리 + 최종 검수 + 운영 전환 기준
```

## 3-2. Patch 구분
```text
Patch 2 = parser 연동 고도화
Patch 3 = DB 스키마 / migration / 로그 구조 정리
Patch 4 = 실행 파일 / BAT / PS1 / .env / 운영 루프 정리
Patch 5 = 통합 테스트 / 회귀 테스트 / 최종 안정화
```

## 3-3. 관계
```text
P2~P5는 '개발 단계'
Patch 2~5는 '검증/보강/운영 적용 루프'
둘은 중복이 아니라 서로 다른 축
```

---

# 4. 전체 흐름도

```text
[P0 완료]
   ↓
[P2 UI/UX 고도화]
   └─ Patch 2 (parser 연동 고도화)
   ↓
[P3 운영 자동화]
   └─ Patch 3 (DB / migration / log 구조 정리)
   ↓
[P4 통합 안정화]
   └─ Patch 4 (run/bat/ps1/env 구조 정리)
   ↓
[P5 제품화 직전 검수]
   └─ Patch 5 (통합/회귀/최종 안정화)
   ↓
[최종 운영 전환]
```

---

# 5. 단계별 목적

# 5-1. P2 목표

P2는 **사용자가 실제로 쓰는 화면/UX 수준을 끌어올리는 단계**다.

## P2 핵심 목표
```text
1. Tkinter 대비 React 화면 동등성 확대
2. 누락 화면(Return/Move/Scan/Log 등) 복구
3. 상단 메뉴/드롭다운/모달 UX 완성
4. 조회/실행 흐름의 사용성 고도화
5. parser preview / write 결과 / 상태 반영 UI 개선
```

## P2에서 다룰 대표 항목
- 상단 메뉴 드롭다운 고도화
- Return 화면
- Move 화면
- Scan 화면
- Log/History 화면
- 입력 검증 UX
- 결과 메시지/상태 표시 개선
- 테이블/필터/재조회 사용성 개선

---

# 5-2. P3 목표

P3는 **운영 자동화와 반복 가능한 실행 체계**를 강화하는 단계다.

## P3 핵심 목표
```text
1. Claude 실행 + 테스트 + 로그 + 결과 기록 루프 자동화
2. 테스트 결과 판정 파일화
3. 로그 자동 분석/정리
4. 반복 실행 구조 반자동/준자동화
5. 운영자 개입 지점을 최소화
```

## P3에서 다룰 대표 항목
- run_all_p0.ps1 확장
- stage별 결과 파일화
- PASS/FAIL 자동 판독
- 로그 요약 리포트
- 단계별 자동 중단/재시도 전략
- 테스트 결과 표준화

---

# 5-3. P4 목표

P4는 **통합 안정화 + 운영 환경 정리 + 보안/권한/배포 직전 준비** 단계다.

## P4 핵심 목표
```text
1. 환경변수/.env 체계 정리
2. 권한/역할/민감정보 분리
3. API/Frontend/Tkinter 공존 안정화
4. SQLite 운영 리스크 완화
5. 배포 직전 운영 표준 정리
```

## P4에서 다룰 대표 항목
- `.env`, `.env.example`, config 구조 정리
- 관리자/운영자 권한 구분 초안
- DB backup 정책
- WAL/timeout 정책 검토
- 운영 로그 보존 기준
- 에러 핸들링 통일
- 기본 health/diagnostics 체계

---

# 5-4. P5 목표

P5는 **제품화 직전 최종 검수와 운영 전환 기준 수립 단계**다.

## P5 핵심 목표
```text
1. 기능/문서/실행/테스트 결과를 최종 정리
2. 운영 인수인계 가능한 기준 확보
3. 배포 가능 패키지 구조 확정
4. 잔여 이슈를 P1+ 또는 Backlog로 분리
5. 운영 전환 GO/NO-GO 기준 수립
```

## P5에서 다룰 대표 항목
- 최종 완료보고서 작성
- 운영자 퀵가이드 확정
- 패키지 ZIP 확정
- 배포/복구 기준 문서
- 알려진 이슈 목록화
- 다음 버전(P1+) backlog 작성

---

# 6. Patch 2~5 상세 목적

# 6-1. Patch 2 목적

Patch 2는 **parser 연동 고도화**다.

## 핵심
```text
PDF parser
Excel parser
preview JSON 표준화
InboundParseModal 자동 채움 안정화
parser 오류 메시지/경고 고도화
```

## 핵심 점검
- preview 데이터 품질
- parser warnings 구조
- payload builder 표준화
- 손상 파일/빈 파일/지원 불가 형식 처리

---

# 6-2. Patch 3 목적

Patch 3는 **DB 스키마 / migration / 로그 구조 정리**다.

## 핵심
```text
audit_log 컬럼 정리
outbound_event_log 정리
migration 초안 / 적용 기준
insert 실패 방지
timestamp/default/nullability 정리
```

## 핵심 점검
- write API 로그 구조
- event_type / action_type 통일
- created_at 정책
- rollback 후 로그 일관성

---

# 6-3. Patch 4 목적

Patch 4는 **실행 파일 / BAT / PS1 / .env / 운영 루프 정리**다.

## 핵심
```text
run.py
run_bootstrap.py
run_react_api.py
run_react.bat
run_all_p0.ps1
run_stage.ps1
.env 구조
```

## 핵심 점검
- 실행 순서
- 상대경로
- 로그 파일
- 실패 시 중단
- 포트/경로/env 충돌

---

# 6-4. Patch 5 목적

Patch 5는 **통합 테스트 / 회귀 테스트 / 최종 안정화**다.

## 핵심
```text
P0-2 read 회귀
P0-3 write 회귀
P0-4 integration 회귀
parser / DB / run / env / UI 전체 재검증
최종 PASS / CONDITIONAL PASS / FAIL 판정
```

## 핵심 점검
- 회귀 여부
- side effect
- 안정성
- 운영 전환 가능성

---

# 7. P2~P5 + Patch 2~5 대응표

| 단계 | 주제 | 연결 Patch | 핵심 출력물 |
|---|---|---|---|
| P2 | UI/UX 고도화 | Patch 2 | 화면/모달/메뉴/preview UX 개선 |
| P3 | 운영 자동화 | Patch 3 | 테스트 판정/로그/자동화 루프 |
| P4 | 통합 안정화 | Patch 4 | run/env/권한/운영 정리 |
| P5 | 제품화 직전 정리 | Patch 5 | 최종 검수/최종 판정/배포기준 |

---

# 8. 단계별 수정 대상 예시

## P2 대표 수정 대상
```text
web/src/App.jsx
web/src/components/*
web/src/pages/*
web/src/api/*
react_api/routes/*
react_api/services/*
```

## P3 대표 수정 대상
```text
09_SCRIPTS/*
05_AUTORUN/*
07_LOGS/*
08_RESULTS/*
06_REPORTS/*
```

## P4 대표 수정 대상
```text
run.py
run_bootstrap.py
run_react_api.py
run_react.bat
.env
.env.example
config/settings files
```

## P5 대표 수정 대상
```text
00_MASTER/*
06_REPORTS/*
배포용 패키지 폴더
ZIP 구성물
운영자 가이드
```

---

# 9. 실행 원칙

## 9-1. 실행 순서
```text
P2 → 테스트 → Patch 2 반영/검증
P3 → 테스트 → Patch 3 반영/검증
P4 → 테스트 → Patch 4 반영/검증
P5 → 테스트 → Patch 5 반영/검증
```

## 9-2. 절대 금지
- P2~P5를 한 번에 몰아서 실행
- Patch 2~5를 테스트 없이 연쇄 적용
- 로그 없이 다음 단계 진행
- FAIL 상태에서 강행

## 9-3. 권장 방식
```text
반자동 게이트형 실행
```

즉,
- 자동 실행
- 사람 또는 결과 파일 기준 PASS 판정
- 통과 시 다음 단계

---

# 10. 테스트 게이트 공통 규칙

모든 단계는 아래를 반드시 따른다.

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

# 11. 단계별 완료 기준

## P2 완료 기준
- [ ] 주요 화면 동등성 복구
- [ ] 상단 메뉴/모달 UX 개선
- [ ] 누락 화면 최소 1차 복구
- [ ] parser preview/read 흐름 사용성 확보

## P3 완료 기준
- [ ] 자동 실행 루프 안정화
- [ ] 테스트 결과 파일화
- [ ] 로그 기록 체계 안정화
- [ ] 단계별 자동 중단 가능

## P4 완료 기준
- [ ] 실행 파일 역할 정리
- [ ] .env 구조 정리
- [ ] 운영 리스크 감소
- [ ] 통합 실행 안정화

## P5 완료 기준
- [ ] 최종 문서 정리
- [ ] 배포 패키지 준비
- [ ] 운영 인수 가능
- [ ] 최종 GO/NO-GO 판정 가능

---

# 12. 권장 산출물

## P2 산출물
- UI 고도화 설계서
- 화면별 테스트체크리스트
- Claude 실행 프롬프트
- UX 개선 메모

## P3 산출물
- 자동실행 v2 설계서
- 테스트 결과 표준 포맷
- 로그 분석 기준
- PASS/FAIL 자동 판독 기준

## P4 산출물
- env/권한/운영 설정 문서
- run 구조 정리 문서
- 통합 안정화 보고서

## P5 산출물
- 최종 운영 패키지
- 최종 완료보고서
- 운영자 퀵가이드 확정판
- 배포/복구 기준서

---

# 13. 실패 유형별 공통 조치

## 유형 A. parser/UI 불일치
- Patch 2에서 normalize 보강
- P2 UI에 dummy-safe 구조 유지

## 유형 B. DB/log 구조 문제
- Patch 3에서 migration 초안 작성
- write/logging 분리 검토

## 유형 C. 실행 스크립트 불안정
- Patch 4에서 run/env/log 구조 재정비
- 반자동 게이트 유지

## 유형 D. 통합 회귀
- Patch 5에서 단계별 회귀 표준화
- P0-2/P0-3/P0-4 핵심 축 재검증

---

# 14. 운영 관점 권장 순서

```text
1. 먼저 P0 실제 실행/안정화
2. P0 PASS 확인
3. 그 다음 P2 설계서/실행프롬프트 세트 작성
4. Patch 2 반영
5. P3 설계서/실행프롬프트 세트 작성
6. Patch 3 반영
7. P4 설계서/실행프롬프트 세트 작성
8. Patch 4 반영
9. P5 설계서/실행프롬프트 세트 작성
10. Patch 5 최종 반영
```

---

# 15. 이 MASTER를 어떻게 사용할 것인가

## 사람이 읽을 때
- P0 이후 전체 계획서로 사용
- 다음 세션에서 단계별 문서 생성 기준으로 사용

## Claude Code에 넣을 때
- 직접 실행 프롬프트로 쓰기보다
- P2/P3/P4/P5 하위 문서를 생성하는 상위 기준서로 사용

## Cursor/수동 작업 시
- 단계별 범위 구분 기준으로 사용
- Patch와 단계를 혼동하지 않게 하는 기준서로 사용

---

# 16. 루비 최종 판단

이번 MASTER의 핵심은 아래다.

```text
지금까지 만든 것은 P0 실행 체계다.
이 문서는 그 다음 단계인 P2~P5와 Patch 2~5를
실행 가능한 로드맵으로 묶어 두는 상위 기준서다.
```

즉,
- 지금은 실행 못 해도
- 다음 세션에서 바로 이어갈 수 있는
**후속 개발 MASTER** 역할을 한다.

---

# 17. 다음 단계 권장

이 MASTER를 만든 뒤 가장 자연스러운 다음 작업은 아래다.

```text
1. GPT_SQM_P2_초상세_작업지시서.md
2. GPT_SQM_P2_테스트체크리스트.md
3. GPT_ClaudeCode_P2_실행프롬프트.md
```

루비 권장 순서는 아래다.

```text
1) P2 초상세 작업지시서
2) P2 테스트체크리스트
3) Claude Code용 P2 실행프롬프트
```
