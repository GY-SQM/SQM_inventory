import os
import sqlite3

db_path = "sqm_inventory.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tables = ['allocation_plan', 'picking_table', 'sold_table', 'inventory_tonbag']
    for table in tables:
        print(f"--- Table: {table} ---")
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            for col in columns:
                print(col)
        except Exception as e:
            print(f"Error reading table {table}: {e}")
    conn.close()
