"""
P2 리팩토링 — InboundValidator
onestop_inbound.py / inbound_upload_mixin.py에서 분리한 검증 로직.
"""
import logging
from datetime import date as _date_type, datetime, timedelta

from core.types import safe_float

logger = logging.getLogger(__name__)


class InboundValidator:
    """입고 데이터 검증 로직."""

    @staticmethod
    def validate_date(s: str) -> bool:
        """YYYY-MM-DD 형식 날짜 문자열 검증."""
        import re as _re
        if not s:
            return True
        s = s.strip()
        if _re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', s):
            try:
                parts = s.split('-')
                _date_type(int(parts[0]), int(parts[1]), int(parts[2]))
                return True
            except ValueError:
                return False
        return False

    @staticmethod
    def calc_dates(arrival_str: str, con_return_str: str, ft_raw: str):
        """arrival/con_return/free_time 상호 계산.
        Returns: (con_return_str, free_time_str, error_msg)
        """
        try:
            arr_d = _date_type(*[int(x) for x in arrival_str.split('-')])
        except (ValueError, IndexError, TypeError):
            return '', '', "⚠️ 입항일 파싱 오류 (YYYY-MM-DD)"

        try:
            if ft_raw:
                if not ft_raw.isdigit() or int(ft_raw) < 0:
                    return '', '', "⚠️ Free time: 0 이상 일수(숫자) 입력"
                free_time_str = ft_raw
                con_return_d = arr_d + timedelta(days=int(ft_raw))
                con_return_str = con_return_d.strftime('%Y-%m-%d')
            elif con_return_str:
                cr_d = _date_type(*[int(x) for x in con_return_str.split('-')])
                free_time_str = str(max(0, (cr_d - arr_d).days))
            else:
                free_time_str = '14'
                con_return_str = (arr_d + timedelta(days=14)).strftime('%Y-%m-%d')
        except (ValueError, IndexError, TypeError):
            return '', '', "⚠️ 반납일/Free time 계산 오류 — 형식 확인"

        try:
            cr_d = _date_type(*[int(x) for x in con_return_str.split('-')])
            if cr_d < arr_d:
                return '', '', "⚠️ 컨테이너 반납일은 입항일과 같거나 이후여야 합니다."
        except (ValueError, IndexError, TypeError) as e:
            logger.debug("[InboundValidator] con_return >= arrival_date 검증 생략: %s", e)

        return con_return_str, free_time_str, ''

    @staticmethod
    def preflight_validate(rows: list) -> list:
        """DB 반영 전 미리보기 데이터 검증 (오류 리스트 반환)."""
        errors = []
        seen_lots = {}
        for idx, row in enumerate(rows, 1):
            lot_no = str(row.get('lot_no', '') or '').strip()
            product = str(row.get('product', '') or '').strip()
            if not lot_no:
                errors.append(f"{idx}행: LOT NO 필수")
            if not product:
                errors.append(f"{idx}행: PRODUCT 필수")
            try:
                nw = safe_float(row.get('net_weight', 0))
                if nw <= 0:
                    errors.append(f"{idx}행: NET(Kg) 0 초과 필요")
            except Exception:
                errors.append(f"{idx}행: NET(Kg) 숫자 형식 오류")
            try:
                mx = int(float(str(row.get('mxbg_pallet', '0')).replace(',', '') or 0))
                if mx <= 0:
                    errors.append(f"{idx}행: MXBG 1 이상 필요")
            except Exception:
                errors.append(f"{idx}행: MXBG 숫자 형식 오류")
            arr = str(row.get('arrival_date', '') or '').strip()
            cr = str(row.get('con_return', '') or '').strip()
            if arr and (len(arr) != 10 or arr.count('-') != 2):
                errors.append(f"{idx}행: ARRIVAL 날짜 형식 오류(YYYY-MM-DD)")
            if cr and (len(cr) != 10 or cr.count('-') != 2):
                errors.append(f"{idx}행: CON RETURN 날짜 형식 오류(YYYY-MM-DD)")
            if arr and cr:
                try:
                    arr_d = datetime.strptime(arr[:10], '%Y-%m-%d').date()
                    cr_d = datetime.strptime(cr[:10], '%Y-%m-%d').date()
                    if cr_d < arr_d:
                        errors.append(f"{idx}행: CON RETURN은 ARRIVAL 이상이어야 함")
                except ValueError as e:
                    logger.warning(f"[preflight_validate] Suppressed: {e}")
            if lot_no:
                if lot_no in seen_lots:
                    errors.append(f"{idx}행: LOT 중복({lot_no}) - {seen_lots[lot_no]}행과 중복")
                else:
                    seen_lots[lot_no] = idx
        return errors

    @staticmethod
    def has_required_docs(file_paths: dict, doc_types: list) -> bool:
        """필수 서류 3종(Packing List, Invoice, B/L)이 모두 선택·파싱되었는지 확인."""
        for doc_type, _name, required in doc_types:
            if required and doc_type not in file_paths:
                return False
        return True
