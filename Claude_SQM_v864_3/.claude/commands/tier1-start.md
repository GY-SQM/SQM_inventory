---
description: Tier 1 (Safe Zone 구축)을 자동으로 시작합니다
---

# /tier1-start

당신은 SQM v864.3 마이그레이션 프로젝트의 수석 아키텍트입니다.

## 수행할 작업

1. **컨텍스트 로딩:**
   - `CLAUDE.md` 읽기 (프로젝트 전체 규칙)
   - `TIER1_PLAN.md` 읽기 (Tier 1 상세 계획)
   - `docs/handoff/v864_2_structure.json` 읽기 (UI 구조)
   - `docs/handoff/design_tokens.json` 읽기 (디자인 토큰)

2. **Plan Mode 전환:**
   - Tier 1 작업을 Agent A(백엔드), B(프론트엔드), C(빌드/QA)로 분해
   - 각 Agent의 산출물 경로를 사장님께 확인

3. **병렬 Sub-Agent 투입:**
   - Agent A: `backend/` 디렉토리 구축 (FastAPI + PyWebView 통합)
   - Agent B: `frontend/` 디렉토리 구축 (HTML + CSS 디자인 시스템)
   - Agent C: Agent A, B 완료 후 `build/` PyInstaller 설정

4. **통합 검증:**
   - `python backend/main.py` 로컬 실행 테스트
   - TIER1_PLAN.md의 Smoke Test 체크리스트 전체 실행

5. **Git 커밋:**
   - `git add .`
   - `git commit -m "feat(tier1): PyWebView shell with full UI replica of v864.2"`
   - `git tag v864.3-tier1`

## 중요 원칙

- **비즈니스 로직 작성 금지** — Tier 1은 껍데기만
- **v864.2 원본 파일 수정 금지** — engine_modules/, features/, parsers/, utils/ 건드리지 말 것
- **CSS 변수 필수** — 색상/폰트 하드코딩 금지
- **모든 버튼은 클릭 가능해야 함** — 기능 없으면 "준비 중" Toast

## 완료 조건

- [ ] exe가 빌드되고 실행된다
- [ ] v864.2와 시각적으로 동일한 레이아웃
- [ ] 25+ 개 클릭 가능 요소 전부 반응
- [ ] Dark/Light 테마 토글 작동
- [ ] FastAPI Swagger UI 접근 가능

작업 시작 전 사장님께 "Tier 1을 시작합니다. 예상 소요 2일. 진행할까요?"라고 확인하세요.
