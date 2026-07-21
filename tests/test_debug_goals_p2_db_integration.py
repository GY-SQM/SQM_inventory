# -*- coding: utf-8 -*-
"""P2 통합 회귀 테스트 — prompt_version DB 영속화.

P2 (2026-07-21): "이번 PL 파싱이 어떤 프롬프트 버전으로 실행됐나" 역추적.
  - parsing_log.prompt_version 컬럼 추가 (멱등 ALTER)
  - _log_parse_result(prompt_version) 인자 추가
  - parse_packing_list 본체 + P0 retry helper에서 자동 기록
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEMINI_PARSER = os.path.join(ROOT, "features", "ai", "gemini_parser.py")
DB_SCHEMA_MIXIN = os.path.join(ROOT, "engine_modules", "db_schema_mixin.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _import_gemini_parser():
    sys.path.insert(0, ROOT)
    from features.ai import gemini_parser  # noqa: F401
    return gemini_parser


# ---------------------------------------------------------------------------
# DB 스키마 멱등 마이그레이션
# ---------------------------------------------------------------------------

def test_p2_db_schema_adds_prompt_version_column():
    """P2: parsing_log 테이블에 prompt_version 컬럼이 정의되어 있어야 함."""
    code = _read(DB_SCHEMA_MIXIN)
    # CREATE TABLE 안에 prompt_version 컬럼이 있어야 함
    assert "prompt_version TEXT" in code, (
        "parsing_log CREATE TABLE에 prompt_version 컬럼 누락"
    )
    # 멱등 ALTER TABLE도 있어야 함
    assert re.search(
        r"ALTER\s+TABLE\s+parsing_log\s+ADD\s+COLUMN\s+prompt_version\s+TEXT",
        code,
        re.IGNORECASE,
    ), "parsing_log 멱등 ALTER TABLE 누락"


def test_p2_db_schema_migration_idempotent():
    """P2: 마이그레이션 코드가 'prompt_version' 컬럼 존재 여부 체크 패턴이어야 함."""
    code = _read(DB_SCHEMA_MIXIN)
    # 단순 substring 패턴: 'prompt_version' 체크 + ALTER TABLE + ADD COLUMN 조합
    assert "'prompt_version' not in" in code or '"prompt_version" not in' in code, (
        "멱등 마이그레이션 패턴('prompt_version' not in) 누락"
    )
    assert "ALTER TABLE parsing_log ADD COLUMN prompt_version" in code, (
        "ALTER TABLE ADD COLUMN prompt_version 누락"
    )


def test_p2_db_schema_prompt_version_index():
    """P2: idx_parsing_log_prompt_version 인덱스가 생성되어야 함 (역추적 성능)."""
    code = _read(DB_SCHEMA_MIXIN)
    assert "idx_parsing_log_prompt_version" in code, (
        "idx_parsing_log_prompt_version 인덱스 누락"
    )


# ---------------------------------------------------------------------------
# _log_parse_result 시그니처
# ---------------------------------------------------------------------------

def test_p2_log_parse_result_signature_has_prompt_version():
    """P2: _log_parse_result 시그니처에 prompt_version 인자 있어야 함."""
    code = _read(GEMINI_PARSER)
    m = re.search(
        r"def\s+_log_parse_result\s*\([^)]*prompt_version[^)]*\)",
        code,
        re.DOTALL,
    )
    assert m, "_log_parse_result 시그니처에 prompt_version 인자 누락"


def test_p2_log_parse_result_insert_includes_prompt_version():
    """P2: _log_parse_result INSERT가 prompt_version 컬럼에 값 저장해야 함."""
    code = _read(GEMINI_PARSER)
    # INSERT INTO parsing_log (..., confidence_score, prompt_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)
    m = re.search(
        r"INSERT\s+INTO\s+parsing_log\s*\([^)]*prompt_version[^)]*\)\s*VALUES\s*\([^)]*\?",
        code,
        re.DOTALL | re.IGNORECASE,
    )
    assert m, "INSERT 문에 prompt_version 컬럼 또는 VALUES ? 누락"


# ---------------------------------------------------------------------------
# P0 retry helper 시그니처
# ---------------------------------------------------------------------------

def test_p2_retry_helper_accepts_prompt_version():
    """P2: _retry_parse_with_validation 시그니처에 prompt_version 인자 있어야 함."""
    code = _read(GEMINI_PARSER)
    m = re.search(
        r"def\s+_retry_parse_with_validation\s*\([^)]*prompt_version[^)]*\)",
        code,
        re.DOTALL,
    )
    assert m, "_retry_parse_with_validation 시그니처에 prompt_version 인자 누락"


def test_p2_retry_helper_passes_prompt_version_to_log():
    """P2: retry helper 내부 _log_parse_result 호출이 prompt_version 전달해야 함."""
    code = _read(GEMINI_PARSER)
    retry_start = code.find("def _retry_parse_with_validation")
    assert retry_start >= 0
    body = code[retry_start:]
    next_def = body.find("\n    def ", 10)
    if next_def > 0:
        body = body[:next_def]
    # 단순 카운트: prompt_version= 이 4번 이상 (4개 _log_parse_result 호출 각각)
    n = body.count("prompt_version=")
    assert n >= 4, (
        f"retry helper 본체에 prompt_version= 호출이 4번 이상이어야 함. 실제 {n}번"
    )


# ---------------------------------------------------------------------------
# parse_packing_list 본체 통합
# ---------------------------------------------------------------------------

def test_p2_parse_packing_list_calculates_fingerprint():
    """P2: parse_packing_list 본체에 _get_prompt_fingerprint 호출이 있어야 함."""
    code = _read(GEMINI_PARSER)
    parse_start = code.find("def parse_packing_list")
    assert parse_start >= 0
    # 본체 어딘가에 _get_prompt_fingerprint 호출이 있어야 함
    body = code[parse_start:]
    next_def = body.find("\n    def ", 10)
    if next_def > 0:
        body = body[:next_def]
    assert "_get_prompt_fingerprint" in body, (
        "parse_packing_list 본체에 _get_prompt_fingerprint 호출 누락"
    )
    # fingerprint 결과를 _prompt_version 변수에 저장하는 라인
    assert "_prompt_version" in body, (
        "fingerprint 계산 결과가 _prompt_version 변수에 저장되지 않음"
    )
    assert "_prompt_version = self._get_prompt_fingerprint" in body, (
        "fingerprint 계산 라인 형식 이상 — `_prompt_version = self._get_prompt_fingerprint(prompt)` 형태여야 함"
    )


def test_p2_parse_packing_list_passes_prompt_version_to_retry():
    """P2: parse_packing_list 본체에서 _retry_parse_with_validation 호출에 prompt_version 전달."""
    code = _read(GEMINI_PARSER)
    parse_start = code.find("def parse_packing_list")
    retry_call_start = code.find("_retry_parse_with_validation(", parse_start)
    assert retry_call_start > parse_start, "retry helper 호출 자체가 없음"
    # 호출의 닫는 괄호 위치까지 슬라이스
    snippet = code[retry_call_start:retry_call_start + 800]
    assert "prompt_version=" in snippet, (
        "_retry_parse_with_validation 호출에 prompt_version= 인자 누락"
    )


def test_p2_parse_packing_list_log_calls_have_prompt_version():
    """P2: parse_packing_list 본체 _log_parse_result 호출 2곳 모두 prompt_version 전달."""
    code = _read(GEMINI_PARSER)
    parse_start = code.find("def parse_packing_list")
    body = code[parse_start:]
    next_def = body.find("\n    def ", 10)
    if next_def > 0:
        body = body[:next_def]
    # 단순 카운트: prompt_version= 이 2번 이상 (P0 후크 + v8.2.4 통계)
    # (retry helper 호출은 retry helper 본체 안에 있으므로 본체 카운트엔 안 잡힘 — retry helper 시그니처 테스트가 따로 커버)
    n = body.count("prompt_version=")
    assert n >= 2, (
        f"parse_packing_list 본체에 prompt_version= 호출이 2번 이상이어야 함. 실제 {n}번"
    )


# ---------------------------------------------------------------------------
# in-process 동작 검증 (mock DB)
# ---------------------------------------------------------------------------

def test_p2_log_parse_result_accepts_prompt_version_kwarg():
    """P2: _log_parse_result가 prompt_version 인자 받아서 예외 없이 호출되어야 함 (no DB 시 silent skip)."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None  # DB 없으면 silent skip — 예외만 안 나면 OK
    # prompt_version 인자 전달
    try:
        parser._log_parse_result(
            doc_type='PL',
            source_file='test.pdf',
            success=True,
            lot_count=3,
            method='gemini',
            prompt_version='abc123def456',
        )
    except TypeError as e:
        raise AssertionError(
            f"_log_parse_result가 prompt_version 인자 거부: {e}"
        )


def test_p2_retry_helper_accepts_prompt_version_kwarg():
    """P2: _retry_parse_with_validation이 prompt_version 인자 받아서 호출 가능해야 함."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None
    lot = mod.LOTItem(list_no=1, lot_no="L1", net_weight_kg=1000.0, gross_weight_kg=1050.0)
    result = mod.PackingListResult(
        lots=[lot],
        total_net_weight_kg=500.0,  # mismatch
    )
    # _call_gemini / _extract_json monkey patch
    parser._call_gemini = lambda *a, **k: "{}"
    parser._extract_json = lambda t: {}
    parser._validate_lot_result = lambda r: (True, "")  # 검증 통과 → early return
    try:
        parser._retry_parse_with_validation(
            pdf_path="dummy.pdf",
            images=[b"img"],
            result=result,
            original_prompt="ORIG",
            max_retry=2,
            prompt_version="test_fp_123",
        )
    except TypeError as e:
        raise AssertionError(
            f"_retry_parse_with_validation이 prompt_version 인자 거부: {e}"
        )
