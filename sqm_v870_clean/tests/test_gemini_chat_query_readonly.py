import sqlite3

from features.ai.gemini_chat_query import GeminiChatQuery


class SqliteDbAdapter:
    def __init__(self, conn):
        self.conn = conn

    def fetchall(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)


def make_chat():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE inventory (
            lot_no TEXT,
            product TEXT,
            status TEXT,
            current_weight REAL
        );
        CREATE TABLE allocation_plan (
            id INTEGER PRIMARY KEY,
            lot_no TEXT,
            status TEXT,
            workflow_status TEXT,
            qty_mt REAL,
            risk_flags TEXT
        );
        CREATE TABLE sold_table (
            lot_no TEXT,
            status TEXT,
            sold_to TEXT
        );
        INSERT INTO inventory VALUES ('L001', 'LITHIUM CARBONATE', 'PENDING', 5000);
        INSERT INTO inventory VALUES ('L002', 'LITHIUM CARBONATE', 'AVAILABLE', 3000);
        INSERT INTO allocation_plan VALUES (1, 'L001', 'STAGED', 'PENDING_APPROVAL', 5.0, 'NEEDS_REVIEW');
        INSERT INTO sold_table VALUES ('L003', 'SOLD', 'ACME');
        """
    )
    chat = GeminiChatQuery.__new__(GeminiChatQuery)
    chat.db = SqliteDbAdapter(conn)
    chat.db_path = ":memory:"
    chat.api_key = ""
    chat.gemini_available = False
    chat.client = None
    chat.model_name = "test"
    chat.chat_history = []
    chat.last_result = None
    return chat


def test_can_summarize_all_database_tables_readonly():
    chat = make_chat()

    result = chat.ask("데이터베이스 전체 테이블 요약 보여줘")

    assert result["success"] is True
    assert result["query_type"] == "DB_전체_테이블_요약"
    names = {row["테이블"] for row in result["data"]}
    assert {"inventory", "allocation_plan", "sold_table"}.issubset(names)


def test_can_preview_specific_table_without_write_access():
    chat = make_chat()

    result = chat.ask("sold_table 테이블 읽어줘")

    assert result["success"] is True
    assert result["query_type"] == "DB_테이블_미리보기"
    assert result["data"][0]["lot_no"] == "L003"
    assert result["sql"].lstrip().upper().startswith("SELECT")


def test_can_summarize_status_across_database():
    chat = make_chat()

    result = chat.ask("모든 데이터베이스 상태 요약")

    assert result["success"] is True
    assert result["query_type"] == "DB_상태_요약"
    status_rows = {(row["테이블"], row["컬럼"], row["값"]) for row in result["data"]}
    assert ("inventory", "status", "PENDING") in status_rows
    assert ("allocation_plan", "workflow_status", "PENDING_APPROVAL") in status_rows


def test_rejects_write_intent_from_chat():
    chat = make_chat()

    result = chat.ask("inventory 테이블 삭제해줘")

    assert result["success"] is False
    assert result["query_type"] == "DB_쓰기_거부"
    assert "읽기 전용" in result["answer"]


def test_readonly_sql_guard_blocks_mutating_pragma():
    chat = make_chat()

    try:
        chat._validate_read_only_sql("PRAGMA journal_mode=WAL")
    except ValueError as exc:
        assert "메타데이터 조회 PRAGMA" in str(exc)
    else:
        raise AssertionError("mutating PRAGMA should be rejected")
