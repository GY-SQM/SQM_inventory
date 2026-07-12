import sqlite3, os, logging, datetime
from fastapi import APIRouter

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scan", tags=["scan"])


def _db_path():
    env = os.environ.get("SQM_TEST_DB_PATH")
    if env and os.path.exists(env): return env
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p = os.path.join(root, "data", "db", "sqm_inventory.db")
    if not os.path.exists(p):
        b = os.path.join(root, "backup", "sqm_backup_20260421_232322.db")
        if os.path.exists(b): return b
    return p


def _db():
    conn = sqlite3.connect(_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


@router.post("/lookup")
def scan_lookup(payload: dict):
    uid = (payload.get("uid") or payload.get("barcode") or "").strip()
    if not uid:
        return dict(success=False, message="uid 또는 barcode 필드 필요", data=None)
    try:
        conn = _db()
        row = conn.execute(
            "SELECT t.id, t.sub_lt, t.lot_no, t.sap_no, t.bl_no, "
            "t.tonbag_uid, t.tonbag_no, t.status, "
            "t.weight, t.location, t.inbound_date, t.picked_to AS container, "
            "i.product, i.status AS lot_status, i.warehouse "
            "FROM inventory_tonbag t "
            "LEFT JOIN inventory i ON i.lot_no = t.lot_no "
            "WHERE t.tonbag_uid = ? OR t.sub_lt = ? LIMIT 1",
            (uid, uid)
        ).fetchone()
        conn.close()
        if not row:
            return dict(success=False, message="바코드 없음: " + uid, data=None)
        data = dict(row)
        data["weight"] = float(data.get("weight") or 0)
        return dict(success=True,
                    message="LOT " + str(data.get("lot_no")) + " — " + str(data.get("status")),
                    data=data)
    except Exception as e:
        log.error("scan_lookup error: %s", e)
        return dict(success=False, message=str(e), data=None)


@router.post("/confirm_outbound")
def scan_confirm_outbound(payload: dict):
    uid = (payload.get("uid") or payload.get("barcode") or "").strip()
    if not uid:
        return dict(success=False, message="uid 또는 barcode 필드 필요", data=None)
    try:
        conn = _db()
        row = conn.execute(
            "SELECT id, sub_lt, lot_no, status FROM inventory_tonbag "
            "WHERE (tonbag_uid = ? OR sub_lt = ?) AND status = ? LIMIT 1",
            (uid, uid, "PICKED")
        ).fetchone()
        if not row:
            conn.close()
            return dict(success=False, message=uid + ": PICKED 상태 톤백 없음", data=None)
        r = dict(row)
        today = datetime.date.today().isoformat()
        conn.execute(
            "UPDATE inventory_tonbag SET status=?, outbound_date=?, updated_at=? WHERE id=?",
            ("SOLD", today, today, r["id"])
        )
        # [감사 raw-SQL/(A)] 바인딩 개수 버그 수정: 플레이스홀더 5개(lot_no + IN 4개)에
        #   값이 4개뿐이라 매 호출마다 sqlite 바인딩 오류로 실패했음. 출고성 상태
        #   4종(SOLD/OUTBOUND/CONFIRMED/SHIPPED)을 채워 정상 동작하게 함.
        remaining = conn.execute(
            "SELECT COUNT(*) FROM inventory_tonbag "
            "WHERE lot_no=? AND status NOT IN (?,?,?,?)",
            (r["lot_no"], "SOLD", "OUTBOUND", "CONFIRMED", "SHIPPED")
        ).fetchone()[0]
        if remaining == 0:
            # HIGH: 상태 검증 추가 (PICKED/AVAILABLE만 SOLD 가능)
            conn.execute(
                "UPDATE inventory SET status=? WHERE lot_no=? AND status IN (?,?)",
                ("SOLD", r["lot_no"], "PICKED", "AVAILABLE")
            )
        conn.commit()
        conn.close()
        # [감사 raw-SQL/(A)] 톤백 SOLD 전환 후 무게 재계산 누락 → 불변식 복구.
        from backend.api.lot_invariant import repair_weight_invariant
        repair_weight_invariant(r["lot_no"], reason="SCAN_CONFIRM_OUTBOUND")
        return dict(success=True,
                    message=uid + " -> SOLD (LOT: " + str(r["lot_no"]) + ")",
                    data=dict(sub_lt=r["sub_lt"], lot_no=r["lot_no"], status="SOLD"))
    except Exception as e:
        log.error("scan_confirm_outbound error: %s", e)
        return dict(success=False, message=str(e), data=None)


@router.post("/return")
def scan_return(payload: dict):
    uid = (payload.get("uid") or payload.get("barcode") or "").strip()
    reason = (payload.get("reason") or "").strip()
    if not uid:
        return dict(success=False, message="uid 또는 barcode 필드 필요", data=None)
    try:
        conn = _db()
        row = conn.execute(
            "SELECT id, sub_lt, lot_no, status FROM inventory_tonbag "
            "WHERE (tonbag_uid = ? OR sub_lt = ?) AND status IN (?,?,?) LIMIT 1",
            (uid, uid, "PICKED", "SOLD")
        ).fetchone()
        if not row:
            conn.close()
            return dict(success=False, message=uid + ": OUTBOUND/PICKED/SOLD 상태 없음", data=None)
        r = dict(row)
        prev = r["status"]
        today = datetime.date.today().isoformat()
        conn.execute(
            "UPDATE inventory_tonbag SET status=?, remarks=?, updated_at=? WHERE id=?",
            ("RETURN", reason or "반품", today, r["id"])
        )
        conn.commit()
        conn.close()
        return dict(success=True,
                    message=uid + ": " + prev + " -> RETURN (" + (reason or "없음") + ")",
                    data=dict(sub_lt=r["sub_lt"], lot_no=r["lot_no"], status="RETURN"))
    except Exception as e:
        log.error("scan_return error: %s", e)
        return dict(success=False, message=str(e), data=None)


@router.put("/move")
def scan_move(payload: dict):
    uid = (payload.get("uid") or payload.get("barcode") or "").strip()
    to_loc = (payload.get("to_location") or payload.get("location") or "").strip()
    if not uid or not to_loc:
        return dict(success=False, message="uid/barcode 와 to_location 필드 필요", data=None)
    try:
        conn = _db()
        row = conn.execute(
            "SELECT id, sub_lt, lot_no, location, status FROM inventory_tonbag "
            "WHERE tonbag_uid = ? OR sub_lt = ? LIMIT 1",
            (uid, uid)
        ).fetchone()
        if not row:
            conn.close()
            return dict(success=False, message="바코드 없음: " + uid, data=None)
        r = dict(row)
        prev = r.get("location") or "-"
        conn.execute("UPDATE inventory_tonbag SET location=? WHERE id=?", (to_loc, r["id"]))
        conn.commit()
        # v8.7.0: 스캔 이동 직후 from/to 셀 모두 비파괴 검증
        _cell_warnings = []
        try:
            from engine_modules.warehouse_cell_logic import check_cell_invariants
            for _loc in {prev, to_loc}:
                if not _loc or _loc == '-':
                    continue
                rep = check_cell_invariants(conn, _loc)   # enforce는 전역 스위치 따름
                if not rep['ok']:
                    _cell_warnings.extend(rep['warnings'])
        except Exception as _e:
            log.debug(f"[scan_move] cell_invariants 건너뜀: {_e}")
        conn.close()
        return dict(success=True,
                    message=uid + ": " + prev + " -> " + to_loc + " 위치 변경 완료",
                    data=dict(sub_lt=r["sub_lt"], lot_no=r["lot_no"],
                              from_location=prev, to_location=to_loc, status=r["status"],
                              cell_warnings=_cell_warnings))
    except Exception as e:
        log.error("scan_move error: %s", e)
        return dict(success=False, message=str(e), data=None)
