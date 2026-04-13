# -*- coding: utf-8 -*-
"""P2-6: LearningAccumulator — 파싱 이력 축적 + 자동 규칙 발견"""
import json
import logging
import sqlite3
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)

class LearningAccumulator:
    """파싱 결과를 축적하고 패턴을 분석하여 템플릿 규칙 자동 개선"""

    def __init__(self, db_path):
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self):
        """ai_learning_log 테이블 생성"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_learning_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    carrier TEXT,
                    doc_type TEXT,
                    parse_method TEXT,
                    field_name TEXT,
                    ai_value TEXT,
                    user_value TEXT,
                    was_corrected INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"학습 테이블 생성 실패: {e}")

    def log_parse(self, carrier, doc_type, parse_method, ai_result, user_corrected):
        """파싱 결과 기록"""
        try:
            conn = sqlite3.connect(self.db_path)
            now = datetime.now().isoformat()
            for field in user_corrected:
                if field in ('success', 'parse_method', 'carrier', 'is_new_carrier', 'doc_type'):
                    continue
                ai_val = str(ai_result.get(field, ''))
                user_val = str(user_corrected.get(field, ''))
                was_corrected = 1 if ai_val != user_val else 0
                conn.execute(
                    "INSERT INTO ai_learning_log (carrier, doc_type, parse_method, field_name, ai_value, user_value, was_corrected, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (carrier, doc_type, parse_method, field, ai_val, user_val, was_corrected, now)
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"학습 로그 기록 실패: {e}")

    def analyze_patterns(self, carrier, doc_type, min_count=10):
        """축적된 데이터에서 패턴 분석"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT field_name, ai_value, user_value, was_corrected FROM ai_learning_log WHERE carrier=? AND doc_type=? ORDER BY created_at DESC LIMIT 100",
                (carrier, doc_type)
            ).fetchall()
            conn.close()

            if len(rows) < min_count:
                return None

            # 필드별 수정 빈도 분석
            corrections = Counter()
            for r in rows:
                if r['was_corrected']:
                    corrections[r['field_name']] += 1

            return {
                'total_logs': len(rows),
                'correction_rate': {k: v / len(rows) for k, v in corrections.items()},
                'most_corrected': corrections.most_common(5),
            }
        except Exception as e:
            logger.error(f"패턴 분석 실패: {e}")
            return None
