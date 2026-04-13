param(
    [Parameter(Mandatory=$true)][string]$StepId,
    [Parameter(Mandatory=$true)][string]$TaskFile
)

Write-Host "========================================"
Write-Host "[SQM AGENT TEAM] START STEP: $StepId"
Write-Host "========================================"

$logDir = "logs"
if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "$StepId`_$timestamp.log"

Write-Host "[INFO] Task File: $TaskFile"
Write-Host "[INFO] Log File : $logFile"

$cmd = "claude --dangerously-skip-permissions --system-prompt-file `"$TaskFile`""
Write-Host "[INFO] Running: $cmd"

powershell -Command $cmd *>&1 | Tee-Object -FilePath $logFile

Write-Host "[INFO] STEP FINISHED: $StepId"
