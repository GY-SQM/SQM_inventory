# GPT_P2_BATCH_B_BAT_GUIDE.md
작성일: 2026-04-07

## 목적
Batch B를 한 번에 반복 실행하기 위한 `.bat` 자동 실행 파일 작성 기준서

---

## 파일명
`run_batch_b_detailed.bat`

## 권장 코드

```bat
@echo off
setlocal

echo ========================================
echo [BATCH B] Detailed Auto Run
echo ========================================

echo [0/6] file existence check
if not exist engine_modules\inventory_modular\outbound_query.py goto :missing
if not exist engine_modules\inventory_modular\outbound_repository.py goto :missing
if not exist engine_modules\inventory_modular\outbound_service.py goto :missing
if not exist engine_modules\inventory_modular\outbound_state_rules.py goto :missing

echo [1/6] py_compile
python -m py_compile engine_modules\inventory_modular\outbound_query.py engine_modules\inventory_modular\outbound_repository.py engine_modules\inventory_modular\outbound_service.py engine_modules\inventory_modular\outbound_state_rules.py
if errorlevel 1 goto :fail

echo [2/6] pytest service
python -m pytest tests\test_outbound_service.py -q
if errorlevel 1 goto :fail

echo [3/6] pytest repository
python -m pytest tests\test_outbound_repository.py -q
if errorlevel 1 goto :fail

echo [4/6] pytest policy
python -m pytest tests\test_outbound_scan_policy.py -q
if errorlevel 1 goto :fail

echo [5/6] verify script
python scripts\verify_outbound_batch_b.py
if errorlevel 1 goto :fail

echo [6/6] PASS
echo BATCH B PASS
goto :end

:missing
echo REQUIRED FILE MISSING
exit /b 2

:fail
echo BATCH B FAIL
exit /b 1

:end
endlocal
pause
```

---

## 사용 순서

1. 프로젝트 루트에서 실행
2. FAIL 발생 시 콘솔 로그 저장
3. `GPT_P2_BATCH_B_VERIFICATION.md`와 대조
4. 수정 후 재실행

---

## 권장 추가 옵션

로그 파일 저장용:

```bat
python scripts\verify_outbound_batch_b.py > logs\batch_b_verify.log 2>&1
```

pytest 결과 저장:

```bat
python -m pytest tests\test_outbound_service.py -q > logs\batch_b_pytest_service.log 2>&1
```

---

## 결론

Batch B용 bat 파일은 단순 편의도구가 아니라
**에러 재현과 원인 추적을 반복 가능하게 만드는 운영 도구**다.
