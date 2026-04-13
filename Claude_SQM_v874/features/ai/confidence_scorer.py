# -*- coding: utf-8 -*-
"""P2-2: ConfidenceScorer — 파싱 결과 신뢰도 평가"""
import re
import logging

logger = logging.getLogger(__name__)

class ConfidenceScorer:
    """각 필드별 신뢰도 점수 계산"""

    # 필드별 검증 규칙
    FIELD_VALIDATORS = {
        'bl_no': lambda v: bool(re.match(r'^[A-Z]{4}\d{8,}$|^[A-Z0-9]{6,20}$', v or '')),
        'container_no': lambda v: bool(re.match(r'^[A-Z]{4}\d{7}$', v or '')),
        'lot_no': lambda v: bool(v and len(v) >= 4),
        'net_weight': lambda v: _is_positive_number(v),
        'tonbag_count': lambda v: _is_positive_int(v),
        'ship_date': lambda v: bool(re.match(r'^\d{4}-\d{2}-\d{2}$', v or '')),
        'arrival_date': lambda v: bool(re.match(r'^\d{4}-\d{2}-\d{2}$', v or '')),
        'vessel': lambda v: bool(v and len(v) >= 2),
        'product': lambda v: bool(v and len(v) >= 2),
        'invoice_no': lambda v: bool(v and len(v) >= 3),
        'sap_no': lambda v: bool(v and len(v) >= 4),
    }

    def score(self, parsed_data, parse_method='AI'):
        """전체 결과 신뢰도 계산"""
        field_scores = {}
        for field, value in parsed_data.items():
            if field in ('success', 'parse_method', 'carrier', 'is_new_carrier', 'doc_type'):
                continue
            field_scores[field] = self._score_field(field, value, parse_method)

        if not field_scores:
            return {'overall': 0, 'level': 'MANUAL', 'fields': {}}

        overall = sum(field_scores.values()) / len(field_scores)

        # 템플릿 파싱은 신뢰도 보너스
        if parse_method == 'TEMPLATE':
            overall = min(100, overall + 10)

        level = 'AUTO' if overall >= 90 else 'CHECK' if overall >= 70 else 'MANUAL'

        return {
            'overall': round(overall, 1),
            'level': level,  # AUTO / CHECK / MANUAL
            'fields': {k: round(v, 1) for k, v in field_scores.items()},
        }

    def _score_field(self, field, value, parse_method):
        """개별 필드 점수 (0~100)"""
        if not value:
            return 0

        base = 50  # 값이 있으면 기본 50점
        validator = self.FIELD_VALIDATORS.get(field)
        if validator:
            if validator(str(value)):
                base = 90  # 형식 검증 통과
            else:
                base = 40  # 형식 불일치

        # 파싱 방법 보너스
        if parse_method == 'TEMPLATE':
            base = min(100, base + 5)

        return base


def _is_positive_number(v):
    try:
        return float(str(v).replace(',', '')) > 0
    except (ValueError, TypeError):
        return False

def _is_positive_int(v):
    try:
        return int(str(v).replace(',', '')) > 0
    except (ValueError, TypeError):
        return False
