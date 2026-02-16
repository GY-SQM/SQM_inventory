# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 데이터 검증 모듈
v2.9.30: 비정상 테스트 발견 취약점 수정

발견된 취약점:
1. 중복 LOT NO 허용 → 차단 필요
2. 음수 중량 저장 → 검증 필요
3. 빈 LOT 번호 허용 → 차단 필요
4. DEPLETED LOT 재출고 → 상태 검증 필요
5. 트랜잭션 롤백 실패 → All-or-Nothing 강화
6. 음수 재고 발생 → CHECK 제약 필요
7. 상태 불일치 → 정합성 검증 필요
"""

import sqlite3
import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    @classmethod
    def success(cls, warnings: List[str] = None) -> 'ValidationResult':
        """성공 ValidationResult 생성"""
        return cls(is_valid=True, errors=[], warnings=warnings or [])
    
    @classmethod
    def failure(cls, errors: List[str], warnings: List[str] = None) -> 'ValidationResult':
        """실패 ValidationResult 생성"""
        return cls(is_valid=False, errors=errors, warnings=warnings or [])


class InventoryValidator:
    """재고 데이터 검증기"""
    
    # 검증 상수
    MIN_WEIGHT_KG = 0.1          # 최소 중량 (0.1kg = 100g)
    MAX_WEIGHT_KG = 100000.0     # 최대 중량 (100톤)
    LOT_NO_PATTERN = r'^112\d{7}$'  # LOT 번호 형식: 112 + 7자리 숫자
    LOT_NO_MIN_LENGTH = 10
    LOT_NO_MAX_LENGTH = 20
    
    def __init__(self, db: Optional['SQMDatabase'] = None) -> None:
        """InboundValidator 초기화"""
        self.db = db
    
    # =========================================================================
    # LOT 번호 검증
    # =========================================================================
    
    def validate_lot_no(self, lot_no: str) -> ValidationResult:
        """
        LOT 번호 유효성 검증
        
        검증 항목:
        1. 빈 값 체크
        2. 길이 체크
        3. 형식 체크 (SQM 형식: 112xxxxxxx)
        """
        errors = []
        warnings = []
        
        # 1. 빈 값 체크
        if not lot_no or not str(lot_no).strip():
            errors.append("LOT 번호가 비어있습니다")
            return ValidationResult.failure(errors)
        
        lot_no = str(lot_no).strip()
        
        # 2. 길이 체크
        if len(lot_no) < self.LOT_NO_MIN_LENGTH:
            errors.append(f"LOT 번호가 너무 짧습니다: {lot_no} (최소 {self.LOT_NO_MIN_LENGTH}자)")
            return ValidationResult.failure(errors)
        
        if len(lot_no) > self.LOT_NO_MAX_LENGTH:
            errors.append(f"LOT 번호가 너무 깁니다: {lot_no} (최대 {self.LOT_NO_MAX_LENGTH}자)")
            return ValidationResult.failure(errors)
        
        # 3. SQM 형식 체크 (112로 시작하는 10자리)
        if not re.match(self.LOT_NO_PATTERN, lot_no):
            warnings.append(f"비표준 LOT 형식: {lot_no} (권장: 112xxxxxxx)")
        
        return ValidationResult.success(warnings)
    
    def validate_lot_no_unique(self, lot_no: str) -> ValidationResult:
        """
        LOT 번호 중복 검증 (DB 조회 필요)
        """
        if not self.db:
            return ValidationResult.success([" DB 연결 없음 - 중복 체크 스킵"])
        
        existing = self.db.fetchone(
            "SELECT id, lot_no, status FROM inventory WHERE lot_no = ?", 
            (lot_no,)
        )
        
        if existing:
            return ValidationResult.failure(
                [f"이미 등록된 LOT 번호입니다: {lot_no} (상태: {existing['status']})"]
            )
        
        return ValidationResult.success()
    
    # =========================================================================
    # 중량 검증
    # =========================================================================
    
    def validate_weight(self, weight: float, field_name: str = "중량") -> ValidationResult:
        """
        중량 유효성 검증
        
        검증 항목:
        1. None/빈 값 체크
        2. 숫자 변환 가능 여부
        3. 음수 체크
        4. 0 체크
        5. 범위 체크 (최소/최대)
        """
        errors = []
        warnings = []
        
        # 1. None 체크
        if weight is None:
            errors.append(f"{field_name}이(가) 비어있습니다")
            return ValidationResult.failure(errors)
        
        # 2. 숫자 변환
        try:
            weight_val = float(weight)
        except (ValueError, TypeError):
            errors.append(f"{field_name}이(가) 숫자가 아닙니다: {weight}")
            return ValidationResult.failure(errors)
        
        # 3. 음수 체크 (CRITICAL)
        if weight_val < 0:
            errors.append(f"{field_name}이(가) 음수입니다: {weight_val}kg")
            return ValidationResult.failure(errors)
        
        # 4. 0 체크 (v2.9.40: 에러로 변경 - 0 중량 입고는 무의미)
        if weight_val == 0:
            errors.append(f"{field_name}이(가) 0입니다")
            return ValidationResult.failure(errors)
        
        # 5. 최소값 체크
        if 0 < weight_val < self.MIN_WEIGHT_KG:
            warnings.append(f"{field_name}이(가) 최소값 미만입니다: {weight_val}kg < {self.MIN_WEIGHT_KG}kg")
        
        # 6. 최대값 체크
        if weight_val > self.MAX_WEIGHT_KG:
            errors.append(f"{field_name}이(가) 최대값을 초과합니다: {weight_val}kg > {self.MAX_WEIGHT_KG}kg")
            return ValidationResult.failure(errors, warnings)
        
        return ValidationResult.success(warnings)
    
    # =========================================================================
    # 출고 검증
    # =========================================================================
    
    def validate_outbound(self, lot_no: str, outbound_qty: float) -> ValidationResult:
        """
        출고 유효성 검증
        
        검증 항목:
        1. LOT 존재 여부
        2. LOT 상태 (AVAILABLE/PARTIAL만 출고 가능)
        3. 재고량 충분 여부
        """
        errors = []
        warnings = []
        
        if not self.db:
            return ValidationResult.failure(["DB 연결 없음"])
        
        # 1. LOT 조회
        lot = self.db.fetchone(
            "SELECT lot_no, current_weight, status FROM inventory WHERE lot_no = ?",
            (lot_no,)
        )
        
        if not lot:
            errors.append(f"존재하지 않는 LOT입니다: {lot_no}")
            return ValidationResult.failure(errors)
        
        # 2. 상태 체크
        if lot['status'] == 'DEPLETED':
            errors.append(f"이미 출고 완료된 LOT입니다: {lot_no} (상태: DEPLETED)")
            return ValidationResult.failure(errors)
        
        if lot['status'] not in ('AVAILABLE', 'PARTIAL'):
            errors.append(f"출고 불가능한 상태입니다: {lot_no} (상태: {lot['status']})")
            return ValidationResult.failure(errors)
        
        # 3. 재고량 체크
        current = lot['current_weight'] or 0
        if outbound_qty > current:
            errors.append(
                f"재고 부족: {lot_no} - 요청 {outbound_qty}kg, 보유 {current}kg"
            )
            return ValidationResult.failure(errors)
        
        # 4. 전량 출고 경고
        if outbound_qty == current:
            warnings.append(f"전량 출고됩니다: {lot_no} ({current}kg)")
        
        return ValidationResult.success(warnings)
    
    # =========================================================================
    # 입고 데이터 통합 검증
    # =========================================================================
    
    def validate_inbound_data(self, packing_data) -> ValidationResult:
        """
        입고 데이터 통합 검증
        
        검증 항목:
        1. 필수 필드 존재 여부
        2. SAP NO 유효성
        3. 각 LOT 데이터 검증
        """
        errors = []
        warnings = []
        
        # 1. 필수 필드 체크
        if not packing_data:
            return ValidationResult.failure(["입고 데이터가 없습니다"])
        
        # 딕셔너리와 객체 모두 지원
        if isinstance(packing_data, dict):
            lots = packing_data.get('lots', [])
            sap_no = packing_data.get('sap_no')
        else:
            lots = getattr(packing_data, 'lots', [])
            sap_no = getattr(packing_data, 'sap_no', None)
        
        if not lots:
            return ValidationResult.failure(["LOT 데이터가 없습니다"])
        
        # 2. SAP NO 체크
        if not sap_no or not str(sap_no).strip():
            warnings.append("SAP NO가 없습니다 (자동 생성됩니다)")
        elif self.db:
            existing = self.db.fetchone("SELECT id FROM shipment WHERE sap_no = ?", (sap_no,))
            if existing:
                errors.append(f"이미 등록된 SAP NO입니다: {sap_no}")
                return ValidationResult.failure(errors, warnings)
        
        # 3. 각 LOT 검증
        lot_nos_in_batch = set()  # 배치 내 중복 체크용
        
        for idx, lot in enumerate(lots):
            lot_no = lot.get('lot_no', '')
            
            # 3.1 LOT 번호 검증
            lot_result = self.validate_lot_no(lot_no)
            if not lot_result.is_valid:
                errors.extend([f"LOT #{idx+1}: {e}" for e in lot_result.errors])
                continue
            warnings.extend([f"LOT #{idx+1}: {w}" for w in lot_result.warnings])
            
            # 3.2 배치 내 중복 체크
            if lot_no in lot_nos_in_batch:
                errors.append(f"LOT #{idx+1}: 배치 내 중복 LOT 번호: {lot_no}")
                continue
            lot_nos_in_batch.add(lot_no)
            
            # 3.3 DB 중복 체크
            if self.db:
                unique_result = self.validate_lot_no_unique(lot_no)
                if not unique_result.is_valid:
                    errors.extend([f"LOT #{idx+1}: {e}" for e in unique_result.errors])
            
            # 3.4 중량 검증
            net_weight = lot.get('net_weight', 0)
            weight_result = self.validate_weight(net_weight, f"LOT #{idx+1} 순중량")
            if not weight_result.is_valid:
                errors.extend(weight_result.errors)
            warnings.extend(weight_result.warnings)
        
        # 결과 반환
        if errors:
            return ValidationResult.failure(errors, warnings)
        
        return ValidationResult.success(warnings)
    
    # =========================================================================
    # 데이터 정합성 검증
    # =========================================================================
    
    def check_data_integrity(self) -> ValidationResult:
        """
        전체 데이터 정합성 검증
        
        검증 항목:
        1. 음수 재고 존재 여부
        2. 상태-재고 불일치
        3. 필수 필드 NULL 여부
        4. inventory↔tonbag 크로스 검증 (v3.8.4)
        """
        if not self.db:
            return ValidationResult.failure(["DB 연결 없음"])
        
        errors = []
        warnings = []
        
        # 1. 음수 재고 체크
        negative = self.db.fetchone(
            "SELECT COUNT(*) as cnt, MIN(current_weight) as min_wt FROM inventory WHERE current_weight < 0"
        )
        if negative and negative['cnt'] > 0:
            errors.append(f"음수 재고 발견: {negative['cnt']}건 (최소값: {negative['min_wt']}kg)")
        
        # 2. 상태-재고 불일치 체크
        depleted_with_stock = self.db.fetchone("""
            SELECT COUNT(*) as cnt FROM inventory 
            WHERE status = 'DEPLETED' AND current_weight > 0
        """)
        if depleted_with_stock and depleted_with_stock['cnt'] > 0:
            errors.append(f"상태 불일치: DEPLETED인데 재고 있음 {depleted_with_stock['cnt']}건")
        
        available_no_stock = self.db.fetchone("""
            SELECT COUNT(*) as cnt FROM inventory 
            WHERE status = 'AVAILABLE' AND current_weight <= 0
        """)
        if available_no_stock and available_no_stock['cnt'] > 0:
            warnings.append(f"상태 불일치: AVAILABLE인데 재고 없음 {available_no_stock['cnt']}건")
        
        # 3. 필수 필드 NULL 체크
        null_fields = self.db.fetchone("""
            SELECT COUNT(*) as cnt FROM inventory 
            WHERE lot_no IS NULL OR lot_no = '' 
               OR product IS NULL OR product = ''
        """)
        if null_fields and null_fields['cnt'] > 0:
            errors.append(f"필수 필드 누락: {null_fields['cnt']}건")
        
        # 4. v3.8.4: inventory↔tonbag 크로스 검증 (중량)
        # v5.7.2: 샘플 포함 합산 — is_sample 조건 넣지 않음 (대원칙 5001 = 500×10 + 1)
        try:
            cross_check = self.db.fetchall("""
                SELECT 
                    i.lot_no,
                    i.current_weight AS inv_weight,
                    COALESCE(t.tonbag_avail_weight, 0) AS tonbag_weight
                FROM inventory i
                LEFT JOIN (
                    SELECT lot_no, SUM(weight) AS tonbag_avail_weight
                    FROM inventory_tonbag
                    WHERE status = 'AVAILABLE'
                    GROUP BY lot_no
                ) t ON i.lot_no = t.lot_no
                WHERE i.current_weight > 0
                  AND ABS(i.current_weight - COALESCE(t.tonbag_avail_weight, 0)) > 0.01
            """)
            if cross_check:
                for row in cross_check[:5]:
                    lot = row['lot_no']
                    inv_w = row['inv_weight']
                    ton_w = row['tonbag_weight']
                    warnings.append(
                        f"크로스 불일치: {lot} (inventory={inv_w:.0f}kg, tonbag합계={ton_w:.0f}kg)"
                    )
                if len(cross_check) > 5:
                    warnings.append(f"... 외 {len(cross_check) - 5}건 추가 불일치")
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"크로스 검증 스킵: {e}")
        
        # 5. v3.8.7: MXBG ↔ 톤백 수량 정합성 검증 — 샘플 톤백 제외
        try:
            mxbg_check = self.db.fetchall("""
                SELECT 
                    i.lot_no,
                    i.mxbg_pallet AS mxbg,
                    COALESCE(t.tonbag_count, 0) AS actual_count
                FROM inventory i
                LEFT JOIN (
                    SELECT lot_no, COUNT(*) AS tonbag_count
                    FROM inventory_tonbag 
                    WHERE COALESCE(is_sample, 0) = 0
                    GROUP BY lot_no
                ) t ON i.lot_no = t.lot_no
                WHERE i.mxbg_pallet > 0
                  AND COALESCE(t.tonbag_count, 0) > 0
                  AND i.mxbg_pallet != COALESCE(t.tonbag_count, 0)
            """)
            if mxbg_check:
                for row in mxbg_check[:5]:
                    lot = row['lot_no']
                    mxbg = row['mxbg']
                    actual = row['actual_count']
                    errors.append(
                        f"MXBG↔톤백 수량 불일치: {lot} (MXBG={mxbg}, 실제톤백={actual})"
                    )
                if len(mxbg_check) > 5:
                    errors.append(f"... 외 {len(mxbg_check) - 5}건 추가 MXBG 불일치")
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"MXBG 검증 스킵: {e}")
        
        if errors:
            return ValidationResult.failure(errors, warnings)
        
        return ValidationResult.success(warnings)

    # =========================================================================
    # 데이터 복구
    # =========================================================================
    
    def fix_data_integrity(self, dry_run: bool = True) -> Dict:
        """
        데이터 정합성 문제 자동 복구
        
        Args:
            dry_run: True면 실제 수정 없이 시뮬레이션만
            
        Returns:
            복구 결과 딕셔너리
        """
        if not self.db:
            return {'success': False, 'error': 'DB 연결 없음'}
        
        result = {
            'success': True,
            'dry_run': dry_run,
            'fixes': [],
            'errors': []
        }
        
        try:
            # 1. 음수 재고 → 0으로 수정
            negative_lots = self.db.fetchall(
                "SELECT lot_no, current_weight FROM inventory WHERE current_weight < 0"
            )
            for lot in negative_lots:
                if not dry_run:
                    self.db.execute(
                        "UPDATE inventory SET current_weight = 0, status = 'DEPLETED' WHERE lot_no = ?",
                        (lot['lot_no'],)
                    )
                result['fixes'].append(f"음수 재고 수정: {lot['lot_no']} ({lot['current_weight']}kg → 0)")
            
            # 2. DEPLETED인데 재고 있으면 → AVAILABLE/PARTIAL로 변경
            depleted_with_stock = self.db.fetchall("""
                SELECT lot_no, current_weight, net_weight FROM inventory 
                WHERE status = 'DEPLETED' AND current_weight > 0
            """)
            for lot in depleted_with_stock:
                new_status = 'AVAILABLE' if lot['current_weight'] >= lot['net_weight'] else 'PARTIAL'
                if not dry_run:
                    self.db.execute(
                        "UPDATE inventory SET status = ? WHERE lot_no = ?",
                        (new_status, lot['lot_no'])
                    )
                result['fixes'].append(f"상태 수정: {lot['lot_no']} DEPLETED → {new_status}")
            
            # 3. AVAILABLE인데 재고 0이면 → DEPLETED로 변경
            available_no_stock = self.db.fetchall("""
                SELECT lot_no FROM inventory 
                WHERE status = 'AVAILABLE' AND current_weight <= 0
            """)
            for lot in available_no_stock:
                if not dry_run:
                    self.db.execute(
                        "UPDATE inventory SET status = 'DEPLETED' WHERE lot_no = ?",
                        (lot['lot_no'],)
                    )
                result['fixes'].append(f"상태 수정: {lot['lot_no']} AVAILABLE → DEPLETED")
            
            # 4. v3.8.7: Free Time 일괄 계산 (arrival_date 있고 free_time이 0인 LOT)
            # D/O별 Free Time이 동일하므로, 같은 BL의 다른 LOT에서 free_time 보완
            try:
                missing_ft = self.db.fetchall("""
                    SELECT lot_no, arrival_date, bl_no
                    FROM inventory 
                    WHERE arrival_date IS NOT NULL 
                      AND arrival_date != ''
                      AND (free_time IS NULL OR free_time = 0)
                """)
                for lot in missing_ft:
                    # 같은 BL의 다른 LOT에서 free_time 가져오기
                    bl = lot.get('bl_no', '') or ''
                    if bl:
                        ref = self.db.fetchone(
                            "SELECT free_time FROM inventory WHERE bl_no = ? AND free_time > 0 LIMIT 1",
                            (bl,)
                        )
                        if ref and ref.get('free_time', 0) > 0:
                            if not dry_run:
                                self.db.execute(
                                    "UPDATE inventory SET free_time = ? WHERE lot_no = ?",
                                    (ref['free_time'], lot['lot_no'])
                                )
                            result['fixes'].append(
                                f"Free Time 보완: {lot['lot_no']} → {ref['free_time']}일 (BL {bl}에서 복사)"
                            )
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
                logger.debug(f"Free Time 일괄 계산 스킵: {e}")
            
            # 5. v3.8.7: salar_invoice_no 일괄 보완 (같은 SAP NO에서 복사)
            try:
                missing_inv = self.db.fetchall("""
                    SELECT lot_no, sap_no, bl_no
                    FROM inventory 
                    WHERE (salar_invoice_no IS NULL OR salar_invoice_no = '')
                      AND sap_no IS NOT NULL AND sap_no != ''
                """)
                for lot in missing_inv:
                    sap = lot.get('sap_no', '') or ''
                    if sap:
                        ref = self.db.fetchone(
                            "SELECT salar_invoice_no FROM inventory WHERE sap_no = ? AND salar_invoice_no != '' LIMIT 1",
                            (sap,)
                        )
                        if ref and ref.get('salar_invoice_no'):
                            if not dry_run:
                                self.db.execute(
                                    "UPDATE inventory SET salar_invoice_no = ? WHERE lot_no = ?",
                                    (ref['salar_invoice_no'], lot['lot_no'])
                                )
                            result['fixes'].append(
                                f"Invoice No 보완: {lot['lot_no']} → {ref['salar_invoice_no']} (SAP {sap}에서 복사)"
                            )
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
                logger.debug(f"Invoice No 일괄 보완 스킵: {e}")
            
            if not dry_run:
                self.db.commit()
            
            result['total_fixes'] = len(result['fixes'])
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            result['success'] = False
            result['errors'].append(str(e))
            if not dry_run:
                self.db.rollback()
        
        return result

    # ═══════════════════════════════════════════════════════
    # v3.8.4 A6: 재고 스냅샷
    # ═══════════════════════════════════════════════════════

    def save_daily_snapshot(self) -> Dict:
        """일별 재고 스냅샷 저장"""
        import json
        from datetime import date as _date

        today = _date.today().isoformat()

        try:
            existing = self.db.fetchone(
                "SELECT id FROM inventory_snapshot WHERE snapshot_date = ?", (today,))

            stats = self.db.fetchone("""
                SELECT 
                    COUNT(*) AS total_lots,
                    COALESCE(SUM(current_weight), 0) AS total_weight,
                    COALESCE(SUM(CASE WHEN status != 'DEPLETED' THEN current_weight ELSE 0 END), 0) AS avail_weight,
                    COALESCE(SUM(picked_weight), 0) AS picked_weight
                FROM inventory
            """)

            tonbag_count = self.db.fetchone(
                "SELECT COUNT(*) AS cnt FROM inventory_tonbag WHERE COALESCE(is_sample,0)=0")

            product_rows = self.db.fetchall("""
                SELECT product, COUNT(*) AS lots, SUM(current_weight) AS weight
                FROM inventory GROUP BY product
            """)
            product_summary = json.dumps(
                [{'product': r['product'], 'lots': r['lots'],
                  'weight_kg': r['weight']} for r in product_rows],
                ensure_ascii=False)

            total_lots = stats['total_lots'] if stats else 0
            total_weight = stats['total_weight'] if stats else 0
            avail_weight = stats['avail_weight'] if stats else 0
            picked_weight = stats['picked_weight'] if stats else 0
            total_tonbags = tonbag_count['cnt'] if tonbag_count else 0

            if existing:
                self.db.execute("""
                    UPDATE inventory_snapshot SET
                        total_lots = ?, total_tonbags = ?,
                        total_weight_kg = ?, available_weight_kg = ?,
                        picked_weight_kg = ?, product_summary = ?,
                        created_at = CURRENT_TIMESTAMP
                    WHERE snapshot_date = ?
                """, (total_lots, total_tonbags, total_weight,
                      avail_weight, picked_weight, product_summary, today))
            else:
                self.db.execute("""
                    INSERT INTO inventory_snapshot 
                    (snapshot_date, total_lots, total_tonbags, total_weight_kg,
                     available_weight_kg, picked_weight_kg, product_summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (today, total_lots, total_tonbags, total_weight,
                      avail_weight, picked_weight, product_summary))

            self.db.commit()

            return {
                'success': True, 'date': today,
                'total_lots': total_lots, 'total_weight_kg': total_weight,
            }
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"스냅샷 저장 오류: {e}")
            return {'success': False, 'error': str(e)}


class InboundValidator(InventoryValidator):
    """입고 전용 검증기 (All-or-Nothing 지원)"""
    
    def validate_all_or_nothing(self, packing_data) -> ValidationResult:
        """
        All-or-Nothing 입고 검증
        
        모든 LOT이 유효해야만 입고 진행
        하나라도 실패하면 전체 거부
        """
        base_result = self.validate_inbound_data(packing_data)
        
        if not base_result.is_valid:
            # 에러가 있으면 전체 거부
            error_count = len(base_result.errors)
            base_result.errors.insert(0, 
                f"[All-or-Nothing] {error_count}개 오류로 인해 전체 입고가 거부됩니다"
            )
        
        return base_result


class OutboundValidator(InventoryValidator):
    """출고 전용 검증기"""
    
    def validate_outbound_batch(self, outbound_list: List[Dict]) -> ValidationResult:
        """
        배치 출고 검증
        
        Args:
            outbound_list: [{'lot_no': 'xxx', 'qty': 1000}, ...]
        """
        errors = []
        warnings = []
        
        for idx, item in enumerate(outbound_list):
            lot_no = item.get('lot_no', '')
            qty = item.get('qty', 0)
            
            result = self.validate_outbound(lot_no, qty)
            if not result.is_valid:
                errors.extend([f"#{idx+1} {lot_no}: {e}" for e in result.errors])
            warnings.extend([f"#{idx+1} {lot_no}: {w}" for w in result.warnings])
        
        if errors:
            return ValidationResult.failure(errors, warnings)
        
        return ValidationResult.success(warnings)


# ============================================================================
# 편의 함수
# ============================================================================

def validate_lot_no(lot_no: str) -> Tuple[bool, str]:
    """
    LOT 번호 간단 검증 (레거시 호환)
    
    Returns:
        (is_valid, error_message)
    """
    v = InventoryValidator()
    result = v.validate_lot_no(lot_no)
    
    if result.is_valid:
        return True, ""
    return False, "; ".join(result.errors)


def validate_weight(weight: float) -> Tuple[bool, str]:
    """
    중량 간단 검증 (레거시 호환)
    """
    v = InventoryValidator()
    result = v.validate_weight(weight)
    
    if result.is_valid:
        return True, ""
    return False, "; ".join(result.errors)


# ============================================================================
# 테스트
# ============================================================================

if __name__ == "__main__":
    logger.debug("=" * 60)
    logger.debug("InventoryValidator 단위 테스트")
    logger.debug("=" * 60)
    
    v = InventoryValidator()
    
    # LOT 번호 테스트
    logger.debug("\n[LOT 번호 검증]")
    test_lots = ['1120001234', '', '123', 'ABC123', '1120000001']
    for lot in test_lots:
        result = v.validate_lot_no(lot)
        status = "✅" if result.is_valid else "❌"
        logger.debug(f"  {status} '{lot}': {result.errors or result.warnings or 'OK'}")
    
    # 중량 테스트
    logger.debug("\n[중량 검증]")
    test_weights = [5000, 0, -100, 0.001, 999999999, None]
    for w in test_weights:
        result = v.validate_weight(w)
        status = "✅" if result.is_valid else "❌"
        logger.debug(f"  {status} {w}: {result.errors or result.warnings or 'OK'}")
    
    logger.debug("\n✅ 테스트 완료")
