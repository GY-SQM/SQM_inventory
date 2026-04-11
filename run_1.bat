@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "F:\program\Sqm jaego\Claude_SQM_v870"

set "ROOT=F:\program\Sqm jaego\Claude_SQM_v870"
set "WEB=%ROOT%\web"
set "MENU=%WEB%\src\components\MenuBar.jsx"
set "APP=%WEB%\src\App.jsx"
set "TMPPS1=%TEMP%\gpt_v870_menu_patch_and_run_temp.ps1"

echo.
echo [STEP] 경로 확인
if not exist "%WEB%\package.json" (
    echo [ERROR] package.json not found: %WEB%\package.json
    pause
    exit /b 1
)
if not exist "%MENU%" (
    echo [ERROR] MenuBar.jsx not found: %MENU%
    pause
    exit /b 1
)
if not exist "%APP%" (
    echo [ERROR] App.jsx not found: %APP%
    pause
    exit /b 1
)

echo.
echo [STEP] 임시 PowerShell 스크립트 생성

> "%TMPPS1%" (
 echo $ErrorActionPreference = 'Stop'
 echo function Backup-File([string]$path^) {
 echo   $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
 echo   $backup = "$path.bak_$stamp"
 echo   Copy-Item -LiteralPath $path -Destination $backup -Force
 echo   Write-Host "  백업 생성: $backup" -ForegroundColor DarkGray
 echo }
 echo function Replace-Regex {
 echo   param([string]$Text,[string]$Pattern,[string]$Replacement,[string]$Name)
 echo   $newText = [regex]::Replace($Text, $Pattern, $Replacement, [System.Text.RegularExpressions.RegexOptions]::Singleline)
 echo   if ($newText -eq $Text^) { Write-Host "  SKIP: $Name" -ForegroundColor Yellow } else { Write-Host "  PATCH: $Name" -ForegroundColor Green }
 echo   return $newText
 echo }
 echo $root = 'F:\program\Sqm jaego\Claude_SQM_v870'
 echo $web = Join-Path $root 'web'
 echo $menuPath = Join-Path $web 'src\components\MenuBar.jsx'
 echo $appPath  = Join-Path $web 'src\App.jsx'
 echo Write-Host "`n[STEP] 백업" -ForegroundColor Cyan
 echo Backup-File $menuPath
 echo Backup-File $appPath
 echo Write-Host "`n[STEP] MenuBar.jsx 패치" -ForegroundColor Cyan
 echo $menu = Get-Content -LiteralPath $menuPath -Raw -Encoding UTF8
 echo $menu = Replace-Regex $menu "flexWrap:\s*'nowrap'\s*,\s*overflowX:\s*'auto'\s*," "flexWrap: 'nowrap', overflow: 'visible', position: 'relative'," "MenuBar bar overflow"
 echo if ($menu -notmatch "const location = useLocation\(\);") {
 echo   $menu = [regex]::Replace($menu, "^\s*useLocation\(\);\s*//.*?$", "  const location = useLocation();`r`n`r`n  useEffect(() =^> {`r`n    setOpenMenu(null);`r`n  }, [location.pathname]);", [System.Text.RegularExpressions.RegexOptions]::Multiline)
 echo   Write-Host "  PATCH: MenuBar location route close" -ForegroundColor Green
 echo }
 echo if ($menu -notmatch "const handleMenuClick =") {
 echo   $menu = [regex]::Replace($menu, "const handleMenuOpen = label =^> \{.*?setOpenMenu\(openMenu === label \? null : label\);\s*\};", "const handleMenuClick = label =^> {`r`n    if (openMenu !== label) setRecentMenu(buildRecentFileItems());`r`n    setOpenMenu(curr =^> (curr === label ? null : label));`r`n  };`r`n`r`n  const handleMenuHover = label =^> {`r`n    if (!openMenu) return;`r`n    if (openMenu !== label) setRecentMenu(buildRecentFileItems());`r`n    setOpenMenu(label);`r`n  };", [System.Text.RegularExpressions.RegexOptions]::Singleline)
 echo   Write-Host "  PATCH: MenuBar click/hover split" -ForegroundColor Green
 echo }
 echo $menu = Replace-Regex $menu "<div className=""sqm-menu-btn-group"" style=\{\{display:'flex', gap:0, flexWrap:'nowrap'\}\}>" "<div className=""sqm-menu-btn-group"" style={{`r`n          display:'flex', gap:0, flexWrap:'nowrap',`r`n          overflowX:'auto', overflowY:'visible',`r`n          flex:'1 1 auto', minWidth:0,`r`n          scrollbarWidth:'thin'`r`n        }}>" "MenuBar button group overflow"
 echo $menu = Replace-Regex $menu "onClick=\{\(\) =^> handleMenuOpen\(menu\.label\)\}\s*onMouseEnter=\{\(\) =^> openMenu && handleMenuOpen\(menu\.label\)\}" "onClick={() =^> handleMenuClick(menu.label)}`r`n              onMouseEnter={() =^> handleMenuHover(menu.label)}" "MenuBar handlers"
 echo Set-Content -LiteralPath $menuPath -Value $menu -Encoding UTF8
 echo Write-Host "`n[STEP] App.jsx 패치" -ForegroundColor Cyan
 echo $app = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
 echo if ($app -notmatch "autoRefresh,\s*setAutoRefresh") {
 echo   $app = [regex]::Replace($app, "function AppInner\(\{\s*dark,\s*toggleTheme,\s*fontScale,\s*increaseFontScale,\s*decreaseFontScale,\s*resetFontScale,\s*devMode,\s*toggleDevMode\s*\}\)", "function AppInner({ dark, toggleTheme, fontScale, increaseFontScale, decreaseFontScale, resetFontScale, devMode, toggleDevMode, autoRefresh, setAutoRefresh })")
 echo   Write-Host "  PATCH: AppInner props" -ForegroundColor Green
 echo }
 echo if ($app -notmatch "case 'devMode':") {
 echo   $app = [regex]::Replace($app, "case 'toggleDevMode':\s*toggleDevMode\(\);\s*navigate\('/dev'\);\s*break;", "case 'toggleDevMode':`r`n      case 'devMode':`r`n        toggleDevMode();`r`n        navigate('/dev');`r`n        break;")
 echo   Write-Host "  PATCH: App devMode action" -ForegroundColor Green
 echo }
 echo if ($app -notmatch "setAutoRefresh\(v =^> !v\);") {
 echo   $app = [regex]::Replace($app, "case 'toggleAutoRefresh':\s*showToast\('자동 새로고침은 MenuBar 우측 버튼으로 변경하세요\.'\);\s*break;", "case 'toggleAutoRefresh':`r`n        setAutoRefresh(v => !v);`r`n        showToast(autoRefresh ? '자동 새로고침 OFF' : '자동 새로고침 ON');`r`n        break;")
 echo   Write-Host "  PATCH: App autoRefresh toggle" -ForegroundColor Green
 echo }
 echo if ($app -notmatch "autoRefresh=\{autoRefresh\}\s*setAutoRefresh=\{setAutoRefresh\}") {
 echo   $app = [regex]::Replace($app, "<AppInner dark=\{dark\} toggleTheme=\{toggleTheme\}\s*fontScale=\{fontScale\} increaseFontScale=\{increaseFontScale\}\s*decreaseFontScale=\{decreaseFontScale\} resetFontScale=\{resetFontScale\}\s*devMode=\{devMode\} toggleDevMode=\{toggleDevMode\} />", "<AppInner dark={dark} toggleTheme={toggleTheme}`r`n        fontScale={fontScale} increaseFontScale={increaseFontScale}`r`n        decreaseFontScale={decreaseFontScale} resetFontScale={resetFontScale}`r`n        devMode={devMode} toggleDevMode={toggleDevMode}`r`n        autoRefresh={autoRefresh} setAutoRefresh={setAutoRefresh} />")
 echo   Write-Host "  PATCH: AppInner props pass-through" -ForegroundColor Green
 echo }
 echo Set-Content -LiteralPath $appPath -Value $app -Encoding UTF8
 echo Write-Host "`n[STEP] dev 서버 실행" -ForegroundColor Cyan
 echo Push-Location $web
 echo try {
 echo   npm run dev
 echo } finally {
 echo   Pop-Location
 echo }
)

echo.
echo [STEP] BAT 단독 실행
powershell -NoProfile -ExecutionPolicy Bypass -File "%TMPPS1%"

set "EXITCODE=%ERRORLEVEL%"
del "%TMPPS1%" >nul 2>&1

echo.
if "%EXITCODE%"=="0" (
    echo [DONE] 완료되었습니다.
) else (
    echo [ERROR] 실행 중 오류가 발생했습니다. exit code=%EXITCODE%
)

pause
exit /b %EXITCODE%
