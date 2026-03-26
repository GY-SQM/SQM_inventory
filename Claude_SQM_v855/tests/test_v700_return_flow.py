# -*- coding: utf-8 -*-
"""
tests/test_v700_return_flow.py
================================
SQM v7.0.0 — RETURN_AS_REINBOUND 정책 테스트 (30개)
=====================================================

[SQM RETURN POLICY v1 — RETURN_AS_REINBOUND]
  재고 엔진: 재입고처럼 처리 (UPDATE, 신규 row 금지)
  이력 엔진: return_log에 원출고 연결 유지

검증 단계:
  P1. Preflight 검증        (T01~T07)  — 반품 가능 조건
  P2. 재고 복구 정합성      (T08~T14)  — tonbag / inventory 복구
  P3. 이력 연결 무결성      (T15~T20)  — return_log ↔ outbound_log
  P4. DB 스키마 구조        (T21~T25)  — 컬럼 / 마이그레이션
  P5. 엔진 통합 + 6건 전체  (T26~T30)  — APL 반품 시나리오
"""
from engine_modules.constants import STATUS_AVAILABLE
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.fixtures.sqm_scenario_data import (
    create_scenario_db, build_scenario,
    migrate_return_log,
    LOT_TOTAL_WEIGHT_KG, TONBAGS_PER_LOT,
    RETURN_COUNT,
)
from engine_modules.return_reinbound_engine import ReturnReinboundEngine


# ─── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def db():
    """
    매 테스트마다 독립된 in-memory DB.
    return_log는 비워서 엔진 처리 전 상태로 시작.
    (시나리오 데이터는 scenario fixture로 별도 접근)
    """
    conn = create_scenario_db(":memory:")
    # 시나리오 삽입 return_log 초기화 → 엔진 중복 체크 독립성 보장
    conn.execute("DELETE FROM return_log")
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def scenario():
    return build_scenario()


@pytest.fixture
def engine(db):
    return ReturnReinboundEngine(db)


@pytest.fixture(scope="module")
def return_items(scenario):
    return scenario['returns']


# ═══════════════════════════════════════════════════════════════════════════════
# P1. Preflight 검증 (T01~T07)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP1Preflight:

    def test_T_R01_valid_outbound_passes_preflight(self, engine, scenario):
        ret = scenario['returns'][0]
        pre = engine._preflight(ret['outbound_id'], ret['lot_no'])
        assert pre.ok is True
        assert pre.errors == []

    def test_T_R02_unknown_outbound_fails_preflight(self, engine, scenario):
        pre = engine._preflight('OUT_NOTEXIST', scenario['returns'][0]['lot_no'])
        assert pre.ok is False
        assert any('출고 이력 없음' in e for e in pre.errors)

    def test_T_R03_lot_mismatch_fails_preflight(self, engine, scenario):
        ret0 = scenario['returns'][0]
        ret1 = scenario['returns'][1]
        pre = engine._preflight(ret0['outbound_id'], ret1['lot_no'])
        assert pre.ok is False
        assert any('LOT 불일치' in e for e in pre.errors)

    def test_T_R04_duplicate_return_fails_preflight(self, engine, scenario):
        ret = scenario['returns'][0]
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location='B-01-01-01',
        )
        pre = engine._preflight(ret['outbound_id'], ret['lot_no'])
        assert pre.ok is False
        assert any('이미 반품' in e for e in pre.errors)

    def test_T_R05_preflight_loads_outbound_row(self, engine, scenario):
        ret = scenario['returns'][0]
        pre = engine._preflight(ret['outbound_id'], ret['lot_no'])
        assert pre.outbound_row is not None
        assert pre.outbound_row['lot_no'] == ret['lot_no']

    def test_T_R06_preflight_loads_tonbag_rows(self, engine, scenario):
        ret = scenario['returns'][0]
        pre = engine._preflight(ret['outbound_id'], ret['lot_no'])
        assert len(pre.tonbag_rows) == TONBAGS_PER_LOT + 1

    def test_T_R07_preflight_errors_are_list(self, engine):
        pre = engine._preflight('INVALID', 'INVALID_LOT')
        assert isinstance(pre.errors, list)
        assert len(pre.errors) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# P2. 재고 복구 정합성 (T08~T14)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP2InventoryRestore:

    def test_T_R08_process_returns_ok_true(self, engine, scenario):
        ret = scenario['returns'][0]
        result = engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location='B-02-03-01',
        )
        assert result.ok is True

    def test_T_R09_tonbag_status_becomes_available(self, engine, db, scenario):
        ret = scenario['returns'][0]
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location='B-02-03-01',
        )
        statuses = [
            r[0] for r in db.execute(
                "SELECT status FROM inventory_tonbag WHERE lot_no=?",
                (ret['lot_no'],)
            ).fetchall()
        ]
        assert all(s == STATUS_AVAILABLE for s in statuses)

    def test_T_R10_tonbag_location_updated_to_new_location(self, engine, db, scenario):
        new_loc = 'B-05-02-03'
        ret = scenario['returns'][0]
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location=new_loc,
        )
        locs = [
            r[0] for r in db.execute(
                "SELECT location FROM inventory_tonbag WHERE lot_no=?",
                (ret['lot_no'],)
            ).fetchall()
        ]
        assert all(l == new_loc for l in locs)

    def test_T_R11_no_new_tonbag_row_inserted(self, engine, db, scenario):
        """핵심: 신규 row 삽입 없음 — tonbag_uid UNIQUE 보장"""
        lot_no = scenario['returns'][0]['lot_no']
        before = db.execute(
            "SELECT COUNT(*) FROM inventory_tonbag WHERE lot_no=?",
            (lot_no,)
        ).fetchone()[0]
        ret = scenario['returns'][0]
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=lot_no,
            new_location='B-01-01-01',
        )
        after = db.execute(
            "SELECT COUNT(*) FROM inventory_tonbag WHERE lot_no=?",
            (lot_no,)
        ).fetchone()[0]
        assert before == after

    def test_T_R12_lot_current_weight_restored(self, engine, db, scenario):
        ret = scenario['returns'][0]
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location='B-01-01-01',
        )
        row = db.execute(
            "SELECT current_weight, total_weight_kg FROM inventory WHERE lot_no=?",
            (ret['lot_no'],)
        ).fetchone()
        assert abs(row[0] - row[1]) < 0.01

    def test_T_R13_lot_status_becomes_available(self, engine, db, scenario):
        ret = scenario['returns'][0]
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location='B-01-01-01',
        )
        status = db.execute(
            "SELECT status FROM inventory WHERE lot_no=?",
            (ret['lot_no'],)
        ).fetchone()[0]
        assert status == STATUS_AVAILABLE

    def test_T_R14_weight_invariant_5001kg_preserved(self, engine, db, scenario):
        ret = scenario['returns'][0]
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location='B-01-01-01',
        )
        w = db.execute(
            "SELECT total_weight_kg FROM inventory WHERE lot_no=?",
            (ret['lot_no'],)
        ).fetchone()[0]
        assert abs(w - LOT_TOTAL_WEIGHT_KG) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# P3. 이력 연결 무결성 (T15~T20)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP3AuditLinkage:

    def test_T_R15_return_log_row_inserted(self, engine, db, scenario):
        ret = scenario['returns'][0]
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location='B-01-01-01',
        )
        cnt = db.execute(
            "SELECT COUNT(*) FROM return_log WHERE outbound_id=?",
            (ret['outbound_id'],)
        ).fetchone()[0]
        assert cnt >= 1

    def test_T_R16_return_log_processed_as_is_reinbound(self, engine, db, scenario):
        ret = scenario['returns'][0]
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location='B-01-01-01',
        )
        row = db.execute(
            "SELECT processed_as FROM return_log WHERE outbound_id=? "
            "ORDER BY rowid DESC LIMIT 1",
            (ret['outbound_id'],)
        ).fetchone()
        assert row[0] == 'REINBOUND'

    def test_T_R17_return_log_new_location_saved(self, engine, db, scenario):
        new_loc = 'B-07-03-04'
        ret = scenario['returns'][0]
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location=new_loc,
        )
        row = db.execute(
            "SELECT new_location FROM return_log WHERE outbound_id=? "
            "ORDER BY rowid DESC LIMIT 1",
            (ret['outbound_id'],)
        ).fetchone()
        assert row[0] == new_loc

    def test_T_R18_outbound_log_row_not_modified(self, engine, db, scenario):
        """outbound_log 절대 불변 원칙 검증"""
        ret = scenario['returns'][0]
        before = dict(db.execute(
            "SELECT * FROM outbound_log WHERE outbound_id=?",
            (ret['outbound_id'],)
        ).fetchone())
        engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location='B-01-01-01',
        )
        after = dict(db.execute(
            "SELECT * FROM outbound_log WHERE outbound_id=?",
            (ret['outbound_id'],)
        ).fetchone())
        assert before == after

    def test_T_R19_return_id_format_rtn_prefix(self, engine, scenario):
        ret = scenario['returns'][0]
        result = engine.process(
            outbound_id=ret['outbound_id'],
            lot_no=ret['lot_no'],
            new_location='B-01-01-01',
        )
        assert result.return_id.startswith('RTN-')

    def test_T_R20_get_return_summary_counts_correctly(self, engine, scenario):
        for i, ret in enumerate(scenario['returns'][:3]):
            engine.process(
                outbound_id=ret['outbound_id'],
                lot_no=ret['lot_no'],
                new_location=f'B-0{i+1}-01-01',
            )
        summary = engine.get_return_summary()
        assert summary['total_count'] >= 3
        assert summary['total_weight_kg'] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# P4. DB 스키마 구조 (T21~T25)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP4Schema:

    def test_T_R21_return_log_has_processed_as_column(self, db):
        cols = {r[1] for r in db.execute("PRAGMA table_info(return_log)")}
        assert 'processed_as' in cols

    def test_T_R22_return_log_has_new_location_column(self, db):
        cols = {r[1] for r in db.execute("PRAGMA table_info(return_log)")}
        assert 'new_location' in cols

    def test_T_R23_return_log_has_operator_id_column(self, db):
        cols = {r[1] for r in db.execute("PRAGMA table_info(return_log)")}
        assert 'operator_id' in cols

    def test_T_R24_migrate_return_log_idempotent(self, db):
        """migrate_return_log 중복 호출 — 멱등성 보장"""
        result1 = migrate_return_log(db)
        result2 = migrate_return_log(db)
        assert result1['ok'] is True
        assert result2['ok'] is True
        assert result2['added'] == []

    def test_T_R25_scenario_returns_have_processed_as_field(self, scenario):
        for ret in scenario['returns']:
            assert ret.get('processed_as') == 'REINBOUND'
            assert ret.get('new_location') is not None
            assert ret['new_location'].startswith('B-')


# ═══════════════════════════════════════════════════════════════════════════════
# P5. 엔진 통합 + APL 반품 6건 전체 (T26~T30)
# ═══════════════════════════════════════════════════════════════════════════════

class TestP5FullScenario:

    def test_T_R26_all_6_returns_process_ok(self, db, scenario):
        engine = ReturnReinboundEngine(db)
        results = [
            engine.process(
                outbound_id=ret['outbound_id'],
                lot_no=ret['lot_no'],
                new_location=ret['new_location'],
                reason=ret['reason'],
            )
            for ret in scenario['returns']
        ]
        assert all(r.ok for r in results), \
            [r.error for r in results if not r.ok]

    def test_T_R27_after_6_returns_all_lots_available(self, db, scenario):
        engine = ReturnReinboundEngine(db)
        for ret in scenario['returns']:
            engine.process(
                outbound_id=ret['outbound_id'],
                lot_no=ret['lot_no'],
                new_location=ret['new_location'],
            )
        for ret in scenario['returns']:
            status = db.execute(
                "SELECT status FROM inventory WHERE lot_no=?",
                (ret['lot_no'],)
            ).fetchone()[0]
            assert status == STATUS_AVAILABLE

    def test_T_R28_after_6_returns_weight_invariant_all_lots(self, db, scenario):
        """반품 6건 후 전체 60 LOT 중량 불변 — 최우선 불변 조건"""
        engine = ReturnReinboundEngine(db)
        for ret in scenario['returns']:
            engine.process(
                outbound_id=ret['outbound_id'],
                lot_no=ret['lot_no'],
                new_location=ret['new_location'],
            )
        bad = db.execute(
            "SELECT COUNT(*) FROM inventory "
            "WHERE ABS(total_weight_kg - ?) > 0.01",
            (LOT_TOTAL_WEIGHT_KG,)
        ).fetchone()[0]
        assert bad == 0

    def test_T_R29_return_log_count_6_after_engine_calls(self, db, scenario):
        """엔진 처리 6건 → return_log 6건 (초기 상태: 비어있음)"""
        engine = ReturnReinboundEngine(db)
        for ret in scenario['returns']:
            engine.process(
                outbound_id=ret['outbound_id'],
                lot_no=ret['lot_no'],
                new_location=ret['new_location'],
            )
        cnt = db.execute("SELECT COUNT(*) FROM return_log").fetchone()[0]
        assert cnt == RETURN_COUNT

    def test_T_R30_all_return_logs_linked_to_outbound(self, db, scenario):
        """return_log.outbound_id → outbound_log FK 무결성 (0 orphans)"""
        engine = ReturnReinboundEngine(db)
        for ret in scenario['returns']:
            engine.process(
                outbound_id=ret['outbound_id'],
                lot_no=ret['lot_no'],
                new_location=ret['new_location'],
            )
        orphans = db.execute("""
            SELECT COUNT(*) FROM return_log r
            LEFT JOIN outbound_log o ON r.outbound_id = o.outbound_id
            WHERE o.outbound_id IS NULL
        """).fetchone()[0]
        assert orphans == 0
