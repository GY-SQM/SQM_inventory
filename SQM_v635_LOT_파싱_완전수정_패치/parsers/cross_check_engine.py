"""
SQM 재고관리 시스템 - 문서 간 크로스 체크 엔진
==============================================

v6.2.1: 신규 생성

4종 선적 문서(Invoice, Packing List, B/L, D/O) 간 교차 검증을 수행합니다.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CheckLevel(IntEnum):
    INFO = 1
    WARNING = 2
    CRITICAL = 3


@dataclass
class CheckItem:
    field_name: str
    level: CheckLevel
    message: str
    sources: Dict[str, str] = field(default_factory=dict)

    @property
    def level_icon(self) -> str:
        if self.level == CheckLevel.INFO:
            return "ℹ️"
        if self.level == CheckLevel.WARNING:
            return "⚠️"
        return "🚫"

    def __str__(self) -> str:
        return f"{self.level_icon} [{self.field_name}] {self.message}"


@dataclass
class CrossCheckResult:
    items: List[CheckItem] = field(default_factory=list)
    checked_at: str = ""
    _lot_levels_cache: Optional[Dict[str, CheckLevel]] = field(default=None, init=False, repr=False)

    _LOT_FIELDS = {"중복 LOT", "LOT 번호 (Invoice Only)", "LOT 번호 (PL Only)"}
    _GLOBAL_FIELDS = {
        "SAP NO", "B/L No", "Vessel", "Product",
        "Net Weight", "Gross Weight", "LOT 개수",
        "Container 수", "Container 번호", "Package 수",
    }

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
        if self.is_clean:
            return "✅ 4종 서류 교차 검증 통과 — 불일치 없음"
        parts = []
        if self.critical_count:
            parts.append(f"🚫 심각 {self.critical_count}건")
        if self.warning_count:
            parts.append(f"⚠️ 주의 {self.warning_count}건")
        if self.info_count:
            parts.append(f"ℹ️ 참고 {self.info_count}건")
        return "크로스 체크: " + ", ".join(parts)

    @property
    def global_level(self) -> Optional[CheckLevel]:
        levels = [i.level for i in self.items if i.field_name in self._GLOBAL_FIELDS]
        return max(levels) if levels else None

    def add(self, field_name: str, level: CheckLevel, message: str, sources: Dict[str, str] = None):
        self._lot_levels_cache = None
        self.items.append(CheckItem(field_name=field_name, level=level, message=message, sources=sources or {}))

    def get_lot_levels(self) -> Dict[str, CheckLevel]:
        if self._lot_levels_cache is not None:
            return self._lot_levels_cache
        lot_map: Dict[str, CheckLevel] = {}
        for item in self.items:
            if item.field_name not in self._LOT_FIELDS:
                continue
            lot_no = item.sources.get("LOT No", "")
            if lot_no:
                existing = lot_map.get(lot_no)
                if existing is None or item.level > existing:
                    lot_map[lot_no] = item.level
            else:
                for _, val in item.sources.items():
                    for ln in str(val).split(","):
                        ln = ln.strip()
                        if ln and len(ln) >= 10:
                            existing = lot_map.get(ln)
                            if existing is None or item.level > existing:
                                lot_map[ln] = item.level
        self._lot_levels_cache = lot_map
        return lot_map

    def get_row_tag(self, lot_no: str) -> Optional[str]:
        lot_levels = self.get_lot_levels()
        lot_level = lot_levels.get(lot_no)
        global_lv = self.global_level
        effective = None
        if lot_level and global_lv:
            effective = max(lot_level, global_lv)
        elif lot_level:
            effective = lot_level
        elif global_lv:
            effective = global_lv

        if effective == CheckLevel.CRITICAL:
            return "xc_critical"
        if effective == CheckLevel.WARNING:
            return "xc_warning"
        if effective == CheckLevel.INFO:
            return "xc_info"
        return None


def _safe_str(obj, attr: str) -> str:
    val = getattr(obj, attr, None) if obj else None
    if val is None:
        return ""
    return str(val).strip()


def _safe_float(obj, attr: str) -> Optional[float]:
    val = getattr(obj, attr, None) if obj else None
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _normalize_vessel(vessel: str) -> str:
    if not vessel:
        return ""
    v = re.sub(r"[^\w\s]", " ", vessel.upper())
    v = re.sub(r"\s+", " ", v).strip()
    return v


def _normalize_container(container_no: str) -> str:
    if not container_no:
        return ""
    return re.sub(r"[^A-Z0-9]", "", container_no.upper())


def _normalize_bl(bl_no: str) -> str:
    if not bl_no:
        return ""
    bl = str(bl_no).strip().upper()
    m = re.match(r"^[A-Z]{3,4}(\d{6,})$", bl)
    if m:
        return m.group(1)
    return bl


def _vessel_fuzzy_match(v1: str, v2: str) -> bool:
    n1 = _normalize_vessel(v1)
    n2 = _normalize_vessel(v2)
    if not n1 or not n2:
        return True
    if n1 == n2 or n1 in n2 or n2 in n1:
        return True
    words1 = n1.split()[:2]
    words2 = n2.split()[:2]
    return words1 == words2 and len(words1) >= 2


def _weight_diff_pct(w1: float, w2: float) -> float:
    if w1 == 0 and w2 == 0:
        return 0.0
    base = max(w1, w2)
    if base == 0:
        return 100.0
    return abs(w1 - w2) / base * 100.0


class CrossCheckEngine:
    WEIGHT_WARN_THRESHOLD = 1.0
    WEIGHT_CRITICAL_THRESHOLD = 5.0

    def check(self, invoice=None, packing_list=None, bl=None, do=None) -> CrossCheckResult:
        from datetime import datetime
        result = CrossCheckResult(checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        doc_count = sum(1 for d in [invoice, packing_list, bl, do] if d is not None)
        if doc_count < 2:
            logger.info("[CrossCheck] 문서 2개 미만 — 교차 검증 스킵")
            return result

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
        return result

    def _check_sap_no(self, result, invoice, pl, bl, do):
        sources, values = {}, set()
        for name, obj, attr in [("Invoice", invoice, "sap_no"), ("Packing List", pl, "sap_no"), ("B/L", bl, "sap_no"), ("D/O", do, "sap_no")]:
            val = _safe_str(obj, attr)
            if val:
                sources[name] = val
                values.add(val)
        if len(values) > 1:
            result.add("SAP NO", CheckLevel.CRITICAL, f"SAP NO 불일치: {len(values)}개 서로 다른 값 발견", sources)

    def _check_bl_no(self, result, invoice, pl, bl, do):
        sources, normalized = {}, {}
        for name, obj, attr in [("Invoice", invoice, "bl_no"), ("B/L", bl, "bl_no"), ("D/O", do, "bl_no")]:
            val = _safe_str(obj, attr)
            if val:
                sources[name] = val
                normalized[name] = _normalize_bl(val)
        if len(set(normalized.values())) > 1:
            result.add("B/L No", CheckLevel.WARNING, "B/L No 불일치 (정규화 후에도 상이)", sources)

    def _check_vessel(self, result, invoice, pl, bl, do):
        sources, vessels = {}, []
        for name, obj, attr in [("Invoice", invoice, "vessel"), ("Packing List", pl, "vessel"), ("B/L", bl, "vessel"), ("D/O", do, "vessel")]:
            val = _safe_str(obj, attr)
            if val:
                sources[name] = val
                vessels.append((name, val))
        if len(vessels) < 2:
            return
        mismatches = []
        for i in range(len(vessels)):
            for j in range(i + 1, len(vessels)):
                if not _vessel_fuzzy_match(vessels[i][1], vessels[j][1]):
                    mismatches.append(f"{vessels[i][0]} vs {vessels[j][0]}")
        if mismatches:
            result.add("Vessel", CheckLevel.WARNING, f"선박명 불일치: {', '.join(mismatches)}", sources)

    def _check_product(self, result, invoice, pl, bl, do):
        sources, products = {}, set()
        for name, obj, attr in [("Invoice", invoice, "product_name"), ("Packing List", pl, "product"), ("B/L", bl, "product_name")]:
            val = _safe_str(obj, attr)
            if val:
                sources[name] = val
                upper = val.upper()
                if "LITHIUM" in upper:
                    products.add("LITHIUM")
                elif "NICKEL" in upper:
                    products.add("NICKEL")
                else:
                    products.add(upper[:20])
        if len(products) > 1:
            result.add("Product", CheckLevel.CRITICAL, "제품명이 서류 간 상이합니다", sources)

    def _check_net_weight(self, result, invoice, pl, bl, do):
        sources, weights = {}, {}
        for name, obj, attr in [("Invoice", invoice, "net_weight_kg"), ("Packing List", pl, "total_net_weight_kg"), ("B/L", bl, "net_weight_kg")]:
            val = _safe_float(obj, attr)
            if val is None and name == "Packing List" and pl:
                val = _safe_float(pl, "total_net_weight")
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
            result.add("Net Weight", CheckLevel.CRITICAL, f"순중량 차이 {max_diff:.1f}% ({worst_pair[0]} vs {worst_pair[1]})", sources)
        elif max_diff >= self.WEIGHT_WARN_THRESHOLD:
            result.add("Net Weight", CheckLevel.WARNING, f"순중량 차이 {max_diff:.2f}% ({worst_pair[0]} vs {worst_pair[1]})", sources)

    def _check_gross_weight(self, result, invoice, pl, bl, do):
        sources, weights = {}, {}
        for name, obj, attrs in [("Invoice", invoice, ["gross_weight_kg"]), ("Packing List", pl, ["total_gross_weight_kg", "total_gross_weight"]), ("B/L", bl, ["gross_weight_kg"]), ("D/O", do, ["gross_weight_kg"])]:
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
            result.add("Gross Weight", CheckLevel.CRITICAL, f"총중량 차이 {max_diff:.1f}% ({worst_pair[0]} vs {worst_pair[1]})", sources)
        elif max_diff >= self.WEIGHT_WARN_THRESHOLD:
            result.add("Gross Weight", CheckLevel.WARNING, f"총중량 차이 {max_diff:.2f}% ({worst_pair[0]} vs {worst_pair[1]})", sources)

    def _check_lot_count(self, result, invoice, pl):
        inv_lots = getattr(invoice, "lot_numbers", []) if invoice else []
        pl_lots = getattr(pl, "lots", []) if pl else []
        inv_count = len(inv_lots) if inv_lots else 0
        pl_count = len(pl_lots) if pl_lots else 0
        if inv_count == 0 or pl_count == 0:
            return
        if inv_count != pl_count:
            diff = abs(inv_count - pl_count)
            level = CheckLevel.CRITICAL if diff >= 3 else CheckLevel.WARNING
            result.add("LOT 개수", level, f"Invoice {inv_count}개 vs Packing List {pl_count}개 (차이: {diff}개)", {"Invoice": f"{inv_count}개", "Packing List": f"{pl_count}개"})

    def _check_lot_numbers(self, result, invoice, pl):
        inv_lots = set(str(x).strip() for x in (getattr(invoice, "lot_numbers", []) or []) if str(x).strip()) if invoice else set()
        pl_lots = set()
        # v6.3.5: PL list_no 순서 맵 구축 (순번 기반 정렬용)
        pl_lot_order: dict = {}
        if pl and getattr(pl, "lots", None):
            for lot in pl.lots:
                lot_no = (getattr(lot, "lot_no", "") or "").strip()
                if lot_no:
                    pl_lots.add(lot_no)
                    try:
                        pl_lot_order[lot_no] = int(getattr(lot, "list_no", 0) or 0)
                    except (ValueError, TypeError):
                        pl_lot_order[lot_no] = 0
        # Invoice 원문 순서 맵 (lot_numbers 리스트 인덱스)
        inv_lot_order: dict = {}
        if invoice and getattr(invoice, "lot_numbers", None):
            for idx, lot_no in enumerate(invoice.lot_numbers):
                lot_no = str(lot_no).strip()
                if lot_no and lot_no not in inv_lot_order:
                    inv_lot_order[lot_no] = idx
        if not inv_lots or not pl_lots:
            return
        only_in_inv = inv_lots - pl_lots
        only_in_pl = pl_lots - inv_lots
        if only_in_inv:
            # Invoice 원문 순서대로 정렬
            inv_sorted = sorted(only_in_inv, key=lambda x: inv_lot_order.get(x, 99999))
            result.add(
                "LOT 번호 (Invoice Only)", CheckLevel.WARNING,
                f"Invoice에만 있는 LOT: {', '.join(inv_sorted)}",
                {"Invoice에만 존재": ", ".join(inv_sorted)}
            )
        if only_in_pl:
            # ★ PL list_no 순서대로 정렬
            pl_sorted = sorted(only_in_pl, key=lambda x: pl_lot_order.get(x, 99999))
            result.add(
                "LOT 번호 (PL Only)", CheckLevel.WARNING,
                f"Packing List에만 있는 LOT: {', '.join(pl_sorted)}",
                {"Packing List에만 존재": ", ".join(pl_sorted)}
            )

    def _check_duplicate_lots(self, result, pl):
        if not pl or not getattr(pl, "lots", None):
            return
        lot_nos = []
        for lot in pl.lots:
            lot_no = getattr(lot, "lot_no", "") or ""
            if lot_no.strip():
                lot_nos.append(lot_no.strip())
        seen, duplicates = {}, {}
        for idx, ln in enumerate(lot_nos, 1):
            if ln in seen:
                if ln not in duplicates:
                    duplicates[ln] = [seen[ln]]
                duplicates[ln].append(idx)
            else:
                seen[ln] = idx
        for lot_no, positions in duplicates.items():
            result.add("중복 LOT", CheckLevel.CRITICAL, f"LOT '{lot_no}'가 Packing List에서 {len(positions)}회 중복 (행: {positions})", {"LOT No": lot_no, "중복 위치": str(positions)})

    def _check_container_count(self, result, pl, bl, do):
        sources, counts = {}, {}
        if pl:
            pl_containers = set()
            if getattr(pl, "containers", None):
                pl_containers = set(pl.containers)
            elif getattr(pl, "lots", None):
                for lot in pl.lots:
                    cn = _normalize_container(getattr(lot, "container_no", "") or "")
                    if cn:
                        pl_containers.add(cn)
            if pl_containers:
                sources["Packing List"] = f"{len(pl_containers)}개"
                counts["Packing List"] = len(pl_containers)
        if bl:
            bl_count = getattr(bl, "total_containers", 0) or 0
            if bl_count == 0 and getattr(bl, "containers", None):
                bl_count = len(bl.containers)
            if bl_count > 0:
                sources["B/L"] = f"{bl_count}개"
                counts["B/L"] = bl_count
        if do and getattr(do, "containers", None):
            do_count = len(do.containers)
            if do_count > 0:
                sources["D/O"] = f"{do_count}개"
                counts["D/O"] = do_count
        if len(counts) >= 2 and len(set(counts.values())) > 1:
            result.add("Container 수", CheckLevel.WARNING, f"컨테이너 수 불일치: {dict(counts)}", sources)

    def _check_container_numbers(self, result, pl, bl, do):
        container_sets = {}
        if pl:
            pl_set = set()
            if getattr(pl, "lots", None):
                for lot in pl.lots:
                    cn = _normalize_container(getattr(lot, "container_no", "") or "")
                    if cn:
                        pl_set.add(cn)
            elif getattr(pl, "containers", None):
                for c in pl.containers:
                    cn = _normalize_container(c)
                    if cn:
                        pl_set.add(cn)
            if pl_set:
                container_sets["Packing List"] = pl_set
        if bl and getattr(bl, "containers", None):
            bl_set = set()
            for c in bl.containers:
                cn = _normalize_container(getattr(c, "container_no", "") or "")
                if cn:
                    bl_set.add(cn)
            if bl_set:
                container_sets["B/L"] = bl_set
        if do and getattr(do, "containers", None):
            do_set = set()
            for c in do.containers:
                cn = _normalize_container(getattr(c, "container_no", "") or "")
                if cn:
                    do_set.add(cn)
            if do_set:
                container_sets["D/O"] = do_set
        if len(container_sets) < 2:
            return
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
                    result.add("Container 번호", CheckLevel.WARNING, f"컨테이너 번호 불일치: {names[i]} vs {names[j]}", sources)

    def _check_package_count(self, result, invoice, bl, do):
        sources, counts = {}, {}
        if invoice:
            inv_pkg = getattr(invoice, "package_count", 0) or 0
            if inv_pkg > 0:
                sources["Invoice"] = f"{inv_pkg}개"
                counts["Invoice"] = inv_pkg
        if bl:
            bl_pkg = getattr(bl, "total_packages", 0) or 0
            if bl_pkg > 0:
                sources["B/L"] = f"{bl_pkg}개"
                counts["B/L"] = bl_pkg
        if do:
            do_pkg = getattr(do, "total_packages", 0) or 0
            if do_pkg > 0:
                sources["D/O"] = f"{do_pkg}개"
                counts["D/O"] = do_pkg
        if len(counts) >= 2 and len(set(counts.values())) > 1:
            result.add("Package 수", CheckLevel.INFO, f"패키지 수 차이: {dict(counts)}", sources)


def cross_check_documents(invoice=None, packing_list=None, bl=None, do=None) -> CrossCheckResult:
    engine = CrossCheckEngine()
    return engine.check(invoice, packing_list, bl, do)
