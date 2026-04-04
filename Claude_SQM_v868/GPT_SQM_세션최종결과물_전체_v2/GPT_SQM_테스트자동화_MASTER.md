# GPT_SQM_테스트자동화_MASTER.md
생성일: 2026-04-04 18:26 (Asia/Seoul)

[질문] 테스트 자동화까지 만들어 달라는 요청  
[질문의도] 다음 세션에서 실행만 하지 말고, 단계별 테스트 결과를 더 빠르고 일관되게 판단할 수 있도록 테스트 자동화 기준 문서를 만든다.

---

# [응답]

# 1. 이 문서의 목표

```text
1. P0 / P2 / P3 / P4 / P5 단계별 테스트를 자동화 가능한 형태로 정리
2. PASS / FAIL / CONDITIONAL PASS 판정을 표준화
3. logs / results / reports 구조를 테스트 자동화와 연결
4. 사람이 전부 수동 확인하지 않아도 되는 준자동 체계를 만든다
```

---

# 2. 권장 자동화 수준

## A안. 반자동 (현재 기본)
- Claude 실행
- 사람이 테스트 체크리스트 확인
- PASS 입력 후 다음 단계

## B안. 준자동 (권장)
- Claude 실행
- 테스트 스크립트 실행
- 결과 파일 생성
- PASS 조건 충족 시 다음 단계

## C안. 완전자동 (비추천)
- Claude 실행
- 테스트
- 판정
- 다음 단계 전부 자동

### 루비 권장
```text
준자동
```

---

# 3. 자동화 대상

## 3-1. 환경 검증
- claude CLI
- python
- 필수 파일 존재
- logs/results/reports 폴더 존재

## 3-2. 실행 결과 검증
- 로그 파일 생성 여부
- 결과 파일 생성 여부
- 에러 키워드 탐지
- expected output 존재 여부

## 3-3. 단계별 기능 검증
- P0-2: LOT 상세 API 응답 / 모달 렌더 준비
- P0-3: upload/create/execute/cancel API 응답
- P0-4: location/update / run/env/log 구조
- P2 이후: UI/API/parser/log 구조 개별 검증

---

# 4. 자동화 원칙

- 테스트는 "완전 판정"보다 "빠른 이상 감지"에 초점
- 치명 오류는 자동 FAIL
- 애매한 상태는 CONDITIONAL PASS
- 사람이 최종 승인하는 구조 유지
- logs / results / reports는 분리 유지

---

# 5. 결과 판정 규칙

## PASS
- 필수 로그 생성
- 필수 결과 파일 생성
- 치명 에러 키워드 없음
- expected success marker 존재

## CONDITIONAL PASS
- 실행은 완료
- 경미한 warning 존재
- 수동 확인 필요 항목 있음

## FAIL
- 실행 로그 없음
- 결과 파일 없음
- traceback / fatal / exception 존재
- expected marker 없음
- 단계 중단 발생

---

# 6. 권장 결과 파일 구조

```text
08_RESULTS/
 ├─ p0_2_result.json
 ├─ p0_3_result.json
 ├─ p0_4_result.json
 ├─ p2_result.json
 ├─ patch2_result.json
 ├─ p3_result.json
 ├─ patch3_result.json
 ├─ p4_result.json
 ├─ patch4_result.json
 ├─ p5_result.json
 ├─ patch5_result.json
 └─ final_result.json
```

---

# 7. 권장 JSON 규격

```json
{
  "stage": "P0-2",
  "status": "PASS",
  "started_at": "2026-04-04 18:30:00",
  "ended_at": "2026-04-04 18:31:10",
  "log_file": "07_LOGS/p0_2_run.log",
  "checks": [
    {"name": "log_exists", "status": "PASS"},
    {"name": "error_keyword_scan", "status": "PASS"},
    {"name": "result_marker", "status": "PASS"}
  ],
  "notes": []
}
```

---

# 8. 자동화 단계

## Step 1
check_env.ps1 실행

## Step 2
run_stage.ps1 실행

## Step 3
test_stage.ps1 실행

## Step 4
결과 파일 생성

## Step 5
run_all_p0.ps1 또는 후속 runner가 결과 파일 읽고 다음 단계 판정

---

# 9. 치명 오류 키워드 예시

```text
Traceback
Exception
Fatal
ModuleNotFoundError
AttributeError
KeyError
RuntimeError
FAILED
rollback failed
```

---

# 10. 조건부 경고 키워드 예시

```text
warning
deprecated
fallback
inferred
partial
manual check
```

---

# 11. 루비 최종 판단

```text
테스트 자동화의 목적은 사람을 완전히 없애는 것이 아니라,
사람이 봐야 할 양을 줄이고,
실패를 더 빨리 발견하게 만드는 것이다.
```
