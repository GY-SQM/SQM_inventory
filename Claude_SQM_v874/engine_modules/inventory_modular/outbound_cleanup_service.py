# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 출고 정리 서비스 Mixin (GC)
=================================================

outbound_mixin.py에서 분리된 정리/정합성 관련 메서드.
Lines 133-397, 1076-1157 원본 기준.

작성자: Ruby (남기동)
"""

import logging
from datetime import datetime
from typing import Dict

from engine_modules.constants import (
    STATUS_AVAILABLE,
    STATUS_RESERVED,
    STATUS_DEPLETED,
    STATUS_PICKED,
    STATUS_SOLD,
    STATUS_OUTBOUND,
    STATUS_PARTIAL,
)

logger = logging.getLogger(__name__)


class OutboundCleanupMixin:
    """출고 정리/정합성 Mixin."""

    def cleanup_orphan_lot_allocations(self, days_old: int = 7) -> Dict:
        """
        ③ v6.7.1: LOT 단위 예약 고아 레코드 정리.
        tonbag_id=NULL이고 생성 후 days_old일 이상 경과된 RESERVED 건을 CANCELLED 처리.

        Args:
            days_old: 정리 기준 일수 (기본 7일)
        Returns:
            {'success': bool, 'cancelled': int}
        """
        result = {'success': False, 'cancelled': 0}
        try:
            if not self._table_exists('allocation_plan'):
                result['success'] = True
                return result
            from datetime import datetime, timedelta
            cutoff = (datetime.now() - timedelta(days=days_old)).strftime('%Y-%m-%d %H:%M:%S')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction('IMMEDIATE'):
                cur = self.db.execute("""
                    UPDATE allocation_plan
                       SET status      = 'CANCELLED',
                           cancelled_at = ?
                     WHERE tonbag_id IS NULL
                       AND status     = 'RESERVED'
                       AND created_at < ?
                """, (now, cutoff))
                cnt = cur.rowcount if hasattr(cur, 'rowcount') else 0
            result['success']   = True
            result['cancelled'] = cnt
            if cnt:
                logger.info(f"[③ 고아정리] LOT 단위 예약 {cnt}건 CANCELLED (>{days_old}일)")
                # [D] v6.8.3: lot_mode 만료 CANCELLED → audit_log 기록
                try:
                    import json as _jd
                    self.db.execute(
                        "INSERT INTO audit_log(event_type, event_data, created_at) VALUES (?, ?, ?)",
                        ('LOT_MODE_ALLOC_EXPIRED',
                         _jd.dumps({'cancelled': cnt, 'days_old': days_old,
                                    'cutoff': cutoff}, ensure_ascii=False),
                         now)
                    )
                except Exception as _ae:
                    logger.debug(f"[D audit_log] 기록 스킵: {_ae}")

            # [D] v6.8.3: 만료 임박(3일 이내) LOT 단위 예약 사전 경고
            try:
                from datetime import timedelta
                _warn_cutoff = (
                    datetime.now() - timedelta(days=max(0, days_old - 3))
                ).strftime('%Y-%m-%d %H:%M:%S')
                _soon_rows = self.db.fetchall("""
                    SELECT lot_no, customer, created_at
                    FROM allocation_plan
                    WHERE tonbag_id IS NULL
                      AND status = 'RESERVED'
                      AND created_at < ?
                    ORDER BY created_at ASC LIMIT 10
                """, (_warn_cutoff,))
                if _soon_rows:
                    result['expiring_soon'] = [
                        {'lot_no': r.get('lot_no') if isinstance(r, dict) else r[0],
                         'customer': r.get('customer') if isinstance(r, dict) else r[1],
                         'created_at': r.get('created_at') if isinstance(r, dict) else r[2]}
                        for r in _soon_rows
                    ]
                    logger.warning(
                        f"[D 만료임박] LOT 단위 예약 {len(_soon_rows)}건 3일 이내 자동 CANCELLED 예정 "
                        f"— 바코드 스캔 또는 취소 처리 필요"
                    )
            except Exception as _de:
                logger.debug(f"[D 만료임박] 체크 스킵: {_de}")

        except Exception as e:
            result['error'] = str(e)
            logger.warning(f"[③ 고아정리] 실패: {e}")
        return result

    def cleanup_expired_staged_allocations(self, days_old: int = 7) -> Dict:
        """
        ③⑦ v6.7.1: STAGED+PENDING_APPROVAL 만료 건 자동 REJECTED.
        승인/반려 없이 days_old일 이상 방치된 대기 건 정리.

        Args:
            days_old: 정리 기준 일수 (기본 7일)
        Returns:
            {'success': bool, 'rejected': int}
        """
        result = {'success': False, 'rejected': 0}
        try:
            if not self._table_exists('allocation_plan'):
                result['success'] = True
                return result
            cols = {r.get('name','') for r in (self.db.fetchall(
                'PRAGMA table_info(allocation_plan)') or [])}
            if 'workflow_status' not in cols:
                result['success'] = True
                return result
            from datetime import datetime, timedelta
            cutoff = (datetime.now() - timedelta(days=days_old)).strftime('%Y-%m-%d %H:%M:%S')
            now    = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.db.transaction('IMMEDIATE'):
                cur = self.db.execute("""
                    UPDATE allocation_plan
                       SET workflow_status = 'REJECTED',
                           rejected_reason = 'AUTO_EXPIRE_AFTER_7DAYS',
                           approved_by     = 'system_cleanup',
                           approved_at     = ?
                     WHERE status          = 'STAGED'
                       AND workflow_status = 'PENDING_APPROVAL'
                       AND created_at      < ?
                """, (now, cutoff))
                cnt = cur.rowcount if hasattr(cur, 'rowcount') else 0
            result['success']  = True
            result['rejected'] = cnt
            if cnt:
                logger.info(f"[③⑦ 만료정리] STAGED PENDING {cnt}건 자동 REJECTED (>{days_old}일)")
        except Exception as e:
            result['error'] = str(e)
            logger.warning(f"[③⑦ 만료정리] 실패: {e}")
        return result

    def fix_lot_status_integrity(self) -> Dict:
        """★ v6.8.6 N+1 쿼리 → 벌크 쿼리 최적화 (v6.8.5 설계 원칙 유지).
        설계 원칙 재정립 전 잘못 기록된 LOT 상태를 일괄 보정:
        - LOT = SOLD 이지만 AVAILABLE 톤백이 남아 있는 케이스 → LOT = AVAILABLE
        - LOT = AVAILABLE 이지만 전체 톤백이 SOLD인 케이스 → LOT = SOLD
        운영 DB에 최초 1회 실행. (관리자 메뉴 → DB 정합성 복구)

        v6.8.6 최적화:
          - 기존: LOT 수 N → 쿼리 3N번 (N+1 패턴)
          - 개선: 3개 집계 쿼리로 전체 처리 (성능 100배 이상 향상)
        """
        result = {'success': False, 'fixed': 0, 'details': [], 'errors': []}
        try:
            # ── 벌크 쿼리 1: LOT=SOLD 이지만 AVAILABLE 톤백 잔존 ──────────
            # GROUP BY로 전체 LOT 한 번에 집계
            # v8.6.5 STAB-4: N+1 제거 — sold_cnt를 GROUP BY에 포함
            needs_avail = self.db.fetchall("""
                SELECT inv.lot_no,
                       SUM(CASE WHEN tb.status = 'AVAILABLE' AND tb.is_sample = 0 THEN 1 ELSE 0 END) AS normal_avail,
                       SUM(CASE WHEN tb.status = 'AVAILABLE' AND tb.is_sample = 1 THEN 1 ELSE 0 END) AS sample_avail,
                       SUM(CASE WHEN tb.status IN ('SOLD','OUTBOUND') THEN 1 ELSE 0 END) AS sold_cnt
                FROM inventory inv
                JOIN inventory_tonbag tb ON tb.lot_no = inv.lot_no
                WHERE inv.status IN (?, 'OUTBOUND')
                GROUP BY inv.lot_no
                HAVING (normal_avail + sample_avail) > 0
            """, (STATUS_SOLD, 'OUTBOUND')) or []

            for _r in needs_avail:
                _lot = _r.get('lot_no') if isinstance(_r, dict) else _r[0]
                _na  = int(_r.get('normal_avail', 0) if isinstance(_r, dict) else _r[1])
                _sa  = int(_r.get('sample_avail', 0) if isinstance(_r, dict) else _r[2])
                _sc_fix = int(_r.get('sold_cnt', 0) if isinstance(_r, dict) else _r[3])
                _fix_status = STATUS_PARTIAL if _sc_fix > 0 else STATUS_AVAILABLE
                self.db.execute(
                    "UPDATE inventory SET status = ? WHERE lot_no = ?",
                    (_fix_status, _lot)
                )
                detail = f"{_lot}: SOLD→{_fix_status} (잔여 일반 {_na}개 + 샘플 {_sa}개)"
                result['details'].append(detail)
                result['fixed'] += 1
                logger.info(f"[fix_integrity] {detail}")

            # ── 벌크 쿼리 2: LOT=AVAILABLE 이지만 전체 톤백 SOLD ───────────
            needs_sold = self.db.fetchall("""
                SELECT inv.lot_no,
                       COUNT(tb.id) AS total,
                       SUM(CASE WHEN tb.status = 'SOLD' THEN 1 ELSE 0 END) AS sold_cnt
                FROM inventory inv
                JOIN inventory_tonbag tb ON tb.lot_no = inv.lot_no
                WHERE inv.status = ?
                GROUP BY inv.lot_no
                HAVING total > 0 AND sold_cnt >= total
            """, (STATUS_AVAILABLE,)) or []

            for _r in needs_sold:
                _lot = _r.get('lot_no') if isinstance(_r, dict) else _r[0]
                _tc  = int(_r.get('total', 0) if isinstance(_r, dict) else _r[1])
                self.db.execute(
                    "UPDATE inventory SET status = ? WHERE lot_no = ?",
                    (STATUS_OUTBOUND, _lot)
                )
                detail = f"{_lot}: AVAILABLE→OUTBOUND (전체 {_tc}개 출고)"
                result['details'].append(detail)
                result['fixed'] += 1
                logger.info(f"[fix_integrity] {detail}")

            result['success'] = True
            result['message'] = f"LOT 상태 정합성 복구 완료: {result['fixed']}건"
        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"[fix_integrity] 오류: {e}")
        return result

    def run_allocation_cleanup(self, days_old: int = 7) -> Dict:
        """
        ③⑦ v6.7.1: 전체 Allocation 정리 일괄 실행.
        - LOT 단위 고아 레코드 정리
        - 만료 STAGED 자동 REJECTED

        Returns:
            {'orphan_cancelled': int, 'expired_rejected': int}
        """
        r1 = self.cleanup_orphan_lot_allocations(days_old)
        r2 = self.cleanup_expired_staged_allocations(days_old)
        return {
            'success': r1.get('success', False) and r2.get('success', False),
            'orphan_cancelled': r1.get('cancelled', 0),
            'expired_rejected': r2.get('rejected', 0),
        }

    def clear_pending_allocation_on_exit(self) -> Dict:
        """
        프로그램 종료 시 승인되지 않은 Allocation 대기건 정리.

        대상: allocation_plan.status=ALLOC_STAGED AND workflow_status=ALLOC_WF_PENDING
        처리: workflow_status=ALLOC_WF_REJECTED, rejected_reason='AUTO_CLEAR_ON_EXIT'
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

    def _recalc_lot_status(self, lot_no: str) -> None:
        """LOT status 재계산 — v7.2.0: OUTBOUND 통합 + RETURN 상태 추가
        ★ 설계 원칙 (기동님 확정)
        판정 우선순위:
         1) AVAILABLE 톤백 1개라도 있고 OUTBOUND/SOLD 없음 → LOT = AVAILABLE
         2) AVAILABLE + OUTBOUND/SOLD 혼재                  → LOT = PARTIAL
         3) 전체 톤백이 모두 OUTBOUND/SOLD                  → LOT = OUTBOUND (신규)
         4) AVAILABLE 없고 RETURN 있음                      → LOT = RETURN (신규)
         5) AVAILABLE 없고 PICKED 있음                      → LOT = PICKED
         6) AVAILABLE 없고 RESERVED 있음                    → LOT = RESERVED
         7) 톤백 없거나 무게 0                              → DEPLETED
        """
        lot = self.db.fetchone(
            "SELECT current_weight, initial_weight FROM inventory WHERE lot_no = ?",
            (lot_no,)
        )
        if not lot:
            return

        # 단일 쿼리로 상태별 COUNT 집계 (v6.8.6: 기존 2회→1회)
        try:
            _cnt_rows = self.db.fetchall(
                "SELECT status, COUNT(*) AS cnt "
                "FROM inventory_tonbag WHERE lot_no = ? GROUP BY status",
                (lot_no,)
            )
            _cnt_map = {}
            _total_cnt = 0
            for _r in (_cnt_rows or []):
                _st = str(_r.get('status','') if isinstance(_r, dict) else _r[0]).strip().upper()
                _c  = int(_r.get('cnt', 0) if isinstance(_r, dict) else _r[1])
                _cnt_map[_st] = _c
                _total_cnt += _c
        except Exception as exc:
            logger.warning("톤백 상태 카운트 조회 실패: %s", exc)
            _cnt_map = {}
            _total_cnt = 0

        _avail_cnt    = _cnt_map.get(STATUS_AVAILABLE, 0)
        _reserved_cnt = _cnt_map.get(STATUS_RESERVED,  0)
        _picked_cnt   = _cnt_map.get(STATUS_PICKED,    0)
        _return_cnt   = _cnt_map.get('RETURN',         0)
        # v7.2.0: OUTBOUND + SOLD(하위호환) 통합 집계
        _outbound_cnt = (_cnt_map.get(STATUS_OUTBOUND, 0)
                         + _cnt_map.get(STATUS_SOLD, 0)
                         + _cnt_map.get('SHIPPED', 0)
                         + _cnt_map.get('CONFIRMED', 0))

        # ★ v7.2.0: OUTBOUND 통합 판정
        #  1) AVAILABLE 존재 + OUTBOUND 없음       → AVAILABLE
        #  2) AVAILABLE + OUTBOUND 혼재            → PARTIAL
        #  3) 전량 OUTBOUND/SOLD                   → OUTBOUND
        #  4) RETURN 존재 (반품 대기)              → RETURN
        #  5) PICKED 존재                          → PICKED
        #  6) RESERVED 존재                        → RESERVED
        #  7) 기타                                 → DEPLETED
        if _avail_cnt > 0 and _outbound_cnt == 0:
            new_status = STATUS_AVAILABLE
        elif _avail_cnt > 0 and _outbound_cnt > 0:
            new_status = STATUS_PARTIAL
        elif _total_cnt > 0 and _outbound_cnt >= _total_cnt:
            new_status = STATUS_OUTBOUND  # v7.2.0: SOLD 대신 OUTBOUND
        elif _return_cnt > 0:
            new_status = 'RETURN'         # v7.2.0: 반품 대기
        elif _picked_cnt > 0:
            new_status = STATUS_PICKED
        elif _reserved_cnt > 0:
            new_status = STATUS_RESERVED
        else:
            cw = lot.get('current_weight') or 0
            new_status = STATUS_DEPLETED if cw <= 0 else STATUS_AVAILABLE

        self.db.execute(
            "UPDATE inventory SET status = ? WHERE lot_no = ?",
            (new_status, lot_no)
        )
