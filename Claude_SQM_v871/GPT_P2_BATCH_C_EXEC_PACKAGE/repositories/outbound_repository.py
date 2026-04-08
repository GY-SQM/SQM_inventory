# -*- coding: utf-8 -*-
from __future__ import annotations

from repositories.base_repository import BaseRepository

class OutboundRepository(BaseRepository):
    def get_tonbag(self, tonbag_no: str):
        row = self.fetchone(
            '''
            SELECT tonbag_no, status, lot_no, bl_no
            FROM inventory_tonbag
            WHERE tonbag_no = ?
            ''',
            (tonbag_no,),
        )
        if not row:
            return None
        keys = ["tonbag_no", "status", "lot_no", "bl_no"]
        return dict(zip(keys, row))

    def mark_sold(self, tonbag_no: str) -> int:
        cur = self.execute(
            '''
            UPDATE inventory_tonbag
            SET status = 'SOLD'
            WHERE tonbag_no = ?
            ''',
            (tonbag_no,),
        )
        return cur.rowcount
