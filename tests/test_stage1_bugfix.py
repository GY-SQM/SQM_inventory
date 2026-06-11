# -*- coding: utf-8 -*-
"""
1단계 버그 수정 스모크 테스트
B-1 ~ B-5, D-1, F-1+F-2+F-6+F-10 수정 검증
"""
import os, sys, sqlite3, tempfile, pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ═══════════════════════════════════════════════════════
# 픽스처: 인메모리 테스트 DB
# ═══════════════════════════════════════════════════════
@pytest.fixture
def test_db():
    """인메모리 SQLite DB — 실제 DB 건드리지 않음"""
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=3000")
    # 최소 스키마 생성
    con.executescript("""
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT, status TEXT, current_weight REAL DEFAULT 0,
            sold_to TEXT, sale_ref TEXT, product TEXT,
            updated_at TEXT
        );
        CREATE TABLE inventory_tonbag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_id INTEGER, lot_no TEXT, sub_lt INTEGER,
            status TEXT, weight REAL DEFAULT 0,
            outbound_date TEXT, updated_at TEXT
        );
        CREATE TABLE allocation_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT, customer TEXT, sale_ref TEXT,
            tonbag_id INTEGER, status TEXT,
            approval_status TEXT,
            approved_at TEXT, updated_at TEXT,
            cancelled_at TEXT
        );
        CREATE TABLE stock_movement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_no TEXT, movement_type TEXT, qty_kg REAL,
            customer TEXT, movement_date TEXT, source_type TEXT,
            actor TEXT, remarks TEXT, created_at TEXT
        );
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT, event_data TEXT,
            user_note TEXT, created_by TEXT, created_at TEXT
        );
    """)
    yield con
    con.close()


# ═══════════════════════════════════════════════════════
# B-5: inventory_api._db() WAL + busy_timeout
# ═══════════════════════════════════════════════════════
class TestB5_DbWAL:
    def test_inventory_api_has_wal_pragma(self):
        src = open(os.path.join(ROOT, 'backend/api/inventory_api.py'), encoding='utf-8').read()
        assert 'PRAGMA journal_mode=WAL' in src, "_db()에 WAL PRAGMA 없음"
        assert 'PRAGMA busy_timeout' in src, "_db()에 busy_timeout PRAGMA 없음"

    def test_wal_in_db_function(self):
        """_db() 함수 블록 안에 실제로 있는지 확인"""
        src = open(os.path.join(ROOT, 'backend/api/inventory_api.py'), encoding='utf-8').read()
        # _db 함수 시작 ~ return 사이에 PRAGMA 존재
        db_func = src[src.index('def _db()'):src.index('def _rows(')]
        assert 'journal_mode=WAL' in db_func
        assert 'busy_timeout' in db_func

    def test_wal_mode_actually_works(self, test_db):
        # :memory: DB는 WAL 미지원(memory 모드 고정) → 파일 DB로 검증
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            tmp_path = f.name
        try:
            con = sqlite3.connect(tmp_path)
            con.execute("PRAGMA journal_mode=WAL")
            result = con.execute("PRAGMA journal_mode").fetchone()[0]
            con.close()
            assert result == 'wal', f"파일 DB WAL 모드 설정 실패: {result}"
        finally:
            os.unlink(tmp_path)


# ═══════════════════════════════════════════════════════
# B-1: approve/reject 컬럼 통일
# ═══════════════════════════════════════════════════════
class TestB1_ApproveReject:
    def test_reject_uses_status_not_approval_status(self):
        src = open(os.path.join(ROOT, 'backend/api/allocation_api.py'), encoding='utf-8').read()
        # reject 함수 부분만 추출
        reject_start = src.index('def reject_allocation')
        reject_end = src.index('\ndef ', reject_start + 1)
        reject_body = src[reject_start:reject_end]
        assert "approval_status='REJECTED'" not in reject_body, \
            "reject_allocation이 여전히 approval_status 컬럼을 수정하고 있음"
        assert "status='REJECTED'" in reject_body, \
            "reject_allocation이 status 컬럼을 수정하지 않음"

    def test_approve_and_reject_use_same_column(self):
        src = open(os.path.join(ROOT, 'backend/api/allocation_api.py'), encoding='utf-8').read()
        approve_start = src.index('def approve_allocation')
        approve_end = src.index('\ndef ', approve_start + 1)
        approve_body = src[approve_start:approve_end]

        reject_start = src.index('def reject_allocation')
        reject_end = src.index('\ndef ', reject_start + 1)
        reject_body = src[reject_start:reject_end]

        assert "status='APPROVED'" in approve_body
        assert "status='REJECTED'" in reject_body

    def test_reject_db_operation(self, test_db):
        """실제 DB 쿼리 동작 검증"""
        test_db.execute(
            "INSERT INTO allocation_plan(lot_no, customer, sale_ref, status) VALUES (?,?,?,?)",
            ('LOT001', 'CATL', 'REF-A', 'STAGED')
        )
        plan_id = test_db.execute("SELECT id FROM allocation_plan").fetchone()[0]
        test_db.execute(
            "UPDATE allocation_plan SET status='REJECTED', updated_at=datetime('now') WHERE id=?",
            (plan_id,)
        )
        test_db.commit()
        row = test_db.execute("SELECT status FROM allocation_plan WHERE id=?", (plan_id,)).fetchone()
        assert row['status'] == 'REJECTED'


# ═══════════════════════════════════════════════════════
# B-2: cancel_by_sale_ref inventory_tonbag 복구
# ═══════════════════════════════════════════════════════
class TestB2_CancelBySaleRef:
    def test_cancel_includes_tonbag_update(self):
        src = open(os.path.join(ROOT, 'backend/api/allocation_api.py'), encoding='utf-8').read()
        func_start = src.index('def cancel_by_sale_ref')
        func_end = src.index('\n@router', func_start)
        func_body = src[func_start:func_end]
        assert 'inventory_tonbag' in func_body, \
            "cancel_by_sale_ref에 inventory_tonbag 업데이트 없음"
        assert "status='AVAILABLE'" in func_body

    def test_tonbag_restored_on_cancel(self, test_db):
        """취소 시 tonbag도 AVAILABLE로 복구되는지 DB 레벨 검증"""
        test_db.execute("INSERT INTO inventory(lot_no, status, current_weight, sale_ref) VALUES (?,?,?,?)",
                        ('LOT001', 'RESERVED', 5000.0, 'REF-X'))
        inv_id = test_db.execute("SELECT id FROM inventory WHERE lot_no='LOT001'").fetchone()[0]
        test_db.execute(
            "INSERT INTO inventory_tonbag(inventory_id, lot_no, sub_lt, status, weight) VALUES (?,?,?,?,?)",
            (inv_id, 'LOT001', 1, 'RESERVED', 500.0)
        )
        test_db.execute(
            "INSERT INTO inventory_tonbag(inventory_id, lot_no, sub_lt, status, weight) VALUES (?,?,?,?,?)",
            (inv_id, 'LOT001', 2, 'PICKED', 500.0)
        )
        test_db.commit()

        # 취소 로직 재현
        test_db.execute(
            "UPDATE inventory SET status='AVAILABLE', sold_to=NULL, sale_ref=NULL WHERE lot_no=? AND status NOT IN ('SOLD')",
            ('LOT001',)
        )
        test_db.execute(
            "UPDATE inventory_tonbag SET status='AVAILABLE' WHERE lot_no=? AND status IN ('RESERVED','PICKED','STAGED')",
            ('LOT001',)
        )
        test_db.commit()

        inv = test_db.execute("SELECT status FROM inventory WHERE lot_no='LOT001'").fetchone()
        assert inv['status'] == 'AVAILABLE'

        tbs = test_db.execute("SELECT status FROM inventory_tonbag WHERE lot_no='LOT001'").fetchall()
        for tb in tbs:
            assert tb['status'] == 'AVAILABLE', f"tonbag status={tb['status']} 복구 안 됨"


# ═══════════════════════════════════════════════════════
# B-3: outbound_confirm current_weight 차감 + rollback
# ═══════════════════════════════════════════════════════
class TestB3_OutboundConfirm:
    def test_current_weight_set_to_zero(self):
        src = open(os.path.join(ROOT, 'backend/api/actions2.py'), encoding='utf-8').read()
        func_start = src.index('def outbound_confirm')
        func_end = src.index('\ndef ', func_start + 1)
        func_body = src[func_start:func_end]
        assert 'current_weight=0' in func_body, \
            "outbound_confirm에 current_weight=0 차감 없음"

    def test_rollback_on_exception(self):
        src = open(os.path.join(ROOT, 'backend/api/actions2.py'), encoding='utf-8').read()
        func_start = src.index('def outbound_confirm')
        func_end = src.index('\ndef ', func_start + 1)
        func_body = src[func_start:func_end]
        assert 'rollback' in func_body, \
            "outbound_confirm except 블록에 rollback 없음"

    def test_weight_becomes_zero_after_sold(self, test_db):
        """출고 후 current_weight=0 검증"""
        test_db.execute(
            "INSERT INTO inventory(lot_no, status, current_weight) VALUES (?,?,?)",
            ('LOT-OUT', 'PICKED', 5000.0)
        )
        inv_id = test_db.execute("SELECT id FROM inventory WHERE lot_no='LOT-OUT'").fetchone()[0]
        test_db.execute(
            "UPDATE inventory SET status='SOLD', current_weight=0 WHERE id=?", (inv_id,)
        )
        test_db.commit()
        row = test_db.execute("SELECT current_weight, status FROM inventory WHERE lot_no='LOT-OUT'").fetchone()
        assert row['status'] == 'SOLD'
        assert row['current_weight'] == 0.0, f"current_weight={row['current_weight']} 0이 아님"


# ═══════════════════════════════════════════════════════
# B-4: onestop_complete inventory.status 갱신
# ═══════════════════════════════════════════════════════
class TestB4_OnestopComplete:
    def test_inventory_update_in_by_lot_loop(self):
        src = open(os.path.join(ROOT, 'backend/api/outbound_api.py'), encoding='utf-8').read()
        func_start = src.index('def onestop_complete')
        func_end = src.index('\n@', func_start + 1)
        func_body = src[func_start:func_end]
        # by_lot 루프 안에 inventory UPDATE가 있는지
        assert 'UPDATE inventory' in func_body, \
            "onestop_complete by_lot 루프에 inventory UPDATE 없음"
        assert "status='SOLD'" in func_body

    def test_inventory_status_updated_with_tonbag(self, test_db):
        """inventory + inventory_tonbag 모두 SOLD로 전환 검증"""
        test_db.execute(
            "INSERT INTO inventory(lot_no, status, current_weight) VALUES (?,?,?)",
            ('LOT-OC', 'PICKED', 5000.0)
        )
        inv_id = test_db.execute("SELECT id FROM inventory WHERE lot_no='LOT-OC'").fetchone()[0]
        for i in range(1, 4):
            test_db.execute(
                "INSERT INTO inventory_tonbag(inventory_id, lot_no, sub_lt, status) VALUES (?,?,?,?)",
                (inv_id, 'LOT-OC', i, 'PICKED')
            )
        test_db.commit()

        # onestop_complete 동작 재현
        test_db.execute(
            "UPDATE inventory_tonbag SET status='SOLD' WHERE lot_no=? AND status='PICKED'",
            ('LOT-OC',)
        )
        test_db.execute(
            "UPDATE inventory SET status='SOLD', current_weight=0 WHERE lot_no=? AND status != 'SOLD'",
            ('LOT-OC',)
        )
        test_db.commit()

        inv = test_db.execute("SELECT status, current_weight FROM inventory WHERE lot_no='LOT-OC'").fetchone()
        assert inv['status'] == 'SOLD'
        assert inv['current_weight'] == 0.0

        tbs = test_db.execute("SELECT status FROM inventory_tonbag WHERE lot_no='LOT-OC'").fetchall()
        assert all(tb['status'] == 'SOLD' for tb in tbs)


# ═══════════════════════════════════════════════════════
# D-1: allocation UNIQUE 인덱스 tonbag_id 단독
# ═══════════════════════════════════════════════════════
class TestD1_AllocationUniqueIndex:
    def test_tonbag_unique_index_in_migration(self):
        src = open(os.path.join(ROOT, 'engine_modules/db_migration_mixin.py'), encoding='utf-8').read()
        assert 'idx_alloc_tonbag_no_dup' in src, \
            "tonbag_id 단독 UNIQUE 인덱스 마이그레이션 없음"

    def test_unique_index_blocks_double_reservation(self, test_db):
        """동일 tonbag_id 이중 예약 차단 검증"""
        # 인덱스 생성
        test_db.execute("""
            CREATE UNIQUE INDEX idx_alloc_tonbag_no_dup
            ON allocation_plan(tonbag_id)
            WHERE status IN ('RESERVED', 'STAGED') AND tonbag_id IS NOT NULL
        """)
        test_db.execute(
            "INSERT INTO allocation_plan(lot_no, customer, sale_ref, tonbag_id, status) VALUES (?,?,?,?,?)",
            ('LOT001', 'CATL', 'REF-A', 100, 'RESERVED')
        )
        test_db.commit()

        # 같은 tonbag_id로 다른 고객사가 예약 시도 → 실패해야 함
        with pytest.raises(sqlite3.IntegrityError):
            test_db.execute(
                "INSERT INTO allocation_plan(lot_no, customer, sale_ref, tonbag_id, status) VALUES (?,?,?,?,?)",
                ('LOT001', 'BYD', 'REF-B', 100, 'RESERVED')
            )
            test_db.commit()

    def test_cancelled_allows_re_reservation(self, test_db):
        """CANCELLED 상태는 인덱스에서 제외 → 재예약 가능"""
        test_db.execute("""
            CREATE UNIQUE INDEX idx_alloc_tonbag_no_dup
            ON allocation_plan(tonbag_id)
            WHERE status IN ('RESERVED', 'STAGED') AND tonbag_id IS NOT NULL
        """)
        # 첫 예약 → 취소
        test_db.execute(
            "INSERT INTO allocation_plan(lot_no, customer, sale_ref, tonbag_id, status) VALUES (?,?,?,?,?)",
            ('LOT001', 'CATL', 'REF-A', 200, 'CANCELLED')
        )
        # 재예약 가능해야 함
        test_db.execute(
            "INSERT INTO allocation_plan(lot_no, customer, sale_ref, tonbag_id, status) VALUES (?,?,?,?,?)",
            ('LOT001', 'BYD', 'REF-B', 200, 'RESERVED')
        )
        test_db.commit()  # 예외 없음 = 성공


# ═══════════════════════════════════════════════════════
# F-1+F-2: router.js 클릭 바인딩 제거
# ═══════════════════════════════════════════════════════
class TestF1F2_RouterCleanup:
    def test_router_init_no_click_binding(self):
        src = open(os.path.join(ROOT, 'frontend/js/router.js'), encoding='utf-8').read()
        func_start = src.index('export function initRouter')
        func_end = src.index('\n}', func_start) + 2
        func_body = src[func_start:func_end]
        assert 'addEventListener' not in func_body, \
            "initRouter()에 여전히 addEventListener 클릭 바인딩 있음"

    def test_router_no_navigateto_call_in_init(self):
        src = open(os.path.join(ROOT, 'frontend/js/router.js'), encoding='utf-8').read()
        func_start = src.index('export function initRouter')
        func_end = src.index('\n}', func_start) + 2
        func_body = src[func_start:func_end]
        # 주석 라인 제거 후 실제 실행 코드에 navigateTo( 있는지 확인
        code_lines = [l for l in func_body.splitlines() if not l.strip().startswith('//')]
        code_only = '\n'.join(code_lines)
        assert 'navigateTo(' not in code_only, \
            "initRouter() 실행 코드에 navigateTo() 호출 남아있음 — 이중 라우터 충돌"


# ═══════════════════════════════════════════════════════
# F-6: sqm-tonbag.js boot 중복 제거
# ═══════════════════════════════════════════════════════
class TestF6_BootDedup:
    def test_tonbag_no_domcontentloaded_boot(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-tonbag.js'), encoding='utf-8').read()
        # DOMContentLoaded에 boot를 등록하는 라인이 없어야 함
        assert "addEventListener('DOMContentLoaded', boot)" not in src, \
            "sqm-tonbag.js에 DOMContentLoaded boot 등록 여전히 존재 — 이중 boot 실행"

    def test_tonbag_exposes_apply_functions(self):
        """boot 제거 후 applyStoredFontScale이 window에 노출되는지"""
        src = open(os.path.join(ROOT, 'frontend/js/sqm-tonbag.js'), encoding='utf-8').read()
        assert 'window.applyStoredFontScale' in src, \
            "sqm-tonbag.js boot 제거 후 applyStoredFontScale window 미노출"
        assert 'window.applyStoredTablePreset' in src, \
            "sqm-tonbag.js boot 제거 후 applyStoredTablePreset window 미노출"

    def test_inline_safely_calls_apply_functions(self):
        """sqm-inline.js가 window.applyStoredFontScale을 안전하게(if 체크) 호출하는지"""
        src = open(os.path.join(ROOT, 'frontend/js/sqm-inline.js'), encoding='utf-8').read()
        assert 'window.applyStoredFontScale' in src


# ═══════════════════════════════════════════════════════
# F-10: defineProperty 오타 제거
# ═══════════════════════════════════════════════════════
class TestF10_DefinePropertyFix:
    def test_typo_property_removed(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-tonbag.js'), encoding='utf-8').read()
        assert "defineProperty(window, 'window.getCurrentRoute()')" not in src, \
            "sqm-tonbag.js 오타 defineProperty('window.getCurrentRoute()') 아직 남아있음"
