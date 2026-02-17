# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 입고 처리 Mixin
======================================

v3.6.6: SQLAlchemy → SQMDatabase API 전환 (self.db 기반)

작성자: Ruby (남기동)
버전: v3.6.6
"""

import sqlite3
import logging
from datetime import date, datetime
from typing import Dict, List

from .base import InventoryBaseMixin, PackingData
import re  # v5.3.0

logger = logging.getLogger(__name__)

# 비즈니스 기본값
from core.constants import DEFAULT_WAREHOUSE, SAMPLE_WEIGHT_KG, STATUS_AVAILABLE, DATE_FORMAT, DATETIME_FORMAT






# --- v5.3.0 helpers: alias + normalization + audit raw capture ---
def _get_sub_lt_raw(tb: dict):
    """Extract raw tonbag/sub_lt value from various possible keys (case-insensitive)."""
    if not isinstance(tb, dict):
        return None, None
    priority = ['bag_no','tonbag_no','sub_lt','dmsub_lt','dm_sub_lt','DM SUB LT','DM_SUB_LT']
    for k in priority:
        if k in tb and tb.get(k) not in (None, ''):
            return tb.get(k), str(k)
    lower_map = {str(k).lower(): k for k in tb.keys()}
    for lk in ['bag_no','tonbag_no','sub_lt','dmsub_lt','dm_sub_lt','dm sub lt']:
        if lk in lower_map:
            k = lower_map[lk]
            v = tb.get(k)
            if v not in (None, ''):
                return v, str(k)
    return None, None

def _normalize_tonbag_no_from_raw_v530(raw, fallback_seq: int, is_sample: bool):
    """v5.3.0: Normalize tonbag_no as TEXT.
    Sample -> 'S00' (sub_lt=0과 일치); Digits -> zfill(3); Non-digits -> internal seq (fallback_seq).
    Raw value MUST be preserved in audit fields.
    """
    if is_sample:
        return 'S00'
    s = '' if raw is None else str(raw).strip()
    if s and re.fullmatch(r'\d+', s):
        return s.zfill(3)
    return str(fallback_seq).zfill(3)
class InboundMixin(InventoryBaseMixin):
    """입고 처리 Mixin (v3.6.6: SQMDatabase API 기반)"""
    
    def process_inbound(self, packing_data, invoice_data=None, 
                        bl_data=None, do_data=None) -> Dict:
        """
        입고 처리
        
        Args:
            packing_data: 패킹 리스트 데이터 (dict 또는 PackingData)
            invoice_data: 인보이스 데이터 (선택)
            bl_data: B/L 데이터 (선택)
            do_data: D/O 데이터 (선택)
        
        Returns:
            dict: {success, message, lot_no, created_lots, created_tonbags, errors, warnings}
        """
        result = {
            'success': False,
            'message': '',
            'lot_no': None,
            'created_lots': [],
            'created_tonbags': 0,
            'errors': [],
            'warnings': [],
        }
        
        try:
            # v3.8.8: 항상 dict로 정규화 (PackingData wrapping 제거)
            if isinstance(packing_data, dict):
                packing = packing_data
            elif hasattr(packing_data, 'to_dict'):
                packing = packing_data.to_dict()
            elif hasattr(packing_data, '_data'):
                packing = packing_data._data
            elif hasattr(packing_data, 'get'):
                # PackingData 또는 dict-like 객체
                packing = {k: packing_data.get(k) for k in [
                    'lot_no', 'sap_no', 'bl_no', 'container_no', 'product', 'product_code',
                    'lot_sqm', 'mxbg_pallet', 'net_weight', 'gross_weight', 'salar_invoice_no',
                    'ship_date', 'arrival_date', 'free_time', 'free_time_date',
                    'warehouse', 'vessel', 'tonbags',
                ] if packing_data.get(k) is not None}
            else:
                packing = vars(packing_data) if hasattr(packing_data, '__dict__') else {}
            
            logger.info(f"[process_inbound] lot_no={packing.get('lot_no')!r}, keys_count={len(packing)}")
            
            # 필수 필드 검증
            if not packing.get('lot_no'):
                result['errors'].append(f"LOT 번호가 없습니다 (type={type(packing_data).__name__}, keys={list(packing.keys())[:5]})")
                return result
            
            lot_no = str(packing.get('lot_no') or '').strip()
            
            # LOT NO 길이 검증
            if len(lot_no) > 30:
                result['errors'].append(f"LOT 번호가 너무 깁니다: {len(lot_no)}자 (최대 30자)")
                return result
            
            # PC-1: LOT 번호 형식 검증 (SQM: 10자리 숫자, 경고만)
            if lot_no and not re.match(r'^\d{10}$', lot_no):
                result['warnings'].append(
                    f"LOT 번호 형식 주의: '{lot_no}' (SQM 표준: 10자리 숫자)")
            
            # 중량 검증
            weight = self._safe_parse_float(
                packing.get('net_weight')
            )
            if weight <= 0:
                result['errors'].append(f"유효하지 않은 중량: {weight}")
                return result
            
            # 중복 확인
            if self._check_lot_exists(lot_no):
                result['errors'].append(f"이미 존재하는 LOT: {lot_no}")
                return result
            
            # 트랜잭션으로 원자적 처리
            with self.db.transaction():
                # LOT 생성
                lot_data = self._prepare_lot_data(packing, bl_data, do_data)
                self._insert_lot(lot_data)
                
                # v3.8.4: 생성된 LOT의 inventory_id 조회
                inv_row = self.db.fetchone(
                    "SELECT id FROM inventory WHERE lot_no = ?", (lot_no,))
                inventory_id = inv_row['id'] if inv_row and isinstance(inv_row, dict) else (
                    inv_row[0] if inv_row else None)
                
                # 톤백 생성 (명시적 tonbags 또는 bag_count 기반 자동 생성)
                tonbags = packing.get('tonbags') or []
                if not tonbags:
                    bag_count = self._safe_parse_int(
                        packing.get('mxbg_pallet')
                    )
                    if bag_count > 0:
                        total_w = self._safe_parse_float(
                            packing.get('net_weight')
                        )
                        # v5.7.1 핵심: 대원칙 5001 = 500×10 + 1 → 샘플 1kg 차감 후 나눔
                        # 잘못된 식: per_bag = total_w / bag_count  → 5001/10 = 500.1 (정합성 깨짐)
                        # 올바른 식: per_bag = (total_w - 1) / bag_count → 5000/10 = 500.0
                        sample_kg = SAMPLE_WEIGHT_KG
                        per_bag = (total_w - sample_kg) / bag_count if bag_count else 0
                        tonbags = [
                            {'sub_lt': i + 1, 'weight_kg': per_bag}
                            for i in range(bag_count)
                        ]
                
                # v3.8.4: inventory_id 전달하여 FK 연결
                tonbag_count = self._insert_tonbags(
                    lot_no, 
                    packing.get('sap_no', ''),
                    packing.get('bl_no', ''),
                    tonbags,
                    inventory_id=inventory_id
                )
                # v5.8.8: 톤백에도 con_return(컨테이너 반납일) 동일 적용
                if lot_data.get('con_return'):
                    try:
                        self.db.execute(
                            "UPDATE inventory_tonbag SET con_return = ? WHERE lot_no = ?",
                            (lot_data['con_return'], lot_no))
                    except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                        logger.debug(f"톤백 con_return 업데이트 스킵(컬럼 없을 수 있음): {_e}")
                
                # v3.8.4: 톤백 합계 = LOT 중량 검증
                if tonbag_count > 0:
                    tb_sum_row = self.db.fetchone(
                        "SELECT SUM(weight) as total FROM inventory_tonbag WHERE lot_no = ?",
                        (lot_no,))
                    tb_sum = (tb_sum_row['total'] if isinstance(tb_sum_row, dict) else tb_sum_row[0]) if tb_sum_row else 0
                    lot_weight = self._safe_parse_float(
                        packing.get('net_weight'))
                    if lot_weight > 0 and abs(tb_sum - lot_weight) > 0.5:
                        result['warnings'].append(
                            f"톤백 합계({tb_sum:.1f}kg) ≠ LOT 중량({lot_weight:.1f}kg) 차이: {abs(tb_sum - lot_weight):.1f}kg")
                
                # v5.1.4: 입고 후 즉시 정합성 검증 (트랜잭션 안)
                if hasattr(self, 'verify_lot_integrity'):
                    integrity = self.verify_lot_integrity(lot_no)
                    if not integrity.get('valid', True):
                        result['warnings'].extend(integrity.get('errors', []))
                        logger.warning(f"입고 후 정합성 경고 ({lot_no}): {integrity.get('errors')}")
                
                result['success'] = True
                result['message'] = f"입고 완료: {lot_no}"
                result['lot_no'] = lot_no
                result['created_lots'].append(lot_no)
                result['created_tonbags'] = tonbag_count
            
            self._log_operation("입고", {
                'lot_no': lot_no, 
                'tonbags': tonbag_count
            })
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"입고 처리 오류: {e}", exc_info=True)
            result['errors'].append(str(e))
        
        return result
    
    def _check_lot_exists(self, lot_no: str) -> bool:
        """LOT 존재 여부 확인"""
        try:
            row = self.db.fetchone(
                "SELECT 1 FROM inventory WHERE lot_no = ?", (lot_no,)
            )
            return row is not None
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError):
            return False
    
    def _prepare_lot_data(self, packing, bl_data=None, 
                          do_data=None) -> Dict:
        """LOT 데이터 준비 (v3.8.8: dict/PackingData/dataclass 모두 지원).
        
        변수 구분 (혼동 방지): arrival_date=입항일(날짜 YYYY-MM-DD), warehouse=창고(예: 광양),
        free_time_date=con_return=컨테이너 반납일, free_time=일수(반납일-입항일).
        """
        # v3.8.8: 모든 타입 → dict 변환 + 디버깅
        orig_type = type(packing).__name__
        if not isinstance(packing, dict):
            if hasattr(packing, 'to_dict'):
                packing = packing.to_dict()
            elif hasattr(packing, '_data'):
                packing = packing._data
            else:
                try:
                    from dataclasses import asdict
                    packing = asdict(packing)
                except (TypeError, ImportError):
                    packing = vars(packing) if hasattr(packing, '__dict__') else {}
        
        # 디버깅: lot_no 값 확인
        logger.info(f"[_prepare_lot_data] type={orig_type}, lot_no={packing.get('lot_no')!r}, keys={list(packing.keys())[:5]}")
        
        weight = self._safe_parse_float(
            packing.get('net_weight')
        )
        gross = self._safe_parse_float(
            packing.get('gross_weight')
        ) or weight
        bag_count = self._safe_parse_int(
            packing.get('mxbg_pallet')
        )
        
        lot_data = {
            'lot_no': packing.get('lot_no'),
            'product': packing.get('product', ''),
            'product_code': packing.get('product_code', ''),
            'bl_no': packing.get('bl_no', ''),
            'sap_no': packing.get('sap_no', ''),
            'container_no': packing.get('container_no', ''),
            'lot_sqm': packing.get('lot_sqm', ''),
            'net_weight': weight,
            'gross_weight': gross,
            'initial_weight': weight,
            'current_weight': weight,
            'picked_weight': 0,
            'mxbg_pallet': bag_count,
            'salar_invoice_no': packing.get('salar_invoice_no', ''),
            'ship_date': packing.get('ship_date', ''),
            'warehouse': packing.get('warehouse', DEFAULT_WAREHOUSE),
            'vessel': packing.get('vessel', ''),
            'inbound_date': date.today().strftime('%Y-%m-%d'),
            'status': STATUS_AVAILABLE,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # v3.8.7: Invoice 데이터 보완
        if packing.get('salar_invoice_no'):
            lot_data['salar_invoice_no'] = packing['salar_invoice_no']
        # v5.6.6: invoice_no fallback 제거 (salar_invoice_no 단일)
        
        # ship_date: 파싱 가능할 때만 설정. B/L·Invoice에서 채워져야 함.
        if packing.get('ship_date'):
            sd = self._safe_parse_date(packing['ship_date'])
            lot_data['ship_date'] = sd.strftime('%Y-%m-%d') if sd else ''
        
        # 입항일(arrival_date): 파싱된 값만 사용. 모를 때는 반드시 비움 — warehouse('광양')와 혼동 금지
        arrival_date = None
        if do_data and do_data.get('arrival_date'):
            arrival_date = self._safe_parse_date(do_data.get('arrival_date'))
        if not arrival_date and packing.get('arrival_date'):
            arrival_date = self._safe_parse_date(packing.get('arrival_date'))
        lot_data['arrival_date'] = arrival_date.strftime('%Y-%m-%d') if arrival_date else ''
        
        # con_return = 컨테이너 반납일 (D/O의 Free_Time 컬럼 = 반납일). free_time = (con_return - arrival_date) 일수
        # con_return / free_time_date 혼용 대응: 둘 다 확인
        con_return_str = (
            packing.get('con_return', '') or
            packing.get('free_time_date', '') or
            (do_data.get('free_time_date', '') if do_data else '')
        )
        con_return_date = self._safe_parse_date(con_return_str) if con_return_str else None
        lot_data['con_return'] = con_return_date.strftime('%Y-%m-%d') if con_return_date else ''
        
        free_time = 0
        if not con_return_str and (do_data or packing.get('free_time_date') is not None):
            logger.debug(f"[_prepare_lot_data] FREE TIME 0: con_return_date 미제공 lot_no={packing.get('lot_no')!r}")
        if con_return_date and arrival_date:
            free_time = (con_return_date - arrival_date).days
            if free_time < 0:
                free_time = 0
        
        # packing에서 이미 계산된 free_time(일수)이 있으면 우선 사용
        if packing.get('free_time'):
            try:
                free_time = int(float(packing['free_time']))
            except (ValueError, TypeError) as _e:
                logger.debug(f"free_time 변환 실패: {packing.get('free_time')!r} → {_e}")
        
        lot_data['free_time'] = free_time
        
        return lot_data
    
    def _insert_lot(self, lot_data: Dict) -> None:
        """LOT 삽입"""
        columns = ', '.join(lot_data.keys())
        placeholders = ', '.join(['?'] * len(lot_data))
        
        sql = f"INSERT INTO inventory ({columns}) VALUES ({placeholders})"
        self.db.execute(sql, tuple(lot_data.values()))
    
    def _insert_tonbags(self, lot_no: str, sap_no: str, bl_no: str,
                        tonbags: List[Dict], inventory_id: int = None) -> int:
        """톤백 삽입 (v5.2.0: tonbag_no TEXT + 샘플 하드스톱)"""
        if not tonbags:
            return 0
        
        count = 0
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = date.today().strftime('%Y-%m-%d')
        
        for tb in tonbags:
            weight = self._safe_parse_float(tb.get('weight_kg') or tb.get('weight'))
            raw_sub_lt, raw_key = _get_sub_lt_raw(tb)
            source_sub_lt_raw = None if raw_sub_lt in (None, '') else str(raw_sub_lt).strip()
            source_sub_lt_hdr = raw_key
            sub_lt = raw_sub_lt if raw_sub_lt not in (None, '') else (count + 1)
            # v5.2.0: tonbag_no TEXT (앞자리 0 보존) + alias(sub_lt/dmsub_lt/DM_SUB_LT)
            tonbag_no = _normalize_tonbag_no_from_raw_v530(sub_lt, fallback_seq=(count+1), is_sample=False)
            
            sql = """
                INSERT INTO inventory_tonbag 
                (inventory_id, lot_no, sap_no, bl_no, sub_lt, tonbag_no,
                 weight, status, is_sample, inbound_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'AVAILABLE', 0, ?, ?)
            """
            self.db.execute(sql, (inventory_id, lot_no, sap_no, bl_no, 
                                  sub_lt, tonbag_no, weight, today, now))
            count += 1
        
        # v5.5.3: 샘플 톤백 자동 생성 (sub_lt=0, tonbag_no="S00", 1kg, is_sample=1)
        # ★ 샘플 생성 실패 = 하드스톱 (All-or-Nothing)
        self.db.execute("""
            INSERT INTO inventory_tonbag 
            (inventory_id, lot_no, sap_no, bl_no, sub_lt, tonbag_no,
             weight, status, is_sample, inbound_date, created_at)
            VALUES (?, ?, ?, ?, 0, 'S00', 1.0, 'AVAILABLE', 1, ?, ?)
        """, (inventory_id, lot_no, sap_no, bl_no, today, now))
        count += 1
        logger.info(f"[_insert_tonbags] 샘플 톤백 생성: {lot_no}/S00 (1kg)")
        
        # v5.2.0: 샘플 존재 검증 (하드스톱)
        sample_check = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM inventory_tonbag WHERE lot_no = ? AND is_sample = 1",
            (lot_no,))
        sample_cnt = (sample_check['cnt'] if isinstance(sample_check, dict) else sample_check[0]) if sample_check else 0
        if sample_cnt != 1:
            raise ValueError(f"샘플 정책 위반: LOT {lot_no}에 샘플 {sample_cnt}개 (필수 정확히 1개)")
        
        return count
    

    # NOTE: process_inbound_safe, preflight_check_inbound
    #   → PreflightMixin으로 이관 완료 (v3.8.4 데드코드 정리)