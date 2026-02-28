# -*- coding: utf-8 -*-
"""
SQM v6.2.4 — 바코드 스캔 엔진 통합 테스트
============================================
테스트 시나리오:
  T01. 정상 PASS (expected == scanned, 1:1 일치)
  T02. FAIL: 누락 UID (expected에만 존재)
  T03. FAIL: 초과 UID (scanned에만 존재)
  T04. PASS: 중복 스캔 허용 (duplicate → 경고만)  [m-1]
  T05. PASS: sub_lt zero-padding 정규화           [C-3]
  T06. sale_ref 필터 (동시 출고건 구분)            [C-2]
  T07. 인코딩 fallback (utf-8, cp949, euc-kr)     [C-4]
  T08. UID 클렌징 (BOM, ZWSP 제거)                [M-5]
  T09. 벌크 PICKED→SOLD 전환                      [C-1, M-2]
  T10. sold_table / picking_table / stock_movement 이력 기록
  T11. 빈 스캔 파일 거부
  T12. uid_verify_history 기록 + 인덱스 확인       [m-2]
  T13. 레거시 호환 (process_barcode_scan_to_sold_from_file)

실행: pytest tests/test_barcode_scan_v624.py -v
작성자: Ruby
"""
import os
import sys
import tempfile
import sqlite3
from pathlib import Path
from typing import Dict, List, Set

import pytest

# 프로젝트 루트
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ═══════════════════════════════════════════════════════
# Mock DB — SQMDatabase 최소 인터페이스 구현
# ═══════════════════════════════════════════════════════
class MockDB:
    """BarcodeScanEngine이 사용하는 DB 인터페이스 최소 구현 (in-memory SQLite)."""

    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self._setup_schema()

    def _setup_schema(self):
        cur = self.conn.cursor()
        # inventory
        cur.execute("""
            CREATE TABLE inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT UNIQUE NOT NULL,
                product TEXT DEFAULT 'LITHIUM CARBONATE',
                current_weight REAL DEFAULT 0,
                picked_weight REAL DEFAULT 0,
                status TEXT DEFAULT 'AVAILABLE',
                updated_at TEXT
            )
        """)
        # inventory_tonbag
        cur.execute("""
            CREATE TABLE inventory_tonbag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                sub_lt INTEGER NOT NULL DEFAULT 0,
                weight REAL DEFAULT 500.0,
                is_sample INTEGER DEFAULT 0,
                status TEXT DEFAULT 'AVAILABLE',
                location TEXT,
                picked_to TEXT,
                picked_date TEXT,
                outbound_date TEXT,
                sale_ref TEXT,
                tonbag_uid TEXT,
                updated_at TEXT
            )
        """)
        # stock_movement
        cur.execute("""
            CREATE TABLE stock_movement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                qty_kg REAL DEFAULT 0,
                remarks TEXT,
                created_at TEXT
            )
        """)
        # picking_table
        cur.execute("""
            CREATE TABLE picking_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT,
                tonbag_id INTEGER,
                sub_lt INTEGER,
                tonbag_uid TEXT,
                customer TEXT,
                qty_kg REAL,
                status TEXT DEFAULT 'ACTIVE',
                picking_date TEXT,
                sold_date TEXT,
                created_by TEXT,
                remark TEXT
            )
        """)
        # sold_table
        cur.execute("""
            CREATE TABLE sold_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT,
                tonbag_id INTEGER,
                sub_lt INTEGER,
                tonbag_uid TEXT,
                sold_qty_kg REAL,
                sold_date TEXT,
                status TEXT DEFAULT 'SOLD',
                created_by TEXT
            )
        """)
        self.conn.commit()

    def execute(self, sql, params=()):
        self.conn.execute(sql, params)
        self.conn.commit()

    def fetchone(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def fetchall(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    class _TxCtx:
        def __init__(self, conn):
            self.conn = conn
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
            return False

    def transaction(self, mode=""):
        return self._TxCtx(self.conn)


# ═══════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════
@pytest.fixture
def db():
    """Clean in-memory DB per test."""
    return MockDB()


@pytest.fixture
def scanner(db):
    """BarcodeScanEngine with mock DB."""
    from core.barcode_scan_engine import BarcodeScanEngine
    return BarcodeScanEngine(db)


@pytest.fixture
def seed_picked(db):
    """5개 PICKED 톤백 시드 (sale_ref 2건 혼합)."""
    lot = '1125072729'
    db.execute(
        "INSERT INTO inventory (lot_no, product, current_weight, status) "
        "VALUES (?, 'LITHIUM CARBONATE', 2500.0, 'AVAILABLE')", (lot,))

    tonbags = [
        (lot, 1, 500.0, 'PICKED', 'REF-A', f'UID-{lot}-01'),
        (lot, 2, 500.0, 'PICKED', 'REF-A', f'UID-{lot}-02'),
        (lot, 3, 500.0, 'PICKED', 'REF-A', f'UID-{lot}-03'),
        (lot, 4, 500.0, 'PICKED', 'REF-B', f'UID-{lot}-04'),
        (lot, 5, 500.0, 'PICKED', 'REF-B', f'UID-{lot}-05'),
    ]
    for (ln, sl, w, st, sr, uid) in tonbags:
        db.execute(
            "INSERT INTO inventory_tonbag "
            "(lot_no, sub_lt, weight, status, sale_ref, tonbag_uid, "
            " picked_date, picked_to) "
            "VALUES (?,?,?,?,?,?, '2026-02-28 10:00:00', 'CUSTOMER-A')",
            (ln, sl, w, st, sr, uid))
        # picking_table에도 ACTIVE 행 삽입
        db.execute(
            "INSERT INTO picking_table "
            "(lot_no, tonbag_id, sub_lt, tonbag_uid, status) "
            "VALUES (?, (SELECT id FROM inventory_tonbag WHERE tonbag_uid=?), ?, ?, 'ACTIVE')",
            (ln, uid, sl, uid))
    return lot, tonbags


@pytest.fixture
def tmp_scan_file():
    """임시 스캔 파일 생성 헬퍼 — yield (path, cleanup)."""
    paths = []

    def _make(lines: List[str], ext='txt', encoding='utf-8'):
        fd, path = tempfile.mkstemp(suffix=f'.{ext}')
        os.close(fd)
        with open(path, 'w', encoding=encoding) as f:
            f.write('\n'.join(lines))
        paths.append(path)
        return path

    yield _make

    for p in paths:
        try:
            os.unlink(p)
        except OSError:
            pass


# ═══════════════════════════════════════════════════════
# T01. 정상 PASS — 1:1 일치
# ═══════════════════════════════════════════════════════
class TestT01_NormalPass:
    def test_verify_pass(self, scanner, seed_picked):
        lot, tonbags = seed_picked
        expected = {t[5] for t in tonbags}  # UID set
        scanned = [t[5] for t in tonbags]   # UID list (동일 순서)

        result = scanner.verify_outbound_scan(expected, scanned)

        assert result['result'] == 'PASS'
        assert result['expected_count'] == 5
        assert not result['missing']
        assert not result['extra']
        assert not result['duplicates']
        assert '통과' in result['message']


# ═══════════════════════════════════════════════════════
# T02. FAIL — 누락 UID
# ═══════════════════════════════════════════════════════
class TestT02_FailMissing:
    def test_missing_uid(self, scanner, seed_picked):
        lot, tonbags = seed_picked
        expected = {t[5] for t in tonbags}
        scanned = [t[5] for t in tonbags[:3]]  # 3개만 스캔 (2개 누락)

        result = scanner.verify_outbound_scan(expected, scanned)

        assert result['result'] == 'FAIL'
        assert len(result['missing']) == 2
        assert '누락' in result['message']


# ═══════════════════════════════════════════════════════
# T03. FAIL — 초과 UID
# ═══════════════════════════════════════════════════════
class TestT03_FailExtra:
    def test_extra_uid(self, scanner, seed_picked):
        lot, tonbags = seed_picked
        expected = {t[5] for t in tonbags}
        scanned = [t[5] for t in tonbags] + ['UNKNOWN-UID-99']

        result = scanner.verify_outbound_scan(expected, scanned)

        assert result['result'] == 'FAIL'
        assert 'UNKNOWN-UID-99' in result['extra']
        assert '초과' in result['message']


# ═══════════════════════════════════════════════════════
# T04. PASS — 중복 스캔 허용 [m-1]
# ═══════════════════════════════════════════════════════
class TestT04_DuplicatePass:
    def test_duplicate_scan_still_pass(self, scanner, seed_picked):
        """중복 스캔이 있어도 unique 기준 일치하면 PASS."""
        lot, tonbags = seed_picked
        expected = {t[5] for t in tonbags}
        # UID-01을 3번 스캔
        scanned = [t[5] for t in tonbags] + [tonbags[0][5], tonbags[0][5]]

        result = scanner.verify_outbound_scan(expected, scanned)

        assert result['result'] == 'PASS', f"Expected PASS but got {result['result']}: {result['message']}"
        assert len(result['duplicates']) >= 1
        assert '중복' in result['message']
        assert '통과' in result['message']


# ═══════════════════════════════════════════════════════
# T05. sub_lt zero-padding 정규화 [C-3]
# ═══════════════════════════════════════════════════════
class TestT05_SubLtNormalize:
    def test_zero_padding(self, scanner):
        """expected에 '5' / scanned에 '05' → 정규화 매칭으로 PASS."""
        from core.barcode_scan_engine import _normalize_sublt
        assert _normalize_sublt('05') == '5'
        assert _normalize_sublt('5') == '5'
        assert _normalize_sublt('100') == '100'
        assert _normalize_sublt('abc') == 'abc'

    def test_verify_with_padding(self, scanner):
        expected = {'UID-001', 'UID-002', '5'}
        scanned = ['UID-001', 'UID-002', '05']

        result = scanner.verify_outbound_scan(expected, scanned)
        # '5' vs '05' → 정규화 매칭 → missing/extra 없어야 함
        assert result['result'] == 'PASS', f"Normalize failed: {result}"


# ═══════════════════════════════════════════════════════
# T06. sale_ref 필터 [C-2]
# ═══════════════════════════════════════════════════════
class TestT06_SaleRefFilter:
    def test_get_picked_sale_refs(self, scanner, seed_picked):
        refs = scanner.get_picked_sale_refs()
        assert 'REF-A' in refs
        assert 'REF-B' in refs

    def test_filter_by_ref_a(self, scanner, seed_picked):
        uids = scanner.get_picked_uids(sale_ref='REF-A')
        assert len(uids) == 3  # REF-A에 3개

    def test_filter_by_ref_b(self, scanner, seed_picked):
        uids = scanner.get_picked_uids(sale_ref='REF-B')
        assert len(uids) == 2  # REF-B에 2개

    def test_all_picked(self, scanner, seed_picked):
        uids = scanner.get_picked_uids()
        assert len(uids) == 5


# ═══════════════════════════════════════════════════════
# T07. 인코딩 fallback [C-4]
# ═══════════════════════════════════════════════════════
class TestT07_EncodingFallback:
    def test_utf8(self, scanner, tmp_scan_file):
        path = tmp_scan_file(['UID-001', 'UID-002'], encoding='utf-8')
        result = scanner.read_scan_file(path)
        assert result == ['UID-001', 'UID-002']

    def test_utf8_bom(self, scanner, tmp_scan_file):
        path = tmp_scan_file(['UID-001', 'UID-002'], encoding='utf-8-sig')
        result = scanner.read_scan_file(path)
        assert 'UID-001' in result
        # BOM이 클렌징되어 UID-001이 정상적으로 읽혀야 함
        assert all('\ufeff' not in uid for uid in result)

    def test_cp949(self, scanner):
        """cp949 인코딩 TXT 파일."""
        fd, path = tempfile.mkstemp(suffix='.txt')
        os.close(fd)
        try:
            with open(path, 'w', encoding='cp949') as f:
                f.write('UID-가나다\nUID-라마바\n')
            result = scanner.read_scan_file(path)
            assert len(result) == 2
            assert 'UID-가나다' in result
        finally:
            os.unlink(path)

    def test_csv_encoding(self, scanner):
        """CSV cp949 인코딩 파일."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas required")
        fd, path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        try:
            with open(path, 'w', encoding='cp949') as f:
                f.write('UID-테스트1\nUID-테스트2\n')
            result = scanner.read_scan_file(path)
            assert len(result) == 2
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════
# T08. UID 클렌징 [M-5]
# ═══════════════════════════════════════════════════════
class TestT08_UidCleaning:
    def test_clean_uid(self):
        from core.barcode_scan_engine import _clean_uid
        assert _clean_uid('\ufeffUID-001') == 'UID-001'        # BOM
        assert _clean_uid('UID-002\u200b') == 'UID-002'        # ZWSP
        assert _clean_uid('  UID-003  ') == 'UID-003'          # 공백
        assert _clean_uid('UID-004\r\n') == 'UID-004'          # CR/LF
        assert _clean_uid('\u00a0UID-005\u00a0') == 'UID-005'  # NBSP
        assert _clean_uid('') == ''
        assert _clean_uid(None) == ''  # None 안전

    def test_verify_with_bom_scanned(self, scanner, seed_picked):
        """스캔 파일에 BOM이 포함되어도 매칭 성공."""
        lot, tonbags = seed_picked
        expected = {t[5] for t in tonbags}
        # BOM + ZWSP 삽입
        scanned = [f'\ufeff{t[5]}\u200b' for t in tonbags]

        result = scanner.verify_outbound_scan(expected, scanned)
        assert result['result'] == 'PASS', f"BOM cleansing failed: {result}"


# ═══════════════════════════════════════════════════════
# T09. 벌크 PICKED → SOLD 전환 [C-1, M-2]
# ═══════════════════════════════════════════════════════
class TestT09_BulkSold:
    def test_process_sold_full(self, scanner, db, seed_picked):
        lot, tonbags = seed_picked
        scanned_codes = [t[5] for t in tonbags]

        result = scanner.process_barcode_scan_to_sold(scanned_codes)

        assert result['success'] is True
        assert result['sold'] == 5
        assert result['not_found'] == []
        assert result['remaining_picked'] == 0

        # DB 확인: 모든 톤백이 SOLD
        rows = db.fetchall(
            "SELECT status FROM inventory_tonbag WHERE lot_no = ?", (lot,))
        assert all(r['status'] == 'SOLD' for r in rows)

    def test_process_partial_with_not_found(self, scanner, db, seed_picked):
        lot, tonbags = seed_picked
        scanned_codes = [tonbags[0][5], 'UNKNOWN-UID']

        result = scanner.process_barcode_scan_to_sold(scanned_codes)

        assert result['sold'] == 1
        assert 'UNKNOWN-UID' in result['not_found']
        assert result['remaining_picked'] == 4

    def test_process_with_sale_ref_filter(self, scanner, db, seed_picked):
        """sale_ref='REF-A'로 필터 → REF-A 3개만 SOLD."""
        lot, tonbags = seed_picked
        ref_a_codes = [t[5] for t in tonbags if t[4] == 'REF-A']

        result = scanner.process_barcode_scan_to_sold(
            ref_a_codes, sale_ref='REF-A')

        assert result['sold'] == 3
        # REF-B 톤백은 여전히 PICKED
        ref_b = db.fetchall(
            "SELECT status FROM inventory_tonbag WHERE sale_ref = 'REF-B'")
        assert all(r['status'] == 'PICKED' for r in ref_b)

    def test_duplicate_code_in_scan(self, scanner, db, seed_picked):
        """같은 UID가 2번 스캔되어도 1회만 SOLD 처리."""
        lot, tonbags = seed_picked
        uid = tonbags[0][5]
        scanned_codes = [uid, uid, uid]

        result = scanner.process_barcode_scan_to_sold(scanned_codes)

        assert result['sold'] == 1  # 중복 무시


# ═══════════════════════════════════════════════════════
# T10. 이력 테이블 기록
# ═══════════════════════════════════════════════════════
class TestT10_HistoryRecords:
    def test_sold_table_created(self, scanner, db, seed_picked):
        lot, tonbags = seed_picked
        scanner.process_barcode_scan_to_sold([tonbags[0][5]])

        sold = db.fetchall("SELECT * FROM sold_table")
        assert len(sold) >= 1
        assert sold[0]['created_by'] == 'barcode_scan'

    def test_picking_table_updated(self, scanner, db, seed_picked):
        lot, tonbags = seed_picked
        scanner.process_barcode_scan_to_sold([tonbags[0][5]])

        pick = db.fetchone(
            "SELECT status FROM picking_table WHERE tonbag_uid = ?",
            (tonbags[0][5],))
        assert pick['status'] == 'SOLD'

    def test_stock_movement_logged(self, scanner, db, seed_picked):
        lot, tonbags = seed_picked
        scanner.process_barcode_scan_to_sold([tonbags[0][5]])

        moves = db.fetchall(
            "SELECT * FROM stock_movement WHERE movement_type = 'SOLD'")
        assert len(moves) >= 1
        assert 'barcode_scan' in moves[0]['remarks']


# ═══════════════════════════════════════════════════════
# T11. 빈 스캔 파일 거부
# ═══════════════════════════════════════════════════════
class TestT11_EmptyFile:
    def test_empty_txt(self, scanner, tmp_scan_file):
        path = tmp_scan_file(['', '  ', '\n'])
        result = scanner.read_scan_file(path)
        assert result == []  # 빈값 + 공백만 → 빈 리스트

    def test_empty_process(self, scanner, seed_picked):
        result = scanner.process_barcode_scan_to_sold([])
        assert result['sold'] == 0


# ═══════════════════════════════════════════════════════
# T12. uid_verify_history 기록 + 인덱스 [m-2]
# ═══════════════════════════════════════════════════════
class TestT12_VerifyHistory:
    def test_history_recorded(self, scanner, seed_picked):
        lot, tonbags = seed_picked
        expected = {t[5] for t in tonbags}
        scanned = [t[5] for t in tonbags]

        scanner.verify_outbound_scan(
            expected, scanned,
            outbound_ref='TEST-REF', sale_ref='REF-A')

        history = scanner.get_verify_history(limit=1)
        assert len(history) == 1
        assert history[0]['verify_result'] == 'PASS'
        assert history[0]['sale_ref'] == 'REF-A'

    def test_index_exists(self, db, scanner):
        """uid_verify_history 인덱스 존재 확인."""
        rows = db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name='uid_verify_history'")
        idx_names = {r['name'] for r in rows}
        assert 'idx_verify_history_ref' in idx_names
        assert 'idx_verify_history_at' in idx_names
        assert 'idx_verify_history_sale' in idx_names


# ═══════════════════════════════════════════════════════
# T13. 레거시 호환
# ═══════════════════════════════════════════════════════
class TestT13_Legacy:
    def test_from_file_method(self, scanner, db, seed_picked, tmp_scan_file):
        lot, tonbags = seed_picked
        path = tmp_scan_file([t[5] for t in tonbags])

        result = scanner.process_barcode_scan_to_sold_from_file(path)

        assert result['success'] is True
        assert result['sold'] == 5


# ═══════════════════════════════════════════════════════
# T14. Excel 스캔 파일 읽기
# ═══════════════════════════════════════════════════════
class TestT14_ExcelRead:
    def test_xlsx_read(self, scanner):
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas required")

        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        try:
            df = pd.DataFrame({'uid': ['UID-001', 'UID-002', 'UID-003']})
            df.to_excel(path, index=False, header=False)
            result = scanner.read_scan_file(path)
            assert len(result) == 3
            assert 'UID-001' in result
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════
# T15. get_picked_full_info 미리보기 데이터
# ═══════════════════════════════════════════════════════
class TestT15_FullInfo:
    def test_full_info_all(self, scanner, seed_picked):
        info = scanner.get_picked_full_info()
        assert len(info) == 5

    def test_full_info_filtered(self, scanner, seed_picked):
        info = scanner.get_picked_full_info(sale_ref='REF-B')
        assert len(info) == 2
        assert all(r['sale_ref'] == 'REF-B' for r in info)
