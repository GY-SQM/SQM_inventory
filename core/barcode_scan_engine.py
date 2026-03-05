"""
SQM v6.12 Stage3 — 바코드 스캔 대조 엔진
==========================================
출고 확정 전 현장 스캔 UID와 시스템 출고 예정 UID를 대조.
불일치 시 Hard Stop.

작성자: Ruby
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)

_INVISIBLE_CHARS = '\ufeff\u200b\u200c\u200d\u00a0\u2060'


def _clean_uid(raw: str) -> str:
    if not raw:
        return ''
    cleaned = str(raw).strip()
    for ch in _INVISIBLE_CHARS:
        cleaned = cleaned.replace(ch, '')
    return cleaned.replace('\r', '').replace('\n', '').strip()


def _normalize_sublt(value) -> str:
    s = str(value).strip()
    try:
        return str(int(s))
    except (ValueError, TypeError):
        return s


class BarcodeScanEngine:
    """바코드 스캔 대조 + uid_verify_history 관리"""

    def __init__(self, db):
        self.db = db
        self._ensure_table()
        self._ensure_swap_table()
        self._ensure_outbound_scan_table()

    # ---------------------------------------------------------------------
    # Phase 3 (RUBI) — Random Outbound: Scan = Immediate Confirm(OUT)
    #   - STEP1~3: TONBAG 상태 변경 금지 (Phase 2)
    #   - STEP4: UID 스캔 순간에만 SOLD(=OUT) 확정
    #   - Target 체크는 allocation_plan.qty_mt(중량) 기반
    # ---------------------------------------------------------------------

    def _ensure_outbound_scan_table(self) -> None:
        """스캔 확정 로그 테이블(best-effort). 없으면 생성만 하고 실패는 무시."""
        try:
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS outbound_scan_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tonbag_id INTEGER,
                    tonbag_uid TEXT,
                    lot_no TEXT,
                    sale_ref TEXT,
                    customer TEXT,
                    weight_kg REAL,
                    source_file TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    undone INTEGER DEFAULT 0,
                    undone_at TEXT
                )
                """
            )
            try:
                self.db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_out_scan_uid ON outbound_scan_log(tonbag_uid)"
                )
                self.db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_out_scan_lot ON outbound_scan_log(lot_no)"
                )
                self.db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_out_scan_at ON outbound_scan_log(created_at DESC)"
                )
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"outbound_scan_log 테이블 생성 스킵: {e}")

    def _pick_target_row_for_lot(self, lot_no: str, sale_ref: str = None) -> Dict:
        """allocation_plan에서 LOT 목표(중량) 조회. sale_ref가 있으면 우선 적용."""
        lot_no = str(lot_no or '').strip()
        if not lot_no:
            return {}
        try:
            # Phase2에서는 tonbag_id가 NULL(톤백 미지정)일 수 있음.
            # status 값은 버전마다 다르므로, "취소/실행완료"만 제외하는 관대한 기준 사용.
            where = "lot_no = ? AND COALESCE(status,'') NOT IN ('CANCELLED','EXECUTED','REJECTED')"
            params = [lot_no]
            if sale_ref:
                where += " AND COALESCE(sale_ref,'') = ?"
                params.append(str(sale_ref).strip())
            row = self.db.fetchone(
                f"SELECT lot_no, customer, sale_ref, SUM(COALESCE(qty_mt,0)) AS qty_mt_sum, COUNT(*) AS row_cnt "
                f"FROM allocation_plan WHERE {where}",
                tuple(params),
            )
            if not row:
                return {}
            if isinstance(row, dict):
                return row
            # tuple fallback
            return {
                "lot_no": lot_no,
                "customer": "",
                "sale_ref": sale_ref or "",
                "qty_mt_sum": float(row[3] or 0),
                "row_cnt": int(row[4] or 0),
            }
        except Exception as e:
            logger.debug(f"allocation_plan 목표 조회 실패: {e}")
            return {}

    def _get_confirmed_weight_kg(self, lot_no: str, sale_ref: str = None) -> float:
        try:
            where = "lot_no = ? AND undone = 0"
            params = [str(lot_no).strip()]
            if sale_ref:
                where += " AND COALESCE(sale_ref,'') = ?"
                params.append(str(sale_ref).strip())
            row = self.db.fetchone(
                f"SELECT SUM(COALESCE(weight_kg,0)) AS s FROM outbound_scan_log WHERE {where}",
                tuple(params),
            )
            if not row:
                return 0.0
            return float(row.get('s', 0) if isinstance(row, dict) else (row[0] or 0))
        except Exception:
            return 0.0

    def _is_uid_already_confirmed(self, uid: str) -> bool:
        uid = _clean_uid(uid)
        if not uid:
            return False
        try:
            row = self.db.fetchone(
                "SELECT id FROM outbound_scan_log WHERE tonbag_uid = ? AND undone = 0 LIMIT 1",
                (uid,),
            )
            return bool(row)
        except Exception:
            return False

    def _confirm_one_uid_random(self, uid: str, sale_ref: str = None, source_file: str = "") -> Dict:
        """(Phase3) UID 1건 스캔 → 즉시 SOLD(=OUT) 확정."""
        uid = _clean_uid(uid)
        if not uid:
            return {"ok": False, "uid": uid, "reason": "EMPTY"}

        if self._is_uid_already_confirmed(uid):
            return {"ok": False, "uid": uid, "reason": "DUPLICATE_CONFIRMED"}

        # tonbag 조회 (Phase2에서는 AVAILABLE/RESERVED/PICKED 어디든 올 수 있음)
        row = self.db.fetchone(
            "SELECT id, lot_no, sub_lt, weight, tonbag_uid, status "
            "FROM inventory_tonbag "
            "WHERE (tonbag_uid = ? OR CAST(sub_lt AS TEXT) = ? OR CAST(sub_lt AS TEXT) = ?) "
            "LIMIT 1",
            (uid, uid, _normalize_sublt(uid)),
        )
        if not row:
            return {"ok": False, "uid": uid, "reason": "UID_NOT_FOUND"}

        lot_no = str(row.get('lot_no', '')).strip()
        if not lot_no:
            return {"ok": False, "uid": uid, "reason": "LOT_EMPTY"}

        target = self._pick_target_row_for_lot(lot_no, sale_ref=sale_ref)
        target_mt = float(target.get('qty_mt_sum', 0) or 0)
        target_kg = target_mt * 1000.0
        if target_kg <= 0:
            return {"ok": False, "uid": uid, "reason": "TARGET_NOT_FOUND", "lot_no": lot_no}

        weight_kg = float(row.get('weight', 0) or 0)
        confirmed_kg = self._get_confirmed_weight_kg(lot_no, sale_ref=sale_ref)
        # 0.1% 또는 최소 1kg 허용 오차
        tolerance_kg = max(1.0, target_kg * 0.001)
        if confirmed_kg + weight_kg > target_kg + tolerance_kg:
            return {
                "ok": False,
                "uid": uid,
                "reason": "TARGET_EXCEEDED",
                "lot_no": lot_no,
                "target_kg": target_kg,
                "confirmed_kg": confirmed_kg,
                "this_kg": weight_kg,
            }

        customer = str(target.get('customer', '') or '').strip()
        eff_sale_ref = (str(sale_ref).strip() if sale_ref else str(target.get('sale_ref', '') or '').strip())

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 확정 처리: inventory_tonbag → SOLD (레거시 호환)
        self.db.execute(
            "UPDATE inventory_tonbag SET status='SOLD', outbound_date=?, picked_to=?, sale_ref=?, updated_at=? WHERE id=?",
            (now, customer, eff_sale_ref, now, row['id']),
        )
        # 로그 기록
        self.db.execute(
            "INSERT INTO outbound_scan_log (tonbag_id, tonbag_uid, lot_no, sale_ref, customer, weight_kg, source_file) "
            "VALUES (?,?,?,?,?,?,?)",
            (row['id'], uid, lot_no, eff_sale_ref, customer, weight_kg, source_file or ''),
        )
        # 재고 이동 이력(있으면)
        try:
            self.db.execute(
                "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                "VALUES (?,'SOLD',?,?,?)",
                (lot_no, weight_kg, f"phase3_scan_confirm uid={uid}", now),
            )
        except Exception:
            pass

        return {
            "ok": True,
            "uid": uid,
            "tonbag_id": row['id'],
            "lot_no": lot_no,
            "sale_ref": eff_sale_ref,
            "customer": customer,
            "weight_kg": weight_kg,
        }

    def process_barcode_scan_confirm_out(self, scanned_codes_or_file, sale_ref: str = None) -> Dict:
        """(Phase3) 스캔 파일/리스트 → 즉시 확정(OUT=SOLD)."""
        scanned_codes = (
            self.read_scan_file(scanned_codes_or_file)
            if isinstance(scanned_codes_or_file, str)
            else list(scanned_codes_or_file or [])
        )
        # UID 정리 + 중복 하드스톱
        seen, duplicates, uniq = set(), [], []
        for raw in scanned_codes:
            u = _clean_uid(raw)
            if not u:
                continue
            if u in seen:
                duplicates.append(u)
            else:
                seen.add(u)
                uniq.append(u)

        if duplicates:
            return {
                "success": False,
                "confirmed": 0,
                "duplicates": sorted(set(duplicates)),
                "errors": [f"중복 UID 스캔: {len(set(duplicates))}개"],
            }

        ok_rows, fails = [], []
        # 트랜잭션으로 원자성 확보 (All-or-Nothing)
        with self.db.transaction("IMMEDIATE"):
            for u in uniq:
                res = self._confirm_one_uid_random(u, sale_ref=sale_ref, source_file="barcode_scan")
                if res.get("ok"):
                    ok_rows.append(res)
                else:
                    fails.append(res)
            if fails:
                # 실패가 1건이라도 있으면 롤백 유도
                raise RuntimeError(json.dumps({"phase3_fail": fails}, ensure_ascii=False))

        return {
            "success": True,
            "confirmed": len(ok_rows),
            "rows": ok_rows,
        }


    def confirm_one_uid_live(self, uid: str, sale_ref: str = None, source: str = "live_scan") -> Dict:
        """(Phase4) 실시간 스캔 1건 확정.
        - Enter 입력(USB 스캐너 키보드 입력)용
        - 실패 시 예외를 던지지 않고 dict로 반환
        """
        try:
            with self.db.transaction("IMMEDIATE"):
                res = self._confirm_one_uid_random(uid, sale_ref=sale_ref, source_file=source)
                if not res.get("ok"):
                    return {"success": False, **res}
            return {"success": True, **res}
        except Exception as e:
            return {"success": False, "uid": _clean_uid(uid), "reason": "EXCEPTION", "message": str(e)}

    def export_scan_confirm_report_csv(self, rows: List[Dict], output_dir: str, prefix: str = "OUTBOUND_SCAN") -> str:
        """(Phase4) 스캔 확정 결과를 CSV로 저장하고 파일 경로를 반환."""
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception:
            pass
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(output_dir, f"{prefix}_{ts}.csv")
        fields = ["sale_ref", "customer", "lot_no", "tonbag_id", "uid", "weight_kg"]
        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                for r in rows or []:
                    if not isinstance(r, dict):
                        continue
                    w.writerow({
                        "sale_ref": r.get("sale_ref", ""),
                        "customer": r.get("customer", ""),
                        "lot_no": r.get("lot_no", ""),
                        "tonbag_id": r.get("tonbag_id", ""),
                        "uid": r.get("uid", ""),
                        "weight_kg": r.get("weight_kg", ""),
                    })
            return path
        except Exception as e:
            logger.debug(f"CSV 리포트 저장 실패: {e}")
            return ""

    def undo_last_scan_confirm(self, sale_ref: str = None) -> Dict:
        """(Phase3) 최근 스캔 확정 1건 Undo (관리자용)."""
        try:
            where = "undone = 0"
            params = []
            if sale_ref:
                where += " AND COALESCE(sale_ref,'') = ?"
                params.append(str(sale_ref).strip())
            row = self.db.fetchone(
                f"SELECT id, tonbag_id, tonbag_uid, lot_no, weight_kg FROM outbound_scan_log "
                f"WHERE {where} ORDER BY id DESC LIMIT 1",
                tuple(params),
            )
            if not row:
                return {"success": False, "message": "Undo 대상 스캔 로그가 없습니다."}

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                self.db.execute(
                    "UPDATE outbound_scan_log SET undone = 1, undone_at = ? WHERE id = ?",
                    (now, row['id']),
                )
                # tonbag 상태 복구: AVAILABLE 로 복귀 (Phase2 기본)
                self.db.execute(
                    "UPDATE inventory_tonbag SET status='AVAILABLE', updated_at=? WHERE id=?",
                    (now, row['tonbag_id']),
                )
                try:
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?,'UNDO_SOLD',?,?,?)",
                        (row.get('lot_no', ''), float(row.get('weight_kg', 0) or 0), f"undo uid={row.get('tonbag_uid','')}", now),
                    )
                except Exception:
                    pass
            return {"success": True, "message": "최근 스캔 확정 1건을 되돌렸습니다.", "uid": row.get('tonbag_uid','')}
        except Exception as e:
            return {"success": False, "message": f"Undo 실패: {e}"}

    def _ensure_table(self):
        try:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS uid_verify_history (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    outbound_ref    TEXT,
                    sale_ref        TEXT,
                    verify_result   TEXT NOT NULL,
                    expected_count  INTEGER,
                    scanned_count   INTEGER,
                    missing_uids    TEXT,
                    extra_uids      TEXT,
                    duplicate_uids  TEXT,
                    scan_file_name  TEXT,
                    verified_at     TEXT DEFAULT (datetime('now'))
                )
            """)
            try:
                self.db.execute("ALTER TABLE uid_verify_history ADD COLUMN sale_ref TEXT")
            except Exception as _ae:
                # 컬럼 이미 존재 시 정상 (sqlite3.OperationalError: duplicate column)
                logging.getLogger(__name__).debug(f"[바코드] sale_ref 컬럼 추가 스킵: {_ae}")
            try:
                self.db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_verify_history_ref "
                    "ON uid_verify_history(outbound_ref)"
                )
                self.db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_verify_history_at "
                    "ON uid_verify_history(verified_at DESC)"
                )
                self.db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_verify_history_sale "
                    "ON uid_verify_history(sale_ref)"
                )
            except Exception as _ie:
                logging.getLogger(__name__).debug(f"[바코드] sale_ref 인덱스 생성 스킵: {_ie}")
        except Exception as e:
            logger.debug(f"uid_verify_history 테이블 생성 스킵: {e}")

    def _ensure_swap_table(self):
        try:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS uid_swap_history (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    lot_no              TEXT NOT NULL,
                    expected_tonbag_id  INTEGER,
                    expected_uid        TEXT,
                    scanned_tonbag_id   INTEGER,
                    scanned_uid         TEXT,
                    reason              TEXT,
                    created_at          TEXT DEFAULT (datetime('now'))
                )
            """)
        except Exception as e:
            logger.debug(f"uid_swap_history 테이블 생성 스킵: {e}")

    def _uid_to_lot_map(self, uids: List[str]) -> Dict[str, str]:
        if not uids:
            return {}
        uniq = [u for u in dict.fromkeys([str(x).strip() for x in uids if str(x).strip()])]
        if not uniq:
            return {}
        try:
            placeholders = ",".join("?" * len(uniq))
            rows = self.db.fetchall(
                f"SELECT tonbag_uid, lot_no FROM inventory_tonbag WHERE tonbag_uid IN ({placeholders})",
                tuple(uniq),
            )
            out = {}
            for r in rows or []:
                uid = str(r.get("tonbag_uid", "")).strip()
                lot = str(r.get("lot_no", "")).strip()
                if uid and lot:
                    out[uid] = lot
            return out
        except Exception as e:
            logger.debug(f"UID→LOT 매핑 조회 실패: {e}")
            return {}

    def read_scan_file(self, file_path: str) -> List[str]:
        def _clean_lines(lines: List[str]) -> List[str]:
            cleaned = []
            for line in lines:
                uid = _clean_uid(line)
                if not uid:
                    continue
                # 헤더 라인(UID/BARCODE 등) 자동 제외
                u = uid.upper()
                if u in ('UID', 'BARCODE', 'TONBAG_UID', 'SUB_LT'):
                    continue
                cleaned.append(uid)
            return cleaned

        ext = file_path.lower().rsplit('.', 1)[-1] if '.' in file_path else ''
        if ext == 'txt':
            encodings = ('utf-8-sig', 'utf-8', 'cp949', 'euc-kr', 'latin-1')
            for enc in encodings:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        lines = _clean_lines([line for line in f])
                    if lines:
                        return lines
                except (UnicodeDecodeError, UnicodeError):
                    continue
            return []
        elif ext == 'csv':
            import pandas as pd
            encodings = ('utf-8-sig', 'utf-8', 'cp949', 'euc-kr', 'latin-1')
            for enc in encodings:
                try:
                    df = pd.read_csv(file_path, header=None, dtype=str, encoding=enc)
                    values = df.iloc[:, 0].dropna().tolist()
                    lines = _clean_lines(values)
                    if lines:
                        return lines
                except (UnicodeDecodeError, UnicodeError):
                    continue
                except Exception:
                    continue
            return []
        elif ext in ('xlsx', 'xls'):
            import pandas as pd
            df = pd.read_excel(file_path, header=None, dtype=str)
            values = df.iloc[:, 0].dropna().tolist()
            return _clean_lines(values)
        else:
            raise ValueError(f"지원하지 않는 파일 형식: .{ext}")

    def _build_picked_maps(self, sale_ref: str = None) -> Tuple[List[Dict], Dict[str, Dict], Dict[str, Dict]]:
        query = (
            "SELECT id, lot_no, sub_lt, weight, tonbag_uid, picked_to, sale_ref "
            "FROM inventory_tonbag WHERE status = 'PICKED'"
        )
        params = []
        if sale_ref:
            query += " AND sale_ref = ?"
            params.append(sale_ref)
        rows = self.db.fetchall(query, tuple(params)) or []
        uid_map, sublt_map = {}, {}
        for r in rows:
            uid = _clean_uid(r.get('tonbag_uid', ''))
            if uid:
                uid_map[uid] = r
            sub_lt_raw = str(r.get('sub_lt', '')).strip()
            if sub_lt_raw:
                sublt_map[sub_lt_raw] = r
                sublt_map[_normalize_sublt(sub_lt_raw)] = r
        return rows, uid_map, sublt_map

    def verify_outbound_scan(self, expected_uids: Set[str], scanned_uids_raw: List[str],
                              outbound_ref: str = '', scan_file_name: str = '', sale_ref: str = '') -> Dict:
        picked_rows, uid_map, sublt_map = self._build_picked_maps(sale_ref=sale_ref or None)
        # expected_uids가 넘어오면 호출자 기준(expected_uids) 우선, 없으면 DB PICKED fallback
        use_db_expected = not bool(expected_uids) and bool(picked_rows)
        expected_ids = {int(r['id']) for r in picked_rows} if use_db_expected else set()

        seen_codes, duplicates = set(), []
        matched_ids = set()
        extra_codes = []
        for raw in scanned_uids_raw:
            code = _clean_uid(raw)
            if not code:
                continue
            if code in seen_codes:
                duplicates.append(code)
                continue
            seen_codes.add(code)
            if use_db_expected:
                row = uid_map.get(code) or sublt_map.get(code) or sublt_map.get(_normalize_sublt(code))
                if row:
                    matched_ids.add(int(row['id']))
                else:
                    extra_codes.append(code)
            else:
                # DB PICKED가 없으면 호출자 expected_uids로 fallback 검증 (테스트/레거시 호환)
                pass

        if use_db_expected:
            missing_rows = [r for r in picked_rows if int(r['id']) not in matched_ids]
            missing = sorted([
                _clean_uid(r.get('tonbag_uid') or '') or str(r.get('sub_lt', ''))
                for r in missing_rows
            ])
            extra = sorted(set(extra_codes))
            expected_count = len(expected_ids)
        else:
            expected_clean = {_clean_uid(u) for u in (expected_uids or set()) if _clean_uid(u)}
            expected_norm = {_normalize_sublt(u) for u in expected_clean}
            scanned_norm = {_normalize_sublt(s) for s in seen_codes}
            missing = sorted([u for u in expected_clean if _normalize_sublt(u) not in scanned_norm])
            extra = sorted([s for s in seen_codes if _normalize_sublt(s) not in expected_norm])
            expected_count = len(expected_clean)
        duplicates = sorted(set(duplicates))
        # 중복은 경고로만 취급 (PASS 유지)
        passed = (not missing) and (not extra)
        pass_swap = False
        swap_lots = []
        if (not duplicates) and missing and extra:
            miss_map = self._uid_to_lot_map(missing)
            extra_map = self._uid_to_lot_map(extra)
            if len(miss_map) == len(missing) and len(extra_map) == len(extra):
                miss_cnt_by_lot = {}
                extra_cnt_by_lot = {}
                for uid in missing:
                    lot = miss_map.get(uid, '')
                    miss_cnt_by_lot[lot] = miss_cnt_by_lot.get(lot, 0) + 1
                for uid in extra:
                    lot = extra_map.get(uid, '')
                    extra_cnt_by_lot[lot] = extra_cnt_by_lot.get(lot, 0) + 1
                # LOT 내부 스왑 조건: 각 LOT에서 extra <= missing
                lot_ok = True
                for lot, ec in extra_cnt_by_lot.items():
                    if not lot or ec > miss_cnt_by_lot.get(lot, 0):
                        lot_ok = False
                        break
                if lot_ok:
                    pass_swap = True
                    swap_lots = sorted(extra_cnt_by_lot.keys())

        result = {
            'result': 'PASS' if passed else ('PASS_SWAP' if pass_swap else 'FAIL'),
            'missing': missing, 'extra': extra, 'duplicates': duplicates,
            'expected_count': expected_count, 'scanned_count': len(scanned_uids_raw),
            'scanned_unique_count': len(seen_codes),
            'swap_lots': swap_lots,
        }
        if passed:
            if duplicates:
                result['message'] = (
                    f"✅ UID 대조 통과 ({expected_count}개 일치, "
                    f"중복 {len(duplicates)}개 경고)"
                )
            else:
                result['message'] = f"✅ UID 대조 통과 ({expected_count}개 일치)"
        elif pass_swap:
            result['message'] = (
                f"⚠️ UID 대조 조건부 통과(PASS_SWAP): "
                f"같은 LOT 내부 스왑으로 진행 가능 (LOT {len(swap_lots)}개)"
            )
        else:
            parts = []
            if missing: parts.append(f"누락 {len(missing)}개")
            if extra: parts.append(f"초과 {len(extra)}개")
            if duplicates: parts.append(f"중복 {len(duplicates)}개")
            result['message'] = f"❌ UID 대조 실패: {', '.join(parts)}"

        try:
            self.db.execute("""
                INSERT INTO uid_verify_history
                (outbound_ref, sale_ref, verify_result, expected_count, scanned_count,
                 missing_uids, extra_uids, duplicate_uids, scan_file_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (outbound_ref, sale_ref, result['result'], result['expected_count'],
                  result['scanned_count'],
                  json.dumps(missing, ensure_ascii=False) if missing else None,
                  json.dumps(extra, ensure_ascii=False) if extra else None,
                  json.dumps(duplicates, ensure_ascii=False) if duplicates else None,
                  scan_file_name))
        except Exception as e:
            logger.warning(f"uid_verify_history 기록 실패: {e}")
        return result

    def get_picked_uids(self, lot_no: str = None, sale_ref: str = None) -> Set[str]:
        query = "SELECT tonbag_uid FROM inventory_tonbag WHERE status = 'PICKED' AND tonbag_uid IS NOT NULL"
        params = []
        if lot_no:
            query += " AND lot_no = ?"
            params.append(lot_no)
        if sale_ref:
            query += " AND sale_ref = ?"
            params.append(sale_ref)
        rows = self.db.fetchall(query, tuple(params))
        return {_clean_uid(r['tonbag_uid']) for r in rows if r.get('tonbag_uid') and _clean_uid(r['tonbag_uid'])}

    def get_picked_sale_refs(self) -> List[str]:
        try:
            rows = self.db.fetchall(
                "SELECT DISTINCT sale_ref FROM inventory_tonbag "
                "WHERE status='PICKED' AND sale_ref IS NOT NULL AND sale_ref != '' "
                "ORDER BY sale_ref"
            ) or []
            return [str(r.get('sale_ref', '')).strip() for r in rows if str(r.get('sale_ref', '')).strip()]
        except Exception:
            return []

    def get_lot_mode_reserved_count(self) -> int:
        """LOT 단위 예약(tonbag_id 미지정) 잔여 건수."""
        try:
            row = self.db.fetchone(
                "SELECT COUNT(*) AS cnt FROM allocation_plan WHERE status='RESERVED' AND tonbag_id IS NULL"
            )
            return int(row.get('cnt', 0) if isinstance(row, dict) else (row[0] if row else 0))
        except Exception:
            return 0

    def process_barcode_scan_for_lot_mode(self, file_path: str) -> Dict:
        """
        LOT 단위 예약 모드 전용 스캔 처리.
        - allocation_plan(RESERVED, tonbag_id IS NULL)의 LOT 계획 1건을 스캔 UID 1건과 매칭
        - 매칭된 톤백은 SOLD 전환
        """
        scanned_codes = self.read_scan_file(file_path)
        seen = set()
        duplicates = []
        uniq_codes = []
        for code in scanned_codes:
            c = _clean_uid(code)
            if not c:
                continue
            if c in seen:
                duplicates.append(c)
            else:
                seen.add(c)
                uniq_codes.append(c)

        if duplicates:
            return {
                'success': False,
                'sold': 0,
                'not_found': [],
                'no_plan': [],
                'duplicates': sorted(set(duplicates)),
                'remaining_lot_reserved': self.get_lot_mode_reserved_count(),
                'errors': [f"중복 UID 스캔: {len(set(duplicates))}개"],
            }

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sold_count = 0
        not_found = []
        no_plan = []
        with self.db.transaction("IMMEDIATE"):
            for code in uniq_codes:
                row = self.db.fetchone(
                    "SELECT id, lot_no, sub_lt, weight, tonbag_uid, status FROM inventory_tonbag "
                    "WHERE (tonbag_uid = ? OR CAST(sub_lt AS TEXT) = ?) "
                    "AND status IN ('AVAILABLE','RESERVED','PICKED')",
                    (code, code),
                )
                if not row:
                    not_found.append(code)
                    continue

                lot_no = row.get('lot_no', '')
                plan = self.db.fetchone(
                    "SELECT id, customer, sale_ref FROM allocation_plan "
                    "WHERE status='RESERVED' AND tonbag_id IS NULL AND lot_no=? "
                    "ORDER BY id ASC LIMIT 1",
                    (lot_no,),
                )
                if not plan:
                    no_plan.append(code)
                    continue

                self.db.execute(
                    "UPDATE inventory_tonbag SET status='SOLD', outbound_date=?, picked_to=?, sale_ref=?, updated_at=? WHERE id=?",
                    (now, plan.get('customer', ''), plan.get('sale_ref', ''), now, row['id']),
                )
                self.db.execute(
                    "UPDATE allocation_plan SET status='EXECUTED', executed_at=?, tonbag_id=?, sub_lt=? WHERE id=?",
                    (now, row['id'], row.get('sub_lt'), plan['id']),
                )
                try:
                    self.db.execute(
                        "INSERT INTO sold_table "
                        "(lot_no, tonbag_id, sub_lt, tonbag_uid, sold_qty_kg, sold_date, status, created_by) "
                        "VALUES (?,?,?,?,?,?,'SOLD','barcode_lot_mode')",
                        (
                            lot_no,
                            row['id'],
                            row.get('sub_lt', 0),
                            row.get('tonbag_uid') or code,
                            row.get('weight') or 0,
                            now,
                        ),
                    )
                except Exception as e:
                    logger.debug(f"sold_table insert skipped in lot_mode scan: {e}")
                self.db.execute(
                    "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                    "VALUES (?,'SOLD',?,?,?)",
                    (
                        lot_no,
                        row.get('weight') or 0,
                        f"barcode_lot_mode uid={code}, plan_id={plan['id']}",
                        now,
                    ),
                )
                sold_count += 1

        return {
            'success': sold_count > 0,
            'sold': sold_count,
            'not_found': not_found,
            'no_plan': no_plan,
            'duplicates': sorted(set(duplicates)),
            'remaining_lot_reserved': self.get_lot_mode_reserved_count(),
        }

    def process_barcode_scan_to_sold(self, scanned_codes_or_file, sale_ref: str = None) -> Dict:
        scanned_codes = (
            self.read_scan_file(scanned_codes_or_file)
            if isinstance(scanned_codes_or_file, str)
            else list(scanned_codes_or_file or [])
        )
        # 중복 스캔은 하드스톱
        seen = set()
        duplicates = []
        uniq_codes = []
        for code in scanned_codes:
            c = str(code).strip()
            if not c:
                continue
            if c in seen:
                duplicates.append(c)
            else:
                seen.add(c)
                uniq_codes.append(c)
        dup_set = sorted(set(duplicates))

        sold_count, not_found, swap_count = 0, [], 0
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        scanned_set = set(uniq_codes)

        with self.db.transaction("IMMEDIATE"):
            for code in uniq_codes:
                code = code.strip()
                if not code: continue
                row = self.db.fetchone(
                    "SELECT id, lot_no, sub_lt, weight, tonbag_uid FROM inventory_tonbag "
                    "WHERE (tonbag_uid = ? OR CAST(sub_lt AS TEXT) = ? OR CAST(sub_lt AS TEXT) = ?) "
                    "AND status = 'PICKED' "
                    + ("AND sale_ref = ?" if sale_ref else ""),
                    ((code, code, _normalize_sublt(code), sale_ref) if sale_ref else (code, code, _normalize_sublt(code))))
                if row:
                    self.db.execute(
                        "UPDATE inventory_tonbag SET status='SOLD', outbound_date=?, updated_at=? "
                        "WHERE id=? AND status='PICKED'",
                        (now, now, row['id'])
                    )
                    try:
                        self.db.execute(
                            "INSERT INTO sold_table (lot_no, tonbag_id, sub_lt, tonbag_uid, sold_qty_kg, sold_date, status, created_by) VALUES (?,?,?,?,?,?,'SOLD','barcode_scan')",
                            (row['lot_no'], row['id'], row['sub_lt'], row.get('tonbag_uid') or '', row.get('weight') or 0, now))
                    except Exception as e:
                        logger.debug(f"sold_table insert skipped in barcode scan: {e}")
                    try:
                        self.db.execute("UPDATE picking_table SET status='SOLD', sold_date=? WHERE tonbag_id=? AND status='ACTIVE'", (now, row['id']))
                    except Exception as e:
                        logger.debug(f"picking_table status update skipped in barcode scan: {e}")
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) VALUES (?,'SOLD',?,?,?)",
                        (row['lot_no'], row.get('weight') or 0, f"barcode_scan uid={code}", now))
                    sold_count += 1
                else:
                    scanned_row = self.db.fetchone(
                        "SELECT id, lot_no, sub_lt, weight, tonbag_uid, picked_to, sale_ref, status "
                        "FROM inventory_tonbag "
                        "WHERE (tonbag_uid = ? OR CAST(sub_lt AS TEXT) = ? OR CAST(sub_lt AS TEXT) = ?) "
                        "AND status IN ('AVAILABLE','RESERVED')",
                        (code, code, _normalize_sublt(code)),
                    )
                    if not scanned_row:
                        not_found.append(code)
                        continue

                    lot_no = scanned_row.get('lot_no', '')
                    picked_row = self.db.fetchone(
                        "SELECT id, lot_no, sub_lt, weight, tonbag_uid, picked_to, sale_ref "
                        "FROM inventory_tonbag "
                        "WHERE lot_no = ? AND status = 'PICKED' "
                        + ("AND sale_ref = ? " if sale_ref else "")
                        + "AND COALESCE(tonbag_uid,'') <> '' AND tonbag_uid NOT IN ({}) "
                        "ORDER BY sub_lt ASC LIMIT 1".format(",".join("?" * len(scanned_set))),
                        ((lot_no, sale_ref, *tuple(scanned_set)) if sale_ref and scanned_set else
                         (lot_no, sale_ref) if sale_ref and not scanned_set else
                         (lot_no, *tuple(scanned_set))),
                    ) if scanned_set else self.db.fetchone(
                        "SELECT id, lot_no, sub_lt, weight, tonbag_uid, picked_to, sale_ref "
                        "FROM inventory_tonbag WHERE lot_no = ? AND status = 'PICKED' "
                        + ("AND sale_ref = ? " if sale_ref else "")
                        + "ORDER BY sub_lt ASC LIMIT 1",
                        ((lot_no, sale_ref) if sale_ref else (lot_no,)),
                    )

                    if not picked_row:
                        not_found.append(code)
                        continue

                    # LOT 내부 swap: 기존 PICKED는 RESERVED로 복귀, 실제 스캔 톤백은 SOLD 처리
                    self.db.execute(
                        "UPDATE inventory_tonbag SET status='RESERVED', picked_date=NULL, outbound_date=NULL, updated_at=? "
                        "WHERE id=?",
                        (now, picked_row['id']),
                    )
                    self.db.execute(
                        "UPDATE inventory_tonbag SET status='SOLD', outbound_date=?, picked_to=?, sale_ref=?, updated_at=? "
                        "WHERE id=?",
                        (now, picked_row.get('picked_to', ''), picked_row.get('sale_ref', ''), now, scanned_row['id']),
                    )
                    self.db.execute(
                        "INSERT INTO uid_swap_history "
                        "(lot_no, expected_tonbag_id, expected_uid, scanned_tonbag_id, scanned_uid, reason, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            lot_no,
                            picked_row.get('id'),
                            picked_row.get('tonbag_uid', ''),
                            scanned_row.get('id'),
                            scanned_row.get('tonbag_uid', '') or code,
                            'PASS_SWAP lot_internal',
                            now,
                        ),
                    )
                    try:
                        self.db.execute(
                            "INSERT INTO sold_table "
                            "(lot_no, tonbag_id, sub_lt, tonbag_uid, sold_qty_kg, sold_date, status, created_by) "
                            "VALUES (?,?,?,?,?,?,'SOLD','barcode_scan_swap')",
                            (
                                lot_no, scanned_row['id'], scanned_row.get('sub_lt', 0),
                                scanned_row.get('tonbag_uid') or code, scanned_row.get('weight') or 0, now
                            ),
                        )
                    except Exception as e:
                        logger.debug(f"sold_table insert skipped in barcode swap: {e}")
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?,'SOLD',?,?,?)",
                        (
                            lot_no,
                            scanned_row.get('weight') or 0,
                            f"barcode_scan PASS_SWAP scanned={code}, expected_uid={picked_row.get('tonbag_uid','')}",
                            now,
                        ),
                    )
                    sold_count += 1
                    swap_count += 1

        remaining_query = "SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE status='PICKED'"
        remaining_params = ()
        if sale_ref:
            remaining_query += " AND sale_ref = ?"
            remaining_params = (sale_ref,)
        remaining = self.db.fetchone(remaining_query, remaining_params)
        remaining_cnt = (remaining['cnt'] if isinstance(remaining, dict) else remaining[0]) if remaining else 0

        return {
            'success': True,
            'sold': sold_count,
            'swap_count': swap_count,
            'not_found': not_found,
            'duplicates': dup_set,
            'remaining_picked': remaining_cnt,
        }

    def process_barcode_scan_to_sold_from_file(self, file_path: str, sale_ref: str = None) -> Dict:
        """레거시 호환용: 파일 경로 기반 호출."""
        return self.process_barcode_scan_to_sold(file_path, sale_ref=sale_ref)

    def get_picked_full_info(self, sale_ref: str = None) -> List[Dict]:
        """PICKED 톤백 상세 정보 반환 (검증 미리보기용)."""
        query = (
            "SELECT id, lot_no, sub_lt, weight, tonbag_uid, sale_ref, "
            "picked_to, picked_date, location "
            "FROM inventory_tonbag WHERE status='PICKED'"
        )
        params = []
        if sale_ref:
            query += " AND sale_ref = ?"
            params.append(sale_ref)
        query += " ORDER BY lot_no, sub_lt"
        try:
            return self.db.fetchall(query, tuple(params)) or []
        except Exception:
            return []

    def get_verify_history(self, limit: int = 50) -> List[Dict]:
        try:
            return self.db.fetchall("SELECT * FROM uid_verify_history ORDER BY verified_at DESC LIMIT ?", (limit,))
        except Exception:
            return []
