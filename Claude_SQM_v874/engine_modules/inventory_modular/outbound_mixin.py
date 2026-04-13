ALLOCATION_FORCE_APPROVAL_ALL = True

# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 출고 처리 Mixin (Thin Wrapper)
=====================================================

v8.7.4: 5개 서브모듈로 분리 후 통합 래퍼.
  - outbound_helpers.py          (GE) 헬퍼/유틸리티
  - outbound_allocation_service.py (GA) Allocation 배정
  - outbound_execution_service.py  (GB) 출고 실행
  - outbound_cleanup_service.py    (GC) 정리/정합성
  - outbound_reserved_service.py   (GD) 예약 실행/확정

잔여 메서드 (~8개): gate1_verify_picking, gate1_apply_picking_result,
  execute_from_picking, cancel_reservation, revert_picked_to_reserved,
  revert_sold_to_picked, quick_outbound, open_inbound_dialog_for_return

작성자: Ruby (남기동)
버전: v3.6.6 → v8.7.4
"""

import sqlite3
import logging
import os
import json
import uuid
from datetime import datetime
from typing import Dict

from engine_modules.constants import (
    STATUS_AVAILABLE,
    STATUS_RESERVED,
    STATUS_DEPLETED,
    STATUS_PICKED,
    STATUS_SOLD,         # ⚠️ DEPRECATED: 읽기 전용 하위호환
    STATUS_OUTBOUND,     # v7.2.0: 신규 출고 완료 상태
    STATUS_PARTIAL,      # v6.8.7 신규
)
from core.types import normalize_lot

# v6.8.6: 인라인 import → top-level 통합 (7곳 중복 제거)
from engine_modules.constants import (
    normalize_customer,
    get_tonbag_unit_weight,
    QUICK_OUTBOUND_MAX_TONBAGS,
)

from .base import InventoryBaseMixin
from .outbound_state_rules import OutboundStateRules as _StateRules  # P2 Batch B
from .outbound_query import OutboundQueryRepository as _QueryRepo    # P2 Batch B
from .outbound_repository import OutboundWriteRepository as _WriteRepo  # P2 Batch B

# v8.7.4: 5개 서브모듈 Mixin import
from .outbound_helpers import OutboundHelpersMixin
from .outbound_allocation_service import OutboundAllocationMixin
from .outbound_execution_service import OutboundExecutionMixin
from .outbound_cleanup_service import OutboundCleanupMixin
from .outbound_reserved_service import OutboundReservedMixin

logger = logging.getLogger(__name__)


class OutboundMixin(
    OutboundHelpersMixin,
    OutboundAllocationMixin,
    OutboundExecutionMixin,
    OutboundCleanupMixin,
    OutboundReservedMixin,
    InventoryBaseMixin,
):
    """출고 처리 통합 Mixin — 5개 서브모듈 + 잔여 메서드."""

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

            # --- v6.9.1 [FIX-1]: Picking Qty > Available TONBAG 검증 ---
            # oversell 방지 핵심 검증
            avail_short = []
            for lot_no in sorted(picking_lots):
                pk = picking_qty.get(lot_no, {})
                pk_count = pk.get('tonbag_count', 0)
                if pk_count == 0:
                    continue
                avail_row = self.db.fetchone(
                    "SELECT COUNT(*) AS cnt FROM inventory_tonbag "
                    "WHERE lot_no=? AND status='AVAILABLE' AND COALESCE(is_sample,0)=0",
                    (lot_no,)
                )
                avail_cnt = int((avail_row.get('cnt') if isinstance(avail_row, dict)
                                 else (avail_row[0] if avail_row else 0)) or 0)
                if pk_count > avail_cnt:
                    avail_short.append(
                        f"LOT {lot_no}: 피킹요청 {pk_count}개 > AVAILABLE {avail_cnt}개 "
                        f"(oversell 위험)"
                    )
            result['avail_short'] = avail_short

            # --- v6.9.1 [FIX-2]: only_in_picking HARD-STOP 강화 ---
            # RESERVED 없는 LOT가 피킹에 있으면 requires_approval 없이 즉시 차단

            qty_mismatches = []
            lot_details = []
            for lot_no in sorted(matched):
                # DB에서 RESERVED 톤백 수/총 무게 조회
                # v6.9.6 [PK-10-FIX]: LOT 모드(tonbag_id=NULL) JOIN 버그 수정
                # 기존: JOIN inventory_tonbag → tonbag_id=NULL 시 항상 0,0 반환
                # 수정: tonbag_id NULL 여부 분기 → LOT 모드는 qty_mt 합산으로 계산
                _lot_mode_chk = self.db.fetchone(
                    "SELECT COUNT(*) AS cnt FROM allocation_plan "
                    "WHERE lot_no=? AND status='RESERVED' AND tonbag_id IS NULL",
                    (lot_no,)
                )
                _is_lot_mode = int(_lot_mode_chk.get('cnt', 0) if _lot_mode_chk else 0) > 0

                if _is_lot_mode:
                    # LOT 모드: qty_mt 직접 합산 (v8.6.0: COUNT*500 하드코딩 제거)
                    # → SUM(qty_mt*1000)으로 500/1000kg 톤백 모두 정확히 처리
                    db_row = self.db.fetchone(
                        """SELECT COUNT(*) AS plan_count,
                                  COALESCE(SUM(CASE WHEN qty_mt >= 0.01 THEN qty_mt * 1000 ELSE 0 END), 0) AS total_kg
                           FROM allocation_plan
                           WHERE lot_no = ? AND status = 'RESERVED'""",
                        (lot_no,)
                    )
                    db_count = db_row['plan_count'] if db_row else 0
                    db_kg = float(db_row['total_kg']) if db_row else 0
                else:
                    # TONBAG 모드 (구버전 호환): inventory_tonbag JOIN
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
            if only_in_picking:
                # v6.9.1 [FIX-2]: RESERVED 없는 LOT → 즉시 HARD-STOP (승인 불가)
                result['passed'] = False
                result['requires_approval'] = False
                result['fail_code'] = 'LOT_NOT_RESERVED'
                lines.append(f'🚫 Gate-1 HARD-STOP — RESERVED 없는 LOT {len(only_in_picking)}개')
                lines.append('   allocation_plan 확인 후 재시도하세요')
            elif avail_short:
                # v6.9.1 [FIX-1]: AVAILABLE 부족 → HARD-STOP
                result['passed'] = False
                result['requires_approval'] = False
                result['fail_code'] = 'AVAIL_INSUFFICIENT'
                lines.append(f'🚫 Gate-1 HARD-STOP — AVAILABLE 부족 (oversell 위험) {len(avail_short)}건')
                for s in avail_short[:5]:
                    lines.append(f'   - {s}')
            elif qty_mismatches:
                # v6.9.6 [PK-10 AUTO-REPAIR]: Picking < RESERVED → 초과 예약 자동 CANCELLED
                # Picking > RESERVED → HARD STOP (과피킹)
                auto_repaired = []
                hard_stop_lots = []
                for d in lot_details:
                    if not d['kg_match']:
                        pk_kg = d['picking_kg']
                        db_kg = d['reserved_kg']
                        lot_no_d = d['lot_no']
                        if pk_kg < db_kg:
                            # Picking < RESERVED → 초과분 allocation_plan CANCELLED
                            # 초과 건수 계산 (MT 기준 역산)
                            _excess_kg = db_kg - pk_kg
                            _unit_mt = self.db.fetchone(
                                "SELECT qty_mt FROM allocation_plan "
                                "WHERE lot_no=? AND status='RESERVED' "
                                "ORDER BY id DESC LIMIT 1",
                                (lot_no_d,)
                            )
                            _unit = float(_unit_mt.get('qty_mt', 0.5)) if _unit_mt else 0.5
                            _cancel_count = max(1, round(_excess_kg / (_unit * 1000)))
                            # 초과 plan CANCELLED (최신 순)
                            _excess_plans = self.db.fetchall(
                                "SELECT id FROM allocation_plan "
                                "WHERE lot_no=? AND status='RESERVED' "
                                "ORDER BY id DESC LIMIT ?",
                                (lot_no_d, _cancel_count)
                            )
                            for _ep in _excess_plans:
                                try:
                                    from datetime import datetime as _dt
                                    self.db.execute(
                                        "UPDATE allocation_plan "
                                        "SET status='CANCELLED', "
                                        "cancelled_at=? "
                                        "WHERE id=?",
                                        (_dt.now().strftime('%Y-%m-%d %H:%M:%S'), _ep['id'])
                                    )
                                except Exception as _ce:
                                    logger.warning(f"[PK-10 AUTO-REPAIR] CANCEL 실패: {_ce}")
                            auto_repaired.append(
                                f"LOT {lot_no_d}: 피킹 {pk_kg:,.0f}kg < RESERVED {db_kg:,.0f}kg "
                                f"→ 초과 {_cancel_count}건 자동 취소"
                            )
                            logger.info(
                                f"[PK-10 AUTO-REPAIR] {lot_no_d}: "
                                f"초과예약 {_cancel_count}건 CANCELLED "
                                f"(picking={pk_kg:.0f}kg < reserved={db_kg:.0f}kg)"
                            )
                        elif pk_kg > db_kg:
                            # Picking > RESERVED → HARD STOP
                            hard_stop_lots.append(
                                f"LOT {lot_no_d}: 피킹 {pk_kg:,.0f}kg > RESERVED {db_kg:,.0f}kg "
                                f"(과피킹 — 추가 Allocation 필요)"
                            )

                if hard_stop_lots:
                    result['passed'] = False
                    result['requires_approval'] = False
                    result['fail_code'] = 'OVER_PICKING'
                    lines.append(f'🚫 Gate-1 HARD-STOP — 과피킹 {len(hard_stop_lots)}건 (RESERVED 초과)')
                    for h in hard_stop_lots[:5]:
                        lines.append(f'   - {h}')
                    result['auto_repaired'] = auto_repaired
                elif auto_repaired:
                    lines.append(f'🔧 Gate-1 AUTO-REPAIR — 초과 예약 {len(auto_repaired)}건 자동 취소')
                    for ar in auto_repaired[:5]:
                        lines.append(f'   ✅ {ar}')
                    result['passed'] = True
                    result['auto_repaired'] = auto_repaired
                    result['fail_code'] = ''
                else:
                    lines.append('⚠️ Gate-1 승인 필요 — LOT 매칭 OK, 수량 불일치 있음')
                    lines.append('   관리자 승인 후 진행할 수 있습니다')
                    result['passed'] = False
                    result['requires_approval'] = True
                    result['fail_code'] = 'QTY_MISMATCH'
            else:
                lines.append('✅ Gate-1 완전 통과 — LOT 매칭 + 수량 검증 모두 OK')
                result['passed'] = True

            lines.append('=' * 60)
            result['error_report'] = '\n'.join(lines)
            logger.info('[Gate-1] passed=%s, matched=%s, missing=%s, qty_mismatch=%s',
                        result['passed'], len(matched), len(only_in_picking), len(qty_mismatches))
        except (sqlite3.Error, AttributeError) as e:
            result['error_report'] = f'Gate-1 DB 오류: {e}'
            logger.error(f'[Gate-1] 오류: {e}', exc_info=True)
        return result

    @staticmethod
    # DEAD CODE REMOVED v8.6.4: _gate1_to_json()
    # 사유: 전체 코드베이스에서 호출 없음 (2026-03-28 감사)
    # 원본 15줄 제거

    def gate1_apply_picking_result(
        self,
        sale_ref: str,
        picking_result,
        picking_no: str = '',
        sales_order: str = '',
        allow_qty_mismatch: bool = False,
        approval_reason: str = '',
    ) -> dict:
        """Gate-1 결과를 저장하고 STEP4 스캔 대기 상태로만 전환한다.
        STEP3에서는 inventory_tonbag.status를 변경하지 않는다.
        """
        result = {'success': False, 'executed': 0, 'gate1': {}, 'errors': []}
        gate1 = self.gate1_verify_picking(picking_result, picking_no)
        result['gate1'] = gate1
        if gate1.get('requires_approval') and not allow_qty_mismatch:
            result['errors'].append('Gate-1 승인 필요: 수량 불일치(QTY_MISMATCH)')
            return result
        if not gate1.get('passed'):
            if gate1.get('requires_approval') and allow_qty_mismatch:
                pass
            else:
                result['errors'].append(gate1.get('error_report', 'Gate-1 실패'))
                return result
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            cols = {str(r.get('name','')).strip().lower() for r in (self.db.fetchall('PRAGMA table_info(allocation_plan)') or [])}
            has_process_state = 'process_state' in cols
            has_gate1_checked_at = 'gate1_checked_at' in cols
            has_gate1_json_path = 'gate1_json_path' in cols
            has_gate1_report_path = 'gate1_report_path' in cols
            has_gate1_requires_approval = 'gate1_requires_approval' in cols
            has_gate1_approved_by = 'gate1_approved_by' in cols
            has_qc_status = 'qc_status' in cols
            has_qc_reason = 'qc_reason' in cols
            gate1_json_path = ''
            gate1_report_path = ''
            try:
                gate1_json_path = self._save_gate1_result_json(gate1, picking_no) if hasattr(self, '_save_gate1_result_json') else ''
            except Exception:
                gate1_json_path = ''
            try:
                gate1_report_path = self._save_gate1_report(gate1, picking_no) if hasattr(self, '_save_gate1_report') else ''
            except Exception:
                gate1_report_path = ''
            with self.db.transaction('IMMEDIATE'):
                if gate1.get('requires_approval') and allow_qty_mismatch:
                    try:
                        self.db.execute(
                            "INSERT INTO audit_log(event_type, event_data, created_at) VALUES (?, ?, ?)",
                            ('OUTBOUND_QTY_MISMATCH_APPROVED', json.dumps({
                                'picking_no': picking_no, 'sales_order': sales_order,
                                'fail_code': gate1.get('fail_code', 'QTY_MISMATCH'),
                                'approval_reason': approval_reason or ''
                            }, ensure_ascii=False), now),
                        )
                    except Exception:
                        logger.debug("[SUPPRESSED] exception in outbound_mixin.py")  # noqa
                matched_lots = list(gate1.get('matched_lots', []))
                # [M] v6.8.4: matched_lots 빈값 → 명시적 오류
                if not matched_lots:
                    _m_err = (
                        "[GATE1_NO_MATCH] Gate-1 통과했으나 매칭 LOT 없음 "
                        "— 피킹리스트 LOT 번호 확인"
                    )
                    logger.error(_m_err)
                    result['errors'].append(_m_err)
                    return result
                for lot_no in matched_lots:
                    sets = []
                    vals = []
                    if has_process_state:
                        sets.append("process_state = ?")
                        vals.append('GATE1_PASSED')
                    if has_gate1_checked_at:
                        sets.append("gate1_checked_at = ?")
                        vals.append(now)
                    if has_gate1_json_path:
                        sets.append("gate1_json_path = ?")
                        vals.append(gate1_json_path)
                    if has_gate1_report_path:
                        sets.append("gate1_report_path = ?")
                        vals.append(gate1_report_path)
                    if has_gate1_requires_approval:
                        sets.append("gate1_requires_approval = ?")
                        vals.append(1 if gate1.get('requires_approval') else 0)
                    if has_gate1_approved_by:
                        sets.append("gate1_approved_by = ?")
                        vals.append((os.environ.get('USERNAME', '') or os.environ.get('USER', '') or 'system') if allow_qty_mismatch else '')
                    if has_qc_status:
                        sets.append("qc_status = ?")
                        vals.append('OK' if gate1.get('passed') else 'WARN')
                    if has_qc_reason:
                        sets.append("qc_reason = ?")
                        vals.append(gate1.get('fail_code', '') or '')
                    if sets:
                        vals.extend([lot_no, 'RESERVED'])
                        self.db.execute(
                            f"UPDATE allocation_plan SET {', '.join(sets)} WHERE lot_no = ? AND status = ?",
                            tuple(vals),
                        )
                # ── v6.9.2 [FIX-5]: 부분 출고 — 초과 RESERVED 톤백 AVAILABLE 복귀 ──
                # 예) Alloc=10, Pick=8 → 2개를 allocation_plan 취소 + tonbag AVAILABLE 복귀
                reverted_total = 0
                for d in gate1.get('lot_details', []):
                    lot = d.get('lot_no', '')
                    pk_cnt = int(d.get('picking_count') or 0)
                    rv_cnt = int(d.get('reserved_count') or 0)
                    if lot and pk_cnt > 0 and rv_cnt > pk_cnt:
                        excess = rv_cnt - pk_cnt
                        # FIFO 기준 초과분 allocation_plan 조회 (created_at 내림차순 = 최신 것부터 취소)
                        excess_plans = self.db.fetchall(
                            """SELECT ap.id, ap.tonbag_id
                               FROM allocation_plan ap
                               JOIN inventory_tonbag tb ON tb.id = ap.tonbag_id
                               WHERE ap.lot_no = ? AND ap.status = 'RESERVED'
                               ORDER BY tb.sub_lt DESC
                               LIMIT ?""",
                            (lot, excess)
                        )
                        for ep in (excess_plans or []):
                            try:
                                self.db.execute(
                                    "UPDATE allocation_plan SET status='CANCELLED', "
                                    "cancelled_at=? WHERE id=?",
                                    (now, ep['id'])
                                )
                                self.db.execute(
                                    "UPDATE inventory_tonbag SET status='AVAILABLE', "
                                    "updated_at=? WHERE id=?",
                                    (now, ep['tonbag_id'])
                                )
                                reverted_total += 1
                            except Exception as _rv_e:
                                logger.warning(f"[v6.9.2] 초과 RESERVED 복귀 실패 {ep}: {_rv_e}")
                        if reverted_total:
                            self._recalc_lot_status(lot)
                            logger.info(
                                f"[v6.9.2] 부분 출고 복귀: LOT {lot} "
                                f"RESERVED {rv_cnt}개 중 {excess}개 → AVAILABLE"
                            )

                result['reverted_to_available'] = reverted_total
                result['success'] = len(matched_lots) > 0
                result['executed'] = len(matched_lots)
                result['json_path'] = gate1_json_path
                result['report_path'] = gate1_report_path
                result['message'] = (
                    f'Gate-1 검증 완료: {len(matched_lots)}개 LOT / STEP4 스캔 대기'
                    + (f' / 초과 예약 {reverted_total}개 → AVAILABLE 복귀' if reverted_total else '')
                )
        except Exception as e:
            logger.error(f'[gate1_apply_picking_result] 오류: {e}', exc_info=True)
            result['errors'].append(str(e))
        return result

    def execute_from_picking(
        self,
        picking_result,
        picking_no: str = '',
        sales_order: str = '',
        allow_qty_mismatch: bool = False,
        approval_reason: str = '',
    ) -> dict:
        """하위 호환용 래퍼. STEP3에서는 Gate-1 결과 저장만 수행한다."""
        return self.gate1_apply_picking_result(
            sale_ref=sales_order or picking_no,
            picking_result=picking_result,
            picking_no=picking_no,
            sales_order=sales_order,
            allow_qty_mismatch=allow_qty_mismatch,
            approval_reason=approval_reason,
        )

    def cancel_reservation(
        self,
        lot_no: str = None,
        plan_id: int = None,
        plan_ids: list = None,
        sale_ref: str = None,   # v7.7.1: sale_ref 일괄 취소 지원
        include_picked: bool = False,   # v8.6.5: PICKED 상태도 취소
        include_outbound: bool = False,  # v8.6.5: OUTBOUND 상태도 취소
    ) -> Dict:
        """
        RESERVED 예약 취소 → AVAILABLE 복원.
        plan_ids: 여러 건 일괄 취소 시 [id, ...] 전달.
        sale_ref: 판매참조번호 기준 일괄 취소 (v7.7.1).
        include_picked: True면 PICKED/EXECUTED 상태도 취소 (v8.6.5).
        include_outbound: True면 OUTBOUND/SOLD 상태도 취소 (v8.6.5).

        Returns:
            {'success': bool, 'cancelled': int}
        """
        result = {'success': False, 'cancelled': 0, 'errors': []}

        # v6.9.3 [CR-FIX-1]: plan_ids=[] HARD-STOP
        # 빈 리스트 전달 시 조건 없이 전체 취소되는 위험 차단
        if plan_ids is not None:
            if not isinstance(plan_ids, (list, tuple)) or len(plan_ids) == 0:
                result['message'] = "취소할 배정(plan_ids)이 비어 있습니다."
                result['errors'].append("[EMPTY_PLAN_IDS] plan_ids=[] — 취소 대상 없음 (HARD-STOP)")
                return result

        # v6.9.3 [CR-FIX-1]: 모든 파라미터 None → 실수 전체 취소 방지
        if plan_ids is None and plan_id is None and lot_no is None and not sale_ref:
            result['message'] = "취소할 예약 없음"
            result['errors'].append("[NO_CANCEL_TARGET] lot_no/plan_id/plan_ids/sale_ref 중 하나는 반드시 지정 필요")
            return result

        # v8.6.5: 취소 대상 상태 범위 확장
        cancel_statuses = ['RESERVED', 'PENDING_APPROVAL', 'STAGED']
        if include_picked:
            cancel_statuses.extend(['PICKED', 'EXECUTED'])
        if include_outbound:
            cancel_statuses.extend(['OUTBOUND', 'SOLD', 'SHIPPED', 'CONFIRMED'])
        status_ph = ','.join('?' * len(cancel_statuses))
        query = f"SELECT id, lot_no, tonbag_id, status FROM allocation_plan WHERE status IN ({status_ph})"
        params = list(cancel_statuses)
        if plan_ids:
            query += " AND id IN (" + ",".join("?" * len(plan_ids)) + ")"
            params.extend(plan_ids)
        else:
            if lot_no:
                query += " AND lot_no = ?"
                params.append(lot_no)
            if plan_id is not None:
                query += " AND id = ?"
                params.append(plan_id)
            # v7.7.1: sale_ref 기준 일괄 취소
            if sale_ref:
                query += " AND sale_ref = ?"
                params.append(str(sale_ref).strip())

        try:
            plans = self.db.fetchall(query, tuple(params))
            if not plans:
                result['message'] = "취소할 예약 없음"
                return result

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # v8.6.5: 상태 흐름 역방향 매핑 (직전 상태로 복원)
            # AVAILABLE → RESERVED → PICKED → OUTBOUND
            _PREV_STATUS_TONBAG = {
                'RESERVED': STATUS_AVAILABLE,
                'PENDING_APPROVAL': STATUS_AVAILABLE,
                'STAGED': STATUS_AVAILABLE,
                'PICKED': 'RESERVED',
                'EXECUTED': 'RESERVED',
                'OUTBOUND': STATUS_PICKED,
                'SOLD': STATUS_PICKED,
                'SHIPPED': STATUS_PICKED,
                'CONFIRMED': STATUS_PICKED,
            }
            _PREV_STATUS_PLAN = {
                'RESERVED': 'CANCELLED',
                'PENDING_APPROVAL': 'CANCELLED',
                'STAGED': 'CANCELLED',
                'PICKED': 'RESERVED',
                'EXECUTED': 'RESERVED',
                'OUTBOUND': 'EXECUTED',
                'SOLD': 'EXECUTED',
                'SHIPPED': 'EXECUTED',
                'CONFIRMED': 'EXECUTED',
            }

            with self.db.transaction("IMMEDIATE"):
                touched_lots = set()
                for plan in plans:
                    _tb_id = plan.get('tonbag_id') if isinstance(plan, dict) else plan[2]
                    _plan_id = plan.get('id') if isinstance(plan, dict) else plan[0]
                    _lot = plan.get('lot_no', '') if isinstance(plan, dict) else plan[1]
                    _cur_status = plan.get('status', 'RESERVED') if isinstance(plan, dict) else plan[3]

                    # 직전 상태 결정
                    _prev_tb = _PREV_STATUS_TONBAG.get(_cur_status, STATUS_AVAILABLE)
                    _prev_plan = _PREV_STATUS_PLAN.get(_cur_status, 'CANCELLED')

                    # 톤백 상태 → 직전 단계로 복원
                    if _tb_id:
                        if _prev_tb == STATUS_AVAILABLE:
                            # RESERVED → AVAILABLE: sale_ref/picked_to 초기화
                            self.db.execute(
                                """UPDATE inventory_tonbag SET
                                    status = ?, picked_to = NULL, sale_ref = NULL, updated_at = ?
                                WHERE id = ?""",
                                (_prev_tb, now, _tb_id))
                        elif _prev_tb == 'RESERVED':
                            # PICKED → RESERVED: outbound_date 초기화, picked_to 유지
                            self.db.execute(
                                """UPDATE inventory_tonbag SET
                                    status = ?, outbound_date = NULL, updated_at = ?
                                WHERE id = ?""",
                                (_prev_tb, now, _tb_id))
                        elif _prev_tb == STATUS_PICKED:
                            # OUTBOUND → PICKED: outbound_date 초기화
                            self.db.execute(
                                """UPDATE inventory_tonbag SET
                                    status = ?, outbound_date = NULL, updated_at = ?
                                WHERE id = ?""",
                                (_prev_tb, now, _tb_id))
                    else:
                        # LOT 모드: lot_no 기준 톤백 → 직전 상태
                        if _lot:
                            if _prev_tb == STATUS_AVAILABLE:
                                self.db.execute(
                                    """UPDATE inventory_tonbag SET
                                        status = ?, picked_to = NULL, sale_ref = NULL, updated_at = ?
                                    WHERE lot_no = ? AND status = ?""",
                                    (_prev_tb, now, _lot, _cur_status))
                            else:
                                self.db.execute(
                                    """UPDATE inventory_tonbag SET
                                        status = ?, outbound_date = NULL, updated_at = ?
                                    WHERE lot_no = ? AND status = ?""",
                                    (_prev_tb, now, _lot, _cur_status))

                    # OUTBOUND/SOLD → PICKED 복원 시: sold_table RETURNED 처리
                    if _cur_status in ('OUTBOUND', 'SOLD', 'SHIPPED', 'CONFIRMED') and _lot:
                        self.db.execute(
                            "UPDATE sold_table SET status='RETURNED' "
                            "WHERE lot_no=? AND status IN ('OUTBOUND','SOLD')",
                            (_lot,))

                    # allocation_plan → 직전 상태로 복원
                    self.db.execute(
                        """UPDATE allocation_plan SET status = ?, cancelled_at = ?
                        WHERE id = ?""",
                        (_prev_plan, now, _plan_id))
                    result['cancelled'] += 1

                    # stock_movement 이력
                    _mv_type = f"REVERT_{_cur_status}_TO_{_prev_tb}"
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, ?, 0, ?, ?)",
                        (_lot, _mv_type, f"plan_id={_plan_id} {_cur_status}→{_prev_plan}", now))
                    if _lot:
                        touched_lots.add(_lot)
                for lot_no in touched_lots:
                    self._recalc_lot_status(lot_no)
                    # v8.0.3 [P2]: RESERVED→AVAILABLE 후 current_weight 재계산
                    if hasattr(self, '_recalc_current_weight'):
                        self._recalc_current_weight(lot_no, reason='P2_CANCEL_RESERVATION')

            # v9.0 [AUDIT]: 수동 예약 취소 audit_log 기록
            if result.get('cancelled', 0) > 0:
                try:
                    import json as _json
                    self.db.execute(
                        "INSERT INTO audit_log(event_type, event_data, created_at) VALUES (?, ?, ?)",
                        (
                            'CANCEL_RESERVATION',
                            _json.dumps({
                                'cancelled': result['cancelled'],
                                'lot_no': lot_no,
                                'plan_id': plan_id,
                                'plan_ids': plan_ids,
                                'sale_ref': sale_ref,
                            }, ensure_ascii=False),
                            now
                        )
                    )
                    logger.debug("[cancel_reservation] audit_log 기록 완료: %d건", result['cancelled'])
                except Exception as _ae:
                    logger.debug("[cancel_reservation] audit_log 기록 실패(무시): %s", _ae)

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
                    tb_weight_row = self.db.fetchone(
                        "SELECT weight FROM inventory_tonbag WHERE id = ?", (r['tonbag_id'],)
                    )
                    _tb_w = float((tb_weight_row.get('weight') if isinstance(tb_weight_row, dict) else (tb_weight_row[0] if tb_weight_row else 0)) or 0)

                    self.db.execute(
                        """UPDATE allocation_plan SET status = 'RESERVED', executed_at = NULL WHERE id = ?""",
                        (r['id'],)
                    )
                    self.db.execute(
                        """UPDATE inventory_tonbag SET status = ?, picked_date = NULL, updated_at = ?
                           WHERE id = ?""",
                        (STATUS_RESERVED, now, r['tonbag_id'])
                    )
                    # v6.9.0 [C3]: current_weight 복구 — PICKED 전환 시 차감했던 무게 복원
                    if _tb_w > 0 and r.get('lot_no'):
                        self.db.execute(
                            """UPDATE inventory
                               SET current_weight = current_weight + ?,
                                   picked_weight  = MAX(0, picked_weight - ?),
                                   updated_at     = ?
                               WHERE lot_no = ?""",
                            (_tb_w, _tb_w, now, r['lot_no'])
                        )
                    result['reverted'] += 1
                    # v6.12.1: stock_movement 'REVERT_PICKED' 이력
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'REVERT_PICKED', ?, ?, ?)",
                        (r['lot_no'], _tb_w, f"plan_id={r['id']}, PICKED→RESERVED", now))
                    if hasattr(self, '_recalc_current_weight'):
                        self._recalc_current_weight(r['lot_no'], reason='P2_REVERT_PICKED_TO_RESERVED')
                    self._recalc_lot_status(r['lot_no'])
            result['success'] = True
            result['message'] = f"판매화물 결정 취소: {result['reverted']}건 → 판매 배정(RESERVED)"
        except (sqlite3.Error, ValueError, TypeError) as e:
            logger.error(f"revert_picked_to_reserved 오류: {e}")
            result['errors'].append(str(e))
        return result

    def revert_sold_to_picked(self, lot_no: str = None) -> Dict:
        """
        출고 취소: SOLD → AVAILABLE 직접 복귀.
        ★ v6.8.5 설계 원칙: 출고 취소 후 바로 AVAILABLE 복귀
        (PICKED 경유 없음 — 재출고 시 Allocation 재업로드 또는 즉시 가용)
        sold_table 해당 행 삭제, allocation_plan EXECUTED → CANCELLED,
        inventory current_weight 복구.
        """
        result = {'success': False, 'reverted': 0, 'errors': []}
        query = """SELECT id, lot_no, weight FROM inventory_tonbag WHERE status IN (?, ?)"""
        params = [STATUS_OUTBOUND, STATUS_SOLD]
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
                    # ★ v6.8.5: SOLD → AVAILABLE 직접 복귀
                    # 출고 취소 후 PICKED를 거치지 않고 바로 가용 상태로
                    _tb_w = float(tb.get('weight') or 0)
                    self.db.execute(
                        """UPDATE inventory_tonbag
                           SET status = ?, outbound_date = NULL,
                               picked_date = NULL, updated_at = ?
                           WHERE id = ?""",
                        (STATUS_AVAILABLE, now, tb_id)
                    )
                    # sold_table 삭제
                    try:
                        self.db.execute("DELETE FROM sold_table WHERE tonbag_id = ?", (tb_id,))
                    except sqlite3.OperationalError:
                        logger.debug("[SUPPRESSED] exception in outbound_mixin.py")  # noqa
                    # allocation_plan EXECUTED → ALLOC_CANCELLED
                    # v6.9.0 [M2]: cancelled_at 컬럼 존재 여부 안전 처리
                    try:
                        try:
                            _alloc_cols = {str(r.get('name','')).lower()
                                           for r in (self.db.fetchall("PRAGMA table_info(allocation_plan)") or [])}
                        except Exception:
                            _alloc_cols = set()
                        if 'cancelled_at' in _alloc_cols:
                            self.db.execute(
                                """UPDATE allocation_plan
                                   SET status = 'CANCELLED',
                                       cancelled_at = ?
                                   WHERE tonbag_id = ?
                                     AND status = 'EXECUTED'""",
                                (now, tb_id)
                            )
                        else:
                            self.db.execute(
                                """UPDATE allocation_plan
                                   SET status = 'CANCELLED'
                                   WHERE tonbag_id = ?
                                     AND status = 'EXECUTED'""",
                                (tb_id,)
                            )
                        logger.debug(
                            f"[I] allocation_plan EXECUTED→ALLOC_CANCELLED: "
                            f"tonbag_id={tb_id}"
                        )
                    except Exception as _ie:
                        logger.warning(f"[I allocation_plan CANCEL] 실패 tonbag_id={tb_id}: {_ie}")
                    # inventory 무게 복구 — picked_weight 차감, current_weight 복원
                    if _tb_w > 0 and tb.get('lot_no'):
                        try:
                            self.db.execute(
                                """UPDATE inventory
                                   SET current_weight = current_weight + ?,
                                       picked_weight  = MAX(0, picked_weight - ?),
                                       updated_at     = ?
                                   WHERE lot_no = ?""",
                                (_tb_w, _tb_w, now, tb['lot_no'])
                            )
                        except Exception as _iw:
                            logger.warning(f"[I inventory 무게복구] 실패: {_iw}")
                    result['reverted'] += 1
                    # stock_movement 'REVERT_SOLD' 이력
                    self.db.execute(
                        "INSERT INTO stock_movement (lot_no, movement_type, qty_kg, remarks, created_at) "
                        "VALUES (?, 'REVERT_SOLD', ?, ?, ?)",
                        (tb.get('lot_no', ''), _tb_w,
                         f"tonbag_id={tb_id}, SOLD→AVAILABLE", now))
                    if tb.get('lot_no'):
                        touched_lots.add(tb['lot_no'])
                for lot in touched_lots:
                    self._recalc_lot_status(lot)
            result['success'] = True
            result['message'] = f"출고 취소: {result['reverted']}건 → 가용(AVAILABLE) 복귀"
            # v8.0.3 [P2]: revert 후 touched_lots 재계산
            for _ln in touched_lots:
                if hasattr(self, '_recalc_current_weight'):
                    self._recalc_current_weight(_ln, reason='P2_REVERT_SOLD_TO_PICKED')
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
# [v6.8.6 top-level import로 이동]         from engine_modules.constants import QUICK_OUTBOUND_MAX_TONBAGS
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

                # v8.0.0 [P2]: inventory 중앙 재계산 함수로 교체
                if hasattr(self, '_recalc_current_weight'):
                    self._recalc_current_weight(lot_no, reason='QUICK_OUTBOUND_PICK')
                else:
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

    # =========================================================================
    # v7.0.0: _preflight_alloc_cols — allocation_plan 테이블 컬럼 존재 검사
    # =========================================================================
    @staticmethod
    # DEAD CODE REMOVED v8.6.4: _rfa_build_error_detail()
    # 사유: 전체 코드베이스에서 호출 없음 (2026-03-28 감사)
    # 원본 31줄 제거

    # ── RETURN_AS_REINBOUND: 입고 다이얼로그 재활용 모드 ──────────────────────
    def open_inbound_dialog_for_return(
        self,
        outbound_id: str,
        lot_no: str,
        customer: str,
        return_reason: str = '반품',
        operator_id: str = 'SYSTEM',
    ) -> dict:
        """
        반품 처리 시 기존 입고 다이얼로그를 mode='return'으로 재활용.

        RETURN_AS_REINBOUND 정책:
          1. Rack Scan  → 새 위치 스캔 (입고 프로세스와 동일)
          2. Tonbag Scan → 톤백 UID 확인 (입고 프로세스와 동일)
          3. ReturnReinboundEngine.process() 호출

        Args:
            outbound_id:   원출고 ID
            lot_no:        반품 LOT 번호
            customer:      고객사 명
            return_reason: 반품 사유
            operator_id:   작업자 ID

        Returns:
            {'ok': bool, 'return_id': str, 'new_location': str, 'error': str}

        Note:
            [v7.0.0 완료] GUI 통합은 ReturnReinboundDialog 로 완성됨.
            - inventory_tab._return_from_context() → ReturnReinboundDialog 직접 호출
            - tonbag_tab._on_tonbag_return()       → ReturnReinboundDialog 직접 호출
            - OneStopInboundDialog mode='return' 분기는 불필요 (ReturnReinboundDialog로 대체)
            이 메서드는 GUI 없는 환경(테스트/CLI)용 엔진 직접 호출 경로로 유지됨.
        """
        # GUI 없는 환경(테스트/CLI)에서는 엔진 직접 호출
        try:
            from engine_modules.return_reinbound_engine import (
                ReturnReinboundEngine,
            )
            # new_location은 GUI에서 PDA 스캔으로 받아옴
            # 테스트 환경에서는 자동 생성
            new_location = getattr(self, '_test_return_location', 'B-01-01-01')

            engine = ReturnReinboundEngine(self.conn if hasattr(self, 'conn') else None)
            if engine.conn is None:
                return {'ok': False, 'error': 'DB 연결 없음'}

            result = engine.process(
                outbound_id=outbound_id,
                lot_no=lot_no,
                new_location=new_location,
                operator_id=operator_id,
                reason=return_reason,
            )
            return {
                'ok':          result.ok,
                'return_id':   result.return_id,
                'new_location': result.new_location,
                'error':       result.error,
            }
        except ImportError:
            return {'ok': False, 'error': 'ReturnReinboundEngine import 실패'}
