# tools/uninstall_cleanup_scheduler.ps1
# SQM v9.0.6 — Windows 스케줄러에서 audit_log cleanup 작업 제거
#
# 사용:
#   powershell -ExecutionPolicy Bypass -File tools/uninstall_cleanup_scheduler.ps1

$ErrorActionPreference = "Stop"

$TaskName = "SQM Audit Cleanup"

$existing = schtasks /Query /TN $TaskName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[INFO] 작업 제거: $TaskName"
    schtasks /Delete /TN $TaskName /F | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[ERR] schtasks /Delete 실패 (exit $LASTEXITCODE)"
        exit 1
    }
    Write-Host "[OK] 제거 완료"
} else {
    Write-Host "[INFO] 등록된 작업 없음 (skip): $TaskName"
}
