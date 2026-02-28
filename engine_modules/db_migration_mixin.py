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
        self._migrate_v588_con_return()
        self._migrate_v591_tonbag_fk_columns()
        self._migrate_v593_allocation_plan()
        self._migrate_v5992_allocation_source()
        self._migrate_v599_missing_columns()
        self._migrate_v600_picking_sold_tables()
        self._migrate_v601_picking_list_meta()
        self._migrate_v622_query_indexes()
        self._migrate_v623_stock_movement_audit_columns()

    def _migrate_v622_query_indexes(self) -> None:
        """
        v6.2.2: 조회/후속연결 성능 인덱스 보강
        - 입고현황 조회 기간 필터(stock_date, created_at)
        - D/O 후속 연결 BL 매칭(case-insensitive)
        - LOT 이동 이력 조회(lot_no + created_at)
        """
        idx_sql = [
            "CREATE INDEX IF NOT EXISTS idx_inventory_created_at ON inventory(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_stock_created ON inventory(stock_date, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_bl_no_nocase ON inventory(bl_no COLLATE NOCASE)",
            "CREATE INDEX IF NOT EXISTS idx_movement_lot_created ON stock_movement(lot_no, created_at)",
        ]
        added = 0
        for sql in idx_sql:
            try:
                self.execute(sql)
                added += 1
            except (sqlite3.OperationalError, OSError) as _e:
                logger.debug(f"[v6.2.2] 인덱스 생성 스킵: {_e}")
        if added:
            try:
                self.execute("ANALYZE")
            except (sqlite3.OperationalError, OSError) as _e:
                logger.debug(f"[v6.2.2] ANALYZE 스킵: {_e}")
            self.commit()
            logger.info(f"[v6.2.2] 조회 성능 인덱스 {added}개 점검/생성")

    def _migrate_v623_stock_movement_audit_columns(self) -> None:
        """
        v6.2.3: stock_movement 감사 추적 컬럼 보강
        - source_type: 변경 출처 구분
        - source_file: 원본 파일 경로/파일명
        """
        try:
            try:
                self.execute("ALTER TABLE stock_movement ADD COLUMN source_type TEXT DEFAULT ''")
                logger.info("[v6.2.3] stock_movement.source_type 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    logger.debug(f"[v6.2.3] stock_movement.source_type 이미 존재: {e}")
                else:
                    raise

            try:
                self.execute("ALTER TABLE stock_movement ADD COLUMN source_file TEXT DEFAULT ''")
                logger.info("[v6.2.3] stock_movement.source_file 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    logger.debug(f"[v6.2.3] stock_movement.source_file 이미 존재: {e}")
                else:
                    raise
            self.commit()
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as e:
            logger.error(f"[v6.2.3] stock_movement 감사 컬럼 마이그레이션 실패: {e}")
            self.rollback()

    def _migrate_v601_picking_list_meta(self) -> None:
        """v6.1.0: picking_list_order 메타데이터 컬럼 추가 (Gate-1 연동)."""
        add_cols = [
            ('picking_list_order', 'picking_no', "TEXT DEFAULT ''"),
            ('picking_list_order', 'delivery_terms', "TEXT DEFAULT ''"),
            ('picking_list_order', 'port_loading', "TEXT DEFAULT ''"),
            ('picking_list_order', 'port_discharge', "TEXT DEFAULT ''"),
            ('picking_list_order', 'containers', "INTEGER DEFAULT 1"),
            ('picking_list_order', 'contact_person', "TEXT DEFAULT ''"),
            ('picking_list_order', 'contact_email', "TEXT DEFAULT ''"),
            ('picking_list_order', 'total_nw_kg', "TEXT DEFAULT ''"),
            ('picking_list_order', 'total_gw_kg', "TEXT DEFAULT ''"),
            ('picking_list_order', 'gate1_result', "TEXT DEFAULT ''"),
        ]
        for table, col, col_type in add_cols:
            try:
                self.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_type}')
                logger.info(f'[v6.1.0] {table}.{col} 추가')
            except sqlite3.OperationalError as e:
                logger.debug(f'[v6.1.0] {col} 이미 존재: {e}')
        try:
            self.commit()
        except sqlite3.OperationalError:
            pass

    def _migrate_v588_con_return(self) -> None:
        """
        v5.8.8: inventory.con_return, inventory_tonbag.con_return 추가
        D/O의 Free_Time 컬럼 = 컨테이너 반납일(날짜). free_time = (con_return - arrival_date) 일수.
        """
        try:
            for table, col in [('inventory', 'con_return'), ('inventory_tonbag', 'con_return')]:
                try:
                    self.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
                    logger.info(f"[v5.8.8] {table}.{col} 컬럼 추가 완료")
                except (sqlite3.OperationalError, OSError) as e:
                    if 'duplicate' in str(e).lower() or 'already exists' in str(e).lower():
                        logger.debug(f"[v5.8.8] {table}.{col} 이미 존재: {e}")
                    else:
                        raise
            self.commit()
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as e:
            logger.error(f"[v5.8.8] con_return 마이그레이션 실패: {e}")
            self.rollback()

    def _migrate_v599_missing_columns(self) -> None:
        """
        v5.9.9: 누락된 컬럼 추가 (query_mixin, dashboard, inventory_tab 오류 방지)
        - inventory.customs: 통관 상태
        - inventory.location: 보관 위치
        - stock_movement.movement_date: 이동 시각 (created_at에서 백필)
        - stock_movement.customer: 고객
        """
        try:
            # inventory.customs
            try:
                self.execute("ALTER TABLE inventory ADD COLUMN customs TEXT")
                logger.info("[v5.9.9] inventory.customs 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    logger.debug(f"[v5.9.9] inventory.customs 이미 존재: {e}")
                else:
                    raise
            # inventory.location
            try:
                self.execute("ALTER TABLE inventory ADD COLUMN location TEXT")
                logger.info("[v5.9.9] inventory.location 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    logger.debug(f"[v5.9.9] inventory.location 이미 존재: {e}")
                else:
                    raise
            # stock_movement.movement_date
            try:
                self.execute("ALTER TABLE stock_movement ADD COLUMN movement_date TIMESTAMP")
                logger.info("[v5.9.9] stock_movement.movement_date 컬럼 추가 완료")
                try:
                    self.execute("UPDATE stock_movement SET movement_date = created_at WHERE movement_date IS NULL")
                    self.commit()
                except (sqlite3.OperationalError, OSError) as _e:
                    logger.debug(f"[v5.9.9] movement_date 백필 스킵: {_e}")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    logger.debug(f"[v5.9.9] stock_movement.movement_date 이미 존재: {e}")
                else:
                    raise
            # stock_movement.customer
            try:
                self.execute("ALTER TABLE stock_movement ADD COLUMN customer TEXT")
                logger.info("[v5.9.9] stock_movement.customer 컬럼 추가 완료")
            except (sqlite3.OperationalError, OSError) as e:
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    logger.debug(f"[v5.9.9] stock_movement.customer 이미 존재: {e}")
                else:
                    raise
            self.commit()
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as e:
            logger.error(f"[v5.9.9] missing columns 마이그레이션 실패: {e}")
            self.rollback()

    def _migrate_v600_picking_sold_tables(self) -> None:
        """
        v6.0.0: SQM v6.0 4단계 상태 모델 — picking_table + sold_table 신규 생성
                allocation_plan 컬럼 확장 (picking_no, bl_no, outbound_id 추가)

        상태 모델:
            AVAILABLE → RESERVED(allocation_plan) → PICKED(picking_table) → SOLD(sold_table)

        Picking List PDF 파싱 결과 저장:
            picking_table: Batch number(lot_no) + Quantity(MT/KG) + customer_ref(Picking No)

        Sales Order Excel 처리 결과 저장:
            sold_table: LOT NO + Picking No 매칭 → SOLD 또는 PENDING
        """
        try:
            # STEP 1. allocation_plan 컬럼 확장
            extra_cols = [
                ("picking_no", "TEXT"),
                ("bl_no", "TEXT"),
                ("outbound_id", "TEXT"),
            ]
            for col_name, col_type in extra_cols:
                try:
                    self.execute(
                        f"ALTER TABLE allocation_plan ADD COLUMN {col_name} {col_type}"
                    )
                    logger.info(f"[v6.0.0] allocation_plan.{col_name} 컬럼 추가")
                except (sqlite3.OperationalError, OSError) as e:
                    if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                        logger.debug(f"[v6.0.0] allocation_plan.{col_name} 이미 존재")
                    else:
                        raise
            self.commit()

            # STEP 2. picking_table 신규 생성
            self.execute("""
                CREATE TABLE IF NOT EXISTS picking_table (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    lot_no           TEXT    NOT NULL,
                    tonbag_id        INTEGER,
                    sub_lt           INTEGER,
                    tonbag_uid       TEXT,
                    picking_no       TEXT,
                    sales_order_no   TEXT,
                    outbound_id      TEXT,
                    customer         TEXT,
                    plan_loading     TEXT,
                    creation_date    TEXT,
                    source_file      TEXT,
                    qty_mt           REAL,
                    qty_kg           REAL,
                    unit             TEXT,
                    is_sample        INTEGER DEFAULT 0,
                    storage_location TEXT,
                    status           TEXT DEFAULT 'ACTIVE',
                    picking_date     TEXT DEFAULT (datetime('now')),
                    sold_date        TEXT,
                    created_by       TEXT DEFAULT 'system',
                    remark           TEXT,
                    FOREIGN KEY (lot_no)    REFERENCES inventory(lot_no),
                    FOREIGN KEY (tonbag_id) REFERENCES inventory_tonbag(id)
                )
            """)
            for idx_sql in [
                "CREATE INDEX IF NOT EXISTS idx_picking_lot       ON picking_table(lot_no)",
                "CREATE INDEX IF NOT EXISTS idx_picking_no        ON picking_table(picking_no)",
                "CREATE INDEX IF NOT EXISTS idx_picking_sales_ord ON picking_table(sales_order_no)",
                "CREATE INDEX IF NOT EXISTS idx_picking_uid       ON picking_table(tonbag_uid)",
                "CREATE INDEX IF NOT EXISTS idx_picking_status    ON picking_table(status)",
                "CREATE INDEX IF NOT EXISTS idx_picking_date      ON picking_table(picking_date)",
            ]:
                try:
                    self.execute(idx_sql)
                except (sqlite3.OperationalError, OSError) as _e:
                    logger.debug(f"[v6.0.0] picking_table 인덱스 스킵: {_e}")
            self.commit()
            logger.info("[v6.0.0] picking_table 생성 완료")

            # STEP 3. sold_table 신규 생성
            self.execute("""
                CREATE TABLE IF NOT EXISTS sold_table (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    lot_no           TEXT    NOT NULL,
                    tonbag_id        INTEGER,
                    sub_lt           INTEGER,
                    tonbag_uid       TEXT,
                    picking_id       INTEGER,
                    sales_order_no   TEXT,
                    sales_order_file TEXT,
                    picking_no       TEXT,
                    sap_no           TEXT,
                    bl_no            TEXT,
                    customer         TEXT,
                    sku              TEXT,
                    delivery_date    TEXT,
                    sold_qty_mt      REAL,
                    sold_qty_kg      REAL,
                    ct_plt           INTEGER,
                    status           TEXT DEFAULT 'PENDING',
                    sold_date        TEXT,
                    created_at       TEXT DEFAULT (datetime('now')),
                    confirmed_by     TEXT,
                    created_by       TEXT DEFAULT 'system',
                    remark           TEXT,
                    FOREIGN KEY (lot_no)     REFERENCES inventory(lot_no),
                    FOREIGN KEY (tonbag_id)  REFERENCES inventory_tonbag(id),
                    FOREIGN KEY (picking_id) REFERENCES picking_table(id)
                )
            """)
            for idx_sql in [
                "CREATE INDEX IF NOT EXISTS idx_sold_lot        ON sold_table(lot_no)",
                "CREATE INDEX IF NOT EXISTS idx_sold_uid        ON sold_table(tonbag_uid)",
                "CREATE INDEX IF NOT EXISTS idx_sold_order_no   ON sold_table(sales_order_no)",
                "CREATE INDEX IF NOT EXISTS idx_sold_picking_no ON sold_table(picking_no)",
                "CREATE INDEX IF NOT EXISTS idx_sold_status     ON sold_table(status)",
                "CREATE INDEX IF NOT EXISTS idx_sold_date       ON sold_table(sold_date)",
                "CREATE INDEX IF NOT EXISTS idx_sold_customer   ON sold_table(customer)",
            ]:
                try:
                    self.execute(idx_sql)
                except (sqlite3.OperationalError, OSError) as _e:
                    logger.debug(f"[v6.0.0] sold_table 인덱스 스킵: {_e}")
            self.commit()
            logger.info("[v6.0.0] sold_table 생성 완료")

            # STEP 4. inventory_tonbag 컬럼 추가
            tonbag_extra_cols = [
                ("picking_id", "INTEGER"),
                ("sold_id", "INTEGER"),
                ("picking_no", "TEXT"),
            ]
            for col_name, col_type in tonbag_extra_cols:
                try:
                    self.execute(
                        f"ALTER TABLE inventory_tonbag ADD COLUMN {col_name} {col_type}"
                    )
                    logger.info(f"[v6.0.0] inventory_tonbag.{col_name} 추가")
                except (sqlite3.OperationalError, OSError) as e:
                    if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                        logger.debug(f"[v6.0.0] inventory_tonbag.{col_name} 이미 존재")
                    else:
                        raise
            self.commit()
            logger.info("✅ [v6.0.0] picking_table + sold_table Migration 완료")

        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as e:
            logger.error(f"❌ [v6.0.0] Migration 실패: {e}")
            self.rollback()
            raise

    def _migrate_v591_tonbag_fk_columns(self) -> None:
        """
        v5.9.1: inventory_tonbag에 FK·입고일·톤백번호·비고 컬럼 추가 (입고 업로드 시 INSERT 실패 방지)
        - inventory_id, sap_no, bl_no, inbound_date (필수)
        - tonbag_no, remarks (v5.2.0 미실행 등 방어용)
        """
        columns_to_add = [
            ("inventory_id", "INTEGER"),
            ("sap_no", "TEXT"),
            ("bl_no", "TEXT"),
            ("inbound_date", "TEXT"),
            ("tonbag_no", "TEXT"),
            ("remarks", "TEXT DEFAULT ''"),
        ]
        try:
            for col_name, col_type in columns_to_add:
                try:
                    self.execute(
                        f"ALTER TABLE inventory_tonbag ADD COLUMN {col_name} {col_type}"
                    )
                    logger.info(f"[v5.9.1] inventory_tonbag.{col_name} 컬럼 추가 완료")
                except (sqlite3.OperationalError, OSError) as e:
                    if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                        logger.debug(f"[v5.9.1] inventory_tonbag.{col_name} 이미 존재: {e}")
                    else:
                        raise
            self.commit()

            # 백필: inventory_id
            try:
                self.execute("""
                    UPDATE inventory_tonbag
                    SET inventory_id = (
                        SELECT i.id FROM inventory i WHERE i.lot_no = inventory_tonbag.lot_no
                    )
                    WHERE inventory_id IS NULL
                """)
                logger.info("[v5.9.1] inventory_id 백필 완료")
            except (sqlite3.OperationalError, OSError) as e:
                logger.debug(f"[v5.9.1] inventory_id 백필 스킵: {e}")

            # 백필: sap_no
            try:
                self.execute("""
                    UPDATE inventory_tonbag SET sap_no = (
                        SELECT COALESCE(i.sap_no,'') FROM inventory i
                        WHERE i.lot_no = inventory_tonbag.lot_no
                    ) WHERE sap_no IS NULL OR sap_no = ''
                """)
                logger.info("[v5.9.1] sap_no 백필 완료")
            except (sqlite3.OperationalError, OSError) as e:
                logger.debug(f"[v5.9.1] sap_no 백필 스킵: {e}")

            # 백필: bl_no
            try:
                self.execute("""
                    UPDATE inventory_tonbag SET bl_no = (
                        SELECT COALESCE(i.bl_no,'') FROM inventory i
                        WHERE i.lot_no = inventory_tonbag.lot_no
                    ) WHERE bl_no IS NULL OR bl_no = ''
                """)
                logger.info("[v5.9.1] bl_no 백필 완료")
            except (sqlite3.OperationalError, OSError) as e:
                logger.debug(f"[v5.9.1] bl_no 백필 스킵: {e}")

            # 백필: inbound_date (패치에 없던 부분 추가)
            try:
                self.execute("""
                    UPDATE inventory_tonbag SET inbound_date = (
                        SELECT COALESCE(i.stock_date, i.arrival_date, i.ship_date, date('now'))
                        FROM inventory i WHERE i.lot_no = inventory_tonbag.lot_no
                    ) WHERE inbound_date IS NULL OR inbound_date = ''
                """)
                logger.info("[v5.9.1] inbound_date 백필 완료")
            except (sqlite3.OperationalError, OSError) as e:
                logger.debug(f"[v5.9.1] inbound_date 백필 스킵: {e}")

            # 백필: tonbag_no (v5.2.0 미실행 시 — S00/001 형식)
            try:
                rows = self.fetchall(
                    "SELECT id, sub_lt, is_sample FROM inventory_tonbag WHERE tonbag_no IS NULL"
                )
                if rows:
                    for row in rows:
                        raw_sub_lt = row.get('sub_lt')
                        is_sample = int(row.get('is_sample') or 0)
                        if is_sample == 1 or str(raw_sub_lt or '0').strip() in ('0', ''):
                            tonbag_no = "S00"
                        else:
                            s = str(raw_sub_lt).strip()
                            tonbag_no = s.zfill(3) if re.fullmatch(r"\d+", s) else "001"
                        self.execute(
                            "UPDATE inventory_tonbag SET tonbag_no = ? WHERE id = ?",
                            (tonbag_no, row['id'])
                        )
                    logger.info(f"[v5.9.1] tonbag_no 백필 완료: {len(rows)}건")
            except (sqlite3.OperationalError, OSError, ValueError) as e:
                logger.debug(f"[v5.9.1] tonbag_no 백필 스킵: {e}")

            self.commit()
            logger.info("[v5.9.1] inventory_tonbag 백필 완료")

            # 인덱스
            try:
                self.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tonbag_inventory_id ON inventory_tonbag(inventory_id)"
                )
                self.commit()
            except (sqlite3.OperationalError, OSError) as _e:
                logger.debug(f"[v5.9.1] 인덱스 생성 스킵: {_e}")

        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as e:
            logger.error(f"[v5.9.1] inventory_tonbag FK 컬럼 마이그레이션 실패: {e}")
            self.rollback()

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

    def _migrate_v593_allocation_plan(self) -> None:
        """
        v5.9.3: allocation_plan 테이블 — Allocation 엑셀에서 파싱된 출고 계획 저장.
        톤백을 RESERVED 상태로 예약하고, 출고일 도래 시 PICKED로 전환.
        """
        try:
            self.execute("""
                CREATE TABLE IF NOT EXISTS allocation_plan (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lot_no TEXT NOT NULL,
                    tonbag_id INTEGER,
                    sub_lt INTEGER,
                    customer TEXT,
                    sale_ref TEXT,
                    qty_mt REAL,
                    outbound_date TEXT,
                    status TEXT DEFAULT 'RESERVED',
                    source_file TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    executed_at TEXT,
                    cancelled_at TEXT,
                    FOREIGN KEY (tonbag_id) REFERENCES inventory_tonbag(id)
                )
            """)
            self.execute("""
                CREATE INDEX IF NOT EXISTS idx_alloc_plan_lot 
                ON allocation_plan(lot_no)
            """)
            self.execute("""
                CREATE INDEX IF NOT EXISTS idx_alloc_plan_status 
                ON allocation_plan(status)
            """)
            self.execute("""
                CREATE INDEX IF NOT EXISTS idx_alloc_plan_date 
                ON allocation_plan(outbound_date)
            """)
            logger.info("[v5.9.3] allocation_plan 테이블 생성 완료")
        except (sqlite3.OperationalError, OSError) as e:
            if "already exists" not in str(e).lower():
                logger.warning(f"[v5.9.3] allocation_plan 생성 오류: {e}")
            else:
                logger.debug(f"[v5.9.3] allocation_plan 이미 존재")

    def _migrate_v5992_allocation_source(self) -> None:
        """v5.9.92: allocation_plan.source — 출고 경로 구분 (AUTO/QUICK/EXCEL 등)."""
        try:
            self.execute("ALTER TABLE allocation_plan ADD COLUMN source TEXT DEFAULT 'AUTO'")
            logger.info("[v5.9.92] allocation_plan.source 컬럼 추가 완료")
        except (sqlite3.OperationalError, OSError) as e:
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                logger.debug("[v5.9.92] allocation_plan.source 이미 존재")
            else:
                logger.warning(f"[v5.9.92] allocation_plan.source 추가 오류: {e}")