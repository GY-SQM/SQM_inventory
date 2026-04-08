"""
OutboundStateRules — v8.7.1 실제 상태값 기반 상태전이 규칙
★ constants.py의 STATUS_* 상수와 일치
생성일: 2026-04-08

실제 상태 흐름 (v8.7.1):
  AVAILABLE → RESERVED → PICKED → OUTBOUND
                ↓           ↓
           CANCELLED   AVAILABLE (취소 시 복원)
"""
from enum import Enum


class TonbagStatus(Enum):
    """
    톤백(개별 단위) 상태 — constants.py의 STATUS_* 와 1:1 대응
    ★ 문자열 직접 사용 금지 — 반드시 이 Enum 사용
    """
    AVAILABLE  = "AVAILABLE"   # 출고 가능
    RESERVED   = "RESERVED"    # 예약 완료 (allocation_plan 생성됨)
    PICKED     = "PICKED"      # 피킹/스캔 완료
    OUTBOUND   = "OUTBOUND"    # 출고 확정 (v7.2.0 신규 — 구 SOLD)
    SOLD       = "SOLD"        # ⚠️ DEPRECATED — 레거시 호환만
    CANCELLED  = "CANCELLED"   # 취소
    DEPLETED   = "DEPLETED"    # 소진


class LotStatus(Enum):
    """
    LOT(재고 묶음) 상태
    """
    AVAILABLE  = "AVAILABLE"
    PARTIAL    = "PARTIAL"     # 일부 출고됨
    RESERVED   = "RESERVED"
    PICKED     = "PICKED"
    OUTBOUND   = "OUTBOUND"
    SOLD       = "SOLD"        # 레거시
    DEPLETED   = "DEPLETED"


# ================================================================
# 톤백 상태전이 허용 맵
# key: 현재 상태 / value: 전이 가능한 다음 상태 목록
# ================================================================
TONBAG_TRANSITIONS = {
    TonbagStatus.AVAILABLE:  [TonbagStatus.RESERVED],
    TonbagStatus.RESERVED:   [TonbagStatus.PICKED, TonbagStatus.AVAILABLE, TonbagStatus.CANCELLED],
    TonbagStatus.PICKED:     [TonbagStatus.OUTBOUND, TonbagStatus.AVAILABLE, TonbagStatus.RESERVED],
    TonbagStatus.OUTBOUND:   [],          # 최종 상태
    TonbagStatus.SOLD:       [],          # 레거시 최종 상태
    TonbagStatus.CANCELLED:  [],          # 최종 상태
    TonbagStatus.DEPLETED:   [],          # 최종 상태
}

# ================================================================
# 메서드 → 상태전이 매핑
# ================================================================
METHOD_TRANSITIONS = {
    "reserve_from_allocation": ("AVAILABLE",  "RESERVED"),
    "execute_reserved":        ("RESERVED",   "PICKED"),
    "confirm_outbound":        ("PICKED",     "OUTBOUND"),
    "cancel_reservation":      ("RESERVED",   "AVAILABLE"),
    "cancel_outbound_tonbag":  ("PICKED",     "AVAILABLE"),
    "revert_picked_to_reserved": ("PICKED",   "RESERVED"),
    "revert_sold_to_picked":   ("OUTBOUND",   "PICKED"),
}


class OutboundStateRules:
    """
    v8.7.1 실제 상태전이 유효성 검사 클래스
    """

    @staticmethod
    def can_transition(current: str, next_state: str) -> bool:
        """상태전이 가능 여부 — True/False"""
        try:
            cur = TonbagStatus(current)
            nxt = TonbagStatus(next_state)
            return nxt in TONBAG_TRANSITIONS.get(cur, [])
        except ValueError:
            return False

    @staticmethod
    def validate_transition(current: str, next_state: str) -> dict:
        """
        상태전이 검증 — 상세 결과
        Returns: {"ok": bool, "error": str or None}
        """
        try:
            cur = TonbagStatus(current)
            nxt = TonbagStatus(next_state)
        except ValueError as e:
            return {"ok": False, "error": f"알 수 없는 상태값: {e}"}

        allowed = TONBAG_TRANSITIONS.get(cur, [])
        if nxt in allowed:
            return {"ok": True, "error": None}

        allowed_str = [s.value for s in allowed]
        return {
            "ok": False,
            "error": (
                f"상태전이 불가: {current} → {next_state}. "
                f"허용: {allowed_str if allowed_str else '없음(최종상태)'}"
            )
        }

    @staticmethod
    def is_final(current: str) -> bool:
        """최종 상태(OUTBOUND/SOLD/CANCELLED/DEPLETED) 여부"""
        try:
            cur = TonbagStatus(current)
            return TONBAG_TRANSITIONS.get(cur) == []
        except ValueError:
            return False

    @staticmethod
    def is_sold_compatible(current: str) -> bool:
        """
        SOLD 레거시 호환 확인
        OUTBOUND 또는 SOLD 둘 다 '출고완료'로 처리
        """
        return current in (TonbagStatus.OUTBOUND.value, TonbagStatus.SOLD.value)

    @staticmethod
    def get_allowed_next(current: str) -> list:
        """현재 상태에서 전이 가능한 다음 상태 목록"""
        try:
            cur = TonbagStatus(current)
            return [s.value for s in TONBAG_TRANSITIONS.get(cur, [])]
        except ValueError:
            return []

    @staticmethod
    def get_method_for_transition(current: str, next_state: str) -> str:
        """
        특정 상태전이에 해당하는 메서드명 반환
        예: ("AVAILABLE", "RESERVED") → "reserve_from_allocation"
        """
        for method, (frm, to) in METHOD_TRANSITIONS.items():
            if frm == current and to == next_state:
                return method
        return ""
