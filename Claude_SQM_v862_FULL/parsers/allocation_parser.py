"""
SQM 재고관리 시스템 - Allocation (출고 리스트) Excel 파서

Author: Ruby
Version: 2.6.1  ← v2.5.4에서 업그레이드

[v2.6.1 변경사항]
- AllocationRow.export_type 필드 추가: Export 컬럼값('반송', '일반수출' 등) 저장

[v2.6.0 변경사항]
- 시트 자동 선택 (_select_best_sheet): 다중 시트 파일에서 LOT+데이터가 있는 최적 시트 자동 감지
- 헤더 탐지 조건 완화: PRODUCT 컬럼 없이 LOT 컬럼만으로도 헤더 행 인정 (Song 양식 대응)
- 샘플 행 자동 분리: qty_mt < 0.01 이면 AllocationRow.is_sample=True 자동 설정
- 'Balance' 컬럼 fallback 지원: QTY(MT) 컬럼 없을 때 Balance를 qty_mt로 사용 (Woo 양식 대응)
- 피벗 테이블 행 자동 필터링: 헤더 행에 섞인 피벗 집계 데이터 무시
- '반송', 'Export', 'Remark' 컬럼 자동 무시 (이미 col_map에서 제외됨)

지원 양식:
A) Song 양식: Sheet1(Product 컬럼 없음) + 데이터 시트(Product 있음) → 데이터 시트 자동 선택
B) Woo  양식: Sheet1 단일 시트, 5행 헤더, Balance/Export/Remark 추가 컬럼, 피벗 테이블 혼재
C) 기존 양식: 1행 타이틀, 2행 무시, 3행 헤더, 4행~ 데이터
D) 화주 원본: 1행 합계(숫자만), 2행 헤더, 3행~ 데이터
"""

from engine_modules.constants import STATUS_SOLD
import logging

from core.types import normalize_lot, safe_float
from utils.common import norm_date_any, norm_sale_ref, norm_sap_no

logger = logging.getLogger(__name__)
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

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

    # v2.6.0: 샘플 행 여부 (qty_mt < 0.01 → True)
    is_sample: bool = False

    # v2.6.1: 수출 유형 ('반송', '일반수출', '' 등) — Woo 양식의 Export 컬럼값 저장
    export_type: str = ""

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
            # v2.6.0: 시트 자동 선택 후 해당 시트만 파싱
            sheet_name = self._select_best_sheet(excel_path)
            read_kwargs = {'header': None}
            if sheet_name is not None:
                read_kwargs['sheet_name'] = sheet_name
                self.warnings.append(f"시트 자동 선택: '{sheet_name}'")

            df = pd.read_excel(excel_path, **read_kwargs)

            result = AllocationData()
            result.source_file = excel_path
            result.parsed_at = datetime.now()
            result.header = self._extract_header(df, excel_path)
            result.rows = self._extract_rows(df, result.header)
            # v8.6.3: 본품 먼저, 샘플 나중 정렬 (같은 LOT도 본품/샘플 분리 표시)
            result.rows.sort(key=lambda r: (r.is_sample, r.lot_no))
            result.total_rows = len(result.rows)
            result.total_qty = sum(row.qty_mt for row in result.rows)

            return result

        except (ValueError, TypeError, KeyError, FileNotFoundError, OSError,
                PermissionError, IsADirectoryError) as e:
            self.errors.append(f"Allocation 파싱 오류: {str(e)}\")")
            return None

    def _select_best_sheet(self, excel_path: str) -> Optional[str]:
        """
        v2.6.0: 다중 시트 파일에서 Allocation 데이터가 있는 최적 시트 자동 선택.

        선택 기준 (우선순위 순):
        1. LOT 컬럼 + PRODUCT 컬럼이 모두 있는 시트 (가장 완전한 양식)
        2. LOT 컬럼만 있고 실제 LOT 번호(8~11자리 숫자)가 있는 시트
        3. 시트가 1개이면 그대로 None 반환 (기존 동작 유지)

        Song 양식: Sheet1(Product 없음) < '250톤 수출작업'(Product 있음) → 후자 선택
        Woo  양식: Sheet1 1개 → None 반환
        """
        try:
            xf = pd.ExcelFile(excel_path)
            sheet_names = xf.sheet_names
        except Exception:
            return None

        if len(sheet_names) <= 1:
            return None  # 단일 시트: 기존 동작

        best_sheet = None
        best_score = -1

        for sh in sheet_names:
            try:
                df_sh = pd.read_excel(excel_path, sheet_name=sh, header=None, nrows=15)
            except Exception:
                continue

            score = 0
            has_lot = False
            has_product = False
            has_lot_data = False

            for i in range(min(10, len(df_sh))):
                row_vals = [str(v).strip().upper() for v in df_sh.iloc[i].values if pd.notna(v)]
                row_str = ' '.join(row_vals)

                if 'LOT' in row_str and 'SUB' not in row_str:
                    has_lot = True
                if 'PRODUCT' in row_str:
                    has_product = True

                # LOT 번호(8~11자리 숫자) 데이터 존재 여부
                for v in df_sh.iloc[i].values:
                    if pd.notna(v):
                        s = str(v).strip().split('.')[0]
                        if s.isdigit() and 8 <= len(s) <= 11:
                            has_lot_data = True

            if has_lot and has_product:
                score = 3
            elif has_lot:
                score = 2
            if has_lot_data:
                score += 1

            if score > best_score:
                best_score = score
                best_sheet = sh

        # 점수가 0이면 선택 불가 → None (기존 동작)
        return best_sheet if best_score > 0 else None

    def _extract_header(self, df: pd.DataFrame, filepath: str) -> AllocationHeader:
        """
        헤더 정보 추출 (1행 타이틀에서)

        예: "Allocation - PT LBM - September / CIF Semarang - 300MT of MIc9000"
        """
        header = AllocationHeader()
        header.filename = Path(filepath).name

        # 1행 타이틀 읽기 (화주 양식: 1행이 합계 숫자만 있을 수 있음)
        if len(df) > 0:
            title_row = df.iloc[0].values
            title_parts = [str(v) for v in title_row if pd.notna(v) and str(v).strip()]
            header.title = ' '.join(title_parts)
            # 화주 원본: 1행이 "300.0600" 같은 합계만 있는 경우 → total_qty로 사용
            if title_parts and len(title_parts) == 1:
                try:
                    only_val = title_parts[0].replace(',', '')
                    if re.match(r'^\d+(?:\.\d+)?$', only_val):
                        header.total_qty = safe_float(only_val)
                except (ValueError, TypeError) as e:
                    logger.warning(f"[_extract_header] Suppressed: {e}")

        title = header.title.upper()

        # 고객명 추출 (패턴 리스트 — CATL/Panasonic/BYD/Northvolt 등 추가 시 한 줄만 추가)
        customer_patterns = [
            ("PT LBM", "PT LBM"), ("PT_LBM", "PT LBM"),
            # v6.7.3: 광양 거래 고객사 패턴 (constants.CUSTOMER_NAME_MAP 연동)
            ("CATL KOREA", "CATL KOREA"), ("CATL", "CATL"),
            ("CONTEMPORARY AMPEREX", "CATL"),
            ("BYD", "BYD"),
            ("LG ENERGY SOLUTION", "LG ENERGY SOLUTION"),
            ("LGES", "LG ENERGY SOLUTION"), ("LG ES", "LG ENERGY SOLUTION"),
            ("LG ENERGY", "LG ENERGY SOLUTION"),
            ("SAMSUNG SDI", "SAMSUNG SDI"), ("SDI", "SAMSUNG SDI"),
            ("SK ON", "SK ON"), ("SK INNOVATION", "SK ON"), ("SK BATTERY", "SK ON"),
            ("POSCO FUTURE M", "POSCO FUTURE M"), ("POSCO CHEM", "POSCO FUTURE M"),
            ("POSCO CHEMICAL", "POSCO FUTURE M"), ("POSCO", "POSCO FUTURE M"),
            ("ECOPRO BM", "ECOPRO BM"), ("ECOPRO", "ECOPRO BM"),
            ("L&F", "L&F"),
            ("SVOLT", "SVOLT ENERGY"),
            ("CALB", "CALB"),
            ("GOTION", "GOTION HIGH-TECH"),
            ("SUNWODA", "SUNWODA"),
            ("LISHEN", "LISHEN"),
            ("SAMSUNG", "SAMSUNG SDI"),
            ("PANASONIC", "Panasonic Energy"),
            ("NORTHVOLT", "Northvolt"),
        ]
        for pattern, name in customer_patterns:
            if pattern in title:
                header.customer = name
                break

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

        # 헤더 행 찾기 - v2.6.0: LOT 컬럼만 있어도 헤더로 인정 (PRODUCT 필수 조건 제거)
        header_row_idx = None
        for i in range(min(10, len(df))):
            row_values = [str(v).strip().upper() for v in df.iloc[i].values if pd.notna(v)]
            row_str = ' '.join(row_values)

            has_lot_col = 'LOT' in row_str and 'SUB' not in row_str
            has_product_col = 'PRODUCT' in row_str

            # v2.6.0: LOT+PRODUCT 둘 다 있으면 최우선 (점수 2)
            #         LOT만 있어도 QTY나 SAP 등 다른 컬럼이 함께 있으면 헤더로 인정 (점수 1)
            if has_lot_col and has_product_col:
                header_row_idx = i
                break
            elif has_lot_col and ('QTY' in row_str or 'SAP' in row_str or STATUS_SOLD in row_str):
                # Product 없는 Song Sheet1 양식 대응
                header_row_idx = i
                # break 하지 않고 계속 탐색 — 더 좋은 행(LOT+PRODUCT)이 있을 수 있음
                # → 이미 _select_best_sheet에서 최적 시트를 골랐으므로 여기선 break
                break

        if header_row_idx is None:
            # 화주 원본: 1행 합계(숫자만), 2행 헤더인 경우 — 2행을 헤더로 사용
            if len(df) >= 2:
                row0_str = ' '.join(str(v).strip() for v in df.iloc[0].values if pd.notna(v))
                if re.match(r'^[\d\s.,]+$', row0_str.replace(' ', '')):
                    header_row_idx = 1
                    self.warnings.append("헤더 행을 2행으로 추정 (1행이 합계만 있는 화주 양식)")
            if header_row_idx is None:
                header_row_idx = 2
                self.warnings.append("헤더 행을 자동 감지하지 못해 기본값(3행) 사용")

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

            # v2.6.0: 피벗 테이블 집계 행 필터링
            # Woo 양식에서 헤더 행 우측에 피벗 데이터(행 레이블, 합계:Balance 등)가 혼재
            # → 실제 데이터 행인지 확인: LOT 컬럼이 8~11자리 숫자여야 함 (아래 lot_no 정규화에서 처리)

            # LOT 번호 정규화 (1125110452.0 → "1125110452", 숫자/문자 혼용 통일)
            lot_no = normalize_lot(lot_raw)
            if not lot_no:
                continue
            if re.fullmatch(r'\d+\.?\d*[eE][+-]?\d+', lot_no):
                lot_no = str(int(float(lot_no)))
            # LOT 번호 유효성 검사 (8~11자리 숫자)
            if len(lot_no) < 8 or len(lot_no) > 11 or not lot_no.isdigit():
                continue

            row = AllocationRow()
            row.lot_no = lot_no

            # Product
            if 'product' in col_map and col_map['product'] < len(row_data):
                val = row_data[col_map['product']]
                row.product = str(val) if pd.notna(val) else header.product

            # SAP NO 정규화 (digits_only 또는 trim)
            if 'sap_no' in col_map and col_map['sap_no'] < len(row_data):
                val = row_data[col_map['sap_no']]
                if pd.notna(val):
                    row.sap_no = norm_sap_no(val) or str(val).strip().split('.')[0]

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
                        # 톤백 개수는 엔진에서 LOT 단위중량(500/1000kg)으로 계산한다.
                        row.sublot_count = 0
                    except (ValueError, TypeError) as _e:
                        logger.debug(f"[allocation_parser] 무시: {_e}")

            # ④ v6.8.0: INVALID_QTY — qty_mt ≤ 0 이면 경고 (샘플 행 제외)
            # 0 이하 수량은 계산 오류 유발 → warnings 에 기록
            if row.qty_mt <= 0 and not row.is_sample:
                _warn = (
                    f"[INVALID_QTY] lot={row.lot_no} qty_mt={row.qty_mt} "
                    f"— 0 이하 수량, 해당 행 제외"
                )
                self.warnings.append(_warn)
                logger.warning(_warn)
                continue  # 해당 행 파싱 스킵

            # v2.6.0: 샘플 행 자동 감지 (qty_mt < 0.01 MT = 10kg 미만 = 샘플 1kg)
            if row.qty_mt > 0 and row.qty_mt < 0.01:
                row.is_sample = True

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

            # SALE REF 정규화 (upper + trim)
            if 'sale_ref' in col_map and col_map['sale_ref'] < len(row_data):
                val = row_data[col_map['sale_ref']]
                if pd.notna(val):
                    row.sale_ref = norm_sale_ref(val) or str(val).strip()

            # ★★★ v2.9.61: SUB LT (톤백 번호) ★★★
            if 'sub_lt' in col_map and col_map['sub_lt'] < len(row_data):
                val = row_data[col_map['sub_lt']]
                if pd.notna(val):
                    try:
                        row.sub_lt = int(float(val))
                    except (ValueError, TypeError) as _e:
                        logger.debug(f'Suppressed (ValueError, TypeError): {_e}')

            # OUTBOUND DATE 정규화 (ISO YYYY-MM-DD)
            if 'outbound_date' in col_map and col_map['outbound_date'] < len(row_data):
                val = row_data[col_map['outbound_date']]
                iso_str = norm_date_any(val)
                if iso_str:
                    try:
                        row.outbound_date = datetime.strptime(iso_str, '%Y-%m-%d').date()
                    except ValueError:
                        row.outbound_date = self._parse_date(val)
                else:
                    row.outbound_date = self._parse_date(val)

            # v2.6.1: Export 컬럼 → export_type (반송 / 일반수출 등)
            if 'export_type' in col_map and col_map['export_type'] < len(row_data):
                val = row_data[col_map['export_type']]
                if pd.notna(val):
                    row.export_type = str(val).strip()

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
        # v2.6.0: Balance를 qty_mt fallback으로 추가 (Woo 양식: QTY(MT) 우선, 없으면 Balance 사용)
        #         Export, Remark 컬럼은 목록에 없으므로 col_map에서 자동 제외됨 (무시)
        alias_patterns = {
            'product': ['PRODUCT', 'PRODUCT_NAME', 'PRODUCT_CODE', '제품', '품목'],
            'sap_no': ['SAP_NO', 'SAP NO', 'SAPNO', 'SAP'],
            'eta_busan': ['ETA_BUSAN', 'ETA BUSAN', 'ETA', '입항일'],
            'date_in_stock': ['DATE_IN_STOCK', 'DATE IN STOCK', 'INBOUND_DATE', 'INBOUND DATE',
                             '입고일', 'STOCK_DATE', 'STOCK DATE'],
            'qty_mt': ['QTY_MT', 'QTY (MT)', 'QTY(MT)', 'QTY', 'QUANTITY', '수량',
                      'WEIGHT', 'NET_WEIGHT', 'NET WEIGHT',
                      'BALANCE'],          # ← v2.6.0: Woo 양식 fallback (QTY(MT)가 없을 때만 사용됨)
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
            # v2.6.1: Export 컬럼 → export_type 으로 매핑 (반송 / 일반수출 구분)
            'export_type': ['EXPORT', '수출유형', '반송', 'EXPORT_TYPE'],
            # v2.6.0: 아래 컬럼들은 alias_patterns에 포함하지 않아 자동 무시됨:
            # 'Remark', 'Invoice date' (Song 양식)
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
