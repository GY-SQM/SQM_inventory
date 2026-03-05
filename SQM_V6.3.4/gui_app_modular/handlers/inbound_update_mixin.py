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
from engine_modules.constants import (
    MOVEMENT_INVOICE_UPDATE,
    MOVEMENT_BL_UPDATE,
    MOVEMENT_DO_UPDATE,
)

logger = logging.getLogger(__name__)


class InboundUpdateMixin:
    """입고 서류 업데이트 + Excel 입고 Mixin"""


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
