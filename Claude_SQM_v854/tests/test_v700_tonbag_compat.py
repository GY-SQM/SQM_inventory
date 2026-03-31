# -*- coding: utf-8 -*-
"""
SQM v7.0.0 — tonbag_compat 호환 레이어 테스트 (15개)
======================================================
sub_lt ↔ tonbag_no 정규화, normalize_all_keys,
get_tonbag_display_no, get_tonbag_uid
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine_modules.tonbag_compat import (
    normalize_rows, get_tonbag_display_no,
    get_tonbag_uid, normalize_all_keys,
    normalize_all_rows, normalize_customer_keys
)

LOT = "1125072340"


# ── 1. normalize_rows ─────────────────────────────────────────────────────

class TestNormalizeRows:

    def test_T701_list_of_rows_all_normalized(self):
        rows = [{'sub_lt': 1}, {'sub_lt': 2}, {'sub_lt': 0}]
        result = normalize_rows(rows)
        assert result[0]['tonbag_no'] == '001'
        assert result[1]['tonbag_no'] == '002'
        assert result[2]['tonbag_no'] == 'S00'

    def test_T702_empty_list_returns_empty(self):
        assert normalize_rows([]) == []

    def test_T703_none_returns_none(self):
        assert normalize_rows(None) is None


# ── 2. get_tonbag_display_no ──────────────────────────────────────────────

class TestGetTonbagDisplayNo:

    def test_T704_sub_lt_1_displays_001(self):
        row = {'sub_lt': 1, 'is_sample': 0}
        assert get_tonbag_display_no(row) == '001'

    def test_T705_sub_lt_20_displays_020(self):
        row = {'sub_lt': 20, 'is_sample': 0}
        assert get_tonbag_display_no(row) == '020'

    def test_T706_sample_displays_S00(self):
        row = {'sub_lt': 0, 'is_sample': 1}
        assert get_tonbag_display_no(row) == 'S00'

    def test_T707_tonbag_no_S00_displays_S00(self):
        row = {'tonbag_no': 'S00'}
        assert get_tonbag_display_no(row) == 'S00'


# ── 3. get_tonbag_uid ─────────────────────────────────────────────────────

class TestGetTonbagUid:

    def test_T708_existing_uid_returned_as_is(self):
        row = {'tonbag_uid': f'{LOT}-001', 'lot_no': LOT, 'sub_lt': 1}
        assert get_tonbag_uid(row) == f'{LOT}-001'

    def test_T709_uid_built_from_lot_and_tonbag_no(self):
        row = {'lot_no': LOT, 'tonbag_no': '005'}
        uid = get_tonbag_uid(row)
        assert LOT in uid
        assert '005' in uid


# ── 4. normalize_all_keys ─────────────────────────────────────────────────

class TestNormalizeAllKeys:

    def test_T710_sub_lt_and_customer_normalized(self):
        row = {'sub_lt': 3, 'sold_to': 'CATL', 'lot_no': LOT}
        result = normalize_all_keys(row)
        assert result['tonbag_no'] == '003'
        assert result.get('customer') == 'CATL'

    def test_T711_mxbg_pallet_normalized(self):
        row = {'mxbg_pallet': 20, 'sub_lt': 1}
        result = normalize_all_keys(row)
        assert result.get('tonbag_count') == 20

    def test_T712_normalize_all_rows_batch(self):
        rows = [{'sub_lt': i} for i in range(1, 4)]
        result = normalize_all_rows(rows)
        assert result[0]['tonbag_no'] == '001'
        assert result[2]['tonbag_no'] == '003'


# ── 5. normalize_customer_keys ────────────────────────────────────────────

class TestNormalizeCustomerKeys:

    def test_T713_sold_to_maps_to_customer(self):
        row = {'sold_to': 'BYD Co.'}
        result = normalize_customer_keys(row)
        assert result.get('customer') == 'BYD Co.'

    def test_T714_picked_to_maps_to_customer(self):
        row = {'picked_to': 'LG Energy'}
        result = normalize_customer_keys(row)
        assert result.get('customer') == 'LG Energy'

    def test_T715_existing_customer_preserved(self):
        row = {'customer': 'CATL', 'sold_to': 'OTHER'}
        result = normalize_customer_keys(row)
        assert result['customer'] == 'CATL'
