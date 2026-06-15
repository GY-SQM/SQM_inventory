#!/usr/bin/env bash
# SessionStart 훅 — 매 세션 시작 시 디버깅 환경을 자동 준비한다.
#   1) headless 테스트 의존성 설치 (이미 있으면 거의 즉시 통과)
#   2) 전체 테스트 스모크 실행 (GUI 의존 테스트는 제외)
#   3) 결과 요약을 세션 컨텍스트로 출력
#
# 목적: 세션이 중간에 회수돼도 새 세션이 곧바로 테스트를 돌릴 수 있게 하여
#       "환경 재준비"에 드는 시간을 0 으로 만든다.
set -u
cd "$(dirname "$0")/../.." || exit 0

echo "── SQM SessionStart: 디버깅 환경 준비 ──"

# 1) 테스트 의존성 설치 (조용히, 실패해도 세션은 계속)
if [ -f requirements-test.txt ]; then
  pip install -q -r requirements-test.txt 2>/dev/null \
    && echo "✓ 테스트 의존성 준비 완료" \
    || echo "⚠ 의존성 설치 일부 실패 (네트워크 정책 확인) — 테스트가 import 에러를 낼 수 있음"
fi

# 2) 스모크 테스트 (GUI/tkinter 의존 테스트 1건 제외)
if python -m pytest --version >/dev/null 2>&1; then
  echo "── 스모크 테스트 실행 중 (GUI 테스트 제외) ──"
  # 제외 대상:
  #  - test_inbound_doc_detector_artifact_guard.py : GUI(tkinter) 필요 → 서버 실행 불가
  #  - test_real_db_has_indexes : 커밋 안 되는 실제 DB 파일에 의존 (환경 의존)
  python -m pytest tests/ -q \
    --ignore=tests/test_inbound_doc_detector_artifact_guard.py \
    --deselect tests/test_phase1_db_index.py::test_real_db_has_indexes \
    2>&1 | tail -5
else
  echo "⚠ pytest 미설치 — 'pip install -r requirements-test.txt' 후 테스트 가능"
fi

echo "── 준비 완료. DEBUG_GOALS.md 의 첫 미체크 항목부터 이어서 진행하세요. ──"
