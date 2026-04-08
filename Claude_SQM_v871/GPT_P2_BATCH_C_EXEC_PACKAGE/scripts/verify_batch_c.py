# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CHECK_FILES = [
    "repositories/base_repository.py",
    "repositories/inventory_repository.py",
    "repositories/inbound_repository.py",
    "repositories/outbound_repository.py",
    "tests/test_base_repository.py",
    "tests/test_inventory_repository.py",
]

def check_exists():
    missing = [p for p in CHECK_FILES if not Path(p).exists()]
    if missing:
        print("[FAIL] missing files")
        for m in missing:
            print(" -", m)
        return False
    print("[PASS] files exist")
    return True

def run_py_compile():
    cmd = [sys.executable, "-m", "py_compile"] + CHECK_FILES[:4]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("[FAIL] py_compile")
        print(result.stdout)
        print(result.stderr)
        return False
    print("[PASS] py_compile")
    return True

def run_pytest():
    cmd = [sys.executable, "-m", "pytest", "tests/test_base_repository.py", "tests/test_inventory_repository.py", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("[FAIL] pytest")
        print(result.stdout)
        print(result.stderr)
        return False
    print("[PASS] pytest")
    print(result.stdout)
    return True

def main():
    ok = True
    ok = check_exists() and ok
    ok = run_py_compile() and ok
    ok = run_pytest() and ok

    if ok:
        print("[FINAL] BATCH C verification PASS")
        sys.exit(0)
    print("[FINAL] BATCH C verification FAIL")
    sys.exit(1)

if __name__ == "__main__":
    main()
