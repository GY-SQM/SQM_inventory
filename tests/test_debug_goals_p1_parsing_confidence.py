"""
P1 (v8.8.x): PL 파싱 신뢰도 점수의 DB 영속화 회귀 테스트.

LangGraph/LangSmith 청사진 검토 결과 채택한 "신뢰도 영속화(LangSmith-lite)":
  - parsing_log 테이블에 confidence_score(0~100) 컬럼 추가
  - 신규 DB CREATE + 기존 DB 멱등 ALTER 마이그레이션
  - GeminiParser._log_parse_result 가 confidence_score 를 기록 가능

검증:
  1. 신규 DB의 parsing_log 에 confidence_score 컬럼 존재
  2. confidence_score INSERT→SELECT 라운드트립 보존
  3. 레거시 테이블(컬럼 없음)에 _init_parsing_log_table 재실행 시 멱등 ALTER 로 컬럼 보강
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


def _v(row, key, idx):
    if row is None:
        return None
    return row[key] if isinstance(row, dict) else row[idx]


@pytest.fixture()
def eng():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    e = SQMInventoryEngineV3(db_path=path)
    yield e
    try:
        e.close()
    except Exception:
        pass
    for p in (path, path + "-wal", path + "-shm"):
        try:
            os.remove(p)
        except OSError:
            pass


def _plog_columns(e):
    return {r[1].lower()
            for r in e.db.execute("PRAGMA table_info(parsing_log)").fetchall()}


def test_parsing_log_has_confidence_column(eng):
    """신규 DB: parsing_log 에 confidence_score 컬럼이 있어야 한다."""
    assert "confidence_score" in _plog_columns(eng)


def test_confidence_score_roundtrip(eng):
    """confidence_score INSERT → SELECT 값 보존."""
    eng.db.execute(
        """INSERT INTO parsing_log
           (doc_type, source_file, success, lot_count, method,
            error_msg, confidence_score)
           VALUES ('PL', 'sample.pdf', 1, 12, 'gemini_confidence', '', ?)""",
        (87.5,),
    )
    row = eng.db.fetchone(
        "SELECT confidence_score cs, lot_count lc FROM parsing_log "
        "WHERE source_file='sample.pdf'")
    assert _v(row, "cs", 0) == 87.5
    assert _v(row, "lc", 1) == 12


def test_confidence_score_nullable(eng):
    """신뢰도 미산출 경로(예: 메인 gemini)는 NULL 로 기록되어도 정상."""
    eng.db.execute(
        """INSERT INTO parsing_log
           (doc_type, source_file, success, lot_count, method, confidence_score)
           VALUES ('BL', 'bl.pdf', 1, 0, 'gemini', NULL)""")
    row = eng.db.fetchone(
        "SELECT confidence_score cs FROM parsing_log WHERE source_file='bl.pdf'")
    assert _v(row, "cs", 0) is None


def test_legacy_table_migration_idempotent(eng):
    """레거시 parsing_log(컬럼 없음) → _init_parsing_log_table 재실행 시 컬럼 보강."""
    # 레거시 형태로 재생성 (confidence_score 없음)
    eng.db.execute("DROP TABLE IF EXISTS parsing_log")
    # 실제 v8.2.4 레거시 스키마 (confidence_score 만 없음)
    eng.db.execute(
        "CREATE TABLE parsing_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, doc_type TEXT NOT NULL, "
        "source_file TEXT, carrier_id TEXT, success INTEGER DEFAULT 0, "
        "bl_no TEXT, lot_count INTEGER DEFAULT 0, method TEXT, "
        "error_msg TEXT, duration_ms INTEGER DEFAULT 0, "
        "created_at TEXT DEFAULT (datetime('now','localtime')))")
    assert "confidence_score" not in _plog_columns(eng)

    # 멱등 마이그레이션 재실행
    eng.db._init_parsing_log_table()
    assert "confidence_score" in _plog_columns(eng)

    # 한 번 더 실행해도 에러 없이 통과 (멱등)
    eng.db._init_parsing_log_table()
    assert "confidence_score" in _plog_columns(eng)
