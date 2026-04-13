"""
InventoryRepository — P2-C-05 신규 생성
기존 query_mixin.py / crud_mixin.py의 핵심 조회/변경 로직을
독립 Repository 클래스로 분리
생성일: 2026-04-08 | SQM v8.7.1

배치 위치: features/repositories/inventory_repository.py
"""
import sqlite3
import logging
from typing import Dict, List, Optional

from features.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


def _to_dict(row) -> dict:
    """sqlite3.Row 또는 tuple → dict 변환"""
    if row is None:
        return {}
    if hasattr(row, 'keys'):
        return dict(row)
    return dict(row)


def _to_dicts(rows) -> list:
    """rows → list of dict"""
    return [_to_dict(r) for r in (rows or [])]


class InventoryRepository(BaseRepository):
    """
    Inventory (재고) 조회 / 변경 Repository
    ★ P2-C: BaseRepository 상속
    ★ engine의 query_mixin / crud_mixin 에서 핵심 메서드 분리
    ★ UI / Service 레이어는 engine 직접 호출 대신 이 클래스 사용 권장
    """

    def __init__(self, db):
        """Args: db — SQMDatabase 인스턴스"""
        super().__init__(db)

    # ================================================================
    # 재고 조회 (SELECT)
    # ================================================================

    def get_inventory(
        self,
        status: str = None,
        product: str = None,
        lot_no: str = None
    ) -> List[Dict]:
        """
        재고 목록 조회 (컬럼 누락 시 폴백 포함)
        [원본 이관] query_mixin.get_inventory()
        """
        query_full = """
            SELECT id, lot_no, sap_no, bl_no, product, product_code,
                   container_no, lot_sqm, sold_to, warehouse, status,
                   location, vessel,
                   initial_weight, current_weight, picked_weight,
                   net_weight, gross_weight, mxbg_pallet,
                   salar_invoice_no, ship_date, arrival_date,
                   con_return, free_time, customs,
                   stock_date, inbound_date, created_at, updated_at
            FROM inventory WHERE 1=1
        """
        query_fallback = """
            SELECT id, lot_no, sap_no, bl_no, product, product_code,
                   container_no, lot_sqm, sold_to, warehouse, status,
                   '' AS location, vessel,
                   initial_weight, current_weight, picked_weight,
                   net_weight, gross_weight, mxbg_pallet,
                   salar_invoice_no, ship_date, arrival_date,
                   con_return, free_time, '' AS customs,
                   stock_date, '' AS inbound_date, created_at, updated_at
            FROM inventory WHERE 1=1
        """
        for query in (query_full, query_fallback):
            try:
                q, params = query, []
                if status:
                    q += " AND status = ?"
                    params.append(status)
                if product:
                    q += " AND product LIKE ?"
                    params.append(f"%{product}%")
                if lot_no:
                    q += " AND lot_no LIKE ?"
                    params.append(f"%{lot_no}%")
                q += " ORDER BY COALESCE(arrival_date, created_at) DESC, lot_no"
                rows = self._fetch_all(q, tuple(params))
                return _to_dicts(rows)
            except (sqlite3.OperationalError, OSError) as e:
                if "no such column" in str(e).lower() and query == query_full:
                    logger.debug(f"재고 조회 폴백 (컬럼 누락): {e}")
                    continue
                logger.error(f"재고 조회 오류: {e}")
                return []
        return []

    def get_inventory_row(self, lot_no: str) -> Optional[Dict]:
        """단일 LOT 행 조회"""
        row = self._fetch_one(
            "SELECT * FROM inventory WHERE lot_no = ?", (lot_no,)
        )
        return _to_dict(row) if row else None

    def get_lot_detail(self, lot_no: str) -> Dict:
        """
        LOT 상세 조회 (톤백 목록 포함)
        [원본 이관] query_mixin.get_lot_detail()
        """
        lot = self.get_inventory_row(lot_no)
        if not lot:
            return {"error": f"LOT not found: {lot_no}"}
        lot["tonbags"] = self.get_tonbags(lot_no=lot_no)
        return lot

    def get_tonbags(
        self,
        lot_no: str = None,
        status: str = None
    ) -> List[Dict]:
        """
        톤백 목록 조회
        [원본 이관] query_mixin.get_tonbags()
        """
        sql = "SELECT * FROM inventory_tonbag WHERE 1=1"
        params = []
        if lot_no:
            sql += " AND lot_no = ?"
            params.append(lot_no)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY sub_lt"
        return _to_dicts(self._fetch_all(sql, tuple(params)))

    def get_inventory_summary(self) -> Dict:
        """
        재고 요약 (LOT 수, 총 중량, 가용 중량 등)
        [원본 이관] query_mixin.get_inventory_summary()
        """
        try:
            row = self._fetch_one("""
                SELECT
                    COUNT(*) as total_lots,
                    COALESCE(SUM(initial_weight), 0)  as total_weight_kg,
                    COALESCE(SUM(current_weight), 0)  as available_weight_kg,
                    COALESCE(SUM(picked_weight), 0)   as picked_weight_kg,
                    COALESCE(SUM(
                        COALESCE(initial_weight,0)
                        - COALESCE(current_weight,0)
                        - COALESCE(picked_weight,0)
                    ), 0) as sold_weight_kg,
                    COALESCE(SUM(mxbg_pallet), 0) as total_bags
                FROM inventory
            """)
            if not row:
                return {}
            data = _to_dict(row)
            for key in ['total_weight_kg', 'available_weight_kg',
                        'picked_weight_kg', 'sold_weight_kg']:
                data[key.replace('_kg', '_mt')] = (data.get(key) or 0) / 1000
            return data
        except Exception as e:
            logger.error(f"재고 요약 조회 오류: {e}")
            return {}

    def get_inventory_by_product(self) -> List[Dict]:
        """제품별 재고 집계"""
        try:
            rows = self._fetch_all("""
                SELECT product, product_code,
                       COUNT(*) as lot_count,
                       COALESCE(SUM(current_weight), 0) as total_weight_kg,
                       COALESCE(SUM(mxbg_pallet), 0) as total_bags
                FROM inventory
                WHERE status NOT IN ('OUTBOUND', 'SOLD', 'DEPLETED')
                GROUP BY product, product_code
                ORDER BY total_weight_kg DESC
            """)
            return _to_dicts(rows)
        except Exception as e:
            logger.error(f"제품별 재고 조회 오류: {e}")
            return []

    def count_tonbags(
        self,
        status: str = None,
        lot_no: str = None
    ) -> int:
        """
        톤백 수 카운트
        [원본 이관] query_mixin.count_tonbags()
        """
        where_parts = []
        params = []
        if status:
            where_parts.append("status = ?")
            params.append(status)
        if lot_no:
            where_parts.append("lot_no = ?")
            params.append(lot_no)
        where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
        return self.row_count("inventory_tonbag", where.replace("WHERE ", ""), tuple(params))

    def inventory_lot_exists(self, lot_no: str) -> bool:
        """LOT 존재 여부"""
        row = self._fetch_one(
            "SELECT 1 FROM inventory WHERE lot_no = ? LIMIT 1", (lot_no,)
        )
        return row is not None

    def search_lots(self, keyword: str = None, **filters) -> List[Dict]:
        """
        LOT 검색
        [원본 이관] query_mixin.search_lots()
        """
        sql = "SELECT * FROM inventory WHERE 1=1"
        params = []
        if keyword:
            sql += " AND (lot_no LIKE ? OR bl_no LIKE ? OR container_no LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        for col in ['status', 'product', 'warehouse', 'sold_to']:
            if filters.get(col):
                sql += f" AND {col} = ?"
                params.append(filters[col])
        sql += " ORDER BY COALESCE(arrival_date, created_at) DESC"
        return _to_dicts(self._fetch_all(sql, tuple(params)))

    # ================================================================
    # 재고 변경 (INSERT / UPDATE)
    # ================================================================

    def update_inventory_field(
        self,
        lot_no: str,
        updates: Dict
    ) -> dict:
        """
        LOT 필드 업데이트 (범용)
        ★ with self.db.transaction() 블록 안에서 호출할 것
        """
        if not updates:
            return {"ok": False, "error": "업데이트 항목 없음"}
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        updates['updated_at'] = now
        set_clause = ', '.join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [lot_no]
        try:
            self._execute(
                f"UPDATE inventory SET {set_clause} WHERE lot_no = ?",
                tuple(params)
            )
            return {"ok": True, "error": None}
        except Exception as e:
            self._log.error(f"update_inventory_field 실패 [{lot_no}]: {e}")
            return {"ok": False, "error": str(e)}

    def get_cargo_overview_counts(self, scope: str = 'all') -> Dict:
        """
        화물 현황 카운트 (대시보드용)
        [원본 이관] query_mixin.get_cargo_overview_counts()
        """
        try:
            rows = self._fetch_all("""
                SELECT status, COUNT(*) as cnt,
                       COALESCE(SUM(current_weight), 0) as weight_kg
                FROM inventory
                GROUP BY status
            """)
            result = {}
            for r in rows:
                d = _to_dict(r)
                result[d.get('status', '')] = {
                    "count":     d.get('cnt', 0),
                    "weight_kg": d.get('weight_kg', 0),
                    "weight_mt": round((d.get('weight_kg', 0) or 0) / 1000, 3)
                }
            return result
        except Exception as e:
            logger.error(f"cargo_overview_counts 오류: {e}")
            return {}
