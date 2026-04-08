"""
SQM P2 — InboundParser: 원스톱 입고 파싱 로직 분리
===================================================

onestop_inbound.py에서 분리된 순수 파싱 + 데이터 병합 로직.
UI 의존성 없음 — log_fn / progress_fn 콜백으로 외부 알림.

분리 대상 (원본 메서드):
  - _pt_init_parser       → init_parser
  - _pt_extract_template_hints → extract_template_hints
  - _pt_parse_documents   → parse_documents
  - _pt_parse_bl          → parse_bl_document
  - _pt_handle_bl_carrier_detection → handle_bl_carrier_detection
  - _merge_results        → merge_results
  - _empty_row            → empty_row
  - _date_str             → date_str
  - _format_bl            → format_bl
  - _fill_do              → fill_do
  - _lot_order_key        → lot_order_key
"""
import os
import logging
from datetime import datetime, timedelta, date as _date_type
from typing import Callable, Optional

from engine_modules.constants import DEFAULT_TONBAG_WEIGHT, STATUS_AVAILABLE
from core.constants import DEFAULT_WAREHOUSE
from core.types import safe_float

logger = logging.getLogger(__name__)

# 미리보기 컬럼 정의 — onestop_inbound.py PREVIEW_COLUMNS와 동일
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
    ("arrival_date",     "ARRIVAL",          90,  "center"),
    ("con_return",       "CON RETURN",       95,  "center"),
    ("free_time",        "FREE TIME",        80,  "center"),
    ("warehouse",        "WH",              100,  "center"),
]

# 선사 → 캐리어ID 매핑
_CARRIER_FROM_TPL = {
    'MSC':      'MSC',    'MAERSK': 'MAERSK',
    'MERSK':    'MAERSK', 'HMM':    'HMM',
    'COSCO':    'COSCO',  'CMA':    'CMA_CGM',
    'EVERGREEN':'EVERGREEN', 'ONE': 'ONE',
    'HAPAG':    'HAPAG',
}


class InboundParser:
    """원스톱 입고 파싱 엔진 — UI 의존성 없음.

    사용법:
        parser = InboundParser(log_fn=print, progress_fn=update_bar)
        parser_instance = parser.init_parser()
        ctx = parser.extract_template_hints(template_data)
        results = parser.parse_documents(parser_instance, ctx, file_paths)
        preview = parser.merge_results(results['invoice'], results['pl'],
                                        results['bl'], results['do'])
    """

    def __init__(
        self,
        log_fn: Optional[Callable] = None,
        progress_fn: Optional[Callable] = None,
    ):
        self._log = log_fn or (lambda msg: logger.info(msg))
        self._progress = progress_fn or (lambda pct, msg: None)

    # ───────────────────────────────────────────────────────────
    # Parser 초기화
    # ───────────────────────────────────────────────────────────

    def init_parser(self):
        """Gemini API 키 확인 후 DocumentParserV3 인스턴스 반환.

        Raises:
            RuntimeError: API 키가 없거나 유효하지 않은 경우.
        """
        from parsers.document_parser_modular import DocumentParserV3 as DocumentParserV2

        gemini_key = os.environ.get('GEMINI_API_KEY', '')
        if not gemini_key:
            try:
                from core.config import get_settings
                settings = get_settings()
                gemini_key = settings.get('gemini_api_key', '')
            except (ImportError, ModuleNotFoundError) as _e:
                logger.debug(f"inbound_parser: {_e}")

        if not gemini_key or str(gemini_key).strip() == '' or str(gemini_key).startswith('your-'):
            raise RuntimeError(
                "API-only 모드: Gemini API Key가 필요합니다. 설정에서 API Key를 입력하세요."
            )

        return DocumentParserV2(gemini_api_key=gemini_key)

    # ───────────────────────────────────────────────────────────
    # 템플릿 힌트 추출
    # ───────────────────────────────────────────────────────────

    def extract_template_hints(self, template_data: dict = None) -> dict:
        """선택된 템플릿에서 bag_weight / gemini_hint / carrier_id 추출.

        Returns:
            dict with keys: bag_weight, hint_packing, hint_invoice, hint_bl,
                           bl_format, tpl_id, tpl_carrier_id
        """
        _tpl = template_data or {}
        _bag_weight       = int(_tpl.get('bag_weight_kg') or DEFAULT_TONBAG_WEIGHT)
        _hint_packing     = str(_tpl.get('gemini_hint_packing', '') or '')
        _hint_invoice     = str(_tpl.get('gemini_hint_invoice', '') or '')
        _hint_bl          = str(_tpl.get('gemini_hint_bl',      '') or '')
        _bl_format        = str(_tpl.get('bl_format', '') or '')
        _tpl_id           = _tpl.get('template_id', 'NONE')
        _tpl_carrier_id   = str(_tpl.get('carrier_id', '') or '').strip().upper()

        # template_id 기반 carrier_id 자동 보정
        _tpl_id_upper = str(_tpl_id or '').upper()
        _inferred = ''
        for _kw, _cv in _CARRIER_FROM_TPL.items():
            if _kw in _tpl_id_upper:
                _inferred = _cv
                break
        if _inferred and _inferred != _tpl_carrier_id:
            logger.warning(
                f"[inbound_parser] carrier_id 불일치 수정: DB='{_tpl_carrier_id}' "
                f"template_id 추론='{_inferred}' → {_inferred} 사용"
            )
            _tpl_carrier_id = _inferred
        elif not _tpl_carrier_id and _inferred:
            _tpl_carrier_id = _inferred

        logger.info(
            f"[inbound_parser] 파싱 템플릿: {_tpl_id} / {_bag_weight}kg "
            f"/ 힌트PL={bool(_hint_packing)} INV={bool(_hint_invoice)} BL={bool(_hint_bl)}"
            f" / 선사={_tpl_carrier_id or '미지정'}"
        )

        return {
            'bag_weight': _bag_weight,
            'hint_packing': _hint_packing,
            'hint_invoice': _hint_invoice,
            'hint_bl': _hint_bl,
            'bl_format': _bl_format,
            'tpl_id': _tpl_id,
            'tpl_carrier_id': _tpl_carrier_id,
        }

    # ───────────────────────────────────────────────────────────
    # 서류별 파싱
    # ───────────────────────────────────────────────────────────

    def parse_documents(self, parser, ctx: dict, file_paths: dict) -> dict:
        """서류별 파싱 루프 — BL → PL → INV → DO 순서.

        Args:
            parser: DocumentParserV3 인스턴스
            ctx: extract_template_hints() 결과
            file_paths: {doc_type: file_path}

        Returns:
            dict: {'pl': result, 'inv': result, 'bl': result, 'do': result,
                   'total': int, 'parsed_results': dict}
        """
        parse_order = ['BL', 'PACKING_LIST', 'INVOICE', 'DO']
        to_parse = [(dt, file_paths[dt]) for dt in parse_order if dt in file_paths]
        total = len(to_parse)
        if total == 0:
            self._progress(90, "파싱할 파일이 없습니다")
            return {'pl': None, 'inv': None, 'bl': None, 'do': None,
                    'total': 0, 'parsed_results': {}}

        icons = {'PACKING_LIST': '📦', 'INVOICE': '📑', 'BL': '🚢', 'DO': '📋'}
        doc_type_display = {
            'PACKING_LIST': 'Packing List',
            'INVOICE': 'Invoice, FA',
            'BL': 'Bill of Loading',
            'DO': 'Delivery Order',
        }

        pl_result = None
        inv_result = None
        bl_result = None
        do_result = None
        parsed_results = {}

        for idx, (doc_type, file_path) in enumerate(to_parse):
            fname = os.path.basename(file_path)
            icon = icons.get(doc_type, '📄')
            pct = int(10 + 70 * idx / total)
            doc_name = doc_type_display.get(doc_type, doc_type)
            self._progress(pct, f"현재 파싱 중: {doc_name} — {fname}")
            self._log(f"{icon} {doc_type} 파싱: {fname}")

            try:
                if doc_type == 'PACKING_LIST':
                    pl_result = parser.parse_packing_list(
                        file_path,
                        bag_weight_kg=ctx['bag_weight'],
                        gemini_hint=ctx['hint_packing'],
                    )
                    parsed_results['packing_list'] = pl_result
                    _lots = getattr(pl_result, 'lots', []) if pl_result else []
                    if _lots:
                        _tnw = getattr(pl_result, 'total_net_weight_kg', 0) or 0
                        self._log(f"  ✅ LOTs: {len(_lots)}, Net: {_tnw:,.0f}kg")

                elif doc_type == 'INVOICE':
                    inv_result = parser.parse_invoice(
                        file_path,
                        gemini_hint=ctx['hint_invoice'],
                    )
                    parsed_results['invoice'] = inv_result
                    if inv_result:
                        self._log(
                            f"  ✅ SAP: {getattr(inv_result, 'sap_no', '')}, "
                            f"Invoice: {getattr(inv_result, 'salar_invoice_no', '')}"
                        )

                elif doc_type == 'BL':
                    bl_result = self.parse_bl_document(parser, file_path, ctx)
                    parsed_results['bl'] = bl_result
                    # 선사 감지 → 힌트 동적 교체 (ctx 변이)
                    self.handle_bl_carrier_detection(bl_result, ctx)

                elif doc_type == 'DO':
                    try:
                        from features.parsers.onestop_inbound_candidate_patch import (
                            parse_do_with_candidate,
                        )
                        do_result = parse_do_with_candidate(
                            parser, file_path, log_fn=self._log,
                        )
                    except ImportError:
                        do_result = parser.parse_do(file_path)
                    parsed_results['do'] = do_result
                    if do_result:
                        self._log(f"  ✅ D/O: B/L={getattr(do_result, 'bl_no', '')}")

            except (ValueError, TypeError, AttributeError, RuntimeError) as e:
                self._log(f"  ❌ {doc_type} 파싱 오류: {e}")
                logger.error(f"파싱 오류 [{doc_type}]: {e}", exc_info=True)
                if isinstance(e, RuntimeError) and doc_type == 'PACKING_LIST':
                    self._log(
                        "  💡 Packing List 실패 시 입고가 완료되지 않아 "
                        "톤백 리스트에 표시되지 않습니다."
                    )

        return {
            'pl': pl_result,
            'inv': inv_result,
            'bl': bl_result,
            'do': do_result,
            'total': total,
            'parsed_results': parsed_results,
        }

    def parse_bl_document(self, parser, file_path: str, ctx: dict):
        """BL 서류 파싱 — 다중 템플릿 후보 엔진 또는 단일 파싱."""
        try:
            from features.parsers.onestop_inbound_candidate_patch import (
                parse_bl_with_candidate,
            )
            _has_candidate = True
        except ImportError:
            _has_candidate = False

        if _has_candidate:
            bl_result = parse_bl_with_candidate(
                parser,
                file_path,
                hint_bl=ctx['hint_bl'],
                bl_format=ctx['bl_format'],
                log_fn=self._log,
                use_multi=True,
                db_carrier_id=ctx['tpl_carrier_id'],
            )
        else:
            bl_result = parser.parse_bl(
                file_path,
                gemini_hint=ctx['hint_bl'],
                bl_format=ctx['bl_format'],
            )

        if bl_result:
            _carrier_id   = getattr(bl_result, 'carrier_id', '')
            _carrier_name = getattr(bl_result, 'carrier_name', '')
            if _carrier_id and _carrier_id != 'UNKNOWN':
                _badge = f"[선사: {_carrier_name or _carrier_id}]"
            else:
                _badge = "[선사: 미확인]"
            self._log(
                f"  ✅ B/L: {getattr(bl_result, 'bl_no', '')} "
                f"{_badge}  "
                f"Containers: {getattr(bl_result, 'total_containers', 0)}"
            )

        return bl_result

    def handle_bl_carrier_detection(self, bl_result, ctx: dict) -> Optional[dict]:
        """BL 파싱 후 선사 감지 → PL/INV 힌트 동적 교체.

        Returns:
            auto-matched template dict if found, else None
        """
        if not bl_result:
            return None
        _carrier_id = getattr(bl_result, 'carrier_id', '')
        if not _carrier_id or _carrier_id == 'UNKNOWN':
            return None

        auto_tpl = None

        # 선사 미선택 상태에서 BL 감지 선사로 힌트 교체 시도
        try:
            from features.ai.bl_carrier_registry import CARRIER_TEMPLATES
            _ctpl = CARRIER_TEMPLATES.get(_carrier_id)
            if _ctpl:
                if not ctx['hint_packing'] and hasattr(_ctpl, 'bl_no_prompt_hint'):
                    ctx['hint_packing'] = (
                        f"이 서류는 {_ctpl.carrier_name} 선사의 Packing List입니다. "
                        f"BL번호 형식: {_ctpl.bl_format_hint}"
                    )
                if not ctx['hint_invoice'] and hasattr(_ctpl, 'carrier_name'):
                    ctx['hint_invoice'] = (
                        f"이 서류는 {_ctpl.carrier_name} 선사의 Invoice/FA입니다."
                    )
                self._log(
                    f"  🔄 선사 힌트 동적 교체: {_ctpl.carrier_name} "
                    f"(PL힌트={'ON' if ctx['hint_packing'] else 'OFF'}, "
                    f"INV힌트={'ON' if ctx['hint_invoice'] else 'OFF'})"
                )
        except (ImportError, ValueError, KeyError, AttributeError) as _he:
            logger.warning(f"선사 힌트 교체 실패(무시): {_he}")

        return auto_tpl

    # ───────────────────────────────────────────────────────────
    # 결과 병합
    # ───────────────────────────────────────────────────────────

    def merge_results(self, invoice, pl, bl, do, engine_db=None) -> list:
        """4종 파싱 결과를 18열 미리보기 데이터로 병합.

        Args:
            invoice, pl, bl, do: 각 서류 파싱 결과
            engine_db: D/O만 있는 경우 DB 자동매칭용 (engine.db)

        Returns:
            list of dict — preview_data 행 목록
        """
        preview_data = []

        if not pl or not getattr(pl, 'lots', None):
            if invoice and getattr(invoice, 'lot_numbers', None):
                for idx, lot_no in enumerate(getattr(invoice, 'lot_numbers', []), 1):
                    row = self.empty_row(idx)
                    row['sap_no'] = getattr(invoice, 'sap_no', '') or ''
                    row['lot_no'] = lot_no
                    row['product'] = getattr(invoice, 'product', '') or 'LITHIUM CARBONATE'
                    row['salar_invoice_no'] = getattr(invoice, 'salar_invoice_no', '') or ''
                    row['ship_date'] = (
                        str(getattr(invoice, 'invoice_date', ''))
                        if getattr(invoice, 'invoice_date', None) else ''
                    )
                    if bl:
                        row['bl_no'] = self.format_bl(getattr(bl, 'bl_no', '') or '')
                    self.fill_do(row, do)
                    row['status'] = STATUS_AVAILABLE
                    preview_data.append(row)
            elif do and engine_db:
                # D/O만 있는 경우: DB에서 기존 LOT(B/L 기준) 자동 조회
                try:
                    from core.types import norm_bl_no_for_query
                except ImportError:
                    try:
                        from utils.common import norm_bl_no_for_query
                    except ImportError:
                        norm_bl_no_for_query = lambda x: x

                try:
                    do_bl_raw = str(getattr(do, 'bl_no', '') or '').strip()
                    do_bl_fmt = self.format_bl(do_bl_raw)
                    candidates = [x for x in {do_bl_raw, do_bl_fmt} if x]
                    db_rows = []
                    for c in candidates:
                        rows = engine_db.fetchall(
                            "SELECT * FROM inventory WHERE bl_no = ? ORDER BY lot_no",
                            (norm_bl_no_for_query(c) or c,)
                        ) or []
                        if rows:
                            db_rows = rows
                            break
                    for idx, rec in enumerate(db_rows, 1):
                        row = self.empty_row(idx)
                        row['sap_no'] = str(rec.get('sap_no', '') or '')
                        row['bl_no'] = str(rec.get('bl_no', '') or do_bl_fmt or do_bl_raw or '')
                        row['container_no'] = str(rec.get('container_no', '') or '')
                        row['product'] = str(rec.get('product', '') or 'LITHIUM CARBONATE')
                        row['product_code'] = str(rec.get('product_code', '') or '')
                        row['lot_no'] = str(rec.get('lot_no', '') or '')
                        row['lot_sqm'] = str(rec.get('lot_sqm', '') or '')
                        row['mxbg_pallet'] = str(rec.get('mxbg_pallet', '') or '10')
                        _nw = rec.get('net_weight', '')
                        _gw = rec.get('gross_weight', '')
                        row['net_weight'] = f"{float(_nw):,.1f}" if str(_nw) not in ('', 'None', 'none') else ''
                        row['gross_weight'] = f"{float(_gw):,.3f}" if str(_gw) not in ('', 'None', 'none') else ''
                        row['salar_invoice_no'] = str(rec.get('salar_invoice_no', '') or '')
                        row['ship_date'] = str(rec.get('ship_date', '') or '')[:10]
                        row['arrival_date'] = str(rec.get('arrival_date', '') or '')[:10]
                        row['con_return'] = str(rec.get('con_return', '') or '')[:10]
                        row['free_time'] = str(rec.get('free_time', '') or '')
                        row['warehouse'] = str(rec.get('warehouse', '') or DEFAULT_WAREHOUSE)
                        row['status'] = str(rec.get('status', '') or STATUS_AVAILABLE)
                        self.fill_do(row, do)
                        preview_data.append(row)
                    if preview_data:
                        self._log(f"📎 D/O 기반 DB 자동매칭: {len(preview_data)}건 (B/L 기준)")
                except Exception as e:
                    logger.warning(f"D/O 단독 DB 자동매칭 실패: {e}")
            return preview_data

        _lots = list(getattr(pl, 'lots', []) or [])
        _lots_sorted = sorted(
            enumerate(_lots, 1),
            key=lambda p: self.lot_order_key(p[1], p[0])
        )
        for idx, (_src, lot) in enumerate(_lots_sorted, 1):
            row = self.empty_row(idx)
            row['sap_no'] = (
                getattr(pl, 'sap_no', '') or
                (getattr(invoice, 'sap_no', '') if invoice else '') or ''
            )
            row['container_no'] = getattr(lot, 'container_no', '') or ''
            row['product'] = getattr(pl, 'product', '') or 'LITHIUM CARBONATE'
            row['product_code'] = getattr(pl, 'code', '') or ''
            row['lot_no'] = getattr(lot, 'lot_no', '') or ''
            row['lot_sqm'] = getattr(lot, 'lot_sqm', '') or ''

            _mxbg = getattr(lot, 'mxbg_pallet', None)
            row['mxbg_pallet'] = str(_mxbg) if _mxbg else '10'

            _nw = getattr(lot, 'net_weight_kg', None)
            row['net_weight'] = f"{float(_nw):,.1f}" if _nw else ''

            _gw = getattr(lot, 'gross_weight_kg', None)
            row['gross_weight'] = f"{float(_gw):,.3f}" if _gw else ''

            if bl:
                row['bl_no'] = self.format_bl(getattr(bl, 'bl_no', '') or '')
                _sd = getattr(bl, 'ship_date', None)
                if _sd:
                    row['ship_date'] = str(_sd)[:10] if len(str(_sd)) >= 10 else str(_sd)

            if invoice:
                row['salar_invoice_no'] = getattr(invoice, 'salar_invoice_no', '') or ''
                if not (row.get('ship_date') or '').strip():
                    _id = getattr(invoice, 'invoice_date', None)
                    if _id:
                        row['ship_date'] = str(_id)[:10] if len(str(_id)) >= 10 else str(_id)
                if not row['sap_no']:
                    row['sap_no'] = getattr(invoice, 'sap_no', '') or ''

            self.fill_do(row, do)
            if not (row.get('warehouse') or '').strip():
                row['warehouse'] = DEFAULT_WAREHOUSE
            row['status'] = STATUS_AVAILABLE
            preview_data.append(row)

        return preview_data

    # ───────────────────────────────────────────────────────────
    # 유틸리티 (순수 함수)
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def empty_row(no: int) -> dict:
        """빈 미리보기 행 생성."""
        row = {col[0]: '' for col in PREVIEW_COLUMNS}
        row['no'] = str(no)
        return row

    @staticmethod
    def date_str(val) -> str:
        """날짜를 YYYY-MM-DD 문자열로. None/'None'/비어있으면 '' 반환."""
        if val is None or (isinstance(val, str) and (not val.strip() or val.strip() in ('None', 'none'))):
            return ''
        if hasattr(val, 'isoformat'):
            return str(val.isoformat())[:10]
        s = str(val).strip()
        return s[:10] if len(s) >= 10 and s not in ('None', 'none') else (s if s and s not in ('None', 'none') else '')

    @staticmethod
    def format_bl(bl_no) -> str:
        """BL번호 포맷 — 숫자만 9자리 이상이면 MAEU 접두사."""
        if not bl_no:
            return ''
        bl_no = str(bl_no).strip()
        if bl_no.isdigit() and len(bl_no) >= 9:
            return f"MAEU{bl_no}"
        return bl_no

    @staticmethod
    def fill_do(row: dict, do) -> None:
        """D/O 데이터로 미리보기 행 보완 (free_time 계산 포함)."""
        if not do:
            return
        if not row.get('bl_no') and getattr(do, 'bl_no', None):
            row['bl_no'] = str(getattr(do, 'bl_no', ''))

        # arrival_date
        arr = getattr(do, 'arrival_date', None)
        if arr and str(arr) != 'None':
            _s = str(arr).strip()[:10]
            if len(_s) == 10 and _s.count('-') == 2 and _s.replace('-', '').isdigit():
                row['arrival_date'] = _s

        # warehouse
        wh = getattr(do, 'warehouse_name', '') or getattr(do, 'warehouse', '')
        if wh:
            row['warehouse'] = str(wh)

        # FREE TIME 계산
        ft_infos = getattr(do, 'free_time_info', []) or []
        if ft_infos and arr and str(arr) != 'None':
            try:
                con_return_str = ''
                for ft in ft_infos:
                    ftd = (
                        (getattr(ft, 'free_time_date', '') or getattr(ft, 'free_time_until', ''))
                        if not isinstance(ft, dict)
                        else (ft.get('free_time_date') or ft.get('free_time_until') or '')
                    )
                    if ftd and str(ftd) != 'None':
                        con_return_str = str(ftd)[:10]
                        break
                if not con_return_str:
                    logger.debug(
                        "[inbound_parser] D/O free_time_info 있으나 반납일 없음. 항목 수: %s",
                        len(ft_infos),
                    )
                if con_return_str:
                    con_return_dt = datetime.strptime(con_return_str, '%Y-%m-%d').date()
                    arr_dt = datetime.strptime(str(arr)[:10], '%Y-%m-%d').date()
                    days = (con_return_dt - arr_dt).days
                    row['free_time'] = str(max(0, days))
                    row['con_return'] = str(con_return_str)[:10]
                    logger.debug(
                        "[inbound_parser] D/O 반납일 적용: con_return=%s, free_time=%s",
                        row['con_return'], row['free_time'],
                    )
            except (ValueError, TypeError) as e:
                logger.debug(f"free_time 계산 실패: {e}")

        # free_time 일수만 있는 경우
        if not (row.get('free_time') or '').strip():
            ft_single = getattr(do, 'free_time', None)
            if ft_single is not None:
                days_val = (
                    getattr(ft_single, 'storage_free_days', None) or
                    (ft_single.get('storage_free_days') if isinstance(ft_single, dict) else None)
                )
                if days_val is not None:
                    row['free_time'] = str(int(days_val))
                    if not (row.get('con_return') or '').strip() and arr and str(arr) != 'None':
                        try:
                            arr_dt = datetime.strptime(str(arr)[:10], '%Y-%m-%d').date()
                            con_dt = arr_dt + timedelta(days=int(days_val))
                            row['con_return'] = con_dt.strftime('%Y-%m-%d')
                        except (ValueError, TypeError):
                            pass

    @staticmethod
    def lot_order_key(lot, fallback_idx: int) -> tuple:
        """Packing List 원본 순서를 우선 유지 (list_no 기준)."""
        raw = getattr(lot, 'list_no', None)
        if raw is None and isinstance(lot, dict):
            raw = lot.get('list_no')
        try:
            return (0, int(str(raw).strip()))
        except (ValueError, TypeError):
            return (1, int(fallback_idx))
