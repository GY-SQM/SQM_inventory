# -*- coding: utf-8 -*-
"""
SQM v4.0.1 — 입고 서류 업데이트 Mixin
=======================================

inbound_processor.py에서 분리:
- Invoice/BL/DO 기반 기존 LOT 업데이트
- Free Time 계산
- Excel 일괄 입고
"""
import os
import sqlite3
import logging
from ..utils.custom_messagebox import CustomMessageBox
from datetime import datetime, timedelta
from typing import Optional, Any

logger = logging.getLogger(__name__)


class InboundUpdateMixin:
    """입고 서류 업데이트 + Excel 입고 Mixin"""

    def _update_existing_lots_from_invoice(self, inv_data, lot_numbers: list) -> int:
        """Invoice 정보로 기존 LOT 업데이트 (SAP NO, Invoice No 등)
        
        v3.6.9: All-or-Nothing 트랜잭션으로 래핑
        
        Returns:
            int: 업데이트된 LOT 수
        """
        updated_count = 0
        sap_no = getattr(inv_data, 'sap_no', '') or ''
        salar_inv_no = getattr(inv_data, 'salar_invoice_no', '') or ''
        ship_date = getattr(inv_data, 'invoice_date', None)
        
        try:
            if not (hasattr(self, 'engine') and hasattr(self.engine, 'db')):
                return 0
            
            with self.engine.db.transaction():
                for lot_no in lot_numbers:
                    lot_no = lot_no.strip()
                    if not lot_no:
                        continue
                    
                    # DB에서 LOT 존재 확인
                    if hasattr(self.engine, '_check_lot_exists'):
                        if not self.engine._check_lot_exists(lot_no):
                            self._log(f"WARNING LOT {lot_no} DB에 없음 - 스킵")
                            continue
                    
                    # 업데이트 쿼리
                    updates = []
                    params = []
                    
                    if sap_no:
                        updates.append("sap_no = ?")
                        params.append(sap_no)
                    if salar_inv_no:
                        updates.append("salar_invoice_no = ?")
                        params.append(salar_inv_no)
                    if ship_date:
                        updates.append("ship_date = ?")
                        params.append(str(ship_date))
                    
                    if updates:
                        sql = f"UPDATE inventory SET {', '.join(updates)} WHERE lot_no = ?"
                        params.append(lot_no)
                        self.engine.db.execute(sql, tuple(params))
                        updated_count += 1
                        self._log(f"OK Invoice → LOT {lot_no} 업데이트 (SAP: {sap_no})")
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            updated_count = 0
            logger.error(f"Invoice LOT 업데이트 오류: {e}", exc_info=True)
            self._log(f"X Invoice 업데이트 오류 (롤백됨): {e}")
        
        return updated_count
    
    def _update_existing_lots_from_bl(self, bl_data) -> int:
        """B/L 정보로 기존 LOT 업데이트 (BL No, 선적일 등)
        
        v3.6.9: All-or-Nothing 트랜잭션으로 래핑
        
        Returns:
            int: 업데이트된 LOT 수
        """
        updated_count = 0
        bl_no = getattr(bl_data, 'bl_no', '') or ''
        sap_no = getattr(bl_data, 'sap_no', '') or ''
        vessel = getattr(bl_data, 'vessel', '') or ''
        ship_date = getattr(bl_data, 'shipped_on_board_date', None) or getattr(bl_data, 'ship_date', None)
        
        if not bl_no:
            return 0
        
        try:
            if not (hasattr(self, 'engine') and hasattr(self.engine, 'db')):
                return 0
            
            with self.engine.db.transaction():
                # SAP NO로 먼저 매칭 시도
                if sap_no:
                    rows = self.engine.db.fetchall(
                        "SELECT lot_no FROM inventory WHERE sap_no = ?", (sap_no,)
                    )
                    if rows:
                        for row in rows:
                            lot_no = row[0] if isinstance(row, (list, tuple)) else (row['lot_no'] if 'lot_no' in row.keys() else str(row[0]))
                            updates = ["bl_no = ?"]
                            params = [bl_no]
                            if ship_date:
                                updates.append("ship_date = ?")
                                params.append(str(ship_date))
                            
                            sql = f"UPDATE inventory SET {', '.join(updates)} WHERE lot_no = ?"
                            params.append(lot_no)
                            self.engine.db.execute(sql, tuple(params))
                            updated_count += 1
                            self._log(f"OK B/L → LOT {lot_no} 업데이트 (BL: {bl_no})")
                
                # SAP NO로 못 찾으면 vessel로 매칭
                if updated_count == 0 and vessel:
                    rows = self.engine.db.fetchall(
                        "SELECT lot_no FROM inventory WHERE vessel LIKE ? AND (bl_no IS NULL OR bl_no = '')",
                        (f"%{vessel}%",)
                    )
                    if rows:
                        for row in rows:
                            lot_no = row[0] if isinstance(row, (list, tuple)) else (row['lot_no'] if 'lot_no' in row.keys() else str(row[0]))
                            updates = ["bl_no = ?"]
                            params = [bl_no]
                            if ship_date:
                                updates.append("ship_date = ?")
                                params.append(str(ship_date))
                            
                            sql = f"UPDATE inventory SET {', '.join(updates)} WHERE lot_no = ?"
                            params.append(lot_no)
                            self.engine.db.execute(sql, tuple(params))
                            updated_count += 1
                            self._log(f"OK B/L(vessel) → LOT {lot_no} 업데이트 (BL: {bl_no})")
        
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            updated_count = 0
            logger.error(f"B/L LOT 업데이트 오류: {e}", exc_info=True)
            self._log(f"X B/L 업데이트 오류 (롤백됨): {e}")
        
        return updated_count
    
    def _update_existing_lots_from_do(self, do_data) -> int:
        """D/O 정보로 기존 LOT 업데이트 (도착일, Free Time 일수, BL No 등)
        
        v3.8.7: Free Time 일수 계산 추가
                free_time = Free Time 날짜 - Arrival Date (일수)
        
        Returns:
            int: 업데이트된 LOT 수
        """
        updated_count = 0
        bl_no = getattr(do_data, 'bl_no', '') or ''
        arrival_date = getattr(do_data, 'arrival_date', None)
        sap_no = getattr(do_data, 'sap_no', '') or ''
        vessel = getattr(do_data, 'vessel', '') or ''
        
        # ★★★ v3.8.7: Free Time 일수 계산 ★★★
        free_time_days = self._calculate_free_time_days(do_data, arrival_date)
        
        try:
            if not (hasattr(self, 'engine') and hasattr(self.engine, 'db')):
                return 0
            
            with self.engine.db.transaction():
                match_conditions = []
                
                # BL NO 매칭
                if bl_no:
                    bl_clean = bl_no
                    for prefix in ['MAEU', 'MSCU', 'HLCU', 'CMDU', 'EGLV', 'COSU', 'OOLU', 'YMLU']:
                        if bl_no.upper().startswith(prefix):
                            bl_clean = bl_no[len(prefix):]
                            break
                    
                    rows = self.engine.db.fetchall(
                        "SELECT lot_no FROM inventory WHERE bl_no LIKE ? OR bl_no LIKE ?",
                        (f"%{bl_no}%", f"%{bl_clean}%")
                    )
                    match_conditions = rows
                
                # BL로 못 찾으면 SAP NO
                if not match_conditions and sap_no:
                    match_conditions = self.engine.db.fetchall(
                        "SELECT lot_no FROM inventory WHERE sap_no = ?", (sap_no,)
                    )
                
                # SAP NO로도 못 찾으면 vessel
                if not match_conditions and vessel:
                    match_conditions = self.engine.db.fetchall(
                        "SELECT lot_no FROM inventory WHERE vessel LIKE ?", (f"%{vessel}%",)
                    )
                
                if match_conditions:
                    for row in match_conditions:
                        lot_no = row[0] if isinstance(row, (list, tuple)) else (row['lot_no'] if 'lot_no' in row.keys() else str(row[0]))
                        updates = []
                        params = []
                        
                        if arrival_date:
                            updates.append("arrival_date = ?")
                            params.append(str(arrival_date))
                        if free_time_days > 0:
                            updates.append("free_time = ?")
                            params.append(free_time_days)
                            # v4.0.2: Free Time 일수 있으면 반납일(con_return)도 자동 계산해 저장
                            if arrival_date:
                                try:
                                    arr_dt = datetime.strptime(str(arrival_date)[:10], '%Y-%m-%d')
                                    ret_dt = arr_dt + timedelta(days=free_time_days)
                                    updates.append("con_return = ?")
                                    params.append(ret_dt.strftime('%Y-%m-%d'))
                                except (ValueError, TypeError):
                                    pass
                        if bl_no:
                            updates.append("bl_no = COALESCE(NULLIF(bl_no, ''), ?)")
                            params.append(bl_no)
                        
                        if updates:
                            sql = f"UPDATE inventory SET {', '.join(updates)} WHERE lot_no = ?"
                            params.append(lot_no)
                            self.engine.db.execute(sql, tuple(params))
                            updated_count += 1
                            self._log(f"OK D/O → LOT {lot_no} 업데이트 (도착일: {arrival_date}, Free Time: {free_time_days}일)")
        
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            updated_count = 0
            logger.error(f"D/O LOT 업데이트 오류: {e}", exc_info=True)
            self._log(f"X D/O 업데이트 오류 (롤백됨): {e}")
        
        return updated_count
    
    def _calculate_free_time_days(self, do_data, arrival_date) -> int:
        """
        v3.8.7: Free Time 일수 계산
        
        Free Time = Free Time 날짜 - Arrival Date (입항일)
        예: 2025-11-11 - 2025-10-17 = 25일
        
        Args:
            do_data: D/O 파싱 결과 (free_time_info 또는 free_time 포함)
            arrival_date: 입항일 (date 또는 str)
            
        Returns:
            int: Free Time 일수 (0이면 계산 불가)
        """
        from datetime import date, datetime
        
        if not arrival_date:
            return 0
        
        # arrival_date를 date 객체로 변환
        if isinstance(arrival_date, str):
            try:
                arrival_dt = datetime.strptime(arrival_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return 0
        elif isinstance(arrival_date, date):
            arrival_dt = arrival_date
        else:
            return 0
        
        # 1순위: free_time_info (컨테이너별 Free Time 날짜)
        free_time_infos = getattr(do_data, 'free_time_info', [])
        if free_time_infos:
            for ft_info in free_time_infos:
                ft_date_str = ''
                if hasattr(ft_info, 'free_time_date'):
                    ft_date_str = ft_info.free_time_date
                elif isinstance(ft_info, dict):
                    ft_date_str = ft_info.get('free_time_date', '') or ft_info.get('free_time_until', '')
                
                if ft_date_str:
                    try:
                        ft_dt = datetime.strptime(str(ft_date_str), '%Y-%m-%d').date()
                        days = (ft_dt - arrival_dt).days
                        if days > 0:
                            self._log(f"OK Free Time 계산: {ft_date_str} - {arrival_date} = {days}일")
                            return days
                    except (ValueError, TypeError):
                        continue
        
        # 2순위: free_time 객체 (storage_free_days 직접 값)
        free_time_obj = getattr(do_data, 'free_time', None)
        if free_time_obj:
            if hasattr(free_time_obj, 'storage_free_days') and free_time_obj.storage_free_days:
                return int(free_time_obj.storage_free_days)
        
        return 0
    
    def _parse_invoice(self, pdf_path: str, parser_v2) -> Optional[Any]:
        """Parse invoice PDF"""
        self._safe_progress(30, "Parsing Invoice...", "Extracting data...")
        
        try:
            inv_data = parser_v2.parse_invoice(pdf_path)
            return inv_data
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Invoice parse error: {e}")
            self._log(f"X Invoice parse error: {e}")
            return None
    
    def _parse_delivery_order(self, pdf_path: str, parser_v2) -> Optional[Any]:
        """Parse delivery order PDF (v3.8.4: parse_do 호환)"""
        self._safe_progress(30, "Parsing D/O...", "Extracting data...")
        
        try:
            # v3.8.4: parse_do 메서드 우선 사용, fallback으로 parse_document
            do_data = None
            if hasattr(parser_v2, 'parse_do'):
                do_data = parser_v2.parse_do(pdf_path)
            elif hasattr(parser_v2, 'parse_document'):
                do_data = parser_v2.parse_document(pdf_path, doc_type='DO')
            else:
                logger.warning("D/O parser method not found")
            return do_data
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"D/O parse error: {e}")
            self._log(f"X D/O parse error: {e}")
            return None
    
    def _process_excel_inbound(self, excel_path: str) -> None:
        """Process Excel inbound file"""

        
        filename = os.path.basename(excel_path)
        self._start_task("Excel Inbound", f"Processing: {filename}")
        self._log(f"Excel inbound: {filename}")
        
        try:
            # Detect Excel type and process
            result = self._import_inbound_excel_auto(excel_path)
            
            if result and result.get('success'):
                lots_count = result.get('lots_processed', 0)
                self._end_task(True, f"OK Excel inbound: {lots_count} LOTs")
                self._log(f"OK Excel inbound: {lots_count} LOTs")
                
                if hasattr(self, '_deferred_refresh_main_tabs'):
                    self._deferred_refresh_main_tabs(delay_ms=50)
                elif hasattr(self, '_refresh_main_tabs'):
                    self._refresh_main_tabs()
                else:
                    self._refresh_inventory()
                    self._refresh_tonbag()
                
                CustomMessageBox.showinfo(self.root, "Excel Inbound Complete",
                    f"Excel inbound complete!\n\n"
                    f"File: {filename}\n"
                    f"LOTs: {lots_count}")
            else:
                errors = result.get('errors', ['Unknown error']) if result else ['Processing failed']
                self._end_task(False, f"X Excel inbound failed")
                self._log(f"X Excel inbound failed: {errors}")
                CustomMessageBox.showerror(self.root, "Excel Inbound Failed", f"Failed:\n{errors}")
                
        except (RuntimeError, ValueError) as e:
            logger.error(f"Excel inbound error: {e}")
            self._end_task(False, f"X Error: {str(e)[:50]}...")
            self._log(f"X Excel inbound error: {e}")
            CustomMessageBox.show_detailed_error(self.root, "Error", "Excel inbound error", exception=e)
