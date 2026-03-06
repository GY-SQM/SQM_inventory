SQM v6.3.5 패치 v4 + 단위 테스트
===================================
작성: Ruby  /  날짜: 2026-03-06

## 포함 파일
  features/ai/gemini_parser.py          ← BUG 1~6 수정
  parsers/cross_check_engine.py         ← BUG-3 정렬 수정
  gui_app_modular/dialogs/onestop_inbound.py  ← BUG-3 순번 표시
  tests/test_gemini_parser_v635.py      ← 단위 테스트 31개

## 단위 테스트 실행
  pip install pytest
  pytest tests/test_gemini_parser_v635.py -v

## 테스트 커버리지
  TestParseEuroWeight          7개  유럽식/미국식 숫자 변환
  TestMakeLotFingerprint       3개  fingerprint 생성
  TestBug4LotNoPrimaryGuard    4개  BUG-4: PL 25개 오파싱
  TestBug5IsRetryFalseWarning  3개  BUG-5: 거짓 경고
  TestBug6RetryThreshold       7개  BUG-6: 재시도 조건 강화
  TestBug1InvoiceHallucinationFilter  4개  BUG-1: Invoice hallucination
  TestIntegration2200034274    3개  통합: 실제 선적 시나리오
  ─────────────────────────────────
  합계                        31개  전체 PASS ✅

## BUG 수정 목록 (v6.3.4 → v6.3.5)
  BUG-1: Invoice LOT Hallucination 필터
  BUG-2: PL LOT Hallucination 필터
  BUG-3: LOT 불일치 PL list_no 순서 정렬 + 순번 표시
  BUG-4: PL 24→25개 오파싱 (lot_no 1차 방어선)
  BUG-5: '중복으로 스킵된 LOT N건' 거짓 경고
  BUG-6: 재시도 발동 조건 >0 → >=3, 최대2회→1회
