# -*- coding: utf-8 -*-
from __future__ import annotations

from repositories.base_repository import BaseRepository

class InboundRepository(BaseRepository):
    def save_parsed_inbound(self, parsed) -> int:
        created = 0
        with self.transaction():
            for row in parsed.get("items", []):
                self.execute(
                    '''
                    INSERT INTO inventory_detail (bl_no, lot_no, product, qty, inbound_date)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (
                        row.get("bl_no"),
                        row.get("lot_no"),
                        row.get("product"),
                        row.get("qty"),
                        row.get("inbound_date"),
                    ),
                )
                created += 1
        return created
