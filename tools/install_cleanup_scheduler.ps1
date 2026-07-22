# tools/install_cleanup_scheduler.ps1
# SQM v9.0.6 — Windows 스케줄러에 audit_log cleanup 작업 등록
#
# 기본: 매주 일요일 오전 3시 (SQM 가동 시간 피함)
# 변경 가능 환경변수:
#   SCHEDULE_DAY   : MON/TUE/WED/THU/FRI/SAT/SUN (default SUN)
#   SCHEDULE_TIME  : HH:MM 24h (default 03:00)
#   DAYS           : 보관 기간 (default 30)
#   PYTHON_EXE     : Python 경로 (default C:\Python314\python.exe)
#
# 사용:
#   powershell -ExecutionPolicy Bypass -File tools/install_cleanup_scheduler.ps1
#   $env:SCHEDULE_DAY="MON"; powershell -ExecutionPolicy Bypass -File tools/install_cleanup_scheduler.ps1

$ErrorActionPreference = "Stop"

$TaskName = "SQM Audit Cleanup"
$ScriptDir = $PSScriptRoot
$ScriptPath = Join-Path $ScriptDir "cleanup_audit_job.py"

# Python 실행 파일 결정
$PythonExe = if ($env:PYTHON_EXE) {
    $env:PYTHON_EXE
} elseif (Test-Path "C:\Python314\python.exe") {
    "C:\Python314\python.exe"
} else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $cmd.Source } else { $null }
}

if (-not $PythonExe) {
    Write-Error "[ERR] Python 실행 파일을 찾을 수 없습니다. PYTHON_EXE 환경변수 설정 필요."
    exit 1
}
if (-not (Test-Path $PythonExe)) {
    Write-Error "[ERR] Python 경로 없음: $PythonExe"
    exit 1
}
if (-not (Test-Path $ScriptPath)) {
    Write-Error "[ERR] 작업 스크립트 없음: $ScriptPath"
    exit 1
}

# 스케줄 파라미터
$ScheduleDay  = if ($env:SCHEDULE_DAY)  { $env:SCHEDULE_DAY }  else { "SUN" }
$ScheduleTime = if ($env:SCHEDULE_TIME) { $env:SCHEDULE_TIME } else { "03:00" }
$Days         = if ($env:DAYS)          { [int]$env:DAYS }     else { 30 }

# 요일 검증
$validDays = @("MON","TUE","WED","THU","FRI","SAT","SUN")
if ($validDays -notcontains $ScheduleDay) {
    Write-Error "[ERR] SCHEDULE_DAY=$ScheduleDay (허용: $($validDays -join ','))"
    exit 1
}
# 시간 형식 검증 (간단한 HH:MM 체크)
if ($ScheduleTime -notmatch '^\d{2}:\d{2}$') {
    Write-Error "[ERR] SCHEDULE_TIME=$ScheduleTime (HH:MM 형식)"
    exit 1
}

# 기존 작업 제거 (idempotent)
$existing = schtasks /Query /TN $TaskName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[INFO] 기존 작업 제거: $TaskName"
    schtasks /Delete /TN $TaskName /F | Out-Null
}

# 작업 등록
$arg = "`"$PythonExe`" `"$ScriptPath`" $Days"
Write-Host "[INFO] 작업 등록: $TaskName"
Write-Host "[INFO]   스케줄: 매주 $ScheduleDay $ScheduleTime"
Write-Host "[INFO]   명령: $arg"

schtasks /Create /SC WEEKLY /D $ScheduleDay /TN $TaskName `
    /TR $arg /ST $ScheduleTime /F | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERR] schtasks /Create 실패 (exit $LASTEXITCODE)"
    exit 1
}

Write-Host ""
Write-Host "[OK] 등록 완료. 확인 명령:"
Write-Host "  schtasks /Query /TN `"$TaskName`" /V /FO LIST"
Write-Host ""
Write-Host "[OK] 제거 명령:"
Write-Host "  powershell -ExecutionPolicy Bypass -File tools/uninstall_cleanup_scheduler.ps1"
