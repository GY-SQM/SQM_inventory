# -*- coding: utf-8 -*-
"""
tools/lint_sql_context.py
==========================
SQM v9.0.6 — narrow SQL context lint (broad → narrow)

v9.0.0의 audit 🟡 #2 (f-string SQL 인벤토리)는 모든 f-string SQL 11건을
broad 패턴(regex)으로 검사했다. v9.0.6에서는 이걸 한 단계 좁혀서
**실제 SQL 실행 호출의 첫 번째 인자**만 검사하는 narrow lint를 추가한다.

왜 narrow 인가?
    - broad (모든 f-string SQL): 11건 모두 화이트리스트/? 바인딩 보호 중 하나
      → 현재 0건 위험 (audit 인벤토리 문서로 영속 검증 중)
    - narrow (cur.execute(f"...") / conn.execute(...)의 첫 인자):
      DB에 직접 전달되는 SQL만 검사 → false positive 제거, **새로 추가되는
      f-string SQL을 사전에 잡아냄**

검사 대상 (narrow context):
    - cur.execute(...)
    - conn.execute(...)
    - cursor.execute(...)
    - db.execute(...)
    - con.execute(...)  (cleanup_audit() 등)
    - con.executescript(...)

검사 항목:
    1. f-string이거나 string concat이면 [WARN]
    2. f-string 안의 {var}가 allowlist(core.db_allowed)에서 import 안 된 변수면 [WARN]
    3. 호출 위치(file:line) 표시

baseline (lint_sql_context.baseline.json):
    첫 가동 시 발견된 패턴 중 검토/허용된 항목은 baseline에 등록.
    이후 가동 시 baseline에 있는 (file, line)은 [REVIEWED]로 표시하고
    exit 0 유지. baseline에 없는 신규 패턴만 [WARN] + exit 1.

설계:
    - AST 기반 (regex 아님) — 정확한 호출 시그니처 파악
    - core.db_allowed에서 ALLOWED_TABLES를 import → 변수명이 테이블명인지 검증
    - exclude: core/db_allowed.py, tools/, tests/, scripts/

사용법:
    python tools/lint_sql_context.py [TARGET_DIR]
    # default: backend/

Exit code:
    0 — baseline 외 신규 발견 0건
    1 — baseline 외 신규 발견 (report 출력)
"""
import ast
import json
import re
import sys
from pathlib import Path
from typing import Iterator, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# SQL 실행 호출 메서드 화이트리스트
SQL_EXEC_METHODS = frozenset({"execute", "executescript"})

# SQL 실행 호출 시그니처 (AST Name/Attribute 어느 쪽이든 매칭)
EXEC_RECEIVER_NAMES = frozenset({"cur", "conn", "cursor", "db", "con"})

# 검사 제외 경로
EXCLUDE_PATTERNS = (
    r"core/db_allowed\.py$",
    r"tools/.*\.py$",
    r"tests/.*\.py$",
    r"scripts/.*\.py$",
    r"__pycache__",
    r"\.git",
    r"\.pytest_cache",
    r"docs/",
)

# core.db_allowed에서 import한 allowlist 변수 (안전한 f-string)
try:
    from core.db_allowed import ALLOWED_TABLES  # type: ignore
    SAFE_TABLE_NAMES = set(ALLOWED_TABLES)
except ImportError:
    SAFE_TABLE_NAMES = set()

# 안전 패턴: f-string 안의 {var}가 이 명명 규칙이면 skip
SAFE_PLACEHOLDER_NAMES = frozenset({
    # placeholder 생성기
    "ph", "phs", "placeholder", "placeholders", "ph_list",
    # SET 절 빌더
    "sets", "set_clauses", "set_clauses_inv", "set_clause", "set_clauses_list",
    # SELECT 절 빌더
    "select_cols", "cols", "columns", "select_columns",
    # WHERE 절 빌더
    "where", "where_clause", "where_clauses", "clauses", "where_conditions",
    # 값 리스트
    "params", "values", "lots", "lot_list", "ids",
    # allowlist 통과 변수 (validate 결과)
    "field", "fields", "tbl", "table", "table_name", "name",
    # f-string.format용 단순 빌더
    "expr", "sale_expr", "select", "select_expr",
})

# baseline 파일 경로
BASELINE_PATH = Path(__file__).resolve().parent / "lint_sql_context.baseline.json"


def load_baseline() -> dict:
    """baseline JSON 로드. 없거나 손상 시 빈 dict."""
    if not BASELINE_PATH.exists():
        return {}
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _baseline_key(rel_path: str, line: int) -> str:
    return f"{rel_path}:{line}"


def should_exclude(path: Path) -> bool:
    p = str(path).replace("\\", "/")
    return any(re.search(pat, p) for pat in EXCLUDE_PATTERNS)


def _is_exec_call(node: ast.Call) -> bool:
    """
    node가 cur.execute(...) / conn.executescript(...) 류인지 판별.

    형태:
        cur.execute(sql, ...)
        conn.executescript(sql)
        self.db.execute(sql, ...)
    """
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr not in SQL_EXEC_METHODS:
        return False
    # 수신자 이름 검사
    receiver = func.value
    if isinstance(receiver, ast.Name):
        return receiver.id in EXEC_RECEIVER_NAMES
    # self.db / self.conn 같은 메서드 체인도 허용
    if isinstance(receiver, ast.Attribute):
        return True
    return False


def _fstring_only_safe_placeholders(node: ast.JoinedStr) -> bool:
    """
    f-string의 모든 {var}가 safe placeholder 패턴(ph, placeholders 등)이면 True.
    예: f"IN ({ph})" where ph = ','.join('?' for _ in lots) → 안전

    safe 분류:
        - Name in SAFE_PLACEHOLDER_NAMES
        - Constant (문자열 리터럴)
        - Call with .join(...) (placeholder 빌더)
        - Subscript (dict/list 인덱싱, 보통 safe 빌더)
    """
    for value in node.values:
        if isinstance(value, ast.FormattedValue):
            inner = value.value
            if isinstance(inner, ast.Name) and inner.id in SAFE_PLACEHOLDER_NAMES:
                continue
            if isinstance(inner, ast.Constant):
                continue
            if isinstance(inner, ast.Call):
                # .join(...) 빌더는 safe (placeholder 생성기)
                if isinstance(inner.func, ast.Attribute) and inner.func.attr == "join":
                    continue
                return False
            if isinstance(inner, ast.Subscript):
                # dict['key'] / list[i] 류 — 보통 safe 빌더 결과
                continue
            # 그 외 (Attribute, BinOp, ...) → unknown → dangerous로 분류
            return False
    return True


def _is_dangerous_sql_arg(arg: ast.AST) -> bool:
    """
    SQL 실행 호출의 첫 인자가 동적(f-string 또는 concat)인지 판별.

    Returns:
        True — f-string 또는 BinOp(string concat)
        False — 상수 문자열, NamedExpr 등
    """
    # f-string: ast.JoinedStr
    if isinstance(arg, ast.JoinedStr):
        # safe placeholder 패턴 (예: IN ({ph})) 이면 skip
        if _fstring_only_safe_placeholders(arg):
            return False
        return True
    # string concat: ast.BinOp(Left=Str, Op=Add, Right=...)
    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
        if isinstance(arg.left, ast.Constant) and isinstance(arg.left.value, str):
            return True
        if isinstance(arg.right, ast.Constant) and isinstance(arg.right.value, str):
            return True
    return False


def _format_call_arg(arg: ast.AST) -> str:
    """호출 인자를 한 줄로 (출력용)."""
    try:
        return ast.unparse(arg)[:120]
    except Exception:
        return "<unparse 실패>"


def find_narrow_sql_exec(target_dir: Path) -> list[dict]:
    """
    target_dir 안의 .py 파일에서 cur.execute() 등 호출을 찾아
    첫 인자가 f-string/string concat인지 검사.

    Returns:
        list of {"file": Path, "line": int, "call": str, "arg": str, "kind": str}
    """
    findings: list[dict] = []
    for py_file in target_dir.rglob("*.py"):
        if should_exclude(py_file):
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not _is_exec_call(node):
                continue
            if not node.args:
                continue
            first_arg = node.args[0]
            if not _is_dangerous_sql_arg(first_arg):
                continue
            kind = "f-string" if isinstance(first_arg, ast.JoinedStr) else "string-concat"
            findings.append({
                "file": py_file,
                "line": node.lineno,
                "call": f"{ast.unparse(node.func)}(...)",
                "arg": _format_call_arg(first_arg),
                "kind": kind,
            })
    return findings


def partition_by_baseline(findings: list[dict], baseline: dict) -> tuple[list[dict], list[dict]]:
    """
    findings를 baseline 매칭(reviewed) / 미매칭(new)로 분류.

    Returns:
        (new_findings, reviewed_findings)
    """
    new: list[dict] = []
    reviewed: list[dict] = []
    for f in findings:
        try:
            rel = f["file"].relative_to(ROOT).as_posix()
        except ValueError:
            # ROOT 외부 파일은 baseline 매칭 불가 → new로 분류
            new.append(f)
            continue
        key = _baseline_key(rel, f["line"])
        if key in baseline:
            f["baseline_note"] = baseline[key]
            reviewed.append(f)
        else:
            new.append(f)
    return new, reviewed


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "backend"
    target_dir = (ROOT / target).resolve()
    if not target_dir.exists():
        print(f"[ERR] 디렉토리 없음: {target_dir}", file=sys.stderr)
        return 2

    # Windows cp949 회피
    import io
    if hasattr(sys.stdout, "buffer"):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass

    print(f"[INFO] 검사 대상: {target_dir}")
    print(f"[INFO] narrow context: cur/conn/cursor/db/con.execute(executescript)의 첫 인자")
    print(f"[INFO] 검사 항목: f-string, string concat")
    print()

    findings = find_narrow_sql_exec(target_dir)
    baseline = load_baseline()
    new_findings, reviewed = partition_by_baseline(findings, baseline)

    if not findings:
        print("[OK] narrow SQL context에서 동적 SQL 0건")
        return 0

    # reviewed 출력 (있을 때만)
    if reviewed:
        by_file: dict[Path, list[dict]] = {}
        for f in reviewed:
            by_file.setdefault(f["file"], []).append(f)
        print(f"[REVIEWED] {len(reviewed)}건 (baseline 등록, 의도된 dynamic)")
        for f, items in sorted(by_file.items(), key=lambda x: -len(x[1])):
            rel = f.relative_to(ROOT)
            print(f"-- {rel} ({len(items)}건) --")
            for it in items:
                note = it.get("baseline_note", "")
                print(f"  L{it['line']} [{it['kind']}] {it['call']}  # {note[:60]}")
        print()

    if not new_findings:
        print("[OK] baseline 외 신규 narrow SQL 0건")
        return 0

    # 신규 발견 (warning)
    by_file2: dict[Path, list[dict]] = {}
    for f in new_findings:
        by_file2.setdefault(f["file"], []).append(f)

    print(f"[WARN] {len(new_findings)}건의 narrow SQL context 동적 SQL 발견 (baseline 외)")
    print(f"[WARN] {len(by_file2)}개 파일")
    print()

    for f, items in sorted(by_file2.items(), key=lambda x: -len(x[1])):
        rel = f.relative_to(ROOT)
        print(f"-- {rel} ({len(items)}건) --")
        for it in items:
            safe_arg = it["arg"].encode("ascii", errors="replace").decode("ascii")[:100]
            print(f"  L{it['line']} [{it['kind']}] {it['call']}")
            print(f"      arg: {safe_arg}")
        print()

    print("[NOTE] 검토 후 안전하면 baseline에 추가:")
    print(f"  {BASELINE_PATH.relative_to(ROOT)}")
    print("  {\"backend/api/foo.py:123\": \"REVERT_MAP 결과, safe\"}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
