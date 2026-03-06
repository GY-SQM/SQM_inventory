# -*- coding: utf-8 -*-
"""
test_s1_onestop.py — S1 원스톱 출고 단위 테스트
=================================================
Mock DB로 핵심 로직 검증 (tkinter GUI 없이 실행 가능)

테스트 항목:
  T1. 상태 머신 전이 (DRAFT→WAIT_SCAN→FINALIZED/REVIEW/ERROR)
  T2. 배치 간 톤백 중복 차단
  T3. audit_log 이벤트 기록
  T4. 90일 proof_docs 자동 정리
  T5. OUT 스캔 파일 파싱 (csv)
  T6. 파일 SHA-256 해시 중복 차단
  T7. CSV 내보내기

실행: python -m pytest test_s1_onestop.py -v
  또는: python test_s1_onestop.py
"""
import os
import sys
import json
import sqlite3
import tempfile
import shutil
import hashlib
import csv
from datetime import datetime, date, timedelta
from collections import OrderedDict
from unittest.mock import MagicMock, patch

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mock DB 클래스 (SQLite in-memory)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MockDB:
    """SQLite in-memory DB — PATCH-02 의존 쿼리 지원"""

    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE inventory_tonbag (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no      TEXT NOT NULL,
                sub_lt      TEXT,
                weight      REAL DEFAULT 0,
                location    TEXT,
                tonbag_uid  TEXT,
                status      TEXT DEFAULT 'AVAILABLE',
                is_sample   INTEGER DEFAULT 0,
                picked_to   TEXT,
                picked_date TEXT,
                sale_ref    TEXT,
                outbound_date TEXT,
                updated_at  TEXT
            );

            CREATE TABLE audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type  TEXT NOT NULL,
                event_data  TEXT,
                batch_id    TEXT,
                tonbag_id   TEXT,
                user_note   TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                created_by  TEXT DEFAULT 'S1_ONESTOP'
            );
            CREATE INDEX idx_audit_event ON audit_log(event_type, created_at);
        """)
        self.conn.commit()

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def fetchall(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def fetchone(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def insert_tonbags(self, lot_no, count=5, weight=1000.0, location='A-01'):
        """테스트용 톤백 삽입"""
        ids = []
        for i in range(count):
            cur = self.conn.execute(
                "INSERT INTO inventory_tonbag (lot_no, sub_lt, weight, location, tonbag_uid, status) "
                "VALUES (?,?,?,?,?,?)",
                (lot_no, f"{i+1:03d}", weight, location,
                 f"TB-{lot_no}-{i+1:03d}", 'AVAILABLE')
            )
            ids.append(cur.lastrowid)
        self.conn.commit()
        return ids


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 테스트 헬퍼
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def make_batch(lot_no, qty_mt=5.0, customer='SQM', sale_ref='SALE-001', batch_id=None):
    """테스트용 배치 딕셔너리 생성"""
    bid = batch_id or f"S1-TEST-{lot_no}"
    return {
        'id': bid,
        'lot_no': lot_no,
        'request_qty_mt': qty_mt,
        'request_qty_kg': qty_mt * 1000,
        'customer': customer,
        'sale_ref': sale_ref,
        'status': 'DRAFT',
        'created_at': datetime.now().isoformat(),
        'selected_tonbags': [],
        'allocated_qty_kg': 0,
        'actual_qty_kg': None,
        'scan_diff_kg': None,
    }


def write_audit(db, event_type, event_data=None, batch_id=None, tonbag_id=None, user_note=None):
    """audit_log 기록 (다이얼로그 없이 직접)"""
    data_str = json.dumps(event_data, ensure_ascii=False) if event_data else None
    db.execute(
        "INSERT INTO audit_log (event_type, event_data, batch_id, tonbag_id, user_note, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (event_type, data_str, batch_id, tonbag_id, user_note, datetime.now().isoformat())
    )
    db.conn.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# T1: 상태 머신 전이
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def test_t1_state_machine():
    """T1. 상태 머신: DRAFT→WAIT_SCAN→FINALIZED/REVIEW/ERROR"""
    print("T1. 상태 머신 전이 ...")

    batch = make_batch('LOT-001')
    assert batch['status'] == 'DRAFT'

    # DRAFT → WAIT_SCAN
    batch['status'] = 'WAIT_SCAN'
    batch['allocated_qty_kg'] = 5000
    batch['selected_tonbags'] = [1, 2, 3, 4, 5]
    assert batch['status'] == 'WAIT_SCAN'

    # Case A: actual == expected → FINALIZED
    b1 = {**batch}
    b1['actual_qty_kg'] = 5000
    diff = b1['actual_qty_kg'] - b1['request_qty_kg']
    b1['scan_diff_kg'] = diff
    if diff == 0:
        b1['status'] = 'FINALIZED'
    assert b1['status'] == 'FINALIZED'
    assert b1['scan_diff_kg'] == 0

    # Case B: actual < expected → REVIEW_REQUIRED
    b2 = {**batch}
    b2['actual_qty_kg'] = 4500
    diff = b2['actual_qty_kg'] - b2['request_qty_kg']
    b2['scan_diff_kg'] = diff
    if diff < 0:
        b2['status'] = 'REVIEW_REQUIRED'
    assert b2['status'] == 'REVIEW_REQUIRED'
    assert b2['scan_diff_kg'] == -500

    # Case C: actual > expected → ERROR (하드스톱)
    b3 = {**batch}
    b3['actual_qty_kg'] = 5500
    diff = b3['actual_qty_kg'] - b3['request_qty_kg']
    b3['scan_diff_kg'] = diff
    if diff > 0:
        b3['status'] = 'ERROR'
    assert b3['status'] == 'ERROR'
    assert b3['scan_diff_kg'] == 500

    # ERROR → REVIEW_REQUIRED (정정 이벤트)
    b3['status'] = 'REVIEW_REQUIRED'
    b3['corrected'] = True
    assert b3['status'] == 'REVIEW_REQUIRED'

    # REVIEW_REQUIRED → FINALIZED (사유 승인)
    b3['status'] = 'FINALIZED'
    b3['review_reason'] = '고객 요청 변경'
    assert b3['status'] == 'FINALIZED'

    print("  ✅ PASS — 모든 전이 정상")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# T2: 배치 간 톤백 중복 차단
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def test_t2_tonbag_conflict():
    """T2. 배치 간 톤백 중복 선택 차단"""
    print("T2. 톤백 중복 차단 ...")

    selections = {
        'BATCH-A': {1, 2, 3},
        'BATCH-B': set(),
    }

    # 헬퍼: 다른 배치의 선택 가져오기
    def get_others(exclude):
        other = set()
        for bid, sel in selections.items():
            if bid != exclude:
                other |= sel
        return other

    # BATCH-B에서 톤백 1 선택 시도 → 차단
    others = get_others('BATCH-B')
    assert 1 in others, "톤백 1은 BATCH-A에서 선택됨"

    # BATCH-B에서 톤백 4 선택 → 허용
    assert 4 not in others, "톤백 4는 미선택"
    selections['BATCH-B'].add(4)
    assert 4 in selections['BATCH-B']

    # 랜덤 선택 시 타 배치 제외 검증
    all_tonbags = [{'id': i, 'weight': 1000} for i in range(1, 8)]
    available = [tb for tb in all_tonbags if tb['id'] not in get_others('BATCH-B')]
    assert len(available) == 4  # 1,2,3 제외 → 4,5,6,7 가용

    print("  ✅ PASS — 중복 차단 + 랜덤 제외 정상")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# T3: audit_log 이벤트 기록
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def test_t3_audit_log():
    """T3. audit_log 테이블 이벤트 기록 및 조회"""
    print("T3. audit_log 이벤트 ...")

    db = MockDB()

    # 이벤트 기록
    write_audit(db, 'UNMATCHED_SCAN',
                event_data={'tonbag_id': 'TB-999', 'weight': 1200},
                tonbag_id='TB-999',
                user_note='미매칭 테스트')

    write_audit(db, 'OUTBOUND_SOLD',
                event_data={'lot_no': 'LOT-001', 'tonbag_count': 5},
                batch_id='S1-TEST-001',
                user_note='출고 완료 테스트')

    write_audit(db, 'PROOF_ATTACH',
                event_data={'file_name': 'test.pdf', 'file_hash': 'abc123'},
                user_note='근거문서 테스트')

    # 전체 조회
    rows = db.fetchall("SELECT * FROM audit_log ORDER BY id")
    assert len(rows) == 3

    # 유형별 필터
    unmatched = db.fetchall("SELECT * FROM audit_log WHERE event_type='UNMATCHED_SCAN'")
    assert len(unmatched) == 1
    assert unmatched[0]['tonbag_id'] == 'TB-999'

    # JSON 데이터 파싱
    data = json.loads(unmatched[0]['event_data'])
    assert data['weight'] == 1200

    sold = db.fetchall("SELECT * FROM audit_log WHERE event_type='OUTBOUND_SOLD'")
    assert sold[0]['batch_id'] == 'S1-TEST-001'

    print("  ✅ PASS — 3건 기록/조회/필터 정상")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# T4: 90일 proof_docs 자동 정리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def test_t4_proof_cleanup():
    """T4. 90일 초과 proof_docs 폴더 자동 정리"""
    print("T4. proof_docs 90일 정리 ...")

    tmpdir = tempfile.mkdtemp()
    try:
        base = os.path.join(tmpdir, 'data', 'proof_docs')
        os.makedirs(base)

        # 100일 전 폴더 (삭제 대상)
        old_date = (date.today() - timedelta(days=100)).isoformat()
        old_dir = os.path.join(base, old_date)
        os.makedirs(old_dir)
        with open(os.path.join(old_dir, 'test.pdf'), 'w') as f:
            f.write('dummy')

        # 30일 전 폴더 (유지)
        recent_date = (date.today() - timedelta(days=30)).isoformat()
        recent_dir = os.path.join(base, recent_date)
        os.makedirs(recent_dir)
        with open(os.path.join(recent_dir, 'keep.pdf'), 'w') as f:
            f.write('keep')

        # 오늘 폴더 (유지)
        today_dir = os.path.join(base, date.today().isoformat())
        os.makedirs(today_dir)

        # 잘못된 형식 폴더 (무시)
        os.makedirs(os.path.join(base, 'not-a-date'))

        assert os.path.isdir(old_dir)
        assert os.path.isdir(recent_dir)

        # 정리 실행 (90일)
        cutoff = date.today().toordinal() - 90
        removed = 0
        for entry in os.listdir(base):
            entry_path = os.path.join(base, entry)
            if not os.path.isdir(entry_path):
                continue
            try:
                folder_date = date.fromisoformat(entry)
            except (ValueError, TypeError):
                continue
            if folder_date.toordinal() < cutoff:
                shutil.rmtree(entry_path, ignore_errors=True)
                removed += 1

        assert removed == 1, f"1개 삭제 예상, 실제 {removed}"
        assert not os.path.isdir(old_dir), "100일 전 폴더 삭제 확인"
        assert os.path.isdir(recent_dir), "30일 전 폴더 유지 확인"
        assert os.path.isdir(today_dir), "오늘 폴더 유지 확인"
        assert os.path.isdir(os.path.join(base, 'not-a-date')), "비날짜 폴더 무시 확인"

        print("  ✅ PASS — 100일 전 삭제, 30일/오늘/비날짜 유지")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# T5: OUT 스캔 파일 파싱 (CSV)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def test_t5_out_scan_csv():
    """T5. OUT 스캔 CSV 파싱 + 미매칭 감지"""
    print("T5. OUT 스캔 CSV 파싱 ...")

    tmpdir = tempfile.mkdtemp()
    try:
        # CSV 생성
        csv_path = os.path.join(tmpdir, 'out_scan.csv')
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['tonbag_id', 'weight', 'location'])
            writer.writerow(['TB-LOT001-001', '1000', 'A-01'])  # 매칭 예정
            writer.writerow(['TB-LOT001-002', '1000', 'A-01'])  # 매칭 예정
            writer.writerow(['TB-UNKNOWN-999', '500', 'B-02'])   # 미매칭

        # 파싱
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            sample = f.read(2048)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=',\t|;')
            reader = csv.reader(f, dialect)
            rows = list(reader)

        header = [c.strip().lower() for c in rows[0]]
        tb_col = next((i for i, h in enumerate(header) if 'tonbag' in h or 'id' in h), 0)
        wt_col = next((i for i, h in enumerate(header) if 'weight' in h or 'kg' in h), 1)

        records = []
        for row in rows[1:]:
            if not row:
                continue
            tb_id = row[tb_col].strip()
            weight = float(row[wt_col].replace(',', '')) if row[wt_col] else 0
            records.append({'tonbag_id': tb_id, 'weight': weight})

        assert len(records) == 3

        # 매칭 시뮬레이션
        selected = {'TB-LOT001-001': 'BATCH-A', 'TB-LOT001-002': 'BATCH-A'}
        matched = [r for r in records if r['tonbag_id'] in selected]
        unmatched = [r for r in records if r['tonbag_id'] not in selected]

        assert len(matched) == 2
        assert len(unmatched) == 1
        assert unmatched[0]['tonbag_id'] == 'TB-UNKNOWN-999'

        print("  ✅ PASS — 3건 파싱, 2건 매칭, 1건 미매칭")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# T6: SHA-256 해시 중복 차단
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def test_t6_hash_dedup():
    """T6. 파일 SHA-256 해시 기반 중복 차단"""
    print("T6. SHA-256 해시 중복 ...")

    tmpdir = tempfile.mkdtemp()
    try:
        # 동일 내용 파일 2개 (다른 이름)
        f1 = os.path.join(tmpdir, 'doc_a.txt')
        f2 = os.path.join(tmpdir, 'doc_b.txt')
        f3 = os.path.join(tmpdir, 'doc_c.txt')

        with open(f1, 'w') as f:
            f.write('hello world 12345')
        shutil.copy2(f1, f2)  # 동일 내용
        with open(f3, 'w') as f:
            f.write('different content')

        def hash_file(filepath):
            h = hashlib.sha256()
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()

        h1 = hash_file(f1)
        h2 = hash_file(f2)
        h3 = hash_file(f3)

        assert h1 == h2, "동일 내용 → 동일 해시"
        assert h1 != h3, "다른 내용 → 다른 해시"

        # 중복 차단 시뮬레이션
        proof_hashes = set()
        proof_hashes.add(h1)
        assert h2 in proof_hashes, "중복 감지 성공"
        assert h3 not in proof_hashes, "신규 파일 허용"

        print("  ✅ PASS — 동일내용 중복감지, 신규 허용")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# T7: CSV 내보내기
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def test_t7_csv_export():
    """T7. 감사 로그 CSV 내보내기"""
    print("T7. CSV 내보내기 ...")

    db = MockDB()
    tmpdir = tempfile.mkdtemp()
    try:
        # audit 기록 3건
        for i in range(3):
            write_audit(db, f'TEST_EVENT_{i}',
                        event_data={'idx': i},
                        user_note=f'테스트 {i}')

        # 조회
        rows = db.fetchall(
            "SELECT id, event_type, batch_id, tonbag_id, user_note, created_at "
            "FROM audit_log ORDER BY id"
        )
        assert len(rows) == 3

        # CSV 쓰기
        csv_path = os.path.join(tmpdir, 'export_test.csv')
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', '이벤트유형', '배치ID', '톤백ID', '메모', '시간'])
            for r in rows:
                writer.writerow([
                    r['id'], r['event_type'],
                    r.get('batch_id') or '—',
                    r.get('tonbag_id') or '—',
                    r.get('user_note', ''),
                    r['created_at'][:19],
                ])

        # 읽기 검증
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            csv_rows = list(reader)

        assert len(csv_rows) == 4  # 헤더 + 3건
        assert csv_rows[0][0] == 'ID'
        assert csv_rows[1][1] == 'TEST_EVENT_0'
        assert csv_rows[3][1] == 'TEST_EVENT_2'

        print("  ✅ PASS — 3건 기록 → CSV 4행 (헤더 포함)")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# T8: DB 톤백 PICKED → SOLD 전이
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def test_t8_db_picked_to_sold():
    """T8. DB 톤백 상태: AVAILABLE → PICKED → SOLD"""
    print("T8. DB 톤백 PICKED→SOLD ...")

    db = MockDB()
    tb_ids = db.insert_tonbags('LOT-001', count=3, weight=1000)

    # AVAILABLE 확인
    avail = db.fetchall("SELECT * FROM inventory_tonbag WHERE status='AVAILABLE'")
    assert len(avail) == 3

    # AVAILABLE → PICKED
    now_str = datetime.now().isoformat()
    for tb_id in tb_ids[:2]:
        db.execute(
            "UPDATE inventory_tonbag SET status='PICKED', picked_to=?, "
            "picked_date=?, updated_at=? WHERE id=?",
            ('S1-TEST-001', date.today().isoformat(), now_str, tb_id)
        )
    db.conn.commit()

    picked = db.fetchall("SELECT * FROM inventory_tonbag WHERE status='PICKED'")
    assert len(picked) == 2

    still_avail = db.fetchall("SELECT * FROM inventory_tonbag WHERE status='AVAILABLE'")
    assert len(still_avail) == 1

    # PICKED → SOLD
    for tb_id in tb_ids[:2]:
        db.execute(
            "UPDATE inventory_tonbag SET status='SOLD', "
            "outbound_date=?, updated_at=? WHERE id=? AND status='PICKED'",
            (date.today().isoformat(), now_str, tb_id)
        )
    db.conn.commit()

    sold = db.fetchall("SELECT * FROM inventory_tonbag WHERE status='SOLD'")
    assert len(sold) == 2

    print("  ✅ PASS — AVAILABLE(3) → PICKED(2) → SOLD(2), 잔여 AVAILABLE(1)")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인 실행
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run_all():
    print("=" * 60)
    print("  S1 원스톱 출고 — 단위 테스트")
    print(f"  실행일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    tests = [
        test_t1_state_machine,
        test_t2_tonbag_conflict,
        test_t3_audit_log,
        test_t4_proof_cleanup,
        test_t5_out_scan_csv,
        test_t6_hash_dedup,
        test_t7_csv_export,
        test_t8_db_picked_to_sold,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAIL — {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR — {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"  결과: {passed} PASS / {failed} FAIL (총 {len(tests)}건)")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all()
    sys.exit(0 if success else 1)
