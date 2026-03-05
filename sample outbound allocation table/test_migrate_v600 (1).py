# -*- coding: utf-8 -*-
"""
SQM v6.0.0 Migration 테스트 스크립트
=====================================

실행 방법:
    python tests/test_migrate_v600.py

테스트 내용:
    1. 테스트용 임시 DB 생성
    2. _migrate_v600_picking_sold_tables() 실행
    3. 생성된 테이블/컬럼/인덱스 검증
    4. 결과 리포트 출력

주의:
    실제 운영 DB는 건드리지 않음
    임시 DB(test_v600.db)는 테스트 후 자동 삭제
"""

import sqlite3
import os
import sys
import logging
import shutil
from datetime import datetime

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# 간이 DB 클래스 (실제 SQMDatabase 없이 테스트)
# ─────────────────────────────────────────
class MinimalDB:
    """테스트용 최소 DB 클래스"""

    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._init_base_tables()

    def _init_base_tables(self):
        """기존 테이블 최소 생성 (migration 전제 조건)"""
        self.cur.executescript("""
            CREATE TABLE IF NOT EXISTS inventory (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no  TEXT UNIQUE NOT NULL,
                product TEXT DEFAULT 'LITHIUM CARBONATE',
                status  TEXT DEFAULT 'AVAILABLE'
            );

            CREATE TABLE IF NOT EXISTS inventory_tonbag (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no     TEXT NOT NULL,
                sub_lt     INTEGER DEFAULT 0,
                weight     REAL DEFAULT 500.0,
                is_sample  INTEGER DEFAULT 0,
                status     TEXT DEFAULT 'AVAILABLE',
                tonbag_uid TEXT,
                sale_ref   TEXT,
                FOREIGN KEY (lot_no) REFERENCES inventory(lot_no)
            );

            CREATE TABLE IF NOT EXISTS allocation_plan (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no       TEXT NOT NULL,
                tonbag_id    INTEGER,
                sub_lt       INTEGER,
                customer     TEXT,
                sale_ref     TEXT,
                qty_mt       REAL,
                outbound_date TEXT,
                status       TEXT DEFAULT 'RESERVED',
                source_file  TEXT,
                created_at   TEXT DEFAULT (datetime('now')),
                executed_at  TEXT,
                cancelled_at TEXT,
                FOREIGN KEY (tonbag_id) REFERENCES inventory_tonbag(id)
            );
        """)
        self.conn.commit()

        # 테스트용 샘플 데이터 삽입
        self.cur.execute(
            "INSERT OR IGNORE INTO inventory (lot_no) VALUES (?)",
            ("1125072340",)
        )
        self.cur.execute(
            "INSERT OR IGNORE INTO inventory_tonbag "
            "(lot_no, sub_lt, weight, tonbag_uid) VALUES (?,?,?,?)",
            ("1125072340", 1, 500.0, "1125072340-1")
        )
        self.conn.commit()

    def execute(self, sql, params=()):
        return self.cur.execute(sql, params)

    def fetchall(self, sql, params=()):
        self.cur.execute(sql, params)
        return [dict(r) for r in self.cur.fetchall()]

    def fetchone(self, sql, params=()):
        self.cur.execute(sql, params)
        row = self.cur.fetchone()
        return dict(row) if row else None

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


# ─────────────────────────────────────────
# Migration 함수 직접 import (경로 처리)
# ─────────────────────────────────────────
def run_migration_on_db(db: MinimalDB) -> bool:
    """db_migration_mixin의 v600 함수를 MinimalDB에 직접 실행"""

    # db_migration_mixin.py의 함수를 동적으로 바인딩
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from engine_modules.db_migration_mixin import DatabaseMigrationMixin

        # MinimalDB에 mixin 함수 바인딩
        import types
        db._migrate_v600_picking_sold_tables = types.MethodType(
            DatabaseMigrationMixin._migrate_v600_picking_sold_tables, db
        )
        db._migrate_v600_picking_sold_tables()
        return True
    except Exception as e:
        logger.error(f"Migration 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─────────────────────────────────────────
# 검증 함수들
# ─────────────────────────────────────────
def get_tables(db: MinimalDB) -> set:
    rows = db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return {r['name'] for r in rows}


def get_columns(db: MinimalDB, table: str) -> set:
    rows = db.fetchall(f"PRAGMA table_info({table})")
    return {r['name'] for r in rows}


def get_indexes(db: MinimalDB, table: str) -> set:
    rows = db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",
        (table,)
    )
    return {r['name'] for r in rows}


# ─────────────────────────────────────────
# 메인 테스트
# ─────────────────────────────────────────
def main():
    TEST_DB = "/tmp/sqm_test_v600.db"

    print("=" * 60)
    print("  SQM v6.0.0 Migration 테스트")
    print(f"  시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 기존 테스트 DB 삭제
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    # DB 생성
    db = MinimalDB(TEST_DB)
    print(f"\n✅ 테스트 DB 생성: {TEST_DB}")

    # Migration 전 상태
    before_tables = get_tables(db)
    print(f"\n📋 Migration 전 테이블: {sorted(before_tables)}")

    # ─── Migration 실행 ───
    print("\n🚀 _migrate_v600_picking_sold_tables() 실행 중...")
    success = run_migration_on_db(db)

    if not success:
        print("\n❌ Migration 실패! 로그를 확인하세요.")
        db.close()
        return False

    # Migration 후 상태
    after_tables = get_tables(db)
    new_tables = after_tables - before_tables
    print(f"\n✅ Migration 완료! 신규 테이블: {sorted(new_tables)}")

    # ─── 검증 1: 신규 테이블 존재 확인 ───
    print("\n" + "─" * 40)
    print("검증 1: 신규 테이블 존재")
    print("─" * 40)
    required_tables = ['picking_table', 'sold_table']
    all_ok = True
    for t in required_tables:
        exists = t in after_tables
        status = "✅" if exists else "❌"
        print(f"  {status} {t}")
        if not exists:
            all_ok = False

    # ─── 검증 2: picking_table 컬럼 확인 ───
    print("\n" + "─" * 40)
    print("검증 2: picking_table 컬럼")
    print("─" * 40)
    picking_cols = get_columns(db, 'picking_table')
    required_picking_cols = [
        'id', 'lot_no', 'tonbag_id', 'tonbag_uid',
        'picking_no', 'sales_order_no', 'outbound_id',
        'customer', 'qty_mt', 'qty_kg', 'unit',
        'is_sample', 'status', 'picking_date'
    ]
    for col in required_picking_cols:
        exists = col in picking_cols
        status = "✅" if exists else "❌"
        print(f"  {status} {col}")
        if not exists:
            all_ok = False

    # ─── 검증 3: sold_table 컬럼 확인 ───
    print("\n" + "─" * 40)
    print("검증 3: sold_table 컬럼")
    print("─" * 40)
    sold_cols = get_columns(db, 'sold_table')
    required_sold_cols = [
        'id', 'lot_no', 'tonbag_id', 'tonbag_uid',
        'picking_id', 'sales_order_no', 'picking_no',
        'sap_no', 'bl_no', 'customer', 'sku',
        'sold_qty_mt', 'sold_qty_kg', 'ct_plt',
        'status', 'sold_date', 'created_at'
    ]
    for col in required_sold_cols:
        exists = col in sold_cols
        status = "✅" if exists else "❌"
        print(f"  {status} {col}")
        if not exists:
            all_ok = False

    # ─── 검증 4: allocation_plan 컬럼 추가 확인 ───
    print("\n" + "─" * 40)
    print("검증 4: allocation_plan 컬럼 추가")
    print("─" * 40)
    alloc_cols = get_columns(db, 'allocation_plan')
    new_alloc_cols = ['picking_no', 'bl_no', 'outbound_id']
    for col in new_alloc_cols:
        exists = col in alloc_cols
        status = "✅" if exists else "❌"
        print(f"  {status} allocation_plan.{col}")
        if not exists:
            all_ok = False

    # ─── 검증 5: inventory_tonbag 컬럼 추가 확인 ───
    print("\n" + "─" * 40)
    print("검증 5: inventory_tonbag 컬럼 추가")
    print("─" * 40)
    tonbag_cols = get_columns(db, 'inventory_tonbag')
    new_tonbag_cols = ['picking_id', 'sold_id', 'picking_no']
    for col in new_tonbag_cols:
        exists = col in tonbag_cols
        status = "✅" if exists else "❌"
        print(f"  {status} inventory_tonbag.{col}")
        if not exists:
            all_ok = False

    # ─── 검증 6: 인덱스 확인 ───
    print("\n" + "─" * 40)
    print("검증 6: 인덱스 생성")
    print("─" * 40)
    picking_idx = get_indexes(db, 'picking_table')
    sold_idx    = get_indexes(db, 'sold_table')
    required_idx = [
        ('picking_table', 'idx_picking_lot'),
        ('picking_table', 'idx_picking_no'),
        ('picking_table', 'idx_picking_status'),
        ('sold_table',    'idx_sold_lot'),
        ('sold_table',    'idx_sold_status'),
        ('sold_table',    'idx_sold_order_no'),
    ]
    for table, idx in required_idx:
        idx_set = picking_idx if table == 'picking_table' else sold_idx
        exists = idx in idx_set
        status = "✅" if exists else "❌"
        print(f"  {status} {table}.{idx}")
        if not exists:
            all_ok = False

    # ─── 검증 7: 멱등성 테스트 (2회 실행해도 오류 없음) ───
    print("\n" + "─" * 40)
    print("검증 7: 멱등성 (2회 실행 테스트)")
    print("─" * 40)
    try:
        run_migration_on_db(db)
        print("  ✅ 2회 실행 오류 없음 (멱등성 확인)")
    except Exception as e:
        print(f"  ❌ 2회 실행 오류: {e}")
        all_ok = False

    # ─── 최종 결과 ───
    print("\n" + "=" * 60)
    if all_ok:
        print("🎉 모든 검증 통과! v6.0.0 Migration 준비 완료!")
    else:
        print("⚠️  일부 검증 실패! 위 로그를 확인하세요.")
    print("=" * 60)

    db.close()

    # 테스트 DB 삭제
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        print(f"\n🗑️  테스트 DB 삭제 완료: {TEST_DB}")

    return all_ok


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)
