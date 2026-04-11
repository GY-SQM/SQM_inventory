@echo off
chcp 65001 > nul
title SQM 자동 시작 설정

echo.
echo ========================================
echo   SQM v8.6.9 PC 부팅 시 자동 시작 설정
echo ========================================
echo.

:: 현재 경로
set SQM_DIR=%~dp0
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_DIR%\SQM_v869.bat

:: 시작 프로그램 폴더에 배치파일 복사
echo [설정] 자동 시작 등록 중...
copy "%SQM_DIR%run_sqm_v869.bat" "%SHORTCUT_PATH%" > nul

if exist "%SHORTCUT_PATH%" (
    echo [완료] 자동 시작 등록 성공!
    echo        PC를 켤 때마다 SQM 서버가 자동으로 시작됩니다.
) else (
    echo [오류] 자동 시작 등록 실패
    echo        관리자 권한으로 다시 실행해보세요.
)

echo.
echo [확인] 자동 시작 폴더: %STARTUP_DIR%
echo.
pause
