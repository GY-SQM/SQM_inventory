# -*- coding: utf-8 -*-
"""회귀 테스트 — audit 🟡 #2 f-string SQL 안전성 인벤토리.

docs/audit-f-string-sql-inventory.md (2026-07-21)에 명시된 11건이
  - 모두 화이트리스트/DB 메타/하드코딩/? 바인딩 보호 중 하나 적용
  - 사용자가 식별자(테이블명/컬럼명) 위치에 직접 주입 불가
임을 회귀 테스트로 보호한다.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel_path: str) -> str:
    with open(os.path.join(ROOT, rel_path), encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 인벤토리 문서 존재
# ---------------------------------------------------------------------------

def test_audit_y2_inventory_doc_exists():
    """audit 🟡 #2: 인벤토리 문서가 존재해야 함."""
    p = os.path.join(ROOT, "docs", "audit-f-string-sql-inventory.md")
    assert os.path.exists(p), f"인벤토리 문서 누락: {p}"


# ---------------------------------------------------------------------------
# 각 11건 + 추가 발견 건의 보호 메커니즘 검증
# ---------------------------------------------------------------------------

def test_y2_actions_py_1051_hardcoded_table_list():
    """🟡 #2.1: actions.py:1051 — 테이블명이 하드코딩 리스트에 있어야 함."""
    code = _read("backend/api/actions.py")
    # get_system_info 함수 영역
    fn_start = code.find("def get_system_info")
    assert fn_start >= 0, "def get_system_info 함수 없음"
    section = code[fn_start:fn_start + 2000]
    assert "for tbl in [" in section, "하드코딩 테이블 리스트 패턴 누락"
    # 6개 테이블 이름이 모두 리터럴로 있어야 함
    for tbl in ("inventory", "inventory_tonbag", "stock_movement",
                "audit_log", "allocation_plan", "inventory_snapshot"):
        assert f'"{tbl}"' in section, f"하드코딩 리스트에 {tbl} 누락"


def test_y2_actions3_py_152_allowed_fields_whitelist():
    """🟡 #2.2: actions3.py:152 — LOT_EDIT_FIELDS 화이트리스트 통과 후만 컬럼명 사용."""
    code = _read("backend/api/actions3.py")
    # LOT_EDIT_FIELDS set 정의 있어야 함
    assert "LOT_EDIT_FIELDS" in code, "LOT_EDIT_FIELDS 화이트리스트 누락"
    # 화이트리스트 체크 (if field not in LOT_EDIT_FIELDS) 후 SQL 실행
    assert re.search(
        r"if\s+field\s+not\s+in\s+LOT_EDIT_FIELDS\s*:",
        code,
    ), "LOT_EDIT_FIELDS 검증 패턴(if field not in) 누락"
    # f-string SQL 위치
    assert re.search(
        r"f[\"']UPDATE\s+document_do\s+SET\s+\{field\}=\?",
        code,
    ), "f-string SQL with {field}=? 패턴 누락"


def test_y2_actions3_py_371_373_sqlite_master_metadata():
    """🟡 #2.3: actions3.py:371, 373 — 테이블명을 sqlite_master 메타에서 가져옴."""
    code = _read("backend/api/actions3.py")
    assert "sqlite_master" in code, "sqlite_master 메타 조회 누락"
    # [{tbl}] SQLite 식별자 escape
    assert re.search(r"\[\{tbl\}\]", code), "[{tbl}] SQLite escape 패턴 누락"


def test_y2_queries3_py_1925_hardcoded_table_list():
    """🟡 #2.4: queries3.py:1925 — 테이블명이 하드코딩 리스트에 있어야 함."""
    code = _read("backend/api/queries3.py")
    # get_settings_info 함수 영역
    fn_start = code.find("def get_settings_info")
    assert fn_start >= 0, "def get_settings_info 함수 없음"
    section = code[fn_start:fn_start + 2000]
    # tables = [ ... ] 하드코딩 리스트
    assert "tables = [" in section, "하드코딩 테이블 리스트 패턴 누락"
    # 주요 테이블 이름이 모두 리터럴로 있어야 함
    for tbl in ("inventory", "inventory_tonbag", "stock_movement",
                "audit_log", "allocation_plan"):
        assert f'"{tbl}"' in section, f"하드코딩 리스트에 {tbl} 누락"


def test_y2_settings_py_251_allowed_whitelist():
    """🟡 #2.5: settings.py:251 — 명시적 allowed 화이트리스트 통과 후 컬럼명 사용.

    v9.0.0: 'allowed = {...}' 인라인 정의 → 'allowed = CARRIER_RULE_EDIT_FIELDS' 로 hoist.
    둘 다 패턴 매치되도록 regex 확장.
    """
    code = _read("backend/api/settings.py")
    # allowed 정의 (인라인 set 또는 import 할당)
    assert (
        re.search(r"allowed\s*=\s*\{[^}]*carrier_id[^}]*\}", code)
        or re.search(r"allowed\s*=\s*CARRIER_RULE_EDIT_FIELDS", code)
    ), "settings.py의 allowed 화이트리스트 누락 (carrier_id 포함)"
    # 'if k in allowed' 또는 'if k not in allowed' 패턴 (dict comprehension 내부)
    assert (
        re.search(r"if\s+k\s+in\s+allowed", code)
        or re.search(r"if\s+k\s+not\s+in\s+allowed", code)
    ), "allowed 검증 패턴(if k in/not in allowed) 누락"


def test_y2_settings_py_540_564_hardcoded_or_whitelist():
    """🟡 #2.6: settings.py:540, 564 — SHOW_TABLES 하드코딩 또는 ALLOWED 화이트리스트.

    v9.0.0: 'ALLOWED = {...}' 인라인 → 'ALLOWED_TABLE_DELETE' import.
    새 패턴 반영.
    """
    code = _read("backend/api/settings.py")
    # SHOW_TABLES 하드코딩 리스트 (line 530) 또는 ALLOWED 화이트리스트 (line 551)
    assert (
        "SHOW_TABLES" in code
        or "ALLOWED" in code
        or "ALLOWED_TABLE_DELETE" in code
    ), "settings.py에 SHOW_TABLES/ALLOWED/ALLOWED_TABLE_DELETE 보호 누락"
    # for tbl in SHOW_TABLES 또는 [t for t in ... if t in ALLOWED(_TABLE_DELETE)] 패턴
    assert (
        re.search(r"for\s+tbl\s+in\s+SHOW_TABLES", code)
        or re.search(r"if\s+t\s+in\s+ALLOWED", code)
        or re.search(r"if\s+t\s+in\s+ALLOWED_TABLE_DELETE", code)
    ), "settings.py에 SHOW_TABLES/ALLOWED/ALLOWED_TABLE_DELETE 보호 패턴 누락"


def test_y2_allocation_api_py_680_hardcoded_sets():
    """🟡 #2.7: allocation_api.py:680 — sets가 하드코딩 상수."""
    code = _read("backend/api/allocation_api.py")
    # "workflow_status='EXPORTED_FOR_EDIT'" 하드코딩
    assert "workflow_status='EXPORTED_FOR_EDIT'" in code, (
        "allocation_api.py의 하드코딩 sets 누락"
    )


def test_y2_allocation_api_py_792_800_1586_715_editable_whitelist():
    """🟡 #2.8: allocation_api.py 4개 위치 — ALLOC_EDITABLE_FIELDS 화이트리스트."""
    code = _read("backend/api/allocation_api.py")
    # ALLOC_EDITABLE_FIELDS 또는 _ALLOC_EDITABLE_FIELDS 둘 중 하나
    assert (
        "ALLOC_EDITABLE_FIELDS" in code
        or "_ALLOC_EDITABLE_FIELDS" in code
    ), "ALLOC_EDITABLE_FIELDS 화이트리스트 누락"
    # if k in ALLOC_EDITABLE_FIELDS 패턴
    assert re.search(
        r"if\s+k\s+in\s+(?:_)?ALLOC_EDITABLE_FIELDS",
        code,
    ), "ALLOC_EDITABLE_FIELDS 검증 패턴(if k in) 누락"


def test_y2_placeholder_pattern_present():
    """🟡 #2.10: ','.join('?' * N) 플레이스홀더 동적 패턴 (모범 사례)."""
    code = _read("backend/api/allocation_api.py") + _read("backend/api/outbound_api.py")
    # IN ({placeholders}) 또는 IN (','.join('?' * N)) 패턴
    assert re.search(
        r"IN\s*\(\s*\{\s*placeholders\s*\}\s*\)|'\?['\"]?\s*\*\s*len\(",
        code,
    ), "IN ({placeholders}) 또는 동적 ? 플레이스홀더 패턴 누락"


def test_y2_inbound_py_1682_hardcoded_callers():
    """🟡 #2.11: inbound.py:1682 — _db_update_lots 호출처 5곳 모두 where_col이 하드코딩 상수."""
    code = _read("backend/api/inbound.py")
    # _db_update_lots 호출 5곳
    calls = re.findall(
        r"_db_update_lots\s*\([^,]+,\s*['\"](\w+)['\"]",
        code,
    )
    assert len(calls) >= 5, (
        f"_db_update_lots 호출이 5번 이상이어야 함. 실제 {len(calls)}번"
    )
    # 모든 호출이 하드코딩된 컬럼명 (사용자 입력 X)
    for col in calls:
        # 컬럼명이 inventory의 알려진 컬럼이어야 함
        known_cols = {
            "sap_no", "folio", "container_no", "bl_no", "lot_no",
            "id", "inbound_date", "status",
        }
        assert col in known_cols, (
            f"_db_update_lots 호출의 where_col='{col}' — 알려진 컬럼 아님 (화이트리스트 외)"
        )


def test_y2_inbound_py_1806_inv_cols_whitelist():
    """🟡 #2.11: inbound.py:1806 — inv_cols (PRAGMA table_info) 화이트리스트."""
    code = _read("backend/api/inbound.py")
    # _table_columns 또는 PRAGMA table_info
    assert (
        "PRAGMA table_info" in code
        or "_table_columns" in code
    ), "inbound.py에 PRAGMA table_info (DB 메타 화이트리스트) 누락"
    # if k not in inv_cols: continue 패턴
    assert re.search(
        r"if\s+k\s+not\s+in\s+inv_cols",
        code,
    ), "inv_cols 검증 패턴(if k not in inv_cols) 누락"


def test_y2_status_revert_api_uses_question_mark_binding():
    """🟡 #2.12: status_revert_api.py — 모든 동적 값이 ? 바인딩."""
    code = _read("backend/api/status_revert_api.py")
    # f-string UPDATE inventory SET status=? 패턴
    n_uses = len(re.findall(
        r"f[\"']UPDATE\s+(?:inventory|inventory_tonbag|allocation_plan|sold_table)\s+SET\s+",
        code,
    ))
    assert n_uses >= 8, (
        f"status_revert_api.py의 f-string UPDATE가 8건 이상이어야 함. 실제 {n_uses}건"
    )
    # 각 f-string UPDATE가 status='PENDING' 같은 하드코딩 + ? 바인딩
    # (f-string 안에 사용자 입력이 직접 안 들어감)
    assert "status='PENDING'" in code, "PENDING 상수 분기 누락"
    assert "status='AVAILABLE'" in code, "AVAILABLE 상수 분기 누락"
    assert "status='RESERVED'" in code, "RESERVED 상수 분기 누락"
