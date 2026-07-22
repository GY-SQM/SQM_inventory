# -*- coding: utf-8 -*-
"""
core/db_allowed.py
==================
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

Phase 1 (예정): backend/ 11개 위치 마이그레이션
    - actions3.py, queries3.py, report_templates.py, settings.py,
      status_revert_api.py, __init__.py 등
"""


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
    "allocation",     # LOT 할당
    "sales_order",    # 판매 오더
    "return_log",     # 반품
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
        return False

    if kind == "table":
        return value in ALLOWED_TABLES
    elif kind == "status":
        return value in ALLOWED_STATUS
    elif kind == "area":
        return value in ALLOWED_AREAS
    elif kind == "scope_type":
        return value in ALLOWED_SCOPES
    elif kind == "lot_field":
        return value in LOT_EDIT_FIELDS
    return False


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
