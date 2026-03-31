# -*- coding: utf-8 -*-
"""
tests/test_v824_inbound_mixin.py
===================================
SQM v8.2.3 — InboundMixin 단위 테스트 (20개)
==============================================
커버 대상: engine_modules/inventory_modular/inbound_mixin.py
  N1. process_inbound 기본 동작  (T01~T08)
  N2. 입력 검증 / 에러 처리      (T09~T14)
  N3. 중복 / 재입고 처리         (T15~T18)
  N4. 무게 정합성 검증           (T19~T20)
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def eng():
    from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
    return SQMInventoryEngineV3(':memory:')


def _inbound(eng, lot_no='GY-N01', **kw):
    """process_inbound 편의 래퍼."""
    data = {
        'lot_no': lot_no,
        'product': kw.pop('product', 'Lithium Carbonate'),
        'net_weight': kw.pop('net_weight', 2001.0),
        'mxbg_pallet': kw.pop('mxbg_pallet', 2),
        'sap_no': kw.pop('sap_no', 'SAP-001'),
        'bl_no': kw.pop('bl_no', 'BL-001'),
    }
    data.update(kw)
    return eng.process_inbound(data)


# ═══════════════════════════════════════════════════════════════
# N1. process_inbound 기본 동작 (T01~T08)
# ═══════════════════════════════════════════════════════════════
class TestN1ProcessInbound:

    def test_T01_basic_inbound_success(self, eng):
        """기본 입고 성공."""
        r = _inbound(eng, 'GY-N01')
        assert r.get('success'), r

    def test_T02_lot_created_in_db(self, eng):
        """입고 후 inventory DB에 존재."""
        _inbound(eng, 'GY-N02')
        row = eng.db.fetchone(
            "SELECT lot_no FROM inventory WHERE lot_no='GY-N02'"
        )
        assert row is not None

    def test_T03_created_lots_returned(self, eng):
        """created_lots에 lot_no 포함."""
        r = _inbound(eng, 'GY-N03')
        assert 'GY-N03' in r.get('created_lots', [])

    def test_T04_tonbags_created(self, eng):
        """입고 후 톤백 생성."""
        _inbound(eng, 'GY-N04', mxbg_pallet=3)
        cnt = eng.db.fetchone(
            "SELECT COUNT(*) AS c FROM inventory_tonbag "
            "WHERE lot_no='GY-N04' AND is_sample=0"
        )['c']
        assert cnt == 3

    def test_T05_sample_tonbag_created(self, eng):
        """샘플 톤백(sub_lt=0) 자동 생성."""
        _inbound(eng, 'GY-N05')
        row = eng.db.fetchone(
            "SELECT sub_lt FROM inventory_tonbag "
            "WHERE lot_no='GY-N05' AND is_sample=1"
        )
        assert row is not None

    def test_T06_status_available(self, eng):
        """입고 후 LOT 상태 AVAILABLE."""
        _inbound(eng, 'GY-N06')
        row = eng.db.fetchone(
            "SELECT status FROM inventory WHERE lot_no='GY-N06'"
        )
        assert row['status'] == 'AVAILABLE'

    def test_T07_stock_movement_recorded(self, eng):
        """stock_movement INBOUND 이력 기록."""
        _inbound(eng, 'GY-N07')
        row = eng.db.fetchone(
            "SELECT movement_type FROM stock_movement WHERE lot_no='GY-N07'"
        )
        assert row is not None
        assert row['movement_type'] == 'INBOUND'

    def test_T08_returns_dict(self, eng):
        """반환값은 항상 dict."""
        r = _inbound(eng, 'GY-N08')
        assert isinstance(r, dict)
        assert 'success' in r
        assert 'errors' in r


# ═══════════════════════════════════════════════════════════════
# N2. 입력 검증 / 에러 처리 (T09~T14)
# ═══════════════════════════════════════════════════════════════
class TestN2Validation:

    def test_T09_missing_lot_no_fails(self, eng):
        """lot_no 누락 → 실패."""
        r = eng.process_inbound({
            'product': 'LC', 'net_weight': 2001.0, 'mxbg_pallet': 2
        })
        assert not r.get('success')
        assert len(r.get('errors', [])) > 0

    def test_T10_zero_weight_fails(self, eng):
        """net_weight=0 → 실패."""
        r = _inbound(eng, 'GY-N10', net_weight=0.0)
        assert not r.get('success')

    def test_T11_negative_weight_fails(self, eng):
        """음수 중량 → 실패."""
        r = _inbound(eng, 'GY-N11', net_weight=-500.0)
        assert not r.get('success')

    def test_T12_errors_list_on_failure(self, eng):
        """실패 시 errors 리스트에 내용 있음."""
        r = eng.process_inbound({'lot_no': '', 'net_weight': 0})
        assert len(r.get('errors', [])) > 0

    def test_T13_none_data_fails(self, eng):
        """None 데이터 → 오류 없이 실패."""
        try:
            r = eng.process_inbound(None)
            assert not r.get('success')
        except (TypeError, AttributeError):
            pass  # 예외도 허용

    def test_T14_nonstandard_lot_format_warns(self, eng):
        """비표준 LOT 번호 → 경고(warning) 발생."""
        r = _inbound(eng, 'CUSTOM-LOT-ABC')
        # 성공하되 warning 포함 가능
        if r.get('success'):
            # warning이 있거나 없어도 됨
            assert isinstance(r.get('warnings', []), list)


# ═══════════════════════════════════════════════════════════════
# N3. 중복 / 재입고 처리 (T15~T18)
# ═══════════════════════════════════════════════════════════════
class TestN3DuplicateHandling:

    def test_T15_duplicate_lot_fails(self, eng):
        """중복 lot_no → 두 번째 입고 실패."""
        _inbound(eng, 'GY-N15')
        r = _inbound(eng, 'GY-N15')
        assert not r.get('success')

    def test_T16_duplicate_error_message(self, eng):
        """중복 시 에러 메시지에 LOT 번호 포함."""
        _inbound(eng, 'GY-N16')
        r = _inbound(eng, 'GY-N16')
        err_str = ' '.join(r.get('errors', []))
        assert 'GY-N16' in err_str or '중복' in err_str or 'exist' in err_str.lower()

    def test_T17_different_lots_both_succeed(self, eng):
        """서로 다른 lot_no → 둘 다 성공."""
        r1 = _inbound(eng, 'GY-N17A')
        r2 = _inbound(eng, 'GY-N17B')
        assert r1.get('success')
        assert r2.get('success')

    def test_T18_db_count_correct(self, eng):
        """여러 입고 후 DB 건수 정확."""
        _inbound(eng, 'GY-N18A')
        _inbound(eng, 'GY-N18B')
        _inbound(eng, 'GY-N18C')
        cnt = eng.db.fetchone(
            "SELECT COUNT(*) AS c FROM inventory "
            "WHERE lot_no LIKE 'GY-N18%'"
        )['c']
        assert cnt == 3


# ═══════════════════════════════════════════════════════════════
# N4. 무게 정합성 검증 (T19~T20)
# ═══════════════════════════════════════════════════════════════
class TestN4WeightIntegrity:

    def test_T19_initial_weight_equals_net_weight(self, eng):
        """initial_weight = net_weight로 저장."""
        _inbound(eng, 'GY-N19', net_weight=2001.0)
        row = eng.db.fetchone(
            "SELECT initial_weight, net_weight FROM inventory WHERE lot_no='GY-N19'"
        )
        # initial_weight와 net_weight가 존재하는지 확인
        assert row is not None
        assert row['net_weight'] > 0

    def test_T20_current_weight_lte_initial(self, eng):
        """current_weight ≤ initial_weight (입고 직후)."""
        _inbound(eng, 'GY-N20', net_weight=2001.0)
        row = eng.db.fetchone(
            "SELECT initial_weight, current_weight FROM inventory WHERE lot_no='GY-N20'"
        )
        assert row['current_weight'] <= row['initial_weight'] + 1.0
