# -*- coding: utf-8 -*-
"""저장소 전역: is_dark = is_dark() name shadowing 일괄 수정.

- import / is_dark() 호출 / 키워드 인자 is_dark= 는 유지
- 대입만 dark_mode 로 바꾼 뒤, 흔한 참조 패턴만 치환
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# 건너뜀 (너무 크거나 샘플)
SKIP_DIR_PARTS = {
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
}


ASSIGN_TERNARY = re.compile(
    r"^(\s*)is_dark\s*=\s*is_dark\s*\(\)\s*if\s+ThemeColors\s+else\s+False\s*(#.*)?$",
    re.MULTILINE,
)
ASSIGN_CALL = re.compile(
    r"^(\s*)is_dark\s*=\s*is_dark\s*\(\)\s*(#.*)?$",
    re.MULTILINE,
)


def patch_text(src: str) -> tuple[str, int]:
    if "is_dark" not in src or "is_dark =" not in src:
        return src, 0
    before = src
    n = 0

    def _sub_str(pat: re.Pattern, repl: str, s: str) -> tuple[str, int]:
        out, c = pat.subn(repl, s)
        return out, c

    def _repl_tern(m: re.Match[str]) -> str:
        c = m.group(2) or ""
        return f"{m.group(1)}dark_mode = is_dark() if ThemeColors else False{c}"

    src, a = ASSIGN_TERNARY.subn(_repl_tern, src)
    n += a

    def _repl_assign(m: re.Match[str]) -> str:
        comment = m.group(2) or ""
        return f"{m.group(1)}dark_mode = is_dark(){comment}"

    src, b = ASSIGN_CALL.subn(_repl_assign, src)
    n += b
    if n == 0:
        return before, 0

    # 흔한 참조 (import 줄은 보통 'is_dark' 가 = 없이 등장 — 아래는 ',' 뒤·if 뒤 위주)
    reps = [
        (re.compile(r",\s*is_dark\)"), ", dark_mode)"),
        (re.compile(r"\bif\s+is_dark\s*:"), "if dark_mode:"),
        (re.compile(r"\belif\s+is_dark\s*:"), "elif dark_mode:"),
        (re.compile(r"\bif\s+not\s+is_dark\s*:"), "if not dark_mode:"),
        (re.compile(r"\bif\s+is_dark\s+else\b"), "if dark_mode else"),
    ]
    for rx, to in reps:
        src, _ = rx.subn(to, src)

    # 잔여: " fg=... is_dark)" 등 — 한 번 더 ", is_dark)" (이미 치환된 것 제외)
    src = re.sub(r",\s*is_dark\)", ", dark_mode)", src)

    # `... if is_dark else` (키워드 if 앞이 아닌 삼항) — 남은 패턴
    src = re.sub(r"\s+if\s+is_dark\s+else\b", " if dark_mode else", src)

    changed = 1 if src != before else 0
    return src, changed


def walk(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*.py"):
        parts = set(p.parts)
        if parts & SKIP_DIR_PARTS:
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if ASSIGN_TERNARY.search(t) or ASSIGN_CALL.search(t):
            out.append(p)
    return sorted(out)


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--dry"]
    root = (
        Path(args[0]).resolve()
        if args
        else Path(__file__).resolve().parents[2]
    )
    dry = "--dry" in sys.argv
    files = walk(root)
    patched = 0
    for fp in files:
        text = fp.read_text(encoding="utf-8", errors="ignore")
        new, _ = patch_text(text)
        if new != text:
            patched += 1
            if not dry:
                fp.write_text(new, encoding="utf-8", newline="\n")
            print(f"{'[dry] ' if dry else ''}{fp}")
    print(f"TOTAL_MATCH_FILES={len(files)} PATCHED={patched} root={root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
