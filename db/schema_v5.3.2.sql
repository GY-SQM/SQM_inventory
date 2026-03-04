-- SQM Inventory System
-- Schema Freeze: v5.3.2
-- Generated: 2026-02-13 KST
-- Notes:
-- - tonbag_no TEXT
-- - UNIQUE(bl_no, lot_no, tonbag_no)
-- - audit: source_sub_lt_raw/source_sub_lt_hdr
-- - mapping history with UNIQUE

CREATE TABLE IF NOT EXISTS tonbags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bl_no TEXT NOT NULL,
  lot_no TEXT NOT NULL,
  tonbag_no TEXT NOT NULL,
  is_sample INTEGER NOT NULL DEFAULT 0,
  net_weight_kg REAL,
  status TEXT DEFAULT 'AVAILABLE',
  source_sub_lt_raw TEXT,
  source_sub_lt_hdr TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT,
  UNIQUE(bl_no, lot_no, tonbag_no)
);

CREATE INDEX IF NOT EXISTS idx_tonbags_bl_lot
ON tonbags(bl_no, lot_no);

CREATE INDEX IF NOT EXISTS idx_tonbags_bl_lot_tonbag
ON tonbags(bl_no, lot_no, tonbag_no);

CREATE TABLE IF NOT EXISTS tonbag_mapping_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bl_no TEXT,
  lot_no TEXT,
  tonbag_no TEXT,
  source_sub_lt_raw TEXT,
  source_sub_lt_hdr TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(bl_no, lot_no, tonbag_no, source_sub_lt_raw)
);
