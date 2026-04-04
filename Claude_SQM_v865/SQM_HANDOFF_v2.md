# SQM_HANDOFF_v2.md

> 새 세션에서 SQM 프로젝트 작업을 끊기지 않고 이어가기 위한 **최신 인계문서**
>  
> 기준 시점: 2026-04-02 22:36 (Asia/Seoul)  
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

## 2. 현재 기준 커밋 / Git 상태

- 기준 커밋:
  - `c408df1`
- 브랜치:
  - `main`
- GitHub 저장소:
  - `https://github.com/kidongnam1/SQM_inventory.git`
- 상태:
  - `backup before outbound_mixin refactor`
  - `origin/main` push 완료
- 주의:
  - `c408df1`는 `outbound_mixin.py`만의 순수 커밋이 아니라 **백업용 대형 스냅샷 커밋**
  - 새 작업은 가능하면 **별도 브랜치**에서 진행

권장 브랜치:
```powershell
git checkout -b refactor/outbound-mixin-safe-pass-1
```

---

## 3. 현재 핵심 작업 범위

### 현재 핵심 대상 파일
- `engine_modules/inventory_modular/outbound_mixin.py`

### 현재 핵심 함수
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

## 4. 가장 최근 완료 결과 (중요)

### outbound_mixin.py 1차 리팩토링
- Claude 기반 1차 리팩토링 완료
- 핵심 3함수 분해 완료

### 리팩토링 전후 요약
| 함수 | Before | After | 감소 |
|---|---:|---:|---:|
| `confirm_outbound` | 263줄 | 82줄 | -181줄 |
| `execute_reserved` | 202줄 | 83줄 | -119줄 수준 |
| `reserve_from_allocation` | 665줄 | 466줄 | -199줄 |

### 검증 결과
- `GPT_verify_outbound_refactor_v3.py` 실행 완료
- 결과:
  - PASS 27
  - WARN 1
  - FAIL 0
- `python -m py_compile .\engine_modules\inventory_modular\outbound_mixin.py` 통과
- `python .\run.py --check` 통과

### 검증 결과 핵심 요약
- `confirm_outbound`, `execute_reserved`, `reserve_from_allocation` 존재
- public signature unchanged
- helper extraction signal 확인
- `OUTBOUND` wording signal 확인
- `DOUBLE_OUTBOUND_BLOCKED` 확인
- new SOLD write pattern 없음
- changed_files WARN 1건 존재  
  (실코드 외 `.bkit`, `.claude`, `.md` 문서성 파일 포함)

### 현재 판단
- `outbound_mixin.py` 1차 리팩토링은 **정적 검증 + 최소 실행 검증 통과**
- 다음 단계로 넘어가도 되는 상태

---

## 5. 현재 완료 / 진행중 / 미착수

### 완료
- `outbound_mixin.py` 위험 분석 완료
- 핵심 3함수 분해 설계 완료
- Claude Code 실행 프롬프트 작성 완료
- 검증 스크립트 작성 완료
- `.bat` 실행 파일 작성 완료
- GitHub checkpoint(`c408df1`) 생성 및 push 완료
- `outbound_mixin.py` 1차 리팩토링 완료
- 정적 검증 통과 (PASS 27 / WARN 1 / FAIL 0)
- `py_compile` 통과
- `run.py --check` 통과

### 진행중
- `SOLD` 상태 참조 전역 분류 준비
- 다음 P0 대상 선정
- 새 세션용 인계 문서 최신화

### 미착수
- `SOLD` 전역 참조 분류/정리
- `onestop_inbound.py` 분해
- 40개+ mixin 구조 정리
- parser 예외 구조 정리
- UI refresh / `after()` 구조 최적화
- 릴리스 / manifest / 버전 관리 정리
- 서비스 계층 분리 확장
- 상태 전이 테스트 체계화

---

## 6. 현재 핵심 판단

### 유지해야 하는 방향
- React 전환하지 않음
- PostgreSQL 전환하지 않음
- tkinter 유지
- SQLite 유지
- 구조 안정화 우선
- 서비스 계층 분리 우선
- 핵심 giant file 분해 우선

### 상태 전이 기준
- 현재 기준 상태 흐름:
  - `AVAILABLE -> RESERVED -> PICKED -> OUTBOUND`
- `SOLD`는 deprecated / legacy compatibility 표현
- 새로운 write-state 기준은 `OUTBOUND`
- `SOLD`는 전수 제거가 아니라:
  1. 새 write-path 금지
  2. 기존 참조 분류
  3. 파일별 점진 정리

### LOT / TONBAG / sample 정책
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

## 7. 새 세션에서 추가로 진행할 디버깅 내용 (핵심 백로그)

> **이 섹션이 이번 v2에서 새로 보강된 핵심 섹션**
>  
> 새 세션에서 단순 이어받기만이 아니라, **무엇을 다음에 디버깅해야 하는지**까지 포함한다.

### P0 — 즉시 진행
1. `SOLD` 참조 전역 분류
   - 분류 기준:
     - write-path
     - read-path
     - UI 표시 문자열
     - report/export
     - legacy compatibility
   - 목표:
     - 새 `SOLD` write-path 금지
     - `OUTBOUND` 현재 write-state 기준 고정
   - 산출물:
     - `SOLD_USAGE_MAP.md` 또는 표

2. `onestop_inbound.py` giant file 분석 및 분해 설계
   - 확인 항목:
     - UI / parser / candidate selection / review / apply 혼합 여부
     - 대형 함수 상위 3개
     - `except Exception` / recovery block 위치
   - 목표:
     - 분해 우선순위 설계
   - 산출물:
     - `onestop_inbound_refactor_plan.md`

3. `outbound_mixin.py` 리팩토링 결과 최종 커밋 여부 확인
   - 확인 항목:
     - 별도 커밋 했는지
     - diff 범위가 적절한지
   - 목표:
     - 새 기준점 생성

### P1 — 단기
4. 40개+ mixin 구조 인벤토리 작성
   - 그룹:
     - UI 프레임/윈도우
     - 메뉴/툴바
     - 탭/refresh
     - 대화상자
     - 업무 오케스트레이션
     - 유틸/진단
   - 목표:
     - 결합도 실측
     - 축소 후보 식별
   - 산출물:
     - `MIXIN_INVENTORY.md`

5. 서비스 계층 분리 후보 도출
   - 우선 도메인:
     - outbound
     - allocation
     - picking
   - 목표:
     - UI/handler에서 순수 비즈니스 함수 추출 시작
   - 산출물:
     - `SERVICE_EXTRACTION_PLAN.md`

6. parser / 예외 처리 구조 정리
   - 대상:
     - `onestop_inbound.py`
     - parser 계열
     - Gemini fallback
   - 목표:
     - hard-stop vs warn-only 기준 정리
   - 산출물:
     - `PARSER_EXCEPTION_PLAN.md`

### P2 — 장기
7. UI refresh / `after()` 구조 정리
8. 테스트 기반 확대
9. 릴리스 / manifest / 버전 정리

---

## 8. 전체 디버깅 로드맵

### Phase 0 — 기준점 확보
- `outbound_mixin.py` 1차 리팩토링 검증 완료
- 다음 커밋 기준점 생성

### Phase 1 — 출고 코어 안정화
- `SOLD` 전역 분류
- `onestop_inbound.py` 분석
- 상태 전이 표준화

### Phase 2 — 구조적 결합도 감소
- 40개+ mixin 인벤토리
- 서비스 계층 분리
- giant handler/file 축소

### Phase 3 — 예외 / 성능 / 릴리스 체계화
- parser 예외 표준화
- UI refresh 구조 정리
- manifest / release 기준 정리

---

## 9. 새 세션에서 우선 확인할 것

1. `outbound_mixin.py` 리팩토링 결과가 별도 커밋되었는지 확인
2. `git diff -- engine_modules/inventory_modular/outbound_mixin.py`
3. `verify_outbound_refactor_report.json` 결과 재확인
4. `SOLD` 참조 파일 수 및 분류 시작
5. `onestop_inbound.py` 실제 줄 수 / 대형 함수 / 예외 구조 확인

---

## 10. 새 세션 첫 작업 순서

```text
1. 업로드된 파일 확인
2. handoff 문서 기준 현재 상태 요약
3. outbound_mixin.py 결과가 커밋되었는지 먼저 확인
4. SOLD 참조를 write / read / UI / report 로 분류
5. onestop_inbound.py giant file 분석 착수
6. 40개+ mixin 구조 인벤토리 초안 작성
```

---

## 11. 현재 보유 산출물

### 문서
- `SQM_HANDOFF_v2.md`
- `GPT_Claude_Code_Final_Execution_Prompt_v1.md`
- 필요 시 v1.1로 보정 예정

### 검증 스크립트
- `GPT_verify_outbound_refactor_v3.py`

### 실행 배치파일
- `GPT_run_verify_outbound_refactor_v3.bat`

### 코드 파일
- 수정된 `outbound_mixin.py`
- 백업본 `outbound_mixin.py.bak_20260402`

### 리포트
- `verify_outbound_refactor_report.json`

---

## 12. 새 세션 시작용 붙여넣기 프롬프트

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

현재 핵심 상태:
- outbound_mixin.py 1차 리팩토링 완료
- 정적 검증 통과
- py_compile 통과
- run.py --check 통과
- 현재 write-state 기준은 OUTBOUND
- SOLD는 deprecated/legacy compatibility 표현

현재 다음 P0:
1. outbound_mixin.py 별도 커밋 여부 확인
2. SOLD 참조를 write / read / UI / report 로 분류
3. onestop_inbound.py giant file 분석 착수

업로드한 파일:
- SQM_HANDOFF_v2.md
- GPT_Claude_Code_Final_Execution_Prompt_v1.md
- GPT_verify_outbound_refactor_v3.py
- GPT_run_verify_outbound_refactor_v3.bat
- verify_outbound_refactor_report.json
- 수정된 outbound_mixin.py
- 백업본 outbound_mixin.py.bak_20260402
- 가능하면 Claude 작업 로그 또는 diff 결과

이 파일들과 인계문서를 기준으로:
1) 현재 상태를 요약하고
2) 다음 P0 작업부터 바로 이어서 진행하고
3) SOLD 분류 또는 onestop_inbound.py 분석 중 무엇부터 할지 추천해줘.

보수적으로 판단하고, 정책 변경 없이 진행해줘.
```

---

## 13. 새 세션에서 주의할 점

- 이전 세션 맥락을 자동으로 완전히 기억한다고 가정하지 말 것
- 항상 최신 handoff 문서를 같이 올릴 것
- giant file 분해는 구조 정리이지 정책 변경이 아님
- `reserve_from_allocation()`는 기존 `_ra_*` helper 재사용 우선
- STOP 조건은 너무 넓게 적용하지 말고, persisted data semantics 변경이 생길 때만 엄격 적용

---

## 14. 루비 기준 한줄 요약

> 현재는 `outbound_mixin.py` 1차 구조 안정화가 끝났고, 다음은 `SOLD` write-path/read-path 분류 → `onestop_inbound.py` → 40개+ mixin 구조 정리 순서로 가는 것이 맞다.
