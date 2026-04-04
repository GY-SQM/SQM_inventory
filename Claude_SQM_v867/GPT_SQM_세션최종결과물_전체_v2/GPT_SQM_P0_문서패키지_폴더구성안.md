# GPT_SQM_P0_문서패키지_폴더구성안.md
생성일: 2026-04-04 16:26 (Asia/Seoul)

---

## [질문]
계속 이어서 진행해서 **P0 문서패키지 폴더구성안**을 작성

## [질문의도]
지금까지 생성한 P0 관련 문서들을 실제 작업 폴더에 어떤 구조로 배치해야  
가장 찾기 쉽고, 실행 순서가 명확하고, 유지보수가 쉬운지  
**실전용 폴더 구조 기준**을 정리한다.

---

# [응답]

# 1. 이 문서의 목적

이 문서는 아래를 해결하기 위한 것이다.

```text
1. P0 문서가 흩어져서 찾기 어려운 문제 해결
2. 설계서 / 테스트 / 실행 프롬프트 / 보고서를 분리 관리
3. 사람이 보든 Claude Code가 보든 순서가 명확하게 정리
4. 나중에 P1/P2로 확장할 때도 같은 체계를 유지
```

---

# 2. 권장 최상위 패키지 구조

```text
SQM_P0_DOC_PACK/
 ├─ 00_MASTER/
 ├─ 01_P0-1_FOUNDATION/
 ├─ 02_P0-2_READ/
 ├─ 03_P0-3_WRITE/
 ├─ 04_P0-4_INTEGRATION/
 ├─ 05_AUTORUN/
 ├─ 06_REPORTS/
 └─ 99_ARCHIVE/
```

---

# 3. 폴더별 역할

## 00_MASTER
P0 전체를 보는 상위 문서 모음

## 01_P0-1_FOUNDATION
구조 고정 / 파일표 / DB / 실행파일 점검 문서

## 02_P0-2_READ
LOT 상세 모달 관련 설계/테스트/실행 프롬프트

## 03_P0-3_WRITE
입고/출고 write loop 관련 설계/테스트/실행 프롬프트

## 04_P0-4_INTEGRATION
위치변경 / 통합실행 / 회귀 / 실행 프롬프트

## 05_AUTORUN
Claude 실행 순서, BAT/PS1, 자동화 관련 문서

## 06_REPORTS
완료보고서 / 최종 판정 / 실행 결과 리포트

## 99_ARCHIVE
이전 버전, 초안, 폐기 문서 보관

---

# 4. 실제 파일 배치 예시

## 4-1. 00_MASTER
```text
00_MASTER/
 ├─ MASTER_FINAL_v867_통합완성본.md
 ├─ GPT_SQM_P0_통합체크리스트_v2.md
 ├─ GPT_SQM_P0_통합인덱스_마스터팩.md
 └─ GPT_SQM_867_React_P0_패치설계서.md
```

## 4-2. 01_P0-1_FOUNDATION
```text
01_P0-1_FOUNDATION/
 ├─ GPT_SQM_P0-1_초상세_작업지시서.md
 ├─ GPT_SQM_P0-1_수정대상파일표.md
 ├─ GPT_SQM_P0-1_DB스키마점검표.md
 ├─ GPT_SQM_P0-1_실행파일연동점검표.md
 └─ GPT_SQM_P0-1_완료보고서.md
```

## 4-3. 02_P0-2_READ
```text
02_P0-2_READ/
 ├─ GPT_SQM_P0-2_LOT상세모달_초상세_작업지시서.md
 ├─ GPT_SQM_P0-2_LOT상세모달_테스트체크리스트.md
 └─ GPT_ClaudeCode_P0-2_실행프롬프트.md
```

## 4-4. 03_P0-3_WRITE
```text
03_P0-3_WRITE/
 ├─ GPT_SQM_P0-3_입고출고_WriteLoop_초상세_작업지시서.md
 ├─ GPT_SQM_P0-3_입고출고_WriteLoop_테스트체크리스트.md
 └─ GPT_ClaudeCode_P0-3_실행프롬프트.md
```

## 4-5. 04_P0-4_INTEGRATION
```text
04_P0-4_INTEGRATION/
 ├─ GPT_SQM_P0-4_위치업데이트_통합실행_초상세_작업지시서.md
 ├─ GPT_SQM_P0-4_테스트체크리스트.md
 └─ GPT_ClaudeCode_P0-4_실행프롬프트.md
```

## 4-6. 05_AUTORUN
```text
05_AUTORUN/
 ├─ GPT_SQM_ClaudeCode_실행순서_안내문.md
 ├─ GPT_SQM_자동실행_BAT_구성매뉴얼.md
 ├─ GPT_SQM_자동실행_PS1_실전예시.md
 └─ prompts/
     ├─ GPT_ClaudeCode_P0-2_실행프롬프트.md
     ├─ GPT_ClaudeCode_P0-3_실행프롬프트.md
     └─ GPT_ClaudeCode_P0-4_실행프롬프트.md
```

## 4-7. 06_REPORTS
```text
06_REPORTS/
 ├─ GPT_SQM_P0_최종_완료보고서_초안.md
 ├─ P0-2_테스트결과.md
 ├─ P0-3_테스트결과.md
 ├─ P0-4_테스트결과.md
 └─ 최종판정_메모.md
```

---

# 5. 파일명 규칙

파일명은 지금처럼 **단계 + 역할 + 성격**이 드러나게 유지하는 것이 좋다.

예:
```text
GPT_SQM_P0-2_LOT상세모달_초상세_작업지시서.md
GPT_SQM_P0-3_입고출고_WriteLoop_테스트체크리스트.md
GPT_ClaudeCode_P0-4_실행프롬프트.md
```

## 권장 규칙
```text
[문서종류]_[단계]_[주제]_[문서성격].md
```

문서성격 예시:
- 초상세_작업지시서
- 테스트체크리스트
- 실행프롬프트
- 완료보고서
- 구성매뉴얼
- 안내문

---

# 6. 운영 규칙

## 6-1. 수정 규칙
- `00_MASTER` 문서는 핵심 기준 문서이므로 함부로 덮어쓰지 않는다
- 단계별 수정은 해당 폴더 문서에만 반영한다
- 테스트 결과 문서는 `06_REPORTS`에 별도 누적한다

## 6-2. 버전 규칙
- 큰 변경이 생기면 `v2`, `v3`를 붙인다
- 초안은 `draft` 대신 `초안`으로 통일해도 된다
- 폐기 문서는 `99_ARCHIVE`로 이동한다

## 6-3. 실행 규칙
- Claude Code는 `00_MASTER` + 단계별 `실행프롬프트` 조합으로 사용
- 수동 구현 시 `초상세_작업지시서` → `테스트체크리스트` 순서 사용
- 최종 결과는 항상 `06_REPORTS`에 기록

---

# 7. 사람이 보는 관점에서의 권장 순서

```text
1. 00_MASTER
2. 01_P0-1_FOUNDATION
3. 02_P0-2_READ
4. 03_P0-3_WRITE
5. 04_P0-4_INTEGRATION
6. 05_AUTORUN
7. 06_REPORTS
```

---

# 8. Claude Code 기준 권장 참조 순서

```text
00_MASTER/MASTER_FINAL_v867_통합완성본.md
00_MASTER/GPT_SQM_P0_통합체크리스트_v2.md
각 단계의 GPT_ClaudeCode_실행프롬프트.md
06_REPORTS/테스트결과
```

즉, Claude는 전체 설계서를 다 보지 않아도 되지만,
**MASTER + 통합체크리스트 + 단계 실행프롬프트**는 반드시 보아야 한다.

---

# 9. 권장 추가 폴더

실무에서는 아래 폴더도 있으면 좋다.

```text
07_LOGS/
08_RESULTS/
09_SCRIPTS/
```

예:
```text
07_LOGS/
 ├─ p0_2_run.log
 ├─ p0_3_run.log
 ├─ p0_4_run.log
 └─ run_status.log

08_RESULTS/
 ├─ stage_status.json
 ├─ p0_2_result.txt
 ├─ p0_3_result.txt
 └─ p0_4_result.txt

09_SCRIPTS/
 ├─ run_all_p0.bat
 ├─ run_all_p0.ps1
 ├─ check_env.ps1
 └─ write_run_log.ps1
```

---

# 10. 최소 패키지형 구조와 확장형 구조

## A안. 최소 패키지형
```text
MASTER / P0-1 / P0-2 / P0-3 / P0-4 / REPORTS
```

### 장점
- 단순
- 찾기 쉬움

### 단점
- 자동화 문서와 실행 스크립트가 섞이기 쉬움

---

## B안. 확장형 구조 (권장)
```text
00_MASTER
01_P0-1_FOUNDATION
02_P0-2_READ
03_P0-3_WRITE
04_P0-4_INTEGRATION
05_AUTORUN
06_REPORTS
07_LOGS
08_RESULTS
09_SCRIPTS
99_ARCHIVE
```

### 장점
- 유지보수 쉬움
- 실행과 문서가 분리됨
- P1/P2 확장 쉬움

### 권장도
**가장 추천**

---

# 11. 루비 최종 판단

이번 폴더구성안의 핵심은 아래다.

```text
문서가 많아질수록 잘 쓰는 방법은 "더 만들기"가 아니라 "잘 배치하기"다.
P0 문서는 이미 충분히 많기 때문에, 지금부터는 폴더 구조가 품질을 결정한다.
```

---

# 12. 다음 단계 권장

다음으로 가장 자연스러운 문서는 아래다.

```text
1. GPT_SQM_최종실행팩_구성체크리스트.md
2. GPT_SQM_실행패키지_배포순서_안내문.md
3. GPT_SQM_P0_문서일괄압축_준비체크리스트.md
```

루비 권장 순서는 아래다.

```text
1) 최종실행팩 구성체크리스트
2) 실행패키지 배포순서 안내문
3) 문서일괄압축 준비체크리스트
```
