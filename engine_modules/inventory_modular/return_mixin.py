# -*- coding: utf-8 -*-
"""
SQM Inventory Engine - Return Mixin
===================================

v2.9.91 - Extracted from inventory.py

Return (반품) processing functions
"""

import logging
from datetime import date, datetime
from typing import List, Dict

logger = logging.getLogger(__name__)


class ReturnMixin:
    """
    Return processing mixin
    
    Methods for processing returns (PICKED -> AVAILABLE)
    """
    
    def get_returnable_tonbags(self, lot_no: str = None) -> List[Dict]:
        """
        Get tonbags that can be returned (status = PICKED)
        
        Args:
            lot_no: Optional filter by LOT number
            
        Returns:
            List of returnable tonbags
        """
        query = """
            SELECT 
                t.lot_no, t.sub_lt, t.weight, t.location,
                t.status, t.outbound_date, t.picked_to, t.sale_ref,
                i.sap_no, i.bl_no, i.product
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON t.lot_no = i.lot_no
            WHERE t.status = 'PICKED'
        """
        params = []
        
        if lot_no:
            query += " AND t.lot_no = ?"
            params.append(lot_no)
        
        query += " ORDER BY t.lot_no, t.sub_lt"
        
        return self.db.fetchall(query, tuple(params))
    
    def get_return_history(self, lot_no: str = None, limit: int = 100) -> List[Dict]:
        """
        Get return history
        
        Args:
            lot_no: Optional filter by LOT number
            limit: Maximum records to return
            
        Returns:
            List of return records
        """
        query = """
            SELECT 
                r.id, r.lot_no, r.sub_lt, r.return_date,
                r.original_customer, r.original_sale_ref,
                r.reason, r.remark, r.created_at,
                i.sap_no, i.product
            FROM return_history r
            LEFT JOIN inventory i ON r.lot_no = i.lot_no
            WHERE 1=1
        """
        params = []
        
        if lot_no:
            query += " AND r.lot_no = ?"
            params.append(lot_no)
        
        query += f" ORDER BY r.created_at DESC LIMIT {limit}"
        
        return self.db.fetchall(query, tuple(params))
    
    def process_return(self, return_data: list) -> Dict:
        """
        반품 처리 (v5.1.5: 정합성 게이트 + stock_movement 이력 + picked_date 초기화)
        
        Args:
            return_data: List of return items
                [{'lot_no': '...', 'sub_lt': 1, 'reason': '...', 'remark': '...'}, ...]
            
        Returns:
            Processing result dict
        """
        result = {
            'success': False,
            'returned': 0,
            'skipped': 0,
            'errors': [],
            'details': [],
            'integrity': {},  # v5.1.5: LOT별 정합성 결과
        }
        
        if not return_data:
            result['errors'].append("No return data provided")
            return result
        
        try:
            with self.db.transaction("IMMEDIATE"):
                for item in return_data:
                    lot_no = str(item.get('lot_no') or '').strip()
                    sub_lt = item.get('sub_lt')
                    reason = item.get('reason', '')
                    remark = item.get('remark', '')
                    
                    if not lot_no or sub_lt is None:
                        result['errors'].append(f"Invalid item: {item}")
                        result['skipped'] += 1
                        continue
                    
                    # Get current tonbag info
                    tonbag = self.db.fetchone("""
                        SELECT lot_no, sub_lt, weight, status, picked_to, sale_ref, is_sample 
                        FROM inventory_tonbag 
                        WHERE lot_no = ? AND sub_lt = ?
                    """, (lot_no, sub_lt))
                    
                    if not tonbag:
                        result['errors'].append(f"Tonbag not found: {lot_no}-{sub_lt}")
                        result['skipped'] += 1
                        continue
                    
                    if tonbag['status'] not in ('PICKED', 'CONFIRMED', 'SHIPPED', 'SOLD', 'RESERVED'):
                        result['errors'].append(
                            f"Cannot return tonbag with status {tonbag['status']}: {lot_no}-{sub_lt}"
                        )
                        result['skipped'] += 1
                        continue
                    
                    tb_weight = float(tonbag['weight'] or 0)
                    
                    # Save return history
                    self.db.execute("""
                        INSERT INTO return_history 
                        (lot_no, sub_lt, return_date, original_customer, 
                         original_sale_ref, reason, remark)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        lot_no, sub_lt, date.today(),
                        tonbag['picked_to'], tonbag.get('sale_ref', ''),
                        reason, remark
                    ))
                    
                    # v5.1.5: stock_movement 이력 추가 (반품)
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.db.execute("""
                        INSERT INTO stock_movement 
                        (lot_no, movement_type, qty_kg, remarks, created_at)
                        VALUES (?, 'RETURN', ?, ?, ?)
                    """, (lot_no, tb_weight,
                          f"sub_lt={sub_lt}, customer={tonbag.get('picked_to','')}, reason={reason}",
                          now))
                    
                    was_reserved = tonbag['status'] == 'RESERVED'

                    # v5.1.5: 톤백 상태 초기화 (picked_date도 포함)
                    self.db.execute("""
                        UPDATE inventory_tonbag 
                        SET status = 'AVAILABLE',
                            outbound_date = NULL,
                            picked_date = NULL,
                            picked_to = NULL,
                            sale_ref = NULL,
                            updated_at = ?
                        WHERE lot_no = ? AND sub_lt = ?
                    """, (now, lot_no, sub_lt))

                    # v5.9.3: RESERVED였으면 allocation_plan도 CANCELLED 처리
                    if was_reserved:
                        try:
                            self.db.execute("""
                                UPDATE allocation_plan SET status = 'CANCELLED', cancelled_at = ?
                                WHERE lot_no = ? AND sub_lt = ? AND status = 'RESERVED'
                            """, (now, lot_no, sub_lt))
                        except Exception as _e:
                            logger.debug(f"Suppressed: {_e}")
                    else:
                        # PICKED/SOLD: inventory current_weight 복구
                        self.db.execute("""
                            UPDATE inventory 
                            SET current_weight = current_weight + ?,
                                picked_weight = MAX(0, picked_weight - ?),
                                updated_at = ?
                            WHERE lot_no = ?
                        """, (tb_weight, tb_weight, now, lot_no))
                    
                    result['returned'] += 1
                    result['details'].append({
                        'lot_no': lot_no,
                        'sub_lt': sub_lt,
                        'weight': tb_weight,
                        'original_customer': tonbag.get('picked_to', '')
                    })
                    
                    logger.info(f"Returned: {lot_no}-{sub_lt} ({tb_weight:.0f}kg)")
                
                # v5.2.0: 반품된 모든 LOT의 status 재계산 (래퍼 제거 → 직접 호출)
                returned_lots = set(d['lot_no'] for d in result['details'])
                for rlt in returned_lots:
                    self._recalc_lot_status(rlt)
                    logger.info(f"LOT status 재계산(반품): {rlt}")
                
                # v5.1.5: 정합성 검증 (트랜잭션 안에서)
                if hasattr(self, 'verify_lot_integrity') and returned_lots:
                    for rlt in returned_lots:
                        integrity = self.verify_lot_integrity(rlt)
                        result['integrity'][rlt] = integrity
                        if not integrity.get('valid', True):
                            raise ValueError(
                                f"반품 후 정합성 실패 ({rlt}): {integrity.get('errors', [])}"
                            )
                
                result['success'] = result['returned'] > 0
                
        except (ValueError, TypeError, AttributeError) as e:
            result['errors'].append(f"Return processing error: {e}")
            logger.exception("Return processing error")
        
        return result
    
    def return_single_tonbag(self, lot_no: str, sub_lt: int,
                             reason: str = None, remark: str = None) -> Dict:
        """
        Return a single tonbag
        
        Args:
            lot_no: LOT number
            sub_lt: Sub LOT number
            reason: Return reason
            remark: Additional remarks
            
        Returns:
            Result dict
        """
        return self.process_return([{
            'lot_no': lot_no,
            'sub_lt': sub_lt,
            'reason': reason or '',
            'remark': remark or ''
        }])
    
    def bulk_return_by_lot(self, lot_no: str, reason: str = None) -> Dict:
        """
        Return all PICKED tonbags for a LOT
        
        Args:
            lot_no: LOT number
            reason: Return reason
            
        Returns:
            Result dict
        """
        # Get all picked tonbags for this lot
        picked = self.db.fetchall("""
            SELECT lot_no, sub_lt FROM inventory_tonbag
            WHERE lot_no = ? AND status = 'PICKED'
        """, (lot_no,))
        
        if not picked:
            return {
                'success': False,
                'returned': 0,
                'errors': [f"No picked tonbags found for LOT: {lot_no}"]
            }
        
        return_data = [
            {'lot_no': row['lot_no'], 'sub_lt': row['sub_lt'], 'reason': reason or ''}
            for row in picked
        ]
        
        return self.process_return(return_data)

    def _recalc_lot_status_return(self, lot_no: str):
        """DEPRECATED(v5.2.0): _recalc_lot_status()를 직접 호출하세요"""
        self._recalc_lot_status(lot_no)
