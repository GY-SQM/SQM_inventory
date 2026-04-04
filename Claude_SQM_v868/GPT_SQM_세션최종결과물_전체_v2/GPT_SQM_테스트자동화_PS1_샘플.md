# GPT_SQM_테스트자동화_PS1_샘플.md
생성일: 2026-04-04 18:26 (Asia/Seoul)

[질문] 테스트 자동화용 PS1 샘플 요청  
[질문의도] 다음 세션에서 바로 참조할 수 있도록 단계 테스트 자동화 스크립트 예시 제공

---

# [응답]

## test_stage.ps1 샘플

```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$Stage
)

$ErrorActionPreference = "Stop"

$logMap = @{
    "P0-2" = ".\07_LOGS\p0_2_run.log"
    "P0-3" = ".\07_LOGS\p0_3_run.log"
    "P0-4" = ".\07_LOGS\p0_4_run.log"
    "P2"   = ".\07_LOGS\p2_run.log"
    "Patch2" = ".\07_LOGS\patch2_run.log"
    "P3"   = ".\07_LOGS\p3_run.log"
    "Patch3" = ".\07_LOGS\patch3_run.log"
    "P4"   = ".\07_LOGS\p4_run.log"
    "Patch4" = ".\07_LOGS\patch4_run.log"
    "P5"   = ".\07_LOGS\p5_run.log"
    "Patch5" = ".\07_LOGS\patch5_run.log"
}

$resultMap = @{
    "P0-2" = ".\08_RESULTS\p0_2_result.json"
    "P0-3" = ".\08_RESULTS\p0_3_result.json"
    "P0-4" = ".\08_RESULTS\p0_4_result.json"
    "P2"   = ".\08_RESULTS\p2_result.json"
    "Patch2" = ".\08_RESULTS\patch2_result.json"
    "P3"   = ".\08_RESULTS\p3_result.json"
    "Patch3" = ".\08_RESULTS\patch3_result.json"
    "P4"   = ".\08_RESULTS\p4_result.json"
    "Patch4" = ".\08_RESULTS\patch4_result.json"
    "P5"   = ".\08_RESULTS\p5_result.json"
    "Patch5" = ".\08_RESULTS\patch5_result.json"
}

$logFile = $logMap[$Stage]
$resultFile = $resultMap[$Stage]
$started = Get-Date

if (-not (Test-Path $logFile)) {
    $result = @{
        stage = $Stage
        status = "FAIL"
        started_at = $started.ToString("yyyy-MM-dd HH:mm:ss")
        ended_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        log_file = $logFile
        checks = @(
            @{name="log_exists"; status="FAIL"}
        )
        notes = @("log file missing")
    }
    $result | ConvertTo-Json -Depth 5 | Set-Content $resultFile -Encoding UTF8
    exit 1
}

$content = Get-Content $logFile -Raw
$fatalPatterns = @("Traceback","Exception","Fatal","ModuleNotFoundError","RuntimeError","FAILED")
$warningPatterns = @("warning","deprecated","fallback","manual check")

$fatalFound = $false
foreach ($p in $fatalPatterns) {
    if ($content -match [regex]::Escape($p)) { $fatalFound = $true; break }
}

$warningFound = $false
foreach ($p in $warningPatterns) {
    if ($content -match [regex]::Escape($p)) { $warningFound = $true; break }
}

$status = "PASS"
$notes = @()
$checks = @(
    @{name="log_exists"; status="PASS"}
)

if ($fatalFound) {
    $status = "FAIL"
    $checks += @{name="fatal_error_scan"; status="FAIL"}
    $notes += "fatal keyword found"
} else {
    $checks += @{name="fatal_error_scan"; status="PASS"}
}

if ($warningFound -and $status -eq "PASS") {
    $status = "CONDITIONAL_PASS"
    $checks += @{name="warning_scan"; status="CONDITIONAL_PASS"}
    $notes += "warning keyword found"
} else {
    $checks += @{name="warning_scan"; status="PASS"}
}

$result = @{
    stage = $Stage
    status = $status
    started_at = $started.ToString("yyyy-MM-dd HH:mm:ss")
    ended_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    log_file = $logFile
    checks = $checks
    notes = $notes
}

$result | ConvertTo-Json -Depth 5 | Set-Content $resultFile -Encoding UTF8

if ($status -eq "FAIL") { exit 1 }
if ($status -eq "CONDITIONAL_PASS") { exit 2 }
exit 0
```

---

## run_all_p0.ps1 연결 예시

```powershell
& ".\run_stage.ps1" -Stage "P0-2"
& ".\test_stage.ps1" -Stage "P0-2"
if ($LASTEXITCODE -eq 1) { throw "P0-2 failed" }

& ".\run_stage.ps1" -Stage "P0-3"
& ".\test_stage.ps1" -Stage "P0-3"
if ($LASTEXITCODE -eq 1) { throw "P0-3 failed" }
```

---

# 1줄 핵심

```text
run → log → test_stage → result.json → 다음 단계 판정
```
