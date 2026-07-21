# -*- coding: utf-8 -*-
"""P0 회귀 테스트 — 검증기반 프롬프트 교정 재파싱 (스켈레톤).

P0 (2026-07-21): PackingListResult self-consistency 검증 + 교정 프롬프트 빌더.
  - 검증 실패 케이스: Σ행 != total_net_weight_kg
  - 검증 통과 케이스: Σ행 == total_net_weight_kg, lot_count=0 (skip)
  - 교정 전략 2종: integer_only, exclude_known_lots
  - parse_packing_list 본체에는 retry loop 미통합 (다음 세션 작업)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEMINI_PARSER = os.path.join(ROOT, "features", "ai", "gemini_parser.py")


def _read_gemini_parser() -> str:
    with open(GEMINI_PARSER, encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 스켈레톤 존재 확인
# ---------------------------------------------------------------------------

def test_p0_validate_lot_result_method_exists():
    """P0: _validate_lot_result 메서드가 정의되어 있어야 함."""
    code = _read_gemini_parser()
    assert "def _validate_lot_result" in code, (
        "P0 스켈레톤: _validate_lot_result 메서드 누락"
    )
    # 시그니처: (self, result) -> tuple
    sig = re.search(
        r"def\s+_validate_lot_result\s*\(\s*self\s*,\s*result[^)]*\)\s*->\s*tuple",
        code,
    )
    assert sig, "_validate_lot_result 시그니처(self, result) -> tuple 형태여야 함"


def test_p0_build_correction_prompt_method_exists():
    """P0: _build_correction_prompt 메서드가 정의되어 있어야 함."""
    code = _read_gemini_parser()
    assert "def _build_correction_prompt" in code, (
        "P0 스켈레톤: _build_correction_prompt 메서드 누락"
    )
    # 시그니처 핵심 파라미터 4개(self, strategy, result, original_prompt)가 모두 있는지 확인
    # (타입 어노테이션·줄바꿈·trailing comma 등 다양한 표기 허용)
    for needle in ("self", "strategy", "result", "original_prompt"):
        # 메서드 헤더(def ... :) 범위 내에서만 검색
        m = re.search(
            r"def\s+_build_correction_prompt\s*\([^)]*\)",
            code,
            re.DOTALL,
        )
        assert m, "def _build_correction_prompt(...) 시그니처 자체를 못 찾음"
        header = m.group(0)
        assert needle in header, (
            f"_build_correction_prompt 시그니처에 '{needle}' 누락: {header!r}"
        )


def test_p0_correction_strategy_constants_defined():
    """P0: 교정 전략 상수 2종이 클래스 상수로 정의되어 있어야 함."""
    code = _read_gemini_parser()
    assert re.search(
        r"CORRECTION_STRATEGY_INTEGER_ONLY\s*=\s*['\"]p0_integer_only['\"]",
        code,
    ), "CORRECTION_STRATEGY_INTEGER_ONLY 상수 누락"
    assert re.search(
        r"CORRECTION_STRATEGY_EXCLUDE_KNOWN\s*=\s*['\"]p0_exclude_known_lots['\"]",
        code,
    ), "CORRECTION_STRATEGY_EXCLUDE_KNOWN 상수 누락"


# ---------------------------------------------------------------------------
# 동작 검증 (in-process 직접 호출)
# ---------------------------------------------------------------------------

def _import_gemini_parser():
    """테스트 환경에서 gemini_parser 모듈 임포트 (DB 의존 모킹)."""
    sys.path.insert(0, ROOT)
    try:
        # DB 연결 없는 가벼운 임포트 (DB 의존 메서드는 _db=None 으로 동작)
        from features.ai import gemini_parser  # noqa: F401
        return gemini_parser
    finally:
        # sys.path 정리 (다른 테스트에 영향 주지 않도록)
        pass


def test_p0_validate_lot_consistent_returns_ok():
    """P0: Σ행 == total 이면 (ok=True, reason='') 반환."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    lot = mod.LOTItem(list_no=1, lot_no="L1", net_weight_kg=1000.0, gross_weight_kg=1050.0)
    lot2 = mod.LOTItem(list_no=2, lot_no="L2", net_weight_kg=2000.0, gross_weight_kg=2050.0)
    result = mod.PackingListResult(
        lots=[lot, lot2],
        total_net_weight_kg=3000.0,
    )
    ok, reason = parser._validate_lot_result(result)
    assert ok is True, f"Σ행 == total 인데 검증 실패: {reason}"
    assert reason == "", f"검증 통과인데 reason 비어있지 않음: {reason}"


def test_p0_validate_lot_mismatch_returns_fail():
    """P0: Σ행 != total 이면 (ok=False, reason='total_mismatch:...') 반환."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    lot = mod.LOTItem(list_no=1, lot_no="L1", net_weight_kg=1000.0, gross_weight_kg=1050.0)
    lot2 = mod.LOTItem(list_no=2, lot_no="L2", net_weight_kg=2000.0, gross_weight_kg=2050.0)
    # total을 일부러 2999.0 으로 (Σ행 = 3000.0)
    result = mod.PackingListResult(
        lots=[lot, lot2],
        total_net_weight_kg=2999.0,
    )
    ok, reason = parser._validate_lot_result(result)
    assert ok is False, "Σ행 != total 인데 검증 통과로 잘못 판정"
    assert "total_mismatch" in reason, f"실패 사유에 'total_mismatch' 누락: {reason}"


def test_p0_validate_lot_empty_passes_through():
    """P0: LOT 0개일 때는 self-consistency 검증 skip (기존 동작 보존)."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    result = mod.PackingListResult(lots=[], total_net_weight_kg=0.0)
    ok, reason = parser._validate_lot_result(result)
    assert ok is True, "LOT 0개에서 검증 강제 실패시키면 기존 동작 파괴"
    assert "lot_count=0" in reason, f"LOT 0개 사유 표시 누락: {reason}"


# ---------------------------------------------------------------------------
# 교정 프롬프트 빌더
# ---------------------------------------------------------------------------

def test_p0_correction_prompt_integer_only():
    """P0: integer_only 전략 → '정수 추출' 힌트가 포함된 프롬프트 반환."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    result = mod.PackingListResult(lots=[])
    out = parser._build_correction_prompt(
        mod.GeminiDocumentParser.CORRECTION_STRATEGY_INTEGER_ONLY,
        result,
        "ORIG_PROMPT",
    )
    assert "ORIG_PROMPT" in out, "원본 프롬프트가 보존되지 않음"
    assert "정수" in out, "정수 추출 힌트 누락"
    assert "p0_integer_only" in out or "P0" in out, "P0 마커 누락"


def test_p0_correction_prompt_exclude_known_lots():
    """P0: exclude_known_lots 전략 → 기존 LOT 번호가 힌트에 포함됨."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    lot = mod.LOTItem(list_no=1, lot_no="ABC-001", net_weight_kg=1000.0, gross_weight_kg=1050.0)
    lot2 = mod.LOTItem(list_no=2, lot_no="ABC-002", net_weight_kg=2000.0, gross_weight_kg=2050.0)
    result = mod.PackingListResult(lots=[lot, lot2])
    out = parser._build_correction_prompt(
        mod.GeminiDocumentParser.CORRECTION_STRATEGY_EXCLUDE_KNOWN,
        result,
        "ORIG_PROMPT",
    )
    assert "ORIG_PROMPT" in out, "원본 프롬프트가 보존되지 않음"
    assert "ABC-001" in out, "기존 LOT 번호가 힌트에 누락"
    assert "ABC-002" in out, "기존 LOT 번호가 힌트에 누락"
    assert "제외" in out, "제외 지시 누락"


def test_p0_correction_prompt_unknown_strategy_returns_original():
    """P0: 알 수 없는 strategy → 원본 프롬프트 그대로 반환 (안전)."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    result = mod.PackingListResult(lots=[])
    out = parser._build_correction_prompt("unknown_strategy", result, "ORIG_PROMPT")
    assert out == "ORIG_PROMPT", "알 수 없는 strategy에서 원본 보존 실패"


# ---------------------------------------------------------------------------
# parse_packing_list 통합 — 검증 후크가 호출되는지 (로깅만, 동작 변경 없음)
# ---------------------------------------------------------------------------

def test_p0_parse_packing_list_has_validation_hook():
    """P0: parse_packing_list 본체에 _validate_lot_result 호출이 있어야 함.

    parse_packing_list 내부에는 `result.success =` 라인이 여러 개일 수 있어
    (초기화 라인 등) 단순 매치로는 순서를 특정하기 어려움.
    따라서 P0 식별 주석(`P0(2026-07-21): self-consistency 검증 후크`)의
    존재 여부로 통합 여부를 판정한다.
    """
    code = _read_gemini_parser()
    # P0 식별 주석이 parse_packing_list 본체에 있는지 확인
    parse_start = code.find("def parse_packing_list")
    assert parse_start >= 0, "parse_packing_list 함수 시작점 못 찾음"
    hook_idx = code.find("P0(2026-07-21): self-consistency 검증 후크", parse_start)
    assert hook_idx > parse_start, (
        "parse_packing_list 본체에 P0 검증 후크(P0 주석) 누락 — 통합 안 됨"
    )
    # 검증 메서드 호출도 같은 영역에 있는지
    validate_idx = code.find("_validate_lot_result", parse_start)
    assert validate_idx > parse_start, (
        "parse_packing_list 본체에 _validate_lot_result 호출 누락"
    )


def test_p0_validation_log_method_tag_used():
    """P0: 검증 실패 시 _log_parse_result 가 method='p0_validate_failed' 로 호출되어야 함."""
    code = _read_gemini_parser()
    # 단순 substring: p0_validate_failed 또는 _LOG_METHOD_VALIDATE_FAIL 태그가 코드 어딘가에 있어야 함
    assert (
        "p0_validate_failed" in code
        or "_LOG_METHOD_VALIDATE_FAIL" in code
    ), "검증 실패 method 태그('p0_validate_failed')가 코드에 누락"


# ---------------------------------------------------------------------------
# P0 retry loop (_retry_parse_with_validation) — 1차 실패 → 2차 성공 시나리오
# ---------------------------------------------------------------------------

def test_p0_retry_method_exists():
    """P0: _retry_parse_with_validation 메서드가 정의되어 있어야 함."""
    code = _read_gemini_parser()
    assert "def _retry_parse_with_validation" in code, (
        "P0 retry: _retry_parse_with_validation 메서드 누락"
    )
    for needle in ("pdf_path", "images", "result", "original_prompt", "max_retry"):
        m = re.search(
            r"def\s+_retry_parse_with_validation\s*\([^)]*\)",
            code,
            re.DOTALL,
        )
        assert m, "_retry_parse_with_validation(...) 시그니처 못 찾음"
        assert needle in m.group(0), (
            f"_retry_parse_with_validation 시그니처에 '{needle}' 누락: {m.group(0)!r}"
        )


def test_p0_retry_called_in_parse_packing_list():
    """P0: parse_packing_list 본체에 _retry_parse_with_validation 호출이 있어야 함."""
    code = _read_gemini_parser()
    parse_start = code.find("def parse_packing_list")
    assert parse_start >= 0, "parse_packing_list 시작점 못 찾음"
    retry_idx = code.find("_retry_parse_with_validation", parse_start)
    assert retry_idx > parse_start, (
        "parse_packing_list 본체에 _retry_parse_with_validation 호출 누락"
    )


def test_p0_retry_log_method_tag_used():
    """P0: retry 시 _log_parse_result 가 method='gemini_retryN' 으로 호출되어야 함."""
    code = _read_gemini_parser()
    retry_start = code.find("def _retry_parse_with_validation")
    assert retry_start >= 0, "_retry_parse_with_validation 메서드 시작점 못 찾음"
    # 메서드 본문은 시작점부터 다음 클래스 끝(파일 끝 또는 class 정의의 마지막 라인)까지 단순 슬라이스.
    # 정확한 끝 매칭은 nested def 때문에 fragile → 단순 substring 으로 충분.
    body = code[retry_start:]
    # 너무 짧으면 다른 def 의 일부를 잘라 가져온 것. 다음 def 가 등장하기 전까지가 본문.
    next_def = body.find("\n    def ", 10)
    if next_def > 0:
        body = body[:next_def]
    assert "gemini_retry" in body, (
        "_retry_parse_with_validation 본문에 'gemini_retry' method 태그 누락"
    )
    assert "for attempt in range" in body, (
        "_retry_parse_with_validation 본문에 attempt loop 누락"
    )


def test_p0_retry_scenario_fail_then_succeed():
    """P0: 1차 검증 실패 → retry1 (integer_only) 호출 → 2차 성공 시나리오.

    시나리오:
      - 초기 result: 2 LOT, total=3000.0, Σ행=3000.0 (검증 통과여야 함)
      - 강제로 total=2500.0 으로 깨뜨려 검증 실패 만들기
      - retry1 호출: _call_gemini 가 새 LOT 1개 반환 (total 정정됨)
      - 그 후 검증 통과해야 함

    mocking: _call_gemini 와 _extract_json 만 monkeypatch.
    """
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    # 1차 결과: 2 LOT, total은 일부러 2500.0 (Σ행=3000.0 → mismatch)
    lot1 = mod.LOTItem(
        list_no=1, lot_no="L1", net_weight_kg=1000.0, gross_weight_kg=1050.0
    )
    lot2 = mod.LOTItem(
        list_no=2, lot_no="L2", net_weight_kg=2000.0, gross_weight_kg=2050.0
    )
    result = mod.PackingListResult(
        lots=[lot1, lot2],
        total_net_weight_kg=2500.0,  # 의도적 mismatch
    )

    # retry1 응답: 새 LOT 1개 (L3, 500kg) → 새 total = 3500.0, Σ행=3500.0
    retry1_response = '{"lots": [{"lot_no": "L3", "net_weight_kg": 500, "gross_weight_kg": 520, "mxbg": 5}]}'

    call_log: list = []

    def fake_call_gemini(prompt, image, *args, **kwargs):
        call_log.append(("call", prompt))
        return retry1_response

    def fake_extract_json(text):
        import json
        call_log.append(("extract", text))
        return json.loads(text)

    # monkey patch
    parser._call_gemini = fake_call_gemini
    parser._extract_json = fake_extract_json

    # retry 발동
    parser._retry_parse_with_validation(
        pdf_path="dummy.pdf",
        images=[b"fake_image_bytes"],
        result=result,
        original_prompt="ORIG",
        max_retry=2,
    )

    # retry1 이 한 번 호출됐어야 함
    assert len(call_log) >= 2, f"_call_gemini 또는 _extract_json 호출 안 됨: {call_log}"
    call_count = sum(1 for kind, _ in call_log if kind == "call")
    assert call_count == 1, f"retry1 1회만 호출되어야 함 (성공 후 early return). 실제 {call_count}회"

    # LOT 3개로 늘어났어야 함
    assert len(result.lots) == 3, f"retry1 후 LOT 3개여야 함. 실제 {len(result.lots)}개"

    # total 재계산 검증
    expected_total = 1000.0 + 2000.0 + 500.0
    assert abs(result.total_net_weight_kg - expected_total) < 0.01, (
        f"total_net_weight_kg 재계산 실패. 기대={expected_total}, 실제={result.total_net_weight_kg}"
    )

    # 검증 통과 (다음 retry 안 함)
    ok, _ = parser._validate_lot_result(result)
    assert ok is True, f"retry1 후 검증 통과해야 함. actual: ok={ok}"


def test_p0_retry_scenario_retry2_used_when_retry1_no_add():
    """P0: retry1 (integer_only) 가 새 LOT 0개 → retry2 (exclude_known_lots) 발동 시나리오.

    시나리오:
      - 초기 result: mismatch
      - retry1 응답: 기존과 같은 LOT만 있음 (new add=0) → _no_add 로깅 후 continue
      - retry2 응답: 새 LOT 1개 → merge, 검증 통과
    """
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    lot1 = mod.LOTItem(
        list_no=1, lot_no="L1", net_weight_kg=1000.0, gross_weight_kg=1050.0
    )
    lot2 = mod.LOTItem(
        list_no=2, lot_no="L2", net_weight_kg=2000.0, gross_weight_kg=2050.0
    )
    result = mod.PackingListResult(
        lots=[lot1, lot2],
        total_net_weight_kg=2500.0,  # mismatch
    )

    # retry1 응답: 기존과 같은 LOT만 (L1)
    retry1_response = '{"lots": [{"lot_no": "L1", "net_weight_kg": 1000, "gross_weight_kg": 1050}]}'
    # retry2 응답: 새 LOT (L3)
    retry2_response = '{"lots": [{"lot_no": "L3", "net_weight_kg": 500, "gross_weight_kg": 520, "mxbg": 5}]}'

    responses = [retry1_response, retry2_response]
    call_count = {"n": 0}

    def fake_call_gemini(prompt, image, *args, **kwargs):
        idx = call_count["n"]
        call_count["n"] += 1
        return responses[idx]

    def fake_extract_json(text):
        import json
        return json.loads(text)

    parser._call_gemini = fake_call_gemini
    parser._extract_json = fake_extract_json

    parser._retry_parse_with_validation(
        pdf_path="dummy.pdf",
        images=[b"fake_image_bytes"],
        result=result,
        original_prompt="ORIG",
        max_retry=2,
    )

    # retry 2회 모두 호출됐어야 함
    assert call_count["n"] == 2, (
        f"retry 2회 호출되어야 함. 실제 {call_count['n']}회"
    )

    # LOT 3개 (기존 2개 + retry2의 L3)
    assert len(result.lots) == 3, f"LOT 3개여야 함. 실제 {len(result.lots)}개"
    lot_nos = {l.lot_no for l in result.lots}
    assert "L3" in lot_nos, "retry2에서 추가한 L3가 결과에 없음"

    # total 재계산
    expected_total = 1000.0 + 2000.0 + 500.0
    assert abs(result.total_net_weight_kg - expected_total) < 0.01, (
        f"total 재계산 실패. 기대={expected_total}, 실제={result.total_net_weight_kg}"
    )


def test_p0_retry_max_attempts_respected():
    """P0: max_retry=2 면 _call_gemini 최대 2회까지만 호출."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    # 1차 결과: mismatch 상태 (LOT 1개 + total 불일치)
    lot1 = mod.LOTItem(
        list_no=1, lot_no="L1", net_weight_kg=1000.0, gross_weight_kg=1050.0
    )
    result = mod.PackingListResult(
        lots=[lot1],
        total_net_weight_kg=500.0,  # mismatch (Σ행=1000)
    )

    # retry 응답이 매번 같은 LOT (L1) → new add=0, continue → 다음 retry
    same_response = '{"lots": [{"lot_no": "L1", "net_weight_kg": 1000, "gross_weight_kg": 1050}]}'
    call_count = {"n": 0}

    def fake_call_gemini(prompt, image, *args, **kwargs):
        call_count["n"] += 1
        return same_response

    def fake_extract_json(text):
        import json
        return json.loads(text)

    parser._call_gemini = fake_call_gemini
    parser._extract_json = fake_extract_json

    parser._retry_parse_with_validation(
        pdf_path="dummy.pdf",
        images=[b"fake_image_bytes"],
        result=result,
        original_prompt="ORIG",
        max_retry=2,
    )

    # max_retry=2 → _call_gemini 최대 2회
    assert call_count["n"] == 2, (
        f"max_retry=2 위반: {call_count['n']}회 호출됨 (상한 초과)"
    )


def test_p0_retry_no_images_skips():
    """P0: images 가 빈 리스트면 retry 자체를 no-op."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    lot1 = mod.LOTItem(
        list_no=1, lot_no="L1", net_weight_kg=1000.0, gross_weight_kg=1050.0
    )
    result = mod.PackingListResult(
        lots=[lot1],
        total_net_weight_kg=500.0,  # mismatch
    )

    call_made = {"n": 0}

    def fake_call_gemini(prompt, image, *args, **kwargs):
        call_made["n"] += 1
        return "{}"

    parser._call_gemini = fake_call_gemini
    parser._extract_json = lambda t: {}

    parser._retry_parse_with_validation(
        pdf_path="dummy.pdf",
        images=[],  # 빈 리스트
        result=result,
        original_prompt="ORIG",
        max_retry=2,
    )

    assert call_made["n"] == 0, "images=[] 인데 _call_gemini 호출됨 (방어 실패)"


def test_p0_retry_early_return_on_already_valid():
    """P0: 1차 결과가 이미 검증 통과면 retry 자체를 발동 안 함 (no-op)."""
    mod = _import_gemini_parser()
    parser = mod.GeminiDocumentParser.__new__(mod.GeminiDocumentParser)
    parser._db = None

    # 1차 결과: 검증 통과 (Σ행 == total)
    lot1 = mod.LOTItem(
        list_no=1, lot_no="L1", net_weight_kg=1000.0, gross_weight_kg=1050.0
    )
    lot2 = mod.LOTItem(
        list_no=2, lot_no="L2", net_weight_kg=2000.0, gross_weight_kg=2050.0
    )
    result = mod.PackingListResult(
        lots=[lot1, lot2],
        total_net_weight_kg=3000.0,  # Σ행=3000.0, 일치
    )

    call_made = {"n": 0}

    def fake_call_gemini(prompt, image, *args, **kwargs):
        call_made["n"] += 1
        return "{}"

    parser._call_gemini = fake_call_gemini
    parser._extract_json = lambda t: {}

    parser._retry_parse_with_validation(
        pdf_path="dummy.pdf",
        images=[b"fake_image_bytes"],
        result=result,
        original_prompt="ORIG",
        max_retry=2,
    )

    assert call_made["n"] == 0, "검증 통과인데 _call_gemini 호출됨 (조기 종료 실패)"
