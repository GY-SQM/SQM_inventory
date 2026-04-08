# -*- coding: utf-8 -*-
"""자동 수복 체계 — npm build / pytest 실패 자동 진단."""
import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_pytest():
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', 'tests/', '-q', '--tb=short'],
        cwd=BASE_DIR, capture_output=True, text=True, timeout=120,
    )
    return result.returncode == 0, result.stdout + result.stderr


def run_npm_build():
    web_dir = os.path.join(BASE_DIR, 'web')
    result = subprocess.run(
        ['npm', 'run', 'build'],
        cwd=web_dir, capture_output=True, text=True, timeout=120,
        shell=True,
    )
    return result.returncode == 0, result.stdout + result.stderr


def diagnose():
    print("=== Auto Repair Diagnosis ===")
    pytest_ok, pytest_out = run_pytest()
    print(f"pytest: {'PASS' if pytest_ok else 'FAIL'}")
    if not pytest_ok:
        print(pytest_out[-500:])

    build_ok, build_out = run_npm_build()
    print(f"npm build: {'PASS' if build_ok else 'FAIL'}")
    if not build_ok:
        print(build_out[-500:])

    if pytest_ok and build_ok:
        print("All systems OK")
    return pytest_ok and build_ok


if __name__ == '__main__':
    ok = diagnose()
    sys.exit(0 if ok else 1)
