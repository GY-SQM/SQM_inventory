"""
SQM 재고관리 시스템 - 문서 간 크로스 체크 엔진
==============================================

v6.2.1: 신규 생성

4종 선적 문서(Invoice, Packing List, B/L, D/O) 간 교차 검증을 수행합니다.

검증 항목:
    - SAP NO 일치 여부
    - B/L No 일치 여부
    - 선박명(Vessel) 일치 여부 (퍼지 매칭)
    - 총 순중량(Net Weight) 비교
    - 총 총중량(Gross Weight) 비교
    - LOT 개수 일치 여부
    - LOT 번호 목록 일치 여부
    - 컨테이너 수 일치 여부
    - 컨테이너 번호 일치 여부
    - 패키지 수 일치 여부
    - 제품명/코드 일치 여부
    - 중복 LOT 번호 검출

검증 레벨:
    - Level 1 (INFO): 사소한 차이 → 노란색
    - Level 2 (WARNING): 주의 필요 → 주황색, 사용자 확인 후 진행
    - Level 3 (CRITICAL): 심각한 불일치 → 빨간색, 업로드 차단

주의: B/L 파싱 및 SHIP DATE 파싱 로직은 이 모듈에서 변경하지 않습니다.
      이 모듈은 파싱 결과를 "읽기 전용"으로 참조하여 교차 검증만 수행합니다.

작성자: Ruby
버전: v6.2.1
날짜: 2026-02-27
"""

import logging
import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# 검증 레벨 정의
# =============================================================================

class CheckLevel(IntEnum):
    """크로스 체크 결과 레벨"""
    INFO = 1        # 사소한 차이 (노란색)
    WARNING = 2     # 주의 필요 (주황색)
    CRITICAL = 3    # 심각 — 업로드 차단 (빨간색)


# =============================================================================
# 검증 결과 데이터 클래스
# =============================================================================

@dataclass
class CheckItem:
    """개별 검증 항목 결과"""
    field_name: str          # 검증 항목명 (예: "Net Weight", "Vessel")
    level: CheckLevel        # INFO / WARNING / CRITICAL
    message: str             # 상세 메시지
    sources: Dict[str, str] = field(default_factory=dict)
    # sources: {"Invoice": "100020", "Packing List": "100020", "B/L": "99000"}

    @property
    def level_icon(self) -> str:
        if self.level == CheckLevel.INFO:
            return "ℹ️"
        elif self.level == CheckLevel.WARNING:
            return "⚠️"
        return "🚫"

    @property
    def level_color(self) -> str:
        """tkinter 호환 색상 코드"""
        if self.level == CheckLevel.INFO:
            return "#FFF3CD"       # 연한 노랑
        elif self.level == CheckLevel.WARNING:
            return "#FFE0B2"       # 연한 주황
        return "#FFCDD2"           # 연한 빨강

    def __str__(self) -> str:
        return f"{self.level_icon} [{self.field_name}] {self.message}"


@dataclass
class CrossCheckResult:
    """크로스 체크 전체 결과"""
    items: List[CheckItem] = field(default_factory=list)
    checked_at: str = ""     # 검증 시간
    _lot_levels_cache: Optional[Dict[str, CheckLevel]] = field(default=None, init=False, repr=False)

    @property
    def has_critical(self) -> bool:
        return any(i.level == CheckLevel.CRITICAL for i in self.items)

    @property
    def has_warning(self) -> bool:
        return any(i.level == CheckLevel.WARNING for i in self.items)

    @property
    def has_info(self) -> bool:
        return any(i.level == CheckLevel.INFO for i in self.items)

    @property
    def is_clean(self) -> bool:
        return len(self.items) == 0

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.items if i.level == CheckLevel.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.items if i.level == CheckLevel.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.items if i.level == CheckLevel.INFO)

    @property
    def summary(self) -> str:
        """한 줄 요약"""
        if self.is_clean:
            return "✅ 4종 서류 교차 검증 통과 — 불일치 없음"
        parts = []
        if self.critical_count > 0:
            parts.append(f"🚫 심각 {self.critical_count}건")
        if self.warning_count > 0:
            parts.append(f"⚠️ 주의 {self.warning_count}건")
        if self.info_count > 0:
            parts.append(f"ℹ️ 참고 {self.info_count}건")
        return "크로스 체크: " + ", ".join(parts)

    @property
    def detail_text(self) -> str:
        """전체 상세 텍스트 (팝업/로그용)"""
        if self.is_clean:
            return self.summary
        lines = [self.summary, ""]
        for item in sorted(self.items, key=lambda x: -x.level):
            lines.append(str(item))
            if item.sources:
                for src, val in item.sources.items():
                    lines.append(f"    {src}: {val}")
        return "\n".join(lines)

    def add(self, field_name: str, level: CheckLevel, message: str,
            sources: Dict[str, str] = None):
        """검증 항목 추가"""
        # 항목이 추가되면 LOT 레벨 캐시는 무효화한다.
        self._lot_levels_cache = None
        self.items.append(CheckItem(
            field_name=field_name,
            level=level,
            message=message,
            sources=sources or {}
        ))

    # ─── 행 단위 하이라이트 지원 ───

    # LOT 관련 필드명 (이 필드의 불일치는 특정 LOT에 매핑)
    _LOT_FIELDS = {"중복 LOT", "LOT 번호 (Invoice Only)", "LOT 번호 (PL Only)"}
    # 전체 문서 레벨 필드명 (모든 행에 적용)
    _GLOBAL_FIELDS = {
        "SAP NO", "B/L No", "Vessel", "Product",
        "Net Weight", "Gross Weight", "LOT 개수",
        "Container 수", "Container 번호", "Package 수",
    }

    @property
    def global_level(self) -> Optional[CheckLevel]:
        """문서 전체에 해당하는 최고 레벨 (행 전체 하이라이트용)"""
        levels = [i.level for i in self.items if i.field_name in self._GLOBAL_FIELDS]
        return max(levels) if levels else None

    def get_lot_levels(self) -> Dict[str, CheckLevel]:
        """
        LOT별 최고 레벨 매핑 반환

        Returns:
            {"1125081447": CheckLevel.CRITICAL, ...}
        """
        if self._lot_levels_cache is not None:
            return self._lot_levels_cache
        lot_map: Dict[str, CheckLevel] = {}
        for item in self.items:
            if item.field_name not in self._LOT_FIELDS:
                continue
            # sources에서 LOT 번호 추출
            lot_no = item.sources.get("LOT No", "")
            if lot_no:
                # 중복 LOT → 해당 LOT만
                existing = lot_map.get(lot_no)
                if existing is None or item.level > existing:
                    lot_map[lot_no] = item.level
            else:
                # LOT 목록 불일치 → sources에서 LOT 번호들 추출
                for key, val in item.sources.items():
                    for ln in val.split(","):
                        ln = ln.strip()
                        if ln and len(ln) >= 10:
                            existing = lot_map.get(ln)
                            if existing is None or item.level > existing:
                                lot_map[ln] = item.level
        self._lot_levels_cache = lot_map
        return lot_map

    def get_row_tag(self, lot_no: str) -> Optional[str]:
        """
        주어진 LOT 번호에 대한 tkinter 태그명 반환

        Returns:
            "xc_critical" / "xc_warning" / "xc_info" / None
        """
        lot_levels = self.get_lot_levels()
        # LOT 직접 매핑
        lot_level = lot_levels.get(lot_no)
        # 전체 문서 레벨
        global_lv = self.global_level
        # 둘 중 높은 쪽
        effective = None
        if lot_level and global_lv:
            effective = max(lot_level, global_lv)
        elif lot_level:
            effective = lot_level
        elif global_lv:
            effective = global_lv

        if effective == CheckLevel.CRITICAL:
            return "xc_critical"
        elif effective == CheckLevel.WARNING:
            return "xc_warning"
        elif effective == CheckLevel.INFO:
            return "xc_info"
        return None


# =============================================================================
# 유틸리티 함수
# =============================================================================

def _safe_str(obj, attr: str) -> str:
    """안전하게 문자열 속성 추출"""
    val = getattr(obj, attr, None) if obj else None
    if val is None:
        return ""
    return str(val).strip()


def _safe_float(obj, attr: str) -> Optional[float]:
    """안전하게 float 속성 추출"""
    val = getattr(obj, attr, None) if obj else None
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _normalize_vessel(vessel: str) -> str:
    """
    선박명 정규화 — 비교용 (대소문자 통일, 불필요 공백/특수문자 제거)
    예: "CHARLOTTE MAERSK 535W" → "CHARLOTTE MAERSK 535W"
        "CHARLOTTE MAERSK"      → "CHARLOTTE MAERSK"
    """
    if not vessel:
        return ""
    v = re.sub(r'[^\w\s]', ' ', vessel.upper())
    v = re.sub(r'\s+', ' ', v).strip()
    return v


def _normalize_container(container_no: str) -> str:
    """
    컨테이너 번호 정규화
    예: "FFAU5355006"  → "FFAU5355006"
        "FFAU535500-6" → "FFAU5355006"
    """
    if not container_no:
        return ""
    return re.sub(r'[^A-Z0-9]', '', container_no.upper())


def _normalize_bl(bl_no: str) -> str:
    """
    B/L 번호 정규화 — 앞에 MAEU 등 캐리어 코드 제거하고 숫자만
    예: "MAEU258468669" → "258468669"
        "258468669"     → "258468669"
    """
    if not bl_no:
        return ""
    bl = str(bl_no).strip().upper()
    # 캐리어 코드(4글자 알파벳) 제거
    m = re.match(r'^[A-Z]{3,4}(\d{6,})$', bl)
    if m:
        return m.group(1)
    return bl


def _vessel_fuzzy_match(v1: str, v2: str) -> bool:
    """
    선박명 퍼지 매칭 — 한쪽이 다른 쪽을 포함하면 일치로 간주
    예: "CHARLOTTE MAERSK 535W" vs "CHARLOTTE MAERSK" → True
    """
    n1 = _normalize_vessel(v1)
    n2 = _normalize_vessel(v2)
    if not n1 or not n2:
        return True  # 빈 값은 비교 불가 → 패스
    if n1 == n2:
        return True
    # 한쪽이 다른 쪽을 포함
    if n1 in n2 or n2 in n1:
        return True
    # 첫 두 단어가 같으면 (선박명만 같고 항차 다를 수 있음)
    words1 = n1.split()[:2]
    words2 = n2.split()[:2]
    if words1 == words2 and len(words1) >= 2:
        return True
    return False


def _weight_diff_pct(w1: float, w2: float) -> float:
    """두 중량 간 차이 비율(%) 계산"""
    if w1 == 0 and w2 == 0:
        return 0.0
    base = max(w1, w2)
    if base == 0:
        return 100.0
    return abs(w1 - w2) / base * 100.0


# =============================================================================
# 크로스 체크 엔진
# =============================================================================

class CrossCheckEngine:
    """
    4종 선적 문서 교차 검증 엔진

    사용법:
        engine = CrossCheckEngine()
        result = engine.check(invoice, packing_list, bl, do)
        if result.has_critical:
            # 업로드 차단
        print(result.detail_text)

    주의:
        - B/L 파싱 로직, SHIP DATE 파싱 로직은 변경하지 않습니다.
        - 이 엔진은 파싱 결과를 읽기 전용으로 참조합니다.
    """

    # 중량 오차 임계값 (%)
    WEIGHT_WARN_THRESHOLD = 1.0     # 1% 이상 → WARNING
    WEIGHT_CRITICAL_THRESHOLD = 5.0  # 5% 이상 → CRITICAL

    def __init__(self):
        pass

    def check(
        self,
        invoice=None,
        packing_list=None,
        bl=None,
        do=None
    ) -> CrossCheckResult:
        """
        4종 문서 교차 검증 수행

        Args:
            invoice: InvoiceData 객체
            packing_list: PackingListData 객체
            bl: BLData 객체
            do: DOData 객체

        Returns:
            CrossCheckResult: 교차 검증 결과
        """
        from datetime import datetime
        result = CrossCheckResult(checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 문서가 2개 미만이면 교차 검증 불가
        doc_count = sum(1 for d in [invoice, packing_list, bl, do] if d is not None)
        if doc_count < 2:
            logger.info("[CrossCheck] 문서 2개 미만 — 교차 검증 스킵")
            return result

        # ─── 각 검증 항목 실행 ───
        self._check_sap_no(result, invoice, packing_list, bl, do)
        self._check_bl_no(result, invoice, packing_list, bl, do)
        self._check_vessel(result, invoice, packing_list, bl, do)
        self._check_product(result, invoice, packing_list, bl, do)
        self._check_net_weight(result, invoice, packing_list, bl, do)
        self._check_gross_weight(result, invoice, packing_list, bl, do)
        self._check_lot_count(result, invoice, packing_list)
        self._check_lot_numbers(result, invoice, packing_list)
        self._check_duplicate_lots(result, packing_list)
        self._check_container_count(result, packing_list, bl, do)
        self._check_container_numbers(result, packing_list, bl, do)
        self._check_package_count(result, invoice, bl, do)

        # 결과 로그
        if result.is_clean:
            logger.info("[CrossCheck] ✅ 4종 서류 교차 검증 통과")
        else:
            logger.warning(
                f"[CrossCheck] 검증 결과: 심각={result.critical_count}, "
                f"주의={result.warning_count}, 참고={result.info_count}"
            )

        return result

    # =========================================================================
    # 개별 검증 메서드
    # =========================================================================

    def _check_sap_no(self, result: CrossCheckResult, invoice, pl, bl, do):
        """SAP NO 교차 검증"""
        sources = {}
        values = set()

        for name, obj, attr in [
            ("Invoice", invoice, "sap_no"),
            ("Packing List", pl, "sap_no"),
            ("B/L", bl, "sap_no"),
            ("D/O", do, "sap_no"),
        ]:
            val = _safe_str(obj, attr)
            if val:
                sources[name] = val
                values.add(val)

        if len(values) > 1:
            result.add(
                "SAP NO", CheckLevel.CRITICAL,
                f"SAP NO 불일치: {len(values)}개 서로 다른 값 발견",
                sources
            )

    def _check_bl_no(self, result: CrossCheckResult, invoice, pl, bl, do):
        """B/L No 교차 검증 (정규화 후 비교)"""
        sources = {}
        normalized = {}

        for name, obj, attr in [
            ("Invoice", invoice, "bl_no"),
            ("B/L", bl, "bl_no"),
            ("D/O", do, "bl_no"),
        ]:
            val = _safe_str(obj, attr)
            if val:
                sources[name] = val
                normalized[name] = _normalize_bl(val)

        unique_normalized = set(normalized.values())
        if len(unique_normalized) > 1:
            # 정규화 후에도 다르면 경고
            result.add(
                "B/L No", CheckLevel.WARNING,
                f"B/L No 불일치 (정규화 후에도 상이): {unique_normalized}",
                sources
            )

    def _check_vessel(self, result: CrossCheckResult, invoice, pl, bl, do):
        """선박명(Vessel) 교차 검증 — 퍼지 매칭"""
        sources = {}
        vessels = []

        for name, obj, attr in [
            ("Invoice", invoice, "vessel"),
            ("Packing List", pl, "vessel"),
            ("B/L", bl, "vessel"),
            ("D/O", do, "vessel"),
        ]:
            val = _safe_str(obj, attr)
            if val:
                sources[name] = val
                vessels.append((name, val))

        if len(vessels) < 2:
            return

        # 모든 쌍 비교
        mismatches = []
        for i in range(len(vessels)):
            for j in range(i + 1, len(vessels)):
                name_a, v_a = vessels[i]
                name_b, v_b = vessels[j]
                if not _vessel_fuzzy_match(v_a, v_b):
                    mismatches.append(f"{name_a} vs {name_b}")

        if mismatches:
            result.add(
                "Vessel", CheckLevel.WARNING,
                f"선박명 불일치: {', '.join(mismatches)}",
                sources
            )

    def _check_product(self, result: CrossCheckResult, invoice, pl, bl, do):
        """제품명/코드 교차 검증"""
        sources = {}
        products = set()

        # 제품명 비교 (키워드 기반 — "LITHIUM CARBONATE" 포함 여부)
        for name, obj, attr in [
            ("Invoice", invoice, "product_name"),
            ("Packing List", pl, "product"),
            ("B/L", bl, "product_name"),
        ]:
            val = _safe_str(obj, attr)
            if val:
                sources[name] = val
                # 핵심 키워드 추출
                upper = val.upper()
                if "LITHIUM" in upper:
                    products.add("LITHIUM")
                elif "NICKEL" in upper:
                    products.add("NICKEL")
                else:
                    products.add(upper[:20])

        if len(products) > 1:
            result.add(
                "Product", CheckLevel.CRITICAL,
                f"제품명이 서류 간 상이합니다: {products}",
                sources
            )

    def _check_net_weight(self, result: CrossCheckResult, invoice, pl, bl, do):
        """총 순중량(Net Weight) 교차 검증"""
        sources = {}
        weights = {}

        for name, obj, attr in [
            ("Invoice", invoice, "net_weight_kg"),
            ("Packing List", pl, "total_net_weight_kg"),
            ("B/L", bl, "net_weight_kg"),
        ]:
            val = _safe_float(obj, attr)
            # PL은 property도 확인
            if val is None and name == "Packing List" and pl:
                val = _safe_float(pl, "total_net_weight")
            if val and val > 0:
                sources[name] = f"{val:,.1f} kg"
                weights[name] = val

        if len(weights) < 2:
            return

        vals = list(weights.values())
        max_diff = 0.0
        worst_pair = ("", "")
        names = list(weights.keys())
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                diff = _weight_diff_pct(vals[i], vals[j])
                if diff > max_diff:
                    max_diff = diff
                    worst_pair = (names[i], names[j])

        if max_diff >= self.WEIGHT_CRITICAL_THRESHOLD:
            result.add(
                "Net Weight", CheckLevel.CRITICAL,
                f"순중량 차이 {max_diff:.1f}% ({worst_pair[0]} vs {worst_pair[1]})",
                sources
            )
        elif max_diff >= self.WEIGHT_WARN_THRESHOLD:
            result.add(
                "Net Weight", CheckLevel.WARNING,
                f"순중량 차이 {max_diff:.2f}% ({worst_pair[0]} vs {worst_pair[1]})",
                sources
            )

    def _check_gross_weight(self, result: CrossCheckResult, invoice, pl, bl, do):
        """총 총중량(Gross Weight) 교차 검증"""
        sources = {}
        weights = {}

        for name, obj, attrs in [
            ("Invoice", invoice, ["gross_weight_kg"]),
            ("Packing List", pl, ["total_gross_weight_kg", "total_gross_weight"]),
            ("B/L", bl, ["gross_weight_kg"]),
            ("D/O", do, ["gross_weight_kg"]),
        ]:
            val = None
            for attr in attrs:
                val = _safe_float(obj, attr)
                if val and val > 0:
                    break
            if val and val > 0:
                sources[name] = f"{val:,.1f} kg"
                weights[name] = val

        if len(weights) < 2:
            return

        vals = list(weights.values())
        names = list(weights.keys())
        max_diff = 0.0
        worst_pair = ("", "")
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                diff = _weight_diff_pct(vals[i], vals[j])
                if diff > max_diff:
                    max_diff = diff
                    worst_pair = (names[i], names[j])

        if max_diff >= self.WEIGHT_CRITICAL_THRESHOLD:
            result.add(
                "Gross Weight", CheckLevel.CRITICAL,
                f"총중량 차이 {max_diff:.1f}% ({worst_pair[0]} vs {worst_pair[1]})",
                sources
            )
        elif max_diff >= self.WEIGHT_WARN_THRESHOLD:
            result.add(
                "Gross Weight", CheckLevel.WARNING,
                f"총중량 차이 {max_diff:.2f}% ({worst_pair[0]} vs {worst_pair[1]})",
                sources
            )

    def _check_lot_count(self, result: CrossCheckResult, invoice, pl):
        """LOT 개수 교차 검증 (Invoice vs Packing List)"""
        inv_lots = getattr(invoice, 'lot_numbers', []) if invoice else []
        pl_lots = getattr(pl, 'lots', []) if pl else []

        inv_count = len(inv_lots) if inv_lots else 0
        pl_count = len(pl_lots) if pl_lots else 0

        if inv_count == 0 or pl_count == 0:
            return

        sources = {
            "Invoice": f"{inv_count}개",
            "Packing List": f"{pl_count}개",
        }

        if inv_count != pl_count:
            diff = abs(inv_count - pl_count)
            level = CheckLevel.CRITICAL if diff >= 3 else CheckLevel.WARNING
            result.add(
                "LOT 개수", level,
                f"Invoice {inv_count}개 vs Packing List {pl_count}개 (차이: {diff}개)",
                sources
            )

    def _check_lot_numbers(self, result: CrossCheckResult, invoice, pl):
        """LOT 번호 목록 교차 검증 (Invoice vs Packing List)"""
        inv_lots = set(str(x).strip() for x in (getattr(invoice, 'lot_numbers', []) or []) if str(x).strip()) if invoice else set()
        pl_lots = set()
        if pl and getattr(pl, 'lots', None):
            for lot in pl.lots:
                lot_no = getattr(lot, 'lot_no', '') or ''
                if lot_no.strip():
                    pl_lots.add(lot_no.strip())

        if not inv_lots or not pl_lots:
            return

        only_in_inv = inv_lots - pl_lots
        only_in_pl = pl_lots - inv_lots

        if only_in_inv:
            result.add(
                "LOT 번호 (Invoice Only)", CheckLevel.WARNING,
                f"Invoice에만 있는 LOT: {', '.join(sorted(only_in_inv))}",
                {"Invoice에만 존재": ", ".join(sorted(only_in_inv))}
            )

        if only_in_pl:
            result.add(
                "LOT 번호 (PL Only)", CheckLevel.WARNING,
                f"Packing List에만 있는 LOT: {', '.join(sorted(only_in_pl))}",
                {"Packing List에만 존재": ", ".join(sorted(only_in_pl))}
            )

    def _check_duplicate_lots(self, result: CrossCheckResult, pl):
        """Packing List 내 중복 LOT 번호 검출"""
        if not pl or not getattr(pl, 'lots', None):
            return

        lot_nos = []
        for lot in pl.lots:
            lot_no = getattr(lot, 'lot_no', '') or ''
            if lot_no.strip():
                lot_nos.append(lot_no.strip())

        seen = {}
        duplicates = {}
        for idx, ln in enumerate(lot_nos, 1):
            if ln in seen:
                if ln not in duplicates:
                    duplicates[ln] = [seen[ln]]
                duplicates[ln].append(idx)
            else:
                seen[ln] = idx

        if duplicates:
            for lot_no, positions in duplicates.items():
                result.add(
                    "중복 LOT", CheckLevel.CRITICAL,
                    f"LOT '{lot_no}'가 Packing List에서 {len(positions)}회 중복 (행: {positions})",
                    {"LOT No": lot_no, "중복 위치": str(positions)}
                )

    def _check_container_count(self, result: CrossCheckResult, pl, bl, do):
        """컨테이너 수 교차 검증"""
        sources = {}
        counts = {}

        # Packing List: containers 리스트 또는 lots에서 unique container 추출
        if pl:
            pl_containers = set()
            if getattr(pl, 'containers', None):
                pl_containers = set(pl.containers)
            elif getattr(pl, 'lots', None):
                for lot in pl.lots:
                    cn = _normalize_container(getattr(lot, 'container_no', '') or '')
                    if cn:
                        pl_containers.add(cn)
            if pl_containers:
                sources["Packing List"] = f"{len(pl_containers)}개"
                counts["Packing List"] = len(pl_containers)

        # B/L
        if bl:
            bl_count = getattr(bl, 'total_containers', 0) or 0
            if bl_count == 0 and getattr(bl, 'containers', None):
                bl_count = len(bl.containers)
            if bl_count > 0:
                sources["B/L"] = f"{bl_count}개"
                counts["B/L"] = bl_count

        # D/O
        if do and getattr(do, 'containers', None):
            do_count = len(do.containers)
            if do_count > 0:
                sources["D/O"] = f"{do_count}개"
                counts["D/O"] = do_count

        if len(counts) < 2:
            return

        unique_counts = set(counts.values())
        if len(unique_counts) > 1:
            result.add(
                "Container 수", CheckLevel.WARNING,
                f"컨테이너 수 불일치: {dict(counts)}",
                sources
            )

    def _check_container_numbers(self, result: CrossCheckResult, pl, bl, do):
        """컨테이너 번호 교차 검증 (정규화 후 비교)"""
        container_sets = {}

        # Packing List
        if pl:
            pl_set = set()
            if getattr(pl, 'lots', None):
                for lot in pl.lots:
                    cn = _normalize_container(getattr(lot, 'container_no', '') or '')
                    if cn:
                        pl_set.add(cn)
            elif getattr(pl, 'containers', None):
                for c in pl.containers:
                    cn = _normalize_container(c)
                    if cn:
                        pl_set.add(cn)
            if pl_set:
                container_sets["Packing List"] = pl_set

        # B/L
        if bl and getattr(bl, 'containers', None):
            bl_set = set()
            for c in bl.containers:
                cn = _normalize_container(getattr(c, 'container_no', '') or '')
                if cn:
                    bl_set.add(cn)
            if bl_set:
                container_sets["B/L"] = bl_set

        # D/O
        if do and getattr(do, 'containers', None):
            do_set = set()
            for c in do.containers:
                cn = _normalize_container(getattr(c, 'container_no', '') or '')
                if cn:
                    do_set.add(cn)
            if do_set:
                container_sets["D/O"] = do_set

        if len(container_sets) < 2:
            return

        # 모든 쌍 비교
        names = list(container_sets.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                set_a = container_sets[names[i]]
                set_b = container_sets[names[j]]
                only_a = set_a - set_b
                only_b = set_b - set_a
                if only_a or only_b:
                    sources = {}
                    if only_a:
                        sources[f"{names[i]}에만 존재"] = ", ".join(sorted(only_a))
                    if only_b:
                        sources[f"{names[j]}에만 존재"] = ", ".join(sorted(only_b))
                    result.add(
                        "Container 번호", CheckLevel.WARNING,
                        f"컨테이너 번호 불일치: {names[i]} vs {names[j]}",
                        sources
                    )

    def _check_package_count(self, result: CrossCheckResult, invoice, bl, do):
        """패키지 수 교차 검증"""
        sources = {}
        counts = {}

        if invoice:
            inv_pkg = getattr(invoice, 'package_count', 0) or 0
            if inv_pkg > 0:
                sources["Invoice"] = f"{inv_pkg}개"
                counts["Invoice"] = inv_pkg

        if bl:
            bl_pkg = getattr(bl, 'total_packages', 0) or 0
            if bl_pkg > 0:
                sources["B/L"] = f"{bl_pkg}개"
                counts["B/L"] = bl_pkg

        if do:
            do_pkg = getattr(do, 'total_packages', 0) or 0
            if do_pkg > 0:
                sources["D/O"] = f"{do_pkg}개"
                counts["D/O"] = do_pkg

        if len(counts) < 2:
            return

        unique_counts = set(counts.values())
        if len(unique_counts) > 1:
            result.add(
                "Package 수", CheckLevel.INFO,
                f"패키지 수 차이: {dict(counts)}",
                sources
            )


# =============================================================================
# 편의 함수
# =============================================================================

def cross_check_documents(invoice=None, packing_list=None, bl=None, do=None) -> CrossCheckResult:
    """
    4종 문서 교차 검증 편의 함수

    >>> result = cross_check_documents(invoice, packing_list, bl, do)
    >>> if result.has_critical:
    ...     print("업로드 차단:", result.detail_text)
    """
    engine = CrossCheckEngine()
    return engine.check(invoice, packing_list, bl, do)
