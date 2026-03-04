#!/bin/bash
# ═══════════════════════════════════════════════════════════
# SQM v6.2.7 — CI 자동 테스트 스크립트
# ═══════════════════════════════════════════════════════════
# 사용법:
#   ./run_tests.sh          # 전체 테스트 + 커버리지
#   ./run_tests.sh quick    # 빠른 테스트 (커버리지 없이)
#   ./run_tests.sh coverage # 커버리지 + HTML 리포트
#   ./run_tests.sh module   # 모듈별 커버리지 요약
#
# 종료 코드:
#   0 = 성공 (모든 테스트 통과)
#   1 = 실패 (테스트 실패 있음)
# ═══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

MODE="${1:-full}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="reports/test_${TIMESTAMP}"

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  SQM v6.2.7 — 테스트 실행${NC}"
echo -e "${BLUE}  모드: ${MODE}${NC}"
echo -e "${BLUE}  시간: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

# 의존성 확인
check_dep() {
    if ! python3 -c "import $1" 2>/dev/null; then
        echo -e "${YELLOW}⚠ $1 미설치 — pip install $1${NC}"
        return 1
    fi
    return 0
}

check_dep pytest || exit 1

case "$MODE" in
    quick)
        echo -e "\n${GREEN}▶ 빠른 테스트 (커버리지 없이)${NC}\n"
        python3 -m pytest tests/ -v --tb=short -q 2>&1
        EXIT_CODE=$?
        ;;

    coverage)
        echo -e "\n${GREEN}▶ 커버리지 + HTML 리포트${NC}\n"
        check_dep coverage || { echo "pip install coverage"; exit 1; }
        mkdir -p "$REPORT_DIR"
        
        python3 -m coverage run --source=engine_modules,parsers,core -m pytest tests/ -v --tb=short 2>&1
        EXIT_CODE=$?
        
        echo -e "\n${BLUE}── 커버리지 요약 ──${NC}\n"
        python3 -m coverage report --show-missing | tee "${REPORT_DIR}/coverage_summary.txt"
        
        python3 -m coverage html -d "${REPORT_DIR}/htmlcov"
        echo -e "\n${GREEN}✅ HTML 리포트: ${REPORT_DIR}/htmlcov/index.html${NC}"
        ;;

    module)
        echo -e "\n${GREEN}▶ 모듈별 커버리지 요약${NC}\n"
        check_dep coverage || { echo "pip install coverage"; exit 1; }
        mkdir -p "$REPORT_DIR"
        
        python3 -m coverage run --source=engine_modules,parsers,core -m pytest tests/ --tb=no -q 2>&1
        EXIT_CODE=$?
        
        echo -e "\n${BLUE}── 핵심 모듈 커버리지 ──${NC}\n"
        python3 -m coverage report \
            --include="engine_modules/inventory_modular/inbound_mixin.py,engine_modules/inventory_modular/outbound_mixin.py,engine_modules/inventory_modular/return_mixin.py,engine_modules/inventory_modular/integrity_mixin.py,engine_modules/database.py,parsers/allocation_parser.py,parsers/picking_list_parser.py" \
            | tee "${REPORT_DIR}/module_coverage.txt"
        ;;

    full|*)
        echo -e "\n${GREEN}▶ 전체 테스트 + 커버리지${NC}\n"
        
        if check_dep coverage 2>/dev/null; then
            mkdir -p "$REPORT_DIR"
            
            python3 -m coverage run --source=engine_modules,parsers,core -m pytest tests/ -v --tb=short 2>&1
            EXIT_CODE=$?
            
            echo -e "\n${BLUE}── 커버리지 요약 ──${NC}\n"
            python3 -m coverage report | tee "${REPORT_DIR}/coverage_summary.txt"
            
            python3 -m coverage html -d "${REPORT_DIR}/htmlcov"
            echo -e "\n${GREEN}✅ HTML 리포트: ${REPORT_DIR}/htmlcov/index.html${NC}"
        else
            python3 -m pytest tests/ -v --tb=short 2>&1
            EXIT_CODE=$?
        fi
        ;;
esac

echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
if [ "${EXIT_CODE:-0}" -eq 0 ]; then
    echo -e "${GREEN}  ✅ 테스트 성공${NC}"
else
    echo -e "${RED}  ❌ 테스트 실패 (exit: ${EXIT_CODE})${NC}"
fi
echo -e "${BLUE}  완료: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

exit ${EXIT_CODE:-0}
