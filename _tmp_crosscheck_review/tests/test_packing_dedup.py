# -*- coding: utf-8 -*-
"""
Packing List 중복 행 파싱 제거 테스트
v6.2.1 — gemini_parser.py append_lot fingerprint 검증
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.ai.gemini_parser import parse_euro_weight

# append_lot 로직을 독립 시뮬레이션
from dataclasses import dataclass, field
from typing import List, Set

@dataclass
class FakeLOT:
    lot_no: str = ""
    container_no: str = ""
    net_weight_kg: float = 0.0

def simulate_append_lot(lots_json: list) -> tuple:
    """
    gemini_parser.py의 append_lot 로직을 시뮬레이션
    Returns: (accepted_lots, skipped_count)
    """
    seen_lot_nos: Set[str] = set()
    seen_fingerprints: Set[str] = set()
    result: List[FakeLOT] = []
    skipped = 0

    for lot_data in lots_json:
        lot_no = str(lot_data.get('lot_no', '')).strip()
        _fp_container = str(lot_data.get('container_no', '')).strip()
        _fp_nw = str(lot_data.get('net_weight_kg', '')).strip()
        fingerprint = f"{lot_no}|{_fp_container}|{_fp_nw}"

        # fingerprint 완전 중복 체크 (lot_no 유무와 무관)
        if fingerprint in seen_fingerprints:
            skipped += 1
            continue

        # lot_no 동일 + fingerprint 다름 → 경고만, 추가
        # (위에서 fingerprint 중복은 이미 걸러짐)

        if lot_no:
            seen_lot_nos.add(lot_no)
        seen_fingerprints.add(fingerprint)
        result.append(FakeLOT(lot_no=lot_no, container_no=_fp_container, net_weight_kg=float(_fp_nw or 0)))

    return result, skipped


# ═══════════════════════════════════════════════
# 테스트 케이스
# ═══════════════════════════════════════════════

def test_no_duplicates():
    """중복 없는 정상 케이스 — 전부 추가"""
    data = [
        {"lot_no": "1125081447", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},
        {"lot_no": "1125081448", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},
        {"lot_no": "1125081449", "container_no": "FFAU5355007", "net_weight_kg": 5001.5},
    ]
    accepted, skipped = simulate_append_lot(data)
    assert len(accepted) == 3
    assert skipped == 0
    print("  ✅ 정상 (중복 없음): 3건 → 3건 추가, 0건 스킵")


def test_exact_duplicate_row():
    """완전 동일 행 중복 → 스킵"""
    data = [
        {"lot_no": "1125081447", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},
        {"lot_no": "1125081448", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},
        {"lot_no": "1125081447", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},  # 완전 중복!
    ]
    accepted, skipped = simulate_append_lot(data)
    assert len(accepted) == 2
    assert skipped == 1
    print("  ✅ 완전 중복 행: 3건 → 2건 추가, 1건 스킵")


def test_multiple_duplicates():
    """같은 행이 3번 반복 → 2건 스킵"""
    data = [
        {"lot_no": "1125081447", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},
        {"lot_no": "1125081447", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},
        {"lot_no": "1125081447", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},
    ]
    accepted, skipped = simulate_append_lot(data)
    assert len(accepted) == 1
    assert skipped == 2
    print("  ✅ 3중 중복: 3건 → 1건 추가, 2건 스킵")


def test_same_lotno_different_data():
    """lot_no 같지만 container·weight 다름 → 둘 다 추가 (경고만)"""
    data = [
        {"lot_no": "1125081447", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},
        {"lot_no": "1125081447", "container_no": "FFAU5355007", "net_weight_kg": 4500.0},  # 다른 컨테이너/중량
    ]
    accepted, skipped = simulate_append_lot(data)
    assert len(accepted) == 2, f"둘 다 추가되어야 함, got {len(accepted)}"
    assert skipped == 0
    print("  ✅ lot_no 동일 + 데이터 상이: 2건 → 2건 모두 추가 (수동 확인 경고)")


def test_gemini_hallucination_pattern():
    """실제 Gemini 환각 패턴: 20행 중 마지막 2행이 앞의 행과 동일하게 반복"""
    data = [
        {"lot_no": f"11250814{i:02d}", "container_no": f"FFAU535500{i%4}", "net_weight_kg": 5001.5}
        for i in range(1, 21)
    ]
    # 마지막 2개를 앞의 행과 동일하게 복제 (Gemini 환각)
    data.append({"lot_no": "1125081401", "container_no": "FFAU5355001", "net_weight_kg": 5001.5})
    data.append({"lot_no": "1125081402", "container_no": "FFAU5355002", "net_weight_kg": 5001.5})
    
    accepted, skipped = simulate_append_lot(data)
    assert len(accepted) == 20, f"20건만 추가되어야 함, got {len(accepted)}"
    assert skipped == 2
    print("  ✅ Gemini 환각 패턴 (20+2중복): 22건 → 20건 추가, 2건 스킵")


def test_cross_page_dedup():
    """2페이지 시뮬레이션: 1페이지 10행 + 2페이지에서 겹치는 3행 + 새 행 7개"""
    page1 = [
        {"lot_no": f"11250814{i:02d}", "container_no": f"FFAU535500{i}", "net_weight_kg": 5001.5}
        for i in range(1, 11)
    ]
    page2_flat = [
        {"lot_no": "1125081408", "container_no": "FFAU5355008", "net_weight_kg": 5001.5},
        {"lot_no": "1125081409", "container_no": "FFAU5355009", "net_weight_kg": 5001.5},
        {"lot_no": "1125081410", "container_no": "FFAU53550010", "net_weight_kg": 5001.5},
    ]
    for i in range(11, 18):
        page2_flat.append({"lot_no": f"11250814{i:02d}", "container_no": f"FFAU53550{i:02d}", "net_weight_kg": 5001.5})
    
    all_lots = page1 + page2_flat
    accepted, skipped = simulate_append_lot(all_lots)
    assert len(accepted) == 17, f"17건이어야 함, got {len(accepted)}"
    assert skipped == 3
    print("  ✅ 페이지 간 중복 (10+10 중 3겹침): 20건 → 17건 추가, 3건 스킵")


def test_empty_lotno_different_data():
    """lot_no 빈 행 — fingerprint만으로 비교"""
    data = [
        {"lot_no": "", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},
        {"lot_no": "", "container_no": "FFAU5355007", "net_weight_kg": 4500.0},  # 다른 데이터
        {"lot_no": "", "container_no": "FFAU5355006", "net_weight_kg": 5001.5},  # 완전 중복
    ]
    accepted, skipped = simulate_append_lot(data)
    assert len(accepted) == 2
    assert skipped == 1
    print("  ✅ lot_no 빈 행 중복: fingerprint로 판별, 3건 → 2건 추가, 1건 스킵")


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Packing List 중복 행 제거 테스트 (v6.2.1)")
    print("=" * 60)
    
    test_no_duplicates()
    test_exact_duplicate_row()
    test_multiple_duplicates()
    test_same_lotno_different_data()
    test_gemini_hallucination_pattern()
    test_cross_page_dedup()
    test_empty_lotno_different_data()
    
    print("\n" + "=" * 60)
    print("✅ 전체 7개 테스트 통과!")
    print("=" * 60)
