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
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class BarcodeScanEngine:
    """바코드 스캔 대조 + uid_verify_history 관리"""

    def __init__(self, db):
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        try:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS uid_verify_history (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    outbound_ref    TEXT,
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
        except Exception as e:
            logger.debug(f"uid_verify_history 테이블 생성 스킵: {e}")

    def read_scan_file(self, file_path: str) -> List[str]:
        ext = file_path.lower().rsplit('.', 1)[-1] if '.' in file_path else ''
        if ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        elif ext == 'csv':
            import pandas as pd
            df = pd.read_csv(file_path, header=None, dtype=str)
            return df.iloc[:, 0].dropna().str.strip().tolist()
        elif ext in ('xlsx', 'xls'):
            import pandas as pd
            df = pd.read_excel(file_path, header=None, dtype=str)
            return df.iloc[:, 0].dropna().str.strip().tolist()
        else:
            raise ValueError(f"지원하지 않는 파일 형식: .{ext}")

    def verify_outbound_scan(self, expected_uids: Set[str], scanned_uids_raw: List[str],
                              outbound_ref: str = '', scan_file_name: str = '') -> Dict:
        seen, duplicates, scanned_unique = set(), [], set()
        for uid in scanned_uids_raw:
            if uid in seen:
                duplicates.append(uid)
            else:
                seen.add(uid)
                scanned_unique.add(uid)

        missing = sorted(expected_uids - scanned_unique)
        extra = sorted(scanned_unique - expected_uids)
        duplicates = sorted(set(duplicates))
        passed = (not missing) and (not extra) and (not duplicates)

        result = {
            'result': 'PASS' if passed else 'FAIL',
            'missing': missing, 'extra': extra, 'duplicates': duplicates,
            'expected_count': len(expected_uids), 'scanned_count': len(scanned_uids_raw),
        }
        if passed:
            result['message'] = f"✅ UID 대조 통과 ({len(expected_uids)}개 일치)"
        else:
            parts = []
            if missing: parts.append(f"누락 {len(missing)}개")
            if extra: parts.append(f"초과 {len(extra)}개")
            if duplicates: parts.append(f"중복 {len(duplicates)}개")
            result['message'] = f"❌ UID 대조 실패: {', '.join(parts)}"

        try:
            self.db.execute("""
                INSERT INTO uid_verify_history
                (outbound_ref, verify_result, expected_count, scanned_count,
                 missing_uids, extra_uids, duplicate_uids, scan_file_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (outbound_ref, result['result'], result['expected_count'],
                  result['scanned_count'],
                  json.dumps(missing, ensure_ascii=False) if missing else None,
                  json.dumps(extra, ensure_ascii=False) if extra else None,
                  json.dumps(duplicates, ensure_ascii=False) if duplicates else None,
                  scan_file_name))
        except Exception as e:
            logger.warning(f"uid_verify_history 기록 실패: {e}")
        return result

    def get_picked_uids(self, lot_no: str = None) -> Set[str]:
        query = "SELECT tonbag_uid FROM inventory_tonbag WHERE status = 'PICKED' AND tonbag_uid IS NOT NULL"
        params = []
        if lot_no:
            query += " AND lot_no = ?"
            params.append(lot_no)
        rows = self.db.fetchall(query, tuple(params))
        return {r['tonbag_uid'] for r in rows if r.get('tonbag_uid')}

    def process_barcode_scan_to_sold(self, file_path: str) -> Dict:
        scanned_codes = self.read_scan_file(file_path)
        sold_count, not_found = 0, []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with self.db.transaction("IMMEDIATE"):
            for code in scanned_codes:
                code = code.strip()
                if not code: continue
                row = self.db.fetchone(
                    "SELECT id, lot_no, sub_lt, weight, tonbag_uid FROM inventory_tonbag "
                    "WHERE (tonbag_uid = ? OR CAST(sub_lt AS TEXT) = ?) AND status = 'PICKED'",
                    (code, code))
                if row:
                    self.db.execute("UPDATE inventory_tonbag SET status='SOLD', outbound_date=?, updated_at=? WHERE id=?",
                                    (now, now, row['id']))
                    try:
                        self.db.execute(
                            "INSERT INTO sold_table (lot_no, tonbag_id, sub_lt, tonbag_uid, sold_qty_kg, sold_date, status, created_by) VALUES (?,?,?,?,?,?,'SOLD','barcode_scan')",
                            (row['lot_no'], row['id'], row['sub_lt'], row.get('tonbag_uid') or '', row.get('weight') or 0, now))
                    except Exception: pass
                    try:
                        self.db.execute("UPDATE picking_table SET status='SOLD', sold_date=? WHERE tonbag_id=? AND status='ACTIVE'", (now, row['id']))
                    except Exception: pass
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) VALUES (?,'SOLD',?,?,?)",
                        (row['lot_no'], row.get('weight') or 0, f"barcode_scan uid={code}", now))
                    sold_count += 1
                else:
                    not_found.append(code)

        remaining = self.db.fetchone("SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE status='PICKED'")
        remaining_cnt = (remaining['cnt'] if isinstance(remaining, dict) else remaining[0]) if remaining else 0

        return {'success': True, 'sold': sold_count, 'not_found': not_found, 'remaining_picked': remaining_cnt}

    def get_verify_history(self, limit: int = 50) -> List[Dict]:
        try:
            return self.db.fetchall("SELECT * FROM uid_verify_history ORDER BY verified_at DESC LIMIT ?", (limit,))
        except Exception:
            return []
