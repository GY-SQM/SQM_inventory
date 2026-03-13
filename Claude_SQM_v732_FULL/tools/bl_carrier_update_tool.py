"""
bl_carrier_update_tool.py — SQM v6.4.0
=========================================
신규 선사 BL 샘플 PDF → 정규식 패턴 자동 추출 → CARRIER_TEMPLATES 업데이트

사용법:
  python bl_carrier_update_tool.py <BL_PDF_경로> [선사ID]

예시:
  python bl_carrier_update_tool.py HMM_BL_sample.pdf HMM
  python bl_carrier_update_tool.py CMA_BL.pdf CMA_CGM

출력:
  1) PDF 텍스트 추출 (pdfplumber)
  2) 선사 자동 탐지 (기존 레지스트리)
  3) BL No 후보 목록 (정규식 + 위치)
  4) 최적 패턴 추천
  5) bl_carrier_registry.py 업데이트 코드 자동 생성
"""

from __future__ import annotations
import re
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ─── 알려진 BL No 패턴 후보 ─────────────────────────────────────────────────
CANDIDATE_PATTERNS = [
    # (이름, 정규식)
    ("B/L No 라벨",           r"B/L\s*(?:No\.?|NUMBER|:)\s*([A-Z]{0,4}\d{6,12})"),
    ("SEA WAYBILL No 라벨",   r"SEA WAYBILL No\.\s+([A-Z]{2,6}\d{6,10})"),
    ("BILL OF LADING No 라벨",r"BILL OF LADING\s*(?:No\.?|:)\s*([A-Z0-9]{6,20})"),
    ("WAYBILL No 라벨",        r"WAYBILL\s*No\.?\s*:?\s*([A-Z]{2,6}\d{6,10})"),
    ("숫자만 (9~12자리)",       r"\b(\d{9,12})\b"),
    ("영문+숫자 혼합",          r"\b([A-Z]{2,6}\d{6,10})\b"),
]


def extract_text_from_pdf(pdf_path: str) -> list[str]:
    """PDF → 페이지별 텍스트 목록"""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as p:
            return [(pg.extract_text() or "") for pg in p.pages[:4]]
    except ImportError:
        logger.error("pdfplumber 없음: pip install pdfplumber --break-system-packages")
        return []
    except Exception as e:
        logger.error(f"PDF 추출 실패: {e}")
        return []


def analyze_bl_candidates(pages_text: list[str]) -> list[dict]:
    """BL No 후보 목록 추출"""
    results = []
    for pat_name, pattern in CANDIDATE_PATTERNS:
        for pg_i, text in enumerate(pages_text):
            for m in re.finditer(pattern, text, re.IGNORECASE):
                # 주변 컨텍스트 (±30자)
                start = max(0, m.start() - 30)
                end   = min(len(text), m.end() + 30)
                ctx   = text[start:end].replace("\n", " ").strip()
                results.append({
                    "pattern_name": pat_name,
                    "regex":        pattern,
                    "match":        m.group(1),
                    "full_match":   m.group(0),
                    "page":         pg_i,
                    "context":      ctx,
                })
    return results


def recommend_pattern(candidates: list[dict], carrier_id: str = "") -> str:
    """최적 패턴 추천 (라벨 기반 > 숫자 패턴)"""
    # 라벨 기반 우선
    for c in candidates:
        if "라벨" in c["pattern_name"] and c["page"] == 0:
            return c["regex"]
    # 첫 번째 후보
    if candidates:
        return candidates[0]["regex"]
    return r"B/L\s*No\.?\s*([A-Z0-9]{6,20})"


def generate_template_code(
    carrier_id:     str,
    carrier_name:   str,
    detect_kw:      list[str],
    bl_pattern:     str,
    bl_example:     str,
    page_scope:     str = "page0",
) -> str:
    """bl_carrier_registry.py에 붙여넣을 템플릿 코드 생성"""
    kw_repr = repr(detect_kw)
    return '''
    # ── {carrier_id} ({carrier_name}) ──────────────────────────────────────
    # ⚠️ 주의: 자동 생성 템플릿 — 실제 BL 파일로 검증 후 사용하세요
    "{carrier_id}": CarrierTemplate(
        carrier_id="{carrier_id}",
        carrier_name="{carrier_name}",
        detect_keywords={kw_repr},
        detect_pattern=r"{detect_kw[0] if detect_kw else carrier_id}",
        bl_extract_pattern=r"{bl_pattern}",
        bl_page_scope="{page_scope}",
        bl_format_hint="{bl_example}",
        sap_page_hint="all",
        bl_no_prompt_hint=(
            "【{carrier_name} Bill of Lading 전용 규칙】\\n"
            "BL No 위치: 1페이지 상단 \'B/L No.\' 라벨 근처\\n"
            "형식 예시: {bl_example}\\n"
            "⚠️ 주의: 자동 생성 — 실제 BL로 검증 필요"
        ),
    ),
'''


def run_analysis(pdf_path: str, carrier_id: str = "") -> None:
    """메인 분석 실행"""
    print(f"\n{'='*65}")
    print("  BL 선사 패턴 분석 도구  —  SQM v6.4.0")
    print(f"{'='*65}")
    print(f"  파일: {pdf_path}")
    print(f"  입력 선사ID: {carrier_id or '(자동탐지)' }")

    # 텍스트 추출
    pages_text = extract_text_from_pdf(pdf_path)
    if not pages_text:
        print("  ❌ PDF 텍스트 추출 실패")
        return

    print(f"\n  ✅ PDF 텍스트 추출 완료: {len(pages_text)}페이지")
    for i, t in enumerate(pages_text):
        first_line = (t.splitlines()[0] if t.strip() else "(빈 페이지)").strip()[:80]
        print(f"    [Page {i+1}] {first_line}")

    # 기존 레지스트리로 선사 탐지
    try:
        _dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, _dir)
        from bl_carrier_registry import detect_carrier
        detected = detect_carrier(pages_text[0])
        if detected:
            print(f"\n  🎯 기존 레지스트리 탐지: {detected.carrier_name} ({detected.carrier_id})")
            if not carrier_id:
                carrier_id = detected.carrier_id
    except Exception as e:
        logger.debug(f"레지스트리 탐지 건너뜀: {e}")

    # BL No 후보 추출
    candidates = analyze_bl_candidates(pages_text)
    print(f"\n  📋 BL No 후보 목록 ({len(candidates)}건):")
    shown = set()
    for c in candidates:
        key = (c["pattern_name"], c["match"])
        if key in shown:
            continue
        shown.add(key)
        print(f"    [{c['page']+1}페이지] {c['pattern_name']:25s} → {c['match']:20s}")
        print(f"           컨텍스트: ...{c['context']}...")

    # 최적 패턴 추천
    best_pattern = recommend_pattern(candidates, carrier_id)
    best_example = candidates[0]["match"] if candidates else "EXAMPLE123"
    print(f"\n  ⭐ 추천 정규식: {best_pattern}")
    print(f"  ⭐ BL No 예시: {best_example}")

    # 템플릿 코드 생성
    inferred_name = carrier_id.replace("_", " ").title() if carrier_id else "Unknown Carrier"
    kws = [w for w in pages_text[0].upper().split()[:30] if len(w) > 3 and w.isalpha()][:3]
    code = generate_template_code(
        carrier_id   = carrier_id or "NEW_CARRIER",
        carrier_name = inferred_name,
        detect_kw    = kws or [carrier_id or "NEW_CARRIER"],
        bl_pattern   = best_pattern,
        bl_example   = best_example,
    )
    print(f"\n  {'─'*60}")
    print("  📄 bl_carrier_registry.py에 붙여넣을 코드:")
    print(f"  {'─'*60}")
    print(code)
    print(f"  {'─'*60}")
    print("  💡 사용법: CARRIER_TEMPLATES 딕셔너리에 위 코드 추가")
    print("  💡 이후: python bl_carrier_update_tool.py <pdf> 로 검증")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python bl_carrier_update_tool.py <BL_PDF_경로> [선사ID]")
        print("예시:   python bl_carrier_update_tool.py HMM_BL.pdf HMM")
        sys.exit(1)
    run_analysis(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
