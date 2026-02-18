# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - Allocation (출고 리스트) Excel 파서

Author: Ruby
Version: 2.5.4

출고 리스트 구조:
- 1행: 타이틀 (예: "Allocation - PT LBM - September / CIF Semarang - 300MT of MIc9000")
- 2행: 빈 행 (또는 합계)
- 3행: 헤더 (Product, SAP NO, ETA BUSAN, Date in stock, QTY (MT), Lot No, WH, Customs, SOLD TO, GW, SALE REF)
- 4행~: 데이터
"""

import logging
from core.types import safe_float
logger = logging.getLogger(__name__)
import re
from datetime import datetime, date
from typing import Optional, List, Dict
from pathlib import Path
from dataclasses import dataclass, field


import pandas as pd


@dataclass
class AllocationHeader:
    """Allocation 헤더 정보"""
    title: str = ""           # 전체 타이틀
    customer: str = ""        # 고객명 (PT LBM, POSCO 등)
    destination: str = ""     # 목적지 (CIF Semarang 등)
    product: str = ""         # 제품명 (MIC9000 등)
    total_qty: float = 0.0    # 총 수량 (300MT)
    period: str = ""          # 기간 (September 등)
    filename: str = ""


@dataclass
class AllocationRow:
    """Allocation 행 데이터 (출고 항목)"""
    product: str = ""
    sap_no: str = ""
    eta_busan: date = None        # ✅ v2.5.4 추가
    date_in_stock: date = None
    qty_mt: float = 0.0
    lot_no: str = ""
    sub_lt: int = 0               # 톤백 번호 (tonbag_no와 동일, DB 호환용)
    warehouse: str = "GY"
    customs: str = ""             # ✅ v2.5.4 추가
    sold_to: str = ""             # 고객사 (customer와 동일, DB 호환용)
    gross_weight: float = 0.0
    sale_ref: str = ""
    outbound_date: date = None

    # 톤백 출고 정보
    sublot_count: int = 0         # 출고할 톤백 수 (tonbag_count와 동일)

    @property
    def tonbag_no(self) -> int:
        """v5.1.0: sub_lt의 표준 별칭"""
        return self.sub_lt
    
    @tonbag_no.setter
    def tonbag_no(self, value: int):
        self.sub_lt = value

    @property
    def customer(self) -> str:
        """v5.1.0: sold_to의 표준 별칭"""
        return self.sold_to
    
    @customer.setter
    def customer(self, value: str):
        self.sold_to = value

    @property
    def tonbag_count(self) -> int:
        """v5.1.0: sublot_count의 표준 별칭"""
        return self.sublot_count
    
    @tonbag_count.setter
    def tonbag_count(self, value: int):
        self.sublot_count = value


@dataclass
class AllocationData:
    """Allocation 전체 데이터"""
    header: AllocationHeader = None
    rows: List[AllocationRow] = field(default_factory=list)
    total_qty: float = 0.0
    total_rows: int = 0
    source_file: str = ""
    parsed_at: datetime = None
    success: bool = True  # v2.9.64: 파싱 성공 여부
    errors: List[str] = field(default_factory=list)  # v2.9.64: 오류 메시지


class AllocationParser:
    """
    Allocation (출고 리스트) Excel 파서 (v2.5.4)

    출고 리스트 구조:
    - 1행: 타이틀
    - 2행: 빈 행 (또는 합계)
    - 3행: 헤더
    - 4행~: 데이터
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

    def parse(self, excel_path: str) -> Optional[AllocationData]:
        """
        Allocation Excel 파싱

        Args:
            excel_path: Excel 파일 경로

        Returns:
            AllocationData 또는 None
        """
        self.errors = []
        self.warnings = []

        try:
            # header=None으로 읽어서 직접 파싱
            df = pd.read_excel(excel_path, header=None)

            result = AllocationData()
            result.source_file = excel_path
            result.parsed_at = datetime.now()
            result.header = self._extract_header(df, excel_path)
            result.rows = self._extract_rows(df, result.header)
            result.total_rows = len(result.rows)
            result.total_qty = sum(row.qty_mt for row in result.rows)

            return result

        except (ValueError, TypeError, KeyError) as e:
            self.errors.append(f"Allocation 파싱 오류: {str(e)}")
            return None

    def _extract_header(self, df: pd.DataFrame, filepath: str) -> AllocationHeader:
        """
        헤더 정보 추출 (1행 타이틀에서)

        예: "Allocation - PT LBM - September / CIF Semarang - 300MT of MIc9000"
        """
        header = AllocationHeader()
        header.filename = Path(filepath).name

        # 1행 타이틀 읽기
        if len(df) > 0:
            title_row = df.iloc[0].values
            title_parts = [str(v) for v in title_row if pd.notna(v) and str(v).strip()]
            header.title = ' '.join(title_parts)

        title = header.title.upper()

        # 고객명 추출
        if "PT LBM" in title or "PT_LBM" in title:
            header.customer = "PT LBM"
        elif "POSCO" in title:
            header.customer = "POSCO"
        elif "SAMSUNG" in title:
            header.customer = "Samsung SDI"
        elif "LG" in title:
            header.customer = "LG Energy"
        elif "SK" in title:
            header.customer = "SK On"

        # 목적지 추출 (CIF xxx)
        cif_match = re.search(r'CIF\s+(\w+)', title, re.IGNORECASE)
        if cif_match:
            header.destination = f"CIF {cif_match.group(1)}"

        # 제품명 추출
        product_patterns = ['MIC9000', 'MIC7100', 'LCA', 'NSH', 'LITHIUM']
        for p in product_patterns:
            if p in title:
                header.product = p
                break

        # 수량 추출 (300MT)
        qty_match = re.search(r'(\d+(?:\.\d+)?)\s*MT', title, re.IGNORECASE)
        if qty_match:
            header.total_qty = safe_float(qty_match.group(1))

        # 기간 추출 (September 등)
        months = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE',
                  'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
        for month in months:
            if month in title:
                header.period = month.capitalize()
                break

        return header

    def _extract_rows(self, df: pd.DataFrame, header: AllocationHeader) -> List[AllocationRow]:
        """
        데이터 행 추출

        구조:
        - 1행(idx 0): 타이틀
        - 2행(idx 1): 빈 행 또는 합계
        - 3행(idx 2): 헤더
        - 4행~(idx 3~): 데이터
        """
        rows = []

        # 헤더 행 찾기 - 'LOT'와 'PRODUCT'가 모두 있는 행
        header_row_idx = None
        for i in range(min(10, len(df))):
            row_values = [str(v).strip().upper() for v in df.iloc[i].values if pd.notna(v)]
            row_str = ' '.join(row_values)

            # 'LOT NO' 또는 'LOT_NO' 또는 'LOTNO'가 있고, 'PRODUCT'도 있는 행
            has_lot_col = 'LOT' in row_str
            has_product_col = 'PRODUCT' in row_str

            if has_lot_col and has_product_col:
                header_row_idx = i
                break

        if header_row_idx is None:
            # 기본값: 3행 (0-indexed: 2)
            header_row_idx = 2
            self.warnings.append(f"헤더 행을 자동 감지하지 못해 기본값(3행) 사용")

        # 컬럼 헤더 추출
        headers = [str(v).strip() if pd.notna(v) else '' for v in df.iloc[header_row_idx].values]
        col_map = self._map_columns(headers)

        # 데이터 행 추출 (헤더 다음 행부터)
        for i in range(header_row_idx + 1, len(df)):
            row_data = df.iloc[i].values

            # LOT NO 컬럼 확인
            lot_col = col_map.get('lot_no')
            if lot_col is None or lot_col >= len(row_data):
                continue

            lot_raw = row_data[lot_col]
            if pd.isna(lot_raw):
                continue

            # v5.9.3: Total/합계 행 필터링
            row_str = ' '.join(str(v).strip().upper() for v in row_data if pd.notna(v))
            if re.match(r'^(TOTAL|합계|SUBTOTAL|소계)', row_str):
                continue

            # LOT 번호를 문자열로 변환 (정수, 실수, 과학표기법 모두 처리)
            if isinstance(lot_raw, float):
                lot_no = str(int(lot_raw)) if lot_raw == int(lot_raw) else str(lot_raw).split('.')[0]
            elif isinstance(lot_raw, int):
                lot_no = str(lot_raw)
            else:
                s = str(lot_raw).strip()
                if re.fullmatch(r'\d+\.?\d*[eE]\+?\d+', s):
                    lot_no = str(int(float(s)))
                else:
                    lot_no = s.split('.')[0]

            # LOT 번호 유효성 검사 (10자리 숫자)
            if not lot_no or len(lot_no) != 10 or not lot_no.isdigit():
                continue

            row = AllocationRow()
            row.lot_no = lot_no

            # Product
            if 'product' in col_map and col_map['product'] < len(row_data):
                val = row_data[col_map['product']]
                row.product = str(val) if pd.notna(val) else header.product

            # SAP NO (v5.9.3: 과학표기법 방어)
            if 'sap_no' in col_map and col_map['sap_no'] < len(row_data):
                val = row_data[col_map['sap_no']]
                if pd.notna(val):
                    if isinstance(val, float):
                        row.sap_no = str(int(val))
                    elif isinstance(val, int):
                        row.sap_no = str(val)
                    else:
                        s = str(val).strip()
                        if re.fullmatch(r'\d+\.?\d*[eE]\+?\d+', s):
                            row.sap_no = str(int(float(s)))
                        else:
                            row.sap_no = s.split('.')[0]

            # ETA BUSAN (v2.5.4)
            if 'eta_busan' in col_map and col_map['eta_busan'] < len(row_data):
                val = row_data[col_map['eta_busan']]
                row.eta_busan = self._parse_date(val)

            # Date in stock
            if 'date_in_stock' in col_map and col_map['date_in_stock'] < len(row_data):
                val = row_data[col_map['date_in_stock']]
                row.date_in_stock = self._parse_date(val)

            # QTY (MT)
            if 'qty_mt' in col_map and col_map['qty_mt'] < len(row_data):
                qty_val = row_data[col_map['qty_mt']]
                if pd.notna(qty_val):
                    try:
                        row.qty_mt = safe_float(qty_val)
                        # Sub LOT 수 계산 (약 500kg = 0.5MT per 톤백)
                        row.sublot_count = max(1, int(row.qty_mt / 0.5))
                    except (ValueError, TypeError) as _e:
                        logger.debug(f"[allocation_parser] 무시: {_e}")

            # Warehouse
            row.warehouse = 'GY'
            if 'warehouse' in col_map and col_map['warehouse'] < len(row_data):
                val = row_data[col_map['warehouse']]
                if pd.notna(val):
                    row.warehouse = str(val).strip()

            # Customs (v2.5.4)
            if 'customs' in col_map and col_map['customs'] < len(row_data):
                val = row_data[col_map['customs']]
                if pd.notna(val):
                    row.customs = str(val).strip()

            # SOLD TO
            row.sold_to = header.customer  # 기본값: 헤더에서 추출한 고객명
            if 'sold_to' in col_map and col_map['sold_to'] < len(row_data):
                val = row_data[col_map['sold_to']]
                if pd.notna(val):
                    row.sold_to = str(val).strip()

            # GW (Gross Weight) — v5.9.3: MT→kg 자동 변환 (10 미만이면 MT로 간주)
            if 'gw' in col_map and col_map['gw'] < len(row_data):
                gw_val = row_data[col_map['gw']]
                if pd.notna(gw_val):
                    try:
                        gw = safe_float(gw_val)
                        if 0 < gw < 10:
                            gw = gw * 1000
                        row.gross_weight = gw
                    except (ValueError, TypeError) as _e:
                        logger.debug(f"[allocation_parser] 무시: {_e}")

            # SALE REF
            if 'sale_ref' in col_map and col_map['sale_ref'] < len(row_data):
                val = row_data[col_map['sale_ref']]
                if pd.notna(val):
                    if isinstance(val, (int, float)):
                        row.sale_ref = str(int(val))
                    else:
                        row.sale_ref = str(val).strip()

            # ★★★ v2.9.61: SUB LT (톤백 번호) ★★★
            if 'sub_lt' in col_map and col_map['sub_lt'] < len(row_data):
                val = row_data[col_map['sub_lt']]
                if pd.notna(val):
                    try:
                        row.sub_lt = int(float(val))
                    except (ValueError, TypeError) as _e:
                        logger.debug(f'Suppressed (ValueError, TypeError): {_e}')

            # ★★★ v2.9.61: OUTBOUND DATE (출고일) ★★★
            if 'outbound_date' in col_map and col_map['outbound_date'] < len(row_data):
                val = row_data[col_map['outbound_date']]
                row.outbound_date = self._parse_date(val)

            rows.append(row)

        return rows

    def _map_columns(self, headers: List[str]) -> Dict[str, int]:
        """
        컬럼명을 인덱스로 매핑 (v2.9.84 - 확장된 alias 지원)
        
        지원 컬럼명 예시:
        - LOT: 'LOT NO', 'Lot No', 'LOT_NO', 'lot_no', 'LOTNO'
        - QTY: 'QTY (MT)', 'QTY_MT', 'QTY', 'Qty Mt'
        - SOLD TO: 'SOLD TO', 'SOLD_TO', 'Sold To', 'Customer'
        """
        col_map = {}
        
        # ★★★ v2.9.84: 확장된 alias 매핑 ★★★
        alias_patterns = {
            'product': ['PRODUCT', 'PRODUCT_NAME', 'PRODUCT_CODE', '제품', '품목'],
            'sap_no': ['SAP_NO', 'SAP NO', 'SAPNO', 'SAP'],
            'eta_busan': ['ETA_BUSAN', 'ETA BUSAN', 'ETA', '입항일'],
            'date_in_stock': ['DATE_IN_STOCK', 'DATE IN STOCK', 'INBOUND_DATE', 'INBOUND DATE', 
                             '입고일', 'STOCK_DATE', 'STOCK DATE'],
            'qty_mt': ['QTY_MT', 'QTY (MT)', 'QTY(MT)', 'QTY', 'QUANTITY', '수량', 
                      'WEIGHT', 'NET_WEIGHT', 'NET WEIGHT'],
            'lot_no': ['LOT_NO', 'LOT NO', 'LOTNO', 'LOT', 'LOT_NUMBER'],
            'sub_lt': ['SUB_LT', 'SUB LT', 'SUBLT', 'SUB_LOT', 'SUBLOT', 'TONBAG', '톤백', '톤백번호'],
            'warehouse': ['WAREHOUSE', 'WH', '창고', 'LOCATION'],
            'customs': ['CUSTOMS', '통관', 'CUSTOMS_STATUS'],
            'sold_to': ['SOLD_TO', 'SOLD TO', 'CUSTOMER', '고객', '거래처', 'BUYER'],
            'gw': ['GW', 'GROSS_WEIGHT', 'GROSS WEIGHT', '총중량'],
            'sale_ref': ['SALE_REF', 'SALE REF', 'SALEREF', 'SALE_REFERENCE'],
            'outbound_date': ['OUTBOUND_DATE', 'OUTBOUND DATE', '출고일', 'PICKED_DATE'],
            'bl_no': ['BL_NO', 'BL NO', 'BLNO', 'BL', 'B/L NO', 'B/L_NO'],
            'container_no': ['CONTAINER_NO', 'CONTAINER NO', 'CONTAINER', 'CONT', 'CNTR'],
        }

        for i, h in enumerate(headers):
            if not h:
                continue
            
            # 정규화: 대문자, 공백→언더스코어, 특수문자 제거
            h_norm = str(h).upper().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '')
            h_orig = str(h).upper().replace(' ', '_')  # 원본도 유지
            
            # alias 패턴 매칭
            for standard_key, aliases in alias_patterns.items():
                if standard_key in col_map:
                    continue  # 이미 매핑됨
                
                for alias in aliases:
                    alias_norm = alias.upper().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '')
                    
                    # 정확히 일치하거나 포함 관계
                    if h_norm == alias_norm or h_orig == alias.upper().replace(' ', '_'):
                        col_map[standard_key] = i
                        break
                    # 부분 매칭 (LOT가 포함된 경우 등)
                    elif standard_key == 'lot_no' and 'LOT' in h_norm and 'SUB' not in h_norm:
                        col_map[standard_key] = i
                        break
                    elif standard_key == 'sub_lt' and 'SUB' in h_norm and ('LT' in h_norm or 'LOT' in h_norm):
                        col_map[standard_key] = i
                        break

        return col_map

    def _parse_date(self, val) -> Optional[date]:
        """날짜 파싱 (다양한 형식 지원)"""
        if pd.isna(val):
            return None

        # pandas Timestamp
        if hasattr(val, 'date'):
            return val.date()

        # datetime
        if isinstance(val, datetime):
            return val.date()

        # date
        if isinstance(val, date):
            return val

        # 문자열
        val_str = str(val).strip()

        # 다양한 날짜 형식 시도
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y.%m.%d',
            '%d.%m.%Y',
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(val_str, fmt).date()
            except ValueError:
                continue

        return None
