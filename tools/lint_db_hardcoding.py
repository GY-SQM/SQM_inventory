# -*- coding: utf-8 -*-
"""
tools/lint_db_hardcoding.py
============================
SQM v9.0.0 — Phase 2 Step 3: central allowlist 외부 사용 감지 lint

core/db_allowed.py에 정의된 allowlist의 모든 식별자(테이블/컬럼/상태/area/...)
가 backend/ 등 다른 모듈에서 **하드코딩**으로 사용되는지 검사한다.

목적:
    1. central allowlist로 통합해야 할 곳이 빠지지 않았는지 확인
    2. SQL 인젝션 위험이 있는 하드코딩 패턴 사전 감지
    3. CI/PR에 자동 코멘트로 사용 가능 (exit 0/1)

사용법:
    python tools/lint_db_hardcoding.py [TARGET_DIR]
    # default: backend/ (queries3.py, status_revert_api.py, actions3.py, settings.py 등)

Exit code:
    0 — 하드코딩 없음
    1 — 하드코딩 발견 (report 출력)

Note:
    - core/db_allowed.py 자체는 제외 (allowlist 정의 위치)
    - tests/ 는 제외 (테스트가 직접 인용하는 경우)
    - tools/ 도 제외 (본 lint 도구)
    - grep 기반 (AST 파싱 아님, 단순하지만 충분)
"""
import re
import sys
from pathlib import Path

# core/db_allowed.py에서 allowlist import
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from core.db_allowed import (
        ALLOWED_TABLES,
        ALLOWED_STATUS,
        ALLOWED_AREAS,
        ALLOWED_SCOPES,
        LOT_EDIT_FIELDS,
        CARRIER_RULE_EDIT_FIELDS,
        ALLOWED_FILE_EXTS,
    )
except ImportError as e:
    print(f"[ERR] core.db_allowed import 실패: {e}", file=sys.stderr)
    sys.exit(2)

# 검사 대상 식별자 (모든 allowlist 통합)
TARGETS = (
    sorted(ALLOWED_TABLES)
    + sorted(ALLOWED_STATUS)
    + sorted(ALLOWED_AREAS)
    + sorted(ALLOWED_SCOPES)
    + sorted(LOT_EDIT_FIELDS)
    + sorted(CARRIER_RULE_EDIT_FIELDS)
    + sorted(ALLOWED_FILE_EXTS)
)

# 제외 경로 (자기 자신, 테스트, 도구)
EXCLUDE_PATTERNS = (
    r"core/db_allowed\.py$",
    r"tools/.*\.py$",
    r"tests/.*\.py$",
    r"__pycache__",
    r"\.git",
    r"\.pytest_cache",
    r"docs/",
)

# 너무 짧은 식별자 (false positive 방지)
MIN_ID_LEN = 4

# 검사할 디렉토리 (default: backend/)
DEFAULT_TARGET = "backend"


def should_exclude(path: Path) -> bool:
    p = str(path).replace("\\", "/")
    return any(re.search(pat, p) for pat in EXCLUDE_PATTERNS)


def find_hardcoding(target_dir: Path) -> list[tuple[Path, int, str]]:
    """
    target_dir 안의 .py 파일에서 TARGETS의 식별자가 사용된 줄을 찾는다.

    Returns:
        list of (file_path, line_number, line_content) tuples
    """
    hits = []
    targets_to_check = [t for t in TARGETS if len(t) >= MIN_ID_LEN]

    for py_file in target_dir.rglob("*.py"):
        if should_exclude(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        # 라인별로 검색
        for line_no, line in enumerate(content.splitlines(), 1):
            # 너무 짧은 라인 (코멘트) skip
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for target in targets_to_check:
                # word boundary 매칭 (단어 단위로만)
                if re.search(rf"\b{re.escape(target)}\b", line):
                    hits.append((py_file, line_no, line.rstrip()))
                    break  # 한 라인에 하나만 보고
    return hits


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET
    target_dir = (ROOT / target).resolve()

    if not target_dir.exists():
        print(f"[ERR] 디렉토리 없음: {target_dir}", file=sys.stderr)
        sys.exit(2)

    # stdout을 utf-8로 강제 (Windows cp949 인코딩 이슈 회피)
    import io
    if hasattr(sys.stdout, "buffer"):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass

    print(f"[INFO] 검사 대상: {target_dir}")
    print(f"[INFO] 검사 식별자 수: {len(TARGETS)}")
    print()

    hits = find_hardcoding(target_dir)
    if not hits:
        print("[OK] central allowlist 외부 하드코딩 없음")
        return 0

    # 파일별 그룹핑
    by_file: dict[Path, list[tuple[int, str]]] = {}
    for f, ln, content in hits:
        by_file.setdefault(f, []).append((ln, content))

    print(f"[WARN] {len(hits)}건의 central allowlist 식별자 사용 발견")
    print(f"[WARN] {len(by_file)}개 파일에 분산")
    print()

    # top 5개 파일만 표시 (너무 많으면 노이즈)
    sorted_files = sorted(by_file.items(), key=lambda x: -len(x[1]))[:5]
    for f, lines in sorted_files:
        rel = f.relative_to(ROOT)
        print(f"-- {rel} ({len(lines)}건) --")
        for ln, content in lines[:3]:  # 파일당 3건만
            safe = content.encode("ascii", errors="replace").decode("ascii")[:120]
            print(f"  L{ln}: {safe}")
        if len(lines) > 3:
            print(f"  ... ({len(lines) - 3}건 더)")
        print()

    print("[NOTE] 각 사용처는 다음 중 하나여야 함:")
    print("  1. from core.db_allowed import ... (이미 central 사용)")
    print("  2. 의도된 하드코딩 (테스트 fixture, docstring, etc.)")
    print("  3. false positive - ignore 등록 필요")
    return 1


if __name__ == "__main__":
    sys.exit(main())
