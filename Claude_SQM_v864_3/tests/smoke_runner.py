"""
Phase 5-C: Smoke scenario runner.
Checks only the LATEST boot session in the log file.
Usage: python tests/smoke_runner.py [log_file]
Exit 0 = all markers found. Exit 1 = missing markers.
"""
import sys
import pathlib

REQUIRED_MARKERS = [
    "[ENGINE] primary loaded",
    "[AUTO-RECOVERY]",
    "[STARTUP]",
    "[STARTUP] \ud1a4\ubc31 \uc0c1\ud0dc \uc815\ud569\uc131 OK",
]

NEGATIVE_MARKERS = [
    "[SAFETY-HOLD]",
]


def extract_latest_session(lines):
    """Return lines from the last boot (last [ENGINE] primary loaded onward)."""
    last_boot = 0
    for i, line in enumerate(lines):
        if "[ENGINE] primary loaded" in line:
            last_boot = i
    return lines[last_boot:]


def run(log_path: str) -> int:
    path = pathlib.Path(log_path)
    if not path.exists():
        print(f"[smoke_runner] log file not found: {log_path}")
        print("[smoke_runner] Run: python run.py > stdout_smoke.txt 2>&1")
        return 1

    content = path.read_text(encoding="utf-8", errors="replace")
    all_lines = content.splitlines()
    lines = extract_latest_session(all_lines)

    print(f"[smoke_runner] {path.name} total={len(all_lines)} / latest session={len(lines)} lines\n")

    ok = True
    for marker in REQUIRED_MARKERS:
        found = any(marker in line for line in lines)
        status = "PASS" if found else "FAIL"
        print(f"  [{status}] required: {marker!r}")
        if not found:
            ok = False

    print()
    for marker in NEGATIVE_MARKERS:
        found = any(marker in line for line in lines)
        status = "FAIL (unexpected)" if found else "PASS"
        print(f"  [{status}] negative: {marker!r}")
        if found:
            ok = False
            for line in lines:
                if marker in line:
                    print(f"         -> {line.strip()}")
            break

    print()
    if ok:
        print("[smoke_runner] PASS - all markers OK")
    else:
        print("[smoke_runner] FAIL - check above")
    return 0 if ok else 1


if __name__ == "__main__":
    log_file = sys.argv[1] if len(sys.argv) > 1 else "stdout_smoke.txt"
    sys.exit(run(log_file))
