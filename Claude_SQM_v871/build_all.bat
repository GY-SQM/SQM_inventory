@echo off
chcp 65001 >nul
echo.
echo ================================================
echo  SQM v8.7.1 — 전체 빌드 스크립트
echo  ① React 빌드
echo  ② pywebview 데스크탑 (SQM_Web.exe)
echo  ③ Electron 데스크탑 (SQM_Setup.exe)
echo ================================================
echo.

set PROJECT=D:\program\Sqm jaego\Claude_SQM_v871
cd /d "%PROJECT%"

:: ============================================================
:: STEP 1. React 빌드
:: ============================================================
echo [STEP 1/3] React 빌드 중...
cd /d "%PROJECT%\web"
where npm >nul 2>&1
if errorlevel 1 (
    echo   ❌ npm 없음 — Node.js 설치 필요
    echo   https://nodejs.org 에서 다운로드
    pause & exit /b 1
)

npm run build
if errorlevel 1 (
    echo   ❌ React 빌드 실패
    pause & exit /b 1
)
echo   ✅ React 빌드 완료 → web\dist\
cd /d "%PROJECT%"
echo.

:: ============================================================
:: STEP 2. pywebview 데스크탑 앱 빌드
:: ============================================================
echo [STEP 2/3] pywebview 데스크탑 앱 빌드...
python -c "import webview" 2>nul
if errorlevel 1 (
    echo   pywebview 설치 중...
    pip install pywebview
)

python -c "import uvicorn, fastapi" 2>nul
if errorlevel 1 (
    echo   uvicorn, fastapi 설치 중...
    pip install uvicorn fastapi
)

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo   PyInstaller 설치 중...
    pip install pyinstaller
)

if exist "dist\SQM_Web" rmdir /s /q "dist\SQM_Web"
pyinstaller sqm_web_desktop.spec --noconfirm --clean

if exist "dist\SQM_Web\SQM_Web.exe" (
    echo   ✅ SQM_Web.exe 완성
    echo   위치: dist\SQM_Web\SQM_Web.exe
) else (
    echo   ❌ pywebview 빌드 실패 — 계속 진행
)
echo.

:: ============================================================
:: STEP 3. Electron 빌드
:: ============================================================
echo [STEP 3/3] Electron 앱 빌드...

:: Electron용 package.json 복사
if not exist "%PROJECT%\electron" mkdir "%PROJECT%\electron"
copy /y "%PROJECT%\electron_main.js"    "%PROJECT%\electron\main.js"    >nul
copy /y "%PROJECT%\electron_package.json" "%PROJECT%\package.json" >nul

npm install --save-dev electron electron-builder
if errorlevel 1 (
    echo   ❌ Electron 의존성 설치 실패
    echo   계속 진행합니다...
    goto :BUILD_DONE
)

npx electron-builder --win --x64
if exist "dist_electron\*.exe" (
    echo   ✅ Electron 설치 파일 완성
    echo   위치: dist_electron\
) else (
    echo   ⚠️  Electron 빌드 확인 필요
)

:BUILD_DONE
echo.
echo ================================================
echo  빌드 완료!
echo.
echo  Tkinter EXE:  build_exe.bat 실행
echo  pywebview:    dist\SQM_Web\SQM_Web.exe
echo  Electron:     dist_electron\*.exe
echo  개발서버:     cd web ^&^& npm run dev
echo ================================================
echo.
pause
