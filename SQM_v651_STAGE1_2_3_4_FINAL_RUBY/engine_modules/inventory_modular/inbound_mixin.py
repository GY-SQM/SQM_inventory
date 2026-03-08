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

from .base import InventoryBaseMixin
import re  # v5.3.0
from utils.common import normalize_lot, norm_tonbag_no_std, norm_bl_no, norm_sap_no, norm_container_no

logger = logging.getLogger(__name__)

# 비즈니스 기본값
from core.constants import DEFAULT_WAREHOUSE, SAMPLE_WEIGHT_KG, STATUS_AVAILABLE
from engine_modules.tonbag_weight_rules import build_rule_result






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

class InboundMixin(InventoryBaseMixin):
    """입고 처리 Mixin (v3.6.6: SQMDatabase API 기반)"""
    
    def process_inbound(self, packing_data, invoice_data=None, 
                        bl_data=None, do_data=None,
                        source_type: str = '', source_file: str = '') -> Dict:
        """
        입고 처리
        
        Args:
            packing_data: 패킹 리스트 데이터 (dict 또는 PackingData)
            invoice_data: 인보이스 데이터 (선택)
            bl_data: B/L 데이터 (선택)
            do_data: D/O 데이터 (선택)
            source_type: 입고 출처 ('PDF', 'EXCEL_MANUAL', 'EXCEL_PASTE', '')
            source_file: 원본 파일명 (감사 추적용)
        
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
            
            lot_no = normalize_lot(packing.get('lot_no')) or str(packing.get('lot_no') or '').strip()
            if not lot_no:
                result['errors'].append("LOT 번호가 비어 있습니다.")
                return result

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
            
            # v6.12.1: SAP 번호 중복 검증 (경고 — 동일 SAP로 다중 LOT 입고 감지)
            sap_no_raw = packing.get('sap_no', '')
            if sap_no_raw:
                sap_std = norm_sap_no(sap_no_raw) or str(sap_no_raw).strip()
                if sap_std:
                    try:
                        dup_row = self.db.fetchone(
                            "SELECT lot_no FROM inventory WHERE sap_no = ? AND lot_no != ?",
                            (sap_std, lot_no))
                        if dup_row:
                            existing_lot = dup_row['lot_no'] if isinstance(dup_row, dict) else dup_row[0]
                            result['warnings'].append(
                                f"SAP 번호 중복: '{sap_std}' — 기존 LOT {existing_lot}에도 동일 SAP가 있습니다. "
                                f"의도된 경우 무시 가능합니다."
                            )
                    except (sqlite3.OperationalError, KeyError):
                        pass  # sap_no 컬럼 없는 구버전 DB — 스킵

            # v6.12.1: B/L 번호 형식 검증 (경고만)
            bl_no_raw = packing.get('bl_no', '')
            if bl_no_raw:
                bl_str = str(bl_no_raw).strip()
                # B/L 일반 패턴: XXXX + 숫자 (예: HDMU1234567, MAEU9876543)
                if bl_str and not re.match(r'^[A-Z]{4}\d{7,}$', bl_str.upper()):
                    result['warnings'].append(
                        f"B/L 번호 형식 주의: '{bl_str}' (표준: 영문4자리+숫자7자리 이상)"
                    )
            
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
                        rule = build_rule_result(total_w, bag_count, sample_kg)
                        per_bag = rule.tonbag_weight_kg
                        result['rule_status'] = rule.rule_status
                        tonbags = [
                            {'sub_lt': i + 1, 'weight_kg': per_bag}
                            for i in range(bag_count)
                        ]
                
                # v3.8.4: inventory_id 전달하여 FK 연결
                sap_std = norm_sap_no(packing.get('sap_no')) or ''
                bl_std = norm_bl_no(packing.get('bl_no')) or ''
                tonbag_count = self._insert_tonbags(
                    lot_no,
                    sap_std,
                    bl_std,
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
                
                # v6.12 Addon-A: 입고 stock_movement 이력 기록 (감사 추적)
                # v6.12.1: source_type, source_file 추가
                try:
                    _src_type = source_type or 'UNKNOWN'
                    self.db.execute("""
                        INSERT INTO stock_movement
                        (lot_no, movement_type, qty_kg, remarks, source_type, source_file, created_at)
                        VALUES (?, 'INBOUND', ?, ?, ?, ?, ?)
                    """, (lot_no, weight,
                           f"tonbags={tonbag_count}, product={packing.get('product','')}, "
                           f"sap={packing.get('sap_no','')}, bl={packing.get('bl_no','')}",
                           _src_type, source_file or '',
                           datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    logger.info(f"[stock_movement] INBOUND 기록: {lot_no}, {weight}kg, source={_src_type}")
                except Exception as _sm_e:
                    logger.debug(f"[stock_movement] INBOUND 기록 스킵: {_sm_e}")
                
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
        
        lot_no_std = normalize_lot(packing.get('lot_no')) or str(packing.get('lot_no') or '').strip()
        bl_std = norm_bl_no(packing.get('bl_no')) or str(packing.get('bl_no') or '').strip()
        sap_std = norm_sap_no(packing.get('sap_no')) or str(packing.get('sap_no') or '').strip()
        lot_data = {
            'lot_no': lot_no_std or packing.get('lot_no'),
            'product': packing.get('product', ''),
            'product_code': packing.get('product_code', ''),
            'bl_no': bl_std or packing.get('bl_no', ''),
            'sap_no': sap_std or packing.get('sap_no', ''),
            'container_no': norm_container_no(packing.get('container_no')) or str(packing.get('container_no') or ''),
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
        
        # v6.2.7: product_code 자동감지 (비어있으면 product_master에서 매칭)
        if not lot_data.get('product_code'):
            try:
                from gui_app_modular.dialogs.product_master_helper import auto_detect_product_code
                detected = auto_detect_product_code(self.db, lot_data.get('product', ''))
                if detected:
                    lot_data['product_code'] = detected
            except Exception:
                pass
        
        return lot_data
    
    def _insert_lot(self, lot_data: Dict) -> None:
        """LOT 삽입 (v6.2.8: 컬럼명 화이트리스트 검증)"""
        # 안전성: 컬럼명이 알파벳+밑줄만 포함하는지 검증
        import re as _re
        for col in lot_data.keys():
            if not _re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", col):
                raise ValueError(f"잘못된 컬럼명: {col!r}")
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
            # v6.2.7: raw_sub_lt → 정규화만 사용 (미사용 변수 제거)
            # 정규화: 001/1 -> tonbag_no "001", sub_lt 1 (문자열 0 패딩 + DB는 정수)
            tonbag_no, sub_lt_int = norm_tonbag_no_std(raw_sub_lt, is_sample=False)
            if not tonbag_no or sub_lt_int == 0:
                fallback = count + 1
                tonbag_no = str(fallback).zfill(3)
                sub_lt_int = fallback

            sql = """
                INSERT INTO inventory_tonbag 
                (inventory_id, lot_no, sap_no, bl_no, sub_lt, tonbag_no,
                 weight, status, is_sample, inbound_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'AVAILABLE', 0, ?, ?)
            """
            self.db.execute(sql, (inventory_id, lot_no, sap_no, bl_no,
                                  sub_lt_int, tonbag_no, weight, today, now))
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
        
        # v6.12 Addon-B: tonbag_uid 명시적 백필 보장
        # SQLite TRIGGER(trg_tonbag_uid_insert)가 정상 동작하면 이미 UID가 있지만,
        # 트리거 미생성/마이그레이션 누락 시에도 UID를 보장합니다.
        try:
            null_uid_count = self.db.fetchone(
                "SELECT COUNT(*) as cnt FROM inventory_tonbag "
                "WHERE lot_no = ? AND (tonbag_uid IS NULL OR tonbag_uid = '')",
                (lot_no,))
            null_cnt = (null_uid_count['cnt'] if isinstance(null_uid_count, dict)
                        else null_uid_count[0]) if null_uid_count else 0
            if null_cnt > 0:
                # 샘플 UID
                self.db.execute(
                    "UPDATE inventory_tonbag SET tonbag_uid = lot_no || '-S00' "
                    "WHERE lot_no = ? AND (COALESCE(is_sample,0)=1 OR sub_lt=0) "
                    "AND (tonbag_uid IS NULL OR tonbag_uid = '')",
                    (lot_no,))
                # 일반 톤백 UID
                self.db.execute(
                    "UPDATE inventory_tonbag SET tonbag_uid = lot_no || '-' || tonbag_no "
                    "WHERE lot_no = ? AND COALESCE(is_sample,0)=0 AND sub_lt > 0 "
                    "AND (tonbag_uid IS NULL OR tonbag_uid = '')",
                    (lot_no,))
                logger.info(f"[_insert_tonbags] tonbag_uid 백필: {lot_no} ({null_cnt}건)")
        except Exception as _uid_e:
            logger.debug(f"[_insert_tonbags] tonbag_uid 백필 스킵: {_uid_e}")
        
        return count
    

    # NOTE: process_inbound_safe, preflight_check_inbound
    #   → PreflightMixin으로 이관 완료 (v3.8.4 데드코드 정리)