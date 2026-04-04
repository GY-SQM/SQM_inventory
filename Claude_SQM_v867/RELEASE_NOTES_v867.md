# SQM `Claude_SQM_v867` 릴리즈 노트

**릴리즈 날짜:** 2026-04-04  
**코드베이스 버전 (`version.py`):** 8.6.5  
**저장소 경로:** `Claude_SQM_v867/`

## 요약

동일 Git 저장소(`Sqm 재고관리`)에 **v867 작업 폴더를 최초로 포함**하는 커밋입니다. 데스크톱(tkinter) 앱, `react_api` 백엔드, `web` 프론트, 테스트·스크립트·문서 패키지가 한 디렉터리에 정리되어 있습니다.

## 포함 범위

- **GUI:** `gui_app_modular/` — 기존 SQM 모듈형 UI
- **엔진:** `engine_modules/` — 입고·출고·쿼리·마이그레이션 등
- **웹/API:** `react_api/`, `web/` — 조회·쓰기 API 및 Vite 기반 프론트
- **문서:** `docs/RECON_V867_WEB_MIGRATION_MAP.md`, `MASTER_FINAL_v867_통합완성본.md`, `GPT_SQM_세션최종결과물_전체_v2/` 등
- **운영 보조:** `scripts/` (Telegram 알림 등), `tests/`

## 보안·운영 메모

- **`.env`**, **`*.db`**, **`node_modules/`**, **`logs/`**, **`output/`**, **`temp/`**, **`backup/`** 등은 루트 `.gitignore` 또는 `web/.gitignore`에 의해 커밋에서 제외됩니다.
- **`.claude/settings.local.json`** 및 **`*.bak_auto` / `*.bak_20*`** 는 이 폴더 전용 `.gitignore`로 제외합니다.

## 이전 버전 대비 (개념)

`MASTER_FINAL_v867_통합완성본.md` 기준, v867에서는 Recon~Phase 8까지의 **웹/API·프론트·보안·대시보드·통합 실행** 작업 축이 문서와 코드에 반영된 스냅샷입니다. 세부 Phase 설명은 해당 MASTER 문서를 참고하세요.

## 검증

로컬에서 다음을 권장합니다.

- `python -m pytest tests/ -q --tb=short` (v867 디렉터리 기준)
- `web/`: `npm install` 후 `npm run build` (Node 환경 필요 시)

---

*(주) 지와이로지스 — SQM 재고관리 시스템*
