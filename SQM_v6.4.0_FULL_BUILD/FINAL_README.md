SQM v6.4.0 — FINAL ALL 통합 패치
====================================
작성: Ruby  /  날짜: 2026-03-07
구문 검증: ✅ 12개 파일 전체 PASS
pytest:   ✅ 20/20 PASS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【1번】 Import 들여쓰기 전수조사 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  배포 대상 파일 들여쓰기 오류: 0건 (수정 완료)
  원인: custom_menubar.py import 블록에서
        FILE_MENU_AI_TOOLS_ITEMS 들여쓰기 4칸 → 12칸 수정
  위험 ImportError fallback: 2건 → 모두 핫픽스 완료
    ① custom_menubar.py _create_file_menu → 수정됨
    ② toolbar_mixin.py _build_inbound_menu → try/except 안전화

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【2번】 FINAL ALL 통합 (이전 세션 모든 패치 포함)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  신규 파일 (3개):
    features/ai/bl_carrier_registry.py   309줄
    tools/bl_carrier_update_tool.py       197줄
    tests/test_bl_carrier_registry.py     272줄

  수정 파일 (9개):
    features/ai/gemini_parser.py         1552줄  BLResult 필드 + 선사 레지스트리 통합
    parsers/cross_check_engine.py         516줄  Maersk BL==Booking 경고 생략
    gui_app_modular/dialogs/
      onestop_inbound.py                 2486줄  선사 뱃지 위젯 UI
      settings_dialog.py                  608줄  BL 선사 도구 다이얼로그
    gui_app_modular/
      menu_registry.py                     81줄  AI 도구 + 빠른 PDF 스캔 (PATCH1 포함)
      mixins/custom_menubar.py             813줄  선사 도구 메뉴 + import 핫픽스
      mixins/toolbar_mixin.py             1302줄  선사 도구 서브메뉴 + try/except
    version.py                             116줄  v6.4.0 릴리즈 노트
    pytest.ini                              35줄  carrier 마커 추가

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【3번】 입고 메뉴 체크리스트 (패치 후 확인사항)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  입고 ▼ 클릭 시 다음 12개 항목이 표시되어야 함:
   1. 📄 PDF 스캔 입고
   2. ⚡ 빠른 PDF 스캔 (폴더)        ← PATCH1 추가
   3. 📊 엑셀 파일 수동 입고
   4. 📋 D/O 후속 연결
   5. 📍 톤백 위치 매핑 (선택)
   6. 📋 입고 현황 조회 (선택)
   7. 📂 반품 입고 (Excel)
   8. 🔄 반품 (재입고)
   9. 📊 반품 사유 통계
  10. 📧 반품 경고 이메일
  11. ⚙️ 이메일 설정
  12. 📋 정합성 검증 리포트 (선택)

  🔧 도구 > 🤖 AI 어시스턴트 에서:
    - 🚢 선사 BL 등록 도구  ← 신규
    - 🔬 선사 패턴 분석     ← 신규

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
적용 방법
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1) 모든 파일 덮어쓰기 (tools/, tests/ 디렉토리 없으면 생성)
  2) SQM 재시작
  3) 입고 ▼ → 12개 항목 확인
  4) 🔧 도구 > 🤖 AI 어시스턴트 → 선사 도구 2개 확인
  5) pytest → 20/20 PASS 확인
