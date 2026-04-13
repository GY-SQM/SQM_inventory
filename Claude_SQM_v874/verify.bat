@echo off
chcp 65001 >nul
echo.
echo ================================================
echo  SQM P2-B+C pytest 검증 스크립트
echo ================================================
echo.

set PROJECT=D:\program\Sqm jaego\Claude_SQM_v871

cd /d "%PROJECT%"

echo [1/2] import 체인 전체 확인...
python -c "
from features.repositories.base_repository import BaseRepository
from features.repositories.inbound_repository import InboundRepository
from features.repositories.outbound_query import OutboundQuery
from features.repositories.outbound_repository import OutboundRepository
from features.repositories.inventory_repository import InventoryRepository
from features.services.outbound_state_rules import OutboundStateRules
from features.services.outbound_service import OutboundService
print('[OK] 전체 import 체인 정상')

# 상속 구조 확인
assert issubclass(InboundRepository, BaseRepository),  'InboundRepository 상속 오류'
assert issubclass(OutboundRepository, BaseRepository), 'OutboundRepository 상속 오류'
assert issubclass(InventoryRepository, BaseRepository),'InventoryRepository 상속 오류'
print('[OK] BaseRepository 상속 구조 정상')

# StateRules 동작 확인
assert OutboundStateRules.can_transition('AVAILABLE', 'RESERVED') == True
assert OutboundStateRules.can_transition('OUTBOUND',  'AVAILABLE') == False
print('[OK] OutboundStateRules 전이 규칙 정상')
print()
print('=== import 체인 전체 통과 ===')
" 2>&1
if errorlevel 1 (
    echo.
    echo [오류] import 실패 — 위 오류 메시지를 루비에게 전달해 주세요.
    pause
    exit /b 1
)

echo.
echo [2/2] pytest 실행 중...
echo   결과를 tests\p2b_test_result.txt 에 저장합니다.
echo.

pytest tests\test_p2b_outbound_refactor.py -v --tb=short 2>&1 | tee tests\p2b_test_result.txt

echo.
echo ================================================
echo  결과 파일: tests\p2b_test_result.txt
echo.
echo  오류가 있으면:
echo    tests\p2b_test_result.txt 내용을 루비에게 전달
echo  전체 통과하면:
echo    P2-D React 전환 단계 진입 가능!
echo ================================================
echo.
pause
