# -*- coding: utf-8 -*-
"""
SQM 재고관리 - 파서 패키지 (v2.9.43)

★★★ Single Source of Truth ★★★
- 모든 데이터 모델: document_models.py
- 모든 파싱 로직: document_parser_v2.py
- PDF 파싱: pdf_parser.py
- 출고 할당: allocation_parser.py
- 문서 감지: document_detector.py (v2.9.43 NEW)
"""

# =============================================================================
# 문서 유형 감지 (v2.9.43 NEW)
# =============================================================================
from .document_detector import (
    DocumentDetector,
    DocumentType,
    DetectionResult,
    ScoreEntry,
    detect_document_type,
    detect_with_report,
)

# =============================================================================
# 데이터 모델 (Single Source of Truth)
# =============================================================================
from .document_models import (
    # Enum
    TransactionType,
    StockStatus,
    OutboundStatus,
    # Base
    BaseModel,
    AuditMixin,
    # Document Parsing
    ContainerInfo,
    FreeTimeInfo,
    LOTInfo,
    FreightCharge,
    # Documents
    InvoiceData,
    PackingListHeader,
    PackingListRow,
    PackingListData,
    BLData,
    DOData,
    ShipmentDocuments,
    # DB Models
    InboundRecord,
    InventoryItem,
    InventorySummary,
    StockMovement,
    OutboundItem,
    OutboundOrder,
    CustomerStock,
)

# =============================================================================
# 메인 파서 (v2.0)
# =============================================================================
from .document_parser_v2 import (
    DocumentParserV2,
    parse_document,
    parse_shipment_documents,
)

# =============================================================================
# PDF 파서
# =============================================================================
try:
    from .pdf_parser import PDFParser, parse_pdf
except ImportError:
    PDFParser = None
    parse_pdf = None

# =============================================================================
# 출고 할당 파서
# =============================================================================
try:
    from .allocation_parser import AllocationParser, AllocationData
except ImportError:
    AllocationParser = None
    AllocationData = None

# =============================================================================
# Picking List 파서 (LBM 스타일, picking_list_order/detail 매칭)
# =============================================================================
try:
    from .picking_list_parser import (
        BatchLine,
        ItemBlock,
        PickingDoc,
        decode_net_weight_kg,
        NET_WEIGHT_IMPLICIT_SAMPLE_KG,
        parse_picking_text,
        parse_picking_list_pdf,
        to_sqm_picking_order_row,
        to_sqm_picking_detail_rows,
        build_pick_plan,
    )
except ImportError:
    BatchLine = None
    ItemBlock = None
    PickingDoc = None
    decode_net_weight_kg = None
    NET_WEIGHT_IMPLICIT_SAMPLE_KG = None
    parse_picking_text = None
    parse_picking_list_pdf = None
    to_sqm_picking_order_row = None
    to_sqm_picking_detail_rows = None
    build_pick_plan = None

# Base Parser
from .base import BaseParser

# =============================================================================
# 문서 감지기 (v2.5.4)
# =============================================================================
try:
    from .document_detector import (
        DocumentDetector,
        DocumentType,
        DetectionResult,
        detect_document_type,
        detect_with_report,
    )
except ImportError:
    DocumentDetector = None
    DocumentType = None
    DetectionResult = None
    detect_document_type = None
    detect_with_report = None


# =============================================================================
# Export
# =============================================================================
__all__ = [
    # ===== 문서 감지 (v2.5.4 NEW) =====
    "DocumentDetector",
    "DocumentType",
    "DetectionResult",
    "ScoreEntry",
    "detect_document_type",
    "detect_with_report",
    # ===== 메인 (권장) =====
    # 파서
    "DocumentParserV2",
    "parse_document",
    "parse_shipment_documents",
    # PDF 파서
    "PDFParser",
    "parse_pdf",
    # 출고 할당
    "AllocationParser",
    "AllocationData",
    # Picking List (LBM)
    "BatchLine",
    "ItemBlock",
    "PickingDoc",
    "parse_picking_text",
    "parse_picking_list_pdf",
    "to_sqm_picking_order_row",
    "to_sqm_picking_detail_rows",
    "build_pick_plan",
    "decode_net_weight_kg",
    "NET_WEIGHT_IMPLICIT_SAMPLE_KG",
    # 데이터 모델
    "ContainerInfo",
    "FreeTimeInfo",
    "LOTInfo",
    "FreightCharge",
    "InvoiceData",
    "PackingListHeader",
    "PackingListRow",
    "PackingListData",
    "BLData",
    "DOData",
    "ShipmentDocuments",
    # DB 모델
    "InboundRecord",
    "InventoryItem",
    "InventorySummary",
    "StockMovement",
    "OutboundItem",
    "OutboundOrder",
    "CustomerStock",
    # Enum
    "TransactionType",
    "StockStatus",
    "OutboundStatus",
    # Base
    "BaseModel",
    "AuditMixin",
    "BaseParser",
]
