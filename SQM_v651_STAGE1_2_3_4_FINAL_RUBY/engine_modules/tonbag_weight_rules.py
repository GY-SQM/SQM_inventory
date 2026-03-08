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


def build_rule_result(lot_total_weight_kg: float, mxbg_pallet: int, sample_weight_kg: float = DEFAULT_SAMPLE_WEIGHT_KG) -> TonbagWeightRuleResult:
    w = calculate_tonbag_weight(lot_total_weight_kg, mxbg_pallet, sample_weight_kg)
    return TonbagWeightRuleResult(
        tonbag_weight_kg=w,
        sample_weight_kg=sample_weight_kg,
        mxbg_pallet=mxbg_pallet,
        rule_status=get_rule_status(w),
    )
