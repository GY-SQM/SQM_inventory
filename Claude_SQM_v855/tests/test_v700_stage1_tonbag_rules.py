# -*- coding: utf-8 -*-
"""
SQM v7.0.0 — Stage1 톤백 UID/NO 규칙 테스트 (25개)
======================================================
1 LOT = 톤백 N개(500kg 또는 1000kg) + 샘플 1개(1kg)
tonbag_uid = lot_no-001 / lot_no-S00
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine_modules.tonbag_patch_rules import normalize_tonbag_no, build_tonbag_uid
from engine_modules.tonbag_compat import (
    normalize_tonbag_keys, is_sample_tonbag
)

LOT = "1125072340"


class TestNormalizeTonbagNo:

    def test_T101_normal_int_1_becomes_001(self):
        assert normalize_tonbag_no(1) == "001"

    def test_T102_normal_int_10_becomes_010(self):
        assert normalize_tonbag_no(10) == "010"

    def test_T103_normal_int_20_stays_020(self):
        assert normalize_tonbag_no(20) == "020"

    def test_T104_string_5_becomes_005(self):
        assert normalize_tonbag_no("5") == "005"

    def test_T105_already_padded_001_unchanged(self):
        assert normalize_tonbag_no("001") == "001"

    def test_T106_sample_flag_gives_S00(self):
        assert normalize_tonbag_no(0, is_sample=True) == "S00"

    def test_T107_S0_legacy_normalized_to_S00(self):
        assert normalize_tonbag_no("S0") == "S00"

    def test_T108_S00_unchanged(self):
        assert normalize_tonbag_no("S00") == "S00"

    def test_T109_string_zero_without_sample_flag(self):
        """is_sample=False일 때 '0' → '000' (3자리 패딩)"""
        result = normalize_tonbag_no("0")
        assert len(result) == 3

    def test_T110_result_always_string(self):
        assert isinstance(normalize_tonbag_no(5), str)


class TestBuildTonbagUid:

    def test_T111_normal_uid_format(self):
        uid = build_tonbag_uid(LOT, "001")
        assert uid == f"{LOT}-001"

    def test_T112_sample_uid_format(self):
        uid = build_tonbag_uid(LOT, "S00")
        assert uid == f"{LOT}-S00"

    def test_T113_uid_separator_is_hyphen(self):
        assert "-" in build_tonbag_uid(LOT, "003")

    def test_T114_uid_starts_with_lot_no(self):
        assert build_tonbag_uid(LOT, "005").startswith(LOT)

    def test_T115_uid_ends_with_tonbag_no(self):
        assert build_tonbag_uid(LOT, "015").endswith("015")


class TestNormalizeTonbagKeys:

    def test_T116_sub_lt_1_gives_tonbag_no_001(self):
        row = {'lot_no': LOT, 'sub_lt': 1}
        assert normalize_tonbag_keys(row)['tonbag_no'] == '001'

    def test_T117_sub_lt_0_gives_S00(self):
        row = {'lot_no': LOT, 'sub_lt': 0}
        assert normalize_tonbag_keys(row)['tonbag_no'] == 'S00'

    def test_T118_is_sample_1_gives_S00(self):
        row = {'lot_no': LOT, 'sub_lt': 5, 'is_sample': 1}
        assert normalize_tonbag_keys(row)['tonbag_no'] == 'S00'

    def test_T119_existing_tonbag_no_preserved(self):
        row = {'lot_no': LOT, 'sub_lt': 5, 'tonbag_no': '005'}
        assert normalize_tonbag_keys(row)['tonbag_no'] == '005'

    def test_T120_sub_lt_preserved_in_result(self):
        row = {'lot_no': LOT, 'sub_lt': 3}
        assert normalize_tonbag_keys(row)['sub_lt'] == 3


class TestIsSampleTonbag:

    def test_T121_is_sample_flag_true(self):
        assert is_sample_tonbag({'is_sample': 1}) is True

    def test_T122_is_sample_flag_false(self):
        assert is_sample_tonbag({'is_sample': 0}) is False

    def test_T123_sub_lt_zero_is_sample(self):
        assert is_sample_tonbag({'sub_lt': 0}) is True

    def test_T124_sub_lt_nonzero_is_not_sample(self):
        assert is_sample_tonbag({'sub_lt': 5, 'is_sample': 0}) is False

    def test_T125_weight_1kg_is_sample(self):
        assert is_sample_tonbag({'weight': 1.0, 'sub_lt': 0}) is True
