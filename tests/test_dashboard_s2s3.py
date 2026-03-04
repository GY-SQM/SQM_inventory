# -*- coding: utf-8 -*-
"""
v6.3.0 S2/S3 테스트: 출고 파이프라인 + 컨테이너 반납 경고
DashboardDataMixin 함수는 GUI 클래스에 있으므로 직접 DB 쿼리로 테스트
"""
import pytest
import sqlite3
import tempfile
import os
from datetime import date, timedelta


@pytest.fixture
def engine():
    from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    eng = SQMInventoryEngineV3(tmp.name)
    yield eng
    eng.close()
    os.unlink(tmp.name)


def _pipeline_stats(db):
    """_get_outbound_pipeline_stats 로직 직접 호출"""
    tb = db.fetchone("""
        SELECT
            SUM(CASE WHEN status='AVAILABLE' THEN 1 ELSE 0 END) AS avail_tb,
            SUM(CASE WHEN status='RESERVED'  THEN 1 ELSE 0 END) AS reserved_tb,
            SUM(CASE WHEN status='PICKED'    THEN 1 ELSE 0 END) AS picked_tb,
            SUM(CASE WHEN status='SOLD'      THEN 1 ELSE 0 END) AS sold_tb,
            COALESCE(SUM(CASE WHEN status='AVAILABLE' THEN weight ELSE 0 END),0)/1000.0 AS avail_mt,
            COALESCE(SUM(CASE WHEN status='SOLD' AND DATE(updated_at)=DATE('now') THEN 1 ELSE 0 END),0) AS today_sold
        FROM inventory_tonbag WHERE COALESCE(is_sample,0)=0
    """)
    return {
        'avail_tb': (tb['avail_tb'] or 0) if tb else 0,
        'reserved_tb': (tb['reserved_tb'] or 0) if tb else 0,
        'picked_tb': (tb['picked_tb'] or 0) if tb else 0,
        'sold_tb': (tb['sold_tb'] or 0) if tb else 0,
        'avail_mt': (tb['avail_mt'] or 0) if tb else 0,
        'today_sold': (tb['today_sold'] or 0) if tb else 0,
    }


def _container_alerts(db):
    """_get_container_return_alerts 로직 직접 호출"""
    alerts = []
    today = date.today()
    rows = db.fetchall("""
        SELECT lot_no, container_no, con_return, status
        FROM inventory
        WHERE con_return IS NOT NULL AND con_return != ''
          AND status IN ('AVAILABLE','RESERVED','PICKED')
        ORDER BY con_return ASC
    """)
    for r in (rows or []):
        lot = r['lot_no'] if isinstance(r, dict) else r[0]
        container = r['container_no'] if isinstance(r, dict) else r[1]
        cr_raw = r['con_return'] if isinstance(r, dict) else r[2]
        if not cr_raw:
            continue
        try:
            cr_date = date.fromisoformat(str(cr_raw)[:10])
        except (ValueError, TypeError):
            continue
        days_left = (cr_date - today).days
        label = container if container else lot
        if days_left < 0:
            alerts.append({'severity': 'error', 'days_left': days_left, 'message': f'{label}: 반납 {abs(days_left)}일 초과'})
        elif days_left == 0:
            alerts.append({'severity': 'error', 'days_left': 0, 'message': f'{label}: 오늘 마감'})
        elif days_left <= 3:
            alerts.append({'severity': 'warning', 'days_left': days_left, 'message': f'{label}: D-{days_left}'})
        elif days_left <= 7:
            alerts.append({'severity': 'info', 'days_left': days_left, 'message': f'{label}: D-{days_left}'})
    alerts.sort(key=lambda x: x['days_left'])
    return alerts[:10]


def _inject_lot(engine, lot_no, con_return=None):
    engine.process_inbound({
        'lot_no': lot_no, 'sap_no': f'SAP-{lot_no}',
        'product': 'LCA', 'product_code': 'LCA',
        'net_weight': 2001, 'mxbg_pallet': 4, 'tonbag_unit_weight': 500,
    })
    if con_return:
        engine.db.execute(
            "UPDATE inventory SET con_return=?, container_no=? WHERE lot_no=?",
            (con_return, f'CONT-{lot_no}', lot_no)
        )
        engine.db.conn.commit()


class TestOutboundPipeline:

    def test_empty(self, engine):
        s = _pipeline_stats(engine.db)
        assert s['avail_tb'] == 0

    def test_with_data(self, engine):
        _inject_lot(engine, 'P-001')
        s = _pipeline_stats(engine.db)
        assert s['avail_tb'] == 4
        assert s['avail_mt'] > 0

    def test_reserved(self, engine):
        _inject_lot(engine, 'P-002')
        engine.reserve_from_allocation([{
            'lot_no': 'P-002', 'qty_mt': 1.0,
            'sold_to': 'CATL', 'sale_ref': 'SR001',
        }], source_file='test.pdf')
        # 승인 대기 → 수동 승인 → 예약 반영
        engine.db.execute(
            "UPDATE allocation_plan SET workflow_status='APPROVED', "
            "approved_by='admin', approved_at=datetime('now')"
        )
        engine.db.conn.commit()
        engine.apply_approved_allocation_reservations()
        s = _pipeline_stats(engine.db)
        assert s['reserved_tb'] == 2
        assert s['avail_tb'] == 2

    def test_multi_lots(self, engine):
        for i in range(3):
            _inject_lot(engine, f'ML-{i:03d}')
        s = _pipeline_stats(engine.db)
        assert s['avail_tb'] == 12  # 3 lots × 4 tonbags


class TestContainerReturnAlerts:

    def test_empty(self, engine):
        assert len(_container_alerts(engine.db)) == 0

    def test_overdue(self, engine):
        _inject_lot(engine, 'OD-1', (date.today() - timedelta(days=2)).isoformat())
        a = _container_alerts(engine.db)
        assert len(a) == 1
        assert a[0]['severity'] == 'error'
        assert '초과' in a[0]['message']

    def test_today(self, engine):
        _inject_lot(engine, 'TD-1', date.today().isoformat())
        a = _container_alerts(engine.db)
        assert len(a) == 1
        assert a[0]['severity'] == 'error'
        assert '오늘' in a[0]['message']

    def test_d3(self, engine):
        _inject_lot(engine, 'D3-1', (date.today() + timedelta(days=2)).isoformat())
        a = _container_alerts(engine.db)
        assert len(a) == 1
        assert a[0]['severity'] == 'warning'

    def test_d7(self, engine):
        _inject_lot(engine, 'D7-1', (date.today() + timedelta(days=6)).isoformat())
        a = _container_alerts(engine.db)
        assert len(a) == 1
        assert a[0]['severity'] == 'info'

    def test_beyond_7(self, engine):
        _inject_lot(engine, 'B7-1', (date.today() + timedelta(days=10)).isoformat())
        assert len(_container_alerts(engine.db)) == 0

    def test_sold_excluded(self, engine):
        _inject_lot(engine, 'SL-1', (date.today() - timedelta(days=1)).isoformat())
        engine.db.execute("UPDATE inventory SET status='SOLD' WHERE lot_no='SL-1'")
        engine.db.conn.commit()
        assert len(_container_alerts(engine.db)) == 0

    def test_priority_sort(self, engine):
        _inject_lot(engine, 'A', (date.today() + timedelta(days=5)).isoformat())
        _inject_lot(engine, 'B', (date.today() - timedelta(days=3)).isoformat())
        _inject_lot(engine, 'C', date.today().isoformat())
        a = _container_alerts(engine.db)
        assert len(a) == 3
        assert a[0]['days_left'] < 0   # B (초과)
        assert a[1]['days_left'] == 0  # C (오늘)
        assert a[2]['days_left'] > 0   # A (여유)
