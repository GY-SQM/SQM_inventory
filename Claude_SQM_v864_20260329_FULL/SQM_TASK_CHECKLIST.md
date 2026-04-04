# SQM_TASK_CHECKLIST.md

> SQM 프로젝트 작업관리 체크리스트  
> 기준 시점: 2026-04-02 22:40 (Asia/Seoul)  
> 인코딩: UTF-8

---

## 1. 프로젝트 운영 원칙 체크

- [ ] tkinter 유지
- [ ] SQLite 유지
- [ ] DB schema 변경 금지 유지
- [ ] business policy 변경 금지 유지
- [ ] public method signature 변경 금지 유지
- [ ] cross-file interface 변경 금지 유지
- [ ] 운영 안정성 / 데이터 정합성 우선 유지

---

## 2. 현재 기준점 체크

- [x] 기준 커밋 `c408df1` 확보
- [x] GitHub `origin/main` push 완료
- [ ] 새 작업용 브랜치 생성
  - 권장: `refactor/outbound-mixin-safe-pass-1`

### 메모
- `c408df1`는 순수 단일 파일 커밋이 아니라 백업용 대형 스냅샷 커밋
- 이후 작업은 가능하면 별도 브랜치에서 진행

---

## 3. outbound_mixin.py 1차 작업 체크

### 분석 / 설계
- [x] `outbound_mixin.py` 위험 분석 완료
- [x] 핵심 3함수 선정 완료
  - [x] `confirm_outbound()`
  - [x] `reserve_from_allocation()`
  - [x] `execute_reserved()`
- [x] Claude Code 실행 프롬프트 작성 완료
- [x] 검증 스크립트 작성 완료
- [x] `.bat` 실행 파일 작성 완료

### 리팩토링 결과
- [x] `confirm_outbound()` 1차 헬퍼 분해 완료
- [x] `reserve_from_allocation()` 미분해 구간 추가 분해 완료
- [x] `execute_reserved()` 1차 헬퍼 분해 완료

### 검증
- [x] 정적 검증 통과
- [x] PASS 27 / WARN 1 / FAIL 0
- [x] `py_compile` 통과
- [x] `run.py --check` 통과
- [ ] 리팩토링 결과 별도 커밋
- [ ] 리팩토링 결과 별도 push
- [ ] 최종 diff 육안 검토 재확인

### 리팩토링 후 핵심 확인
- [x] public signature unchanged
- [x] new SOLD write pattern 없음
- [x] `OUTBOUND` wording signal 확인
- [x] `DOUBLE_OUTBOUND_BLOCKED` 확인
- [ ] lot-mode / tonbag-mode 실제 시나리오 점검
- [ ] inventory weight 반영 실제 시나리오 점검
- [ ] sold_table / picking_table 실제 반영 시나리오 점검

---

## 4. SOLD 상태 정리 체크 (다음 P0)

### 1단계: 분류
- [ ] `SOLD` 참조 전역 검색
- [ ] write-path 분류
- [ ] read-path 분류
- [ ] UI 표시 문자열 분류
- [ ] report/export 분류
- [ ] legacy compatibility 분류

### 2단계: 조치
- [ ] 새 `SOLD` write-path 금지 확인
- [ ] `OUTBOUND`를 현재 write-state 기준으로 고정
- [ ] 핵심 파일부터 `SOLD` 표현 정리
- [ ] 상태 전이 테스트 시나리오 초안 작성

### 산출물
- [ ] `SOLD_USAGE_MAP.md` 작성
- [ ] 상태 전이 표 초안 작성

---

## 5. onestop_inbound.py 분석 체크 (다음 P0)

### 구조 분석
- [ ] 파일 줄 수 재확인
- [ ] 대형 함수 상위 3개 추출
- [ ] UI / parser / candidate / review / apply 블록 분리
- [ ] `except Exception` / recovery block 위치 확인
- [ ] parser fallback / Gemini 경로 확인

### 설계
- [ ] giant function 분해 전략 초안 작성
- [ ] helper extraction 후보 작성
- [ ] hard-stop / warn-only 구분 초안 작성

### 산출물
- [ ] `onestop_inbound_refactor_plan.md` 작성

---

## 6. mixin 40개+ 구조 정리 체크 (P1)

### 인벤토리
- [ ] 실제 mixin 목록 전수 추출
- [ ] 상속 구조 도식화
- [ ] 기능 그룹별 분류
  - [ ] UI 프레임/윈도우
  - [ ] 메뉴/툴바
  - [ ] 탭/refresh
  - [ ] 대화상자
  - [ ] 업무 오케스트레이션
  - [ ] 유틸/진단

### 평가
- [ ] dead mixin 후보 식별
- [ ] 유사/중복 mixin 후보 식별
- [ ] 지나치게 얇은 mixin 후보 식별
- [ ] giant mixin 후보 식별

### 산출물
- [ ] `MIXIN_INVENTORY.md`
- [ ] `MIXIN_REFACTOR_PLAN.md`

---

## 7. 서비스 계층 분리 체크 (P1)

### 후보 도출
- [ ] outbound 서비스 함수 후보 정리
- [ ] allocation 서비스 함수 후보 정리
- [ ] picking 서비스 함수 후보 정리

### 분리 방향
- [ ] UI/handler → thin wrapper 방향 확인
- [ ] 순수 비즈니스 함수 추출 기준 정리
- [ ] DB write / state rule / result builder 분리 기준 정리

### 산출물
- [ ] `SERVICE_EXTRACTION_PLAN.md`

---

## 8. parser / 예외 처리 정리 체크 (P1)

### 분석
- [ ] `except pass` 전수 검색
- [ ] broad exception 전수 검색
- [ ] parser 계열 실패 흐름 정리
- [ ] Gemini fallback 실패 흐름 정리

### 설계
- [ ] hard-stop vs warn-only 표 작성
- [ ] parse failure 표준 result object 초안 작성
- [ ] 사용자 메시지 vs 내부 로그 분리 기준 작성

### 산출물
- [ ] `PARSER_EXCEPTION_PLAN.md`

---

## 9. UI refresh / after() 최적화 체크 (P2)

### 분석
- [ ] `after()` 호출 지도 작성
- [ ] 중복 refresh 위치 확인
- [ ] TreeView 대량 갱신 위치 확인

### 개선 후보
- [ ] dirty refresh 도입 후보
- [ ] background refresh 후보
- [ ] tab별 refresh 공통화 후보
- [ ] TreeView insert/delete 공통화 후보

### 산출물
- [ ] `UI_REFRESH_PLAN.md`

---

## 10. 릴리스 / manifest 정리 체크 (P2)

### 점검
- [ ] 현재 배포 기준 폴더 확정
- [ ] `v864`, `v866` 관계 정리
- [ ] release snapshot vs backup snapshot 구분
- [ ] 실제 배포 대상 파일 목록 정리

### 산출물
- [ ] `RELEASE_MANIFEST.md`

---

## 11. 현재 보유 파일 체크

- [x] `SQM_HANDOFF_v2.md`
- [x] `GPT_Claude_Code_Final_Execution_Prompt_v1.md`
- [x] `GPT_verify_outbound_refactor_v3.py`
- [x] `GPT_run_verify_outbound_refactor_v3.bat`
- [x] `verify_outbound_refactor_report.json`
- [x] 수정된 `outbound_mixin.py`
- [x] 백업본 `outbound_mixin.py.bak_20260402`

---

## 12. 새 세션 시작 전 체크

- [ ] `SQM_HANDOFF_v2.md` 최신판 업로드
- [ ] 이 체크리스트 파일 업로드
- [ ] 수정된 `outbound_mixin.py` 업로드
- [ ] 백업본 `outbound_mixin.py.bak_20260402` 업로드
- [ ] 검증 리포트 JSON 업로드
- [ ] 필요 시 Claude 작업 로그 / diff 업로드

---

## 13. 새 세션 첫 작업 체크

- [ ] 현재 상태 요약 받기
- [ ] `outbound_mixin.py` 별도 커밋 여부 확인
- [ ] `SOLD` 참조 전역 분류 시작
- [ ] `onestop_inbound.py` giant file 분석 시작
- [ ] 다음 P0 / P1 순서 확정

---

## 14. 진행 메모

### 최근 완료 메모
- `outbound_mixin.py` 1차 리팩토링 및 검증 완료
- 최소 실행 검증 통과
- 다음 핵심은 `SOLD` 분류와 `onestop_inbound.py`

### 주의 메모
- giant file 분해는 구조 정리이지 정책 변경이 아님
- `reserve_from_allocation()`는 기존 `_ra_*` helper 재사용 우선
- 너무 넓은 STOP 조건은 피하고, persisted data semantics 변경 시만 엄격 적용

---

## 15. 루비 기준 다음 순서

1. [ ] `outbound_mixin.py` 결과 별도 커밋
2. [ ] `SOLD` 참조를 write/read/UI/report로 분류
3. [ ] `onestop_inbound.py` 분석
4. [ ] 40개+ mixin 인벤토리 작성
5. [ ] 서비스 계층 분리 후보 정리
