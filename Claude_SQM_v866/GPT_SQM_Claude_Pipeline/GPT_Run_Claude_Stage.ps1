param(
    [Parameter(Mandatory = $true)]
    [string]$StageId,

    [Parameter(Mandatory = $true)]
    [string]$PromptFile,

    [string]$ProjectRoot = ".",
    [string]$ReportsRoot = "reports/claude_runs",
    [switch]$SkipPrevCheck
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host "[INFO] $msg" -ForegroundColor Cyan
}

function Write-WarnMsg($msg) {
    Write-Host "[WARN] $msg" -ForegroundColor Yellow
}

function Write-ErrMsg($msg) {
    Write-Host "[ERROR] $msg" -ForegroundColor Red
}

function Resolve-FullPath([string]$BaseDir, [string]$PathText) {
    if ([System.IO.Path]::IsPathRooted($PathText)) {
        return [System.IO.Path]::GetFullPath($PathText)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $BaseDir $PathText))
}

function Get-PrevStageId([string]$Current) {
    if ($Current -notmatch '^B(\d{2})$') {
        return $null
    }

    $num = [int]$Matches[1]
    if ($num -le 0) {
        return $null
    }

    return ('B{0:D2}' -f ($num - 1))
}

function Assert-CommandExists([string]$CommandName) {
    $cmd = Get-Command $CommandName -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Required command not found: $CommandName"
    }
}

function Ensure-Dir([string]$DirPath) {
    if (-not (Test-Path -LiteralPath $DirPath)) {
        New-Item -ItemType Directory -Force -Path $DirPath | Out-Null
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ResolvedProjectRoot = Resolve-FullPath -BaseDir $ScriptDir -PathText $ProjectRoot
$ResolvedPromptFile = Resolve-FullPath -BaseDir $ResolvedProjectRoot -PathText $PromptFile
$ResolvedReportsRoot = Resolve-FullPath -BaseDir $ResolvedProjectRoot -PathText $ReportsRoot
$StageReportDir = Join-Path $ResolvedReportsRoot $StageId
$StatusFile = Join-Path $StageReportDir 'status.txt'
$SummaryFile = Join-Path $StageReportDir 'runner_summary.txt'
$RunnerLogFile = Join-Path $StageReportDir 'runner_log.txt'
$CommandFile = Join-Path $StageReportDir 'runner_command.txt'
$PrevStageId = Get-PrevStageId $StageId

Write-Info "StageId      : $StageId"
Write-Info "ProjectRoot  : $ResolvedProjectRoot"
Write-Info "PromptFile   : $ResolvedPromptFile"
Write-Info "ReportsRoot  : $ResolvedReportsRoot"

if (-not (Test-Path -LiteralPath $ResolvedProjectRoot)) {
    throw "Project root not found: $ResolvedProjectRoot"
}

if (-not (Test-Path -LiteralPath $ResolvedPromptFile)) {
    throw "Prompt file not found: $ResolvedPromptFile"
}

Assert-CommandExists -CommandName 'claude'
Ensure-Dir -DirPath $ResolvedReportsRoot
Ensure-Dir -DirPath $StageReportDir

if (-not $SkipPrevCheck -and $PrevStageId) {
    $PrevStatusFile = Join-Path (Join-Path $ResolvedReportsRoot $PrevStageId) 'status.txt'

    if (-not (Test-Path -LiteralPath $PrevStatusFile)) {
        throw "Previous stage status file not found: $PrevStatusFile"
    }

    $PrevStatus = (Get-Content -LiteralPath $PrevStatusFile -ErrorAction Stop | Select-Object -First 1).Trim().ToUpperInvariant()
    if ($PrevStatus -ne 'PASS') {
        throw "Previous stage $PrevStageId is not PASS. Current value: $PrevStatus"
    }

    Write-Info "Previous stage check passed: $PrevStageId = PASS"
} elseif ($SkipPrevCheck) {
    Write-WarnMsg "Previous stage status check skipped by option."
} else {
    Write-Info "No previous stage check needed for $StageId"
}

$TimeStamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$ClaudeArgs = @(
    '--dangerously-skip-permissions',
    '--system-prompt-file', $ResolvedPromptFile
)

$DisplayCommand = 'claude --dangerously-skip-permissions --system-prompt-file "' + $ResolvedPromptFile + '"'
Set-Content -LiteralPath $CommandFile -Value $DisplayCommand -Encoding UTF8

Push-Location $ResolvedProjectRoot
try {
    Write-Info "Running Claude Code command..."
    Write-Info $DisplayCommand

    "[$TimeStamp] START $StageId" | Out-File -LiteralPath $RunnerLogFile -Encoding UTF8
    "[$TimeStamp] CMD   $DisplayCommand" | Out-File -LiteralPath $RunnerLogFile -Encoding UTF8 -Append

    $output = & claude @ClaudeArgs 2>&1
    $exitCode = $LASTEXITCODE

    if ($null -ne $output) {
        $output | Out-File -LiteralPath $RunnerLogFile -Encoding UTF8 -Append
    }

    $EndStamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "[$EndStamp] END   $StageId / ExitCode=$exitCode" | Out-File -LiteralPath $RunnerLogFile -Encoding UTF8 -Append

    if ($exitCode -ne 0) {
        Set-Content -LiteralPath $StatusFile -Value 'FAIL' -Encoding UTF8
        @(
            "StageId=$StageId",
            "Result=FAIL",
            "Reason=Claude command exited with non-zero exit code",
            "ExitCode=$exitCode",
            "Command=$DisplayCommand",
            "LogFile=$RunnerLogFile"
        ) | Set-Content -LiteralPath $SummaryFile -Encoding UTF8

        throw "Claude command failed with exit code $exitCode"
    }

    if (-not (Test-Path -LiteralPath $StatusFile)) {
        Write-WarnMsg "Stage status.txt was not created by Claude. Writing provisional PASS based on runner exit code."
        Set-Content -LiteralPath $StatusFile -Value 'PASS' -Encoding UTF8
    }

    $StageStatus = (Get-Content -LiteralPath $StatusFile | Select-Object -First 1).Trim().ToUpperInvariant()
    @(
        "StageId=$StageId",
        "Result=$StageStatus",
        "ExitCode=$exitCode",
        "Command=$DisplayCommand",
        "PromptFile=$ResolvedPromptFile",
        "RunnerLog=$RunnerLogFile"
    ) | Set-Content -LiteralPath $SummaryFile -Encoding UTF8

    if ($StageStatus -eq 'PASS') {
        Write-Host "[PASS] $StageId passed. You may proceed to the next stage." -ForegroundColor Green
        exit 0
    }
    else {
        Write-ErrMsg "$StageId ended with status: $StageStatus"
        exit 2
    }
}
finally {
    Pop-Location
}
