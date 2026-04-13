"""
P3-S1 Refactor: inbound_utils — 독립 유틸 함수
gui_app_modular/dialogs/inbound_utils.py

선택 책임: 데이터 후처리 + 포맷팅 + 날짜 계산 (Standalone functions)
이동 출처: onestop_inbound.py (7개 함수)
"""

from datetime import datetime, timedelta
import logging


logger = logging.getLogger(__name__)


# PREVIEW_COLUMNS: 미리보기 테이블 컬럼 정의 (onestop_inbound에서 정의됨)
# 필요시 import하거나 이곳에서 정의
PREVIEW_COLUMNS = [
    ("no",               "NO",               50,  "center"),
    ("lot_no",           "LOT NO",          110,  "center"),
    ("sap_no",           "SAP NO",          110,  "center"),
    ("bl_no",            "BL NO",           150,  "center"),
    ("product",          "PRODUCT",         180,  "center"),
    ("status",           "STATUS",           80,  "center"),
    ("container_no",     "CONTAINER",       130,  "center"),
    ("product_code",     "CODE",            100,  "center"),
    ("lot_sqm",          "LOT SQM",          80,  "center"),
    ("mxbg_pallet",      "MXBG",             70,  "center"),
    ("net_weight",       "NET(Kg)",          90,  "center"),
    ("gross_weight",     "GROSS(kg)",         90,  "center"),
    ("salar_invoice_no", "INVOICE NO",      120,  "center"),
    ("ship_date",        "SHIP DATE",        90,  "center"),
]


def merge_results(invoice, pl, bl, do):
    """
    4종 파싱 결과를 18열 미리보기 데이터로 병합
    P2: InboundParser 위임
    
    Args:
        invoice, pl, bl, do: 파싱된 데이터 객체
    
    Returns:
        list: 미리보기용 행 리스트
    """
    # NOTE: 실제 구현은 InboundParser에서 담당
    # 이 함수는 호출 인터페이스 유지용
    from features.parsers.inbound_parser import InboundParser
    parser = InboundParser()
    return parser.merge_results(invoice, pl, bl, do)


def empty_row(no: int) -> dict:
    """
    빈 미리보기 행 생성
    
    Args:
        no: 행 번호
    
    Returns:
        dict: 빈 행 딕셔너리
    """
    row = {col[0]: '' for col in PREVIEW_COLUMNS}
    row['no'] = str(no)
    return row


def date_str(val) -> str:
    """
    날짜를 YYYY-MM-DD 문자열로 변환
    None/'None'/비어있으면 '' 반환
    
    Args:
        val: 날짜 값 (datetime, str, etc)
    
    Returns:
        str: YYYY-MM-DD 형식 또는 ''
    """
    if val is None or (isinstance(val, str) and (not val.strip() or val.strip() in ('None', 'none'))):
        return ''
    if hasattr(val, 'isoformat'):
        return str(val.isoformat())[:10]
    s = str(val).strip()
    return s[:10] if len(s) >= 10 and s not in ('None', 'none') else (s if s and s not in ('None', 'none') else '')


def format_bl(bl_no) -> str:
    """
    BL 번호 포맷
    
    Args:
        bl_no: BL 번호
    
    Returns:
        str: 포맷된 BL 번호
    """
    if not bl_no:
        return ''
    bl_no = str(bl_no).strip()
    if bl_no.isdigit() and len(bl_no) >= 9:
        return f"MAEU{bl_no}"
    return bl_no


def fill_do(row: dict, do) -> None:
    """
    v3.8.8: D/O 데이터로 미리보기 행 보완 (free_time 계산 포함)
    
    Args:
        row: 미리보기 행 딕셔너리 (수정됨)
        do: D/O 파싱 데이터 객체
    """
    if not do:
        return
    
    if not row.get('bl_no') and getattr(do, 'bl_no', None):
        row['bl_no'] = str(getattr(do, 'bl_no', ''))
    
    # arrival_date (업로드3/4: D/O 파싱값으로 채움, YYYY-MM-DD)
    # v5.8.8: 날짜가 아닌 값(예: '광양')이면 넣지 않음 — ARRIVAL 컬럼 혼동 방지
    arr = getattr(do, 'arrival_date', None)
    if arr and str(arr) != 'None':
        _s = str(arr).strip()[:10]
        if len(_s) == 10 and _s.count('-') == 2 and _s.replace('-', '').isdigit():
            row['arrival_date'] = _s
    
    # warehouse
    wh = getattr(do, 'warehouse_name', '') or getattr(do, 'warehouse', '')
    if wh:
        row['warehouse'] = str(wh)
    
    # FREE TIME = con_return(컨테이너 반납일) - arrival_date (일수). D/O의 Free_Time 컬럼 = 반납일
    ft_infos = getattr(do, 'free_time_info', []) or []
    if ft_infos and arr and str(arr) != 'None':
        try:
            con_return_str = ''
            for ft in ft_infos:
                ftd = (getattr(ft, 'free_time_date', '') or getattr(ft, 'free_time_until', '')) if not isinstance(ft, dict) else (ft.get('free_time_date') or ft.get('free_time_until') or '')
                if ftd and str(ftd) != 'None':
                    con_return_str = str(ftd)[:10]
                    break
            if not con_return_str:
                logger.debug(
                    "[원스톱 미리보기] D/O free_time_info 있으나 반납일 없음 — CON RETURN/FREE TIME 빈칸. 항목 수: %s",
                    len(ft_infos),
                )
            if con_return_str:
                con_return_dt = datetime.strptime(con_return_str, '%Y-%m-%d').date()
                arr_dt = datetime.strptime(str(arr)[:10], '%Y-%m-%d').date()
                days = (con_return_dt - arr_dt).days
                row['free_time'] = str(max(0, days))
                row['con_return'] = str(con_return_str)[:10]
                logger.debug(
                    "[원스톱 미리보기] D/O 반납일 적용: con_return=%s, free_time(일수)=%s",
                    row['con_return'],
                    row['free_time'],
                )
        except (ValueError, TypeError) as e:
            logging.getLogger(__name__).debug(f"free_time 계산 실패: {e}")
    
    # 업로드4: free_time 일수만 있는 경우 (DO.free_time.storage_free_days)
    if not (row.get('free_time') or '').strip():
        ft_single = getattr(do, 'free_time', None)
        if ft_single is not None:
            days_val = getattr(ft_single, 'storage_free_days', None) or (ft_single.get('storage_free_days') if isinstance(ft_single, dict) else None)
            if days_val is not None:
                row['free_time'] = str(int(days_val))
                # FREE TIME 일수만 있으면 반납일(con_return) = arrival_date + 일수 로 계산해 CON RETURN에도 표시
                if not (row.get('con_return') or '').strip() and arr and str(arr) != 'None':
                    try:
                        arr_dt = datetime.strptime(str(arr)[:10], '%Y-%m-%d').date()
                        con_dt = arr_dt + timedelta(days=int(days_val))
                        row['con_return'] = con_dt.strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        logger.debug("[SUPPRESSED] exception in inbound_utils.py")  # noqa


@staticmethod
def amd_validate_date(s: str) -> bool:
    """
    날짜 유효성 검증
    P2: InboundValidator 위임
    
    Args:
        s: 날짜 문자열
    
    Returns:
        bool: 유효 여부
    """
    from features.validators.inbound_validator import InboundValidator
    return InboundValidator.validate_date(s)


@staticmethod
def amd_calc_dates(arrival_str: str, con_return_str: str, ft_raw: str):
    """
    날짜 계산
    P2: InboundValidator 위임
    
    Args:
        arrival_str: 입항일
        con_return_str: 반납일
        ft_raw: Free time (일수 또는 문자열)
    
    Returns:
        dict: 계산된 날짜 정보
    """
    from features.validators.inbound_validator import InboundValidator
    return InboundValidator.calc_dates(arrival_str, con_return_str, ft_raw)
