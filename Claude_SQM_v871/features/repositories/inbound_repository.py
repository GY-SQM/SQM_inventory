"""
P2 리팩토링 — InboundRepository
onestop_inbound.py / inbound_upload_mixin.py에서 분리한 DB 저장 로직.
engine.process_inbound 호출을 위한 데이터 준비 및 저장 실행.
"""
import logging
import sqlite3
from datetime import datetime

from core.types import safe_float

logger = logging.getLogger(__name__)


class InboundRepository:
    """입고 데이터 DB 저장."""

    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def _default_warehouse():
        try:
            from core.constants import DEFAULT_WAREHOUSE
            return DEFAULT_WAREHOUSE
        except ImportError:
            return ''

    def build_packing_dict(self, row: dict, pl, invoice, bl, do,
                           format_bl_fn=None, date_str_fn=None) -> dict:
        """미리보기 행 데이터를 engine.process_inbound용 packing_dict로 변환."""
        _format_bl = format_bl_fn or (lambda x: x)
        _date_str = date_str_fn or (lambda x: str(x) if x else '')

        lot_no = str(row.get('lot_no', '') or '')
        _tonbag = row.get('mxbg_pallet', row.get('tonbag_count', 10))
        try:
            _tonbag = int(float(str(_tonbag).replace(',', '') or 0))
        except (TypeError, ValueError):
            _tonbag = 10

        _arrival = str(row.get('arrival_date', '') or '').strip()[:10]
        _con_return = str(row.get('con_return', '') or '').strip()[:10]
        _free_time = 0
        _ft_raw = str(row.get('free_time', '') or '').strip()
        if _ft_raw:
            try:
                _free_time = int(float(_ft_raw.replace(',', '')))
            except (ValueError, TypeError):
                _free_time = 0
        if not _con_return and do:
            ft_infos = getattr(do, 'free_time_info', []) or []
            for ft in ft_infos:
                ftd = getattr(ft, 'free_time_date', '') or (ft.get('free_time_date', '') if isinstance(ft, dict) else '')
                if ftd:
                    _con_return = str(ftd)[:10]
                    break
        if _con_return and _arrival and not _ft_raw:
            try:
                _ft_dt = datetime.strptime(_con_return[:10], '%Y-%m-%d').date()
                _arr_dt = datetime.strptime(_arrival[:10], '%Y-%m-%d').date()
                _free_time = max(0, (_ft_dt - _arr_dt).days)
            except (ValueError, TypeError):
                _free_time = 0

        return {
            'lot_no': lot_no,
            'lot_sqm': str(row.get('lot_sqm', '') or ''),
            'sap_no': str(row.get('sap_no', '') or getattr(pl, 'sap_no', '') or (getattr(invoice, 'sap_no', '') if invoice else '') or ''),
            'bl_no': _format_bl(
                str(row.get('bl_no', '') or '') or
                (getattr(bl, 'bl_no', '') if bl else '') or
                (getattr(do, 'bl_no', '') if do else '') or ''
            ),
            'container_no': str(row.get('container_no', '') or ''),
            'product': str(row.get('product', '') or getattr(pl, 'product', '') or 'LITHIUM CARBONATE'),
            'product_code': str(row.get('product_code', '') or getattr(pl, 'code', '') or ''),
            'net_weight': safe_float(row.get('net_weight', 0) or 0),
            'gross_weight': safe_float(row.get('gross_weight', 0) or 0),
            'mxbg_pallet': _tonbag,
            'tonbag_count': _tonbag,
            'salar_invoice_no': str(row.get('salar_invoice_no', '') or (getattr(invoice, 'salar_invoice_no', '') if invoice else '') or ''),
            'ship_date': str(row.get('ship_date', '') or _date_str(getattr(bl, 'ship_date', None) if bl else None) or _date_str(getattr(invoice, 'invoice_date', None) if invoice else None) or ''),
            'arrival_date': _arrival,
            'free_time': _free_time,
            'free_time_date': _con_return,
            'con_return': _con_return,
            'warehouse': str(row.get('warehouse', '') or (getattr(do, 'warehouse', self._default_warehouse()) if do else self._default_warehouse())),
            'vessel': getattr(pl, 'vessel', '') or '',
        }

    def build_doc_dicts(self, invoice, bl, do, format_bl_fn=None, date_str_fn=None):
        """invoice/bl/do 파싱 결과를 engine용 dict로 변환."""
        _format_bl = format_bl_fn or (lambda x: x)
        _date_str = date_str_fn or (lambda x: str(x) if x else '')

        inv_dict = None
        if invoice:
            inv_dict = {
                'sap_no': getattr(invoice, 'sap_no', '') or '',
                'salar_invoice_no': getattr(invoice, 'salar_invoice_no', '') or '',
                'invoice_date': str(getattr(invoice, 'invoice_date', '')) if getattr(invoice, 'invoice_date', None) else '',
            }

        bl_dict = None
        if bl:
            bl_dict = {
                'bl_no': _format_bl(getattr(bl, 'bl_no', '') or ''),
                'ship_date': _date_str(getattr(bl, 'ship_date', None)) or _date_str(getattr(bl, 'shipped_date', None)) or '',
                'vessel': getattr(bl, 'vessel', '') or '',
            }

        do_dict = None
        if do:
            _con_return = ''
            ft_infos = getattr(do, 'free_time_info', []) or []
            for ft in ft_infos:
                ftd = getattr(ft, 'free_time_date', '') or (ft.get('free_time_date', '') if isinstance(ft, dict) else '')
                if ftd:
                    _con_return = str(ftd)[:10]
                    break
            _do_arr = getattr(do, 'arrival_date', None)
            _do_arrival = (_do_arr.isoformat() if hasattr(_do_arr, 'isoformat') else str(_do_arr or '')) if _do_arr and str(_do_arr) != 'None' else ''
            do_dict = {
                'bl_no': str(getattr(do, 'bl_no', '') or ''),
                'arrival_date': _do_arrival,
                'free_time_date': _con_return,
                'free_time': str(getattr(do, 'free_time', '') or ''),
                'warehouse': str(getattr(do, 'warehouse', '') or ''),
            }

        return inv_dict, bl_dict, do_dict

    def save_lot(self, packing_dict: dict, inv_dict, bl_dict, do_dict) -> dict:
        """단일 LOT를 engine.process_inbound로 저장."""
        return self.engine.process_inbound(
            packing_data=packing_dict, invoice_data=inv_dict,
            bl_data=bl_dict, do_data=do_dict
        )

    def lot_exists(self, lot_no: str) -> bool:
        """LOT 중복 확인."""
        try:
            return self.engine.inventory_lot_exists(lot_no)
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError):
            return False
