"""
SQM 재고관리 시스템 - 데이터 정합성 + 스냅샷 + 알림 Mixin
============================================================

v3.8.5 신규 모듈

기능:
    1. 자동 정합성 검증 (출고/반품 후 즉시 assert)
    2. 일간 재고 스냅샷 (특정 날짜 기준 재고 조회)
    3. 대시보드 알림 (DEPLETED 미정리, 정합성 경고)

작성자: Ruby (남기동)
"""

import json
import logging
from datetime import date
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

WEIGHT_TOLERANCE_KG = 0.5  # 무게 허용 오차 (kg)


class IntegrityMixin:
    """데이터 정합성 + 스냅샷 + 알림 Mixin"""

    # ══════════════════════════════════════════════════════════
    # 기능 1: 자동 정합성 검증
    # ══════════════════════════════════════════════════════════

    def verify_lot_integrity(self, lot_no: str) -> Dict:
        """
        단일 LOT 정합성 검증

        검증 항목:
            1. initial_weight = current_weight + picked_weight
            2. inventory.current_weight = SUM(톤백 AVAILABLE weight)
            3. inventory.picked_weight = SUM(톤백 PICKED weight)
            4. current_weight >= 0, picked_weight >= 0
            5. 톤백 총수 = mxbg_pallet (경고)

        Args:
            lot_no: LOT 번호

        Returns:
            dict: {valid, errors, warnings, details}
        """
        result = {'valid': True, 'errors': [], 'warnings': [], 'details': {}}

        try:
            lot = self.db.fetchone(
                "SELECT lot_no, initial_weight, current_weight, picked_weight, mxbg_pallet "
                "FROM inventory WHERE lot_no = ?", (lot_no,))
            if not lot:
                result['errors'].append(f"LOT 없음: {lot_no}")
                result['valid'] = False
                return result

            iw = float(lot['initial_weight'] or 0)
            cw = float(lot['current_weight'] or 0)
            pw = float(lot['picked_weight'] or 0)

            result['details'] = {
                'initial_weight': iw,
                'current_weight': cw,
                'picked_weight': pw,
            }

            # 검증 1: initial = current + picked
            diff = abs(iw - (cw + pw))
            if diff > WEIGHT_TOLERANCE_KG:
                result['errors'].append(
                    f"무게 불일치: initial({iw:.1f}) ≠ "
                    f"current({cw:.1f}) + picked({pw:.1f}), 차이={diff:.1f}kg"
                )
                result['valid'] = False

            # 검증 2-3: 톤백 합계 대조 (v5.7.2: 가용/출고 합산에 샘플 포함 — 대원칙 5001=500×10+1)
            # 가용 합계: status IN ('AVAILABLE','SAMPLE','RESERVED') — RESERVED는 current_weight 미차감 상태
            # v7.0.1: RESERVED 포함 (reserve_from_allocation에서 current_weight 안 건드리므로)
            tb_summary = self.db.fetchone("""
                SELECT 
                    COALESCE(SUM(CASE WHEN status IN ('AVAILABLE','SAMPLE','RESERVED') THEN weight ELSE 0 END), 0) as avail_w,
                    COALESCE(SUM(CASE WHEN status IN ('PICKED','CONFIRMED','SHIPPED','SOLD') THEN weight ELSE 0 END), 0) as picked_w,
                    COALESCE(SUM(CASE WHEN status = 'RESERVED' THEN weight ELSE 0 END), 0) as reserved_w,
                    SUM(CASE WHEN COALESCE(is_sample,0)=0 THEN 1 ELSE 0 END) as total_count,
                    SUM(CASE WHEN status='AVAILABLE' THEN 1 ELSE 0 END) as avail_count,
                    SUM(CASE WHEN status='RESERVED' THEN 1 ELSE 0 END) as reserved_count,
                    SUM(CASE WHEN status IN ('PICKED','CONFIRMED','SHIPPED') THEN 1 ELSE 0 END) as picked_count,
                    SUM(CASE WHEN COALESCE(is_sample,0)=1 THEN 1 ELSE 0 END) as sample_count
                FROM inventory_tonbag WHERE lot_no = ?
            """, (lot_no,))

            if tb_summary:
                tb_avail = float(tb_summary['avail_w'] or 0)
                tb_picked = float(tb_summary['picked_w'] or 0)
                tb_total = int(tb_summary['total_count'] or 0)

                result['details']['tonbag_available_weight'] = tb_avail
                result['details']['tonbag_picked_weight'] = tb_picked
                result['details']['tonbag_reserved_weight'] = float(tb_summary.get('reserved_w') or 0)
                result['details']['tonbag_count'] = tb_total
                result['details']['reserved_count'] = int(tb_summary.get('reserved_count') or 0)

                if abs(cw - tb_avail) > WEIGHT_TOLERANCE_KG:
                    result['errors'].append(
                        f"LOT↔톤백 가용 불일치: inv.current({cw:.1f}) ≠ "
                        f"tonbag.available({tb_avail:.1f})"
                    )
                    result['valid'] = False

                if abs(pw - tb_picked) > WEIGHT_TOLERANCE_KG:
                    result['errors'].append(
                        f"LOT↔톤백 출고 불일치: inv.picked({pw:.1f}) ≠ "
                        f"tonbag.picked({tb_picked:.1f})"
                    )
                    result['valid'] = False

                # 검증 5: 톤백 수 검증 (경고)
                mxbg = int(lot['mxbg_pallet'] or 0)
                if mxbg > 0 and tb_total != mxbg:
                    result['warnings'].append(
                        f"톤백 수 불일치: 등록({mxbg}) ≠ 실제({tb_total})"
                    )

                # ★ v5.2.0 검증 6: 샘플 정책 하드스톱
                sample_count = int(tb_summary.get('sample_count') or 0)
                result['details']['sample_count'] = sample_count
                if sample_count == 0:
                    result['errors'].append(
                        f"샘플 정책 위반: LOT {lot_no}에 샘플 톤백 0개 (필수 1개)"
                    )
                    result['valid'] = False
                elif sample_count > 1:
                    result['errors'].append(
                        f"샘플 정책 위반: LOT {lot_no}에 샘플 톤백 {sample_count}개 (최대 1개)"
                    )
                    result['valid'] = False

            # 검증 4: 음수 검증
            if cw < -0.01:
                result['errors'].append(f"current_weight 음수: {cw}")
                result['valid'] = False
            if pw < -0.01:
                result['errors'].append(f"picked_weight 음수: {pw}")
                result['valid'] = False

            # ═══ v5.6.0 검증 7: 대원칙 (톤백 단가 = 500kg 또는 1000kg) ═══
            # LOT 총무게 = (톤백수 × 단가) + 샘플 1kg
            if tb_summary and tb_total > 0:
                from core.constants import SAMPLE_WEIGHT_KG
                SAMPLE_WEIGHT = SAMPLE_WEIGHT_KG
                VALID_UNIT_WEIGHTS = (500.0, 1000.0)  # v6.12: 비표준 단가 추가 시 여기에 추가 (예: 750.0)
                TOLERANCE = 0.5  # 0.5kg 허용

                # 방법: (initial_weight - 1) / 톤백수 = 단가 → 500 or 1000이어야 함
                unit_weight = (iw - SAMPLE_WEIGHT) / tb_total if tb_total > 0 else 0

                # 개별 톤백 무게 확인 (일반 톤백만)
                tb_weights = self.db.fetchall(
                    "SELECT weight FROM inventory_tonbag WHERE lot_no = ? AND COALESCE(is_sample,0) = 0",
                    (lot_no,))

                if tb_weights:
                    weights = [float(r['weight'] or 0) for r in tb_weights]
                    unique_weights = set(round(w, 1) for w in weights)

                    # 모든 톤백이 동일 무게인지 확인
                    if len(unique_weights) > 1:
                        result['warnings'].append(
                            f"톤백 무게 불균일: {sorted(unique_weights)}")

                    # 단가가 500 or 1000인지 확인
                    avg_weight = sum(weights) / len(weights)
                    is_valid_unit = any(
                        abs(avg_weight - vw) < TOLERANCE for vw in VALID_UNIT_WEIGHTS)

                    if not is_valid_unit:
                        result['errors'].append(
                            f"대원칙 위반: 톤백 평균 {avg_weight:.1f}kg "
                            f"(허용: {VALID_UNIT_WEIGHTS})")
                        result['valid'] = False

                    # LOT 총무게 정합성: 톤백합 + 샘플 = initial_weight
                    tonbag_sum = sum(weights)
                    expected_total = tonbag_sum + SAMPLE_WEIGHT
                    if abs(iw - expected_total) > TOLERANCE:
                        result['errors'].append(
                            f"대원칙 총무게 불일치: initial({iw:.1f}) ≠ "
                            f"톤백합({tonbag_sum:.1f}) + 샘플({SAMPLE_WEIGHT}) = {expected_total:.1f}")
                        result['valid'] = False

                    result['details']['unit_weight'] = round(avg_weight, 1)
                    result['details']['principle_valid'] = is_valid_unit

        except (ValueError, TypeError, KeyError) as e:
            result['errors'].append(f"검증 오류: {e}")
            result['valid'] = False
            logger.error(f"정합성 검증 오류: {e}", exc_info=True)

        return result

    def verify_all_integrity(self) -> Dict:
        """
        전체 재고 정합성 검증

        Returns:
            dict: {valid, total_lots, error_lots, warning_lots, details}
        """
        result = {
            'valid': True,
            'total_lots': 0,
            'error_lots': [],
            'warning_lots': [],
            'details': {}
        }

        try:
            lots = self.db.fetchall("SELECT lot_no FROM inventory")
            result['total_lots'] = len(lots)

            for lot in lots:
                lot_no = lot['lot_no']
                check = self.verify_lot_integrity(lot_no)

                if not check['valid']:
                    result['valid'] = False
                    result['error_lots'].append({
                        'lot_no': lot_no,
                        'errors': check['errors']
                    })

                if check['warnings']:
                    result['warning_lots'].append({
                        'lot_no': lot_no,
                        'warnings': check['warnings']
                    })

            logger.info(
                f"전체 정합성 검증: {result['total_lots']}개 LOT, "
                f"에러 {len(result['error_lots'])}건, "
                f"경고 {len(result['warning_lots'])}건"
            )

        except (ValueError, TypeError, AttributeError) as e:
            result['valid'] = False
            result['details']['error'] = str(e)
            logger.error(f"전체 정합성 검증 오류: {e}")

        return result

    def _assert_lot_integrity(self, lot_no: str) -> None:
        """
        출고/반품 후 자동 호출되는 정합성 assert

        불일치 감지 시 로그 경고만 기록 (트랜잭션 롤백하지 않음)

        Args:
            lot_no: 검증할 LOT 번호
        """
        try:
            check = self.verify_lot_integrity(lot_no)
            if not check['valid']:
                logger.warning(
                    f"[정합성 경고] {lot_no}: {check['errors']}"
                )
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"정합성 assert 오류: {e}")

    # ══════════════════════════════════════════════════════════
    # 기능 2: 일간 재고 스냅샷
    # ══════════════════════════════════════════════════════════

    def get_snapshot(self, snapshot_date: date = None) -> Optional[Dict]:
        """
        특정 날짜 스냅샷 조회

        Args:
            snapshot_date: 조회 날짜 (기본: 오늘)

        Returns:
            스냅샷 데이터 또는 None
        """
        if snapshot_date is None:
            snapshot_date = date.today()

        row = self.db.fetchone(
            "SELECT * FROM inventory_snapshot WHERE snapshot_date = ?",
            (snapshot_date.isoformat(),))

        if row:
            data = dict(row)
            if data.get('product_summary'):
                try:
                    data['product_summary'] = json.loads(data['product_summary'])
                except (json.JSONDecodeError, TypeError) as _e:
                    logger.debug(f"JSON 파싱 실패: {_e}")
            return data
        return None

    def get_snapshot_range(self, start_date: date, end_date: date) -> List[Dict]:
        """
        기간별 스냅샷 조회 (추이 분석용)

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            스냅샷 리스트
        """
        rows = self.db.fetchall("""
            SELECT * FROM inventory_snapshot 
            WHERE snapshot_date BETWEEN ? AND ?
            ORDER BY snapshot_date
        """, (start_date.isoformat(), end_date.isoformat()))

        result = []
        for row in rows:
            data = dict(row)
            if data.get('product_summary'):
                try:
                    data['product_summary'] = json.loads(data['product_summary'])
                except (json.JSONDecodeError, TypeError) as _e:
                    logger.debug(f"JSON 파싱 실패: {_e}")
            result.append(data)
        return result

    # ══════════════════════════════════════════════════════════
    # 기능 6: 대시보드 알림
    # ══════════════════════════════════════════════════════════
