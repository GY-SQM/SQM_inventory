# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.parser_result — stub (v7.0.0)
==================================================
문서 파싱 결과 컨테이너.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ParserResult:
    """파싱 결과 컨테이너 (단일 문서)"""
    doc_type: str = ""          # "INVOICE" | "PACKING_LIST" | "BL" | "DO"
    lot_no: str = ""
    bl_no: str = ""
    vessel: str = ""
    port_of_loading: str = ""
    port_of_discharge: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""
    source_file: str = ""
    parse_success: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.parse_success and not self.errors

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.parse_success = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'doc_type': self.doc_type,
            'lot_no': self.lot_no,
            'bl_no': self.bl_no,
            'vessel': self.vessel,
            'items': self.items,
            'parse_success': self.parse_success,
            'warnings': self.warnings,
            'errors': self.errors,
        }
