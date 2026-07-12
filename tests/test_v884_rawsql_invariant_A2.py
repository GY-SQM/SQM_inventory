# -*- coding: utf-8 -*-
"""[감사 raw-SQL / 방침 (A)] 엑셀기반 다중-LOT 엔드포인트 무게 불변식 복구 회귀 테스트.

대상:
  - inventory_api.scan_bulk_upload (action=return): 톤백 PICKED→RETURN 전환 시
    parent inventory 무게 버킷 재계산 누락 → current_weight 가 실제 재고를 반영 못함.
  - outbound_api.barcode_confirm_sold: 톤백 →SOLD 전환 시 parent inventory 무게 재계산
    누락 → current_weight 가 '판 재고'를 여전히 가용으로 과대표시.

주의: verify_lot_integrity 의 initial=current+picked 합계검사만으로는 이 버그가
  안 잡힌다(합은 맞고 버킷이 틀림). 따라서 current/picked 실제 값을 직접 검증한다.
"""
import io
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_modules.inventory_modular.engine import SQMInventoryEngineV3


class _UF:
    """UploadFile 대체 shim — 엔드포인트는 .filename / .file.read() 만 사용."""
    def __init__(self, filename, data: bytes):
        self.filename = filename
        self.file = io.BytesIO(data)


def _mk_engine():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return SQMInventoryEngineV3(db_path=path), path


def _cleanup(eng, path):
    try:
        eng.close()
    except Exception:
        pass
    for p in (path, path + "-wal", path + "-shm"):
        try:
            os.remove(p)
        except OSError:
            pass


def _seed_available(eng, lot, normals=2, kg=1000):
    db = eng.db
    init = normals * kg + 1
    db.execute(
        "INSERT INTO inventory (lot_no, product, initial_weight, current_weight, "
        "picked_weight, mxbg_pallet, status) VALUES (?,?,?,?,0,?,'AVAILABLE')",
        (lot, "P1", init, init, normals))
    iid = eng.db.fetchone("SELECT id FROM inventory WHERE lot_no=?", (lot,))
    iid = iid["id"] if isinstance(iid, dict) else iid[0]
    for s in range(1, normals + 1):
        db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
                   "is_sample, status) VALUES (?,?,?,?,0,'AVAILABLE')", (iid, lot, s, kg))
    db.execute("INSERT INTO inventory_tonbag (inventory_id, lot_no, sub_lt, weight, "
               "is_sample, status) VALUES (?,?,0,1,1,'AVAILABLE')", (iid, lot))


def _weights(eng, lot):
    r = eng.db.fetchone("SELECT current_weight, picked_weight FROM inventory WHERE lot_no=?", (lot,))
    if isinstance(r, dict):
        return float(r["current_weight"]), float(r["picked_weight"])
    return float(r[0]), float(r[1])


def _bind_engine(monkeypatch, eng):
    import backend.api as bapi
    monkeypatch.setattr(bapi, "engine", eng, raising=False)
    monkeypatch.setattr(bapi, "ENGINE_AVAILABLE", True, raising=False)


def test_scan_bulk_return_recalcs_weight(monkeypatch):
    eng, path = _mk_engine()
    try:
        _bind_engine(monkeypatch, eng)
        monkeypatch.setenv("SQM_TEST_DB_PATH", path)
        import backend.api.inventory_api as iv

        _seed_available(eng, "LOTBK", normals=2)
        eng.quick_outbound("LOTBK", 2, "ACME")   # 2 normal → PICKED (current=1(샘플), picked=2000)
        row = eng.db.fetchall(
            "SELECT tonbag_uid FROM inventory_tonbag WHERE lot_no='LOTBK' AND status='PICKED'")
        uids = [(r["tonbag_uid"] if isinstance(r, dict) else r[0]) for r in row]
        csv = "tonbag_uid\n" + "\n".join(uids) + "\n"

        r = iv.scan_bulk_upload(_UF("s.csv", csv.encode("utf-8")), action="return")
        assert r["ok"] is True, r

        cur, pk = _weights(eng, "LOTBK")
        # PICKED→RETURN: RETURN 은 창고 내 재고 → current 로 복귀, picked=0
        assert abs(cur - 2001) < 0.01, f"current={cur} (기대 2001: RETURN 2000 + 샘플 1)"
        assert abs(pk - 0) < 0.01, f"picked={pk} (기대 0)"
    finally:
        _cleanup(eng, path)


def test_barcode_confirm_sold_recalcs_weight(monkeypatch):
    eng, path = _mk_engine()
    try:
        _bind_engine(monkeypatch, eng)
        import backend.api.outbound_api as ob
        import features.parsers.barcode_sold_parser as bsp

        _seed_available(eng, "LOTBC", normals=2)   # 2 normal + 1 sample, 전부 AVAILABLE
        row = eng.db.fetchone(
            "SELECT tonbag_uid FROM inventory_tonbag WHERE lot_no='LOTBC' AND is_sample=0 LIMIT 1")
        uid = row["tonbag_uid"] if isinstance(row, dict) else row[0]

        def _fake_parse(_path):
            return {"parse_ok": True,
                    "items": [{"tonbag_uid": uid, "actual_location": "A-1"}],
                    "warnings": []}
        monkeypatch.setattr(bsp, "parse_barcode_sold_excel", _fake_parse)

        r = ob.barcode_confirm_sold(_UF("bar.xlsx", b"dummy"), dry_run=False)
        assert r["ok"] is True, r
        assert r["summary"]["applied"] >= 1, r["summary"]

        cur, pk = _weights(eng, "LOTBC")
        # 1 normal AVAILABLE→SOLD: current 는 남은 normal(1000)+샘플(1)=1001, picked=1000
        assert abs(cur - 1001) < 0.01, f"current={cur} (기대 1001 — 판 재고가 가용에서 빠져야 함)"
        assert abs(pk - 1000) < 0.01, f"picked={pk} (기대 1000)"
    finally:
        _cleanup(eng, path)
