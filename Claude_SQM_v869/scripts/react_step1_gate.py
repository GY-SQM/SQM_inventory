# -*- coding: utf-8 -*-
"""
React Phase 1 - Step 1 Gate Test
=================================
API 서버가 정상 동작하는지 검증하는 스크립트.
모든 게이트 통과해야 Step 2(React 설치)로 진행 가능.

사용법:
  1) 터미널 1: cd Claude_SQM_v865 && uvicorn GPT_SQM_React_Phase1_Draft.api.main:app --port 8000
  2) 터미널 2: python scripts/react_step1_gate.py
"""
import json
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8080"
RESULTS = []


def check(name: str, url: str, expect_keys: list = None, expect_status: int = 200):
    """단일 엔드포인트 검증."""
    full_url = f"{BASE_URL}{url}"
    try:
        req = urllib.request.Request(full_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))

        if status != expect_status:
            RESULTS.append(("FAIL", name, f"status={status}, expected={expect_status}"))
            return

        if expect_keys:
            missing = [k for k in expect_keys if k not in body]
            if missing:
                RESULTS.append(("FAIL", name, f"missing keys: {missing}"))
                return

        RESULTS.append(("PASS", name, f"status={status}, keys OK"))

    except urllib.error.HTTPError as e:
        if expect_status and e.code == expect_status:
            RESULTS.append(("PASS", name, f"expected {e.code}"))
        else:
            RESULTS.append(("FAIL", name, f"HTTP {e.code}: {e.reason}"))
    except urllib.error.URLError as e:
        RESULTS.append(("FAIL", name, f"연결 실패: {e.reason}"))
    except Exception as e:
        RESULTS.append(("FAIL", name, f"예외: {e}"))


def check_lot_detail():
    """LOT 상세 - 실제 LOT 번호를 먼저 찾아서 검증."""
    try:
        url = f"{BASE_URL}/api/inventory/search?page=1&page_size=1"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        rows = body.get("rows", [])
        if not rows:
            RESULTS.append(("WARN", "lot_detail", "검색 결과 없음 — LOT 상세 스킵"))
            return
        lot_no = rows[0].get("lot_no", "")
        if not lot_no:
            RESULTS.append(("WARN", "lot_detail", "lot_no 비어있음"))
            return
        check(
            "GET /api/inventory/lot/{lot_no}",
            f"/api/inventory/lot/{lot_no}",
            expect_keys=["lot_no", "tonbags", "status_summary", "generated_at"],
        )
    except Exception as e:
        RESULTS.append(("FAIL", "lot_detail", f"예외: {e}"))


def check_tkinter_no_conflict():
    """tkinter 앱 import가 API와 충돌하지 않는지 간접 확인."""
    try:
        import importlib
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        mod = importlib.import_module("config")
        db_path = getattr(mod, "DB_PATH", None)
        if db_path and os.path.exists(str(db_path)):
            RESULTS.append(("PASS", "tkinter_compat", f"DB_PATH 접근 가능: {db_path}"))
        else:
            RESULTS.append(("WARN", "tkinter_compat", f"DB_PATH 미확인: {db_path}"))
    except Exception as e:
        RESULTS.append(("FAIL", "tkinter_compat", f"config import 실패: {e}"))


def main():
    print("=" * 60)
    print("  React Phase 1 - Step 1 Gate Test")
    print("=" * 60)
    print(f"  Target: {BASE_URL}")
    print()

    # Gate 1: 서버 연결
    check("GET /api/health", "/api/health", expect_keys=["ok", "service"])

    # 서버 연결 실패 시 즉시 중단
    if RESULTS and RESULTS[0][0] == "FAIL":
        print("  [FAIL] API 서버 연결 실패!")
        print(f"         {RESULTS[0][2]}")
        print()
        print("  서버를 먼저 실행하세요:")
        print("  cd Claude_SQM_v865")
        print("  uvicorn GPT_SQM_React_Phase1_Draft.api.main:app --port 8000")
        print()
        print("GATE RESULT: FAIL")
        return 1

    # Gate 2: Dashboard 엔드포인트
    check("GET /api/dashboard/summary", "/api/dashboard/summary",
          expect_keys=["items", "totals", "generated_at"])
    check("GET /api/dashboard/by-product", "/api/dashboard/by-product",
          expect_keys=["rows", "generated_at"])
    check("GET /api/dashboard/location-summary", "/api/dashboard/location-summary",
          expect_keys=["rows", "generated_at"])

    # Gate 3: Inventory 엔드포인트
    check("GET /api/inventory/filters", "/api/inventory/filters",
          expect_keys=["statuses", "products", "locations"])
    check("GET /api/inventory/search", "/api/inventory/search?page=1&page_size=5",
          expect_keys=["total", "rows", "page", "page_size"])

    # Gate 4: LOT 상세 (동적 LOT 번호)
    check_lot_detail()

    # Gate 5: tkinter 호환성
    check_tkinter_no_conflict()

    # 결과 출력
    print("-" * 60)
    passed = sum(1 for r in RESULTS if r[0] == "PASS")
    failed = sum(1 for r in RESULTS if r[0] == "FAIL")
    warned = sum(1 for r in RESULTS if r[0] == "WARN")

    for status, name, detail in RESULTS:
        icon = {"PASS": "OK", "FAIL": "NG", "WARN": "??"}[status]
        print(f"  [{icon}] {name}")
        print(f"       {detail}")

    print("-" * 60)
    print(f"  PASS: {passed}  FAIL: {failed}  WARN: {warned}")
    print()

    if failed > 0:
        print("GATE RESULT: FAIL")
        print("Step 2 진행 불가 — 위 실패 항목을 먼저 수정하세요.")
        return 1
    else:
        print("GATE RESULT: PASS")
        print("Step 2(React 설치) 진행 가능합니다.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
