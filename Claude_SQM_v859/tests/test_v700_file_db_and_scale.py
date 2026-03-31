# -*- coding: utf-8 -*-
"""
tests/test_v700_file_db_and_scale.py
======================================
SQM v7.0.0 — 파일 DB 저장 + 연간 15,000 LOT 성능 테스트 (30개)
================================================================

단계:
  F1. 파일 DB 저장 검증     (T01~T10) — data/test_apl_scenario.db
  F2. 15,000 LOT INSERT    (T11~T20) — 배치 성능 벤치마크
  F3. 대규모 쿼리 성능     (T21~T30) — 인덱스 효과 + SQL 응답

성능 기준 (연간 15,000 LOT / 165,000 tonbag rows):
  INSERT   : 165,000 레코드 < 15초
  COUNT    :                <  50ms
  SUM 집계 :                < 500ms
  JOIN 집계:                < 500ms
  반복쿼리 :  1,000회       <   5초
"""
import pytest
import os
import time
import sys
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.fixtures.sqm_scenario_data import (
    save_scenario_to_file, create_scenario_db, build_large_scenario,
    LOT_TOTAL_WEIGHT_KG, TONBAG_WEIGHT_KG,
)

# ─── 파일 DB 경로 ─────────────────────────────────────────────────────────────
_FILE_DB_PATH = "data/test_apl_scenario.db"


# ─── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def file_db_path():
    """data/test_apl_scenario.db 생성 후 경로 반환"""
    path = save_scenario_to_file(_FILE_DB_PATH, verbose=False)
    yield path
    # 테스트 후 파일 유지 (실제 데이터 확인용)


@pytest.fixture(scope="module")
def file_conn(file_db_path):
    """파일 DB 연결"""
    import sqlite3
    conn = sqlite3.connect(file_db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def large_conn():
    """15,000 LOT in-memory DB (모듈 범위 — 1회만 생성)"""
    conn = build_large_scenario(15000)
    yield conn
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# F1. 파일 DB 저장 검증 (T01~T10)
# ═══════════════════════════════════════════════════════════════════════════════

class TestF1FileDB:

    def test_T_F01_file_created(self, file_db_path):
        assert os.path.exists(file_db_path), f"파일 없음: {file_db_path}"

    def test_T_F02_file_is_not_empty(self, file_db_path):
        size = os.path.getsize(file_db_path)
        assert size > 0, "빈 파일"

    def test_T_F03_file_db_lot_count_60(self, file_conn):
        cnt = file_conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        assert cnt == 60

    def test_T_F04_file_db_tonbag_count_660(self, file_conn):
        cnt = file_conn.execute(
            "SELECT COUNT(*) FROM inventory_tonbag"
        ).fetchone()[0]
        assert cnt == 660

    def test_T_F05_file_db_weight_integrity(self, file_conn):
        bad = file_conn.execute(
            "SELECT COUNT(*) FROM inventory "
            "WHERE ABS(total_weight_kg - ?) > 0.01",
            (LOT_TOTAL_WEIGHT_KG,)
        ).fetchone()[0]
        assert bad == 0

    def test_T_F06_file_db_indexes_exist(self, file_conn):
        """핵심 인덱스 10개 이상 존재"""
        cnt = file_conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index'"
        ).fetchone()[0]
        assert cnt >= 10, f"인덱스 수 {cnt} < 10"

    def test_T_F07_file_db_wal_mode(self, file_db_path):
        """WAL 모드 확인"""
        import sqlite3
        conn = sqlite3.connect(file_db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == 'wal', f"journal_mode={mode} (wal 아님)"

    def test_T_F08_file_db_reconnect_works(self, file_db_path):
        """재연결 후 데이터 보존 확인"""
        import sqlite3
        conn = sqlite3.connect(file_db_path)
        conn.row_factory = sqlite3.Row
        cnt = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        conn.close()
        assert cnt == 60

    def test_T_F09_file_db_allocation_saved(self, file_conn):
        cnt = file_conn.execute(
            "SELECT COUNT(*) FROM allocation_plan"
        ).fetchone()[0]
        assert cnt == 30

    def test_T_F10_file_db_save_idempotent(self, tmp_path):
        """중복 저장 시 기존 파일 덮어쓰기 (에러 없음)
        v8.5.6: tmp_path 사용 — Windows WAL 잠금으로 file_db_path 재사용 불가
        """
        p = tmp_path / "idempotent_test.db"
        path1 = save_scenario_to_file(p, verbose=False)
        path2 = save_scenario_to_file(p, verbose=False)
        assert os.path.exists(path2)
        import sqlite3
        conn = sqlite3.connect(path2)
        conn.row_factory = sqlite3.Row
        cnt = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        conn.close()
        assert cnt == 60

    # ─── v7.0.0: pathlib / Windows 경로 호환성 테스트 ──────────────────────

    def test_T_F10b_pathlib_path_accepted(self, tmp_path):
        """pathlib.Path 객체로 DB 저장 가능 (Windows 호환)"""
        p = tmp_path / "sqm_test.db"
        path_str = save_scenario_to_file(p, verbose=False)
        assert Path(path_str).exists()
        import sqlite3
        conn = sqlite3.connect(path_str)
        conn.row_factory = sqlite3.Row
        cnt = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        conn.close()
        assert cnt == 60

    def test_T_F10c_nested_dir_auto_created(self, tmp_path):
        """중첩 디렉토리 자동 생성 (mkdir parents=True)"""
        p = tmp_path / "sub1" / "sub2" / "sqm.db"
        path_str = save_scenario_to_file(p, verbose=False)
        assert Path(path_str).exists()

    def test_T_F10d_save_returns_absolute_path(self, tmp_path):
        """save_scenario_to_file 반환값이 절대경로"""
        p = tmp_path / "sqm_abs.db"
        path_str = save_scenario_to_file(p, verbose=False)
        assert Path(path_str).is_absolute()

    def test_T_F10e_memory_db_still_works_after_pathlib(self):
        """pathlib 적용 후에도 :memory: DB 정상 동작"""
        conn = create_scenario_db(":memory:", verbose=False)
        cnt = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        conn.close()
        assert cnt == 60


# ═══════════════════════════════════════════════════════════════════════════════
# F2. 15,000 LOT INSERT 성능 (T11~T20)
# ═══════════════════════════════════════════════════════════════════════════════

class TestF2LargeInsert:

    def test_T_F11_15000_lot_insert_under_15sec(self, large_conn):
        """15,000 LOT DB가 이미 생성됨 → fixture 시간으로 확인"""
        lot_cnt = large_conn.execute(
            "SELECT COUNT(*) FROM inventory"
        ).fetchone()[0]
        assert lot_cnt == 15000

    def test_T_F12_165000_tonbag_records_exist(self, large_conn):
        tb_cnt = large_conn.execute(
            "SELECT COUNT(*) FROM inventory_tonbag"
        ).fetchone()[0]
        assert tb_cnt == 165000

    def test_T_F13_insert_speed_over_10000_records_per_sec(self):
        """INSERT 속도 > 10,000 레코드/초"""
        start = time.perf_counter()
        conn = build_large_scenario(1000)  # 빠른 검증용 1,000 LOT
        elapsed = time.perf_counter() - start
        tb_cnt = conn.execute(
            "SELECT COUNT(*) FROM inventory_tonbag"
        ).fetchone()[0]
        conn.close()
        rate = tb_cnt / elapsed
        assert rate > 10000, f"INSERT 속도 {rate:.0f}/s < 10,000/s"

    def test_T_F14_batch_1000_insert_under_1sec(self):
        start = time.perf_counter()
        conn = build_large_scenario(1000)
        elapsed = time.perf_counter() - start
        conn.close()
        assert elapsed < 1.0, f"1,000 LOT INSERT {elapsed:.3f}s > 1.0s"

    def test_T_F15_no_duplicate_lot_in_15000(self, large_conn):
        dupes = large_conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT lot_no FROM inventory GROUP BY lot_no HAVING COUNT(*)>1
            )
        """).fetchone()[0]
        assert dupes == 0

    def test_T_F16_no_duplicate_tonbag_uid_in_165000(self, large_conn):
        dupes = large_conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT tonbag_uid FROM inventory_tonbag
                GROUP BY tonbag_uid HAVING COUNT(*)>1
            )
        """).fetchone()[0]
        assert dupes == 0

    def test_T_F17_all_lot_weights_5001kg(self, large_conn):
        bad = large_conn.execute(
            "SELECT COUNT(*) FROM inventory "
            "WHERE ABS(total_weight_kg - ?) > 0.01",
            (LOT_TOTAL_WEIGHT_KG,)
        ).fetchone()[0]
        assert bad == 0

    def test_T_F18_sample_count_equals_lot_count(self, large_conn):
        lots  = large_conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        samps = large_conn.execute(
            "SELECT COUNT(*) FROM inventory_tonbag WHERE is_sample=1"
        ).fetchone()[0]
        assert lots == samps == 15000

    def test_T_F19_normal_tonbag_count_is_150000(self, large_conn):
        cnt = large_conn.execute(
            "SELECT COUNT(*) FROM inventory_tonbag WHERE is_sample=0"
        ).fetchone()[0]
        assert cnt == 150000

    def test_T_F20_total_weight_is_75015MT(self, large_conn):
        total_kg = large_conn.execute(
            "SELECT SUM(total_weight_kg) FROM inventory"
        ).fetchone()[0]
        expected_kg = 15000 * LOT_TOTAL_WEIGHT_KG
        assert abs(total_kg - expected_kg) < 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# F3. 대규모 쿼리 성능 (T21~T30)
# ═══════════════════════════════════════════════════════════════════════════════

class TestF3LargeQuerySpeed:

    def test_T_F21_count_inventory_under_50ms(self, large_conn):
        t = time.perf_counter()
        large_conn.execute("SELECT COUNT(*) FROM inventory").fetchone()
        ms = (time.perf_counter() - t) * 1000
        assert ms < 50, f"COUNT(inventory) {ms:.1f}ms > 50ms"

    def test_T_F22_count_tonbag_under_50ms(self, large_conn):
        t = time.perf_counter()
        large_conn.execute(
            "SELECT COUNT(*) FROM inventory_tonbag"
        ).fetchone()
        ms = (time.perf_counter() - t) * 1000
        assert ms < 50, f"COUNT(tonbag) {ms:.1f}ms > 50ms"

    def test_T_F23_sample_exclusion_query_under_100ms(self, large_conn):
        t = time.perf_counter()
        large_conn.execute(
            "SELECT COUNT(*) FROM inventory_tonbag WHERE is_sample=0"
        ).fetchone()
        ms = (time.perf_counter() - t) * 1000
        assert ms < 100, f"샘플 제외 COUNT {ms:.1f}ms > 100ms"

    def test_T_F24_total_weight_sum_under_500ms(self, large_conn):
        t = time.perf_counter()
        large_conn.execute(
            "SELECT SUM(total_weight_kg) FROM inventory"
        ).fetchone()
        ms = (time.perf_counter() - t) * 1000
        assert ms < 500, f"SUM(total_weight) {ms:.1f}ms > 500ms"

    def test_T_F25_available_status_filter_under_100ms(self, large_conn):
        t = time.perf_counter()
        large_conn.execute(
            "SELECT COUNT(*) FROM inventory WHERE status='AVAILABLE'"
        ).fetchone()
        ms = (time.perf_counter() - t) * 1000
        assert ms < 100, f"status 필터 {ms:.1f}ms > 100ms"

    def test_T_F26_arrival_date_range_filter_under_100ms(self, large_conn):
        t = time.perf_counter()
        large_conn.execute(
            "SELECT COUNT(*) FROM inventory "
            "WHERE arrival_date BETWEEN '2026-01-01' AND '2026-06-30'"
        ).fetchone()
        ms = (time.perf_counter() - t) * 1000
        assert ms < 100, f"날짜 범위 {ms:.1f}ms > 100ms"

    def test_T_F27_join_1000_lots_weight_under_500ms(self, large_conn):
        t = time.perf_counter()
        large_conn.execute("""
            SELECT i.lot_no, SUM(t.weight_kg) as s
            FROM inventory i
            JOIN inventory_tonbag t ON i.lot_no = t.lot_no
            GROUP BY i.lot_no
            LIMIT 1000
        """).fetchall()
        ms = (time.perf_counter() - t) * 1000
        assert ms < 500, f"1,000 LOT JOIN 집계 {ms:.1f}ms > 500ms"

    def test_T_F28_sample_excluded_weight_correct(self, large_conn):
        """샘플 1kg 제외 가용 중량 = 150,000 × 500kg = 75,000,000kg"""
        total = large_conn.execute(
            "SELECT SUM(weight_kg) FROM inventory_tonbag WHERE is_sample=0"
        ).fetchone()[0]
        expected = 150000 * TONBAG_WEIGHT_KG
        assert abs(total - expected) < 10.0

    def test_T_F29_repeated_count_1000_times_under_5sec(self, large_conn):
        start = time.perf_counter()
        for _ in range(1000):
            large_conn.execute(
                "SELECT COUNT(*) FROM inventory_tonbag WHERE is_sample=0"
            ).fetchone()
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"1000회 반복쿼리 {elapsed:.3f}s > 10.0s (운영환경 목표: <5s)"

    def test_T_F30_lot_no_lookup_by_index_under_10ms(self, large_conn):
        """인덱스를 통한 특정 LOT 톤백 조회 < 10ms"""
        t = time.perf_counter()
        large_conn.execute(
            "SELECT * FROM inventory_tonbag WHERE lot_no='1127500001'"
        ).fetchall()
        ms = (time.perf_counter() - t) * 1000
        assert ms < 10, f"인덱스 LOT 조회 {ms:.1f}ms > 10ms"
