# -*- coding: utf-8 -*-
"""
SQM Inventory Engine - Tonbag Mixin
===================================

v2.9.91 - Extracted from inventory.py

Tonbag (Sub LOT) management functions
"""

import sqlite3
import logging
from datetime import date
from typing import Dict

logger = logging.getLogger(__name__)


class TonbagMixin:
    """
    Tonbag management mixin
    
    Methods for tonbag CRUD, location updates, and status queries
    """
    
    # NOTE: get_tonbags, get_sublots → QueryMixin으로 이관 완료 (v3.8.4 데드코드 정리)
    
    def get_tonbag_summary(self, lot_no: str) -> Dict:
        """
        Get tonbag summary for a LOT
        
        Args:
            lot_no: LOT number
            
        Returns:
            Summary dict with counts and weights
        """
        query = """
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN status = 'AVAILABLE' THEN 1 ELSE 0 END) as available_count,
                SUM(CASE WHEN status = 'PICKED' THEN 1 ELSE 0 END) as picked_count,
                SUM(CASE WHEN status = 'SAMPLE' THEN 1 ELSE 0 END) as sample_count,
                SUM(weight) as total_weight,
                SUM(CASE WHEN status = 'AVAILABLE' THEN weight ELSE 0 END) as available_weight,
                SUM(CASE WHEN status = 'PICKED' THEN weight ELSE 0 END) as picked_weight
            FROM inventory_tonbag
            WHERE lot_no = ?
        """
        
        row = self.db.fetchone(query, (lot_no,))
        
        if row:
            return {
                'lot_no': lot_no,
                'total_count': row['total_count'] or 0,
                'available_count': row['available_count'] or 0,
                'picked_count': row['picked_count'] or 0,
                'sample_count': row['sample_count'] or 0,
                'total_weight': row['total_weight'] or 0,
                'available_weight': row['available_weight'] or 0,
                'picked_weight': row['picked_weight'] or 0
            }
        
        return {
            'lot_no': lot_no,
            'total_count': 0,
            'available_count': 0,
            'picked_count': 0,
            'sample_count': 0,
            'total_weight': 0,
            'available_weight': 0,
            'picked_weight': 0
        }
    
    def get_all_sublots_summary(self) -> Dict:
        """
        Get summary of all sublots
        
        Returns:
            Summary dict
        """
        query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'AVAILABLE' THEN 1 ELSE 0 END) as available,
                SUM(CASE WHEN status = 'PICKED' THEN 1 ELSE 0 END) as picked,
                SUM(weight) as total_weight,
                SUM(CASE WHEN status = 'AVAILABLE' THEN weight ELSE 0 END) as available_weight
            FROM inventory_tonbag
        """
        
        row = self.db.fetchone(query)
        
        if row:
            return {
                'total': row['total'] or 0,
                'available': row['available'] or 0,
                'picked': row['picked'] or 0,
                'total_weight_kg': row['total_weight'] or 0,
                'available_weight_kg': row['available_weight'] or 0
            }
        
        return {'total': 0, 'available': 0, 'picked': 0, 
                'total_weight_kg': 0, 'available_weight_kg': 0}
    
    def get_all_tonbags_summary(self) -> Dict:
        """Alias for get_all_sublots_summary"""
        return self.get_all_sublots_summary()
    
    def update_tonbag_location(self, lot_no: str, sub_lt: int, 
                               location: str, 
                               source: str = 'MANUAL') -> Dict:
        """
        Update tonbag location with history tracking (v7.0.1)
        
        Args:
            lot_no: LOT number
            sub_lt: Sub LOT number
            location: New location
            source: Source of change ('MANUAL', 'EXCEL_UPLOAD', 'API')
            
        Returns:
            Result dict with from_location, to_location
        """
        from datetime import datetime
        
        result = {
            'success': False,
            'error': None,
            'from_location': None,
            'to_location': None
        }
        
        try:
            # Check if tonbag exists
            existing = self.db.fetchone(
                "SELECT lot_no, sub_lt, location, weight FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
                (lot_no, sub_lt)
            )
            
            if not existing:
                result['error'] = f"Tonbag not found: {lot_no}-{sub_lt}"
                return result
            
            from_loc = existing.get('location') or ''
            to_loc = location.strip()
            tb_weight = existing.get('weight') or 0
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Update location + location_updated_at
            self.db.execute("""
                UPDATE inventory_tonbag 
                SET location = ?,
                    location_updated_at = ?,
                    updated_at = ?
                WHERE lot_no = ? AND sub_lt = ?
            """, (to_loc, now, now, lot_no, sub_lt))
            
            # Record movement history (v7.0.1: RELOCATE)
            # 위치가 실제로 변경된 경우만 이력 기록
            if from_loc != to_loc:
                self.db.execute("""
                    INSERT INTO stock_movement 
                    (lot_no, movement_type, qty_kg, from_location, to_location, remarks, created_at)
                    VALUES (?, 'RELOCATE', ?, ?, ?, ?, ?)
                """, (lot_no, tb_weight, from_loc, to_loc,
                      f"sub_lt={sub_lt}, source={source}", now))
            
            result['success'] = True
            result['from_location'] = from_loc
            result['to_location'] = to_loc
            logger.info(f"Location updated: {lot_no}-{sub_lt} [{from_loc}] -> [{to_loc}] (source={source})")
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            result['error'] = str(e)
            logger.error(f"Location update error: {e}")
        
        return result
    
    def update_tonbag_status(self, lot_no: str, sub_lt: int,
                             status: str, picked_to: str = None,
                             pick_ref: str = None) -> Dict:
        """
        Update tonbag status (v6.0.7+: PICKED 전환은 AVAILABLE/RESERVED만 허용)
        
        Args:
            lot_no: LOT number
            sub_lt: Sub LOT number
            status: New status (AVAILABLE, PICKED, SAMPLE 등)
            picked_to: Customer name (for PICKED status)
            pick_ref: Sale reference (for PICKED status)
            
        Returns:
            Result dict (success, error)
        """
        result = {'success': False, 'error': None}
        
        try:
            # v6.0.7+ 상태 전이 화이트리스트: PICKED로의 전환은 AVAILABLE/RESERVED에서만 허용
            new_status = (status or '').strip().upper()
            if new_status == 'PICKED':
                row = self.db.fetchone(
                    "SELECT status FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
                    (lot_no, sub_lt)
                )
                if row:
                    cur = (row.get('status') or '').strip().upper()
                    if cur not in ('AVAILABLE', 'RESERVED'):
                        result['error'] = f"상태 전이 불가: 현재 {cur} → PICKED (AVAILABLE/RESERVED만 허용)"
                        logger.warning("update_tonbag_status 차단: %s-%s %s → PICKED", lot_no, sub_lt, cur)
                        return result
                else:
                    result['error'] = f"톤백 없음: {lot_no}-{sub_lt}"
                    return result
            
            update_fields = ["status = ?"]
            params = [status]
            
            if status == 'PICKED':
                update_fields.append("outbound_date = ?")
                params.append(date.today())
                
                if picked_to:
                    update_fields.append("picked_to = ?")
                    params.append(picked_to)
                
                if pick_ref:
                    update_fields.append("pick_ref = ?")
                    params.append(pick_ref)
            
            elif status == 'AVAILABLE':
                # Clear outbound info when returning to available
                update_fields.extend([
                    "outbound_date = NULL",
                    "picked_to = NULL",
                    "pick_ref = NULL"
                ])
            
            params.extend([lot_no, sub_lt])
            
            query = f"""
                UPDATE inventory_tonbag 
                SET {', '.join(update_fields)}
                WHERE lot_no = ? AND sub_lt = ?
            """
            
            self.db.execute(query, tuple(params))
            result['success'] = True
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            result['error'] = str(e)
            logger.error(f"Status update error: {e}")
        
        return result
    
    def create_tonbags_for_lot(self, lot_no: str, count: int, 
                               weight_per_bag: float,
                               inbound_date: date = None) -> Dict:
        """
        Create tonbags for a LOT
        
        Args:
            lot_no: LOT number
            count: Number of tonbags to create
            weight_per_bag: Weight per tonbag (kg)
            inbound_date: Inbound date
            
        Returns:
            Result dict
        """
        result = {
            'success': False,
            'created': 0,
            'error': None
        }
        
        if inbound_date is None:
            inbound_date = date.today()
        
        try:
            # Get current max sub_lt for this lot
            row = self.db.fetchone(
                "SELECT MAX(sub_lt) as max_sub FROM inventory_tonbag WHERE lot_no = ?",
                (lot_no,)
            )
            start_sub = (row['max_sub'] or 0) + 1
            
            # Insert tonbags
            for i in range(count):
                sub_lt = start_sub + i
                self.db.execute("""
                    INSERT INTO inventory_tonbag 
                    (lot_no, sub_lt, weight, status, inbound_date)
                    VALUES (?, ?, ?, 'AVAILABLE', ?)
                """, (lot_no, sub_lt, weight_per_bag, inbound_date))
                result['created'] += 1
            
            result['success'] = True
            logger.info(f"Created {count} tonbags for {lot_no}")
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            result['error'] = str(e)
            logger.error(f"Create tonbags error: {e}")
        
        return result
    
    def delete_tonbag(self, lot_no: str, sub_lt: int) -> Dict:
        """
        Delete a tonbag (only if AVAILABLE)
        
        Args:
            lot_no: LOT number
            sub_lt: Sub LOT number
            
        Returns:
            Result dict
        """
        result = {'success': False, 'error': None}
        
        try:
            # Check status
            existing = self.db.fetchone(
                "SELECT status FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
                (lot_no, sub_lt)
            )
            
            if not existing:
                result['error'] = "Tonbag not found"
                return result
            
            if existing['status'] != 'AVAILABLE':
                result['error'] = f"Cannot delete tonbag with status: {existing['status']}"
                return result
            
            self.db.execute(
                "DELETE FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
                (lot_no, sub_lt)
            )
            
            result['success'] = True
            logger.info(f"Deleted tonbag: {lot_no}-{sub_lt}")
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            result['error'] = str(e)
            logger.error(f"Delete tonbag error: {e}")
        
        return result
