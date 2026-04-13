# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 출고 예약 실행/확정 서비스 Mixin (GD)
===========================================================

outbound_mixin.py에서 분리된 execute_reserved + confirm_outbound 관련 메서드.
Lines 2300-2954 원본 기준.

작성자: Ruby (남기동)
"""

import sqlite3
import logging
import math
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
)

logger = logging.getLogger(__name__)


class OutboundReservedMixin:
    """출고 예약 실행/확정 Mixin."""

    # ── execute_reserved 헬퍼 ─────────────────────────────────

    def _er_load_reserved_plans(self, lot_no: str = None, target_date: str = None) -> list:
        """RESERVED 상태 allocation_plan 조회."""
        query = """SELECT ap.id, ap.lot_no, ap.tonbag_id, ap.sub_lt,
                          ap.customer, ap.sale_ref, ap.outbound_date
                   FROM allocation_plan ap
                   WHERE ap.status = 'RESERVED'"""
        params = []
        if lot_no:
            query += " AND ap.lot_no = ?"
            params.append(lot_no)
        if target_date:
            query += " AND ap.outbound_date <= ?"
            params.append(target_date)
        return self.db.fetchall(query, tuple(params))

    def _er_warn_stale_plans(self, plans: list, result: dict):
        """outbound_date 30일 초과 만료 예약 경고."""
        if not plans:
            return
        try:
            from datetime import timedelta
            _h_threshold = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            _stale = [
                p for p in plans
                if p.get('outbound_date') and str(p.get('outbound_date','')) < _h_threshold
            ]
            if _stale:
                _stale_lots = list({p.get('lot_no','') for p in _stale})[:5]
                _h_warn = (
                    f"[STALE_RESERVATION] 출고일 30일 초과 예약 {len(_stale)}건 포함 "
                    f"— LOT: {', '.join(_stale_lots)} "
                    f"/ 담당자 확인 권장"
                )
                logger.warning(_h_warn)
                result.setdefault('warnings', []).append(_h_warn)
        except Exception as _he:
            logger.debug(f"[ER_STALE_WARN] 스킵: {_he}")

    def _er_validate_tonbag(self, plan: dict, result: dict):
        """톤백 상태/무게 검증. (tb_dict, tb_weight, tonbag_uid) 반환, 실패 시 None."""
        tb_id = plan['tonbag_id']
        p_lot = plan['lot_no']

        tb = self.db.fetchone(
            "SELECT weight, status, tonbag_uid, "
            "COALESCE(is_sample, 0) AS is_sample FROM inventory_tonbag WHERE id = ?",
            (tb_id,)
        )
        if not tb or tb['status'] != STATUS_RESERVED:
            result['errors'].append(f"톤백 {tb_id} 상태 불일치")
            return None

        _is_sample_tb = int(tb.get('is_sample') or 0)
        tb_weight = tb['weight'] or 0

        if tb_weight <= 0:
            _k_warn = (
                f"[ZERO_WEIGHT_TONBAG] 톤백 {tb_id} (lot={p_lot}) "
                f"무게=0kg — 입고 데이터 오류, PICKED 스킵 "
                f"(재고관리→무게 수정 후 재시도)"
            )
            logger.warning(_k_warn)
            result['errors'].append(_k_warn)
            return None

        if _is_sample_tb and tb_weight > 1.01:
            _warn = (f"[SAMPLE_WEIGHT_WARN] 샘플 톤백 {tb_id} (lot={p_lot}) "
                     f"무게={tb_weight}kg > 1kg — 이상값, PICKED 스킵")
            logger.warning(_warn)
            result['errors'].append(_warn)
            return None

        tonbag_uid = (tb.get('tonbag_uid') or '').strip() or None
        return {'tb': tb, 'weight': tb_weight, 'uid': tonbag_uid}

    def _er_apply_pick_transition(self, plan: dict, tb_weight: float, now: str):
        """톤백 RESERVED→PICKED 전환 + inventory weight 갱신 + plan EXECUTED."""
        tb_id = plan['tonbag_id']
        p_lot = plan['lot_no']

        # 톤백 상태 전환
        self.db.execute(
            """UPDATE inventory_tonbag SET
                status = ?, picked_date = ?, outbound_date = ?, updated_at = ?
            WHERE id = ?""",
            (STATUS_PICKED, now, plan['outbound_date'] or now, now, tb_id)
        )
        # inventory weight 갱신
        self.db.execute(
            """UPDATE inventory SET
                current_weight = MAX(0, current_weight - ?),
                picked_weight = picked_weight + ?,
                updated_at = ?
            WHERE lot_no = ?""",
            (tb_weight, tb_weight, now, p_lot)
        )
        if hasattr(self, '_recalc_current_weight'):
            self._recalc_current_weight(p_lot, reason='P2_RESERVED_TO_PICKED')
        # plan 상태 갱신
        self.db.execute(
            """UPDATE allocation_plan SET status = 'EXECUTED', executed_at = ?
            WHERE id = ?""",
            (now, plan['id'])
        )

    def _er_record_pick_movement(self, plan: dict, tb_weight: float, now: str):
        """stock_movement에 PICKED_MOVE 이력 INSERT."""
        self.db.execute(
            """INSERT INTO stock_movement
            (lot_no, movement_type, qty_kg, remarks, created_at)
            VALUES (?, 'PICKED_MOVE', ?, ?, ?)""",
            (plan['lot_no'], tb_weight,
             f"RESERVED→PICKED, customer={plan['customer']}, sale_ref={plan['sale_ref']}", now)
        )

    def _er_insert_picking_row(self, plan: dict, tb_weight: float, tonbag_uid, now: str, result: dict) -> bool:
        """picking_table에 PICKED 이력 INSERT. 중복 시 False 반환 (해당 톤백 스킵)."""
        try:
            self.db.execute(
                """INSERT INTO picking_table
                (lot_no, tonbag_id, sub_lt, tonbag_uid, customer, qty_kg, status, picking_date, created_by, remark)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, 'system', ?)""",
                (plan['lot_no'], plan['tonbag_id'], plan['sub_lt'], tonbag_uid,
                 plan.get('customer') or '', tb_weight, now,
                 f"plan_id={plan['id']}, sale_ref={plan.get('sale_ref', '')}")
            )
        except sqlite3.OperationalError as e:
            _oe_msg = str(e).lower()
            if "no such table" in _oe_msg:
                pass
            elif "unique" in _oe_msg:
                _h3_msg = (
                    f"[PICKING_DUPLICATE] 중복 피킹 차단: "
                    f"tonbag_id={plan['tonbag_id']}, lot={plan['lot_no']} — "
                    f"이미 picking_table에 존재합니다"
                )
                logger.warning(_h3_msg)
                result['errors'].append(_h3_msg)
                return False
            else:
                # NOTE: picking_table INSERT 실패 — 운영 중요도 높을 수 있으므로 경고 로깅
                logger.warning(
                    f"[ER_PICKING] INSERT 실패: tonbag_id={plan['tonbag_id']}, "
                    f"lot={plan['lot_no']}, error={e}"
                )
        return True

    # ── execute_reserved 메인 ────────────────────────────────

    def execute_reserved(self, lot_no: str = None, target_date: str = None) -> Dict:
        """
        RESERVED 톤백을 PICKED로 전환 (출고 실행).
        lot_no 지정 시 해당 LOT만, target_date 지정 시 해당 날짜 이하만 실행.

        Returns:
            {'success': bool, 'executed': int, 'errors': []}
        """
        result = {'success': False, 'executed': 0, 'errors': []}

        try:
            # 1) RESERVED plans 로드
            plans = self._er_load_reserved_plans(lot_no, target_date)

            # 2) 만료 예약 경고
            self._er_warn_stale_plans(plans, result)

            # 3) 예약 없음 처리
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

            # 4) 트랜잭션: plan별 RESERVED→PICKED 전환
            with self.db.transaction("IMMEDIATE"):
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                processed_lots = set()

                for plan in plans:
                    p_lot = plan['lot_no']
                    tb_id = plan['tonbag_id']

                    # LOT 모드: tonbag_id=NULL → 바코드 스캔 대기
                    if tb_id is None:
                        logger.debug(
                            f"[LOT-MODE] {p_lot} plan_id={plan['id']} "
                            f"tonbag_id=NULL → 바코드 스캔 대기 (execute_reserved 스킵)"
                        )
                        result['executed'] += 1
                        processed_lots.add(p_lot)
                        continue

                    # 톤백 검증
                    validated = self._er_validate_tonbag(plan, result)
                    if not validated:
                        continue

                    # 상태 전환 + weight 갱신 + plan EXECUTED
                    self._er_apply_pick_transition(plan, validated['weight'], now)

                    # movement 이력
                    self._er_record_pick_movement(plan, validated['weight'], now)

                    # picking_table INSERT (중복 시 스킵)
                    if not self._er_insert_picking_row(plan, validated['weight'], validated['uid'], now, result):
                        continue

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


    # ══════════════════════════════════════════════════════════════════════
    # v8.6.4: confirm_outbound + gate1_verify_picking 분해 — 서브메서드 4개
    # ══════════════════════════════════════════════════════════════════════

    def _co_check_double_sold(self, tonbag_id) -> bool:
        """v8.6.4: 이중 SOLD 차단 (confirm_outbound 분해 1/4).

        sold_table에 동일 tonbag_id가 이미 존재하면 True (이중 차단).
        """
        import sqlite3 as _sq
        if not tonbag_id:
            return False
        try:
            row = self.db.fetchone(
                "SELECT id FROM sold_table WHERE tonbag_id=? AND status IN ('OUTBOUND','SOLD')",
                (tonbag_id,)
            )
            return bool(row)
        except (_sq.OperationalError, OSError):
            return False

    def _co_verify_weight_conservation(self, lot_no: str) -> dict:
        """v8.6.4: 출고 확정 후 무게 보존 법칙 사후검증 (confirm_outbound 분해 2/4).

        initial_weight == current_weight + picked_weight (+-1.0kg 허용)
        Returns: {'ok': bool, 'diff': float, 'msg': str}
        """
        import sqlite3 as _sq
        try:
            row = self.db.fetchone(
                """SELECT i.initial_weight,
                          COALESCE(SUM(CASE WHEN t.status='AVAILABLE' THEN t.weight ELSE 0 END),0) AS avail,
                          COALESCE(SUM(CASE WHEN t.status='PICKED'    THEN t.weight ELSE 0 END),0) AS picked,
                          COALESCE(SUM(CASE WHEN t.status IN ('OUTBOUND','SOLD')
                                           THEN t.weight ELSE 0 END),0) AS outb
                   FROM inventory i
                   LEFT JOIN inventory_tonbag t ON t.lot_no=i.lot_no AND COALESCE(t.is_sample,0)=0
                   WHERE i.lot_no=?
                   GROUP BY i.lot_no""",
                (lot_no,)
            )
            if not row:
                return {'ok': True, 'diff': 0.0, 'msg': ''}
            r = dict(row) if not isinstance(row, dict) else row
            initial = float(r.get('initial_weight') or 0)
            actual  = float(r.get('avail',0)) + float(r.get('picked',0)) + float(r.get('outb',0))
            diff    = abs(initial - actual)
            ok      = diff <= 1.0
            msg     = ('' if ok else
                       f"[LOT_TOTAL_MISMATCH] {lot_no}: initial={initial:.1f} actual={actual:.1f} diff={diff:.1f}kg")
            return {'ok': ok, 'diff': diff, 'msg': msg}
        except (_sq.OperationalError, OSError) as e:
            logger.debug(f"[confirm] 무게 검증 스킵: {e}")
            return {'ok': True, 'diff': 0.0, 'msg': ''}

    def _g1_aggregate_picking_qty(self, picking_rows: list) -> dict:
        """v8.6.4: 피킹 LOT별 요청 수량 집계 (gate1_verify_picking 분해 3/4).

        Returns: {lot_no: {'qty_mt': float, 'bag_count': int}}
        """
        from collections import defaultdict
        agg = defaultdict(lambda: {'qty_mt': 0.0, 'bag_count': 0})
        for r in picking_rows:
            lot = str(r.get('lot_no') or '').strip()
            if not lot:
                continue
            qty = float(r.get('qty_mt') or r.get('weight_kg', 0) / 1000.0)
            agg[lot]['qty_mt']    += qty
            agg[lot]['bag_count'] += int(r.get('bag_count') or 1)
        return dict(agg)

    def _g1_cancel_excess_allocation(self, lot_no: str,
                                      excess_mt: float) -> int:
        """v8.6.4: Picking < RESERVED 초과분 allocation_plan CANCELLED (gate1_verify_picking 분해 4/4).

        최신 순으로 초과분만 CANCELLED.
        Returns: cancelled 건수
        """
        import sqlite3 as _sq
        import math
        if excess_mt <= 0:
            return 0
        excess_bags = math.ceil(excess_mt / 0.5)
        try:
            candidates = self.db.fetchall(
                """SELECT id FROM allocation_plan
                   WHERE lot_no=? AND status='RESERVED'
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (lot_no, excess_bags)
            )
            if not candidates:
                return 0
            ids = tuple(
                (r.get('id') if isinstance(r, dict) else r[0])
                for r in candidates
            )
            placeholders = ','.join(['?'] * len(ids))
            self.db.execute(
                f"UPDATE allocation_plan SET status='CANCELLED' WHERE id IN ({placeholders})",
                ids
            )
            logger.info(f"[Gate1] {lot_no} 초과 allocation {len(ids)}건 CANCELLED")
            return len(ids)
        except (_sq.OperationalError, OSError) as e:
            logger.warning(f"[Gate1] allocation CANCELLED 실패 {lot_no}: {e}")
            return 0

    # ── confirm_outbound 헬퍼 ──────────────────────────────────

    def _co_load_picked_tonbags(self, lot_no: str = None) -> list:
        """PICKED 상태 톤백 조회. lot_no 지정 시 해당 LOT만."""
        query = """SELECT id, lot_no, sub_lt, weight, tonbag_uid FROM inventory_tonbag
                   WHERE status = ?"""
        params = [STATUS_PICKED]
        if lot_no:
            query += " AND lot_no = ?"
            params.append(lot_no)
        return self.db.fetchall(query, tuple(params))

    def _co_guard_against_double_outbound(self, tonbags: list, result: dict) -> bool:
        """이중 출고 차단. 이미 sold_table에 존재하면 True(차단) 반환."""
        _tb_ids = [tb['id'] for tb in tonbags]
        if not _tb_ids:
            return False
        try:
            _ph = ','.join('?' * len(_tb_ids))
            _already_sold = self.db.fetchall(
                f"SELECT tonbag_id FROM sold_table WHERE tonbag_id IN ({_ph})",
                tuple(_tb_ids)
            )
            if _already_sold:
                _dup_ids = [str(r.get('tonbag_id') if isinstance(r, dict) else r[0])
                           for r in _already_sold]
                _f_msg = (
                    f"[DOUBLE_OUTBOUND_BLOCKED] 이미 출고된 톤백 {len(_dup_ids)}개 중복 확정 시도: "
                    f"tonbag_ids={', '.join(_dup_ids)} — 출고 확정 차단"
                )
                logger.error(_f_msg)
                result['errors'].append(_f_msg)
                return True
        except Exception as _fe:
            logger.error(f"[DOUBLE_OUTBOUND_CHECK] safety guard 실패 — 출고 차단: {_fe}")
            result['errors'].append(f"이중 출고 체크 실패: {_fe}")
            return True
        return False

    def _co_validate_customer_sale_ref(self, tonbags: list, result: dict) -> bool:
        """sale_ref/customer 혼재 검증. 혼재 시 True(차단) 반환."""
        _tb_ids = [tb['id'] for tb in tonbags]
        if not _tb_ids:
            return False
        _sale_ref_set = set()
        _customer_set = set()
        try:
            _ph = ','.join('?' * len(_tb_ids))
            _plans = self.db.fetchall(
                f"SELECT tonbag_id, sale_ref, customer FROM allocation_plan "
                f"WHERE tonbag_id IN ({_ph}) "
                f"GROUP BY tonbag_id HAVING id = MAX(id)",
                tuple(_tb_ids)
            )
            for _plan in (_plans or []):
                _sr = str(_plan.get('sale_ref') or '').strip()
                _cu_raw = str(_plan.get('customer') or '').strip()
                try:
                    _cu = normalize_customer(_cu_raw)
                except Exception:
                    _cu = _cu_raw
                if _sr: _sale_ref_set.add(_sr)
                if _cu: _customer_set.add(_cu)
        except Exception as _h2e:
            logger.debug(f"[CO_VALIDATE] sale_ref/customer 혼재체크 스킵: {_h2e}")

        if len(_customer_set) > 1:
            _warn = (f"[CONFIRM_WARN] PICKED 톤백에 복수 고객 혼재: "
                     f"{', '.join(sorted(_customer_set))} — 출고 확정을 중단합니다.")
            logger.warning(_warn)
            result['errors'].append(_warn)
            return True
        if len(_sale_ref_set) > 1:
            _warn = (f"[CONFIRM_WARN] PICKED 톤백에 복수 sale_ref 혼재: "
                     f"{', '.join(sorted(_sale_ref_set))} — 출고 확정을 중단합니다.")
            logger.warning(_warn)
            result['errors'].append(_warn)
            return True
        return False

    def _co_build_sold_row_payload(self, tb: dict, now: str) -> tuple:
        """sold_table INSERT용 페이로드 구성. (columns, values) 반환."""
        tb_id = tb['id']
        uid_val = (tb.get('tonbag_uid') or '').strip() or ''
        if not uid_val:
            uid_val = str(tb.get('sub_lt') or tb_id)

        # picking_id 조회
        try:
            pick_row = self.db.fetchone(
                "SELECT id FROM picking_table WHERE tonbag_id = ? ORDER BY id DESC LIMIT 1",
                (tb_id,)
            )
            picking_id = pick_row['id'] if pick_row else None
        except sqlite3.OperationalError:
            picking_id = None

        # inventory 정보
        _inv_row = self.db.fetchone(
            "SELECT sap_no, bl_no, product_code, product, gross_weight, net_weight, "
            "mxbg_pallet, sold_to, sale_ref FROM inventory WHERE lot_no = ?",
            (tb['lot_no'],)
        )
        _inv = dict(_inv_row) if _inv_row else {}

        # picking_table 정보
        _pick_info = self.db.fetchone(
            "SELECT sales_order_no, picking_no, customer, outbound_id FROM picking_table "
            "WHERE tonbag_id = ? ORDER BY id DESC LIMIT 1",
            (tb_id,)
        )
        _pi = dict(_pick_info) if _pick_info else {}

        # allocation_plan 정보 (fallback)
        _alloc_info = self.db.fetchone(
            "SELECT customer, sale_ref FROM allocation_plan "
            "WHERE tonbag_id = ? ORDER BY id DESC LIMIT 1",
            (tb_id,)
        )
        _al = dict(_alloc_info) if _alloc_info else {}

        # GW 계산
        _is_sample = tb.get('is_sample', 0) or (1 if tb.get('sub_lt', -1) == 0 else 0)
        _tb_gw_kg = 0.0
        if _is_sample:
            _tb_gw_kg = (tb.get('weight') or 0) * 1.025
        elif _inv.get('mxbg_pallet') and _inv.get('gross_weight'):
            _tb_gw_kg = float(_inv['gross_weight']) / int(_inv['mxbg_pallet'])

        _customer = (_pi.get('customer') or _al.get('customer')
                    or _inv.get('sold_to') or '')
        _sold_qty_kg = tb.get('weight') or 0
        _sold_qty_mt = round(_sold_qty_kg / 1000.0, 6) if _sold_qty_kg else 0
        _sku = _inv.get('product_code') or ''
        if _is_sample and _sku and 'Sample' not in _sku:
            _sku = f"{_sku} Sample"

        return (
            tb['lot_no'], tb_id, tb.get('sub_lt', 0), uid_val, picking_id,
            _sold_qty_kg, _sold_qty_mt, _tb_gw_kg, now,
            _inv.get('sap_no', ''), _inv.get('bl_no', ''),
            _customer, _sku,
            _pi.get('sales_order_no', ''), _pi.get('picking_no', ''),
            now[:10],
            1 if not _is_sample else 1,
            1 if _is_sample else 0
        )

    def _co_insert_sold_row(self, tb: dict, now: str):
        """sold_table에 출고 이력 1건 INSERT."""
        try:
            values = self._co_build_sold_row_payload(tb, now)
            self.db.execute(
                """INSERT INTO sold_table
                (lot_no, tonbag_id, sub_lt, tonbag_uid, picking_id,
                 sold_qty_kg, sold_qty_mt, gross_weight_kg, sold_date, status, created_by,
                 sap_no, bl_no, customer, sku, sales_order_no, picking_no,
                 delivery_date, ct_plt, is_sample)
                VALUES (?, ?, ?, ?, ?,
                        ?, ?, ?, ?, 'OUTBOUND', 'system',
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?)""",
                values
            )
        except sqlite3.OperationalError as e:
            # NOTE: sold_table 미존재 시 무시, 그 외는 로깅
            if "no such table" not in str(e).lower():
                logger.warning(
                    f"[CO_INSERT_SOLD] sold_table 기록 실패: tonbag_id={tb['id']}, "
                    f"lot_no={tb.get('lot_no')}, error={e}"
                )

    def _co_insert_outbound_movement(self, tb: dict, now: str):
        """stock_movement에 OUTBOUND 이력 INSERT."""
        self.db.execute(
            "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
            "VALUES (?, 'OUTBOUND', ?, ?, ?)",
            (tb['lot_no'], tb.get('weight', 0),
             f"confirm_outbound, sub_lt={tb.get('sub_lt', 0)}", now))

    def _co_run_post_checks(self, touched_lots: set, result: dict):
        """출고 확정 후 LOT_TOTAL_MISMATCH + SAMPLE_POLICY 사후검증."""
        if not touched_lots:
            return
        try:
            _post_errors = []
            _inv_rows = self.db.fetchall(
                "SELECT lot_no, initial_weight, current_weight, picked_weight "
                "FROM inventory WHERE lot_no IN (%s)" %
                ','.join('?' * len(touched_lots)),
                tuple(touched_lots)
            )
            for _r in (_inv_rows or []):
                _iw = float(_r.get('initial_weight') or 0)
                _cw = float(_r.get('current_weight') or 0)
                _pw = float(_r.get('picked_weight') or 0)
                if abs(_iw - (_cw + _pw)) > 0.01:
                    _msg = (
                        f"[LOT_TOTAL_MISMATCH] {_r.get('lot_no')}: "
                        f"initial={_iw}kg ≠ current({_cw})+picked({_pw})={_cw+_pw}kg"
                    )
                    logger.error(_msg)
                    _post_errors.append(_msg)

            _sample_rows = self.db.fetchall(
                "SELECT lot_no, COUNT(*) AS cnt FROM inventory_tonbag "
                "WHERE is_sample=1 AND lot_no IN (%s) GROUP BY lot_no" %
                ','.join('?' * len(touched_lots)),
                tuple(touched_lots)
            )
            for _sr in (_sample_rows or []):
                _cnt = int(_sr.get('cnt') or 0)
                if _cnt != 1:
                    _msg = (
                        f"[SAMPLE_POLICY_BROKEN] {_sr.get('lot_no')}: "
                        f"샘플 {_cnt}개 (정책: 1개)"
                    )
                    logger.error(_msg)
                    _post_errors.append(_msg)

            if _post_errors:
                result['post_check_errors'] = _post_errors
                result['message'] += f" ⚠ 사후검증 {len(_post_errors)}건 오류"
            else:
                logger.info("[POST_OUTBOUND] LOT_TOTAL + SAMPLE_POLICY 검증 통과")
        except Exception as _pe:
            logger.debug(f"[POST_OUTBOUND] 사후검증 스킵: {_pe}")

    # ── confirm_outbound 메인 ────────────────────────────────

    def confirm_outbound(self, lot_no: str = None, force_all: bool = False) -> Dict:
        """
        PICKED → OUTBOUND 확정 (SOLD는 레거시 호환 표현).

        Args:
            lot_no: 특정 LOT 지정. None이면 전체 (force_all=True 필수)
            force_all: lot_no=None 전체 확정 시 반드시 True로 명시

        Returns:
            {'success': bool, 'confirmed': int}
        """
        result = {'success': False, 'confirmed': 0, 'errors': []}

        # [H1] lot_no=None 전체 확정 — force_all=True 없으면 hard-stop
        if not lot_no and not force_all:
            _h1_msg = (
                "[CONFIRM_ALL_BLOCKED] lot_no 미지정 전체 확정은 "
                "force_all=True 명시 필수 — 실수 호출 차단"
            )
            logger.error(_h1_msg)
            result['errors'].append(_h1_msg)
            return result

        if not lot_no and force_all:
            logger.warning(
                "[CONFIRM_ALL_WARNING] lot_no 미지정 — 전체 PICKED 톤백 일괄 확정 모드 "
                "(force_all=True 명시 확인됨)"
            )
            result.setdefault('warnings', []).append("전체 PICKED 톤백 일괄 확정 모드")

        try:
            # 1) PICKED 톤백 로드
            tonbags = self._co_load_picked_tonbags(lot_no)
            if not tonbags:
                result['message'] = "확정할 톤백 없음"
                return result

            # 2) 이중 출고 차단
            if self._co_guard_against_double_outbound(tonbags, result):
                return result

            # 3) sale_ref/customer 혼재 검증
            if self._co_validate_customer_sale_ref(tonbags, result):
                return result

            # 4) 트랜잭션: 상태변경 + sold_table + movement + lot 재계산
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction("IMMEDIATE"):
                touched_lots = set()
                # 톤백 STATUS 일괄 OUTBOUND 전환
                _upd_rows = [
                    (STATUS_OUTBOUND, now, now, tb['id']) for tb in tonbags
                ]
                self.db.executemany(
                    "UPDATE inventory_tonbag SET status = ?, outbound_date = ?, updated_at = ? WHERE id = ?",
                    _upd_rows
                )
                for tb in tonbags:
                    self._co_insert_sold_row(tb, now)
                    self._co_insert_outbound_movement(tb, now)
                    result['confirmed'] += 1
                    if tb.get('lot_no'):
                        touched_lots.add(tb['lot_no'])
                for lot in touched_lots:
                    self._recalc_lot_status(lot)

            result['success'] = result['confirmed'] > 0
            result['message'] = f"출고 확정: {result['confirmed']}건 OUTBOUND"

            # 5) 출고 확정 후 touched_lots 전체 재계산
            for _ln in touched_lots:
                if hasattr(self, '_recalc_current_weight'):
                    self._recalc_current_weight(_ln, reason='P2_CONFIRM_OUTBOUND')

            # 6) 사후검증: LOT_TOTAL_MISMATCH + SAMPLE_POLICY
            self._co_run_post_checks(touched_lots, result)

        except (ValueError, TypeError, sqlite3.Error) as e:
            logger.error(f"출고 확정 오류: {e}")
            result['errors'].append(str(e))

        return result
