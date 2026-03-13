@echo off
REM ============================================================
REM  SQM 구버전 ZIP 정리 스크립트
REM  최신: SQM_v643_FINAL_ALL_v6.zip 만 남기고 나머지 archive\
REM  실행 위치: ZIP 파일들이 있는 폴더에서 실행
REM  날짜: 2026-03-07
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo  ============================================
echo   SQM 구버전 ZIP 정리 도구
echo   최신 버전: SQM_v643_FINAL_ALL_v6.zip
echo  ============================================
echo.

REM archive 폴더 생성
if not exist "archive\" (
    mkdir archive
    echo  [생성] archive\ 폴더 생성됨
)

REM 이동 대상: FINAL_ALL_v6 제외한 모든 SQM ZIP
set KEEP=SQM_v643_FINAL_ALL_v6.zip
set MOVED=0
set SKIPPED=0

for %%f in (SQM_v*.zip) do (
    if /i "%%f" == "%KEEP%" (
        echo  [유지] %%f
        set /a SKIPPED+=1
    ) else (
        move /y "%%f" "archive\%%f" >nul 2>&1
        if !errorlevel! == 0 (
            echo  [이동] %%f  →  archive\
            set /a MOVED+=1
        ) else (
            echo  [실패] %%f  이동 실패
        )
    )
)

REM HOTFIX ZIP 도 archive로
for %%f in (*HOTFIX*.zip *핫픽스*.zip) do (
    if exist "%%f" (
        move /y "%%f" "archive\%%f" >nul 2>&1
        echo  [이동] %%f  →  archive\
        set /a MOVED+=1
    )
)

echo.
echo  ============================================
echo   완료: %MOVED%개 이동 / %SKIPPED%개 유지
echo   현재 폴더: %KEEP%
echo   이전 버전: archive\ 폴더 확인
echo  ============================================
echo.
pause
