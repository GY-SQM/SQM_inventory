# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 재고 엔진 (Facade)
==========================================

v3.0 - 레거시 버전 사용 (호환성 보장)

★★★ 실제 구현: legacy/inventory_legacy.py ★★★

모듈화 버전(inventory_modular/)은 SQLAlchemy를 사용하여
현재 테스트와 호환되지 않습니다. 
안정성을 위해 레거시 버전을 사용합니다.

기존 코드:
    from engine_modules.inventory import SQMInventoryEngine
    engine = SQMInventoryEngine(db_path)
    
위 코드가 그대로 동작합니다.
"""

import logging
import sys
import os

logger = logging.getLogger(__name__)

# legacy 폴더를 path에 추가
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LEGACY = os.path.join(_ROOT, 'legacy')
if _LEGACY not in sys.path:
    sys.path.insert(0, _LEGACY)

# ★★★ v3.0: 모듈화 버전 사용 (레거시 폴더 없음) ★★★
try:
    from engine_modules.inventory_modular import SQMInventoryEngine
    logger.debug("[v3.0] inventory.py: 모듈화 버전 사용")
except ImportError as e:
    logger.error(f"[v3.0] 모듈화 버전 import 실패: {e}")
    SQMInventoryEngine = None

# 모듈화 버전도 export (선택적 사용)
try:
    from engine_modules.inventory_modular import (
        SQMInventoryEngineV3,
        InboundMixin,
        OutboundMixin,
        QueryMixin,
        ExportMixin,
        ShipmentMixin,
        TonbagMixin,
        ReturnMixin,
        ImportMixin,
        PreflightMixin,
        CRUDMixin,
        safe_parse_date,
        safe_parse_float,
        safe_parse_int,
        dict_to_packing_data,
        PackingDataAdapter,
        format_lot_no,
        format_weight,
        normalize_column_name,
    )
except ImportError as e:
    logger.warning(f"[v3.0] 모듈화 버전 import 실패: {e}")
    SQMInventoryEngineV3 = None

# pandas 플래그 (호환성)
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

# validators 플래그 (호환성)
try:
    HAS_VALIDATORS = True
except ImportError:
    HAS_VALIDATORS = False

__all__ = [
    # Main engine (레거시)
    'SQMInventoryEngine',
    
    # Modular version (선택적)
    'SQMInventoryEngineV3',
    
    # Flags
    'HAS_PANDAS',
    'HAS_VALIDATORS',
]

try:
    from version import __version__
except ImportError:
    __version__ = "0.0.0"  # S2-3: version.py 누락 시 fallback
    import logging as _vlog
    _vlog.getLogger(__name__).warning("[버전] version.py 로드 실패 → fallback 0.0.0")
