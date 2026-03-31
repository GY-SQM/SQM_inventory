# -*- coding: utf-8 -*-
"""
tests/test_v821_query_mixin.py
================================
SQM v8.2.3 — QueryMixin 단위 테스트 (25개)
============================================
커버 대상: engine_modules/inventory_modular/query_mixin.py
  Q1. get_inventory / get_all_inventory  (T01~T05)
  Q2. get_inventory_summary              (T06~T09)
  Q3. get_tonbags / get_all_tonbags      (T10~T14)
  Q4. search_lots                        (T15~T18)
  Q5. get_lot_detail                     (T19~T21)
  Q6. 공통 N+1 방지 메서드               (T22~T25)
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def eng():
    from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
    e = SQMInventoryEngineV3(':memory:')
    # 기본 LOT 2개 (1000kg 단가, 정합성 통과)
    e.add_inventory('GY-Q01', product='Lithium Carbonate',
                    net_weight=2001.0, mxbg_pallet=2)
    e.add_inventory('GY-Q02', product='Nickel Sulfate',
                    net_weight=4001.0, mxbg_pallet=4)
    yield e


# ═══════════════════════════════════════════════════════════════
# Q1. get_inventory / get_all_inventory (T01~T05)
# ═══════════════════════════════════════════════════════════════
class TestQ1GetInventory:

    def test_T01_returns_list(self, eng):
        """get_inventory → list 반환."""
        result = eng.get_inventory()
        assert isinstance(result, list)

    def test_T02_contains_inserted_lots(self, eng):
        """삽입한 LOT이 결과에 포함."""
        result = eng.get_inventory()
        lot_nos = [r.get('lot_no') or (r[1] if isinstance(r, tuple) else '')
                   for r in result]
        assert 'GY-Q01' in lot_nos
        assert 'GY-Q02' in lot_nos

    def test_T03_status_filter_available(self, eng):
        """status='AVAILABLE' 필터 동작."""
        result = eng.get_inventory(status='AVAILABLE')
        assert len(result) >= 2

    def test_T04_product_filter(self, eng):
        """product 필터 동작."""
        result = eng.get_inventory(product='Lithium Carbonate')
        assert len(result) == 1

    def test_T05_get_all_returns_all(self, eng):
        """get_all_inventory → 전체 반환."""
        result = eng.get_all_inventory()
        assert len(result) >= 2


# ═══════════════════════════════════════════════════════════════
# Q2. get_inventory_summary (T06~T09)
# ═══════════════════════════════════════════════════════════════
class TestQ2Summary:

    def test_T06_returns_dict(self, eng):
        """get_inventory_summary → dict 반환."""
        result = eng.get_inventory_summary()
        assert isinstance(result, dict)

    def test_T07_total_lots_correct(self, eng):
        """total_lots = 2."""
        result = eng.get_inventory_summary()
        assert result.get('total_lots', 0) == 2

    def test_T08_total_weight_positive(self, eng):
        """total_weight_kg > 0."""
        result = eng.get_inventory_summary()
        assert result.get('total_weight_kg', 0) > 0

    def test_T09_available_weight_lte_total(self, eng):
        """available_weight ≤ total_weight."""
        result = eng.get_inventory_summary()
        assert result.get('available_weight_kg', 0) <= result.get('total_weight_kg', 0) + 1


# ═══════════════════════════════════════════════════════════════
# Q3. get_tonbags / get_all_tonbags (T10~T14)
# ═══════════════════════════════════════════════════════════════
class TestQ3Tonbags:

    def test_T10_get_tonbags_by_lot(self, eng):
        """lot_no 필터 동작."""
        result = eng.get_tonbags(lot_no='GY-Q01')
        assert len(result) >= 2  # 일반 2개 + 샘플 1개

    def test_T11_get_all_tonbags(self, eng):
        """get_all_tonbags → 전체 반환."""
        result = eng.get_all_tonbags()
        assert len(result) >= 6  # 2+1 + 4+1

    def test_T12_tonbag_has_weight(self, eng):
        """각 톤백에 weight 필드 존재."""
        result = eng.get_tonbags(lot_no='GY-Q01')
        for tb in result:
            w = tb.get('weight') if isinstance(tb, dict) else tb[3]
            assert w is not None

    def test_T13_status_filter_available(self, eng):
        """status='AVAILABLE' 필터."""
        result = eng.get_tonbags(lot_no='GY-Q01', status='AVAILABLE')
        assert len(result) >= 1

    def test_T14_sample_included_in_all(self, eng):
        """get_all_tonbags에 샘플(sub_lt=0) 포함."""
        result = eng.get_all_tonbags()
        sub_lts = [tb.get('sub_lt') if isinstance(tb, dict) else tb[2]
                   for tb in result]
        assert 0 in sub_lts


# ═══════════════════════════════════════════════════════════════
# Q4. search_lots (T15~T18)
# ═══════════════════════════════════════════════════════════════
class TestQ4SearchLots:

    def test_T15_keyword_match(self, eng):
        """키워드 매칭."""
        result = eng.search_lots(keyword='GY-Q')
        assert len(result) >= 2

    def test_T16_keyword_no_match(self, eng):
        """매칭 없는 키워드 → 빈 list."""
        result = eng.search_lots(keyword='ZZZNOMATCH')
        assert result == [] or len(result) == 0

    def test_T17_no_keyword_returns_all(self, eng):
        """키워드 없으면 전체 반환."""
        result = eng.search_lots()
        assert len(result) >= 2

    def test_T18_exact_lot_no_match(self, eng):
        """정확한 lot_no 검색."""
        result = eng.search_lots(keyword='GY-Q01')
        assert any((r.get('lot_no') if isinstance(r, dict) else r[1]) == 'GY-Q01'
                   for r in result)


# ═══════════════════════════════════════════════════════════════
# Q5. get_lot_detail (T19~T21)
# ═══════════════════════════════════════════════════════════════
class TestQ5LotDetail:

    def test_T19_returns_dict(self, eng):
        """get_lot_detail → dict 반환."""
        result = eng.get_lot_detail('GY-Q01')
        assert isinstance(result, dict)

    def test_T20_contains_lot_no(self, eng):
        """반환값에 lot_no 포함."""
        result = eng.get_lot_detail('GY-Q01')
        assert result.get('lot_no') == 'GY-Q01'

    def test_T21_nonexistent_lot(self, eng):
        """없는 LOT → None 또는 빈 dict."""
        result = eng.get_lot_detail('NOT-EXIST')
        # 없는 LOT → None, 빈 dict, 또는 error dict 모두 허용
        assert result is None or isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════
# Q6. 공통 N+1 방지 메서드 (T22~T25)
# ═══════════════════════════════════════════════════════════════
class TestQ6N1PreventionMethods:

    def test_T22_count_tonbags_total(self, eng):
        """count_tonbags 전체 카운트."""
        cnt = eng.count_tonbags(lot_no='GY-Q01')
        assert cnt >= 3  # 일반 2 + 샘플 1

    def test_T23_count_tonbags_no_sample(self, eng):
        """count_tonbags is_sample=0 필터."""
        cnt = eng.count_tonbags(lot_no='GY-Q01', is_sample=0)
        assert cnt == 2

    def test_T24_get_inventory_map(self, eng):
        """get_inventory_map 배치 조회."""
        result = eng.get_inventory_map(['GY-Q01', 'GY-Q02'])
        assert 'GY-Q01' in result
        assert 'GY-Q02' in result

    def test_T25_get_tonbag_map(self, eng):
        """get_tonbag_map 배치 조회."""
        result = eng.get_tonbag_map(['GY-Q01'])
        # {(lot_no, sub_lt): row} 형태
        keys = list(result.keys())
        lot_nos = [k[0] for k in keys]
        assert 'GY-Q01' in lot_nos
