# -*- coding: utf-8 -*-
from __future__ import annotations

from repositories.base_repository import BaseRepository

class InventoryRepository(BaseRepository):
    def get_inventory_summary(self):
        return self.fetchall(
            '''
            SELECT product, COUNT(*) AS item_count, SUM(qty) AS total_qty
            FROM inventory_detail
            GROUP BY product
            ORDER BY product
            '''
        )
