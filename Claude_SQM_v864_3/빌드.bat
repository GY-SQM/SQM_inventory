@echo off
chcp 65001 > nul
title SQM v864.3 EXE 빌드
cd /d "%~dp0"

echo.
echo ====================================================
echo  SQM Inventory v864.3 - PyInstaller EXE 빌드
echo ====================================================
echo.

REM 프로젝트 .venv 활성화
if exist .venv\Scripts\activate.bat (
    echo [1] .venv 활성화...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] .venv 없음 - 시스템 Python 사용
)

REM PyInstaller 확인
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [2] PyInstaller 설치 중...
    pip install pyinstaller
)

REM pandas 확인
python -c "import pandas" 2>nul
if errorlevel 1 (
    echo [!] pandas 미설치 - pip install pandas
    pip install pandas openpyxl
)

REM 이전 빌드 정리
echo [3] 이전 빌드 정리...
if exist dist\SQM_v864_3.exe del /q dist\SQM_v864_3.exe
if exist build\work rmdir /s /q build\work

REM 빌드 실행
echo.
echo [4] EXE 빌드 시작... (2~5분 소요)
echo.
pyinstaller build\SQM_v864_3.spec --noconfirm --distpath=dist --workpath=build\work

if errorlevel 1 (
    echo.
    echo ====================================================
    echo  [ERROR] 빌드 실패!
    echo ====================================================
    echo.
    echo  다음을 확인하세요:
    echo   1. Python 3.10+ 설치 (python --version)
    echo   2. 의존성 설치 (pip install -r requirements_webview.txt)
    echo   3. 안티바이러스가 차단하는지 확인
    echo.
    pause
    exit /b 1
)

echo.
echo ====================================================
echo  [SUCCESS] 빌드 완료!
echo ====================================================
echo.
echo  EXE 위치: %cd%\dist\SQM_v864_3.exe
echo.

REM EXE 크기 표시
for %%f in (dist\SQM_v864_3.exe) do echo  파일 크기: %%~zf bytes (약 %%~zf)

echo.
echo  실행하려면: dist\SQM_v864_3.exe 더블클릭
echo  또는: python main_webview.py (개발 모드)
echo.
pause
