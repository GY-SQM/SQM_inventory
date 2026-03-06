ALLOCATION_FORCE_APPROVAL_ALL = True

# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 출고 처리 Mixin
======================================

v3.6.6: SQLAlchemy → SQMDatabase API 전환 (self.db 기반)

작성자: Ruby (남기동)
버전: v3.6.6
"""

import sqlite3
import logging
import math
import random
import os
import hashlib
import configparser
import csv
import json
from datetime import datetime
from typing import Dict, List, Optional
from utils.path_utils import resolve_reports_dir

from core.constants import (
    STATUS_AVAILABLE,
    STATUS_RESERVED,
    STATUS_DEPLETED,
    STATUS_PICKED,
    STATUS_SOLD,
)
from core.types import normalize_lot

from .base import InventoryBaseMixin

logger = logging.getLogger(__name__)


class OutboundMixin(InventoryBaseMixin):
    ALLOCATION_APPROVAL_QTY_KG_THRESHOLD = 10000.0
    ALLOCATION_APPROVAL_RATIO_THRESHOLD = 0.5

    def _table_exists(self, table_name: str) -> bool:
        try:
            row = self.db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            return bool(row)
        except Exception:
            return False

    def _ensure_outbound_txn_tables(self) -> None:
        """outbound_event_log 테이블 best-effort 생성 (RUBI 패치·타임라인 UI용)."""
        try:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS outbound_event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    outbound_no TEXT,
                    event_type TEXT,
                    message TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_outbound_event_log_created "
                "ON outbound_event_log(created_at DESC)"
            )
        except Exception as e:
            logger.debug(f"outbound_event_log 테이블 생성 스킵: {e}")

    def get_outbound_event_log(self, limit: int = 50) -> List[Dict]:
        """출고 이벤트 로그 최근 N건 조회 (타임라인 UI용). 테이블 없으면 빈 목록."""
        try:
            self._ensure_outbound_txn_tables()
            rows = self.db.fetchall(
                "SELECT id, outbound_no, event_type, message, created_at "
                "FROM outbound_event_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            if not rows:
                return []
            out = []
            for r in rows:
                if isinstance(r, dict):
                    out.append(dict(r))
                else:
                    out.append({
                        "id": r[0], "outbound_no": r[1] or "",
                        "event_type": r[2] or "", "message": r[3] or "",
                        "created_at": r[4] or "",
                    })
            return out
        except Exception as e:
            logger.debug(f"get_outbound_event_log: {e}")
            return []

    def _get_outbound_status(self, outbound_no: str) -> str:
        """출고번호별 상태 문자열 반환 (배너용). outbound 테이블에 status 컬럼 있으면 사용."""
        if not outbound_no:
            return ""
        try:
            row = self.db.fetchone(
                "SELECT status FROM outbound WHERE outbound_no = ? LIMIT 1",
                (outbound_no,),
            )
            if row:
                return (row.get("status") if isinstance(row, dict) else row[0]) or ""
        except Exception:
            pass
        return ""

    def clear_pending_allocation_on_exit(self) -> Dict:
        """
        프로그램 종료 시 승인되지 않은 Allocation 대기건 정리.

        대상: allocation_plan.status='STAGED' AND workflow_status='PENDING_APPROVAL'
        처리: workflow_status='REJECTED', rejected_reason='AUTO_CLEAR_ON_EXIT'
        """
        result = {"success": False, "cleared": 0, "error": ""}
        try:
            if not self._table_exists("allocation_plan"):
                result["success"] = True
                return result

            cols = self.db.fetchall("PRAGMA table_info(allocation_plan)") or []
            col_names = {
                str(c.get("name", "")).strip().lower()
                for c in cols
                if isinstance(c, dict)
            }
            if "workflow_status" not in col_names:
                result["success"] = True
                return result

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            actor = "system_exit"
            with self.db.transaction("IMMEDIATE"):
                cur = self.db.execute(
                    """
                    UPDATE allocation_plan
                       SET workflow_status = 'REJECTED',
                           rejected_reason = COALESCE(NULLIF(rejected_reason,''), 'AUTO_CLEAR_ON_EXIT'),
                           approved_by = COALESCE(NULLIF(approved_by,''), ?),
                           approved_at = COALESCE(approved_at, ?)
                     WHERE status = 'STAGED'
                       AND workflow_status = 'PENDING_APPROVAL'
                    """,
                    (actor, now),
                )
                try:
                    result["cleared"] = int(getattr(cur, "rowcount", 0) or 0)
                except (TypeError, ValueError):
                    result["cleared"] = 0
            result["success"] = True
            if result["cleared"] > 0:
                logger.info(f"[allocation] 종료 시 승인대기 자동 정리: {result['cleared']}건")
            return result
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"[allocation] 종료 시 승인대기 정리 실패: {e}", exc_info=True)
            return result

    def _normalize_outbound_date(self, raw_date) -> str:
        """outbound_date를 YYYY-MM-DD로 정규화, 실패 시 ValueError."""
        txt = str(raw_date or "").strip()
        if not txt:
            return ""
        try:
            return datetime.strptime(txt[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            raise ValueError(f"INVALID_OUTBOUND_DATE: '{txt}' (허용 형식: YYYY-MM-DD)")

    def _save_allocation_fail_report(
        self,
        rows: list,
        errors: list,
        source_file: str = "",
        error_details: list | None = None,
    ) -> dict:
        """Allocation 검증 실패 리포트 CSV+JSON 저장."""
        out = {"csv": "", "json": ""}
        if not errors:
            return out
        try:
            reports_root = resolve_reports_dir()
            out_dir = os.path.join(reports_root, "allocation")
            os.makedirs(out_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.join(out_dir, f"allocation_fail_{ts}.csv")
            json_path = os.path.join(out_dir, f"allocation_fail_{ts}.json")

            detail_rows = list(error_details or [])
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["line_no", "FAIL_CODE", "lot_no", "sold_to", "qty_mt", "reason"])
                if detail_rows:
                    for d in detail_rows:
                        w.writerow([
                            d.get("line_no", ""),
                            d.get("fail_code", "ALLOCATION_VALIDATE_FAIL"),
                            d.get("lot_no", ""),
                            d.get("sold_to", ""),
                            d.get("qty_mt", ""),
                            d.get("reason", ""),
                        ])
                else:
                    for r in rows or []:
                        lot_no = str((r.get("lot_no", "") if isinstance(r, dict) else getattr(r, "lot_no", "")) or "")
                        sold_to = str((r.get("sold_to", "") if isinstance(r, dict) else getattr(r, "sold_to", "")) or "")
                        qty_mt = (r.get("qty_mt", "") if isinstance(r, dict) else getattr(r, "qty_mt", ""))
                        fail_reason = "; ".join(errors[:3])
                        fail_code = "ALLOCATION_VALIDATE_FAIL"
                        if "INVALID_OUTBOUND_DATE" in fail_reason:
                            fail_code = "INVALID_OUTBOUND_DATE"
                        w.writerow(["", fail_code, lot_no, sold_to, qty_mt, fail_reason])

            with open(json_path, "w", encoding="utf-8") as f:
                payload = {
                    "source_file": source_file,
                    "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "error_count": len(errors),
                    "errors": errors,
                    "error_details": detail_rows,
                }
                json.dump(payload, f, ensure_ascii=False, indent=2)

            out["csv"] = csv_path
            out["json"] = json_path
            return out
        except Exception as e:
            logger.debug(f"Allocation 실패 리포트 저장 스킵: {e}")
            return out

    def _assert_sample_policy(self, lot_no: str) -> None:
        """v5.3.7: Hard-stop if sample policy is violated (must be exactly 1 sample row per LOT)."""
        row = self.db.fetchone(
            "SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no = ? AND COALESCE(is_sample,0)=1",
            (lot_no,)
        )
        cnt = (row['cnt'] if isinstance(row, dict) else row[0]) if row else 0
        if cnt != 1:
            raise ValueError(f"샘플 정책 위반: LOT {lot_no}에 샘플 {cnt}개 (필수 정확히 1개)")

    def _get_allocation_random_mode(self) -> str:
        """
        Allocation 예약 랜덤 모드 조회.
        우선순위: ENV(SQM_ALLOC_RANDOM_MODE) > settings.ini[outbound].allocation_random_mode > 기본(random)

        Returns:
            'random' | 'seeded'
        """
        raw = str(os.environ.get("SQM_ALLOC_RANDOM_MODE", "") or "").strip().lower()
        if not raw:
            try:
                cfg = configparser.ConfigParser()
                cfg.read(os.path.join(os.getcwd(), "settings.ini"), encoding="utf-8")
                raw = str(cfg.get("outbound", "allocation_random_mode", fallback="")).strip().lower()
            except Exception as e:
                logger.debug(f"allocation_random_mode 설정 읽기 스킵: {e}")

        if raw in ("seeded", "deterministic", "reproducible", "sale_ref_seed", "seed"):
            return "seeded"
        return "random"

    def _get_allocation_strict_mode(self) -> bool:
        """
        Allocation 예약 Strict 모드 조회.
        우선순위: ENV(SQM_ALLOCATION_STRICT_MODE) > settings.ini[outbound].allocation_strict_mode > 기본(True)
        """
        raw = str(os.environ.get("SQM_ALLOCATION_STRICT_MODE", "") or "").strip().lower()
        if not raw:
            try:
                cfg = configparser.ConfigParser()
                cfg.read(os.path.join(os.getcwd(), "settings.ini"), encoding="utf-8")
                raw = str(cfg.get("outbound", "allocation_strict_mode", fallback="")).strip().lower()
            except Exception as e:
                logger.debug(f"allocation_strict_mode 설정 읽기 스킵: {e}")

        if not raw:
            return True
        return raw in ("1", "true", "yes", "on", "strict")

    def _get_allocation_reservation_mode(self, override_mode: str = "") -> str:
        """
        Allocation 예약 모드 조회.
        우선순위: 인자 override > ENV(SQM_ALLOCATION_RESERVATION_MODE)
               > settings.ini[outbound].allocation_reservation_mode > 기본(tonbag)

        Returns:
            'tonbag' | 'lot'
        """
        raw = str(override_mode or "").strip().lower()
        if not raw:
            raw = str(os.environ.get("SQM_ALLOCATION_RESERVATION_MODE", "") or "").strip().lower()
        if not raw:
            try:
                cfg = configparser.ConfigParser()
                cfg.read(os.path.join(os.getcwd(), "settings.ini"), encoding="utf-8")
                raw = str(cfg.get("outbound", "allocation_reservation_mode", fallback="")).strip().lower()
            except Exception as e:
                logger.debug(f"allocation_reservation_mode 설정 읽기 스킵: {e}")
        if raw in ("lot", "lot_only", "lot_mode"):
            return "lot"
        return "tonbag"

    def _has_allocation_source_fingerprint_column(self) -> bool:
        """allocation_plan.source_fingerprint 컬럼 존재 여부."""
        try:
            rows = self.db.fetchall("PRAGMA table_info(allocation_plan)")
            cols = {str(r.get("name", "")).strip().lower() for r in (rows or [])}
            return "source_fingerprint" in cols
        except Exception as e:
            logger.debug(f"source_fingerprint 컬럼 확인 스킵: {e}")
            return False

    def _compute_allocation_source_fingerprint(self, allocation_rows: list, source_file: str = "") -> str:
        """
        Allocation 입력 fingerprint 생성.
        - 파일: 파일 내용 SHA1 우선, 실패 시 파일 메타+경로로 대체
        - 붙여넣기: 행 데이터 정규화 문자열 SHA1
        """
        try:
            sf = str(source_file or "").strip()
            if sf and sf != "(붙여넣기)" and os.path.isfile(sf):
                try:
                    h = hashlib.sha1()
                    with open(sf, "rb") as f:
                        for chunk in iter(lambda: f.read(1024 * 1024), b""):
                            h.update(chunk)
                    return h.hexdigest()
                except Exception as e:
                    logger.debug(f"Allocation 파일 해시 계산 실패(메타 대체): {e}")
                try:
                    st = os.stat(sf)
                    base = f"path={os.path.abspath(sf)}|size={st.st_size}|mtime={int(st.st_mtime)}"
                    return hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()
                except Exception as e:
                    logger.debug(f"Allocation 파일 메타 해시 계산 실패: {e}")

            # 붙여넣기 또는 파일 접근 불가 시: 행 기반 fingerprint
            normalized_rows = []
            for alloc in (allocation_rows or []):
                lot_no = str(alloc.get("lot_no", "") if isinstance(alloc, dict) else getattr(alloc, "lot_no", "")).strip().upper()
                qty_mt = float((alloc.get("qty_mt", 0) if isinstance(alloc, dict) else getattr(alloc, "qty_mt", 0)) or 0)
                sold_to = str(alloc.get("sold_to", "") if isinstance(alloc, dict) else getattr(alloc, "sold_to", "")).strip().upper()
                customer = str(alloc.get("customer", "") if isinstance(alloc, dict) else getattr(alloc, "customer", "")).strip().upper()
                sale_ref = str(alloc.get("sale_ref", "") if isinstance(alloc, dict) else getattr(alloc, "sale_ref", "")).strip().upper()
                outbound_date = str(
                    alloc.get("outbound_date", "") if isinstance(alloc, dict) else getattr(alloc, "outbound_date", "")
                ).strip()[:10]
                normalized_rows.append(
                    f"{lot_no}|{qty_mt:.6f}|{sold_to}|{customer}|{sale_ref}|{outbound_date}"
                )
            normalized_rows.sort()
            base = "paste|" + "\n".join(normalized_rows)
            return hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()
        except Exception as e:
            logger.debug(f"Allocation fingerprint 계산 실패: {e}")
            return ""

    @staticmethod
    def _build_allocation_seed(
        lot_no: str,
        sale_ref: str,
        qty_mt: float,
        outbound_date,
        source_file: str,
    ) -> str:
        """
        같은 요청이면 같은 선택 결과가 나오도록 고정 시드 문자열 생성.
        sale_ref 우선, 없으면 요청 필드 조합으로 생성.
        """
        sale_ref_norm = str(sale_ref or "").strip().upper()
        date_norm = str(outbound_date or "").strip()[:10]
        source_norm = str(source_file or "").strip()
        base = (
            f"sale_ref={sale_ref_norm}|lot={str(lot_no or '').strip().upper()}|"
            f"qty_mt={float(qty_mt or 0):.6f}|date={date_norm}|src={source_norm}"
        )
        return hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()

    """출고 처리 Mixin (v3.6.6: SQMDatabase API 기반)"""
    
    def process_outbound(self, allocation_data, source: str = 'AUTO', stop_at_picked: bool = False) -> Dict:
        """
        출고 처리 (v3.8.4: All-or-Nothing + 톤백 동기화, v5.9.92: source/stop_at_picked)
        
        source: 출고 경로 구분 (AUTO/QUICK/EXCEL 등). allocation_plan에 기록.
        stop_at_picked: True면 톤백 PICKED까지만 하고 재고·outbound 미반영(빠른 출고용).
        """
        result = {
            'success': False,
            'message': '',
            'processed': 0,
            'lots_processed': 0,
            'total_weight_kg': 0,
            'total_picked': 0,
            'errors': [],
            'warnings': [],
        }
        
        try:
            if isinstance(allocation_data, dict):
                allocations = [allocation_data]
            else:
                allocations = list(allocation_data)
            
            if not allocations:
                result['message'] = "처리할 데이터 없음"
                return result
            
            # ★ All-or-Nothing: 전체를 하나의 트랜잭션으로
            with self.db.transaction("IMMEDIATE"):
                processed_lots = []
                for alloc in allocations:
                    processed = self._process_single_outbound(alloc, source=source, stop_at_picked=stop_at_picked)
                    if processed:
                        result['processed'] += 1
                        result['total_weight_kg'] += processed.get('weight_kg', 0)
                        result['total_picked'] += processed.get('weight_kg', 0) / 1000.0
                        processed_lots.append(processed.get('lot_no'))
                
                # v5.1.4: 트랜잭션 안에서 정합성 검증
                if hasattr(self, 'verify_lot_integrity') and processed_lots:
                    for lot_no in set(processed_lots):
                        integrity = self.verify_lot_integrity(lot_no)
                        if not integrity.get('valid', True):
                            raise ValueError(
                                f"출고 후 정합성 실패 ({lot_no}): {integrity.get('errors', [])}"
                            )
            
            result['lots_processed'] = result['processed']
            
            if result['processed'] > 0:
                result['success'] = True
                result['message'] = f"출고 완료: {result['processed']}건"
            else:
                result['message'] = "처리된 출고 없음"
            
            self._log_operation("출고", {
                'processed': result['processed'],
                'weight_kg': result['total_weight_kg']
            })
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"출고 처리 오류 (전체 롤백): {e}", exc_info=True)
            result['errors'].append(str(e))
        
        return result
    
    def _process_single_outbound(
        self, alloc: Dict, source: str = 'AUTO', stop_at_picked: bool = False
    ) -> Optional[Dict]:
        """
        단일 출고 처리 (v3.8.4: inventory + tonbag 동기화, v5.9.92: source, stop_at_picked)
        
        stop_at_picked=True면 톤백 PICKED + allocation_plan 기록만 하고 재고/outbound 미반영.
        """
        lot_no = str(alloc.get('lot_no') or '').strip()
        weight_kg = self._safe_parse_float(alloc.get('weight_kg'))
        if weight_kg <= 0:
            qty_mt = self._safe_parse_float(alloc.get('qty_mt'))
            weight_kg = qty_mt * 1000.0
        
        customer = alloc.get('customer') or alloc.get('sold_to', '')
        sale_ref = alloc.get('sale_ref', '')
        
        if not lot_no or weight_kg <= 0:
            return None
        
        lot = self.db.fetchone(
            "SELECT current_weight, picked_weight FROM inventory WHERE lot_no = ?",
            (lot_no,)
        )
        if not lot:
            raise ValueError(f"LOT 없음: {lot_no}")
        
        available = lot['current_weight'] or 0
        if available < weight_kg - 0.01:
            raise ValueError(
                f"가용 재고 부족: {lot_no} (가용: {available:.0f}kg, 요청: {weight_kg:.0f}kg)"
            )
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        qty_mt_val = weight_kg / 1000.0
        
        # ★ 1단계: 톤백 PICKED 처리 (가용 톤백에서 필요 수량만큼, 샘플 제외)
        remaining_kg = weight_kg
        tonbags = self.db.fetchall(
            """SELECT id, sub_lt, weight FROM inventory_tonbag 
               WHERE lot_no = ? AND status = ?
                 AND COALESCE(is_sample, 0) = 0
               ORDER BY sub_lt DESC""",
            (lot_no, STATUS_AVAILABLE)
        )
        picked_count = 0
        first_tonbag_id = None
        if tonbags:
            for tb in tonbags:
                if remaining_kg <= 0.01:
                    break
                tb_weight = tb['weight'] or 0
                if tb_weight <= 0:
                    continue
                if first_tonbag_id is None:
                    first_tonbag_id = tb['id']
                self.db.execute(
                    """UPDATE inventory_tonbag SET
                        status = ?,
                        picked_to = ?,
                        picked_date = ?,
                        sale_ref = ?,
                        outbound_date = ?,
                        updated_at = ?
                    WHERE id = ?""",
                    (STATUS_PICKED, customer, now, sale_ref, now, now, tb['id'])
                )
                remaining_kg -= tb_weight
                picked_count += 1
        
        # v5.9.92: allocation_plan에 출고 기록 (source 저장)
        try:
            self.db.execute(
                """INSERT INTO allocation_plan 
                (lot_no, tonbag_id, customer, sale_ref, qty_mt, outbound_date, status, source, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, 'PICKED', ?, ?)""",
                (lot_no, first_tonbag_id, customer, sale_ref, qty_mt_val, now, source, now)
            )
        except (sqlite3.OperationalError, OSError) as e:
            if "allocation_plan" in str(e) and "source" in str(e).lower():
                logger.debug("allocation_plan.source 미존재 시 무시: %s", e)
            else:
                raise
        
        if stop_at_picked:
            # ★ S4-1 FIX (S3-BUG-1): inventory 무게 갱신 추가
            # 이전: 톤백만 PICKED 변경, inventory 무게 미갱신 → 정합성 실패 → 롤백
            # 수정: current_weight↓ + picked_weight↑ → 정합성 유지
            self._update_lot_after_pick(lot_no, weight_kg)
            self._recalc_lot_status(lot_no)
            # PICK 이력 기록 (OUTBOUND와 구분)
            self.db.execute(
                """INSERT INTO stock_movement 
                (lot_no, movement_type, qty_kg, remarks, created_at)
                VALUES (?, 'PICK', ?, ?, ?)""" ,
                (lot_no, weight_kg, f"customer={customer},source={source}", now)
            )
            return {'lot_no': lot_no, 'weight_kg': weight_kg, 'tonbags_picked': picked_count}
        
        # ★ 2단계: inventory 업데이트
        new_weight = available - weight_kg
        if new_weight < 0:
            new_weight = 0
        new_status = STATUS_DEPLETED if new_weight <= 0 else STATUS_AVAILABLE
        self.db.execute(
            """UPDATE inventory SET
                current_weight = ?,
                picked_weight = picked_weight + ?,
                status = ?,
                sold_to = CASE WHEN ? != '' THEN ? ELSE sold_to END,
                updated_at = ?
            WHERE lot_no = ?""",
            (new_weight, weight_kg, new_status, customer, customer, now, lot_no)
        )
        self._recalc_lot_status(lot_no)
        
        # ★ 3단계: stock_movement 이력
        self.db.execute(
            """INSERT INTO stock_movement 
            (lot_no, movement_type, qty_kg, remarks, created_at)
            VALUES (?, 'OUTBOUND', ?, ?, ?)""",
            (lot_no, weight_kg, f"customer={customer}" if customer else '', now)
        )
        
        # ★ 4단계: outbound 테이블 기록
        self.db.execute(
            """INSERT INTO outbound 
            (customer, total_qty_mt, outbound_date, created_at)
            VALUES (?, ?, ?, ?)""",
            (customer, weight_kg, now, now)
        )
        
        return {'lot_no': lot_no, 'weight_kg': weight_kg, 'tonbags_picked': picked_count}
    
    def _update_lot_after_pick(self, lot_no: str, weight_kg: float) -> None:
        """피킹 후 LOT 업데이트"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.db.execute(
            """UPDATE inventory SET
                current_weight = MAX(0, current_weight - ?),
                picked_weight = picked_weight + ?,
                status = CASE 
                    WHEN current_weight - ? <= 0 THEN ?
                    ELSE status
                END,
                updated_at = ?
            WHERE lot_no = ?""",
            (weight_kg, weight_kg, weight_kg, STATUS_DEPLETED, now, lot_no)
        )
    

    # NOTE: process_outbound_safe, preflight_check_outbound
    #   → PreflightMixin으로 이관 완료 (v3.8.4 데드코드 정리)

    def cancel_outbound_tonbag(self, lot_no: str, sub_lt: int) -> Dict:
        """
        출고 취소: 톤백 PICKED → AVAILABLE + inventory.current_weight 복구
        
        All-or-Nothing: 톤백 + inventory 모두 성공해야 commit
        """
        from datetime import datetime
        result = {'success': False, 'message': '', 'errors': []}
        
        try:
            with self.db.transaction("IMMEDIATE"):
                # 톤백 정보 조회
                tonbag = self.db.fetchone("""
                    SELECT id, weight, status, picked_to 
                    FROM inventory_tonbag 
                    WHERE lot_no = ? AND sub_lt = ?
                """, (lot_no, sub_lt))
                
                if not tonbag:
                    result['errors'].append(f"톤백 없음: {lot_no}-{sub_lt}")
                    return result
                
                if tonbag['status'] != STATUS_PICKED:
                    result['errors'].append(f"PICKED 상태가 아님: {lot_no}-{sub_lt} ({tonbag['status']})")
                    return result
                
                weight = tonbag['weight'] or 0
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 1. 톤백: PICKED → AVAILABLE
                self.db.execute("""
                    UPDATE inventory_tonbag SET
                        status = ?,
                        picked_to = NULL,
                        picked_date = NULL,
                        pick_ref = NULL,
                        outbound_date = NULL,
                        updated_at = ?
                    WHERE lot_no = ? AND sub_lt = ?
                """, (STATUS_AVAILABLE, now, lot_no, sub_lt))
                
                # 2. inventory: current_weight 복구
                self.db.execute("""
                    UPDATE inventory SET
                        current_weight = current_weight + ?,
                        picked_weight = MAX(0, picked_weight - ?),
                        updated_at = ?
                    WHERE lot_no = ?
                """, (weight, weight, now, lot_no))
                
                # 3. inventory status 재계산
                self._recalc_lot_status(lot_no)
                
                # 4. stock_movement 이력 (B3 FIX: 필수 기록)
                self.db.execute("""
                    INSERT INTO stock_movement 
                    (lot_no, movement_type, qty_kg, remarks, created_at)
                    VALUES (?, 'CANCEL_OUTBOUND', ?, ?, ?)
                """, (lot_no, weight, f"customer={tonbag['picked_to'] or ''}", now))
                
                result['success'] = True
                result['message'] = f"출고 취소 완료: {lot_no}-{sub_lt} ({weight:.0f}kg)"
                logger.info(result['message'])
            
            # v3.8.5: 취소 후 자동 정합성 검증
            if result['success'] and hasattr(self, '_assert_lot_integrity'):
                self._assert_lot_integrity(lot_no)
                
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            result['errors'].append(str(e))
            logger.error(f"출고 취소 오류: {e}")
        
        return result

    def cancel_outbound_bulk(self, items: list) -> Dict:
        """
        일괄 출고 취소 (All-or-Nothing)
        items: [{'lot_no': '...', 'sub_lt': 1}, ...]
        """
        from datetime import datetime
        result = {'success': False, 'cancelled': 0, 'errors': []}
        
        try:
            with self.db.transaction("IMMEDIATE"):
                touched_lots = set()
                for item in items:
                    lot_no = str(item.get('lot_no') or '').strip()
                    sub_lt = item.get('sub_lt')
                    
                    tonbag = self.db.fetchone("""
                        SELECT weight, status, picked_to 
                        FROM inventory_tonbag 
                        WHERE lot_no = ? AND sub_lt = ? AND status = ?
                    """, (lot_no, sub_lt, STATUS_PICKED))
                    
                    if not tonbag:
                        raise ValueError(f"취소 불가: {lot_no}-{sub_lt}")
                    
                    weight = tonbag['weight'] or 0
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    self.db.execute("""
                        UPDATE inventory_tonbag SET
                            status = ?, picked_to = NULL, picked_date = NULL,
                            pick_ref = NULL, outbound_date = NULL, updated_at = ?
                        WHERE lot_no = ? AND sub_lt = ?
                    """, (STATUS_AVAILABLE, now, lot_no, sub_lt))
                    
                    self.db.execute("""
                        UPDATE inventory SET
                            current_weight = current_weight + ?,
                            picked_weight = MAX(0, picked_weight - ?),
                            updated_at = ?
                        WHERE lot_no = ?
                    """, (weight, weight, now, lot_no))
                    
                    # stock_movement 이력 기록 (v3.8.4 bugfix)
                    self.db.execute("""
                        INSERT INTO stock_movement 
                        (lot_no, movement_type, qty_kg, remarks, created_at)
                        VALUES (?, 'CANCEL_OUTBOUND', ?, ?, ?)
                    """, (lot_no, weight, f"bulk_cancel customer={tonbag['picked_to'] or ''}", now))
                    
                    result['cancelled'] += 1
                    if lot_no:
                        touched_lots.add(lot_no)
                
                # 모든 관련 LOT status 재계산
                for lot_no in touched_lots:
                    self._recalc_lot_status(lot_no)
                
                result['success'] = True
                result['message'] = f"일괄 취소 완료: {result['cancelled']}건"
                
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            result['errors'].append(str(e))
            logger.error(f"일괄 출고 취소 오류: {e}")
        
        return result

    def _recalc_lot_status(self, lot_no: str) -> None:
        """LOT status 재계산 (current_weight 기반)"""
        lot = self.db.fetchone(
            "SELECT current_weight, initial_weight FROM inventory WHERE lot_no = ?",
            (lot_no,)
        )
        if not lot:
            return
        # 톤백 상태 우선(판매배정/판매화물 결정/출고 등) → 없으면 잔량 기반
        try:
            status_rows = self.db.fetchall(
                "SELECT status, COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no = ? GROUP BY status",
                (lot_no,)
            )
            status_set = {str(r.get('status', '')).strip().upper() for r in (status_rows or [])}
        except (sqlite3.Error, ValueError, TypeError):
            status_set = set()

        if 'SOLD' in status_set:
            new_status = STATUS_SOLD
        elif 'SHIPPED' in status_set:
            new_status = 'SHIPPED'
        elif 'PICKED' in status_set:
            new_status = STATUS_PICKED
        elif 'RESERVED' in status_set:
            new_status = STATUS_RESERVED
        else:
            cw = lot['current_weight'] or 0
            iw = lot['initial_weight'] or 0
            if cw <= 0:
                new_status = STATUS_DEPLETED
            elif cw >= iw:
                new_status = STATUS_AVAILABLE
            else:
                new_status = STATUS_AVAILABLE

        self.db.execute(
            "UPDATE inventory SET status = ? WHERE lot_no = ?",
            (new_status, lot_no)
        )

    # ═══════════════════════════════════════════════════════
    # v5.9.3: Allocation 기반 예약/실행/확정
    # ═══════════════════════════════════════════════════════

    def _allocation_risk_flags(self, qty_kg: float, available_kg: float) -> list[str]:
        flags = []
        if qty_kg >= self.ALLOCATION_APPROVAL_QTY_KG_THRESHOLD:
            flags.append("LARGE_VOLUME")
        if available_kg > 0 and qty_kg >= available_kg * self.ALLOCATION_APPROVAL_RATIO_THRESHOLD:
            flags.append("OVER_50PCT")
        return flags

    def _allocation_requires_approval(self, qty_kg: float, available_kg: float) -> bool:
        return len(self._allocation_risk_flags(qty_kg, available_kg)) > 0

    def reserve_from_allocation(self, allocation_rows: list, source_file: str = '', reservation_mode: str = '') -> Dict:
        """
        Allocation 엑셀에서 파싱된 데이터로 톤백 예약 (AVAILABLE → RESERVED).
        allocation_plan 테이블에 계획 기록 + 톤백 상태 변경.

        Args:
            allocation_rows: AllocationRow 또는 dict 리스트
            source_file: 원본 파일명

        Returns:
            {'success': bool, 'reserved': int, 'errors': [], 'plan_ids': []}
        """
        result = {
            'success': False,
            'reserved': 0,
            'pending_approval': 0,
            'errors': [],
            'error_details': [],
            'plan_ids': [],
            'requested_rows': len(allocation_rows),
            'reservation_mode': 'tonbag',
        }

        def _alloc_val(alloc, key, default=None):
            """AllocationRow(dataclass) 또는 dict 모두 지원"""
            if isinstance(alloc, dict):
                return alloc.get(key, default)
            return getattr(alloc, key, default)

        # [RUBI-PHASE2] 랜덤출고 정책:
        # Allocation 업로드 단계에서는 TONBAG를 특정/예약하지 않습니다.
        # (tonbag_id는 NULL 유지) → 승인 후에도 실제 TONBAG 확정은 UID 스캔 순간에만 발생합니다.
        try:
            cols = set()
            _rows = self.db.fetchall("PRAGMA table_info(allocation_plan)") or []
            cols = {str(r.get("name", "")).strip().lower() for r in _rows}
        except Exception:
            cols = set()

        has_workflow = "workflow_status" in cols
        has_risk_flags = "risk_flags" in cols
        has_source_fp = "source_fingerprint" in cols
        has_source = "source" in cols
        has_import_batch_id = "import_batch_id" in cols
        has_line_no = "line_no" in cols

        # 안전한 insert SQL 구성 (존재하는 컬럼만 사용)
        base_cols = ["lot_no", "tonbag_id", "sub_lt", "customer", "sale_ref", "qty_mt", "outbound_date", "status", "source_file", "created_at"]
        if has_source:
            base_cols.insert(base_cols.index("status")+1, "source")
        if has_source_fp:
            base_cols.append("source_fingerprint")
        if has_workflow:
            base_cols.append("workflow_status")
        if has_risk_flags:
            base_cols.append("risk_flags")
        if has_import_batch_id:
            base_cols.append("import_batch_id")
        if has_line_no:
            base_cols.append("line_no")

        ph = ", ".join(["?"] * len(base_cols))
        sql = f"INSERT INTO allocation_plan ({', '.join(base_cols)}) VALUES ({ph})"

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        source_fingerprint = self._compute_allocation_source_fingerprint(allocation_rows, source_file)

        staged = 0
        with self.db.transaction("IMMEDIATE"):
            for idx, alloc in enumerate(allocation_rows or [], start=1):
                lot_no = str(_alloc_val(alloc, "lot_no", "") or "").strip()
                if not lot_no:
                    continue
                customer = str(_alloc_val(alloc, "customer", "") or "").strip()
                sale_ref = str(_alloc_val(alloc, "sale_ref", "") or "").strip()
                qty_mt = float(_alloc_val(alloc, "qty_mt", 0) or 0)
                outbound_date = str(_alloc_val(alloc, "outbound_date", "") or "").strip() or None

                status_val = "STAGED" if has_workflow else "RESERVED"
                row = [
                    lot_no, None, None, customer, sale_ref, qty_mt, outbound_date, status_val,
                    os.path.basename(source_file or ""), now
                ]
                if has_source:
                    row.insert(base_cols.index("source"), "ALLOCATION")
                if has_source_fp:
                    row.append(source_fingerprint)
                if has_workflow:
                    row.append("PENDING_APPROVAL")
                if has_risk_flags:
                    row.append("")
                if has_import_batch_id:
                    row.append(None)
                if has_line_no:
                    row.append(idx)

                self.db.execute(sql, tuple(row))
                staged += 1

        result["success"] = staged > 0
        result["reserved"] = 0
        result["pending_approval"] = staged if has_workflow else 0
        result["plan_ids"] = []
        result["reservation_mode"] = "lot"
        if staged == 0 and not result["errors"]:
            result["errors"].append("유효한 Allocation 행이 없습니다.")
        return result
        strict_mode = self._get_allocation_strict_mode()
        allocation_random_mode = self._get_allocation_random_mode()
        effective_mode = self._get_allocation_reservation_mode(reservation_mode)
        result['reservation_mode'] = effective_mode
        has_alloc_batch_table = self._table_exists("allocation_import_batch")
        has_source_fp_col = self._has_allocation_source_fingerprint_column()
        source_fingerprint = self._compute_allocation_source_fingerprint(allocation_rows, source_file)
        alloc_plan_cols = set()
        try:
            rows = self.db.fetchall("PRAGMA table_info(allocation_plan)")
            alloc_plan_cols = {str(r.get("name", "")).strip().lower() for r in (rows or [])}
        except Exception as e:
            logger.debug(f"allocation_plan 컬럼 조회 스킵: {e}")
        has_source_col = "source" in alloc_plan_cols
        has_import_batch_id_col = "import_batch_id" in alloc_plan_cols
        has_line_no_col = "line_no" in alloc_plan_cols
        has_gate_status_col = "gate_status" in alloc_plan_cols
        has_fail_code_col = "fail_code" in alloc_plan_cols
        has_fail_reason_col = "fail_reason" in alloc_plan_cols
        has_validated_at_col = "validated_at" in alloc_plan_cols
        has_workflow_status_col = "workflow_status" in alloc_plan_cols
        has_risk_flags_col = "risk_flags" in alloc_plan_cols
        has_approved_by_col = "approved_by" in alloc_plan_cols
        has_approved_at_col = "approved_at" in alloc_plan_cols
        has_rejected_reason_col = "rejected_reason" in alloc_plan_cols
        has_export_type_col = "export_type" in alloc_plan_cols   # v6.3.3 RUBI

        def _build_error_detail(line_no: int, fail_code: str, reason: str, lot_no: str, sold_to: str, qty_mt):
            result['error_details'].append(
                {
                    "line_no": line_no,
                    "fail_code": fail_code,
                    "reason": reason,
                    "lot_no": lot_no,
                    "sold_to": sold_to,
                    "qty_mt": qty_mt,
                }
            )

        def _insert_allocation_plan_row(payload: dict):
            cols = []
            vals = []
            for k, v in payload.items():
                if k in alloc_plan_cols:
                    cols.append(k)
                    vals.append(v)
            if not cols:
                raise ValueError("allocation_plan insert 컬럼 없음")
            placeholders = ", ".join(["?"] * len(cols))
            sql = f"INSERT INTO allocation_plan ({', '.join(cols)}) VALUES ({placeholders})"
            self.db.execute(sql, tuple(vals))
            row = self.db.fetchone("SELECT last_insert_rowid() AS rid")
            rid = int(row.get("rid", 0) if isinstance(row, dict) else (row[0] if row else 0))
            if rid:
                result["plan_ids"].append(rid)
            return rid

        # 중복 Allocation 감지 (fingerprint 우선, 없으면 basename 폴백)
        if source_fingerprint:
            try:
                if has_source_fp_col:
                    dup = self.db.fetchone(
                        """SELECT COUNT(*) AS cnt FROM allocation_plan
                           WHERE status = 'RESERVED' AND source_fingerprint = ?""",
                        (source_fingerprint,)
                    )
                    fname = os.path.basename(source_file) if source_file and source_file != '(붙여넣기)' else '(붙여넣기)'
                else:
                    fname = os.path.basename(source_file) if source_file and source_file != '(붙여넣기)' else '(붙여넣기)'
                    dup = self.db.fetchone(
                        """SELECT COUNT(*) AS cnt FROM allocation_plan
                           WHERE status = 'RESERVED' AND source_file LIKE ?""",
                        (f"%{fname}",)
                    )
                dup_cnt = dup.get('cnt', 0) if isinstance(dup, dict) else (dup[0] if dup else 0)
                if dup_cnt > 0:
                    result['duplicate_file'] = True
                    result['duplicate_count'] = int(dup_cnt)
                    result['duplicate_file_name'] = fname
                    result['duplicate_source_fingerprint'] = source_fingerprint
            except Exception as e:
                logger.debug(f"중복 Allocation 파일 감지 실패: {e}")

        import_batch_id = None
        if has_alloc_batch_table:
            try:
                now_batch = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.db.execute(
                    """INSERT INTO allocation_import_batch
                       (source_file, total_lines, passed_lines, failed_lines, imported_at)
                       VALUES (?, ?, 0, 0, ?)""",
                    (source_file or '(붙여넣기)', len(allocation_rows or []), now_batch)
                )
                row = self.db.fetchone("SELECT last_insert_rowid() AS rid")
                import_batch_id = int(row.get("rid", 0) if isinstance(row, dict) else (row[0] if row else 0))
                result["import_batch_id"] = import_batch_id
                try:
                    self.db.commit()
                except Exception as e:
                    logger.warning(f"[출고] 커밋 실패 (데이터 손실 위험): {e}")
            except Exception as e:
                logger.debug(f"allocation_import_batch 생성 스킵: {e}")

        try:
            with self.db.transaction("IMMEDIATE"):
                strict_errors = []
                plan_line_counter = 0

                for line_no, alloc in enumerate(allocation_rows, start=1):
                    lot_no = (normalize_lot(_alloc_val(alloc, 'lot_no')) or '').strip()
                    customer = str(_alloc_val(alloc, 'sold_to') or _alloc_val(alloc, 'customer') or '').strip()
                    sale_ref = str(_alloc_val(alloc, 'sale_ref') or '').strip()
                    qty_mt = float(_alloc_val(alloc, 'qty_mt') or 0)
                    outbound_date = _alloc_val(alloc, 'outbound_date')
                    sublot_count = int(_alloc_val(alloc, 'sublot_count') or _alloc_val(alloc, 'tonbag_count') or 0)
                    is_sample_req = bool(_alloc_val(alloc, 'is_sample', False))
                    if not is_sample_req and qty_mt > 0:
                        # allocation_dialog 기준: 10kg(0.01MT) 이하는 샘플 행
                        is_sample_req = qty_mt <= 0.01 + 1e-9
                    # v6.3.3 RUBI: export_type ('반송', '일반수출' 등)
                    export_type_val = str(_alloc_val(alloc, 'export_type') or '').strip()

                    if not lot_no:
                        msg = "LOT 번호 누락"
                        result['errors'].append(msg)
                        strict_errors.append(msg)
                        _build_error_detail(line_no, "INVALID_LOT", msg, lot_no, customer, qty_mt)
                        continue

                    # v6.12 Addon-G: DB에서 실제 톤백 단가 조회 (500/1000kg 동적 대응)
                    from engine_modules.constants import get_tonbag_unit_weight
                    _unit_w = get_tonbag_unit_weight(self.db, lot_no)
                    weight_kg = qty_mt * 1000 if qty_mt > 0 else sublot_count * _unit_w

                    if is_sample_req:
                        tonbags = self.db.fetchall(
                            """SELECT id, sub_lt, weight FROM inventory_tonbag
                               WHERE lot_no = ? AND status = ?
                                 AND COALESCE(is_sample, 0) = 1""",
                            (lot_no, STATUS_AVAILABLE)
                        )
                    else:
                        tonbags = self.db.fetchall(
                            """SELECT id, sub_lt, weight FROM inventory_tonbag
                               WHERE lot_no = ? AND status = ?
                                 AND COALESCE(is_sample, 0) = 0""",
                            (lot_no, STATUS_AVAILABLE)
                        )

                    if not tonbags:
                        # 원인 구분: DB에 LOT 없음 vs 톤백이 이미 예약/출고됨
                        exists = self.db.fetchone(
                            "SELECT 1 FROM inventory_tonbag WHERE lot_no = ? LIMIT 1",
                            (lot_no,)
                        )
                        if not exists:
                            msg = f"가용 톤백 없음: {lot_no} (LOT 미등록 → 입고 먼저 반영)"
                            result['errors'].append(msg)
                            strict_errors.append(msg)
                            _build_error_detail(line_no, "LOT_NOT_IN_DB", msg, lot_no, customer, qty_mt)
                        else:
                            status_rows = self.db.fetchall(
                                "SELECT status, COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no = ? GROUP BY status",
                                (lot_no,)
                            )
                            status_summary = ", ".join(
                                f"{r.get('status', 'UNKNOWN')}={r.get('cnt', 0)}" for r in (status_rows or [])
                            ) or "상태 집계 없음"
                            avail_row = self.db.fetchone(
                                "SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no = ? AND status = ?",
                                (lot_no, STATUS_AVAILABLE)
                            )
                            avail_sample_row = self.db.fetchone(
                                "SELECT COUNT(*) AS cnt FROM inventory_tonbag "
                                "WHERE lot_no = ? AND status = ? AND COALESCE(is_sample, 0) = 1",
                                (lot_no, STATUS_AVAILABLE)
                            )
                            avail_normal_row = self.db.fetchone(
                                "SELECT COUNT(*) AS cnt FROM inventory_tonbag "
                                "WHERE lot_no = ? AND status = ? AND COALESCE(is_sample, 0) = 0",
                                (lot_no, STATUS_AVAILABLE)
                            )
                            avail_cnt = (avail_row.get('cnt') if isinstance(avail_row, dict) else avail_row[0]) if avail_row else 0
                            avail_sample_cnt = (avail_sample_row.get('cnt') if isinstance(avail_sample_row, dict) else avail_sample_row[0]) if avail_sample_row else 0
                            avail_normal_cnt = (avail_normal_row.get('cnt') if isinstance(avail_normal_row, dict) else avail_normal_row[0]) if avail_normal_row else 0
                            if avail_cnt > 0:
                                req_type = "샘플(1kg)" if is_sample_req else "일반(비샘플)"
                                extra_reason = (
                                    f"판매가능 톤백 {avail_cnt}개 "
                                    f"(일반 {avail_normal_cnt}개 / 샘플 {avail_sample_cnt}개, 요청유형={req_type})"
                                )
                            else:
                                extra_reason = "판매가능 톤백 0개"
                            msg = (
                                f"가용 톤백 없음: {lot_no} (중복 배정 | {extra_reason} | 상태: {status_summary} | 조치: [예약 취소] 후 재시도)"
                            )
                            result['errors'].append(msg)
                            strict_errors.append(msg)
                            _build_error_detail(line_no, "NO_AVAILABLE_TONBAG", msg, lot_no, customer, qty_mt)
                        continue

                    if sublot_count > 0:
                        pick_count = sublot_count
                    else:
                        pick_count = 1 if is_sample_req else max(1, math.ceil(weight_kg / _unit_w))
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    try:
                        ob_date_str = self._normalize_outbound_date(outbound_date)
                    except ValueError as ve:
                        msg = str(ve)
                        result['errors'].append(msg)
                        strict_errors.append(msg)
                        _build_error_detail(line_no, "INVALID_OUTBOUND_DATE", msg, lot_no, customer, qty_mt)
                        continue

                    if len(tonbags) < pick_count:
                        msg = (
                            f"가용 부족: {lot_no} 요청 {pick_count}개 / 가용 {len(tonbags)}개"
                        )
                        result['errors'].append(msg)
                        strict_errors.append(msg)
                        _build_error_detail(line_no, "QTY_EXCEEDS_AVAILABLE", msg, lot_no, customer, qty_mt)
                        continue

                    reserved_in_lot = 0
                    reserved_kg = 0.0
                    seed_hash = ""
                    selected_sub_lts = []
                    available_kg = sum(float(tb.get('weight') or 0) for tb in tonbags)
                    need_approval = True or self._allocation_requires_approval(weight_kg, available_kg)
                    risk_flags = self._allocation_risk_flags(weight_kg, available_kg)

                    # 대량/위험 건은 STAGED + PENDING_APPROVAL로 적재하고 즉시 RESERVED는 하지 않음
                    if need_approval and has_workflow_status_col:
                        qty_mt_each = (qty_mt / pick_count) if pick_count > 0 else qty_mt
                        risk_txt = "|".join(risk_flags)
                        for _ in range(pick_count):
                            payload = {
                                "lot_no": lot_no,
                                "tonbag_id": None,
                                "sub_lt": None,
                                "customer": customer,
                                "sale_ref": sale_ref,
                                "qty_mt": qty_mt_each,
                                "outbound_date": ob_date_str,
                                "status": "STAGED",
                                "source_file": source_file,
                                "source_fingerprint": source_fingerprint if has_source_fp_col else "",
                                "created_at": now,
                            }
                            if has_source_col:
                                payload["source"] = "APPROVAL_QUEUE"
                            if has_import_batch_id_col and import_batch_id:
                                payload["import_batch_id"] = import_batch_id
                            if has_line_no_col:
                                plan_line_counter += 1
                                payload["line_no"] = plan_line_counter
                            if has_gate_status_col:
                                payload["gate_status"] = "PASS"
                            if has_fail_code_col:
                                payload["fail_code"] = ""
                            if has_fail_reason_col:
                                payload["fail_reason"] = ""
                            if has_validated_at_col:
                                payload["validated_at"] = now
                            if has_workflow_status_col:
                                payload["workflow_status"] = "PENDING_APPROVAL"
                            if has_risk_flags_col:
                                payload["risk_flags"] = risk_txt
                            if has_approved_by_col:
                                payload["approved_by"] = ""
                            if has_approved_at_col:
                                payload["approved_at"] = None
                            if has_rejected_reason_col:
                                payload["rejected_reason"] = ""
                            if has_export_type_col:                      # v6.3.3 RUBI
                                payload["export_type"] = export_type_val
                            _insert_allocation_plan_row(payload)
                            result['pending_approval'] += 1
                        logger.info(
                            f"[reserve-stage] {lot_no}: 승인대기 {pick_count}건 적재 "
                            f"(qty_kg={weight_kg:.0f}, avail_kg={available_kg:.0f}, risk={risk_flags})"
                        )
                        continue

                    if effective_mode == "lot":
                        # LOT 단위 예약: 톤백 상태는 바꾸지 않고 allocation_plan에 미지정(tonbag_id NULL) 계획만 기록.
                        qty_mt_each = (qty_mt / pick_count) if pick_count > 0 else qty_mt
                        for _ in range(pick_count):
                            payload = {
                                "lot_no": lot_no,
                                "tonbag_id": None,
                                "sub_lt": None,
                                "customer": customer,
                                "sale_ref": sale_ref,
                                "qty_mt": qty_mt_each,
                                "outbound_date": ob_date_str,
                                "status": "RESERVED",
                                "source_file": source_file,
                                "source_fingerprint": source_fingerprint if has_source_fp_col else "",
                                "created_at": now,
                            }
                            if has_source_col:
                                payload["source"] = "LOT"
                            if has_import_batch_id_col and import_batch_id:
                                payload["import_batch_id"] = import_batch_id
                            if has_line_no_col:
                                plan_line_counter += 1
                                payload["line_no"] = plan_line_counter
                            if has_gate_status_col:
                                payload["gate_status"] = "PASS"
                            if has_fail_code_col:
                                payload["fail_code"] = ""
                            if has_fail_reason_col:
                                payload["fail_reason"] = ""
                            if has_validated_at_col:
                                payload["validated_at"] = now
                            if has_export_type_col:                      # v6.3.3 RUBI
                                payload["export_type"] = export_type_val
                            _insert_allocation_plan_row(payload)
                            reserved_in_lot += 1
                        reserved_kg = sum(float(tb.get('weight') or 0) for tb in tonbags[:pick_count])
                    else:
                        # 톤백 단위 예약: 기존 동작 유지
                        pool = list(tonbags)
                        if allocation_random_mode == "seeded":
                            seed_hash = self._build_allocation_seed(
                                lot_no=lot_no,
                                sale_ref=sale_ref,
                                qty_mt=qty_mt,
                                outbound_date=ob_date_str,
                                source_file=source_file,
                            )
                            rng = random.Random(seed_hash)
                            rng.shuffle(pool)
                        else:
                            random.shuffle(pool)
                        selected = pool[:pick_count]
                        selected_sub_lts = [str(tb.get('sub_lt', '')) for tb in selected]

                        for tb in selected:
                            self.db.execute(
                                """UPDATE inventory_tonbag SET
                                    status = ?, picked_to = ?, sale_ref = ?, updated_at = ?
                                WHERE id = ?""",
                                (STATUS_RESERVED, customer, sale_ref, now, tb['id'])
                            )
                            payload = {
                                "lot_no": lot_no,
                                "tonbag_id": tb["id"],
                                "sub_lt": tb["sub_lt"],
                                "customer": customer,
                                "sale_ref": sale_ref,
                                "qty_mt": qty_mt,
                                "outbound_date": ob_date_str,
                                "status": "RESERVED",
                                "source_file": source_file,
                                "source_fingerprint": source_fingerprint if has_source_fp_col else "",
                                "created_at": now,
                            }
                            if has_source_col:
                                payload["source"] = "TONBAG"
                            if has_import_batch_id_col and import_batch_id:
                                payload["import_batch_id"] = import_batch_id
                            if has_line_no_col:
                                plan_line_counter += 1
                                payload["line_no"] = plan_line_counter
                            if has_gate_status_col:
                                payload["gate_status"] = "PASS"
                            if has_fail_code_col:
                                payload["fail_code"] = ""
                            if has_fail_reason_col:
                                payload["fail_reason"] = ""
                            if has_validated_at_col:
                                payload["validated_at"] = now
                            if has_export_type_col:                      # v6.3.3 RUBI
                                payload["export_type"] = export_type_val
                            _insert_allocation_plan_row(payload)
                            reserved_in_lot += 1
                            reserved_kg += float(tb.get('weight') or 0)

                    result['reserved'] += reserved_in_lot
                    if reserved_in_lot > 0 and effective_mode != "lot":
                        self._recalc_lot_status(lot_no)
                    if reserved_in_lot > 0:
                        self.db.execute(
                            "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                            "VALUES (?, 'RESERVED', ?, ?, ?)",
                            (
                                lot_no,
                                reserved_kg,
                                f"allocation(mode:{effective_mode}, rand:{allocation_random_mode}), tonbags={reserved_in_lot}, "
                                f"sub_lt={','.join(selected_sub_lts) if selected_sub_lts else '-'}, "
                                f"customer={customer}, seed={seed_hash[:8] if seed_hash else '-'}",
                                now,
                            ),
                        )
                    logger.info(
                        f"[reserve-{effective_mode}] {lot_no}: {reserved_in_lot}개 RESERVED "
                        f"(rand={allocation_random_mode}, seed={seed_hash[:8] if seed_hash else '-'}, "
                        f"sample={is_sample_req}, sub_lt={selected_sub_lts}) -> {customer}"
                    )

                if strict_mode and strict_errors:
                    raise ValueError(
                        "[STRICT] Allocation 예약 중단: " + " | ".join(strict_errors[:10])
                    )

            result['success'] = (result['reserved'] > 0) or (result.get('pending_approval', 0) > 0)
            if result['success']:
                if effective_mode == "lot":
                    result['message'] = f"예약 완료(LOT 단위): {result['reserved']}개 계획"
                else:
                    result['message'] = f"예약 완료: {result['reserved']}개 톤백"
            if result.get('pending_approval', 0) > 0:
                staged_msg = f"승인대기 적재: {result.get('pending_approval', 0)}건"
                if result.get('message'):
                    result['message'] += f" / {staged_msg}"
                else:
                    result['message'] = staged_msg

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"Allocation 예약 오류 (전체 롤백): {e}", exc_info=True)
            result['reserved'] = 0
            result['errors'].append(str(e))

        # 모든 LOT이 이미 예약 상태인 경우 안내 메시지 추가
        if result['reserved'] == 0 and result['errors']:
            all_dup = all("중복 배정" in err or "이미 예약/출고됨" in err for err in result['errors'])
            if all_dup:
                result['errors'].append(
                    "⚠️ 모든 LOT이 이미 예약 상태입니다.\n"
                    "• 다시 예약: [예약 취소] 후 재시도\n"
                    "• 기존 예약 진행: [출고 실행]"
                )

        if has_alloc_batch_table and result.get("import_batch_id"):
            try:
                failed_lines = len(result.get("error_details", []))
                passed_lines = max(0, len(allocation_rows or []) - failed_lines)
                self.db.execute(
                    "UPDATE allocation_import_batch SET passed_lines=?, failed_lines=? WHERE id=?",
                    (passed_lines, failed_lines, result.get("import_batch_id"))
                )
                try:
                    self.db.commit()
                except Exception as e:
                    logger.warning(f"[출고] 커밋 실패 (데이터 손실 위험): {e}")
            except Exception as e:
                logger.debug(f"allocation_import_batch 집계 업데이트 스킵: {e}")

        if result.get("errors"):
            report_paths = self._save_allocation_fail_report(
                allocation_rows,
                result.get("errors", []),
                source_file=source_file,
                error_details=result.get("error_details", []),
            )
            if report_paths.get("csv") or report_paths.get("json"):
                result["fail_report"] = report_paths
                if has_alloc_batch_table and result.get("import_batch_id"):
                    try:
                        self.db.execute(
                            "UPDATE allocation_import_batch SET report_csv_path=?, report_json_path=? WHERE id=?",
                            (
                                report_paths.get("csv", ""),
                                report_paths.get("json", ""),
                                result.get("import_batch_id"),
                            ),
                        )
                        try:
                            self.db.commit()
                        except Exception as e:
                            logger.warning(f"[출고] 커밋 실패 (데이터 손실 위험): {e}")
                    except Exception as e:
                        logger.debug(f"allocation_import_batch 리포트 경로 업데이트 스킵: {e}")

        return result

    def apply_approved_allocation_reservations(self, limit: int = 0) -> Dict:
        """
        승인 완료(STAGED + APPROVED) 건을 실제 RESERVED로 반영.
        """
        result = {"success": False, "applied": 0, "errors": []}
        try:
            alloc_plan_cols = set()
            rows = self.db.fetchall("PRAGMA table_info(allocation_plan)")
            alloc_plan_cols = {str(r.get("name", "")).strip().lower() for r in (rows or [])}
            if "workflow_status" not in alloc_plan_cols:
                result["errors"].append("allocation_plan.workflow_status 컬럼이 없습니다.")
                return result
            has_risk_flags_col = "risk_flags" in alloc_plan_cols
            has_source_col = "source" in alloc_plan_cols
            has_approved_by_col = "approved_by" in alloc_plan_cols
            has_approved_at_col = "approved_at" in alloc_plan_cols

            q = (
                "SELECT id, lot_no, customer, sale_ref, qty_mt, outbound_date, COALESCE(risk_flags, '') AS risk_flags "
                "FROM allocation_plan "
                "WHERE status='STAGED' AND workflow_status='APPROVED' "
                "ORDER BY created_at ASC, id ASC"
            )
            if limit and int(limit) > 0:
                q += f" LIMIT {int(limit)}"
            staged_rows = self.db.fetchall(q) or []
            if not staged_rows:
                result["errors"].append("반영할 승인 완료(STAGED/APPROVED) 건이 없습니다.")
                return result

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            actor = os.environ.get("USERNAME", "") or os.environ.get("USER", "") or "system"
            with self.db.transaction("IMMEDIATE"):
                for r in staged_rows:
                    plan_id = int(r.get("id", 0))
                    lot_no = str(r.get("lot_no", "")).strip()
                    customer = str(r.get("customer", "")).strip()
                    sale_ref = str(r.get("sale_ref", "")).strip()
                    qty_mt = float(r.get("qty_mt", 0) or 0)
                    is_sample_req = qty_mt <= 0.01 + 1e-9
                    # [RUBI-PHASE2] 승인 완료 건은 TONBAG를 예약하지 않고 'LOT Target(대기)'로만 반영합니다.
                    # 실제 TONBAG 확정은 출고 스캔(UID) 순간에만 발생합니다.
                    # 최소 안전장치: LOT에 판매가능(AVAILABLE) 톤백이 1개도 없으면 승인 반영을 막습니다.
                    try:
                        cnt_row = self.db.fetchone(
                            "SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE lot_no=? AND status=?",
                            (lot_no, STATUS_AVAILABLE),
                        )
                        avail_cnt = int(cnt_row.get("cnt", 0) if isinstance(cnt_row, dict) else (cnt_row[0] if cnt_row else 0))
                    except Exception:
                        avail_cnt = 0
                    if avail_cnt <= 0:
                        result["errors"].append(f"미반영: {lot_no} 판매가능 톤백 없음 (plan_id={plan_id})")
                        continue

                    # allocation_plan만 상태 전환 (tonbag_id/sub_lt는 NULL 유지)
                    self.db.execute(
                        """UPDATE allocation_plan
                           SET status='RESERVED',
                               tonbag_id=NULL,
                               sub_lt=NULL,
                               workflow_status='APPLIED'
                           WHERE id=? AND status='STAGED' AND workflow_status='APPROVED'""",
                        (plan_id,),
                    )
                    result["applied"] += 1
                    try:
                        details = {
                            "plan_id": plan_id,
                            "workflow": "APPROVED_TO_RESERVED",
                            "risk_flags": r.get("risk_flags", "") if has_risk_flags_col else "",
                        }
                        self.db.execute(
                            """INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at, source, actor, details_json)
                               VALUES (?, 'RESERVED', ?, ?, ?, ?, ?, ?)""",
                            (
                                lot_no,
                                float(tb.get("weight") or 0),
                                f"approved allocation apply, customer={customer}",
                                now,
                                "APPROVAL_APPLY" if has_source_col else None,
                                actor if has_approved_by_col else None,
                                json.dumps(details, ensure_ascii=False) if has_approved_at_col else None,
                            ),
                        )
                    except Exception as e:
                        logger.debug(f"stock_movement 기록 스킵: {e}")
                    self._recalc_lot_status(lot_no)

            result["success"] = result["applied"] > 0
            if not result["success"] and not result["errors"]:
                result["errors"].append("반영된 건이 없습니다.")
            return result
        except (sqlite3.Error, ValueError, TypeError) as e:
            logger.error(f"승인분 예약 반영 오류: {e}", exc_info=True)
            result["errors"].append(str(e))
            return result

    def execute_reserved(self, lot_no: str = None, target_date: str = None) -> Dict:
        """
        RESERVED 톤백을 PICKED로 전환 (출고 실행).
        lot_no 지정 시 해당 LOT만, target_date 지정 시 해당 날짜 이하만 실행.

        Returns:
            {'success': bool, 'executed': int, 'errors': []}
        """
        result = {'success': False, 'executed': 0, 'errors': []}

        query = """SELECT ap.id, ap.lot_no, ap.tonbag_id, ap.sub_lt,
                          ap.customer, ap.sale_ref, ap.outbound_date
                   FROM allocation_plan ap
                   WHERE ap.status = 'RESERVED'
                     AND ap.tonbag_id IS NOT NULL"""
        params = []

        if lot_no:
            query += " AND ap.lot_no = ?"
            params.append(lot_no)
        if target_date:
            query += " AND ap.outbound_date <= ?"
            params.append(target_date)

        try:
            plans = self.db.fetchall(query, tuple(params))
            if not plans:
                lot_mode_cnt = 0
                try:
                    row = self.db.fetchone(
                        "SELECT COUNT(*) AS cnt FROM allocation_plan WHERE status='RESERVED' AND tonbag_id IS NULL"
                    )
                    lot_mode_cnt = int(row.get('cnt', 0) if isinstance(row, dict) else (row[0] if row else 0))
                except Exception:
                    lot_mode_cnt = 0
                if lot_mode_cnt > 0:
                    result['message'] = (
                        f"실행할 톤백 예약 건 없음 (LOT 단위 예약 {lot_mode_cnt}건 대기 중: 바코드 스캔으로 확정하세요)"
                    )
                else:
                    result['message'] = "실행할 예약 건 없음"
                return result

            with self.db.transaction("IMMEDIATE"):
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                processed_lots = set()

                for plan in plans:
                    p_lot = plan['lot_no']
                    tb_id = plan['tonbag_id']

                    tb = self.db.fetchone(
                        "SELECT weight, status, tonbag_uid FROM inventory_tonbag WHERE id = ?",
                        (tb_id,)
                    )
                    if not tb or tb['status'] != STATUS_RESERVED:
                        result['errors'].append(f"톤백 {tb_id} 상태 불일치")
                        continue

                    tb_weight = tb['weight'] or 0
                    tonbag_uid = (tb.get('tonbag_uid') or '').strip() or None

                    self.db.execute(
                        """UPDATE inventory_tonbag SET
                            status = ?, picked_date = ?, outbound_date = ?, updated_at = ?
                        WHERE id = ?""",
                        (STATUS_PICKED, now, plan['outbound_date'] or now, now, tb_id)
                    )

                    self.db.execute(
                        """UPDATE inventory SET
                            current_weight = MAX(0, current_weight - ?),
                            picked_weight = picked_weight + ?,
                            updated_at = ?
                        WHERE lot_no = ?""",
                        (tb_weight, tb_weight, now, p_lot)
                    )

                    self.db.execute(
                        """UPDATE allocation_plan SET status = 'EXECUTED', executed_at = ?
                        WHERE id = ?""",
                        (now, plan['id'])
                    )

                    self.db.execute(
                        """INSERT INTO stock_movement
                        (lot_no, movement_type, qty_kg, remarks, created_at)
                        VALUES (?, 'OUTBOUND', ?, ?, ?)""",
                        (p_lot, tb_weight,
                         f"customer={plan['customer']}, sale_ref={plan['sale_ref']}", now)
                    )

                    # v6.0: PICKED 이력 기록 (picking_table) — remark에 plan_id/sale_ref 추적
                    try:
                        self.db.execute(
                            """INSERT INTO picking_table
                            (lot_no, tonbag_id, sub_lt, tonbag_uid, customer, qty_kg, status, picking_date, created_by, remark)
                            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, 'system', ?)""",
                            (p_lot, tb_id, plan['sub_lt'], tonbag_uid,
                             plan.get('customer') or '', tb_weight, now,
                             f"plan_id={plan['id']}, sale_ref={plan.get('sale_ref', '')}")
                        )
                    except sqlite3.OperationalError as e:
                        if "no such table" not in str(e).lower():
                            logger.debug(f"[picking_table] 기록 스킵: {e}")

                    processed_lots.add(p_lot)
                    result['executed'] += 1

                for pl in processed_lots:
                    self._recalc_lot_status(pl)

            result['success'] = result['executed'] > 0
            result['message'] = f"출고 실행 완료: {result['executed']}건"

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"출고 실행 오류 (전체 롤백): {e}", exc_info=True)
            result['errors'].append(str(e))

        return result

    def confirm_outbound(self, lot_no: str = None) -> Dict:
        """
        PICKED → SOLD 확정.

        Returns:
            {'success': bool, 'confirmed': int}
        """
        result = {'success': False, 'confirmed': 0, 'errors': []}

        query = """SELECT id, lot_no, sub_lt, weight, tonbag_uid FROM inventory_tonbag
                   WHERE status = ?"""
        params = [STATUS_PICKED]
        if lot_no:
            query += " AND lot_no = ?"
            params.append(lot_no)

        try:
            tonbags = self.db.fetchall(query, tuple(params))
            if not tonbags:
                result['message'] = "확정할 톤백 없음"
                return result

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                touched_lots = set()
                for tb in tonbags:
                    tb_id = tb['id']
                    self.db.execute(
                        "UPDATE inventory_tonbag SET status = ?, outbound_date = ?, updated_at = ? WHERE id = ?",
                        (STATUS_SOLD, now, now, tb_id)
                    )
                    # v6.0: SOLD 이력 기록 (sold_table)
                    uid_val = (tb.get('tonbag_uid') or '').strip() or ''
                    if not uid_val:
                        uid_val = str(tb.get('sub_lt') or tb_id)
                    try:
                        pick_row = self.db.fetchone(
                            "SELECT id FROM picking_table WHERE tonbag_id = ? ORDER BY id DESC LIMIT 1",
                            (tb_id,)
                        )
                        picking_id = pick_row['id'] if pick_row else None
                    except sqlite3.OperationalError:
                        picking_id = None
                    try:
                        self.db.execute(
                            """INSERT INTO sold_table
                            (lot_no, tonbag_id, sub_lt, tonbag_uid, picking_id, sold_qty_kg, sold_date, status, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'SOLD', 'system')""",
                            (tb['lot_no'], tb_id, tb.get('sub_lt', 0), uid_val, picking_id,
                             tb.get('weight') or 0, now)
                        )
                    except sqlite3.OperationalError as e:
                        if "no such table" not in str(e).lower():
                            logger.debug(f"[sold_table] 기록 스킵: {e}")
                    # v6.12.1: stock_movement 'SOLD' 이력
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'SOLD', ?, ?, ?)",
                        (tb['lot_no'], tb.get('weight', 0),
                         f"confirm_outbound, sub_lt={tb.get('sub_lt', 0)}", now))
                    result['confirmed'] += 1
                    if tb.get('lot_no'):
                        touched_lots.add(tb['lot_no'])
                for lot in touched_lots:
                    self._recalc_lot_status(lot)

            result['success'] = result['confirmed'] > 0
            result['message'] = f"출고 확정: {result['confirmed']}건 SOLD"

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"출고 확정 오류: {e}")
            result['errors'].append(str(e))

        return result

    def gate1_verify_picking(
        self,
        picking_result,
        picking_no: str = '',
    ) -> dict:
        """
        Gate-1: 피킹리스트 LOT ↔ allocation_plan RESERVED LOT 교차검증.

        v6.12.1 강화:
        - LOT 존재 여부 대조 (기존)
        - 톤백 수/무게 대조 (신규): 피킹 요청 수량 vs RESERVED 수량
        - 결과 상세 리포트 생성
        """
        result = {
            'passed': False,
            'requires_approval': False,
            'fail_code': '',
            'picking_lots': set(),
            'reserved_lots': set(),
            'only_in_picking': set(),
            'only_in_reserved': set(),
            'matched_lots': set(),
            'qty_mismatches': [],       # v6.12.1: 수량 불일치 상세
            'lot_details': [],          # v6.12.1: LOT별 상세 비교
            'error_report': '',
        }
        try:
            # --- 피킹 LOT 추출 ---
            if hasattr(picking_result, 'tonbag'):
                picking_lots = {getattr(item, 'lot_no', str(item.get('lot_no', '')))
                                for item in picking_result.tonbag}
            elif isinstance(picking_result, dict) and 'items' in picking_result:
                picking_lots = {item['lot_no'] for item in picking_result['items']
                                if item.get('lot_no')}
            else:
                picking_lots = set()

            result['picking_lots'] = picking_lots
            if not picking_lots:
                result['error_report'] = 'Gate-1 실패: 피킹 LOT 없음'
                return result

            # --- 피킹 LOT별 요청 수량 집계 ---
            picking_qty = {}  # {lot_no: {'qty_kg': float, 'tonbag_count': int}}
            if hasattr(picking_result, 'tonbag'):
                for item in picking_result.tonbag:
                    lot = getattr(item, 'lot_no', '')
                    kg = getattr(item, 'qty_kg', 0) or getattr(item, 'weight_kg', 0) or 0
                    if lot:
                        if lot not in picking_qty:
                            picking_qty[lot] = {'qty_kg': 0, 'tonbag_count': 0}
                        picking_qty[lot]['qty_kg'] += float(kg)
                        picking_qty[lot]['tonbag_count'] += 1
            elif isinstance(picking_result, dict):
                for item in picking_result.get('items', []):
                    lot = item.get('lot_no', '')
                    kg = float(item.get('qty_kg', 0) or 0)
                    if lot:
                        if lot not in picking_qty:
                            picking_qty[lot] = {'qty_kg': 0, 'tonbag_count': 0}
                        picking_qty[lot]['qty_kg'] += kg
                        picking_qty[lot]['tonbag_count'] += 1

            # --- DB 대조 ---
            placeholders = ','.join('?' * len(picking_lots))
            rows = self.db.fetchall(
                f"""SELECT DISTINCT lot_no FROM allocation_plan
                    WHERE status = 'RESERVED' AND lot_no IN ({placeholders})""",
                tuple(picking_lots)
            )
            reserved_in_db = {r['lot_no'] for r in rows}
            all_reserved = self.db.fetchall(
                "SELECT DISTINCT lot_no FROM allocation_plan WHERE status = 'RESERVED'"
            )
            all_reserved_lots = {r['lot_no'] for r in all_reserved}
            result['reserved_lots'] = all_reserved_lots

            only_in_picking = picking_lots - reserved_in_db
            only_in_reserved = all_reserved_lots - picking_lots
            matched = picking_lots & reserved_in_db
            result['only_in_picking'] = only_in_picking
            result['only_in_reserved'] = only_in_reserved
            result['matched_lots'] = matched

            # --- v6.12.1: 수량 교차 검증 ---
            qty_mismatches = []
            lot_details = []
            for lot_no in sorted(matched):
                # DB에서 RESERVED 톤백 수/총 무게 조회
                db_row = self.db.fetchone(
                    """SELECT COUNT(*) AS tb_count,
                              COALESCE(SUM(t.weight), 0) AS total_kg
                       FROM allocation_plan ap
                       JOIN inventory_tonbag t ON t.id = ap.tonbag_id
                       WHERE ap.lot_no = ? AND ap.status = 'RESERVED'""",
                    (lot_no,)
                )
                db_count = db_row['tb_count'] if db_row else 0
                db_kg = float(db_row['total_kg']) if db_row else 0

                pk = picking_qty.get(lot_no, {'qty_kg': 0, 'tonbag_count': 0})
                pk_kg = pk['qty_kg']
                pk_count = pk['tonbag_count']

                detail = {
                    'lot_no': lot_no,
                    'picking_kg': pk_kg,
                    'picking_count': pk_count,
                    'reserved_kg': db_kg,
                    'reserved_count': db_count,
                    'kg_match': abs(pk_kg - db_kg) < 1.0,
                    'count_match': pk_count == 0 or pk_count == db_count,
                }
                lot_details.append(detail)

                if not detail['kg_match']:
                    qty_mismatches.append(
                        f"LOT {lot_no}: 피킹 {pk_kg:,.0f}kg vs RESERVED {db_kg:,.0f}kg "
                        f"(차이: {abs(pk_kg - db_kg):,.0f}kg)"
                    )

            result['qty_mismatches'] = qty_mismatches
            result['lot_details'] = lot_details

            # --- 리포트 생성 ---
            lines = [
                '=' * 60,
                f'[Gate-1 교차검증] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                f'피킹리스트: {picking_no}',
                f'피킹 LOT: {len(picking_lots)}개 | RESERVED: {len(all_reserved_lots)}개 | 매칭: {len(matched)}개',
                '',
            ]

            # LOT 존재 불일치
            if only_in_picking:
                lines.append(f'❌ 피킹에만 있고 RESERVED 없는 LOT ({len(only_in_picking)}개):')
                for lot in sorted(only_in_picking)[:10]:
                    lines.append(f'   - {lot}')
                if len(only_in_picking) > 10:
                    lines.append(f'   ... 외 {len(only_in_picking)-10}개')
                lines.append('')

            if only_in_reserved:
                lines.append(f'⚠️ RESERVED에만 있고 피킹 없는 LOT ({len(only_in_reserved)}개):')
                for lot in sorted(only_in_reserved)[:10]:
                    lines.append(f'   - {lot}')
                lines.append('')

            # v6.12.1: 수량 불일치
            if qty_mismatches:
                lines.append(f'⚠️ 수량 불일치 ({len(qty_mismatches)}건):')
                for m in qty_mismatches[:10]:
                    lines.append(f'   - {m}')
                if len(qty_mismatches) > 10:
                    lines.append(f'   ... 외 {len(qty_mismatches)-10}건')
                lines.append('')

            # 매칭 LOT 요약
            if lot_details:
                ok_count = sum(1 for d in lot_details if d['kg_match'])
                lines.append(f'📊 매칭 LOT 수량 검증: {ok_count}/{len(lot_details)} 일치')
                lines.append('')

            # 최종 판정
            if not only_in_picking:
                if qty_mismatches:
                    lines.append('⚠️ Gate-1 승인 필요 — LOT 매칭 OK, 수량 불일치 있음')
                    lines.append('   관리자 승인 후 진행할 수 있습니다')
                    result['passed'] = False
                    result['requires_approval'] = True
                    result['fail_code'] = 'QTY_MISMATCH'
                else:
                    lines.append('✅ Gate-1 완전 통과 — LOT 매칭 + 수량 검증 모두 OK')
                    result['passed'] = True
            else:
                lines.append('🚫 Gate-1 실패 — 전체 출고 처리 중단됨')
                lines.append('   allocation_plan 확인 후 재시도하세요')

            lines.append('=' * 60)
            result['error_report'] = '\n'.join(lines)
            logger.info('[Gate-1] passed=%s, matched=%s, missing=%s, qty_mismatch=%s',
                        result['passed'], len(matched), len(only_in_picking), len(qty_mismatches))
        except (sqlite3.Error, AttributeError) as e:
            result['error_report'] = f'Gate-1 DB 오류: {e}'
            logger.error(f'[Gate-1] 오류: {e}', exc_info=True)
        return result

    @staticmethod
    def _gate1_to_json(gate1: dict) -> str:
        """Gate-1 결과를 JSON 문자열로 변환 (DB 저장용). set→list 자동 변환."""
        import json as _json
        try:
            serializable = {}
            for k, v in gate1.items():
                if isinstance(v, set):
                    serializable[k] = sorted(v)
                elif k == 'error_report':
                    continue  # 텍스트 리포트는 별도 저장
                else:
                    serializable[k] = v
            return _json.dumps(serializable, ensure_ascii=False)
        except (TypeError, ValueError):
            return _json.dumps({'passed': gate1.get('passed', False)})

    def execute_from_picking(
        self,
        picking_result,
        picking_no: str = '',
        sales_order: str = '',
        allow_qty_mismatch: bool = False,
        approval_reason: str = '',
    ) -> dict:
        """Gate-1 통과 후 피킹리스트 기반 RESERVED → PICKED 전환."""
        result = {'success': False, 'executed': 0, 'gate1': {}, 'errors': []}
        gate1 = self.gate1_verify_picking(picking_result, picking_no)
        result['gate1'] = gate1
        if gate1.get('requires_approval') and not allow_qty_mismatch:
            result['errors'].append('Gate-1 승인 필요: 수량 불일치(QTY_MISMATCH)')
            logger.warning('[execute_from_picking] 승인 필요 상태 → 중단')
            return result
        if not gate1['passed']:
            if gate1.get('requires_approval') and allow_qty_mismatch:
                logger.info('[execute_from_picking] 수량 불일치 승인 후 계속 진행')
            else:
                result['errors'].append(gate1['error_report'])
                logger.warning('[execute_from_picking] Gate-1 실패 → 중단')
                return result

        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            meta = picking_result.meta
            with self.db.transaction('IMMEDIATE'):
                if gate1.get('requires_approval') and allow_qty_mismatch:
                    try:
                        details = {
                            'picking_no': picking_no,
                            'sales_order': sales_order,
                            'fail_code': gate1.get('fail_code', 'QTY_MISMATCH'),
                            'qty_mismatches': list(gate1.get('qty_mismatches', [])),
                            'approval_reason': approval_reason or '',
                        }
                        self.db.execute(
                            """INSERT INTO audit_log(event_type, payload, created_at)
                               VALUES (?, ?, ?)""",
                            ('OUTBOUND_QTY_MISMATCH_APPROVED', json.dumps(details, ensure_ascii=False), now)
                        )
                    except sqlite3.Error as e:
                        logger.debug(f'Suppressed: {e}')
                self.db.execute(
                    """INSERT INTO picking_list_order
                       (sales_order, customer_ref, picking_date, status,
                        total_lots, total_weight, picking_no, delivery_terms,
                        port_loading, port_discharge, containers,
                        contact_person, contact_email,
                        total_nw_kg, total_gw_kg, gate1_result,
                        created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        sales_order or getattr(meta, 'sales_order', ''),
                        getattr(meta, 'outbound_id', ''),
                        getattr(meta, 'creation_date', ''),
                        'EXECUTED',
                        len(gate1['matched_lots']),
                        picking_result.summary.get('total_mt', 0) * 1000,
                        getattr(meta, 'picking_no', ''),
                        getattr(meta, 'delivery_terms', ''),
                        getattr(meta, 'port_loading', ''),
                        getattr(meta, 'port_discharge', ''),
                        getattr(meta, 'containers', '1'),
                        getattr(meta, 'contact_person', ''),
                        getattr(meta, 'contact_email', ''),
                        getattr(meta, 'total_nw_kg', ''),
                        getattr(meta, 'total_gw_kg', ''),
                        self._gate1_to_json(gate1),
                        now, now,
                    )
                )
                row = self.db.fetchone('SELECT last_insert_rowid() AS id')
                picking_order_id = row['id'] if row else None
                executed = 0
                for lot_no in gate1['matched_lots']:
                    self.db.execute(
                        """UPDATE allocation_plan SET status = 'EXECUTED', executed_at = ?
                           WHERE lot_no = ? AND status = 'RESERVED'""",
                        (now, lot_no)
                    )
                    tonbags = self.db.fetchall(
                        """SELECT id, weight FROM inventory_tonbag
                           WHERE lot_no = ? AND status = 'RESERVED'""",
                        (lot_no,)
                    )
                    for tb in tonbags:
                        self.db.execute(
                            """UPDATE inventory_tonbag SET
                                status = ?, picked_date = ?, updated_at = ?
                               WHERE id = ?""",
                            (STATUS_PICKED, now, now, tb['id'])
                        )
                        if picking_order_id is not None:
                            try:
                                self.db.execute(
                                    """INSERT INTO picking_list_detail
                                       (picking_order_id, lot_no, weight, picked_status, picked_at)
                                       VALUES (?, ?, ?, 'PICKED', ?)""",
                                    (picking_order_id, lot_no, tb.get('weight', 0), now)
                                )
                            except sqlite3.OperationalError:
                                pass
                    self._recalc_lot_status(lot_no)
                    executed += 1
                result['success'] = executed > 0
                result['executed'] = executed
                result['message'] = f'피킹 실행 완료: {executed}개 LOT → 판매화물 결정'
        except (sqlite3.Error, ValueError) as e:
            result['errors'].append(str(e))
            logger.error(f'[execute_from_picking] 오류: {e}', exc_info=True)
        return result

    def cancel_reservation(
        self,
        lot_no: str = None,
        plan_id: int = None,
        plan_ids: list = None,
    ) -> Dict:
        """
        RESERVED 예약 취소 → AVAILABLE 복원.
        plan_ids: 여러 건 일괄 취소 시 [id, ...] 전달.

        Returns:
            {'success': bool, 'cancelled': int}
        """
        result = {'success': False, 'cancelled': 0, 'errors': []}

        query = "SELECT id, lot_no, tonbag_id FROM allocation_plan WHERE status = 'RESERVED'"
        params = []
        if plan_ids:
            if not isinstance(plan_ids, (list, tuple)) or not plan_ids:
                result['message'] = "취소할 배정(plan_ids)이 비어 있습니다."
                return result
            query += " AND id IN (" + ",".join("?" * len(plan_ids)) + ")"
            params.extend(plan_ids)
        else:
            if lot_no:
                query += " AND lot_no = ?"
                params.append(lot_no)
            if plan_id is not None:
                query += " AND id = ?"
                params.append(plan_id)

        try:
            plans = self.db.fetchall(query, tuple(params))
            if not plans:
                result['message'] = "취소할 예약 없음"
                return result

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                touched_lots = set()
                for plan in plans:
                    self.db.execute(
                        """UPDATE inventory_tonbag SET
                            status = ?, picked_to = NULL, sale_ref = NULL, updated_at = ?
                        WHERE id = ?""",
                        (STATUS_AVAILABLE, now, plan['tonbag_id'])
                    )
                    self.db.execute(
                        """UPDATE allocation_plan SET status = 'CANCELLED', cancelled_at = ?
                        WHERE id = ?""",
                        (now, plan['id'])
                    )
                    result['cancelled'] += 1
                    # v6.12.1: stock_movement 'CANCEL_RESERVE' 이력
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'CANCEL_RESERVE', 0, ?, ?)",
                        (plan.get('lot_no', ''), f"plan_id={plan['id']}", now))
                    if plan.get('lot_no'):
                        touched_lots.add(plan['lot_no'])
                for lot_no in touched_lots:
                    self._recalc_lot_status(lot_no)

            result['success'] = result['cancelled'] > 0
            result['message'] = f"예약 취소: {result['cancelled']}건"

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"예약 취소 오류: {e}")
            result['errors'].append(str(e))

        return result

    def revert_picked_to_reserved(self, lot_no: str = None) -> Dict:
        """
        판매화물 결정 취소: PICKED → 판매 배정(RESERVED)으로 되돌림.
        allocation_plan EXECUTED → RESERVED, inventory_tonbag PICKED → RESERVED.
        """
        result = {'success': False, 'reverted': 0, 'errors': []}
        query = """SELECT id, lot_no, tonbag_id FROM allocation_plan WHERE status = 'EXECUTED'"""
        params = [] if not lot_no else [lot_no]
        if lot_no:
            query += " AND lot_no = ?"
        try:
            rows = self.db.fetchall(query, tuple(params))
            if not rows:
                result['message'] = "되돌릴 판매화물 결정(EXECUTED) 건이 없습니다."
                return result
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                for r in rows:
                    self.db.execute(
                        """UPDATE allocation_plan SET status = 'RESERVED', executed_at = NULL WHERE id = ?""",
                        (r['id'],)
                    )
                    self.db.execute(
                        """UPDATE inventory_tonbag SET status = ?, picked_date = NULL, updated_at = ?
                           WHERE id = ?""",
                        (STATUS_RESERVED, now, r['tonbag_id'])
                    )
                    result['reverted'] += 1
                    # v6.12.1: stock_movement 'REVERT_PICKED' 이력
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'REVERT_PICKED', 0, ?, ?)",
                        (r['lot_no'], f"plan_id={r['id']}, PICKED→RESERVED", now))
                    self._recalc_lot_status(r['lot_no'])
            result['success'] = True
            result['message'] = f"판매화물 결정 취소: {result['reverted']}건 → 판매 배정(RESERVED)"
        except (sqlite3.Error, ValueError, TypeError) as e:
            logger.error(f"revert_picked_to_reserved 오류: {e}")
            result['errors'].append(str(e))
        return result

    def revert_sold_to_picked(self, lot_no: str = None) -> Dict:
        """
        출고 취소(→ 판매화물 결정): SOLD → PICKED로 되돌림.
        inventory_tonbag SOLD → PICKED, sold_table 해당 톤백 행 삭제.
        """
        result = {'success': False, 'reverted': 0, 'errors': []}
        query = """SELECT id, lot_no FROM inventory_tonbag WHERE status = ?"""
        params = [STATUS_SOLD]
        if lot_no:
            query += " AND lot_no = ?"
            params.append(lot_no)
        try:
            tonbags = self.db.fetchall(query, tuple(params))
            if not tonbags:
                result['message'] = "되돌릴 출고(SOLD) 톤백이 없습니다."
                return result
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                touched_lots = set()
                for tb in tonbags:
                    tb_id = tb['id']
                    self.db.execute(
                        """UPDATE inventory_tonbag SET status = ?, outbound_date = NULL, updated_at = ?
                           WHERE id = ?""",
                        (STATUS_PICKED, now, tb_id)
                    )
                    try:
                        self.db.execute("DELETE FROM sold_table WHERE tonbag_id = ?", (tb_id,))
                    except sqlite3.OperationalError:
                        pass
                    result['reverted'] += 1
                    # v6.12.1: stock_movement 'REVERT_SOLD' 이력
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'REVERT_SOLD', 0, ?, ?)",
                        (tb.get('lot_no', ''), f"tonbag_id={tb_id}, SOLD→PICKED", now))
                    if tb.get('lot_no'):
                        touched_lots.add(tb['lot_no'])
                for lot in touched_lots:
                    self._recalc_lot_status(lot)
            result['success'] = True
            result['message'] = f"출고 취소: {result['reverted']}건 → 판매화물 결정(PICKED)"
        except (sqlite3.Error, ValueError, TypeError) as e:
            logger.error(f"revert_sold_to_picked 오류: {e}")
            result['errors'].append(str(e))
        return result

    # ═══════════════════════════════════════════════════════
    # v6.2.4 Stage4: 빠른 출고 (Quick Outbound) — 성능 개선판
    # ═══════════════════════════════════════════════════════

    def quick_outbound(self, lot_no: str, count: int, customer: str,
                        reason: str = '', operator: str = '') -> Dict:
        """
        빠른 출고: Allocation 없이 소량 즉시 출고.
        최대 QUICK_OUTBOUND_MAX_TONBAGS개, AVAILABLE → PICKED 직접 전환.
        """
        import uuid
        from engine_modules.constants import QUICK_OUTBOUND_MAX_TONBAGS
        result = {
            'success': False, 'picked_count': 0,
            'total_weight_kg': 0, 'errors': []
        }

        if count > QUICK_OUTBOUND_MAX_TONBAGS:
            result['errors'].append(f"빠른 출고 최대 {QUICK_OUTBOUND_MAX_TONBAGS}개 (요청: {count}개)")
            return result
        customer = (customer or '').strip()
        if not customer:
            result['errors'].append("고객명 필수")
            return result
        lot_no = str(lot_no).strip()
        if not lot_no:
            result['errors'].append("LOT 번호 필요")
            return result

        try:
            with self.db.transaction("IMMEDIATE"):
                tonbags = self.db.fetchall(
                    """SELECT id, sub_lt, weight, tonbag_uid FROM inventory_tonbag
                       WHERE lot_no = ? AND status = ? AND COALESCE(is_sample,0) = 0
                       ORDER BY sub_lt DESC LIMIT ?""",
                    (lot_no, STATUS_AVAILABLE, count))

                if len(tonbags) < count:
                    raise ValueError(f"가용 톤백 부족: {len(tonbags)}개 (요청: {count}개)")

                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                quick_ref = f"QUICK-{now.replace(' ', '_').replace(':', '')}-{uuid.uuid4().hex[:6]}"
                total_weight = 0.0

                for tb in tonbags:
                    tb_w = tb['weight'] or 0
                    # AVAILABLE → PICKED 직접
                    self.db.execute(
                        """UPDATE inventory_tonbag
                           SET status = ?, picked_to = ?, sale_ref = ?,
                               picked_date = ?, outbound_date = ?, updated_at = ?
                           WHERE id = ?""",
                        (STATUS_PICKED, customer, quick_ref, now, now, now, tb['id']))

                    # allocation_plan EXECUTED 직접 적재
                    try:
                        self.db.execute(
                            """INSERT INTO allocation_plan
                               (lot_no, tonbag_id, sub_lt, customer, sale_ref,
                                qty_mt, status, source, source_file, executed_at, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, 'EXECUTED', 'QUICK', ?, ?, ?)""",
                            (lot_no, tb['id'], tb['sub_lt'], customer, quick_ref,
                             tb_w / 1000.0, f"reason={reason}, op={operator}", now, now))
                    except (sqlite3.OperationalError, OSError) as e:
                        if "source" in str(e).lower():
                            self.db.execute(
                                """INSERT INTO allocation_plan
                                   (lot_no, tonbag_id, sub_lt, customer, sale_ref,
                                    qty_mt, status, source_file, executed_at, created_at)
                                   VALUES (?, ?, ?, ?, ?, ?, 'EXECUTED', ?, ?, ?)""",
                                (lot_no, tb['id'], tb['sub_lt'], customer, quick_ref,
                                 tb_w / 1000.0, f"QUICK:reason={reason}:op={operator}", now, now))
                        else:
                            raise
                    # picking_table
                    try:
                        self.db.execute(
                            """INSERT INTO picking_table
                            (lot_no, tonbag_id, sub_lt, tonbag_uid, customer, qty_kg, status, picking_date, created_by, remark)
                            VALUES (?,?,?,?,?,?,'ACTIVE',?,'system',?)""",
                            (lot_no, tb['id'], tb['sub_lt'], tb.get('tonbag_uid') or '', customer, tb_w, now,
                             f"QUICK: {reason}, op={operator}"))
                    except Exception as e:
                        logger.debug(f"picking_table INSERT skipped in quick outbound: {e}")
                    total_weight += tb_w
                    result['picked_count'] += 1

                # inventory 차감
                self.db.execute(
                    "UPDATE inventory SET current_weight=MAX(0,current_weight-?), picked_weight=picked_weight+?, updated_at=? WHERE lot_no=?",
                    (total_weight, total_weight, now, lot_no))
                # stock_movement
                self.db.execute(
                    "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) VALUES (?,'QUICK_OUTBOUND',?,?,?)",
                    (
                        lot_no,
                        total_weight,
                        f"customer={customer}, reason={reason}, op={operator}, count={count}, ref={quick_ref}",
                        now,
                    ))

                self._recalc_lot_status(lot_no)
                if hasattr(self, 'verify_lot_integrity'):
                    integrity = self.verify_lot_integrity(lot_no)
                    if not integrity.get('valid', True):
                        err_list = integrity.get('errors', [])
                        err_msg = "; ".join(str(e) for e in err_list[:3])
                        raise ValueError(f"빠른 출고 정합성 실패 ({lot_no}): {err_msg}")

                result['success'] = True
                result['total_weight_kg'] = total_weight
                result['quick_ref'] = quick_ref
                result['message'] = f"빠른 출고: {result['picked_count']}개 → PICKED ({total_weight:,.0f}kg)"
                logger.info(result['message'])

        except (ValueError, TypeError) as e:
            result['errors'].append(str(e))
            logger.error(f"빠른 출고 검증 오류: {e}", exc_info=True)
        except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
            result['errors'].append(f"DB 오류: {e}")
            logger.error(f"빠른 출고 DB 오류: {e}", exc_info=True)
        except Exception as e:
            result['errors'].append(f"예기치 않은 오류: {e}")
            logger.error(f"빠른 출고 미예상 오류: {e}", exc_info=True)
        return result
