# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 출고 헬퍼 Mixin (GE)
==========================================

outbound_mixin.py에서 분리된 헬퍼 메서드 모음.
Lines 61-589, 4016 원본 기준.

작성자: Ruby (남기동)
"""

import logging
import os
import hashlib
import configparser
import csv
import json
from datetime import datetime
from typing import Dict, List

from utils.path_utils import resolve_reports_dir
from core.types import normalize_lot

logger = logging.getLogger(__name__)


class OutboundHelpersMixin:
    """출고 관련 헬퍼 메서드 Mixin."""

    def _table_exists(self, table_name: str) -> bool:
        try:
            row = self.db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            return bool(row)
        except Exception as exc:
            logger.debug("_table_exists(%s) 조회 실패: %s", table_name, exc)
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
            logger.debug("[SUPPRESSED] exception in outbound_mixin.py")  # noqa
        return ""

    def _normalize_outbound_date(self, raw_date) -> str:
        """outbound_date를 YYYY-MM-DD로 정규화, 실패 시 ValueError.
        [C] v6.8.3: NULL/공백이면 오늘 날짜 자동 설정 (execute_reserved 영구 제외 방지)
        """
        txt = str(raw_date or "").strip()
        if not txt:
            # [C] NULL → 오늘 날짜 자동 설정 + 경고 로그
            _today = datetime.now().strftime('%Y-%m-%d')
            logger.warning(
                f"[C OUTBOUND_DATE_NULL] outbound_date 미입력 "
                f"→ 오늘 날짜 자동 설정: {_today}"
            )
            return _today
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
        v6.9.4 [LOT-MODE-ONLY]: 항상 'lot' 반환.

        설계 원칙 (기동님 확정 2026-03-10):
          - 예약 단계(Allocation)에서는 tonbag_id를 특정하지 않음
          - 개수(pick_count)만 allocation_plan에 기록 (tonbag_id = NULL)
          - 실출고 바코드 스캔 순간에 비로소 tonbag_id 확정
          - 이 원칙이 SQM의 근간 로직

        Returns:
            'lot' (항상 고정, tonbag 모드 폐기)
        """
        # v6.9.4: tonbag 즉시 특정 경로 완전 폐기
        # override_mode / ENV / settings.ini 값 무시 — 항상 lot 모드
        _ = override_mode  # 하위호환 시그니처 유지
        return "lot"

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

    def _preflight_alloc_cols(self) -> dict:
        """allocation_plan 테이블 컬럼 존재 여부 사전 검사.
        v8.2.2: dead code 제거 후 테스트 의존성으로 복구.
        반환: {cols: set, has_source: bool, has_line_no: bool,
               has_export_type: bool, has_workflow_status: bool, has_fail_code: bool}
        """
        try:
            rows = self.db.fetchall(
                "PRAGMA table_info(allocation_plan)"
            ) or []
            cols = set(
                (r.get('name') if isinstance(r, dict) else r[1])
                for r in rows
            )
            return {
                'cols':               cols,
                'has_source':         'source'          in cols,
                'has_line_no':        'line_no'         in cols,
                'has_export_type':    'export_type'     in cols,
                'has_workflow_status':'workflow_status' in cols,
                'has_fail_code':      'fail_code'       in cols,
            }
        except Exception as e:
            logger.debug(f"_preflight_alloc_cols 오류: {e}")
            return {
                'cols': set(),
                'has_source': False, 'has_line_no': False,
                'has_export_type': False, 'has_workflow_status': False,
                'has_fail_code': False,
            }
