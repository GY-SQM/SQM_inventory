# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 출고 배정 서비스 Mixin (GA)
=================================================

outbound_mixin.py에서 분리된 Allocation 관련 메서드.
Lines 1158-2299 원본 기준.

작성자: Ruby (남기동)
"""

import sqlite3
import logging
import math
import random
import os
import json
from datetime import datetime
from typing import Dict

from engine_modules.constants import (
    STATUS_AVAILABLE,
    STATUS_RESERVED,
    STATUS_PICKED,
    STATUS_SOLD,
    STATUS_OUTBOUND,
    normalize_customer,
    get_tonbag_unit_weight,
)
from core.types import normalize_lot

logger = logging.getLogger(__name__)


class OutboundAllocationMixin:
    """출고 배정(Allocation) Mixin."""

    # v6.9.4 [LOT-MODE-ONLY]: 승인 임계치 조정
    # 기존 50% → 100% 초과 불가(사실상 비활성화) + 절대량 20,000kg(40톤)으로 상향
    # 이유: LOT 모드에서는 STAGED → 스캔 불가 → 출고 마비
    # 실운영 기준: LOT 전량 예약이 일반적 (CATL/BYD 전량 출고 흔함)
    ALLOCATION_APPROVAL_QTY_KG_THRESHOLD = 20000.0   # 40MT 초과 시만 승인 (기존 10MT)
    ALLOCATION_APPROVAL_RATIO_THRESHOLD  = 1.01       # 100% 초과 불가 → 사실상 비활성화

    def _allocation_risk_flags(self, qty_kg: float, available_kg: float) -> list[str]:
        flags = []
        if qty_kg >= self.ALLOCATION_APPROVAL_QTY_KG_THRESHOLD:
            flags.append("LARGE_VOLUME")
        if available_kg > 0 and qty_kg >= available_kg * self.ALLOCATION_APPROVAL_RATIO_THRESHOLD:
            flags.append("OVER_50PCT")
        return flags

    def _allocation_requires_approval(self, qty_kg: float, available_kg: float) -> bool:
        return len(self._allocation_risk_flags(qty_kg, available_kg)) > 0

    def _ra_build_result_template(self, allocation_rows: list, reservation_mode: str) -> dict:
        """v8.6.2 [SRP]: reserve_from_allocation 결과 dict 초기화 템플릿.

        예약 결과의 단일 진실 공급원 — 키 추가 시 여기만 수정.
        """
        return {
            'success': False,
            'reserved': 0,
            'pending_approval': 0,
            'errors': [],
            'error_details': [],
            'plan_ids': [],
            'requested_rows': len(allocation_rows),
            'reservation_mode': reservation_mode or 'tonbag',
        }

    def _ra_get_alloc_plan_cols(self) -> set:
        """v8.6.2 [SRP]: allocation_plan 테이블 컬럼 집합 조회.

        has_* 플래그 계산의 단일 소스.
        DB 조회 실패 시 빈 set 반환 (fallback 안전).
        """
        try:
            rows = self.db.fetchall("PRAGMA table_info(allocation_plan)")
            return {str(r.get("name", "")).strip().lower() for r in (rows or [])}
        except Exception as e:
            logger.debug(f"[_ra_get_alloc_plan_cols] 컬럼 조회 스킵: {e}")
            return set()

    # ── v8.6.4 [SRP] reserve_from_allocation 서브메서드 ────────────────

    @staticmethod
    def _ra_alloc_val(alloc, key, default=None):
        """AllocationRow(dataclass) 또는 dict 모두 지원하는 값 접근 헬퍼."""
        if isinstance(alloc, dict):
            return alloc.get(key, default)
        return getattr(alloc, key, default)

    def _ra_insert_plan_row(self, payload: dict, alloc_plan_cols: set) -> int:
        """allocation_plan 테이블에 행 삽입, 생성된 row id 반환."""
        cols, vals = [], []
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
        return int(row.get("rid", 0) if isinstance(row, dict) else (row[0] if row else 0))

    def _ra_build_plan_payload(self, *, lot_no, customer, sale_ref, qty_mt,
                               outbound_date, status, source_label, now,
                               source_file, source_fingerprint,
                               alloc_plan_cols, import_batch_id, line_no,
                               export_type_val='', sc_rcvd_val=None,
                               tonbag_id=None, sub_lt=None,
                               workflow_status=None, risk_flags_txt=None):
        """v8.6.4 [SRP]: 3가지 경로(승인대기/LOT/톤백) 공통 payload 생성.

        기존 3회 반복 payload 구성 → 단일 메서드로 통합.
        """
        cols = alloc_plan_cols
        payload = {
            "lot_no": lot_no,
            "tonbag_id": tonbag_id,
            "sub_lt": sub_lt,
            "customer": customer,
            "sale_ref": sale_ref,
            "qty_mt": qty_mt,
            "outbound_date": outbound_date,
            "status": status,
            "source_file": source_file,
            "source_fingerprint": source_fingerprint if "source_fingerprint" in cols else "",
            "created_at": now,
        }
        if "source" in cols:
            payload["source"] = source_label
        if "import_batch_id" in cols and import_batch_id:
            payload["import_batch_id"] = import_batch_id
        if "line_no" in cols and line_no is not None:
            payload["line_no"] = line_no
        if "gate_status" in cols:
            payload["gate_status"] = "PASS"
        if "fail_code" in cols:
            payload["fail_code"] = ""
        if "fail_reason" in cols:
            payload["fail_reason"] = ""
        if "validated_at" in cols:
            payload["validated_at"] = now
        if "workflow_status" in cols and workflow_status:
            payload["workflow_status"] = workflow_status
        if "risk_flags" in cols and risk_flags_txt is not None:
            payload["risk_flags"] = risk_flags_txt
        if "approved_by" in cols and workflow_status:
            payload["approved_by"] = ""
        if "approved_at" in cols and workflow_status:
            payload["approved_at"] = None
        if "rejected_reason" in cols and workflow_status:
            payload["rejected_reason"] = ""
        if "export_type" in cols:
            payload["export_type"] = export_type_val
        if "sc_rcvd" in cols:
            payload["sc_rcvd"] = sc_rcvd_val
        return payload

    def _ra_parse_allocation_line(self, alloc, _alloc_val_fn):
        """Allocation 행 1줄을 파싱하여 dict로 반환. 정규화 포함."""
        lot_no = (normalize_lot(_alloc_val_fn(alloc, 'lot_no')) or '').strip()
        _raw_customer = str(_alloc_val_fn(alloc, 'sold_to') or _alloc_val_fn(alloc, 'customer') or '').strip()
        try:
            customer = normalize_customer(_raw_customer)
        except Exception as exc:
            logger.debug("normalize_customer 실패, 원본값 사용: %s", exc)
            customer = _raw_customer
        sale_ref = str(_alloc_val_fn(alloc, 'sale_ref') or '').strip()
        qty_mt = float(_alloc_val_fn(alloc, 'qty_mt') or 0)
        outbound_date = _alloc_val_fn(alloc, 'outbound_date')
        sublot_count = int(_alloc_val_fn(alloc, 'sublot_count') or _alloc_val_fn(alloc, 'tonbag_count') or 0)
        is_sample_req = bool(_alloc_val_fn(alloc, 'is_sample', False))
        export_type_val = str(_alloc_val_fn(alloc, 'export_type') or '').strip()
        _sc = _alloc_val_fn(alloc, 'sc_rcvd')
        sc_rcvd_val = str(_sc) if _sc else None
        _unit_val = str(_alloc_val_fn(alloc, 'unit') or '').strip().upper()
        return {
            'lot_no': lot_no, 'customer': customer, '_raw_customer': _raw_customer,
            'sale_ref': sale_ref, 'qty_mt': qty_mt, 'outbound_date': outbound_date,
            'sublot_count': sublot_count, 'is_sample_req': is_sample_req,
            'export_type_val': export_type_val, 'sc_rcvd_val': sc_rcvd_val,
            'unit_val': _unit_val,
        }

    def _ra_validate_line_inputs(self, ctx: dict, line_no: int, result: dict, _build_error_detail) -> str:
        """행 입력 유효성 검증. 에러 시 에러 코드 문자열 반환, 통과 시 '' 반환."""
        lot_no = ctx['lot_no']
        customer = ctx['customer']
        qty_mt = ctx['qty_mt']
        sale_ref = ctx['sale_ref']

        if not lot_no:
            msg = "LOT 번호 누락"
            result['errors'].append(msg)
            _build_error_detail(line_no, "INVALID_LOT", msg, lot_no, customer, qty_mt)
            return "INVALID_LOT"
        if qty_mt == 0:
            msg = (f"[AL-09][ZERO_QTY] LOT {lot_no}: qty_mt=0 "
                   f"(빈 행 또는 수량 미입력 — 엑셀 확인 필요)")
            logger.error(msg)
            result['errors'].append(msg)
            _build_error_detail(line_no, "ZERO_QTY", msg, lot_no, customer, qty_mt)
            return "ZERO_QTY"
        if qty_mt < 0:
            msg = (f"[INVALID_QTY] LOT {lot_no}: qty_mt={qty_mt} "
                   f"(음수는 예약 불가 — 양수값 입력 필요)")
            logger.warning(msg)
            result['errors'].append(msg)
            _build_error_detail(line_no, "INVALID_QTY", msg, lot_no, customer, qty_mt)
            return "INVALID_QTY"
        if not customer:
            msg = (f"[INVALID_CUSTOMER] LOT {lot_no}: customer/sold_to가 비어 있음 "
                   f"(고객사 지정 필수)")
            logger.warning(msg)
            result['errors'].append(msg)
            _build_error_detail(line_no, "INVALID_CUSTOMER", msg, lot_no, customer, qty_mt)
            return "INVALID_CUSTOMER"
        if not sale_ref:
            msg = (f"[WARN_SALE_REF] LOT {lot_no}: sale_ref 미입력 "
                   f"(판매참조번호 없이 예약 진행)")
            logger.warning(msg)
            result.setdefault('warnings', []).append(msg)
        if ctx['unit_val'] and ctx['unit_val'] not in ('', 'KG'):
            msg = (f"[UNIT_MISMATCH] 허용되지 않은 단위: '{ctx['unit_val']}' "
                   f"(lot={lot_no}, line={line_no}) — KG만 허용")
            logger.warning(msg)
            result['errors'].append(msg)
            _build_error_detail(line_no, "UNIT_MISMATCH", msg, lot_no, customer, qty_mt)
            return "UNIT_MISMATCH"
        return ""

    def _ra_check_alloc_conflict(self, ctx: dict, line_no: int, result: dict, _build_error_detail) -> bool:
        """동일 (lot_no, customer, sale_ref, outbound_date) 활성 상태 충돌 체크. 충돌 시 True."""
        lot_no = ctx['lot_no']
        customer = ctx['customer']
        sale_ref = ctx['sale_ref']
        outbound_date = ctx['outbound_date']
        qty_mt = ctx['qty_mt']
        try:
            _conflict_statuses = "('STAGED','RESERVED','PENDING_APPROVAL')"
            _conflict_row = self.db.fetchone(
                f"""SELECT id FROM allocation_plan
                   WHERE lot_no = ? AND customer = ? AND sale_ref = ?
                     AND status IN {_conflict_statuses}
                     AND (outbound_date = ? OR (outbound_date IS NULL AND ? IS NULL))
                   LIMIT 1""",
                (lot_no, customer, sale_ref, outbound_date, outbound_date)
            )
            if _conflict_row:
                _conflict_id = _conflict_row.get('id', '?') if isinstance(_conflict_row, dict) else _conflict_row[0]
                msg = (f"[ALLOC_CONFLICT] 중복 행 차단: lot={lot_no} "
                       f"customer={customer} sale_ref={sale_ref} "
                       f"outbound_date={outbound_date} "
                       f"(기존 plan_id={_conflict_id})")
                logger.warning(msg)
                result['errors'].append(msg)
                _build_error_detail(line_no, "ALLOC_CONFLICT", msg, lot_no, customer, qty_mt)
                return True
        except Exception as _ce:
            logger.debug(f"[ALLOC_CONFLICT] 충돌 체크 스킵 (DB 오류): {_ce}")
        return False

    def _ra_check_lot_dup(self, ctx: dict, line_no: int, result: dict,
                          _build_error_detail, _batch_processed_lots: set) -> bool:
        """LOT 단위 sale_ref 중복 체크. 중복 시 True."""
        sale_ref = ctx['sale_ref']
        lot_no = ctx['lot_no']
        qty_mt = ctx['qty_mt']
        customer = ctx['customer']
        if not sale_ref:
            return False
        try:
            _lot_key = (sale_ref, lot_no)
            if _lot_key not in _batch_processed_lots:
                _lot_dup = self.db.fetchone(
                    """SELECT id FROM allocation_plan
                       WHERE sale_ref = ? AND lot_no = ?
                         AND tonbag_id IS NULL
                         AND status IN ('RESERVED','PENDING_APPROVAL')
                       LIMIT 1""",
                    (sale_ref, lot_no)
                )
                if _lot_dup:
                    _dup_id = _lot_dup.get('id','?') if isinstance(_lot_dup, dict) else _lot_dup[0]
                    msg = (
                        f"[LOT_MODE_DUP] LOT 단위 예약 중복: sale_ref={sale_ref} "
                        f"lot={lot_no} plan_id={_dup_id} — 이전 배정이 남아있음 (전체 초기화 후 재시도)"
                    )
                    logger.warning(msg)
                    result['errors'].append(msg)
                    _build_error_detail(line_no, "LOT_MODE_DUP", msg, lot_no, customer, qty_mt)
                    return True
        except Exception as _ge:
            logger.debug(f"[LOT_MODE_DUP 중복체크] 스킵: {_ge}")
        return False

    def _ra_resolve_pick_count(self, ctx: dict, tonbags: list, weight_kg: float,
                               _unit_w: float, result: dict) -> int:
        """요청 수량에서 pick_count(배정 톤백 수) 계산."""
        lot_no = ctx['lot_no']
        sublot_count = ctx['sublot_count']
        is_sample_req = ctx['is_sample_req']
        qty_mt = ctx['qty_mt']

        if sublot_count > 0:
            pick_count = sublot_count
            if not is_sample_req and _unit_w > 0 and qty_mt > 0:
                _calc_count = max(1, math.ceil((qty_mt * 1000) / _unit_w))
                if abs(_calc_count - sublot_count) > 1:
                    _b_warn = (
                        f"[TONBAG_COUNT_MISMATCH] {lot_no}: "
                        f"입력 sublot_count={sublot_count}개 "
                        f"vs qty_mt={qty_mt}MT÷{_unit_w}kg=계산{_calc_count}개 "
                        f"— sublot_count 우선 사용"
                    )
                    logger.warning(_b_warn)
                    result.setdefault('warnings', []).append(_b_warn)
        else:
            if is_sample_req:
                pick_count = 1
            elif _unit_w <= 0:
                _b_warn = (
                    f"[UNIT_WEIGHT_UNKNOWN] {lot_no}: "
                    f"톤백 단가 조회 실패(0kg) → 500kg 기본값 사용"
                )
                logger.warning(_b_warn)
                result.setdefault('warnings', []).append(_b_warn)
                _unit_w = 500.0
                pick_count = max(1, math.ceil(weight_kg / _unit_w))
            else:
                pick_count = max(1, math.ceil(weight_kg / _unit_w))
            logger.debug(
                f"[B pick_count] {lot_no}: "
                f"qty_mt={qty_mt}→weight_kg={weight_kg}÷unit_w={_unit_w}"
                f"=pick_count={pick_count}"
            )
        return pick_count

    def _ra_record_reservation_result(self, lot_no: str, reserved_in_lot: int,
                                       reserved_kg: float, selected_sub_lts: list,
                                       seed_hash: str, customer: str, sale_ref: str,
                                       effective_mode: str, allocation_random_mode: str,
                                       is_sample_req: bool, now: str,
                                       _batch_processed_lots: set, result: dict):
        """예약 결과 기록: stock_movement + audit_log + 배치 추적."""
        result['reserved'] += reserved_in_lot
        if reserved_in_lot > 0 and sale_ref:
            _batch_processed_lots.add((sale_ref, lot_no))
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
            try:
                from engine_modules.audit_helper import write_audit, EVT_RESERVED
                write_audit(self.db, EVT_RESERVED, lot_no=lot_no, detail={
                    'customer':    customer,
                    'tonbags':     reserved_in_lot,
                    'weight_kg':   reserved_kg,
                    'sale_ref':    sale_ref,
                    'mode':        effective_mode,
                })
            except Exception as _ae:
                logger.debug(f"[RESERVED audit] 스킵: {_ae}")
        logger.info(
            f"[reserve-{effective_mode}] {lot_no}: {reserved_in_lot}개 RESERVED "
            f"(rand={allocation_random_mode}, seed={seed_hash[:8] if seed_hash else '-'}, "
            f"sample={is_sample_req}, sub_lt={selected_sub_lts}) -> {customer}"
        )

    def _ra_log_random_selection(self, lot_no: str, sale_ref: str, customer: str,
                                  allocation_random_mode: str, seed_hash: str,
                                  tonbags: list, selected: list, reserved_in_lot: int, now: str):
        """랜덤 선택 이력 audit_log 저장."""
        try:
            _all_uids = [str(tb.get('tonbag_uid') or tb.get('sub_lt','')) for tb in tonbags]
            _sel_uids = [str(tb.get('tonbag_uid') or tb.get('sub_lt','')) for tb in (selected or [])]
            _excl_uids = [u for u in _all_uids if u not in _sel_uids]
            _g7_payload = json.dumps({
                "event":              "ALLOC_RANDOM_LOG",
                "lot_no":             lot_no,
                "sale_ref":           sale_ref,
                "customer":           customer,
                "random_mode":        allocation_random_mode,
                "random_seed":        seed_hash if seed_hash else None,
                "candidate_bag_count": len(_all_uids),
                "candidate_bag_list": _all_uids,
                "selected_bag_count": len(_sel_uids),
                "selected_bag_list":  _sel_uids,
                "excluded_bag_count": len(_excl_uids),
                "excluded_bag_list":  _excl_uids,
                "excluded_reason":    "not_selected_by_random_shuffle",
                "pick_count":         reserved_in_lot,
                "selection_timestamp": now,
            }, ensure_ascii=False)
            self.db.execute(
                "INSERT INTO audit_log(event_type, event_data, created_at) VALUES (?,?,?)",
                ("ALLOC_RANDOM_LOG", _g7_payload, now),
            )
            logger.debug(f"[G7-RANDOM-LOG] {lot_no} 랜덤 선택 로그 저장: "
                         f"후보={len(_all_uids)} 선택={len(_sel_uids)} 제외={len(_excl_uids)}")
        except Exception as _g7e:
            logger.debug(f"[G7-RANDOM-LOG] 로그 저장 스킵: {_g7e}")

    def _ra_check_duplicate_file(self, source_file, source_fingerprint, has_source_fp_col, result):
        """v8.6.4 [SRP]: 중복 Allocation 파일 감지 (fingerprint 우선, basename 폴백)."""
        if not source_fingerprint:
            return
        try:
            fname = os.path.basename(source_file) if source_file and source_file != '(붙여넣기)' else '(붙여넣기)'
            if has_source_fp_col:
                dup = self.db.fetchone(
                    """SELECT COUNT(*) AS cnt FROM allocation_plan
                       WHERE status = 'RESERVED' AND source_fingerprint = ?""",
                    (source_fingerprint,))
            else:
                dup = self.db.fetchone(
                    """SELECT COUNT(*) AS cnt FROM allocation_plan
                       WHERE status = 'RESERVED' AND source_file LIKE ?""",
                    (f"%{fname}",))
            dup_cnt = dup.get('cnt', 0) if isinstance(dup, dict) else (dup[0] if dup else 0)
            if dup_cnt > 0:
                result['duplicate_file'] = True
                result['duplicate_count'] = int(dup_cnt)
                result['duplicate_file_name'] = fname
                result['duplicate_source_fingerprint'] = source_fingerprint
        except Exception as e:
            logger.debug(f"중복 Allocation 파일 감지 실패: {e}")

    def _ra_g5_batch_validate(self, allocation_rows, result):
        """v8.6.4 [SRP]: [G5-MXBG] 배치 내 동일 LOT 합산 + 기존 RESERVED 초과 사전 검증.

        Returns True if G5 hard-stop (전체 배치 차단), False otherwise.
        """
        _av = self._ra_alloc_val
        _batch_lot_qty: dict = {}
        for _ba in (allocation_rows or []):
            _bln = (normalize_lot(_av(_ba, 'lot_no')) or '').strip()
            _bqt = float(_av(_ba, 'qty_mt') or 0)
            if _bln:
                _batch_lot_qty[_bln] = _batch_lot_qty.get(_bln, 0.0) + _bqt

        _g5_lot_list = [k for k, v in _batch_lot_qty.items() if v > 0]
        if not _g5_lot_list:
            return False

        _g5_ph = ",".join("?" * len(_g5_lot_list))
        _g5_total_rows = self.db.fetchall(
            f"SELECT lot_no, COALESCE(SUM(weight),0) AS total_kg "
            f"FROM inventory_tonbag "
            f"WHERE lot_no IN ({_g5_ph}) "
            f"AND status NOT IN ('SOLD','RETURNED','DEPLETED') "
            f"GROUP BY lot_no", _g5_lot_list)
        _g5_total_map = {
            (r.get('lot_no') if isinstance(r, dict) else r[0]):
            float(r.get('total_kg') if isinstance(r, dict) else r[1])
            for r in (_g5_total_rows or [])
        }
        _g5_already_rows = self.db.fetchall(
            f"SELECT lot_no, COALESCE(SUM(qty_mt * 1000), 0) AS already_kg "
            f"FROM allocation_plan "
            f"WHERE lot_no IN ({_g5_ph}) "
            f"AND status IN ('RESERVED','STAGED','PENDING_APPROVAL') "
            f"AND qty_mt >= 0.01 "
            f"GROUP BY lot_no", _g5_lot_list)
        _g5_already_map = {
            (r.get('lot_no') if isinstance(r, dict) else r[0]):
            float(r.get('already_kg') if isinstance(r, dict) else r[1])
            for r in (_g5_already_rows or [])
        }

        _g5_errors = []
        for _bln, _bqt_sum in _batch_lot_qty.items():
            if _bqt_sum <= 0:
                continue
            _bqt_kg = _bqt_sum * 1000.0
            _btotal_kg = _g5_total_map.get(_bln, 0.0)
            _balready_kg = _g5_already_map.get(_bln, 0.0)
            if _btotal_kg > 0 and (_balready_kg + _bqt_kg) > _btotal_kg + 0.5:
                _bremain_kg = max(0.0, _btotal_kg - _balready_kg)
                _g5_msg = (
                    f"[G5-MXBG-EXCEED] {_bln}: "
                    f"기존예약 {_balready_kg:.0f}kg + 이번배치 {_bqt_kg:.0f}kg"
                    f" > MXBG총량 {_btotal_kg:.0f}kg"
                    f" (잔여 배정 가능: {_bremain_kg:.0f}kg)")
                logger.error(_g5_msg)
                _g5_errors.append(_g5_msg)
                result['errors'].append(_g5_msg)

        if _g5_errors:
            result['success'] = False
            result['errors'].insert(0,
                f"[G5-HARD-STOP] 배치 내 LOT 중복 초과 {len(_g5_errors)}건 — 전체 배치 차단")
            logger.error(f"[G5-HARD-STOP] {len(_g5_errors)}건 배치 차단")
            return True
        return False

    def _ra_pre_dup_warnings(self, allocation_rows, result):
        """v8.6.4 [SRP]: [PRE-DUP] 기존 예약 LOT 사전 중복 감지 (경고만, 처리는 계속)."""
        _av = self._ra_alloc_val
        try:
            _batch_sale_refs = set()
            for _ba in (allocation_rows or []):
                _bsr = str(_av(_ba, 'sale_ref') or '').strip()
                _bqt = float(_av(_ba, 'qty_mt') or 0)
                if _bsr and _bqt >= 0.01:
                    _batch_sale_refs.add(_bsr)
            for _bsr in _batch_sale_refs:
                _already = self.db.fetchall(
                    "SELECT DISTINCT lot_no FROM allocation_plan "
                    "WHERE sale_ref=? AND status IN ('RESERVED','PENDING_APPROVAL','STAGED')",
                    (_bsr,))
                _already_lots = {
                    str(r.get('lot_no') if isinstance(r, dict) else r[0]).strip()
                    for r in (_already or []) if r}
                if _already_lots:
                    _batch_main_lots = {
                        (normalize_lot(_av(_ba, 'lot_no')) or '').strip()
                        for _ba in (allocation_rows or [])
                        if float(_av(_ba, 'qty_mt') or 0) >= 0.01}
                    _overlap = _already_lots & _batch_main_lots
                    if _overlap:
                        _msg = (
                            f"[PRE-DUP] sale_ref={_bsr}: "
                            f"이미 예약된 LOT {len(_overlap)}개 포함 — "
                            f"{sorted(_overlap)[:5]}{'...' if len(_overlap)>5 else ''} "
                            f"(LOT_MODE_DUP으로 스킵됩니다)")
                        logger.warning(_msg)
                        result.setdefault('warnings', []).append(_msg)
        except Exception as _pde:
            logger.debug(f"[PRE-DUP] 사전 중복 감지 스킵: {_pde}")

    def _ra_finalize_result(self, result, allocation_rows, source_file, has_alloc_batch_table):
        """v8.6.4 [SRP]: [Phase 3] 결과 집계 + import_batch 통계 + fail report."""
        if result['reserved'] == 0 and result['errors']:
            all_dup = all("중복 배정" in err or "이미 예약/출고됨" in err
                          for err in result['errors'])
            if all_dup:
                result['errors'].append(
                    "⚠️ 모든 LOT이 이미 예약 상태입니다.\n"
                    "• 다시 예약: [예약 취소] 후 재시도\n"
                    "• 기존 예약 진행: [출고 실행]")

        if has_alloc_batch_table and result.get("import_batch_id"):
            try:
                failed_lines = len(result.get("error_details", []))
                passed_lines = max(0, len(allocation_rows or []) - failed_lines)
                self.db.execute(
                    "UPDATE allocation_import_batch SET passed_lines=?, failed_lines=? WHERE id=?",
                    (passed_lines, failed_lines, result.get("import_batch_id")))
            except Exception as e:
                logger.debug(f"allocation_import_batch 집계 업데이트 스킵: {e}")

        if result.get("errors"):
            report_paths = self._save_allocation_fail_report(
                allocation_rows, result.get("errors", []),
                source_file=source_file,
                error_details=result.get("error_details", []))
            if report_paths.get("csv") or report_paths.get("json"):
                result["fail_report"] = report_paths
                if has_alloc_batch_table and result.get("import_batch_id"):
                    try:
                        self.db.execute(
                            "UPDATE allocation_import_batch SET report_csv_path=?, report_json_path=? WHERE id=?",
                            (report_paths.get("csv", ""),
                             report_paths.get("json", ""),
                             result.get("import_batch_id")))
                    except Exception as e:
                        logger.debug(f"allocation_import_batch 리포트 경로 업데이트 스킵: {e}")

    # ── reserve_from_allocation 메인 ──────────────────────────────────

    def reserve_from_allocation(self, allocation_rows: list, source_file: str = '', reservation_mode: str = '') -> Dict:
        """
        Allocation 엑셀에서 파싱된 데이터로 톤백 예약 (AVAILABLE → RESERVED).
        allocation_plan 테이블에 계획 기록 + 톤백 상태 변경.

        v9.1 구조:
          [Phase 1] import_batch 생성 (보조)
          [Phase 2] 메인 트랜잭션 — All-or-Nothing 보호 (with self.db.transaction)
            [P2-1] G5 사전 검증  [P2-2] 사전 중복 경고  [P2-3] LOT별 루프
          [Phase 3] 결과 집계

        All-or-Nothing: Phase 2 에러 시 전체 자동 롤백. Phase 1/3은 보조.

        Args:
            allocation_rows: AllocationRow 또는 dict 리스트
            source_file: 원본 파일명

        Returns:
            {'success': bool, 'reserved': int, 'errors': [], 'plan_ids': []}
        """
        # v8.6.2 [SRP]: result 초기화 → _ra_build_result_template()
        result = self._ra_build_result_template(allocation_rows, reservation_mode)

        _alloc_val = self._ra_alloc_val  # v8.6.4 [SRP]: static method 참조

        # [RUBI-PHASE2] 랜덤출고 정책:
        strict_mode = self._get_allocation_strict_mode()
        allocation_random_mode = self._get_allocation_random_mode()
        effective_mode = self._get_allocation_reservation_mode(reservation_mode)
        result['reservation_mode'] = effective_mode
        has_alloc_batch_table = self._table_exists("allocation_import_batch")
        has_source_fp_col = self._has_allocation_source_fingerprint_column()
        source_fingerprint = self._compute_allocation_source_fingerprint(allocation_rows, source_file)
        # v8.6.2 [SRP]: col 조회 → _ra_get_alloc_plan_cols()
        alloc_plan_cols = self._ra_get_alloc_plan_cols()
        has_workflow_status_col = "workflow_status" in alloc_plan_cols

        def _build_error_detail(line_no: int, fail_code: str, reason: str, lot_no: str, sold_to: str, qty_mt):
            result['error_details'].append({
                "line_no": line_no, "fail_code": fail_code, "reason": reason,
                "lot_no": lot_no, "sold_to": sold_to, "qty_mt": qty_mt,
            })

        def _insert_plan(payload: dict):
            """v8.6.4: 서브메서드 위임 + plan_ids 추적."""
            rid = self._ra_insert_plan_row(payload, alloc_plan_cols)
            if rid:
                result["plan_ids"].append(rid)
            return rid

        # v8.6.4 [SRP]: 중복 Allocation 파일 감지 → 서브메서드
        self._ra_check_duplicate_file(source_file, source_fingerprint, has_source_fp_col, result)

        # ══ [Phase 1] import_batch 생성 (보조, 실패해도 계속) ════════
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
            except Exception as e:
                logger.debug(f"allocation_import_batch 생성 스킵: {e}")

        # ══ [Phase 2] 메인 트랜잭션 (All-or-Nothing 보호) ════════════
        try:
            with self.db.transaction("IMMEDIATE"):
                strict_errors = []
                plan_line_counter = 0

                # v8.6.4 [SRP]: G5 사전 검증 → 서브메서드
                if self._ra_g5_batch_validate(allocation_rows, result):
                    return result  # G5 HARD-STOP

                # v8.6.4 [SRP]: PRE-DUP 사전 중복 경고 → 서브메서드
                self._ra_pre_dup_warnings(allocation_rows, result)

                # ── [Phase 2-3] LOT별 예약 루프 ────────────────────
                _batch_processed_lots = set()
                for line_no, alloc in enumerate(allocation_rows, start=1):
                    # 행 파싱
                    ctx = self._ra_parse_allocation_line(alloc, _alloc_val)
                    lot_no = ctx['lot_no']
                    customer = ctx['customer']
                    sale_ref = ctx['sale_ref']
                    qty_mt = ctx['qty_mt']
                    outbound_date = ctx['outbound_date']
                    sublot_count = ctx['sublot_count']
                    is_sample_req = ctx['is_sample_req']
                    export_type_val = ctx['export_type_val']
                    sc_rcvd_val = ctx['sc_rcvd_val']

                    if ctx['_raw_customer'] != customer and ctx['_raw_customer']:
                        logger.debug(f"[E normalize_customer] '{ctx['_raw_customer']}' → '{customer}'")

                    # Gate A: 입력 유효성 검증
                    _val_err = self._ra_validate_line_inputs(ctx, line_no, result, _build_error_detail)
                    if _val_err:
                        if _val_err in ('INVALID_LOT',):
                            strict_errors.append(result['errors'][-1])
                        continue

                    # Gate: Allocation Row 충돌 차단
                    if self._ra_check_alloc_conflict(ctx, line_no, result, _build_error_detail):
                        continue

                    # Gate B: LOT+sale_ref 중복 차단
                    if self._ra_check_lot_dup(ctx, line_no, result, _build_error_detail, _batch_processed_lots):
                        continue

                    # [A] v6.8.3: LOT 헤더 미존재 명시 체크
                    # inventory 테이블에 LOT 자체가 없으면
                    # 이후 톤백 조회도 의미 없으므로 여기서 즉시 차단
                    _inv_hdr = self.db.fetchone(
                        "SELECT lot_no, status, product FROM inventory WHERE lot_no = ? LIMIT 1",
                        (lot_no,)
                    )
                    if not _inv_hdr:
                        msg = (
                            f"[LOT_NOT_FOUND] {lot_no}: "
                            f"재고 테이블에 LOT 없음 — 입고 처리 후 다시 시도하세요 "
                            f"(Allocation 파일의 LOT 번호 오타 여부도 확인)"
                        )
                        logger.error(msg)
                        result['errors'].append(msg)
                        strict_errors.append(msg)
                        _build_error_detail(line_no, "LOT_NOT_FOUND", msg, lot_no, customer, qty_mt)
                        continue
                    _inv_status = str(_inv_hdr.get('status') or '').strip().upper()

                    # v8.5.9 [G2-MXBG-FIX]: 총 cargo (톤백 + 샘플 포함)
                    # 샘플 1kg도 배정 요청에 포함되므로 MXBG 총량에도 샘플 포함
                    if qty_mt > 0:
                        _g2_total_row = self.db.fetchone(
                            "SELECT COALESCE(SUM(weight),0) AS total_kg "
                            "FROM inventory_tonbag "
                            "WHERE lot_no=? "
                            "AND status NOT IN ('SOLD','RETURNED','DEPLETED')",
                            (lot_no,)
                        )
                        _g2_total_kg = float(
                            (_g2_total_row.get('total_kg') if isinstance(_g2_total_row, dict) else _g2_total_row[0])
                            if _g2_total_row else 0
                        )
                        # v8.6.0 [G2-COUNT*500→SUM]: COUNT*500 하드코딩 제거
                        # → qty_mt*1000 직접 합산으로 500/1000kg 톤백 모두 정확히 처리
                        # v8.6.0 [G2-STAGED포함]: STAGED/PENDING_APPROVAL도 예약 점유량에 포함
                        # → 승인 워크플로우 활성화 시 이중배정 방지
                        _g2_already_row = self.db.fetchone(
                            "SELECT COALESCE(SUM(qty_mt * 1000), 0) AS already_kg "
                            "FROM allocation_plan "
                            "WHERE lot_no=? "
                            "AND status IN ('RESERVED','STAGED','PENDING_APPROVAL') "
                            "AND qty_mt >= 0.01",
                            (lot_no,)
                        )
                        _g2_already_kg = float(
                            (_g2_already_row.get('already_kg') if isinstance(_g2_already_row, dict) else _g2_already_row[0])
                            if _g2_already_row else 0
                        )
                        _g2_req_kg = qty_mt * 1000.0
                        # 검증: 기존예약 + 이번요청 > MXBG 총량
                        if _g2_total_kg > 0 and (_g2_already_kg + _g2_req_kg) > _g2_total_kg + 0.5:
                            _g2_remain_kg = max(0.0, _g2_total_kg - _g2_already_kg)
                            _g2_msg = (
                                f"[G2-MXBG-EXCEED] {lot_no}: "
                                f"기존예약 {_g2_already_kg:.0f}kg + 이번요청 {_g2_req_kg:.0f}kg"
                                f" > MXBG총량 {_g2_total_kg:.0f}kg"
                                f" (잔여 배정 가능: {_g2_remain_kg:.0f}kg)"
                            )
                            logger.error(_g2_msg)
                            result['errors'].append(_g2_msg)
                            strict_errors.append(_g2_msg)
                            _build_error_detail(line_no, "G2_CARGO_EXCEED", _g2_msg, lot_no, customer, qty_mt)
                            continue

                    # v6.9.0 [C2]: PARTIAL 추가 — 부분 출고 LOT도 추가 Allocation 허용
                    if _inv_status not in ('AVAILABLE', 'RESERVED', 'PARTIAL'):
                        msg = (
                            f"[LOT_STATUS_MISMATCH] {lot_no}: "
                            f"현재 LOT 상태={_inv_status} "
                            f"(AVAILABLE/RESERVED/PARTIAL만 Allocation 가능)"
                        )
                        logger.warning(msg)
                        result['errors'].append(msg)
                        strict_errors.append(msg)
                        _build_error_detail(line_no, "LOT_STATUS_MISMATCH", msg, lot_no, customer, qty_mt)
                        continue

                    # v6.12 Addon-G: DB에서 실제 톤백 단가 조회 (500/1000kg 동적 대응)
# [v6.8.6 top-level import로 이동]                     from engine_modules.constants import STATUS_PICKED, STATUS_RESERVED, STATUS_SOLD, get_tonbag_unit_weight
                    _unit_w = get_tonbag_unit_weight(self.db, lot_no)
                    weight_kg = qty_mt * 1000 if qty_mt > 0 else sublot_count * _unit_w

                    if is_sample_req:
                        tonbags = self.db.fetchall(
                            """SELECT id, sub_lt, weight,
                               COALESCE(location,'') AS location
                               FROM inventory_tonbag
                               WHERE lot_no = ? AND status = ?
                                 AND COALESCE(is_sample, 0) = 1""",
                            (lot_no, STATUS_AVAILABLE)
                        )
                    else:
                        tonbags = self.db.fetchall(
                            """SELECT id, sub_lt, weight,
                               COALESCE(location,'') AS location
                               FROM inventory_tonbag
                               WHERE lot_no = ? AND status = ?
                                 AND COALESCE(is_sample, 0) = 0""",
                            (lot_no, STATUS_AVAILABLE)
                        )

                    # [P2] v6.8.1: 위치 미배정 톤백 경고
                    # 입고 후 현장 배치가 안 된 톤백(location=NULL/공백)이
                    # 출고 지시되면 현장에서 찾지 못하는 사태 방지
                    if tonbags and not is_sample_req:
                        _no_loc = [tb for tb in tonbags
                                   if not str(tb.get('location') or '').strip()]
                        if _no_loc:
                            _loc_warn = (
                                f"[LOCATION_NOT_ASSIGNED] {lot_no}: "
                                f"{len(_no_loc)}개 톤백 위치 미배정 "
                                f"— [재고관리→위치배정] 후 출고 진행 권장"
                            )
                            logger.warning(_loc_warn)
                            result.setdefault('warnings', []).append(_loc_warn)

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

                    # [B] qty_mt → 톤백 개수 변환 검증
                    pick_count = self._ra_resolve_pick_count(ctx, tonbags, weight_kg, _unit_w, result)
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
                        # v6.9.3 [AL-FIX-5]: 가용 초과 → HARD-STOP (oversell 원천 차단)
                        # PENDING_APPROVAL로 넘기지 않고 즉시 차단
                        msg = (
                            f"[QTY_EXCEEDS_AVAILABLE] {lot_no}: "
                            f"요청 {pick_count}개 > 가용 {len(tonbags)}개 "
                            f"— oversell 방지 HARD-STOP "
                            f"(Allocation 수정 또는 추가 입고 후 재시도)"
                        )
                        result['errors'].append(msg)
                        strict_errors.append(msg)
                        _build_error_detail(line_no, "QTY_EXCEEDS_AVAILABLE", msg, lot_no, customer, qty_mt)
                        continue

                    reserved_in_lot = 0
                    reserved_kg = 0.0
                    seed_hash = ""
                    selected_sub_lts = []
                    selected = []
                    available_kg = sum(float(tb.get('weight') or 0) for tb in tonbags)

                    # v6.9.3 [AL-10-FIX]: STAGED 경로에서도 실질 가용 수량 체크
                    # AVAILABLE 톤백 수 - 이미 STAGED/PENDING 계획된 수 = 실질 가용
                    # v8.5.9: 샘플 요청은 전용 is_sample=1 행에서 배정하므로 STAGED 체크 스킵
                    if not is_sample_req:
                        try:
                            _staged_cnt_row = self.db.fetchone(
                                """SELECT COUNT(*) AS cnt FROM allocation_plan
                                   WHERE lot_no=? AND status IN ('STAGED','RESERVED','PENDING_APPROVAL')
                                     AND tonbag_id IS NULL AND qty_mt >= 0.01""",
                                (lot_no,)
                            )
                            _staged_cnt = int((_staged_cnt_row.get('cnt') if isinstance(_staged_cnt_row, dict)
                                               else _staged_cnt_row[0]) if _staged_cnt_row else 0)
                            _real_avail = len(tonbags) - _staged_cnt
                            if _real_avail < pick_count:
                                msg = (
                                    f"[QTY_EXCEEDS_AVAILABLE] {lot_no}: "
                                    f"요청 {pick_count}개 > 실질가용 {_real_avail}개 "
                                    f"(AVAILABLE={len(tonbags)}, 이미STAGED={_staged_cnt}) "
                                    f"— oversell 방지 HARD-STOP"
                                )
                                result['errors'].append(msg)
                                strict_errors.append(msg)
                                _build_error_detail(line_no, "QTY_EXCEEDS_AVAILABLE", msg, lot_no, customer, qty_mt)
                                continue
                        except Exception as _ae:
                            logger.debug(f"[AL-10-FIX] 실질가용 체크 스킵: {_ae}")

                    # v6.9.0 [C4]: True or 제거 — 실제 승인 필요 여부 판정
                    need_approval = self._allocation_requires_approval(weight_kg, available_kg)
                    risk_flags = self._allocation_risk_flags(weight_kg, available_kg)

                    # v8.6.4 [SRP]: payload 공통 kwargs
                    _common_kw = dict(
                        lot_no=lot_no, customer=customer, sale_ref=sale_ref,
                        outbound_date=ob_date_str, now=now,
                        source_file=source_file, source_fingerprint=source_fingerprint,
                        alloc_plan_cols=alloc_plan_cols, import_batch_id=import_batch_id,
                        export_type_val=export_type_val, sc_rcvd_val=sc_rcvd_val,
                    )

                    # 대량/위험 건은 STAGED + PENDING_APPROVAL로 적재하고 즉시 RESERVED는 하지 않음
                    if need_approval and has_workflow_status_col:
                        qty_mt_each = (qty_mt / pick_count) if pick_count > 0 else qty_mt
                        risk_txt = "|".join(risk_flags)
                        for _ in range(pick_count):
                            plan_line_counter += 1
                            payload = self._ra_build_plan_payload(
                                qty_mt=qty_mt_each, status="STAGED",
                                source_label="APPROVAL_QUEUE",
                                line_no=plan_line_counter,
                                workflow_status="PENDING_APPROVAL",
                                risk_flags_txt=risk_txt,
                                **_common_kw)
                            _insert_plan(payload)
                            result['pending_approval'] += 1
                        logger.info(
                            f"[reserve-stage] {lot_no}: 승인대기 {pick_count}건 적재 "
                            f"(qty_kg={weight_kg:.0f}, avail_kg={available_kg:.0f}, risk={risk_flags})")
                        continue

                    if effective_mode == "lot":
                        # LOT 단위 예약: 톤백 상태는 바꾸지 않고 allocation_plan에 미지정(tonbag_id NULL) 계획만 기록.
                        qty_mt_each = (qty_mt / pick_count) if pick_count > 0 else qty_mt
                        for _ in range(pick_count):
                            plan_line_counter += 1
                            payload = self._ra_build_plan_payload(
                                qty_mt=qty_mt_each, status="RESERVED",
                                source_label="LOT", line_no=plan_line_counter,
                                **_common_kw)
                            _insert_plan(payload)
                            reserved_in_lot += 1
                        reserved_kg = sum(float(tb.get('weight') or 0) for tb in tonbags[:pick_count])
                    else:
                        # 톤백 단위 예약: 기존 동작 유지
                        pool = list(tonbags)
                        if allocation_random_mode == "seeded":
                            seed_hash = self._build_allocation_seed(
                                lot_no=lot_no, sale_ref=sale_ref, qty_mt=qty_mt,
                                outbound_date=ob_date_str, source_file=source_file)
                            rng = random.Random(seed_hash)
                            rng.shuffle(pool)
                        else:
                            random.shuffle(pool)
                        selected = pool[:pick_count]
                        selected_sub_lts = [str(tb.get('sub_lt', '')) for tb in selected]

                        # v7.7.0: 개별 UPDATE → executemany (N+1 → 1회 처리)
                        _upd_rows = [
                            (STATUS_RESERVED, customer, sale_ref, now, tb['id'])
                            for tb in selected]
                        self.db.executemany(
                            """UPDATE inventory_tonbag SET
                                status = ?, picked_to = ?, sale_ref = ?, updated_at = ?
                            WHERE id = ?""", _upd_rows)
                        # v8.1.5 [TONBAG-QTY-FIX]: LOT 모드와 동일하게 per-tonbag 단위로 저장
                        qty_mt_each_tb = (qty_mt / pick_count) if pick_count > 0 else qty_mt
                        for tb in selected:
                            plan_line_counter += 1
                            payload = self._ra_build_plan_payload(
                                qty_mt=qty_mt_each_tb, status="RESERVED",
                                source_label="TONBAG", line_no=plan_line_counter,
                                tonbag_id=tb["id"], sub_lt=tb["sub_lt"],
                                **_common_kw)
                            _insert_plan(payload)
                            reserved_in_lot += 1
                            reserved_kg += float(tb.get('weight') or 0)

                    # 예약 결과 기록: movement + audit + 배치 추적
                    self._ra_record_reservation_result(
                        lot_no, reserved_in_lot, reserved_kg, selected_sub_lts,
                        seed_hash, customer, sale_ref, effective_mode,
                        allocation_random_mode, is_sample_req, now,
                        _batch_processed_lots, result)

                    # 랜덤 선택 이력 로그
                    self._ra_log_random_selection(
                        lot_no, sale_ref, customer, allocation_random_mode,
                        seed_hash, tonbags, selected, reserved_in_lot, now)

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

        # v8.6.4 [SRP]: Phase 3 결과 집계 → 서브메서드
        self._ra_finalize_result(result, allocation_rows, source_file, has_alloc_batch_table)

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
                # ⑤ v6.7.1: 자동 마이그레이션 — 컬럼 없으면 즉시 추가 후 재시도
                logger.warning("[⑤] workflow_status 컬럼 없음 → 자동 마이그레이션 실행")
                try:
                    self.db.execute(
                        "ALTER TABLE allocation_plan "
                        "ADD COLUMN workflow_status TEXT DEFAULT 'APPROVED'"
                    )
                    self.db.execute(
                        "ALTER TABLE allocation_plan "
                        "ADD COLUMN rejected_reason TEXT"
                    )
                    self.db.execute(
                        "ALTER TABLE allocation_plan "
                        "ADD COLUMN approved_by TEXT"
                    )
                    self.db.execute(
                        "ALTER TABLE allocation_plan "
                        "ADD COLUMN approved_at TEXT"
                    )
                    # 컬럼 재조회
                    rows2 = self.db.fetchall("PRAGMA table_info(allocation_plan)")
                    alloc_plan_cols = {str(r.get("name","")).strip().lower()
                                       for r in (rows2 or [])}
                    if "workflow_status" not in alloc_plan_cols:
                        result["errors"].append(
                            "workflow_status 자동 마이그레이션 실패 — 수동 확인 필요")
                        return result
                    logger.info("[⑤] workflow_status 자동 마이그레이션 완료")
                except Exception as _e:
                    result["errors"].append(
                        f"workflow_status 마이그레이션 오류: {_e}")
                    return result
            has_risk_flags_col = "risk_flags" in alloc_plan_cols
            has_source_col = "source" in alloc_plan_cols
            has_approved_by_col = "approved_by" in alloc_plan_cols
            has_approved_at_col = "approved_at" in alloc_plan_cols

            # [C] v6.7.8: SQL 상수 리터럴로 교체 — ALLOC_STAGED/ALLOC_WF_APPROVED는
            # Python 변수이므로 SQL 문자열 안에 직접 쓰면 구문 오류 발생
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
                    str(r.get("sale_ref", "")).strip()
                    qty_mt = float(r.get("qty_mt", 0) or 0)
                    _ = qty_mt <= 0.01 + 1e-9  # is_sample_req: 향후 샘플 필터링 예약
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
                               workflow_status=ALLOC_WF_APPLIED
                           WHERE id=? AND status=ALLOC_STAGED AND workflow_status=ALLOC_WF_APPROVED""",
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
                                float((qty_mt or 0) * 1000.0),
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
