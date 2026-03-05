# -*- coding: utf-8 -*-
"""
SQM v7.0.1 — 정합성 검증 강화 + 위치 대시보드 테스트
"""

import pytest
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# core.constants 순환 참조 방지 stub
import types as _types
if 'core' not in sys.modules:
    _core = _types.ModuleType('core')
    _core_const = _types.ModuleType('core.constants')
    _core_const.SAMPLE_WEIGHT_KG = 1.0
    _core_const.DEFAULT_WAREHOUSE = '광양'
    _core_const.STATUS_AVAILABLE = 'AVAILABLE'
    _core_const.STATUS_RESERVED = 'RESERVED'
    _core_const.STATUS_PICKED = 'PICKED'
    _core_const.STATUS_SOLD = 'SOLD'
    _core_const.STATUS_DEPLETED = 'DEPLETED'
    _core_const.STATUS_CONFIRMED = 'CONFIRMED'
    _core_const.STATUS_SHIPPED = 'SHIPPED'
    _core_const.MOVEMENT_INBOUND = 'INBOUND'
    _core_const.MOVEMENT_OUTBOUND = 'OUTBOUND'
    _core_const.MOVEMENT_RETURN = 'RETURN'
    _core_const.MOVEMENT_RESERVED = 'RESERVED'
    _core_const.MOVEMENT_CANCEL_RESERVE = 'CANCEL_RESERVE'
    _core_const.MOVEMENT_REVERT_PICKED = 'REVERT_PICKED'
    _core_const.MOVEMENT_REVERT_SOLD = 'REVERT_SOLD'
    _core_const.MOVEMENT_SOLD = 'SOLD'
    _core_const.MOVEMENT_CANCEL_OUTBOUND = 'CANCEL_OUTBOUND'
    sys.modules['core'] = _core
    sys.modules['core.constants'] = _core_const
    _core.constants = _core_const

WEIGHT_TOLERANCE_KG = 0.5


class IntegrityTestDB:
    """정합성 테스트용 인메모리 DB"""
    
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self._setup()
    
    def _setup(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_no TEXT NOT NULL UNIQUE,
                product TEXT DEFAULT 'LITHIUM',
                status TEXT DEFAULT 'AVAILABLE',
                initial_weight REAL DEFAULT 0,
                current_weight REAL DEFAULT 0,
                picked_weight REAL DEFAULT 0,
                net_weight REAL DEFAULT 0,
                mxbg_pallet INTEGER DEFAULT 0,
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
                is_sample INTEGER DEFAULT 0,
                status TEXT DEFAULT 'AVAILABLE',
                location TEXT,
                location_updated_at TEXT,
                updated_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE stock_movement (
                id INTEGER PRIMARY KEY, lot_no TEXT, movement_type TEXT,
                qty_kg REAL, from_location TEXT, to_location TEXT,
                customer TEXT, movement_date TIMESTAMP, remarks TEXT,
                source_type TEXT, source_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE shipment (
                id INTEGER PRIMARY KEY, sap_no TEXT UNIQUE
            )
        """)
        self.conn.commit()
    
    def _insert_lot_with_tonbags(self, lot_no, count=10, unit_weight=500.0,
                                  statuses=None, locations=None):
        """테스트용 LOT + 톤백 + 샘플 삽입"""
        sample_w = 1.0  # SAMPLE_WEIGHT_KG
        initial_w = count * unit_weight + sample_w
        
        if statuses is None:
            statuses = ['AVAILABLE'] * count
        
        # AVAILABLE + SAMPLE = current_weight (RESERVED는 current에 포함)
        avail_w = sum(unit_weight for s in statuses if s in ('AVAILABLE', 'RESERVED'))
        avail_w += sample_w
        picked_w = sum(unit_weight for s in statuses if s in ('PICKED', 'SOLD'))
        
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO inventory (lot_no, product, status, initial_weight, current_weight, 
                                   picked_weight, net_weight, mxbg_pallet)
            VALUES (?, 'LITHIUM', 'AVAILABLE', ?, ?, ?, ?, ?)
        """, (lot_no, initial_w, avail_w, picked_w, initial_w, count))
        inv_id = cur.lastrowid
        
        for i in range(count):
            loc = locations[i] if locations and i < len(locations) else f'A-01-01-{i+1:02d}'
            cur.execute("""
                INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, is_sample, status, location)
                VALUES (?, ?, ?, ?, 0, ?, ?)
            """, (inv_id, lot_no, i + 1, unit_weight, statuses[i], loc))
        
        # 샘플
        cur.execute("""
            INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, is_sample, status, location)
            VALUES (?, ?, 0, ?, 1, 'SAMPLE', 'S-ZONE')
        """, (inv_id, lot_no, sample_w))
        
        self.conn.commit()
    
    def fetchone(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None
    
    def fetchall(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    
    def execute(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()
        return cur
    
    def commit(self):
        self.conn.commit()
    
    def rollback(self):
        self.conn.rollback()


class TestIntegrityReserved:
    """RESERVED 톤백 정합성 검증 테스트"""
    
    def test_reserved_included_in_avail_weight(self):
        """RESERVED 톤백이 avail_w에 포함되어 정합성 통과"""
        db = IntegrityTestDB()
        # 10개 중 3개 RESERVED
        statuses = ['AVAILABLE'] * 7 + ['RESERVED'] * 3
        db._insert_lot_with_tonbags('1234567890', 10, 500.0, statuses)
        
        import importlib.util
        spec = importlib.util.spec_from_file_location('integrity_mixin',
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'engine_modules', 'inventory_modular', 'integrity_mixin.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        class Engine(mod.IntegrityMixin):
            pass
        
        engine = Engine()
        engine.db = db
        
        result = engine.verify_lot_integrity('1234567890')
        assert result['valid'] is True, f"정합성 실패: {result['errors']}"
        assert result['details']['reserved_count'] == 3
        assert result['details']['tonbag_reserved_weight'] == 1500.0
    
    def test_reserved_and_picked_mix(self):
        """RESERVED + PICKED 혼합 상태 정합성"""
        db = IntegrityTestDB()
        # 5 AVAILABLE + 3 RESERVED + 2 PICKED
        statuses = ['AVAILABLE'] * 5 + ['RESERVED'] * 3 + ['PICKED'] * 2
        db._insert_lot_with_tonbags('1234567891', 10, 500.0, statuses)
        
        import importlib.util
        spec = importlib.util.spec_from_file_location('integrity_mixin',
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'engine_modules', 'inventory_modular', 'integrity_mixin.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        class Engine(mod.IntegrityMixin):
            pass
        
        engine = Engine()
        engine.db = db
        
        result = engine.verify_lot_integrity('1234567891')
        assert result['valid'] is True, f"정합성 실패: {result['errors']}"
    
    def test_all_reserved_valid(self):
        """전체 RESERVED도 정합성 통과"""
        db = IntegrityTestDB()
        statuses = ['RESERVED'] * 10
        db._insert_lot_with_tonbags('1234567892', 10, 500.0, statuses)
        
        import importlib.util
        spec = importlib.util.spec_from_file_location('integrity_mixin',
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'engine_modules', 'inventory_modular', 'integrity_mixin.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        class Engine(mod.IntegrityMixin):
            pass
        
        engine = Engine()
        engine.db = db
        
        result = engine.verify_lot_integrity('1234567892')
        assert result['valid'] is True, f"정합성 실패: {result['errors']}"


class TestValidateOutbound:
    """validate_outbound RESERVED LOT 허용 테스트"""
    
    def test_reserved_lot_outbound_allowed(self):
        """RESERVED 상태 LOT 출고 허용"""
        db = IntegrityTestDB()
        db.execute("""
            INSERT INTO inventory (lot_no, product, status, initial_weight, current_weight)
            VALUES ('1234567893', 'LITHIUM', 'RESERVED', 5001, 5001)
        """)
        
        import importlib.util
        spec = importlib.util.spec_from_file_location('validators',
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'engine_modules', 'validators.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        v = mod.InventoryValidator(db=db)
        result = v.validate_outbound('1234567893', 1000)
        assert result.is_valid is True


class TestCheckDataIntegrityLocationWarning:
    """check_data_integrity 위치 미지정 경고 테스트"""
    
    def test_no_location_warning(self):
        """위치 미지정 톤백 경고"""
        db = IntegrityTestDB()
        db.execute("INSERT INTO inventory (lot_no, product) VALUES ('1234567894', 'LITHIUM')")
        for i in range(5):
            db.execute("""
                INSERT INTO inventory_tonbag (lot_no, sub_lt, status, location)
                VALUES ('1234567894', ?, 'AVAILABLE', ?)
            """, (i + 1, f'A-01-01-{i+1:02d}'))
        for i in range(3):
            db.execute("""
                INSERT INTO inventory_tonbag (lot_no, sub_lt, status, location)
                VALUES ('1234567894', ?, 'AVAILABLE', NULL)
            """, (i + 6,))
        
        import importlib.util
        spec = importlib.util.spec_from_file_location('validators',
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'engine_modules', 'validators.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        v = mod.InventoryValidator(db=db)
        result = v.check_data_integrity()
        
        warning_text = ' '.join(result.warnings)
        assert '위치 미지정' in warning_text
        assert '3개' in warning_text


class TestLocationZoneStats:
    """구역별 위치 통계 테스트 (파일 소스 검사)"""
    
    def test_method_exists(self):
        """_get_location_zone_stats 메서드 존재"""
        mixin_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "gui_app_modular", "tabs", "dashboard_data_mixin.py"
        )
        with open(mixin_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'def _get_location_zone_stats' in source
    
    def test_dashboard_widget_exists(self):
        """_setup_dash_location_zone 메서드 존재"""
        tab_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "gui_app_modular", "tabs", "dashboard_tab.py"
        )
        with open(tab_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'def _setup_dash_location_zone' in source
        assert 'def _refresh_dashboard_location_zone' in source
        assert '_refresh_dashboard_location_zone' in source  # _refresh_dashboard에서 호출
    
    def test_dashboard_refresh_calls_location(self):
        """_refresh_dashboard에서 location zone 새로고침 호출"""
        tab_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "gui_app_modular", "tabs", "dashboard_tab.py"
        )
        with open(tab_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # _refresh_dashboard 메서드 내에서 호출
        idx_start = source.index('def _refresh_dashboard(self)')
        idx_end = source.index('\n    def ', idx_start + 1)
        method_source = source[idx_start:idx_end]
        assert '_refresh_dashboard_location_zone' in method_source


class TestValidatorsSource:
    """validators.py 소스 검증"""
    
    def test_outbound_allows_reserved(self):
        """validate_outbound에서 RESERVED 허용"""
        val_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "engine_modules", "validators.py"
        )
        with open(val_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "'AVAILABLE', 'PARTIAL', 'RESERVED'" in source
    
    def test_location_warning_in_check(self):
        """check_data_integrity에 위치 미지정 경고 존재"""
        val_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "engine_modules", "validators.py"
        )
        with open(val_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert '위치 미지정 톤백' in source


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
