# -*- coding: utf-8 -*-
"""A3 회귀 테스트 — DB 마이그레이션 실패는 조용히 삼키지 않고 앱 시작을 차단한다."""
import ast
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_INIT = os.path.join(ROOT, "backend", "api", "__init__.py")


def _read_api_init() -> str:
    with open(API_INIT, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _find_run_db_migrations(tree: ast.Module) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_run_db_migrations":
            return node
    raise AssertionError("backend/api/__init__.py에서 _run_db_migrations() 함수를 찾지 못함")


def _find_outer_migration_try(fn: ast.FunctionDef) -> ast.Try:
    for node in fn.body:
        if isinstance(node, ast.Try):
            return node
    raise AssertionError("_run_db_migrations()의 최상위 try 블록을 찾지 못함")


def test_db_migration_failure_is_re_raised_to_block_app_startup():
    tree = ast.parse(_read_api_init())
    fn = _find_run_db_migrations(tree)
    outer_try = _find_outer_migration_try(fn)

    assert outer_try.handlers, "_run_db_migrations() 최상위 try에 except 핸들러가 없음"

    for handler in outer_try.handlers:
        has_raise = any(isinstance(n, ast.Raise) for n in ast.walk(handler))
        assert has_raise, (
            "DB 마이그레이션 실패를 except에서 삼키고 있음. "
            "앱 시작을 차단하도록 예외를 다시 raise 해야 함"
        )


def test_db_migration_failure_logs_traceback_not_warning_only():
    code = _read_api_init()
    tree = ast.parse(code)
    fn = _find_run_db_migrations(tree)
    outer_try = _find_outer_migration_try(fn)

    handler_src = "\n".join(
        ast.get_source_segment(code, handler) or ""
        for handler in outer_try.handlers
    )

    assert "logging.exception" in handler_src, (
        "DB 마이그레이션 실패는 traceback을 남기도록 logging.exception으로 기록해야 함"
    )
    assert "logging.warning" not in handler_src, (
        "DB 마이그레이션 핵심 실패를 warning만 남기고 계속 진행하면 안 됨"
    )
    assert "RuntimeError" in handler_src or "raise" in handler_src, (
        "DB 마이그레이션 실패는 명시적 예외로 앱 시작을 차단해야 함"
    )


def test_db_migrations_run_before_fastapi_app_is_created():
    code = _read_api_init()

    migration_call_pos = code.find("_run_db_migrations()")
    app_create_pos = code.find("app = FastAPI(")

    assert migration_call_pos != -1, "모듈 시작 경로에 _run_db_migrations() 호출이 없음"
    assert app_create_pos != -1, "FastAPI 앱 생성 구문을 찾지 못함"
    assert migration_call_pos < app_create_pos, (
        "DB 마이그레이션은 FastAPI 앱 생성 전에 실행되어야 "
        "마이그레이션 실패 시 앱 시작을 차단할 수 있음"
    )


def test_db_migration_connection_uses_busy_timeout_and_close_guard():
    code = _read_api_init()
    tree = ast.parse(code)
    fn = _find_run_db_migrations(tree)
    fn_src = ast.get_source_segment(code, fn) or ""

    assert "timeout=30" in fn_src, "SQLite 일시 lock 완화를 위해 connect timeout을 설정해야 함"
    assert "PRAGMA busy_timeout=30000" in fn_src, "SQLite busy_timeout을 설정해야 함"
    assert "con is not None" in fn_src and "con.close()" in fn_src, (
        "마이그레이션 중간 실패 시에도 DB connection close를 보장해야 함"
    )
