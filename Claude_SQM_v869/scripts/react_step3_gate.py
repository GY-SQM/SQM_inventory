# -*- coding: utf-8 -*-
"""
React Phase 1 - Step 3 Gate Test
=================================
API + React 연동이 정상 동작하는지 검증.

사전 조건:
  1) uvicorn react_api.main:app --port 8000  (실행 중)
  2) cd web && npx vite --port 5173          (실행 중)

사용법:
  python scripts/react_step3_gate.py
"""
import json
import sys
import urllib.request
import urllib.error

API_URL = "http://127.0.0.1:8080"
VITE_URL = "http://localhost:5173"
RESULTS = []


def gate(name, passed, detail=""):
    RESULTS.append(("PASS" if passed else "FAIL", name, detail))


def fetch(url, timeout=10):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def fetch_text(url, timeout=10):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8")


def main():
    print("=" * 60)
    print("  React Phase 1 - Step 3 Gate Test")
    print("=" * 60)
    print(f"  API:  {API_URL}")
    print(f"  Vite: {VITE_URL}")
    print()

    # ── Gate 1: API 서버 직접 접근 ──
    try:
        code, data = fetch(f"{API_URL}/api/health")
        gate("API direct: /api/health", code == 200 and data.get("ok"), f"status={code}")
    except Exception as e:
        gate("API direct: /api/health", False, f"API 서버 연결 실패: {e}")
        print("  [FAIL] API 서버가 실행되지 않았습니다.")
        print(f"  실행: cd Claude_SQM_v865 && uvicorn react_api.main:app --port 8000")
        print("\nGATE RESULT: FAIL")
        return 1

    # ── Gate 2: Vite 서버 접근 ──
    try:
        code, html = fetch_text(f"{VITE_URL}/")
        has_root = '<div id="root">' in html
        gate("Vite: HTML load", code == 200 and has_root, f"status={code}, root div={'found' if has_root else 'MISSING'}")
    except Exception as e:
        gate("Vite: HTML load", False, f"Vite 서버 연결 실패: {e}")
        print("  [FAIL] Vite dev 서버가 실행되지 않았습니다.")
        print(f"  실행: cd Claude_SQM_v865/web && npx vite --port 5173")
        print("\nGATE RESULT: FAIL")
        return 1

    # ── Gate 3: Vite 프록시를 통한 API 접근 ──
    try:
        code, data = fetch(f"{VITE_URL}/api/health")
        gate("Proxy: /api/health", code == 200 and data.get("ok"), f"proxy OK")
    except Exception as e:
        gate("Proxy: /api/health", False, f"proxy 실패: {e}")

    # ── Gate 4: Dashboard 데이터 ──
    try:
        code, data = fetch(f"{VITE_URL}/api/dashboard/summary")
        items = data.get("items", [])
        totals = data.get("totals", {})
        bag_count = totals.get("bag_count", 0)
        gate("Dashboard: summary", code == 200 and len(items) > 0,
             f"statuses={len(items)}, bags={bag_count}")
    except Exception as e:
        gate("Dashboard: summary", False, str(e))

    try:
        code, data = fetch(f"{VITE_URL}/api/dashboard/by-product")
        rows = data.get("rows", [])
        gate("Dashboard: by-product", code == 200 and len(rows) > 0,
             f"products={len(rows)}")
    except Exception as e:
        gate("Dashboard: by-product", False, str(e))

    try:
        code, data = fetch(f"{VITE_URL}/api/dashboard/location-summary")
        rows = data.get("rows", [])
        gate("Dashboard: location-summary", code == 200,
             f"locations={len(rows)}")
    except Exception as e:
        gate("Dashboard: location-summary", False, str(e))

    # ── Gate 5: Inventory 데이터 ──
    try:
        code, data = fetch(f"{VITE_URL}/api/inventory/filters")
        statuses = data.get("statuses", [])
        products = data.get("products", [])
        gate("Inventory: filters", code == 200 and len(statuses) > 0,
             f"statuses={statuses}, products={len(products)}")
    except Exception as e:
        gate("Inventory: filters", False, str(e))

    try:
        code, data = fetch(f"{VITE_URL}/api/inventory/search?page=1&page_size=5")
        total = data.get("total", 0)
        rows = data.get("rows", [])
        gate("Inventory: search", code == 200 and total > 0,
             f"total={total}, returned={len(rows)}")
    except Exception as e:
        gate("Inventory: search", False, str(e))

    # ── Gate 6: LOT 상세 (동적) ──
    try:
        _, search_data = fetch(f"{VITE_URL}/api/inventory/search?page=1&page_size=1")
        lot_no = search_data.get("rows", [{}])[0].get("lot_no", "")
        if lot_no:
            code, data = fetch(f"{VITE_URL}/api/inventory/lot/{lot_no}")
            tb_count = len(data.get("tonbags", []))
            gate("Inventory: lot detail", code == 200 and tb_count > 0,
                 f"lot={lot_no}, tonbags={tb_count}")
        else:
            gate("Inventory: lot detail", False, "no lot_no found")
    except Exception as e:
        gate("Inventory: lot detail", False, str(e))

    # ── Gate 7: SOLD->OUTBOUND 정규화 확인 ──
    try:
        _, data = fetch(f"{VITE_URL}/api/inventory/filters")
        statuses = data.get("statuses", [])
        has_sold = "SOLD" in statuses
        # OUTBOUND가 없을 수 있음 (데이터에 해당 상태가 없으면 정상)
        # 핵심 검증: SOLD가 필터에 노출되면 안 됨
        gate("Status normalization",
             not has_sold,
             f"SOLD in filters={'Y (BAD)' if has_sold else 'N (GOOD)'}, statuses={statuses}")
    except Exception as e:
        gate("Status normalization", False, str(e))

    # ── Gate 8: React 번들 로드 ──
    try:
        _, html = fetch_text(f"{VITE_URL}/")
        has_main = "main.jsx" in html or "main.js" in html
        gate("React bundle", has_main, f"main.jsx ref={'found' if has_main else 'MISSING'}")
    except Exception as e:
        gate("React bundle", False, str(e))

    # ── 결과 출력 ──
    print("-" * 60)
    passed = sum(1 for r in RESULTS if r[0] == "PASS")
    failed = sum(1 for r in RESULTS if r[0] == "FAIL")

    for status, name, detail in RESULTS:
        icon = "OK" if status == "PASS" else "NG"
        print(f"  [{icon}] {name}")
        print(f"       {detail}")

    print("-" * 60)
    print(f"  PASS: {passed}  FAIL: {failed}")
    print()

    if failed > 0:
        print("GATE RESULT: FAIL")
        print("Step 4 진행 불가.")
        return 1
    else:
        print("GATE RESULT: PASS")
        print("Step 4(리팩토링 지시서 실행) 진행 가능합니다.")
        print()
        print("브라우저에서 확인:")
        print(f"  Dashboard:  {VITE_URL}/")
        print(f"  Inventory:  {VITE_URL}/inventory")
        return 0


if __name__ == "__main__":
    sys.exit(main())
