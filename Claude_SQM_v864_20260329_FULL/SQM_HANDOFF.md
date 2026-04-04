# SQM_HANDOFF.md

> 새 세션에서 SQM 프로젝트 작업을 끊기지 않고 이어가기 위한 인계문서 템플릿  
> 인코딩: UTF-8

---

## 1. 프로젝트 기본 정보

- 프로젝트명: SQM Inventory / Outbound Management
- 환경:
  - Python
  - tkinter + ttkbootstrap
  - SQLite
- 운영 성격:
  - 내부 업무용 데스크톱 도구
  - 광양 창고 운영
  - LOT / TONBAG / 입고 / 배정 / 피킹 / 출고 / 반품 관리
- 핵심 원칙:
  - tkinter 유지
  - SQLite 유지
  - DB schema 변경 금지
  - business policy 변경 금지
  - 점진적 리팩토링 우선
  - 운영 안정성 / 데이터 정합성 최우선

---

## 2. 현재 기준 커밋 / 브랜치

- 기준 커밋:
  - `c408df1`
- 브랜치:
  - `main`
- GitHub 저장소:
  - `https://github.com/kidongnam1/SQM_inventory.git`
- 상태:
  - backup before outbound_mixin refactor 커밋 완료
  - origin/main push 완료

---

## 3. 현재 작업 범위

### 현재 핵심 작업 파일
- `engine_modules/inventory_modular/outbound_mixin.py`

### 현재 집중 함수
1. `confirm_outbound()`
2. `reserve_from_allocation()`
3. `execute_reserved()`

### 현재 작업 목표
- giant function 분해
- helper extraction
- `SOLD` → `OUTBOUND` 표현 정리
- 핵심 write / 보조 write 구분
- public signature 유지
- business policy 유지

---

## 4. 현재 완료 / 진행중 / 미착수

### 완료
- `outbound_mixin.py` 위험 분석 완료
- 핵심 3함수 분해 설계 완료
- Claude Code 실행 프롬프트 작성 완료
- `outbound_mixin.py` 검증 스크립트 작성 완료
- `.bat` 실행 파일 작성 완료
- GitHub checkpoint(`c408df1`) 생성 및 push 완료

### 진행중
- Claude가 `outbound_mixin.py` 1차 리팩토링 진행 / 완료 후 검증 단계
- `confirm_outbound()` helper 분해
- `reserve_from_allocation()` 미분해 구간 추가 분해
- `execute_reserved()` helper 분해
- 상태 전이 혼선(`SOLD`/`OUTBOUND`) 파일 내부 범위 점검

### 미착수
- `onestop_inbound.py` 분해
- 40개+ mixin 구조 정리
- `SOLD` 전역 참조 분류/정리
- parser 예외 구조 정리
- UI refresh / after() 구조 최적화
- 릴리스 / manifest / 버전 관리 정리

---

## 5. 현재 핵심 판단

### 유지해야 하는 방향
- React 전환하지 않음
- PostgreSQL 전환하지 않음
- tkinter 유지
- SQLite 유지
- 구조 안정화 우선
- 서비스 계층 분리 우선
- 핵심 giant file 분해 우선

### 현재 P0
1. `outbound_mixin.py` 1차 리팩토링 검증
2. `SOLD` write-path 정리
3. `onestop_inbound.py` 분해 착수
4. partial commit / transaction risk 점검

### 현재 P1
5. 서비스 계층 분리
6. 40개+ mixin 인벤토리/축소
7. parser 예외 처리 표준화

### 현재 P2
8. UI refresh / after() 정리
9. 테스트 기반 확대
10. 릴리스 / manifest 정리

---

## 6. 핵심 정책 메모

### 상태 전이
- 현재 기준 상태 흐름:
  - `AVAILABLE -> RESERVED -> PICKED -> OUTBOUND`
- `SOLD`는 deprecated / legacy compatibility 표현
- 새로운 write-state 기준은 `OUTBOUND`
- `SOLD` 전수 제거가 아니라:
  1. 새 write-path 금지
  2. 기존 참조 분류
  3. 파일별 정리

### LOT / TONBAG
- LOT mode 의미 변경 금지
- TONBAG mode 의미 변경 금지
- `allocation_plan.tonbag_id = NULL` 경로 의미 유지
- sample 정책 해석 변경 금지

### 변경 금지
- DB schema 변경 금지
- business policy rewrite 금지
- public method signature 변경 금지
- cross-file interface 변경 금지

---

## 7. 현재 보유 산출물

### 문서
- `GPT_Claude_Code_Final_Execution_Prompt_v1.md`
- 필요 시 v1.1로 보정 예정

### 검증 스크립트
- `GPT_verify_outbound_refactor_v3.py`

### 실행 배치파일
- `GPT_run_verify_outbound_refactor_v3.bat`

### 코드 파일
- 수정된 `outbound_mixin.py`
- 백업본 `outbound_mixin.py.bak_20260402`

---

## 8. 새 세션에서 우선 확인할 것

1. Claude 리팩토링 결과 로그
2. `git diff -- engine_modules/inventory_modular/outbound_mixin.py`
3. 검증 스크립트 실행 결과
4. PASS / WARN / FAIL 항목
5. 현재 변경 파일 범위
6. `SOLD` 신규 write-path 존재 여부
7. public signature 유지 여부

---

## 9. 새 세션 첫 작업 순서

```text
1. 업로드된 파일 확인
2. outbound_mixin.py 리팩토링 결과 검증
3. PASS / WARN / FAIL 정리
4. 위험 수정 / 허용 수정 / 되돌릴 수정 분류
5. 다음 작업 우선순위 결정
   - SOLD 정리
   - onestop_inbound.py
   - mixin 구조 정리
```

---

## 10. 새 세션 시작용 붙여넣기 프롬프트

아래 문장을 새 세션 첫 메시지로 사용:

```text
지금부터 이전 SQM 세션 작업을 이어서 진행해줘.

프로젝트 기준:
- tkinter 유지
- SQLite 유지
- DB schema 변경 금지
- business policy 변경 금지
- 점진적 리팩토링 우선
- 운영 안정성과 데이터 정합성 최우선

현재 기준 커밋:
- c408df1 (GitHub push 완료)

현재 핵심 작업:
- outbound_mixin.py 1차 리팩토링 검증
- confirm_outbound(), reserve_from_allocation(), execute_reserved() 점검
- SOLD는 deprecated/legacy, 현재 write-state는 OUTBOUND 기준

업로드한 파일:
- SQM_HANDOFF.md
- GPT_Claude_Code_Final_Execution_Prompt_v1.md
- GPT_verify_outbound_refactor_v3.py
- GPT_run_verify_outbound_refactor_v3.bat
- 수정된 outbound_mixin.py
- 백업본 outbound_mixin.py.bak_20260402
- 가능하면 Claude 작업 로그 또는 diff 결과

이 파일들과 인계문서를 기준으로:
1) 현재 상태를 요약하고
2) outbound_mixin.py 리팩토링 결과를 PASS/WARN/FAIL로 검증하고
3) 다음 우선 작업(SOLD 정리 / onestop_inbound.py / mixin 정리)을 제안해줘.

보수적으로 판단하고, 정책 변경 없이 진행해줘.
```

---

## 11. 인계 시 업로드 추천 파일 목록

### 최소 업로드
- `SQM_HANDOFF.md`
- 수정된 `outbound_mixin.py`
- `outbound_mixin.py.bak_20260402`

### 권장 업로드
- `SQM_HANDOFF.md`
- `GPT_Claude_Code_Final_Execution_Prompt_v1.md`
- `GPT_verify_outbound_refactor_v3.py`
- `GPT_run_verify_outbound_refactor_v3.bat`
- 수정된 `outbound_mixin.py`
- `outbound_mixin.py.bak_20260402`
- Claude 작업 로그 / diff 결과

---

## 12. 새 세션에서 주의할 점

- 이전 세션 맥락을 자동으로 완전히 기억한다고 가정하지 말 것
- 항상 `SQM_HANDOFF.md`를 같이 올릴 것
- giant file 분해는 구조 정리이지 정책 변경이 아님
- `reserve_from_allocation()`는 기존 `_ra_*` helper 재사용 우선
- STOP 조건은 너무 넓게 보지 말고, persisted data semantics 변경이 생길 때만 엄격 적용

---

## 13. 루비 기준 한줄 요약

> 현재는 `outbound_mixin.py` 1차 구조 안정화 단계이며, 그 다음은 `SOLD` write-path 정리 → `onestop_inbound.py` → 40개+ mixin 구조 정리 순서로 가는 것이 맞다.
