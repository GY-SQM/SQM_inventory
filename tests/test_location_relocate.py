"""
SQM v7.0.1 — 이동(RELOCATE) 로직 패치 테스트
==============================================

테스트 항목:
  1. MOVEMENT_RELOCATE 상수 존재
  2. update_tonbag_location — 이력 기록 + location_updated_at
  3. update_tonbag_location — 위치 미변경 시 이력 미기록
  4. update_locations (일괄) — stock_movement RELOCATE 기록
  5. get_location_summary — weight 컬럼 사용 (current_weight 버그 수정)
  6. _import_location_excel → uploader 리다이렉트 확인
  7. 톤백 우클릭 메서드 존재
"""

import os
import sqlite3
import sys

import pytest

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConstants:
    """상수 테스트"""

    def test_movement_relocate_exists(self):
        """MOVEMENT_RELOCATE 상수 존재 확인"""
        from engine_modules.constants import MOVEMENT_RELOCATE
        assert MOVEMENT_RELOCATE == 'RELOCATE'

    def test_all_movement_types(self):
        """전체 movement_type 상수 12개 확인"""
        from engine_modules import constants
        movement_types = [
            'MOVEMENT_INBOUND', 'MOVEMENT_OUTBOUND', 'MOVEMENT_RETURN',
            'MOVEMENT_ADJUSTMENT', 'MOVEMENT_QUICK_OUTBOUND', 'MOVEMENT_SOLD',
            'MOVEMENT_CANCEL_OUTBOUND', 'MOVEMENT_RESERVED', 'MOVEMENT_CANCEL_RESERVE',
            'MOVEMENT_REVERT_PICKED', 'MOVEMENT_REVERT_SOLD', 'MOVEMENT_RELOCATE'
        ]
        for mt in movement_types:
            assert hasattr(constants, mt), f"상수 누락: {mt}"


class MockDB:
    """테스트용 인메모리 SQLite DB"""

    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self._setup_tables()

    def _setup_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                product TEXT,
                status TEXT DEFAULT 'AVAILABLE',
                initial_weight REAL DEFAULT 0,
                current_weight REAL DEFAULT 0,
                warehouse TEXT DEFAULT '광양'
            )
        """)
        cur.execute("""
            CREATE TABLE inventory_tonbag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,
                lot_no TEXT NOT NULL,
                sub_lt INTEGER NOT NULL DEFAULT 0,
                weight REAL DEFAULT 500.0,
                status TEXT DEFAULT 'AVAILABLE',
                location TEXT,
                location_updated_at TEXT,
                picked_to TEXT,
                picked_date TEXT,
                pick_ref TEXT,
                outbound_date TEXT,
                sale_ref TEXT,
                tonbag_uid TEXT,
                updated_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE stock_movement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                qty_kg REAL DEFAULT 0,
                from_location TEXT,
                to_location TEXT,
                customer TEXT,
                movement_date TIMESTAMP,
                remarks TEXT,
                source_type TEXT,
                source_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

        # 테스트 데이터 삽입
        cur.execute("""
            INSERT INTO inventory (lot_no, product, status, initial_weight, current_weight)
            VALUES ('1234567890', 'LITHIUM', 'AVAILABLE', 5001, 5001)
        """)
        inv_id = cur.lastrowid

        for i in range(1, 11):
            cur.execute("""
                INSERT INTO inventory_tonbag 
                (inventory_id, lot_no, sub_lt, weight, status, location)
                VALUES (?, '1234567890', ?, 500.0, 'AVAILABLE', ?)
            """, (inv_id, i, f'A-01-01-{i:02d}'))

        # 샘플 톤백
        cur.execute("""
            INSERT INTO inventory_tonbag 
            (inventory_id, lot_no, sub_lt, weight, status, location)
            VALUES (?, '1234567890', 0, 1.0, 'SAMPLE', 'S-ZONE')
        """, (inv_id,))

        self.conn.commit()

    def fetchone(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        if row:
            return dict(row)
        return None

    def fetchall(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    def execute(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()
        return cur

    def transaction(self):
        return _TransactionCtx(self.conn)


class _TransactionCtx:
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


class TestUpdateTonbagLocation:
    """tonbag_mixin.update_tonbag_location 테스트"""

    def setup_method(self):
        self.db = MockDB()

    def test_location_update_with_history(self):
        """위치 변경 시 stock_movement RELOCATE 기록"""
        from engine_modules.inventory_modular.tonbag_mixin import TonbagMixin

        class Engine(TonbagMixin):
            pass

        engine = Engine()
        engine.db = self.db

        result = engine.update_tonbag_location('1234567890', 1, 'B-02-03-04', source='MANUAL')

        assert result['success'] is True
        assert result['from_location'] == 'A-01-01-01'
        assert result['to_location'] == 'B-02-03-04'

        # DB 확인
        tb = self.db.fetchone(
            "SELECT location, location_updated_at FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
            ('1234567890', 1)
        )
        assert tb['location'] == 'B-02-03-04'
        assert tb['location_updated_at'] is not None

        # stock_movement 확인
        mv = self.db.fetchone(
            "SELECT * FROM stock_movement WHERE lot_no = ? AND movement_type = 'RELOCATE'",
            ('1234567890',)
        )
        assert mv is not None
        assert mv['from_location'] == 'A-01-01-01'
        assert mv['to_location'] == 'B-02-03-04'
        assert mv['qty_kg'] == 500.0
        assert 'sub_lt=1' in mv['remarks']
        assert 'source=MANUAL' in mv['remarks']

    def test_no_history_when_same_location(self):
        """위치 미변경 시 stock_movement 미기록"""
        from engine_modules.inventory_modular.tonbag_mixin import TonbagMixin

        class Engine(TonbagMixin):
            pass

        engine = Engine()
        engine.db = self.db

        result = engine.update_tonbag_location('1234567890', 1, 'A-01-01-01')
        assert result['success'] is True

        mv = self.db.fetchone(
            "SELECT * FROM stock_movement WHERE lot_no = ? AND movement_type = 'RELOCATE'",
            ('1234567890',)
        )
        assert mv is None  # 같은 위치 → 이력 없음

    def test_nonexistent_tonbag(self):
        """존재하지 않는 톤백"""
        from engine_modules.inventory_modular.tonbag_mixin import TonbagMixin

        class Engine(TonbagMixin):
            pass

        engine = Engine()
        engine.db = self.db

        result = engine.update_tonbag_location('9999999999', 99, 'B-01-01-01')
        assert result['success'] is False
        assert 'not found' in result['error'].lower()

    def test_location_updated_at_populated(self):
        """location_updated_at 갱신 확인"""
        from engine_modules.inventory_modular.tonbag_mixin import TonbagMixin

        class Engine(TonbagMixin):
            pass

        engine = Engine()
        engine.db = self.db

        # 변경 전 — location_updated_at는 NULL
        before = self.db.fetchone(
            "SELECT location_updated_at FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
            ('1234567890', 5)
        )
        assert before['location_updated_at'] is None

        # 변경
        engine.update_tonbag_location('1234567890', 5, 'C-03-02-01')

        after = self.db.fetchone(
            "SELECT location_updated_at FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
            ('1234567890', 5)
        )
        assert after['location_updated_at'] is not None


class TestBulkUpdateLocations:
    """tonbag_location_uploader.update_locations 일괄 업데이트 테스트"""

    def setup_method(self):
        self.db = MockDB()

    def _get_uploader(self):
        """tkinter 우회: 직접 모듈 import"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tonbag_location_uploader",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "gui_app_modular", "utils", "tonbag_location_uploader.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.TonbagLocationUploader(self.db)

    def test_bulk_update_with_relocate_history(self):
        """일괄 업데이트 시 RELOCATE 이력 기록"""
        uploader = self._get_uploader()

        matched_data = [
            {
                'tonbag_id': 1, 'location': 'D-01-01-01',
                'lot_no': '1234567890', 'sub_lt': 1,
                'current_location': 'A-01-01-01'
            },
            {
                'tonbag_id': 2, 'location': 'D-01-01-02',
                'lot_no': '1234567890', 'sub_lt': 2,
                'current_location': 'A-01-01-02'
            },
            {
                'tonbag_id': 3, 'location': 'A-01-01-03',  # 동일 위치 — 이력 미생성
                'lot_no': '1234567890', 'sub_lt': 3,
                'current_location': 'A-01-01-03'
            },
        ]

        success, msg = uploader.update_locations(matched_data)
        assert success is True
        assert '3개 톤백' in msg
        assert '이동 이력 2건' in msg  # 3번은 위치 미변경 → 2건만

        # stock_movement 확인
        mvs = self.db.fetchall(
            "SELECT * FROM stock_movement WHERE movement_type = 'RELOCATE' ORDER BY id"
        )
        assert len(mvs) == 2
        assert mvs[0]['from_location'] == 'A-01-01-01'
        assert mvs[0]['to_location'] == 'D-01-01-01'
        assert mvs[1]['from_location'] == 'A-01-01-02'
        assert mvs[1]['to_location'] == 'D-01-01-02'

    def test_bulk_update_empty_data(self):
        """빈 데이터 시 실패"""
        uploader = self._get_uploader()
        success, msg = uploader.update_locations([])
        assert success is False

    def test_location_updated_at_set_in_bulk(self):
        """일괄 업데이트 시 location_updated_at 갱신"""
        uploader = self._get_uploader()

        matched_data = [{
            'tonbag_id': 4, 'location': 'E-01-01-01',
            'lot_no': '1234567890', 'sub_lt': 4,
            'current_location': 'A-01-01-04'
        }]

        success, _ = uploader.update_locations(matched_data)
        assert success is True

        tb = self.db.fetchone(
            "SELECT location_updated_at FROM inventory_tonbag WHERE id = 4"
        )
        assert tb['location_updated_at'] is not None


class TestGetLocationSummary:
    """get_location_summary — weight 컬럼 사용 확인"""

    def setup_method(self):
        self.db = MockDB()

    def test_summary_uses_weight_column(self):
        """weight 컬럼으로 SUM — current_weight 아님"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tonbag_location_uploader",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "gui_app_modular", "utils", "tonbag_location_uploader.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        uploader = mod.TonbagLocationUploader(self.db)

        summary = uploader.get_location_summary()

        # 10개 톤백이 각각 다른 location에 있음
        assert len(summary) >= 1

        # total_weight가 0이 아님 (weight 컬럼 사용 시 500.0)
        for loc, data in summary.items():
            assert data['total_weight'] > 0, f"위치 {loc}의 total_weight가 0 — current_weight 컬럼 사용 버그"


class TestImportLocationRedirect:
    """_import_location_excel → uploader 리다이렉트 확인 (파일 소스 검사)"""

    def test_redirect_code_exists(self):
        """교체된 코드에 show_tonbag_location_upload_dialog 호출 존재"""
        handler_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "gui_app_modular", "handlers", "status_import_handlers.py"
        )
        with open(handler_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # _import_location_excel 부분에 uploader 리다이렉트 존재
        assert 'show_tonbag_location_upload_dialog' in source
        # 구 코드 흔적 없음 (pd.read_excel은 다른 메서드에 있을 수 있으므로 메서드 단위 검증)
        # _import_location_excel 메서드만 추출
        idx_start = source.index('def _import_location_excel')
        idx_end = source.index('\n    def ', idx_start + 1)
        method_source = source[idx_start:idx_end]

        assert 'show_tonbag_location_upload_dialog' in method_source
        assert 'pd.read_excel' not in method_source
        assert 'filedialog.askopenfilename' not in method_source


class TestTonbagTabContextMenu:
    """톤백 탭 우클릭 메서드 존재 확인 (파일 소스 검사)"""

    def _get_source(self):
        tab_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "gui_app_modular", "tabs", "tonbag_tab.py"
        )
        with open(tab_path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_right_click_method_exists(self):
        """_on_tonbag_right_click 메서드 존재"""
        source = self._get_source()
        assert 'def _on_tonbag_right_click(self' in source

    def test_edit_location_method_exists(self):
        """_on_tonbag_edit_location 메서드 존재"""
        source = self._get_source()
        assert 'def _on_tonbag_edit_location(self' in source

    def test_right_click_binding_in_source(self):
        """Button-3 바인딩 코드 존재"""
        source = self._get_source()
        assert 'Button-3' in source

    def test_context_menu_has_location_option(self):
        """컨텍스트 메뉴에 위치 변경 항목 존재"""
        source = self._get_source()
        assert '위치 변경' in source

    def test_relocate_history_in_edit(self):
        """위치 변경 시 update_tonbag_location 호출"""
        source = self._get_source()
        assert 'update_tonbag_location' in source
        assert "source='MANUAL'" in source


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
