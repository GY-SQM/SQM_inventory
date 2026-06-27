"""
FastAPI TestClient 통합 테스트
- /api/inventory, /api/outbound, /api/allocation, /api/integrity 엔드포인트
- UI JS 파일이 기대하는 응답 필드와 실제 API 응답의 정합성 전수검사
- 발견된 버그/불일치를 테스트로 문서화

격리 전략:
  SQM_TEST_DB_PATH 환경변수 → inventory_api.py의 _db()가 temp DB 사용
  backend_api.engine 교체 → outbound_api.py, confirm 등 엔진 경유 엔드포인트 커버
"""
import os
import sys
import tempfile
import logging
import warnings

logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient
from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


# ──────────────────────────────────────────────────────────────────────────────
# Module-scoped fixture: temp DB + engine patch + env var
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    import backend.api as backend_api
    from backend.main import app

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # inv_router._db() 가 temp DB를 바라보게 함
    os.environ["SQM_TEST_DB_PATH"] = path

    e = SQMInventoryEngineV3(db_path=path)
    db = e.db

    # ── 시딩: 3 LOT (APITEST001-002=AVAILABLE, APITEST003=RESERVED) ─────────
    for i in range(1, 4):
        lot = f"APITEST{i:03d}"
        status = "AVAILABLE" if i <= 2 else "RESERVED"
        db.execute(
            "INSERT INTO inventory (lot_no, product, initial_weight, current_weight,"
            " picked_weight, mxbg_pallet, status) VALUES (?,?,?,?,0,?,?)",
            (lot, "CuCO3", 3001.0, 3001.0, 3, status),
        )
        iid = db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot,))["id"]
        for s in range(1, 4):
            db.execute(
                "INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt,"
                " weight, is_sample, status) VALUES (?,?,?,?,0,'AVAILABLE')",
                (iid, lot, s, 1000.0),
            )
        # 샘플 톤백
        db.execute(
            "INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt,"
            " weight, is_sample, status) VALUES (?,?,0,1,1,'AVAILABLE')",
            (iid, lot),
        )

    orig_engine = backend_api.engine
    orig_avail = backend_api.ENGINE_AVAILABLE
    backend_api.engine = e
    backend_api.ENGINE_AVAILABLE = True

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    backend_api.engine = orig_engine
    backend_api.ENGINE_AVAILABLE = orig_avail
    e.close()
    try:
        os.unlink(path)
    except Exception:
        pass
    os.environ.pop("SQM_TEST_DB_PATH", None)


# ──────────────────────────────────────────────────────────────────────────────
# TestHealthEndpoints
# ──────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoints:
    def test_api_health_200(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200, f"/api/health 200 기대, 실제={r.status_code}"

    def test_api_health_has_status(self, client):
        d = client.get("/api/health").json()
        assert "status" in d, "/api/health 응답에 'status' 필드 없음"

    def test_api_health_status_ok(self, client):
        d = client.get("/api/health").json()
        assert d["status"] == "ok", f"status=ok 기대, 실제={d['status']}"

    def test_api_health_modules_field_ui_mismatch(self, client):
        """
        [알려진 UI 불일치]
        health_router(inventory_api.py)가 먼저 등록되어 {lots, tonbags} 반환.
        sqm-core.js는 modules_loaded / engine_available 기대.
        JS의 fallback 로직(h.modules_loaded !== undefined ? ...)으로
        'Modules: 0/8' 표시됨 — 실제 가용 엔진이 있어도 항상 0으로 표시되는 UX 결함.
        """
        d = client.get("/api/health").json()
        has_modules_loaded = "modules_loaded" in d
        has_engine_available = "engine_available" in d
        # 둘 중 하나라도 있어야 Statusbar가 정확히 표시됨
        assert has_modules_loaded or has_engine_available, (
            "[UI 불일치] /api/health 응답에 modules_loaded·engine_available 필드 모두 없음 "
            "→ sqm-core.js statusbar에서 'Modules: 0/8' 항상 표시 (실제값 반영 안 됨). "
            f"실제 응답 keys: {list(d.keys())}"
        )

    def test_integrity_quick_200(self, client):
        r = client.get("/api/integrity/quick")
        assert r.status_code == 200, f"/api/integrity/quick 200 기대, 실제={r.status_code}"

    def test_integrity_quick_has_status(self, client):
        d = client.get("/api/integrity/quick").json()
        assert "status" in d, "/api/integrity/quick 응답에 'status' 필드 없음"


# ──────────────────────────────────────────────────────────────────────────────
# TestInventoryEndpoints — 응답 구조 UI 정합성
# ──────────────────────────────────────────────────────────────────────────────

class TestInventoryEndpoints:
    """
    sqm-inventory.js 기대 필드:
      r.lot, r.status, r.tb_avail, r.avail_bags, r.avail_mt,
      r.tb_reserved, r.tb_picked, r.total_bags, r.initial_weight,
      r.balance, r.net, r.customer, r.sale_ref, r.wh
    응답은 list (extractRows가 Array.isArray 처리) 또는 {data: [...]} dict 모두 허용.
    """

    def test_get_inventory_200(self, client):
        r = client.get("/api/inventory")
        assert r.status_code == 200, f"/api/inventory 200 기대, 실제={r.status_code}"

    def test_get_inventory_returns_list(self, client):
        d = client.get("/api/inventory").json()
        # extractRows: Array.isArray(res) → res
        rows = d if isinstance(d, list) else d.get("data", d.get("items", []))
        assert isinstance(rows, list), f"/api/inventory 응답이 list 아님: {type(d).__name__}"

    def test_get_inventory_has_seeded_lots(self, client):
        d = client.get("/api/inventory").json()
        rows = d if isinstance(d, list) else d.get("data", [])
        lots = {r.get("lot", r.get("lot_no", "")) for r in rows}
        assert "APITEST001" in lots, f"APITEST001이 /api/inventory 결과에 없음. lots={list(lots)[:10]}"

    def test_inventory_row_has_required_ui_fields(self, client):
        """sqm-inventory.js 렌더링에 필요한 필드 검증"""
        d = client.get("/api/inventory").json()
        rows = d if isinstance(d, list) else d.get("data", [])
        apitest = next((r for r in rows if r.get("lot") == "APITEST001"), None)
        assert apitest is not None, "APITEST001 행 없음"

        required = ["lot", "status", "initial_weight", "avail_mt"]
        for field in required:
            assert field in apitest, (
                f"[UI 불일치] /api/inventory 행에 '{field}' 필드 없음 "
                f"(sqm-inventory.js가 r.{field} 참조). keys={list(apitest.keys())}"
            )

    def test_inventory_fallback_fields_present(self, client):
        """tb_avail vs avail_bags 폴백 — 둘 중 하나 있어야 함"""
        d = client.get("/api/inventory").json()
        rows = d if isinstance(d, list) else d.get("data", [])
        apitest = next((r for r in rows if r.get("lot") == "APITEST001"), None)
        has_either = ("tb_avail" in apitest) or ("avail_bags" in apitest)
        assert has_either, (
            "[UI 불일치] tb_avail·avail_bags 둘 다 없음 "
            "— sqm-inventory.js 가용 톤백 수 표시 불가"
        )

    def test_inventory_status_filter_available(self, client):
        r = client.get("/api/inventory?status=AVAILABLE")
        assert r.status_code == 200
        rows = r.json() if isinstance(r.json(), list) else r.json().get("data", [])
        statuses = {row.get("status") for row in rows}
        # AVAILABLE 필터 → RESERVED 행 없어야 함
        assert "RESERVED" not in statuses, (
            f"[필터 버그] status=AVAILABLE 요청인데 RESERVED 행 포함: {statuses}"
        )

    def test_inventory_filter_excludes_apitest003(self, client):
        """APITEST003 = RESERVED → status=AVAILABLE 결과에서 제외돼야 함"""
        r = client.get("/api/inventory?status=AVAILABLE")
        rows = r.json() if isinstance(r.json(), list) else r.json().get("data", [])
        lots = {row.get("lot", row.get("lot_no")) for row in rows}
        assert "APITEST003" not in lots, (
            "[필터 버그] RESERVED LOT(APITEST003)이 status=AVAILABLE 결과에 포함됨"
        )

    def test_inventory_lot_detail_200(self, client):
        r = client.get("/api/inventory/APITEST001")
        assert r.status_code == 200, f"/api/inventory/APITEST001 200 기대, {r.status_code}"

    def test_inventory_nonexistent_lot_should_be_404(self, client):
        """
        [알려진 버그] /api/inventory/{lot_no} — inventory_api.py 의 get_lot_detail 이
        404 대신 200 + {"error": "LOT not found: ..."} 반환.
        sqm-inventory.js / sqm-inline.js 에서 HTTP 404를 catch 해 에러 처리를 하는 로직이
        작동하지 않고, {error: "..."} 응답을 정상 데이터로 오인할 수 있음.
        """
        r = client.get("/api/inventory/NONEXISTENT_XYZABC")
        assert r.status_code == 404, (
            f"[버그] /api/inventory/존재안하는LOT → 404 기대, 실제={r.status_code}. "
            f"응답: {r.json()}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# TestOutboundFlow — 전구간 API 흐름
# ──────────────────────────────────────────────────────────────────────────────

class TestOutboundFlow:
    """
    AVAILABLE → PICKED (quick) → SOLD (confirm) 전구간 API 흐름
    각 단계 응답의 'ok' / 'data' 구조가 JS가 기대하는 형태인지 검증.
    """

    def test_quick_info_200(self, client):
        r = client.get("/api/outbound/quick/info?lot_no=APITEST002")
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True, f"quick/info ok=true 기대: {d}"
        assert "data" in d, "quick/info data 필드 없음"

    def test_quick_outbound_success(self, client):
        r = client.post(
            "/api/outbound/quick",
            json={"lot_no": "APITEST002", "count": 2, "customer": "TEST_CLIENT"},
        )
        assert r.status_code == 200
        d = r.json()
        # sqm-inline.js: if (res && res.ok)
        assert d.get("ok") is True, f"[UI 불일치] quick outbound ok=true 기대: {d}"
        assert "data" in d, "quick 응답에 data 필드 없음"
        assert "message" in d, "quick 응답에 message 필드 없음"

    def test_quick_outbound_data_fields(self, client):
        """sqm-inline.js가 d.picked_count, d.total_weight_mt, d.lot_no 참조"""
        r = client.post(
            "/api/outbound/quick",
            json={"lot_no": "APITEST001", "count": 2, "customer": "TEST_CLIENT"},
        )
        d = r.json().get("data", {})
        assert "lot_no" in d, "[UI 불일치] quick.data.lot_no 없음"
        assert "picked_count" in d, "[UI 불일치] quick.data.picked_count 없음 (JS: d.picked_count||0)"
        assert "total_weight_mt" in d, "[UI 불일치] quick.data.total_weight_mt 없음"

    def test_picked_summary_200(self, client):
        r = client.get("/api/outbound/picked-summary?lot_no=APITEST001")
        assert r.status_code == 200
        d = r.json()
        # sqm-inline.js: if (!res || !res.ok)
        assert d.get("ok") is True, f"[UI 불일치] picked-summary ok=true 기대: {d}"

    def test_picked_summary_has_items(self, client):
        r = client.get("/api/outbound/picked-summary?lot_no=APITEST001")
        d = r.json()
        data = d.get("data", {})
        items = data.get("items", [])
        assert len(items) > 0, (
            f"APITEST001 PICKED 후 picked-summary items 비어있음. data={data}"
        )

    def test_confirm_outbound_success(self, client):
        r = client.post("/api/outbound/confirm", json={"lot_no": "APITEST001"})
        assert r.status_code == 200
        d = r.json()
        # sqm-inline.js: if (res && res.ok)
        assert d.get("ok") is True, f"[UI 불일치] confirm ok=true 기대: {d}"

    def test_confirm_outbound_data_fields(self, client):
        """sqm-inline.js: d.lot_no, d.confirmed 참조"""
        r = client.post("/api/outbound/confirm", json={"lot_no": "APITEST002"})
        d = r.json()
        if d.get("ok"):
            data = d.get("data", {})
            assert "confirmed" in data, (
                "[UI 불일치] confirm.data.confirmed 없음 (JS: d.confirmed||0)"
            )

    def test_outbound_history_200(self, client):
        r = client.get("/api/outbound/history")
        assert r.status_code == 200

    def test_outbound_history_is_list(self, client):
        d = client.get("/api/outbound/history").json()
        rows = d if isinstance(d, list) else d.get("data", [])
        assert isinstance(rows, list), f"outbound/history list 기대: {type(d).__name__}"

    def test_audit_log_200(self, client):
        r = client.get("/api/outbound/audit-log")
        assert r.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# TestAllocationEndpoints — 배정 응답 구조
# ──────────────────────────────────────────────────────────────────────────────

class TestAllocationEndpoints:
    """
    sqm-allocation.js 는 /api/q/allocation-summary 를 주로 사용하고,
    extractRows(res) → res.data.items 경로로 행을 추출.
    """

    def test_allocation_summary_200(self, client):
        r = client.get("/api/q/allocation-summary")
        assert r.status_code == 200

    def test_allocation_summary_structure(self, client):
        """extractRows(res) → res.data → d.items 경로 검증"""
        d = client.get("/api/q/allocation-summary").json()
        # {ok, data: {items: [...], total: N}}
        assert "data" in d, f"allocation-summary data 필드 없음: {list(d.keys())}"
        data = d["data"]
        assert "items" in data, (
            "[UI 불일치] allocation-summary data.items 없음 "
            "— extractRows가 빈 배열 반환해 화면 비어보임"
        )
        assert isinstance(data["items"], list), "data.items가 list 아님"

    def test_allocation_lot_overview_200(self, client):
        r = client.get("/api/allocation/lot-overview")
        assert r.status_code == 200

    def test_allocation_lot_overview_has_data(self, client):
        d = client.get("/api/allocation/lot-overview").json()
        assert "data" in d or "ok" in d, (
            f"lot-overview 응답 구조 불명: {list(d.keys())}"
        )

    def test_allocation_revert_step_post_200(self, client):
        """배정 되돌리기 — 빈 데이터로 호출해도 4xx/5xx 없어야 함"""
        r = client.post(
            "/api/allocation/revert-step",
            json={"from_status": "RESERVED"},
        )
        # 데이터 없으면 ok=false 일 수 있으나 500은 아니어야 함
        assert r.status_code < 500, (
            f"allocation/revert-step 서버 오류: {r.status_code} {r.text[:200]}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# TestUIFieldMismatch — JS 기대 필드 vs 실제 API 응답 전수검사
# ──────────────────────────────────────────────────────────────────────────────

class TestUIFieldMismatch:
    """
    JS 파일의 정적 분석 결과를 바탕으로 실제 API 응답 필드 불일치를 검증.
    불일치 = 화면에 '-' 또는 빈 칸이 표시되는 잠재적 버그.
    """

    def test_inventory_field_lot_not_lot_no(self, client):
        """
        inv_router는 'lot_no AS lot' 으로 alias — JS는 r.lot 참조.
        반대로 __init__.py의 /api/inventory/{lot_no} detail은 lot_no 키 사용.
        두 엔드포인트 간 필드명 불일치가 있지만 JS가 올바른 엔드포인트를 호출하면 OK.
        """
        rows = client.get("/api/inventory").json()
        row = (rows if isinstance(rows, list) else rows.get("data", []))
        row = next((r for r in row if r.get("lot") == "APITEST001"), None)
        if row:
            assert "lot" in row, (
                "[필드 불일치] /api/inventory 행에 'lot' 없고 'lot_no'만 있음 "
                "— sqm-inventory.js r.lot 참조 → 빈 칸 표시"
            )

    def test_inventory_initial_weight_in_mt(self, client):
        """initial_weight 단위: inv_router는 MT, JS는 MT로 사용 (fmtN)"""
        rows = client.get("/api/inventory").json()
        row = (rows if isinstance(rows, list) else rows.get("data", []))
        row = next((r for r in row if r.get("lot") == "APITEST001"), None)
        if row:
            iw = row.get("initial_weight")
            assert iw is not None, "initial_weight 필드 없음"
            # 3001 kg → 3.001 MT 기대
            assert float(iw) < 100, (
                f"[단위 불일치] initial_weight={iw}이 MT 단위가 아닌 것으로 의심 "
                "(3001 kg → 3.001 MT 기대)"
            )

    def test_quick_response_ok_not_success(self, client):
        """
        outbound_api.py quick → 'ok' 필드 반환.
        구 __init__.py POST /api/outbound/{lot}/confirm → 'success' 반환.
        sqm-inline.js는 'res.ok' 체크 → outbound_api 경로는 정상.
        """
        r = client.post(
            "/api/outbound/quick",
            json={"lot_no": "APITEST003", "count": 1, "customer": "MISMATCH_TEST"},
        )
        d = r.json()
        # ok가 있어야 하고, success만 있으면 JS 조건 false → 화면에 에러박스 표시
        assert "ok" in d, (
            "[UI 불일치] /api/outbound/quick 응답에 'ok' 필드 없음 "
            "— sqm-inline.js: if(res && res.ok) 조건 항상 false"
        )

    def test_allocation_summary_extractRows_path(self, client):
        """
        extractRows(res):
          Array.isArray(res) → res
          res.data 가 array → res.data
          res.data.items 가 array → res.data.items  ← allocation-summary 이 경로
        allocation-summary 는 {ok, data: {items: [...]}} 반환 → items 경로 사용.
        """
        d = client.get("/api/q/allocation-summary").json()
        data = d.get("data", {})
        items = data.get("items", None)
        assert items is not None, (
            "[UI 불일치] extractRows path 깨짐: data.items 없음 "
            "→ sqm-allocation.js 배정 목록 빈 화면"
        )

    def test_confirm_response_has_ok_not_only_success(self, client):
        """
        /api/outbound/confirm (outbound_api.py) → {ok, data: {confirmed, ...}}
        /api/outbound/{lot_no}/confirm (__init__.py) → {success, message}
        JS는 res.ok 체크 → outbound_api 경로가 호출돼야 정상.
        """
        r = client.post("/api/outbound/confirm", json={"lot_no": "APITEST001", "force_all": False})
        d = r.json()
        assert "ok" in d, (
            "[UI 불일치] /api/outbound/confirm 응답에 'ok' 없음 "
            "— sqm-inline.js res.ok 체크 실패 → 성공해도 에러 UI 표시"
        )


# ──────────────────────────────────────────────────────────────────────────────
# TestErrorHandling — 에러 응답이 화면을 깨지 않는지 검증
# ──────────────────────────────────────────────────────────────────────────────

class TestErrorHandling:

    def test_inventory_nonexistent_lot_returns_404_or_error_structure(self, client):
        """
        존재하지 않는 LOT → 화면에서 catch 해 에러 메시지 표시 필요.
        현재 상태 문서화: 200 + {error: "..."} 반환 (HTTP 404 아님).
        """
        r = client.get("/api/inventory/NEVER_EXISTS_ZZZ")
        # 이상적: 404. 현실: 200 + {error}
        if r.status_code == 200:
            d = r.json()
            assert "error" in d or "detail" in d, (
                "존재하지 않는 LOT 조회 시 200이면 error/detail 필드라도 있어야 함 "
                f"실제={d}"
            )
        else:
            assert r.status_code in (404, 422), (
                f"비정상 LOT → 404 또는 422 기대, 실제={r.status_code}"
            )

    def test_quick_outbound_invalid_count(self, client):
        """count=0 → 4xx 또는 ok=false"""
        r = client.post(
            "/api/outbound/quick",
            json={"lot_no": "APITEST001", "count": 0, "customer": "X"},
        )
        d = r.json()
        is_error = r.status_code >= 400 or d.get("ok") is False
        assert is_error, f"count=0 요청이 성공으로 처리됨: {r.status_code} {d}"

    def test_confirm_no_lot_no_force_all_blocked(self, client):
        """lot_no 없고 force_all=false → 차단 응답 (ok=false)"""
        r = client.post("/api/outbound/confirm", json={})
        assert r.status_code < 500, f"서버 오류 {r.status_code}: {r.text[:200]}"
        d = r.json()
        assert d.get("ok") is False or r.status_code >= 400, (
            "lot_no 없는 confirm이 ok=true로 처리됨 — 전체 일괄출고 실수 위험"
        )

    def test_allocation_cancel_nonexistent_lot(self, client):
        """없는 LOT 배정 취소 → 500 아니어야 함"""
        r = client.post("/api/allocation/NEVER_EXISTS_ZZZ/cancel")
        assert r.status_code < 500, (
            f"없는 LOT 취소 시 500 서버 오류: {r.status_code}"
        )

    def test_integrity_check_no_crash(self, client):
        r = client.get("/api/integrity/check")
        assert r.status_code == 200
        d = r.json()
        assert "success" in d or "ok" in d or "status" in d, (
            f"integrity/check 응답 구조 불명: {list(d.keys())}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# TestIntegrity — 출고 후 불변식 API 검증
# ──────────────────────────────────────────────────────────────────────────────

class TestIntegrity:

    def test_integrity_check_200(self, client):
        r = client.get("/api/integrity/check")
        assert r.status_code == 200

    def test_integrity_check_no_errors_on_apitest(self, client):
        r = client.get("/api/integrity/check")
        d = r.json()
        data = d.get("data", {})
        errors = []
        if isinstance(data, dict):
            errors = data.get("errors", data.get("invalid", []))
        elif isinstance(data, list):
            errors = [x for x in data if not x.get("valid", True)]
        apitest_errors = [e for e in errors if "APITEST" in str(e)]
        assert len(apitest_errors) == 0, (
            f"APITEST LOT 무결성 오류: {apitest_errors}"
        )

    def test_integrity_diagnostic_200(self, client):
        r = client.get("/api/integrity/diagnostic")
        assert r.status_code == 200
