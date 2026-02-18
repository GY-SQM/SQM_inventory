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
DEFAULT_TONBAG_COUNT = 10         # 기본 톤백 수

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
