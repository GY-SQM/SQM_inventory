---
description: Tier 2 단계에서 특정 기능(F001~F085)을 구현합니다
argument-hint: <feature_id> (예: F001)
---

# /tier2-implement

사용법: `/tier2-implement F001`

## 수행할 작업

1. **기능 정보 조회:**
   - `docs/handoff/feature_matrix.json`에서 `$1` (예: F001)에 해당하는 항목 찾기
   - 다음 정보 확인:
     - `label_korean` (UI 라벨)
     - `tkinter_callback` (v864.2 원본 함수)
     - `tkinter_source` (원본 파일:라인)
     - `business_logic_file` (백엔드 로직 파일)
     - `proposed_api_endpoint` (FastAPI 경로)
     - `proposed_js_handler` (JS 핸들러 이름)

2. **Backend 구현:**
   - `business_logic_file`을 `backend/legacy/`로 복사 (아직 없으면)
   - `backend/api/` 하위에 해당 카테고리의 엔드포인트 파일 생성/수정
   - **규칙:** legacy 함수를 직접 호출하는 얇은 wrapper만 작성
   - try/except + HTTPException 필수

3. **Frontend 구현:**
   - `frontend/js/handlers/`에 `proposed_js_handler` 함수 작성
   - fetch API 호출 + 결과 처리 + 에러 Toast
   - 해당 UI 요소(버튼/메뉴)에 onclick 연결

4. **회귀 검증 (v864.2 대조):**
   - v864.2에서 같은 기능 실행 → 결과 기록
   - v864.3에서 같은 기능 실행 → 결과 비교
   - 불일치 발견 시 즉시 중단하고 사장님께 보고

5. **개별 Git 커밋:**
   - `git add <변경된 파일들>`
   - `git commit -m "feat(tier2): implement $1 - <label_korean>"`
   - **규칙:** 기능당 1 커밋. 여러 기능 묶지 말 것 (롤백 가능성)

## 중요 원칙

- **v864.2 비즈니스 로직은 수정 금지** — legacy 복사 후에도 내용 동일
- **개별 커밋 원칙** — 기능 하나당 커밋 하나. 섞지 말 것
- **회귀 테스트 필수** — 대조 없이 "완료" 표기 금지
- **에러 처리** — 모든 실패 경로에 사용자 알림

## 완료 조건

- [ ] v864.2와 동일한 결과 확인됨
- [ ] Backend 엔드포인트 Swagger에 표시됨
- [ ] Frontend 버튼/메뉴가 정상 반응
- [ ] Git 커밋 완료 (단일 기능 단위)

작업 완료 후 `feature_matrix.json`에 `"tier2_status": "completed"` 표시 추가.
