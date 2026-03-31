# -*- coding: utf-8 -*-
"""
tests/test_v700_db_insert.py
==============================
SQM v7.0.0 — DB INSERT 정합성 테스트 (25개)
=============================================

실제 SQLite DB에 시나리오 데이터를 INSERT하고
SQL 쿼리 수준에서 데이터 무결성을 검증합니다.

단계:
  D1. 기본 카운트 검증     (T01~T05)
  D2. 중량 정합성 검증     (T06~T10)
  D3. FK 참조 무결성       (T11~T15)
  D4. 상태 일관성 검증     (T16~T20)
  D5. 고객사별 데이터 검증  (T21~T25)
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.fixtures.sqm_scenario_data import (
    create_scenario_db, LOT_TOTAL_WEIGHT_KG,
)


@pytest.fixture(scope="module")
def db():
    conn = create_scenario_db(":memory:")
    yield conn
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# D1. 기본 카운트 검증 (T01~T05)
# ═══════════════════════════════════════════════════════════════════════════════

class TestD1BasicCounts:

    def test_T_D01_vessel_count_3(self, db):
        cnt = db.execute("SELECT COUNT(*) FROM vessel_master").fetchone()[0]
        assert cnt == 3

    def test_T_D02_container_count_15(self, db):
        cnt = db.execute("SELECT COUNT(*) FROM container_master").fetchone()[0]
        assert cnt == 15

    def test_T_D03_lot_count_60(self, db):
        cnt = db.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        assert cnt == 60

    def test_T_D04_tonbag_count_660(self, db):
        cnt = db.execute("SELECT COUNT(*) FROM inventory_tonbag").fetchone()[0]
        assert cnt == 660

    def test_T_D05_outbound_count_30(self, db):
        cnt = db.execute("SELECT COUNT(*) FROM outbound_log").fetchone()[0]
        assert cnt == 30


# ═══════════════════════════════════════════════════════════════════════════════
# D2. 중량 정합성 검증 (T06~T10)
# ═══════════════════════════════════════════════════════════════════════════════

class TestD2WeightIntegrity:

    def test_T_D06_total_weight_is_300_1MT(self, db):
        """전체 총중량 = 60 LOT × 5,001kg = 300,060kg = 300.06MT"""
        total = db.execute(
            "SELECT SUM(total_weight_kg) FROM inventory"
        ).fetchone()[0]
        assert abs(total - 60 * LOT_TOTAL_WEIGHT_KG) < 0.1

    def test_T_D07_every_lot_weight_is_5001kg(self, db):
        """모든 LOT의 total_weight_kg = 5,001"""
        bad = db.execute(
            "SELECT COUNT(*) FROM inventory WHERE ABS(total_weight_kg - ?) > 0.01",
            (LOT_TOTAL_WEIGHT_KG,)
        ).fetchone()[0]
        assert bad == 0, f"중량 불일치 LOT {bad}개"

    def test_T_D08_normal_tonbag_weight_is_500kg(self, db):
        bad = db.execute(
            "SELECT COUNT(*) FROM inventory_tonbag "
            "WHERE is_sample=0 AND ABS(weight_kg - 500.0) > 0.01"
        ).fetchone()[0]
        assert bad == 0

    def test_T_D09_sample_tonbag_weight_is_1kg(self, db):
        bad = db.execute(
            "SELECT COUNT(*) FROM inventory_tonbag "
            "WHERE is_sample=1 AND ABS(weight_kg - 1.0) > 0.01"
        ).fetchone()[0]
        assert bad == 0

    def test_T_D10_lot_tonbag_sum_equals_lot_weight(self, db):
        """LOT별 톤백 합계 = LOT 총중량 (SQL JOIN 검증)"""
        rows = db.execute("""
            SELECT i.lot_no,
                   i.total_weight_kg,
                   SUM(t.weight_kg) as tonbag_sum
            FROM inventory i
            JOIN inventory_tonbag t ON i.lot_no = t.lot_no
            GROUP BY i.lot_no
            HAVING ABS(i.total_weight_kg - tonbag_sum) > 0.01
        """).fetchall()
        assert len(rows) == 0, f"톤백 합계 불일치 LOT {len(rows)}개"


# ═══════════════════════════════════════════════════════════════════════════════
# D3. FK 참조 무결성 (T11~T15)
# ═══════════════════════════════════════════════════════════════════════════════

class TestD3FKIntegrity:

    def test_T_D11_no_orphan_tonbags(self, db):
        """고아 톤백 없음 (lot_no FK)"""
        orphans = db.execute("""
            SELECT COUNT(*) FROM inventory_tonbag t
            LEFT JOIN inventory i ON t.lot_no = i.lot_no
            WHERE i.lot_no IS NULL
        """).fetchone()[0]
        assert orphans == 0

    def test_T_D12_no_orphan_lots(self, db):
        """고아 LOT 없음 (container_id FK)"""
        orphans = db.execute("""
            SELECT COUNT(*) FROM inventory i
            LEFT JOIN container_master c ON i.container_id = c.container_id
            WHERE c.container_id IS NULL
        """).fetchone()[0]
        assert orphans == 0

    def test_T_D13_no_orphan_containers(self, db):
        """고아 컨테이너 없음 (vessel_id FK)"""
        orphans = db.execute("""
            SELECT COUNT(*) FROM container_master c
            LEFT JOIN vessel_master v ON c.vessel_id = v.vessel_id
            WHERE v.vessel_id IS NULL
        """).fetchone()[0]
        assert orphans == 0

    def test_T_D14_all_outbound_lots_exist_in_inventory(self, db):
        orphans = db.execute("""
            SELECT COUNT(*) FROM outbound_log o
            LEFT JOIN inventory i ON o.lot_no = i.lot_no
            WHERE i.lot_no IS NULL
        """).fetchone()[0]
        assert orphans == 0

    def test_T_D15_all_return_outbound_ids_exist(self, db):
        orphans = db.execute("""
            SELECT COUNT(*) FROM return_log r
            LEFT JOIN outbound_log o ON r.outbound_id = o.outbound_id
            WHERE o.outbound_id IS NULL
        """).fetchone()[0]
        assert orphans == 0


# ═══════════════════════════════════════════════════════════════════════════════
# D4. 상태 일관성 검증 (T16~T20)
# ═══════════════════════════════════════════════════════════════════════════════

class TestD4StatusConsistency:

    def test_T_D16_all_inventory_status_available(self, db):
        """시나리오 초기 상태: 전체 AVAILABLE"""
        bad = db.execute(
            "SELECT COUNT(*) FROM inventory WHERE status != 'AVAILABLE'"
        ).fetchone()[0]
        assert bad == 0

    def test_T_D17_all_tonbag_status_available(self, db):
        bad = db.execute(
            "SELECT COUNT(*) FROM inventory_tonbag WHERE status != 'AVAILABLE'"
        ).fetchone()[0]
        assert bad == 0

    def test_T_D18_all_outbound_status_sold(self, db):
        bad = db.execute(
            "SELECT COUNT(*) FROM outbound_log WHERE status != 'SOLD'"
        ).fetchone()[0]
        assert bad == 0

    def test_T_D19_duplicate_lot_no_not_exist(self, db):
        dupes = db.execute("""
            SELECT COUNT(*) FROM (
                SELECT lot_no FROM inventory GROUP BY lot_no HAVING COUNT(*) > 1
            )
        """).fetchone()[0]
        assert dupes == 0

    def test_T_D20_duplicate_tonbag_uid_not_exist(self, db):
        dupes = db.execute("""
            SELECT COUNT(*) FROM (
                SELECT tonbag_uid FROM inventory_tonbag
                GROUP BY tonbag_uid HAVING COUNT(*) > 1
            )
        """).fetchone()[0]
        assert dupes == 0


# ═══════════════════════════════════════════════════════════════════════════════
# D5. 고객사별 데이터 검증 (T21~T25)
# ═══════════════════════════════════════════════════════════════════════════════

class TestD5CustomerData:

    def test_T_D21_catl_allocation_count_12(self, db):
        cnt = db.execute(
            "SELECT COUNT(*) FROM allocation_plan WHERE customer='CATL'"
        ).fetchone()[0]
        assert cnt == 12

    def test_T_D22_byd_allocation_count_10(self, db):
        cnt = db.execute(
            "SELECT COUNT(*) FROM allocation_plan WHERE customer='BYD'"
        ).fetchone()[0]
        assert cnt == 10

    def test_T_D23_lge_allocation_count_8(self, db):
        cnt = db.execute(
            "SELECT COUNT(*) FROM allocation_plan "
            "WHERE customer='LG Energy Solution'"
        ).fetchone()[0]
        assert cnt == 8

    def test_T_D24_allocation_always_10days_before_ship(self, db):
        bad = db.execute("""
            SELECT COUNT(*) FROM allocation_plan
            WHERE CAST(
                (julianday(ship_date) - julianday(alloc_date))
            AS INTEGER) != 10
        """).fetchone()[0]
        assert bad == 0

    def test_T_D25_picking_always_5days_before_ship(self, db):
        bad = db.execute("""
            SELECT COUNT(*) FROM picking_list
            WHERE CAST(
                (julianday(ship_date) - julianday(pick_date))
            AS INTEGER) != 5
        """).fetchone()[0]
        assert bad == 0
