SQM v6.4.0 — 메뉴 통합 패치 (1+2+3)
=========================================
작성: Ruby  /  날짜: 2026-03-07
pytest: 20/20 PASS ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【1번】 menu_registry.py + custom_menubar.py + toolbar_mixin.py
       🤖 AI 어시스턴트 서브메뉴에 선사 도구 추가
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  menu_registry.py:
    FILE_MENU_AI_TOOLS_ITEMS 리스트 추가 (단일 소스)
      - 🚢 선사 BL 등록 도구   → _on_bl_carrier_register
      - 🔬 선사 패턴 분석       → _on_bl_carrier_analyze

  custom_menubar.py:
    🔧 도구 > 🤖 AI 어시스턴트 서브메뉴 상단에 선사 도구 2개 추가
    (기존 AI채팅/API설정/API테스트 위에 배치)

  toolbar_mixin.py:
    🔧 설정/도구 팝업 메뉴에 "🚢 BL 선사 도구" 서브메뉴 추가
    (Gemini API 서브메뉴 바로 위에 배치)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【2번】 settings_dialog.py — 실제 GUI 다이얼로그 구현
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  _on_bl_carrier_register():
    - Toplevel 820x600 다이얼로그
    - PDF 파일 선택 (filedialog)
    - threading으로 tools/bl_carrier_update_tool.py 실행
    - ScrolledText에 분석 결과 실시간 표시
    - [📂 BL PDF 선택] [🗑️ 지우기] [✕ 닫기] 버튼

  _on_bl_carrier_analyze():
    - Toplevel 700x450 다이얼로그
    - 등록된 선사 목록 + 상세 규칙 표시
    - MSC/Maersk → ✅ 검증됨
    - HMM/CMA/ONE → ⚠️ 샘플 미검증 안내

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【3번】 pytest.ini + test_bl_carrier_registry.py
       carrier 마커 추가 → 선사 테스트만 선택 실행 가능
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  pytest.ini:
    markers에 carrier 마커 추가:
      carrier: BL 선사 탐지/파싱 테스트 (bl_carrier_registry)

  test_bl_carrier_registry.py:
    모든 클래스에 @pytest.mark.carrier 추가
    실행 예시:
      pytest -m carrier           # 선사 테스트만 실행
      pytest -m "not carrier"     # 선사 테스트 제외
      pytest                      # 전체 실행 (20/20 PASS)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
적용 방법
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  gui_app_modular/menu_registry.py              ← 덮어쓰기
  gui_app_modular/mixins/custom_menubar.py      ← 덮어쓰기
  gui_app_modular/mixins/toolbar_mixin.py       ← 덮어쓰기
  gui_app_modular/dialogs/settings_dialog.py    ← 덮어쓰기
  tests/test_bl_carrier_registry.py             ← 덮어쓰기
  pytest.ini                                    ← 덮어쓰기
