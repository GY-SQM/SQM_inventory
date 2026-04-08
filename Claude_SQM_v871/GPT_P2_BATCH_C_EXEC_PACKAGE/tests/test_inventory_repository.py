# -*- coding: utf-8 -*-
import sqlite3

from repositories.inventory_repository import InventoryRepository

def test_inventory_summary():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE inventory_detail (product TEXT, qty REAL)"
    )
    conn.execute("INSERT INTO inventory_detail (product, qty) VALUES ('P1', 10)")
    conn.execute("INSERT INTO inventory_detail (product, qty) VALUES ('P1', 20)")
    conn.commit()

    repo = InventoryRepository(conn)
    rows = repo.get_inventory_summary()

    assert len(rows) == 1
