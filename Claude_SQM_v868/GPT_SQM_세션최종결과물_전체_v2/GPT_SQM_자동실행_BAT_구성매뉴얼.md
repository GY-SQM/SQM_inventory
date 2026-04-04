# GPT_SQM_자동실행_BAT_구성매뉴얼.md
생성일: 2026-04-04 16:14 (Asia/Seoul)

---

## [질문]
계속 이어서 진행해서 **자동실행 BAT 구성 매뉴얼**을 작성

## [질문의도]
지금까지 만든 P0 문서와 Claude Code 실행 순서를 바탕으로,  
실제 Windows 환경에서 **Claude 실행 → 단계별 테스트 → 로그 저장 → 결과 확인**까지
BAT/PowerShell 기준으로 재현 가능한 실행 구조를 설계한다.

---

# [응답]

# 1. 이 문서의 목적

이 문서는 아래를 해결하기 위한 것이다.

```text
1. Claude Code를 수동으로 여러 번 입력하지 않게 한다
2. P0-2 / P0-3 / P0-4를 순서대로 실행할 수 있게 한다
3. 각 단계별 로그와 결과를 남기게 한다
4. 실패 시 어느 단계에서 멈췄는지 바로 알 수 있게 한다
```

---

# 2. 전체 자동실행 구조

권장 구조는 아래와 같다.

```text
BAT 실행
→ 환경 확인
→ 프로젝트 경로 확인
→ Claude Code P0-2 실행
→ P0-2 테스트
→ 통과 시 P0-3 실행
→ P0-3 테스트
→ 통과 시 P0-4 실행
→ P0-4 테스트
→ 최종 완료보고서 저장
```

즉, 한 줄로 요약하면:

```text
실행 + 테스트 + 로그 + 다음 단계 진입 조건
```

---

# 3. 권장 폴더 구조

```text
SQM_AUTORUN/
 ├─ run_all_p0.bat
 ├─ run_p0_2.bat
 ├─ run_p0_3.bat
 ├─ run_p0_4.bat
 ├─ check_env.ps1
 ├─ write_run_log.ps1
 ├─ logs/
 ├─ prompts/
 │   ├─ GPT_ClaudeCode_P0-2_실행프롬프트.md
 │   ├─ GPT_ClaudeCode_P0-3_실행프롬프트.md
 │   └─ GPT_ClaudeCode_P0-4_실행프롬프트.md
 ├─ tests/
 │   ├─ P0-2_테스트결과.md
 │   ├─ P0-3_테스트결과.md
 │   └─ P0-4_테스트결과.md
 └─ reports/
     └─ GPT_SQM_P0_최종_완료보고서_초안.md
```

---

# 4. 실행 원칙

## 4-1. 단계별 분리 실행 원칙

절대 아래처럼 하지 않는다.

```text
P0-2 + P0-3 + P0-4를 한 번에 바로 몰아서 실행
```

반드시 아래처럼 한다.

```text
P0-2 실행 → 테스트 → 통과
P0-3 실행 → 테스트 → 통과
P0-4 실행 → 테스트 → 통과
```

## 4-2. 실패 시 원칙

```text
실패한 단계에서 즉시 중단
→ logs 폴더에 기록
→ 다음 단계로 넘어가지 않음
```

---

# 5. BAT 파일 분리 전략

## A. `run_p0_2.bat`
목적:
- Claude Code에 P0-2 실행 프롬프트 투입
- 결과 로그 저장

## B. `run_p0_3.bat`
목적:
- P0-3 write loop 실행
- 결과 로그 저장

## C. `run_p0_4.bat`
목적:
- location/update + 실행 통합 + 회귀 실행
- 결과 로그 저장

## D. `run_all_p0.bat`
목적:
- 위 3개를 순서대로 호출
- 중간 실패 시 즉시 중단
- 최종 결과 요약 저장

---

# 6. PowerShell 보조 스크립트 역할

## `check_env.ps1`
역할:
- Claude CLI 존재 여부 확인
- Python 존재 여부 확인
- 프로젝트 폴더 존재 여부 확인
- 필수 프롬프트 파일 존재 여부 확인
- logs/reports 폴더 존재 여부 확인

## `write_run_log.ps1`
역할:
- 현재 시각 기록
- 실행 단계 기록
- 성공/실패 기록
- 에러 메시지 저장
- 최종 상태 저장

---

# 7. BAT 동작 순서 설계

## 7-1. `run_all_p0.bat` 권장 흐름

```bat
@echo off
setlocal

echo [1/6] 환경 점검
powershell -ExecutionPolicy Bypass -File check_env.ps1
if errorlevel 1 goto FAIL

echo [2/6] P0-2 실행
call run_p0_2.bat
if errorlevel 1 goto FAIL

echo [3/6] P0-2 테스트 결과 확인
rem 실제 테스트 스크립트/수동 판정 결과 체크 지점

echo [4/6] P0-3 실행
call run_p0_3.bat
if errorlevel 1 goto FAIL

echo [5/6] P0-4 실행
call run_p0_4.bat
if errorlevel 1 goto FAIL

echo [6/6] 완료 로그 저장
powershell -ExecutionPolicy Bypass -File write_run_log.ps1 -Stage "P0_ALL" -Status "PASS"
goto END

:FAIL
powershell -ExecutionPolicy Bypass -File write_run_log.ps1 -Stage "P0_ALL" -Status "FAIL"
exit /b 1

:END
endlocal
pause
```

---

# 8. 단계별 BAT 예시 구조

## 8-1. `run_p0_2.bat`
```bat
@echo off
setlocal

echo [P0-2] Claude Code 실행 시작
claude --dangerously-skip-permissions --system-prompt-file "MASTER_FINAL_v867_통합완성본.md" < "prompts\GPT_ClaudeCode_P0-2_실행프롬프트.md" > "logs\p0_2_run.log" 2>&1
if errorlevel 1 exit /b 1

echo [P0-2] 완료
endlocal
exit /b 0
```

## 8-2. `run_p0_3.bat`
```bat
@echo off
setlocal

echo [P0-3] Claude Code 실행 시작
claude --dangerously-skip-permissions --system-prompt-file "MASTER_FINAL_v867_통합완성본.md" < "prompts\GPT_ClaudeCode_P0-3_실행프롬프트.md" > "logs\p0_3_run.log" 2>&1
if errorlevel 1 exit /b 1

echo [P0-3] 완료
endlocal
exit /b 0
```

## 8-3. `run_p0_4.bat`
```bat
@echo off
setlocal

echo [P0-4] Claude Code 실행 시작
claude --dangerously-skip-permissions --system-prompt-file "MASTER_FINAL_v867_통합완성본.md" < "prompts\GPT_ClaudeCode_P0-4_실행프롬프트.md" > "logs\p0_4_run.log" 2>&1
if errorlevel 1 exit /b 1

echo [P0-4] 완료
endlocal
exit /b 0
```

---

# 9. check_env.ps1 권장 항목

```powershell
$ErrorActionPreference = "Stop"

Write-Host "[CHECK] Claude CLI 확인"
$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) { throw "claude CLI not found" }

Write-Host "[CHECK] Python 확인"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "python not found" }

Write-Host "[CHECK] logs 폴더 확인"
if (-not (Test-Path ".\logs")) { New-Item -ItemType Directory -Path ".\logs" | Out-Null }

Write-Host "[CHECK] reports 폴더 확인"
if (-not (Test-Path ".\reports")) { New-Item -ItemType Directory -Path ".\reports" | Out-Null }

Write-Host "[CHECK] prompts 폴더 확인"
if (-not (Test-Path ".\prompts")) { throw "prompts folder not found" }

Write-Host "[CHECK] 필수 프롬프트 파일 확인"
$required = @(
  ".\prompts\GPT_ClaudeCode_P0-2_실행프롬프트.md",
  ".\prompts\GPT_ClaudeCode_P0-3_실행프롬프트.md",
  ".\prompts\GPT_ClaudeCode_P0-4_실행프롬프트.md"
)

foreach ($f in $required) {
  if (-not (Test-Path $f)) { throw "missing file: $f" }
}

Write-Host "[CHECK] 완료"
exit 0
```

---

# 10. write_run_log.ps1 권장 항목

```powershell
param(
    [string]$Stage,
    [string]$Status
)

$logFile = ".\logs\run_status.log"
$time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Add-Content -Path $logFile -Value "$time | STAGE=$Stage | STATUS=$Status"
Write-Host "[LOG] $time | STAGE=$Stage | STATUS=$Status"
```

---

# 11. 테스트 결과 연결 방식

자동실행 BAT는 Claude 실행까지만 하지 말고,  
각 단계 테스트 결과 파일과 연결되는 구조를 갖는 것이 좋다.

예:

```text
run_p0_2.bat 실행 후
→ tests\P0-2_테스트결과.md 갱신 또는 수동 확인
→ PASS일 때만 run_p0_3.bat 호출
```

즉, 가장 이상적인 구조는 아래다.

```text
Claude 실행 로그
+ 테스트 결과 파일
+ 최종 상태 로그
```

---

# 12. 권장 로그 파일 구조

```text
logs/
 ├─ p0_2_run.log
 ├─ p0_3_run.log
 ├─ p0_4_run.log
 ├─ run_status.log
 └─ final_summary.log
```

---

# 13. 실패 시 체크 포인트

## 실패 유형 A. claude CLI 미인식
- PATH 문제
- shell 재시작 필요
- 설치 재확인

## 실패 유형 B. BAT에서 즉시 종료
- `pause` 추가
- 로그 리다이렉션 추가
- `errorlevel` 분기 확인

## 실패 유형 C. 프롬프트 파일 경로 오류
- prompts 폴더 구조 확인
- 상대경로 기준 확인

## 실패 유형 D. Claude는 실행됐지만 단계 구분 불명확
- 로그 파일 분리
- write_run_log.ps1 사용

## 실패 유형 E. 테스트 없이 다음 단계로 진행
- run_all_p0.bat에서 테스트 확인 구간 강제 삽입

---

# 14. 권장 운영 방식

## A안. 반자동 실행
- BAT가 단계별로 실행
- 테스트는 사람이 확인
- 통과 시 다음 BAT 실행

### 장점
- 안전함
- 디버깅 쉬움

### 권장도
**가장 추천**

---

## B안. 준자동 실행
- BAT + PowerShell + 결과 파일 판정
- 특정 텍스트(PASS) 있으면 다음 단계 자동 진행

### 장점
- 반복 작업 감소

### 단점
- 테스트 결과 포맷 통일 필요

---

## C안. 완전 자동 실행
- Claude 실행
- 테스트 자동
- 결과 자동 판정
- 다음 단계 자동

### 단점
- 현재 환경에서는 오판 위험 높음

### 권장도
**지금은 비추천**

---

# 15. 루비 최종 판단

이번 BAT 구성 매뉴얼의 핵심은 아래다.

```text
문서를 아무리 잘 만들어도,
실행 구조가 없으면 반복 가능성이 없다.
BAT/PS1 구조는 P0 문서를 실제 작업 체계로 바꾸는 마지막 연결고리다.
```

---

# 16. 다음 단계 권장

다음으로 가장 자연스러운 문서는 아래다.

```text
1. GPT_SQM_자동실행_PS1_실전예시.md
2. GPT_SQM_P0_문서패키지_폴더구성안.md
3. GPT_SQM_최종실행팩_구성체크리스트.md
```

루비 권장 순서는 아래다.

```text
1) PS1 실전예시
2) 문서패키지 폴더구성안
3) 최종실행팩 구성체크리스트
```
