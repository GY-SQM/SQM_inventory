# SQM v867 Master Runner - PowerShell
# UTF-8 설정
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

$LogDir = Join-Path $ProjectDir "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogFile = Join-Path $LogDir "run_log.txt"

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $msg" | Add-Content -Path $LogFile -Encoding UTF8
    Write-Host $msg
}

Write-Host "============================================"
Write-Host "  SQM v867 Master Runner (PowerShell)"
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "============================================"
Write-Host ""

# ===== Pre-Test =====
Write-Log "[Pre-Test] 시작..."

# 1. .env
if (-not (Test-Path ".env")) {
    Write-Log "[FAIL] .env 없음"
    exit 1
}
Write-Host "  [OK] .env 존재"

# 2. MASTER
$MasterFile = "MASTER_FINAL_v867_통합완성본.md"
if (-not (Test-Path $MasterFile)) {
    Write-Log "[FAIL] MASTER 파일 없음"
    exit 1
}
Write-Host "  [OK] MASTER 파일 존재"

# 3. Bridge
if (-not (Test-Path "scripts\telegram_bridge.py")) {
    Write-Log "[FAIL] bridge 없음"
    exit 1
}
Write-Host "  [OK] Bridge 파일 존재"

# 4. Backend 테스트
Write-Host "  [TEST] Backend 테스트..."
$testResult = python -m pytest tests/stage_gates/ -q --tb=line 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "[FAIL] Backend 테스트 실패"
    Write-Host $testResult
    exit 1
}
Write-Host "  [OK] Backend 테스트 통과"

# 5. API 로드 확인
python -c "import sys; sys.path.insert(0,'.'); from react_api.main import app; print(f'  [OK] API routes: {len([r for r in app.routes if hasattr(r,`"path`")])}개')" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Log "[FAIL] API 로드 실패"
    exit 1
}

Write-Log "[Pre-Test] 모두 통과"
Write-Host ""

# ===== 실행 =====
Write-Host "실행 모드:"
Write-Host "  1. Claude 직접 실행"
Write-Host "  2. Telegram Bridge 실행"
Write-Host "  3. 종료"
$mode = Read-Host "선택 (1/2/3)"

switch ($mode) {
    "1" {
        Write-Log "Claude 직접 실행"
        & claude --dangerously-skip-permissions --file $MasterFile
    }
    "2" {
        Write-Log "Telegram Bridge 실행"
        & python scripts\telegram_bridge.py
    }
    default {
        Write-Host "종료."
    }
}

Write-Log "실행 완료"
