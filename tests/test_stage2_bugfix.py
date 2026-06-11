# -*- coding: utf-8 -*-
"""
2단계 버그 수정 스모크 테스트
F-3/4/5/7/8, B-7/8/9/10, D-2/3/4/5/6 수정 검증
"""
import os, sys, sqlite3, pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


@pytest.fixture
def test_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY, lot_no TEXT,
            status TEXT, current_weight REAL DEFAULT 0,
            sold_to TEXT, sale_ref TEXT, updated_at TEXT
        );
        CREATE TABLE inventory_tonbag (
            id INTEGER PRIMARY KEY, inventory_id INTEGER,
            lot_no TEXT, sub_lt INTEGER, tonbag_id INTEGER,
            status TEXT, weight REAL DEFAULT 0,
            outbound_date TEXT, updated_at TEXT
        );
        CREATE TABLE allocation_plan (
            id INTEGER PRIMARY KEY, lot_no TEXT,
            customer TEXT, sale_ref TEXT, tonbag_id INTEGER,
            status TEXT, updated_at TEXT, cancelled_at TEXT
        );
        CREATE TABLE sold_table (
            id INTEGER PRIMARY KEY, sales_order_no TEXT,
            lot_no TEXT, sub_lt INTEGER, tonbag_id INTEGER,
            status TEXT
        );
    """)
    yield con
    con.close()


# ═══════════════════════════════════════════════════
# F-3+F-7: window.API 즉시캡처 제거
# ═══════════════════════════════════════════════════
class TestF3F7_ApiCapture:
    def test_aux_modals_no_window_api_capture(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-aux-modals.js'), encoding='utf-8').read()
        assert 'var API = window.API' not in src, \
            "sqm-aux-modals.js에 window.API 즉시캡처 남아있음"
        assert '_api()' in src, "sqm-aux-modals.js에 _api() 함수 없음"

    def test_upload_modals_no_window_api_capture(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-upload-modals.js'), encoding='utf-8').read()
        assert 'var API = window.API' not in src, \
            "sqm-upload-modals.js에 window.API 즉시캡처 남아있음"

    def test_settings_templates_no_raw_window_api(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-settings-templates.js'), encoding='utf-8').read()
        # window.API || 체인 직접 캡처 제거됐는지
        assert "var API = window.API || window.SQM_API_BASE" not in src, \
            "sqm-settings-templates.js에 window.API 직접캡처 남아있음"
        assert '_api()' in src

    def test_api_func_reads_sqm_api_base_first(self):
        """_api() 함수가 SQM_API_BASE를 우선 읽는지"""
        for fname in ['sqm-aux-modals.js', 'sqm-settings-templates.js']:
            src = open(os.path.join(ROOT, f'frontend/js/{fname}'), encoding='utf-8').read()
            func_start = src.index('function _api()')
            func_end = src.index('}', func_start) + 1
            func_body = src[func_start:func_end]
            assert 'SQM_API_BASE' in func_body, f"{fname}: _api()가 SQM_API_BASE 참조 안 함"


# ═══════════════════════════════════════════════════
# F-4: dispatchAction — onImportAllocationTemplate 추가
# ═══════════════════════════════════════════════════
class TestF4_DispatchAction:
    def test_import_alloc_template_in_inline_endpoints(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-inline.js'), encoding='utf-8').read()
        assert 'onImportAllocationTemplate' in src, \
            "sqm-inline.js ENDPOINTS에 onImportAllocationTemplate 없음 — tonbag 액션 누락"


# ═══════════════════════════════════════════════════
# F-5: _currentRoute getter — getCurrentRoute() 위임
# ═══════════════════════════════════════════════════
class TestF5_CurrentRoute:
    def test_currentroute_getter_uses_getcurrentroute(self):
        src = open(os.path.join(ROOT, 'frontend/js/sqm-inline.js'), encoding='utf-8').read()
        prop_start = src.index("Object.defineProperty(window, '_currentRoute'")
        prop_end = src.index('});', prop_start) + 3
        prop_body = src[prop_start:prop_end]
        assert 'getCurrentRoute' in prop_body, \
            "_currentRoute getter가 window.getCurrentRoute()를 위임하지 않음"


# ═══════════════════════════════════════════════════
# B-7: /api/allocation 이중 등록 제거
# ═══════════════════════════════════════════════════
class TestB7_AllocationRouter:
    def test_alloc_router_not_double_registered(self):
        src = open(os.path.join(ROOT, 'backend/api/__init__.py'), encoding='utf-8').read()
        # alloc_router include가 주석처리되거나 제거됐는지
        lines = [l for l in src.splitlines() if 'alloc_router' in l and 'include_router' in l]
        active = [l for l in lines if not l.strip().startswith('#')]
        assert len(active) == 0, \
            f"/api/allocation alloc_router 이중 등록 남아있음: {active}"


# ═══════════════════════════════════════════════════
# B-8: sidebar-counts SHIPPED/CONFIRMED 포함
# ═══════════════════════════════════════════════════
class TestB8_SidebarCounts:
    def test_shipped_confirmed_in_query(self):
        src = open(os.path.join(ROOT, 'backend/api/dashboard.py'), encoding='utf-8').read()
        # 함수 전체가 아닌 파일 전체에서 sidebar-counts 관련 쿼리 확인
        assert "'SHIPPED'" in src or '"SHIPPED"' in src, \
            "sidebar-counts 쿼리에 SHIPPED 미포함"
        assert "'CONFIRMED'" in src or '"CONFIRMED"' in src, \
            "sidebar-counts 쿼리에 CONFIRMED 미포함"


# ═══════════════════════════════════════════════════
# B-9: dashboard 에러 응답 ok 키 통일
# ═══════════════════════════════════════════════════
class TestB9_DashboardError:
    def test_dashboard_stats_error_has_ok_key(self):
        src = open(os.path.join(ROOT, 'backend/api/dashboard.py'), encoding='utf-8').read()
        # 이전: {"error": str(e)} 단독 → 이후: {"ok": False, "error": ...}
        assert '{"error": str(e)}' not in src, \
            "dashboard.py 에러 응답에 ok 키 없음 ({\"error\":...} 패턴 남아있음)"

    def test_dashboard_alerts_error_has_ok_key(self):
        src = open(os.path.join(ROOT, 'backend/api/dashboard.py'), encoding='utf-8').read()
        assert '"alerts": [], "total": 0, "error": str(e)}' not in src or \
               '"ok": False' in src


# ═══════════════════════════════════════════════════
# B-10: patch_allocation 응답 형식 통일
# ═══════════════════════════════════════════════════
class TestB10_PatchAllocation:
    def test_patch_allocation_uses_ok_key(self):
        src = open(os.path.join(ROOT, 'backend/api/allocation_api.py'), encoding='utf-8').read()
        func_start = src.index('def patch_allocation')
        func_end = src.index('\n@router', func_start)
        func_body = src[func_start:func_end]
        assert '"success": True' not in func_body, \
            "patch_allocation이 여전히 {success:True} 패턴 사용"
        assert '"ok": True' in func_body, \
            "patch_allocation이 {ok:True} 패턴 미사용"


# ═══════════════════════════════════════════════════
# D-2: 마이그레이션 순서 재정렬
# ═══════════════════════════════════════════════════
class TestD2_MigrationOrder:
    def test_v675_before_v700(self):
        src = open(os.path.join(ROOT, 'engine_modules/db_migration_mixin.py'), encoding='utf-8').read()
        pos675 = src.index('_migrate_v675_conflict_indexes')
        pos700 = src.index('_migrate_v700_return_log_reinbound')
        assert pos675 < pos700, "v675가 v700보다 뒤에 실행됨 (역순)"

    def test_v740_before_v800(self):
        src = open(os.path.join(ROOT, 'engine_modules/db_migration_mixin.py'), encoding='utf-8').read()
        pos740 = src.index('_migrate_v740_picking_template')
        pos800 = src.index('_migrate_v800_template_bl_format')
        assert pos740 < pos800, "v740가 v800보다 뒤에 실행됨 (역순)"

    def test_v868_before_v871(self):
        src = open(os.path.join(ROOT, 'engine_modules/db_migration_mixin.py'), encoding='utf-8').read()
        pos868 = src.index('_migrate_v868_pending_workflow_columns')
        pos871 = src.index('_migrate_v871_allocation_no_dup_index')
        assert pos868 < pos871, "v868이 v871보다 뒤에 실행됨 (역순)"

    def test_v868_before_v872(self):
        src = open(os.path.join(ROOT, 'engine_modules/db_migration_mixin.py'), encoding='utf-8').read()
        pos868 = src.index('_migrate_v868_packing_type_column')
        pos872 = src.index('_migrate_v872_inventory_weight_floor_insert')
        assert pos868 < pos872, "v868이 v872보다 뒤에 실행됨 (역순)"


# ═══════════════════════════════════════════════════
# D-3: RAISE(FAIL) 트리거 상위 catch
# ═══════════════════════════════════════════════════
class TestD3_TriggerCatch:
    def test_cancel_outbound_catches_trigger_error(self):
        src = open(os.path.join(ROOT, 'engine_modules/inventory_modular/outbound_mixin.py'), encoding='utf-8').read()
        assert 'cannot be negative' in src, \
            "outbound_mixin에 RAISE(FAIL) 트리거 에러 catch 없음"
        assert 'ValueError' in src


# ═══════════════════════════════════════════════════
# D-4: sold_table UNIQUE — COALESCE 타입 혼용 수정
# ═══════════════════════════════════════════════════
class TestD4_SoldTableUnique:
    def test_coalesce_removed_from_index(self):
        src = open(os.path.join(ROOT, 'engine_modules/db_migration_mixin.py'), encoding='utf-8').read()
        assert "COALESCE(sub_lt, '')" not in src, \
            "sold_table UNIQUE 인덱스에 COALESCE(sub_lt,'') 타입 혼용 남아있음"

    def test_tonbag_id_based_index_added(self):
        src = open(os.path.join(ROOT, 'engine_modules/db_migration_mixin.py'), encoding='utf-8').read()
        assert 'idx_sold_dedup_v2' in src, \
            "tonbag_id 기반 새 인덱스 idx_sold_dedup_v2 없음"

    def test_new_index_blocks_duplicate(self, test_db):
        test_db.execute("""
            CREATE UNIQUE INDEX idx_sold_dedup_v2
            ON sold_table(sales_order_no, tonbag_id)
            WHERE sales_order_no IS NOT NULL AND tonbag_id IS NOT NULL
        """)
        test_db.execute(
            "INSERT INTO sold_table(sales_order_no, tonbag_id, status) VALUES (?,?,?)",
            ('SO-001', 100, 'ACTIVE')
        )
        test_db.commit()
        with pytest.raises(sqlite3.IntegrityError):
            test_db.execute(
                "INSERT INTO sold_table(sales_order_no, tonbag_id, status) VALUES (?,?,?)",
                ('SO-001', 100, 'ACTIVE')
            )
            test_db.commit()


# ═══════════════════════════════════════════════════
# D-5: 복구 경로 weight 음수 검증
# ═══════════════════════════════════════════════════
class TestD5_CancelWeight:
    def test_cancel_validates_negative_weight(self):
        src = open(os.path.join(ROOT, 'engine_modules/inventory_modular/outbound_mixin.py'), encoding='utf-8').read()
        func_start = src.index('def cancel_outbound_tonbag')
        func_end = src.index('\n    def ', func_start + 1)
        func_body = src[func_start:func_end]
        assert 'weight < 0' in func_body, \
            "cancel_outbound_tonbag에 weight 음수 검증 없음"
        assert 'abs(weight)' in func_body, \
            "cancel_outbound_tonbag에 abs() 방어 처리 없음"


# ═══════════════════════════════════════════════════
# D-6: sidebar-counts total.sample_bags 실제 합산
# ═══════════════════════════════════════════════════
class TestD6_SampleBags:
    def test_total_sample_bags_not_hardcoded_zero(self):
        src = open(os.path.join(ROOT, 'backend/api/dashboard.py'), encoding='utf-8').read()
        assert 'total_sample' in src, "total_sample 합산 변수 없음"
        # total_sample 이 sample_bags 합산에 쓰이는지
        assert 'sample_bags\": total_sample' in src or \
               '"sample_bags": total_sample' in src, \
            "total.sample_bags가 total_sample로 설정되지 않음"
