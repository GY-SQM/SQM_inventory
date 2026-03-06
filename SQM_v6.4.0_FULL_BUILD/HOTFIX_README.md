SQM v6.4.0 — 핫픽스: 입고 메뉴 2개만 표시되는 문제 수정
=============================================================
작성: Ruby  /  날짜: 2026-03-07

【원인】
  custom_menubar.py 의 import 블록에서 FILE_MENU_AI_TOOLS_ITEMS 의
  들여쓰기가 4칸으로 깨짐 → 런타임 ImportError 발생 →
  _build_inbound_menu fallback 실행 → "PDF 스캔 입고" + "빠른 PDF 스캔" 2개만 표시

【수정 파일 3개】

  ① gui_app_modular/menu_registry.py
     - PATCH1 기반 (⚡ 빠른 PDF 스캔 (폴더) + 🚀 S1 원스톱 출고 포함)
     - FILE_MENU_AI_TOOLS_ITEMS 추가

  ② gui_app_modular/mixins/custom_menubar.py
     - import 블록 들여쓰기 수정 (4칸 → 8칸)
       Before: '    FILE_MENU_AI_TOOLS_ITEMS,'   (4칸)
       After:  '            FILE_MENU_AI_TOOLS_ITEMS,'  (12칸, 정상)
     - lambda __import__ → for 루프 방식으로 안전화

  ③ gui_app_modular/mixins/toolbar_mixin.py
     - BL 선사 도구 서브메뉴: try/except로 감싸 registry 미배포 시 조용히 생략

【적용 방법】
  1) 3개 파일 덮어쓰기
  2) SQM 재시작
  3) 입고 ▼ 클릭 → 전체 메뉴 표시 확인
     (PDF 스캔 입고 / 빠른 PDF 스캔 (폴더) / 엑셀 수동 입고 / D/O 후속 연결 ...)
