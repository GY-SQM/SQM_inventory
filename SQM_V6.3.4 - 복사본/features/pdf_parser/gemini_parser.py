"""
SQM 재고관리 시스템 - Gemini AI 파서 Compatibility Shim

이 모듈은 하위 호환을 위해 유지되며, 실제 구현은
`features.ai.gemini_parser`를 단일 소스로 사용합니다.
"""

# Single Source of Truth
from features.ai.gemini_parser import *  # noqa: F401,F403
from features.ai.gemini_parser import GeminiDocumentParser  # noqa: F401

__all__ = ["GeminiDocumentParser"]

