# -*- coding: utf-8 -*-
"""
P5 테스트: validate_status_transition() — 허용/비허용 전이 검증
"""
import pytest
from engine_modules.validators import (
    validate_status_transition,
    _ALLOWED_TONBAG_TRANSITIONS,
)


class TestStatusTransition:
    """톤백 상태 전이 규칙 검증"""

    # --- 허용되는 전이 ---
    @pytest.mark.parametrize("old,new", [
        ("RETURN", "AVAILABLE"),
        ("AVAILABLE", "RESERVED"),
        ("AVAILABLE", "PICKED"),
        ("RESERVED", "PICKED"),
        ("RESERVED", "AVAILABLE"),
        ("PICKED", "SOLD"),
        ("PICKED", "OUTBOUND"),
        ("PICKED", "SHIPPED"),
        ("SOLD", "RETURN"),
        ("OUTBOUND", "RETURN"),
        ("SHIPPED", "RETURN"),
    ])
    def test_allowed_transitions(self, old, new):
        """허용된 전이는 예외 없이 통과해야 한다"""
        validate_status_transition(old, new, context="test")

    # --- 차단되는 전이 ---
    @pytest.mark.parametrize("old,new", [
        ("DEPLETED", "AVAILABLE"),   # 종료 상태에서 복귀 불가
        ("AVAILABLE", "SOLD"),       # 직접 판매 불가 (PICKED 거쳐야)
        ("AVAILABLE", "OUTBOUND"),   # 직접 출고 불가
        ("RETURN", "SOLD"),          # 반품에서 직접 판매 불가
        ("RETURN", "PICKED"),        # 반품에서 직접 피킹 불가
    ])
    @pytest.mark.edge
    def test_disallowed_transitions(self, old, new):
        """비허용 전이는 ValueError를 발생시켜야 한다"""
        with pytest.raises(ValueError, match="허용되지 않은 상태 전이"):
            validate_status_transition(old, new, context="test")

    # --- DEPLETED는 어디로도 전이 불가 ---
    @pytest.mark.edge
    def test_depleted_blocks_all(self):
        """DEPLETED 상태에서는 어떤 전이도 불가"""
        for target in ["AVAILABLE", "RESERVED", "PICKED", "SOLD", "RETURN"]:
            with pytest.raises(ValueError):
                validate_status_transition("DEPLETED", target, context="test")

    # --- 맵에 없는 상태 ---
    @pytest.mark.edge
    def test_unknown_old_status(self):
        """맵에 없는 old_status → 빈 set이므로 모든 전이 차단"""
        with pytest.raises(ValueError):
            validate_status_transition("UNKNOWN", "AVAILABLE", context="test")

    # --- context가 에러 메시지에 포함되는지 ---
    def test_context_in_error_message(self):
        """에러 메시지에 context가 포함되어야 한다"""
        with pytest.raises(ValueError, match="my_context"):
            validate_status_transition("DEPLETED", "AVAILABLE", context="my_context")

    # --- 전이 맵 완전성 ---
    def test_transition_map_completeness(self):
        """모든 주요 상태가 전이 맵에 존재하는지 확인"""
        expected_states = {
            'AVAILABLE', 'RESERVED', 'PICKED', 'SOLD',
            'OUTBOUND', 'SHIPPED', 'RETURN', 'DEPLETED'
        }
        assert expected_states == set(_ALLOWED_TONBAG_TRANSITIONS.keys())
