# -*- coding: utf-8 -*-
"""
SQM 공용 테스트 fixture
========================
모든 테스트 파일에서 import 없이 fixture 사용 가능.
pytest가 자동 로드.
"""

import os
import sys
import tempfile
import logging
import pytest
from datetime import datetime

# 프로젝트 루트 설정
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 엔진 fixture
# ═══════════════════════════════════════════

@pytest.fixture
def engine():
    """테스트용 SQMInventoryEngineV3 (임시 DB, 자동 정리)."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    try:
        from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
        eng = SQMInventoryEngineV3(db_path)
        yield eng
    finally:
        try:
            eng.db.close()
        except Exception:
            pass
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture
def engine_pair():
    """독립 DB를 가진 엔진 2개 (thread-local 테스트용)."""
    paths = []
    engines = []
    for _ in range(2):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            paths.append(f.name)
        from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
        engines.append(SQMInventoryEngineV3(paths[-1]))
    yield tuple(engines)
    for eng in engines:
        try:
            eng.db.close()
        except Exception:
            pass
    for p in paths:
        try:
            os.unlink(p)
        except OSError:
            pass


# ═══════════════════════════════════════════
# LOT 데이터 fixture (실제 엔진 API 형식)
# ═══════════════════════════════════════════

@pytest.fixture
def lot_500kg():
    """500kg 톤백 x 10 + 샘플 1kg = 5001kg.

    필드명은 engine.process_inbound() 기준:
    - sap_no (not sap_batch)
    - product (not product_type)
    - mxbg_pallet (not tonbag_count)
    - net_weight (not total_weight)
    """
    return {
        'lot_no': 'LOT-EDGE-500',
        'sap_no': 'SAP-500-001',
        'bl_no': 'BL-EDGE-500',
        'container_no': 'CONT-EDGE-500',
        'product': 'LITHIUM CARBONATE',
        'product_code': 'LC',
        'mxbg_pallet': 10,
        'net_weight': 5001.0,
        'gross_weight': 5200.0,
        'salar_invoice_no': 'INV-EDGE-500',
        'warehouse': 'GY',
    }


@pytest.fixture
def lot_1000kg():
    """1000kg 톤백 x 5 + 샘플 1kg = 5001kg."""
    return {
        'lot_no': 'LOT-EDGE-1000',
        'sap_no': 'SAP-1000-001',
        'bl_no': 'BL-EDGE-1000',
        'container_no': 'CONT-EDGE-1000',
        'product': 'NICKEL SULFATE',
        'product_code': 'NS',
        'mxbg_pallet': 5,
        'net_weight': 5001.0,
        'gross_weight': 5200.0,
        'salar_invoice_no': 'INV-EDGE-1000',
        'warehouse': 'GY',
    }


@pytest.fixture
def lot_small():
    """500kg 톤백 x 2 + 샘플 1kg = 1001kg (소량 LOT)."""
    return {
        'lot_no': 'LOT-EDGE-SMALL',
        'sap_no': 'SAP-SM-001',
        'bl_no': 'BL-EDGE-SM',
        'container_no': 'CONT-EDGE-SM',
        'product': 'LITHIUM CARBONATE',
        'product_code': 'LC',
        'mxbg_pallet': 2,
        'net_weight': 1001.0,
        'gross_weight': 1100.0,
        'salar_invoice_no': 'INV-EDGE-SM',
        'warehouse': 'GY',
    }


# ═══════════════════════════════════════════
# 헬퍼 함수 (테스트에서 직접 import 가능)
# ═══════════════════════════════════════════

def inbound_lot(engine, lot_data: dict) -> dict:
    """LOT 입고 헬퍼 — engine.process_inbound() 사용."""
    result = engine.process_inbound(lot_data)
    assert result['success'], f"입고 실패: {result.get('errors', [])}"
    return result


def outbound_lot(engine, lot_no: str, customer: str, weight_kg: float,
                 source: str = 'TEST', stop_at_picked: bool = False) -> dict:
    """출고 헬퍼 — engine.process_outbound() 사용."""
    alloc = {
        'lot_no': lot_no,
        'customer': customer,
        'weight_kg': weight_kg,
        'qty_mt': weight_kg / 1000.0,
    }
    return engine.process_outbound(alloc, source=source, stop_at_picked=stop_at_picked)


def get_lot(engine, lot_no: str) -> dict:
    """inventory 행 조회 -> dict."""
    row = engine.db.fetchone(
        "SELECT * FROM inventory WHERE lot_no = ?", (lot_no,))
    return row if row else None


def get_tonbags(engine, lot_no: str, status=None) -> list:
    """톤백 목록 조회 (샘플 제외)."""
    if status:
        rows = engine.db.fetchall(
            "SELECT * FROM inventory_tonbag WHERE lot_no = ? AND status = ? "
            "AND COALESCE(is_sample,0)=0", (lot_no, status))
    else:
        rows = engine.db.fetchall(
            "SELECT * FROM inventory_tonbag WHERE lot_no = ? "
            "AND COALESCE(is_sample,0)=0", (lot_no,))
    return rows or []
