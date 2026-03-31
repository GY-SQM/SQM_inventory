# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.cross_validator — stub (v7.0.0)
===================================================
Invoice × PL × BL × DO 교차 검증.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from .session_manager import DocumentSession


@dataclass
class CrossValidationResult:
    session_id: str = ""
    passed: bool = True
    warnings: List[Dict[str, str]] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
    field_matches: Dict[str, bool] = field(default_factory=dict)

    def add_warning(self, field: str, msg: str,
                    src_a: str = "", src_b: str = "") -> None:
        self.warnings.append({'field': field, 'message': msg,
                              'source_a': src_a, 'source_b': src_b})

    def add_error(self, field: str, msg: str,
                  src_a: str = "", src_b: str = "") -> None:
        self.errors.append({'field': field, 'message': msg,
                            'source_a': src_a, 'source_b': src_b})
        self.passed = False

    @property
    def is_clean(self) -> bool:
        return self.passed and not self.warnings


def cross_validate_session(session: DocumentSession) -> CrossValidationResult:
    """세션 내 문서 교차 검증 수행"""
    result = CrossValidationResult(session_id=session.session_id)

    inv = session.get_document('INVOICE')
    pl = session.get_document('PACKING_LIST')
    bl = session.get_document('BL')

    if not inv or not pl:
        result.add_error('documents', 'Invoice 또는 Packing List 누락')
        return result

    # LOT 번호 교차 검증
    if inv.lot_no and pl.lot_no and inv.lot_no != pl.lot_no:
        result.add_error(
            'lot_no',
            f'LOT 번호 불일치: Invoice={inv.lot_no}, PL={pl.lot_no}',
            src_a=inv.lot_no, src_b=pl.lot_no
        )

    # B/L 번호 교차 검증
    if bl and inv.bl_no and bl.bl_no and inv.bl_no != bl.bl_no:
        result.add_warning(
            'bl_no',
            f'B/L 번호 불일치: Invoice={inv.bl_no}, BL={bl.bl_no}',
            src_a=inv.bl_no, src_b=bl.bl_no
        )

    session.cross_check_passed = result.passed
    return result
