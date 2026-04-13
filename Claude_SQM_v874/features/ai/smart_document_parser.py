# -*- coding: utf-8 -*-
"""P2-1: SmartDocumentParser — AI 기반 서류 자동 파싱"""
import os
import re
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CARRIER_KEYWORDS = {
    'HMM': ['HMM', 'HYUNDAI MERCHANT'],
    'MSC': ['MSC', 'MEDITERRANEAN SHIPPING'],
    'MAERSK': ['MAERSK'],
    'EVERGREEN': ['EVERGREEN', 'EMC'],
    'ONE': ['ONE', 'OCEAN NETWORK EXPRESS'],
    'COSCO': ['COSCO', 'COSCOSHIPPING'],
    'ZIM': ['ZIM'],
    'YANGMING': ['YANG MING', 'YML'],
    'HAPAG': ['HAPAG', 'HAPAG-LLOYD'],
    'PIL': ['PIL', 'PACIFIC INTERNATIONAL'],
    'CMA': ['CMA CGM', 'CMA-CGM'],
    'WANHAI': ['WAN HAI', 'WANHAI'],
}

class SmartDocumentParser:
    """PDF/이미지 서류를 AI 또는 템플릿으로 자동 파싱"""

    def __init__(self, db_path=None):
        self.db_path = db_path

    def parse_document(self, file_path, doc_type='BL'):
        """메인 파싱 엔트리포인트"""
        raw_text = self._extract_text(file_path)
        if not raw_text:
            return {'success': False, 'error': '텍스트 추출 실패', 'parse_method': 'FAILED'}

        carrier = self.detect_carrier(raw_text)
        template = self._find_template(carrier, doc_type)

        if template:
            result = self._parse_with_template(raw_text, template)
            result['parse_method'] = 'TEMPLATE'
            result['carrier'] = carrier
            result['is_new_carrier'] = False
            logger.info(f"템플릿 파싱 성공: {carrier}/{doc_type}")
        else:
            result = self._parse_with_ai(file_path, doc_type, raw_text)
            result['parse_method'] = 'AI'
            result['carrier'] = carrier or 'UNKNOWN'
            result['is_new_carrier'] = True
            logger.info(f"AI 파싱: {carrier or 'UNKNOWN'}/{doc_type}")

        result['success'] = True
        result['doc_type'] = doc_type
        return result

    def detect_carrier(self, text):
        """텍스트에서 해운사 감지"""
        upper = text.upper()
        for carrier, keywords in CARRIER_KEYWORDS.items():
            for kw in keywords:
                if kw in upper:
                    return carrier
        return None

    def _extract_text(self, file_path):
        """PDF에서 텍스트 추출"""
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                texts = []
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        texts.append(t)
                return '\n'.join(texts)
        except ImportError:
            logger.warning("pdfplumber 미설치 — pip install pdfplumber")
            # 폴백: PyPDF2
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                return '\n'.join(p.extract_text() or '' for p in reader.pages)
            except Exception as e:
                logger.error(f"PDF 텍스트 추출 실패: {e}")
                return None
        except Exception as e:
            logger.error(f"텍스트 추출 오류: {e}")
            return None

    def _find_template(self, carrier, doc_type):
        """DB에서 해운사+서류유형 매칭 템플릿 검색"""
        if not carrier or not self.db_path:
            return None
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM inbound_template WHERE carrier=? AND doc_type=? AND is_active=1 ORDER BY usage_count DESC LIMIT 1",
                (carrier, doc_type)
            ).fetchone()
            conn.close()
            if row:
                return dict(row)
        except Exception as e:
            logger.debug(f"템플릿 조회 실패: {e}")
        return None

    def _parse_with_template(self, text, template):
        """저장된 템플릿 규칙으로 파싱 (AI 미호출)"""
        field_mappings = json.loads(template.get('field_mappings', '{}'))
        post_rules = json.loads(template.get('post_rules', '[]'))
        result = {}

        for field, pattern in field_mappings.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip() if match.lastindex else match.group(0).strip()
                # 후처리 규칙 적용
                for rule in post_rules:
                    if rule.get('field') == field:
                        value = self._apply_post_rule(value, rule)
                result[field] = value

        return result

    def _parse_with_ai(self, file_path, doc_type, raw_text=None):
        """Gemini Vision API로 파싱"""
        try:
            # 기존 gemini_parser 활용
            from features.ai.gemini_parser import parse_with_gemini
            result = parse_with_gemini(file_path, doc_type)
            if result:
                return result
        except ImportError:
            logger.info("gemini_parser 없음 — 룰 기반 폴백")
        except Exception as e:
            logger.warning(f"AI 파싱 실패: {e}")

        # AI 실패 시 룰 기반 폴백
        return self._rule_based_fallback(raw_text or '', doc_type)

    def _rule_based_fallback(self, text, doc_type):
        """AI 없이 정규식으로 기본 필드 추출"""
        result = {}
        patterns = {
            'bl_no': r'B/?L\s*(?:NO\.?|Number)?\s*[:\s]*([A-Z0-9]{6,20})',
            'container_no': r'([A-Z]{4}\d{7})',
            'lot_no': r'LOT\s*(?:NO\.?)?\s*[:\s]*(\S+)',
            'vessel': r'(?:VESSEL|V/V)\s*[:\s]*([A-Z][A-Z\s]+)',
            'net_weight': r'(?:NET\s*(?:WEIGHT|WT))\s*[:\s]*([\d,]+\.?\d*)\s*(?:KG|MT)',
        }
        for field, pat in patterns.items():
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip()
        return result

    def _apply_post_rule(self, value, rule):
        """후처리 규칙 적용"""
        action = rule.get('action', '')
        if action == 'remove_spaces':
            return value.replace(' ', '')
        elif action == 'uppercase':
            return value.upper()
        elif action == 'remove_commas':
            return value.replace(',', '')
        elif action == 'date_format':
            # YYYY-MM-DD 변환 시도
            for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y%m%d']:
                try:
                    from datetime import datetime
                    return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
                except ValueError:
                    continue
        return value
