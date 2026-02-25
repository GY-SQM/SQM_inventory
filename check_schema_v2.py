import sqlite3
import os

# Use the workspace path provided in user_info
db_path = "sqm_inventory.db" 
# Or search for it
if not os.path.exists(db_path):
    # Try absolute path based on workspace
    db_path = r"g:\프로그램\Sqm 재고관리\SQM_v611\sqm_inventory.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    print(f"Opening database at {db_path}")
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
