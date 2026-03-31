# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.pattern_registry (v7.0.0)
==============================================
15개 필드 패턴 레지스트리 (Invoice/PL/BL/DO 전체 커버)
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PatternProfile:
    field_name: str
    patterns: List[str] = field(default_factory=list)
    doc_types: List[str] = field(default_factory=list)
    required: bool = False
    transform: Optional[str] = None  # "float" | "date" | "upper" | None

    def match(self, text: str) -> Optional[str]:
        for pat in self.patterns:
            m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
            if m:
                return m.group(1).strip() if m.lastindex else m.group(0).strip()
        return None


class PatternRegistry:
    def __init__(self) -> None:
        self._profiles: Dict[str, PatternProfile] = {}

    def register(self, profile: PatternProfile) -> None:
        self._profiles[profile.field_name] = profile

    def get(self, field_name: str) -> Optional[PatternProfile]:
        return self._profiles.get(field_name)

    def get_for_doc_type(self, doc_type: str) -> List[PatternProfile]:
        return [p for p in self._profiles.values()
                if not p.doc_types or doc_type in p.doc_types]

    def all_field_names(self) -> List[str]:
        return list(self._profiles.keys())

    def __len__(self) -> int:
        return len(self._profiles)


# ─── 기본 레지스트리 (15개 필드) ─────────────────────────────────────────────
DEFAULT_PATTERN_REGISTRY = PatternRegistry()

# 1. LOT 번호
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='lot_no',
    patterns=[
        r'LOT\s*(?:NO\.?|NUMBER|번호)?\s*[:\-]?\s*(\d{10})',
        r'\b(112\d{7})\b',
    ],
    required=True
))

# 2. B/L 번호
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='bl_no',
    patterns=[
        r'B/?L\s*(?:NO\.?|NUMBER)?\s*[:\-]?\s*([A-Z]{3,6}\d{7,15})',
        r'BILL\s+OF\s+LADING\s*(?:NO\.?)?\s*[:\-]?\s*([A-Z0-9]{8,20})',
    ],
    doc_types=['BL', 'DO', 'INVOICE'],
    required=True
))

# 3. Vessel (선박명)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='vessel',
    patterns=[
        r'VESSEL\s*(?:NAME)?\s*[:\-]?\s*([A-Z][A-Z0-9 \-]{2,30}?)(?:\s*VOY|\s*\n)',
        r'M/V\s+([A-Z][A-Z0-9 \-]{2,30})',
    ],
    doc_types=['BL', 'DO'],
    transform='upper'
))

# 4. Voyage (항차)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='voyage',
    patterns=[
        r'VOY(?:AGE)?\s*(?:NO\.?)?\s*[:\-]?\s*([A-Z0-9\-]{3,12})',
        r'V\.\s*([A-Z0-9\-]{3,12})',
    ],
    doc_types=['BL', 'DO']
))

# 5. Port of Loading (선적항)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='port_of_loading',
    patterns=[
        r'PORT\s+OF\s+LOADING\s*[:\-]?\s*([A-Z][A-Z ]{2,30})',
        r'P(?:ORT)?\.?\s*O(?:F)?\.?\s*L(?:OADING)?\s*[:\-]?\s*([A-Z][A-Z ]{2,25})',
        r'FROM\s*[:\-]?\s*([A-Z]{3,30},?\s*[A-Z]{2,30})',
    ],
    doc_types=['BL', 'DO']
))

# 6. Port of Discharge (양하항)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='port_of_discharge',
    patterns=[
        r'PORT\s+OF\s+DISCHARGE\s*[:\-]?\s*([A-Z][A-Z ]{2,30})',
        r'DISCHARGE\s+PORT\s*[:\-]?\s*([A-Z][A-Z ]{2,30})',
        r'TO\s*[:\-]?\s*([A-Z]{3,30},?\s*[A-Z]{2,30})',
    ],
    doc_types=['BL', 'DO']
))

# 7. Container No (컨테이너 번호)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='container_no',
    patterns=[
        r'\b([A-Z]{4}\d{7})\b',
        r'CONTAINER\s*(?:NO\.?)?\s*[:\-]?\s*([A-Z]{4}\d{7})',
    ],
    doc_types=['BL', 'DO', 'PACKING_LIST'],
    transform='upper'
))

# 8. Seal No (씰 번호)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='seal_no',
    patterns=[
        r'SEAL\s*(?:NO\.?|NUMBER)?\s*[:\-]?\s*([A-Z0-9]{5,15})',
    ],
    doc_types=['BL', 'PACKING_LIST']
))

# 9. 총 중량 (Gross Weight / Total Weight)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='gross_weight',
    patterns=[
        r'GROSS\s*WEIGHT\s*[:\-]?\s*([\d,\.]+)\s*(?:KGS?|MT|METRIC\s*TON)',
        r'TOTAL\s*WEIGHT\s*[:\-]?\s*([\d,\.]+)\s*(?:KGS?|MT)',
        r'GW\s*[:\-]?\s*([\d,\.]+)',
    ],
    transform='float'
))

# 10. 순 중량 (Net Weight)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='net_weight',
    patterns=[
        r'NET\s*WEIGHT\s*[:\-]?\s*([\d,\.]+)\s*(?:KGS?|MT)',
        r'NW\s*[:\-]?\s*([\d,\.]+)',
    ],
    transform='float'
))

# 11. 수량 / 패키지 수 (Packages / Bags)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='packages',
    patterns=[
        r'(\d+)\s*(?:BAGS?|PKGS?|PACKAGES?|PALLETS?|톤백)',
        r'QUANTITY\s*[:\-]?\s*(\d+)',
        r'QTY\s*[:\-]?\s*(\d+)',
    ],
    transform='float'
))

# 12. Invoice No (인보이스 번호)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='invoice_no',
    patterns=[
        r'INVOICE\s*(?:NO\.?|NUMBER)?\s*[:\-]?\s*([A-Z0-9\-]{5,20})',
        r'INV\.?\s*(?:NO\.?)?\s*[:\-]?\s*([A-Z0-9\-]{5,20})',
    ],
    doc_types=['INVOICE'],
    required=True
))

# 13. Shipper / 화주
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='shipper',
    patterns=[
        r'SHIPPER\s*[:\-]?\s*([A-Z][A-Z0-9 &\.,]{3,50})',
        r'SELLER\s*[:\-]?\s*([A-Z][A-Z0-9 &\.,]{3,50})',
    ],
    doc_types=['BL', 'INVOICE']
))

# 14. Consignee / 수하인
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='consignee',
    patterns=[
        r'CONSIGNEE\s*[:\-]?\s*([A-Z][A-Z0-9 &\.,]{3,50})',
        r'BUYER\s*[:\-]?\s*([A-Z][A-Z0-9 &\.,]{3,50})',
    ],
    doc_types=['BL', 'INVOICE', 'DO']
))

# 15. ETD / ETA (출항/입항 예정일)
DEFAULT_PATTERN_REGISTRY.register(PatternProfile(
    field_name='etd',
    patterns=[
        r'ETD\s*[:\-]?\s*(\d{4}[-/]\d{2}[-/]\d{2})',
        r'DATE\s+OF\s+DEPARTURE\s*[:\-]?\s*(\d{4}[-/]\d{2}[-/]\d{2})',
        r'SAILED\s*[:\-]?\s*(\d{4}[-/]\d{2}[-/]\d{2})',
    ],
    transform='date'
))

assert len(DEFAULT_PATTERN_REGISTRY) == 15, f"패턴 수 오류: {len(DEFAULT_PATTERN_REGISTRY)}"
