"""
Phase B: 1000 LOT x 10 tonbag 부하 테스트 DB 생성 + API 응답 시간 측정
=========================================================================
실행:
    python scripts/seed_load_test_db.py --seed      # DB 시드 생성
    python scripts/seed_load_test_db.py --bench     # 응답 시간만 측정
    python scripts/seed_load_test_db.py             # 시드 + 벤치마크
"""
import sys
import io
import json
import random
import string
import sqlite3
import time
import argparse
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "db" / "sqm_inventory.db"
REPORTS_DIR = PROJECT_ROOT / "REPORTS"
REPORTS_DIR.mkdir(exist_ok=True)

# ── 임계값 ──
THRESHOLD_GENERAL_MS = 3000   # 일반 엔드포인트 < 3s
THRESHOLD_SEARCH_MS = 500     # global-search < 500ms

PRODUCTS = [
    "LITHIUM CARBONATE", "LITHIUM HYDROXIDE", "COBALT SULFATE",
    "NICKEL SULFATE", "MANGANESE SULFATE", "IRON PHOSPHATE",
]
WAREHOUSES = ["A창고", "B창고", "C창고", "D창고"]
STATUSES = ["AVAILABLE", "ALLOCATED", "OUTBOUND", "HOLD"]


def rand_str(prefix: str, n: int = 10) -> str:
    return prefix + "".join(random.choices(string.digits, k=n))


def seed_db(target_lots: int = 1000, tonbags_per_lot: int = 10):
    """테스트 LOT 데이터 삽입. 기존 실 데이터는 건드리지 않음."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 현재 행 수 확인
    cur.execute("SELECT COUNT(*) FROM inventory")
    existing_lots = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM inventory_tonbag")
    existing_tonbags = cur.fetchone()[0]
    print(f"현재 DB: {existing_lots} LOT / {existing_tonbags} tonbag")

    # 이미 테스트 시드가 있으면 삭제
    cur.execute("DELETE FROM inventory_tonbag WHERE lot_no LIKE 'TEST_%'")
    cur.execute("DELETE FROM inventory WHERE lot_no LIKE 'TEST_%'")
    conn.commit()
    print(f"기존 테스트 LOT 삭제 완료")

    # 1000개 LOT 삽입
    print(f"{target_lots} LOT x {tonbags_per_lot} tonbag 시드 삽입 중...")
    t0 = time.time()

    lot_rows = []
    tonbag_rows = []
    now_ts = "2026-04-26 00:00:00"

    for i in range(target_lots):
        lot_no = f"TEST_{i:06d}"
        product = random.choice(PRODUCTS)
        net_wt = round(random.uniform(2000, 10000), 2)
        lot_rows.append((
            lot_no,                          # lot_no
            f"SQM{i:07d}",                   # lot_sqm
            f"22000{i:05d}",                 # sap_no
            f"BL{i:010d}",                   # bl_no
            f"CONT{i:010d}",                 # container_no
            product,                         # product
            "TEST-CODE",                     # product_code
            net_wt,                          # net_weight
            round(net_wt * 1.026, 2),        # gross_weight
            net_wt,                          # initial_weight
            net_wt,                          # current_weight
            0.0,                             # picked_weight
            tonbags_per_lot,                 # mxbg_pallet (approx)
            tonbags_per_lot,                 # tonbag_count
            "2026-01-01",                    # ship_date
            "2026-03-01",                    # arrival_date
            "2026-03-02",                    # stock_date
            f"INV{i:07d}",                   # salar_invoice_no
            random.choice(WAREHOUSES),       # warehouse
            random.choice(STATUSES),         # status
            None, None, None, None,          # sold_to, sale_ref, vessel, free_time
            None, None, None, None,          # con_return, location, customs, inbound_date
            None,                            # remarks
            now_ts, now_ts,                  # created_at, updated_at
            None, None, None, None, None, None,  # voyage, do_no, invoice_date, total_amount, currency, unit_price
        ))

        wt_each = round(net_wt / tonbags_per_lot, 2)
        for j in range(tonbags_per_lot):
            tonbag_rows.append((
                None,                        # inventory_id (will be filled after INSERT)
                lot_no,                      # lot_no
                f"22000{i:05d}",             # sap_no
                f"BL{i:010d}",               # bl_no
                "2026-03-02",                # inbound_date
                j + 1,                       # sub_lt (integer)
                wt_each,                     # weight
                0,                           # is_sample
                "AVAILABLE",                 # status
                random.choice(WAREHOUSES),   # location
                now_ts,                      # location_updated_at
                None, None, None,            # picked_to, picked_date, pick_ref
                f"TEST_UID_{i:06d}_{j:03d}", # tonbag_uid (unique)
            ))

    # Batch insert LOTs
    cur.executemany("""
        INSERT INTO inventory (
            lot_no, lot_sqm, sap_no, bl_no, container_no, product, product_code,
            net_weight, gross_weight, initial_weight, current_weight, picked_weight,
            mxbg_pallet, tonbag_count, ship_date, arrival_date, stock_date,
            salar_invoice_no, warehouse, status, sold_to, sale_ref, vessel, free_time,
            con_return, location, customs, inbound_date, remarks, created_at, updated_at,
            voyage, do_no, invoice_date, total_amount, currency, unit_price
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, lot_rows)
    conn.commit()

    # tonbag insert에 inventory_id 채우기
    cur.execute("SELECT id, lot_no FROM inventory WHERE lot_no LIKE 'TEST_%'")
    lot_id_map = {row[1]: row[0] for row in cur.fetchall()}

    filled_tonbags = []
    for tb in tonbag_rows:
        inv_id = lot_id_map.get(tb[1])  # tb[1] = lot_no
        # tb[0] was placeholder None for inventory_id, replace with real id
        filled_tonbags.append((inv_id,) + tb[1:])

    cur.executemany("""
        INSERT INTO inventory_tonbag (
            inventory_id, lot_no, sap_no, bl_no, inbound_date, sub_lt,
            weight, is_sample, status, location, location_updated_at,
            picked_to, picked_date, pick_ref, tonbag_uid
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, filled_tonbags)
    conn.commit()
    conn.close()

    elapsed = time.time() - t0
    total_tonbags = target_lots * tonbags_per_lot
    print(f"시드 완료: {target_lots} LOT / {total_tonbags} tonbag ({elapsed:.1f}s)")
    return {"lots_inserted": target_lots, "tonbags_inserted": total_tonbags, "elapsed_s": round(elapsed, 2)}


def bench_endpoints(repeat: int = 3) -> dict:
    """API 응답 시간 측정"""
    try:
        import requests
    except ImportError:
        return {"error": "requests not installed"}

    endpoints = [
        ("GET", "/api/inventory", "inventory_24col"),
        ("GET", "/api/q/global-search?q=LITHIUM", "global_search"),
        ("GET", "/api/action/integrity-report", "integrity_report"),
        ("GET", "/api/dashboard/stats", "dashboard_stats"),
        ("GET", "/api/health", "health"),
    ]

    results = {}
    print(f"\n응답 시간 측정 (repeat={repeat}):")
    print(f"  {'엔드포인트':<45} {'avg':>8} {'min':>8} {'max':>8} {'판정'}")
    print(f"  {'-'*45} {'-'*8} {'-'*8} {'-'*8} {'-'*6}")

    all_pass = True
    for method, path, name in endpoints:
        times_ms = []
        last_status = None
        for _ in range(repeat):
            t0 = time.time()
            try:
                r = requests.get(f"http://127.0.0.1:8765{path}", timeout=10)
                last_status = r.status_code
            except Exception as e:
                last_status = 0
            elapsed_ms = (time.time() - t0) * 1000
            times_ms.append(elapsed_ms)
            time.sleep(0.1)

        avg = sum(times_ms) / len(times_ms)
        mn = min(times_ms)
        mx = max(times_ms)

        # 임계값 판정
        threshold = THRESHOLD_SEARCH_MS if "search" in path else THRESHOLD_GENERAL_MS
        verdict = "PASS" if avg < threshold else "FAIL"
        if verdict == "FAIL":
            all_pass = False

        print(f"  {path:<45} {avg:>7.0f}ms {mn:>7.0f}ms {mx:>7.0f}ms  {verdict}")
        results[name] = {
            "path": path,
            "avg_ms": round(avg, 1),
            "min_ms": round(mn, 1),
            "max_ms": round(mx, 1),
            "threshold_ms": threshold,
            "last_status": last_status,
            "pass": verdict == "PASS",
        }

    results["_all_pass"] = all_pass
    return results


def cleanup_test_data():
    """테스트 데이터 삭제"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("DELETE FROM inventory_tonbag WHERE lot_no LIKE 'TEST_%'")
    tb_deleted = cur.rowcount
    cur.execute("DELETE FROM inventory WHERE lot_no LIKE 'TEST_%'")
    lot_deleted = cur.rowcount
    conn.commit()
    conn.close()
    print(f"테스트 데이터 정리: {lot_deleted} LOT / {tb_deleted} tonbag 삭제")
    return {"lots_deleted": lot_deleted, "tonbags_deleted": tb_deleted}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help="시드 데이터만 삽입")
    parser.add_argument("--bench", action="store_true", help="벤치마크만 실행")
    parser.add_argument("--cleanup", action="store_true", help="테스트 데이터 삭제")
    parser.add_argument("--lots", type=int, default=1000, help="LOT 수 (기본 1000)")
    parser.add_argument("--tonbags", type=int, default=10, help="LOT당 tonbag 수 (기본 10)")
    args = parser.parse_args()

    if args.cleanup:
        cleanup_test_data()
        return 0

    print("=" * 60)
    print("Phase B: 부하 테스트 — 대용량 데이터셋")
    print("=" * 60)

    report = {
        "phase": "B",
        "title": "부하 테스트 (1000+ LOT)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "thresholds": {
            "general_ms": THRESHOLD_GENERAL_MS,
            "search_ms": THRESHOLD_SEARCH_MS,
        },
    }

    # 1. 기존 데이터 기준 벤치마크
    print(f"\n[Phase B.1] 현재 DB ({42}LOT) 기준 벤치마크...")
    bench_before = bench_endpoints()
    report["bench_before"] = bench_before

    # 2. 시드 삽입 (--bench만이면 건너뜀)
    if not args.bench:
        print(f"\n[Phase B.2] {args.lots} LOT x {args.tonbags} tonbag 시드 삽입...")
        seed_result = seed_db(args.lots, args.tonbags)
        report["seed"] = seed_result

        # 3. 대용량 DB 기준 벤치마크
        print(f"\n[Phase B.3] {args.lots + 42} LOT 기준 벤치마크...")
        bench_after = bench_endpoints()
        report["bench_after"] = bench_after

        # 4. 정리
        print(f"\n[Phase B.4] 테스트 데이터 정리...")
        cleanup = cleanup_test_data()
        report["cleanup"] = cleanup
    else:
        bench_after = bench_before

    # 결과 판정
    all_pass = bench_after.get("_all_pass", False)
    failed = [name for name, r in bench_after.items()
              if name != "_all_pass" and isinstance(r, dict) and not r.get("pass", True)]

    print(f"\n{'='*60}")
    print(f"Phase B 결과: {'PASS' if all_pass else 'FAIL'}")
    if failed:
        print(f"  임계값 초과 엔드포인트: {failed}")
    print(f"{'='*60}")

    report["summary"] = {
        "overall_pass": all_pass,
        "failed_endpoints": failed,
    }

    report_path = REPORTS_DIR / "load_test.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {report_path}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
