SQM v6.3.5 패치 — Invoice/PL LOT 파싱 완전 수정
=================================================
작성: Ruby  /  날짜: 2026-03-06

## 수정된 버그 3종

### BUG-1: Invoice LOT Hallucination 필터 (★치명적)
  파일: features/ai/gemini_parser.py
  - N° LOTES 정규식 결과를 ground-truth로 사용
  - Gemini가 만든 가짜 LOT 자동 제거
  - 로그: "[GeminiParser] Invoice hallucination 필터: N개 제거"
  → 결과: Invoice LOT 28개→24개, Invoice Only 4→0개

### BUG-2: PL LOT Hallucination 필터 (신규 추가)
  파일: features/ai/gemini_parser.py
  - PL 텍스트에서 정규식으로 LOT 추출 (_extract_pl_lots_regex)
  - Gemini PL 결과도 동일하게 hallucination 필터 + 누락 경고
  - 로그: "[GeminiParser] PL hallucination 검증 완료: 원문 N개, Gemini N개 → 최종 N개"

### BUG-3: LOT 불일치 정렬 + 순번 표시
  파일: parsers/cross_check_engine.py
        gui_app_modular/dialogs/onestop_inbound.py
  - Invoice Only: Invoice 원문 등장 순서 정렬
  - PL Only: PL list_no 순서 정렬 (기동님 요청)
  - 팝업 버튼: "1126011037" → "1. 1126011037" 순번 표시

## 적용 방법 (3개 파일 덮어쓰기)
  features/ai/gemini_parser.py
  parsers/cross_check_engine.py
  gui_app_modular/dialogs/onestop_inbound.py

## 재파싱 시뮬레이션 결과 (2200034274 기준)
  패치 전: Invoice 28개, Invoice Only 4개(가짜), PL Only 1개
  패치 후: Invoice 24개, Invoice Only 0개, PL Only 1개(1126011037 실제)
           팝업: "1. 1126011037" 순번 표시
