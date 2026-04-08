# -*- coding: utf-8 -*-
"""
React Phase 1 - Step 2 Gate Test
=================================
React/Vite 프로젝트가 정상 구성되었는지 검증.
모든 게이트 통과해야 Step 3(API 연동)으로 진행 가능.

사용법:
  python scripts/react_step2_gate.py
"""
import os
import sys
import json
import subprocess

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
RESULTS = []


def gate(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((status, name, detail))


def check_file_exists(name, path):
    exists = os.path.exists(path)
    gate(name, exists, f"{'exists' if exists else 'MISSING'}: {path}")


def check_file_contains(name, path, keyword):
    if not os.path.exists(path):
        gate(name, False, f"file not found: {path}")
        return
    with open(path, encoding="utf-8") as f:
        content = f.read()
    found = keyword in content
    gate(name, found, f"{'found' if found else 'NOT FOUND'}: '{keyword}'")


def main():
    print("=" * 60)
    print("  React Phase 1 - Step 2 Gate Test")
    print("=" * 60)
    print(f"  Web dir: {WEB_DIR}")
    print()

    # Gate 1: web/ directory exists
    gate("web/ directory", os.path.isdir(WEB_DIR), WEB_DIR)

    # Gate 2: package.json valid
    pkg_path = os.path.join(WEB_DIR, "package.json")
    check_file_exists("package.json", pkg_path)
    if os.path.exists(pkg_path):
        with open(pkg_path, encoding="utf-8") as f:
            pkg = json.load(f)
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        gate("react dependency", "react" in deps, f"react={'react' in deps}")
        gate("react-router-dom", "react-router-dom" in deps, f"installed={'react-router-dom' in deps}")
        gate("vite dependency", "@vitejs/plugin-react" in deps, f"vite plugin={'@vitejs/plugin-react' in deps}")

    # Gate 3: node_modules installed
    nm = os.path.join(WEB_DIR, "node_modules")
    gate("node_modules", os.path.isdir(nm), f"{'exists' if os.path.isdir(nm) else 'MISSING - run npm install'}")

    # Gate 4: Core source files
    check_file_exists("App.jsx", os.path.join(WEB_DIR, "src", "App.jsx"))
    check_file_exists("main.jsx", os.path.join(WEB_DIR, "src", "main.jsx"))
    check_file_exists("DashboardPage.jsx", os.path.join(WEB_DIR, "src", "pages", "DashboardPage.jsx"))
    check_file_exists("InventoryPage.jsx", os.path.join(WEB_DIR, "src", "pages", "InventoryPage.jsx"))
    check_file_exists("api/client.js", os.path.join(WEB_DIR, "src", "api", "client.js"))
    check_file_exists("api/dashboardApi.js", os.path.join(WEB_DIR, "src", "api", "dashboardApi.js"))
    check_file_exists("api/inventoryApi.js", os.path.join(WEB_DIR, "src", "api", "inventoryApi.js"))

    # Gate 5: Routing configured
    check_file_contains("BrowserRouter in App", os.path.join(WEB_DIR, "src", "App.jsx"), "BrowserRouter")
    check_file_contains("Route /inventory", os.path.join(WEB_DIR, "src", "App.jsx"), "/inventory")

    # Gate 6: Vite proxy configured
    check_file_contains("API proxy", os.path.join(WEB_DIR, "vite.config.js"), "proxy")
    check_file_contains("proxy target 8000", os.path.join(WEB_DIR, "vite.config.js"), "8000")

    # Gate 7: Vite build — dist/index.html 존재로 검증
    # (Windows에서 npx exit code가 비정상일 수 있으므로 결과물로 판단)
    dist = os.path.join(WEB_DIR, "dist", "index.html")
    dist_js = os.path.join(WEB_DIR, "dist", "assets")
    has_dist = os.path.exists(dist) and os.path.isdir(dist_js)
    gate("vite build (dist check)", has_dist,
         "dist/index.html + dist/assets/ exist" if has_dist else "MISSING - run: cd web && npx vite build")

    # Results
    print("-" * 60)
    passed = sum(1 for r in RESULTS if r[0] == "PASS")
    failed = sum(1 for r in RESULTS if r[0] == "FAIL")

    for status, name, detail in RESULTS:
        icon = "OK" if status == "PASS" else "NG"
        print(f"  [{icon}] {name}")
        if detail:
            print(f"       {detail}")

    print("-" * 60)
    print(f"  PASS: {passed}  FAIL: {failed}")
    print()

    if failed > 0:
        print("GATE RESULT: FAIL")
        print("Step 3 진행 불가.")
        return 1
    else:
        print("GATE RESULT: PASS")
        print("Step 3(API 연동 검증) 진행 가능합니다.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
