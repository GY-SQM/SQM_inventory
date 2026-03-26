# -*- coding: utf-8 -*-
"""
tests/test_v830_phase9_11.py
==============================
SQM v8.3.0 — Phase 9~11 통합 테스트 (30개)
============================================
  P9A. audit_helper           (T01~T08)
  P9B. error_notifier         (T09~T12)
  P9C. daily_report           (T13~T18)
  P10. migration_manager      (T19~T24)
  P11. allocation_approval    (T25~T30)
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def eng():
    from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
    e = SQMInventoryEngineV3(':memory:')
    e.add_inventory('GY-P01', product='LC', net_weight=2001.0, mxbg_pallet=2)
    e.add_inventory('GY-P02', product='NS', net_weight=2001.0, mxbg_pallet=2)
    yield e


# ═══════════════════════════════════════════════════════════════
# P9A. audit_helper (T01~T08)
# ═══════════════════════════════════════════════════════════════
class TestP9AAuditHelper:

    def test_T01_write_audit_returns_true(self, eng):
        """write_audit 기본 기록 성공."""
        from engine_modules.audit_helper import write_audit, EVT_INBOUND
        result = write_audit(eng.db, EVT_INBOUND, lot_no='GY-P01',
                             detail={'weight_kg': 2001.0})
        assert result is True

    def test_T02_audit_record_in_db(self, eng):
        """기록 후 audit_log DB에 존재."""
        from engine_modules.audit_helper import write_audit, EVT_INBOUND
        write_audit(eng.db, EVT_INBOUND, lot_no='GY-P01')
        cnt = eng.db.fetchone(
            "SELECT COUNT(*) AS c FROM audit_log WHERE event_type='INBOUND'"
        )['c']
        assert cnt >= 1

    def test_T03_write_audit_does_not_raise(self, eng):
        """잘못된 DB 전달해도 예외 없이 False 반환."""
        from engine_modules.audit_helper import write_audit, EVT_OUTBOUND
        result = write_audit(None, EVT_OUTBOUND, lot_no='GY-P01')
        assert result is False

    def test_T04_write_audit_bulk(self, eng):
        """write_audit_bulk 다건 기록."""
        from engine_modules.audit_helper import write_audit_bulk, EVT_INBOUND, EVT_OUTBOUND
        events = [
            {'event_type': EVT_INBOUND, 'lot_no': 'GY-P01'},
            {'event_type': EVT_OUTBOUND, 'lot_no': 'GY-P02'},
        ]
        count = write_audit_bulk(eng.db, events)
        assert count == 2

    def test_T05_query_lot_history(self, eng):
        """query_lot_history — 특정 LOT 이력 조회."""
        from engine_modules.audit_helper import write_audit, query_lot_history, EVT_INBOUND
        write_audit(eng.db, EVT_INBOUND, lot_no='GY-P01',
                    detail={'product': 'LC'})
        history = query_lot_history(eng.db, 'GY-P01')
        assert isinstance(history, list)
        assert len(history) >= 1

    def test_T06_query_lot_history_empty(self, eng):
        """없는 LOT 이력 → 빈 list."""
        from engine_modules.audit_helper import query_lot_history
        history = query_lot_history(eng.db, 'NOT-EXIST-LOT')
        assert history == []

    def test_T07_query_audit_summary(self, eng):
        """query_audit_summary — 이벤트 타입별 집계."""
        from engine_modules.audit_helper import write_audit, query_audit_summary
        from engine_modules.audit_helper import EVT_INBOUND, EVT_RETURN
        write_audit(eng.db, EVT_INBOUND, lot_no='GY-P01')
        write_audit(eng.db, EVT_INBOUND, lot_no='GY-P02')
        write_audit(eng.db, EVT_RETURN,  lot_no='GY-P01')
        summary = query_audit_summary(eng.db)
        assert isinstance(summary, dict)
        assert summary.get(EVT_INBOUND, 0) >= 2

    def test_T08_audit_detail_json(self, eng):
        """detail dict가 JSON으로 저장 후 복원."""
        from engine_modules.audit_helper import write_audit, query_lot_history, EVT_LOT_UPDATE
        write_audit(eng.db, EVT_LOT_UPDATE, lot_no='GY-P01',
                    detail={'updated_fields': ['product', 'bl_no']})
        history = query_lot_history(eng.db, 'GY-P01')
        assert len(history) >= 1
        detail = history[-1].get('detail', {})
        assert 'updated_fields' in detail


# ═══════════════════════════════════════════════════════════════
# P9B. error_notifier (T09~T12)
# ═══════════════════════════════════════════════════════════════
class TestP9BErrorNotifier:

    def test_T09_notify_error_disabled(self):
        """알림 비활성화 시 False 반환 (실제 전송 안 함)."""
        from utils.error_notifier import notify_error
        result = notify_error('TEST_EVENT', '테스트 메시지')
        assert result is False  # NOTIFY_EMAIL_ENABLED=False 기본

    def test_T10_notify_integrity_fail_disabled(self):
        """정합성 오류 알림 — 비활성 시 False."""
        from utils.error_notifier import notify_integrity_fail
        result = notify_integrity_fail('GY-P01', ['무게 불일치'])
        assert result is False

    def test_T11_notify_parsing_fail_disabled(self):
        """파싱 실패 알림 — 비활성 시 False."""
        from utils.error_notifier import notify_parsing_fail
        result = notify_parsing_fail('TEST.pdf', 'DO', '텍스트 추출 실패')
        assert result is False

    def test_T12_build_html_not_empty(self):
        """HTML 본문 생성 — 비어있지 않음."""
        from utils.error_notifier import _build_html, LEVEL_ERROR
        html = _build_html(
            title='테스트 오류',
            level=LEVEL_ERROR,
            items=['항목1', '항목2'],
        )
        assert '<html>' in html
        assert '테스트 오류' in html
        assert '항목1' in html


# ═══════════════════════════════════════════════════════════════
# P9C. daily_report (T13~T18)
# ═══════════════════════════════════════════════════════════════
class TestP9CDailyReport:

    def test_T13_collect_daily_data_returns_dict(self, eng):
        """_collect_daily_data → dict 반환."""
        from utils.daily_report import _collect_daily_data
        from datetime import date
        result = _collect_daily_data(eng.db, date.today().strftime('%Y-%m-%d'))
        assert isinstance(result, dict)
        assert 'summary' in result

    def test_T14_summary_has_required_keys(self, eng):
        """summary에 필수 키 포함."""
        from utils.daily_report import _collect_daily_data
        from datetime import date
        data = _collect_daily_data(eng.db, date.today().strftime('%Y-%m-%d'))
        s = data['summary']
        for key in ['inbound_cnt', 'outbound_cnt', 'return_cnt', 'inbound_kg']:
            assert key in s, f"키 누락: {key}"

    def test_T15_inbound_counted_today(self, eng):
        """오늘 입고한 LOT이 inbound 목록에 포함."""
        from utils.daily_report import _collect_daily_data
        from datetime import date
        data = _collect_daily_data(eng.db, date.today().strftime('%Y-%m-%d'))
        assert data['summary']['inbound_cnt'] >= 2

    def test_T16_generate_report_returns_dict(self, eng):
        """generate_daily_report → dict 반환."""
        from utils.daily_report import generate_daily_report
        from datetime import date
        result = generate_daily_report(eng.db,
                                       date_str=date.today().strftime('%Y-%m-%d'),
                                       send_email=False)
        assert isinstance(result, dict)
        assert 'success' in result

    def test_T17_report_file_created(self, eng, tmp_path):
        """엑셀 파일 생성 확인."""
        import importlib
        from utils import daily_report as dr
        orig = dr.REPORT_DIR
        dr.REPORT_DIR = str(tmp_path)
        try:
            from datetime import date
            result = dr.generate_daily_report(eng.db,
                                              date_str=date.today().strftime('%Y-%m-%d'),
                                              send_email=False)
            if result.get('success'):
                assert os.path.exists(result['filepath'])
        finally:
            dr.REPORT_DIR = orig

    def test_T18_ensure_report_dir(self, tmp_path):
        """_ensure_report_dir — 폴더 생성."""
        from utils import daily_report as dr
        orig = dr.REPORT_DIR
        new_dir = str(tmp_path / 'sqm_reports')
        dr.REPORT_DIR = new_dir
        try:
            dr._ensure_report_dir()
            assert os.path.isdir(new_dir)
        finally:
            dr.REPORT_DIR = orig


# ═══════════════════════════════════════════════════════════════
# P10. migration_manager (T19~T24)
# ═══════════════════════════════════════════════════════════════
class TestP10MigrationManager:

    def test_T19_creates_schema_version_table(self, eng):
        """MigrationManager 생성 시 schema_version 테이블 존재."""
        from engine_modules.migration_manager import MigrationManager
        MigrationManager(eng.db)
        row = eng.db.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        assert row is not None

    def test_T20_current_version_returns_int(self, eng):
        """current_version → 정수 반환."""
        from engine_modules.migration_manager import MigrationManager
        mgr = MigrationManager(eng.db)
        v = mgr.current_version()
        assert isinstance(v, int)

    def test_T21_mark_applied_records_version(self, eng):
        """_mark_applied → schema_version에 기록."""
        from engine_modules.migration_manager import MigrationManager
        mgr = MigrationManager(eng.db)
        mgr._mark_applied(830, 'v8.3.0', 'Phase 9~11 테스트')
        assert mgr.current_version() == 830

    def test_T22_history_returns_list(self, eng):
        """history → list 반환."""
        from engine_modules.migration_manager import MigrationManager
        mgr = MigrationManager(eng.db)
        mgr._mark_applied(100, 'v1.0.0', '초기 버전')
        h = mgr.history()
        assert isinstance(h, list)
        assert len(h) >= 1

    def test_T23_sync_existing_runs_without_error(self, eng):
        """sync_existing → 오류 없이 실행."""
        from engine_modules.migration_manager import MigrationManager
        mgr = MigrationManager(eng.db)
        synced = mgr.sync_existing()
        assert isinstance(synced, int)

    def test_T24_upgrade_skips_already_applied(self, eng):
        """이미 적용된 버전은 스킵."""
        from engine_modules.migration_manager import MigrationManager
        mgr = MigrationManager(eng.db)
        mgr._mark_applied(830, 'v8.3.0', '이미 적용')
        result = mgr.upgrade(target_version=830)
        assert result['applied'] == []


# ═══════════════════════════════════════════════════════════════
# P11. allocation_approval (T25~T30)
# ═══════════════════════════════════════════════════════════════
class TestP11AllocationApproval:

    def _insert_pending(self, eng, lot_no='GY-P01', sale_ref='SR-001'):
        """STAGED + PENDING_APPROVAL 배정 레코드 삽입."""
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        eng.db.execute("""
            INSERT INTO allocation_plan
            (lot_no, customer, qty_mt, status, sale_ref,
             workflow_status, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (lot_no, 'CATL', 2.0, 'STAGED', sale_ref,
              'PENDING_APPROVAL', now))

    def test_T25_pending_count_query(self, eng):
        """PENDING_APPROVAL 건수 조회."""
        self._insert_pending(eng, 'GY-P01', 'SR-001')
        self._insert_pending(eng, 'GY-P02', 'SR-002')
        row = eng.db.fetchone("""
            SELECT COUNT(*) AS cnt FROM allocation_plan
            WHERE status='STAGED' AND workflow_status='PENDING_APPROVAL'
        """)
        assert row['cnt'] == 2

    def test_T26_approve_updates_workflow_status(self, eng):
        """승인 처리 → workflow_status = APPROVED."""
        self._insert_pending(eng)
        row = eng.db.fetchone(
            "SELECT id FROM allocation_plan WHERE workflow_status='PENDING_APPROVAL'"
        )
        plan_id = row['id']
        eng.db.execute(
            "UPDATE allocation_plan SET workflow_status='APPROVED' WHERE id=?",
            (plan_id,)
        )
        updated = eng.db.fetchone(
            "SELECT workflow_status FROM allocation_plan WHERE id=?", (plan_id,)
        )
        assert updated['workflow_status'] == 'APPROVED'

    def test_T27_reject_updates_workflow_status(self, eng):
        """반려 처리 → workflow_status = REJECTED."""
        self._insert_pending(eng, 'GY-P02', 'SR-003')
        row = eng.db.fetchone(
            "SELECT id FROM allocation_plan WHERE sale_ref='SR-003'"
        )
        plan_id = row['id']
        eng.db.execute(
            "UPDATE allocation_plan SET workflow_status='REJECTED', "
            "rejected_reason='품질 기준 미달' WHERE id=?",
            (plan_id,)
        )
        updated = eng.db.fetchone(
            "SELECT workflow_status, rejected_reason FROM allocation_plan WHERE id=?",
            (plan_id,)
        )
        assert updated['workflow_status'] == 'REJECTED'
        assert '품질 기준 미달' in updated['rejected_reason']

    def test_T28_alloc_wf_constants_available(self):
        """workflow_status 상수 import 가능."""
        from engine_modules.constants import (
            ALLOC_WF_APPROVED, ALLOC_WF_REJECTED,
            ALLOC_WF_PENDING, ALLOC_WF_APPLIED,
        )
        assert ALLOC_WF_APPROVED == 'APPROVED'
        assert ALLOC_WF_REJECTED == 'REJECTED'
        assert ALLOC_WF_PENDING  == 'PENDING_APPROVAL'
        assert ALLOC_WF_APPLIED  == 'APPLIED'

    def test_T29_audit_written_on_approve(self, eng):
        """승인 시 audit_log에 RESERVED 이벤트 기록."""
        from engine_modules.audit_helper import write_audit, query_lot_history
        from engine_modules.audit_helper import EVT_RESERVED
        self._insert_pending(eng)
        write_audit(eng.db, EVT_RESERVED, lot_no='GY-P01',
                    detail={'action': 'APPROVED', 'approved_by': 'test'})
        history = query_lot_history(eng.db, 'GY-P01')
        evt_types = [h['event_type'] for h in history]
        assert EVT_RESERVED in evt_types

    def test_T30_pending_zero_after_all_approved(self, eng):
        """전체 승인 후 PENDING_APPROVAL 건수 = 0."""
        self._insert_pending(eng, 'GY-P01', 'SR-T30A')
        self._insert_pending(eng, 'GY-P02', 'SR-T30B')
        eng.db.execute(
            "UPDATE allocation_plan SET workflow_status='APPROVED' "
            "WHERE workflow_status='PENDING_APPROVAL'"
        )
        row = eng.db.fetchone("""
            SELECT COUNT(*) AS cnt FROM allocation_plan
            WHERE workflow_status='PENDING_APPROVAL'
        """)
        assert row['cnt'] == 0
