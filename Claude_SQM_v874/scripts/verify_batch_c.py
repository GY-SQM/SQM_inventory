# -*- coding: utf-8 -*-
"""P2 Batch C 검증 자동화 스크립트."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


CHECK_FILES = [
    "features/repositories/base_repository.py",
    "features/repositories/inventory_repository.py",
    "features/repositories/inbound_repository.py",
    "engine_modules/inventory_modular/outbound_query.py",
    "engine_modules/inventory_modular/outbound_repository.py",
    "engine_modules/inventory_modular/outbound_service.py",
    "engine_modules/inventory_modular/outbound_state_rules.py",
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
    py_files = [f for f in CHECK_FILES if not f.startswith("tests/")]
    cmd = [sys.executable, "-m", "py_compile"] + py_files
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("[FAIL] py_compile")
        print(result.stdout)
        print(result.stderr)
        return False
    print("[PASS] py_compile")
    return True


def run_pytest():
    test_files = [
        "tests/test_base_repository.py",
        "tests/test_inventory_repository.py",
        "tests/test_p2_inbound_refactor.py",
        "tests/test_outbound_batch_b.py",
    ]
    existing = [f for f in test_files if Path(f).exists()]
    cmd = [sys.executable, "-m", "pytest"] + existing + ["-q"]
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
