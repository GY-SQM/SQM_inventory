"""
SQM 재고관리 시스템 - Gemini AI 파서 Compatibility Shim
Ruby v2: star import 제거 → 명시적 import
"""
# Single Source of Truth — features.ai.gemini_parser
from features.ai.gemini_parser import logger, parse_euro_weight, LOTItem, PackingListResult, InvoiceResult, ContainerDetail, BLResult, DOResult, GeminiDocumentParser, get_gemini_parser, parse_with_gemini

__all__ = ['logger', 'parse_euro_weight', 'LOTItem', 'PackingListResult', 'InvoiceResult', 'ContainerDetail', 'BLResult', 'DOResult', 'GeminiDocumentParser', 'get_gemini_parser', 'parse_with_gemini']
