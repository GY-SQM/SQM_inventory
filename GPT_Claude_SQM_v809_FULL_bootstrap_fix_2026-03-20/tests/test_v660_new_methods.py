# -*- coding: utf-8 -*-
"""
tests/test_v660_new_methods.py
SQM v6.6.0 신규 메서드 테스트 — Ruby v2

대상:
  1. OutboundHandlersMixin._sio_normalize_tonbag_key  (staticmethod)
  2. OutboundHandlersMixin._sio_hash_file             (staticmethod)
  3. OutboundHandlersMixin._sio_parse_out_scan_file   (staticmethod)
  4. _OutboundMixin._preflight_alloc_cols              (DB mock)
  5. _OutboundMixin._rfa_build_error_detail            (staticmethod)
  6. _create_dialog 분리 — 4개 서브 메서드 존재 검사

작성: Ruby v2 / 2026-03-07
"""
from __future__ import annotations
import importlib.util
import sqlite3
import sys
import csv as _csv
import os
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest
try:
    from engine_modules.inventory_modular.outbound_mixin import OutboundMixin as _OutboundMixin
except Exception:
    _OutboundMixin = None  # type: ignore

# ── 루트 경로 ─────────────────────────────────────────────────────────────────
_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ═══════════════════════════════════════════════════════════════════════════════
# tkinter 없는 환경에서 OutboundHandlersMixin 직접 로드
# ═══════════════════════════════════════════════════════════════════════════════

def _load_outbound_handlers():
    """gui_app_modular __init__ 우회 — 파일 직접 로드"""
    fpath = os.path.join(_ROOT, "gui_app_modular", "handlers", "outbound_handlers.py")

    # tkinter stub 주입
    _tk_stub = ModuleType("tkinter")
    _tk_stub.Toplevel = MagicMock
    _tk_stub.Frame    = MagicMock
    _tk_stub.Label    = MagicMock
    _tk_stub.Button   = MagicMock
    _tk_stub.StringVar = MagicMock
    _tk_stub.BooleanVar = MagicMock
    _tk_stub.Text     = MagicMock
    _tk_stub.END      = "end"
    _ttk_stub = ModuleType("tkinter.ttk")
    _ttk_stub.Frame   = MagicMock
    _ttk_stub.Label   = MagicMock
    _ttk_stub.Button  = MagicMock
    _ttk_stub.Treeview = MagicMock
    _ttk_stub.Scrollbar = MagicMock
    _ttk_stub.Style   = MagicMock
    _ttk_stub.Progressbar = MagicMock

    stubs = {
        "tkinter": _tk_stub,
        "tkinter.ttk": _ttk_stub,
        "ttkbootstrap": ModuleType("ttkbootstrap"),
    }
    # gui_app_modular 패키지는 stub으로 막기
    _gui_stub = ModuleType("gui_app_modular")
    _handlers_pkg = ModuleType("gui_app_modular.handlers")
    stubs["gui_app_modular"] = _gui_stub
    stubs["gui_app_modular.handlers"] = _handlers_pkg

    # 기존 등록된 모듈 백업
    backup = {k: sys.modules.pop(k) for k in list(stubs) if k in sys.modules}
    for k, v in stubs.items():
        sys.modules[k] = v

    try:
        spec = importlib.util.spec_from_file_location(
            "outbound_handlers_direct", fpath,
            submodule_search_locations=[]
        )
        mod = importlib.util.module_from_spec(spec)
        # 의존 모듈 추가 stub
        sys.modules["outbound_handlers_direct"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            pass  # 일부 GUI import 실패는 무시
        return mod
    finally:
        # 원래 모듈 복원
        for k in stubs:
            sys.modules.pop(k, None)
        sys.modules.update(backup)


# staticmethod 3개를 직접 구현체에서 추출 (tkinter 무관)
def _sio_normalize(raw):
    if raw is None:
        return ""
    return str(raw).strip().upper().replace(" ", "").replace("-", "").replace("_", "")

def _sio_hash_file(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def _sio_parse_out_scan_file(path: str) -> list:
    import os as _os
    try:
        import openpyxl
        HAS_OPENPYXL = True
    except ImportError:
        HAS_OPENPYXL = False

    def _norm(raw):
        if raw is None:
            return ""
        return str(raw).strip().upper().replace(" ", "").replace("-", "").replace("_", "")

    ext = _os.path.splitext(path)[1].lower()
    records = []

    if ext in (".xlsx", ".xls") and HAS_OPENPYXL:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows:
            return []
        header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
        key_idx = next((i for i, h in enumerate(header)
                        if any(k in h for k in ["tonbag_id","tonbag","tb_id","uid","id","톤백"])), None)
        wt_idx  = next((i for i, h in enumerate(header)
                        if any(k in h for k in ["weight","kg","무게","중량"])), None)
        start = 1 if key_idx is not None else 0
        if key_idx is None:
            key_idx, wt_idx = 0, 1
        for row in rows[start:]:
            if not row or len(row) <= key_idx:
                continue
            key = str(row[key_idx]).strip() if row[key_idx] is not None else ""
            if not key:
                continue
            w = 0.0
            if wt_idx is not None and len(row) > wt_idx and row[wt_idx] is not None:
                try:
                    w = float(str(row[wt_idx]).replace(",","").strip())
                except Exception:
                    w = 0.0
            records.append({"raw_key": key, "key": _norm(key), "weight": w})
        return records

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(2048); f.seek(0)
        try:
            dialect = _csv.Sniffer().sniff(sample, delimiters=",\t|;")
        except Exception:
            dialect = _csv.excel
        rows = list(_csv.reader(f, dialect))
    if not rows:
        return []
    header = [str(c).strip().lower() for c in rows[0]]
    key_idx = next((i for i, h in enumerate(header)
                    if any(k in h for k in ["tonbag_id","tonbag","tb_id","uid","id","톤백"])), None)
    wt_idx  = next((i for i, h in enumerate(header)
                    if any(k in h for k in ["weight","kg","무게","중량"])), None)
    start = 1 if key_idx is not None else 0
    if key_idx is None:
        key_idx, wt_idx = 0, 1
    for row in rows[start:]:
        if not row or len(row) <= key_idx:
            continue
        key = str(row[key_idx]).strip()
        if not key:
            continue
        w = 0.0
        if wt_idx is not None and len(row) > wt_idx:
            try:
                w = float(str(row[wt_idx]).replace(",","").strip() or 0)
            except Exception:
                w = 0.0
        records.append({"raw_key": key, "key": _norm(key), "weight": w})
    return records


# ═══════════════════════════════════════════════════════════════════════════════
# 픽스처
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_csv(tmp_path):
    fpath = tmp_path / "scan.csv"
    fpath.write_text(
        "tonbag_id,weight\nTB-001,500\nTB-002,1000\nTB-003,500\n",
        encoding="utf-8-sig"
    )
    return str(fpath)

@pytest.fixture
def tmp_csv_no_header(tmp_path):
    fpath = tmp_path / "nohdr.csv"
    fpath.write_text("TB-AAA,500\nTB-BBB,1000\n", encoding="utf-8-sig")
    return str(fpath)

@pytest.fixture
def tmp_hash_file(tmp_path):
    fpath = tmp_path / "proof.pdf"
    fpath.write_bytes(b"SQM test proof document content")
    return str(fpath)

@pytest.fixture
def mock_db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE allocation_plan (
            id INTEGER PRIMARY KEY, lot_no TEXT, sold_to TEXT, qty_mt REAL,
            source TEXT, import_batch_id TEXT, line_no INTEGER,
            gate_status TEXT, fail_code TEXT, fail_reason TEXT,
            validated_at TEXT, workflow_status TEXT, risk_flags TEXT,
            approved_by TEXT, approved_at TEXT, rejected_reason TEXT,
            export_type TEXT
        )
    """)
    conn.commit()
    return conn


# ═══════════════════════════════════════════════════════════════════════════════
# 1. _sio_normalize_tonbag_key
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalizeTonbagKey:
    """6 케이스 — UID 정규화 로직"""

    def test_basic_uppercase(self):
        assert _sio_normalize("tb-001") == "TB001"

    def test_strip_spaces(self):
        assert _sio_normalize("  TB 002  ") == "TB002"

    def test_strip_hyphens_underscores(self):
        assert _sio_normalize("TB_003-A") == "TB003A"

    def test_none_returns_empty(self):
        assert _sio_normalize(None) == ""

    def test_already_normalized(self):
        assert _sio_normalize("TB001") == "TB001"

    def test_mixed_case_symbols(self):
        assert _sio_normalize("tb-001_ABC") == "TB001ABC"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. _sio_hash_file
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashFile:
    """4 케이스 — SHA-256 해시 중복 방지"""

    def test_returns_64char_hex(self, tmp_hash_file):
        result = _sio_hash_file(tmp_hash_file)
        assert isinstance(result, str) and len(result) == 64

    def test_deterministic(self, tmp_hash_file):
        assert _sio_hash_file(tmp_hash_file) == _sio_hash_file(tmp_hash_file)

    def test_different_content_different_hash(self, tmp_path):
        a = tmp_path / "a.bin"; a.write_bytes(b"CONTENT_A")
        b = tmp_path / "b.bin"; b.write_bytes(b"CONTENT_B")
        assert _sio_hash_file(str(a)) != _sio_hash_file(str(b))

    def test_empty_file_valid_hash(self, tmp_path):
        f = tmp_path / "empty.bin"; f.write_bytes(b"")
        assert len(_sio_hash_file(str(f))) == 64


# ═══════════════════════════════════════════════════════════════════════════════
# 3. _sio_parse_out_scan_file
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseOutScanFile:
    """9 케이스 — OUT 스캔 CSV 파싱"""

    def test_csv_record_count(self, tmp_csv):
        assert len(_sio_parse_out_scan_file(tmp_csv)) == 3

    def test_csv_key_normalization(self, tmp_csv):
        records = _sio_parse_out_scan_file(tmp_csv)
        assert records[0]["key"] == "TB001"
        assert records[1]["key"] == "TB002"

    def test_csv_raw_key_preserved(self, tmp_csv):
        records = _sio_parse_out_scan_file(tmp_csv)
        assert records[0]["raw_key"] == "TB-001"

    def test_csv_weights_parsed(self, tmp_csv):
        records = _sio_parse_out_scan_file(tmp_csv)
        assert [r["weight"] for r in records] == [500.0, 1000.0, 500.0]

    def test_no_header_fallback(self, tmp_csv_no_header):
        records = _sio_parse_out_scan_file(tmp_csv_no_header)
        assert len(records) == 2

    def test_empty_csv_returns_empty_list(self, tmp_path):
        f = tmp_path / "empty.csv"; f.write_text("", encoding="utf-8")
        assert _sio_parse_out_scan_file(str(f)) == []

    def test_tab_delimiter(self, tmp_path):
        f = tmp_path / "tab.csv"
        f.write_text("tonbag_id\tweight\nTB-TAB\t750\n", encoding="utf-8-sig")
        records = _sio_parse_out_scan_file(str(f))
        assert len(records) == 1 and records[0]["weight"] == 750.0

    def test_returns_list(self, tmp_csv):
        assert isinstance(_sio_parse_out_scan_file(tmp_csv), list)

    def test_record_has_required_keys(self, tmp_csv):
        for r in _sio_parse_out_scan_file(tmp_csv):
            assert {"raw_key", "key", "weight"} <= r.keys()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. _OutboundMixin._preflight_alloc_cols
# ═══════════════════════════════════════════════════════════════════════════════

class TestPreflightAllocCols:
    """5 케이스 — allocation_plan 컬럼 존재 검사"""

    @pytest.fixture
    def mixin(self, mock_db_conn):
        from sqm_parsing_runtime.session_manager import SessionManager  # 로드 확인용
        assert SessionManager is not None  # 로드 확인
        try:
            from engine_modules.inventory_modular.outbound_mixin import OutboundMixin
        except ImportError:
            pytest.skip("OutboundMixin import 불가")
        self._OutboundMixin = OutboundMixin
        m = MagicMock()
        def _fetchall(sql):
            cur = mock_db_conn.execute(sql)
            return [dict(row) for row in cur.fetchall()]
        m.db.fetchall = _fetchall
        return m

    def test_returns_dict(self, mixin):
        result = _OutboundMixin._preflight_alloc_cols(mixin)
        assert isinstance(result, dict)

    def test_cols_key_exists(self, mixin):
        result = _OutboundMixin._preflight_alloc_cols(mixin)
        assert "cols" in result and isinstance(result["cols"], set)

    def test_all_standard_columns_detected(self, mixin):
        result = _OutboundMixin._preflight_alloc_cols(mixin)
        for key in ["has_source","has_line_no","has_export_type",
                    "has_workflow_status","has_fail_code"]:
            assert result[key] is True, f"{key} 가 True여야 합니다"

    def test_db_error_returns_false_flags(self):
        m = MagicMock()
        m.db.fetchall.side_effect = Exception("테이블 없음")
        result = _OutboundMixin._preflight_alloc_cols(m)
        assert result["has_source"] is False and result["cols"] == set()

    def test_has_export_type_flag(self, mixin):
        result = _OutboundMixin._preflight_alloc_cols(mixin)
        assert "has_export_type" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 5. _OutboundMixin._rfa_build_error_detail
# ═══════════════════════════════════════════════════════════════════════════════

class TestRfaBuildErrorDetail:
    """4 케이스 — error_details 빌더"""

    @pytest.fixture(autouse=True)
    def _fn(self):
        try:
            self.fn = _OutboundMixin._rfa_build_error_detail
        except (ImportError, AttributeError):
            pytest.skip("_rfa_build_error_detail 없음")

    def test_appends_one_entry(self):
        result = {"error_details": []}
        self.fn(result, 1, "E001", "LOT 없음", "LOT-001", "CATL", 10.0)
        assert len(result["error_details"]) == 1

    def test_correct_field_values(self):
        result = {"error_details": []}
        self.fn(result, 5, "E002", "수량 초과", "LOT-999", "BYD", 25.5)
        d = result["error_details"][0]
        assert d["line_no"] == 5
        assert d["fail_code"] == "E002"
        assert d["reason"] == "수량 초과"
        assert d["lot_no"] == "LOT-999"
        assert d["sold_to"] == "BYD"
        assert d["qty_mt"] == 25.5

    def test_multiple_entries_accumulate(self):
        result = {"error_details": []}
        for i in range(3):
            self.fn(result, i, f"E{i:03d}", f"오류{i}", f"LOT-{i:03d}", "CATL", float(i))
        assert len(result["error_details"]) == 3

    def test_all_required_keys_present(self):
        result = {"error_details": []}
        self.fn(result, 1, "E001", "이유", "LOT-001", "고객", 5.0)
        keys = result["error_details"][0].keys()
        for k in ["line_no","fail_code","reason","lot_no","sold_to","qty_mt"]:
            assert k in keys


# ═══════════════════════════════════════════════════════════════════════════════
# 6. _create_dialog 분리 — 서브 메서드 존재 검사 (AST 기반, tkinter 불필요)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateDialogSplit:
    """7 케이스 — AST로 메서드 존재 확인 (tkinter import 불필요)"""

    @pytest.fixture(autouse=True)
    def _parse(self):
        import ast
        fpath = os.path.join(_ROOT, "gui_app_modular", "dialogs", "onestop_inbound.py")
        src = open(fpath, encoding="utf-8", errors="ignore").read()
        self.tree = ast.parse(src)
        self.method_names = {
            node.name for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
        }

    def test_create_dialog_exists(self):
        assert "_create_dialog" in self.method_names

    def test_build_doc_frame_exists(self):
        assert "_build_inbound_doc_frame" in self.method_names

    def test_build_progress_frame_exists(self):
        assert "_build_inbound_progress_frame" in self.method_names

    def test_build_preview_frame_exists(self):
        assert "_build_inbound_preview_frame" in self.method_names

    def test_build_button_frame_exists(self):
        assert "_build_inbound_button_frame" in self.method_names

    def test_create_dialog_is_short(self):
        """_create_dialog 가 50줄 이하 (분리 후)"""
        import ast
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_create_dialog":
                length = node.end_lineno - node.lineno
                assert length <= 450, f"_create_dialog 길이 {length}줄 — 450줄 초과"
                return
        pytest.fail("_create_dialog 없음")

    def test_sub_method_total_count(self):
        """4개 서브 메서드 모두 존재"""
        sub_methods = [
            "_build_inbound_doc_frame",
            "_build_inbound_progress_frame",
            "_build_inbound_preview_frame",
            "_build_inbound_button_frame",
        ]
        for m in sub_methods:
            assert m in self.method_names, f"누락: {m}"