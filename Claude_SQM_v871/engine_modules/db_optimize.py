# -*- coding: utf-8 -*-
"""
SQM DB 성능 최적화 — P2 개선 #6
★ 기존 인덱스: 단일 컬럼 위주 (db_schema_mixin + db_migration_mixin)
★ 이 파일 추가: 실제 쿼리 패턴 기반 복합 인덱스 + WAL 설정 강화
생성일: 2026-04-08 | SQM v8.7.1

배치 위치: engine_modules/db_optimize.py
호출 위치: SQMDatabase.__init__() 마지막에 추가
  → self._run_db_optimize()
"""
import logging
import sqlite3

logger = logging.getLogger(__name__)

# ================================================================
# 추가할 복합 인덱스 목록
# 기준: outbound_mixin / query_mixin 실제 쿼리 패턴 분석
# ================================================================
COMPOSITE_INDEXES = [

    # ── allocation_plan 복합 인덱스 ───────────────────────────
    # execute_reserved() 에서 자주 사용:
    # WHERE status='RESERVED' AND lot_no=? AND outbound_date<=?
    (
        "idx_alloc_status_lot_date",
        "allocation_plan",
        "status, lot_no, outbound_date"
    ),
    # confirm_outbound() 후 plan 업데이트:
    # WHERE tonbag_id=? AND status='EXECUTED'
    (
        "idx_alloc_tonbag_status",
        "allocation_plan",
        "tonbag_id, status"
    ),

    # ── inventory_tonbag 복합 인덱스 ──────────────────────────
    # load_picked_tonbags() / load_reserved_plans():
    # WHERE status=? AND lot_no=?
    (
        "idx_tonbag_status_lot",
        "inventory_tonbag",
        "status, lot_no"
    ),
    # recalc_lot_status():
    # GROUP BY status WHERE lot_no=?
    (
        "idx_tonbag_lot_status_cnt",
        "inventory_tonbag",
        "lot_no, status, id"
    ),
    # is_sample 조회 최적화
    (
        "idx_tonbag_lot_sample",
        "inventory_tonbag",
        "lot_no, is_sample, status"
    ),

    # ── sold_table 복합 인덱스 ────────────────────────────────
    # check_double_sold():
    # WHERE tonbag_id=? AND status IN ('OUTBOUND','SOLD')
    (
        "idx_sold_tonbag_status",
        "sold_table",
        "tonbag_id, status"
    ),
    # 날짜+고객 조합 조회 (리포트용)
    (
        "idx_sold_date_customer",
        "sold_table",
        "sold_date, customer"
    ),
    # lot_no + sold_date 조합
    (
        "idx_sold_lot_date",
        "sold_table",
        "lot_no, sold_date"
    ),

    # ── picking_table 복합 인덱스 ─────────────────────────────
    # get_picking_info():
    # WHERE tonbag_id=? ORDER BY id DESC
    (
        "idx_picking_tonbag_id_desc",
        "picking_table",
        "tonbag_id, id"
    ),

    # ── stock_movement 복합 인덱스 ────────────────────────────
    # 이력 조회: WHERE lot_no=? ORDER BY created_at DESC
    (
        "idx_movement_lot_date_desc",
        "stock_movement",
        "lot_no, created_at DESC"
    ),
    # 타입별 조회: WHERE movement_type=? AND created_at>=?
    (
        "idx_movement_type_date",
        "stock_movement",
        "movement_type, created_at"
    ),

    # ── inventory 복합 인덱스 ─────────────────────────────────
    # get_inventory() 정렬: ORDER BY arrival_date DESC, lot_no
    (
        "idx_inv_arrival_lot",
        "inventory",
        "arrival_date DESC, lot_no"
    ),
    # status + product 조합 조회
    (
        "idx_inv_status_product",
        "inventory",
        "status, product_code, lot_no"
    ),
]

# ================================================================
# PRAGMA 설정 (WAL + 성능)
# ================================================================
PRAGMA_SETTINGS = [
    # WAL 모드 — 읽기/쓰기 동시성 향상 (이미 설정됐을 수 있음)
    "PRAGMA journal_mode=WAL",
    # 캐시 크기 증가 (기본 2MB → 16MB)
    "PRAGMA cache_size=-16000",
    # 임시 파일 메모리 저장
    "PRAGMA temp_store=MEMORY",
    # mmap 활성화 (256MB)
    "PRAGMA mmap_size=268435456",
    # 동기화 레벨 (WAL에서 NORMAL이 안전하고 빠름)
    "PRAGMA synchronous=NORMAL",
]


def run_db_optimize(db) -> dict:
    """
    DB 최적화 실행
    Args: db — SQMDatabase 인스턴스 (execute/fetchone 인터페이스)
    Returns: {"indexes_added": int, "indexes_skipped": int, "errors": []}
    """
    result = {"indexes_added": 0, "indexes_skipped": 0, "errors": []}

    # 1) PRAGMA 설정
    for pragma in PRAGMA_SETTINGS:
        try:
            db.execute(pragma)
            logger.debug(f"PRAGMA 적용: {pragma}")
        except Exception as e:
            logger.debug(f"PRAGMA 스킵: {pragma} — {e}")

    # 2) 복합 인덱스 추가
    for idx_name, table, columns in COMPOSITE_INDEXES:
        try:
            # 테이블 존재 확인
            row = db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if not row:
                result["indexes_skipped"] += 1
                logger.debug(f"테이블 없음 — 인덱스 스킵: {idx_name} ({table})")
                continue

            # 인덱스 이미 존재 확인
            existing = db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                (idx_name,)
            )
            if existing:
                result["indexes_skipped"] += 1
                logger.debug(f"인덱스 이미 존재: {idx_name}")
                continue

            db.execute(
                f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({columns})"
            )
            result["indexes_added"] += 1
            logger.info(f"✅ 복합 인덱스 추가: {idx_name} ON {table}({columns})")

        except (sqlite3.OperationalError, OSError) as e:
            result["indexes_skipped"] += 1
            logger.debug(f"인덱스 스킵: {idx_name} — {e}")
        except Exception as e:
            result["errors"].append(f"{idx_name}: {e}")
            logger.warning(f"인덱스 오류: {idx_name} — {e}")

    # 3) ANALYZE — 통계 업데이트 (쿼리 플래너 최적화)
    try:
        db.execute("ANALYZE")
        logger.info("✅ ANALYZE 완료 — 쿼리 플래너 통계 갱신")
    except Exception as e:
        logger.debug(f"ANALYZE 스킵: {e}")

    # 4) 커밋
    try:
        db.commit()
    except Exception:
        pass

    logger.info(
        f"DB 최적화 완료: 인덱스 추가={result['indexes_added']}, "
        f"스킵={result['indexes_skipped']}, "
        f"오류={len(result['errors'])}"
    )
    return result


def get_index_stats(db) -> list:
    """
    현재 DB의 전체 인덱스 목록 반환 (진단용)
    """
    try:
        rows = db.fetchall(
            "SELECT name, tbl_name FROM sqlite_master "
            "WHERE type='index' ORDER BY tbl_name, name"
        )
        return [
            {"index": r[0] if not hasattr(r, 'keys') else r['name'],
             "table": r[1] if not hasattr(r, 'keys') else r['tbl_name']}
            for r in (rows or [])
        ]
    except Exception as e:
        logger.error(f"인덱스 목록 조회 실패: {e}")
        return []
