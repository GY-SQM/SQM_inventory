# -*- coding: utf-8 -*-
"""
SQM v5.9.4 — DB 스키마 초기화 Mixin
====================================

database.py에서 분리 (1242줄 → ~660 + ~580).
테이블 생성(_init_*), 마이그레이션(_migrate_v243),
스키마 검증(_verify_schema), 인덱스 생성(_create_indexes)을 담당.
"""
import sqlite3
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DatabaseSchemaMixin:
    """DB 스키마 초기화/검증/인덱스 — SQMDatabase에 MRO 합성"""

    def _init_database(self) -> None:
        """데이터베이스 테이블 초기화 (v4.0.3: 섹션별 분리)"""
        self._init_shipment_table()
        self._init_inventory_table()
        self._init_tonbag_table()
        self._init_outbound_tables()
        self._init_movement_tables()
        self._init_snapshot_tables()
        self._migrate_v243()
        # v6.0: allocation_plan / picking_table / sold_table 은 반드시 생성 (v243 중간 실패 시에도)
        self._ensure_allocation_and_picking_sold_tables()
        # 최신 마이그레이션 체인 실행 (idempotent). 신규 컬럼/인덱스 보강 반영.
        try:
            self._run_all_migrations()
        except Exception as e:
            logger.warning(f"[스키마] 전체 마이그레이션 체인 실행 스킵/실패: {e}")

    def _ensure_allocation_and_picking_sold_tables(self) -> None:
        """allocation_plan, picking_table, sold_table 존재 보장 (예약·출고 이력용)."""
        try:
            self._migrate_v593_allocation_plan()
        except Exception as e:
            logger.warning(f"[스키마] allocation_plan 생성 스킵/실패: {e}")
        try:
            self._migrate_v600_picking_sold_tables()
        except Exception as e:
            logger.warning(f"[스키마] picking_table/sold_table 생성 스킵/실패: {e}")

    def _init_shipment_table(self) -> None:
        """선적(Shipment) 테이블"""
        self.execute("""
            CREATE TABLE IF NOT EXISTS shipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sap_no TEXT UNIQUE,
                folio TEXT,
                bl_no TEXT,
                container_no TEXT,
                product TEXT,
                product_code TEXT,
                origin TEXT DEFAULT 'Chile',
                destination TEXT DEFAULT '광양',
                ship_date DATE,
                arrival_date DATE,
                total_net_weight REAL,
                total_gross_weight REAL,
                port_of_loading TEXT,
                port_of_discharge TEXT,
                vessel TEXT,
                status TEXT DEFAULT 'ARRIVED',
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("[스키마] shipment 테이블 생성 완료")

    def _init_inventory_table(self) -> None:
        """재고(Inventory) 테이블 — v2.5.4: LOT 단위 통합 재고"""
        self.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT UNIQUE NOT NULL,
                lot_sqm TEXT,
                sap_no TEXT,
                bl_no TEXT,
                container_no TEXT,
                product TEXT NOT NULL DEFAULT 'LITHIUM CARBONATE',
                product_code TEXT,
                net_weight REAL DEFAULT 0,
                gross_weight REAL DEFAULT 0,
                initial_weight REAL DEFAULT 0,
                current_weight REAL DEFAULT 0,
                picked_weight REAL DEFAULT 0,
                mxbg_pallet INTEGER DEFAULT 0,
                tonbag_count INTEGER DEFAULT 0,
                ship_date DATE,
                arrival_date DATE,
                stock_date DATE,
                salar_invoice_no TEXT,
                warehouse TEXT DEFAULT '광양',
                status TEXT DEFAULT 'AVAILABLE',
                sold_to TEXT,
                sale_ref TEXT,
                vessel TEXT,
                free_time INTEGER DEFAULT 0,
                con_return TEXT,
                location TEXT,
                customs TEXT,
                inbound_date TEXT,
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("[스키마] inventory 테이블 생성 완료")

        self.execute("""
            CREATE TABLE IF NOT EXISTS inventory_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                container_no TEXT,
                net_weight REAL DEFAULT 0,
                gross_weight REAL DEFAULT 0,
                mxbg_pallet INTEGER DEFAULT 0,
                location TEXT,
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lot_no) REFERENCES inventory(lot_no) ON DELETE CASCADE
            )
        """)
        logger.info("[스키마] inventory_detail 테이블 생성 완료")

    def _init_tonbag_table(self) -> None:
        """톤백(inventory_tonbag) 테이블 — 개별 톤백 관리"""
        self.execute("""
            CREATE TABLE IF NOT EXISTS inventory_tonbag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,
                lot_no TEXT NOT NULL,
                sap_no TEXT,
                bl_no TEXT,
                inbound_date TEXT,
                sub_lt INTEGER NOT NULL DEFAULT 0,
                weight REAL DEFAULT 500.0,
                is_sample INTEGER DEFAULT 0,
                status TEXT DEFAULT 'AVAILABLE',
                location TEXT,
                location_updated_at TEXT,
                picked_to TEXT,
                picked_date TEXT,
                pick_ref TEXT,
                outbound_date TEXT,
                sale_ref TEXT,
                tonbag_uid TEXT,
                source_sub_lt_raw TEXT,
                source_sub_lt_hdr TEXT,
                con_return TEXT,
                tonbag_no TEXT,
                remarks TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lot_no) REFERENCES inventory(lot_no) ON DELETE CASCADE,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id)
            )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_tonbag_lot ON inventory_tonbag(lot_no)")
        # idx_tonbag_inventory_id는 _migrate_v591_tonbag_fk_columns()에서 생성 (구 DB에 inventory_id 추가 후)
        self.execute("CREATE INDEX IF NOT EXISTS idx_tonbag_status ON inventory_tonbag(status)")
        self.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tonbag_lot_sublt ON inventory_tonbag(lot_no, sub_lt)")
        logger.info("[스키마] inventory_tonbag 테이블 생성 완료")

    def _init_outbound_tables(self) -> None:
        """출고(outbound + outbound_item) 테이블"""
        self.execute("""
            CREATE TABLE IF NOT EXISTS outbound (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_ref TEXT,
                customer TEXT,
                total_qty_mt REAL DEFAULT 0,
                outbound_date DATE,
                destination TEXT,
                status TEXT DEFAULT 'PENDING',
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.execute("""
            CREATE TABLE IF NOT EXISTS outbound_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outbound_id INTEGER,
                inventory_id INTEGER,
                lot_no TEXT NOT NULL,
                sub_lt INTEGER,
                qty_kg REAL DEFAULT 0,
                inbound_date DATE,
                location TEXT,
                customer TEXT,
                destination TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (outbound_id) REFERENCES outbound(id) ON DELETE CASCADE,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id)
            )
        """)
        logger.info("[스키마] outbound, outbound_item 테이블 생성 완료")

    def _init_movement_tables(self) -> None:
        """재고 이동 이력(stock_movement) + 반품(return_history) 테이블"""
        self.execute("""
            CREATE TABLE IF NOT EXISTS stock_movement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                qty_kg REAL DEFAULT 0,
                from_location TEXT,
                to_location TEXT,
                customer TEXT,
                movement_date TIMESTAMP,
                source_type TEXT DEFAULT '',
                source_file TEXT DEFAULT '',
                ref_table TEXT,
                ref_id INTEGER,
                source TEXT,
                actor TEXT,
                details_json TEXT,
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lot_no) REFERENCES inventory(lot_no)
            )
        """)
        try:
            # 구 DB(컬럼 미존재)에서는 초기화 단계에서 실패할 수 있으므로 마이그레이션에서 재시도.
            self.execute(
                "CREATE INDEX IF NOT EXISTS idx_stock_mv_ref ON stock_movement(ref_table, ref_id)"
            )
        except sqlite3.OperationalError as e:
            logger.debug(f"[스키마] idx_stock_mv_ref 생성 지연(마이그레이션에서 재시도): {e}")
        self.execute("""
            CREATE TABLE IF NOT EXISTS return_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                sub_lt INTEGER,
                return_date DATE,
                original_customer TEXT,
                original_sale_ref TEXT,
                reason TEXT,
                remark TEXT,
                weight_kg REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lot_no) REFERENCES inventory(lot_no)
            )
        """)
        logger.info("[스키마] stock_movement, return_history 테이블 생성 완료")

        self.execute("""
            CREATE TABLE IF NOT EXISTS allocation_import_batch (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT,
                conflict_policy TEXT DEFAULT 'block_duplicates',
                total_lines INTEGER DEFAULT 0,
                passed_lines INTEGER DEFAULT 0,
                failed_lines INTEGER DEFAULT 0,
                report_csv_path TEXT,
                report_json_path TEXT,
                imported_at TEXT DEFAULT (datetime('now'))
            )
        """)
        logger.info("[스키마] allocation_import_batch 테이블 생성 완료")

    def _init_snapshot_tables(self) -> None:
        """재고 스냅샷(inventory_snapshot) 테이블"""
        self.execute("""
            CREATE TABLE IF NOT EXISTS inventory_snapshot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date DATE NOT NULL,
                total_lots INTEGER DEFAULT 0,
                total_tonbags INTEGER DEFAULT 0,
                total_weight_kg REAL DEFAULT 0,
                available_weight_kg REAL DEFAULT 0,
                picked_weight_kg REAL DEFAULT 0,
                product_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_date)
            )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_date ON inventory_snapshot(snapshot_date)")
        logger.info("[스키마] inventory_snapshot 테이블 생성 완료")

    def _migrate_v243(self) -> None:
        """v2.4.3 스키마 마이그레이션 — 출고 리스트 필드 추가 + 톤백 테이블 이름 변경"""
        try:
            self.execute("ALTER TABLE inventory_sublot RENAME TO inventory_tonbag")
            logger.info("[마이그레이션] inventory_sublot → inventory_tonbag 이름 변경됨")
        except sqlite3.OperationalError as e:
            if "no such table" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.debug(f"[마이그레이션] 테이블 이름 변경 스킵: {e}")

        migrations = [
            ("shipment", "port_of_loading", "TEXT"),
            ("shipment", "port_of_discharge", "TEXT"),
            ("shipment", "total_net_weight", "REAL"),
            ("shipment", "total_gross_weight", "REAL"),
            ("outbound", "destination", "TEXT"),
            ("outbound", "remarks", "TEXT"),
            ("outbound_item", "inbound_date", "DATE"),
            ("outbound_item", "location", "TEXT"),
            ("outbound_item", "customer", "TEXT"),
            ("outbound_item", "destination", "TEXT"),
            ("inventory_tonbag", "sale_ref", "TEXT"),
        ]
        for table, column, col_type in migrations:
            try:
                self.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                logger.info(f"[마이그레이션] {table}.{column} 추가됨")
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    logger.debug(f"[마이그레이션] {table}.{column} 스킵: {e}")

        self._migrate_v289_picking_list()
        self._migrate_v388_column_unify()
        self._migrate_v391_sample_tonbag()
        self._migrate_v396_search_indexes()
        self._migrate_v588_con_return()
        self._migrate_v591_tonbag_fk_columns()
        self._migrate_v593_allocation_plan()
        self._migrate_v599_missing_columns()
        self._migrate_v600_picking_sold_tables()

    def _verify_schema(self) -> Dict[str, Any]:
        """DB 스키마 자동 점검 — 필수 테이블/컬럼 확인"""
        result = {
            'ok': True, 'missing_tables': [],
            'missing_columns': {}, 'warnings': []
        }
        required_tables = [
            'shipment', 'inventory', 'inventory_tonbag', 'outbound', 'outbound_item',
            'allocation_plan',  # v5.9.3 예약(RESERVED) 이력
        ]
        required_columns = {
            'shipment': ['sap_no', 'bl_no', 'arrival_date', 'origin', 'destination'],
            'inventory': ['lot_no', 'sap_no', 'product', 'current_weight', 'status'],
            'inventory_tonbag': ['lot_no', 'sub_lt', 'weight', 'status'],
        }
        try:
            existing_tables = self.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
            existing_table_names = {row['name'] for row in existing_tables}
            for table in required_tables:
                if table not in existing_table_names:
                    result['missing_tables'].append(table)
                    result['ok'] = False
            # allocation_plan 누락 시 마이그레이션 재시도 (구 DB 호환)
            if 'allocation_plan' in result['missing_tables']:
                try:
                    self._migrate_v593_allocation_plan()
                    self._migrate_v600_picking_sold_tables()
                    existing_tables = self.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
                    existing_table_names = {row['name'] for row in existing_tables}
                    if 'allocation_plan' in existing_table_names:
                        result['missing_tables'] = [t for t in result['missing_tables'] if t != 'allocation_plan']
                        result['ok'] = not result['missing_tables'] and not result['missing_columns']
                        logger.info("[스키마 점검] allocation_plan 생성 후 보정 완료")
                except Exception as e:
                    logger.debug(f"[스키마 점검] allocation_plan 보정 스킵: {e}")
            for table, columns in required_columns.items():
                if table not in existing_table_names:
                    continue
                existing_cols = self.fetchall(f"PRAGMA table_info({table})")
                existing_col_names = {row['name'] for row in existing_cols}
                missing = [col for col in columns if col not in existing_col_names]
                if missing:
                    result['missing_columns'][table] = missing
                    result['ok'] = False
            if result['ok']:
                logger.info("[스키마 점검] ✅ 모든 필수 테이블/컬럼 확인됨")
            else:
                if result['missing_tables']:
                    logger.warning(f"[스키마 점검] ⚠️ 누락된 테이블: {result['missing_tables']}")
                if result['missing_columns']:
                    logger.warning(f"[스키마 점검] ⚠️ 누락된 컬럼: {result['missing_columns']}")
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"[스키마 점검] 오류: {e}")
            result['ok'] = False
            result['warnings'].append(str(e))
        return result

    def get_schema_status(self) -> Dict[str, Any]:
        """외부에서 스키마 상태 조회용"""
        return self._verify_schema()

    def _create_indexes(self) -> None:
        """성능 향상을 위한 인덱스 생성"""
        indexes = [
            ("idx_inventory_lot_no", "inventory", "lot_no"),
            ("idx_inventory_sap_no", "inventory", "sap_no"),
            ("idx_inventory_status", "inventory", "status"),
            ("idx_inventory_stock_date", "inventory", "stock_date"),
            ("idx_inventory_created_at", "inventory", "created_at"),
            ("idx_inventory_stock_created", "inventory", "stock_date, created_at"),
            ("idx_inventory_product", "inventory", "product_code"),
            ("idx_inventory_warehouse", "inventory", "warehouse"),
            ("idx_inventory_bl_no_nocase", "inventory", "bl_no COLLATE NOCASE"),
            ("idx_inventory_lot_product", "inventory", "lot_no, product_code"),
            ("idx_inventory_sap_status", "inventory", "sap_no, status"),
            ("idx_inventory_product_status", "inventory", "product_code, status"),
            ("idx_detail_lot_no", "inventory_detail", "lot_no"),
            ("idx_detail_container", "inventory_detail", "container_no"),
            ("idx_detail_lot_container", "inventory_detail", "lot_no, container_no"),
            ("idx_shipment_sap_no", "shipment", "sap_no"),
            ("idx_shipment_bl_no", "shipment", "bl_no"),
            ("idx_shipment_folio", "shipment", "folio"),
            ("idx_shipment_status", "shipment", "status"),
            ("idx_outbound_sale_ref", "outbound", "sale_ref"),
            ("idx_outbound_customer", "outbound", "customer"),
            ("idx_outbound_date", "outbound", "outbound_date"),
            ("idx_outbound_item_lot", "outbound_item", "lot_no"),
            ("idx_outbound_item_inventory", "outbound_item", "inventory_id"),
            ("idx_outbound_item_outbound", "outbound_item", "outbound_id"),
            ("idx_movement_lot", "stock_movement", "lot_no"),
            ("idx_movement_type", "stock_movement", "movement_type"),
            ("idx_movement_date", "stock_movement", "created_at"),
            ("idx_movement_lot_created", "stock_movement", "lot_no, created_at"),
        ]
        for idx_name, table, columns in indexes:
            try:
                self.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({columns})")
            except sqlite3.OperationalError as e:
                logger.debug(f"인덱스 생성 스킵: {idx_name} - {e}")
        try:
            self.execute("ANALYZE")
        except (sqlite3.Error, OSError) as e:
            logger.debug(f"ANALYZE 실패: {e}")
