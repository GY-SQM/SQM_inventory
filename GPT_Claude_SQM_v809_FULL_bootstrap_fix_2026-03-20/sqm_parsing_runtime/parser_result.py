# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.parser_result (v7.7.0)
==========================================
문서 파싱 결과 컨테이너.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ParserResult:
    """단일 문서 파싱 결과."""
    doc_type: str = ""           # PACKING_LIST / INVOICE / BL / DO
    success: bool = False
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    raw_response: str = ""
    carrier_id: str = ""
    page_count: int = 0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def __bool__(self) -> bool:
        return self.success
