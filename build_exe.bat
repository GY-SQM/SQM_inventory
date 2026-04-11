@echo off
chcp 65001 >nul
echo.
echo ================================================
echo  SQM v8.7.1 — 완전 자동 EXE 빌드 v2
echo  Q1: run.py 자동 감지
echo  Q3: 광양 PC 무설치 실행 보장
echo ================================================
echo.

set PROJECT=D:\program\Sqm jaego\Claude_SQM_v871
cd /d "%PROJECT%"

:: ── Q1: 진입점 파일 존재 확인 ────────────────────────────────
echo [Q1] 진입점 파일 확인 중...
if exist "run.py" (
    echo   ✅ run.py 발견 — 진입점으로 사용
    set ENTRY=run.py
) else if exist "run_bootstrap.py" (
    echo   ⚠️  run.py 없음 → run_bootstrap.py 폴백
    set ENTRY=run_bootstrap.py
    :: spec 파일도 폴백으로 업데이트
) else (
    echo   ❌ 진입점 파일 없음 (run.py / run_bootstrap.py)
    echo   빌드를 중단합니다.
    pause & exit /b 1
)
echo.

:: ── PyInstaller 설치 확인 ────────────────────────────────────
echo [설치 확인] PyInstaller...
python -c "import PyInstaller; print('  버전:', PyInstaller.__version__)" 2>nul
if errorlevel 1 (
    echo   PyInstaller 없음 — 설치 중...
    pip install pyinstaller
)

:: ── UPX 확인 (압축 도구) ────────────────────────────────────
where upx >nul 2>&1
if errorlevel 1 (
    echo   [정보] UPX 없음 — 압축 없이 빌드 (크기 약 10%% 증가)
)
echo.

:: ── 기존 빌드 정리 ──────────────────────────────────────────
echo [1/5] 기존 빌드 정리...
if exist "dist\SQM" rmdir /s /q "dist\SQM"
if exist "build\SQM" rmdir /s /q "build\SQM"
echo   완료
echo.

:: ── 필수 디렉토리 생성 ──────────────────────────────────────
echo [2/5] 빌드 환경 준비...
if not exist "data\db" mkdir "data\db"
if not exist "backup"  mkdir "backup"
if not exist "logs"    mkdir "logs"
echo   완료
echo.

:: ── PyInstaller 빌드 ─────────────────────────────────────────
echo [3/5] PyInstaller 빌드 시작...
echo   (최초 빌드 3~8분 소요)
echo.
pyinstaller sqm_desktop.spec --noconfirm --clean
echo.

:: ── 빌드 결과 확인 ──────────────────────────────────────────
echo [4/5] 빌드 결과 확인...
if not exist "dist\SQM\SQM.exe" (
    echo   ❌ 빌드 실패
    echo.
    echo   오류 원인 확인:
    echo   1. build\SQM\warn-SQM.txt 파일 확인
    echo   2. 오류 내용 루비에게 전달
    pause & exit /b 1
)

:: EXE 크기 확인
for %%f in ("dist\SQM\SQM.exe") do set EXE_SIZE=%%~zf
set /a EXE_MB=%EXE_SIZE% / 1048576
echo   ✅ SQM.exe 생성 완료 (%EXE_MB% MB)
echo.

:: ── Q3: 광양 배포 패키지 생성 ────────────────────────────────
echo [5/5] 광양 PC 배포 패키지 생성...

:: 배포 패키지 폴더
set DEPLOY_PKG=%PROJECT%\dist\SQM_Gwangyang

if exist "%DEPLOY_PKG%" rmdir /s /q "%DEPLOY_PKG%"
mkdir "%DEPLOY_PKG%"

:: EXE + 관련 파일 복사
xcopy /s /q "dist\SQM\*" "%DEPLOY_PKG%\" >nul
echo   SQM.exe 복사 완료

:: .env 설정 파일 포함 (BOT_TOKEN 등)
if exist ".env" (
    copy /y ".env" "%DEPLOY_PKG%\.env" >nul
    echo   .env 복사 완료
)

:: 실행 가이드 생성
(
echo SQM 재고관리 시스템 — 광양 설치 가이드
echo =========================================
echo.
echo 1. 이 폴더를 광양 PC의 C:\SQM\ 에 복사
echo 2. SQM.exe 더블클릭으로 실행
echo 3. Python 설치 불필요
echo.
echo 주의사항:
echo - 폴더 전체를 이동하세요 (SQM.exe만 복사하면 안됩니다)
echo - 방화벽 차단 시 "액세스 허용" 클릭
echo - 첫 실행 시 Windows Defender 경고 → "추가 정보" → "실행"
echo.
echo 문의: @Claude_kdnbot /상태
) > "%DEPLOY_PKG%\README_설치가이드.txt"

:: 폴더 크기 확인
for /f "tokens=3" %%a in ('dir /s /-c "%DEPLOY_PKG%" ^| findstr "파일"') do set PKG_SIZE=%%a
echo   배포 패키지: %DEPLOY_PKG%

echo.
echo ================================================
echo  ✅ 빌드 완료!
echo.
echo  로컬 실행:  dist\SQM\SQM.exe
echo  광양 배포:  dist\SQM_Gwangyang\ (폴더 전체 복사)
echo ================================================
echo.

:: 바탕화면 바로가기 생성
set SHORTCUT_PATH=%USERPROFILE%\Desktop\SQM.lnk
powershell -Command "try { $s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath='%PROJECT%\dist\SQM\SQM.exe'; $s.WorkingDirectory='%PROJECT%\dist\SQM'; $s.Description='SQM 재고관리 시스템'; $s.Save(); Write-Host '  바탕화면 바로가기 생성됨' } catch { Write-Host '  바로가기 생성 건너뜀' }"

pause
