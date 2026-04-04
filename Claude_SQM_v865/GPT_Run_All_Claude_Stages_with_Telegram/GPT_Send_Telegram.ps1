param(
    [Parameter(Mandatory = $true)]
    [string]$BotToken,

    [Parameter(Mandatory = $true)]
    [string]$ChatId,

    [Parameter(Mandatory = $true)]
    [string]$Message
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($BotToken) -or $BotToken -eq 'PUT_YOUR_BOT_TOKEN_HERE') {
    Write-Host '[WARN] TELEGRAM_BOT_TOKEN 값이 설정되지 않았습니다. 메시지 전송을 건너뜁니다.'
    exit 0
}

if ([string]::IsNullOrWhiteSpace($ChatId) -or $ChatId -eq 'PUT_YOUR_CHAT_ID_HERE') {
    Write-Host '[WARN] TELEGRAM_CHAT_ID 값이 설정되지 않았습니다. 메시지 전송을 건너뜁니다.'
    exit 0
}

$uri = "https://api.telegram.org/bot$BotToken/sendMessage"
$body = @{
    chat_id = $ChatId
    text    = $Message
}

try {
    Invoke-RestMethod -Method Post -Uri $uri -Body $body | Out-Null
    Write-Host "[OK] Telegram message sent: $Message"
    exit 0
}
catch {
    Write-Host "[WARN] Telegram send failed: $($_.Exception.Message)"
    exit 0
}
