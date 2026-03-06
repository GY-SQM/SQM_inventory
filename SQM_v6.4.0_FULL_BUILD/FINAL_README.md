SQM v6.5.0 FINAL ALL v9
========================
날짜: 2026-03-07

【v6.5.0 최종 수정 (1+2+3)】

  1) 로그 메시지 확인 포인트 (onestop_inbound.py)
     → "⚡ 자동 파싱 시작 (빠른 스캔 모드)" 메시지로 타이밍 확인
     → 3단계: update_idletasks → after_idle → after(500ms)

  2) 탐지 로직 분리 (inbound_doc_detector.py 신규)
     inbound_processor.py:  338줄 → 168줄 (-170줄)
     inbound_doc_detector.py: 246줄 (탐지 전담)
     단일 책임 / 독립 테스트 / 향후 AI 교체 용이

  3) pytest 15개 추가 (tests/test_inbound_doc_detector.py)
     collect_candidate_files: 4개
     detect_from_folder: 6개  
     detect_by_pdf_text: 5개 (실제 PL/FA PDF 검증)
     전체: 15/15 PASSED (2.16초)

【파일 구성 — 19개】
  gui_app_modular/handlers/
    inbound_processor.py       입고 핸들러 (168줄, 탐지 위임)
    inbound_doc_detector.py    탐지 전담 모듈 (246줄) ← 신규
  tests/
    test_bl_carrier_registry.py  20개
    test_inbound_doc_detector.py 15개 ← 신규

【pytest 전체】
  test_bl_carrier_registry.py:   20/20 PASSED
  test_inbound_doc_detector.py:  15/15 PASSED
  합계: 35개
