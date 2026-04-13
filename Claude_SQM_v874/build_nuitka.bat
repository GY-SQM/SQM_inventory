@echo off
chcp 65001 >nul
echo.
echo ================================================
echo  SQM v8.7.3 — Nuitka EXE 빌드 (Python 3.13)
echo  진입점: run.py (pywebview 기반)
echo  출력: dist\SQM\SQM.exe
echo ================================================
echo.

set PROJECT=f:\program\Sqm jaego\Claude_SQM_v873
set PYTHON=C:\Users\남기동\AppData\Local\Programs\Python\Python313\python.exe
cd /d "%PROJECT%"

:: ── [1/6] 진입점 확인 ───────────────────────────────────────
echo [1/6] 진입점 파일 확인...
if exist "run.py" (
    echo   OK run.py 발견
) else (
    echo   ERROR run.py 없음 — 빌드 중단
    pause & exit /b 1
)
echo.

:: ── [2/6] Python / Nuitka 확인 ─────────────────────────────
echo [2/6] Python / Nuitka 확인...
"%PYTHON%" --version
"%PYTHON%" -m nuitka --version 2>nul
if errorlevel 1 (
    echo   Nuitka 미설치 — 설치 중...
    "%PYTHON%" -m pip install nuitka ordered-set zstandard pywebview
    if errorlevel 1 (
        echo   ERROR Nuitka 설치 실패
        pause & exit /b 1
    )
)
echo.

:: ── [3/6] 필수 디렉토리 생성 ────────────────────────────────
echo [3/6] 빌드 환경 준비...
if not exist "data\db" mkdir "data\db"
if not exist "backup"  mkdir "backup"
if not exist "logs"    mkdir "logs"
echo   완료
echo.

:: ── [4/6] 이전 빌드 정리 ───────────────────────────────────
echo [4/6] 이전 빌드 정리...
if exist "dist\SQM" rmdir /s /q "dist\SQM"
if exist "run.build" rmdir /s /q "run.build"
if exist "run.dist" rmdir /s /q "run.dist"
if exist "run.onefile-build" rmdir /s /q "run.onefile-build"
echo   완료
echo.

:: ── [5/6] Nuitka 빌드 ──────────────────────────────────────
echo [5/6] Nuitka 빌드 시작... (10~30분 소요)
echo   빌드 시작 시간: %date% %time%
echo.

"%PYTHON%" -m nuitka ^
    --standalone ^
    --output-dir=dist\SQM ^
    --output-filename=SQM.exe ^
    --windows-console-mode=disable ^
    --windows-product-name="SQM Inventory System" ^
    --windows-product-version=8.7.3.0 ^
    --windows-file-version=8.7.3.0 ^
    --windows-company-name="SQM" ^
    --windows-file-description="SQM Inventory System v8.7.3" ^
    --enable-plugin=tk-inter ^
    --include-package=core ^
    --include-package=engine_modules ^
    --include-package=engine_modules.inventory_modular ^
    --include-package=gui_app_modular ^
    --include-package=gui_app_modular.dialogs ^
    --include-package=gui_app_modular.handlers ^
    --include-package=gui_app_modular.mixins ^
    --include-package=gui_app_modular.tabs ^
    --include-package=gui_app_modular.utils ^
    --include-package=features ^
    --include-package=features.ai ^
    --include-package=features.ai.carrier_templates ^
    --include-package=features.notifications ^
    --include-package=features.parsers ^
    --include-package=features.repositories ^
    --include-package=features.services ^
    --include-package=features.validators ^
    --include-package=parsers ^
    --include-package=parsers.document_parser_modular ^
    --include-package=react_api ^
    --include-package=react_api.middleware ^
    --include-package=react_api.routes ^
    --include-package=react_api.schemas ^
    --include-package=react_api.services ^
    --include-package=react_api.utils ^
    --include-module=run_bootstrap ^
    --include-module=version ^
    --include-module=config ^
    --include-module=config_sql ^
    --include-module=config_logging ^
    --include-module=theme_aware ^
    --include-data-dir=data=data ^
    --include-data-dir=backup=backup ^
    --include-data-dir=logs=logs ^
    --include-data-files=version.py=version.py ^
    --include-data-files=config.py=config.py ^
    --include-data-files=config_sql.py=config_sql.py ^
    --include-data-files=config_logging.py=config_logging.py ^
    --include-data-files=theme_preference.json=theme_preference.json ^
    --nofollow-import-to=matplotlib ^
    --nofollow-import-to=scipy ^
    --nofollow-import-to=sklearn ^
    --nofollow-import-to=tensorflow ^
    --nofollow-import-to=IPython ^
    --nofollow-import-to=jupyter ^
    --nofollow-import-to=notebook ^
    --nofollow-import-to=pytest ^
    --nofollow-import-to=hypothesis ^
    --assume-yes-for-downloads ^
    --remove-output ^
    --jobs=4 ^
    run.py

if errorlevel 1 (
    echo.
    echo   ERROR Nuitka 빌드 실패
    echo   빌드 종료 시간: %date% %time%
    pause & exit /b 1
)
echo.
echo   빌드 종료 시간: %date% %time%
echo.

:: ── [6/6] 빌드 결과 확인 ───────────────────────────────────
echo [6/6] 빌드 결과 확인...

:: Nuitka standalone 출력 디렉토리는 run.dist
if exist "dist\SQM\run.dist\SQM.exe" (
    for %%f in ("dist\SQM\run.dist\SQM.exe") do set EXE_SIZE=%%~zf
    set /a EXE_MB=!EXE_SIZE! / 1048576
    echo   OK SQM.exe 생성 완료
    echo   위치: dist\SQM\run.dist\SQM.exe
    echo.
    echo ================================================
    echo  빌드 성공! SQM v8.7.3
    echo  실행: dist\SQM\run.dist\SQM.exe
    echo ================================================
) else if exist "dist\SQM\SQM.exe" (
    echo   OK SQM.exe 생성 완료
    echo   위치: dist\SQM\SQM.exe
    echo.
    echo ================================================
    echo  빌드 성공! SQM v8.7.3
    echo  실행: dist\SQM\SQM.exe
    echo ================================================
) else (
    echo   ERROR SQM.exe를 찾을 수 없습니다
    echo   dist\SQM 디렉토리 내용:
    dir /s /b "dist\SQM\*.exe" 2>nul
    echo.
    echo   빌드 로그를 확인해주세요.
)
echo.
pause
