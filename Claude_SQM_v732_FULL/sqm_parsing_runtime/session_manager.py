# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.session_manager — stub (v7.0.0)
===================================================
문서 파싱 세션 관리 (단일 입고 건 = 여러 문서의 묶음).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from .parser_result import ParserResult


@dataclass
class DocumentSession:
    """단일 입고 세션 (Invoice + PL + BL + DO)"""
    session_id: str = ""
    lot_no: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    documents: Dict[str, ParserResult] = field(default_factory=dict)
    cross_check_passed: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_document(self, doc_type: str, result: ParserResult) -> None:
        self.documents[doc_type] = result

    def get_document(self, doc_type: str) -> Optional[ParserResult]:
        return self.documents.get(doc_type)

    @property
    def has_invoice(self) -> bool:
        return 'INVOICE' in self.documents

    @property
    def has_packing_list(self) -> bool:
        return 'PACKING_LIST' in self.documents

    @property
    def has_bl(self) -> bool:
        return 'BL' in self.documents

    @property
    def is_complete(self) -> bool:
        return self.has_invoice and self.has_packing_list and self.has_bl

    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'lot_no': self.lot_no,
            'created_at': self.created_at,
            'doc_types': list(self.documents.keys()),
            'cross_check_passed': self.cross_check_passed,
            'warnings': self.warnings,
            'errors': self.errors,
        }


class SessionManager:
    """파싱 세션 생성 및 관리"""

    def __init__(self) -> None:
        self._sessions: Dict[str, DocumentSession] = {}
        self._counter: int = 0

    def create_session(self, lot_no: str = "") -> DocumentSession:
        self._counter += 1
        session_id = f"SES{self._counter:06d}"
        session = DocumentSession(session_id=session_id, lot_no=lot_no)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[DocumentSession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[DocumentSession]:
        return list(self._sessions.values())

    def remove_session(self, session_id: str) -> bool:
        return bool(self._sessions.pop(session_id, None))

    def __len__(self) -> int:
        return len(self._sessions)
