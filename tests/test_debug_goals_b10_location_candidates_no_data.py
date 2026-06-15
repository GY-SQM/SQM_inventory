# -*- coding: utf-8 -*-
"""B10 회귀 테스트 — 위치 후보 데이터가 없을 때 빈 값 대신 명시 메시지를 제공한다."""
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = os.path.join(ROOT, "backend", "api", "location_candidates.py")
ACTIONS = os.path.join(ROOT, "backend", "api", "actions.py")
ACTIONS2 = os.path.join(ROOT, "backend", "api", "actions2.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def test_location_candidates_exposes_no_data_message_and_status_helper():
    code = _read(CANDIDATES)

    assert "NO_LOCATION_DATA_MESSAGE" in code, "위치데이터 없음 공통 메시지 상수가 필요함"
    assert "위치데이터 없음" in code, "빈 후보 대신 사용자 메시지를 명시해야 함"
    assert "def load_latest_candidate_status" in code, "최신 batch 없음 상태 helper가 필요함"
    assert "has_data" in code and "message" in code, "상태 helper는 has_data/message를 반환해야 함"


def test_lot_excel_candidate_summary_uses_no_data_message_when_global_candidates_empty():
    code = _read(ACTIONS)

    assert "load_latest_candidate_status" in code, "LOT Excel 후보 표시에서 상태 helper를 사용해야 함"
    assert "NO_LOCATION_DATA_MESSAGE" in code, "LOT Excel 빈 후보에 위치데이터 없음 메시지를 써야 함"
    assert "candidate_status" in code, "전역 위치데이터 상태를 확인해야 함"


def test_tonbag_excel_candidate_summary_uses_no_data_message_when_global_candidates_empty():
    code = _read(ACTIONS2)

    assert "load_latest_candidate_status" in code, "톤백 Excel 후보 표시에서 상태 helper를 사용해야 함"
    assert "NO_LOCATION_DATA_MESSAGE" in code, "톤백 Excel 빈 후보에 위치데이터 없음 메시지를 써야 함"
    assert "candidate_status" in code, "전역 위치데이터 상태를 확인해야 함"
