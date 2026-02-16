# -*- coding: utf-8 -*-
"""
SQM Inventory - Database Migration Mixin
=========================================

v3.9.6 - Extracted from database.py (1,378 lines → 분할)

마이그레이션 함수들만 분리:
- _migrate_v243
- _migrate_v289_picking_list
- _migrate_v388_column_unify
- _migrate_v391_sample_tonbag
- _migrate_v396_search_indexes
"""

import logging
import re
import sqlite3
from utils.path_utils import resolve_reports_dir  # v5.3.4

logger = logging.getLogger(__name__)


class DatabaseMigrationMixin:
    """마이그레이션 전용 Mixin — SQMDatabase에 MRO로 합성"""

    def _run_all_migrations(self) -> None:
        """모든 마이그레이션 순차 실행 (v243 제외 — database.py에서 직접 호출)"""
        self._migrate_v289_picking_list()
        self._migrate_v388_column_unify()
        self._migrate_v391_sample_tonbag()
        self._migrate_v396_search_indexes()
        self._migrate_v420_tonbag_uid()
        self._migrate_v423_tonbag_location()
        self._migrate_v520_tonbag_no_text()

    def _migrate_v420_tonbag_uid(self) -> None:
        """
        v4.2.0: inventory_tonbag.tonbag_uid 추가 + 백필 + 트리거
        
        규칙:
        - 일반 톤백: {lot_no}-{sub_lt}  예) 1125072340-1
        - 샘플: {lot_no}-S0  예) 1125072340-S0
        """
        try:
            # ========================================
            # 1단계: 컬럼 추가
            # ========================================
            try:
                self.execute("ALTER TABLE inventory_tonbag ADD COLUMN tonbag_uid TEXT")
                logger.info("[v4.2.0] inventory_tonbag.tonbag_uid 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate column" in str(e).lower():
                    logger.debug(f"[v4.2.0] tonbag_uid 컬럼 이미 존재: {e}")
                else:
                    raise
            
            # ========================================
            # 2단계: 기존 데이터 백필
            # ========================================
            logger.info("[v4.2.0] 기존 데이터 tonbag_uid 백필 시작...")
            
            # 샘플 톤백 (is_sample=1 또는 sub_lt=0)
            updated_sample = self.execute("""
                UPDATE inventory_tonbag
                SET tonbag_uid = lot_no || '-S0'
                WHERE (COALESCE(is_sample, 0) = 1 OR sub_lt = 0)
                  AND (tonbag_uid IS NULL OR tonbag_uid = '')
            """)
            logger.info(f"[v4.2.0] 샘플 백필 완료")
            
            # 일반 톤백
            updated_normal = self.execute("""
                UPDATE inventory_tonbag
                SET tonbag_uid = lot_no || '-' || CAST(sub_lt AS TEXT)
                WHERE COALESCE(is_sample, 0) = 0
                  AND sub_lt > 0
                  AND (tonbag_uid IS NULL OR tonbag_uid = '')
            """)
            logger.info(f"[v4.2.0] 일반 톤백 백필 완료")
            
            # ========================================
            # 3단계: 유니크 인덱스 생성
            # ========================================
            logger.info("[v4.2.0] 인덱스 생성 시작...")
            
            # UID 전체 유니크
            self.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_tonbag_uid_unique
                ON inventory_tonbag(tonbag_uid)
            """)
            logger.info("[v4.2.0] idx_tonbag_uid_unique 생성 완료")
            
            # 샘플 LOT당 1개 보장
            self.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_tonbag_sample_per_lot
                ON inventory_tonbag(lot_no)
                WHERE COALESCE(is_sample, 0) = 1
            """)
            logger.info("[v4.2.0] idx_tonbag_sample_per_lot 생성 완료")
            
            # ========================================
            # 4단계: INSERT 트리거 (UID 자동 생성)
            # ========================================
            self.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_tonbag_uid_insert
                AFTER INSERT ON inventory_tonbag
                FOR EACH ROW
                WHEN NEW.tonbag_uid IS NULL OR NEW.tonbag_uid = ''
                BEGIN
                    UPDATE inventory_tonbag
                    SET tonbag_uid = CASE
                        WHEN COALESCE(NEW.is_sample, 0) = 1 OR NEW.sub_lt = 0 
                            THEN NEW.lot_no || '-S0'
                        ELSE NEW.lot_no || '-' || CAST(NEW.sub_lt AS TEXT)
                    END
                    WHERE id = NEW.id;
                END;
            """)
            logger.info("[v4.2.0] trg_tonbag_uid_insert 생성 완료")
            
            # ========================================
            # 5단계: UPDATE 트리거 (UID 자동 갱신)
            # ========================================
            self.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_tonbag_uid_update
                AFTER UPDATE OF lot_no, sub_lt, is_sample ON inventory_tonbag
                FOR EACH ROW
                BEGIN
                    UPDATE inventory_tonbag
                    SET tonbag_uid = CASE
                        WHEN COALESCE(NEW.is_sample, 0) = 1 OR NEW.sub_lt = 0 
                            THEN NEW.lot_no || '-S0'
                        ELSE NEW.lot_no || '-' || CAST(NEW.sub_lt AS TEXT)
                    END
                    WHERE id = NEW.id;
                END;
            """)
            logger.info("[v4.2.0] trg_tonbag_uid_update 생성 완료")
            
            # ========================================
            # 6단계: 커밋
            # ========================================
            self.commit()
            logger.info("[v4.2.0] ✅ tonbag_uid 마이그레이션 완료")
            
        except (sqlite3.OperationalError, OSError, sqlite3.IntegrityError) as e:
            logger.error(f"[v4.2.0] ❌ 마이그레이션 실패: {e}")
            self.rollback()
            raise

    def _migrate_v289_picking_list(self) -> None:
        """v2.9.89 마이그레이션: Picking List 테이블 추가
        ⚠️ v5.6.8: 데드 테이블 — 코드에서 사용하지 않음. 기존 DB 호환용 유지."""
        tables = [
            """CREATE TABLE IF NOT EXISTS picking_list_order (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outbound_id INTEGER,
                sales_order TEXT DEFAULT '',
                customer_ref TEXT DEFAULT '',
                picking_date TEXT,
                status TEXT DEFAULT 'DRAFT',
                total_lots INTEGER DEFAULT 0,
                total_weight REAL DEFAULT 0,
                remarks TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (outbound_id) REFERENCES outbound(id)
            )""",
            """CREATE TABLE IF NOT EXISTS picking_list_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                picking_order_id INTEGER NOT NULL,
                lot_no TEXT NOT NULL,
                sub_lt TEXT,
                weight REAL DEFAULT 0,
                picked_status TEXT DEFAULT 'PENDING',
                picked_at TEXT,
                remarks TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (picking_order_id) REFERENCES picking_list_order(id),
                FOREIGN KEY (lot_no) REFERENCES inventory(lot_no)
            )""",
        ]
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_picking_order_outbound ON picking_list_order(outbound_id)",
            "CREATE INDEX IF NOT EXISTS idx_picking_order_sales ON picking_list_order(sales_order)",
            "CREATE INDEX IF NOT EXISTS idx_picking_order_customer ON picking_list_order(customer_ref)",
            "CREATE INDEX IF NOT EXISTS idx_picking_detail_lot ON picking_list_detail(lot_no)",
            "CREATE INDEX IF NOT EXISTS idx_picking_detail_status ON picking_list_detail(picked_status)",
        ]
        try:
            for sql in tables:
                self.execute(sql)
            for sql in indexes:
                self.execute(sql)
            self.commit()
            logger.info("[v2.9.89] Picking List 테이블 마이그레이션 완료")
        except (sqlite3.OperationalError, OSError) as e:
            logger.debug(f"[v2.9.89] Picking List 마이그레이션 스킵: {e}")

    def _migrate_v388_column_unify(self) -> None:
        """v3.8.8: 컬럼명 통일 마이그레이션"""
        add_cols = [
            ("inventory", "salar_invoice_no", "TEXT DEFAULT ''"),
            ("inventory", "ship_date", "TEXT DEFAULT ''"),
            ("inventory", "vessel", "TEXT DEFAULT ''"),
            ("inventory", "arrival_date", "TEXT DEFAULT ''"),
            ("inventory", "inbound_date", "TEXT DEFAULT ''"),
            ("inventory", "initial_weight", "REAL DEFAULT 0"),
            ("inventory", "current_weight", "REAL DEFAULT 0"),
            ("inventory", "picked_weight", "REAL DEFAULT 0"),
            ("inventory", "mxbg_pallet", "INTEGER DEFAULT 0"),
            ("inventory_tonbag", "location", "TEXT DEFAULT ''"),
            ("inventory_tonbag", "picked_to", "TEXT DEFAULT ''"),
            ("inventory_tonbag", "pick_ref", "TEXT DEFAULT ''"),
            ("inventory_tonbag", "picked_date", "TEXT DEFAULT ''"),
            ("inventory_tonbag", "outbound_date", "TEXT DEFAULT ''"),
            ("inventory_tonbag", "remarks", "TEXT DEFAULT ''"),
        ]
        for table, col, col_type in add_cols:
            try:
                self.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except (sqlite3.OperationalError, OSError) as _e:
                logger.debug(f'Suppressed: {_e}')
        try:
            self.commit()
            logger.info("[v3.8.8] 컬럼 통일 마이그레이션 완료")
        except (sqlite3.OperationalError, OSError) as e:
            logger.debug(f"[v3.8.8] 컬럼 통일 마이그레이션 스킵: {e}")

    def _migrate_v391_sample_tonbag(self) -> None:
        """v3.9.1: 샘플 톤백 is_sample 컬럼 추가"""
        try:
            try:
                self.execute("ALTER TABLE inventory_tonbag ADD COLUMN is_sample INTEGER DEFAULT 0")
                logger.info("[v3.9.1] inventory_tonbag.is_sample 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as _e:
                logger.debug(f'Suppressed: {_e}')
            self.execute("""
                UPDATE inventory_tonbag SET is_sample = 1
                WHERE sub_lt = 0 AND (is_sample IS NULL OR is_sample = 0)
            """)
            self.commit()
            logger.info("[v3.9.1] 샘플 톤백 마이그레이션 완료")
        except (sqlite3.OperationalError, OSError) as e:
            logger.debug(f"[v3.9.1] 샘플 톤백 마이그레이션 스킵: {e}")

    def _migrate_v396_search_indexes(self) -> None:
        """v3.9.6: 검색 성능 인덱스 추가"""
        idx_list = [
            "CREATE INDEX IF NOT EXISTS idx_inventory_bl_no ON inventory(bl_no)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_container ON inventory(container_no)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_arrival ON inventory(arrival_date)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_invoice ON inventory(salar_invoice_no)",
            "CREATE INDEX IF NOT EXISTS idx_tonbag_sample ON inventory_tonbag(is_sample)",
            "CREATE INDEX IF NOT EXISTS idx_tonbag_inv_id ON inventory_tonbag(inventory_id)",
        ]
        added = 0
        for sql in idx_list:
            try:
                self.execute(sql)
                added += 1
            except (sqlite3.OperationalError, OSError) as _e:
                logger.debug(f'Suppressed: {_e}')
        if added:
            self.commit()
            logger.info(f"[v3.9.6] 검색 인덱스 {added}개 추가")
    
    def _migrate_v423_tonbag_location(self) -> None:
        """
        v4.2.3: inventory_tonbag.location 컬럼 추가
        
        목적: 바코드 스캔 위치 관리
        형식: A-1-3 (구역-열-층)
        """
        try:
            # ========================================
            # 1단계: location 컬럼 추가
            # ========================================
            try:
                self.execute("ALTER TABLE inventory_tonbag ADD COLUMN location TEXT")
                logger.info("[v4.2.3] inventory_tonbag.location 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate column" in str(e).lower():
                    logger.debug(f"[v4.2.3] location 컬럼 이미 존재: {e}")
                else:
                    raise
            
            # ========================================
            # 2단계: 인덱스 추가 (위치 검색 최적화)
            # ========================================
            try:
                self.execute("CREATE INDEX IF NOT EXISTS idx_tonbag_location ON inventory_tonbag(location)")
                logger.info("[v4.2.3] location 인덱스 생성 완료")
            except (sqlite3.OperationalError, OSError) as e:
                logger.debug(f"[v4.2.3] 인덱스 생성 스킵: {e}")
            
            self.commit()
            logger.info("✅ [v4.2.3] 톤백 위치 관리 마이그레이션 완료")
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as e:
            logger.error(f"❌ [v4.2.3] 톤백 위치 마이그레이션 실패: {e}")
            self.rollback()

    
    def _migrate_v423_tonbag_location(self) -> None:
        """
        v4.2.3: inventory_tonbag.location 추가 (톤백 위치 관리)
        
        컬럼:
        - location: VARCHAR(50) - 톤백 위치 (예: A-1-3, B-2-5)
        - location_updated_at: TEXT - 위치 업데이트 시간
        
        용도:
        - 바코드 스캔으로 톤백 위치 추적
        - Excel 업로드로 일괄 위치 업데이트
        """
        try:
            # ========================================
            # 1단계: location 컬럼 추가
            # ========================================
            try:
                self.execute("ALTER TABLE inventory_tonbag ADD COLUMN location TEXT")
                logger.info("[v4.2.3] inventory_tonbag.location 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate column" in str(e).lower():
                    logger.debug(f"[v4.2.3] location 컬럼 이미 존재: {e}")
                else:
                    raise
            
            # ========================================
            # 2단계: location_updated_at 컬럼 추가
            # ========================================
            try:
                self.execute("ALTER TABLE inventory_tonbag ADD COLUMN location_updated_at TEXT")
                logger.info("[v4.2.3] inventory_tonbag.location_updated_at 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate column" in str(e).lower():
                    logger.debug(f"[v4.2.3] location_updated_at 컬럼 이미 존재: {e}")
                else:
                    raise
            
            # ========================================
            # 3단계: 인덱스 생성
            # ========================================
            try:
                self.execute("CREATE INDEX IF NOT EXISTS idx_tonbag_location ON inventory_tonbag(location)")
                logger.info("[v4.2.3] location 인덱스 생성 완료")
            except (sqlite3.OperationalError, OSError) as e:
                logger.debug(f"[v4.2.3] 인덱스 생성 실패 (무시): {e}")
            
            self.commit()
            logger.info("✅ [v4.2.3] 톤백 위치 관리 마이그레이션 완료")
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as e:
            logger.error(f"❌ [v4.2.3] 톤백 위치 마이그레이션 실패: {e}")
            raise

    def _migrate_v520_tonbag_no_text(self) -> None:
        """
        v5.2.0: tonbag_no TEXT 컬럼 추가 + 기존 데이터 백필 + sale_ref 컬럼
        
        규칙:
        - 일반 톤백: sub_lt → "001", "002", ... (3자리 패딩)
        - 샘플: sub_lt=0 → "S00"
        """
        try:
            # 1단계: tonbag_no 컬럼 추가
            try:
                self.execute("ALTER TABLE inventory_tonbag ADD COLUMN tonbag_no TEXT")
                logger.info("[v5.2.0] inventory_tonbag.tonbag_no 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate column" in str(e).lower():
                    logger.debug(f"[v5.2.0] tonbag_no 컬럼 이미 존재")
                else:
                    raise

            # 2단계: sale_ref 컬럼 추가 (출고 참조번호)
            try:
                self.execute("ALTER TABLE inventory_tonbag ADD COLUMN sale_ref TEXT")
                logger.info("[v5.2.0] inventory_tonbag.sale_ref 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate column" in str(e).lower():
                    logger.debug(f"[v5.2.0] sale_ref 컬럼 이미 존재")
                else:
                    raise

            # 3단계: 기존 데이터 백필 (sub_lt → tonbag_no)
            rows = self.fetchall(
                "SELECT id, sub_lt, is_sample FROM inventory_tonbag WHERE tonbag_no IS NULL"
            )
            if rows:
                logger.info(f"[v5.2.0] tonbag_no 백필: {len(rows)}건")
                for row in rows:
                    raw_sub_lt = row.get('sub_lt')
                    is_sample = int(row.get('is_sample') or 0)
                    if is_sample == 1 or str(raw_sub_lt or '0').strip() in ('0', ''):
                        tonbag_no = "S00"
                    else:
                        s = str(raw_sub_lt).strip()
                        if re.fullmatch(r"\d+", s):
                            tonbag_no = s.zfill(3)
                        else:
                            raise ValueError(f"[v5.2.0] tonbag_no 백필 실패: 비정형 sub_lt={s} (id={row.get('id')})")
                    self.execute(
                        "UPDATE inventory_tonbag SET tonbag_no = ? WHERE id = ?",
                        (tonbag_no, row['id'])
                    )
                logger.info(f"[v5.2.0] tonbag_no 백필 완료: {len(rows)}건")

            # 4단계: 인덱스 생성
            try:
                self.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_tonbag_bl_lot_no "
                    "ON inventory_tonbag(bl_no, lot_no, tonbag_no)"
                )
                self.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tonbag_tonbag_no "
                    "ON inventory_tonbag(tonbag_no)"
                )
                logger.info("[v5.2.0] tonbag_no 인덱스 생성 완료")
            except (sqlite3.OperationalError, OSError) as e:
                logger.debug(f"[v5.2.0] 인덱스 생성 (무시): {e}")

            self.commit()
            logger.info("✅ [v5.2.0] tonbag_no TEXT 마이그레이션 완료")

        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as e:
            logger.error(f"❌ [v5.2.0] tonbag_no 마이그레이션 실패: {e}")
            raise


    # --------------------------
    # v5.3.0 Migration
    # --------------------------
    def _migrate_v530_add_sublt_audit_and_mapping(self, conn):
        """v5.3.0: Add audit columns for raw sub_lt and create mapping history table.
        - Adds tonbags.source_sub_lt_raw TEXT / tonbags.source_sub_lt_hdr TEXT (if missing)
        - Creates tonbag_mapping_history table (if missing)
        - Backfills mapping history from tonbags where raw values exist (no fabrication)
        """
        cur = conn.cursor()

        cur.execute("PRAGMA table_info(tonbags)")
        cols = {row[1] for row in cur.fetchall()}
        if 'source_sub_lt_raw' not in cols:
            cur.execute("ALTER TABLE tonbags ADD COLUMN source_sub_lt_raw TEXT")
        if 'source_sub_lt_hdr' not in cols:
            cur.execute("ALTER TABLE tonbags ADD COLUMN source_sub_lt_hdr TEXT")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tonbag_mapping_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bl_no TEXT,
            lot_no TEXT,
            tonbag_no TEXT,
            source_sub_lt_raw TEXT,
            source_sub_lt_hdr TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(bl_no, lot_no, tonbag_no, source_sub_lt_raw)
        )
        """)

        try:
            cur.execute("SELECT bl_no, lot_no, tonbag_no, source_sub_lt_raw, source_sub_lt_hdr FROM tonbags")
            rows = cur.fetchall()
            for bl_no, lot_no, tonbag_no, rawv, rawh in rows:
                if rawv is None and rawh is None:
                    continue
                cur.execute(
                    "INSERT INTO tonbag_mapping_history(bl_no, lot_no, tonbag_no, source_sub_lt_raw, source_sub_lt_hdr) VALUES (?,?,?,?,?)",
                    (bl_no, lot_no, tonbag_no, rawv, rawh)
                )
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as _e:
            logger.debug(f"Suppressed: {_e}")

        conn.commit()