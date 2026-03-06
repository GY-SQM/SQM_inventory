SQM v6.5.0 FINAL ALL v10
========================
2026-03-07

[v10 수정 — onestop_inbound.py]

1. TclError 완전 수정
   _parse_thread → after(0) 메인스레드 위임

2. 창 크기 정상화
   state(zoomed) → 1100x780 적정 크기

3. 미리보기 테이블 기본 숨김
   창 열릴 때: 서류 선택 영역만 (심플)
   파싱 완료 후: 자동 테이블 표시
