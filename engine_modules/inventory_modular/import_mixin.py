"""
SQM Inventory Engine - Import Mixin
===================================

v2.9.91 - Extracted from inventory.py

Excel import functions for inventory data
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Check pandas availability
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None


class ImportMixin:
    """
    Import mixin for loading data from Excel
    
    Methods for importing inventory, tonbag, and location data
    """

    # Column name mappings for various Excel formats
    COLUMN_MAP = {
        'lot_no': ['Lot No', 'LOT NO', 'lot_no', 'LOT_NO', 'LOTNO', 'LOT', 'Lot'],
        'sap_no': ['SAP NO', 'SAP_NO', 'sap_no', 'SAPNO', 'SAP', 'Sap No'],
        'product': ['Product', 'PRODUCT', 'product', 'PRODUCT_NAME', '제품', '품목'],
        'qty_mt': ['QTY (MT)', 'QTY_MT', 'NET WEIGHT', 'net_weight', 'QTY', 'WEIGHT',
                  'Net Weight', '수량', 'QUANTITY'],
        'balance': ['Balance', 'BALANCE', 'balance', '잔량'],
        'gross_weight': ['GW', 'GROSS WEIGHT', 'gross_weight', 'GROSS_WEIGHT',
                        'Gross Weight', '총중량'],
        'warehouse': ['WH', '창고', 'warehouse', 'WAREHOUSE', 'Warehouse'],
        'invoice_no': ['Salar Invoice no.', 'SALAR INVOICE NO', 'invoice_no',
                      'SALAR_INVOICE_NO', 'Invoice No'],
        'stock_date': ['Date in stock', 'stock_date', 'STOCK_DATE', 'DATE_IN_STOCK',
                      'DATE IN STOCK', 'INBOUND_DATE', 'INBOUND DATE', '입고일'],
        'sold_to': ['SOLD TO', 'sold_to', 'SOLD_TO', 'Sold To', 'Customer',
                   'CUSTOMER', '고객', '거래처'],
        'sale_ref': ['SALE REF', 'sale_ref', 'SALE_REF', 'Sale Ref', 'SALEREF'],
        'condition': ['Condition', 'condition', 'CONDITION', '상태'],
        'remark': ['Remark', 'remark', 'REMARK', 'REMARKS', '비고', 'NOTE'],
        'bl_no': ['BL NO', 'bl_no', 'BL_NO', 'BLNO', 'BL', 'B/L NO', 'B/L_NO'],
        'container_no': ['CONTAINER', 'container_no', 'CONTAINER_NO', 'CONTAINER NO',
                        'Container No', 'CONT', 'CNTR'],
        'eta_busan': ['ETA BUSAN', 'ETA_BUSAN', 'ETA', '입항일', 'ARRIVAL_DATE'],
        'sub_lt': ['SUB LT', 'SUB_LT', 'SUBLT', '톤백번호', 'TONBAG', 'TONBAG_NO', '톤백'],
    }

    def _get_col_value(self, row, key: str, default: Any = '') -> Any:
        """
        Get column value from row using multiple possible column names
        
        Args:
            row: DataFrame row
            key: Column key (from COLUMN_MAP)
            default: Default value if not found
            
        Returns:
            Column value or default
        """
        if not HAS_PANDAS:
            return default

        for col_name in self.COLUMN_MAP.get(key, [key]):
            if col_name in row.index and pd.notna(row.get(col_name)):
                return row.get(col_name)
        return default


    # NOTE: import_tonbags_from_excel, import_locations_from_excel
    #   → 미호출로 삭제 (v3.8.4 데드코드 정리)
