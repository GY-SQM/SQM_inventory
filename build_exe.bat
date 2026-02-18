@echo off
chcp 65001 > nul

REM version.py에서 버전 읽기 (Single Source of Truth)
for /f "tokens=2 delims='" %%v in ('python -c "from version import __version__; print(__version__)"') do set VER=%%v
if "%VER%"=="" (
    for /f %%v in ('python -c "from version import __version__; print(__version__)"') do set VER=%%v
)

title SQM Inventory v%VER% 빌드

echo ========================================
echo   SQM Inventory v%VER% EXE 빌드
echo ========================================
echo.

REM Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    pause
    exit /b 1
)

REM PyInstaller 확인/설치
pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo [설치] PyInstaller 설치 중...
    pip install pyinstaller
)

REM UPX 다운로드 안내 (선택)
echo.
echo [정보] UPX 압축을 사용하려면 https://upx.github.io/ 에서 다운로드 후
echo        이 폴더에 upx.exe를 복사하세요. (선택사항)
echo.

REM 이전 빌드 정리
if exist "dist" (
    echo [정리] 이전 빌드 삭제 중...
    rmdir /s /q dist
)
if exist "build\sqm_inventory" (
    rmdir /s /q build\sqm_inventory
)

REM 빌드 실행 (spec은 루트에 위치)
echo [빌드] PyInstaller 실행 중...
echo.

pyinstaller sqm_inventory.spec --clean

if errorlevel 1 (
    echo.
    echo [오류] 빌드 실패!
    pause
    exit /b 1
)

REM 추가 파일 복사
echo.
echo [복사] 추가 파일 복사 중...
if not exist "dist\data\db" mkdir "dist\data\db"
copy /y VERSION.txt dist\ > nul
copy /y README.md dist\ > nul

REM 결과 확인
echo.
echo ========================================
echo   빌드 완료!
echo ========================================
echo.
dir dist\*.exe
echo.

pause
