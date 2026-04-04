#!/usr/bin/env python3
"""B10 Quality Script: Scan for bare except / silent pass patterns.

Scans all .py files under project root (excluding GPT_SQM_React*, tests/, reports/)
for the following patterns:
  - except: pass
  - except Exception: pass  (without logging)
  - except:  (bare except without any specific exception type)
"""
import os
import re
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXCLUDE_DIRS = {"GPT_SQM_React_Phase1_Draft", "GPT_SQM_React_Phase1_Runnable_Set",
                "tests", "reports", "__pycache__", ".git", "backup", "temp",
                "GPT_auto_tasks", "GPT_SQM_Claude_B00_B13_FullPack",
                "GPT_Run_All_Claude_Stages_with_Telegram"}

# Patterns ranked by severity
PATTERNS = [
    ("CRITICAL", re.compile(r"^\s*except\s*:\s*pass\s*(#.*)?$"),
     "bare except: pass"),
    ("HIGH", re.compile(r"^\s*except\s+Exception\s*:\s*pass\s*(#.*)?$"),
     "except Exception: pass (silent swallow)"),
    ("MEDIUM", re.compile(r"^\s*except\s*:\s*$"),
     "bare except: (no type specified)"),
    ("LOW", re.compile(r"^\s*except\s+Exception\s*:\s*$"),
     "except Exception: (broad catch, check body)"),
]


def should_skip(dirpath: str) -> bool:
    parts = os.path.normpath(dirpath).split(os.sep)
    return any(d in EXCLUDE_DIRS for d in parts)


def scan_file(filepath: str):
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return findings

    for i, line in enumerate(lines, start=1):
        for severity, pat, desc in PATTERNS:
            if pat.match(line):
                findings.append({
                    "file": filepath,
                    "line": i,
                    "severity": severity,
                    "pattern": desc,
                    "code": line.rstrip(),
                })
    return findings


def main():
    all_findings = []
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        # Prune excluded dirs
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        if should_skip(dirpath):
            continue
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(dirpath, fn)
            all_findings.extend(scan_file(fp))

    # Print report
    print(f"=== Bare Except / Silent Pass Scan ===")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Total findings: {len(all_findings)}")
    print()

    by_severity = {}
    for f in all_findings:
        by_severity.setdefault(f["severity"], []).append(f)

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        items = by_severity.get(sev, [])
        if items:
            print(f"--- {sev} ({len(items)} findings) ---")
            for item in items:
                relpath = os.path.relpath(item["file"], PROJECT_ROOT)
                print(f"  {relpath}:{item['line']}  {item['pattern']}")
                print(f"    {item['code']}")
            print()

    if not all_findings:
        print("No bare except / silent pass patterns found.")

    # Summary counts
    print("=== Summary ===")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        print(f"  {sev}: {len(by_severity.get(sev, []))}")
    print(f"  TOTAL: {len(all_findings)}")

    return 0 if len(by_severity.get("CRITICAL", [])) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
