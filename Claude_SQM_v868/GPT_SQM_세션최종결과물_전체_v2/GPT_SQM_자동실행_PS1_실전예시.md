# GPT_SQM_자동실행_PS1_실전예시.md
생성일: 2026-04-04 16:20 (Asia/Seoul)

---

## [질문]
계속 이어서 진행해서 **자동실행 PS1 실전예시** 문서를 작성

## [질문의도]
앞서 만든 BAT 구성 매뉴얼을 실제로 구현할 수 있도록  
Windows PowerShell 기준의 **실전 예시 스크립트 / 단계 분기 / 로그 기록 / 실패 처리 방식**을 정리한다.

---

# [응답]

# 1. 이 문서의 목적

이 문서는 아래를 해결하기 위한 것이다.

```text
1. BAT만으로 부족한 조건 분기와 로그 처리를 PowerShell로 보완
2. P0-2 / P0-3 / P0-4 실행을 보다 안정적으로 제어
3. 실패 시 즉시 중단하고 정확한 단계 로그를 남김
4. 수동 확인과 반자동 실행을 함께 지원
```

---

# 2. PowerShell을 쓰는 이유

BAT는 간단하지만 아래 한계가 있다.

- 조건 분기가 거칠다
- 오류 메시지 정리가 약하다
- 파일/로그 다루기가 불편하다
- 결과 상태 파일 관리가 불편하다

PowerShell은 아래 장점이 있다.

```text
- 에러 핸들링이 좋다
- 파일/폴더 검사에 강하다
- 로그 남기기 쉽다
- 단계 상태 파일 만들기 쉽다
```

---

# 3. 권장 파일 구성

```text
SQM_AUTORUN/
 ├─ run_all_p0.ps1
 ├─ run_stage.ps1
 ├─ check_env.ps1
 ├─ write_run_log.ps1
 ├─ prompts/
 │   ├─ GPT_ClaudeCode_P0-2_실행프롬프트.md
 │   ├─ GPT_ClaudeCode_P0-3_실행프롬프트.md
 │   └─ GPT_ClaudeCode_P0-4_실행프롬프트.md
 ├─ logs/
 ├─ results/
 └─ reports/
```

---

# 4. 기본 실행 원칙

## 4-1. 단계 실행 원칙
반드시 아래 순서를 지킨다.

```text
P0-2 실행
→ 테스트 확인
→ P0-3 실행
→ 테스트 확인
→ P0-4 실행
→ 테스트 확인
→ 최종 완료보고서
```

## 4-2. 실패 시 원칙
```text
- 실패 즉시 중단
- 현재 단계 기록
- 로그 저장
- 다음 단계 진행 금지
```

---

# 5. run_all_p0.ps1 실전 예시

```powershell
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Write-StageLog {
    param(
        [string]$Stage,
        [string]$Status,
        [string]$Message = ""
    )
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$time | STAGE=$Stage | STATUS=$Status | MESSAGE=$Message"
    Add-Content -Path ".\logs\run_status.log" -Value $line
    Write-Host $line
}

function Confirm-TestResult {
    param(
        [string]$StageName
    )
    Write-Host ""
    Write-Host "[$StageName] 테스트 결과를 확인하세요."
    $answer = Read-Host "PASS 입력 시 다음 단계 진행 / 그 외는 중단"
    if ($answer -ne "PASS") {
        throw "$StageName test not confirmed"
    }
}

try {
    if (-not (Test-Path ".\logs")) { New-Item -ItemType Directory -Path ".\logs" | Out-Null }
    if (-not (Test-Path ".\results")) { New-Item -ItemType Directory -Path ".\results" | Out-Null }

    Write-StageLog -Stage "ENV" -Status "START" -Message "환경 점검 시작"
    & ".\check_env.ps1"
    Write-StageLog -Stage "ENV" -Status "PASS" -Message "환경 점검 완료"

    Write-StageLog -Stage "P0-2" -Status "START" -Message "Claude 실행"
    & ".\run_stage.ps1" -Stage "P0-2"
    Write-StageLog -Stage "P0-2" -Status "DONE" -Message "Claude 실행 완료"
    Confirm-TestResult -StageName "P0-2"
    Write-StageLog -Stage "P0-2" -Status "PASS" -Message "테스트 확인 완료"

    Write-StageLog -Stage "P0-3" -Status "START" -Message "Claude 실행"
    & ".\run_stage.ps1" -Stage "P0-3"
    Write-StageLog -Stage "P0-3" -Status "DONE" -Message "Claude 실행 완료"
    Confirm-TestResult -StageName "P0-3"
    Write-StageLog -Stage "P0-3" -Status "PASS" -Message "테스트 확인 완료"

    Write-StageLog -Stage "P0-4" -Status "START" -Message "Claude 실행"
    & ".\run_stage.ps1" -Stage "P0-4"
    Write-StageLog -Stage "P0-4" -Status "DONE" -Message "Claude 실행 완료"
    Confirm-TestResult -StageName "P0-4"
    Write-StageLog -Stage "P0-4" -Status "PASS" -Message "테스트 확인 완료"

    Write-StageLog -Stage "P0_ALL" -Status "PASS" -Message "전체 단계 완료"
}
catch {
    Write-StageLog -Stage "P0_ALL" -Status "FAIL" -Message $_.Exception.Message
    throw
}
```

---

# 6. run_stage.ps1 실전 예시

```powershell
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("P0-2","P0-3","P0-4")]
    [string]$Stage
)

$ErrorActionPreference = "Stop"

$promptMap = @{
    "P0-2" = ".\prompts\GPT_ClaudeCode_P0-2_실행프롬프트.md"
    "P0-3" = ".\prompts\GPT_ClaudeCode_P0-3_실행프롬프트.md"
    "P0-4" = ".\prompts\GPT_ClaudeCode_P0-4_실행프롬프트.md"
}

$logMap = @{
    "P0-2" = ".\logs\p0_2_run.log"
    "P0-3" = ".\logs\p0_3_run.log"
    "P0-4" = ".\logs\p0_4_run.log"
}

$promptFile = $promptMap[$Stage]
$logFile = $logMap[$Stage]
$masterFile = ".\MASTER_FINAL_v867_통합완성본.md"

if (-not (Test-Path $promptFile)) {
    throw "Prompt file not found: $promptFile"
}

if (-not (Test-Path $masterFile)) {
    throw "MASTER file not found: $masterFile"
}

$cmd = "claude --dangerously-skip-permissions --system-prompt-file `"$masterFile`" < `"$promptFile`""
$fullCmd = "cmd /c $cmd > `"$logFile`" 2>&1"

Write-Host "[$Stage] 실행 시작"
Invoke-Expression $fullCmd

if ($LASTEXITCODE -ne 0) {
    throw "$Stage execution failed. See log: $logFile"
}

Write-Host "[$Stage] 실행 완료"
```

---

# 7. check_env.ps1 실전 예시

```powershell
$ErrorActionPreference = "Stop"

$requiredFolders = @(".\logs", ".\results", ".\reports", ".\prompts")
foreach ($folder in $requiredFolders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder | Out-Null
    }
}

$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) { throw "claude CLI not found" }

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "python not found" }

$requiredFiles = @(
    ".\MASTER_FINAL_v867_통합완성본.md",
    ".\prompts\GPT_ClaudeCode_P0-2_실행프롬프트.md",
    ".\prompts\GPT_ClaudeCode_P0-3_실행프롬프트.md",
    ".\prompts\GPT_ClaudeCode_P0-4_실행프롬프트.md"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        throw "required file missing: $file"
    }
}

Write-Host "[CHECK] environment ready"
```

---

# 8. 반자동 운영 방식 예시

현재 가장 추천하는 방식은 **반자동**이다.

```text
1. PowerShell이 Claude 실행
2. 로그 저장
3. 사람(사용자)이 테스트 체크리스트 확인
4. PASS 입력 시 다음 단계 자동 진행
```

이 방식이 좋은 이유:

- 오류를 초기에 잡기 쉽다
- Claude가 잘못 고쳐도 다음 단계 확산을 막을 수 있다
- 실무 데이터 손상 위험이 낮다

---

# 9. 준자동 운영 방식 예시

반자동보다 조금 더 자동화하고 싶으면 아래처럼 할 수 있다.

```text
1. 테스트 결과 파일에 PASS/FAIL 저장
2. PowerShell이 그 파일을 읽음
3. PASS이면 다음 단계 진행
4. FAIL이면 중단
```

예시:

```powershell
function Read-TestStatus {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "test result file not found: $Path"
    }

    $content = Get-Content $Path -Raw
    if ($content -match "PASS") {
        return $true
    }
    return $false
}
```

하지만 이 방식은 **테스트 결과 문서 형식을 통일해야** 한다.

---

# 10. 권장 로그 구조

```text
logs/
 ├─ run_status.log
 ├─ p0_2_run.log
 ├─ p0_3_run.log
 ├─ p0_4_run.log
 ├─ p0_2_test.log
 ├─ p0_3_test.log
 ├─ p0_4_test.log
 └─ final_summary.log
```

## 최소 기록 항목
- 시각
- 단계명
- 상태
- 에러 메시지
- 로그 파일 경로

---

# 11. 운영 시 자주 생기는 문제와 대응

## 문제 1. claude 명령이 PS1에서 안 잡힘
대응:
- PATH 확인
- shell 재시작
- `Get-Command claude` 확인

## 문제 2. `< prompt.md` 리다이렉션이 PowerShell에서 꼬임
대응:
- `cmd /c`로 감싸서 실행
- 위 예시처럼 `Invoke-Expression` 사용

## 문제 3. 로그는 남는데 exit code가 불명확
대응:
- `$LASTEXITCODE` 확인
- 실패 시 명시적으로 throw

## 문제 4. 사용자가 테스트 안 했는데 다음 단계로 넘어감
대응:
- `Read-Host` 방식으로 확인 단계 강제
- 또는 PASS 파일 읽기 방식 적용

## 문제 5. 프로젝트 경로가 바뀌어 스크립트가 깨짐
대응:
- `Set-Location $root`
- 상대경로 기준 통일

---

# 12. 권장 운영 모드 최종 정리

| 운영 모드 | 설명 | 권장도 |
|---|---|---|
| 수동 | 단계별 명령 직접 입력 | 낮음 |
| 반자동 | PS1 실행 + 사람 테스트 확인 | 매우 높음 |
| 준자동 | 테스트 결과 파일 판독 후 자동 진행 | 중간 |
| 완전자동 | Claude+테스트+판정 모두 자동 | 현재는 비권장 |

---

# 13. 루비 최종 판단

이번 PS1 실전예시의 핵심은 아래다.

```text
BAT는 시작 버튼,
PS1은 실제 제어 엔진이다.
실제 운영 안정성을 생각하면 BAT보다 PS1 중심으로 가는 것이 훨씬 낫다.
```

---

# 14. 다음 단계 권장

다음으로 가장 자연스러운 문서는 아래다.

```text
1. GPT_SQM_P0_문서패키지_폴더구성안.md
2. GPT_SQM_최종실행팩_구성체크리스트.md
3. GPT_SQM_실행패키지_배포순서_안내문.md
```

루비 권장 순서는 아래다.

```text
1) 문서패키지 폴더구성안
2) 최종실행팩 구성체크리스트
3) 실행패키지 배포순서 안내문
```
