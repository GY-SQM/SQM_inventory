# SQM v8.7.0 — UI 디자인 마스터 플랜 문서화

## 개요
**UI 디자인 마스터 플랜** 문서를 추가하고, 테마·간격·컬럼·다이얼로그 등 **인프라 연결 로드맵**을 정리한 릴리스입니다.  
기존에 구축된 ThemeColors, Spacing, FontScale, UICalculator를 실제 코드에 적용하기 위한 **우선순위·체크리스트·파일 목록**을 제공합니다.

---

## v8.7.0에서 반영한 내용

| 항목 | 내용 |
|------|------|
| **문서** | `docs/UI_DESIGN_MASTER_PLAN.md` — 전문가 관점 핵심 문제 3가지·개선안·마이그레이션 체크리스트 |
| **버전** | `version.py` — __version__ = 8.7.0, VERSION_HISTORY 8.7.0 항목 추가 |
| **우선순위** | 1 색상 팔레트 통일 → 2 8px 그리드 → 3 기본 컬럼 7~8개 → 4 트리뷰 행간/제브라 → 5 폰트 통일 → 6 다이얼로그 표준화 → 7 툴바 미니멀화 |

---

## UI 마스터 플랜 요약

- **가장 큰 문제 3가지**: (1) 색상 하드코딩 169곳 → 다크 테마 시 UI 붕괴 (2) 간격·정렬 규칙 부재 (3) 정보 밀도 과다(재고 19열·톤백 20열 전부 기본 표시)
- **인프라**: ThemeColors, Spacing, FontScale, UICalculator, DialogSize, ReadableStyle — 이미 존재, **연결만 하면 됨**
- **방향**: 32개 파일의 하드코딩을 인프라 참조로 단계적 교체 (새 설계 X)

---

## 변경된 파일 요약

| 구분 | 파일 |
|------|------|
| **버전** | version.py |
| **문서** | docs/UI_DESIGN_MASTER_PLAN.md, docs/RELEASE_NOTES_v8.7.0.md |
| **엔진** | engine_modules/database.py, inventory_modular (base, crud_mixin, inbound_mixin, integrity_mixin), validators.py |
| **GUI** | gui_app_modular/dialogs (onestop_inbound), mixins (custom_menubar, diagnostics, keybindings, menu, toolbar), tabs (inventory_tab, tonbag_tab), utils (__init__, gui_bootstrap, helpers, safe_utils), window_config.json |
| **파서** | parsers/document_parser_modular (bl_mixin, do_mixin) |
| **기타** | features/ai/gemini_parser.py, requirements.txt, theme_preference.json, docs (DEBUGGING_RISK_OVERVIEW, REFACTORING_MASTER_PLAN 등) |

---

*작성일: 2026-02-17 | SQM v8.7.0*
