# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 조회 기능 Mixin (v3.6.0)
================================================
실제 DB 테이블: inventory, inventory_tonbag, stock_movement, shipment
"""
import sqlite3
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def _row_to_dict(row) -> Dict:
    """DB Row → dict 변환"""
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except (TypeError, ValueError):
        if hasattr(row, 'keys'):
            return {k: row[k] for k in row.keys()}
        return {}


def _rows_to_dicts(rows) -> List[Dict]:
    """DB Row 리스트 → dict 리스트 변환"""
    if not rows:
        return []
    return [_row_to_dict(r) for r in rows]


class QueryMixin:
    """재고 조회 Mixin - 실제 DB 스키마 기반"""

    # ══════════════════════════════════════════════════════════
    # inventory 테이블 조회
    # ══════════════════════════════════════════════════════════
    def get_inventory(self, status: str = None, product: str = None,
                      lot_no: str = None) -> List[Dict]:
        """재고 목록 조회 (v3.9.4: 18열 전체 포함)"""
        try:
            query = """
                SELECT id, lot_no, sap_no, bl_no, product, product_code,
                       container_no, lot_sqm,
                       sold_to, warehouse, status, location, vessel,
                       initial_weight, current_weight, picked_weight,
                       net_weight, gross_weight, mxbg_pallet,
                       salar_invoice_no, ship_date, arrival_date, free_time,
                       customs,
                       stock_date, inbound_date, created_at, updated_at
                FROM inventory WHERE 1=1
            """
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if product:
                query += " AND product LIKE ?"
                params.append(f"%{product}%")
            if lot_no:
                query += " AND lot_no LIKE ?"
                params.append(f"%{lot_no}%")
            query += " ORDER BY COALESCE(arrival_date, created_at) DESC, lot_no"
            rows = self.db.fetchall(query, tuple(params))
            from engine_modules.tonbag_compat import normalize_all_rows
            return normalize_all_rows(_rows_to_dicts(rows))
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"재고 조회 오류: {e}")
            return []

    def get_all_inventory(self) -> List[Dict]:
        """전체 재고 조회 (inventory_tab 호환)"""
        return self.get_inventory()

    def get_lot_detail(self, lot_no: str) -> Dict:
        """LOT 상세 조회"""
        try:
            row = self.db.fetchone(
                "SELECT * FROM inventory WHERE lot_no = ?", (lot_no,))
            if not row:
                return {'error': f'LOT not found: {lot_no}'}
            lot_data = _row_to_dict(row)
            lot_data['tonbags'] = self.get_tonbags(lot_no=lot_no)
            return lot_data
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"LOT 상세 조회 오류: {e}")
            return {'error': str(e)}

    def get_lot_items(self, lot_no: str) -> List[Dict]:
        """LOT 항목 조회 (톤백 목록)"""
        return self.get_tonbags(lot_no=lot_no)

    # ══════════════════════════════════════════════════════════
    # inventory_tonbag 테이블 조회
    # ══════════════════════════════════════════════════════════

    def get_all_tonbags(self) -> List[Dict]:
        """전체 톤백 조회 (tonbag_tab 호환)"""
        return self.get_tonbags()

    def get_tonbags_with_inventory(self) -> List[Dict]:
        """v3.9.0: 톤백 + 재고(LOT) 정보 JOIN 조회
        
        톤백리스트 탭용 — 재고리스트 18열 + TONBAG NO + LOCATION = 20열
        v5.6.3: 톤백 개별 current/initial 보강 — Balance/Inbound 표시용
        """
        try:
            query = """
                SELECT 
                    i.lot_no, i.sap_no, i.bl_no, i.container_no,
                    i.product, i.mxbg_pallet, 
                    t.sub_lt AS tonbag_no,
                    t.location,
                    t.is_sample,
                    i.net_weight, i.salar_invoice_no,
                    i.ship_date, i.arrival_date,
                    i.free_time, i.warehouse,
                    t.status AS tonbag_status,
                    i.customs,
                    i.current_weight, i.initial_weight,
                    t.weight AS tonbag_weight,
                    t.weight AS tonbag_initial_weight,
                    CASE WHEN t.status IN ('PICKED','SOLD','SHIPPED','DEPLETED') THEN 0 ELSE t.weight END AS tonbag_current_weight,
                    t.picked_date, t.picked_to
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON t.lot_no = i.lot_no
                ORDER BY i.lot_no, t.sub_lt
            """
            rows = self.db.fetchall(query)
            from engine_modules.tonbag_compat import normalize_rows
            return normalize_rows(_rows_to_dicts(rows))
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"톤백+재고 JOIN 조회 오류: {e}", exc_info=True)
            return []

    def get_tonbags(self, lot_no: str = None, status: str = None) -> List[Dict]:
        """v5.5.3 P5: 톤백 조회 (17열 전체 + normalize_rows)"""
        try:
            query = """
                SELECT id, inventory_id, lot_no, sub_lt, sap_no, bl_no,
                       weight, status, location, picked_to, pick_ref,
                       inbound_date, picked_date, outbound_date,
                       remarks, created_at, updated_at
                FROM inventory_tonbag WHERE 1=1
            """
            params = []
            if lot_no:
                query += " AND lot_no = ?"
                params.append(lot_no)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY lot_no, sub_lt"
            rows = self.db.fetchall(query, tuple(params))
            from engine_modules.tonbag_compat import normalize_rows
            return normalize_rows(_rows_to_dicts(rows))
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"톤백 조회 오류: {e}")
            return []

    # v5.1.0: 하위 호환 래퍼
    def get_sublots(self, lot_no: str = None, status: str = None) -> List[Dict]:
        """[Deprecated] get_tonbags()로 대체. 하위 호환용."""
        return self.get_tonbags(lot_no=lot_no, status=status)

    # ══════════════════════════════════════════════════════════
    # 요약/집계
    # ══════════════════════════════════════════════════════════
    def get_inventory_summary(self) -> Dict:
        """재고 요약 조회"""
        try:
            query = """
                SELECT
                    COUNT(*) as total_lots,
                    COALESCE(SUM(initial_weight), 0) as total_weight_kg,
                    COALESCE(SUM(current_weight), 0) as available_weight_kg,
                    COALESCE(SUM(picked_weight), 0) as picked_weight_kg,
                    COALESCE(SUM(COALESCE(initial_weight,0) - COALESCE(current_weight,0) - COALESCE(picked_weight,0)), 0) as sold_weight_kg,
                    COALESCE(SUM(mxbg_pallet), 0) as total_bags
                FROM inventory
            """
            row = self.db.fetchone(query)
            if not row:
                return {}
            data = _row_to_dict(row)
            for key in ['total_weight_kg', 'available_weight_kg',
                        'picked_weight_kg', 'sold_weight_kg']:
                data[key.replace('_kg', '_mt')] = (data.get(key) or 0) / 1000
            return data
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"재고 요약 조회 오류: {e}")
            return {}

    def get_inventory_by_product(self) -> List[Dict]:
        """제품별 재고 조회"""
        try:
            query = """
                SELECT product,
                       COUNT(*) as lot_count,
                       COALESCE(SUM(initial_weight), 0) as total_kg,
                       COALESCE(SUM(current_weight), 0) as available_kg,
                       COALESCE(SUM(mxbg_pallet), 0) as bag_count
                FROM inventory
                GROUP BY product ORDER BY product
            """
            rows = self.db.fetchall(query)
            return _rows_to_dicts(rows)
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"제품별 재고 조회 오류: {e}")
            return []

    def get_inventory_by_customer(self) -> List[Dict]:
        """고객별 재고 조회 (톤백 기준)"""
        try:
            query = """
                SELECT COALESCE(picked_to, '미배정') as customer,
                       COUNT(DISTINCT lot_no) as lot_count,
                       COALESCE(SUM(weight), 0) as total_kg,
                       COUNT(*) as bag_count
                FROM inventory_tonbag
                WHERE status IN ('PICKED', 'OUTBOUND')
                GROUP BY picked_to ORDER BY total_kg DESC
            """
            rows = self.db.fetchall(query)
            return _rows_to_dicts(rows)
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"고객별 재고 조회 오류: {e}")
            return []

    def search_lots(self, keyword: str = None, **filters) -> List[Dict]:
        """LOT 검색"""
        try:
            query = "SELECT * FROM inventory WHERE 1=1"
            params = []
            if keyword:
                query += """
                    AND (lot_no LIKE ? OR bl_no LIKE ?
                         OR product LIKE ? OR sap_no LIKE ?)
                """
                kw = f"%{keyword}%"
                params.extend([kw, kw, kw, kw])
            safe_columns = {
                'status', 'product', 'bl_no', 'sap_no',
                'warehouse', 'sold_to', 'container_no'
            }
            for key, value in filters.items():
                if value and key in safe_columns:
                    query += f" AND {key} = ?"
                    params.append(value)
            query += " ORDER BY COALESCE(arrival_date, created_at) DESC LIMIT 100"
            rows = self.db.fetchall(query, tuple(params))
            return _rows_to_dicts(rows)
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"LOT 검색 오류: {e}")
            return []
