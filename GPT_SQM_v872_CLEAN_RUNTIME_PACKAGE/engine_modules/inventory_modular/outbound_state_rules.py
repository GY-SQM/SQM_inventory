# -*- coding: utf-8 -*-
"""
P2 Batch B — OutboundStateRules
출고 상태 전이 규칙, 유효성 검증, 설정값 조회.
outbound_mixin.py에서 분리한 순수 규칙 로직.
"""
import os
import configparser
import hashlib
import logging
from datetime import datetime

from engine_modules.constants import (
    STATUS_AVAILABLE, STATUS_RESERVED, STATUS_DEPLETED,
    STATUS_PICKED, STATUS_SOLD, STATUS_OUTBOUND, STATUS_PARTIAL,
    normalize_customer,
)
from core.types import normalize_lot

logger = logging.getLogger(__name__)


class OutboundStateRules:
    """출고 상태 전이 규칙 및 정책 정의."""

    # 승인 임계치
    ALLOCATION_APPROVAL_QTY_KG_THRESHOLD = 20000.0
    ALLOCATION_APPROVAL_RATIO_THRESHOLD = 1.01

    # 상태별 직전 단계 매핑 (cancel_reservation 용)
    PREV_STATUS_TONBAG = {
        'RESERVED': STATUS_AVAILABLE,
        'PENDING_APPROVAL': STATUS_AVAILABLE,
        'STAGED': STATUS_AVAILABLE,
        'PICKED': 'RESERVED',
        'EXECUTED': 'RESERVED',
        'OUTBOUND': STATUS_PICKED,
        'SOLD': STATUS_PICKED,
        'SHIPPED': STATUS_PICKED,
        'CONFIRMED': STATUS_PICKED,
    }

    PREV_STATUS_PLAN = {
        'RESERVED': 'CANCELLED',
        'PENDING_APPROVAL': 'CANCELLED',
        'STAGED': 'CANCELLED',
        'PICKED': 'RESERVED',
        'EXECUTED': 'RESERVED',
        'OUTBOUND': 'EXECUTED',
        'SOLD': 'EXECUTED',
        'SHIPPED': 'EXECUTED',
        'CONFIRMED': 'EXECUTED',
    }

    @staticmethod
    def allocation_risk_flags(qty_kg: float, available_kg: float,
                              threshold_kg: float = 20000.0,
                              threshold_ratio: float = 1.01) -> list:
        """승인 위험 플래그 계산."""
        flags = []
        if qty_kg >= threshold_kg:
            flags.append("LARGE_VOLUME")
        if available_kg > 0 and qty_kg >= available_kg * threshold_ratio:
            flags.append("OVER_50PCT")
        return flags

    @staticmethod
    def allocation_requires_approval(qty_kg: float, available_kg: float,
                                     threshold_kg: float = 20000.0,
                                     threshold_ratio: float = 1.01) -> bool:
        """승인 필요 여부 판정."""
        return len(OutboundStateRules.allocation_risk_flags(
            qty_kg, available_kg, threshold_kg, threshold_ratio)) > 0

    @staticmethod
    def normalize_outbound_date(raw_date) -> str:
        """outbound_date를 YYYY-MM-DD로 정규화. 실패 시 ValueError."""
        txt = str(raw_date or "").strip()
        if not txt:
            _today = datetime.now().strftime('%Y-%m-%d')
            logger.warning(
                f"[C OUTBOUND_DATE_NULL] outbound_date 미입력 → 오늘 날짜 자동 설정: {_today}"
            )
            return _today
        try:
            return datetime.strptime(txt[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            raise ValueError(f"INVALID_OUTBOUND_DATE: '{txt}' (허용 형식: YYYY-MM-DD)")

    @staticmethod
    def get_allocation_random_mode() -> str:
        """Allocation 랜덤 모드 조회: 'random' | 'seeded'."""
        raw = str(os.environ.get("SQM_ALLOC_RANDOM_MODE", "") or "").strip().lower()
        if not raw:
            try:
                cfg = configparser.ConfigParser()
                cfg.read(os.path.join(os.getcwd(), "settings.ini"), encoding="utf-8")
                raw = str(cfg.get("outbound", "allocation_random_mode", fallback="")).strip().lower()
            except Exception as e:
                logger.debug(f"allocation_random_mode 설정 읽기 스킵: {e}")
        if raw in ("seeded", "deterministic", "reproducible", "sale_ref_seed", "seed"):
            return "seeded"
        return "random"

    @staticmethod
    def get_allocation_strict_mode() -> bool:
        """Allocation Strict 모드 조회."""
        raw = str(os.environ.get("SQM_ALLOCATION_STRICT_MODE", "") or "").strip().lower()
        if not raw:
            try:
                cfg = configparser.ConfigParser()
                cfg.read(os.path.join(os.getcwd(), "settings.ini"), encoding="utf-8")
                raw = str(cfg.get("outbound", "allocation_strict_mode", fallback="")).strip().lower()
            except Exception as e:
                logger.debug(f"allocation_strict_mode 설정 읽기 스킵: {e}")
        if not raw:
            return True
        return raw in ("1", "true", "yes", "on", "strict")

    @staticmethod
    def get_allocation_reservation_mode(override_mode: str = "") -> str:
        """v6.9.4 [LOT-MODE-ONLY]: 항상 'lot' 반환."""
        _ = override_mode
        return "lot"

    @staticmethod
    def compute_lot_status(cnt_map: dict, current_weight: float = 0) -> str:
        """톤백 상태별 COUNT 기반 LOT 상태 판정.

        Args:
            cnt_map: {status_str: count} 딕셔너리
            current_weight: inventory.current_weight
        Returns:
            새로운 LOT 상태 문자열
        """
        _avail_cnt = cnt_map.get(STATUS_AVAILABLE, 0)
        _reserved_cnt = cnt_map.get(STATUS_RESERVED, 0)
        _picked_cnt = cnt_map.get(STATUS_PICKED, 0)
        _return_cnt = cnt_map.get('RETURN', 0)
        _outbound_cnt = (cnt_map.get(STATUS_OUTBOUND, 0)
                         + cnt_map.get(STATUS_SOLD, 0)
                         + cnt_map.get('SHIPPED', 0)
                         + cnt_map.get('CONFIRMED', 0))
        _total_cnt = sum(cnt_map.values())

        if _avail_cnt > 0 and _outbound_cnt == 0:
            return STATUS_AVAILABLE
        elif _avail_cnt > 0 and _outbound_cnt > 0:
            return STATUS_PARTIAL
        elif _total_cnt > 0 and _outbound_cnt >= _total_cnt:
            return STATUS_OUTBOUND
        elif _return_cnt > 0:
            return 'RETURN'
        elif _picked_cnt > 0:
            return STATUS_PICKED
        elif _reserved_cnt > 0:
            return STATUS_RESERVED
        else:
            return STATUS_DEPLETED if current_weight <= 0 else STATUS_AVAILABLE

    @staticmethod
    def build_allocation_seed(lot_no: str, sale_ref: str, qty_mt: float,
                              outbound_date, source_file: str) -> str:
        """Allocation 시드 생성."""
        sale_ref_norm = str(sale_ref or "").strip().upper()
        date_norm = str(outbound_date or "").strip()[:10]
        source_norm = str(source_file or "").strip()
        base = (
            f"sale_ref={sale_ref_norm}|lot={str(lot_no or '').strip().upper()}|"
            f"qty_mt={float(qty_mt or 0):.6f}|date={date_norm}|src={source_norm}"
        )
        return hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()

    @staticmethod
    def compute_allocation_source_fingerprint(allocation_rows: list, source_file: str = "") -> str:
        """Allocation 입력 fingerprint 생성."""
        try:
            sf = str(source_file or "").strip()
            if sf and sf != "(붙여넣기)" and os.path.isfile(sf):
                try:
                    h = hashlib.sha1()
                    with open(sf, "rb") as f:
                        for chunk in iter(lambda: f.read(1024 * 1024), b""):
                            h.update(chunk)
                    return h.hexdigest()
                except Exception as e:
                    logger.debug(f"Allocation 파일 해시 계산 실패(메타 대체): {e}")
                try:
                    st = os.stat(sf)
                    base = f"path={os.path.abspath(sf)}|size={st.st_size}|mtime={int(st.st_mtime)}"
                    return hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()
                except Exception as e:
                    logger.debug(f"Allocation 파일 메타 해시 계산 실패: {e}")

            normalized_rows = []
            for alloc in (allocation_rows or []):
                lot_no = str(alloc.get("lot_no", "") if isinstance(alloc, dict) else getattr(alloc, "lot_no", "")).strip().upper()
                qty_mt = float((alloc.get("qty_mt", 0) if isinstance(alloc, dict) else getattr(alloc, "qty_mt", 0)) or 0)
                sold_to = str(alloc.get("sold_to", "") if isinstance(alloc, dict) else getattr(alloc, "sold_to", "")).strip().upper()
                customer = str(alloc.get("customer", "") if isinstance(alloc, dict) else getattr(alloc, "customer", "")).strip().upper()
                sale_ref = str(alloc.get("sale_ref", "") if isinstance(alloc, dict) else getattr(alloc, "sale_ref", "")).strip().upper()
                outbound_date = str(
                    alloc.get("outbound_date", "") if isinstance(alloc, dict) else getattr(alloc, "outbound_date", "")
                ).strip()[:10]
                normalized_rows.append(
                    f"{lot_no}|{qty_mt:.6f}|{sold_to}|{customer}|{sale_ref}|{outbound_date}"
                )
            normalized_rows.sort()
            base = "paste|" + "\n".join(normalized_rows)
            return hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()
        except Exception as e:
            logger.debug(f"Allocation fingerprint 계산 실패: {e}")
            return ""

    @staticmethod
    def alloc_val(alloc, key, default=None):
        """AllocationRow(dataclass) 또는 dict 모두 지원하는 값 접근 헬퍼."""
        if isinstance(alloc, dict):
            return alloc.get(key, default)
        return getattr(alloc, key, default)

    @staticmethod
    def parse_allocation_line(alloc, alloc_val_fn=None):
        """Allocation 행 1줄을 파싱하여 dict로 반환."""
        _av = alloc_val_fn or OutboundStateRules.alloc_val
        lot_no = (normalize_lot(_av(alloc, 'lot_no')) or '').strip()
        _raw_customer = str(_av(alloc, 'sold_to') or _av(alloc, 'customer') or '').strip()
        try:
            customer = normalize_customer(_raw_customer)
        except Exception as exc:
            logger.debug("normalize_customer 실패, 원본값 사용: %s", exc)
            customer = _raw_customer
        sale_ref = str(_av(alloc, 'sale_ref') or '').strip()
        qty_mt = float(_av(alloc, 'qty_mt') or 0)
        outbound_date = _av(alloc, 'outbound_date')
        sublot_count = int(_av(alloc, 'sublot_count') or _av(alloc, 'tonbag_count') or 0)
        is_sample_req = bool(_av(alloc, 'is_sample', False))
        export_type_val = str(_av(alloc, 'export_type') or '').strip()
        _sc = _av(alloc, 'sc_rcvd')
        sc_rcvd_val = str(_sc) if _sc else None
        _unit_val = str(_av(alloc, 'unit') or '').strip().upper()
        return {
            'lot_no': lot_no, 'customer': customer, '_raw_customer': _raw_customer,
            'sale_ref': sale_ref, 'qty_mt': qty_mt, 'outbound_date': outbound_date,
            'sublot_count': sublot_count, 'is_sample_req': is_sample_req,
            'export_type_val': export_type_val, 'sc_rcvd_val': sc_rcvd_val,
            'unit_val': _unit_val,
        }

    @staticmethod
    def validate_line_inputs(ctx: dict, line_no: int) -> tuple:
        """행 입력 유효성 검증. (error_code, message) 반환. 통과 시 ('', '')."""
        lot_no = ctx['lot_no']
        customer = ctx['customer']
        qty_mt = ctx['qty_mt']
        sale_ref = ctx['sale_ref']

        if not lot_no:
            return "INVALID_LOT", "LOT 번호 누락"
        if qty_mt == 0:
            return "ZERO_QTY", (
                f"[AL-09][ZERO_QTY] LOT {lot_no}: qty_mt=0 "
                f"(빈 행 또는 수량 미입력 — 엑셀 확인 필요)")
        if qty_mt < 0:
            return "INVALID_QTY", (
                f"[INVALID_QTY] LOT {lot_no}: qty_mt={qty_mt} "
                f"(음수는 예약 불가 — 양수값 입력 필요)")
        if not customer:
            return "INVALID_CUSTOMER", (
                f"[INVALID_CUSTOMER] LOT {lot_no}: customer/sold_to가 비어 있음 "
                f"(고객사 지정 필수)")
        if ctx['unit_val'] and ctx['unit_val'] not in ('', 'KG'):
            return "UNIT_MISMATCH", (
                f"[UNIT_MISMATCH] 허용되지 않은 단위: '{ctx['unit_val']}' "
                f"(lot={lot_no}, line={line_no}) — KG만 허용")
        if not sale_ref:
            return "", f"[WARN_SALE_REF] LOT {lot_no}: sale_ref 미입력"
        return "", ""
