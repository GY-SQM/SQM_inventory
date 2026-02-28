# -*- coding: utf-8 -*-
"""
SQM v6.12 Stage3 — 바코드 스캔 대조 엔진
==========================================
출고 확정 전 현장 스캔 UID와 시스템 출고 예정 UID를 대조.
불일치 시 Hard Stop.

작성자: Ruby
"""
import json
import logging
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
            except Exception:
                pass
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
        # expected_uids 인자는 하위호환 유지용(실제 검증은 DB PICKED 기반으로 통일)
        _ = expected_uids
        picked_rows, uid_map, sublt_map = self._build_picked_maps(sale_ref=sale_ref or None)
        expected_ids = {int(r['id']) for r in picked_rows}

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
            row = uid_map.get(code) or sublt_map.get(code) or sublt_map.get(_normalize_sublt(code))
            if row:
                matched_ids.add(int(row['id']))
            else:
                extra_codes.append(code)

        missing_rows = [r for r in picked_rows if int(r['id']) not in matched_ids]
        missing = sorted([
            _clean_uid(r.get('tonbag_uid') or '') or str(r.get('sub_lt', ''))
            for r in missing_rows
        ])
        extra = sorted(set(extra_codes))
        duplicates = sorted(set(duplicates))
        passed = (not missing) and (not extra) and (not duplicates)
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
            'expected_count': len(expected_ids), 'scanned_count': len(scanned_uids_raw),
            'scanned_unique_count': len(seen_codes),
            'swap_lots': swap_lots,
        }
        if passed:
            result['message'] = f"✅ UID 대조 통과 ({len(expected_ids)}개 일치)"
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
        if duplicates:
            return {
                'success': False,
                'sold': 0,
                'not_found': [],
                'duplicates': sorted(set(duplicates)),
                'remaining_picked': 0,
                'errors': [f"중복 UID 스캔: {len(set(duplicates))}개"],
            }

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
            'remaining_picked': remaining_cnt,
        }

    def get_verify_history(self, limit: int = 50) -> List[Dict]:
        try:
            return self.db.fetchall("SELECT * FROM uid_verify_history ORDER BY verified_at DESC LIMIT ?", (limit,))
        except Exception:
            return []
