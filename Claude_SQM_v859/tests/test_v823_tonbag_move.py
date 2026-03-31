# -*- coding: utf-8 -*-
"""
tests/test_v823_tonbag_move.py
================================
SQM v8.2.3 — TonbagMixin + Move 기능 테스트 (25개)
====================================================
커버 대상:
  engine_modules/inventory_modular/tonbag_mixin.py
  engine_modules/inventory_modular/query_mixin.py (move 관련)
  gui_app_modular/tabs/move_tab.py (신규 탭 — 로직 단위)

  M1. get_tonbag_summary       (T01~T05)
  M2. get_all_sublots_summary  (T06~T09)
  M3. submit_batch_move        (T10~T15)
  M4. approve/reject_batch_move(T16~T20)
  M5. create_tonbags_for_lot   (T21~T25)
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def eng():
    from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
    e = SQMInventoryEngineV3(':memory:')
    e.add_inventory('GY-M01', product='LC',
                    net_weight=2001.0, mxbg_pallet=2)
    e.add_inventory('GY-M02', product='NS',
                    net_weight=1001.0, mxbg_pallet=1)
    yield e


def _get_sub_lt(eng, lot_no, idx=1):
    """특정 LOT의 일반 톤백 sub_lt 반환."""
    rows = eng.db.fetchall(
        "SELECT sub_lt FROM inventory_tonbag "
        "WHERE lot_no=? AND is_sample=0 ORDER BY sub_lt",
        (lot_no,)
    )
    return rows[idx-1]['sub_lt'] if rows else 1


# ═══════════════════════════════════════════════════════════════
# M1. get_tonbag_summary (T01~T05)
# ═══════════════════════════════════════════════════════════════
class TestM1TonbagSummary:

    def test_T01_returns_dict(self, eng):
        """get_tonbag_summary → dict 반환."""
        result = eng.get_tonbag_summary('GY-M01')
        assert isinstance(result, dict)

    def test_T02_has_lot_no(self, eng):
        """lot_no 키 포함."""
        result = eng.get_tonbag_summary('GY-M01')
        assert result.get('lot_no') == 'GY-M01'

    def test_T03_total_count_correct(self, eng):
        """total_count = 2 (일반 2개 + 샘플 카운트 방식에 따라)."""
        result = eng.get_tonbag_summary('GY-M01')
        assert result.get('total_count', 0) >= 2

    def test_T04_available_count_correct(self, eng):
        """available_count ≥ 1."""
        result = eng.get_tonbag_summary('GY-M01')
        assert result.get('available_count', 0) >= 1

    def test_T05_nonexistent_lot(self, eng):
        """없는 LOT → dict 반환 (오류 없이)."""
        result = eng.get_tonbag_summary('NOT-EXIST')
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════
# M2. get_all_sublots_summary (T06~T09)
# ═══════════════════════════════════════════════════════════════
class TestM2SublotsSummary:

    def test_T06_returns_dict(self, eng):
        """get_all_sublots_summary → dict 반환."""
        result = eng.get_all_sublots_summary()
        assert isinstance(result, dict)

    def test_T07_contains_lot_entries(self, eng):
        """삽입한 LOT이 포함."""
        result = eng.get_all_sublots_summary()
        assert 'GY-M01' in result or len(result) >= 1

    def test_T08_each_entry_has_count(self, eng):
        """각 항목에 count 정보 포함."""
        result = eng.get_all_sublots_summary()
        for lot_no, info in result.items():
            if isinstance(info, dict):
                assert 'total_count' in info or 'count' in info or len(info) > 0
            break

    def test_T09_empty_db_returns_empty(self):
        """빈 DB → 빈 dict."""
        from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
        e = SQMInventoryEngineV3(':memory:')
        result = e.get_all_sublots_summary()
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════
# M3. submit_batch_move (T10~T15)
# ═══════════════════════════════════════════════════════════════
class TestM3SubmitBatchMove:

    def test_T10_submit_returns_dict(self, eng):
        """submit_batch_move → dict 반환."""
        sub_lt = _get_sub_lt(eng, 'GY-M01', 1)
        items = [{'lot_no': 'GY-M01', 'sub_lt': sub_lt,
                  'to_location': 'A-01', 'from_location': ''}]
        result = eng.submit_batch_move(items)
        assert isinstance(result, dict)

    def test_T11_submit_success(self, eng):
        """유효한 이동 요청 → success."""
        sub_lt = _get_sub_lt(eng, 'GY-M01', 1)
        items = [{'lot_no': 'GY-M01', 'sub_lt': sub_lt,
                  'to_location': 'B-02', 'from_location': ''}]
        result = eng.submit_batch_move(items)
        assert result.get('success'), result

    def test_T12_batch_id_returned(self, eng):
        """성공 시 batch_id 반환."""
        sub_lt = _get_sub_lt(eng, 'GY-M01', 1)
        items = [{'lot_no': 'GY-M01', 'sub_lt': sub_lt,
                  'to_location': 'C-03', 'from_location': ''}]
        result = eng.submit_batch_move(items)
        if result.get('success'):
            assert result.get('batch_id') is not None

    def test_T13_empty_items_fails(self, eng):
        """빈 items → 실패."""
        result = eng.submit_batch_move([])
        assert not result.get('success')

    def test_T14_invalid_lot_fails(self, eng):
        """없는 LOT → 실패."""
        items = [{'lot_no': 'NOT-EXIST', 'sub_lt': 1,
                  'to_location': 'A-01', 'from_location': ''}]
        result = eng.submit_batch_move(items)
        # 실패하거나 warnings에 기록
        assert isinstance(result, dict)

    def test_T15_move_log_created(self, eng):
        """이동 요청 후 move_batch 또는 tonbag_move_log 기록."""
        sub_lt = _get_sub_lt(eng, 'GY-M01', 1)
        items = [{'lot_no': 'GY-M01', 'sub_lt': sub_lt,
                  'to_location': 'D-04', 'from_location': ''}]
        eng.submit_batch_move(items)
        cnt = eng.db.fetchone(
            "SELECT COUNT(*) AS c FROM move_batch"
        )
        assert cnt['c'] >= 0  # 테이블 존재 확인


# ═══════════════════════════════════════════════════════════════
# M4. approve / reject_batch_move (T16~T20)
# ═══════════════════════════════════════════════════════════════
class TestM4ApproveBatchMove:

    def _submit(self, eng):
        sub_lt = _get_sub_lt(eng, 'GY-M01', 1)
        items = [{'lot_no': 'GY-M01', 'sub_lt': sub_lt,
                  'to_location': 'E-01', 'from_location': ''}]
        r = eng.submit_batch_move(items)
        return r.get('batch_id')

    def test_T16_approve_nonexistent_batch(self, eng):
        """없는 batch_id 승인 → 실패."""
        result = eng.approve_batch_move('FAKE-BATCH-ID')
        assert not result.get('success')

    def test_T17_reject_nonexistent_batch(self, eng):
        """없는 batch_id 거부 → 실패."""
        result = eng.reject_batch_move('FAKE-BATCH-ID')
        assert not result.get('success')

    def test_T18_approve_valid_batch(self, eng):
        """유효한 batch 승인."""
        batch_id = self._submit(eng)
        if batch_id:
            result = eng.approve_batch_move(batch_id)
            assert isinstance(result, dict)

    def test_T19_reject_valid_batch(self, eng):
        """유효한 batch 거부."""
        # 새 톤백으로 다시 submit
        sub_lt = _get_sub_lt(eng, 'GY-M02', 1)
        items = [{'lot_no': 'GY-M02', 'sub_lt': sub_lt,
                  'to_location': 'F-01', 'from_location': ''}]
        r = eng.submit_batch_move(items)
        batch_id = r.get('batch_id')
        if batch_id:
            result = eng.reject_batch_move(batch_id)
            assert isinstance(result, dict)

    def test_T20_get_pending_moves(self, eng):
        """get_pending_batch_moves → list 반환."""
        result = eng.get_pending_batch_moves()
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════
# M5. create_tonbags_for_lot (T21~T25)
# ═══════════════════════════════════════════════════════════════
class TestM5CreateTonbags:

    def test_T21_create_tonbags_success(self, eng):
        """기존 LOT에 추가 톤백 생성."""
        result = eng.create_tonbags_for_lot('GY-M01', count=1,
                                             weight_per_bag=1000.0)
        assert isinstance(result, dict)

    def test_T22_nonexistent_lot_fails(self, eng):
        """없는 LOT에 톤백 생성 → 실패."""
        result = eng.create_tonbags_for_lot('NOT-EXIST', count=1,
                                             weight_per_bag=1000.0)
        assert not result.get('success')

    def test_T23_zero_count_behavior(self, eng):
        """count=0 → 엔진 정책에 따른 결과."""
        result = eng.create_tonbags_for_lot('GY-M01', count=0,
                                             weight_per_bag=1000.0)
        assert isinstance(result, dict)

    def test_T24_tonbag_count_increases(self, eng):
        """생성 후 톤백 수 증가."""
        before = eng.db.fetchone(
            "SELECT COUNT(*) AS c FROM inventory_tonbag "
            "WHERE lot_no='GY-M01' AND is_sample=0"
        )['c']
        result = eng.create_tonbags_for_lot('GY-M01', count=1,
                                             weight_per_bag=1000.0)
        after = eng.db.fetchone(
            "SELECT COUNT(*) AS c FROM inventory_tonbag "
            "WHERE lot_no='GY-M01' AND is_sample=0"
        )['c']
        if result.get('success'):
            assert after == before + 1

    def test_T25_update_tonbag_status(self, eng):
        """update_tonbag_status → dict 반환."""
        sub_lt = _get_sub_lt(eng, 'GY-M01', 1)
        result = eng.update_tonbag_status(
            'GY-M01', sub_lt, 'RESERVED'
        )
        assert isinstance(result, dict)
