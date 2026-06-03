"""
SQM 재고관리 - Gemini AI 대화형 재고 조회 (v2.9.43)

기능:
- 자연어로 재고 조회 (예: "리튬카보네이트 현재고 알려줘")
- 조회 결과 Excel 내보내기
- 조회 결과 PDF 리포트 생성
- 대화 히스토리 유지

사용법:
    from gemini_chat_query import GeminiChatQuery
    
    chat = GeminiChatQuery(db_path="inventory.db", api_key="YOUR_KEY")
    result = chat.ask("리튬카보네이트 제품 현재고 알려줘")
    logger.debug(f"{result['answer']}")
    
    # Excel 내보내기
    chat.export_last_result_to_excel("output.xlsx")
"""
import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


READ_ONLY_QUERY_TYPES = {
    "DB_전체_테이블_요약",
    "DB_테이블_미리보기",
    "DB_상태_요약",
    "DB_쓰기_거부",
    "AI_자유조회",          # 전체 스키마 기반 읽기전용 NL→SQL 자유 조회
}

TABLE_ALIASES = {
    "재고": "inventory",
    "입고": "inventory",
    "입고 대기": "inventory",
    "톤백": "inventory_tonbag",
    "서브롯": "inventory_tonbag",
    "sublot": "inventory_tonbag",
    "출고 예정": "outbound",
    "출고": "outbound",
    "allocation": "allocation_plan",
    "allocaton": "allocation_plan",
    "예약": "allocation_plan",
    "배정": "allocation_plan",
    "picking": "picking_table",
    "피킹": "picking_table",
    "sold": "sold_table",
    "판매": "sold_table",
    "반품": "return_history",
    "return": "return_history",
    "위치 이동": "stock_movement",
    "위치": "stock_movement",
    "이동": "stock_movement",
    "대량 이동": "move_batch",
    "move_batch": "move_batch",
    "오류": "audit_log",
    "에러": "audit_log",
    "검증": "allocation_plan",
}

HARD_WRITE_INTENT_TERMS = (
    "삭제", "저장", "반영", "확정", "반려", "취소",
    "update", "delete", "insert", "drop", "alter", "create", "replace",
    "truncate", "attach", "detach", "vacuum",
)

SOFT_WRITE_INTENT_TERMS = (
    "수정", "변경", "승인",
)

READ_INTENT_TERMS = (
    "조회", "알려", "보여", "목록", "요약", "몇", "상태", "대기", "읽",
    "read", "show", "list", "summary", "pending",
)


# ═══════════════════════════════════════════════════════════════════════
# 쿼리 템플릿 정의
# ═══════════════════════════════════════════════════════════════════════

QUERY_TEMPLATES = {
    "전체_재고_요약": """
        SELECT 
            COUNT(*) as lot_count,
            ROUND(SUM(initial_weight)/1000, 2) as total_inbound_mt,
            ROUND(SUM(current_weight)/1000, 2) as total_current_mt,
            ROUND((SUM(initial_weight) - SUM(current_weight))/1000, 2) as total_outbound_mt
        FROM inventory
    """,

    "제품별_재고": """
        SELECT 
            product as 제품,
            COUNT(*) as LOT수,
            ROUND(SUM(initial_weight)/1000, 2) as 입고량_MT,
            ROUND(SUM(current_weight)/1000, 2) as 현재고_MT,
            ROUND(SUM(current_weight)*100.0/SUM(initial_weight), 1) as 잔량율
        FROM inventory
        {where_clause}
        GROUP BY product
        ORDER BY 현재고_MT DESC
    """,

    "SAP별_재고": """
        SELECT 
            sap_no as SAP_NO,
            product as 제품,
            COUNT(*) as LOT수,
            ROUND(SUM(initial_weight)/1000, 2) as 입고량_MT,
            ROUND(SUM(current_weight)/1000, 2) as 현재고_MT
        FROM inventory
        {where_clause}
        GROUP BY sap_no
        ORDER BY sap_no
    """,

    "LOT_목록": """
        SELECT 
            lot_no as LOT_NO,
            sap_no as SAP_NO,
            bl_no as BL_NO,
            product as 제품,
            ROUND(initial_weight/1000, 3) as 입고량_MT,
            ROUND(current_weight/1000, 3) as 현재고_MT,
            status as 상태,
            arrival_date as 입고일
        FROM inventory
        {where_clause}
        ORDER BY arrival_date DESC, lot_no
        LIMIT {limit}
    """,

    "SubLOT_목록": """
        SELECT 
            t.lot_no as LOT_NO,
            t.sub_lt as Sub_LOT,
            t.weight as 중량_KG,
            t.status as 상태,
            t.inbound_date as 입고일,
            t.outbound_date as 출고일,
            i.product as 제품
        FROM inventory_tonbag t
        LEFT JOIN inventory i ON t.lot_no = i.lot_no
        {where_clause}
        ORDER BY t.lot_no, t.sub_lt
        LIMIT {limit}
    """,

    "월별_현황": """
        SELECT 
            strftime('%Y-%m', arrival_date) as 월,
            COUNT(*) as LOT수,
            ROUND(SUM(initial_weight)/1000, 2) as 입고량_MT
        FROM inventory
        {where_clause}
        GROUP BY 월
        ORDER BY 월
    """,

    "상태별_현황": """
        SELECT 
            status as 상태,
            COUNT(*) as 수량,
            ROUND(SUM(current_weight)/1000, 2) as 중량_MT
        FROM inventory
        {where_clause}
        GROUP BY status
    """,

    "출고_현황": """
        SELECT 
            t.outbound_date as 출고일,
            COUNT(*) as 출고수량,
            ROUND(SUM(t.weight)/1000, 2) as 출고량_MT,
            i.product as 제품
        FROM inventory_tonbag t
        LEFT JOIN inventory i ON t.lot_no = i.lot_no
        WHERE t.status = 'PICKED'
        {and_clause}
        GROUP BY t.outbound_date, i.product
        ORDER BY t.outbound_date DESC
        LIMIT {limit}
    """,

    "저재고_LOT": """
        SELECT 
            lot_no as LOT_NO,
            product as 제품,
            ROUND(current_weight/1000, 3) as 현재고_MT,
            ROUND(current_weight*100.0/initial_weight, 1) as 잔량율
        FROM inventory
        WHERE current_weight > 0 
        AND current_weight < initial_weight * {threshold}
        ORDER BY 잔량율 ASC
        LIMIT {limit}
    """,
    "예약_배정_현황": """
        SELECT 
            status as 상태,
            COUNT(*) as 건수,
            ROUND(SUM(COALESCE(qty_mt, 0)), 2) as 수량_MT
        FROM allocation_plan
        GROUP BY status
        ORDER BY 
            CASE status WHEN 'RESERVED' THEN 1 WHEN 'EXECUTED' THEN 2 WHEN 'CANCELLED' THEN 3 ELSE 4 END
    """,
    "예약_배정_목록": """
        SELECT 
            ap.lot_no as LOT_NO,
            ap.sub_lt as Sub_LT,
            ap.customer as 고객,
            ap.sale_ref as SALE_REF,
            ap.qty_mt as 수량_MT,
            ap.outbound_date as 출고예정일,
            ap.status as 상태,
            ap.created_at as 예약일시
        FROM allocation_plan ap
        {where_clause}
        ORDER BY ap.created_at DESC
        LIMIT {limit}
    """,
    "입고_PENDING_목록": """
        SELECT
            lot_no as LOT_NO,
            sap_no as SAP_NO,
            product as 제품,
            ROUND(COALESCE(net_weight, initial_weight, current_weight, 0) / 1000.0, 3) as 중량_MT,
            container_no as 컨테이너,
            warehouse as 창고,
            inbound_date as 입고예정일,
            arrival_date as 입항일,
            bl_no as BL_NO,
            vessel as 선박,
            created_at as 등록일시
        FROM inventory
        WHERE status = 'PENDING'
        {and_clause}
        ORDER BY COALESCE(inbound_date, arrival_date, created_at) DESC
        LIMIT {limit}
    """,
    "입고_PENDING_요약": """
        SELECT
            COUNT(*) as 건수,
            ROUND(SUM(COALESCE(net_weight, initial_weight, current_weight, 0)) / 1000.0, 3) as 총중량_MT,
            COUNT(DISTINCT container_no) as 컨테이너수,
            COUNT(DISTINCT product) as 제품수
        FROM inventory
        WHERE status = 'PENDING'
        {and_clause}
    """,
    "Allocation_승인대기": """
        SELECT
            id as ID,
            lot_no as LOT_NO,
            sub_lt as Sub_LT,
            customer as 고객,
            sale_ref as SALE_REF,
            qty_mt as 수량_MT,
            outbound_date as 출고예정일,
            status as 상태,
            workflow_status as 워크플로상태,
            created_at as 요청일시
        FROM allocation_plan
        WHERE status = 'STAGED'
          AND workflow_status = 'PENDING_APPROVAL'
          {and_clause}
        ORDER BY created_at DESC, id DESC
        LIMIT {limit}
    """,
    "대량이동_PENDING": """
        SELECT
            batch_id as Batch_ID,
            total_count as 건수,
            reason_code as 사유,
            submitted_by as 요청자,
            submitted_at as 요청일시,
            note as 메모
        FROM move_batch
        WHERE status = 'PENDING'
        ORDER BY submitted_at DESC
        LIMIT {limit}
    """,
    "운영_PENDING_요약": """
        SELECT '입고 대기' as 구분, COUNT(*) as 건수
        FROM inventory
        WHERE status = 'PENDING'
        UNION ALL
        SELECT 'Allocation 승인 대기' as 구분, COUNT(*) as 건수
        FROM allocation_plan
        WHERE status = 'STAGED'
          AND workflow_status = 'PENDING_APPROVAL'
        UNION ALL
        SELECT '대량 이동 승인 대기' as 구분, COUNT(*) as 건수
        FROM move_batch
        WHERE status = 'PENDING'
    """,
}

# 제품명 매핑 (한글 → DB값)
# v3.6.9: 공통 모듈에서 PRODUCT_MAPPING import (중복 제거)
try:
    from features.ai.gemini_utils import PRODUCT_MAPPING
except ImportError:
    try:
        from gemini_utils import PRODUCT_MAPPING
    except ImportError:
        # fallback: 최소한의 매핑
        PRODUCT_MAPPING = {
            "리튬카보네이트": "LITHIUM CARBONATE",
            "탄산리튬": "LITHIUM CARBONATE",
            "리튬하이드록사이드": "LITHIUM HYDROXIDE",
            "수산화리튬": "LITHIUM HYDROXIDE",
            "리튬클로라이드": "LITHIUM CHLORIDE",
            "염화리튬": "LITHIUM CHLORIDE",
            "포타슘클로라이드": "POTASSIUM CHLORIDE",
            "염화칼륨": "POTASSIUM CHLORIDE",
            "소듐나이트레이트": "SODIUM NITRATE",
            "질산나트륨": "SODIUM NITRATE",
        }


@dataclass
class QueryResult:
    """쿼리 결과"""
    success: bool
    query_type: str
    sql: str
    data: List[Dict]
    columns: List[str]
    row_count: int
    answer: str
    timestamp: datetime = field(default_factory=datetime.now)
    error: str = ""


class GeminiChatQuery:
    """Gemini AI 대화형 재고 조회"""

    def __init__(self, db_path: str, api_key: str = None):
        """
        Args:
            db_path: 데이터베이스 경로
            api_key: Gemini API 키 (없으면 환경변수에서 로드)
        """
        self.db_path = db_path
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

        self.db = None
        self.chat_history: List[Dict] = []
        self.last_result: Optional[QueryResult] = None

        self._init_db()
        self._init_gemini()

    def _init_db(self):
        """DB 초기화"""
        try:
            from engine_modules.database import SQMDatabase
            self.db = SQMDatabase(self.db_path)
            logger.info(f"DB 연결 성공: {self.db_path}")
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"DB 연결 실패: {e}")
            raise

    def _init_gemini(self):
        """Gemini API 초기화 (v3.6.9: google-genai SDK로 통일)"""
        self.gemini_available = False
        self.client = None
        self.model_name = "gemini-2.5-flash"

        if not self.api_key:
            logger.warning("Gemini API 키가 없습니다. 규칙 기반 파싱만 사용합니다.")
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self.gemini_available = True
            logger.info(f"Gemini API 초기화 성공 (모델: {self.model_name})")
        except ImportError:
            logger.warning("google-genai 패키지가 없습니다: pip install google-genai")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning(f"Gemini API 초기화 실패: {e}")

    def ask(self, question: str) -> Dict[str, Any]:
        """
        자연어 질문으로 재고 조회
        
        Args:
            question: 자연어 질문
            
        Returns:
            dict: {
                'success': bool,
                'answer': str,
                'data': list,
                'columns': list,
                'row_count': int,
                'query_type': str,
                'elapsed_ms': int  # v3.6.9: 응답 시간 (ms)
            }
        """
        import time
        _ask_start = time.time()

        logger.info(f"질문: {question}")

        # 1. 질문 분석
        intent = self._analyze_intent(question)
        logger.info(f"의도 분석: {intent}")

        # 2. SQL 생성 및 실행
        result = self._execute_query(intent, question)

        # 3. 결과 저장
        self.last_result = result
        self.chat_history.append({
            "role": "user",
            "content": question,
            "timestamp": datetime.now().isoformat()
        })
        self.chat_history.append({
            "role": "assistant",
            "content": result.answer,
            "timestamp": datetime.now().isoformat()
        })

        _elapsed_ms = int((time.time() - _ask_start) * 1000)
        logger.info(f"질문 처리 완료: {_elapsed_ms}ms")

        return {
            "success": result.success,
            "answer": result.answer,
            "data": result.data,
            "columns": result.columns,
            "row_count": result.row_count,
            "query_type": result.query_type,
            "sql": result.sql,
            "elapsed_ms": _elapsed_ms
        }

    def _analyze_intent(self, question: str) -> Dict[str, Any]:
        """질문 의도 분석"""
        q = question.lower()

        intent = {
            "query_type": "전체_재고_요약",
            "product": None,
            "sap_no": None,
            "bl_no": None,
            "lot_no": None,
            "date_range": None,
            "status": None,
            "limit": 100,
            "threshold": 0.3,  # 저재고 기준
        }

        # 제품 추출
        for kr_name, en_name in PRODUCT_MAPPING.items():
            if kr_name in q:
                intent["product"] = en_name
                break

        # SAP NO 추출
        sap_match = re.search(r'sap\s*(?:no|번호)?\s*[:\s]?\s*(\d{7})', q)
        if sap_match:
            intent["sap_no"] = sap_match.group(1)
        else:
            sap_match = re.search(r'22\d{5}', q)
            if sap_match:
                intent["sap_no"] = sap_match.group(0)

        # BL NO 추출
        bl_match = re.search(r'bl\s*(?:no|번호)?\s*[:\s]?\s*([A-Z]{4}\d+)', q, re.I)
        if bl_match:
            intent["bl_no"] = bl_match.group(1).upper()

        # LOT NO 추출
        lot_match = re.search(r'lot\s*(?:no|번호)?\s*[:\s]?\s*(\d{8,11})', q)  # v8.7.0: 8~11자리
        if lot_match:
            intent["lot_no"] = lot_match.group(1)
        else:
            lot_match = re.search(r'112\d{7}', q)
            if lot_match:
                intent["lot_no"] = lot_match.group(0)

        # 날짜/월 추출
        month_match = re.search(r'(\d{4})년?\s*(\d{1,2})월', q)
        if month_match:
            intent["date_range"] = f"{month_match.group(1)}-{int(month_match.group(2)):02d}"

        # 쿼리 타입 결정
        if self._has_write_intent(q):
            intent["query_type"] = "DB_쓰기_거부"
            return intent

        if self._is_database_overview_question(q):
            intent["query_type"] = "DB_전체_테이블_요약"
            return intent

        if self._is_database_status_question(q):
            intent["query_type"] = "DB_상태_요약"
            return intent

        table_name = self._find_readable_table(question) if self._is_table_preview_question(q) else None
        if table_name:
            intent["query_type"] = "DB_테이블_미리보기"
            intent["table_name"] = table_name
            return intent

        pending_terms = ("pending", "펜딩", "대기", "미반입")
        has_pending = any(term in q for term in pending_terms)
        has_approval_wait = ("승인" in q and "대기" in q) or "pending_approval" in q
        has_allocation = (
            "allocation" in q or "allocaton" in q or "예약" in q
            or "배정" in q or "allocation table" in q
        )
        has_batch_move = (
            ("대량" in q and "이동" in q) or "batch move" in q
            or "move_batch" in q or "이동승인" in q
        )

        if has_batch_move and has_pending:
            intent["query_type"] = "대량이동_PENDING"
        elif has_approval_wait or (has_allocation and has_pending):
            intent["query_type"] = "Allocation_승인대기"
        elif (
            ("입고" in q or "창고" in q or "미반입" in q or "보세" in q) and has_pending
        ) or (has_pending and (intent["product"] or intent["sap_no"] or intent["bl_no"] or intent["lot_no"])):
            if "요약" in q or "몇" in q or "건수" in q or "총" in q:
                intent["query_type"] = "입고_PENDING_요약"
            else:
                intent["query_type"] = "입고_PENDING_목록"
        elif has_pending:
            intent["query_type"] = "운영_PENDING_요약"
        elif has_allocation:
            # "allocation table에서 몇 개 allocation됐니?" → 예약/배정 현황
            if "목록" in q or "리스트" in q or "내역" in q:
                intent["query_type"] = "예약_배정_목록"
            else:
                intent["query_type"] = "예약_배정_현황"
        elif "전체" in q and ("요약" in q or "현황" in q):
            intent["query_type"] = "전체_재고_요약"
        elif "제품" in q and "별" in q:
            intent["query_type"] = "제품별_재고"
        elif "sap" in q and "별" in q:
            intent["query_type"] = "SAP별_재고"
        elif "월" in q and "별" in q:
            intent["query_type"] = "월별_현황"
        elif "상태" in q and "별" in q:
            intent["query_type"] = "상태별_현황"
        elif "출고" in q and ("현황" in q or "내역" in q or "목록" in q):
            intent["query_type"] = "출고_현황"
        elif "저재고" in q or "부족" in q or ("잔량" in q and ("이하" in q or "미만" in q)):
            intent["query_type"] = "저재고_LOT"
            # 퍼센트 추출
            pct_match = re.search(r'(\d+)\s*%', q)
            if pct_match:
                intent["threshold"] = int(pct_match.group(1)) / 100
        elif "sublot" in q or "sub-lot" in q or "서브롯" in q or "서브 롯" in q:
            intent["query_type"] = "SubLOT_목록"
        elif "lot" in q and ("목록" in q or "리스트" in q or "조회" in q):
            intent["query_type"] = "LOT_목록"
        elif intent["product"] or intent["sap_no"]:
            # 특정 조건이 있으면 LOT 목록
            if "재고" in q or "현황" in q:
                intent["query_type"] = "제품별_재고"
            else:
                intent["query_type"] = "LOT_목록"
        elif "현재고" in q or "재고" in q:
            if intent["product"]:
                intent["query_type"] = "제품별_재고"
            else:
                intent["query_type"] = "전체_재고_요약"

        # ── ★ 전용 템플릿이 하나도 안 맞아 기본값(전체_재고_요약)으로 떨어진 경우:
        #    Gemini 사용 가능하면 전체 스키마 기반 읽기전용 자유 조회로 폴백.
        #    (단, 사용자가 명시적으로 '전체 요약/현황'을 묻거나 순수 재고 질문이면 기존 템플릿 유지) ──
        if intent["query_type"] == "전체_재고_요약" and getattr(self, "gemini_available", False):
            named_table = self._find_readable_table(question)
            core_inventory = (("재고" in q or "현재고" in q) and named_table is None)
            explicit_overall = (("전체" in q and ("요약" in q or "현황" in q)) or core_inventory)
            if not explicit_overall:
                intent["query_type"] = "AI_자유조회"

        return intent

    def _has_write_intent(self, q: str) -> bool:
        """채팅에서 상태 변경/쓰기 요청은 항상 거부한다."""
        if any(term in q for term in HARD_WRITE_INTENT_TERMS):
            return True
        if any(term in q for term in SOFT_WRITE_INTENT_TERMS):
            return not any(term in q for term in READ_INTENT_TERMS)
        return False

    def _is_database_overview_question(self, q: str) -> bool:
        """전체 DB 테이블 목록/건수 요약 질문인지 판별."""
        has_db = "db" in q or "database" in q or "데이터베이스" in q or "테이블" in q
        has_overview = "전체" in q or "모든" in q or "목록" in q or "요약" in q
        return has_db and has_overview and "상태" not in q

    def _is_database_status_question(self, q: str) -> bool:
        """DB 전체 상태 컬럼 요약 질문인지 판별."""
        has_scope = "전체" in q or "모든" in q or "database" in q or "데이터베이스" in q
        has_status = "상태" in q or "status" in q or "워크플로" in q or "workflow" in q
        return has_scope and has_status

    def _is_table_preview_question(self, q: str) -> bool:
        """특정 테이블 원본 행 미리보기 질문인지 판별."""
        if "테이블" in q or "table" in q:
            return True
        return any(table_name.lower() in q for table_name in self._get_readable_tables())

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """SQLite 식별자 안전 인용."""
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("빈 테이블명은 사용할 수 없습니다.")
        return '"' + identifier.replace('"', '""') + '"'

    def _validate_read_only_sql(self, sql: str) -> None:
        """생성된 SQL이 읽기 전용인지 최종 확인."""
        without_comments = re.sub(r"--.*?(?:\n|$)|/\*.*?\*/", "", sql, flags=re.DOTALL)
        compact = re.sub(r"\s+", " ", without_comments.strip())
        first_word = compact.split(" ", 1)[0].upper() if compact else ""
        if first_word not in ("SELECT", "WITH", "PRAGMA"):
            raise ValueError("AI 채팅은 읽기 전용 SQL만 실행할 수 있습니다.")
        if first_word == "PRAGMA" and not re.match(
            r"^PRAGMA\s+(table_info|index_list|foreign_key_list|database_list)\b",
            compact,
            re.IGNORECASE,
        ):
            raise ValueError("AI 채팅은 메타데이터 조회 PRAGMA만 실행할 수 있습니다.")
        blocked = re.search(
            r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|VACUUM)\b",
            compact,
            re.IGNORECASE,
        )
        if blocked:
            raise ValueError("AI 채팅은 데이터 수정 SQL을 실행할 수 없습니다.")

    def _fetchall_readonly(self, sql: str, params: tuple = ()) -> List[Dict]:
        self._validate_read_only_sql(sql)
        return self.db.fetchall(sql, params)

    def _get_readable_tables(self) -> List[str]:
        rows = self._fetchall_readonly(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        return [str(r.get("name", "")) for r in rows if r.get("name")]

    def _table_columns(self, table_name: str) -> List[str]:
        quoted = self._quote_identifier(table_name)
        rows = self._fetchall_readonly(f"PRAGMA table_info({quoted})")
        return [str(r.get("name", "")) for r in rows if r.get("name")]

    def _find_readable_table(self, question: str) -> Optional[str]:
        """질문에서 실제 DB 테이블명을 찾는다."""
        q = question.lower()
        tables = set(self._get_readable_tables())
        if not tables:
            return None

        for table_name in sorted(tables, key=len, reverse=True):
            if table_name.lower() in q:
                return table_name

        for alias, table_name in sorted(TABLE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if alias.lower() in q and table_name in tables:
                return table_name

        return None

    # ── ★ 전체 스키마 기반 읽기전용 자유 조회 (NL→SQL) ──────────────────────
    def _build_full_schema(self) -> str:
        """읽기 가능한 모든 테이블의 (테이블: 컬럼들) 스키마 텍스트."""
        lines = []
        for t in self._get_readable_tables():
            try:
                cols = self._table_columns(t)
            except Exception:
                cols = []
            lines.append(f"{t}({', '.join(cols)})")
        return "\n".join(lines)

    @staticmethod
    def _extract_sql(text: str) -> Optional[str]:
        """LLM 응답에서 SELECT/WITH SQL만 추출."""
        if not text:
            return None
        s = text.strip()
        m = re.search(r"```(?:sql)?\s*(.+?)```", s, re.S | re.I)   # 코드펜스 제거
        if m:
            s = m.group(1).strip()
        m2 = re.search(r"\b(SELECT|WITH)\b", s, re.I)              # 첫 SELECT/WITH 부터
        if not m2:
            return None
        s = s[m2.start():].strip()
        s = s.split(";")[0].strip()                                # 첫 문장만
        return s or None

    @staticmethod
    def _enforce_limit(sql: str, max_rows: int) -> str:
        """최외곽 SELECT 레벨에 LIMIT가 없으면 안전 상한 추가.
        서브쿼리 안의 LIMIT(괄호 depth>0)는 무시 — 행 수 우회 방지."""
        depth = 0
        i = 0
        while i < len(sql):
            ch = sql[i]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif depth == 0 and sql[i:i+5].upper() == 'LIMIT':
                prev = sql[i - 1] if i > 0 else ' '
                nxt  = sql[i + 5] if i + 5 < len(sql) else ' '
                if not (prev.isalnum() or prev == '_') and not (nxt.isalnum() or nxt == '_'):
                    return sql  # 최외곽 LIMIT 이미 있음
            i += 1
        return f"{sql.rstrip().rstrip(';')}\nLIMIT {int(max_rows)}"

    def _generate_sql_via_gemini(self, question: str, schema: str) -> Optional[str]:
        """전체 스키마를 주고 읽기전용 SELECT 1개를 생성."""
        prompt = (
            "당신은 SQLite 읽기 전용 데이터 분석가입니다. 아래 [스키마]에 존재하는 "
            "테이블/컬럼만 사용해 [질문]에 답하는 SQLite 쿼리 1개를 작성하세요.\n"
            "규칙:\n"
            "- 반드시 SELECT 또는 WITH ... SELECT 만. INSERT/UPDATE/DELETE/ALTER/DROP 등 변경문 절대 금지.\n"
            "- 스키마에 없는 테이블/컬럼은 쓰지 말 것.\n"
            "- 결과는 최대 500행(LIMIT 500 이하).\n"
            "- 설명/주석/코드펜스 없이 SQL 본문만 출력.\n\n"
            f"[스키마]\n{schema}\n\n[질문]\n{question}\n\n[SQL]"
        )
        try:
            from features.ai.gemini_utils import call_gemini_safe
            resp = call_gemini_safe(self.client, self.model_name, prompt, timeout=30)
            text = resp.text if resp is not None else None
        except ImportError:
            try:
                text = self.client.models.generate_content(
                    model=self.model_name, contents=prompt
                ).text
            except Exception as e:
                logger.warning(f"NL2SQL 생성 실패(fallback): {e}")
                return None
        except Exception as e:
            logger.warning(f"NL2SQL 생성 실패: {e}")
            return None
        return self._extract_sql(text)

    def _execute_ai_freeform(self, question: str) -> QueryResult:
        """전체 스키마 기반 읽기전용 자유 조회."""
        if not getattr(self, "gemini_available", False) or not self.client:
            return QueryResult(False, "AI_자유조회", "", [], [], 0,
                               "AI 자유 조회는 Gemini API 키가 설정돼야 사용할 수 있습니다.", error="no_api_key")
        schema = self._build_full_schema()
        sql = self._generate_sql_via_gemini(question, schema)
        if not sql:
            return QueryResult(False, "AI_자유조회", "", [], [], 0,
                               "질문을 SQL로 변환하지 못했습니다. 테이블/컬럼을 더 구체적으로 알려주세요.",
                               "sql_gen_failed")
        try:
            sql = self._enforce_limit(sql, 500)
            self._validate_read_only_sql(sql)          # ★ 기존 읽기전용 가드 재사용
            data = self._fetchall_readonly(sql)
        except ValueError as e:
            return QueryResult(False, "AI_자유조회", sql, [], [], 0,
                               f"읽기 전용 정책으로 차단된 쿼리입니다: {e}", error="read_only_guard")
        except sqlite3.Error as e:
            return QueryResult(False, "AI_자유조회", sql, [], [], 0,
                               f"쿼리 실행 오류: {e}\nSQL: {sql}", error="sql_error")
        columns = list(data[0].keys()) if data else []
        if not data:
            answer = f"조건에 맞는 데이터가 없습니다.\n\n실행 SQL:\n{sql}"
        else:
            preview_cols = ", ".join(columns[:8]) + (" …" if len(columns) > 8 else "")
            answer = (f"📊 {len(data)}건 조회됨 (읽기 전용).\n"
                      f"컬럼: {preview_cols}\n\n실행 SQL:\n{sql}")
        return QueryResult(True, "AI_자유조회", sql, data, columns, len(data), answer)

    def _execute_database_tool(self, intent: Dict, question: str) -> QueryResult:
        """전체 DB 읽기 전용 도구 실행."""
        query_type = intent["query_type"]
        try:
            if query_type == "AI_자유조회":
                return self._execute_ai_freeform(question)

            if query_type == "DB_쓰기_거부":
                return QueryResult(
                    success=False,
                    query_type=query_type,
                    sql="",
                    data=[],
                    columns=[],
                    row_count=0,
                    answer=(
                        "읽기 전용 AI 채팅에서는 데이터 수정, 승인, 반려, 확정, 삭제를 실행할 수 없습니다. "
                        "필요한 값은 조회만 하고, 상태 변경은 기존 화면의 명시적 버튼에서 처리하세요."
                    ),
                    error="read_only_guard",
                )

            if query_type == "DB_전체_테이블_요약":
                data = []
                for table_name in self._get_readable_tables():
                    quoted = self._quote_identifier(table_name)
                    row = self._fetchall_readonly(f"SELECT COUNT(*) AS row_count FROM {quoted}")[0]
                    cols = self._table_columns(table_name)
                    data.append({
                        "테이블": table_name,
                        "행수": int(row.get("row_count", 0) or 0),
                        "컬럼수": len(cols),
                    })
                answer = self._generate_answer(query_type, data, ["테이블", "행수", "컬럼수"], intent, question)
                return QueryResult(True, query_type, "sqlite_master + COUNT(*)", data,
                                   ["테이블", "행수", "컬럼수"], len(data), answer)

            if query_type == "DB_테이블_미리보기":
                table_name = intent.get("table_name") or self._find_readable_table(question)
                if not table_name:
                    return QueryResult(False, query_type, "", [], [], 0,
                                       "읽을 테이블을 찾지 못했습니다. '전체 테이블 요약'으로 테이블명을 먼저 확인하세요.",
                                       "table_not_found")
                quoted = self._quote_identifier(table_name)
                limit = int(intent.get("limit", 100))
                sql = f"SELECT * FROM {quoted} LIMIT ?"
                data = self._fetchall_readonly(sql, (limit,))
                columns = list(data[0].keys()) if data else self._table_columns(table_name)
                intent["table_name"] = table_name
                answer = self._generate_answer(query_type, data, columns, intent, question)
                return QueryResult(True, query_type, sql, data, columns, len(data), answer)

            if query_type == "DB_상태_요약":
                data = []
                status_columns = {
                    "status", "workflow_status", "gate_status", "approval_status",
                    "fail_code", "fail_reason", "risk_flags",
                }
                for table_name in self._get_readable_tables():
                    columns = self._table_columns(table_name)
                    for col in columns:
                        if col.lower() not in status_columns:
                            continue
                        quoted_table = self._quote_identifier(table_name)
                        quoted_col = self._quote_identifier(col)
                        sql = (
                            f"SELECT {quoted_col} AS value, COUNT(*) AS count "
                            f"FROM {quoted_table} "
                            f"WHERE {quoted_col} IS NOT NULL AND TRIM(CAST({quoted_col} AS TEXT)) <> '' "
                            f"GROUP BY {quoted_col} ORDER BY count DESC LIMIT 50"
                        )
                        for row in self._fetchall_readonly(sql):
                            data.append({
                                "테이블": table_name,
                                "컬럼": col,
                                "값": row.get("value"),
                                "건수": int(row.get("count", 0) or 0),
                            })
                columns = ["테이블", "컬럼", "값", "건수"]
                answer = self._generate_answer(query_type, data, columns, intent, question)
                return QueryResult(True, query_type, "status-column GROUP BY scan", data,
                                   columns, len(data), answer)

            return QueryResult(False, query_type, "", [], [], 0, "지원하지 않는 DB 조회 도구입니다.")
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as e:
            err_msg = str(e)
            logger.error(f"읽기 전용 DB 도구 오류: {e}")
            return QueryResult(False, query_type, "", [], [], 0,
                               f"읽기 전용 DB 조회 중 오류가 발생했습니다: {err_msg}", err_msg)

    def _execute_query(self, intent: Dict, question: str) -> QueryResult:
        """쿼리 실행"""
        query_type = intent["query_type"]

        try:
            if query_type in READ_ONLY_QUERY_TYPES:
                return self._execute_database_tool(intent, question)

            # WHERE 절 구성 — ? 파라미터 바인딩 사용 (SQL 인젝션 방지 P0-1)
            where_parts: list = []
            and_parts: list = []
            params: list = []

            if intent["product"]:
                where_parts.append("product = ?")
                and_parts.append("i.product = ?")
                params.append(intent["product"])

            if intent["sap_no"]:
                where_parts.append("sap_no = ?")
                and_parts.append("i.sap_no = ?")
                params.append(intent["sap_no"])

            if intent["bl_no"]:
                where_parts.append("bl_no = ?")
                and_parts.append("i.bl_no = ?")
                params.append(intent["bl_no"])

            if intent["lot_no"]:
                where_parts.append("lot_no = ?")
                and_parts.append("i.lot_no = ?")
                params.append(intent["lot_no"])

            if intent["date_range"]:
                where_parts.append("arrival_date LIKE ?")
                and_parts.append("i.arrival_date LIKE ?")
                params.append(f"{intent['date_range']}%")

            # 예약_배정: allocation_plan 테이블만 사용 → lot_no / created_at 조건만
            if query_type in ("예약_배정_현황", "예약_배정_목록"):
                ap_parts: list = []
                ap_params: list = []
                if intent.get("lot_no"):
                    ap_parts.append("ap.lot_no = ?")
                    ap_params.append(intent["lot_no"])
                if intent.get("date_range"):
                    ap_parts.append("ap.created_at LIKE ?")
                    ap_params.append(f"{intent['date_range']}%")
                where_parts = ap_parts
                and_parts = ap_parts
                params = ap_params

            # PENDING 전용 조회는 각 템플릿이 안전한 고정 조건을 이미 포함한다.
            if query_type in ("입고_PENDING_목록", "입고_PENDING_요약"):
                inv_parts: list = []
                inv_params: list = []
                if intent.get("product"):
                    inv_parts.append("product = ?")
                    inv_params.append(intent["product"])
                if intent.get("sap_no"):
                    inv_parts.append("sap_no = ?")
                    inv_params.append(intent["sap_no"])
                if intent.get("bl_no"):
                    inv_parts.append("bl_no = ?")
                    inv_params.append(intent["bl_no"])
                if intent.get("lot_no"):
                    inv_parts.append("lot_no = ?")
                    inv_params.append(intent["lot_no"])
                if intent.get("date_range"):
                    inv_parts.append("(inbound_date LIKE ? OR arrival_date LIKE ? OR created_at LIKE ?)")
                    inv_params.extend([f"{intent['date_range']}%"] * 3)
                where_parts = []
                and_parts = inv_parts
                params = inv_params
            elif query_type == "Allocation_승인대기":
                ap_parts = []
                ap_params = []
                if intent.get("lot_no"):
                    ap_parts.append("lot_no = ?")
                    ap_params.append(intent["lot_no"])
                if intent.get("date_range"):
                    ap_parts.append("created_at LIKE ?")
                    ap_params.append(f"{intent['date_range']}%")
                where_parts = []
                and_parts = ap_parts
                params = ap_params
            elif query_type in ("대량이동_PENDING", "운영_PENDING_요약"):
                where_parts = []
                and_parts = []
                params = []

            where_clause = ""
            and_clause = ""
            if where_parts:
                where_clause = "WHERE " + " AND ".join(where_parts)
            if and_parts:
                and_clause = "AND " + " AND ".join(and_parts)

            # SQL 생성 — limit/threshold는 숫자이므로 format 안전
            sql_template = QUERY_TEMPLATES.get(query_type, QUERY_TEMPLATES["전체_재고_요약"])
            sql = sql_template.format(
                where_clause=where_clause,
                and_clause=and_clause,
                limit=int(intent.get("limit", 100)),
                threshold=float(intent.get("threshold", 0.3))
            )

            # 실행 — 파라미터 바인딩으로 SQL 인젝션 방지
            rows = self._fetchall_readonly(sql, tuple(params))

            # 결과를 딕셔너리 리스트로 변환
            if rows and isinstance(rows[0], dict):
                # SQMDatabase가 이미 dict로 반환
                data = rows
                columns = list(rows[0].keys()) if rows else []
            else:
                # tuple/Row인 경우 — params 함께 전달
                self._validate_read_only_sql(sql)
                cursor = self.db.execute(sql, tuple(params))
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = [dict(zip(columns, row)) for row in rows]

            # 답변 생성
            answer = self._generate_answer(query_type, data, columns, intent, question)

            return QueryResult(
                success=True,
                query_type=query_type,
                sql=sql,
                data=data,
                columns=columns,
                row_count=len(data),
                answer=answer
            )

        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError) as e:
            err_msg = str(e)
            logger.error(f"쿼리 실행 오류: {e}")
            allocation_query_types = (
                "예약_배정_현황",
                "예약_배정_목록",
                "Allocation_승인대기",
                "운영_PENDING_요약",
            )
            if "allocation_plan" in err_msg and query_type in allocation_query_types:
                answer = (
                    "Allocation(예약) 테이블이 DB에 없습니다. "
                    "앱을 한 번 종료 후 다시 실행하면 테이블이 자동 생성됩니다."
                )
            elif "move_batch" in err_msg and query_type in ("대량이동_PENDING", "운영_PENDING_요약"):
                answer = (
                    "대량 이동 승인 테이블(move_batch)이 DB에 없습니다. "
                    "앱을 한 번 종료 후 다시 실행하면 테이블이 자동 생성됩니다."
                )
            else:
                answer = f"조회 중 오류가 발생했습니다: {err_msg}"
            return QueryResult(
                success=False,
                query_type=query_type,
                sql="",
                data=[],
                columns=[],
                row_count=0,
                answer=answer,
                error=err_msg
            )

    def _generate_answer(self, query_type: str, data: List[Dict],
                         columns: List[str], intent: Dict, question: str) -> str:
        """자연어 답변 생성"""
        if not data:
            # 쿼리 타입별 맞춤 빈 결과 안내
            if query_type == "저재고_LOT":
                pct = int(intent.get("threshold", 0.3) * 100)
                return f"✅ 잔량율 {pct}% 이하인 LOT가 없습니다.\n현재 모든 LOT가 충분한 재고를 보유하고 있습니다."
            elif query_type == "제품별_재고" and intent.get("product"):
                return (f"📋 '{intent['product']}' 제품의 재고가 없습니다.\n"
                        f"현재 DB에 등록된 제품을 확인하려면 '제품별 재고'를 조회하세요.")
            elif query_type == "입고_PENDING_목록":
                return "✅ 현재 입고 PENDING LOT가 없습니다."
            elif query_type == "Allocation_승인대기":
                return "✅ 현재 Allocation 승인 대기 항목이 없습니다."
            elif query_type == "대량이동_PENDING":
                return "✅ 현재 대량 이동 승인 대기 배치가 없습니다."
            elif query_type == "DB_테이블_미리보기":
                table_name = intent.get("table_name") or "선택한 테이블"
                return f"📋 {table_name} 테이블에 표시할 데이터가 없습니다."
            elif query_type == "DB_상태_요약":
                return "📋 상태/검증 컬럼이 있는 테이블을 찾지 못했거나 집계할 값이 없습니다."
            return "📋 조회 결과가 없습니다."

        deterministic_query_types = {
            "입고_PENDING_목록",
            "입고_PENDING_요약",
            "Allocation_승인대기",
            "대량이동_PENDING",
            "운영_PENDING_요약",
        }

        # Gemini 사용 가능하면 AI 답변 생성
        # PENDING/승인대기 운영 상태는 숫자와 상태명이 정확해야 하므로 규칙 기반으로 고정한다.
        if self.gemini_available and len(data) <= 50 and query_type not in deterministic_query_types:
            try:
                import time
                _start = time.time()
                answer = self._generate_ai_answer(data, columns, question)
                _elapsed = int((time.time() - _start) * 1000)
                logging.info(f"AI 답변 생성 완료 ({_elapsed}ms)")

                # v5.6.8: AI 답변 검증 — 데이터가 있는데 "없습니다"라고 하면 fallback
                if data and any(kw in answer for kw in ['없습니다', '정보가 없', '데이터가 없', '찾을 수 없']):
                    logging.warning(f"AI 답변이 데이터({len(data)}건)와 모순 → 규칙 기반 fallback")
                else:
                    return answer
            except PermissionError as e:
                return f"⚠️ API 키 오류: {e}\nsettings.ini의 api_key를 확인하세요."
            except RuntimeError:
                return "⚠️ API 한도 초과: 잠시 후 다시 시도해주세요."
            except TimeoutError:
                pass  # 규칙 기반으로 fallback
            except (ValueError, TypeError, KeyError) as e:
                logging.debug(f"AI 답변 생성 실패: {e}")  # 실패시 규칙 기반으로

        # 규칙 기반 답변
        if query_type == "전체_재고_요약":
            r = data[0]
            return (
                f"📊 전체 재고 현황\n\n"
                f"• 총 LOT 수: {r.get('lot_count', 0):,}개\n"
                f"• 총 입고량: {r.get('total_inbound_mt', 0):,.1f} MT\n"
                f"• 현재 재고: {r.get('total_current_mt', 0):,.1f} MT\n"
                f"• 총 출고량: {r.get('total_outbound_mt', 0):,.1f} MT"
            )

        elif query_type == "제품별_재고":
            lines = ["📊 제품별 재고 현황\n"]
            for r in data:
                lines.append(
                    f"• {r.get('제품', '')}: {r.get('현재고_MT', 0):,.1f} MT "
                    f"({r.get('LOT수', 0)}개 LOT, 잔량율 {r.get('잔량율', 0):.1f}%)"
                )
            return "\n".join(lines)

        elif query_type == "SAP별_재고":
            lines = [f"📊 SAP NO별 재고 현황 ({len(data)}건)\n"]
            for r in data[:10]:  # 상위 10개만
                lines.append(
                    f"• {r.get('SAP_NO', '')}: {r.get('현재고_MT', 0):,.1f} MT "
                    f"({r.get('제품', '')})"
                )
            if len(data) > 10:
                lines.append(f"\n... 외 {len(data)-10}건")
            return "\n".join(lines)

        elif query_type == "월별_현황":
            lines = ["📊 월별 입고 현황\n"]
            for r in data:
                lines.append(
                    f"• {r.get('월', '')}: {r.get('입고량_MT', 0):,.1f} MT ({r.get('LOT수', 0)}개 LOT)"
                )
            return "\n".join(lines)

        elif query_type in ("LOT_목록", "SubLOT_목록"):
            product_info = ""
            if intent.get("product"):
                # 제품 매핑 역변환 (영문→한글)
                kr_map = {"LITHIUM CARBONATE": "리튬카보네이트", "NICKEL SULFATE": "니켈설페이트"}
                kr = kr_map.get(intent["product"], intent["product"])
                total_mt = sum(r.get("현재고_MT", 0) for r in data)
                product_info = f" ({kr})"
                return (
                    f"📋 {kr} 재고 현황{product_info}\n\n"
                    f"• LOT 수: {len(data)}개\n"
                    f"• 총 현재고: {total_mt:,.1f} MT\n\n"
                    f"(상세 데이터는 Excel/PDF로 내보내기 가능)"
                )
            return f"📋 조회 결과: {len(data)}건\n\n(상세 데이터는 Excel/PDF로 내보내기 가능)"

        elif query_type == "저재고_LOT":
            lines = [f"⚠️ 저재고 LOT ({len(data)}건)\n"]
            for r in data[:10]:
                lines.append(
                    f"• {r.get('LOT_NO', '')}: {r.get('현재고_MT', 0):.2f} MT "
                    f"(잔량 {r.get('잔량율', 0):.1f}%) - {r.get('제품', '')}"
                )
            return "\n".join(lines)
        elif query_type == "예약_배정_현황":
            total = sum(r.get("건수", 0) for r in data)
            if total == 0:
                return "📋 Allocation(예약/배정) 현황\n\n• 예약된 건수: 0건 (allocation_plan에 데이터 없음)"
            lines = [f"📋 Allocation(예약/배정) 현황 — 총 {total}건\n"]
            status_kr = {"RESERVED": "예약중", "EXECUTED": "출고실행됨", "CANCELLED": "취소됨"}
            for r in data:
                st = r.get("상태", "")
                lines.append(
                    f"• {status_kr.get(st, st)}: {r.get('건수', 0)}건 "
                    f"({r.get('수량_MT', 0):,.1f} MT)"
                )
            return "\n".join(lines)
        elif query_type == "예약_배정_목록":
            if not data:
                return "📋 예약/배정 목록: 0건"
            return f"📋 예약/배정 목록: {len(data)}건\n\n(상세는 Excel/PDF 내보내기 가능)"

        elif query_type == "운영_PENDING_요약":
            total = 0
            lines = ["⏳ 운영 PENDING 요약\n"]
            for r in data:
                count = int(r.get("건수", 0) or 0)
                total += count
                lines.append(f"• {r.get('구분', '')}: {count:,}건")
            lines.append(f"\n총 {total:,}건의 대기 항목이 있습니다.")
            return "\n".join(lines)

        elif query_type == "입고_PENDING_요약":
            r = data[0]
            return (
                "⏳ 입고 PENDING 요약\n\n"
                f"• 대기 LOT: {int(r.get('건수', 0) or 0):,}건\n"
                f"• 총 중량: {float(r.get('총중량_MT', 0) or 0):,.3f} MT\n"
                f"• 컨테이너: {int(r.get('컨테이너수', 0) or 0):,}개\n"
                f"• 제품 수: {int(r.get('제품수', 0) or 0):,}개"
            )

        elif query_type == "입고_PENDING_목록":
            total_mt = sum(float(r.get("중량_MT", 0) or 0) for r in data)
            lines = [f"⏳ 입고 PENDING 목록 — 상위 {len(data):,}건 / {total_mt:,.3f} MT\n"]
            for r in data[:10]:
                lines.append(
                    f"• {r.get('LOT_NO', '')}: {r.get('제품', '')}, "
                    f"{float(r.get('중량_MT', 0) or 0):,.3f} MT, "
                    f"컨테이너 {r.get('컨테이너', '') or '-'}"
                )
            if len(data) > 10:
                lines.append(f"\n... 외 {len(data) - 10:,}건")
            return "\n".join(lines)

        elif query_type == "Allocation_승인대기":
            total_mt = sum(float(r.get("수량_MT", 0) or 0) for r in data)
            lines = [f"⏳ Allocation 승인 대기 — {len(data):,}건 / {total_mt:,.3f} MT\n"]
            for r in data[:10]:
                lines.append(
                    f"• {r.get('LOT_NO', '')}-{r.get('Sub_LT', '')}: "
                    f"{r.get('고객', '') or '-'}, {float(r.get('수량_MT', 0) or 0):,.3f} MT"
                )
            if len(data) > 10:
                lines.append(f"\n... 외 {len(data) - 10:,}건")
            return "\n".join(lines)

        elif query_type == "대량이동_PENDING":
            total_count = sum(int(r.get("건수", 0) or 0) for r in data)
            lines = [f"⏳ 대량 이동 승인 대기 — {len(data):,}배치 / {total_count:,}건\n"]
            for r in data[:10]:
                lines.append(
                    f"• {r.get('Batch_ID', '')}: {int(r.get('건수', 0) or 0):,}건, "
                    f"{r.get('사유', '') or '-'}, 요청자 {r.get('요청자', '') or '-'}"
                )
            if len(data) > 10:
                lines.append(f"\n... 외 {len(data) - 10:,}배치")
            return "\n".join(lines)

        elif query_type == "DB_전체_테이블_요약":
            total_rows = sum(int(r.get("행수", 0) or 0) for r in data)
            lines = [f"📚 DB 전체 테이블 요약 — {len(data):,}개 테이블 / {total_rows:,}행\n"]
            for r in data[:30]:
                lines.append(
                    f"• {r.get('테이블', '')}: {int(r.get('행수', 0) or 0):,}행, "
                    f"{int(r.get('컬럼수', 0) or 0):,}컬럼"
                )
            if len(data) > 30:
                lines.append(f"\n... 외 {len(data) - 30:,}개 테이블")
            lines.append("\n읽기 전용 조회만 가능하며 데이터 수정은 차단됩니다.")
            return "\n".join(lines)

        elif query_type == "DB_테이블_미리보기":
            table_name = intent.get("table_name") or "선택한 테이블"
            return (
                f"📋 {table_name} 테이블 미리보기 — {len(data):,}건\n\n"
                f"컬럼: {', '.join(columns[:20])}"
                + ("\n(상세 데이터는 표/내보내기 기능에서 확인하세요.)" if len(columns) <= 20 else "\n(컬럼이 많아 일부만 표시했습니다.)")
            )

        elif query_type == "DB_상태_요약":
            lines = [f"📊 DB 상태/검증 컬럼 요약 — {len(data):,}개 상태값\n"]
            for r in data[:40]:
                lines.append(
                    f"• {r.get('테이블', '')}.{r.get('컬럼', '')} = "
                    f"{r.get('값', '')}: {int(r.get('건수', 0) or 0):,}건"
                )
            if len(data) > 40:
                lines.append(f"\n... 외 {len(data) - 40:,}개 상태값")
            lines.append("\n조회 전용 결과입니다. 승인/확정/삭제 같은 상태 변경은 실행하지 않습니다.")
            return "\n".join(lines)

        else:
            return f"조회 결과: {len(data)}건"

    def _generate_ai_answer(self, data: List[Dict], columns: List[str], question: str) -> str:
        """Gemini로 AI 답변 생성"""
        if not self.client:
            return self._generate_answer_fallback(data, columns)

        prompt = f"""
다음은 재고 조회 결과입니다. 사용자의 질문에 대해 친절하고 간결하게 한국어로 답변해주세요.

중요: DB에서 제품명은 영문으로 저장되어 있습니다.
- 'LITHIUM CARBONATE' = 리튬카보네이트 (탄산리튬)
- 'NICKEL SULFATE' = 니켈설페이트 (황산니켈)
사용자가 한글로 물어봐도, 조회 결과에 해당 영문 제품이 있으면 동일한 제품으로 답변하세요.

질문: {question}

조회 결과 (컬럼: {columns}):
{json.dumps(data[:20], ensure_ascii=False, indent=2)}

총 {len(data)}건

답변 형식:
- 핵심 정보를 먼저 요약
- 필요시 상세 내역 나열
- 이모지 적절히 사용
- 200자 이내로 간결하게
"""

        try:
            from features.ai.gemini_utils import call_gemini_safe
            response = call_gemini_safe(
                self.client, self.model_name, prompt, timeout=30
            )
        except ImportError:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
        return response.text

    def export_to_excel(self, filepath: str = None) -> str:
        """마지막 조회 결과를 Excel로 내보내기"""
        if not self.last_result or not self.last_result.data:
            return "내보낼 데이터가 없습니다."

        try:
            import pandas as pd

            if filepath is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"재고조회_{self.last_result.query_type}_{timestamp}.xlsx"

            df = pd.DataFrame(self.last_result.data)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='조회결과', index=False)

                # 열 너비 자동 조정
                worksheet = writer.sheets['조회결과']
                for idx, col in enumerate(df.columns):
                    max_len = max(
                        df[col].astype(str).map(len).max(),
                        len(str(col))
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)

            logger.info(f"Excel 내보내기 완료: {filepath}")
            return filepath

        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"Excel 내보내기 실패: {e}")
            return f"오류: {str(e)}"

    def export_to_pdf(self, filepath: str = None) -> str:
        """마지막 조회 결과를 PDF로 내보내기"""
        if not self.last_result or not self.last_result.data:
            return "내보낼 데이터가 없습니다."

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )

            if filepath is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"재고조회_{self.last_result.query_type}_{timestamp}.pdf"

            # 한글 폰트 등록 시도
            try:
                pdfmetrics.registerFont(TTFont('Malgun', 'malgun.ttf'))
                font_name = 'Malgun'
            except (ValueError, TypeError, KeyError):
                font_name = 'Helvetica'

            doc = SimpleDocTemplate(
                filepath,
                pagesize=landscape(A4),
                rightMargin=10*mm,
                leftMargin=10*mm,
                topMargin=10*mm,
                bottomMargin=10*mm
            )

            elements = []
            styles = getSampleStyleSheet()

            # 제목
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=16,
                spaceAfter=20
            )
            elements.append(Paragraph(f"재고 조회 결과 - {self.last_result.query_type}", title_style))
            elements.append(Paragraph(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            elements.append(Spacer(1, 10*mm))

            # 테이블
            data = self.last_result.data[:100]  # 최대 100행
            columns = self.last_result.columns

            table_data = [columns]  # 헤더
            for row in data:
                table_data.append([str(row.get(col, '')) for col in columns])

            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))

            elements.append(table)

            # 요약
            elements.append(Spacer(1, 10*mm))
            elements.append(Paragraph(f"총 {len(data)}건 / 전체 {self.last_result.row_count}건", styles['Normal']))

            doc.build(elements)

            logger.info(f"PDF 내보내기 완료: {filepath}")
            return filepath

        except ImportError:
            return "PDF 생성을 위해 reportlab 패키지가 필요합니다."
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"PDF 내보내기 실패: {e}")
            return f"오류: {str(e)}"

    def get_history(self) -> List[Dict]:
        """대화 히스토리 반환"""
        return self.chat_history

    def clear_history(self):
        """대화 히스토리 초기화"""
        self.chat_history = []
        self.last_result = None


# ═══════════════════════════════════════════════════════════════════════
# 테스트
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 테스트 실행
    TEST_DB = "./test_inventory.db"

    if not os.path.exists(TEST_DB):
        logger.debug(f"테스트 DB가 없습니다: {TEST_DB}")
        exit(1)

    chat = GeminiChatQuery(db_path=TEST_DB)

    logger.debug("=" * 60)
    logger.debug("  SQM 재고 AI 조회 테스트")
    logger.debug("=" * 60)

    # 테스트 질문들
    questions = [
        "전체 재고 현황 알려줘",
        "제품별 재고 현황",
        "리튬카보네이트 현재고",
        "2025년 3월 입고분",
        "저재고 LOT 목록 (30% 이하)",
        "SAP NO별 재고 현황",
    ]

    for q in questions:
        logger.debug(f"\n질문: {q}")
        logger.debug("-" * 40)
        result = chat.ask(q)
        logger.debug(f"{result['answer']}")
        logger.debug(f"(조회 건수: {result['row_count']})")

    # Excel 내보내기 테스트
    logger.debug("\n" + "=" * 60)
    logger.debug("Excel 내보내기 테스트...")
    excel_path = chat.export_to_excel()
    logger.debug(f"생성됨: {excel_path}")
