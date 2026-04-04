# GPT_SQM_최종실행팩_폴더트리_샘플.md
생성일: 2026-04-04 16:40 (Asia/Seoul)

---

## [질문]
루비 권장 순서대로 계속 진행해서 **최종실행팩 폴더트리 샘플**을 작성

## [질문의도]
지금까지 만든 모든 문서/프롬프트/스크립트를 실제 운영 가능한 실행팩으로 묶을 때  
어떤 폴더 트리로 배치하면 되는지 **복사 가능한 샘플 구조**를 제공한다.

---

# [응답]

# 1. 이 문서의 목적

이 문서는 아래 상황에서 바로 사용할 수 있다.

```text
1. 새 폴더를 만들고 실행팩을 배치할 때
2. 다른 PC로 옮길 때
3. ZIP 압축 전 최종 구조를 맞출 때
4. 운영자/개발자/AI 실행도구가 같은 구조를 보게 할 때
```

---

# 2. 권장 최종 폴더 트리 (확장형 기준)

```text
SQM_P0_EXEC_PACK/
├─ 00_MASTER/
│  ├─ MASTER_FINAL_v867_통합완성본.md
│  ├─ GPT_SQM_867_React_P0_패치설계서.md
│  ├─ GPT_SQM_P0_통합체크리스트_v2.md
│  └─ GPT_SQM_P0_통합인덱스_마스터팩.md
│
├─ 01_P0-1_FOUNDATION/
│  ├─ GPT_SQM_P0-1_초상세_작업지시서.md
│  ├─ GPT_SQM_P0-1_수정대상파일표.md
│  ├─ GPT_SQM_P0-1_DB스키마점검표.md
│  ├─ GPT_SQM_P0-1_실행파일연동점검표.md
│  └─ GPT_SQM_P0-1_완료보고서.md
│
├─ 02_P0-2_READ/
│  ├─ GPT_SQM_P0-2_LOT상세모달_초상세_작업지시서.md
│  ├─ GPT_SQM_P0-2_LOT상세모달_테스트체크리스트.md
│  └─ GPT_ClaudeCode_P0-2_실행프롬프트.md
│
├─ 03_P0-3_WRITE/
│  ├─ GPT_SQM_P0-3_입고출고_WriteLoop_초상세_작업지시서.md
│  ├─ GPT_SQM_P0-3_입고출고_WriteLoop_테스트체크리스트.md
│  └─ GPT_ClaudeCode_P0-3_실행프롬프트.md
│
├─ 04_P0-4_INTEGRATION/
│  ├─ GPT_SQM_P0-4_위치업데이트_통합실행_초상세_작업지시서.md
│  ├─ GPT_SQM_P0-4_테스트체크리스트.md
│  └─ GPT_ClaudeCode_P0-4_실행프롬프트.md
│
├─ 05_AUTORUN/
│  ├─ GPT_SQM_ClaudeCode_실행순서_안내문.md
│  ├─ GPT_SQM_자동실행_BAT_구성매뉴얼.md
│  ├─ GPT_SQM_자동실행_PS1_실전예시.md
│  ├─ GPT_SQM_최종실행팩_구성체크리스트.md
│  ├─ GPT_SQM_실행패키지_배포순서_안내문.md
│  ├─ GPT_SQM_P0_문서일괄압축_준비체크리스트.md
│  └─ prompts/
│     ├─ GPT_ClaudeCode_P0-2_실행프롬프트.md
│     ├─ GPT_ClaudeCode_P0-3_실행프롬프트.md
│     └─ GPT_ClaudeCode_P0-4_실행프롬프트.md
│
├─ 06_REPORTS/
│  ├─ GPT_SQM_P0_최종_완료보고서_초안.md
│  ├─ P0-2_테스트결과.md
│  ├─ P0-3_테스트결과.md
│  ├─ P0-4_테스트결과.md
│  └─ 최종판정_메모.md
│
├─ 07_LOGS/
│  ├─ run_status.log
│  ├─ p0_2_run.log
│  ├─ p0_3_run.log
│  ├─ p0_4_run.log
│  ├─ p0_2_test.log
│  ├─ p0_3_test.log
│  ├─ p0_4_test.log
│  └─ final_summary.log
│
├─ 08_RESULTS/
│  ├─ stage_status.json
│  ├─ p0_2_result.txt
│  ├─ p0_3_result.txt
│  ├─ p0_4_result.txt
│  └─ final_result.txt
│
├─ 09_SCRIPTS/
│  ├─ run_all_p0.bat
│  ├─ run_p0_2.bat
│  ├─ run_p0_3.bat
│  ├─ run_p0_4.bat
│  ├─ run_all_p0.ps1
│  ├─ run_stage.ps1
│  ├─ check_env.ps1
│  └─ write_run_log.ps1
│
└─ 99_ARCHIVE/
   ├─ old_versions/
   ├─ drafts/
   └─ deprecated/
```

---

# 3. 최소 운영형 폴더 트리

운영 초기에 너무 복잡하면 아래 **최소형 구조**로 시작해도 된다.

```text
SQM_P0_EXEC_PACK_MIN/
├─ MASTER/
│  ├─ MASTER_FINAL_v867_통합완성본.md
│  ├─ GPT_SQM_P0_통합체크리스트_v2.md
│  └─ GPT_SQM_P0_통합인덱스_마스터팩.md
│
├─ P0-2/
│  ├─ GPT_SQM_P0-2_LOT상세모달_초상세_작업지시서.md
│  ├─ GPT_SQM_P0-2_LOT상세모달_테스트체크리스트.md
│  └─ GPT_ClaudeCode_P0-2_실행프롬프트.md
│
├─ P0-3/
│  ├─ GPT_SQM_P0-3_입고출고_WriteLoop_초상세_작업지시서.md
│  ├─ GPT_SQM_P0-3_입고출고_WriteLoop_테스트체크리스트.md
│  └─ GPT_ClaudeCode_P0-3_실행프롬프트.md
│
├─ P0-4/
│  ├─ GPT_SQM_P0-4_위치업데이트_통합실행_초상세_작업지시서.md
│  ├─ GPT_SQM_P0-4_테스트체크리스트.md
│  └─ GPT_ClaudeCode_P0-4_실행프롬프트.md
│
├─ AUTORUN/
│  ├─ GPT_SQM_ClaudeCode_실행순서_안내문.md
│  ├─ GPT_SQM_자동실행_BAT_구성매뉴얼.md
│  └─ GPT_SQM_자동실행_PS1_실전예시.md
│
├─ REPORTS/
└─ SCRIPTS/
```

---

# 4. 운영 관점 추천 구조

## 운영자용으로 가장 보기 쉬운 구조
```text
00_MASTER
05_AUTORUN
06_REPORTS
09_SCRIPTS
```

## 개발자/리팩토링 작업자용으로 가장 중요한 구조
```text
01_P0-1_FOUNDATION
02_P0-2_READ
03_P0-3_WRITE
04_P0-4_INTEGRATION
```

## Claude Code / Cursor용으로 가장 중요한 구조
```text
00_MASTER
각 단계별 GPT_ClaudeCode_실행프롬프트.md
05_AUTORUN/prompts
```

---

# 5. 폴더별 필수/선택 구분

| 폴더 | 필수 여부 | 이유 |
|---|---|---|
| `00_MASTER` | 필수 | 기준 문서 |
| `01_P0-1_FOUNDATION` | 필수 | 구조/DB/실행 기초 |
| `02_P0-2_READ` | 필수 | read 단계 |
| `03_P0-3_WRITE` | 필수 | write 단계 |
| `04_P0-4_INTEGRATION` | 필수 | 통합 단계 |
| `05_AUTORUN` | 필수 | 실행 안내/자동화 |
| `06_REPORTS` | 필수 | 결과 기록 |
| `07_LOGS` | 강력 권장 | 추적성 |
| `08_RESULTS` | 권장 | 자동 판정 연계 |
| `09_SCRIPTS` | 필수 | 실제 실행 |
| `99_ARCHIVE` | 선택 | 정리용 |

---

# 6. 실제 운영 시 배치 규칙

## 규칙 1. 문서와 스크립트는 분리
- 문서는 `00_MASTER~06_REPORTS`
- 실행 스크립트는 `09_SCRIPTS`

## 규칙 2. 로그와 결과를 분리
- 로그는 `07_LOGS`
- 판정 결과는 `08_RESULTS`

## 규칙 3. prompts는 복제 보관 가능
- 원본은 단계 폴더에도 있음
- Claude 실행 편의를 위해 `05_AUTORUN/prompts`에도 복제 가능

## 규칙 4. 초안은 archive로 이동
- 실사용 폴더에는 최신본만 둔다

---

# 7. 운영 시 가장 많이 쓰는 파일 위치

## 사람이 가장 자주 여는 파일
```text
00_MASTER/MASTER_FINAL_v867_통합완성본.md
00_MASTER/GPT_SQM_P0_통합체크리스트_v2.md
05_AUTORUN/GPT_SQM_ClaudeCode_실행순서_안내문.md
06_REPORTS/GPT_SQM_P0_최종_완료보고서_초안.md
```

## Claude Code 실행 시 가장 자주 참조하는 파일
```text
00_MASTER/MASTER_FINAL_v867_통합완성본.md
05_AUTORUN/prompts/GPT_ClaudeCode_P0-2_실행프롬프트.md
05_AUTORUN/prompts/GPT_ClaudeCode_P0-3_실행프롬프트.md
05_AUTORUN/prompts/GPT_ClaudeCode_P0-4_실행프롬프트.md
```

## 테스트 시 가장 자주 보는 파일
```text
02_P0-2_READ/*테스트체크리스트.md
03_P0-3_WRITE/*테스트체크리스트.md
04_P0-4_INTEGRATION/*테스트체크리스트.md
06_REPORTS/P0-2_테스트결과.md
06_REPORTS/P0-3_테스트결과.md
06_REPORTS/P0-4_테스트결과.md
```

---

# 8. 초기 셋업 순서

```text
1. 00_MASTER 배치
2. 단계별 폴더 배치
3. 05_AUTORUN 배치
4. 09_SCRIPTS 배치
5. 07_LOGS / 08_RESULTS / 06_REPORTS 폴더 생성
6. check_env.ps1 실행
7. P0-2부터 단계 실행
```

---

# 9. 루비 최종 판단

```text
좋은 폴더 구조의 기준은 "예쁘게 보이는가"가 아니라
"누가 봐도 다음에 무엇을 열어야 하는지 바로 아는가"이다.
이 샘플 구조는 그 기준에 맞춰 설계되었다.
```

---

# 10. 다음 단계 권장

다음으로 가장 자연스러운 문서는 아래다.

```text
1. GPT_SQM_최종운영자_1페이지_퀵가이드.md
2. GPT_SQM_최종실행팩_바로실행_체크카드.md
3. GPT_SQM_실행팩_ZIP_포장기준.md
```

루비 권장 순서는 아래다.

```text
1) 운영자 1페이지 퀵가이드
2) 바로실행 체크카드
3) ZIP 포장기준
```
