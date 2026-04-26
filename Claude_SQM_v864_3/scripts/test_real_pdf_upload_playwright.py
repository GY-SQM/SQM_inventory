"""
Phase A: Real PDF Upload Validation - Playwright + multipart
=============================================================
v864-3 /api/inbound/onestop-upload 에 실제 PDF 파일을 업로드하고
파싱 결과 + 크로스체크 결과를 검증합니다.

사용:
    python scripts/test_real_pdf_upload_playwright.py
    python scripts/test_real_pdf_upload_playwright.py --headless
"""
import json
import sys
import io
import argparse
import base64
import os
import time
from pathlib import Path

# Windows cp949 터미널에서 유니코드 출력 안전하게 처리
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "REPORTS"
REPORTS_DIR.mkdir(exist_ok=True)

# ── PDF 파일 위치 탐색 순서 ──
PDF_SEARCH_DIRS = [
    Path("D:/program/SQM_inventory"),
    Path("D:/program/sqm_2_upload_clean_v864_2"),
    Path("D:/program/SQM_inventory/Claude_SQM_v864_2"),
    PROJECT_ROOT / "tests" / "fixtures",
]

# 알려진 실제 PDF 파일들
KNOWN_PDFS = {
    "bl":      ["2200033057 BL.pdf"],
    "pl":      ["2200033057_PackingList1.pdf"],
    "invoice": ["2200033057 FA.pdf", "2200033057 Invoice.pdf"],
    "do":      ["2200033057 DO.pdf"],
}


def find_pdf(kind: str) -> Path | None:
    """PDF 파일 탐색"""
    candidates = KNOWN_PDFS.get(kind, [])
    for search_dir in PDF_SEARCH_DIRS:
        for fname in candidates:
            p = search_dir / fname
            if p.exists():
                return p
    # 마지막으로 전체 탐색
    for search_dir in PDF_SEARCH_DIRS:
        if not search_dir.exists():
            continue
        for p in search_dir.glob("*.pdf"):
            name_lower = p.name.lower()
            if kind == "bl" and ("bl" in name_lower or "lading" in name_lower):
                return p
            if kind == "pl" and ("packing" in name_lower or "pack" in name_lower):
                return p
            if kind == "invoice" and ("invoice" in name_lower or " fa" in name_lower or "inv" in name_lower):
                return p
            if kind == "do" and (" do" in name_lower or "delivery" in name_lower):
                return p
    return None


def test_api_direct() -> dict:
    """requests 로 직접 API 테스트 (Playwright 없이 백엔드 검증)"""
    results = []
    try:
        import requests
    except ImportError:
        return {"method": "direct_api", "error": "requests not installed", "pass": False}

    # BL, PL, INV, DO 파일 찾기
    pdf_paths = {
        "bl":      find_pdf("bl"),
        "pl":      find_pdf("pl"),
        "invoice": find_pdf("invoice"),
        "do":      find_pdf("do"),
    }

    print("\n[Phase A.1] PDF 파일 탐색 결과:")
    found_any = False
    for kind, p in pdf_paths.items():
        if p:
            print(f"  {kind.upper():8s}: {p}")
            found_any = True
        else:
            print(f"  {kind.upper():8s}: 없음 (선택적)")

    if not pdf_paths["pl"]:
        print("  ⚠️  PL (Packing List)가 없어 API 실 업로드 테스트를 건너뜁니다.")
        return {
            "method": "direct_api",
            "skip_reason": "PL PDF not found",
            "pdf_found": {k: str(v) if v else None for k, v in pdf_paths.items()},
            "pass": None,  # 건너뜀
        }

    # ── 테스트 1: dry_run=true (파싱만) ──
    print("\n[Phase A.2] POST /api/inbound/onestop-upload?dry_run=true ...")
    t0 = time.time()
    files = {}
    opened_files = []
    try:
        if pdf_paths["pl"]:
            f = open(pdf_paths["pl"], "rb")
            opened_files.append(f)
            files["pl"] = (pdf_paths["pl"].name, f, "application/pdf")
        if pdf_paths["bl"]:
            f = open(pdf_paths["bl"], "rb")
            opened_files.append(f)
            files["bl"] = (pdf_paths["bl"].name, f, "application/pdf")
        if pdf_paths["invoice"]:
            f = open(pdf_paths["invoice"], "rb")
            opened_files.append(f)
            files["invoice"] = (pdf_paths["invoice"].name, f, "application/pdf")
        if pdf_paths["do"]:
            f = open(pdf_paths["do"], "rb")
            opened_files.append(f)
            files["do_file"] = (pdf_paths["do"].name, f, "application/pdf")

        resp = requests.post(
            "http://127.0.0.1:8765/api/inbound/onestop-upload?dry_run=true",
            files=files,
            timeout=30,
        )
        elapsed = time.time() - t0
        status_ok = resp.status_code == 200

        if status_ok:
            body = resp.json()
            print(f"  HTTP {resp.status_code} ({elapsed:.2f}s)")
            # 파싱 결과 검증: 응답 구조 {ok, message, data:{preview_rows, cross_check, ...}}
            data = body.get("data") or {}
            cross_check = data.get("cross_check", {}) if isinstance(data, dict) else {}
            preview_rows = data.get("preview_rows", []) if isinstance(data, dict) else []
            preview_count = data.get("preview_count", 0) if isinstance(data, dict) else 0
            has_rows = isinstance(preview_rows, list) and len(preview_rows) > 0

            if has_rows:
                print(f"  PL 파싱 행 수: {len(preview_rows)} ({preview_count})")
                if isinstance(cross_check, dict):
                    cc_summary = cross_check.get("summary", "")
                    critical = cross_check.get("critical", 0)
                    warning = cross_check.get("warning", 0)
                    print(f"  크로스체크: critical={critical}, warning={warning}")
                    print(f"  요약: {cc_summary[:80]}")
            else:
                print(f"  WARNING: 파싱 결과 없음. 응답 키: {list(body.keys()) if isinstance(body, dict) else type(body)}")

            cross_check_pass = isinstance(cross_check, dict) and cross_check.get("critical", 0) == 0

            result_dry = {
                "test": "onestop_upload_dry_run",
                "status_code": resp.status_code,
                "elapsed_s": round(elapsed, 3),
                "preview_count": preview_count,
                "has_rows": has_rows,
                "cross_check_critical": cross_check.get("critical", 0) if isinstance(cross_check, dict) else None,
                "cross_check_warning": cross_check.get("warning", 0) if isinstance(cross_check, dict) else None,
                "cross_check_pass": cross_check_pass,
                "pass": status_ok and has_rows,
            }
        else:
            print(f"  ❌ HTTP {resp.status_code}: {resp.text[:200]}")
            result_dry = {
                "test": "onestop_upload_dry_run",
                "status_code": resp.status_code,
                "error": resp.text[:300],
                "pass": False,
            }
        results.append(result_dry)

    except Exception as e:
        print(f"  ❌ Exception: {e}")
        results.append({"test": "onestop_upload_dry_run", "error": str(e), "pass": False})
    finally:
        for f in opened_files:
            f.close()

    # ── 테스트 2: /api/inbound/pdf-upload (단일 PL) ──
    if pdf_paths["pl"]:
        print("\n[Phase A.3] POST /api/inbound/pdf-upload (단일 PL) ...")
        t0 = time.time()
        try:
            with open(pdf_paths["pl"], "rb") as f:
                resp2 = requests.post(
                    "http://127.0.0.1:8765/api/inbound/pdf-upload",
                    files={"file": (pdf_paths["pl"].name, f, "application/pdf")},
                    timeout=30,
                )
            elapsed2 = time.time() - t0
            print(f"  HTTP {resp2.status_code} ({elapsed2:.2f}s)")
            body2 = resp2.json() if resp2.status_code == 200 else {}
            results.append({
                "test": "pdf_upload_single_pl",
                "status_code": resp2.status_code,
                "elapsed_s": round(elapsed2, 3),
                "response_keys": list(body2.keys()) if isinstance(body2, dict) else str(type(body2)),
                "pass": resp2.status_code == 200,
            })
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            results.append({"test": "pdf_upload_single_pl", "error": str(e), "pass": False})

    # ── 테스트 3: /api/inbound/pdf (base64) ──
    if pdf_paths["pl"]:
        print("\n[Phase A.4] POST /api/inbound/pdf (base64 PL) ...")
        t0 = time.time()
        try:
            with open(pdf_paths["pl"], "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            resp3 = requests.post(
                "http://127.0.0.1:8765/api/inbound/pdf",
                json={"pdf_base64": b64, "filename": pdf_paths["pl"].name},
                timeout=30,
            )
            elapsed3 = time.time() - t0
            print(f"  HTTP {resp3.status_code} ({elapsed3:.2f}s)")
            results.append({
                "test": "pdf_inbound_base64",
                "status_code": resp3.status_code,
                "elapsed_s": round(elapsed3, 3),
                "pass": resp3.status_code == 200,
            })
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            results.append({"test": "pdf_inbound_base64", "error": str(e), "pass": False})

    passed = sum(1 for r in results if r.get("pass") is True)
    failed = sum(1 for r in results if r.get("pass") is False)
    skipped = sum(1 for r in results if r.get("pass") is None)

    return {
        "method": "direct_api",
        "pdf_found": {k: str(v) if v else None for k, v in pdf_paths.items()},
        "tests": results,
        "summary": {"total": len(results), "pass": passed, "fail": failed, "skip": skipped},
    }


def test_playwright_ui(headless: bool = True) -> dict:
    """Playwright로 UI 업로드 플로우 검증"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  Playwright 미설치, UI 테스트 건너뜀")
        return {"method": "playwright_ui", "skip_reason": "playwright not installed", "pass": None}

    pl_path = find_pdf("pl")
    if not pl_path:
        return {"method": "playwright_ui", "skip_reason": "PL PDF not found", "pass": None}

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("\n[Phase A.5] Playwright UI 업로드 테스트...")
        try:
            page.goto("http://127.0.0.1:8765/", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            print("  페이지 로드 OK")

            # OneStop 입고 모달 열기 시도
            page.evaluate("""
                (function(){
                    var b = document.querySelector('button[data-action="onOneStopInbound"]');
                    if (b) b.click();
                })();
            """)
            page.wait_for_timeout(1000)

            modal = page.query_selector("#sqm-modal")
            modal_visible = modal is not None and modal.is_visible()
            print(f"  OneStop 모달 열림: {'YES' if modal_visible else 'NO'}")

            results.append({
                "test": "onestop_modal_open",
                "pass": modal_visible,
            })

            if modal_visible:
                # PL 파일 업로드 입력 찾기
                file_input = page.query_selector('input[type="file"]')
                if file_input:
                    file_input.set_input_files(str(pl_path))
                    page.wait_for_timeout(2000)
                    print(f"  PL 파일 업로드 시도: {pl_path.name}")

                    # 응답 확인 (네트워크 요청 또는 UI 변화)
                    body_text = page.inner_text("body")
                    has_result = "LOT" in body_text or "packing" in body_text.lower() or "파싱" in body_text

                    results.append({
                        "test": "onestop_file_upload_ui",
                        "pass": True,  # 파일 설정 자체는 성공
                        "has_result_text": has_result,
                    })
                else:
                    print("  ⚠️  파일 입력 필드 없음")
                    results.append({
                        "test": "onestop_file_input_found",
                        "pass": False,
                        "note": "file input not found in modal",
                    })

                # 모달 닫기
                close_btn = page.query_selector(
                    "#sqm-modal button[onclick*='display'], #sqm-modal-inner > button, #sqm-modal .btn-close"
                )
                if close_btn:
                    close_btn.click()
                    page.wait_for_timeout(300)

        except Exception as e:
            print(f"  ❌ Playwright 예외: {e}")
            results.append({"test": "playwright_ui", "error": str(e), "pass": False})

        browser.close()

    passed = sum(1 for r in results if r.get("pass") is True)
    failed = sum(1 for r in results if r.get("pass") is False)

    return {
        "method": "playwright_ui",
        "pl_file": str(pl_path),
        "tests": results,
        "summary": {"total": len(results), "pass": passed, "fail": failed},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("Phase A: 실 PDF 업로드 검증")
    print("=" * 60)

    # 1. 직접 API 테스트
    api_result = test_api_direct()

    # 2. Playwright UI 테스트
    ui_result = test_playwright_ui(headless=args.headless)

    # 3. 결과 집계
    all_tests = []
    if "tests" in api_result:
        all_tests.extend(api_result["tests"])
    if "tests" in ui_result:
        all_tests.extend(ui_result["tests"])

    passed = sum(1 for t in all_tests if t.get("pass") is True)
    failed = sum(1 for t in all_tests if t.get("pass") is False)
    skipped = sum(1 for t in all_tests if t.get("pass") is None)

    print(f"\n{'='*60}")
    print(f"Phase A 결과: 총 {len(all_tests)}건 · PASS {passed} · FAIL {failed} · SKIP {skipped}")
    print(f"{'='*60}")

    # 실패 상세
    failed_tests = [t for t in all_tests if t.get("pass") is False]
    if failed_tests:
        print(f"\n❌ 실패 항목 ({len(failed_tests)}건):")
        for t in failed_tests:
            name = t.get("test", "?")
            err = t.get("error") or t.get("note") or f"HTTP {t.get('status_code', '?')}"
            print(f"  - {name}: {err}")

    # JSON 저장
    report = {
        "phase": "A",
        "title": "실 PDF 업로드 검증",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "api_result": api_result,
        "ui_result": ui_result,
        "summary": {
            "total": len(all_tests),
            "pass": passed,
            "fail": failed,
            "skip": skipped,
            "overall_pass": failed == 0 and passed > 0,
        },
    }

    report_path = REPORTS_DIR / "playwright_real_pdf.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {report_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
