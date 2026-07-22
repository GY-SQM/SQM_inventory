# -*- coding: utf-8 -*-
"""
core/db_allowed.py
==================
SQM v9.0.0 — 중앙 화이트리스트 (DB 접근 검증)
SQM v9.0.0 — 중앙 화이트리스트 (DB 접근 검증)

backend/ 11개 위치에 분산되어 있던 화이트리스트를 한 곳에 통합한다.
모든 DB 접근(테이블, 컬럼, 상태, operation)은 validate()를 거친다.

설계 원칙:
    1. 단일 source of truth — 화이트리스트는 여기서만 관리
    2. frozenset 사용 — 런타임 변경 불가 (immutable)
    3. validate(area, kind, value) — 단일 진입점
    4. kind 확장 가능 (table / column / status / operation / ...)

Phase 0 (2026-07-22): 스켈레톤
    - ALLOWED_TABLES / ALLOWED_STATUS 기본 세트
    - validate() 기본 구현
    - helper (all_tables, all_statuses)

Phase 1 (2026-07-22): CLOSED ✓
    - Step 1: status_revert_api.py → ALLOWED_SCOPES
    - Step 2: status_revert_api.py → REVERT_MAP + ALLOWED_STATUS.RESERVED
    - Step 3: actions3.py → LOT_EDIT_FIELDS
    - Step 4: settings.py → CARRIER_RULE_EDIT_FIELDS + ALLOWED_TABLE_DELETE
    - queries3.py: 정적 ALLOWED_* 없음 (모두 동적 set comprehension) → SKIP
      (v8.8.5 audit 인벤토리 #1.4: "queries3.py:1925 — 테이블명 동적 (DB 메타)")

Phase 2 (2026-07-22): 확장
    - Step 1: report_templates.py _ALLOWED_EXT (파일 확장자) ✓
    - Step 2: queries3.py _REPORT_FIELDS (L331 frozenset lookup)
              — L644/653/891 dynamic set (user input) 의도된 dynamic으로 skip
    - Step 3: lint 가드 (tools/lint_db_hardcoding.py) ✓
    - Step 4: 모니터링 (in-memory 카운터 + stats_detailed)
    - (예정) audit_log 영속화
"""


import io
import logging
import sqlite3
from pathlib import Path
from types import MappingProxyType
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── 화이트리스트 ────────────────────────────────────────────────

# SQM 도메인에서 사용하는 테이블 (v9.0.0 Phase 0 기본 세트)
# Phase 1 마이그레이션에서 backend/ 11개 위치의 리스트와 통합
ALLOWED_TABLES = frozenset({
    # 핵심 도메인
    "inventory",      # 메인 재고
    "lot",            # LOT 단위
    "tonbag",         # 톤백 단위
    "sold_table",     # 출고 이력
    "stock_movement", # 재고 이동 로그
    # 입고 / 출고
    "inbound_doc",    # 입고 서류
    "picking",        # 피킹
    "outbound",       # 출고
    "outbound_item",  # 출고 상세
    "picking_table",  # 피킹 테이블
    "outbound_event_log",  # 출고 이벤트 로그
    "allocation",     # LOT 할당
    "allocation_plan",    # 할당 계획
    "sales_order",    # 판매 오더
    "return_log",     # 반품
    "return_history", # 반품 이력
    # 마스터
    "product_master", # 제품 마스터
    "carriers",       # 선사 마스터
    "locations",      # 창고 위치
    "users",          # 사용자
    # 감사 / 로그
    "audit_log",          # 감사 로그
    "parsing_log",        # PL 파싱 로그 (confidence, prompt_version)
    "tonbag_move_log",    # 톤백 이동 로그
    "mig_history",        # 마이그레이션 이력
    # 설정 / 메타
    "settings",       # 시스템 설정
    "schema_version", # DB 스키마 버전
})

# 재고 상태 머신 (SQM 핵심 상태)
ALLOWED_STATUS = frozenset({
    # inventory / lot
    "AVAILABLE",        # 가용
    "RESERVED",         # 예약 (할당 확정, 출고 전)
    "PENDING",          # 입고 대기
    "PENDING_APPROVAL", # 할당 승인 대기
    "STAGED",           # 피킹 준비
    "PICKED",           # 피킹 완료
    "SOLD",             # 출고 완료
    "RETURN",           # 반품
    "SAMPLE",           # 샘플 (is_sample=1)
    "ARCHIVED",         # 보관(아카이브)
    # 보조
    "BLOCKED",          # 차단
    "HOLD",             # 보류
})

# 도메인 영역 (area) — Phase 1에서 영역별 컬럼 검증으로 확장
ALLOWED_AREAS = frozenset({
    "inventory",
    "outbound",
    "allocation",
    "inbound",
    "picking",
    "return",
    "sales_order",
    "audit",
    "parsing",
    "settings",
})

# 상태복원 API의 scope 타입 (status_revert_api.py → central allowlist 이전)
# Phase 1 Step 1: backend/api/status_revert_api.py에서 마이그레이션
ALLOWED_SCOPES = frozenset({
    "container_no",
    "bl_no",
    "lot_no",
    "lot_nos",
    "selected_lots",
    "inbound_date",
    "sale_ref",
    "customer",
    "picking_no",
    "outbound_date",
    "barcode_batch",
    "return_reason",
    "current_filter",
    "all_status",
})

# 상태 전이 맵 (status_revert_api.py → central allowlist 이전)
# Phase 1 Step 2: backend/api/status_revert_api.py에서 마이그레이션
# from_status → to_status (허용되는 되돌리기 단계)
# Note: dict (mutable) — 의도적. 상태 머신 진화 시 업데이트 가능.
#       키/값 모두 ALLOWED_STATUS 안의 값이어야 한다 (런타임 cross-check 권장).
REVERT_MAP = {
    "AVAILABLE": "PENDING",
    "RESERVED": "AVAILABLE",
    "PICKED": "RESERVED",
    "SOLD": "PICKED",
    "RETURN": "AVAILABLE",
}

# LOT 수정 가능 컬럼 화이트리스트 (actions3.py → central allowlist 이전)
# Phase 1 Step 3: backend/api/actions3.py의 ALLOWED_FIELDS 마이그레이션
# SQL Injection 방지: 사용자 입력 field 값이 이 리스트 안에 있어야만 UPDATE 허용
LOT_EDIT_FIELDS = frozenset({
    "free_time",
    "con_return",
    "warehouse_name",
    "warehouse_code",
    "arrival_date",
    "stock_date",
    "place_of_delivery",
    "final_destination",
})

# 선사 규칙(carrier_rules) 수정 가능 컬럼 (settings.py → central allowlist 이전)
# Phase 1 Step 4: backend/api/settings.py:237의 함수-로컬 `allowed` 마이그레이션
# update_carrier_rule: 사용자 입력 updates dict 안의 key만 통과
CARRIER_RULE_EDIT_FIELDS = frozenset({
    "carrier_id",
    "doc_type",
    "rule_name",
    "pattern",
    "description",
    "sample_value",
    "is_active",
})

# 개발용 table-delete 허용 테이블 (settings.py → central allowlist 이전)
# Phase 1 Step 4: backend/api/settings.py:552의 모듈-로컬 ALLOWED 마이그레이션
# 절대 허용 안 함: inventory, inventory_tonbag (실 데이터)
# invariant: ALLOWED_TABLE_DELETE ⊆ ALLOWED_TABLES
ALLOWED_TABLE_DELETE = frozenset({
    "outbound",
    "outbound_item",
    "allocation_plan",
    "picking_table",
    "sold_table",
    "return_history",
    "stock_movement",
    "audit_log",
    "parsing_log",
    "outbound_event_log",
})

# 파일 확장자 화이트리스트 (report_templates.py → central allowlist 이전)
# Phase 2 Step 1: backend/api/report_templates.py:18의 _ALLOWED_EXT 마이그레이션
# Note: file extension (DB 무관) — central allowlist 모듈에 같이 두는 이유는 단일 검증 진입점 통일
ALLOWED_FILE_EXTS = frozenset({
    ".xlsx",
    ".xls",
    ".pdf",
    ".docx",
    ".csv",
    ".html",
})

# Report fields by report_type (queries3.py → central allowlist 이전)
# Phase 2 Step 2: backend/api/queries3.py:70의 _REPORT_FIELDS 마이그레이션
# report_type → frozenset of field names (label 정보는 _REPORT_FIELDS_LABELS_BY_TYPE 참고)
# Note: 이 dict의 frozenset은 L331의 dynamic set comprehension을 명시적으로 만든 것.
#       L644/653/891의 {v.lower() for v in vals}는 dynamic (user input) — 의도된 dynamic set으로 유지.
REPORT_FIELDS_BY_TYPE = MappingProxyType({
    "outbound_report": frozenset({
        "destination", "delivery_date", "lot_no", "sap_no", "bl_no",
        "container_no", "sales_order_no", "picking_no", "sku",
        "description", "nw_mt", "gw_mt", "qty", "is_sample",
    }),
    "export_work_report": frozenset({
        "fixed_1", "description", "lot_no", "qty", "nw_mt",
        "gw_mt", "container_no", "seal_no", "size_type",
    }),
    "sales_order_dn": frozenset({
        "destination", "delivery_date", "lot_no", "sap_no", "bl_no",
        "sales_order_no", "picking_no", "sku", "description",
        "nw_mt", "gw_mt", "qty",
    }),
    "storage_confirmation": frozenset({
        "no", "part_no", "part_description", "sap_no", "lot_no",
        "in_date", "invoice_net_weight", "inspection_net_weight",
        "balance", "damage_weight", "damage_reason",
        "container_no", "bl_no",
    }),
    "sold_inventory_report": frozenset({
        "product", "sap_no", "eta_busan", "date_in_stock", "sc_rcvd",
        "days", "qty_mt", "lot_no", "wh", "salar_invoice_no",
        "sold_to", "sale_ref", "invoice_date", "picked_up_qty_mt",
        "balance", "gw", "actual_pick_up", "old", "condition", "remark",
    }),
})


# ── 단일 검증 진입점 ──────────────────────────────────────────

def validate(area: str, kind: str, value: str) -> bool:
    """
    화이트리스트 검증.

    Args:
        area:  도메인 영역 ('inventory', 'outbound', 'allocation', ...)
               현재는 kind='table'/'status' 일 때만 영향. 다른 kind는 무시.
        kind:  검증 종류
               - 'table'     : 테이블명 → ALLOWED_TABLES
               - 'status'    : 재고 상태 → ALLOWED_STATUS
               - 'area'      : 도메인 영역 → ALLOWED_AREAS
               - 그 외       : False
        value: 검증할 값 (대소문자 구분: status는 대문자, table은 소문자 컨벤션)

    Returns:
        bool: True = 화이트리스트에 있음 (허용), False = 없음 (차단)

    Examples:
        >>> validate('inventory', 'table', 'lot')
        True
        >>> validate('inventory', 'table', 'sql_injection_attempt')
        False
        >>> validate('outbound', 'status', 'AVAILABLE')
        True
        >>> validate('outbound', 'status', 'INVALID')
        False
    """
    if not isinstance(value, str) or not value:
        _record_validate(area, kind, False)
        _write_audit(area, kind, False, str(value) if value is not None else "")
        return False

    if kind == "table":
        result = value in ALLOWED_TABLES
    elif kind == "status":
        result = value in ALLOWED_STATUS
    elif kind == "area":
        result = value in ALLOWED_AREAS
    elif kind == "scope_type":
        result = value in ALLOWED_SCOPES
    elif kind == "lot_field":
        result = value in LOT_EDIT_FIELDS
    elif kind == "file_ext":
        result = value in ALLOWED_FILE_EXTS
    else:
        result = False

    _record_validate(area, kind, result)
    _write_audit(area, kind, result, value)
    return result


# ── 모니터링 (Phase 2 Step 4) ─────────────────────────────────

# in-memory 카운터 (Thread-safe with GIL)
# 형식: { (area, kind, result) : count }
#   - result: True (허용) / False (차단)
#   - 호출 패턴 추적 + 차단 시도 카운트
_VALIDATE_COUNTS: dict[tuple[str, str, bool], int] = {}


def _record_validate(area: str, kind: str, result: bool) -> None:
    """validate() 호출 카운트 (in-memory)."""
    key = (area, kind, result)
    _VALIDATE_COUNTS[key] = _VALIDATE_COUNTS.get(key, 0) + 1


# v9.0.3: audit_log DB 영속화
# 별도 테이블 db_allowed_audit — 자동 마이그레이션 (테이블 없으면 생성)
_AUDIT_TABLE_NAME = "db_allowed_audit"


def _init_audit_table(db_path: Optional[str] = None) -> None:
    """db_allowed_audit 테이블 자동 생성 (마이그레이션)."""
    path = db_path or _get_default_db_path()
    if not path:
        return  # DB 경로 없으면 skip (테스트 환경 등)
    try:
        con = sqlite3.connect(path, timeout=5)
        try:
            con.execute(f"""
                CREATE TABLE IF NOT EXISTS {_AUDIT_TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL DEFAULT (datetime('now')),
                    area TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    result INTEGER NOT NULL,
                    value TEXT
                )
            """)
            con.execute(f"CREATE INDEX IF NOT EXISTS idx_{_AUDIT_TABLE_NAME}_ts ON {_AUDIT_TABLE_NAME}(ts)")
            con.execute(f"CREATE INDEX IF NOT EXISTS idx_{_AUDIT_TABLE_NAME}_kind ON {_AUDIT_TABLE_NAME}(kind)")
            con.commit()
        finally:
            con.close()
    except sqlite3.Error as e:
        logger.warning(f"audit table init 실패 (skip): {e}")


def _get_default_db_path() -> Optional[str]:
    """기본 DB 경로 추정 (config 또는 환경변수)."""
    try:
        from config import DB_PATH  # type: ignore
        return str(DB_PATH)
    except Exception:
        return None  # 테스트 환경에서는 None


def _write_audit(area: str, kind: str, result: bool, value: str) -> None:
    """audit_log DB 기록 (silent 실패 — 모니터링은 best-effort)."""
    path = _get_default_db_path()
    if not path:
        return
    try:
        con = sqlite3.connect(path, timeout=2)
        try:
            con.execute(
                f"INSERT INTO {_AUDIT_TABLE_NAME} (area, kind, result, value) VALUES (?, ?, ?, ?)",
                (area, kind, 1 if result else 0, value[:200] if value else None),
            )
            con.commit()
        finally:
            con.close()
    except sqlite3.Error as e:
        logger.debug(f"audit write 실패 (skip): {e}")


def stats_detailed() -> dict:
    """
    validate() 호출 통계 (모니터링용).

    Returns:
        dict: {
            "total_calls": int,
            "allowed": int,
            "blocked": int,
            "by_kind": {kind: {"allowed": int, "blocked": int}, ...},
        }
    """
    total = sum(_VALIDATE_COUNTS.values())
    allowed = sum(v for (a, k, r), v in _VALIDATE_COUNTS.items() if r)
    blocked = total - allowed

    by_kind: dict[str, dict[str, int]] = {}
    for (a, k, r), v in _VALIDATE_COUNTS.items():
        if k not in by_kind:
            by_kind[k] = {"allowed": 0, "blocked": 0}
        by_kind[k]["allowed" if r else "blocked"] += v

    return {
        "total_calls": total,
        "allowed": allowed,
        "blocked": blocked,
        "by_kind": by_kind,
    }


def reset_counts() -> None:
    """카운터 초기화 (테스트용)."""
    _VALIDATE_COUNTS.clear()


# ── 헬퍼 (디버그/모니터링용) ─────────────────────────────────

def all_tables() -> list:
    """정렬된 테이블 리스트 반환."""
    return sorted(ALLOWED_TABLES)


def all_statuses() -> list:
    """정렬된 상태 리스트 반환."""
    return sorted(ALLOWED_STATUS)


def all_areas() -> list:
    """정렬된 영역 리스트 반환."""
    return sorted(ALLOWED_AREAS)


def stats() -> dict:
    """현재 화이트리스트 통계 (모니터링/디버그용)."""
    return {
        "tables": len(ALLOWED_TABLES),
        "statuses": len(ALLOWED_STATUS),
        "areas": len(ALLOWED_AREAS),
    }
