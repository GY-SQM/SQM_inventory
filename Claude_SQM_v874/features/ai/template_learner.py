# -*- coding: utf-8 -*-
"""P2-4: TemplateLearner — AI 결과 + 사용자 수정 → 템플릿 자동 생성"""
import json
import re
import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

class TemplateLearner:
    """AI 파싱 결과와 사용자 수정을 비교하여 규칙 학습"""

    def __init__(self, db_path):
        self.db_path = db_path

    def learn_from_correction(self, carrier, doc_type, ai_result, user_corrected):
        """AI 결과 vs 사용자 수정 → 규칙 감지 → 템플릿 저장"""
        field_mappings = {}
        post_rules = []

        for field in user_corrected:
            if field in ('success', 'parse_method', 'carrier', 'is_new_carrier', 'doc_type'):
                continue

            ai_val = str(ai_result.get(field, ''))
            user_val = str(user_corrected.get(field, ''))

            if not user_val:
                continue

            # 규칙 감지
            rules = self._detect_rules(field, ai_val, user_val)
            if rules:
                post_rules.extend(rules)

            # 필드 매핑 패턴 생성
            if user_val:
                pattern = self._generate_pattern(field, user_val)
                if pattern:
                    field_mappings[field] = pattern

        if not field_mappings:
            logger.info(f"학습 가능한 규칙 없음: {carrier}/{doc_type}")
            return None

        # DB 저장
        template_data = {
            'carrier': carrier,
            'doc_type': doc_type,
            'field_mappings': json.dumps(field_mappings, ensure_ascii=False),
            'post_rules': json.dumps(post_rules, ensure_ascii=False),
        }

        self._save_template(template_data)
        logger.info(f"템플릿 저장: {carrier}/{doc_type} ({len(field_mappings)}개 필드)")
        return template_data

    def _detect_rules(self, field, ai_val, user_val):
        """AI값 → 사용자값 변환 규칙 감지"""
        rules = []

        if ai_val and user_val:
            # 공백 제거
            if ai_val.replace(' ', '') == user_val:
                rules.append({'field': field, 'action': 'remove_spaces'})
            # 대문자 변환
            elif ai_val.upper() == user_val:
                rules.append({'field': field, 'action': 'uppercase'})
            # 콤마 제거
            elif ai_val.replace(',', '') == user_val:
                rules.append({'field': field, 'action': 'remove_commas'})

        return rules

    def _generate_pattern(self, field, value):
        """필드값으로부터 정규식 패턴 생성"""
        field_labels = {
            'bl_no': r'B/?L\s*(?:NO\.?|Number)?\s*[:\s]*(\S+)',
            'container_no': r'([A-Z]{4}\d{7})',
            'lot_no': r'LOT\s*(?:NO\.?)?\s*[:\s]*(\S+)',
            'net_weight': r'NET\s*(?:WEIGHT|WT)\s*[:\s]*([\d,]+\.?\d*)',
            'vessel': r'(?:VESSEL|V/V)\s*[:\s]*(.+?)(?:\n|$)',
            'ship_date': r'(?:SHIPPED|SHIP\s*DATE)\s*[:\s]*(\d{4}[-/]\d{2}[-/]\d{2})',
            'arrival_date': r'(?:ARRIVAL|ETA)\s*[:\s]*(\d{4}[-/]\d{2}[-/]\d{2})',
            'invoice_no': r'(?:INVOICE|INV)\s*(?:NO\.?)?\s*[:\s]*(\S+)',
        }
        return field_labels.get(field)

    def _save_template(self, data):
        """템플릿을 DB에 저장/업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            existing = conn.execute(
                "SELECT id FROM inbound_template WHERE carrier=? AND doc_type=?",
                (data['carrier'], data['doc_type'])
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE inbound_template SET field_mappings=?, post_rules=?, updated_at=?, usage_count=usage_count+1 WHERE id=?",
                    (data['field_mappings'], data['post_rules'], datetime.now().isoformat(), existing[0])
                )
            else:
                conn.execute(
                    "INSERT INTO inbound_template (carrier, doc_type, field_mappings, post_rules, is_active, usage_count, created_at) VALUES (?,?,?,?,1,0,?)",
                    (data['carrier'], data['doc_type'], data['field_mappings'], data['post_rules'], datetime.now().isoformat())
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"템플릿 저장 실패: {e}")
