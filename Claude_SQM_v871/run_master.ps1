# SQM v869 AutoPilot Launcher (PowerShell)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

$MasterFile = "MASTER.md"
$CLAUDE = (Get-Command claude -ErrorAction SilentlyContinue).Source
if (-not $CLAUDE) { $CLAUDE = "$env:APPDATA\npm\claude.cmd" }
if (-not (Test-Path $CLAUDE)) { $CLAUDE = "$env:USERPROFILE\.local\bin\claude.exe" }

$LogDir = Join-Path $ProjectDir "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SQM v869 AutoPilot Launcher"
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "============================================"
Write-Host ""

# ===== Pre-Test =====
$checks = @(
    @{ Path = "react_api\main.py";          Label = "react_api" },
    @{ Path = ".env";                        Label = ".env" },
    @{ Path = "scripts\telegram_bridge.py";  Label = "telegram_bridge" },
    @{ Path = "scripts\watchdog.py";         Label = "watchdog" },
    @{ Path = $MasterFile;                   Label = "MASTER.md" }
)

foreach ($c in $checks) {
    if (Test-Path $c.Path) {
        Write-Host "  [OK] $($c.Label)" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $($c.Label) not found" -ForegroundColor Red
        exit 1
    }
}

try {
    & $CLAUDE --version 2>$null | Out-Null
    Write-Host "  [OK] Claude Code" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] Claude not found: $CLAUDE" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[ALL PRE-TESTS PASSED]" -ForegroundColor Green
Write-Host ""

# ===== 실행 모드 =====
Write-Host "============================================"
Write-Host "  1. Telegram Bridge + Claude (창 2개)"
Write-Host "  2. Claude 직접 실행 (창 1개, 알림 없음)"
Write-Host "  3. 종료"
Write-Host "============================================"
$mode = Read-Host "선택 (1/2/3, 기본=2)"
if ([string]::IsNullOrWhiteSpace($mode)) { $mode = "2" }

switch ($mode) {
    "1" {
        Write-Host ""
        Write-Host "[STEP 1] Claude Code 새 창 실행..." -ForegroundColor Yellow
        Start-Process -FilePath $CLAUDE -ArgumentList "--dangerously-skip-permissions" -WorkingDirectory $ProjectDir
        Start-Sleep -Seconds 3
        Write-Host "[STEP 2] Watchdog + Bridge 시작..." -ForegroundColor Yellow
        & python "$ProjectDir\scripts\watchdog.py"
    }
    "2" {
        Write-Host ""
        Write-Host "Claude Code 직접 실행..." -ForegroundColor Yellow
        & $CLAUDE --dangerously-skip-permissions -p "MASTER.md 파일을 읽고 S1부터 S12까지 중단 없이 모두 실행하라. 질문하지 말고 끝까지 진행하라. 각 단계 완료 시 반드시 python scripts/telegram_notify.py 로 Telegram 알림을 보내라."
    }
    default {
        Write-Host "종료."
    }
}

Write-Host "Done: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
