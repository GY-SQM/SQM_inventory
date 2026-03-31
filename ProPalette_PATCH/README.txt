SQM Pro 팔레트 패치 v8.6.4 — 2026-03-29
====================================================
적용: SQM 설치 폴더에 덮어씌우기
주의: fixes/ 폴더(신규)도 반드시 복사
====================================================

DARK 팔레트: 딥 미드나잇 블루 × 소프트 스카이 블루
  배경: #0b1322 (딥 미드나잇) — 따뜻한 네이비
  강조: #38bdf8 (스카이 블루) — 눈부심 없음
  카드: Muted Pastel — 채도 낮춰 고급스럽게

LIGHT 팔레트: 쿨 아이스 화이트 × 딥 네이비
  툴바/사이드바: #162040 딥 네이비 유지
  배경: #f0f5fc 쿨 아이스 화이트
  강조: #1460c8 딥 로얄 블루
  카드: Muted Deep — 차분한 딥 톤

====================================================

  gui_app_modular/utils/ui_constants.py
  → DARK/LIGHT 팔레트 완전 교체 — Pro 딥 네이비 × 스카이 블루

  gui_app_modular/tabs/dashboard_tab.py
  → 카드 색상 — Muted Pastel/Deep 동기화

  fixes/__init__.py
  → 신규 패키지

  fixes/global_tree_style.py
  → Treeview 스타일

  fixes/theme_colorful_override.py
  → STATUS_COLORS 동기화

  gui_app_modular/utils/theme_refresh.py
  → apply_global_tree_style 인자

  gui_app_modular/mixins/theme_mixin.py
  → 대시보드 자동 갱신

  gui_app_modular/mixins/toolbar_mixin.py
  → Light→litera + 컬러 버튼 바

  theme_aware.py
  → is_dark → _GLOBAL_IS_DARK
