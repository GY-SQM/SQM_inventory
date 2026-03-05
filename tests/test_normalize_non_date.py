# -*- coding: utf-8 -*-
"""
비날짜 정규화 회귀 테스트
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.common import norm_digits_only, norm_bl_no, norm_sap_no
from features.ai.gemini_parser import parse_euro_weight


def test_norm_digits_only_excel_float_suffix():
    assert norm_digits_only("2200033057.0") == "2200033057"
    assert norm_digits_only("2200033057.00") == "2200033057"
    assert norm_digits_only("MAEU258468669.0") == "258468669"


def test_norm_bl_sap_no_excel_float_suffix():
    assert norm_bl_no("258468669.0") == "258468669"
    assert norm_sap_no("2200033057.0") == "2200033057"


def test_parse_euro_weight_three_digit_integer_part():
    assert parse_euro_weight("100.020") == 100020.0
    assert parse_euro_weight("5.001") == 5001.0
