# -*- coding: utf-8 -*-
"""
SQM Web — Engine Bridge
========================
Connects NiceGUI frontend to existing SQM engine.
All DB calls go through run_in_executor for async safety.
"""

import sys
import asyncio
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import DB_PATH

_executor = ThreadPoolExecutor(max_workers=4)
_engine = None


def _get_engine():
    """Get or create SQMInventoryEngine instance (thread-safe singleton)."""
    global _engine
    if _engine is None:
        from engine_modules.inventory import SQMInventoryEngine
        _engine = SQMInventoryEngine(str(DB_PATH))
        logger.info(f"[Bridge] Engine initialized: {DB_PATH}")
    return _engine


def get_engine():
    """Public wrapper for engine access."""
    return _get_engine()


async def async_call(fn, *args, **kwargs):
    """Run any sync function in executor for async safety."""
    loop = asyncio.get_event_loop()
    if kwargs:
        return await loop.run_in_executor(_executor, lambda: fn(*args, **kwargs))
    return await loop.run_in_executor(_executor, fn, *args)


# ═══════════════════════════════════════════════════════
# Inventory Queries
# ═══════════════════════════════════════════════════════

async def get_inventory(status: str = None) -> List[Dict]:
    """Get inventory list, optionally filtered by status."""
    engine = _get_engine()
    rows = await async_call(engine.get_inventory, status=status)
    return rows or []


async def get_inventory_summary() -> Dict:
    """Get inventory counts and weights grouped by status."""
    engine = _get_engine()

    def _query():
        try:
            rows = engine.db.fetchall(
                "SELECT status, COUNT(*) as cnt, "
                "COALESCE(SUM(current_weight), 0) as total_weight, "
                "COALESCE(SUM(initial_weight), 0) as initial_weight "
                "FROM inventory GROUP BY status"
            )
            result = {}
            for r in (rows or []):
                row = dict(r) if not isinstance(r, dict) else r
                result[row['status']] = {
                    'count': row['cnt'],
                    'weight_kg': row['total_weight'],
                    'weight_mt': round(row['total_weight'] / 1000, 1),
                    'initial_kg': row['initial_weight'],
                }
            return result
        except Exception as e:
            logger.error(f"[Bridge] get_inventory_summary error: {e}")
            return {}

    return await async_call(_query)


async def get_tonbags(lot_no: str = None, status: str = None) -> List[Dict]:
    """Get tonbag list, optionally filtered."""
    engine = _get_engine()

    def _query():
        q = "SELECT * FROM inventory_tonbag WHERE 1=1"
        params = []
        if lot_no:
            q += " AND lot_no = ?"
            params.append(lot_no)
        if status:
            q += " AND status = ?"
            params.append(status)
        q += " ORDER BY lot_no, sub_lt"
        return [dict(r) if not isinstance(r, dict) else r
                for r in (engine.db.fetchall(q, params) or [])]

    return await async_call(_query)


async def get_allocation_plans() -> List[Dict]:
    """Get allocation plans."""
    engine = _get_engine()

    def _query():
        try:
            rows = engine.db.fetchall(
                "SELECT ap.*, i.product, i.bl_no, i.current_weight "
                "FROM allocation_plan ap "
                "LEFT JOIN inventory i ON ap.lot_no = i.lot_no "
                "ORDER BY ap.created_at DESC LIMIT 500"
            )
            return [dict(r) if not isinstance(r, dict) else r for r in (rows or [])]
        except Exception as e:
            logger.warning(f"[Bridge] allocation query: {e}")
            return []

    return await async_call(_query)


async def get_stock_movements(limit: int = 200) -> List[Dict]:
    """Get recent stock movements for log tab."""
    engine = _get_engine()

    def _query():
        try:
            rows = engine.db.fetchall(
                "SELECT * FROM stock_movement ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) if not isinstance(r, dict) else r for r in (rows or [])]
        except Exception as e:
            logger.warning(f"[Bridge] stock_movement query: {e}")
            return []

    return await async_call(_query)


async def get_outbound_history(limit: int = 200) -> List[Dict]:
    """Get outbound (picked/sold/shipped) records."""
    engine = _get_engine()

    def _query():
        try:
            rows = engine.db.fetchall(
                "SELECT t.*, i.product, i.bl_no "
                "FROM inventory_tonbag t "
                "LEFT JOIN inventory i ON t.lot_no = i.lot_no "
                "WHERE t.status IN ('PICKED', 'OUTBOUND', 'SOLD', 'SHIPPED', 'CONFIRMED') "
                "ORDER BY t.updated_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) if not isinstance(r, dict) else r for r in (rows or [])]
        except Exception as e:
            logger.warning(f"[Bridge] outbound_history query: {e}")
            return []

    return await async_call(_query)


async def get_return_history(limit: int = 200) -> List[Dict]:
    """Get return records."""
    engine = _get_engine()

    def _query():
        try:
            rows = engine.db.fetchall(
                "SELECT * FROM return_history ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) if not isinstance(r, dict) else r for r in (rows or [])]
        except Exception as e:
            logger.warning(f"[Bridge] return_history: {e}")
            return []

    return await async_call(_query)


async def get_dashboard_stats() -> Dict:
    """Get comprehensive dashboard statistics."""
    engine = _get_engine()

    def _query():
        stats = {
            'total_lots': 0,
            'total_tonbags': 0,
            'total_weight_mt': 0.0,
            'by_status': {},
            'by_product': [],
            'recent_movements': [],
        }
        try:
            # LOT counts by status
            rows = engine.db.fetchall(
                "SELECT status, COUNT(*) as cnt, "
                "COALESCE(SUM(current_weight), 0)/1000.0 as mt "
                "FROM inventory GROUP BY status"
            )
            for r in (rows or []):
                row = dict(r) if not isinstance(r, dict) else r
                stats['by_status'][row['status']] = {
                    'count': row['cnt'],
                    'mt': round(row['mt'], 1)
                }
                stats['total_lots'] += row['cnt']
                stats['total_weight_mt'] += row['mt']

            stats['total_weight_mt'] = round(stats['total_weight_mt'], 1)

            # Tonbag total
            row = engine.db.fetchone("SELECT COUNT(*) as cnt FROM inventory_tonbag")
            if row:
                stats['total_tonbags'] = dict(row).get('cnt', 0) if not isinstance(row, dict) else row.get('cnt', 0)

            # By product
            rows = engine.db.fetchall(
                "SELECT product, COUNT(*) as cnt, "
                "COALESCE(SUM(current_weight), 0)/1000.0 as mt "
                "FROM inventory GROUP BY product ORDER BY mt DESC LIMIT 10"
            )
            stats['by_product'] = [
                dict(r) if not isinstance(r, dict) else r for r in (rows or [])
            ]

            # Recent movements
            rows = engine.db.fetchall(
                "SELECT movement_type, COUNT(*) as cnt "
                "FROM stock_movement "
                "WHERE created_at >= date('now', '-30 days') "
                "GROUP BY movement_type"
            )
            stats['recent_movements'] = [
                dict(r) if not isinstance(r, dict) else r for r in (rows or [])
            ]

        except Exception as e:
            logger.error(f"[Bridge] dashboard stats error: {e}")

        return stats

    return await async_call(_query)


async def get_lot_status_overview() -> List[Dict]:
    """v8.1.5: LOT별 통합 현황 — AVAILABLE/RESERVED/PICKED/OUTBOUND + 샘플."""
    engine = _get_engine()

    def _query():
        try:
            rows = engine.db.fetchall("""
                SELECT
                    i.lot_no, i.sap_no,
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=0 THEN 1 ELSE 0 END) AS total_tb,
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=0 AND t.status='AVAILABLE'
                        THEN 1 ELSE 0 END) AS avail_tb,
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=0 AND t.status='PICKED'
                        THEN 1 ELSE 0 END) AS picked_tb,
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=0
                        AND t.status IN ('OUTBOUND','SOLD') THEN 1 ELSE 0 END) AS out_tb,
                    COALESCE((SELECT CAST(SUM(ap.qty_mt/0.5) AS INT)
                        FROM allocation_plan ap
                        WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), 0) AS reserved_tb,
                    COALESCE((SELECT SUM(ap.qty_mt)
                        FROM allocation_plan ap
                        WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), 0) AS reserved_mt,
                    COALESCE((SELECT GROUP_CONCAT(DISTINCT ap.sale_ref)
                        FROM allocation_plan ap
                        WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), '') AS sale_refs,
                    MAX(CASE WHEN t.is_sample=1 THEN t.status ELSE NULL END) AS sample_status,
                    SUM(CASE WHEN t.is_sample=1 THEN 1 ELSE 0 END) AS sample_cnt
                FROM inventory i
                LEFT JOIN inventory_tonbag t ON t.lot_no = i.lot_no
                GROUP BY i.lot_no
                ORDER BY i.lot_no
            """)
            return [dict(r) if not isinstance(r, dict) else r for r in (rows or [])]
        except Exception as e:
            logger.warning(f"[Bridge] lot_status_overview: {e}")
            return []

    return await async_call(_query)


async def search_inventory(keyword: str) -> List[Dict]:
    """Search inventory by keyword (lot_no, bl_no, product, container_no)."""
    engine = _get_engine()

    def _query():
        kw = f"%{keyword}%"
        rows = engine.db.fetchall(
            "SELECT * FROM inventory "
            "WHERE lot_no LIKE ? OR bl_no LIKE ? OR product LIKE ? "
            "OR container_no LIKE ? OR sap_no LIKE ? "
            "ORDER BY created_at DESC LIMIT 200",
            (kw, kw, kw, kw, kw)
        )
        return [dict(r) if not isinstance(r, dict) else r for r in (rows or [])]

    return await async_call(_query)
