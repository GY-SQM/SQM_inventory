# -*- coding: utf-8 -*-
"""Stage 2 tonbag weight rules.

기존 SQM 로직을 공식 규칙으로 모듈화한다.
공식:
    tonbag_weight = (lot_total_weight_kg - sample_weight_kg) / mxbg_pallet
"""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SAMPLE_WEIGHT_KG = 1.0

@dataclass(frozen=True)
class TonbagWeightRuleResult:
    tonbag_weight_kg: float
    sample_weight_kg: float
    mxbg_pallet: int
    rule_status: str


def calculate_tonbag_weight(lot_total_weight_kg: float, mxbg_pallet: int, sample_weight_kg: float = DEFAULT_SAMPLE_WEIGHT_KG) -> float:
    if mxbg_pallet <= 0:
        return 0.0
    return (float(lot_total_weight_kg) - float(sample_weight_kg)) / int(mxbg_pallet)


def get_rule_status(weight_kg: float) -> str:
    # 운영 해석: 500은 확정, 1000은 pending_confirmation.
    if abs(float(weight_kg) - 500.0) < 0.5:
        return 'confirmed'
    if abs(float(weight_kg) - 1000.0) < 0.5:
        return 'pending_confirmation'
    return 'unknown'


def build_rule_result(
    lot_total_weight_kg: float,
    mxbg_pallet: int,
    sample_weight_kg: float = DEFAULT_SAMPLE_WEIGHT_KG,
    expected_per_bag: int | None = None,          # v7.2.0: 입고 템플릿 주입값
) -> TonbagWeightRuleResult:
    """
    톤백 단가 계산.

    v7.2.0: expected_per_bag(입고 템플릿에서 주입)이 있으면
    계산값 대신 템플릿 단가로 rule_status를 결정하고
    톤백 무게도 expected_per_bag으로 고정한다.
    → 1000kg 톤백이 와도 500kg로 잘못 계산되는 버그 방지.
    """
    w = calculate_tonbag_weight(lot_total_weight_kg, mxbg_pallet, sample_weight_kg)

    if expected_per_bag is not None:
        try:
            expected = float(expected_per_bag)
            # 계산값과 템플릿값 편차 허용: ±5%
            if abs(w - expected) / max(expected, 1) < 0.05:
                # 정상: 계산값이 템플릿과 일치 → 그대로 사용
                status = get_rule_status(w)
            else:
                # 편차 있음: 템플릿 단가로 강제 덮어쓰기 + 경고 status
                w = expected
                status = f'template_override_{int(expected)}kg'
        except (TypeError, ValueError):
            status = get_rule_status(w)
    else:
        status = get_rule_status(w)

    return TonbagWeightRuleResult(
        tonbag_weight_kg=w,
        sample_weight_kg=sample_weight_kg,
        mxbg_pallet=mxbg_pallet,
        rule_status=status,
    )
