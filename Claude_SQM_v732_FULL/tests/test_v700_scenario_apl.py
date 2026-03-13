# -*- coding: utf-8 -*-
"""
tests/test_v700_scenario_apl.py
================================
SQM v7.0.0 — APL 3항차 입출고 시나리오 자동화 테스트 (45개)
==============================================================

시나리오:
  APL 3척 × 5컨테이너 × 4LOT × (10톤백×500kg + 샘플1kg)
  입고: 2026-03-01 ~ 04-15
  출고: 2026-05-01 ~ 06-30 (50% / CATL·BYD·LGE)
  반품: 출고 후 15~30일 (출고분 20%)
  이동: 미출고 30% 위치 변경

단계:
  S1. 데이터 구조 검증 (T01~T10)
  S2. 입고 무결성 검증 (T11~T20)
  S3. 출고 흐름 검증   (T21~T30)
  S4. 반품 검증         (T31~T35)
  S5. 위치이동 검증     (T36~T40)
  S6. Allocation/Picking (T41~T45)
"""
from engine_modules.constants import STATUS_AVAILABLE
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.fixtures.sqm_scenario_data import (
    build_scenario, create_scenario_db,
    VESSELS_COUNT, CONTAINERS_PER_VESSEL, LOT_TOTAL_WEIGHT_KG,
    TOTAL_OUTBOUND_LOTS, RETURN_COUNT, MOVE_COUNT,
    INBOUND_START, INBOUND_END,
    OUTBOUND_START, OUTBOUND_END,
)
from datetime import date


# ─── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def scenario():
    """모듈 범위 시나리오 데이터 (1회 생성)"""
    return build_scenario()


@pytest.fixture(scope="module")
def conn():
    """모듈 범위 SQLite DB (1회 INSERT)"""
    c = create_scenario_db(":memory:")
    yield c
    c.close()


# ═══════════════════════════════════════════════════════════════════════════════
# S1. 데이터 구조 검증 (T01~T10)
# ═══════════════════════════════════════════════════════════════════════════════

class TestS1DataStructure:

    def test_T01_vessel_count_is_3(self, scenario):
        assert len(scenario['vessels']) == VESSELS_COUNT

    def test_T02_container_count_is_15(self, scenario):
        assert len(scenario['containers']) == VESSELS_COUNT * CONTAINERS_PER_VESSEL

    def test_T03_lot_count_is_60(self, scenario):
        assert len(scenario['lots']) == 60

    def test_T04_tonbag_total_is_660(self, scenario):
        assert len(scenario['tonbags']) == 660

    def test_T05_normal_tonbag_count_is_600(self, scenario):
        normals = [t for t in scenario['tonbags'] if not t['is_sample']]
        assert len(normals) == 600

    def test_T06_sample_count_equals_lot_count(self, scenario):
        samples = [t for t in scenario['tonbags'] if t['is_sample']]
        assert len(samples) == len(scenario['lots'])

    def test_T07_outbound_count_is_30(self, scenario):
        assert len(scenario['outbounds']) == TOTAL_OUTBOUND_LOTS

    def test_T08_return_count_is_6(self, scenario):
        assert len(scenario['returns']) == RETURN_COUNT

    def test_T09_move_count_is_9(self, scenario):
        assert len(scenario['moves']) == MOVE_COUNT

    def test_T10_allocation_count_equals_outbound_count(self, scenario):
        assert len(scenario['allocations']) == len(scenario['outbounds'])


# ═══════════════════════════════════════════════════════════════════════════════
# S2. 입고 무결성 검증 (T11~T20)
# ═══════════════════════════════════════════════════════════════════════════════

class TestS2InboundIntegrity:

    def test_T11_every_lot_weight_is_5001kg(self, scenario):
        """핵심 불변조건: 1 LOT = 5001kg (500×10+1)"""
        for lot in scenario['lots']:
            assert lot['total_weight_kg'] == LOT_TOTAL_WEIGHT_KG, \
                f"LOT {lot['lot_no']}: {lot['total_weight_kg']} ≠ {LOT_TOTAL_WEIGHT_KG}"

    def test_T12_tonbag_uid_format_correct(self, scenario):
        """tonbag_uid = lot_no-001 형식"""
        for tb in scenario['tonbags']:
            uid = tb['tonbag_uid']
            assert '-' in uid
            parts = uid.split('-')
            assert len(parts) == 2
            assert parts[0] == tb['lot_no']

    def test_T13_sample_tonbag_no_is_S00(self, scenario):
        samples = [t for t in scenario['tonbags'] if t['is_sample']]
        for s in samples:
            assert s['tonbag_no'] == 'S00'
            assert s['tonbag_uid'].endswith('-S00')

    def test_T14_normal_tonbag_no_is_3digits(self, scenario):
        normals = [t for t in scenario['tonbags'] if not t['is_sample']]
        for t in normals:
            assert len(t['tonbag_no']) == 3
            assert t['tonbag_no'].isdigit()

    def test_T15_arrival_dates_within_range(self, scenario):
        for lot in scenario['lots']:
            d = date.fromisoformat(lot['arrival_date'])
            assert INBOUND_START <= d <= INBOUND_END, \
                f"입고일 범위 초과: {lot['lot_no']} = {d}"

    def test_T16_location_format_A_XX_XX_XX(self, scenario):
        """입고 초기 로케이션 형식: A-01-01-01"""
        import re
        pat = re.compile(r'^[AB]-\d{2}-\d{2}-\d{2}$')
        for lot in scenario['lots']:
            assert pat.match(lot['location']), \
                f"Location 형식 오류: {lot['location']}"

    def test_T17_lot_no_starts_with_112(self, scenario):
        for lot in scenario['lots']:
            assert lot['lot_no'].startswith('112')
            assert len(lot['lot_no']) == 10

    def test_T18_all_lots_linked_to_container(self, scenario):
        container_ids = {c['container_id'] for c in scenario['containers']}
        for lot in scenario['lots']:
            assert lot['container_id'] in container_ids

    def test_T19_all_containers_linked_to_vessel(self, scenario):
        vessel_ids = {v['vessel_id'] for v in scenario['vessels']}
        for ctr in scenario['containers']:
            assert ctr['vessel_id'] in vessel_ids

    def test_T20_db_lot_count_is_60(self, conn):
        cnt = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        assert cnt == 60


# ═══════════════════════════════════════════════════════════════════════════════
# S3. 출고 흐름 검증 (T21~T30)
# ═══════════════════════════════════════════════════════════════════════════════

class TestS3OutboundFlow:

    def test_T21_outbound_ratio_is_50pct(self, scenario):
        total = len(scenario['lots'])
        outbound = len(scenario['outbounds'])
        ratio = outbound / total
        assert abs(ratio - 0.5) < 0.01, f"출고비율: {ratio:.2%}"

    def test_T22_catl_gets_12_lots(self, scenario):
        catl = [o for o in scenario['outbounds'] if o['customer'] == 'CATL']
        assert len(catl) == 12

    def test_T23_byd_gets_10_lots(self, scenario):
        byd = [o for o in scenario['outbounds'] if o['customer'] == 'BYD']
        assert len(byd) == 10

    def test_T24_lge_gets_8_lots(self, scenario):
        lge = [o for o in scenario['outbounds']
               if o['customer'] == 'LG Energy Solution']
        assert len(lge) == 8

    def test_T25_ship_dates_within_range(self, scenario):
        for ob in scenario['outbounds']:
            d = date.fromisoformat(ob['ship_date'])
            assert OUTBOUND_START <= d <= OUTBOUND_END

    def test_T26_outbound_weight_equals_lot_weight(self, scenario):
        for ob in scenario['outbounds']:
            assert ob['weight_kg'] == LOT_TOTAL_WEIGHT_KG

    def test_T27_no_lot_outbound_twice(self, scenario):
        lot_nos = [o['lot_no'] for o in scenario['outbounds']]
        assert len(lot_nos) == len(set(lot_nos)), "중복 출고 LOT 발견"

    def test_T28_db_outbound_log_count_is_30(self, conn):
        cnt = conn.execute("SELECT COUNT(*) FROM outbound_log").fetchone()[0]
        assert cnt == 30

    def test_T29_db_customer_distribution_correct(self, conn):
        rows = conn.execute(
            "SELECT customer, COUNT(*) as cnt FROM outbound_log GROUP BY customer"
        ).fetchall()
        dist = {r['customer']: r['cnt'] for r in rows}
        assert dist.get('CATL') == 12
        assert dist.get('BYD') == 10
        assert dist.get('LG Energy Solution') == 8

    def test_T30_remaining_lots_still_available(self, scenario):
        outbound_lot_nos = {o['lot_no'] for o in scenario['outbounds']}
        remaining = [l for l in scenario['lots']
                     if l['lot_no'] not in outbound_lot_nos]
        assert len(remaining) == 30
        for lot in remaining:
            assert lot['status'] == STATUS_AVAILABLE


# ═══════════════════════════════════════════════════════════════════════════════
# S4. 반품 검증 (T31~T35)
# ═══════════════════════════════════════════════════════════════════════════════

class TestS4Returns:

    def test_T31_return_count_is_6(self, scenario):
        assert len(scenario['returns']) == RETURN_COUNT

    def test_T32_return_ratio_of_outbound_is_20pct(self, scenario):
        ratio = len(scenario['returns']) / len(scenario['outbounds'])
        assert abs(ratio - 0.20) < 0.01

    def test_T33_return_date_after_ship_date(self, scenario):
        ob_map = {o['outbound_id']: o['ship_date']
                  for o in scenario['outbounds']}
        for ret in scenario['returns']:
            ship = date.fromisoformat(ob_map[ret['outbound_id']])
            rdate = date.fromisoformat(ret['return_date'])
            assert rdate > ship, \
                f"반품일({rdate})이 출고일({ship}) 이전"

    def test_T34_return_delay_is_15_to_30_days(self, scenario):
        ob_map = {o['outbound_id']: o['ship_date']
                  for o in scenario['outbounds']}
        for ret in scenario['returns']:
            ship  = date.fromisoformat(ob_map[ret['outbound_id']])
            rdate = date.fromisoformat(ret['return_date'])
            delay = (rdate - ship).days
            assert 15 <= delay <= 30, f"반품 지연 {delay}일 범위 초과"

    def test_T35_db_return_log_count_is_6(self, conn):
        cnt = conn.execute("SELECT COUNT(*) FROM return_log").fetchone()[0]
        assert cnt == 6


# ═══════════════════════════════════════════════════════════════════════════════
# S5. 위치이동 검증 (T36~T40)
# ═══════════════════════════════════════════════════════════════════════════════

class TestS5LocationMove:

    def test_T36_move_count_is_9(self, scenario):
        assert len(scenario['moves']) == MOVE_COUNT

    def test_T37_move_ratio_of_remaining_is_30pct(self, scenario):
        remaining = 30  # 미출고 LOT
        ratio = len(scenario['moves']) / remaining
        assert abs(ratio - 0.30) < 0.01

    def test_T38_moved_to_B_zone(self, scenario):
        """이동 목적지는 B존"""
        for mv in scenario['moves']:
            assert mv['to_location'].startswith('B-'), \
                f"이동 목적지 B존 아님: {mv['to_location']}"

    def test_T39_from_and_to_locations_differ(self, scenario):
        for mv in scenario['moves']:
            assert mv['from_location'] != mv['to_location']

    def test_T40_db_move_log_count_is_9(self, conn):
        """v6.6.0: location_move_log → stock_movement.RELOCATE 통합 검증"""
        cnt = conn.execute(
            "SELECT COUNT(*) FROM stock_movement WHERE movement_type='RELOCATE'"
        ).fetchone()[0]
        assert cnt == 9


# ═══════════════════════════════════════════════════════════════════════════════
# S6. Allocation / Picking List 검증 (T41~T45)
# ═══════════════════════════════════════════════════════════════════════════════

class TestS6AllocationPicking:

    def test_T41_allocation_10days_before_ship(self, scenario):
        for alloc in scenario['allocations']:
            ship  = date.fromisoformat(alloc['ship_date'])
            alloc_d = date.fromisoformat(alloc['alloc_date'])
            diff = (ship - alloc_d).days
            assert diff == 10, \
                f"Allocation이 출고 {diff}일 전 (10일 아님)"

    def test_T42_picking_5days_before_ship(self, scenario):
        for pick in scenario['picking']:
            ship   = date.fromisoformat(pick['ship_date'])
            pick_d = date.fromisoformat(pick['pick_date'])
            diff   = (ship - pick_d).days
            assert diff == 5, \
                f"Picking이 출고 {diff}일 전 (5일 아님)"

    def test_T43_allocation_before_picking(self, scenario):
        pick_map = {p['lot_no']: p['pick_date']
                    for p in scenario['picking']}
        for alloc in scenario['allocations']:
            alloc_d = date.fromisoformat(alloc['alloc_date'])
            pick_d  = date.fromisoformat(pick_map[alloc['lot_no']])
            assert alloc_d < pick_d, \
                f"Allocation({alloc_d}) ≥ Picking({pick_d})"

    def test_T44_db_allocation_count_is_30(self, conn):
        cnt = conn.execute(
            "SELECT COUNT(*) FROM allocation_plan"
        ).fetchone()[0]
        assert cnt == 30

    def test_T45_db_picking_list_count_is_30(self, conn):
        cnt = conn.execute(
            "SELECT COUNT(*) FROM picking_list"
        ).fetchone()[0]
        assert cnt == 30
