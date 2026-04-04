[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"
$BOT = "8665850610:AAFx9Jcti2_jCKqjs1ZxFcHd18FtywO5-h8"
$CID = "538125119"

$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskDir = Join-Path $base "auto_tasks"

function Send-TG($msg) {
    try {
        $body = @{ chat_id = $CID; text = $msg } | ConvertTo-Json -Compress
        Invoke-RestMethod -Uri "https://api.telegram.org/bot$BOT/sendMessage" -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) | Out-Null
    } catch { Write-Host "TG send failed: $_" }
}

Set-Location $base
Write-Host "Working dir: $base"

$startTime = Get-Date -Format "yyyy-MM-dd HH:mm"
Write-Host "============================================"
Write-Host "  SQM v865 P2 Overnight Refactoring"
Write-Host "  Start: $startTime"
Write-Host "============================================"
Send-TG "[SQM] P2 overnight started - $startTime"

$tasks = @(
    @{ name = "outbound_handlers.py"; file = "task1_outbound_handlers.md" },
    @{ name = "advanced_dialogs_mixin.py"; file = "task2_advanced_dialogs.md" },
    @{ name = "except cleanup"; file = "task3_except_cleanup.md" },
    @{ name = "SQL consolidation"; file = "task4_sql_consolidation.md" },
    @{ name = "after() cleanup"; file = "task5_after_cleanup.md" }
)

for ($i = 0; $i -lt $tasks.Count; $i++) {
    $num = $i + 1
    $total = $tasks.Count
    $t = $tasks[$i]
    $taskFile = Join-Path $taskDir $t.file

    Write-Host ""
    Write-Host "[$num/$total] $($t.name) starting..."
    Write-Host "Task file: $taskFile"
    Write-Host "----------------------------------------"

    if (Test-Path $taskFile) {
        & claude --dangerously-skip-permissions --system-prompt-file "$taskFile" -p "start"
    } else {
        Write-Host "ERROR: File not found: $taskFile"
    }

    $doneTime = Get-Date -Format "HH:mm"
    Send-TG "[SQM] Task $num/$total DONE - $($t.name) ($doneTime)"
    Write-Host "[$num/$total] Done: $doneTime"
}

$endTime = Get-Date -Format "yyyy-MM-dd HH:mm"
Send-TG "[SQM] ALL $($tasks.Count) TASKS COMPLETE! $endTime"
Write-Host ""
Write-Host "============================================"
Write-Host "  All done: $endTime"
Write-Host "============================================"
Read-Host "Press Enter to exit"
