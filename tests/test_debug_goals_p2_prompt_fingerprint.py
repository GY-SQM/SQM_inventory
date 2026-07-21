# -*- coding: utf-8 -*-
"""P2 회귀 테스트 — 프롬프트 핑거프린트 (스켈레톤).

P2 (2026-07-21): "이번 PL 파싱이 어떤 프롬프트 버전으로 실행됐나" 역추적용
helper. DB 컬럼 추가는 다음 세션. 이번엔 helper 존재·동작만 검증.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEMINI_PARSER = os.path.join(ROOT, "features", "ai", "gemini_parser.py")


def _read_gemini_parser() -> str:
    with open(GEMINI_PARSER, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _import_gemini_parser():
    sys.path.insert(0, ROOT)
    from features.ai import gemini_parser  # noqa: F401
    return gemini_parser


# ---------------------------------------------------------------------------
# helper 존재 + 시그니처
# ---------------------------------------------------------------------------

def test_p2_prompt_fingerprint_helper_exists():
    """P2: _get_prompt_fingerprint 메서드(또는 정적메서드) 가 정의되어 있어야 함."""
    code = _read_gemini_parser()
    assert "def _get_prompt_fingerprint" in code, (
        "P2 스켈레톤: _get_prompt_fingerprint 메서드 누락"
    )
    # 시그니처: (self 또는 없음, prompt: str) -> str
    sig = re.search(
        r"def\s+_get_prompt_fingerprint\s*\([^)]*\)",
        code,
        re.DOTALL,
    )
    assert sig, "_get_prompt_fingerprint(...) 시그니처를 못 찾음"
    assert "prompt" in sig.group(0), (
        f"_get_prompt_fingerprint 시그니처에 'prompt' 인자 누락: {sig.group(0)!r}"
    )


def test_p2_section_comment_present():
    """P2: P2 섹션 식별 주석이 코드에 있어야 함."""
    code = _read_gemini_parser()
    assert "P2 (2026-07-21) — 프롬프트/좌표 변경 이력 감사" in code, (
        "P2 섹션 주석 누락 — P2 식별자 부재"
    )


# ---------------------------------------------------------------------------
# 동작 검증 (in-process)
# ---------------------------------------------------------------------------

def test_p2_fingerprint_deterministic():
    """P2: 동일 prompt → 동일 fingerprint (결정론적)."""
    mod = _import_gemini_parser()
    fp1 = mod.GeminiDocumentParser._get_prompt_fingerprint("hello world")
    fp2 = mod.GeminiDocumentParser._get_prompt_fingerprint("hello world")
    assert fp1 == fp2, f"동일 prompt인데 fingerprint 다름: {fp1} vs {fp2}"
    assert len(fp1) > 0, "fingerprint가 빈 문자열"


def test_p2_fingerprint_changes_with_content():
    """P2: prompt 내용이 다르면 fingerprint도 달라야 함."""
    mod = _import_gemini_parser()
    fp1 = mod.GeminiDocumentParser._get_prompt_fingerprint("Extract LOT data")
    fp2 = mod.GeminiDocumentParser._get_prompt_fingerprint("Extract LOT rows")
    assert fp1 != fp2, "다른 prompt인데 fingerprint 동일 (충돌 또는 버그)"
    # 12자 hex (sha256 첫 12자) — 문자 검증
    assert re.match(r"^[0-9a-f]{12}$", fp1), f"fingerprint가 12자 hex 형식 아님: {fp1}"


def test_p2_fingerprint_empty_prompt_returns_empty():
    """P2: prompt가 빈 문자열이면 fingerprint도 빈 문자열 (no-op)."""
    mod = _import_gemini_parser()
    fp = mod.GeminiDocumentParser._get_prompt_fingerprint("")
    assert fp == "", f"빈 prompt인데 fingerprint 생성됨: {fp!r}"


def test_p2_fingerprint_korean_prompt_supported():
    """P2: 한글 prompt도 정상 동작 (UTF-8 인코딩 검증)."""
    mod = _import_gemini_parser()
    fp = mod.GeminiDocumentParser._get_prompt_fingerprint("Packing List에서 LOT를 추출하세요")
    assert len(fp) == 12, f"한글 prompt fingerprint 길이 이상: {fp}"
    assert re.match(r"^[0-9a-f]{12}$", fp), f"한글 prompt fingerprint 형식 이상: {fp}"
