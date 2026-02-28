# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 — 비즈니스 상수 (v5.6.8)
==============================================

모든 하드코딩 상수를 이 파일에서 관리합니다.
값을 변경하면 시스템 전체에 자동 적용됩니다.

작성자: Ruby (남기동)
"""

# ═══════════════════════════════════════════════════════
# 1. 재고 상태 (inventory.status / inventory_tonbag.status)
# 출고 흐름: AVAILABLE → RESERVED → PICKED → SOLD / 전량 시 DEPLETED
# ═══════════════════════════════════════════════════════
STATUS_AVAILABLE = 'AVAILABLE'    # 입고 완료, 출고 가능
STATUS_RESERVED = 'RESERVED'      # v5.9.3: Allocation 예약 (톤백 지정 완료, 출고 대기)
STATUS_PICKED = 'PICKED'          # 출고 실행 (피킹 완료)
STATUS_SOLD = 'SOLD'              # 출고 확정 (판매 완료)
STATUS_DEPLETED = 'DEPLETED'      # 전량 출고 완료
STATUS_RETURNED = 'RETURNED'      # 반품

# 출고 상태 (outbound.status)
OUTBOUND_PENDING = 'PENDING'      # 출고 대기
OUTBOUND_CONFIRMED = 'CONFIRMED'  # 출고 확정
OUTBOUND_CANCELLED = 'CANCELLED'  # 출고 취소

# 이동 유형 (stock_movement.movement_type)
MOVEMENT_INBOUND = 'INBOUND'
MOVEMENT_OUTBOUND = 'OUTBOUND'
MOVEMENT_RETURN = 'RETURN'
MOVEMENT_ADJUSTMENT = 'ADJUSTMENT'
MOVEMENT_QUICK_OUTBOUND = 'QUICK_OUTBOUND'
MOVEMENT_SOLD = 'SOLD'
MOVEMENT_CANCEL_OUTBOUND = 'CANCEL_OUTBOUND'
MOVEMENT_RESERVED = 'RESERVED'                # v6.12.1: Allocation 예약
MOVEMENT_CANCEL_RESERVE = 'CANCEL_RESERVE'    # v6.12.1: 예약 취소
MOVEMENT_REVERT_PICKED = 'REVERT_PICKED'      # v6.12.1: PICKED→RESERVED 되돌림
MOVEMENT_REVERT_SOLD = 'REVERT_SOLD'          # v6.12.1: SOLD→PICKED 되돌림
MOVEMENT_RELOCATE = 'RELOCATE'                # v7.0.1: 톤백 위치 이동
MOVEMENT_DO_UPDATE = 'DO_UPDATE'              # D/O 후속 연결 UPDATE 이력
MOVEMENT_INVOICE_UPDATE = 'INVOICE_UPDATE'    # Invoice 후속 연결 UPDATE 이력
MOVEMENT_BL_UPDATE = 'BL_UPDATE'              # B/L 후속 연결 UPDATE 이력
MOVEMENT_RETURN_DOC_REVIEW = 'RETURN_DOC_REVIEW'  # 반품 후 문서 연계 점검 필요 이력

# ═══════════════════════════════════════════════════════
# 2. 창고
# ═══════════════════════════════════════════════════════
DEFAULT_WAREHOUSE = '광양'
WAREHOUSE_CODE = 'GY'

# ═══════════════════════════════════════════════════════
# 3. SQM 대원칙 — 무게/톤백
# ═══════════════════════════════════════════════════════
SAMPLE_WEIGHT_KG = 1.0            # 샘플 1개 = 1kg (고정)
TONBAG_WEIGHT_500 = 500           # 500kg 톤백
TONBAG_WEIGHT_1000 = 1000         # 1000kg 톤백
DEFAULT_TONBAG_WEIGHT = 500       # fallback 기본 단가 (DB 조회 실패 시)
DEFAULT_TONBAG_COUNT = 10         # 기본 톤백 수


# ═══════════════════════════════════════════════════════
# v6.12 Addon-G: 톤백 단가 DB 조회 유틸 (500/1000kg 동적 대응)
# ═══════════════════════════════════════════════════════
def get_tonbag_unit_weight(db, lot_no: str) -> float:
    """
    해당 LOT의 실제 톤백 단가(kg)를 DB에서 조회.
    일반 톤백(is_sample=0)의 weight를 조회하여 반환.
    조회 실패 시 DEFAULT_TONBAG_WEIGHT(500) 반환.

    사용처: 출고/배정/반품에서 톤백 개수 추정 시 500 하드코딩 대신 호출.
    """
    if db is None or not lot_no:
        return DEFAULT_TONBAG_WEIGHT
    try:
        row = db.fetchone(
            "SELECT weight FROM inventory_tonbag "
            "WHERE lot_no = ? AND COALESCE(is_sample, 0) = 0 AND weight > 0 "
            "LIMIT 1",
            (lot_no,)
        )
        if row:
            w = float(row['weight'] if isinstance(row, dict) else row[0])
            if w > 0:
                return w
    except Exception:
        pass
    return DEFAULT_TONBAG_WEIGHT


def estimate_tonbag_count(weight_kg: float, unit_weight: float = 0) -> int:
    """
    무게(kg)에서 톤백 개수 추정.
    unit_weight가 주어지면 그것으로, 아니면 DEFAULT_TONBAG_WEIGHT로 나눔.
    """
    uw = unit_weight if unit_weight > 0 else DEFAULT_TONBAG_WEIGHT
    return max(1, int(weight_kg / uw))

# ═══════════════════════════════════════════════════════
# 4. 제품 코드
# ═══════════════════════════════════════════════════════
PRODUCT_LITHIUM = 'LITHIUM CARBONATE'
PRODUCT_NICKEL = 'NICKEL SULFATE'

# ═══════════════════════════════════════════════════════
# 5. BL 접두사 (선사 코드)
# ═══════════════════════════════════════════════════════
BL_PREFIXES = ('MAEU', 'MSCU', 'HLCU', 'CMDU', 'EGLV', 'COSU', 'OOLU', 'YMLU')

# ═══════════════════════════════════════════════════════
# 6. 날짜/시간 형식
# ═══════════════════════════════════════════════════════
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# 빠른 출고 제한
QUICK_OUTBOUND_MAX_TONBAGS = 8

# ═══════════════════════════════════════════════════════
# 7. v6.12.1: 반품 사유 표준 코드
# ═══════════════════════════════════════════════════════
RETURN_REASON_CODES = [
    '품질 불량', '수량 오류', '고객 취소', '배송 문제',
    '파손/변질', '규격 불일치', '기타',
]

# 반품 알림 임계치 (N회 이상 반품 시 대시보드 경고)
RETURN_ALERT_THRESHOLD = 3

# v6.12.2: 반품 자동 승인 임계치 (이하 = 자동, 초과 = 관리자 확인 필요)
RETURN_AUTO_APPROVE_MAX_TONBAGS = 5
