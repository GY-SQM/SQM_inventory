# -*- coding: utf-8 -*-
"""
P2-C-03 — InventoryRepository: 재고 조회 Pilot.
BaseRepository 기반 재고 관련 조회 레포지토리.
"""
from __future__ import annotations

import logging
from features.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class InventoryRepository(BaseRepository):
    """재고 조회 레포지토리 (Pilot)."""

    def get_inventory_summary(self) -> list:
        """제품별 재고 요약 조회."""
        return self.fetchall(
            """SELECT product, COUNT(*) AS item_count,
                      COALESCE(SUM(current_weight), 0) AS total_weight
               FROM inventory
               GROUP BY product
               ORDER BY product"""
        )

    def get_lot_by_no(self, lot_no: str) -> dict:
        """LOT 번호로 재고 1건 조회."""
        row = self.fetchone(
            "SELECT * FROM inventory WHERE lot_no = ?",
            (lot_no,)
        )
        return dict(row) if row else None

    def lot_exists(self, lot_no: str) -> bool:
        """LOT 존재 여부 확인."""
        row = self.fetchone(
            "SELECT 1 FROM inventory WHERE lot_no = ? LIMIT 1",
            (lot_no,)
        )
        return bool(row)

    def get_tonbag_status_summary(self, lot_no: str) -> dict:
        """LOT별 톤백 상태 요약."""
        rows = self.fetchall(
            "SELECT status, COUNT(*) AS cnt FROM inventory_tonbag "
            "WHERE lot_no = ? GROUP BY status",
            (lot_no,)
        )
        result = {}
        for r in (rows or []):
            if isinstance(r, dict):
                result[r['status']] = r['cnt']
            else:
                result[r[0]] = r[1]
        return result
