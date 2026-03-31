# -*- coding: utf-8 -*-
"""
sqm_parsing_runtime.session_manager (v7.7.0)
===========================================
문서 파싱 세션 관리 (단일 입고 건 = 여러 문서의 묶음)
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class DocumentSession:
    """단일 입고 건의 파싱 세션."""
    session_id: str = ""
    bl_no: str = ""
    sap_no: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    documents: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_document(self, doc_type: str, result: Any) -> None:
        self.documents[doc_type] = result

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        logger.error(f"[Session {self.session_id}] {msg}")

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        logger.warning(f"[Session {self.session_id}] {msg}")

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class SessionManager:
    """파싱 세션 생성·관리."""

    def __init__(self) -> None:
        self._sessions: Dict[str, DocumentSession] = {}

    def create_session(self, bl_no: str = "", sap_no: str = "") -> DocumentSession:
        import uuid
        sid = str(uuid.uuid4())[:8]
        s = DocumentSession(session_id=sid, bl_no=bl_no, sap_no=sap_no)
        self._sessions[sid] = s
        logger.debug(f"[SessionManager] 세션 생성: {sid}")
        return s

    def get_session(self, session_id: str) -> Optional[DocumentSession]:
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        logger.debug(f"[SessionManager] 세션 종료: {session_id}")
