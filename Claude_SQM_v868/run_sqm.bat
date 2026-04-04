@echo off
chcp 65001 > nul
title SQM v8.6.7 실행

:: 로그 파일 경로 설정
set LOG=%~dp0logs\run_sqm.log
if not exist "%~dp0logs" mkdir "%~dp0logs"

echo ============================================
echo    SQM v8.6.7 시작
echo ============================================
echo.
echo 로그 파일: %LOG%
echo.

:: 로그 시작
echo [%date% %time%] ===== SQM 시작 ===== >> "%LOG%"

cd /d "%~dp0"

:: ── STEP 1: pdf_engine 확인 ──────────────────────────────
echo [1/3] pdf_engine 확인 중...
python -c "from core.pdf_engine import engine_info; info=engine_info(); print('  엔진:', info['engine'])" >> "%LOG%" 2>&1
python -c "from core.pdf_engine import engine_info; info=engine_info(); print('  엔진:', info['engine'])"
if errorlevel 1 (
    echo.
    echo ============================================
    echo   [오류] pdf_engine 로드 실패!
    echo   로그 확인: %LOG%
    echo ============================================
    echo [%date% %time%] [오류] pdf_engine 로드 실패 >> "%LOG%"
    echo.
    pause
    exit /b 1
)
echo [%date% %time%] [OK] pdf_engine 확인 완료 >> "%LOG%"
echo.

:: ── STEP 2: FastAPI 서버 확인 ────────────────────────────
echo [2/3] FastAPI 서버 시작...
echo [%date% %time%] FastAPI 서버 시작 시도 >> "%LOG%"

start "SQM_FastAPI" cmd /k "cd /d %~dp0 && echo FastAPI 시작... && python -m uvicorn react_api.main:app --reload --host 127.0.0.1 --port 8000 || (echo. && echo [오류] FastAPI 실패! && pause)"
timeout /t 4 > nul

:: FastAPI 포트 확인
netstat -an | find "8000" | find "LISTENING" > nul
if errorlevel 1 (
    echo.
    echo ============================================
    echo   [오류] FastAPI 포트 8000 응답 없음!
    echo   FastAPI 창을 확인하세요
    echo   로그 확인: %LOG%
    echo ============================================
    echo [%date% %time%] [오류] FastAPI 포트 8000 응답 없음 >> "%LOG%"
    echo.
    echo 계속 진행하시겠습니까? (Y/N)
    set /p CONTINUE=
    if /i "%CONTINUE%" neq "Y" (
        taskkill /fi "WINDOWTITLE eq SQM_FastAPI" /f > nul 2>&1
        exit /b 1
    )
) else (
    echo [OK] FastAPI 포트 8000 확인
    echo [%date% %time%] [OK] FastAPI 포트 8000 확인 >> "%LOG%"
)
echo.

:: ── STEP 3: React 프론트 ─────────────────────────────────
echo [3/3] React 프론트 시작...
echo [%date% %time%] React 시작 시도 >> "%LOG%"

if not exist "%~dp0web\node_modules" (
    echo.
    echo ============================================
    echo   [경고] node_modules 없음!
    echo   npm install 실행 중... (시간 걸림)
    echo ============================================
    cd /d "%~dp0web"
    npm install >> "%LOG%" 2>&1
    cd /d "%~dp0"
)

start "SQM_React" cmd /k "cd /d %~dp0web && npm run dev || (echo. && echo [오류] React 실패! && pause)"
timeout /t 3 > nul
echo [%date% %time%] [OK] React 시작 >> "%LOG%"
echo.

:: ── 실행 완료 안내 ───────────────────────────────────────
echo ============================================
echo   [완료] SQM v8.6.7 실행 중
echo   FastAPI : http://127.0.0.1:8000/docs
echo   React   : http://127.0.0.1:5173
echo   로그    : %LOG%
echo ============================================
echo.
echo [%date% %time%] [OK] 전체 시작 완료 >> "%LOG%"

:: ── tkinter 앱 실행 ──────────────────────────────────────
echo SQM tkinter 앱 시작...
python run.py >> "%LOG%" 2>&1
if errorlevel 1 (
    echo.
    echo ============================================
    echo   [오류] tkinter 앱 실행 실패!
    echo   로그 확인: %LOG%
    echo ============================================
    echo [%date% %time%] [오류] tkinter 앱 실패 >> "%LOG%"
    echo.
)

echo.
echo 모든 서버를 종료하시겠습니까? (Y/N)
set /p STOP=
if /i "%STOP%"=="Y" (
    taskkill /fi "WINDOWTITLE eq SQM_FastAPI" /f > nul 2>&1
    taskkill /fi "WINDOWTITLE eq SQM_React" /f > nul 2>&1
    echo [%date% %time%] 서버 종료 >> "%LOG%"
    echo 종료 완료
)

pause
